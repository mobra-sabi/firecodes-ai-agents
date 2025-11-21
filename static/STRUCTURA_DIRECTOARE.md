# STRUCTURA DIRECTOARE - AI Agents Platform
**Actualizat: 6 Noiembrie 2025**

## 📁 Directoare Principale

```
ai_agents/
│
├── 📂 actions/                      # ⭐ NOU - Act-to-Action System (conectori externi)
│   ├── __init__.py
│   ├── action_executor.py          # Executor acțiuni
│   ├── google_ads_connector.py     # Conector Google Ads
│   ├── wordpress_connector.py      # Conector WordPress
│   └── seo_api_connector.py        # Conector SEO APIs
│
├── 📂 adapters/                     # Adapter-uri pentru scraper și search providers
│   ├── scraper_adapter.py
│   └── search_providers.py
│
├── 📂 agents/                       # Definiții de agenți (versiuni diferite)
│   ├── site_agent.py
│   ├── enhanced_commercial_agent.py
│   ├── learning_agent.py
│   └── ...
│
├── 📂 api/                          # API endpoints (goale, folosim tools/agent_api.py)
│   └── __init__.py
│
├── 📂 archive/                      # ⭐ NOU - Fișiere arhivate (documentație veche, rapoarte)
│   ├── old_docs/                    # Documentație veche
│   ├── old_reports/                 # Rapoarte vechi
│   ├── old_scripts/                 # Script-uri vechi
│   └── validation_reports/          # Rapoarte validare agenți
│
├── 📂 config/                       # Configurații
│   ├── database_config.py
│   ├── gpu_config.py
│   ├── llm_secrets.py
│   ├── policies.yaml
│   └── settings.yaml
│
├── 📂 database/                     # Handler-e pentru baze de date
│   ├── mongodb_handler.py          # ⭐ Handler MongoDB + Repositories
│   └── qdrant_vectorizer.py
│
├── 📂 langchain_agents/             # ⭐ NOU - Integrare LangChain completă
│   ├── __init__.py
│   ├── llm_manager.py              # Manager Qwen/DeepSeek pentru LangChain
│   ├── chain_registry.py           # Registry pentru lanțuri LangChain
│   ├── chains/                      # Lanțuri LangChain
│   │   ├── site_analysis_chain.py  # Analiză site (Qwen + DeepSeek)
│   │   ├── industry_strategy_chain.py # Strategie industrie (DeepSeek)
│   │   └── decision_chain.py       # Plan acțiuni (Qwen)
│   ├── agents/                      # Agenți LangChain
│   │   ├── site_agent.py           # Agent pentru fiecare site
│   │   └── global_orchestrator.py  # Orchestrator global
│   ├── tools/                       # Tool-uri LangChain
│   │   └── vector_search_tool.py  # Căutare Qdrant
│   └── memory/                      # Manager memorie
│       └── memory_manager.py
│
├── 📂 orchestrator/                 # Orchestrator principal
│   ├── frontier_manager.py
│   ├── llm_supervisor.py
│   ├── orchestrator_loop.py         # ⭐ Sistem task-uri async
│   ├── model_router.py              # ⭐ Router modele Qwen/DeepSeek
│   ├── qwen_runner.py
│   └── langchain_integration.py     # ⭐ NOU - Integrare LangChain cu orchestrator
│
├── 📂 static/                       # Frontend UI
│   ├── main_interface.html         # ✨ INTERFAȚA PRINCIPALĂ (UI)
│   ├── chat.html
│   ├── agent_status.html
│   └── STRUCTURA_DIRECTOARE.md     # ⭐ Acest fișier
│
├── 📂 tools/                        # Utilități și tool-uri
│   ├── agent_api.py                # ⭐ FastAPI server principal (ACTIV)
│   ├── deepseek_client.py          # Client DeepSeek API
│   ├── llm_clients.py              # ⭐ Clienți LLM centralizați
│   ├── admin_discovery.py          # Descoperire competitori
│   └── site_agent_creator.py       # Creator agenți (versiune veche)
│
└── 📂 utils/                        # Utilități generale
    └── prompt_hash.py              # ⭐ Hash pentru cache DeepSeek
```

## 📄 Fișiere Principale (Root)

