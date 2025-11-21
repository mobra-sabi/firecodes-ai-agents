#!/usr/bin/env python3
"""
Test pentru sistemul îmbunătățit de creare agenți
"""

import asyncio
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

from site_agent_creator import create_agent_logic
from pymongo import MongoClient
from bson import ObjectId

# Site de test (unul simplu și rapid)
TEST_URL = "https://www.ropaintsolutions.ro"

async def test_improved_creation():
    print("\n" + "="*70)
    print("🧪 TEST SISTEM ÎMBUNĂTĂȚIT CREARE AGENȚI")
    print("="*70)
    print(f"\nSite test: {TEST_URL}\n")
    
    try:
        # Șterge agentul existent dacă există
        client = MongoClient("mongodb://localhost:27017/")
        db = client.ai_agents_db
        
        existing = db.site_agents.find_one({"site_url": TEST_URL})
        if existing:
            agent_id = existing['_id']
            print(f"🗑️  Șterg agent existent: {agent_id}")
            db.site_agents.delete_one({"_id": agent_id})
            db.site_content.delete_many({"agent_id": agent_id})
        
        # Creează agent nou
        print("\n🚀 Încep crearea agentului cu sistemul îmbunătățit...\n")
        
        result = await create_agent_logic(
            url=TEST_URL,
            api_key="test",
            loop=asyncio.get_event_loop(),
            websocket=None
        )
        
        print("\n" + "="*70)
        print("📊 REZULTAT CREARE:")
        print("="*70)
        print(f"\n✅ Agent ID: {result.get('agent_id')}")
        print(f"✅ Domain: {result.get('domain')}")
        print(f"✅ Status: {result.get('status')}")
        print(f"✅ Validation Passed: {result.get('validation_passed', 'N/A')}")
        
        summary = result.get('summary', {})
        print(f"\n📄 Summary:")
        print(f"   - Content: {summary.get('content_extracted', 0)} caractere")
        print(f"   - Vectors: {summary.get('vectors_saved', 0)}")
        print(f"   - Memory: {'✅' if summary.get('memory_configured') else '❌'}")
        print(f"   - Qwen: {'✅' if summary.get('qwen_integrated') else '❌'}")
        
        # Verifică în baza de date
        agent = db.site_agents.find_one({"_id": ObjectId(result['agent_id'])})
        content_count = db.site_content.count_documents({"agent_id": ObjectId(result['agent_id'])})
        services_count = len(agent.get('services', []))
        
        print(f"\n🔍 Verificare baza de date:")
        print(f"   - Content chunks în MongoDB: {content_count}")
        print(f"   - Servicii detectate: {services_count}")
        print(f"   - Status final: {agent.get('status')}")
        print(f"   - Validation passed: {agent.get('validation_passed', 'N/A')}")
        
        # Verificare finală
        print("\n" + "="*70)
        if result.get('validation_passed'):
            print("✅✅✅ TEST REUȘIT - AGENT VALID ȘI FUNCȚIONAL! ✅✅✅")
        else:
            print("⚠️  TEST PARȚIAL - Agent creat dar incomplet")
            if agent.get('validation_errors'):
                print(f"   Erori: {agent.get('validation_errors')}")
        print("="*70)
        
        return result.get('validation_passed', False)
        
    except Exception as e:
        print(f"\n❌ EROARE LA TEST: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_improved_creation())
    sys.exit(0 if success else 1)

