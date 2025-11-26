import os
import json
from datetime import datetime
from pymongo import MongoClient
from typing import List, Dict, Any
import requests

# Config
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
client = MongoClient(MONGO_URI)
db = client['ai_agents_db']
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-a5ef584416d94f8482540e075c776157")

class BusinessIntelligenceAdvanced:
    def __init__(self):
        self.db = db
        self.offers_collection = self.db['client_financial_history']

    def _call_llm(self, prompt):
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4
        }
        
        # Încercăm de 3 ori (Retry Logic)
        for attempt in range(3):
            try:
                resp = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data, timeout=30)
                response_json = resp.json()
                
                if 'choices' in response_json:
                    return response_json['choices'][0]['message']['content']
                elif 'error' in response_json:
                    print(f"⚠️ API Error (Attempt {attempt+1}): {response_json['error']}")
                    import time
                    time.sleep(2 * (attempt + 1)) # Așteptăm 2s, 4s, 6s
                else:
                    print(f"⚠️ Unknown Response: {response_json}")
                    
            except Exception as e:
                print(f"⚠️ Connection Error (Attempt {attempt+1}): {e}")
                import time
                time.sleep(2)
                
        return "Nu am putut genera răspunsul din cauza aglomerării rețelei AI. Încearcă din nou mai târziu."

    # --- 1. INGESTIE FINANCIARĂ ---
    def add_project_history(self, domain: str, project_data: Dict):
        """
        Stochează date despre un proiect trecut: 
        {
            "project_name": "Hala Industriala X",
            "offer_value": 50000, 
            "collected_value": 48000,
            "costs": 30000,
            "category": "ignifugare_metal",
            "date": "2024-01-15"
        }
        """
        project_data['domain'] = domain
        project_data['created_at'] = datetime.now()
        
        # Calcul automat metrici
        project_data['profit'] = project_data['offer_value'] - project_data['costs']
        project_data['margin'] = (project_data['profit'] / project_data['offer_value']) * 100 if project_data['offer_value'] > 0 else 0
        project_data['collection_rate'] = (project_data['collected_value'] / project_data['offer_value']) * 100 if project_data['offer_value'] > 0 else 0
        
        self.offers_collection.insert_one(project_data)
        print(f"✅ Proiect {project_data['project_name']} salvat cu marjă {project_data['margin']:.1f}%")

    def analyze_financial_health(self, domain: str):
        """Analizează portofoliul și identifică ce merge și ce nu"""
        projects = list(self.offers_collection.find({"domain": domain}))
        
        if not projects:
            return "Nu există date financiare suficiente."
            
        # Agregare date
        categories = {}
        total_profit = 0
        bad_debt = 0 # Bani neîncasati
        
        for p in projects:
            cat = p.get('category', 'general')
            if cat not in categories: categories[cat] = {"revenue": 0, "profit": 0, "count": 0}
            
            categories[cat]["revenue"] += p['offer_value']
            categories[cat]["profit"] += p['profit']
            categories[cat]["count"] += 1
            
            not_collected = p['offer_value'] - p['collected_value']
            if not_collected > 0:
                bad_debt += not_collected

        # Identificare "Cash Cows" și "Money Pits"
        best_category = max(categories.items(), key=lambda x: x[1]['profit'])[0]
        
        analysis = {
            "total_projects": len(projects),
            "most_profitable_category": best_category,
            "total_bad_debt": bad_debt,
            "category_breakdown": categories,
            "insight": f"Cea mai profitabilă activitate este {best_category}. Ai pierdut {bad_debt} EUR din neîncasări."
        }
        return analysis

    # --- 2. PLANIFICARE DEZVOLTARE (DEEP THINKING) ---
    def generate_growth_plan(self, domain: str, financial_analysis: Dict):
        """Generează plan de dezvoltare bazat pe bani + piață"""
        
        # Luăm context din piață (simulat sau din DB)
        market_context = "Piața cere vopsea termospumantă, competitorii tăi se extind pe zona industrială."
        
        prompt = f"""
        Ești un Strateg de Business de top. Analizează datele financiare ale clientului '{domain}' și contextul pieței.
        
        DATE FINANCIARE:
        - Cea mai profitabilă categorie: {financial_analysis.get('most_profitable_category')}
        - Bani pierduți (neîncasați): {financial_analysis.get('total_bad_debt')}
        - Breakdown: {json.dumps(financial_analysis.get('category_breakdown'))}
        
        CONTEXT PIAȚĂ:
        {market_context}
        
        SARCINĂ:
        Creează un Plan de Dezvoltare Strategică pe 3 puncte:
        1. **Consolidare**: Cum să maximizeze profitul pe ce face deja bine.
        2. **Expansiune**: O nouă direcție de business bazată pe cash-ul disponibil.
        3. **Redresare**: Cum să recupereze banii neîncasați sau să evite clienții răi.
        
        Răspunde structurat Markdown.
        """
        
        plan = self._call_llm(prompt)
        return plan

    # --- 3. IMPLEMENTARE (ACTION TAKERS) ---
    def generate_action_assets(self, domain: str, action_type: str, details: Dict):
        """
        Generează asset-uri reale de implementare.
        action_type: 'email_debt_collection', 'rfq_supplier', 'landing_page_content'
        """
        if action_type == 'email_debt_collection':
            client_name = details.get('client_name', 'Client')
            amount = details.get('amount', 0)
            prompt = f"Scrie un email ferm dar profesional către clientul {client_name} pentru a recupera suma de {amount} EUR restantă de 30 de zile. Include amenințare subtilă legală dar păstrează ușa deschisă."
            return self._call_llm(prompt)
            
        elif action_type == 'rfq_supplier':
            material = details.get('material', 'vopsea')
            qty = details.get('quantity', '1000L')
            prompt = f"Scrie o Cerere de Ofertă (RFQ) către distribuitori pentru {qty} de {material}. Vrem preț competitiv, termen de plată 60 zile. Ton: Procurement Manager experimentat."
            return self._call_llm(prompt)
            
        elif action_type == 'landing_page_content':
            service = details.get('service', 'Serviciu Nou')
            prompt = f"Scrie structura și textul (H1, H2, Call to Action) pentru un Landing Page care vinde serviciul '{service}'. Folosește copywriting persuasiv, focus pe beneficii (nu caracteristici)."
            return self._call_llm(prompt)
            
        return "Tip acțiune necunoscut."

