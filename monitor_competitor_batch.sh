#!/bin/bash
# Monitor pentru batch competitor agents

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  📊 COMPETITOR AGENTS BATCH - MONITOR                                ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Check dacă rulează
if [ -f competitor_batch.pid ]; then
    PID=$(cat competitor_batch.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Batch RUNNING (PID: $PID)"
    else
        echo "❌ Batch STOPPED"
    fi
else
    echo "⚠️  No PID file found"
fi

echo ""
echo "📋 PROGRESS (last 30 lines):"
echo "─────────────────────────────────────────────────────────────────────"
tail -30 competitor_batch.log | grep -E "Creating agent|✅|❌|Score:|BATCH|Master"
echo ""
echo "─────────────────────────────────────────────────────────────────────"
echo ""
echo "💡 Commands:"
echo "   • Full log: tail -f competitor_batch.log"
echo "   • Stop: kill \$(cat competitor_batch.pid)"
echo "   • Check API: curl http://localhost:5000/agents/6910ef1d112d6bca72be0622/slave-agents"
