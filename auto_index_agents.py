#!/usr/bin/env python3
"""
Script pentru indexarea automată a tuturor agenților care nu au date în Qdrant
"""

import asyncio
import sys
import os
from pymongo import MongoClient
from qdrant_client import QdrantClient
from site_ingestor import run_site_ingest
from dotenv import load_dotenv

# Încarcă variabilele de environment
load_dotenv('.env')

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:9308/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ai_agents_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:9306")

class AutoIndexer:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[MONGODB_DATABASE]
        self.agents_collection = self.db.agents
        self.qdrant_client = QdrantClient(url=QDRANT_URL)
        
    def get_agents_without_data(self):
        """Obține agenții care nu au date indexate în Qdrant"""
        agents = list(self.agents_collection.find({}))
        agents_without_data = []
        
        for agent in agents:
            agent_id = str(agent['_id'])
            site_url = agent.get('site_url')
            agent_name = agent.get('name', 'Unknown Agent')
            
            if not site_url:
                print(f"⚠️  Skipping agent {agent_name} ({agent_id}) - no site_url found.")
                continue
            
            collection_name = f"agent_{agent_id}_content"
            
            try:
                # Check if collection exists and has vectors
                collection_info = self.qdrant_client.get_collection(collection_name=collection_name)
                if collection_info.points_count > 0:
                    print(f"✅ Agent {agent_name} ({agent_id}) already has {collection_info.points_count} points. Skipping.")
                    continue
            except Exception as e:
                print(f"📝 Agent {agent_name} ({agent_id}) needs indexing: {e}")
            
            agents_without_data.append(agent)
        
        return agents_without_data
    
    async def index_agent(self, agent):
        """Indexează un agent"""
        agent_id = str(agent['_id'])
        site_url = agent.get('site_url')
        agent_name = agent.get('name', 'Unknown Agent')
        
        print(f"\n🔄 Indexing agent: {agent_name}")
        print(f"   ID: {agent_id}")
        print(f"   URL: {site_url}")
        
        config = {
            'qdrant_url': QDRANT_URL,
            'mongodb_uri': MONGODB_URI,
            'mongodb_db': MONGODB_DATABASE,
            'max_pages': 10,  # Limit pentru testare rapidă
            'chunk_size': 1000,
            'chunk_overlap': 200
        }
        
        try:
            result = await run_site_ingest(site_url, agent_id, config)
            
            if result.get('status') == 'success':
                pages_scraped = result.get('pages_scraped', 0)
                chunks_created = result.get('chunks_created', 0)
                print(f"   ✅ Success: {pages_scraped} pages, {chunks_created} chunks")
                return True
            else:
                error = result.get('error', 'Unknown error')
                print(f"   ❌ Failed: {error}")
                return False
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return False
    
    async def index_all_agents(self):
        """Indexează toți agenții care nu au date"""
        print("🚀 AUTO-INDEXING AGENTS WITHOUT DATA")
        print("=" * 50)
        
        agents_without_data = self.get_agents_without_data()
        
        if not agents_without_data:
            print("✅ All agents already have data indexed!")
            return
        
        print(f"📋 Found {len(agents_without_data)} agents that need indexing")
        
        successful = 0
        failed = 0
        
        for i, agent in enumerate(agents_without_data, 1):
            print(f"\n📊 Progress: {i}/{len(agents_without_data)}")
            
            success = await self.index_agent(agent)
            
            if success:
                successful += 1
            else:
                failed += 1
        
        print(f"\n{'=' * 50}")
        print("📊 FINAL RESULTS")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Total processed: {len(agents_without_data)}")
        
        self.client.close()
        
        return successful, failed

async def main():
    """Funcția principală"""
    indexer = AutoIndexer()
    
    try:
        successful, failed = await indexer.index_all_agents()
        
        if successful > 0:
            print(f"\n🎉 Successfully indexed {successful} agents!")
            print("💬 You can now test the chat functionality for these agents.")
        
        if failed > 0:
            print(f"\n⚠️  {failed} agents failed to index. Check the logs above for details.")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Indexing interrupted by user")
    except Exception as e:
        print(f"\n❌ General error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
