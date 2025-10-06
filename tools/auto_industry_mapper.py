import os, re, json, time, argparse, urllib.parse, requests
from datetime import datetime
from pymongo import MongoClient
from orchestrator.orchestrator_loop import Orchestrator

# ---------- utils ----------
def norm_domain(u: str) -> str:
    try:
        d = urllib.parse.urlsplit(u).netloc.lower()
        if d.startswith("www."): d = d[4:]
        return d
    except Exception:
        return ""

def pick_url(item):
    for k in ("link","url","formattedUrl","displayLink"):
        v = item.get(k)
        if isinstance(v, str) and v.startswith(("http://","https://")):
            return v
    v = item.get("url") or item.get("displayUrl")
    if isinstance(v, str) and v.startswith(("http://","https://")):
        return v
    return None

# ---------- SERP client with providers list ----------
def serp_search(query: str, count: int = 10):
    providers = [p.strip().lower() for p in os.getenv("SERP_PROVIDER","brave,serpapi").split(",") if p.strip()]
    last_err = None
    for prov in providers:
        try:
            if prov == "brave":
                key = os.getenv("BRAVE_API_KEY")
                assert key, "BRAVE_API_KEY missing"
                r = requests.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": count},
                    headers={"X-Subscription-Token": key, "Accept": "application/json"},
                    timeout=30
                )
                r.raise_for_status()
                j = r.json()
                items = []
                for b in (j.get("web",{}) or {}).get("results",[]) or []:
                    u = b.get("url")
                    if u: items.append(u)
                if items: return items
            elif prov == "serpapi":
                key = os.getenv("SERPAPI_KEY")
                assert key, "SERPAPI_KEY missing"
                r = requests.get(
                    "https://serpapi.com/search.json",
                    params={"engine":"google","q":query,"api_key":key,"num":count},
                    timeout=30
                )
                r.raise_for_status()
                j = r.json()
                items = []
                for block in ("organic_results","news_results","top_stories"):
                    for it in j.get(block,[]) or []:
                        u = pick_url(it)
                        if u: items.append(u)
                if items: return items
            else:
                continue
        except Exception as e:
            last_err = e
            continue
    if last_err: raise last_err
    return []

# ---------- Seed summary (pentru prompt) ----------
def seed_summary(seed_domain: str, max_docs: int = 20):
    try:
        mc = MongoClient("mongodb://127.0.0.1:27017")
        col = mc["ai_agents_db"]["site_content"]
        cur = col.find({"domain":{"$regex":rf"(^|\.){re.escape(seed_domain)}$"}},
                       {"title":1, "url":1, "word_count":1}).sort("fetched_at",-1).limit(max_docs)
        titles = []
        for d in cur:
            t = (d.get("title") or "").strip()
            if t: titles.append(t[:140])
        return {"domain": seed_domain, "sample_titles": titles[:15], "sample_count": len(titles)}
    except Exception:
        return {"domain": seed_domain, "sample_titles": [], "sample_count": 0}

# ---------- ChatGPT supervisor ----------
def openai_chat(messages, model=None):
    model = model or os.getenv("LLM_MODEL","gpt-4o-mini")
    base = os.getenv("OPENAI_BASE_URL","https://api.openai.com/v1")
    key  = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY missing (supervisor)")
    url = base.rstrip("/") + "/chat/completions"
    r = requests.post(url, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }, json={
        "model": model,
        "messages": messages,
        "temperature": 0.2
    }, timeout=60)
    r.raise_for_status()
    j = r.json()
    return j["choices"][0]["message"]["content"]