### 🔥 Core Application Files
- **`agent_api.py`** ⭐ - FastAPI server principal (endpoints, WebSocket, UI) - **NOTĂ: Serverul activ este `tools/agent_api.py`**
- **`site_agent_creator.py`** ⭐ - Creator agenți noi (scraping, indexare, Qdrant)
- **`competitive_strategy.py`** ⭐ - Generator strategii competitive cu DeepSeek (IMPROVED astăzi)
- **`industry_indexer.py`** ⭐ - Indexare industrie completă
- **`reindex_qdrant.py`** ⭐ - **NOU ASTĂZI** - Script reindexare Qdrant pentru toți agenții
- **`validate_and_fix_agents.py`** ⭐ - **NOU ASTĂZI** - Script validare și corectare agenți
- **`competitor_discovery.py`** - Descoperire competitori
- **`site_specific_intelligence.py`** - Inteligență specifică site-ului
- **`qwen_memory.py`** - Sistem memorie și învățare Qwen

### 🤖 AI & LLM Integration
- **`gpt5_qwen_architecture.py`** - Arhitectură GPT-5 + Qwen
- **`langchain_agent_integration.py`** - Integrare LangChain
- **`chat_memory_integration.py`** - Integrare memorie chat
- **`guardrails.py`** - Protecții și validări

### 🔧 Utilities & Scripts
- **`health_checker.py`** - Verificare sănătate servicii
- **`clean_problematic_agents.py`** - Curățare agenți problematici
- **`verify_and_clean_agents.py`** - Verificare și curățare agenți
- **`auto_site_extractor.py`** - Extragere automată date site

### 📜 Configuration & Scripts
- **`.env`** ⭐ - Variabile de mediu (API keys, URLs)
- **`start_server.sh`** ⭐ - Pornire server
- **`stop_server.sh`** ⭐ - Oprire server
- **`requirements.txt`** - Dependențe Python

### 📚 Documentation (Active)
- **`HARTA_PROCESE_APLICATIE.md`** ⭐ - Harta proceselor aplicației
- **`TODO_LANGCHAIN.md`** ⭐ - Plan integrare LangChain
- **`TESTARE_LANGCHAIN.md`** ⭐ - Ghid testare LangChain
- **`GHID_RAPID_TESTARE.md`** ⭐ - Ghid rapid testare
- **`MANUAL_TESTARE_LANGCHAIN.md`** ⭐ - Manual testare LangChain
- **`QDRANT_SYSTEM_REFACTOR.md`** ⭐ - **NOU ASTĂZI** - Documentație refactor Qdrant
- **`static/STRUCTURA_DIRECTOARE.md`** ⭐ - Acest fișier

## 🔑 Fișiere Critice pentru Funcționare

### 1. Backend API
- **`tools/agent_api.py`** ⭐⭐⭐ - **SERVERUL ACTIV** - FastAPI server principal
- **`site_agent_creator.py`** - Creare agenți
- **`competitive_strategy.py`** - Strategii competitive (IMPROVED astăzi)
- **`industry_indexer.py`** - Indexare industrie
- **`reindex_qdrant.py`** - **NOU ASTĂZI** - Reindexare Qdrant

### 2. Frontend UI
- **`static/main_interface.html`** - Interfața principală utilizator

### 3. Configuration
- **`.env`** - Toate variabilele de mediu
- **`config/database_config.py`** - Config baze de date
- **`config/llm_secrets.py`** - Secret-uri LLM

### 4. Database Handlers
- **`database/mongodb_handler.py`** - MongoDB + Repositories
- **`database/qdrant_vectorizer.py`** - Qdrant

### 5. LLM Clients & Orchestration
- **`tools/deepseek_client.py`** - DeepSeek API
- **`tools/llm_clients.py`** - Clienți LLM centralizați
- **`orchestrator/model_router.py`** - Router pentru decizie Qwen vs DeepSeek
- **`qwen_memory.py`** - Qwen Memory & Learning

### 6. LangChain Integration (NOU)
- **`langchain_agents/llm_manager.py`** - Manager LLM pentru LangChain
- **`langchain_agents/chain_registry.py`** - Registry lanțuri
- **`langchain_agents/chains/`** - Lanțuri LangChain (site_analysis, industry_strategy, decision)
- **`langchain_agents/agents/`** - Agenți LangChain (site_agent, global_orchestrator)
- **`orchestrator/langchain_integration.py`** - Integrare LangChain cu orchestrator

### 7. Task System & Playbooks
- **`orchestrator/orchestrator_loop.py`** - Sistem task-uri async
- **`utils/prompt_hash.py`** - Hash pentru cache DeepSeek

## 📊 Flux de Date

