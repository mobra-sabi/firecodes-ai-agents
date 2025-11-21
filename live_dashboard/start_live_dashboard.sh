#!/bin/bash
###############################################################################
# 🌐 Start Live Dashboard - Real-time monitoring pentru toate nodurile AI
###############################################################################

cd /srv/hf/ai_agents/live_dashboard

echo "🌐 Starting Live Dashboard on port 6000..."

# Kill existing process
pkill -f "uvicorn.*backend_live" 2>/dev/null
sleep 2

# Start backend
nohup python3 backend_live.py > /srv/hf/ai_agents/logs/live_dashboard.log 2>&1 &

sleep 3

# Check if started
if lsof -i :6000 > /dev/null 2>&1; then
    echo "✅ Live Dashboard started successfully!"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "🌐 LIVE DASHBOARD"
    echo "═══════════════════════════════════════════════════════════════"
    echo "URL:        http://localhost:6000"
    echo "WebSocket:  ws://localhost:6000/ws"
    echo "Logs:       tail -f /srv/hf/ai_agents/logs/live_dashboard.log"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "📊 Features:"
    echo "   • Real-time monitoring pentru toate nodurile"
    echo "   • Live updates prin WebSocket"
    echo "   • Interacțiuni în timp real"
    echo "   • Status GPU cluster"
    echo "   • Monitorizare vLLM, MongoDB, Qdrant"
    echo ""
    echo "🔄 Dashboard-ul se actualizează automat la fiecare 5 secunde"
    echo ""
else
    echo "❌ Failed to start Live Dashboard"
    echo "Check logs: tail -f /srv/hf/ai_agents/logs/live_dashboard.log"
    exit 1
fi


