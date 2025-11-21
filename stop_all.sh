#!/bin/bash

echo "🛑 Oprește AI Agents Platform..."

# Oprește UI-ul
if fuser -k 8080/tcp 2>/dev/null; then
    echo "✅ UI-ul a fost oprit"
else
    echo "ℹ️  UI-ul nu rulează pe portul 8080"
fi

# Oprește backend-ul
if fuser -k 8083/tcp 2>/dev/null; then
    echo "✅ Backend-ul a fost oprit"
else
    echo "ℹ️  Backend-ul nu rulează pe portul 8083"
fi

echo "✅ Totul a fost oprit!"
