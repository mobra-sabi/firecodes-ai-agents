import os
import time
import json
from datetime import datetime
from pymongo import MongoClient

# Config
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
client = MongoClient(MONGO_URI)
db = client['ai_agents_db']

class ContinuousMonitor:
    def __init__(self):
        self.db = db
        
    def check_rankings(self, domain):
        """Verifică pozițiile în Google pentru un domeniu (Simulare logică)"""
        print(f"🔄 [MONITOR] Verificare ranking zilnic pentru {domain}...")
        
        # Aici ar veni logica reală de apelare Google Search API
        # Pentru demo, simulăm o schimbare de poziție
        
        current_rank = 5  # Să zicem că ieri era pe 5
        new_rank = 4      # Azi a urcat pe 4
        
        if new_rank < current_rank:
            self.create_insight(domain, "SEO_IMPROVEMENT", 
                f"🚀 Vești bune! Ai urcat pe poziția {new_rank} pentru 'ignifugare lemn'.",
                "Continuă să adaugi conținut pe blog despre normele ISU.")
        elif new_rank > current_rank:
            self.create_insight(domain, "SEO_ALERT",
                f"⚠️ Atenție! Ai scăzut pe poziția {new_rank}. Competitorul 'ignifugare.eu' te-a depășit.",
                "Verifică pagina lor nouă despre prețuri și actualizează meta-descrierile.")

    def check_competitors(self, domain):
        """Verifică ce fac competitorii"""
        print(f"👀 [MONITOR] Spionaj competitori pentru {domain}...")
        
        # Simulăm detectarea unei schimbări la un competitor
        competitor = "promat.com"
        change_detected = True
        
        if change_detected:
            self.create_insight(domain, "COMPETITOR_ACTION",
                f"📢 {competitor} a lansat un ghid nou PDF.",
                "Ar trebui să creezi și tu un 'Ghid de Siguranță' pentru clienți pentru a nu pierde autoritate.")

    def create_insight(self, domain, type, message, action_item):
        """Salvează hint-ul în baza de date pentru a fi afișat în Dashboard"""
        insight = {
            "domain": domain,
            "type": type, # SEO, PRICE, CONTENT, ALERT
            "message": message,
            "action_item": action_item,
            "created_at": datetime.now(),
            "is_read": False,
            "priority": "high" if "ALERT" in type else "medium"
        }
        
        # Salvăm în colecția 'client_notifications'
        self.db.client_notifications.insert_one(insight)
        print(f"💡 Insight generat: {message}")

    def run_daily_check(self, domain="tehnica-antifoc.ro"):
        print(f"=== RULARE MONITORIZARE ZILNICĂ: {datetime.now()} ===")
        self.check_rankings(domain)
        self.check_competitors(domain)
        print("=== FINALIZAT ===")

if __name__ == "__main__":
    monitor = ContinuousMonitor()
    # Simulăm rularea zilnică
    monitor.run_daily_check("tehnica-antifoc.ro")

