# 🎯 SCHEMA COMPLETĂ DE EXECUȚIE - AI AGENT PLATFORM

---

## 📊 DIAGRAMA ARHITECTURII COMPLETE

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER (Browser)                                  │
│                                                                         │
│  Dashboard: https://sub-multimedia-difficulties-cluster.trycloudflare  │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
        ┌───────▼────────┐       ┌───────▼────────┐
        │  HTTP Server   │       │  Agent API     │
        │  Port 8888     │       │  Port 5000     │
        │  Static Files  │       │  FastAPI       │
        └───────┬────────┘       └───────┬────────┘
                │                        │
                │         ┌──────────────┴──────────────┐
                │         │                             │
        ┌───────▼─────────▼──────┐         ┌──────────▼─────────┐
        │    MongoDB              │         │   Qdrant           │
        │    Port 27017           │         │   Port 9306        │
        │                         │         │                    │
        │  ┌─────────────────┐   │         │  ┌──────────────┐  │
        │  │ site_agents     │   │         │  │ Embeddings   │  │
        │  │ 151 documente   │   │         │  │ 55,970 vect  │  │
        │  └─────────────────┘   │         │  └──────────────┘  │
        │                         │         │                    │
        │  ┌─────────────────┐   │         └────────────────────┘
        │  │ users           │   │
        │  │ accounts        │   │                ┌──────────────┐
        │  └─────────────────┘   │                │  Qwen LLM    │
        │                         │                │  GPU 6-10    │
        │  ┌─────────────────┐   │                │  Ports       │
        │  │ reports         │   │                │  9301, 9304  │
        │  │ CI data         │   │                └──────┬───────┘
        │  └─────────────────┘   │                       │
        └─────────────────────────┘                       │
                                                 ┌────────▼────────┐
                                                 │  DeepSeek API   │
                                                 │  (External)     │
                                                 │  Orchestration  │
                                                 └─────────────────┘
```

---

## 🧩 MODULELE SISTEMULUI

### **MODUL 1: FRONTEND (Dashboard)**

#### **Locație:**
```
/srv/hf/ai_agents/static/complete_dashboard.html
```

#### **Ce Face:**
- Interfață web pentru control complet
- 4 tabs: Overview, Start Workflow, Agents, Live Progress
- Comunică cu API-ul prin HTTP requests
- Auto-refresh la 30 secunde

#### **Cum Îl Folosești:**
1. Deschizi în browser
2. Tab **Overview** - vezi statistici
3. Tab **Start Workflow** - lansezi workflow nou
4. Tab **Agents** - gestionezi agenții
5. Tab **Live Progress** - monitorizezi execuția

#### **API Calls:**
```javascript
GET  /api/agents          → Lista agenți
POST /api/start-workflow  → Start workflow nou
GET  /api/workflow/{id}   → Status workflow
GET  /api/stats           → Statistici
```

---

### **MODUL 2: HTTP SERVER**

#### **Locație:**
```
python3 -m http.server 8888
```

#### **Ce Face:**
- Servește fișiere statice (HTML, CSS, JS)
- Expune dashboard-ul
- Nu procesează logică backend

#### **Cum Îl Folosești:**
```bash
# Start server
cd /srv/hf/ai_agents
python3 -m http.server 8888

# Access
http://localhost:8888/static/complete_dashboard.html
```

---

### **MODUL 3: AGENT API (FastAPI)**

#### **Locație:**
```
/srv/hf/ai_agents/agent_api.py
```

#### **Ce Face:**
- API REST principal
- Gestionează agenți (CRUD)
- Orchestrează workflow-uri
- Integrează Qwen, DeepSeek, MongoDB, Qdrant

#### **Endpoints Principale:**

```python
# AGENȚI
GET    /api/agents              # Lista tuturor agenților
GET    /api/agents/{id}         # Detalii agent specific
POST   /api/agents              # Creare agent nou
DELETE /api/agents/{id}         # Ștergere agent

# WORKFLOW
POST   /api/start-workflow      # Start workflow nou
GET    /api/workflow/{id}       # Status workflow
POST   /api/stop-workflow/{id}  # Stop workflow

# STATISTICI
GET    /api/stats               # Statistici globale
GET    /api/live-stats          # Date live pentru dashboard

# CI REPORTS
GET    /api/ci-report/{id}      # Raport CI pentru agent
GET    /api/orgchart/{id}       # Organogram master-slave
```

#### **Cum Îl Folosești:**
```bash
# Start API
cd /srv/hf/ai_agents
python3 -m uvicorn agent_api:app --host 0.0.0.0 --port 5000

