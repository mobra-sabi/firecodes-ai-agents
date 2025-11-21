#!/bin/bash

echo "══════════════════════════════════════════════════════════════"
echo "  🚀 Starting SERP Monitoring Application"
echo "══════════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if MongoDB is running
echo -n "Checking MongoDB... "
if mongosh --eval "db.version()" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${YELLOW}⚠ Not running. Starting MongoDB...${NC}"
    sudo systemctl start mongod
    sleep 2
fi

# Create logs directory
mkdir -p logs

# Kill existing processes
echo ""
echo "Stopping existing processes..."
pkill -f "uvicorn.*dashboard_api" 2>/dev/null
pkill -f "serp_scheduler" 2>/dev/null
sleep 2

# Start Backend API
echo ""
echo "Starting Backend API..."
cd /srv/hf/ai_agents/agent_platform/backend
nohup uvicorn dashboard_api:app --host 0.0.0.0 --port 5000 --reload > /srv/hf/ai_agents/serp_monitoring_app/logs/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"

# Wait for backend to be ready
echo -n "Waiting for backend to be ready"
for i in {1..10}; do
    if curl -s http://localhost:5000/api/serp/health > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Start Scheduler (optional - commented by default)
# Uncomment to enable daily monitoring
# echo ""
# echo "Starting Scheduler (daily monitoring)..."
# cd /srv/hf/ai_agents/serp_monitoring_app/backend
# nohup python3 serp_scheduler.py --mode daemon > ../logs/scheduler.log 2>&1 &
# SCHEDULER_PID=$!
# echo -e "${GREEN}✓ Scheduler started (PID: $SCHEDULER_PID)${NC}"

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  ✅ Application Started Successfully!"
echo "══════════════════════════════════════════════════════════════"
echo ""
echo "📍 Access Points:"
echo "   • Admin Dashboard: http://localhost:5000/static/serp_admin.html"
echo "   • API Docs:        http://localhost:5000/docs"
echo "   • Health Check:    http://localhost:5000/api/serp/health"
echo ""
echo "📊 Stats:"
echo "   • Backend PID: $BACKEND_PID"
# echo "   • Scheduler PID: $SCHEDULER_PID"
echo ""
echo "📋 Commands:"
echo "   • View logs:  tail -f logs/backend.log"
echo "   • Stop all:   ./stop.sh"
echo "   • Test API:   ./test.sh"
echo ""
echo "══════════════════════════════════════════════════════════════"

