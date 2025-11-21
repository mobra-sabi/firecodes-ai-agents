#!/usr/bin/env python3
"""
📊 STRATEGIC REPORT GENERATOR
Generează rapoarte strategice comprehensive pentru management

Usage:
    python3 generate_strategic_report.py <agent_id>
    python3 generate_strategic_report.py 6910ef1d112d6bca72be0622
"""

import sys
import requests
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient

API_BASE = "http://localhost:5000"
MONGO_URI = "mongodb://localhost:27017/"


def get_mongo_data(agent_id):
    """Get comprehensive data from API (not direct MongoDB)"""
    try:
        response = requests.get(f"{API_BASE}/api/agents")
        agents = response.json()
        
        # Find agent by ID
        for agent in agents:
            if agent.get('_id') == agent_id:
                return agent
        
        return None
    except Exception as e:
        print(f"❌ Error fetching agent data: {e}")
        return None


def get_api_data(agent_id):
    """Get data from API endpoints"""
    result = {
        'landscape': {},
        'competitors': {'competitors': []},
        'analysis': {'analysis': {'analysis_data': {}}},
        'slaves': {'slaves': []}
    }
    
    try:
        # Try landscape
        try:
            r = requests.get(f"{API_BASE}/agents/{agent_id}/competitive-landscape", timeout=10)
            if r.status_code == 200 and r.text.strip():
                result['landscape'] = r.json()
        except:
            print("⚠️  Landscape endpoint not available")
        
        # Try competitors
        try:
            r = requests.get(f"{API_BASE}/agents/{agent_id}/competitors", timeout=10)
            if r.status_code == 200 and r.text.strip():
                result['competitors'] = r.json()
        except:
            print("⚠️  Competitors endpoint not available")
        
        # Try analysis
        try:
            r = requests.get(f"{API_BASE}/agents/{agent_id}/competition-analysis", timeout=10)
            if r.status_code == 200 and r.text.strip():
                result['analysis'] = r.json()
        except:
            print("⚠️  Analysis endpoint not available")
        
        # Try slaves
        try:
            r = requests.get(f"{API_BASE}/agents/{agent_id}/slave-agents", timeout=10)
            if r.status_code == 200 and r.text.strip():
                result['slaves'] = r.json()
        except:
            print("⚠️  Slaves endpoint not available")
        
        return result
        
    except Exception as e:
        print(f"❌ Error fetching API data: {e}")
        return result


