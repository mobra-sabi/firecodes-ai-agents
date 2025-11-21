# 🎨 Auto-Learning Dashboard UI

## 🚀 Pornire Rapidă

```bash
cd /srv/hf/ai_agents/auto_learning_ui
bash start_ui.sh
```

Apoi deschide în browser:
```
http://localhost:5001
```

---

## 📊 Ce Vezi în Dashboard

### 1. **Stat Cards (Top)**
- **Interacțiuni Totale** - Total în MongoDB
- **Interacțiuni Astăzi** - Ultimele 24h
- **Dataset JSONL** - Linii și mărime
- **Qdrant Points** - Puncte în colecție

### 2. **Acțiuni (Butoane)**
- 🧪 **Test Orchestrator** - Generează o interacțiune de test
- 📊 **Build JSONL** - Export date din MongoDB în JSONL
- 🔄 **Update Qdrant** - Actualizează baza vectorială
- 🔃 **Refresh All** - Reîncarcă toate datele

### 3. **Status Sisteme**
- 📊 Dataset JSONL (există/nu există, linii, mărime)
- 🎯 Fine-Tuning (model există/nu există)
- 🔍 Qdrant (conectat/offline, număr points)

### 4. **Interacțiuni Recente**
- Tabel cu ultimele 10 interacțiuni
- Timestamp, Provider, Topic, Tokens, Status

### 5. **Orchestrator Statistics**
- Total calls, success rate
- Statistici per provider (DeepSeek, Together, Kimi)

---

## 🔄 Auto-Refresh

Dashboard-ul se actualizează automat la fiecare **10 secunde**.

---

## 🛠️ Comenzi Utile

### Pornire UI:
```bash
cd /srv/hf/ai_agents/auto_learning_ui
bash start_ui.sh
```

### Oprire UI:
```bash
kill $(lsof -t -i:5001)
```

### Verifică logs:
```bash
tail -f /srv/hf/ai_agents/logs/ui.log
```

### Verifică dacă rulează:
```bash
curl http://localhost:5001/api/stats/interactions
```

---

## 📁 Structură Fișiere

```
auto_learning_ui/
├── backend_api.py          # FastAPI backend
├── start_ui.sh             # Script pornire
├── static/
│   └── dashboard.html      # UI frontend
└── README.md               # Acest fișier
```

---

## 🐛 Troubleshooting

### Port 5001 ocupat:
```bash
kill $(lsof -t -i:5001)
bash start_ui.sh
```

### MongoDB nu răspunde:
```bash
sudo systemctl status mongod
sudo systemctl start mongod
```

### Qdrant nu răspunde:
```bash
curl http://127.0.0.1:6333/collections
```

### FastAPI nu este instalat:
```bash
pip install fastapi uvicorn
```

---

## 🎯 Funcționalități

✅ **Monitorizare în timp real** - Toate procesele
✅ **Acțiuni directe** - Butoane pentru toate operațiunile
✅ **Statistici live** - Date actualizate automat
✅ **Logs în UI** - Vezi output-ul acțiunilor
✅ **Design modern** - Interfață frumoasă și intuitivă

---

**Versiune:** 1.0.0  
**Status:** ✅ Production Ready


