# tools/agent_chat.py
import os, sys, json, re, time, traceback
from typing import Dict, Any, List, Tuple
from urllib.parse import urlsplit

# === EXISTENTE în proiectul tău ===
from tools.serp_client import search as serp_search      # -> urls = serp_search(query, count=10)
from orchestrator.orchestrator_loop import Orchestrator  # -> orch.run(url, max_pages=...)

# === LLM (OpenAI-compatible) ===
import requests

# === DB pentru raport ===
from pymongo import MongoClient

# ------------- CONFIG -------------
OPENAI_API_KEY  = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_MODEL       = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMP        = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# Filtre SERP/crawl (pot fi schimbate din env)
INCLUDE_TLDS    = set((os.getenv("INCLUDE_TLDS", "org,gov,edu,int").lower()).split(","))
EXCLUDE_PATTERNS= os.getenv("EXCLUDE_PATTERNS",
    r"(gardening|irrigation|sprinkler(world|s)|home\s?depot|orbitonline|rainbird|retail|shop|store)").strip()
INCLUDE_PATTERN = os.getenv("INCLUDE_PATTERN", r".*").strip()

# Bugete sesiune (default-ok; pot fi supra-scrise din CLI/prompt)
DEFAULT_PER_SITE_PAGES = int(os.getenv("PER_SITE_PAGES", "6"))
DEFAULT_MAX_SITES      = int(os.getenv("MAX_SITES", "30"))
DEFAULT_MAX_PER_DOMAIN = int(os.getenv("MAX_PER_DOMAIN", "5"))
CRAWL_DELAY            = float(os.getenv("CRAWL_DELAY", "0.5"))

# Mongo (folosim MONGODB_URI / MONGO_DB, ca în restul proiectului)
MONGO_URL = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
DB_NAME   = os.getenv("MONGO_DB", "ai_agents_db")

if not OPENAI_API_KEY:
    print("ERROR: Setează OPENAI_API_KEY în env (fără newline la final).")
    sys.exit(1)

# ------------- UTILS -------------
def norm_domain(u: str) -> str:
    try:
        d = urlsplit(u).netloc.lower()
        if d.startswith("www."): d = d[4:]
        return d
    except Exception:
        return ""

def has_allowed_tld(domain: str) -> bool:
    # extrage TLD-ul final
    if not domain: return False
    parts = domain.split(".")
    tld = parts[-1] if parts else ""
    return tld in INCLUDE_TLDS if INCLUDE_TLDS else True

def filter_urls(urls: List[str],
                inc_rx: re.Pattern,
                exc_rx: re.Pattern,
                seen_urls: set,
                seen_domains: set,
                max_sites: int,
                max_per_domain: int) -> List[Tuple[str,str]]:
    """
    Returnează perechi (domain, url) filtrate și deduplicate, limitate pe domeniu & total.
    """
    picked = []
    per_dom = {}
    for u in urls or []:
        if not isinstance(u, str) or not u.startswith(("http://","https://")):
            continue
        if u in seen_urls:
            continue
        if exc_rx.search(u):
            continue
        if not inc_rx.search(u):
            continue
        d = norm_domain(u)
        if not d:
            continue
        if not has_allowed_tld(d):
            continue
        # fairness pe domeniu
        if per_dom.get(d, 0) >= max_per_domain:
            continue
        picked.append((d, u))
        per_dom[d] = per_dom.get(d, 0) + 1
        if len(picked) >= max_sites:
            break
    return picked

def extract_first_url(text: str) -> str:
    m = re.search(r"https?://[^\s)>\]]+", text or "")
    return m.group(0) if m else ""

