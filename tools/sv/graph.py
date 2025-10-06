import json
from langgraph.graph import StateGraph, END

from .llm_client import make_llm
from .state import get_cfg, compile_filters, dedup, norm_domain
from .actions import do_search, do_crawl
from .reporting import quick_report

SYS_PROMPT = """You are the autonomous Supervisor of a web mapping pipeline.
Always reply ONLY JSON:
{"thought":"<short>","next_action":"search|crawl|report|stop","args":{...}}
- search: {"query":"...","count":10}
- crawl: {"url":"...","max_pages":6}
- report: {}
- stop: {}
Prefer .org/.gov/.edu/.int. Avoid gardening/irrigation/retail/ecommerce noise.
One step at a time; when enough info, do report then stop.
"""

def build_app():
    llm = make_llm()
    cfg = get_cfg()
    inc_rx, exc_rx = compile_filters(cfg)
    sup_log = cfg["sup_log"]

    class S(dict): ...
    def log(tag, obj):
        if sup_log:
            print(f"[SUP] {tag}: {json.dumps(obj, ensure_ascii=False)}", flush=True)

    def plan_node(state: S) -> S:
        # safety defaults
        state.setdefault("visited_urls", [])
        state.setdefault("to_visit", [])
        state.setdefault("new_domains", [])
        state.setdefault("max_sites", cfg["max_sites"])
        state.setdefault("per_site_pages", cfg["per_site_pages"])
        state.setdefault("max_per_domain", cfg["max_per_domain"])

        # dacă deja am atins bugetul—raport
        if len(state.get("visited_urls", [])) >= state["max_sites"]:
            state.update({"action":"report", "args":{}, "last_plan":{"thought":"budget hit","next_action":"report","args":{}}})
            log("PLAN", state["last_plan"]); return state

        context = {
            "seed_url": state.get("seed_url"),
            "filters": {
                "include_tlds": sorted(cfg["include_tlds"]),
                "exclude_patterns": cfg["exclude_patterns"],
                "include_pattern": cfg["include_pattern"],
            },
            "budgets": {
                "per_site_pages": state["per_site_pages"],
                "max_sites": state["max_sites"],
                "max_per_domain": state["max_per_domain"],
            },
            "progress": {
                "visited": len(state.get("visited_urls",[])),
                "to_visit": len(state.get("to_visit",[])),
                "new_domains": len(state.get("new_domains",[])),
            }
        }
        msg = [
            {"role":"system","content":SYS_PROMPT},
            {"role":"user","content":json.dumps({"task":state["prompt"],"context":context}, ensure_ascii=False)}
        ]
        try:
            out = llm.invoke(msg).content.strip()
        except Exception as e:
            # fallback: dacă LLM cade, mergem direct pe report
            plan = {"thought": f"llm-fail:{e}", "next_action":"report", "args":{}}
            state.update({"last_plan":plan, "action":"report", "args":{}})
            log("PLAN", plan); return state

        if out.startswith("```"):
            out = out.strip("` \n\t")
            if out.lower().startswith("json"):
                out = out[4:].lstrip()

        try:
            plan = json.loads(out)
        except Exception:
            plan = {"thought":"fallback-json", "next_action":"report", "args":{}}

        state["last_plan"] = plan
        state["action"] = plan.get("next_action","report")
        state["args"]   = plan.get("args",{})
        log("PLAN", plan)
        return state

    def search_node(state: S) -> S:
        res = do_search(state.get("args",{}), cfg, inc_rx, exc_rx, state.get("visited_urls",[]))
        if not res.get("ok"):
            state["last_result"] = res
            state["action"] = "report"
            state["args"] = {}
            return state

        urls = res.get("urls", [])
        tv = state.get("to_visit", [])
        tv = tv + [u for u in urls if u not in tv]
        state["to_visit"] = dedup(tv)
        state["last_result"] = {"ok": True, "queued": urls}
        if state["to_visit"]:
            state["action"] = "crawl"
            state["args"] = {"url": state["to_visit"][0], "max_pages": state["per_site_pages"]}
        else:
            state["action"] = "report"; state["args"]={}
        return state

    def crawl_node(state: S) -> S:
        url = state.get("args",{}).get("url") or (state.get("to_visit",[])[:1] or [""])[0]
        if not url:
            state["last_result"] = {"ok": False, "error": "empty queue"}
            state["action"] = "report"; state["args"]={}
            return state

        res = do_crawl({"url": url}, cfg)
        state["last_result"] = res
        if res.get("ok"):
            visited = state.get("visited_urls", [])
            to_visit= state.get("to_visit", [])
            newdoms = state.get("new_domains", [])
            visited.append(url)
            if url in to_visit: to_visit.remove(url)
            d = norm_domain(url)
            if d: newdoms.append(d)
            state["visited_urls"] = dedup(visited)
            state["to_visit"] = to_visit
            state["new_domains"] = dedup(newdoms)

        if len(state["visited_urls"]) >= state["max_sites"]:
            state["action"] = "report"; state["args"]={}
        elif state["to_visit"]:
            nxt = state["to_visit"][0]
            state["action"] = "crawl"
            state["args"] = {"url": nxt, "max_pages": state["per_site_pages"]}
        else:
            state["action"] = "report"; state["args"]={}
        return state

    def report_node(state: S) -> S:
        rep = quick_report(state.get("new_domains", []))
        state["report"] = rep
        state["last_result"] = {"ok": True, "report": rep}
        print("[SUP] REPORT:", json.dumps(rep, ensure_ascii=False), flush=True)
        state["action"] = "stop"; state["args"]={}
        return state

    wf = StateGraph(S)
    wf.add_node("plan",   plan_node)
    wf.add_node("search", search_node)
    wf.add_node("crawl",  crawl_node)
    wf.add_node("report", report_node)

    def router(state: S):
        a = state.get("action","report")
        return a if a in ("plan","search","crawl","report") else "report"

    wf.set_entry_point("plan")
    wf.add_conditional_edges("plan",   router, {"search":"search", "crawl":"crawl", "report":"report", "stop": END})
    wf.add_conditional_edges("search", router, {"search":"search", "crawl":"crawl", "report":"report", "stop": END})
    wf.add_conditional_edges("crawl",  router, {"search":"search", "crawl":"crawl", "report":"report", "stop": END})
    wf.add_edge("report", END)

    app = wf.compile()
    return app, cfg
