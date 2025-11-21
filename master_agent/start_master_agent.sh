#!/bin/bash

# Master Agent Startup Script

echo "══════════════════════════════════════════════════════════════"
echo "  🎭 Starting Master Agent"
echo "══════════════════════════════════════════════════════════════"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Kill existing process
echo "🛑 Stopping existing Master Agent..."
pkill -f "uvicorn.*agent_main" 2>/dev/null
sleep 2

# Create necessary directories
mkdir -p logs
mkdir -p voice/output

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found"
    exit 1
fi

# Check dependencies
echo "📦 Checking dependencies..."
python3 -c "import fastapi, pymongo, qdrant_client, sentence_transformers" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Some dependencies may be missing. Install with:"
    echo "   pip install fastapi uvicorn pymongo qdrant-client sentence-transformers"
fi

# Start service
echo "🚀 Starting Master Agent on port 5010..."
nohup python3 -m uvicorn agent_main:app --host 0.0.0.0 --port 5010 --reload > logs/startup.log 2>&1 &

PID=$!
echo "✅ Master Agent started with PID: $PID"
echo ""
echo "📍 Endpoints:"
echo "   • Chat: http://localhost:5010/api/chat"
echo "   • Execute: http://localhost:5010/api/execute"
echo "   • State: http://localhost:5010/api/state"
echo "   • Profile: http://localhost:5010/api/profile/{user_id}"
echo "   • WebSocket: ws://localhost:5010/api/ws/{user_id}"
echo ""
echo "📊 Logs:"
echo "   • Actions: $SCRIPT_DIR/logs/agent_actions.log"
echo "   • Startup: $SCRIPT_DIR/logs/startup.log"
echo ""
echo "══════════════════════════════════════════════════════════════"

sleep 3

# Test endpoint
echo "🧪 Testing health endpoint..."
curl -s http://localhost:5010/health | python3 -m json.tool 2>/dev/null || echo "⚠️  Service may still be starting..."

echo ""
echo "✅ Master Agent is running!"


