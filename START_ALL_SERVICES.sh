#!/bin/bash

echo "🚀 STARTING ALL AI AGENTS SERVICES..."
echo ""

# Kill existing processes
echo "⏹️  Stopping existing services..."
pkill -f "agent_main"
pkill -f "backend_live"
pkill -f "dashboard_api"
sleep 2

# Start Master Agent (5010)
echo "▶️  Starting Master Agent (5010)..."
cd /srv/hf/ai_agents/master_agent
nohup python3 -m uvicorn agent_main:app --host 0.0.0.0 --port 5010 --reload > logs/agent.log 2>&1 &
sleep 3

# Start Live Dashboard (6000)
echo "▶️  Starting Live Dashboard (6000)..."
cd /srv/hf/ai_agents/live_dashboard
nohup python3 backend_live.py > /srv/hf/ai_agents/logs/live_dashboard.log 2>&1 &
sleep 3

# Start Auto-Learning UI (5001)
echo "▶️  Starting Auto-Learning UI (5001)..."
cd /srv/hf/ai_agents/auto_learning_ui
nohup python3 backend_api.py > /srv/hf/ai_agents/logs/auto_learning_ui.log 2>&1 &
sleep 2

# Start SERP App (5000)
echo "▶️  Starting SERP Monitoring App (5000)..."
cd /srv/hf/ai_agents/serp_monitoring_app
bash start.sh > /dev/null 2>&1

echo ""
echo "✅ ALL SERVICES STARTED!"
echo ""
echo "📊 STATUS:"
echo "   Master Agent:        http://localhost:5010"
echo "   Live Dashboard:      http://localhost:6000"
echo "   Auto-Learning UI:    http://localhost:5001"
echo "   SERP App:            http://localhost:5000"
echo "   Agent API:           http://localhost:8000"
echo "   Agent Platform UI:   http://localhost:4000"
echo ""
echo "🧪 TEST:"
echo "   curl http://localhost:5010/api/state"
echo "   curl http://localhost:6000/api/nodes"
echo ""
