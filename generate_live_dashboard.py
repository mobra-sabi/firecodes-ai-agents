#!/usr/bin/env python3
"""Generate static HTML dashboard with live data from MongoDB"""

from pymongo import MongoClient
from datetime import datetime

mongo = MongoClient('mongodb://localhost:27017/')
db = mongo.ai_agents_db

# Get statistics
total = db.site_agents.count_documents({})
masters = db.site_agents.count_documents({"agent_type": "master"})
slaves = db.site_agents.count_documents({"agent_type": "slave"})

pipeline = [{"$group": {"_id": None, "total": {"$sum": "$chunks_indexed"}}}]
chunks_result = list(db.site_agents.aggregate(pipeline))
total_chunks = chunks_result[0]["total"] if chunks_result else 0

# Get master agents with slaves
master_list = list(db.site_agents.find({"agent_type": "master"}, {"domain": 1, "chunks_indexed": 1, "created_at": 1}).sort("created_at", -1).limit(15))
for m in master_list:
    m["slave_count"] = db.site_agents.count_documents({"master_agent_id": m["_id"]})

# Get recent slaves
slave_list = list(db.site_agents.find({"agent_type": "slave"}, {"domain": 1, "chunks_indexed": 1, "created_at": 1, "master_agent_id": 1}).sort("created_at", -1).limit(15))
for s in slave_list:
    master = db.site_agents.find_one({"_id": s.get("master_agent_id")}, {"domain": 1})
    s["master_domain"] = master["domain"] if master else "Unknown"

# Generate HTML
html = f"""<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 AI Agent Platform - Live Data</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 32px;
            color: #1f2937;
            margin-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 48px;
            font-weight: bold;
            color: #2563eb;
            margin: 10px 0;
        }}
        .stat-label {{
            font-size: 16px;
            color: #6b7280;
            font-weight: 500;
        }}
        .agents-section {{
            background: white;
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .section-title {{
            font-size: 24px;
            color: #1f2937;
            margin-bottom: 20px;
            font-weight: 600;
        }}
        .agent-card {{
            background: #f3f4f6;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
            border-left: 4px solid #2563eb;
        }}
        .agent-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .agent-domain {{
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
        }}
        .agent-type {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .type-master {{ background: #dbeafe; color: #1e40af; }}
        .type-slave {{ background: #dcfce7; color: #166534; }}
        .agent-stats {{
            display: flex;
            gap: 20px;
            font-size: 14px;
            color: #6b7280;
        }}
        .timestamp {{
            color: #6b7280;
            font-size: 14px;
            margin-top: 10px;
        }}
        .refresh-btn {{
            background: #2563eb;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-left: 15px;
        }}
        .refresh-btn:hover {{ background: #1e40af; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 AI Agent Platform - Live Data
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
            </h1>
            <p style="color: #6b7280; margin-top: 10px;">Direct from MongoDB</p>
            <p class="timestamp">Last updated: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Agenți</div>
                <div class="stat-value">{total}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Master Agents</div>
                <div class="stat-value">{masters}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Slave Agents</div>
                <div class="stat-value">{slaves}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Chunks</div>
                <div class="stat-value">{total_chunks:,}</div>
            </div>
        </div>

        <div class="agents-section">
            <div class="section-title">🏆 Master Agents (Recent {len(master_list)})</div>
"""

for m in master_list:
    created = m.get("created_at").strftime("%d %b %Y") if m.get("created_at") else "N/A"
    html += f"""
            <div class="agent-card">
                <div class="agent-header">
                    <div class="agent-domain">{m['domain']}</div>
                    <span class="agent-type type-master">MASTER</span>
                </div>
                <div class="agent-stats">
                    <span>🧩 {m.get('chunks_indexed', 0):,} chunks</span>
                    <span>👥 {m['slave_count']} slaves</span>
                    <span>📅 {created}</span>
                </div>
            </div>
"""

html += f"""
        </div>

        <div class="agents-section">
            <div class="section-title">👥 Recent Slave Agents ({len(slave_list)})</div>
"""

for s in slave_list:
    created = s.get("created_at").strftime("%d %b %Y") if s.get("created_at") else "N/A"
    html += f"""
            <div class="agent-card">
                <div class="agent-header">
                    <div class="agent-domain">{s['domain']}</div>
                    <span class="agent-type type-slave">SLAVE</span>
                </div>
                <div class="agent-stats">
                    <span>🧩 {s.get('chunks_indexed', 0):,} chunks</span>
                    <span>🔗 Master: {s.get('master_domain', 'N/A')}</span>
                    <span>📅 {created}</span>
                </div>
            </div>
"""

html += """
        </div>
    </div>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""

# Write to file
with open('/srv/hf/ai_agents/static/realtime_dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Dashboard generat: /srv/hf/ai_agents/static/realtime_dashboard.html")
print(f"📊 Statistici:")
print(f"   Total: {total} agenți")
print(f"   Masters: {masters}")
print(f"   Slaves: {slaves}")
print(f"   Chunks: {total_chunks:,}")

