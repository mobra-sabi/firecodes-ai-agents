#!/bin/bash
# Script pentru pornire Cloudflare Tunnel pentru SERP Monitoring App

echo "══════════════════════════════════════════════════════════════"
echo "  🌐 Starting Cloudflare Tunnel for SERP Monitoring"
echo "══════════════════════════════════════════════════════════════"
echo ""

# Oprește tunelurile existente
pkill -f "cloudflared.*5000" 2>/dev/null
sleep 1

# Pornește tunel pentru SERP Monitoring (port 5000)
echo "Starting tunnel for SERP Monitoring (port 5000)..."
nohup cloudflared tunnel --url http://localhost:5000 > /srv/hf/ai_agents/logs/cloudflare_tunnel_serp.log 2>&1 &
TUNNEL_PID=$!

echo "✅ Tunnel started (PID: $TUNNEL_PID)"
echo ""
echo "📋 Logs: tail -f /srv/hf/ai_agents/logs/cloudflare_tunnel_serp.log"
echo ""
echo "⚠️  Notă: URL-ul tunelului va apărea în loguri după câteva secunde"
echo "   Rulează: tail -f /srv/hf/ai_agents/logs/cloudflare_tunnel_serp.log | grep -i 'trycloudflare'"
echo ""

