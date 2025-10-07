# tools/industry_expander.py
# Expand industry by creating agents for similar sites suggested by ChatGPT

import os, json
from tools.simple_agent_creator import create_agent
from tools.orchestrator_advisor import analyze_website

LOG = bool(int(os.getenv("SUP_LOG","0")))
def log(*a):
    if LOG:
        print(*a, file=__import__("sys").stderr, flush=True)

def expand_industry(seed_url: str, max_sites: int = 5) -> dict:
    """
    Analyze seed URL, get similar sites from ChatGPT, create agents for them.
    """
    log(f"Expanding industry from {seed_url}")

    # Get analysis
    analysis = analyze_website(seed_url)
    similar_sites = analysis.get("similar_sites", [])[:max_sites]

    created_agents = []
    for site in similar_sites:
        log(f"Creating agent for {site}")
        result = create_agent(site)
        if result["ok"]:
            created_agents.append(result)
        else:
            log(f"Failed to create agent for {site}: {result.get('error')}")

    return {
        "seed_url": seed_url,
        "analysis": analysis,
        "created_agents": created_agents,
        "total_created": len(created_agents)
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m tools.industry_expander <seed_url> [max_sites]")
        sys.exit(1)

    seed_url = sys.argv[1]
    max_sites = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    result = expand_industry(seed_url, max_sites)
    print(json.dumps(result, ensure_ascii=False, indent=2))
