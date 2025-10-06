#!/usr/bin/env bash
set -euo pipefail

DEST1="$(pwd)/.secrets/openai.key"
DEST2="$HOME/.config/ai_agents/openai.key"

read -rsp "Lipește cheia ta OpenAI (nu se va afișa): " KEY
echo
KEY="$(printf '%s' "$KEY")"  # fără newline

if [ -z "$KEY" ]; then
  echo "Cheie goală. Anulat."
  exit 1
fi

mkdir -p "$(dirname "$DEST1")" "$(dirname "$DEST2")"
printf '%s' "$KEY" > "$DEST1"
printf '%s' "$KEY" > "$DEST2"
chmod 600 "$DEST1" "$DEST2"

echo "Cheia a fost salvată în:"
echo "  - $DEST1"
echo "  - $DEST2"

# Test opțional (dacă curl e disponibil)
if command -v curl >/dev/null 2>&1; then
  echo "Test OpenAI /models..."
  HTTP=$(curl -sS https://api.openai.com/v1/models \
    -H "Authorization: Bearer $KEY" -o /tmp/oa_models.json -w '%{http_code}')
  if [ "$HTTP" = "200" ]; then
    echo "OK: autentificare reușită."
  else
    echo "ATENȚIE: răspuns HTTP $HTTP de la OpenAI (verifică cheia)."
    head -c 200 /tmp/oa_models.json || true
    echo
  fi
fi

echo "Gata. Codul va citi cheia direct din fișier. Nu mai trebuie să exporți variabile."
