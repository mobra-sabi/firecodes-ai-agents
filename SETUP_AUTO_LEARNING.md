# 🧠 SETUP ÎNVĂȚARE AUTOMATĂ - COMENZI PAS CU PAS

## ✅ Structura creată

Toate fișierele au fost create. Acum rulează comenzile în ordine:

---

## 🧩 PAS 1: VERIFICĂ STRUCTURA

```bash
cd /srv/hf/ai_agents
ls -la data_collector/ fine_tuning/ rag_updater/ datasets/ logs/
```

---

## 🧩 PAS 2: TEST COLECTOR DE DATE

```bash
python3 /srv/hf/ai_agents/data_collector/collector.py
```

**Așteptat:** Mesaj "✅ Test interaction saved with ID: ..."

---

## 🧩 PAS 3: VERIFICĂ MONGODB

```bash
mongosh
use adbrain_ai
db.interactions.find().limit(3).pretty()
exit
```

**Așteptat:** Vezi interacțiunile salvate

---

## 🧩 PAS 4: TEST ORCHESTRATOR CU SALVARE

```bash
cd /srv/hf/ai_agents
python3 << 'EOF'
from llm_orchestrator import get_orchestrator

orch = get_orchestrator()
result = orch.chat([
    {"role": "user", "content": "Explică în 2 propoziții ce este protecția anticorozivă."}
])

print(f"Provider: {result.get('provider')}")
print(f"Success: {result.get('success')}")
print(f"Response: {result.get('content', '')[:200]}")
EOF
```

**Așteptat:** Interacțiunea este salvată automat în MongoDB

---

## 🧩 PAS 5: VERIFICĂ INTERACȚIUNI SALVATE

```bash
mongosh --quiet --eval "db.getSiblingDB('adbrain_ai').interactions.countDocuments()"
```

**Așteptat:** Număr > 0

---

## 🧩 PAS 6: EXPORT DATE ÎN JSONL

```bash
python3 /srv/hf/ai_agents/fine_tuning/build_jsonl.py
```

**Așteptat:** 
- Dacă ai < 100 interacțiuni: "⚠️ Not enough data"
- Dacă ai >= 100: "✅ Created JSONL dataset"

---

## 🧩 PAS 7: VERIFICĂ FIȘIER JSONL

```bash
ls -lh /srv/hf/ai_agents/datasets/training_data.jsonl
wc -l /srv/hf/ai_agents/datasets/training_data.jsonl
```

**Așteptat:** Fișier JSONL creat cu linii de date

---

## 🧩 PAS 8: RULEAZĂ FINE-TUNING (OPȚIONAL - DOAR DACĂ AI >= 100 INTERACȚIUNI)

```bash
bash /srv/hf/ai_agents/fine_tuning/train_qwen.sh
```

**Notă:** Acest pas durează mult (ore) și necesită GPU-uri. Poți să-l rulezi mai târziu.

---

## 🧩 PAS 9: ACTUALIZEAZĂ QDRANT

```bash
python3 /srv/hf/ai_agents/rag_updater/update_qdrant.py
```

**Așteptat:** "✅ Updated Qdrant collection with X new points"

---

## 🧩 PAS 10: VERIFICĂ QDRANT

```bash
curl http://127.0.0.1:6333/collections/mem_auto
```

**Așteptat:** JSON cu informații despre colecție

---

## 🧩 PAS 11: CONFIGUREAZĂ CRON PENTRU ÎNVĂȚARE AUTOMATĂ ZILNIC

```bash
crontab -e
```

**Adaugă linia:**
```
0 3 * * * cd /srv/hf/ai_agents && python3 fine_tuning/build_jsonl.py && bash fine_tuning/train_qwen.sh >> logs/fine_tune.log 2>&1 && python3 rag_updater/update_qdrant.py >> logs/qdrant_update.log 2>&1
```

**Salvează:** `Ctrl+X`, apoi `Y`, apoi `Enter`

**Explicare:** Rulează zilnic la 3:00 AM:
1. Export JSONL
2. Fine-tuning (dacă ai suficiente date)
3. Update Qdrant

---

## 🧩 PAS 12: VERIFICĂ CRON

```bash
crontab -l
```

**Așteptat:** Vezi linia adăugată

---

## 🧩 PAS 13: TEST CICLU COMPLET MANUAL

```bash
cd /srv/hf/ai_agents
python3 fine_tuning/build_jsonl.py
bash fine_tuning/train_qwen.sh
python3 rag_updater/update_qdrant.py
```

**Așteptat:** Toate cele 3 pași rulează cu succes

---

## 📊 VERIFICĂRI FINALE

### Verifică MongoDB:
```bash
mongosh --quiet --eval "db.getSiblingDB('adbrain_ai').interactions.countDocuments()"
```

### Verifică JSONL:
```bash
ls -lh /srv/hf/ai_agents/datasets/training_data.jsonl
```

### Verifică Qdrant:
```bash
curl -s http://127.0.0.1:6333/collections/mem_auto | python3 -m json.tool | grep points_count
```

### Verifică Model Fine-Tuned (dacă ai rulat):
```bash
ls -lh /srv/hf/ai_agents/fine_tuning/output/
```

---

## 🎯 REZUMAT

✅ **Sistemul de învățare automată este configurat!**

**Ce se întâmplă acum:**
1. **Orchestratorul** salvează automat toate interacțiunile în MongoDB
2. **Zilnic la 3:00 AM** (cron):
   - Export JSONL din MongoDB
   - Fine-tuning Qwen (dacă ai >= 100 interacțiuni)
   - Update Qdrant cu noile interacțiuni
3. **Modelul se îmbunătățește continuu** cu fiecare interacțiune

**Fișiere importante:**
- `/srv/hf/ai_agents/data_collector/collector.py` - Salvează interacțiuni
- `/srv/hf/ai_agents/fine_tuning/build_jsonl.py` - Export JSONL
- `/srv/hf/ai_agents/fine_tuning/train_qwen.sh` - Fine-tuning
- `/srv/hf/ai_agents/rag_updater/update_qdrant.py` - Update Qdrant
- `/srv/hf/ai_agents/llm_orchestrator.py` - Modificat pentru salvare automată

---

## 🐛 TROUBLESHOOTING

### MongoDB nu răspunde:
```bash
sudo systemctl status mongod
sudo systemctl start mongod
```

### Qdrant nu răspunde:
```bash
docker ps | grep qdrant
# sau
systemctl status qdrant
```

### Nu sunt suficiente date:
- Așteaptă să se acumuleze interacțiuni (orchestratorul le salvează automat)
- Verifică: `mongosh --quiet --eval "db.getSiblingDB('adbrain_ai').interactions.countDocuments()"`

### Fine-tuning eșuează:
- Verifică GPU-uri: `nvidia-smi`
- Verifică spațiu disk: `df -h`
- Verifică logs: `tail -f /srv/hf/ai_agents/logs/fine_tune.log`


