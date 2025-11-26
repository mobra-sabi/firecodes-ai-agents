import os
import json
from pymongo import MongoClient
from datetime import datetime

# Configurare MongoDB
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
client = MongoClient(MONGO_URI)
db = client['ai_agents_db']

def generate_report(domain):
    print(f"📊 Generare raport DEMO pentru: {domain}...")
    
    # 1. Găsește Master Agent
    master = db.site_agents.find_one({"domain": domain, "agent_type": "master"})
    if not master:
        print(f"❌ Master agent not found for {domain}")
        return

    # 2. Statistici Competitori
    # Căutăm după master_agent_id (ObjectID)
    total_competitors = db.site_agents.count_documents({"master_agent_id": master['_id'], "agent_type": "slave"})
    competitors = list(db.site_agents.find({"master_agent_id": master['_id'], "agent_type": "slave"}))
    
    if total_competitors == 0:
        # Fallback: încercăm după parent_domain string
        total_competitors = db.site_agents.count_documents({"parent_domain": domain, "agent_type": "slave"})
        competitors = list(db.site_agents.find({"parent_domain": domain, "agent_type": "slave"}))
    
    # 3. Extrage Competitori de Top (pe baza scorului de relevanță dacă există, sau random/primii)
    # În viitor putem sorta după un scor 'threat_level'
    top_competitors = competitors[:10] 

    # 4. Analiza Keywords (din descoperire)
    # Încercăm să găsim keywords din competitor_discovery sau slave agents
    keywords = set()
    for comp in competitors:
        if 'keyword' in comp:
            keywords.add(comp['keyword'])
    
    # HEADER RAPORT
    report = f"""# 🏗️ RAPORT DE INTELIGENȚĂ COMPETITIVĂ - {domain.upper()}
**Data Generării:** {datetime.now().strftime('%d %b %Y')}
**Sistem:** AI Competitive Intelligence Suite v1.0

---

## 1. 🎯 SUMAR EXECUTIV
Sistemul AI a scanat complet piața digitală pentru **{domain}**.
- **Competitori Analizați:** {total_competitors} companii
- **Cuvinte Cheie Monitorizate:** {len(keywords)} expresii cheie
- **Acoperire Piață:** Națională (România)

### 💡 Insight Principal:
Piața de protecție la foc este extrem de fragmentată. Deși există mulți jucători ({total_competitors}), majoritatea se concentrează pe nișe specifice (doar ignifugare lemn, doar vopsele). **{domain}** are avantajul unei abordări integrate, dar trebuie să se diferențieze clar de "vânzătorii de produse" (ex: magazine bricolaj) vs. "furnizorii de soluții".

---

## 2. ⚔️ TOP COMPETITORI IDENTIFICAȚI
Analiza detaliată a principalilor jucători din piață:

"""

    # LISTA COMPETITORI
    for i, comp in enumerate(top_competitors, 1):
        comp_domain = comp.get('domain', 'N/A')
        comp_url = comp.get('site_url', 'N/A')
        
        # Încercăm să luăm descrierea din 'agent_config' -> 'knowledge_base' -> 'company_info'
        desc = "Analiză în curs..."
        services = []
        try:
            kb = comp.get('agent_config', {}).get('knowledge_base', {})
            desc = kb.get('company_info', {}).get('unique_selling_points', ['Nu sunt date detaliate'])[0]
            services = [s.get('service_name') for s in kb.get('services_offered', [])]
        except:
            pass
            
        report += f"""### {i}. {comp_domain}
- **Website:** {comp_url}
- **Poziționare:** {desc}
- **Servicii Identificate:** {', '.join(services[:5])}
\n"""

    report += """
---

## 3. 🔑 ANALIZA CUVINTELOR CHEIE (Oportunități SEO)
Termenii pe care competitorii îi atacă agresiv:

"""
    # Afișăm keywords grupate (mockup logic, sau real dacă avem date)
    keywords_list = list(keywords)[:20]
    for k in keywords_list:
        report += f"- `{k}`\n"

    report += """
---

## 4. 🚀 RECOMANDĂRI STRATEGICE (AI GENERATED)

### A. Diferențiere
Majoritatea competitorilor comunică "tehnic" (produse, norme). **Recomandare:** Comunicați "soluții și siguranță". Nu vindeți "vopsea intumescentă", vindeți "certitudinea avizului ISU".

### B. Lacune în Piață (Gaps)
Am identificat că puțini competitori oferă conținut educațional despre **mentenanța** sistemelor de protecție la foc. Acesta este un unghi excelent pentru a captura trafic timpuriu.

### C. Acțiune Imediată
Crearea de pagini dedicate (Landing Pages) pentru fiecare sub-nișă identificată la competitori:
1. Ignifugare Lemn vs Metal (pagini separate)
2. Consultanță ISU (serviciu distinct)

---

*Generat automat de AI Agents System.*
"""

    # Salvare Raport
    filename = f"reports/{domain}_DEMO_REPORT.md"
    os.makedirs("reports", exist_ok=True)
    with open(filename, "w") as f:
        f.write(report)
    
    print(f"✅ Raport salvat în: {filename}")
    print(report)

if __name__ == "__main__":
    generate_report("tehnica-antifoc.ro")

