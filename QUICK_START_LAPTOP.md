# ⚡ Quick Start - Setup pe Laptop

## 🚀 Pași Rapizi

### 1. Clonează Repo-ul

```bash
git clone git@github.com:mobra-sabi/firecodes-ai-agents.git
cd firecodes-ai-agents
```

### 2. Creează .env

**IMPORTANT**: Copiază `.env` de pe server sau creează manual:

```bash
# Creează .env cu API keys-urile tale
nano .env
```

**Minim necesar**:
```env
DEEPSEEK_API_KEY=sk-...
BRAVE_API_KEY=BSA_...
SCRAPERAPI_KEY=...
MONGODB_URI=mongodb://localhost:27017/
QDRANT_URL=http://localhost:6333
```

### 3. Setup Python

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# sau .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 4. Setup Frontend

```bash
cd frontend-pro
npm install
```

### 5. Pornește Serviciile

#### MongoDB (Docker - recomandat)
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

#### Qdrant (Docker)
```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

#### Backend
```bash
source .venv/bin/activate
uvicorn agent_api:app --host 0.0.0.0 --port 8090
```

#### Frontend
```bash
cd frontend-pro
npm run dev
```

### 6. Accesează Aplicația

- Frontend: http://localhost:5173
- Backend API: http://localhost:8090
- API Docs: http://localhost:8090/docs

---

## 🔄 Sincronizare cu Server

### Pe Server (după modificări):
```bash
cd /srv/hf/ai_agents
./push_to_github.sh
```

### Pe Laptop (pentru update):
```bash
git pull origin main
```

---

## 📦 Import Date MongoDB (Opțional)

Dacă vrei datele de pe server:

```bash
# Pe server: export
mongodump --port 27018 --db ai_agents_db --out ./mongodb_export
tar -czf mongodb_export.tar.gz mongodb_export/

# Pe laptop: import
tar -xzf mongodb_export.tar.gz
mongorestore --db ai_agents_db mongodb_export/ai_agents_db/
```

---

## ⚠️ Probleme Comune

### Port 8090 ocupat
```bash
# Găsește procesul
lsof -i :8090
# Oprește-l
kill <PID>
```

### MongoDB nu pornește
```bash
# Verifică dacă rulează
docker ps | grep mongodb
# Sau pornește manual
docker start mongodb
```

### Frontend nu pornește
```bash
# Șterge node_modules și reinstalează
rm -rf node_modules package-lock.json
npm install
```

---

**Pentru detalii complete, vezi**: `GITHUB_SETUP.md`

