#!/usr/bin/env python3
"""
Script pentru actualizarea agenților existenți cu integrare Qwen
"""

import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import logging

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
agents_collection = db.site_agents

def update_agent_with_qwen(agent_id: str, domain: str):
    """Actualizează un agent cu integrare Qwen"""
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            logger.warning(f"⚠️ Agent {agent_id} not found")
            return False
        
        # Obține memory_config existent sau creează unul nou
        memory_config = agent.get("memory_config", {})
        
        # Adaugă configurația Qwen Learning
        if "qwen_learning" not in memory_config:
            memory_config["qwen_learning"] = {
                "enabled": True,
                "learning_collection": f"qwen_learning_{agent_id}",
                "conversation_collection": f"qwen_conversations_{agent_id}",
                "learning_frequency": "after_each_conversation",
                "pattern_analysis": True,
                "context_enhancement": True
            }
        
        # Actualizează agent în MongoDB
        update_result = agents_collection.update_one(
            {"_id": ObjectId(agent_id)},
            {"$set": {
                "qwen_integrated": True,
                "qwen_learning_enabled": True,
                "memory_config": memory_config
            }}
        )
        
        if update_result.modified_count > 0 or update_result.matched_count > 0:
            logger.info(f"✅ Agent {domain} (ID: {agent_id[:8]}...) - Qwen integrat")
            return True
        else:
            logger.warning(f"⚠️ Agent {domain} (ID: {agent_id[:8]}...) - Nu a fost necesară actualizarea (deja configurat)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Eroare la actualizarea agentului {domain} (ID: {agent_id}): {e}")
        return False

def main():
    logger.info("=== ACTUALIZARE QWEN PENTRU AGENȚI EXISTENȚI ===")
    
    # Găsește agenții fără Qwen integrat
    query = {
        "$or": [
            {"qwen_integrated": {"$exists": False}},
            {"qwen_integrated": False},
            {"qwen_learning_enabled": {"$exists": False}},
            {"qwen_learning_enabled": False}
        ]
    }
    
    agents_to_update = list(agents_collection.find(query))
    
    total_agents = agents_collection.count_documents({})
    agents_with_qwen = agents_collection.count_documents({
        "qwen_integrated": True,
        "qwen_learning_enabled": True
    })
    
    logger.info(f"\nTotal agenți în baza de date: {total_agents}")
    logger.info(f"✅ Agenți cu Qwen integrat: {agents_with_qwen}")
    logger.info(f"❌ Agenți fără Qwen integrat: {len(agents_to_update)}")
    
    if not agents_to_update:
        logger.info("\n✅ Toți agenții au Qwen integrat!")
        return
    
    logger.info(f"\nActualizare {len(agents_to_update)} agenți...")
    
    updated_count = 0
    failed_count = 0
    
    for agent in agents_to_update:
        agent_id = str(agent["_id"])
        domain = agent.get("domain", "unknown.com")
        
        logger.info(f"Procesez agentul: {domain} (ID: {agent_id[:8]}...)...")
        if update_agent_with_qwen(agent_id, domain):
            updated_count += 1
        else:
            failed_count += 1
    
    logger.info("\n=== REZULTAT ===")
    logger.info(f"✅ Actualizați: {updated_count}")
    logger.info(f"❌ Eșuați: {failed_count}")
    logger.info(f"📊 Total procesați: {updated_count + failed_count}")
    
    # Verificare finală
    final_agents_with_qwen = agents_collection.count_documents({
        "qwen_integrated": True,
        "qwen_learning_enabled": True
    })
    
    if final_agents_with_qwen == total_agents:
        logger.info(f"\n✅ Toți agenții au Qwen integrat! ({final_agents_with_qwen}/{total_agents})")
    else:
        logger.warning(f"\n⚠️ Atenție: {total_agents - final_agents_with_qwen} agenți încă nu au Qwen integrat.")

if __name__ == "__main__":
    main()


