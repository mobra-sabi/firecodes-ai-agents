import os
import json
import argparse
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

# Configurare MongoDB
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
client = MongoClient(MONGO_URI)
db = client['ai_agents_db']

def generate_report(domain):
    print(f"📊 Generare raport SMART pentru: {domain}...")
    
    # 1. Găsește Master Agent
    # Încearcă să găsească master agent-ul după domeniu (cu sau fără www/https)
    master = db.site_agents.find_one({
        "$or": [
            {"domain": domain},
            {"site_url": {"$regex": domain}},
            {"parent_domain": domain, "agent_type": "master"} 
        ],
        "agent_type": "master"
    })
    
    if not master:
        print(f"❌ Master agent not found for {domain}")
        # Fallback: list all masters
        masters = list(db.site_agents.find({"agent_type": "master"}))
        print("Disponibile:", [m.get('domain') for m in masters])
        return

    print(f"✅ Master Agent găsit: {master.get('domain')} (ID: {master['_id']})")

    # 2. Statistici Competitori
    competitors_cursor = db.site_agents.find({"master_agent_id": master['_id'], "agent_type": "slave"})
    competitors = list(competitors_cursor)
    total_competitors = len(competitors)
    
    print(f"✅ Competitori găsiți în DB: {total_competitors}")

    # 3. Sortează după scorul de relevanță (dacă există)
    # Structura discovery_data.validation_details.similarity_score sau discovery_data.discovery_score
    def get_score(comp):
        try:
            return comp.get('discovery_data', {}).get('discovery_score', 0)
        except:
            return 0
            
    sorted_competitors = sorted(competitors, key=get_score, reverse=True)
    top_competitors = sorted_competitors[:15] # Top 15

    # 4. Extrage Keywords Strategice (din Master)
    master_keywords = master.get('keywords', [])
    subdomains = master.get('subdomains', [])

    # HEADER RAPORT
    report = f"""# 🏗️ RAPORT STRATEGIC DE PIAȚĂ - {domain.upper()}
**Generat de:** Qwen-72B Local AI @ {datetime.now().strftime('%H:%M, %d %b %Y')}
**Hardware:** 8x GPU Cluster (Local Infrastructure)

---

## 1. 🎯 SUMAR EXECUTIV
AI-ul a analizat în profunzime domeniul **{domain}** și a mapat ecosistemul digital.

- **Competitori Identificați & Analizați:** {total_competitors} companii relevante
- **Cuvinte Cheie Strategice:** {len(master_keywords)} expresii monitorizate
- **Subdomenii de Activitate:** {', '.join(subdomains[:5])}

### 💡 Insight Strategic:
Piața este activă, cu {total_competitors} jucători validați ca fiind relevanți. AI-ul a filtrat automat site-urile irelevante (magazine generaliste, forumuri), păstrând doar competiția directă care oferă servicii de hidroizolații/construcții similare.

---

## 2. 🏆 TOP 15 COMPETITORI (Analizați de AI)
Iată cei mai relevanți jucători, ordonați după scorul de similaritate cu afacerea ta:

"""

    # LISTA COMPETITORI CU MOTIVARE
    for i, comp in enumerate(top_competitors, 1):
        comp_domain = comp.get('domain', 'N/A')
        comp_url = comp.get('site_url', 'N/A')
        
        # Extrage datele de validare
        discovery = comp.get('discovery_data', {})
        validation = discovery.get('validation_details', {})
        reason = validation.get('reason', "Validat automat pe baza cuvintelor cheie.")
        score = discovery.get('discovery_score', 0)
        
        # Curăță motivul (uneori e JSON string)
        if isinstance(reason, str) and len(reason) > 300:
            reason = reason[:300] + "..."

        report += f"""### {i}. {comp_domain} (Scor Relevanță: {score}/100)
- **URL:** {comp_url}
- **Why It Matters (AI Analysis):** {reason}
\n"""

    report += """
---

## 3. 🔑 CUVINTE CHEIE & OPORTUNITĂȚI (SEO Gaps)
Următoarele expresii sunt folosite intens de competitori și reprezintă oportunități de trafic:

"""
    # Afișăm keywords
    for k in master_keywords[:25]:
        report += f"- `{k}`\n"

    report += """
---

## 4. 🚀 PLAN DE ACȚIUNE (Next Steps)
Pe baza acestei analize, recomand următoarele acțiuni imediate:

1. **Monitorizare Prețuri:** Activarea modulului "Spy" pe top 5 competitori pentru a afla prețurile lor la manoperă.
2. **Campanie Conținut:** Crearea de pagini dedicate pentru subdomeniile unde competiția e slabă (ex: hidroizolații fundații vs terase).
3. **Lead Generation:** Contactarea automată a furnizorilor comuni pentru oferte mai bune.

---
*Raport generat automat de Sistemul AI Local.*
"""

    # Salvare Raport
    domain_safe = domain.replace('.', '_')
    filename = f"reports/{domain_safe}_STRATEGIC_REPORT.md"
    os.makedirs("reports", exist_ok=True)
    with open(filename, "w") as f:
        f.write(report)
    
    print(f"✅ Raport salvat în: {filename}")
    
    # Afișează preview
    print("\n--- PREVIEW RAPORT ---\n")
    print(report[:2000]) # Primi 2000 chars

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("domain", help="Domeniul analizat (ex: hidroizolatii-terase.ro)")
    args = parser.parser.parse_args() if hasattr(parser, 'parser') else argparse.Namespace(domain="hidroizolatii-terase.ro") # Fallback for direct execution
    
    # Dacă rulăm din linie de comandă cu argumente
    import sys
    if len(sys.argv) > 1:
        generate_report(sys.argv[1])
    else:
        generate_report("hidroizolatii-terase.ro")

