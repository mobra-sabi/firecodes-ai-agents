#!/usr/bin/env python3
import json, sys, re
from tools.sv.graph import build_app

def extract_first_url(text: str) -> str:
    m = re.search(r"https?://[^\s)>\]]+", text or "")
    return m.group(0) if m else ""

def main(prompt: str):
    app, cfg = build_app()
    seed = extract_first_url(prompt)
    init = {
        "prompt": prompt,
        "seed_url": seed,
        "per_site_pages": cfg["per_site_pages"],
        "max_sites": cfg["max_sites"],
        "max_per_domain": cfg["max_per_domain"],
        "to_visit": [],
        "visited_urls": [],
        "new_domains": [],
        "action": "search",
        "args": {"query": "fire safety standards codes site:.edu OR site:.gov OR site:.org", "count": 10},
    }
    res = None
    for chunk in app.stream(init, config={"recursion_limit": cfg["recursion_limit"]}):
        for _, v in chunk.items():
            res = v
        if res and res.get("action") == "stop":
            break

    print(json.dumps({
        "ok": True,
        "visited_urls": res.get("visited_urls", []) if res else [],
        "new_domains": sorted(set(res.get("new_domains", []))) if res else [],
        "report": res.get("report", {}) if res else {}
    }, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("You: ").strip()
    main(prompt)