def ask_supervisor(seed_url: str):
    seed_dom = norm_domain(seed_url)
    ctx = seed_summary(seed_dom)
    sys = (
      "You are an autonomous industry-mapper supervisor. "
      "Given a seed site, produce a JSON plan with keys: "
      "`queries` (array of web queries), "
      "`include_patterns` (regex string), "
      "`exclude_patterns` (regex string), "
      "`max_per_domain` (int 1..10), and `_why` (5-10 sentences explaining decisions). "
      "Keep it compact and executable. No prose outside JSON."
    )
    usr = {
      "seed_url": seed_url,
      "seed_domain": seed_dom,
      "seed_sample_titles": ctx.get("sample_titles", [])[:10],
      "goal": "map industry sites related to fire protection / codes / standards around the seed; avoid unrelated gardening/irrigation retail; prefer official orgs, standards bodies, associations, code portals, enforcement.",
      "budget": {"max_sites": 60, "per_site_pages": 8}
    }
    content = openai_chat([
        {"role":"system","content": sys},
        {"role":"user","content": json.dumps(usr)}
    ])
    # parse JSON only
    plan = {}
    try:
        plan = json.loads(content)
    except Exception:
        # fallback minimal plan
        plan = {
            "queries":[f"{ctx['domain']} regulations","NFPA 13","fire sprinkler system requirements","firestopping requirements","FM Approvals fire protection"],
            "include_patterns":"(fire|sprinkler|nfpa|firestop|ul|fm|code|standard|inspection|ibc|ifc)",
            "exclude_patterns":"(irrigation|lawn|garden|home\\s?depot|orbitonline|rainbird|sprinklerworld)",
            "max_per_domain": 6,
            "_why":"Fallback plan used because model response was not valid JSON."
        }
    return plan

# ---------- Audit log ----------
def log_supervisor(seed, plan, picked_sites):
    try:
        mc = MongoClient("mongodb://127.0.0.1:27017")
        mc["ai_agents_db"]["supervisor_logs"].insert_one({
            "ts": datetime.utcnow(),
            "seed": seed,
            "plan": plan,
            "picked_sites": picked_sites,
            "reasoning": plan.get("_why","")
        })
    except Exception as e:
        print(f"[audit warn] cannot write supervisor log: {e}")

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seed", help="Seed URL (ex: https://www.iccsafe.org)")
    ap.add_argument("--per_site_pages", type=int, default=6)
    ap.add_argument("--max_sites", type=int, default=20)
    ap.add_argument("--crawl_delay", type=float, default=0.5)
    args = ap.parse_args()

    orch = Orchestrator(crawl_delay=args.crawl_delay)

    print(f"[seed] crawl {args.seed}")
    orch.run(args.seed, max_pages=args.per_site_pages)

    # supervisor makes the plan
    print("[supervisor] planning…")
    plan = ask_supervisor(args.seed)
    print(f"[plan] {plan}")

    include_re = re.compile(plan.get("include_patterns") or ".*", re.I)
    exclude_re = re.compile(plan.get("exclude_patterns") or r"$^", re.I)
    max_per_domain = int(plan.get("max_per_domain") or 6)

    # discovery via SERP
    seen = set([norm_domain(args.seed)])
    queue = []
    for q in plan.get("queries",[])[:40]:
        try:
            urls = serp_search(q, count=10)
        except Exception as e:
            print(f"[serp error] {e}")
            continue
        bucket = {}
        for u in urls:
            if not include_re.search(u) or exclude_re.search(u):
                continue
            d = norm_domain(u)
            if not d or d in seen:
                continue
            bucket.setdefault(d, 0)
            if bucket[d] < max_per_domain:
                bucket[d] += 1
                seen.add(d)
                queue.append((d, u))
        if len(queue) >= args.max_sites:
            break

    print(f"[queue] {len(queue)} new sites")
    log_supervisor(args.seed, plan, [d for d,_ in queue])

    # crawl per target
    for i, (d,u) in enumerate(queue[:args.max_sites], 1):
        print(f"[{i}/{min(args.max_sites,len(queue))}] crawl {d} → {u}")
        try:
            orch.run(u, max_pages=args.per_site_pages)
        except Exception as e:
            print(f"[crawl error] {d}: {e}")
        time.sleep(0.2)

if __name__ == "__main__":
    main()
