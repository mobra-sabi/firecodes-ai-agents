#!/bin/bash
# Start Vite dev server in background

cd /srv/hf/ai_agents/frontend-pro

# Check if already running
if pgrep -f "vite" > /dev/null; then
    echo "✅ Vite dev server is already running"
    exit 0
fi

# Set PATH for Node.js
export PATH="/home/mobra/.nvm/versions/node/v20.19.5/bin:$PATH"

# Start in background
nohup npm run dev > /tmp/frontend-pro.log 2>&1 &
echo "✅ Vite dev server started (PID: $!)"
echo "📝 Logs: /tmp/frontend-pro.log"
echo "🌐 Access at: http://localhost:3000"

