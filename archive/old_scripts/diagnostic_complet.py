#!/usr/bin/env python3
"""
Diagnostic Complet - Verifică toate componentele mecanismului
"""

import os
from pymongo import MongoClient
from bson import ObjectId
from qdrant_client import QdrantClient
from dotenv import load_dotenv
import logging

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

def diagnostic_complet():
    """Verificare completă a tuturor componentelor"""
    
    print("="*70)
    print("DIAGNOSTIC COMPLET MECANISM CREARE AGENT")
    print("="*70)
    
    # 1. VERIFICARE AGENȚI
    print("\n1. AGENȚI ÎN BAZA DE DATE:")
    print("-"*70)
    agents = list(agents_collection.find())
    print(f"Total agenți: {len(agents)}")
    
    agents_valizi = 0
    agents_fake = 0
    
    for agent in agents:
        agent_id = str(agent["_id"])
        domain = agent.get("domain", "N/A")
        
        # Verificări
        has_vector_collection = bool(agent.get("vector_collection"))
        memory_initialized = agent.get("memory_initialized", False)
        qwen_integrated = agent.get("qwen_integrated", False)
        
        # Verifică MongoDB
        mongo_count = site_content_collection.count_documents({"agent_id": agent_id})
        
        # Verifică Qdrant
        collection_name = agent.get("vector_collection") or f"agent_{agent_id}"
        qdrant_points = 0
        qdrant_exists = False
        try:
            info = qdrant_client.get_collection(collection_name)
            qdrant_points = info.points_count
            qdrant_exists = True
        except:
            pass
        
        # Determină status
        has_content = mongo_count > 0 or qdrant_points > 0
        is_valid = has_content and memory_initialized and qwen_integrated
        
        status_icon = "✅" if is_valid else "❌"
        
        print(f"\n{status_icon} {domain} (ID: {agent_id[:8]}...)")
        print(f"   Vector collection: {agent.get('vector_collection') or 'N/A'}")
        print(f"   Memory initialized: {memory_initialized}")
        print(f"   Qwen integrated: {qwen_integrated}")
        print(f"   MongoDB chunks: {mongo_count}")
        print(f"   Qdrant collection: {collection_name} ({qdrant_points} puncte)" if qdrant_exists else f"   Qdrant collection: {collection_name} (NU EXISTĂ)")
        print(f"   Status: {'✅ VALID' if is_valid else '❌ FAKE sau INCOMPLET'}")
        
        if is_valid:
            agents_valizi += 1
        else:
            agents_fake += 1
    
    # 2. VERIFICARE MONGODB
    print("\n\n2. MONGODB site_content:")
    print("-"*70)
    total_docs = site_content_collection.count_documents({})
    docs_with_agent_id = site_content_collection.count_documents({"agent_id": {"$exists": True, "$ne": None}})
    docs_without_agent_id = total_docs - docs_with_agent_id
    
    print(f"Total documente: {total_docs}")
    print(f"Documente CU agent_id: {docs_with_agent_id}")
    print(f"Documente FĂRĂ agent_id (vechi): {docs_without_agent_id}")
    
    if docs_with_agent_id > 0:
        sample = site_content_collection.find_one({"agent_id": {"$exists": True, "$ne": None}})
        print(f"\nSample document CU agent_id:")
        print(f"  Fields: {list(sample.keys())}")
        print(f"  agent_id: {sample.get('agent_id')}")
        print(f"  chunk_index: {sample.get('chunk_index')}")
        print(f"  content length: {len(sample.get('content', ''))} caractere")
    
    # 3. VERIFICARE QDRANT
    print("\n\n3. QDRANT COLLECTIONS:")
    print("-"*70)
    try:
        collections = qdrant_client.get_collections()
        print(f"Total colecții: {len(collections.collections)}")
        
        agent_collections = [c for c in collections.collections if c.name.startswith("agent_")]
        print(f"Colecții agent_*: {len(agent_collections)}")
        
        for coll in agent_collections[:10]:  # Primele 10
            try:
                info = qdrant_client.get_collection(coll.name)
                print(f"  ✅ {coll.name}: {info.points_count} puncte")
            except:
                print(f"  ❌ {coll.name}: EROARE")
    except Exception as e:
        print(f"❌ Eroare la obținerea colecțiilor: {e}")
    
    # 4. REZUMAT FINAL
    print("\n\n" + "="*70)
    print("REZUMAT FINAL")
    print("="*70)
    print(f"✅ Agenți valizi: {agents_valizi}")
    print(f"❌ Agenți fake/incompleți: {agents_fake}")
    print(f"📊 Total agenți: {len(agents)}")
    print(f"\nMongoDB site_content:")
    print(f"  Total documente: {total_docs}")
    print(f"  Documente CU agent_id: {docs_with_agent_id}")
    print(f"  Documente FĂRĂ agent_id (vechi): {docs_without_agent_id}")
    
    # 5. RECOMANDĂRI
    print("\n" + "="*70)
    print("RECOMANDĂRI")
    print("="*70)
    
    if agents_fake > 0:
        print(f"⚠️ {agents_fake} agenți fake/incompleți identificați")
        print("   Rulează: python3 verify_and_clean_agents.py --delete")
    
    if docs_without_agent_id > 0:
        print(f"⚠️ {docs_without_agent_id} documente vechi în site_content (fără agent_id)")
        print("   Acestea sunt documente vechi - pot fi ignorate sau șterse")
    
    if agents_valizi == 0:
        print("\n⚠️ NICIUN AGENT VALID ÎN BAZA DE DATE")
        print("   Creează agenți noi folosind interfața!")
    
    if agents_valizi > 0:
        print(f"\n✅ {agents_valizi} agenți valizi gata de utilizare")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    diagnostic_complet()