# ------------- LLM -------------
def openai_chat(messages, temperature=LLM_TEMP):
    try:
        r = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": temperature
            },
            timeout=120,
        )
        r.raise_for_status()
        j = r.json()
        return j["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"LLM error: {e}")

SUPERVISOR_SYS = """You are the autonomous Supervisor of a web mapping pipeline.
Always reply ONLY with compact JSON (no prose), schema:
{
  "thought": "<very short why>",
  "next_action": "search|crawl|report|stop",
  "args": { ... }
}
- "search": expects {"query": "<string>", "count": 10}
- "crawl" : expects {"url": "<http/https>", "max_pages": 6}
- "report": expects {}
- "stop"  : expects {}
Goals:
- Start from the user's intent/seed and expand to related authoritative sources about fire codes/protection.
- Prefer .org/.gov/.edu/.int; avoid gardening/irrigation/retail/e-commerce noise.
- Be concise; one action per step. If you have enough data, pick "report" then "stop".
"""

# ------------- REPORT -------------
mc = MongoClient(MONGO_URL)
db = mc[DB_NAME]

def quick_report(session_new_domains: List[str]) -> Dict[str,Any]:
    agents = db["site_agents"]
    total_agents = agents.estimated_document_count()
    top = list(agents.find({}, {"_id":0,"domain":1,"pages":1}).sort("pages",-1).limit(12))
    return {
        "site_agents_total": total_agents,
        "top_domains": top,
        "session_new_domains": sorted(set(session_new_domains))
    }

# ------------- EXECUTOR -------------
orch = Orchestrator(crawl_delay=CRAWL_DELAY)

def do_search(args: Dict[str,Any],
              inc_rx: re.Pattern,
              exc_rx: re.Pattern,
              seen_urls: set,
              seen_domains: set,
              max_sites: int,
              max_per_domain: int) -> Dict[str,Any]:
    q = (args.get("query") or "").strip()
    cnt = int(args.get("count", 10))
    if not q:
        return {"ok": False, "error": "empty query"}
    try:
        raw_urls = serp_search(q, count=cnt) or []
        filtered = filter_urls(
            raw_urls, inc_rx, exc_rx,
            seen_urls=seen_urls, seen_domains=seen_domains,
            max_sites=max_sites, max_per_domain=max_per_domain
        )
        return {"ok": True, "query": q, "urls": [u for _,u in filtered]}
    except Exception as e:
        return {"ok": False, "error": f"serp_client: {e}"}

def do_crawl(args: Dict[str,Any],
             per_site_pages: int,
             seen_urls: set,
             session_new_domains: List[str]) -> Dict[str,Any]:
    url = (args.get("url") or "").strip()
    mp  = int(args.get("max_pages", per_site_pages))
    if not url.startswith(("http://","https://")):
        return {"ok": False, "error": "invalid url"}
    try:
        orch.run(url, max_pages=mp)
        seen_urls.add(url)
        d = norm_domain(url)
        if d:
            session_new_domains.append(d)
        return {"ok": True, "crawled": url, "max_pages": mp}
    except Exception as e:
        return {"ok": False, "error": repr(e)}

# ------------- SUPERVISOR LOOP -------------
def run_supervisor(user_msg: str,
                   per_site_pages: int = DEFAULT_PER_SITE_PAGES,
                   max_sites: int = DEFAULT_MAX_SITES,
                   max_per_domain: int = DEFAULT_MAX_PER_DOMAIN,
                   max_steps: int = 12):
    # regex-urile de includere/excludere
    inc_rx = re.compile(INCLUDE_PATTERN, re.I)
    exc_rx = re.compile(EXCLUDE_PATTERNS, re.I)

    # seed_url (dacă userul a pus unul în prompt)
    seed_url = extract_first_url(user_msg)

    # seturi de stare pe sesiune
    seen_urls: set = set()
    seen_domains: set = set()
    session_new_domains: List[str] = []

    # dacă avem seed, încearcă o primă acțiune de crawl local (în afara LLM), 1-2 pagini,
    # ca să avem un minim de context în DB
    if seed_url:
        try:
            print(f"[seed] crawl {seed_url}")
            orch.run(seed_url, max_pages=min(2, per_site_pages))
            seen_urls.add(seed_url)
            sd = norm_domain(seed_url)
            if sd: seen_domains.add(sd)
        except Exception as e:
            print(f"[seed error] {e}")

    # context sumar pentru LLM (opțional, scurt)
    agents = db["site_agents"]
    top = list(agents.find({}, {"_id":0,"domain":1,"pages":1}).sort("pages",-1).limit(8))
    ctx = {
        "seed_url": seed_url or None,
        "filters": {
            "include_tlds": sorted(INCLUDE_TLDS),
            "exclude_patterns": EXCLUDE_PATTERNS,
            "include_pattern": INCLUDE_PATTERN
        },
        "budgets": {
            "per_site_pages": per_site_pages,
            "max_sites": max_sites,
            "max_per_domain": max_per_domain
        },
        "known_top_domains": top
    }

    messages = [
        {"role":"system", "content": SUPERVISOR_SYS},
        {"role":"user",   "content": json.dumps({"task": user_msg, "context": ctx}, ensure_ascii=False)}
    ]
    history_summ = []

    for step in range(1, max_steps+1):
        # 1) Cere planul JSON
        try:
            out = openai_chat(messages)
        except Exception as e:
            return {"ok": False, "error": f"{e}"}

        # 2) Normalizează (taie ```json ... ```)
        txt = out.strip()
        if txt.startswith("```"):
            # scoate fence
            txt = re.sub(r"^```(?:json|JSON)?\s*", "", txt)
            txt = re.sub(r"\s*```$", "", txt)

        # 3) Parsează JSON strict; dacă nu e JSON, cere din nou strict JSON
        try:
            plan = json.loads(txt)
        except Exception:
            messages.append({"role":"assistant","content": out})
            messages.append({"role":"user","content":"Respond ONLY JSON per schema. No prose."})
            continue

        action  = (plan.get("next_action") or "").strip()
        args    = plan.get("args", {}) or {}
        thought = (plan.get("thought") or "").strip()

        # 4) Execută
        if action == "search":
            res = do_search(args, inc_rx, exc_rx, seen_urls, seen_domains, max_sites, max_per_domain)

            # dacă avem rezultate, împingem crawl-uri pentru primele N URL-uri propuse
            if res.get("ok") and res.get("urls"):
                queue = res["urls"]
                # face fairness pe domeniu în plus (max_per_domain) înainte de crawl
                per_dom = {}
                for u in queue:
                    d = norm_domain(u)
                    if not d: continue
                    if per_dom.get(d, 0) >= max_per_domain: continue
                    print(f"[expand] crawl {d} → {u}")
                    cres = do_crawl({"url": u, "max_pages": per_site_pages},
                                    per_site_pages, seen_urls, session_new_domains)
                    per_dom[d] = per_dom.get(d, 0) + 1
                    # log
                    history_summ.append({"step": step, "thought": thought, "action": "crawl", "args": {"url": u, "max_pages": per_site_pages}, "result": cres})
                    time.sleep(0.2)

        elif action == "crawl":
            res = do_crawl(args, per_site_pages, seen_urls, session_new_domains)

        elif action == "report":
            rep = quick_report(session_new_domains)
            res = {"ok": True, "report": rep}

        elif action == "stop":
            return {"ok": True, "done": True, "history": history_summ}

        else:
            res = {"ok": False, "error": f"unknown action {action}"}

        # 5) Log pas -> istoric + feedback pentru LLM
        history_summ.append({"step": step, "thought": thought, "action": action, "args": args, "result": res})
        messages.append({"role":"assistant","content": json.dumps({"action":action, "result":res}, ensure_ascii=False)})
        messages.append({"role":"user","content":"Next step. JSON only."})

        # dacă tocmai am dat report cu succes, închidem
        if action == "report" and res.get("ok"):
            return {"ok": True, "done": True, "history": history_summ}

    # dacă am atins max_steps fără stop/report, returnăm ce avem
    return {"ok": True, "done": False, "history": history_summ}

# ------------- CLI -------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = input("You: ").strip()

    # Poți suprascrie rapid bugetele din ENV (opțional)
    per_site_pages = int(os.getenv("CLI_PER_SITE_PAGES", DEFAULT_PER_SITE_PAGES))
    max_sites      = int(os.getenv("CLI_MAX_SITES", DEFAULT_MAX_SITES))
    max_per_domain = int(os.getenv("CLI_MAX_PER_DOMAIN", DEFAULT_MAX_PER_DOMAIN))

    res = run_supervisor(
        prompt,
        per_site_pages=per_site_pages,
        max_sites=max_sites,
        max_per_domain=max_per_domain,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))
