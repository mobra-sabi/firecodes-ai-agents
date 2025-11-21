# tools/supervisor_graph.py
import os, re, json, time, sys, datetime
from typing import Dict, Any, List
from urllib.parse import urlsplit

# === cheie OpenAI din fișier/env ===
try:
    from tools.llm_key_loader import ensure_openai_key
except Exception:
    def ensure_openai_key(): ...
ensure_openai_key()

# --- SERP + Orchestrator (existente la tine) ---
from tools.serp_client import search as serp_search
from orchestrator.orchestrator_loop import Orchestrator

# --- DB pt raport ---
from pymongo import MongoClient

# --- LangChain / LangGraph ---
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

LOG = bool(int(os.getenv("SUP_LOG","0")))
def log(*a):
    if LOG:
        print(*a, file=sys.stderr, flush=True)  # <-- pe STDERR, ca să nu strice JSON-ul de pe stdout

# ============== CONFIG ==============
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
LLM_MODEL       = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMP        = float(os.getenv("LLM_TEMPERATURE", "0.2"))

PER_SITE_PAGES  = int(os.getenv("PER_SITE_PAGES", "8"))
MAX_SITES       = int(os.getenv("MAX_SITES", "30"))
MAX_PER_DOMAIN  = int(os.getenv("MAX_PER_DOMAIN", "6"))
MIN_VISITS      = int(os.getenv("MIN_VISITS", "4"))  # minim crawl-uri înainte de report
CRAWL_DELAY     = float(os.getenv("CRAWL_DELAY", "0.5"))

INCLUDE_TLDS    = set((os.getenv("INCLUDE_TLDS","org,gov,edu,int").lower()).split(","))
INCLUDE_DOMAINS = set([d.strip().lower() for d in (os.getenv("INCLUDE_DOMAINS","").lower()).split(",") if d.strip()])
EXCLUDE_DOMAINS = set([d.strip().lower() for d in (os.getenv("EXCLUDE_DOMAINS","").lower()).split(",") if d.strip()])

EXCLUDE_PATTERNS= os.getenv("EXCLUDE_PATTERNS",
    r"(gardening|irrigation|sprinkler(world|s)|home\s?depot|orbitonline|rainbird|retail|shop|store)")
INCLUDE_PATTERN = os.getenv("INCLUDE_PATTERN", r".*")

MONGO_URL = os.getenv("MONGODB_URI","mongodb://127.0.0.1:27017")
DB_NAME   = os.getenv("MONGO_DB","ai_agents_db")

# ============== UTILS ==============
def norm_domain(u: str) -> str:
    try:
        d = urlsplit(u).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except:
        return ""

def has_allowed_tld(domain: str) -> bool:
    if not domain: return False
    tld = domain.split(".")[-1]
    return (tld in INCLUDE_TLDS) if INCLUDE_TLDS else True

def domain_allowed(domain: str) -> bool:
    d = (domain or "").lower()
    if not d: return False
    if EXCLUDE_DOMAINS and d in EXCLUDE_DOMAINS: return False
    if INCLUDE_DOMAINS and d not in INCLUDE_DOMAINS: return False
    return True

def filter_urls(urls: List[str], inc_rx, exc_rx,
                seen_urls: set, max_sites: int, max_per_domain: int) -> List[str]:
    picked, per_dom = [], {}
    for u in urls or []:
        if not isinstance(u, str) or not u.startswith(("http://","https://")): continue
        if u in seen_urls: continue
        if exc_rx.search(u): continue
        if not inc_rx.search(u): continue
        d = norm_domain(u)
        if not d or not has_allowed_tld(d): continue
        if not domain_allowed(d): continue
        if per_dom.get(d,0) >= max_per_domain: continue
        picked.append(u)
        per_dom[d] = per_dom.get(d,0) + 1
        if len(picked) >= max_sites: break
    return picked

def extract_first_url(text: str) -> str:
    m = re.search(r"https?://[^\s)>\]]+", text or "")
    return m.group(0) if m else ""

# ============== LLM (opțional) ==============
sys_prompt = """You are the autonomous Supervisor of a web mapping pipeline.
Reply ONLY JSON:
{"thought":"<short>","next_action":"search|crawl|report|stop","args":{...}}
- search: {"query":"...","count":10}
- crawl: {"url":"...","max_pages":6}
- report: {}
- stop: {}
Prefer .org/.gov/.edu/.int. Avoid gardening/irrigation/retail/ecommerce noise.
"""
llm_kwargs = {"model": LLM_MODEL, "temperature": LLM_TEMP}
if OPENAI_BASE_URL: llm_kwargs["base_url"] = OPENAI_BASE_URL
llm = ChatOpenAI(**llm_kwargs)  # îl păstrăm pentru extinderi viitoare

