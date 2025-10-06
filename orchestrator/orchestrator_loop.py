from __future__ import annotations
import os, time, uuid, math, re, hashlib
from urllib.parse import urlparse, urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
import requests
from pymongo import MongoClient, errors as mongo_errors

from orchestrator.frontier_manager import FrontierManager
from database.qdrant_vectorizer import QdrantVectorizer
from adapters.scraper_adapter import smart_fetch

try:
    from orchestrator.qwen_runner import propose_queries
except Exception:
    def propose_queries(industry_summary: str, gaps: list[str], lang: str="en") -> list[str]:
        # fallback dacă Qwen nu e configurat
        return ["fire protection association", "NFPA 13 suppliers", "passive fire protection", "firestopping standards"]

MONGODB_URI = os.getenv("MONGODB_URI","mongodb://127.0.0.1:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE","ai_agents_db")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION","site_content")
USER_AGENT = os.getenv("CRAWL_UA","Mozilla/5.0 (compatible; Orchestrator/1.0)")

def normalize_url(u: str) -> str:
    try:
        s = urlsplit(u)
        s = s._replace(fragment="")
        qs = [(k, v) for k, v in parse_qsl(s.query, keep_blank_values=True)
              if k.lower() not in {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","fbclid"}]
        q = urlencode(qs, doseq=True)
        path = s.path or "/"
        path = re.sub(r"/+", "/", path)
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        s = s._replace(query=q, path=path)
        return urlunsplit(s)
    except Exception:
        return u

def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b): return 0.0
    s = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    if na==0 or nb==0: return 0.0
    return s/(na*nb)

def discover_sitemap_links(seed_url: str, limit: int = 200) -> list[str]:
    d = domain(seed_url)
    base = f"{urlparse(seed_url).scheme}://{d}"
    robots_url = urljoin(base, "/robots.txt")
    sess = requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT})
    urls: list[str] = []
    try:
        r = sess.get(robots_url, timeout=10)
        if r.status_code == 200:
            smaps = re.findall(r"(?i)^sitemap:\s*(\S+)", r.text, flags=re.M)
            for sm in smaps[:5]:
                try:
                    sr = sess.get(sm, timeout=15)
                    if sr.status_code != 200: continue
                    locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", sr.text, flags=re.I)
                    for u in locs:
                        if domain(u) == d:
                            urls.append(normalize_url(u.strip()))
                        if len(urls) >= limit: break
                except Exception:
                    continue
                if len(urls) >= limit: break
    except Exception:
        pass
    seen, uniq = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); uniq.append(u)
    return uniq[:limit]

def text_hash(text: str) -> str:
    # hash stabil, după normalizare simplă a spațiilor
    norm = re.sub(r"\s+", " ", (text or "")).strip()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()