# Test API
curl http://localhost:5000/api/stats
```

---

### **MODUL 4: CEO MASTER WORKFLOW**

#### **Locație:**
```
/srv/hf/ai_agents/ceo_master_workflow.py
```

#### **Ce Face:**
Workflow complet în 11 faze pentru competitive intelligence:

```
FAZA 1: Creare Master Agent
  └─ Scraping site (Beautiful Soup)
  └─ Chunking text (paragraphs)
  └─ Embeddings cu Qwen (GPU 6-10)
  └─ Indexare în Qdrant
  └─ Salvare MongoDB

FAZA 2: LangChain Integration
  └─ Creare agent conversațional
  └─ Memorie context
  └─ RAG pipeline (Qdrant)

FAZA 3: DeepSeek Voice
  └─ DeepSeek se identifică cu site-ul
  └─ Devine expert în domeniu

FAZA 4: Subdomain Decomposition
  └─ DeepSeek descompune site în subdomenii
  └─ Ex: "Design interior", "Renovări", "Construcții"

FAZA 5: Keyword Generation
  └─ 10-15 keywords per subdomeniu
  └─ DeepSeek generează keywords strategice

FAZA 6: Competitor Discovery
  └─ Brave Search API pentru fiecare keyword
  └─ Top 15 rezultate per keyword
  └─ Deduplicare competitori
  └─ Salvare poziții SERP

FAZA 7: Slave Agent Creation
  └─ Pentru fiecare competitor găsit
  └─ Scraping + Embeddings + Qdrant
  └─ Link la master agent
  └─ Procesare paralelă (5 GPU simultan)

FAZA 8: Master Learning
  └─ Master învață din toți slaves
  └─ DeepSeek analizează competiția
  └─ Generare insights

FAZA 9: Organogram Generation
  └─ Structură master-slave
  └─ Vizualizare ierarhie

FAZA 10: Competitive Map
  └─ Hartă competitivă per keyword
  └─ Poziții SERP
  └─ Oportunități

FAZA 11: CEO Report
  └─ Raport executiv
  └─ Insights acționabile
  └─ KPIs competitivi
```

#### **Cum Îl Folosești:**
```bash
# Manual
cd /srv/hf/ai_agents
python3 run_ceo_workflow_live.py

# Sau din Dashboard
Tab "Start Workflow" → Input URL → START
```

---

### **MODUL 5: MONGODB**

#### **Ce Face:**
- Stochează toate datele structurate
- Collections:
  - `site_agents` - 151 agenți
  - `users` - Conturi utilizatori
  - `competitor_discovery_reports` - Rapoarte CI
  - `master_learning` - Insights învățare

#### **Cum Îl Folosești:**
```bash
# Connect
mongo

# Use database
use ai_agents_db

# Query
db.site_agents.find({agent_type: "master"}).count()
db.site_agents.find({agent_type: "slave"}).count()

# Stats
db.site_agents.aggregate([
  {$group: {_id: null, total: {$sum: "$chunks_indexed"}}}
])
```

---

### **MODUL 6: QDRANT (Vector DB)**

#### **Ce Face:**
- Stochează embeddings pentru search semantic
- 55,970+ vectori
- Collections per agent: `construction_{domain}`
- Similarity search pentru RAG

#### **Cum Îl Folosești:**
```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=9306)

# List collections
collections = client.get_collections()

# Search
results = client.search(
    collection_name="construction_daibau_ro",
    query_vector=embedding,
    limit=5
)
```

---

### **MODUL 7: QWEN LLM (GPU)**

#### **Ce Face:**
- LLM inference pe GPU
- 2 servere vLLM:
  - Port 9301: Qwen2.5-7B-Instruct-AWQ
  - Port 9304: Qwen2.5-7B-Instruct
- GPU 6-10 pentru procesare paralelă

#### **Cum Îl Folosești:**
```python
from openai import OpenAI

# Connect to vLLM server
client = OpenAI(
    base_url="http://localhost:9301/v1",
    api_key="EMPTY"
)

# Generate
response = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct-AWQ",
    messages=[{"role": "user", "content": "Analyze this site..."}]
)
```

---

### **MODUL 8: DEEPSEEK API**

#### **Ce Face:**
- Orchestrare strategică
- Analiză competitivă
- Generare insights
- Decompoziție subdomenii
- Planning keywords

#### **Cum Îl Folosești:**
```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-...",
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{
        "role": "user",
        "content": "Decompose this website into subdomains..."
    }]
)
```

---

## 🔄 FLUXUL COMPLET DE EXECUȚIE

### **SCENARIO 1: Vizualizare Date Existente**

```
USER
  ↓
Opens Dashboard
  ↓
Dashboard loads → fetch('/api/agents')
  ↓
Agent API → MongoDB.find({})
  ↓
Returns: 151 agents
  ↓