# ============== DB / REPORT ==============
mc = MongoClient(MONGO_URL)
db = mc[DB_NAME]
def quick_report(session_new_domains: List[str]) -> Dict[str,Any]:
    agents = db["site_agents"]
    total = agents.estimated_document_count()
    top = list(agents.find({}, {"_id":0,"domain":1,"pages":1}).sort("pages",-1).limit(12))
    return {"site_agents_total": total, "top_domains": top,
            "session_new_domains": sorted(set(session_new_domains or []))}

# ============== ORCHESTRATOR ==============
orch = Orchestrator(crawl_delay=CRAWL_DELAY)

# ============== STATE ==============
class S(dict): ...
def dedup(seq):
    seen=set(); out=[]
    for x in seq or []:
        if x in seen: continue
        seen.add(x); out.append(x)
    return out

# ============== NODES (faze deterministe) ==============
def plan_node(state: S) -> Dict[str,Any]:
    # o singură dată, apoi trecem în faza search
    return {"phase": "search", "last_plan": {"ok": True, "note": "entering search phase"}, "search_count": 0}

def search_node(state: S) -> Dict[str,Any]:
    inc_rx = re.compile(INCLUDE_PATTERN, re.I)
    exc_rx = re.compile(EXCLUDE_PATTERNS, re.I)

    search_count = state.get("search_count", 0) + 1

    if INCLUDE_DOMAINS:
        domq = " OR ".join([f"site:{d}" for d in INCLUDE_DOMAINS])
        base_q = f"({domq}) fire OR code OR standard OR sprinkler"
    else:
        seed = state.get("seed_url") or "https://www.iccsafe.org"
        d = norm_domain(seed) or "iccsafe.org"
        base_q = f"site:{d} code OR standard OR fire OR sprinkler"

    # Vary query based on search_count
    if search_count == 1:
        q = base_q
    elif search_count == 2:
        q = f"{base_q} OR NFPA OR IBC OR IFC"
    elif search_count == 3:
        q = f"{base_q} OR certification OR training OR inspection"
    else:
        q = f"{base_q} OR association OR organization OR institute"

    count = int(state.get("args",{}).get("count", 10))

    try:
        raw = serp_search(q, count=count) or []
        res_urls = filter_urls(
            raw,
            inc_rx, exc_rx,
            seen_urls=set(state.get("visited_urls",[])),
            max_sites=state.get("max_sites", MAX_SITES),
            max_per_domain=state.get("max_per_domain", MAX_PER_DOMAIN)
        )
        log(f"[SUP] SEARCH {search_count} ok ({len(res_urls)} urls) for: {q}")
    except Exception as e:
        log("[SUP] SEARCH error:", repr(e))
        return {"phase":"report","last_result":{"ok":False,"error":f"serp: {e}"}}

    tv = state.get("to_visit",[])
    tv = dedup(tv + [u for u in res_urls if u not in tv])
    if not tv:
        return {"phase":"report", "to_visit": tv, "last_result":{"ok":True,"queued":[]}, "search_count": search_count }

    return {
        "phase":"crawl",
        "to_visit": tv,
        "search_count": search_count,
        "last_result": {"ok": True, "query": q, "queued": res_urls},
        "args": {"url": tv[0], "max_pages": state.get("per_site_pages", PER_SITE_PAGES)}
    }

