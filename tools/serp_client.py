# tools/serp_client.py
from __future__ import annotations
import os, json, time
import requests
from typing import List, Dict, Any

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

class SerpError(RuntimeError):
    pass

# ---- key loader (ENV sau fișier) ----
def _load_brave_key() -> str:
    k = (os.getenv("BRAVE_API_KEY") or "").strip()
    if k:
        return k
    for p in (".secrets/brave.key",
              os.path.expanduser("~/.config/ai_agents/brave.key")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                k = f.read().strip()
                if k:
                    os.environ["BRAVE_API_KEY"] = k  # util pt. sub-procese
                    return k
        except FileNotFoundError:
            pass
    return ""

BRAVE_API_KEY   = _load_brave_key()
BRAVE_UI_LANG   = (os.getenv("BRAVE_UI_LANG") or "en-US").strip()
BRAVE_COUNTRY   = (os.getenv("BRAVE_COUNTRY") or "us").strip().lower()
BRAVE_SAFESEARCH= (os.getenv("BRAVE_SAFESEARCH") or "moderate").strip().lower()  # off|moderate|strict

def _get_with_retries(url: str, params: dict, headers: dict, timeout=30, tries=2):
    last = None
    for _ in range(tries):
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r
        last = r
        time.sleep(0.35)
    txt = (last.text or "")[:500] if last is not None else ""
    raise SerpError(f"Brave HTTP {last.status_code if last else '??'}: {txt}")

def _extract_urls(data: Dict[str, Any]) -> List[str]:
    urls: List[str] = []

    # 1) web.results
    web = (data or {}).get("web") or {}
    for item in web.get("results") or []:
        u = item.get("url")
        if isinstance(u, str) and u.startswith(("http://", "https://")):
            urls.append(u)

    # 2) mixed.main poate fi dict SAU listă
    mixed = (data or {}).get("mixed") or {}
    main = mixed.get("main")
    blocks = []
    if isinstance(main, list):
        blocks = main
    elif isinstance(main, dict):
        blocks = [main]
    elif main is None:
        blocks = []
    else:
        # tip necunoscut; ignorăm
        blocks = []

    for block in blocks:
        if not isinstance(block, dict):
            continue
        # uneori block e de forma {"type":"web","results":[...]}
        for item in block.get("results") or []:
            if not isinstance(item, dict):
                continue
            u = item.get("url")
            if isinstance(u, str) and u.startswith(("http://", "https://")):
                urls.append(u)

    # dedup păstrând ordinea
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def _brave_search(query: str, count: int = 10) -> list[str]:
    if not BRAVE_API_KEY:
        raise SerpError("BRAVE_API_KEY lipsește (ENV sau .secrets/brave.key).")

    q = (query or "").strip()
    if not q:
        return []

    # Brave acceptă 1..20
    count = max(1, min(int(count or 10), 20))

    params = {
        "q": q,
        "count": count,
        "ui_lang": BRAVE_UI_LANG,     # ex. en-US
        "country": BRAVE_COUNTRY,     # ex. us
        "safesearch": BRAVE_SAFESEARCH,
    }
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }

    r = _get_with_retries(BRAVE_ENDPOINT, params=params, headers=headers, timeout=30, tries=2)

    try:
        data = r.json()
    except Exception as e:
        raise SerpError(f"Brave JSON parse error: {e}") from e

    urls = _extract_urls(data)
    return urls[:count]

def search(query: str, count: int = 10) -> list[str]:
    return _brave_search(query, count=count)

# ---- CLI: python -m tools.serp_client "q" 5 [--debug]
if __name__ == "__main__":
    import sys
    dbg = False
    args = [a for a in sys.argv[1:] if a != "--debug"]
    dbg = (len(sys.argv) != len(args))
    q = args[0] if args else "site:nfpa.org codes and standards"
    c = int(args[1]) if len(args) > 1 else 5
    if dbg:
        print(json.dumps({
            "ui_lang": BRAVE_UI_LANG, "country": BRAVE_COUNTRY, "safesearch": BRAVE_SAFESEARCH,
            "key_present": bool(BRAVE_API_KEY), "key_len": len(BRAVE_API_KEY),
            "endpoint": BRAVE_ENDPOINT
        }, indent=2))
    print(json.dumps(search(q, c), indent=2))
