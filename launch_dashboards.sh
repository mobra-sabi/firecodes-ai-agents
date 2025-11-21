#!/bin/bash

# 🚀 DASHBOARD LAUNCHER
# Deschide toate dashboard-urile în browser

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║         🚀 COMPETITIVE INTELLIGENCE DASHBOARDS 🚀              ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if API is running
if ! ps aux | grep -q "[p]ython.*agent_api"; then
    echo "❌ API Server nu rulează!"
    echo "   Pornește cu: python3 -m uvicorn tools.agent_api:app --host 0.0.0.0 --port 5000 --reload"
    exit 1
fi

echo "✅ API Server: RUNNING"
echo ""

# URLs
MAIN_DASHBOARD="http://localhost:5000/static/competitive_dashboard.html"
FULL_VIEW="http://localhost:5000/static/competitive_dashboard_full.html"
WIDGETS="http://localhost:5000/static/dashboard_widgets.html"

echo "📊 DASHBOARDURI DISPONIBILE:"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "1. 📈 MAIN DASHBOARD (Overview & KPIs)"
echo "   URL: $MAIN_DASHBOARD"
echo "   → Executive overview, KPIs, Top 10, Charts, SWOT"
echo ""
echo "2. 📋 FULL TABLE VIEW (Toți Competitorii)"
echo "   URL: $FULL_VIEW"
echo "   → Tabelă completă, Search, Filters, Export CSV"
echo ""
echo "3. 🎯 INTERACTIVE WIDGETS (Dark Theme)"
echo "   URL: $WIDGETS"
echo "   → Charts avansate, Timeline, Keyword cloud"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Prompt user
echo "Ce vrei să deschizi?"
echo ""
echo "  [1] Main Dashboard"
echo "  [2] Full Table View"
echo "  [3] Interactive Widgets"
echo "  [A] Toate"
echo "  [Q] Quit"
echo ""
read -p "Alege (1/2/3/A/Q): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Deschid Main Dashboard..."
        xdg-open "$MAIN_DASHBOARD" 2>/dev/null || open "$MAIN_DASHBOARD" 2>/dev/null || echo "   Deschide manual: $MAIN_DASHBOARD"
        ;;
    2)
        echo ""
        echo "🚀 Deschid Full Table View..."
        xdg-open "$FULL_VIEW" 2>/dev/null || open "$FULL_VIEW" 2>/dev/null || echo "   Deschide manual: $FULL_VIEW"
        ;;
    3)
        echo ""
        echo "🚀 Deschid Interactive Widgets..."
        xdg-open "$WIDGETS" 2>/dev/null || open "$WIDGETS" 2>/dev/null || echo "   Deschide manual: $WIDGETS"
        ;;
    [Aa])
        echo ""
        echo "🚀 Deschid toate dashboard-urile..."
        sleep 1
        xdg-open "$MAIN_DASHBOARD" 2>/dev/null || open "$MAIN_DASHBOARD" 2>/dev/null || echo "   Deschide manual: $MAIN_DASHBOARD"
        sleep 2
        xdg-open "$FULL_VIEW" 2>/dev/null || open "$FULL_VIEW" 2>/dev/null || echo "   Deschide manual: $FULL_VIEW"
        sleep 2
        xdg-open "$WIDGETS" 2>/dev/null || open "$WIDGETS" 2>/dev/null || echo "   Deschide manual: $WIDGETS"
        ;;
    [Qq])
        echo ""
        echo "👋 Bye!"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ Opțiune invalidă!"
        exit 1
        ;;
esac

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ DASHBOARD DESCHIS!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "💡 TIPS:"
echo "   • Folosește F5 pentru refresh"
echo "   • Verifică Console (F12) pentru debugging"
echo "   • Export CSV din Full Table View"
echo ""
echo "📚 DOCUMENTAȚIE:"
echo "   • DASHBOARD_README.md - Guide complet"
echo "   • DASHBOARD_COMPLETE_SUMMARY.md - Rezumat"
echo ""

