#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8083}"
LOG_FILE="server.log"
PID_FILE="server.pid"

# venv
if [[ -f ".venv/bin/activate" ]]; then
  source .venv/bin/activate
else
  source /home/mobra/aienv/bin/activate 2>/dev/null || true
fi

# env
if [[ -f "config.env" ]]; then
  set -a; source config.env; set +a
fi

# port liber?
if ss -ltn "( sport = :$PORT )" | awk 'NR>1{found=1} END{exit found?0:1}'; then
  echo "[start] EROARE: port $PORT este ocupat. Rulează ./stop_server.sh"
  exit 1
fi

echo "[start] pornesc uvicorn pe 0.0.0.0:${PORT} ..."
nohup uvicorn agent_api:app --host 0.0.0.0 --port "${PORT}" --workers 1 --proxy-headers \
  > "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"

# Așteaptă până serverul răspunde (max 30s)
for i in {1..60}; do
  if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null; then
    echo "[start] OK, server UP. PID=$(cat "$PID_FILE") | log: $LOG_FILE"
    exit 0
  fi
  sleep 0.5
done

echo "[start] FAIL: server nu răspunde pe /health. Vezi $LOG_FILE"
exit 1
