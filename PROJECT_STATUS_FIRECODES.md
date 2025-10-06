# AI Agents — Fire Codes Mapping (status & next steps)

_Actualizat: 2025-10-06 09:20_

## 1) Ce avem funcțional acum
- **Qdrant/Mongo**: colecția cu date este `site_embeddings`; `tools/build_site_agents.py` scrie agregări per domeniu în Mongo `ai_agents_db.site_agents`.
- **Stare agregări**: 63 domenii (top: iccsafe.org 5138; nfpa.org 103; nfsa.org 54; nist.gov 45…).
- **OpenAI key**: `tools/configure_openai_key.sh` (salvează în `.secrets/openai.key` și `~/.config/ai_agents/openai.key`). `tools/llm_key_loader.py` citește, curăță newline/BOM; LLM ok (`gpt-4o-mini`).
- **Brave Search**: cheie în `.secrets/brave.key`. `tools/serp_client.py` folosește Brave cu retry și parse robust (`web.results` + `mixed`).
- **Supervisor (LangGraph)**: `tools/supervisor_graph.py` cu noduri `plan → search → crawl → report`, filtre, seed din prompt, raport din Mongo (încă sare uneori direct la report).
- **Fallback determinist**: `tools/fallback_firecode_mapper.py` → SERP Brave → crawl real, artefacte:
  - `logs/visited_fb_<ts>.txt`
  - `logs/report_fb_<ts>.json`
- **Runner + JSON filter**: `tools/run_firecode_job.sh` (salvează curat în `logs/sv_run_<ts>.json` + `.stderr`).

## 2) Rețete rapide
### Chei
\`\`\`bash
bash tools/configure_openai_key.sh
source tools/configure_openai_key.sh --export
printf '%s' 'BSA_…' > .secrets/brave.key && chmod 600 .secrets/brave.key
\`\`\`

### Teste
\`\`\`bash
python - <<'PY'
from tools.llm_key_loader import ensure_openai_key
from langchain_openai import ChatOpenAI
ensure_openai_key()
print(ChatOpenAI(model="gpt-4o-mini", temperature=0).invoke([{"role":"user","content":"OK"}]).content)
PY

python -m tools.serp_client "site:nfpa.org codes and standards" 3 --debug
\`\`\`

### Crawl fallback (recomandat)
\`\`\`bash
export INCLUDE_DOMAINS="iccsafe.org,codes.iccsafe.org"
export EXCLUDE_DOMAINS="shop.iccsafe.org"
export INCLUDE_TLDS="org"
export PER_SITE_PAGES=12 MAX_PER_DOMAIN=12 CRAWL_DELAY=0.6

TS="$(date +"%Y%m%d_%H%M%S")"
python -m tools.fallback_firecode_mapper | tee "logs/fallback_${TS}.log"
\`\`\`

### Supervisor cu JSON filtrat
\`\`\`bash
INCLUDE_DOMAINS="iccsafe.org,codes.iccsafe.org" \
EXCLUDE_DOMAINS="shop.iccsafe.org" \
PER_SITE_PAGES=12 MAX_SITES=24 MAX_PER_DOMAIN=12 MIN_VISITS=4 \
SUP_LOG=1 GRAPH_RECURSION_LIMIT=150 \
./tools/run_firecode_job.sh
\`\`\`

## 3) Probleme cunoscute
1) Supervisor nu intră mereu în **CRAWL**.  
2) Poate atinge **recursion_limit**.  
3) Multe pagini ICC sunt shop/paywall/PDF (excludem `shop.iccsafe.org`).

## 4) Next steps
- Driver determinist în grafic: continuă `crawl` până la `MIN_VISITS`/`MAX_SITES`, apoi `report`.
- `report_node` să salveze `logs/visited_<ts>.txt` și `logs/report_<ts>.json`.
- Ajustează filtrele `INCLUDE_PATTERN`.
- Rerulează `tools/build_site_agents.py` după crawl.

## 5) Comenzi utile
\`\`\`bash
QDRANT_COLLECTION="site_embeddings" PYTHONPATH=. python tools/build_site_agents.py
python -m tools.fallback_firecode_mapper
./tools/run_firecode_job.sh
\`\`\`

### Run 2025-10-06 09:29
- Visited: 24 URLs
- Report: `logs/report_fb_20251006_092604.json`

