# FireCodes Mapper — Autonomous Web Discovery System

_Updated: October 7, 2025_

## Vision & Objectives

Build an autonomous industrial discovery system where the LLM decides what to search and scrape on the web, starting from a seed site. The target flow:

- Client inputs a seed site.
- Crawl & parse entire site → MongoDB (pages/sites collections) + Qdrant (vectors) with normalization, deduplication, entities, language detection.
- LLM Supervisor analyzes collected data, extracts entities/themes, generates SERP queries + target types (directories, suppliers, associations, marketplaces, competitors) + crawl rules + priorities.
- Frontier Manager (priority queue): score = semantic similarity, authority, novelty, diversity; fairness per domain.
- Multi-hop discovery: for each new site → crawl → store → update frontier; loop until stop conditions (saturation, budget, minimum taxonomy coverage).
- Continuous learning (Qwen) from decision logs (context → action → result).

Phase 0 (compliance): robots.txt, rate-limit, "politeness delay", only public content.
Phase 1 (seed ingest): Playwright/Selenium if needed + trafilatura/Readability; normalization, entities, deduplication; Mongo (pages, sites), Qdrant (industry_mem/site_embeddings).
Phase 2 (LLM Supervisor): decides queries/targets/rules/priorities.
Phase 3 (multi-hop): SERP → target filtering → crawl → store → loop.
Phase 4 (stop): saturation/budget/minimum taxonomy coverage.

## Current Status vs. Target (by Phases)

### Phase 0 — Rules & Compliance
✅ Rate-limit & delay configurable in crawl (e.g. CRAWL_DELAY=0.6), domain filtering (INCLUDE/EXCLUDE_DOMAINS, INCLUDE_TLDS).
⚠️ Formalize robots.txt checker in used crawler (implicit in some scripts, but not centralized).
⏳ Document TOS per domain + fallback for PDF/paywall.

### Phase 1 — Seed Ingest (Mongo + Qdrant)
✅ Qdrant: collection `site_embeddings` operational; payload existing.
✅ Domain aggregation: `tools/build_site_agents.py` writes to Mongo `ai_agents_db.site_agents` (centroid, pages).
⚠️ Mongo pages/sites: detailed schema (title, text, html_hash, headers, outlinks, entities) not yet implemented as such (only domain aggregations exist).
⏳ Deduplication (hash + near-duplicate via cosine) + entities (brand/products/categories) — to be introduced in parse pipeline.

### Phase 2 — LLM Supervisor (decision)
⚠️ `tools/supervisor_graph.py` exists (nodes plan → search → crawl → report), but:
- Sometimes jumps directly to report without forcing minimum crawl;
- Errors: GRAPH_RECURSION_LIMIT, KeyError('__end__') (incomplete transitions to END).
⏳ Add deterministic driver: no report until MIN_VISITS/MAX_SITES reached.

### Phase 3 — Multi-hop Discovery
✅ SERP: `tools/serp_client.py` (Brave) fixed: 422 resolved, mixed can be list, debug flags.
✅ Deterministic fallback: `tools/fallback_firecode_mapper.py` → SERP Brave → real crawl → artifacts (visited_fb_*.txt, report_fb_*.json).
⚠️ Still enters some shop/paywall links (despite EXCLUDE=shop.iccsafe.org) — strengthen filtering after seed expansion.
⏳ Frontier Manager priority (semantic/authority/novelty/diversity) — to be implemented as separate module and used by supervisor.

### Phase 4 — Stop Conditions
⏳ Saturation heuristics (novelty rate), budget (pages/hours), minimum taxonomy coverage — to be added.

