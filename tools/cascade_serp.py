import os, argparse, urllib.parse, requests, time
from datetime import datetime, timedelta, timezone
from orchestrator.orchestrator_loop import Orchestrator

# -------------------- helpers --------------------

def norm_domain(u: str) -> str:
    try:
        d = urllib.parse.urlsplit(u).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return ""

def pick_url(item):
    """
    Extrage URL din structuri Brave / SerpAPI.
    """
    # Brave: web.results[i].url
    if "url" in item and isinstance(item["url"], str) and item["url"].startswith(("http://", "https://")):
        return item["url"]

    # SerpAPI: organic_results[].link etc.
    for k in ("link", "formattedUrl", "displayed_link", "displayLink"):
        v = item.get(k)
        if isinstance(v, str) and v.startswith(("http://", "https://")):
            return v
    return None

# -------------------- optional Mongo cache --------------------
# SERP_CACHE=1 (default) | 0  ;  SERP_CACHE_TTL (sec, default 30 zile)
_SERP_CACHE_ON = os.getenv("SERP_CACHE", "1") != "0"
_SERP_CACHE_TTL = int(os.getenv("SERP_CACHE_TTL", 30 * 24 * 3600))
_serp_col = None
if _SERP_CACHE_ON:
    try:
        from pymongo import MongoClient, ASCENDING
        _mc = MongoClient(os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017"))
        _serp_col = _mc["ai_agents_db"]["serp_cache"]
        _serp_col.create_index([("key", ASCENDING)], unique=True)
        _serp_col.create_index("expires_at", expireAfterSeconds=0)
    except Exception:
        _serp_col = None  # continuă fără cache dacă nu e Mongo

def _cache_key(provider: str, q: str, count: int) -> str:
    return f"{provider}:{count}:{q.strip().lower()}"

def _cache_get(provider: str, q: str, count: int):
    # IMPORTANT: Collection NU suportă truthiness → comparăm explicit cu None
    if _serp_col is None:
        return None
    try:
        doc = _serp_col.find_one({"key": _cache_key(provider, q, count)}, {"_id": 0, "urls": 1, "expires_at": 1})
        if doc and doc.get("expires_at") and doc["expires_at"] > datetime.now(timezone.utc):
            return doc.get("urls") or None
    except Exception:
        return None
    return None

def _cache_put(provider: str, q: str, count: int, urls):
    if _serp_col is None:
        return
    try:
        _serp_col.update_one(
            {"key": _cache_key(provider, q, count)},
            {"$set": {"urls": list(urls) if urls else [], "expires_at": datetime.now(timezone.utc) + timedelta(seconds=_SERP_CACHE_TTL)}},
            upsert=True,
        )
    except Exception:
        pass

# -------------------- SERP providers --------------------

def _search_brave(q, num=10):
    """
    Brave Search API (primar).
    Necesită: export BRAVE_API_KEY=...
    """
    key = os.getenv("BRAVE_API_KEY")
    if not key:
        raise RuntimeError("BRAVE_API_KEY lipsă")
    cached = _cache_get("brave", q, num)
    if cached is not None:
        return cached

    url = "https://api.search.brave.com/res/v1/web/search"
    r = requests.get(
        url,
        headers={"X-Subscription-Token": key},
        params={"q": q, "count": num, "safesearch": "off"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    items = (data.get("web", {}) or {}).get("results", []) or []
    urls = []
    for it in items[:num]:
        u = pick_url(it) or it.get("url")
        if u and u.startswith(("http://", "https://")):
            urls.append(u)
    _cache_put("brave", q, num, urls)
    return urls

def _search_serpapi(q, num=10):
    """
    SerpAPI (fallback).
    Necesită: export SERPAPI_KEY=...
    """
    key = os.getenv("SERPAPI_KEY")
    if not key:
        raise RuntimeError("SERPAPI_KEY lipsă")
    cached = _cache_get("serpapi", q, num)
    if cached is not None:
        return cached

    url = "https://serpapi.com/search.json"
    r = requests.get(url, params={"engine": "google", "q": q, "api_key": key, "num": num}, timeout=30)
    r.raise_for_status()
    j = r.json()
    urls = []
    for block in ("organic_results", "news_results", "top_stories"):
        for it in j.get(block, []) or []:
            u = pick_url(it)
            if u:
                urls.append(u)
    urls = urls[:num]
    _cache_put("serpapi", q, num, urls)
    return urls

def serp_search(query: str, count: int = 10, provider_order: str | None = None):
    """
    Fallback automat: Brave → SerpAPI.
    Override cu --provider_order sau SERP_PROVIDER (ex: "brave,serpapi").
    """
    order_env = provider_order or os.getenv("SERP_PROVIDER") or "brave,serpapi"
    order = [p.strip().lower() for p in order_env.split(",") if p.strip()]
    last_err = None
    for prov in order:
        try:
            if prov == "brave":
                urls = _search_brave(query, count)
            elif prov == "serpapi":
                urls = _search_serpapi(query, count)
            else:
                continue
            if urls:
                return urls
        except Exception as e:
            last_err = e
            # treci la următorul provider pentru erori de auth/rate/temporare
            sc = getattr(getattr(e, "response", None), "status_code", 0)
            if sc in (401, 403, 429, 500, 502, 503, 504) or isinstance(e, requests.RequestException):
                continue
            break
    raise RuntimeError(f"Eșec pe toți providerii SERP: {last_err}")

# -------------------- main flow --------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seed", help="Seed URL (ex: https://www.nfpa.org/codes-and-standards)")
    ap.add_argument(
        "--queries",
        default="NFPA 13,sprinkler systems,firestopping,passive fire protection,NFPA standards,UL FM approvals",
        help="Interogări separate prin virgulă",
    )
    ap.add_argument("--per_site_pages", type=int, default=8, help="câte pagini per site nou")
    ap.add_argument("--max_sites", type=int, default=10, help="numărul maxim de site-uri noi")
    ap.add_argument("--crawl_delay", type=float, default=0.5)
    ap.add_argument("--provider_order", default=None, help='ex: "brave,serpapi" (altfel ia din SERP_PROVIDER)')
    args = ap.parse_args()

    orch = Orchestrator(crawl_delay=args.crawl_delay)

    print(f"[seed] crawl {args.seed}")
    orch.run(args.seed, max_pages=args.per_site_pages)

    seen = set([norm_domain(args.seed)])
    queue = []

    for q in [x.strip() for x in args.queries.split(",") if x.strip()]:
        print(f"[serp] {q}")
        try:
            urls = serp_search(q, count=10, provider_order=args.provider_order)
        except Exception as e:
            print(f"[serp error] {e}")
            continue

        for u in urls:
            d = norm_domain(u)
            if not d or d in seen:
                continue
            seen.add(d)
            queue.append((d, u))
        if len(queue) >= args.max_sites:
            break

    print(f"[queue] {len(queue)} site-uri noi")
    for i, (d, u) in enumerate(queue[: args.max_sites], 1):
        print(f"[{i}/{min(args.max_sites, len(queue))}] crawl {d} → {u}")
        try:
            orch.run(u, max_pages=args.per_site_pages)
        except Exception as e:
            print(f"[crawl error] {d}: {e}")
        time.sleep(0.2)

if __name__ == "__main__":
    main()
	

