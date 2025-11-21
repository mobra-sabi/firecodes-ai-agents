"""
🎯 DASHBOARD API ENDPOINTS
Endpoint-uri suplimentare pentru dashboard

Adaugă în agent_api.py pentru funcționalitate completă
"""

from flask import jsonify, request
from datetime import datetime
import json

# ============================================================================
# DASHBOARD ANALYTICS ENDPOINTS
# ============================================================================

@app.route('/api/dashboard/overview', methods=['GET'])
def dashboard_overview():
    """
    Dashboard Overview - date generale sistem
    """
    try:
        # Total agenți
        total_agents = agents_collection.count_documents({"validation_passed": True, "status": "ready"})
        
        # Agenți master vs slave
        master_agents = agents_collection.count_documents({
            "validation_passed": True,
            "agent_type": {"$ne": "slave"}
        })
        slave_agents = agents_collection.count_documents({
            "validation_passed": True,
            "agent_type": "slave"
        })
        
        # Total competitori descoperiți
        total_competitors = 0
        agents_with_competitors = agents_collection.find({
            "competitive_discovery": {"$exists": True}
        })
        
        for agent in agents_with_competitors:
            if agent.get("competitive_discovery", {}).get("discovered_competitors"):
                total_competitors += len(agent["competitive_discovery"]["discovered_competitors"])
        
        # Total keywords monitorizate
        total_keywords = 0
        agents_with_analysis = agents_collection.find({
            "competitive_analysis": {"$exists": True}
        })
        
        for agent in agents_with_analysis:
            subdomains = agent.get("competitive_analysis", {}).get("analysis_data", {}).get("subdomains", [])
            for subdomain in subdomains:
                total_keywords += len(subdomain.get("keywords", []))
        
        # Activitate recentă
        recent_agents = list(agents_collection.find(
            {"validation_passed": True},
            {"domain": 1, "created_at": 1, "agent_type": 1}
        ).sort("created_at", -1).limit(10))
        
        return jsonify({
            "ok": True,
            "overview": {
                "total_agents": total_agents,
                "master_agents": master_agents,
                "slave_agents": slave_agents,
                "total_competitors": total_competitors,
                "total_keywords": total_keywords,
                "recent_activity": [
                    {
                        "domain": a.get("domain"),
                        "type": a.get("agent_type", "master"),
                        "created_at": a.get("created_at", datetime.now()).isoformat()
                    }
                    for a in recent_agents
                ]
            }
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/dashboard/analytics/<agent_id>', methods=['GET'])
def dashboard_agent_analytics(agent_id):
    """
    Analytics detaliate pentru un agent specific
    """
    try:
        from bson import ObjectId
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        
        if not agent:
            return jsonify({"ok": False, "error": "Agent not found"}), 404
        
        # Competitive discovery stats
        discovery = agent.get("competitive_discovery", {})
        competitors = discovery.get("discovered_competitors", [])
        
        # Score distribution
        score_distribution = {
            "high": len([c for c in competitors if c.get("score", 0) > 60]),
            "medium": len([c for c in competitors if 45 <= c.get("score", 0) <= 60]),
            "low": len([c for c in competitors if c.get("score", 0) < 45])
        }
        
        # Subdomain coverage
        subdomain_stats = []
        for subdomain_name, subdomain_data in discovery.get("discovery_by_subdomain", {}).items():
            subdomain_stats.append({
                "name": subdomain_name,
                "competitors_count": len(subdomain_data.get("competitors", [])),
                "keywords_count": len(subdomain_data.get("keywords", []))
            })
        
        # Slave agents stats
        slave_agents = list(agents_collection.find({
            "master_agent_id": str(agent_id),
            "agent_type": "slave"
        }, {"domain": 1, "created_at": 1, "validation_passed": 1}))
        
        return jsonify({
            "ok": True,
            "analytics": {
                "domain": agent.get("domain"),
                "total_competitors": len(competitors),
                "score_distribution": score_distribution,
                "subdomain_stats": subdomain_stats,
                "slave_agents": {
                    "total": len(slave_agents),
                    "active": len([s for s in slave_agents if s.get("validation_passed")]),
                    "list": [
                        {
                            "domain": s.get("domain"),
                            "status": "active" if s.get("validation_passed") else "pending"
                        }
                        for s in slave_agents
                    ]
                },
                "last_updated": discovery.get("discovery_date", datetime.now()).isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/dashboard/competitor-details/<agent_id>/<domain>', methods=['GET'])
def competitor_details(agent_id, domain):
    """
    Detalii complete pentru un competitor specific
    """
    try:
        from bson import ObjectId
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        
        if not agent:
            return jsonify({"ok": False, "error": "Agent not found"}), 404
        
        # Find competitor in discovery data
        competitors = agent.get("competitive_discovery", {}).get("discovered_competitors", [])
        competitor = next((c for c in competitors if c.get("domain") == domain), None)
        
        if not competitor:
            return jsonify({"ok": False, "error": "Competitor not found"}), 404
        
        # Check if competitor is also an agent
        competitor_agent = agents_collection.find_one({
            "domain": domain,
            "agent_type": "slave",
            "master_agent_id": str(agent_id)
        })
        
        # Get subdomain appearances
        discovery_by_subdomain = agent.get("competitive_discovery", {}).get("discovery_by_subdomain", {})
        appearances = []
        
        for subdomain_name, subdomain_data in discovery_by_subdomain.items():
            for comp in subdomain_data.get("competitors", []):
                if comp.get("domain") == domain:
                    appearances.append({
                        "subdomain": subdomain_name,
                        "position": comp.get("position"),
                        "keyword": comp.get("keyword", "")
                    })
        
        return jsonify({
            "ok": True,
            "competitor": {
                "domain": competitor.get("domain"),
                "score": competitor.get("score"),
                "appearances_count": competitor.get("appearances_count"),
                "avg_position": competitor.get("avg_position"),
                "is_agent": competitor_agent is not None,
                "agent_id": str(competitor_agent["_id"]) if competitor_agent else None,
                "appearances": appearances,
                "first_seen": competitor.get("first_seen", datetime.now()).isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/dashboard/export/<agent_id>/<format>', methods=['GET'])
def export_dashboard_data(agent_id, format):
    """
    Export date în format CSV sau JSON
    format: 'csv' | 'json'
    """
    try:
        from bson import ObjectId
        import csv
        from io import StringIO
        
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        
        if not agent:
            return jsonify({"ok": False, "error": "Agent not found"}), 404
        
        competitors = agent.get("competitive_discovery", {}).get("discovered_competitors", [])
        
        if format == 'csv':
            # Generate CSV
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['Rank', 'Domain', 'Score', 'Appearances', 'Avg Position', 'Is Agent'])
            
            for i, comp in enumerate(competitors, 1):
                writer.writerow([
                    i,
                    comp.get("domain"),
                    round(comp.get("score", 0), 2),
                    comp.get("appearances_count", 0),
                    round(comp.get("avg_position", 0), 2) if comp.get("avg_position") else '-',
                    'Yes' if comp.get("is_agent") else 'No'
                ])
            
            output.seek(0)
            return output.getvalue(), 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename=competitors_{agent_id}.csv'
            }
            
        elif format == 'json':
            # Generate JSON
            export_data = {
                "agent_domain": agent.get("domain"),
                "export_date": datetime.now().isoformat(),
                "total_competitors": len(competitors),
                "competitors": [
                    {
                        "rank": i + 1,
                        "domain": c.get("domain"),
                        "score": c.get("score"),
                        "appearances": c.get("appearances_count"),
                        "avg_position": c.get("avg_position")
                    }
                    for i, c in enumerate(competitors)
                ]
            }
            
            return jsonify(export_data), 200, {
                'Content-Type': 'application/json',
                'Content-Disposition': f'attachment; filename=competitors_{agent_id}.json'
            }
        
        else:
            return jsonify({"ok": False, "error": "Invalid format. Use 'csv' or 'json'"}), 400
            
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================================
# COMPARATIVE ANALYSIS ENDPOINTS
# ============================================================================

@app.route('/api/dashboard/compare/<agent1_id>/<agent2_id>', methods=['GET'])
def compare_agents(agent1_id, agent2_id):
    """
    Compară doi agenți (useful pentru master vs competitor agent)
    """
    try:
        from bson import ObjectId
        
        agent1 = agents_collection.find_one({"_id": ObjectId(agent1_id)})
        agent2 = agents_collection.find_one({"_id": ObjectId(agent2_id)})
        
        if not agent1 or not agent2:
            return jsonify({"ok": False, "error": "One or both agents not found"}), 404
        
        # Extract competitive data
        def extract_stats(agent):
            return {
                "domain": agent.get("domain"),
                "total_competitors": len(agent.get("competitive_discovery", {}).get("discovered_competitors", [])),
                "total_keywords": sum(
                    len(sd.get("keywords", []))
                    for sd in agent.get("competitive_analysis", {}).get("analysis_data", {}).get("subdomains", [])
                ),
                "avg_competitor_score": sum(
                    c.get("score", 0)
                    for c in agent.get("competitive_discovery", {}).get("discovered_competitors", [])
                ) / max(len(agent.get("competitive_discovery", {}).get("discovered_competitors", [])), 1)
            }
        
        return jsonify({
            "ok": True,
            "comparison": {
                "agent1": extract_stats(agent1),
                "agent2": extract_stats(agent2)
            }
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================================
# INSTRUCTIONS PENTRU INTEGRARE
# ============================================================================

"""
📋 PENTRU A INTEGRA ACESTE ENDPOINT-URI:

1. Deschide agent_api.py
2. Adaugă aceste funcții după celelalte route-uri
3. Restart Flask server
4. Endpoint-urile vor fi disponibile automat

🌐 EXEMPLE DE USAGE:

GET /api/dashboard/overview
→ Date generale sistem

GET /api/dashboard/analytics/6910ef1d112d6bca72be0622
→ Analytics pentru tehnica-antifoc.ro

GET /api/dashboard/competitor-details/6910ef1d112d6bca72be0622/ignisprotection.ro
→ Detalii competitor specific

GET /api/dashboard/export/6910ef1d112d6bca72be0622/csv
→ Export CSV

GET /api/dashboard/compare/6910ef1d112d6bca72be0622/<competitor_agent_id>
→ Comparație între doi agenți
"""

