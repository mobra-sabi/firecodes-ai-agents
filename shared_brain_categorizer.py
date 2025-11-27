import pymongo
import time
import re
import logging

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - CATEGORIZER - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Categorizer")

# DB Connection
client = pymongo.MongoClient("mongodb://localhost:27018/")
db = client["ro_index_db"]
sites_col = db["crawled_sites"]

# Taxonomie (Keywords)
CATEGORIES = {
    "CONSTRUCTII": ["constructii", "amenajari", "termopane", "materiale", "santier", "beton", "arhitect", "zidarie", "scule"],
    "AUTO": ["auto", "masini", "piese", "service", "anvelope", "ulei", "motor", "bmw", "audi", "vw", "reparatii auto"],
    "IMOBILIARE": ["imobiliare", "apartamente", "de vanzare", "inchiriere", "garsoniera", "terenuri", "case", "agentie imobiliara"],
    "IT_TECH": ["software", "hardware", "calculatoare", "telefoane", "web design", "programare", "hosting", "laptop", "digital"],
    "FASHION": ["haine", "incaltaminte", "rochii", "moda", "tricouri", "blugi", "accesorii", "fashion", "outfit"],
    "MEDICAL": ["clinica", "doctor", "sanatate", "farmacie", "stomatologie", "dentist", "analize", "medic", "spital"],
    "NEWS": ["stiri", "noutati", "actualitate", "ziar", "cotidian", "eveniment", "breaking news", "politic"],
    "TURISM": ["hotel", "pensiune", "cazare", "vacanta", "sejur", "agentie turism", "zboruri", "booking"],
    "ECOMMERCE": ["cosul meu", "adauga in cos", "produs", "livrare", "pret", "magazin online", "checkout"]
}

def detect_category(title, url):
    """Deduce categoria bazat pe titlu și URL"""
    text = (str(title) + " " + str(url)).lower()
    
    scores = {cat: 0 for cat in CATEGORIES}
    
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1
                
    # Returnează categoria cu scorul maxim, dacă e > 0
    best_cat = max(scores, key=scores.get)
    if scores[best_cat] > 0:
        return best_cat
    return "DIVERS"

def run_categorizer():
    logger.info("🧠 Shared Brain Categorizer STARTED")
    
    while True:
        # Găsește site-uri care nu au categorie setată
        # Procesăm în batch-uri de 1000
        cursor = sites_col.find({"category": {"$exists": False}}).limit(1000)
        
        count = 0
        updates = []
        
        for doc in cursor:
            cat = detect_category(doc.get('title', ''), doc.get('url', ''))
            
            updates.append(pymongo.UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"category": cat, "categorized_at": time.time()}}
            ))
            count += 1
            
        if updates:
            result = sites_col.bulk_write(updates)
            logger.info(f"🏷️  Categorized {result.modified_count} sites. (Last: {cat})")
        else:
            logger.info("💤 No new sites to categorize. Sleeping...")
            time.sleep(10) # Așteaptă date noi de la crawler

if __name__ == "__main__":
    run_categorizer()

