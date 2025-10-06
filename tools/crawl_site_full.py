#!/usr/bin/env python3
import argparse
import re as _re
from urllib.parse import urlparse

import re
import time
import datetime
from datetime import timezone
from urllib.parse import urlparse, urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

import requests
from pymongo import MongoClient
from bs4 import BeautifulSoup

from database.qdrant_vectorizer import QdrantVectorizer

# ---------- Config din ENV ----------
import os
USER_AGENT = os.getenv(
    "CRAWL_UA",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127 Safari/537.36"
)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017")
DB_NAME   = os.getenv("DB_NAME", "ai_agents_db")
COLL_NAME = os.getenv("COLL_NAME", "site_content")

# ---------- Filtre / excluderi ----------
BINARY_EXT = re.compile(
    r"\.(?:pdf|zip|rar|7z|tar|gz|bz2|xz|dmg|exe|apk|msi|iso|bin|"
    r"jpg|jpeg|png|gif|webp|bmp|tiff?|svg|"
    r"mp3|wav|flac|aac|ogg|m4a|"
    r"mp4|mkv|avi|mov|webm|"
    r"docx?|xlsx?|pptx?|csv|tsv|ics)(?:[#?].*)?$",
    re.I
)

NOISY_PATH = re.compile(
    r"(/search|/feeds?|/feed/|/wp-json|/wp-admin|/tag/|/author/|/comments?/)"
    r"|(\.(?:rss|atom)$)",
    re.I
)

NOISY_QUERY_KEYS = {"s", "q", "query", "format", "share", "ref", "utm_source", "utm_medium",
                    "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"}

