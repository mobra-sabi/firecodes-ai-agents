#!/usr/bin/env python3
"""
Script pentru a indexa automat toți agenții care nu au date în Qdrant
"""

import asyncio
import sys
import os
from pymongo import MongoClient
from site_ingestor import run_site_ingest

# Configurație
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:9308')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'ai_agents_db')

async def check_agent_has_data(agent_id: str) -> bool:
    """Verifică dacă agentul are date indexate în Qdrant"""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url="http://localhost:9306")
        collection_name = f"agent_{agent_id}_content"
        
        # Încearcă să obțină informații despre colecție
        try:
            info = client.get_collection(collection_name)
            return info.points_count > 0
        except Exception:
            return False
    except Exception as e:
        print(f"❌ Eroare la verificarea datelor pentru agent {agent_id}: {e}")
        return False

async def index_agent(agent: dict) -> bool:
    """Indexează un agent dacă nu are date"""
    agent_id = agent['_id']
    site_url = agent.get('site_url', '')
    
    if not site_url:
        print(f"⚠️  Agent {agent_id} nu are site_url, săriți...")
        return False
    
    print(f"🔍 Verificând agent {agent_id} ({site_url})...")
    
    # Verifică dacă are deja date
    has_data = await check_agent_has_data(agent_id)
    if has_data:
        print(f"✅ Agent {agent_id} are deja date indexate")
        return True
    
    print(f"📥 Indexez agent {agent_id}...")
    
    config = {
        'qdrant_url': 'http://localhost:9306',
        'mongodb_uri': MONGODB_URI,
        'mongodb_db': MONGODB_DATABASE,
        'max_pages': 10,
        'chunk_size': 1000,
        'chunk_overlap': 200
    }
    
    try:
        result = await run_site_ingest(site_url, agent_id, config)
        
        if result.get('status') == 'success':
            print(f"✅ Agent {agent_id} indexat cu succes: {result.get('pages_scraped', 0)} pagini, {result.get('chunks_created', 0)} chunks")
            return True
        else:
            print(f"❌ Eroare la indexarea agentului {agent_id}: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Eroare la indexarea agentului {agent_id}: {e}")
        return False

async def main():
    """Funcția principală"""
    print("🚀 Încep indexarea automată a agenților...")
    
    # Conectare la MongoDB
    try:
        client = MongoClient(MONGODB_URI)
        db = client[MONGODB_DATABASE]
        agents_collection = db.agents
        
        # Obține toți agenții
        agents = list(agents_collection.find({}))
        print(f"📊 Găsiți {len(agents)} agenți în baza de date")
        
        if not agents:
            print("❌ Nu s-au găsit agenți în baza de date")
            return
        
        # Indexează fiecare agent
        success_count = 0
        total_count = len(agents)
        
        for i, agent in enumerate(agents, 1):
            print(f"\n--- Agent {i}/{total_count} ---")
            if await index_agent(agent):
                success_count += 1
        
        print(f"\n🎉 Indexare completă!")
        print(f"✅ Succes: {success_count}/{total_count} agenți")
        print(f"❌ Eșec: {total_count - success_count}/{total_count} agenți")
        
    except Exception as e:
        print(f"❌ Eroare la conectarea la MongoDB: {e}")
        return

if __name__ == "__main__":
    asyncio.run(main())


