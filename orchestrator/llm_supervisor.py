import os, re, json, requests
from collections import Counter
from urllib.parse import urlsplit
from pymongo import MongoClient

_DB = MongoClient(os.getenv("MONGO_URL","mongodb://127.0.0.1:27017"))["ai_agents_db"]
_PAGES = _DB["site_content"]

def _domain(u:str)->str:
    try:
        d = urlsplit(u).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return ""

def _keywords_for_domain(dom:str, top=20):
    texts=[]
    for d in _PAGES.find({"domain":{"$regex":rf"(^|\.){re.escape(dom)}$"}},{"title":1,"content":1}).limit(200):
        if d.get("title"): texts.append(d["title"])
        if d.get("content"): texts.append(d["content"][:1500])
    bag = re.findall(r"[a-zA-Z][a-zA-Z\-\./]{2,}", " ".join(texts))
    stop = set(("the and for with from that this are was were into your our you www http https html jpg png pdf com org gov".split()))
    bag = [w.lower() for w in bag if w.lower() not in stop]
    return [w for w,_ in Counter(bag).most_common(top)]

def _call_openai(prompt:str):
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    base = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL") or "https://api.openai.com"
    model = os.getenv("LLM_MODEL","gpt-4o-mini")
    if not api_key: return None
    try:
        r = requests.post(base.rstrip("/")+"/v1/chat/completions", timeout=60,
            headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
            json={"model":model,"temperature":0.2,
                  "messages":[
                      {"role":"system","content":"You are a web research planner. Reply with compact JSON only."},
                      {"role":"user","content":prompt}
                  ]})
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
        return json.loads(txt)
    except Exception:
        return None

def plan_next_actions(seed_url:str):
    dom = _domain(seed_url)
    kws = _keywords_for_domain(dom, top=30)
    fallback = {
        "queries":[
            f"{dom} regulations", "NFPA 13", "fire sprinkler system requirements",
            "firestopping requirements", "UL standards fire", "FM Approvals fire protection",
            "IBC IFC fire protection chapter", "inspection testing maintenance NFPA 25"
        ],
        "include_patterns": r"(fire|sprinkler|nfpa|firestop|ul|fm|code|standard|inspection|ibc|ifc)",
        "exclude_patterns": r"(irrigation|lawn|garden|home\s?depot|orbitonline|rainbird|sprinklerworld)",
        "max_per_domain": 6
    }
    prompt = f"""
Seed domain: {dom}
Top keywords seen: {', '.join(kws[:20])}

Task: Propose a minimal JSON plan with fields:
- queries: 6–10 web search queries focused on fire protection / codes / standards / authoritative orgs in the *same industry*, not irrigation/lawn.
- include_patterns: a single regex that *keeps* industry-relevant URLs.
- exclude_patterns: a single regex that *filters out* irrelevant (lawn/irrigation/ecommerce) URLs.
- max_per_domain: small integer (4–8).

Return JSON only.
"""
    plan = _call_openai(prompt)
    return plan or fallback
