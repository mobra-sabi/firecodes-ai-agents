#!/usr/bin/env bash
set -euo pipefail

# ---------- setări destinații ----------
DEST_REPO="$(pwd)/.secrets/openai.key"
DEST_HOME="$HOME/.config/ai_agents/openai.key"

# ---------- citește cheia din terminal ----------
echo "Introduce cheia ta OpenAI (nu se va afișa)."
read -rsp "OPENAI_API_KEY: " KEY
echo
# fără CR/LF
KEY="$(printf '%s' "$KEY" | tr -d '\r\n')"

if [ -z "$KEY" ]; then
  echo "Cheie goală. Anulat."
  exit 1
fi

# ---------- salvează în fișiere ----------
mkdir -p "$(dirname "$DEST_REPO")" "$(dirname "$DEST_HOME")"
printf '%s' "$KEY" > "$DEST_REPO"
printf '%s' "$KEY" > "$DEST_HOME"
chmod 600 "$DEST_REPO" "$DEST_HOME"

echo "✅ Cheia a fost salvată în:"
echo "   - $DEST_REPO"
echo "   - $DEST_HOME"

# ---------- test opțional cu OpenAI ----------
if command -v curl >/dev/null 2>&1; then
  echo "Verificare rapidă la OpenAI /v1/models…"
  HTTP=$(curl -sS https://api.openai.com/v1/models \
    -H "Authorization: Bearer $KEY" \
    -o /tmp/openai_models_check.json -w '%{http_code}' || true)
  if [ "$HTTP" = "200" ]; then
    echo "✅ Autentificare reușită."
  else
    echo "⚠️  Răspuns HTTP $HTTP — verifică dacă cheia este corectă."
    head -c 200 /tmp/openai_models_check.json 2>/dev/null || true
    echo
  fi
fi

# ---------- export în sesiunea curentă (doar dacă e 'sourced' + --export) ----------
IS_SOURCED=0
# dacă scriptul e "sourced", BASH_SOURCE[0] != $0
if [ -n "${BASH_SOURCE:-}" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; then
  IS_SOURCED=1
fi

if [ ${IS_SOURCED} -eq 1 ] && [ "${1:-}" = "--export" ]; then
  export OPENAI_API_KEY="$KEY"
  echo "🔧 Variabila OPENAI_API_KEY a fost exportată în această sesiune de shell."
else
  echo
  echo "ℹ️  Dacă vrei să exporți cheia în ENV pentru sesiunea curentă, rulează:"
  echo "    source tools/configure_openai_key.sh --export"
fi

echo "Gata. Codul tău o poate citi din fișier (recomandat) sau din ENV."