```
Frontend (main_interface.html)
    ↓
tools/agent_api.py (FastAPI) ⭐ SERVERUL ACTIV
    ↓
├──→ site_agent_creator.py (creare agenți)
├──→ competitive_strategy.py (strategii) ⭐ IMPROVED ASTĂZI
│   └──→ generate_industry_strategy() (orchestrat cu cache)
│       ├──→ orchestrator/model_router.py (decizie Qwen/DeepSeek)
│       ├──→ tools/llm_clients.py (QwenClient/DeepSeekClient)
│       └──→ utils/prompt_hash.py (cache verificare)
├──→ industry_indexer.py (indexare industrie)
├──→ reindex_qdrant.py ⭐ NOU ASTĂZI (reindexare Qdrant)
├──→ validate_and_fix_agents.py ⭐ NOU ASTĂZI (validare agenți)
├──→ orchestrator/orchestrator_loop.py (task-uri async)
├──→ langchain_agents/ ⭐ NOU (lanțuri LangChain)
│   ├──→ chains/ (site_analysis, industry_strategy, decision)
│   └──→ agents/ (site_agent, global_orchestrator)
└──→ competitor_discovery.py (descoperire competitori)
    ↓
├──→ MongoDB (date agenți, conținut, conversații, tasks, strategies)
├──→ Qdrant (vectori embeddings) ⭐ REFACTORED ASTĂZI
└──→ DeepSeek API / Qwen (Ollama) (analiză și strategii)
```

## 🎯 Puncte de Intrare Principale

1. **UI activă:** `static/main_interface.html` (servită la `/`)
2. **Server activ:** **`tools/agent_api.py`** ⭐⭐⭐ (pornește cu `uvicorn --app-dir /home/mobra/ai_agents tools.agent_api:app`)
   - `GET /api/agents`, `GET /api/agents/last`, `GET /api/agents/{agent_id}/status`
   - `POST /api/analyze-agent` — generează strategie (DeepSeek reasoner) ⭐ IMPROVED ASTĂZI
   - `GET  /api/strategy/{agent_id}` — citește strategia salvată pentru UI
   - `POST /api/index-industry` — indexează industria pentru agent
   - `POST /agents/{agent_id}/run_chain/{chain_name}` ⭐ NOU - Rulează lanțuri LangChain
   - `GET /chains/list` ⭐ NOU - Listează lanțuri disponibile
   - `POST /api/answer` și `POST /ask` — Q&A/chat
   - `GET  /health` — status servicii
3. **Creare/ingestie:** `site_agent_creator.py`
4. **Configurație:** `.env`

## 🆕 Modificări Astăzi (6 Noiembrie 2025)

### 1. Sistem Qdrant Refăcut ⭐
- **`reindex_qdrant.py`** - Script nou pentru reindexare completă Qdrant
  - Folosește curl direct pentru stabilitate maximă
  - Analizează toți agenții și reindexează conținutul în Qdrant
  - Generează embeddings cu HuggingFace (BAAI/bge-large-en-v1.5)
  - Salvează vectorii în batch-uri de 50
- **`QDRANT_SYSTEM_REFACTOR.md`** - Documentație refactor Qdrant

### 2. Validare Agenți ⭐
- **`validate_and_fix_agents.py`** - Script nou pentru validare agenți
  - Verifică dacă agenții au conținut în MongoDB sau Qdrant
  - Recrează agenții non-conformi automat
  - Șterge agenții care nu pot fi recreați
  - Generează rapoarte detaliate

### 3. Îmbunătățiri Strategie Competitivă ⭐
- **`competitive_strategy.py`** - Prompt îmbunătățit pentru strategii mai detaliate
  - Analizează până la 100 chunks (în loc de 50)
  - Folosește până la 2000 caractere per chunk (în loc de 1000)
  - Prompt mai specific și detaliat
  - Fallback îmbunătățit pentru strategii generice
  - Max tokens: 6000, Temperature: 0.5 pentru precizie

### 4. Fix Timeout DeepSeek API ⭐⭐⭐ **NOU**
- **`tools/deepseek_client.py`** - Timeout și retry logic îmbunătățit
  - Timeout default: 180s (3 minute) în loc de 60s
  - Retry logic: 3 încercări cu exponential backoff
  - Timeout progresiv: 180s → 210s → 240s (max 300s)
  - Logging detaliat pentru debugging
- **`competitive_strategy.py`** - Timeout dinamic și fallback
  - Timeout dinamic bazat pe prompt size
  - Fallback automat: reduce max_tokens (6000 → 3000) la timeout
  - Trunchiere prompt la timeout pentru a evita timeout-uri repetate
