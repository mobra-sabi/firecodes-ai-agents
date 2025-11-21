#!/usr/bin/env python3
"""
Monitorizare completă transformare industrie - verifică MongoDB + Qdrant + chunks
"""
import time
from datetime import datetime
from pymongo import MongoClient

# Configurare
MONGO_URI = "mongodb://localhost:27017"

def check_qdrant():
    """Verifică Qdrant dacă este disponibil"""
    try:
        from qdrant_client import QdrantClient
        qdrant = QdrantClient(url="http://localhost:6333", timeout=2)
        collections = qdrant.get_collections().collections
        return qdrant, collections
    except:
        return None, []

def count_chunks_in_qdrant(qdrant, collections, agent_id):
    """Numără chunks pentru un agent în Qdrant"""
    if not qdrant:
        return 0
    
    total = 0
    for coll in collections:
        try:
            # Caută chunks pentru acest agent
            result = qdrant.scroll(
                collection_name=coll.name,
                scroll_filter={
                    "must": [{
                        "key": "agent_id",
                        "match": {"value": str(agent_id)}
                    }]
                },
                limit=1000
            )
            if result[0]:
                total += len(result[0])
        except:
            pass
    return total

def main():
    print("=" * 80)
    print("📊 MONITORIZARE TRANSFORMARE COMPLETĂ")
    print("=" * 80)
    print(f"⏰ Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Conectare
    mongo = MongoClient(MONGO_URI)
    db = mongo["ai_agents_db"]
    
    # Verifică Qdrant
    qdrant, collections = check_qdrant()
    if qdrant:
        print("✅ Qdrant: CONECTAT")
    else:
        print("⚠️ Qdrant: NU DISPONIBIL (monitorizare fără verificare chunks)")
    print()
    
    start_time = time.time()
    last_pending = -1
    last_created = -1
    stuck_count = 0
    
    while True:
        try:
            # Statistici
            total_companies = db.construction_companies_discovered.count_documents({})
            pending = db.construction_companies_discovered.count_documents({"status": "pending"})
            created = db.construction_companies_discovered.count_documents({"status": "agent_created"})
            
            # Agenți
            total_agents = db.site_agents.count_documents({
                "is_slave": {"$ne": True},
                "industry": {"$regex": "construct", "$options": "i"}
            })
            
            # Chunks (dacă Qdrant disponibil)
            total_chunks = 0
            agents_with_chunks = 0
            if qdrant:
                agents_sample = list(db.site_agents.find({
                    "is_slave": {"$ne": True},
                    "industry": {"$regex": "construct", "$options": "i"}
                }).limit(50))
                
                for agent in agents_sample:
                    agent_id = agent["_id"]
                    chunks = count_chunks_in_qdrant(qdrant, collections, agent_id)
                    if chunks > 0:
                        agents_with_chunks += 1
                        total_chunks += chunks
            
            # Timp
            elapsed = time.time() - start_time
            elapsed_min = int(elapsed / 60)
            elapsed_sec = int(elapsed % 60)
            
            # Progress
            if total_companies > 0:
                progress = (created / total_companies) * 100
            else:
                progress = 0
            
            # Status
            if pending == 0 and created > 0:
                status = "✅ COMPLET"
            elif pending == last_pending and created == last_created:
                stuck_count += 1
                if stuck_count > 6:  # 1 minut fără progres
                    status = "⚠️ BLOcat"
                else:
                    status = "🔄 RUNNING"
            else:
                stuck_count = 0
                status = "🔄 RUNNING"
            
            # Display
            print(f"\r[{elapsed_min:02d}:{elapsed_sec:02d}] {status} | "
                  f"Companii: {total_companies} (Pending: {pending}, Created: {created}) | "
                  f"Agenți: {total_agents}", end="", flush=True)
            
            if qdrant:
                print(f" | Chunks: {total_chunks} ({agents_with_chunks} agenți cu chunks)", end="", flush=True)
            
            print(f" | Progress: {progress:.1f}%", end="", flush=True)
            
            # Verifică finalizare
            if pending == 0 and created > 0:
                print("\n\n" + "=" * 80)
                print("✅ TRANSFORMARE COMPLETĂ!")
                print("=" * 80)
                print(f"⏰ Finalizat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⏱️ Durată: {elapsed_min} minute {elapsed_sec} secunde")
                print(f"📊 Total companii: {total_companies}")
                print(f"✅ Agenți creați: {created}")
                print(f"🤖 Total agenți în DB: {total_agents}")
                
                if qdrant:
                    print(f"📦 Total chunks în Qdrant: {total_chunks}")
                    print(f"✅ Agenți cu chunks: {agents_with_chunks}")
                    
                    # Verificare detaliată
                    print("\n🔍 VERIFICARE INTEGRITATE:")
                    agents_all = list(db.site_agents.find({
                        "is_slave": {"$ne": True},
                        "industry": {"$regex": "construct", "$options": "i"}
                    }))
                    
                    with_chunks = 0
                    without_chunks = 0
                    for agent in agents_all:
                        chunks = count_chunks_in_qdrant(qdrant, collections, agent["_id"])
                        if chunks > 0:
                            with_chunks += 1
                        else:
                            without_chunks += 1
                    
                    print(f"   ✅ Agenți cu chunks: {with_chunks}")
                    if without_chunks > 0:
                        print(f"   ⚠️ Agenți fără chunks: {without_chunks}")
                else:
                    print("⚠️ Qdrant nu este disponibil - nu se pot verifica chunks")
                
                print("\n" + "=" * 80)
                print("✅ TOATE AGENȚII SUNT CREAȚI COMPLET!")
                print("=" * 80)
                break
            
            last_pending = pending
            last_created = created
            
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Oprire manuală")
            break
        except Exception as e:
            print(f"\n❌ Eroare: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()

