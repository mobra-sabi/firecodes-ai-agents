#!/usr/bin/env python3
"""
Script pentru a corecta și reprocesa agenții conform planului
"""

import asyncio
import sys
import os
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from ceo_master_workflow import CEOMasterWorkflow

async def fix_and_reprocess_agents():
    """
    Corectează agenții și reprocesează master agenții fără chunks
    """
    client = MongoClient("mongodb://localhost:27017/")
    db = client["ai_agents_db"]
    
    print("🔧 CORECTARE ȘI REPROCESARE AGENȚI\n")
    
    # 1. Corectează structura agenților
    print("1️⃣ Corectare structură agenți...")
    
    # Agenți cu master_agent_id dar fără is_slave
    fixed_slave = db.site_agents.update_many(
        {
            "master_agent_id": {"$exists": True, "$ne": None},
            "is_slave": {"$ne": True}
        },
        {
            "$set": {
                "is_slave": True,
                "agent_type": "slave",
                "last_updated": datetime.now(timezone.utc)
            }
        }
    )
    print(f"   ✅ {fixed_slave.modified_count} agenți marcați ca slave")
    
    # Agenți fără created_at
    agents_no_created = list(db.site_agents.find({
        "$or": [
            {"created_at": {"$exists": False}},
            {"created_at": None}
        ]
    }))
    
    for agent in agents_no_created:
        agent_id = agent.get("_id")
        if isinstance(agent_id, ObjectId):
            created_time = agent_id.generation_time
        else:
            created_time = datetime.now(timezone.utc)
        
        db.site_agents.update_one(
            {"_id": agent_id},
            {
                "$set": {
                    "created_at": created_time,
                    "last_updated": datetime.now(timezone.utc)
                }
            }
        )
    print(f"   ✅ {len(agents_no_created)} agenți cu created_at adăugat")
    
    # Agenți fără site_url
    agents_no_url = list(db.site_agents.find({
        "$or": [
            {"site_url": {"$exists": False}},
            {"site_url": None},
            {"site_url": ""}
        ]
    }))
    
    for agent in agents_no_url:
        domain = agent.get("domain", "")
        if domain:
            site_url = f"https://{domain}" if not domain.startswith("www.") else f"https://{domain}"
            db.site_agents.update_one(
                {"_id": agent.get("_id")},
                {
                    "$set": {
                        "site_url": site_url,
                        "last_updated": datetime.now(timezone.utc)
                    }
                }
            )
    print(f"   ✅ {len(agents_no_url)} agenți cu site_url adăugat\n")
    
    # 2. Găsește master agenții fără chunks
    print("2️⃣ Găsire master agenți fără chunks...")
    master_agents_no_chunks = list(db.site_agents.find({
        "is_slave": {"$ne": True},
        "chunks_indexed": {"$in": [0, None]}
    }))
    
    print(f"   📊 Găsiți {len(master_agents_no_chunks)} master agenți fără chunks\n")
    
    if not master_agents_no_chunks:
        print("✅ Toți master agenții au chunks! Nu este nevoie de reprocesare.")
        return
    
    # 3. Reprocesează master agenții fără chunks
    print("3️⃣ Reprocesare master agenți fără chunks...\n")
    
    workflow = CEOMasterWorkflow()
    
    for agent in master_agents_no_chunks:
        domain = agent.get("domain", "N/A")
        site_url = agent.get("site_url", "")
        agent_id = str(agent.get("_id"))
        status = agent.get("status", "unknown")
        
        if not site_url:
            print(f"   ⚠️ {domain}: Nu are site_url, skip")
            continue
        
        print(f"   🔄 Reprocesare: {domain}")
        print(f"      URL: {site_url}")
        print(f"      Status: {status}")
        
        try:
            # Rulează workflow complet
            result = await workflow.execute_full_workflow(
                site_url=site_url,
                results_per_keyword=15,
                parallel_gpu_agents=5
            )
            
            if result.get("status") == "completed":
                print(f"      ✅ {domain}: Workflow completat cu succes")
                print(f"         Master Agent: {result.get('master_agent_id')}")
                print(f"         Slave Agents: {result.get('slave_agents_count', 0)}")
            else:
                print(f"      ❌ {domain}: Workflow failed - {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"      ❌ {domain}: Eroare - {str(e)}")
        
        print()
    
    print("✅ REPROCESARE COMPLETĂ!")

if __name__ == "__main__":
    asyncio.run(fix_and_reprocess_agents())

