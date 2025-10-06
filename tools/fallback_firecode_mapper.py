import os, re, sys, time, json, subprocess, collections
from urllib.parse import urljoin, urlparse

INCLUDE_DOMAINS = set((os.environ.get("INCLUDE_DOMAINS") or "iccsafe.org,codes.iccsafe.org").split(","))
INCLUDE_TLDS    = set((os.environ.get("INCLUDE_TLDS") or "org").split(","))
PER_SITE_PAGES  = int(os.environ.get("PER_SITE_PAGES", "12"))
MAX_PER_DOMAIN  = int(os.environ.get("MAX_PER_DOMAIN", "12"))
CRAWL_DELAY     = float(os.environ.get("CRAWL_DELAY", "0.6"))
QUERY           = 'site:iccsafe.org code OR standard OR fire OR sprinkler'

def brave_search(query, n=12):
    # Folosește clientul tău existent (nu expunem cheia)
    try:
        out = subprocess.check_output(
            ["python", "-m", "tools.serp_client", query, str(n), "--debug"],
            stderr=subprocess.STDOUT, text=True
        )
        # Caut ultima listă JSON (CLI-ul tău tipărește un array pe o linie)
        m = re.search(r"\[\s*\"https?://.*\]\s*$", out, flags=re.M|re.S)
        if m:
            return json.loads(m.group(0))
    except subprocess.CalledProcessError as e:
        print("[FB] SERP ERR:", e.output.strip(), file=sys.stderr)
    return []

def http_get(url, timeout=15):
    # Fără dependențe — urllib.request implicit
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
    try:
        req = Request(url, headers={"User-Agent": "firecode-mapper/1.0"})
        with urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type","")
            if "text" not in ct and "html" not in ct:
                return ""
            return r.read(1_500_000).decode("utf-8","ignore")
    except Exception as e:
        return ""

def allowed(u):
    try:
        pu = urlparse(u)
        host = (pu.netloc or "").lower()
        if not host: return False
        # tld filter
        if "." in host:
            tld = host.rsplit(".",1)[-1]
            if INCLUDE_TLDS and tld not in INCLUDE_TLDS: return False
        # domain allowlist
        if INCLUDE_DOMAINS:
            return any(host==d or host.endswith("."+d) for d in INCLUDE_DOMAINS)
        return True
    except:
        return False

def extract_links(base, html):
    urls = set()
    # href="...", href='...'
    for m in re.finditer(r'href\s*=\s*["\']([^"\']+)["\']', html, flags=re.I):
        href = m.group(1)
        if href.startswith("#"): continue
        absu = urljoin(base, href)
        urls.add(absu)
    return urls

def crawl(seeds):
    visited = []
    per_domain = collections.Counter()
    q = []
    # normalize & seed
    for s in seeds:
        if allowed(s): q.append(s)
    seen = set()
    while q and sum(per_domain.values()) < (len(INCLUDE_DOMAINS) or 2)*PER_SITE_PAGES:
        url = q.pop(0)
        if url in seen: continue
        seen.add(url)
        if not allowed(url): continue
        dom = urlparse(url).netloc.lower()
        if per_domain[dom] >= MAX_PER_DOMAIN: continue

        html = http_get(url)
        if not html: 
            continue
        visited.append(url)
        per_domain[dom] += 1
        # enque in-domain links up to a soft cap
        for link in extract_links(url, html):
            if allowed(link) and link not in seen:
                q.append(link)
        time.sleep(CRAWL_DELAY)
        # stop when per-domain page goal is near
        if all(per_domain[d] >= min(PER_SITE_PAGES, MAX_PER_DOMAIN) for d in per_domain):
            # continue a bit to gather for small domains
            pass
    return visited, per_domain

def main():
    TS = time.strftime("%Y%m%d_%H%M%S")
    logdir = os.path.join("logs")
    os.makedirs(logdir, exist_ok=True)

    print("[FB] Searching seeds with Brave…", file=sys.stderr)
    seeds = brave_search(QUERY, n=max(PER_SITE_PAGES*2, 12))
    # Asigurăm câteva seed-uri de pe codes.iccsafe.org dacă apar
    if not seeds:
        seeds = ["https://codes.iccsafe.org/","https://www.iccsafe.org/"]
    print(f"[FB] {len(seeds)} seed(s)", file=sys.stderr)

    print("[FB] Crawling…", file=sys.stderr)
    visited, per_domain = crawl(seeds)

    # save artifacts
    visited_path = os.path.join(logdir, f"visited_fb_{TS}.txt")
    with open(visited_path, "w", encoding="utf-8") as f:
        for u in sorted(set(visited)):
            f.write(u+"\n")

    report = {
        "domains": [{"domain": d, "pages": int(n)} for d,n in per_domain.most_common()],
        "visited_count": len(set(visited)),
        "seed_count": len(seeds),
        "include_domains": sorted(INCLUDE_DOMAINS),
        "include_tlds": sorted(INCLUDE_TLDS),
        "per_site_pages": PER_SITE_PAGES,
        "max_per_domain": MAX_PER_DOMAIN,
    }
    report_path = os.path.join(logdir, f"report_fb_{TS}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "ok": True,
        "visited_file": visited_path,
        "report_file": report_path,
        "summary": report
    }, ensure_ascii=False))
if __name__ == "__main__":
    main()
