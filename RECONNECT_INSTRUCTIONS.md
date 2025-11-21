# 📋 Instrucțiuni pentru Reconectare - Creare Agenți

## ✅ Procesul Rulează în Background

**IMPORTANT**: Procesul de creare a agenților rulează în **background** și va continua chiar dacă te deconectezi de la server. Nu trebuie să reîncepi procesul!

---

## 🔍 Când Te Reconectezi - Verifică Statusul

### Opțiunea 1: Script Automat (Recomandat)
```bash
cd /srv/hf/ai_agents
./check_agent_creation_status.sh
```

### Opțiunea 2: Verificare Manuală

#### 1. Verifică Statusul în MongoDB
```bash
cd /srv/hf/ai_agents
python3 << 'EOF'
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
load_dotenv()

client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27018/'))
db = client[os.getenv('MONGODB_DATABASE', 'construction_agents')]

# Găsește competitive map-ul activ
maps = list(db.competitive_map.find({}).sort('updated_at', -1).limit(1))
if maps:
    m = maps[0]
    master_id = m.get('master_agent_id')
    if isinstance(master_id, ObjectId):
        master_id = str(master_id)
    
    print(f"Master Agent ID: {master_id}")
    print(f"Status: {m.get('agent_creation_status', 'not_started')}")
    progress = m.get('agent_creation_progress', {})
    if progress:
        print(f"Progres: {progress.get('completed', 0)}/{progress.get('total', 0)} ({progress.get('percentage', 0)}%)")
    print(f"Agenți creați: {m.get('slave_agents_created', 0)}")
    sites = m.get('competitive_map', [])
    print(f"Total site-uri: {len(sites)}")
    print(f"Cu agenți: {len([s for s in sites if s.get('has_agent')])}")
EOF
```

#### 2. Verifică Logurile Recente
```bash
cd /srv/hf/ai_agents
tail -n 50 logs/backend.log | grep -E "Starting parallel|Processing batch|Created agent|Failed|Error|completed"
```

#### 3. Verifică Dacă Backend-ul Rulează
```bash
ps aux | grep -E "uvicorn.*agent_api" | grep -v grep
```

---

## 📊 Interpretare Status

### Status: `in_progress`
- ✅ **Procesul continuă normal**
- Nu face nimic, doar verifică progresul în frontend
- Progresul se actualizează automat în MongoDB

### Status: `completed`
- ✅ **Toți agenții au fost creați cu succes**
- Verifică în frontend lista de agenți creați
- Numărul de agenți creați: `slave_agents_created`

### Status: `failed`
- ❌ **Procesul a eșuat**
- Verifică logurile pentru detalii: `tail -n 100 logs/backend.log | grep -i error`
- Verifică eroarea în MongoDB: `m.get('error')`
- **DOAR ATUNCI** repornește procesul pentru site-urile care nu au agenți

### Status: `not_started`
- ⚠️ **Procesul nu a pornit sau s-a oprit**
- Verifică logurile pentru a vedea de ce
- Dacă e necesar, repornește procesul din frontend

---

## 🔄 Dacă Trebuie Să Repornești Procesul

**ATENȚIE**: Repornește procesul **DOAR** dacă:
1. Statusul este `failed` sau `not_started`
2. Procesul s-a oprit complet (nu mai vezi activitate în loguri)
3. Vrei să procesezi site-uri noi care nu au fost selectate anterior

**NU reporni procesul dacă:**
- Statusul este `in_progress` (procesul continuă)
- Statusul este `completed` (procesul s-a terminat cu succes)

---

## 📈 Monitorizare Live

### Pentru progres live în timp real:
```bash
cd /srv/hf/ai_agents
tail -f logs/backend.log | grep -E "Created agent|Processing batch|Failed|Error"
```

### Pentru a vedea toate mesajele:
```bash
cd /srv/hf/ai_agents
tail -f logs/backend.log
```

---

## 🎯 Frontend

În frontend, progresul se actualizează automat:
- Card verde cu bara de progres: "Creating Agents... X/Y (Z%)"
- Actualizare la fiecare 2 secunde când procesul este activ
- Nu trebuie să reîmprospătezi manual pagina

---

## ⚡ Comenzi Rapide

```bash
# Verificare rapidă status
cd /srv/hf/ai_agents && ./check_agent_creation_status.sh

# Verificare loguri recente
tail -n 30 /srv/hf/ai_agents/logs/backend.log | grep -E "Created agent|Processing batch"

# Verificare backend
ps aux | grep uvicorn | grep agent_api
```

---

## 📝 Notă Importantă

**Procesul rulează în thread-uri daemon în background**, deci:
- ✅ Continuă chiar dacă te deconectezi
- ✅ Nu se oprește când închizi terminalul
- ✅ Se oprește doar dacă backend-ul se oprește sau apare o eroare fatală

**Dacă backend-ul se oprește**, procesul se oprește și trebuie repornit backend-ul și apoi procesul de creare a agenților.

