#!/usr/bin/env bash
set -euo pipefail
PID_FILE="server.pid"
PORT="${PORT:-8083}"

# 1) Oprește PID-ul din fișier (dacă mai trăiește)
if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${PID:-}" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "[stop] kill PID=$PID"
    kill "$PID" || true
    sleep 1
    kill -9 "$PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
fi

# 2) Omoară ce mai e pe port
echo "[stop] fuser -k :$PORT"
sudo fuser -k ${PORT}/tcp 2>/dev/null || true

# 3) Omoară procesele rătăcite după nume
echo "[stop] pkill uvicorn/agent_api"
pkill -f 'uvicorn|agent_api' 2>/dev/null || true

# 4) Așteaptă să se elibereze portul
for i in {1..10}; do
  if ss -ltn "( sport = :$PORT )" | awk 'NR>1{found=1} END{exit found?1:0}'; then
    echo "[stop] port $PORT liber"
    exit 0
  fi
  sleep 0.5
done
echo "[stop] WARN: port $PORT încă ocupat"
exit 0
