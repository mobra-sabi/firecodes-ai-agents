#!/usr/bin/env python3
"""
Script pentru actualizarea tuturor agenților existenți cu configurarea memoriei.
"""

import os
import sys
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Încarcă variabilele de mediu
load_dotenv(override=True)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

def get_qdrant_collection_name(agent_id):
    """Generează numele colecției Qdrant pentru un agent."""
    return f"agent_{agent_id}"

def check_qdrant_collection(collection_name):
    """Verifică dacă colecția Qdrant există."""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=60,
            prefer_grpc=True,
            force_disable_check_same_thread=True
        )
        collection_info = client.get_collection(collection_name)
        return collection_info.points_count if collection_info else 0
    except:
        return 0

def update_agent_memory(agent):
    """Actualizează configurarea memoriei pentru un agent."""
    agent_id = agent.get('_id')
    domain = agent.get('domain', 'N/A')
    
    # Generează numele colecției Qdrant
    collection_name = get_qdrant_collection_name(agent_id)
    
    # Verifică dacă colecția Qdrant există
    vectors_count = check_qdrant_collection(collection_name)
    
    # Configurarea memoriei
    memory_config = {
        "working_memory": {
            "max_conversation_turns": 10,
            "context_window": 4000,
            "current_session": []
        },
        "long_term_memory": {
            "vector_db": "qdrant" if vectors_count > 0 else "mongodb",
            "collection_name": collection_name if vectors_count > 0 else None,
            "embedding_model": "BAAI/bge-large-en-v1.5",
            "content_ttl": "30 days"
        },
        "retention_policies": {
            "conversation_ttl": "7 days",
            "content_ttl": "30 days",
            "max_storage_size": "1GB"
        },
        "vector_db": "qdrant" if vectors_count > 0 else "mongodb",
        "conversation_context": []
    }
    
    # Actualizează agent în MongoDB
    update_result = agents_collection.update_one(
        {"_id": ObjectId(agent_id)},
        {"$set": {
            "memory_initialized": True,
            "memory_config": memory_config,
            "qwen_memory_enabled": True,
            "vector_collection": collection_name if vectors_count > 0 else None
        }}
    )
    
    return update_result.modified_count > 0 or update_result.matched_count > 0

def main():
    """Funcția principală."""
    global agents_collection
    
    # Conectare MongoDB
    client = MongoClient(MONGO_URI)
    db = client.ai_agents_db
    agents_collection = db.site_agents
    
    # Găsește toți agenții fără memorie configurată
    agents = list(agents_collection.find())
    
    agents_to_update = []
    agents_already_configured = []
    
    for agent in agents:
        memory_initialized = agent.get('memory_initialized', False)
        memory_config = agent.get('memory_config', {})
        has_memory = memory_initialized and memory_config != {}
        
        if not has_memory:
            agents_to_update.append(agent)
        else:
            agents_already_configured.append(agent)
    
    print(f"=== ACTUALIZARE MEMORIE PENTRU AGENȚI EXISTENȚI ===\n")
    print(f"Total agenți: {len(agents)}")
    print(f"✅ Agenți cu memorie configurată: {len(agents_already_configured)}")
    print(f"❌ Agenți FĂRĂ memorie configurată: {len(agents_to_update)}\n")
    
    if len(agents_to_update) == 0:
        print("✅ Toți agenții au memorie configurată!")
        return
    
    print(f"Actualizare {len(agents_to_update)} agenți...\n")
    
    updated_count = 0
    failed_count = 0
    
    for agent in agents_to_update:
        domain = agent.get('domain', 'N/A')
        agent_id = str(agent.get('_id'))
        
        try:
            success = update_agent_memory(agent)
            if success:
                print(f"✅ {domain} (ID: {agent_id[:8]}...) - Memorie configurată")
                updated_count += 1
            else:
                print(f"⚠️  {domain} (ID: {agent_id[:8]}...) - Nu s-a putut actualiza")
                failed_count += 1
        except Exception as e:
            print(f"❌ {domain} (ID: {agent_id[:8]}...) - EROARE: {e}")
            failed_count += 1
    
    print(f"\n=== REZULTAT ===")
    print(f"✅ Actualizați: {updated_count}")
    print(f"❌ Eșuați: {failed_count}")
    print(f"📊 Total procesați: {len(agents_to_update)}")

if __name__ == "__main__":
    main()


