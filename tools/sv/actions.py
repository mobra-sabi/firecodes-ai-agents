import os
from typing import Dict, Any, List

from tools.serp_client import search as serp_search
from orchestrator.orchestrator_loop import Orchestrator

from .state import norm_domain, dedup

_orch = Orchestrator(crawl_delay=float(os.getenv("CRAWL_DELAY","0.5")))

def filter_urls(urls: List[str], inc_rx, exc_rx,
                seen_urls: set, max_sites: int, max_per_domain: int,
                include_tlds) -> List[str]:
    picked, per_dom = [], {}
    for u in urls or []:
        if not isinstance(u, str) or not u.startswith(("http://","https://")): continue
        if u in seen_urls: continue
        if exc_rx.search(u): continue
        if not inc_rx.search(u): continue
        d = norm_domain(u)
        if not d: continue
        tld = d.split(".")[-1]
        if include_tlds and tld not in include_tlds: continue
        if per_dom.get(d,0) >= max_per_domain: continue
        picked.append(u)
        per_dom[d] = per_dom.get(d,0) + 1
        if len(picked) >= max_sites: break
    return picked

def do_search(args: Dict[str,Any], cfg, inc_rx, exc_rx, visited: List[str]):
    q = (args.get("query") or "").strip()
    cnt = int(args.get("count", 10))
    if not q:
        return {"ok": False, "error": "empty query"}
    urls = []
    errs = []
    try:
        urls = serp_search(q, count=cnt) or []
    except Exception as e:
        errs.append(str(e))

    if not urls:
        return {"ok": False, "error": "serp: " + " | ".join(errs) if errs else "no urls"}

    res_urls = filter_urls(urls, inc_rx, exc_rx, set(visited),
                           cfg["max_sites"], cfg["max_per_domain"], cfg["include_tlds"])
    return {"ok": True, "urls": res_urls}

def do_crawl(args: Dict[str,Any], cfg):
    url = (args.get("url") or "").strip()
    if not url.startswith(("http://","https://")):
        return {"ok": False, "error": "invalid url"}
    try:
        _orch.run(url, max_pages=cfg["per_site_pages"])
        return {"ok": True, "crawled": url, "max_pages": cfg["per_site_pages"]}
    except Exception as e:
        return {"ok": False, "error": repr(e)}
