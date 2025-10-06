# tools/auto_industry_crawl.py
import os, re, time, gzip, io, json, argparse, urllib.parse, requests
from collections import OrderedDict
from typing import List, Dict, Iterable, Set
from urllib.parse import urlparse, urljoin
from orchestrator.orchestrator_loop import Orchestrator

# --- seeds „de încredere” pentru construcții / siguranță la incendiu ---
CURATED_DOMAINS = [
    "nfpa.org", "iccsafe.org", "osha.gov", "nist.gov", "fema.gov",
    "ul.com", "fmglobal.com", "sfpe.org", "fm.com",
]

# --- helpers ---
def domain(u: str) -> str:
    try:
        return urlparse(u).netloc.lower().split(":")[0]
    except Exception:
        return ""

def normalize(u: str) -> str:
    try:
        s = urllib.parse.urlsplit(u)._replace(fragment="")
        q = urllib.parse.parse_qsl(s.query, keep_blank_values=True)
        q = [(k, v) for (k, v) in q if k.lower() not in {
            "utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","fbclid"
        }]
        return urllib.parse.urlunsplit(s._replace(query=urllib.parse.urlencode(q, doseq=True)))
    except Exception:
        return u

def uniq_keep_order(xs: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for x in xs:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

# --- SERP providers ---
def serp_search(queries: List[str], per_query: int = 10) -> List[str]:
    prov = (os.getenv("SERP_PROVIDER") or "").lower().strip()
    urls: List[str] = []
    if prov == "serpapi" and os.getenv("SERPAPI_KEY"):
        key = os.getenv("SERPAPI_KEY")
        for q in queries:
            try:
                r = requests.get(
                    "https://serpapi.com/search.json",
                    params={"engine": "google", "q": q, "num": per_query, "api_key": key},
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                for it in (data.get("organic_results") or []):
                    link = it.get("link")
                    if link:
                        urls.append(link)
            except Exception:
                continue
    elif prov == "bing" and os.getenv("BING_V7_SUBSCRIPTION_KEY"):
        key = os.getenv("BING_V7_SUBSCRIPTION_KEY")
        headers = {"Ocp-Apim-Subscription-Key": key}
        for q in queries:
            try:
                r = requests.get(
                    "https://api.bing.microsoft.com/v7.0/search",
                    headers=headers, params={"q": q, "count": per_query}, timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                for it in (data.get("webPages", {}).get("value") or []):
                    link = it.get("url")
                    if link:
                        urls.append(link)
            except Exception:
                continue
    # fără chei -> 0 rezultate din SERP (rămân curated + crawl ulterior)
    return urls

# --- robots.txt sitemap discovery ---
def robots_sitemaps(base: str, headers=None, timeout=15) -> List[str]:
    d = domain(base)
    if not d: return []
    scheme = urlparse(base).scheme or "https"
    robots_url = f"{scheme}://{d}/robots.txt"
    try:
        r = requests.get(robots_url, headers=headers or {}, timeout=timeout)
        if r.status_code != 200:
            return []
        out = []
        for line in r.text.splitlines():
            line = line.strip()
            if not line.lower().startswith("sitemap:"):
                continue
            url = line.split(":", 1)[1].strip()
            if url:
                out.append(url)
        return out
    except Exception:
        return []

def guess_sitemaps(base: str) -> List[str]:
    d = domain(base)
    if not d: return []
    scheme = urlparse(base).scheme or "https"
    return [f"{scheme}://{d}/sitemap.xml"]

def is_sitemap(url: str) -> bool:
    u = url.lower()
    return u.endswith(".xml") or u.endswith(".xml.gz") or "sitemap" in u

def expand_sitemaps(smap_urls: List[str], headers=None, timeout=25) -> List[str]:
    out: List[str] = []
    sess = requests.Session()
    for su in uniq_keep_order(smap_urls):
        try:
            r = sess.get(su, headers=headers or {}, timeout=timeout)
            if r.status_code != 200:
                continue
            content = r.content
            if su.lower().endswith(".gz"):
                try:
                    content = gzip.GzipFile(fileobj=io.BytesIO(content)).read()
                except Exception:
                    pass
            text = content.decode("utf-8", errors="ignore")
            # sitemap index sau urlset: extrage <loc>…</loc>
            locs = re.findall(r"<loc>(.*?)</loc>", text, flags=re.I | re.S)
            for loc in locs:
                loc = loc.strip()
                if not loc:
                    continue
                if is_sitemap(loc):
                    # 1 nivel de recursie light
                    out.extend(expand_sitemaps([loc], headers=headers, timeout=timeout))
                else:
                    out.append(loc)
        except Exception:
            continue
    return uniq_keep_order(out)

def filter_urls_for_domain(urls: Iterable[str], dom: str, include_subdomains: bool) -> List[str]:
    dom = dom.lower()
    out = []
    for u in urls:
        du = domain(u)
        if not du: continue
        if include_subdomains:
            ok = du == dom or du.endswith("." + dom)
        else:
            ok = du == dom
        if ok:
            out.append(normalize(u))
    return uniq_keep_order(out)

# --- main flow ---
def discover_domains(theme: str, extra_queries: List[str], max_domains: int) -> List[str]:
    queries = extra_queries or []
    if theme:
        base = theme.strip()
        queries = uniq_keep_order(queries + [
            f"{base} standards", f"{base} codes", f"{base} fire protection",
            "NFPA 13", "sprinkler systems", "firestopping", "passive fire protection",
            "UL standards", "FM Approvals", "ICC codes", "OSHA 1926 fire"
        ])
    urls = []
    # 1) curated
    urls.extend([f"https://{d}/" for d in CURATED_DOMAINS])
    # 2) serp (opțional, dacă ai chei)
    urls.extend(serp_search(queries, per_query=10))
    # reduce la domenii unice
    doms = OrderedDict()
    for u in urls:
        d = domain(u)
        if not d: continue
        # normalizări simple (www. → root)
        d = re.sub(r"^www\.", "", d)
        doms[d] = True
        if len(doms) >= max_domains:
            break
    return list(doms.keys())

def pick_urls_for_domain(dom: str, include_subdomains: bool, max_pages: int, headers=None) -> List[str]:
    # 1) încearcă robots.txt → Sitemap:
    s1 = robots_sitemaps(f"https://{dom}/", headers=headers)
    # 2) fallback sitemap.xml
    s2 = guess_sitemaps(f"https://{dom}/")
    sitems = uniq_keep_order(s1 + s2)
    expanded = expand_sitemaps(sitems, headers=headers)
    if not expanded:
        # dacă nu avem sitemap, măcar ia home
        expanded = [f"https://{dom}/"]
    urls = filter_urls_for_domain(expanded, dom, include_subdomains=include_subdomains)
    # heuristici: ignoră login/cart/search
    urls = [u for u in urls if not re.search(r"/(login|signin|cart|checkout|search|tag|category)/?", u, flags=re.I)]
    return urls[:max_pages]

def run_crawl(theme: str, queries_csv: str, include_subdomains: bool, max_domains: int,
              per_domain_pages: int, per_batch: int, crawl_delay: float):
    print(f"[auto] theme={theme!r} max_domains={max_domains} per_domain_pages={per_domain_pages}")
    extra_queries = [q.strip() for q in (queries_csv or "").split(",") if q.strip()]
    # HEADERS din orchestrator, dacă există
    try:
        from orchestrator.orchestrator_loop import HEADERS as ORCH_HEADERS
    except Exception:
        ORCH_HEADERS = {}
    # descoperă domenii
    doms = discover_domains(theme, extra_queries, max_domains=max_domains)
    print("[auto] candidate domains:", ", ".join(doms))
    o = Orchestrator(crawl_delay=crawl_delay)

    processed = 0
    for d in doms:
        try:
            urls = pick_urls_for_domain(d, include_subdomains, per_domain_pages, headers=ORCH_HEADERS)
            if not urls:
                print(f"[{d}] no urls")
                continue
            print(f"[{d}] plan {len(urls)} urls")
            # rulează în mini-loturi
            batch = []
            for u in urls:
                batch.append(u)
                if len(batch) >= per_batch:
                    for uu in batch:
                        try:
                            o.run(uu, max_pages=1)
                            processed += 1
                        except Exception as e:
                            print("[err]", uu, e)
                    batch = []
                    time.sleep(crawl_delay)
            # restul
            for uu in batch:
                try:
                    o.run(uu, max_pages=1)
                    processed += 1
                except Exception as e:
                    print("[err]", uu, e)
        except Exception as e:
            print(f"[{d}] error:", e)
    print("[auto] processed pages:", processed)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("theme", type=str, help="ex: 'construction fire protection'")
    ap.add_argument("--queries", type=str, default="", help="extra queries, CSV")
    ap.add_argument("--include_subdomains", action="store_true")
    ap.add_argument("--max_domains", type=int, default=20)
    ap.add_argument("--per_domain_pages", type=int, default=150)
    ap.add_argument("--per_batch", type=int, default=25)
    ap.add_argument("--crawl_delay", type=float, default=0.4)
    args = ap.parse_args()
    run_crawl(
        theme=args.theme,
        queries_csv=args.queries,
        include_subdomains=args.include_subdomains,
        max_domains=args.max_domains,
        per_domain_pages=args.per_domain_pages,
        per_batch=args.per_batch,
        crawl_delay=args.crawl_delay,
    )

if __name__ == "__main__":
    main()
