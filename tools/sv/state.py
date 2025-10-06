import os, re
from urllib.parse import urlsplit

def norm_domain(u: str) -> str:
    try:
        d = urlsplit(u).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except:
        return ""

def dedup(seq):
    seen=set(); out=[]
    for x in seq:
        if x in seen: continue
        seen.add(x); out.append(x)
    return out

def get_cfg():
    return {
        "per_site_pages": int(os.getenv("PER_SITE_PAGES","6")),
        "max_sites":      int(os.getenv("MAX_SITES","30")),
        "max_per_domain": int(os.getenv("MAX_PER_DOMAIN","5")),
        "crawl_delay":    float(os.getenv("CRAWL_DELAY","0.5")),
        "include_tlds":   set((os.getenv("INCLUDE_TLDS","org,gov,edu,int").lower()).split(",")),
        "include_pattern": os.getenv("INCLUDE_PATTERN", r".*"),
        "exclude_patterns": os.getenv("EXCLUDE_PATTERNS",
            r"(gardening|irrigation|sprinkler(world|s)|home\s?depot|orbitonline|rainbird|retail|shop|store)"),
        "sup_log":        bool(int(os.getenv("SUP_LOG","0"))),
        "graph_steps":    int(os.getenv("MAX_GRAPH_STEPS","40")),
        "recursion_limit":int(os.getenv("GRAPH_RECURSION_LIMIT","120")),
    }

def has_allowed_tld(domain: str, include_tlds) -> bool:
    if not domain: return False
    tld = domain.split(".")[-1]
    return (tld in include_tlds) if include_tlds else True

def compile_filters(cfg):
    return re.compile(cfg["include_pattern"], re.I), re.compile(cfg["exclude_patterns"], re.I)
