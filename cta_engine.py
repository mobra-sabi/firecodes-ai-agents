import pymongo
import json
import re
from datetime import datetime

class CTAEngine:
    def __init__(self):
        self.client = pymongo.MongoClient("mongodb://localhost:27018/")
        self.db = self.client["ro_index_db"]
        self.sites = self.db["crawled_sites"]

    def analyze_domain(self, domain):
        """
        Analizează un domeniu și generează acțiuni concrete.
        """
        # Curățăm input-ul (scoatem https:// etc)
        if not domain: return {"status": "error", "message": "Nu ai introdus un domeniu."}
        domain = domain.replace("https://", "").replace("http://", "").strip().strip("/")
        
        # 1. Colectare date despre domeniu
        # Căutăm toate paginile care aparțin acestui domeniu (regex flexibil)
        domain_regex = f".*{re.escape(domain)}.*"
        domain_docs = list(self.sites.find({"domain": {"$regex": domain_regex, "$options": "i"}}))
        
        if not domain_docs:
            # Fallback: Căutăm în URL
            domain_docs = list(self.sites.find({"url": {"$regex": domain_regex, "$options": "i"}}))

        if not domain_docs:
            return {
                "status": "not_found", 
                "message": f"Domeniul {domain} nu este încă în indexul nostru. Crawler-ul îl va prelua curând!",
                "actions": []
            }

        page_count = len(domain_docs)
        last_update = domain_docs[0].get('scraped_at', datetime.now())
        
        # Calcul conținut total (text)
        total_size = sum(doc.get('content_length', 0) for doc in domain_docs)
        avg_size = total_size / page_count if page_count > 0 else 0

        # 2. Analiză Competitivă (Sumară)
        # Căutăm domenii cu titluri similare (keywords)
        keywords = []
        title_sample = domain_docs[0].get('title', "")
        if title_sample:
            # Luăm cuvinte lungi din titlu
            words = re.findall(r'\w+', title_sample)
            keywords = [w for w in words if len(w) > 4 and w.lower() not in ['home', 'page', 'welcome', 'index', 'website', 'online']][:3]
        
        competitors_count = 0
        if keywords:
            regex = "|".join(keywords)
            # Căutăm alții care au aceleași cuvinte în titlu
            # Folosim limit pentru viteză
            competitors_count = len(self.sites.distinct("domain", {"title": {"$regex": regex, "$options": "i"}}))
            if competitors_count > 0: competitors_count -= 1 # Scădem domeniul curent

        # 3. Generare Hints (Reguli simple -> Vor fi înlocuite de LLM)
        actions = []

        # HINT: Content Volume
        if page_count < 10:
            actions.append({
                "type": "CRITICAL",
                "icon": "🚨",
                "title": "Volum Critic de Mic",
                "desc": f"Ai doar {page_count} pagini indexate. Media în industrie este 40-50. Trebuie să generezi pagini noi urgent pentru a fi vizibil."
            })
        elif page_count < 50:
            actions.append({
                "type": "GROWTH",
                "icon": "📈",
                "title": "Potențial de Creștere",
                "desc": f"Ai un număr decent de pagini ({page_count}), dar există loc de expansiune. Încearcă să faci un Blog sau pagini dedicate pe servicii."
            })
        else:
            actions.append({
                "type": "SUCCESS",
                "icon": "✅",
                "title": "Structură Solidă",
                "desc": f"Excelent! Ai {page_count} pagini. Motorul de căutare te vede ca o autoritate. Acum focusează-te pe actualizarea conținutului vechi."
            })
        
        # HINT: Content Density
        if avg_size < 3000: # bytes 
            actions.append({
                "type": "SEO",
                "icon": "📝",
                "title": "Conținut Subțire (Thin Content)",
                "desc": "Paginile tale au foarte puțin text util. Google penalizează asta. Adaugă descrieri detaliate."
            })

        # HINT: Market
        if competitors_count > 5:
            actions.append({
                "type": "MARKET",
                "icon": "⚔️",
                "title": "Competiție Intensă",
                "desc": f"Am găsit {competitors_count} alți jucători care folosesc aceleași cuvinte cheie ({', '.join(keywords)}). Trebuie să te diferențiezi prin ofertă."
            })
        else:
            actions.append({
                "type": "OPPORTUNITY",
                "icon": "💎",
                "title": "Nișă Liberă",
                "desc": "Ești într-o zonă cu puțină competiție directă detectată pe aceste cuvinte cheie. E momentul să domini piața!"
            })

        return {
            "status": "success",
            "domain": domain,
            "profile": {
                "pages": page_count,
                "total_data_kb": round(total_size / 1024),
                "competitors": competitors_count,
                "top_keywords": keywords
            },
            "actions": actions
        }

if __name__ == "__main__":
    # Test rapid
    engine = CTAEngine()
    print(json.dumps(engine.analyze_domain("emag.ro"), indent=2))

