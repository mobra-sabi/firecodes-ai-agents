#!/usr/bin/env python3
"""Monitor progres recreare agenți cu update la 5 minute"""

import time
from pymongo import MongoClient
from datetime import datetime, timedelta
import subprocess

def check_progress():
    """Verifică progresul în MongoDB"""
    mongo = MongoClient("mongodb://localhost:27017/")
    db = mongo.ai_agents_db
    
    # Agenți creați în ultimele 2 ore
    recent_time = datetime.now() - timedelta(hours=2)
    
    # Agenți conformi
    conforming = list(db.site_agents.find({
        "has_embeddings": True,
        "chunks_indexed": {"$gte": 50},
        "validation_passed": True,
        "status": {"$in": ["validated", "ready"]},
        "agent_type": "master"
    }, {"domain": 1, "chunks_indexed": 1, "created_at": 1}))
    
    # Agenți recent creați
    recent = list(db.site_agents.find(
        {"created_at": {"$gte": recent_time}},
        {"domain": 1, "chunks_indexed": 1, "status": 1, "created_at": 1}
    ).sort([("created_at", -1)]).limit(10))
    
    # Total
    total = db.site_agents.count_documents({})
    
    return {
        "total": total,
        "conforming": len(conforming),
        "conforming_agents": conforming,
        "recent": recent,
        "timestamp": datetime.now()
    }

def is_script_running():
    """Verifică dacă scriptul încă rulează"""
    result = subprocess.run(['pgrep', '-f', 'recreate_agents_batch.py'], capture_output=True)
    return result.returncode == 0

print("=" * 80)
print("🔄 MONITOR RECREARE AGENȚI - UPDATE LA 5 MINUTE")
print("=" * 80)
print(f"⏰ Start monitoring: {datetime.now().strftime('%H:%M:%S')}")
print()

iteration = 0
start_conforming = None

while True:
    iteration += 1
    progress = check_progress()
    
    if start_conforming is None:
        start_conforming = progress['conforming']
    
    print(f"\n{'='*80}")
    print(f"📊 UPDATE #{iteration} - {progress['timestamp'].strftime('%H:%M:%S')}")
    print(f"{'='*80}")
    
    print(f"\n📈 PROGRES GENERAL:")
    print(f"   Total agenți în DB: {progress['total']}")
    print(f"   ✅ Conformi: {progress['conforming']} (+{progress['conforming'] - start_conforming} față de start)")
    print(f"   📊 Rată conformitate: {progress['conforming']/progress['total']*100:.1f}%")
    
    if progress['recent']:
        print(f"\n🆕 ULTIMII {len(progress['recent'])} AGENȚI CREAȚI:")
        for idx, agent in enumerate(progress['recent'], 1):
            created = agent.get('created_at', datetime.now())
            age_min = int((datetime.now() - created).total_seconds() / 60)
            print(f"   {idx:2d}. {agent['domain']}")
            print(f"       Chunks: {agent.get('chunks_indexed', 0)}, Status: {agent.get('status', 'N/A')}")
            print(f"       Creat: acum {age_min} minute")
    
    if progress['conforming_agents']:
        print(f"\n✅ TOP 5 AGENȚI CONFORMI:")
        for idx, agent in enumerate(progress['conforming_agents'][:5], 1):
            print(f"   {idx}. {agent['domain']}: {agent.get('chunks_indexed', 0)} chunks")
    
    # Check dacă scriptul încă rulează
    if not is_script_running():
        print(f"\n{'='*80}")
        print(f"✅ SCRIPT TERMINAT!")
        print(f"{'='*80}")
        print(f"\n📊 STATISTICI FINALE:")
        print(f"   Agenți conformi la start: {start_conforming}")
        print(f"   Agenți conformi la final: {progress['conforming']}")
        print(f"   ✅ Agenți recreați cu succes: {progress['conforming'] - start_conforming}")
        print(f"   📊 Rată finală conformitate: {progress['conforming']/progress['total']*100:.1f}%")
        break
    
    print(f"\n⏳ Următorul update în 5 minute (la {(datetime.now() + timedelta(minutes=5)).strftime('%H:%M:%S')})...")
    print(f"   Status script: 🔄 RUNNING")
    
    time.sleep(300)  # 5 minute

print(f"\n{'='*80}")
print(f"🏁 MONITORING TERMINAT")
print(f"{'='*80}")

