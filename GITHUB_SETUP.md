# 🚀 Ghid pentru Mutarea Aplicației pe Laptop / GitHub

## 📋 Status Actual

- ✅ **Repo Git există**: `git@github.com:mobra-sabi/firecodes-ai-agents.git`
- ✅ **.gitignore configurat**: `.env`, `logs/`, `node_modules/`, `.venv/` sunt excluse
- ✅ **Ultimul commit**: 25d2563 (Fix scraper_adapter import path)

---

## 🔄 Pași pentru Sincronizare cu GitHub

### 1. Verifică Modificările

```bash
cd /srv/hf/ai_agents
git status
```

### 2. Adaugă Modificările Recente

```bash
# Adaugă toate modificările (fără .env și logs - sunt în .gitignore)
git add .

# Verifică ce va fi commitat
git status
```

### 3. Commit Modificările

```bash
git commit -m "Optimizare GPU maxim + ScraperAPI + fix meta tensor

- Detectare automată număr GPU-uri (9 RTX 3080 Ti)
- Optimizare paralelism pentru utilizare maximă GPU
- Fix eroare meta tensor în SentenceTransformer
- ScraperAPI integrat și funcțional
- Distribuție uniformă task-uri pe toate GPU-urile"
```

### 4. Push pe GitHub

```bash
git push origin main
```

---

## 💻 Setup pe Laptop

### 1. Clonează Repo-ul

```bash
git clone git@github.com:mobra-sabi/firecodes-ai-agents.git
cd firecodes-ai-agents
```

### 2. Creează Fișierul .env

**IMPORTANT**: Fișierul `.env` NU este în Git (e în .gitignore pentru securitate).

Creează manual `.env` pe laptop cu conținutul de pe server:

```bash
# Copiază .env de pe server (NU îl pune în Git!)
# Sau creează manual cu API keys-urile tale
```

**Conținut minim necesar**:
```env
# LLM APIs
DEEPSEEK_API_KEY=sk-755e228a434547d4942ed9c84343aa15
DEEPSEEK_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=sk-755e228a434547d4942ed9c84343aa15
OPENAI_BASE_URL=https://api.deepseek.com

# Brave Search API
BRAVE_API_KEY=BSA_Ji6p06dxYaLS_CsTxn2IOC-sX5s

# ScraperAPI
SCRAPERAPI_KEY=9095058f38c686b1cf081b3e4db5137b

# Together AI
TOGETHER_API_KEY=39c0e4caf004a00478163b18cf70ee62e48bd1fe7c95d129348523a2b4b7b39d
TOGETHER_BASE_URL=https://api.together.xyz/v1

# MongoDB
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=ai_agents_db

# Qdrant
QDRANT_URL=http://localhost:6333
```

### 3. Instalează Dependențele Python

```bash
# Creează virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# sau
.venv\Scripts\activate  # Windows

# Instalează dependențele
pip install -r requirements.txt
```

### 4. Instalează Dependențele Frontend

```bash
cd frontend-pro
npm install
```

### 5. Pornește Serviciile

#### MongoDB (Local)
```bash
# Linux/Mac
mongod --dbpath ./data/mongodb --port 27017

# Sau folosește Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

#### Qdrant (Docker)
```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

#### Backend
```bash
cd /path/to/firecodes-ai-agents
source .venv/bin/activate
uvicorn agent_api:app --host 0.0.0.0 --port 8090
```

#### Frontend
```bash
cd frontend-pro
npm run dev
```

---

## 📦 Export Date MongoDB (Opțional)

Dacă vrei să muți și datele (agenți, etc.) de pe server:

### Pe Server (viezure):

```bash
cd /srv/hf/ai_agents

# Export MongoDB
mongodump --port 27018 --db ai_agents_db --out ./mongodb_export

# Comprimă export-ul
tar -czf mongodb_export.tar.gz mongodb_export/

# Transferă pe laptop (folosind scp sau altă metodă)
# scp mongodb_export.tar.gz user@laptop:/path/to/destination
```

### Pe Laptop:

```bash
# Dezarhivează
tar -xzf mongodb_export.tar.gz

# Import în MongoDB local
mongorestore --db ai_agents_db mongodb_export/ai_agents_db/
```

---

## ⚠️ Notă Importantă

1. **.env NU este în Git** - trebuie creat manual pe fiecare mașină
2. **Logs/ nu este în Git** - se creează automat
3. **node_modules/ nu este în Git** - se instalează cu `npm install`
4. **.venv/ nu este în Git** - se creează cu `python3 -m venv .venv`

---

## 🔐 Securitate

- ✅ `.env` este în `.gitignore` - API keys-urile nu sunt în Git
- ✅ `logs/` este în `.gitignore` - logurile nu sunt în Git
- ⚠️ **NU comita niciodată** fișiere cu API keys sau date sensibile

---

## 📝 Comenzi Rapide

```bash
# Verifică status
git status

# Adaugă modificări
git add .

# Commit
git commit -m "Descriere modificări"

# Push pe GitHub
git push origin main

# Pull de pe GitHub (pe laptop)
git pull origin main
```

---

## 🎯 Workflow Recomandat

1. **Pe Server**: Lucrezi, testezi, modifici codul
2. **Când ești gata**: `git add .`, `git commit`, `git push`
3. **Pe Laptop**: `git pull` pentru a obține ultimele modificări
4. **Pe Laptop**: Creează `.env` manual (dacă nu există deja)

---

**Ultima actualizare**: 21 NOV 2025

