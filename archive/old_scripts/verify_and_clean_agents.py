#!/usr/bin/env python3
"""
Script pentru verificarea și curățarea agenților fake
Elimină agenții care nu au conținut nici în Qdrant, nici în MongoDB
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
site_content_collection = db.site_content

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    prefer_grpc=True,
    force_disable_check_same_thread=True
)

def verify_agent(agent_id: str, agent: dict) -> dict:
    """Verifică dacă un agent este complet și funcțional"""
    agent_id_str = str(agent_id)
    domain = agent.get("domain", "unknown")
    
    result = {
        "agent_id": agent_id_str,
        "domain": domain,
        "is_valid": False,
        "issues": [],
        "has_qdrant_content": False,
        "has_mongodb_content": False,
        "has_vector_collection": False,
        "has_memory": False
    }
    
    # 1. Verifică vector_collection
    vector_collection = agent.get("vector_collection")
    if vector_collection:
        result["has_vector_collection"] = True
        
        # Verifică dacă există colecție Qdrant
        try:
            collection_info = qdrant_client.get_collection(vector_collection)
            points_count = collection_info.points_count
            
            if points_count > 0:
                result["has_qdrant_content"] = True
                logger.info(f"✅ Agent {domain}: Qdrant collection '{vector_collection}' are {points_count} puncte")
            else:
                result["issues"].append(f"Colecție Qdrant '{vector_collection}' există dar este goală")
                logger.warning(f"⚠️ Agent {domain}: Colecție Qdrant '{vector_collection}' este goală")
        except:
            result["issues"].append(f"Colecție Qdrant '{vector_collection}' nu există")
            logger.warning(f"⚠️ Agent {domain}: Colecție Qdrant '{vector_collection}' nu există")
    else:
        # Verifică dacă există colecție cu numele standard
        collection_name_standard = f"agent_{agent_id_str}"
        try:
            collection_info = qdrant_client.get_collection(collection_name_standard)
            points_count = collection_info.points_count
            
            if points_count > 0:
                result["has_qdrant_content"] = True
                result["issues"].append(f"vector_collection nu este configurat, dar colecția '{collection_name_standard}' există cu {points_count} puncte")
                logger.info(f"✅ Agent {domain}: Colecție standard '{collection_name_standard}' are {points_count} puncte")
            else:
                result["issues"].append(f"vector_collection nu este configurat și colecția standard este goală")
        except:
            result["issues"].append(f"vector_collection nu este configurat și colecția standard nu există")
    
    # 2. Verifică conținut în MongoDB
    try:
        content_count = site_content_collection.count_documents({"agent_id": agent_id_str})
        if content_count > 0:
            result["has_mongodb_content"] = True
            logger.info(f"✅ Agent {domain}: MongoDB are {content_count} documente de conținut")
        else:
            result["issues"].append(f"MongoDB nu are conținut pentru acest agent")
            logger.warning(f"⚠️ Agent {domain}: MongoDB nu are conținut")
    except Exception as e:
        result["issues"].append(f"Eroare la verificarea MongoDB: {e}")
    
    # 3. Verifică memorie
    memory_initialized = agent.get("memory_initialized", False)
    if memory_initialized:
        result["has_memory"] = True
    else:
        result["issues"].append("Memorie nu este inițializată")
    
    # 4. Determină dacă agentul este valid
    # Agentul este valid dacă are conținut în cel puțin una din bazele de date
    if result["has_qdrant_content"] or result["has_mongodb_content"]:
        result["is_valid"] = True
        if result["has_qdrant_content"] and result["has_mongodb_content"]:
            result["status"] = "✅ COMPLET - Are conținut în Qdrant și MongoDB"
        elif result["has_qdrant_content"]:
            result["status"] = "⚠️ PARȚIAL - Are conținut doar în Qdrant"
        else:
            result["status"] = "⚠️ PARȚIAL - Are conținut doar în MongoDB"
    else:
        result["is_valid"] = False
        result["status"] = "❌ FAKE - Nu are conținut nici în Qdrant, nici în MongoDB"
    
    return result

def main():
    logger.info("=== VERIFICARE ȘI CURĂȚARE AGENȚI ===")
    
    # Obține toți agenții
    all_agents = list(agents_collection.find())
    total_agents = len(all_agents)
    
    logger.info(f"\nTotal agenți în baza de date: {total_agents}\n")
    
    valid_agents = []
    fake_agents = []
    
    for agent in all_agents:
        agent_id = agent["_id"]
        result = verify_agent(agent_id, agent)
        
        logger.info(f"\n📋 Agent: {result['domain']} (ID: {result['agent_id'][:8]}...)")
        logger.info(f"   Status: {result['status']}")
        
        if result["issues"]:
            logger.info(f"   Probleme:")
            for issue in result["issues"]:
                logger.info(f"     - {issue}")
        
        if result["is_valid"]:
            valid_agents.append(result)
        else:
            fake_agents.append(result)
    
    # Rezumat
    logger.info("\n" + "="*60)
    logger.info("=== REZUMAT ===")
    logger.info(f"✅ Agenți valizi: {len(valid_agents)}")
    logger.info(f"❌ Agenți fake (fără conținut): {len(fake_agents)}")
    logger.info(f"📊 Total: {total_agents}")
    
    # Listă agenți fake
    if fake_agents:
        logger.info("\n=== AGENȚI FAKE (TO BE DELETED) ===")
        for fake in fake_agents:
            logger.info(f"❌ {fake['domain']} (ID: {fake['agent_id'][:8]}...): {fake['status']}")
    
    # Confirmă ștergerea
    if fake_agents:
        logger.info(f"\n⚠️ GĂSIȚI {len(fake_agents)} AGENȚI FAKE")
        logger.info("Rulează scriptul cu --delete pentru a șterge agenții fake")
        
        import sys
        if "--delete" in sys.argv:
            logger.info("\n🗑️ ȘTERG AGENȚI FAKE...")
            for fake in fake_agents:
                try:
                    agents_collection.delete_one({"_id": ObjectId(fake["agent_id"])})
                    logger.info(f"✅ Șters agent {fake['domain']} (ID: {fake['agent_id'][:8]}...)")
                except Exception as e:
                    logger.error(f"❌ Eroare la ștergerea agentului {fake['domain']}: {e}")
            
            logger.info(f"\n✅ Șters {len(fake_agents)} agenți fake")
        else:
            logger.info("\n📝 Pentru a șterge agenții fake, rulează:")
            logger.info("   python3 verify_and_clean_agents.py --delete")
    else:
        logger.info("\n✅ Toți agenții sunt valizi!")

if __name__ == "__main__":
    main()