- **`tools/agent_api.py`** - Timeout asyncio și error handling
  - Timeout asyncio: 300s (5 min) pentru operația completă
  - Mesaje de eroare mai clare și user-friendly
  - Detecție automată tip eroare (timeout vs connection)
- **`static/main_interface.html`** - UI îmbunătățit
  - Mesaje de eroare mai clare pentru timeout-uri
  - Informații despre durata estimată pentru utilizator

### 5. Organizare Proiect
- Creat folder **`archive/`** pentru fișiere vechi
  - `archive/old_docs/` - Documentație veche
  - `archive/old_reports/` - Rapoarte vechi
  - `archive/validation_reports/` - Rapoarte validare
  - `archive/old_scripts/` - Script-uri vechi și teste

## 🔁 Creare Agent (flux)

1) UI → websocket: `create_site_agent_ws`
2) Crawl (Playwright) → extrage text (max `MAX_CRAWL_PAGES`)
3) Split în chunk-uri → embeddings (BAAI/bge-large-en-v1.5)
4) Qdrant upsert pe HTTP 6333 (colecția `agent_{id}`) ⭐ REFACTORED ASTĂZI
5) Inițializează memorie Qwen (Mongo + vector DB)
6) Răspuns final cu statistici

## 🧩 Integrare LangChain (NOU)

### Lanțuri Disponibile:
- **`site_analysis`** - Analiză completă site (Qwen + DeepSeek)
- **`industry_strategy`** - Strategie competitivă industrie (DeepSeek)
- **`decision_chain`** - Plan acțiuni concrete (Qwen)

### Endpoints LangChain:
- `POST /agents/{agent_id}/run_chain/{chain_name}` - Rulează lanț
- `GET /chains/list` - Listează lanțuri disponibile
- `GET /chains/{chain_name}/preview` - Preview lanț

## ⚙️ Configurație Actuală

### DeepSeek
- `DEEPSEEK_API_KEY` - Cheie API DeepSeek
- `DEEPSEEK_BASE_URL=https://api.deepseek.com/v1`
- `DEEPSEEK_MODEL=deepseek-reasoner`

### Qdrant
- `QDRANT_URL=http://127.0.0.1:6333` (HTTP)
- Conexiuni pe HTTP (prefer_grpc=false) pentru stabilitate
- Script reindexare: `reindex_qdrant.py`

### MongoDB
- `MONGO_URI=mongodb://localhost:27017/`
- `MONGO_DB=ai_agents_db`

## 📦 Pachete/Dependențe Relevante

- fastapi, uvicorn, starlette
- pymongo, bson
- qdrant-client
- requests, beautifulsoup4 (bs4)
- python-dotenv
- openai (client compatibil DeepSeek), langchain-openai
- langchain, langchain-core, langchain-community ⭐ NOU
- sentence-transformers, transformers

## 🗂️ Structură Archive

Fișierele vechi au fost mutate în `archive/`:
- **`archive/old_docs/`** - Documentație veche
- **`archive/old_reports/`** - Rapoarte vechi (RAPORT_*, REZUMAT_*, VERIFICARE_*, FIX_*)
- **`archive/validation_reports/`** - Rapoarte validare (agent_validation_report_*.json, qdrant_reindex_report_*.json)

---

## 📖 DESCRIEREA SISTEMULUI

### 🎯 Scopul Platformei

**AI Agents Platform** este o platformă completă pentru crearea, gestionarea și analiza agenților AI pentru site-uri web. Fiecare site devine un agent autonom cu memorie, capacitate de învățare și abilități de analiză competitivă.

### 🏗️ Arhitectura Sistemului

#### 1. **Creare Agenți** (`site_agent_creator.py`)
- **Input**: URL site web
- **Proces**:
  1. Crawling site-ului cu Playwright (max pagini configurable)
  2. Extragere și curățare conținut HTML
  3. Split în chunk-uri pentru procesare
  4. Generare embeddings cu HuggingFace (BAAI/bge-large-en-v1.5)
  5. Salvare vectori în Qdrant (colecție `agent_{id}`)
  6. Salvare conținut brut în MongoDB (`site_content`)
  7. Inițializare memorie Qwen pentru învățare continuă
- **Output**: Agent cu conținut indexat și memorie inițializată

