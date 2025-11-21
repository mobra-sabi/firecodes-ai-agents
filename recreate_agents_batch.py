#!/usr/bin/env python3
"""
🔄 RECREARE AUTOMATĂ AGENȚI NON-CONFORMI
=========================================

Recrează toți agenții non-conformi folosind construction_agent_creator.py
cu GPU chunks și DeepSeek orchestrator.
"""

import json
import subprocess
import os
import time
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

def delete_old_agent(agent_id: str, domain: str):
    """Șterge agentul vechi din MongoDB"""
    mongo = MongoClient("mongodb://localhost:27017/")
    db = mongo.ai_agents_db
    
    result = db.site_agents.delete_one({"_id": ObjectId(agent_id)})
    if result.deleted_count > 0:
        print(f"   ✅ Agent vechi șters din MongoDB")
    else:
        print(f"   ⚠️ Agent nu a fost găsit în MongoDB")

def recreate_agent(domain: str, url: str, agent_id: str, index: int, total: int):
    """Recrează un agent folosind construction_agent_creator.py"""
    
    print(f"\n{'='*80}")
    print(f"🔄 [{index}/{total}] RECREARE: {domain}")
    print(f"{'='*80}")
    print(f"   URL: {url}")
    print(f"   ID vechi: {agent_id}")
    print(f"   Timp start: {datetime.now().strftime('%H:%M:%S')}")
    
    try:
        # 1. Șterge agentul vechi
        delete_old_agent(agent_id, domain)
        
        # 2. Creează agent nou cu GPU chunks
        env = {
            **os.environ,
            "MONGODB_URI": "mongodb://localhost:27017",
            "QDRANT_URL": "http://localhost:9306"
        }
        
        print(f"\n   🚀 Pornesc construction_agent_creator.py...")
        
        result = subprocess.run(
            ['python3', '/srv/hf/ai_agents/tools/construction_agent_creator.py', '--url', url, '--mode', 'create_agent'],
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout
            env=env
        )
        
        # Log output
        if result.stdout:
            print(f"\n   📋 STDOUT:")
            for line in result.stdout.split('\n')[-20:]:  # Last 20 lines
                if line.strip():
                    print(f"      {line}")
        
        if result.stderr and result.returncode != 0:
            print(f"\n   ⚠️ STDERR:")
            for line in result.stderr.split('\n')[-10:]:  # Last 10 lines
                if line.strip():
                    print(f"      {line}")
        
        if result.returncode == 0:
            print(f"\n   ✅ SUCCES! Agent recreat cu GPU chunks")
            
            # Verifică în MongoDB
            mongo = MongoClient("mongodb://localhost:27017/")
            db = mongo.ai_agents_db
            new_agent = db.site_agents.find_one({"domain": domain}, sort=[("created_at", -1)])
            
            if new_agent:
                print(f"   ✅ Găsit în MongoDB:")
                print(f"      New ID: {new_agent['_id']}")
                print(f"      Chunks: {new_agent.get('chunks_indexed', 0)}")
                print(f"      Status: {new_agent.get('status', 'N/A')}")
                print(f"      Has embeddings: {new_agent.get('has_embeddings', False)}")
                return True
            else:
                print(f"   ⚠️ Agent recreat dar nu găsit în MongoDB!")
                return False
        else:
            print(f"\n   ❌ EROARE! Exit code: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n   ❌ TIMEOUT! Agent a depășit 10 minute")
        return False
    except Exception as e:
        print(f"\n   ❌ EXCEPȚIE: {e}")
        return False

def main():
    """Main recreare batch"""
    
    print("=" * 80)
    print("🔄 RECREARE AUTOMATĂ AGENȚI NON-CONFORMI")
    print("=" * 80)
    print(f"⏰ Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load agents to recreate
    with open('/tmp/agents_to_recreate.json', 'r') as f:
        agents = json.load(f)
    
    print(f"\n📊 Total agenți de recreat: {len(agents)}")
    print(f"⏱️ Timp estimat: ~{len(agents) * 5} minute ({len(agents) * 5 / 60:.1f} ore)")
    
    # Confirmă
    response = input(f"\n⚠️ Vrei să recreezi toți {len(agents)} agenți? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Anulat de user")
        return
    
    # Statistici
    stats = {
        "total": len(agents),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "start_time": time.time()
    }
    
    # Recrează fiecare agent
    for idx, agent in enumerate(agents, 1):
        success = recreate_agent(
            agent['domain'],
            agent['url'],
            agent['agent_id'],
            idx,
            len(agents)
        )
        
        if success:
            stats["success"] += 1
        else:
            stats["failed"] += 1
        
        # Pauză între agenți (prevent rate limit)
        if idx < len(agents):
            print(f"\n   ⏸️ Pauză 5 secunde...")
            time.sleep(5)
    
    # Raport final
    elapsed = time.time() - stats["start_time"]
    
    print(f"\n{'='*80}")
    print(f"📊 RAPORT FINAL RECREARE")
    print(f"{'='*80}")
    print(f"   Total agenți: {stats['total']}")
    print(f"   ✅ Succese: {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
    print(f"   ❌ Eșuări: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
    print(f"   ⏱️ Timp total: {elapsed/60:.1f} minute")
    print(f"   ⏰ Timp mediu/agent: {elapsed/len(agents):.1f} secunde")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()