Learning/Training (Qwen)
⏳ Systematic logging of (context → action → result) pairs and dataset generation for fine-tuning (training/*.jsonl files exist, but not linked to current supervisor decisions).

## What Was Executed (from this chat)

Keys & Setup
- OpenAI key: `tools/configure_openai_key.sh` (storage in .secrets/ + ~/.config), loader robust `tools/llm_key_loader.py`.
- Brave key: .secrets/brave.key + fallback loader; fix to client (ui_lang/country/safesearch, parse mixed).
- Deterministic crawl (fallback)
  - Run multiple times with:
    - INCLUDE_DOMAINS="iccsafe.org,codes.iccsafe.org"
    - EXCLUDE_DOMAINS="shop.iccsafe.org"
    - INCLUDE_TLDS="org"
    - PER_SITE_PAGES=12 MAX_PER_DOMAIN=12 CRAWL_DELAY=0.6

  - Typical result: ~24 URLs visited/run, files:
    - logs/visited_fb_<ts>.txt
    - logs/report_fb_<ts>.json
- Qdrant + Mongo aggregation
  - Qdrant OK (site_embeddings), `tools/build_site_agents.py` → ~70 domains / ~5859 points in latest run.
- Supervisor Graph (LLM)
  - Ran, but crashed on KeyError('__end__') or jumped directly to report; reached GRAPH_RECURSION_LIMIT.
- Conclusion: Need to strengthen graph edges + deterministic driver.

Export & Transfer
- `tools/make_snapshot.sh` → exports/firecodes_project_<ts>.tar.gz (+ exports/meta/requirements-freeze.txt).
- Transfer to laptop via scp from PowerShell (Tailscale/SSH).

GitHub Integration
- Repo created: mobra-sabi/firecodes-ai-agents.
- SSH-key on server, git push -u origin main, .gitignore correct (exclude .secrets/*.key, logs/, exports/).
- ChatGPT Attach repository (Codex) — ok.

CI / Self-hosted Runner (in progress)
- Initial wrong download (URL "latest/download/…", invalid archive).
- Then correct download (v2.328.0): no longer includes svc.sh — ok.
- Created systemd unit for run.sh (start as service).
- Error 404 at ./config.sh --token TOKEN (TOKEN placeholder). Need real token from Settings → Actions → Runners → New self-hosted runner.

YAML workflow saved in shell (normal to error) — need to save in .github/workflows/ci.yml.

Auxiliary Scripts
- `tools/run_firecodes_pipeline.sh` — one-liner: fallback crawl → build_site_agents → snapshot → status.
- `tools/push_to_github.sh` — rapid sync with origin.

## Problems/Blockages & Their Status
- SERP Brave 422 / mixed list → ✅ Resolved in `tools/serp_client.py`.
- Supervisor jumps to report / recursion limit / __end__ → ⚠️ To fix edges + deterministic driver.
- Shop/paywall still slips sometimes → ⚠️ Stronger pattern filtering & seed expander.
- Missing complete Mongo pages/sites → ⚠️ Implement schema and parser.
- Runner 404 → ⚠️ Use real token from GitHub UI; after ./config.sh … --unattended, service becomes "Listening for Jobs".

## What Remains to Do (Priority Backlog, Concrete)
### A. Ingest Pipeline (Phase 1)
- Implement scraper + parser that writes to Mongo:
  - pages{url, domain, title, text, html_hash, lang, fetched_at, headers, outlinks[], entities[]}
  - sites{domain, first_seen, last_crawl, robots_policy, crawl_status, coverage_metrics}
- Integrate trafilatura/Readability + Playwright for dynamic pages.
- Deduplication (hash + near-duplicate via cosine).
- Entity extraction (spaCy / regex + heuristics) for brand/products/categories.

### B. LLM Supervisor & Frontier (Phases 2–3)
- Fix edges in `supervisor_graph.py` (all branches to __end__/END).
- Add deterministic driver: no report until MIN_VISITS and/or MAX_SITES reached.
- Frontier Manager: queue with score (semantic + authority + novelty + diversity), fairness per domain.
- Stop conditions: saturation, budget, minimum taxonomy coverage.

### C. Compliance & Filtering
- Central robots.txt module (respect per host).
- Consolidated URL filters (shop/paywall exclusions, only chapters/appendix, etc.).

### D. CI/CD & Operations
- Configure self-hosted runner with real token:
  - ./config.sh --url https://github.com/<user>/<repo> --token <REAL_TOKEN> --labels self-hosted,viezure,python --unattended
- Add .github/workflows/ci.yml (example below).
- In Actions → Secrets, set OPENAI_API_KEY, BRAVE_API_KEY.
- CI artifacts: upload logs/report_fb_*.json, logs/visited_fb_*.txt.

### E. Learning
- Log (context → action → result) for each LLM decision.
- Dataset generation script training/*.jsonl for Qwen fine-tuning.

## Key Files Existing

- Deterministic crawl: `tools/fallback_firecode_mapper.py`
- SERP client: `tools/serp_client.py` (Brave fixed)
- Supervisor (LLM/LangGraph): `tools/supervisor_graph.py` (to stabilize)
- Aggregation → Mongo: `tools/build_site_agents.py`
- Runner pipeline: `tools/run_firecodes_pipeline.sh`
- Snapshot: `tools/make_snapshot.sh`

## Quick Start Commands (Manual, on Server)
```bash
TS=$(date +'%Y%m%d_%H%M%S'); \
python -m tools.fallback_firecode_mapper | tee logs/fallback_${TS}.log; \
QDRANT_COLLECTION="site_embeddings" PYTHONPATH=. python tools/build_site_agents.py || true; \
./tools/make_snapshot.sh || true; \
git add -A; git commit -m "Daily run ${TS}" || true; git push
```

## CI Workflow (Example)

Save in `.github/workflows/ci.yml`:

```yaml
name: FireCodes_CI

on:
  workflow_dispatch:
  push:
    branches: [ main ]

jobs:
  run-pipeline:
    runs-on: [self-hosted, viezure, python]
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install deps
        run: |
          python -m pip install -U pip
          pip install qdrant-client pymongo langchain-openai requests trafilatura playwright
          python -m playwright install --with-deps chromium

      - name: Run fallback crawl
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          BRAVE_API_KEY: ${{ secrets.BRAVE_API_KEY }}
        run: |
          export INCLUDE_DOMAINS="iccsafe.org,codes.iccsafe.org"
          export EXCLUDE_DOMAINS="shop.iccsafe.org"
          export INCLUDE_TLDS="org"
          export PER_SITE_PAGES=12 MAX_PER_DOMAIN=12 CRAWL_DELAY=0.6
          TS=$(date +'%Y%m%d_%H%M%S')
          python -m tools.fallback_firecode_mapper | tee logs/fallback_${TS}.log

      - name: Build site agents
        run: |
          QDRANT_COLLECTION="site_embeddings" PYTHONPATH=. python tools/build_site_agents.py || true

      - name: Upload logs
        uses: actions/upload-artifact@v4
        with:
          name: firecodes-logs
          path: |
            logs/*.log
            logs/report_fb_*.json
            logs/visited_fb_*.txt
```

Important: In GitHub → repo → Settings → Actions → Runners → New self-hosted runner → get real token and run ./config.sh on server. After configuration, run.sh will display "Listening for Jobs".
