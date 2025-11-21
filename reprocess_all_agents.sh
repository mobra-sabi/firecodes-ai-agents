#!/usr/bin/bash
###########################################
# REPROCESARE AUTOMATĂ TOȚI AGENȚII
# Generează embeddings și indexează conținut
###########################################

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  🔄 REPROCESARE AUTOMATĂ - TOȚI AGENȚII                             ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Verifică că Qdrant rulează
if ! curl -s http://localhost:9306/ > /dev/null 2>&1; then
    echo "❌ Qdrant nu rulează pe portul 9306!"
    echo "   Pornește-l cu: docker start qdrant"
    exit 1
fi

echo "✅ Qdrant rulează pe portul 9306"
echo ""

# Obține toți agenții din MongoDB
python3 << 'PYEOF'
from pymongo import MongoClient
from bson import ObjectId
import subprocess
import time

client = MongoClient('mongodb://localhost:27017/')
db = client['ai_agents_db']

# Găsește agenții fără date complete
agents = list(db.site_agents.find({
    '$or': [
        {'pages_indexed': {'$exists': False}},
        {'pages_indexed': 0},
        {'chunks_indexed': 0}
    ]
}).limit(10))  # Max 10 agenți per batch

print(f"📊 Găsiți {len(agents)} agenți de reprocesare")
print("=" * 70)

for i, agent in enumerate(agents, 1):
    agent_id = str(agent['_id'])
    domain = agent.get('domain', 'N/A')
    site_url = agent.get('site_url', f"https://{domain}")
    
    print(f"\n{i}/{len(agents)}. Reprocesez: {domain}")
    print(f"   URL: {site_url}")
    
    try:
        # Rulează construction_agent_creator
        result = subprocess.run(
            ['timeout', '300', 'python3', '/srv/hf/ai_agents/tools/construction_agent_creator.py', 
             '--url', site_url, '--mode', 'create_agent'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"   ✅ Success")
        elif result.returncode == 124:
            print(f"   ⏱️  Timeout (5 min) - continuă cu următorul")
        else:
            print(f"   ⚠️  Exit code: {result.returncode}")
            
    except Exception as e:
        print(f"   ❌ Eroare: {e}")
    
    # Pauză între agenți
    time.sleep(2)

print("\n" + "=" * 70)
print("✅ BATCH COMPLET!")
PYEOF

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  ✅ REPROCESARE FINALIZATĂ                                          ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

