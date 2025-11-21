import os, requests
from typing import List

def _serpapi_search(q: str, k: int) -> List[str]:
    key = os.getenv("SERPAPI_KEY")
    if not key:
        return []
    r = requests.get("https://serpapi.com/search.json", params={
        "engine":"google","q":q,"num":k,"api_key":key
    }, timeout=20)
    r.raise_for_status()
    data = r.json()
    urls = []
    for it in (data.get("organic_results") or [])[:k]:
        u = (it.get("link") or "").strip()
        if u.startswith("http"): urls.append(u)
    return urls

def _bing_search(q: str, k: int) -> List[str]:
    key = os.getenv("BING_V7_SUBSCRIPTION_KEY")
    if not key:
        return []
    r = requests.get("https://api.bing.microsoft.com/v7.0/search",
        params={"q": q, "count": k},
        headers={"Ocp-Apim-Subscription-Key": key}, timeout=20)
    r.raise_for_status()
    data = r.json()
    urls=[]
    for it in (data.get("webPages",{}).get("value") or [])[:k]:
        u = (it.get("url") or "").strip()
        if u.startswith("http"): urls.append(u)
    return urls

def search_serp(queries: List[str], k: int = 10) -> List[str]:
    prov = (os.getenv("SERP_PROVIDER") or "").lower()
    urls=[]
    for q in queries[:8]:
        if prov=="bing":
            urls += _bing_search(q, k)
        else:
            urls += _serpapi_search(q, k)
        # Brave (opțional)
        brave_key = os.getenv("BRAVE_API_KEY")
        if brave_key:
            try:
                r = requests.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": q, "count": k},
                    headers={"X-Subscription-Token": brave_key},
                    timeout=20,
                )
                if r.status_code == 200:
                    data = r.json()
                    for it in (data.get("web",{}).get("results") or [])[:k]:
                        u = (it.get("url") or "").strip()
                        if u.startswith("http"):
                            urls.append(u)
            except Exception:
                pass
    # dedup păstrând ordinea
    seen=set(); out=[]
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out[:k*len(queries)]
