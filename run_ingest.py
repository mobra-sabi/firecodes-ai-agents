#!/usr/bin/env python3
"""
Script pentru a rula ingest pentru un agent specific
"""

import asyncio
import sys
from site_ingestor import run_site_ingest

async def main():
    if len(sys.argv) != 3:
        print("Usage: python3 run_ingest.py <agent_id> <site_url>")
        print("Example: python3 run_ingest.py 68f732b6f86c99d4d127ea88 https://www.tehnica-antifoc.ro")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    site_url = sys.argv[2]
    
    print(f"🚀 Starting ingest for agent {agent_id}")
    print(f"📄 Site URL: {site_url}")
    
    # Configurație pentru ingest
    config = {
        'qdrant_url': 'http://localhost:9306',
        'mongodb_uri': 'mongodb://localhost:9308/',
        'mongodb_db': 'ai_agents_db',
        'max_pages': 10,
        'chunk_size': 1000,
        'chunk_overlap': 200
    }
    
    try:
        result = await run_site_ingest(site_url, agent_id, config)
        
        print(f"🔍 Full result: {result}")
        
        if result.get('success'):
            print("✅ Ingest completed successfully!")
            print(f"📊 Pages processed: {result.get('pages_processed', 0)}")
            print(f"📝 Chunks created: {result.get('chunks_created', 0)}")
            print(f"🔍 Collection name: {result.get('collection_name', 'N/A')}")
        else:
            print("❌ Ingest failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error during ingest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
