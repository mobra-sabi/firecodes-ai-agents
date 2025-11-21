#!/usr/bin/env python3
"""
Script pentru a reporni procesul de scraping și embeddings pentru agenții nefinalizați
Folosește ScraperAPI pentru scraping robust
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pymongo import MongoClient
from config.database_config import MONGODB_URI, MONGODB_DATABASE
from tools.construction_agent_creator import ConstructionAgentCreator
from datetime import datetime
import time

def retry_incomplete_agents():
    """Repornește procesul pentru agenții nefinalizați"""
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]
    agents_collection = db.site_agents if 'site_agents' in db.list_collection_names() else db.agents
    
    # Găsește agenții nefinalizați (fără chunks)
    incomplete_agents = list(agents_collection.find({
        "industry": "construction",
        "chunks_indexed": 0
    }))
    
    print(f"🔄 REPORNIRE PROCES PENTRU AGENȚI NEFINALIZAȚI\n")
    print(f"📊 Agenți nefinalizați: {len(incomplete_agents)}\n")
    
    if not incomplete_agents:
        print("✅ Toți agenții sunt finalizați!")
        client.close()
        return
    
    creator = ConstructionAgentCreator()
    
    print("🚀 Pornire procesare cu ScraperAPI...\n")
    
    success_count = 0
    failed_count = 0
    
    for idx, agent in enumerate(incomplete_agents, 1):
        domain = agent.get('domain', 'N/A')
        url = agent.get('url', f"https://{domain}")
        
        print(f"[{idx}/{len(incomplete_agents)}] Procesare {domain}...")
        
        try:
            # Re-analizează și re-scrape site-ul (folosește ScraperAPI automat)
            analysis = creator.analyze_construction_site(url)
            
            # Verifică dacă scraping-ul a reușit
            site_content = analysis.get('site_content', {})
            pages_scraped = len(site_content.get('pages', []))
            embeddings_count = analysis.get('embeddings_created', 0)
            
            # Actualizează agentul în MongoDB
            agents_collection.update_one(
                {"_id": agent["_id"]},
                {
                    "$set": {
                        "pages_indexed": pages_scraped,
                        "chunks_indexed": embeddings_count,
                        "has_embeddings": embeddings_count > 0,
                        "has_content": pages_scraped > 0,
                        "status": "validated" if embeddings_count > 0 else "created",
                        "last_updated": datetime.now()
                    }
                }
            )
            
            if embeddings_count > 0:
                print(f"   ✅ Finalizat: {pages_scraped} pagini, {embeddings_count} chunks")
                success_count += 1
            else:
                print(f"   ⚠️ Scraping eșuat sau fără conținut (site poate fi inaccesibil)")
                failed_count += 1
            
            # Pauză mică între request-uri pentru a nu suprasolicita ScraperAPI
            time.sleep(2)
            
        except Exception as e:
            print(f"   ❌ Eroare: {e}")
            failed_count += 1
            # Marchează ca failed
            agents_collection.update_one(
                {"_id": agent["_id"]},
                {
                    "$set": {
                        "status": "failed",
                        "last_updated": datetime.now()
                    }
                }
            )
    
    print(f"\n✅ Procesare completă!")
    print(f"   - Succes: {success_count}")
    print(f"   - Eșuat: {failed_count}")
    print(f"   - Total: {len(incomplete_agents)}")
    
    client.close()

if __name__ == "__main__":
    retry_incomplete_agents()

