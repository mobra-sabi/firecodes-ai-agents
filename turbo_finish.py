import asyncio
import os
import logging
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import sys

# Adăugăm calea curentă la path
sys.path.append(os.getcwd())

from ceo_master_workflow import CEOMasterWorkflow

# Configurare Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/turbo_finish.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TurboFinish")

async def main():
    MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
    client = MongoClient(MONGO_URI)
    db = client['ai_agents_db']
    
    DOMAIN = "hidroizolatii-terase.ro"
    PARALLEL_COUNT = 12 # FORȚĂM NOTA - avem 8 GPU-uri de top!
    
    logger.info(f"🚀 Pornire TURBO FINISH pentru {DOMAIN} cu {PARALLEL_COUNT} workers")
    
    # 1. Găsește Master Agent
    master = db.site_agents.find_one({"domain": DOMAIN, "agent_type": "master"})
    if not master:
        logger.error(f"❌ Master agent not found for {DOMAIN}")
        return
        
    master_id = str(master["_id"])
    logger.info(f"✅ Master Agent găsit: {master_id}")
    
    # 2. Găsește lista de competitori descoperiți (din Faza 5)
    discovery_doc = db.competitor_discoveries.find_one(
        {"agent_id": master["_id"]}, 
        sort=[("created_at", -1)]
    )
    
    if not discovery_doc or "discovery_data" not in discovery_doc:
        logger.error("❌ Nu s-au găsit date de discovery (competitori). Rulați workflow-ul normal.")
        return
        
    all_competitors = discovery_doc["discovery_data"].get("competitors", [])
    logger.info(f"📊 Total competitori descoperiți inițial: {len(all_competitors)}")
    
    # 3. Verifică ce agenți există deja
    existing_slaves = list(db.site_agents.find(
        {"master_agent_id": master["_id"], "agent_type": "slave"},
        {"site_url": 1}
    ))
    existing_urls = {s.get("site_url") for s in existing_slaves}
    
    logger.info(f"✅ Agenți deja creați: {len(existing_urls)}")
    
    # 4. Filtrează doar cei rămași
    remaining_competitors = [
        c for c in all_competitors 
        if c.get("url") not in existing_urls
    ]
    
    if not remaining_competitors:
        logger.info("🎉 Toți agenții sunt deja creați! Nimic de făcut.")
        return
        
    logger.info(f"🔥 RĂMAȘI DE PROCESAT: {len(remaining_competitors)}")
    
    # 5. Execută procesare paralelă
    workflow = CEOMasterWorkflow()
    
    # Injectăm direct în faza 7
    logger.info("⚡ Lansare execuție paralelă...")
    result = await workflow._phase7_create_competitor_agents_parallel(
        competitors=remaining_competitors,
        parallel_count=PARALLEL_COUNT,
        master_agent_id=master_id
    )
    
    if result.get("success"):
        logger.info("✅ Procesare TURBO finalizată cu succes!")
        
        # Facem și organigrama finală
        slave_ids = result.get("agent_ids", [])
        # Adăugăm și pe cei vechi la listă
        slave_ids.extend([str(s["_id"]) for s in existing_slaves])
        
        logger.info("Generare organigramă finală...")
        await workflow._phase8_create_master_slave_orgchart(master_id, slave_ids)
        
    else:
        logger.error(f"❌ Eroare la procesare: {result.get('error')}")

if __name__ == "__main__":
    # Setăm GPU corect pentru embeddings (evităm conflict cu vLLM)
    os.environ["CUDA_VISIBLE_DEVICES"] = "8,9" 
    asyncio.run(main())

