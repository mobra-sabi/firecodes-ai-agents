import os
import json
from pymongo import MongoClient
from datetime import datetime
from typing import List, Dict

# Config
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
client = MongoClient(MONGO_URI)
db = client['ai_agents_db']

class PricingOffersSystem:
    def __init__(self):
        self.db = db
        
    def update_client_profile(self, domain: str, profile_data: Dict):
        """
        Actualizează profilul clientului cu detalii operaționale
        Ex: nr_angajati, materiale_folosite, furnizori_curenti
        """
        print(f"📝 Actualizare profil client pentru {domain}...")
        
        # Structurăm datele în knowledge_base
        update_data = {
            "agent_config.knowledge_base.operational_data": {
                "employees_count": profile_data.get("employees"),
                "materials_used": profile_data.get("materials", []), # List[str]
                "current_suppliers": profile_data.get("suppliers", []), # List[Dict]
                "target_margin": profile_data.get("margin", 0.20),
                "last_updated": datetime.now()
            }
        }
        
        self.db.site_agents.update_one(
            {"domain": domain, "agent_type": "master"},
            {"$set": update_data}
        )
        print("✅ Profil operațional actualizat.")

    def find_better_suppliers(self, material: str, current_price: float = None):
        """
        Caută în baza de date (competitori) distribuitori sau prețuri mai bune pentru un material
        """
        print(f"🔍 Căutare furnizori pentru material: {material}...")
        
        # În realitate, am căuta în Qdrant folosind embeddings pentru "vânzare {material}"
        # Aici simulăm o căutare în textul competitorilor din MongoDB
        
        # Căutăm competitori care menționează materialul în descriere sau servicii
        potential_suppliers = []
        
        # Regex search simplu (în producție folosim Qdrant)
        cursor = self.db.site_agents.find({
            "agent_type": "slave",
            "$or": [
                {"agent_config.knowledge_base.services_offered.description": {"$regex": material, "$options": "i"}},
                {"agent_config.knowledge_base.company_info.unique_selling_points": {"$regex": material, "$options": "i"}}
            ]
        }).limit(5)
        
        for agent in cursor:
            potential_suppliers.append({
                "domain": agent.get("domain"),
                "url": agent.get("site_url"),
                "context": "Distribuitor sau utilizator identificat"
            })
            
        return potential_suppliers

    def analyze_and_optimize_offer(self, domain: str, offer_text: str):
        """
        Analizează o ofertă veche text, compară cu piața și generează una nouă
        """
        print(f"💰 Optimizare ofertă pentru {domain}...")
        
        # 1. Identificăm serviciile/materialele din text (NLP simplu sau LLM)
        # Simulăm extragerea
        detected_items = ["ignifugare lemn", "vopsea intumescentă"]
        
        # 2. Căutăm prețuri de referință în piață (din ce am învățat de la competitori)
        market_insights = []
        for item in detected_items:
            # Aici am interoga baza de date 'market_prices' dacă am avea-o populată
            market_insights.append(f"Preț mediu piață pentru '{item}': 15-25 EUR/mp")
            
        # 3. Generăm sugestii
        suggestions = [
            "⚠️ Prețul tău pare sub media pieței. Poți crește cu 10%.",
            "💡 Competitorul 'promat.com' oferă garanție 5 ani. Adaugă și tu asta în ofertă.",
            "🚚 Poți găsi vopsea mai ieftină la 'distribuitor-vopsele.ro' (identificat în baza de date)."
        ]
        
        return {
            "original_text_summary": offer_text[:100] + "...",
            "detected_items": detected_items,
            "market_context": market_insights,
            "optimization_suggestions": suggestions,
            "generated_offer_template": f"OFERTĂ PREMIUM\nServicii: {', '.join(detected_items)}\n\nAvând în vedere standardele actuale..."
        }

# Test rapid
if __name__ == "__main__":
    system = PricingOffersSystem()
    
    # 1. Update Profil
    system.update_client_profile("tehnica-antifoc.ro", {
        "employees": 15,
        "materials": ["vopsea intumescentă", "lac ignifug", "gips carton antifoc"],
        "suppliers": ["Promat", "Hilti"]
    })
    
    # 2. Găsire furnizori
    suppliers = system.find_better_suppliers("vopsea")
    print(f"Found {len(suppliers)} potential suppliers for 'vopsea'")
    
    # 3. Optimizare ofertă
    offer = system.analyze_and_optimize_offer("tehnica-antifoc.ro", "Oferta ignifugare pod 200mp cu vopsea standard. Pret total 2000 EUR.")
    print(json.dumps(offer, indent=2, ensure_ascii=False))