Dashboard displays stats
```

### **SCENARIO 2: Start Workflow Nou**

```
USER
  ↓
Tab "Start Workflow"
  ↓
Input: https://new-site.com
  ↓
Click "START"
  ↓
POST /api/start-workflow {site_url: "..."}
  ↓
Agent API → Background Task
  ↓
CEO Master Workflow starts
  │
  ├─→ Phase 1: Scraping (BeautifulSoup)
  ├─→ Phase 2: Chunking (paragraphs)
  ├─→ Phase 3: Embeddings (Qwen GPU)
  ├─→ Phase 4: Qdrant indexing
  ├─→ Phase 5: DeepSeek subdomains
  ├─→ Phase 6: DeepSeek keywords
  ├─→ Phase 7: Brave Search (15/keyword)
  ├─→ Phase 8: Slave creation (parallel GPU)
  ├─→ Phase 9: Master learning
  ├─→ Phase 10: Organogram
  └─→ Phase 11: CEO Report
  ↓
Dashboard "Live Progress" tab
  └─ Auto-refresh shows progress
```

### **SCENARIO 3: Query Agent cu RAG**

```
USER
  ↓
Asks: "What services does daibau.ro offer?"
  ↓
Agent API → LangChain Agent
  ↓
Qdrant.search("services", collection="construction_daibau_ro")
  ↓
Returns: Top 5 relevant chunks
  ↓
Qwen LLM (GPU) generates answer with context
  ↓
Response: "Daibau.ro offers construction, renovation..."
```

---

## 🎮 GHID PRACTIC DE UTILIZARE

### **PAS 1: Pornire Sistem**

```bash
# Terminal 1: MongoDB (de obicei pornit automat)
sudo systemctl start mongodb

# Terminal 2: Qdrant (de obicei pornit automat)
# Check: curl http://localhost:9306

# Terminal 3: Agent API
cd /srv/hf/ai_agents
python3 -m uvicorn agent_api:app --host 0.0.0.0 --port 5000

# Terminal 4: HTTP Server
cd /srv/hf/ai_agents
python3 -m http.server 8888

# Terminal 5: Cloudflare Tunnel (pentru acces public)
~/cloudflared tunnel --url http://localhost:8888
```

### **PAS 2: Acces Dashboard**

```
URL Public: https://sub-multimedia-difficulties-cluster.trycloudflare.com/static/complete_dashboard.html

URL Local: http://localhost:8888/static/complete_dashboard.html
```

### **PAS 3: Folosire Dashboard**

#### **Tab OVERVIEW:**
1. Vezi statistici globale
2. Click **Refresh** pentru date fresh
3. Verifică System Status

#### **Tab START WORKFLOW:**
1. Input URL site (ex: https://example.com)
2. Setează rezultate/keyword (15 recomandat)
3. Setează GPU parallelism (5 recomandat)
4. Click **START**
5. Mergi la tab **Live Progress**

#### **Tab AGENTS:**
1. Vezi lista master agents
2. Vezi lista slave agents
3. Click pe agent pentru detalii

#### **Tab LIVE PROGRESS:**
1. Vezi progress bar (%)
2. Vezi ETA
3. Vezi last slave created
4. Urmărește activity log

---

## 📊 MONITORIZARE ȘI DEBUG

### **Check Servere Active:**
```bash
ps aux | grep -E "uvicorn|http.server|cloudflared"
```

### **Check MongoDB:**
```bash
mongo ai_agents_db --eval "db.site_agents.count()"
```

### **Check Qdrant:**
```bash
curl http://localhost:9306/collections
```

### **Check API:**
```bash
curl http://localhost:5000/api/stats
```

### **Logs:**
```bash
# Agent API logs
tail -f /tmp/agent_api.log

# Workflow logs
tail -f /tmp/full_industry_discovery.log

# HTTP Server logs
tail -f /tmp/http_server.log
```

---

## 🎯 REZUMAT RAPID

### **Ce Ai:**
1. ✅ **Dashboard** - Control complet web
2. ✅ **Agent API** - Backend FastAPI
3. ✅ **MongoDB** - 151 agenți, 55,970 chunks
4. ✅ **Qdrant** - Vector search
5. ✅ **Qwen** - LLM pe GPU
6. ✅ **DeepSeek** - Orchestrare
7. ✅ **Workflow** - CEO competitive intelligence

### **Ce Faci:**
1. **Vizualizezi** date existente (Overview)
2. **Creezi** agenți noi (Start Workflow)
3. **Monitorizezi** progress live (Live Progress)
4. **Gestionezi** agenții (Agents tab)

### **Cum Rulează:**
```
Dashboard → API → MongoDB/Qdrant → GPU/DeepSeek → Results
```

---

**Sistemul e COMPLET și FUNCȚIONAL!** 🎊

