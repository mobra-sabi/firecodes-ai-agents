#!/bin/bash

echo "🚀 Pornesc UI-ul pentru AI Agents Platform..."

# Verifică dacă serverul backend rulează
if ! curl -s http://localhost:8083/health > /dev/null; then
    echo "❌ Serverul backend nu rulează. Pornesc serverul..."
    ./start_server.sh
    sleep 3
fi

# Verifică dacă avem Python pentru a porni un server HTTP simplu
if command -v python3 &> /dev/null; then
    echo "✅ Pornesc serverul HTTP pentru UI..."
    echo "🌐 UI-ul este disponibil la: http://localhost:8080"
    echo "📱 Deschide browserul și navighează la adresa de mai sus"
    echo ""
    echo "🔧 Pentru a opri UI-ul, apasă Ctrl+C"
    echo ""
    
    # Pornește serverul HTTP pe portul 8080
    cd /home/mobra/ai_agents
    python3 -m http.server 8080
elif command -v python &> /dev/null; then
    echo "✅ Pornesc serverul HTTP pentru UI..."
    echo "🌐 UI-ul este disponibil la: http://localhost:8080"
    echo "📱 Deschide browserul și navighează la adresa de mai sus"
    echo ""
    echo "🔧 Pentru a opri UI-ul, apasă Ctrl+C"
    echo ""
    
    # Pornește serverul HTTP pe portul 8080
    cd /home/mobra/ai_agents
    python -m SimpleHTTPServer 8080
else
    echo "❌ Python nu este instalat. Te rog instalează Python pentru a rula UI-ul."
    echo "💡 Alternativ, poți deschide direct fișierul ui_interface_with_sessions.html în browser"
    exit 1
fi