def crawl_node(state: S) -> Dict[str,Any]:
    to_visit = list(state.get("to_visit",[]))
    visited  = list(state.get("visited_urls",[]))
    new_domains = list(state.get("new_domains",[]))
    per_site_pages = state.get("per_site_pages", PER_SITE_PAGES)
    visits = int(state.get("visits", 0))

    url = state.get("args",{}).get("url") or (to_visit[0] if to_visit else "")
    if not url:
        return {"phase":"report","last_result":{"ok":False,"error":"empty queue"}}

    try:
        log(f"[SUP] CRAWL -> {url} (max_pages={per_site_pages})")
        orch.run(url, max_pages=per_site_pages)
        visited.append(url)
        if url in to_visit: to_visit.remove(url)
        d = norm_domain(url)
        if d: new_domains.append(d)
        visits += 1
        last = {"ok": True, "crawled": url, "max_pages": per_site_pages}
    except Exception as e:
        log("[SUP] CRAWL error:", repr(e))
        last = {"ok": False, "error": repr(e)}

    max_sites = state.get("max_sites", MAX_SITES)
    if len(visited) >= max_sites:
        nxt_phase = "report"
    elif not to_visit:
        if visits >= MIN_VISITS:
            nxt_phase = "report"
        else:
            nxt_phase = "search"  # go back to search for more
    else:
        nxt_phase = "crawl"

    args = {}
    if nxt_phase == "crawl" and to_visit:
        args = {"url": to_visit[0], "max_pages": per_site_pages}
        time.sleep(0.2)
    elif nxt_phase == "search":
        args = {}  # search will generate new query

    return {
        "phase": nxt_phase,
        "to_visit": to_visit,
        "visited_urls": dedup(visited),
        "new_domains": dedup(new_domains),
        "visits": visits,
        "last_result": last,
        "args": args
    }

def report_node(state: S) -> Dict[str,Any]:
    rep = quick_report(state.get("new_domains",[]))
    log("[SUP] REPORT:", json.dumps(rep, ensure_ascii=False))
    return {"phase": "stop", "report": rep, "last_result": {"ok": True, "report": rep}}

def stop_node(state: S) -> Dict[str,Any]:
    return {}

def final_node(state: S) -> Dict[str,Any]:
    return state

# ============== GRAPH ==============
def router(state: S):
    p = state.get("phase","plan")
    if p == "plan":   return "plan"
    if p == "search": return "search"
    if p == "crawl":  return "crawl"
    if p == "report": return "report"
    if p == "stop":   return "stop"
    return "plan"

workflow = StateGraph(S)
workflow.add_node("plan",   plan_node)
workflow.add_node("search", search_node)
workflow.add_node("crawl",  crawl_node)
workflow.add_node("report", report_node)
workflow.add_node("final",  final_node)

workflow.set_entry_point("plan")
workflow.add_conditional_edges("plan",   router, ["search", "crawl", "report", "stop"])
workflow.add_conditional_edges("search", router, ["search", "crawl", "report", "stop"])
workflow.add_conditional_edges("crawl",  router, ["search", "crawl", "report", "stop"])
workflow.add_conditional_edges("report", router, ["search", "stop"])
workflow.add_edge("final", END)

app = workflow.compile()

# ============== CLI ==============
def run(prompt: str) -> dict:
    seed = extract_first_url(prompt) or "https://www.iccsafe.org"
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    init = S({
        "prompt": prompt,
        "seed_url": seed,
        "per_site_pages": PER_SITE_PAGES,
        "max_sites": MAX_SITES,
        "max_per_domain": MAX_PER_DOMAIN,
        "to_visit": [],
        "visited_urls": [],
        "new_domains": [],
        "visits": 0,
        "search_count": 0,
        "phase": "plan",
        "args": {},
    })

    recursion = int(os.getenv("GRAPH_RECURSION_LIMIT","80"))
    try:
        res = app.invoke(init, config={"recursion_limit": recursion})
        log(f"[SUP] RES phase: {res.get('phase')}")
    except Exception as e:
        log("[SUP] GRAPH ERROR:", repr(e))
        rep = quick_report([])
        return {"action":"stop","visited_urls":[], "new_domains":[], "report": rep,
                "visited_file": None, "report_file": None}

    if not res or res.get("phase") != "stop":
        log("[SUP] GRAPH did not reach final phase")
        rep = quick_report([])
        return {"action":"stop","visited_urls":[], "new_domains":[], "report": rep,
                "visited_file": None, "report_file": None}

    visited = res.get("visited_urls", [])
    rep     = res.get("report", {})

    visited_path = os.path.join(logs_dir, f"visited_supervisor_{ts}.txt")
    with open(visited_path, "w", encoding="utf-8") as f:
        for u in visited: f.write(u+"\n")

    report_path = os.path.join(logs_dir, f"report_supervisor_{ts}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)

    return {
        "action": "stop",
        "visited_urls": visited,
        "new_domains": sorted(set(res.get("new_domains", []))),
        "report": rep,
        "visited_file": visited_path,
        "report_file": report_path
    }

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("You: ").strip()
    out = run(prompt) or {}
    print(json.dumps({"ok": True, **out}, indent=2, ensure_ascii=False))
