#!/bin/bash

echo "🚀 Pornesc AI Agents Platform (versiunea simplificată)..."

# Verifică dacă backend-ul rulează
if ! curl -s http://localhost:8083/health > /dev/null; then
    echo "📡 Pornesc backend-ul..."
    ./start_server.sh
    sleep 3
else
    echo "✅ Backend-ul rulează deja"
fi

# Verifică dacă UI-ul rulează
if ! curl -s http://localhost:8080 > /dev/null; then
    echo "🌐 Pornesc UI-ul..."
    python3 -m http.server 8080 &
    sleep 2
else
    echo "✅ UI-ul rulează deja"
fi

echo ""
echo "🎉 AI Agents Platform este gata!"
echo ""
echo "📱 Accesează aplicația la:"
echo "   http://localhost:8080/ui_simple.html"
echo ""
echo "🔧 Pentru a opri totul:"
echo "   ./stop_all.sh"
echo ""
echo "📊 Status:"
echo "   Backend: http://localhost:8083/health"
echo "   UI: http://localhost:8080"
echo ""
echo "💡 Dacă ai probleme cu UI-ul original, folosește versiunea simplificată!"
