#!/usr/bin/env python3
"""
Script pentru fixarea agenților care nu au vector_collection configurat
"""

import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import logging
from qdrant_client import QdrantClient

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
agents_collection = db.site_agents

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    prefer_grpc=True,
    force_disable_check_same_thread=True
)

def fix_agent_vector_collection(agent_id: str, agent: dict):
    """Fix vector_collection pentru un agent"""
    try:
        agent_id_str = str(agent_id)
        domain = agent.get("domain", "unknown")
        
        # Verifică dacă există colecție Qdrant cu numele standard
        collection_name_standard = f"agent_{agent_id_str}"
        
        collection_name = None
        
        # Verifică dacă există colecție Qdrant
        try:
            collection_info = qdrant_client.get_collection(collection_name_standard)
            collection_name = collection_name_standard
            logger.info(f"✅ Colecție Qdrant găsită: {collection_name} ({collection_info.points_count} puncte)")
        except:
            logger.warning(f"⚠️ Colecție Qdrant '{collection_name_standard}' nu există pentru agent {domain}")
        
        # Actualizează agentul cu vector_collection dacă există
        if collection_name:
            update_result = agents_collection.update_one(
                {"_id": ObjectId(agent_id_str)},
                {"$set": {
                    "vector_collection": collection_name
                }}
            )
            
            if update_result.modified_count > 0:
                logger.info(f"✅ Agent {domain} (ID: {agent_id_str[:8]}...) - vector_collection actualizat: {collection_name}")
                return True
            else:
                logger.info(f"ℹ️ Agent {domain} - vector_collection deja configurat sau nu a fost necesară actualizarea")
                return False
        else:
            logger.warning(f"⚠️ Agent {domain} (ID: {agent_id_str[:8]}...) - nu are colecție Qdrant. Trebuie recreat.")
            return False
            
    except Exception as e:
        logger.error(f"❌ Eroare la fixarea agentului {agent_id}: {e}")
        return False

def main():
    logger.info("=== FIX VECTOR_COLLECTION PENTRU AGENȚI ===")
    
    # Găsește agenții fără vector_collection sau cu vector_collection None/empty
    query = {
        "$or": [
            {"vector_collection": {"$exists": False}},
            {"vector_collection": None},
            {"vector_collection": ""}
        ]
    }
    
    agents_to_fix = list(agents_collection.find(query))
    
    total_agents = agents_collection.count_documents({})
    agents_with_vector = agents_collection.count_documents({"vector_collection": {"$exists": True, "$ne": None, "$ne": ""}})
    
    logger.info(f"\nTotal agenți în baza de date: {total_agents}")
    logger.info(f"✅ Agenți cu vector_collection: {agents_with_vector}")
    logger.info(f"❌ Agenți fără vector_collection: {len(agents_to_fix)}")
    
    if not agents_to_fix:
        logger.info("\n✅ Toți agenții au vector_collection configurat!")
        return
    
    logger.info(f"\nFix {len(agents_to_fix)} agenți...")
    
    fixed_count = 0
    failed_count = 0
    
    for agent in agents_to_fix:
        agent_id = agent["_id"]
        domain = agent.get("domain", "unknown")
        
        logger.info(f"Procesez agentul: {domain} (ID: {str(agent_id)[:8]}...)...")
        if fix_agent_vector_collection(agent_id, agent):
            fixed_count += 1
        else:
            failed_count += 1
    
    logger.info("\n=== REZULTAT ===")
    logger.info(f"✅ Fixați: {fixed_count}")
    logger.info(f"❌ Necesită recreare: {failed_count}")
    logger.info(f"📊 Total procesați: {fixed_count + failed_count}")
    
    # Verificare finală
    final_agents_with_vector = agents_collection.count_documents({"vector_collection": {"$exists": True, "$ne": None, "$ne": ""}})
    if final_agents_with_vector == total_agents:
        logger.info(f"\n✅ Toți agenții au vector_collection configurat! ({final_agents_with_vector}/{total_agents})")
    else:
        logger.warning(f"\n⚠️ Atenție: {total_agents - final_agents_with_vector} agenți încă nu au vector_collection configurat.")

if __name__ == "__main__":
    main()


