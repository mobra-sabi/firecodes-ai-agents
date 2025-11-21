#!/bin/bash

echo "🛑 Oprește UI-ul pentru AI Agents Platform..."

# Oprește serverul HTTP pe portul 8080
if fuser -k 8080/tcp 2>/dev/null; then
    echo "✅ Serverul UI a fost oprit"
else
    echo "ℹ️  Serverul UI nu rulează pe portul 8080"
fi

# Oprește și serverul backend dacă este specificat
if [ "$1" = "--all" ]; then
    echo "🛑 Oprește și serverul backend..."
    ./stop_server.sh
fi

echo "✅ Gata!"
