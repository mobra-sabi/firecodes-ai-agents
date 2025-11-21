#!/bin/bash

echo "="
echo "🏭 CONTINUOUS INDUSTRY INDEXER - LAUNCHER"
echo "="*80

# Kill existing processes
pkill -f "python3 -m http.server 8888" 2>/dev/null
pkill -f "continuous_industry_indexer.py" 2>/dev/null

# Start HTTP server for monitoring
cd /srv/hf/ai_agents
python3 -m http.server 8888 --bind 0.0.0.0 > /dev/null 2>&1 &
SERVER_PID=$!

echo "✅ HTTP Server started (PID: $SERVER_PID)"
echo "📍 Monitoring URL: http://localhost:8888/static/live_indexing_monitor.html"
echo ""

# Wait a bit
sleep 2

# Start indexer with stats export
python3 continuous_industry_indexer.py 2>&1 | tee /tmp/indexing.log &
INDEXER_PID=$!

echo "✅ Indexer started (PID: $INDEXER_PID)"
echo ""
echo "🌐 OPEN IN BROWSER:"
echo "   http://localhost:8888/static/live_indexing_monitor.html"
echo ""
echo "📊 Or from network:"
IP=$(hostname -I | awk '{print $1}')
echo "   http://$IP:8888/static/live_indexing_monitor.html"
echo ""
echo "⏹️  To stop: pkill -f continuous_industry_indexer"
echo "="*80

# Keep script running
wait $INDEXER_PID
