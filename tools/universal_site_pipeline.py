#!/usr/bin/env python3
import os
import re
import sys
import argparse
import datetime as dt
from urllib.parse import urljoin, urlparse
from typing import List, Tuple, Dict

# HTTP fetcher
try:
    import cloudscraper
    http = cloudscraper.create_scraper()
except Exception:
    import requests
    http = requests.Session()

from bs4 import BeautifulSoup
import tldextract
from pymongo import MongoClient, ASCENDING, DESCENDING
from openai import OpenAI

# ----------------------------
# Utilitare
# ----------------------------
def now_ts():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def normalize_url(base: str, href: str) -> str | None:
    try:
        u = urljoin(base, href)
        pu = urlparse(u)
        u = pu._replace(fragment="").geturl()
        return u.rstrip("/")
    except Exception:
        return None

def same_domain(u: str, base: str) -> bool:
    try:
        d1 = tldextract.extract(u).top_domain_under_public_suffix
        d2 = tldextract.extract(base).top_domain_under_public_suffix
        return d1 == d2
    except Exception:
        return False

def extract_text(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text).strip()
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    return title, text

def mongo_connect():
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    cli = MongoClient(mongo_url)
    db = cli.get_database("ai_agents")
    col = db.get_collection("universal_site_pages")
    col.create_index([("url", ASCENDING)], unique=True)
    col.create_index([("domain", ASCENDING), ("content_length", DESCENDING)])
    col.create_index([("ts", DESCENDING)])
    return db, col

def save_page(col, doc: Dict):
    try:
        col.update_one({"url": doc["url"]}, {"$set": doc}, upsert=True)
    except Exception as e:
        print(f"[WARN] upsert url={doc['url']} failed: {e}", file=sys.stderr)

