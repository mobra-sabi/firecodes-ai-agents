#!/bin/bash

echo "══════════════════════════════════════════════════════════════"
echo "  🛑 Stopping SERP Monitoring Application"
echo "══════════════════════════════════════════════════════════════"
echo ""

# Kill backend
echo "Stopping Backend API..."
pkill -f "uvicorn.*dashboard_api" 2>/dev/null
echo "✓ Backend stopped"

# Kill scheduler
echo "Stopping Scheduler..."
pkill -f "serp_scheduler" 2>/dev/null
echo "✓ Scheduler stopped"

echo ""
echo "✅ All processes stopped"
echo ""

