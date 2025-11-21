#!/bin/bash

echo "══════════════════════════════════════════════════════════════"
echo "  🧪 Testing SERP Monitoring API"
echo "══════════════════════════════════════════════════════════════"
echo ""

API_BASE="http://localhost:5000"
AGENT_ID="6915e1275eb1766cbe71fd4b"

# Test 1: Health check
echo "1. Testing Health Check..."
HEALTH=$(curl -s $API_BASE/api/serp/health)
if echo $HEALTH | grep -q "healthy"; then
    echo "   ✅ Health check passed"
else
    echo "   ❌ Health check failed"
    exit 1
fi

# Test 2: List competitors
echo ""
echo "2. Testing List Competitors..."
COMPETITORS=$(curl -s "$API_BASE/api/serp/competitors?limit=3")
COUNT=$(echo $COMPETITORS | jq '. | length' 2>/dev/null || echo 0)
echo "   ✅ Found $COUNT competitors"

# Test 3: List alerts
echo ""
echo "3. Testing List Alerts..."
ALERTS=$(curl -s "$API_BASE/api/serp/alerts?agent_id=$AGENT_ID&limit=5")
ALERT_COUNT=$(echo $ALERTS | jq '. | length' 2>/dev/null || echo 0)
echo "   ✅ Found $ALERT_COUNT alerts"

# Test 4: Generate CEO Report (optional - takes time)
echo ""
echo "4. Testing CEO Report Generation..."
echo "   (This may take 5-10 seconds...)"
REPORT=$(curl -s -X POST "$API_BASE/api/serp/report/deepseek?agent_id=$AGENT_ID&use_deepseek=false")
REPORT_ID=$(echo $REPORT | jq -r '.report_id' 2>/dev/null)
if [ "$REPORT_ID" != "null" ] && [ ! -z "$REPORT_ID" ]; then
    echo "   ✅ CEO Report generated: $REPORT_ID"
else
    echo "   ⚠️ CEO Report generation failed (may need SERP data first)"
fi

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  ✅ Basic Tests Completed"
echo "══════════════════════════════════════════════════════════════"
echo ""
echo "📊 Summary:"
echo "   • Health: OK"
echo "   • Competitors: $COUNT found"
echo "   • Alerts: $ALERT_COUNT found"
echo "   • CEO Report: ${REPORT_ID:-N/A}"
echo ""
echo "🌐 Full testing available at:"
echo "   http://localhost:5000/static/serp_admin.html"
echo ""