#### 2. **Generare Strategie Competitivă** (`competitive_strategy.py`)
- **Input**: Agent ID
- **Proces**:
  1. Extrage conținutul agentului din Qdrant/MongoDB
  2. Construiește prompt detaliat cu toate serviciile identificate
  3. Trimite la DeepSeek Reasoner pentru analiză strategică
  4. Parsează răspunsul JSON cu strategii concrete
  5. Salvează strategia în MongoDB (`competitive_strategies`)
- **Output**: Strategie competitivă completă cu:
  - Lista serviciilor identificate
  - Strategii de cercetare pentru fiecare serviciu
  - Priorități de cercetare
  - Rezultate așteptate

#### 3. **Indexare Industrie** (`industry_indexer.py`)
- **Input**: Agent ID, max_sites, concurrency
- **Proces**:
  1. Obține strategia competitivă a agentului
  2. Generează query-uri de căutare pentru competitori
  3. Caută competitori folosind search providers (SerpAPI, DuckDuckGo)
  4. Crawlează site-urile competitorilor în paralel
  5. Indexează conținutul competitorilor în Qdrant (`industry_{agent_id}`)
  6. Salvează metadata în MongoDB (`competitors`, `industry_resources`)
- **Output**: Industrie indexată cu competitori și resurse

#### 4. **Sistem LangChain** (`langchain_agents/`)
- **Lanțuri disponibile**:
  - **`site_analysis`**: Analiză completă site (Qwen pentru sumarizare + DeepSeek pentru strategie)
  - **`industry_strategy`**: Strategie competitivă industrie (DeepSeek pentru reasoning)
  - **`decision_chain`**: Plan acțiuni concrete (Qwen pentru extrageri structurate)
- **Agenți**:
  - **`SiteAgent`**: Agent LangChain pentru fiecare site cu tool-uri proprii
  - **`GlobalOrchestrator`**: Meta-agent care decide ce lanț/model să folosească
- **Memorie**: Sincronizare automată între LangChain memory și MongoDB/Qdrant

#### 5. **Sistem de Memorie și Învățare** (`qwen_memory.py`)
- **Short-term memory**: Conversații recente (LangChain BufferMemory)
- **Long-term memory**: MongoDB + Qdrant pentru cunoștințe persistente
- **Learning**: Îmbunătățire continuă bazată pe interacțiuni

### 🔄 Fluxuri de Date Principale

#### Flux 1: Creare Agent → Strategie → Indexare
```
1. User → UI: Creează agent pentru site
2. site_agent_creator.py → Crawl site → Qdrant + MongoDB
3. User → UI: Generează strategie competitivă
4. competitive_strategy.py → DeepSeek → Strategie → MongoDB
5. User → UI: Indexează industrie
6. industry_indexer.py → Caută competitori → Indexează → Qdrant
```

#### Flux 2: Chat/Conversație
```
1. User → UI: Întrebare despre site
2. agent_api.py → site_specific_intelligence.py
3. Qdrant: Căutare semantică pentru context
4. Qwen/DeepSeek: Generează răspuns bazat pe context
5. Salvează conversația în MongoDB (memorie)
6. UI: Afișează răspuns
```

#### Flux 3: LangChain Chains
```
1. User → UI: Rulează lanț LangChain
2. agent_api.py → orchestrator/langchain_integration.py
3. langchain_agents/chain_registry.py → Selectează lanț
4. Lanț execută pașii (Qwen/DeepSeek)
5. Rezultat salvat în MongoDB
6. UI: Afișează rezultat
```

### 🧠 Modelul de Reasoning

#### Qwen (Local GPU)
- **Rol**: Task-uri grele locale
- **Folosit pentru**:
  - Crawling și scraping site-uri
  - Generare embeddings
  - Sumarizare conținut
  - Extrageri structurate (JSON)
  - Procesare batch-uri mari
- **Avantaje**: Rapid, local, fără cost API

#### DeepSeek Reasoner (API)
- **Rol**: Reasoning strategic și analize complexe
- **Folosit pentru**:
  - Generare strategii competitive
  - Analiză strategică industrie
  - Reasoning complex
  - Răspunsuri la întrebări complexe
- **Avantaje**: Puternic, reasoning avansat, acces la internet

### 💾 Storage și Persistență

#### MongoDB
- **Colecții principale**:
  - `site_agents`: Metadata agenți
  - `site_content`: Conținut brut site-uri (chunks)
  - `competitive_strategies`: Strategii competitive
  - `competitors`: Competitori identificați
  - `industry_resources`: Resurse industriale
  - `conversations`: Conversații cu agenții
  - `tasks`: Task-uri async (orchestrator)
- **Rol**: Storage documentar, metadata, conversații