class Orchestrator:
    def __init__(self, crawl_delay: float = 0.8):
        self.fm = FrontierManager(crawl_delay=crawl_delay)
        self.qv = QdrantVectorizer()
        self.qv.ensure_collection()

        self.mc = MongoClient(MONGODB_URI)
        self.col = self.mc[MONGODB_DATABASE][MONGODB_COLLECTION]
        try:
            self.col.create_index([("url",1)], unique=True, name="uniq_url")
            self.col.create_index([("timestamp",-1)], name="ts_desc")
            self.col.create_index([("domain",1)], name="by_domain")
            self.col.create_index([("domain",1), ("text_hash",1)], unique=True, name="uniq_domain_text")
        except Exception:
            pass

    def upsert_doc(self, url: str, title: str, text: str, vec: list[float] | None):
        th = text_hash(text)
        dom = domain(url)
        # dacă exact același conținut există în domeniu, sari
        existing_same = self.col.find_one({"domain": dom, "text_hash": th}, {"url":1})
        if existing_same and existing_same.get("url") == url:
            print(f"[skip] unchanged {url}")
            return False
        # dacă URL-ul există, vezi dacă hash s-a schimbat
        existing_url = self.col.find_one({"url": url}, {"text_hash":1})
        if existing_url and existing_url.get("text_hash") == th:
            print(f"[skip] unchanged {url}")
            return False

        # embedd doar când e nou/schimbat
        if vec is None:
            vec = self.qv.vectorize_content({"content": text})

        doc = {
            "url": url,
            "domain": dom,
            "title": title,
            "content": text,
            "text_hash": th,
            "timestamp": int(time.time()),
        }
        self.col.update_one({"url": url}, {"$set": doc}, upsert=True)
        pid = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
        self.qv.store_embedding(pid, vec, {"url": url, "title": title, "domain": dom})
        return True

    def run(self, seed_url: str, max_pages: int = 50):
        seed_url = normalize_url(seed_url)
        seed_dom = domain(seed_url)
        self.fm.add(seed_url, priority=1.0, meta={"reason":"seed"})
        processed = 0
        seed_vec = self.qv.vectorize_content({"content": seed_url})

        while not self.fm.empty() and processed < max_pages:
            item = self.fm.pop()
            if not item: break
            url = item.url

            res = smart_fetch(url, USER_AGENT)
            if not res.get("ok"):
                print(f"[skip] no content: {url}")
                continue

            # 1) dacă am întreg site-ul
            site_pages = res.get("site_pages")
            if isinstance(site_pages, list) and site_pages:
                print(f"[site] pages={len(site_pages)} from {url}")
                for p in site_pages:
                    u = normalize_url(p.get("url") or seed_url)
                    t = p.get("title") or ""
                    text = p.get("text") or p.get("content") or ""
                    if not (u and text): continue
                    self.fm.mark_seen_url(u)
                    ok = self.upsert_doc(u, t, text, vec=None)
                    if ok: processed += 1
                    if processed >= max_pages: break
                outlinks = []
                for p in site_pages: outlinks += p.get("outlinks") or []
                res["outlinks"] = outlinks

            # 2) pagină unică
            final_url = normalize_url(res.get("url") or url)
            title = res.get("title") or ""
            text = res.get("text") or ""
            self.fm.mark_seen_url(final_url)
            if text.strip():
                ok = self.upsert_doc(final_url, title, text, vec=None)
                if ok: processed += 1
                print(f"[ok] {final_url} (len={len(text)}, out={len(res.get('outlinks') or [])})")

            # 3) outlink-uri interne
            outlinks = res.get("outlinks") or []
            if not outlinks:
                candidates = discover_sitemap_links(final_url)
                print(f"[sitemap] found={len(candidates)} for {seed_dom}")
                outlinks = candidates

            if outlinks:
                new_items = []
                for link in outlinks[:500]:
                    link = normalize_url(link)
                    d = domain(link)
                    same_domain = 1.0 if d == seed_dom else 0.3
                    authority = 1.0 if (link.endswith("/") or urlparse(link).path in ("","/")) else 0.6
                    sim = 0.8 if d == seed_dom else 0.4
                    prio = self.fm.score(sim, authority, same_domain)
                    new_items.append({"url": link, "priority": prio, "meta": {"src": final_url}})
                self.fm.add_many(new_items)

            # 4) SERP expansion (Qwen -> queries -> SERP)
            try:
                from adapters.search_providers import search_serp
                summary = (title + " " + text[:800]).strip()
                qs = propose_queries(summary, [], lang="en")
                serp_urls = search_serp(qs, k=10)
                ext_items = []
                for link in serp_urls:
                    link = normalize_url(link)
                    d = domain(link)
                    diversity = 1.0 if d != seed_dom else 0.3
                    authority = 0.8
                    sim = 0.5
                    prio = self.fm.score(sim, authority, diversity)
                    ext_items.append({"url": link, "priority": prio, "meta": {"src": final_url, "via":"serp"}})
                self.fm.add_many(ext_items)
            except Exception:
                pass

        return processed
