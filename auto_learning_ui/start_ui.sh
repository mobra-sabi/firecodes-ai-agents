#!/bin/bash
# 🎨 Start Auto-Learning UI Dashboard

cd /srv/hf/ai_agents/auto_learning_ui

echo "══════════════════════════════════════════════════════════════"
echo "  🎨 Starting Auto-Learning Dashboard"
echo "══════════════════════════════════════════════════════════════"
echo ""

# Check if port 5001 is available
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 5001 is already in use. Killing existing process..."
    kill -9 $(lsof -t -i:5001) 2>/dev/null
    sleep 2
fi

# Start FastAPI server
echo "🚀 Starting FastAPI server on port 5001..."
nohup python3 -m uvicorn backend_api:app --host 0.0.0.0 --port 5001 --reload > /srv/hf/ai_agents/logs/ui.log 2>&1 &
UI_PID=$!

echo "✅ Dashboard started (PID: $UI_PID)"
echo ""
echo "📍 Access Dashboard:"
echo "   http://localhost:5001"
echo ""
echo "📋 Commands:"
echo "   • View logs:  tail -f /srv/hf/ai_agents/logs/ui.log"
echo "   • Stop:       kill $UI_PID"
echo ""
echo "══════════════════════════════════════════════════════════════"