#### Qdrant
- **Colecții**:
  - `agent_{agent_id}`: Vectori embeddings pentru conținutul agentului
  - `industry_{agent_id}`: Vectori embeddings pentru industria agentului
- **Rol**: Căutare semantică, RAG (Retrieval Augmented Generation)
- **Model embeddings**: BAAI/bge-large-en-v1.5 (1024 dimensiuni)

### 🔌 Integrări Externe

#### DeepSeek API
- **Endpoint**: `https://api.deepseek.com/v1`
- **Model**: `deepseek-reasoner` (cel mai puternic)
- **Timeout**: 180s cu retry logic (3 încercări)
- **Folosit pentru**: Strategii, reasoning, analize complexe

#### Qwen (Ollama Local)
- **Endpoint**: `http://localhost:9304/v1`
- **Model**: Qwen local pe GPU
- **Folosit pentru**: Task-uri grele locale, embeddings, sumarizare

#### Search Providers
- **SerpAPI**: Căutare Google pentru competitori
- **DuckDuckGo**: Fallback pentru căutare
- **Folosit pentru**: Descoperire competitori, research industrie

### 🎨 Interfața Utilizator

#### `static/main_interface.html`
- **Secțiuni principale**:
  1. **Lista Agenți**: Selectare agent activ
  2. **Agent Master**: Acțiuni pentru agent (creare, analiză, indexare)
  3. **Lanțuri LangChain**: Butoane pentru rulare lanțuri
  4. **Strategie Competitivă**: Afișare strategie generată
  5. **Chat**: Conversație cu agentul
- **Funcționalități**:
  - Creare agenți noi (WebSocket pentru progres)
  - Generare strategie competitivă (DeepSeek)
  - Indexare industrie (paralelizată)
  - Rulare lanțuri LangChain
  - Chat cu agenții

### ⚙️ Configurație și Variabile de Mediu

#### `.env` (Critice)
```bash
# DeepSeek API
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-reasoner

# Qwen Local
QWEN_BASE_URL=http://localhost:9304/v1

# MongoDB
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=ai_agents_db

# Qdrant
QDRANT_URL=http://127.0.0.1:6333
QDRANT_API_KEY=

# Search Providers
SERPAPI_KEY=...
```

### 🚀 Pornire Sistem

```bash
# 1. Pornește MongoDB (dacă nu rulează)
sudo systemctl start mongod

# 2. Pornește Qdrant (dacă nu rulează)
cd /home/mobra && ./qdrant --config-path ./qdrant_config.yaml &

# 3. Pornește Qwen Ollama (dacă nu rulează)
# (depinde de configurația ta)

# 4. Pornește serverul FastAPI
cd /srv/hf/ai_agents
./start_server.sh
# sau manual:
uvicorn --app-dir /home/mobra/ai_agents tools.agent_api:app --host 0.0.0.0 --port 8083
```

### 📊 Metrici și Monitoring

- **Health Check**: `GET /health` - Status toate serviciile
- **Agent Status**: `GET /api/agents/{agent_id}/status` - Status agent specific
- **Logs**: `logs/server_8083.log` - Log-uri server

### 🔒 Securitate și Best Practices

- **API Keys**: Stocate în `.env`, nu în cod
- **CORS**: Configurat pentru acces din browser
- **Timeout-uri**: Configurate pentru a evita blocarea
- **Retry Logic**: Implementat pentru operațiuni critice
- **Error Handling**: Mesaje clare pentru utilizator

### 🎯 Cazuri de Utilizare

1. **Creare Agent pentru Site Nou**
   - User introduce URL site
   - Sistem crawl-ează și indexează automat
   - Agent devine disponibil pentru analiză

2. **Analiză Competitivă**
   - User generează strategie competitivă
   - Sistem analizează site-ul și identifică servicii
   - DeepSeek generează strategie detaliată
   - User poate indexa industria pentru competitori

3. **Chat cu Agent**
   - User pune întrebări despre site
   - Sistem caută în Qdrant pentru context relevant
   - Qwen/DeepSeek generează răspuns bazat pe context
   - Conversația se salvează pentru învățare

4. **Rulare Lanțuri LangChain**
   - User selectează lanț (site_analysis, industry_strategy, decision_chain)
   - Sistem execută lanțul cu Qwen/DeepSeek
   - Rezultatul se salvează și afișează în UI

---

**Notă:** Serverul activ rulează din `tools/agent_api.py`. Fișierul `agent_api.py` din root este o versiune veche și poate fi arhivat.
