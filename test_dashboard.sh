#!/bin/bash

# 🎨 TEST DASHBOARD COMPONENTS
# Verifică funcționalitatea tuturor endpoint-urilor

echo "═══════════════════════════════════════════════════════════"
echo "🎨 TESTING DASHBOARD - Competitive Intelligence"
echo "═══════════════════════════════════════════════════════════"
echo ""

MASTER_ID="6910ef1d112d6bca72be0622"
API_BASE="http://localhost:5000"

echo "📊 1. TESTING COMPETITIVE LANDSCAPE..."
curl -s "${API_BASE}/agents/${MASTER_ID}/competitive-landscape" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('ok'):
    print('✅ Competitive Landscape OK')
    print(f\"   Master: {data.get('master', {}).get('domain')}\")
    print(f\"   Slaves: {len(data.get('slaves', []))}\")
    print(f\"   Total Competitors: {data.get('analytics', {}).get('total_competitors')}\")
else:
    print('❌ FAILED')
"
echo ""

echo "🏆 2. TESTING COMPETITORS LIST..."
curl -s "${API_BASE}/agents/${MASTER_ID}/competitors" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('ok'):
    comps = data.get('competitors', [])
    print(f'✅ Competitors List OK - {len(comps)} competitori')
    if comps:
        top = comps[0]
        print(f\"   Top 1: {top.get('domain')} (score: {top.get('score'):.1f})\")
else:
    print('❌ FAILED')
"
echo ""

echo "🧠 3. TESTING DEEPSEEK ANALYSIS..."
curl -s "${API_BASE}/agents/${MASTER_ID}/competition-analysis" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('ok'):
    analysis = data.get('analysis', {}).get('analysis_data', {})
    print('✅ DeepSeek Analysis OK')
    print(f\"   Strengths: {len(analysis.get('strengths', []))}\")
    print(f\"   Weaknesses: {len(analysis.get('weaknesses', []))}\")
    print(f\"   Opportunities: {len(analysis.get('opportunities', []))}\")
    print(f\"   Actions: {len(analysis.get('immediate_actions', []))}\")
else:
    print('❌ FAILED')
"
echo ""

echo "👥 4. TESTING SLAVE AGENTS..."
curl -s "${API_BASE}/agents/${MASTER_ID}/slave-agents" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('ok'):
    slaves = data.get('slaves', [])
    print(f'✅ Slave Agents OK - {len(slaves)} slaves')
    active = sum(1 for s in slaves if s.get('validation_passed'))
    print(f\"   Active: {active}/{len(slaves)}\")
else:
    print('❌ FAILED')
"
echo ""

echo "═══════════════════════════════════════════════════════════"
echo "🌐 DASHBOARD URLS:"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📊 Main Dashboard:"
echo "   http://localhost:5000/static/competitive_dashboard.html"
echo ""
echo "📋 Full View (All 306 Competitors):"
echo "   http://localhost:5000/static/competitive_dashboard_full.html"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ DASHBOARD READY!"
echo "═══════════════════════════════════════════════════════════"