ALLOWED_CT = (
    "text/html",
    "application/xhtml+xml",
    "text/plain",
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"})


def normalize_url(u: str) -> str:
    try:
        s = urlsplit(u)
        s = s._replace(fragment="")
        qs = [(k, v) for k, v in parse_qsl(s.query, keep_blank_values=True)
              if k.lower() not in NOISY_QUERY_KEYS]
        q = urlencode(qs, doseq=True)
        # path curat, fără trailing slash inutil
        path = s.path or "/"
        path = re.sub(r"/+", "/", path)
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        s = s._replace(query=q, path=path)
        return urlunsplit(s)
    except Exception:
        return u


def same_site(u: str, root_domain: str, include_subdomains: bool) -> bool:
    d = urlparse(u).netloc.lower()
    rd = root_domain.lower()
    if include_subdomains:
        return d == rd or d.endswith("." + rd)
    return d == rd


def is_binary_url(u: str) -> bool:
    return bool(BINARY_EXT.search(u))


def looks_noisy(u: str) -> bool:
    sp = urlsplit(u)
    if NOISY_PATH.search(sp.path or ""):
        return True
    # query chei zgomotoase
    for k, _ in parse_qsl(sp.query, keep_blank_values=True):
        if k.lower() in NOISY_QUERY_KEYS:
            return True
    return False


def content_type_is_allowed(ct: str | None) -> bool:
    if not ct:
        return True  # unele servere nu seteză corect; lăsăm să treacă dar filtrăm prin heuristici
    ct = ct.split(";")[0].strip().lower()
    if ct in ALLOWED_CT:
        return True
    # respinge binarele uzuale
    if any(x in ct for x in ("application/pdf", "application/zip", "application/msword",
                              "application/vnd", "image/", "audio/", "video/")):
        return False
    return False


def fetch(url: str, timeout: int = 30) -> tuple[str | None, str | None]:
    try:
        r = SESSION.get(url, timeout=timeout, allow_redirects=True)
        final = r.url
        ct = r.headers.get("Content-Type", "")
        if not content_type_is_allowed(ct):
            return None, final
        if r.status_code != 200:
            return None, final
        text = r.text or ""
        # brut, dar destul de robust: dacă răspunsul e suspicios de binar (nul bytes)
        if "\x00" in text:
            return None, final
        return text, final
    except Exception:
        return None, None


def extract_text_and_links(html: str, base_url: str) -> tuple[str, list[str], str]:
    soup = BeautifulSoup(html, "html.parser")
    # titlul
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    # text
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # outlinks
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("mailto:") or href.startswith("tel:"):
            continue
        full = urljoin(base_url, href)
        out.append(full)
    return text, out, title


def domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def iter_sitemap(seed: str, cap: int | None = None):
    # încearcă sitemap la /sitemap.xml
    root = urlparse(seed)
    base = f"{root.scheme}://{root.netloc}"
    guesses = [
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
        f"{base}/sitemap-index.xml",
    ]
    seen = set()
    out = []
    for sm in guesses:
        try:
            r = SESSION.get(sm, timeout=15)
            if r.status_code == 200 and "<urlset" in r.text or "<sitemapindex" in r.text:
                seen.add(sm)
                # parsare simplă
                urls = re.findall(r"<loc>\s*([^<]+)\s*</loc>", r.text)
                for u in urls:
                    u = u.strip()
                    if not u:
                        continue
                    if u.endswith(".xml") and "sitemap" in u.lower():
                        # sitemap-uri subordonate — le mai încercăm rapid
                        try:
                            rr = SESSION.get(u, timeout=15)
                            if rr.status_code == 200:
                                for uu in re.findall(r"<loc>\s*([^<]+)\s*</loc>", rr.text):
                                    uu = uu.strip()
                                    if uu and uu not in out:
                                        out.append(uu)
                                        if cap and len(out) >= cap:
                                            return out
                        except Exception:
                            pass
                    else:
                        if u not in out:
                            out.append(u)
                            if cap and len(out) >= cap:
                                return out
        except Exception:
            continue
    return out


def upsert_mongo(col, doc: dict):
    col.update_one({"url": doc["url"]}, {"$set": doc}, upsert=True)



def _is_sitemap(url: str) -> bool:
    u = url.lower()
    return u.endswith('.xml') or u.endswith('.xml.gz') or 'sitemap' in u

def _expand_sitemaps(session, sitemap_urls, headers=None, timeout=20):
    out = []
    for su in sitemap_urls:
        try:
            r = session.get(su, headers=headers or {}, timeout=timeout)
            ct = (r.headers.get('content-type') or '').lower()
            if ('xml' in ct) or _is_sitemap(su):
                # parsează <loc> ... </loc>
                locs = _re.findall(r'<loc>(.*?)</loc>', r.text, flags=_re.I|_re.S)
                out.extend([x.strip() for x in locs if x.strip()])
        except Exception:
            pass
    # Filtrează tot ce e clar sitemap, păstrăm doar candidate de conținut
    return [u for u in out if not _is_sitemap(u)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seed", type=str, help="URL-ul inițial (site root)")
    ap.add_argument("--include_subdomains", action="store_true", help="Permite subdomenii")
    ap.add_argument("--max_pages", type=int, default=1000)
    ap.add_argument("--per_batch", type=int, default=50)
    ap.add_argument("--crawl_delay", type=float, default=0.4)
    args = ap.parse_args()

    seed = normalize_url(args.seed)
    root_dom = domain(seed)
    print(f"[seed] {seed}  domain={root_dom}")

    # sitemap (cap la max_pages ca plan inițial)
    urls = iter_sitemap(seed, cap=args.max_pages) or []
    if urls:
        print(f"[sitemap] găsite: {len(urls)} → plan…")
    else:
        print("[sitemap] nimic găsit; continui de la seed")
        urls = [seed]

    # filtre inițiale + normalizare
    plan = []
    for u in urls:
        u = normalize_url(u)
        if not same_site(u, root_dom, args.include_subdomains):
            continue
        if is_binary_url(u) or looks_noisy(u):
            continue
        plan.append(u)

    # conexiuni
    mc = MongoClient(MONGO_URL)
    mcol = mc[DB_NAME][COLL_NAME]
    qv = QdrantVectorizer()
    qv.ensure_collection()

    processed = set()
    total = 0
    batch = 0
    t0 = time.time()

    while plan and total < args.max_pages:
        chunk = []
        while plan and len(chunk) < args.per_batch and total + len(chunk) < args.max_pages:
            u = plan.pop(0)
            if u in processed:
                continue
            chunk.append(u)

        if not chunk:
            break

        batch += 1
        print(f"[batch {batch}] {len(chunk)} pagini")
        for u in chunk:
            processed.add(u)

            if is_binary_url(u) or looks_noisy(u):
                print(f"[skip] noisy/binary {u}")
                continue

            html, final = fetch(u)
            final = normalize_url(final or u)

            if not html:
                print(f"[skip] no content: {u}")
                time.sleep(args.crawl_delay)
                continue

            # extrage text/outlinks/titlu
            text, outlinks, title = extract_text_and_links(html, final)
            if not text or len(text.split()) < 50:
                # prea puțin conținut util -> salt (dar adaug outlinks pentru explorare)
                for o in outlinks:
                    o = normalize_url(o)
                    if same_site(o, root_dom, args.include_subdomains) and not is_binary_url(o) and not looks_noisy(o):
                        plan.append(o)
                print(f"[skip] low-content {final}")
                time.sleep(args.crawl_delay)
                continue

            doc = {
                "url": final,
                "domain": domain(final),
                "title": title or domain(final),
                "content": text,
                "word_count": len(text.split()),
                "fetched_at": datetime.datetime.now(timezone.utc).isoformat(),
            }
            upsert_mongo(mcol, doc)

            # vectorizare (rezistent la OOM — lăsăm vector [0]*dim dacă strict + serviciul nu răspunde)
            vec = qv.vectorize_content(doc) or [0.0] * qv.embedder.dimension
            try:
                qv.store_embedding(None, vec, {"url": doc["url"], "title": doc["title"], "domain": doc["domain"]})
                print(f"[ok] {final} (len={len(text)}, out={len(outlinks)})")
            except Exception as e:
                print(f"[warn] qdrant upsert: {e}")

            # extinde planul cu outlinks interne
            for o in outlinks:
                o = normalize_url(o)
                if not same_site(o, root_dom, args.include_subdomains):
                    continue
                if is_binary_url(o) or looks_noisy(o):
                    continue
                if o not in processed:
                    plan.append(o)

            total += 1
            time.sleep(args.crawl_delay)

    dt = time.time() - t0
    print(f"[done] pagini procesate: {total} în {dt:.1f}s")


if __name__ == "__main__":
    main()
