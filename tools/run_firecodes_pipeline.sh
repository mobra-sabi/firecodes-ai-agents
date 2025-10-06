#!/usr/bin/env bash
set -euo pipefail

TS="$(date +'%Y%m%d_%H%M%S')"
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# 1) fallback crawl (determinist)
python -m tools.fallback_firecode_mapper | tee "${LOG_DIR}/fallback_${TS}.log"

# extrage artefactele din log (fără să pice dacă lipsește jq)
VIS=$(command -v jq >/dev/null 2>&1 && jq -r '.visited_file' "${LOG_DIR}/fallback_${TS}.log" || echo "")
REP=$(command -v jq >/dev/null 2>&1 && jq -r '.report_file'  "${LOG_DIR}/fallback_${TS}.log" || echo "")

# 2) rebuild site agents
QDRANT_COLLECTION="site_embeddings" PYTHONPATH=. python tools/build_site_agents.py || true

# 3) snapshot arhivă
./tools/make_snapshot.sh || true

# 4) append status în PROJECT_STATUS_FIRECODES.md
DATE="$(date +"%Y-%m-%d %H:%M")"
VISCOUNT="0"
if [ -n "${VIS}" ] && [ -f "${VIS}" ]; then
  VISCOUNT="$(wc -l < "${VIS}")"
fi

{
  echo
  echo "### Run ${DATE}"
  echo "- Visited: ${VISCOUNT} URLs"
  echo "- Visited file: \`${VIS:-n/a}\`"
  echo "- Report file:  \`${REP:-n/a}\`"
} >> PROJECT_STATUS_FIRECODES.md

echo "[✓] Pipeline done. Visited=${VISCOUNT}, VIS=${VIS:-n/a}, REP=${REP:-n/a}"