# Test rapid
if __name__ == "__main__":
    bi = BusinessIntelligenceAdvanced()
    
    # 1. Adăugăm date istorice (Mock)
    bi.add_project_history("tehnica-antifoc.ro", {
        "project_name": "Mall Plaza",
        "offer_value": 15000, "collected_value": 15000, "costs": 8000,
        "category": "ignifugare_lemn"
    })
    bi.add_project_history("tehnica-antifoc.ro", {
        "project_name": "Hala Depozit",
        "offer_value": 40000, "collected_value": 30000, "costs": 35000, # Profit mic + neîncasat
        "category": "vopsea_metal"
    })
    
    # 2. Analizăm
    analysis = bi.analyze_financial_health("tehnica-antifoc.ro")
    print("\n📊 ANALIZĂ FINANCIARĂ:\n", json.dumps(analysis, indent=2, ensure_ascii=False))
    
    # 3. Plan Dezvoltare
    print("\n🧠 DEEP THINKING PLAN:\n")
    plan = bi.generate_growth_plan("tehnica-antifoc.ro", analysis)
    print(plan)
    
    # 4. Implementare (Action)
    print("\n⚡ ACȚIUNE IMPLEMENTARE (Email Recuperare):\n")
    action = bi.generate_action_assets("tehnica-antifoc.ro", "email_debt_collection", {"client_name": "Hala Depozit SRL", "amount": 10000})
    print(action)