def list_internal_links(html: str, base: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        u = normalize_url(base, a["href"])
        if not u:
            continue
        if same_domain(u, base):
            links.add(u)
    return list(links)

# ----------------------------
# Scraping (BFS limitat)
# ----------------------------
def ingest_site(start_url: str, max_pages: int = 120, max_depth: int = 3, timeout: int = 20):
    db, col = mongo_connect()
    base = start_url.rstrip("/")
    seed = base
    seen = set()
    queue: List[Tuple[str, int]] = [(seed, 0)]
    grabbed = 0

    print(f"[INFO] Ingest start: {base} (max_pages={max_pages}, max_depth={max_depth})")
    while queue and grabbed < max_pages:
        url, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            r = http.get(url, timeout=timeout)
            status = getattr(r, "status_code", 0)
            html = r.text if hasattr(r, "text") else r.content.decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[WARN] GET {url} failed: {e}", file=sys.stderr)
            continue

        if status != 200 or not html:
            print(f"[WARN] status={status} for {url}", file=sys.stderr)
            continue

        title, text = extract_text(html)
        domain = tldextract.extract(base).top_domain_under_public_suffix or urlparse(base).netloc
        doc = {
            "url": url,
            "domain": domain,
            "title": title,
            "text": text,
            "html": html[:300000],
            "content_length": len(text),
            "ts": now_ts(),
        }
        save_page(col, doc)
        grabbed += 1
        print(f"[OK] saved ({grabbed}/{max_pages}) {url} len={len(text)}")

        if depth < max_depth:
            for u in list_internal_links(html, base):
                if u not in seen:
                    queue.append((u, depth + 1))

    print(f"[INFO] Ingest done: {grabbed} pagini salvate în Mongo")

# ----------------------------
# Overview (LLM)
# ----------------------------
SYSTEM_PROMPT_RO = (
    "Răspunde exclusiv în limba română. Folosește DOAR informația din conținutul extras (text) și evită presupunerile. "
    "Nu inventa competitori și nu include 'Amazon Romania'. Dacă nu găsești date suficiente, scrie: 'Nu există date suficiente în conținutul extras'. "
    "Structură: Industrie (descriere), Competitori (cu puncte tari/slabe), Oportunități, Riscuri, Plan de 30 de zile."
)

def fetch_pages_for_domain(domain: str, limit: int = 12) -> List[Dict]:
    _, col = mongo_connect()
    cur = col.find({"domain": domain}).sort("content_length", DESCENDING).limit(limit)
    return list(cur)

def build_context(pages: List[Dict], target_tokens: int = 3000) -> str:
    tokens_per_char = 0.25  # ~4 chars/token
    max_chars = int(target_tokens / tokens_per_char)

    def head_tail(txt: str, head: int = 6000, tail: int = 3000) -> str:
        if not txt:
            return ""
        if len(txt) <= head + tail:
            return txt
        return txt[:head] + "\n...\n" + txt[-tail:]

    buf = []
    total = 0
    for p in pages:
        snippet = head_tail(p.get("text", ""))
        segment = "URL: {url}\nTITLE: {title}\nCONTENT:\n{content}\n---\n".format(
            url=p.get("url",""),
            title=p.get("title",""),
            content=snippet
        )
        if total + len(segment) > max_chars:
            break
        buf.append(segment)
        total += len(segment)
    return "".join(buf)

def llm_overview_for_url(site_url: str, model: str, base_url: str, temperature: float, max_tokens: int):
    domain = tldextract.extract(site_url).top_domain_under_public_suffix or urlparse(site_url).netloc
    pages = fetch_pages_for_domain(domain, limit=12)
    if not pages:
        print("[WARN] Nu există pagini salvate pentru domeniul {domain}. Rulează întâi ingest.".format(domain=domain))
        return None

    api_key = os.getenv("OPENAI_API_KEY", "local-vllm")
    client = OpenAI(base_url=base_url, api_key=api_key)

    target = int(os.getenv("CONTEXT_TOKENS", "3000"))
    for tgt in [target, 2200, 1600, 1200, 900]:
        context = build_context(pages, target_tokens=tgt)
        user_prompt = "Generează un overview pentru site-ul: {site}.\nContext (pagini extrase):\n{ctx}\nFii concis, structurat și specific la conținut.".format(
            site=site_url, ctx=context
        )
        msgs = [
            {"role": "system", "content": SYSTEM_PROMPT_RO},
            {"role": "user", "content": user_prompt},
        ]
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content
            return content
        except Exception as e:
            print("[WARN] Retry cu context_tokens={t} din cauza: {err}".format(t=tgt, err=e))
            continue
    return "Nu există date suficiente în conținutul extras sau contextul este prea mare."

def save_markdown(site_url: str, md_text: str):
    domain = tldextract.extract(site_url).top_domain_under_public_suffix or urlparse(site_url).netloc
    fn = domain.replace(".", "_") + "_.md"
    out_dir = os.path.expanduser("~/ai_agents/results")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, fn)
    with open(path, "w", encoding="utf-8") as f:
        f.write("## {site}\n\n- ts: {ts}\n\n".format(site=site_url, ts=now_ts()))
        f.write(md_text.strip() + "\n")
    print("[OK] Markdown salvat: {p}".format(p=path))
    return path

# ----------------------------
# CLI
# ----------------------------
def cmd_ingest(args):
    ingest_site(args.url, max_pages=args.max_pages, max_depth=args.max_depth, timeout=20)

def cmd_overview(args):
    md = llm_overview_for_url(
        site_url=args.url,
        model=args.model,
        base_url=args.base_url,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    if md:
        save_markdown(args.url, md)

def main():
    ap = argparse.ArgumentParser(description="Universal Site Pipeline (scrape + overview)")
    sub = ap.add_subparsers(dest="cmd")

    ap_ing = sub.add_parser("ingest", help="Scrape și salvează pagini în Mongo")
    ap_ing.add_argument("--url", required=True, help="URL site (ex: https://exemplu.ro/)")
    ap_ing.add_argument("--max-pages", type=int, default=120)
    ap_ing.add_argument("--max-depth", type=int, default=3)
    ap_ing.set_defaults(func=cmd_ingest)

    ap_ov = sub.add_parser("overview", help="Generează overview în română folosind LLM")
    ap_ov.add_argument("--url", required=True)
    ap_ov.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap_ov.add_argument("--base-url", default="http://localhost:9302/v1")
    ap_ov.add_argument("--temperature", type=float, default=0.1)
    ap_ov.add_argument("--max-tokens", type=int, default=900)
    ap_ov.set_defaults(func=cmd_overview)

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        sys.exit(1)
    args.func(args)

if __name__ == "__main__":
    main()
