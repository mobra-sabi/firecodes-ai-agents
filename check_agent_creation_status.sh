#!/bin/bash
# Script pentru verificarea statusului creării agenților după reconectare

echo "=== VERIFICARE STATUS CREARE AGENȚI ==="
echo ""

# Verifică statusul în MongoDB
cd /srv/hf/ai_agents
python3 << 'EOF'
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

# Folosește variabilele de mediu sau valorile default
mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27018/')
mongodb_db = os.getenv('MONGODB_DATABASE', 'construction_agents')

# Dacă nu sunt setate, încearcă să le citească din .env manual
if mongodb_uri == 'mongodb://localhost:27018/':
    try:
        env_path = '/srv/hf/ai_agents/.env'
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('MONGODB_URI='):
                        mongodb_uri = line.split('=', 1)[1].strip().strip('"').strip("'")
                    elif line.startswith('MONGODB_DATABASE='):
                        mongodb_db = line.split('=', 1)[1].strip().strip('"').strip("'")
    except:
        pass

client = MongoClient(mongodb_uri)
db = client[mongodb_db]

# Verifică toate competitive maps-urile
maps = list(db.competitive_map.find({}).sort('updated_at', -1).limit(5))

if maps:
    for i, m in enumerate(maps, 1):
        master_id = m.get('master_agent_id')
        if isinstance(master_id, ObjectId):
            master_id = str(master_id)
        
        print(f"\n=== Competitive Map {i} ===")
        print(f"Master Agent ID: {master_id}")
        print(f"Status creare: {m.get('agent_creation_status', 'not_started')}")
        
        progress = m.get('agent_creation_progress', {})
        if progress:
            completed = progress.get('completed', 0)
            total = progress.get('total', 0)
            percentage = progress.get('percentage', 0)
            print(f"Progres: {completed}/{total} ({percentage}%)")
        else:
            print("Progres: N/A")
        
        print(f"Agenți creați: {m.get('slave_agents_created', 0)}")
        sites = m.get('competitive_map', [])
        print(f"Total site-uri: {len(sites)}")
        print(f"Selectate: {len([s for s in sites if s.get('selected')])}")
        print(f"Cu agenți: {len([s for s in sites if s.get('has_agent')])}")
        print(f"Ultima actualizare: {m.get('updated_at')}")
        
        # Verifică dacă procesul este în progres
        status = m.get('agent_creation_status', 'not_started')
        if status == 'in_progress':
            print("⚠️  Procesul este în curs! Verifică logurile pentru progres live.")
        elif status == 'completed':
            print("✅ Procesul este complet!")
        elif status == 'failed':
            print("❌ Procesul a eșuat! Verifică logurile pentru detalii.")
            if m.get('error'):
                print(f"   Eroare: {m.get('error')}")
else:
    print("Nu există competitive maps în baza de date")
EOF

echo ""
echo "=== VERIFICARE LOGURI RECENTE ==="
echo ""
echo "Ultimele mesaje din loguri:"
tail -n 30 /srv/hf/ai_agents/logs/backend.log | grep -E "Starting parallel|Processing batch|Created agent|Failed|Error|completed|percentage|SLAVE agent" | tail -10

echo ""
echo "=== VERIFICARE PROCES BACKEND ==="
if pgrep -f "uvicorn.*agent_api" > /dev/null; then
    echo "✅ Backend-ul rulează"
    ps aux | grep -E "uvicorn.*agent_api" | grep -v grep | head -1
else
    echo "❌ Backend-ul NU rulează! Trebuie repornit."
fi

echo ""
echo "=== INSTRUCȚIUNI ==="
echo "1. Dacă statusul este 'in_progress': procesul continuă, doar verifică progresul în frontend"
echo "2. Dacă statusul este 'completed': toți agenții au fost creați cu succes"
echo "3. Dacă statusul este 'failed': verifică logurile pentru erori și repornește procesul"
echo "4. Pentru progres live: tail -f /srv/hf/ai_agents/logs/backend.log | grep -E 'Created agent|Processing batch'"

