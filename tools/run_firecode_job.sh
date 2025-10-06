#!/usr/bin/env bash
set -euo pipefail

TS="$(date +"%Y%m%d_%H%M%S")"
mkdir -p logs

PROMPT=${1:-$'Urmează STRICT pașii plan→search→crawl→report.\nNu finaliza fără CRAWL.\nCrawl pe iccsafe.org și codes.iccsafe.org (minim 12 pagini / domeniu). La final: raport + lista URL-urilor vizitate.\nTask: Vreau să mapezi ecosistemul codurilor de incendiu pornind de la https://www.iccsafe.org; dă-mi un raport.'}

RUN_RAW="logs/sv_run_${TS}.raw"
RUN_JSON="logs/sv_run_${TS}.json"
RUN_LOG="logs/sv_run_${TS}.stderr"

# 1) rulează; colectăm tot stdout în .raw, stderr în .stderr
python -m tools.supervisor_graph "$PROMPT" >"$RUN_RAW" 2>"$RUN_LOG" || true

# 2) extragem DOAR blocul JSON: de la prima linie care începe cu { până la EOF
sed -n '/^{/,$p' "$RUN_RAW" > "$RUN_JSON" || true

echo "[i] Raw stdout     : $RUN_RAW"
echo "[i] JSON filtrat   : $RUN_JSON"
echo "[i] Log (stderr)   : $RUN_LOG"

# 3) validăm JSON-ul; dacă pică, arătăm primele linii ca să vezi ce a ieșit
if ! jq -e . "$RUN_JSON" >/dev/null 2>&1; then
  echo "[!] JSON invalid. Primele 40 linii din raw:" >&2
  nl -ba "$RUN_RAW" | sed -n '1,40p' >&2
  exit 1
fi

# 4) extrage artefactele
VIS="$(jq -r '.visited_file // empty' "$RUN_JSON")"
REP="$(jq -r '.report_file  // empty' "$RUN_JSON")"

if [[ -n "${VIS}" && -f "${VIS}" ]]; then
  echo "[i] URL-uri vizitate: $VIS"
  wc -l "$VIS"
else
  echo "[!] Nu există fișier cu URL-uri vizitate."
fi

if [[ -n "${REP}" && -f "${REP}" ]]; then
  echo "[i] Raport JSON: $REP"
else
  echo "[!] Nu există fișier raport."
fi