def generate_html_report(agent_id, mongo_data, api_data):
    """Generate comprehensive HTML report"""
    
    agent_domain = mongo_data.get('domain', 'Unknown')
    competitors = api_data['competitors'].get('competitors', [])
    analysis_data = api_data['analysis'].get('analysis', {}).get('analysis_data', {})
    slaves = api_data['slaves'].get('slaves', [])
    
    # Calculate metrics
    total_competitors = len(competitors)
    avg_score = sum(c.get('score', 0) for c in competitors) / max(total_competitors, 1)
    high_score_count = len([c for c in competitors if c.get('score', 0) > 60])
    total_keywords = sum(c.get('appearances_count', 0) for c in competitors)
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Strategic Report - {agent_domain}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 40px 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 30px rgba(0,0,0,0.1);
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 50px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 42px;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 18px;
            opacity: 0.9;
        }}
        
        .header .meta {{
            margin-top: 20px;
            font-size: 14px;
            opacity: 0.8;
        }}
        
        .content {{
            padding: 50px;
        }}
        
        .section {{
            margin-bottom: 50px;
        }}
        
        .section-title {{
            font-size: 28px;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .section-title i {{
            font-size: 32px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
        }}
        
        .metric-value {{
            font-size: 48px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .metric-label {{
            font-size: 16px;
            opacity: 0.9;
        }}
        
        .list-section {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 25px;
        }}
        
        .list-section h3 {{
            font-size: 20px;
            margin-bottom: 15px;
            color: #667eea;
        }}
        
        .list-section ul {{
            list-style: none;
        }}
        
        .list-section li {{
            padding: 12px;
            margin-bottom: 8px;
            background: white;
            border-left: 4px solid #667eea;
            border-radius: 5px;
        }}
        
        .list-section.strengths li {{ border-left-color: #10b981; }}
        .list-section.weaknesses li {{ border-left-color: #ef4444; }}
        .list-section.opportunities li {{ border-left-color: #3b82f6; }}
        .list-section.threats li {{ border-left-color: #f59e0b; }}
        .list-section.actions li {{ border-left-color: #8b5cf6; }}
        
        .competitor-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        .competitor-table th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        
        .competitor-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .competitor-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .score-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 13px;
        }}
        
        .score-high {{ background: #dcfce7; color: #16a34a; }}
        .score-medium {{ background: #fef3c7; color: #d97706; }}
        .score-low {{ background: #fee2e2; color: #dc2626; }}
        
        .footer {{
            background: #2d3748;
            color: white;
            padding: 30px 50px;
            text-align: center;
        }}
        
        .footer p {{
            margin: 5px 0;
        }}
        
        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-chart-line"></i> RAPORT STRATEGIC</h1>
            <div class="subtitle">Analiza Competitive Intelligence</div>
            <div class="meta">
                <strong>{agent_domain}</strong> | 
                Generat: {datetime.now().strftime("%d %B %Y, %H:%M")}
            </div>
        </div>
        
        <div class="content">
            <!-- Executive Summary -->
            <div class="section">
                <h2 class="section-title">
                    <i class="fas fa-file-alt"></i>
                    Executive Summary
                </h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{total_competitors}</div>
                        <div class="metric-label">Competitori Identificați</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{high_score_count}</div>
                        <div class="metric-label">Competitori Majori (>60)</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{len(slaves)}</div>
                        <div class="metric-label">Slave Agents Creați</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{avg_score:.1f}</div>
                        <div class="metric-label">Score Mediu Competitori</div>
                    </div>
                </div>
                <p style="font-size: 16px; line-height: 1.8; color: #555;">
                    Acest raport prezintă o analiză comprehensivă a peisajului competitiv pentru 
                    <strong>{agent_domain}</strong>. Am identificat <strong>{total_competitors}</strong> competitori
                    activi pe piață, din care <strong>{high_score_count}</strong> sunt considerați competitori majori
                    cu un nivel ridicat de competitivitate. Sistemul de AI agents a creat <strong>{len(slaves)}</strong>
                    agenți slave pentru monitorizare continuă.
                </p>
            </div>
            
            <!-- SWOT Analysis -->
            <div class="section">
                <h2 class="section-title">
                    <i class="fas fa-brain"></i>
                    Analiza SWOT (DeepSeek AI)
                </h2>
                
                <div class="list-section strengths">
                    <h3><i class="fas fa-check-circle"></i> Puncte Forte (Strengths)</h3>
                    <ul>
                        {''.join(f"<li>{s}</li>" for s in analysis_data.get('strengths', ['N/A'])[:5])}
                    </ul>
                </div>
                
                <div class="list-section weaknesses">
                    <h3><i class="fas fa-exclamation-triangle"></i> Puncte Slabe (Weaknesses)</h3>
                    <ul>
                        {''.join(f"<li>{w}</li>" for w in analysis_data.get('weaknesses', ['N/A'])[:5])}
                    </ul>
                </div>
                
                <div class="list-section opportunities">
                    <h3><i class="fas fa-lightbulb"></i> Oportunități (Opportunities)</h3>
                    <ul>
                        {''.join(f"<li>{o}</li>" for o in analysis_data.get('opportunities', ['N/A'])[:5])}
                    </ul>
                </div>
                
                <div class="list-section threats">
                    <h3><i class="fas fa-shield-alt"></i> Amenințări (Threats)</h3>
                    <ul>
                        {''.join(f"<li>{t}</li>" for t in analysis_data.get('threats', ['N/A'])[:5])}
                    </ul>
                </div>
            </div>
            
            <!-- Immediate Actions -->
            <div class="section">
                <h2 class="section-title">
                    <i class="fas fa-tasks"></i>
                    Acțiuni Imediate Recomandate
                </h2>
                <div class="list-section actions">
                    <ul>
                        {''.join(f"<li><strong>#{i+1}</strong> - {action}</li>" for i, action in enumerate(analysis_data.get('immediate_actions', ['N/A'])[:10]))}
                    </ul>
                </div>
            </div>
            
            <!-- Top Competitors -->
            <div class="section">
                <h2 class="section-title">
                    <i class="fas fa-trophy"></i>
                    Top 20 Competitori
                </h2>
                <table class="competitor-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Domeniu</th>
                            <th>Score</th>
                            <th>Keywords</th>
                            <th>Poz. Medie</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    # Add top 20 competitors
    for i, comp in enumerate(competitors[:20], 1):
        score = comp.get('score', 0)
        score_class = 'score-high' if score > 60 else 'score-medium' if score > 45 else 'score-low'
        html += f"""
                        <tr>
                            <td><strong>{i}</strong></td>
                            <td>{comp.get('domain', 'N/A')}</td>
                            <td><span class="score-badge {score_class}">{score:.1f}</span></td>
                            <td>{comp.get('appearances_count', 0)}</td>
                            <td>{f"{comp.get('avg_position', 0):.1f}" if comp.get('avg_position') else '-'}</td>
                        </tr>
"""
    
    html += """
                    </tbody>
                </table>
            </div>
            
            <!-- Recommendations -->
            <div class="section">
                <h2 class="section-title">
                    <i class="fas fa-rocket"></i>
                    Recomandări Strategice
                </h2>
                <div class="list-section">
                    <ul>
                        <li><strong>Prioritate 1:</strong> Implementează serviciile lipsă identificate în analiza de gap</li>
                        <li><strong>Prioritate 2:</strong> Optimizează SEO pentru keywords cu cel mai mare potențial</li>
                        <li><strong>Prioritate 3:</strong> Dezvoltă parteneriate pentru servicii complementare</li>
                        <li><strong>Prioritate 4:</strong> Creează conținut educațional pentru diferențiere</li>
                        <li><strong>Prioritate 5:</strong> Monitorizează continuu competitorii majori (score >60)</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>© 2025 Competitive Intelligence System</strong></p>
            <p>Powered by DeepSeek AI • LangChain • MongoDB • Qdrant</p>
            <p style="margin-top: 15px; font-size: 12px; opacity: 0.7;">
                Acest raport a fost generat automat folosind AI multi-agent system
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    return html


def save_report(agent_id, html_content):
    """Save report to file"""
    filename = f"strategic_report_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = f"/srv/hf/ai_agents/reports/{filename}"
    
    import os
    os.makedirs("/srv/hf/ai_agents/reports", exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return filepath


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_strategic_report.py <agent_id>")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    
    print(f"📊 Generating Strategic Report for agent {agent_id}...")
    print()
    
    # Fetch data
    print("📥 Fetching MongoDB data...")
    mongo_data = get_mongo_data(agent_id)
    if not mongo_data:
        print("❌ Agent not found in MongoDB")
        sys.exit(1)
    print(f"✅ MongoDB data OK - Domain: {mongo_data.get('domain')}")
    
    print("📥 Fetching API data...")
    api_data = get_api_data(agent_id)
    if not api_data:
        print("❌ Failed to fetch API data")
        sys.exit(1)
    print("✅ API data OK")
    
    # Generate report
    print("📝 Generating HTML report...")
    html_content = generate_html_report(agent_id, mongo_data, api_data)
    
    # Save report
    print("💾 Saving report...")
    filepath = save_report(agent_id, html_content)
    
    print()
    print("=" * 70)
    print("✅ RAPORT STRATEGIC GENERAT CU SUCCES!")
    print("=" * 70)
    print()
    print(f"📄 Fișier salvat: {filepath}")
    print(f"🌐 Deschide în browser pentru vizualizare completă")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()

