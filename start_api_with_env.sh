#!/bin/bash
################################################################################
# AI Agents Platform - API Startup Script
# Starts the API with all required environment variables
################################################################################

echo "================================================================================"
echo "🚀 Starting AI Agents Platform API"
echo "================================================================================"
echo ""

# Load API keys
export DEEPSEEK_API_KEY=$(cat /srv/hf/ai_agents/.secrets/deepseek.key 2>/dev/null || echo "")
export OPENAI_API_KEY=$(cat /srv/hf/ai_agents/.secrets/openai.key 2>/dev/null || echo "")
export BRAVE_API_KEY=$(cat /srv/hf/ai_agents/.secrets/brave.key 2>/dev/null || echo "")

# Database URLs
export MONGODB_URI="mongodb://localhost:27017"
export QDRANT_URL="http://localhost:6333"

# Optional: Local GPU LLM
export QWEN_BASE_URL="http://localhost:9304/v1"
export QWEN_MODEL="qwen2.5"

# Verify critical keys
echo "📋 Checking configuration..."
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "   ⚠️  DeepSeek API key not found (will use OpenAI fallback)"
else
    echo "   ✅ DeepSeek API key loaded"
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "   ⚠️  OpenAI API key not found"
else
    echo "   ✅ OpenAI API key loaded"
fi

if [ -z "$BRAVE_API_KEY" ]; then
    echo "   ⚠️  Brave API key not found"
else
    echo "   ✅ Brave API key loaded"
fi

echo ""
echo "🔧 Starting API server..."

# Change to tools directory
cd /srv/hf/ai_agents/tools

# Kill any existing API process
pkill -f agent_api.py 2>/dev/null
pkill -f "uvicorn.*agent_api" 2>/dev/null

# Start API with uvicorn in background
nohup uvicorn agent_api:app --host 0.0.0.0 --port 5000 --workers 1 > /tmp/api.log 2>&1 &

# Get PID
API_PID=$!

echo "   ✅ API started (PID: $API_PID)"
echo ""

# Wait a moment for API to initialize
sleep 5

# Test if API is responding
if curl -s http://100.66.157.27:5000/api/system/health > /dev/null 2>&1; then
    echo "✅ API is responding!"
    echo ""
    echo "================================================================================"
    echo "🎉 AI AGENTS PLATFORM IS RUNNING!"
    echo "================================================================================"
    echo ""
    echo "Access points:"
    echo "  • Professional Panel: http://100.66.157.27:5000/static/professional_control_panel.html"
    echo "  • Production Dashboard: http://100.66.157.27:5000/static/production_dashboard.html"
    echo "  • API Documentation: http://100.66.157.27:5000/docs"
    echo ""
    echo "Logs:"
    echo "  • tail -f /tmp/api.log"
    echo ""
    echo "To stop:"
    echo "  • pkill -f agent_api.py"
    echo ""
    echo "================================================================================"
else
    echo "⚠️  API may still be starting..."
    echo "   Check logs: tail -f /tmp/api.log"
fi

