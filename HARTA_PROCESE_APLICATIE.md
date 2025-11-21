# 🗺️ Harta Proceselor - AI Agents Platform

**Data creării:** 2025-11-06  
**Versiune:** 1.0  
**Server:** http://100.66.157.27:8083

---

## 📋 Cuprins

1. [Arhitectura Generală](#arhitectura-generala)
2. [Procesul de Creare Agent](#procesul-de-creare-agent)
3. [Procesul de Indexare Industrie](#procesul-de-indexare-industrie)
4. [Procesul de Chat/Conversație](#procesul-de-chatconversatie)
5. [Procesul de Discovery Competitori](#procesul-de-discovery-competitori)
6. [Procesul de Generare Strategie](#procesul-de-generare-strategie)
7. [Integrări Servicii Externe](#integrari-servicii-externe)
8. [WebSocket-uri Real-Time](#websocket-uri-real-time)
9. [Fluxuri de Date](#fluxuri-de-date)

---

## 🏗️ Arhitectura Generală

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT (Browser)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   HTML/JS    │  │   WebSocket  │  │   REST API   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────────┐
│                    FastAPI Server (Port 8083)                   │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              tools/agent_api.py (Main Entry)              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Endpoints  │  │  WebSockets  │  │  Background  │        │
│  │   REST API   │  │   Real-Time  │  │    Tasks     │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          │                  │                  │
    ┌─────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐
    │ MongoDB   │      │  Qdrant   │      │   LLMs    │
    │  :27017   │      │  :6333    │      │           │
    └───────────┘      └───────────┘      └───────────┘
                              │                  │
                              │                  │
                        ┌─────▼─────┐      ┌─────▼─────┐
                        │  Qwen     │      │ DeepSeek  │
                        │  :9304    │      │  (API)    │
                        └───────────┘      └───────────┘
```

---

## 🚀 Procesul de Creare Agent

### Endpoint: `POST /ws/create-agent` (WebSocket)

**Flux complet:**

```
1. CLIENT → WebSocket Connection
   └─> URL: ws://100.66.157.27:8083/ws/create-agent?url=https://example.com

2. SERVER → Accept Connection
   └─> tools/agent_api.py: create_agent_websocket()
       └─> create_site_agent_ws(websocket, url, api_key)

3. SERVER → Verificare Agent Existent
   └─> site_agent_creator.py: create_agent_logic()
       └─> MongoDB: agents_collection.find_one({"site_url": url})
           ├─> Dacă există → Return "existed" + agent_id
           └─> Dacă nu există → Continuă procesul

4. SERVER → Extragere Informații Site
   └─> AutoSiteExtractor.extract_site_data(domain)
       ├─> HTTP Request → Site URL
       ├─> BeautifulSoup → Parse HTML
       ├─> Regex → Extract contact info, company info, services
       └─> MongoDB: db.site_data.replace_one() → Salvează datele

5. SERVER → Creare Agent în MongoDB
   └─> _upsert_agent(url, name, domain, status="ready")
       └─> MongoDB: agents_collection.update_one() → Creează/Actualizează agent

6. SERVER → Crawling Site
   └─> crawl_and_scrape_site(url, loop, websocket)
       ├─> Playwright → Navigate site
       ├─> BeautifulSoup → Extract text
       ├─> Recursive crawling → Max 200 pagini
       └─> Return: concatenated text content

7. SERVER → Chunking Text
   └─> RecursiveCharacterTextSplitter
       ├─> chunk_size: 50000 caractere
       ├─> chunk_overlap: 5000 caractere
       └─> Return: list of chunks

8. SERVER → Salvare Chunks în MongoDB
   └─> db.site_content.insert_many()
       └─> Salvează chunks cu metadata (agent_id, chunk_index, url)

9. SERVER → Creare Vectori și Salvare în Qdrant
   └─> create_vectorstore_direct() [în thread pool]
       ├─> QdrantClient → HTTP connection (port 6333)
       ├─> client.create_collection() → Creează colecție "agent_{agent_id}"
       ├─> HuggingFaceEmbeddings → Generează embeddings (1024 dim)
       │   └─> Model: BAAI/bge-large-en-v1.5
       ├─> embeddings.embed_query(chunk) → Pentru fiecare chunk
       ├─> PointStruct → Creează puncte cu vectori + payload
       └─> client.upsert() → Salvează vectori în Qdrant
           └─> Retry logic: 3 încercări cu exponential backoff

10. SERVER → Inițializare Memorie și Qwen Learning
    └─> MongoDB: agents_collection.update_one()
        ├─> memory_initialized: True
        ├─> memory_config: {conversation_history, learning_collection, ...}
        ├─> qwen_integrated: True
        └─> qwen_learning_enabled: True

11. SERVER → Finalizare
    └─> send_status(websocket, "final", {agent_id, summary, ...})
        └─> CLIENT → Primește mesaj final cu agent_id și detalii
```

**Componente implicate:**
- `site_agent_creator.py`: create_agent_logic(), create_site_agent_ws()
- `auto_site_extractor.py`: AutoSiteExtractor
- `tools/agent_api.py`: create_agent_websocket()
- MongoDB: `ai_agents_db.site_agents`, `ai_agents_db.site_data`, `ai_agents_db.site_content`
- Qdrant: Colecție `agent_{agent_id}` cu vectori 1024-dim
- HuggingFace Embeddings: BAAI/bge-large-en-v1.5

**Durată estimată:** 30-120 secunde (depinde de mărimea site-ului)

---

## 📊 Procesul de Indexare Industrie

### Endpoint: `POST /api/index-industry`

**Flux complet:**

```
1. CLIENT → POST Request
   └─> POST /api/index-industry
       Body: {agent_id, max_sites: 20, concurrency: 5}

2. SERVER → Obține Agent Principal
   └─> MongoDB: agents_collection.find_one({"_id": ObjectId(agent_id)})

3. SERVER → Obține/Generează Strategie Competitivă
   └─> MongoDB: strategies_collection.find_one({"agent_id": agent_id})
       ├─> Dacă există → Folosește strategia existentă
       └─> Dacă nu există → competitive_strategy.py: analyze_agent_and_generate_strategy()
           ├─> Obține conținut din Qdrant sau MongoDB
           ├─> DeepSeek API → reasoner_chat() → Generează strategie
           └─> MongoDB: strategies_collection.insert_one() → Salvează strategia

4. SERVER → Descoperă Competitori
   └─> competitor_discovery.py: discover_competitors_from_strategy()
       ├─> Web Search → Folosește strategia pentru queries
       ├─> Filtrare → Exclude domain-ul principal
       └─> Return: Lista de URL-uri competitori

5. SERVER → Indexare Paralelă Competitori
   └─> asyncio.gather() cu Semaphore(concurrency)
       └─> Pentru fiecare competitor URL:
           ├─> create_agent_logic(url, api_key, loop, websocket)
           │   └─> Același proces ca la creare agent (pasii 4-10)
           ├─> MongoDB: industry_resources_collection.insert_one()
           │   └─> Salvează resursă industrială
           └─> WebSocket → Trimite progres pentru fiecare site

6. SERVER → Finalizare
   └─> Return: {
           "ok": True,
           "summary": {
               "total_sites": X,
               "successful": Y,
               "failed": Z,
               "competitors": [...]
           }
       }
```

**Componente implicate:**
- `industry_indexer.py`: index_industry_for_agent()
- `competitive_strategy.py`: CompetitiveStrategyGenerator
- `competitor_discovery.py`: discover_competitors_from_strategy()
- `site_agent_creator.py`: create_agent_logic() (reutilizat)
- DeepSeek API: reasoner_chat() pentru strategie
- MongoDB: `ai_agents_db.competitive_strategies`, `ai_agents_db.industry_resources`

**Durată estimată:** 5-30 minute (depinde de numărul de competitori și concurrency)

---

## 💬 Procesul de Chat/Conversație

### Endpoint: `POST /ask` sau `WebSocket /ws/task/{agent_id}`

**Flux complet:**

```
1. CLIENT → POST Request sau WebSocket
   └─> POST /ask
       Body: {agent_id, question, conversation_history: []}
   SAU
   └─> WebSocket: /ws/task/{agent_id}?strategy=...

2. SERVER → Obține Agent
   └─> MongoDB: agents_collection.find_one({"_id": ObjectId(agent_id)})

3. SERVER → Obține Context din Qdrant
   └─> Qdrant: collection_name = agent.get("vector_collection")
       ├─> HuggingFaceEmbeddings → Generează embedding pentru question
       ├─> Qdrant: client.search() → Caută vectori similari
       ├─> Top K rezultate (K=5-10)
       └─> Extract: text chunks relevante

4. SERVER → Construiește Prompt
   └─> Combină:
       ├─> System prompt (instrucțiuni agent)
       ├─> Context din Qdrant (chunks relevante)
       ├─> Conversation history (ultimele N mesaje)
       └─> User question

5. SERVER → Generează Răspuns
   └─> Qwen Client (local GPU) SAU OpenAI Client
       ├─> Qwen: http://localhost:9304/v1 (preferat pentru sarcini grele)
       ├─> OpenAI: API fallback (dacă Qwen nu e disponibil)
       └─> LLM.generate() → Generează răspuns

6. SERVER → Salvare Conversație
   └─> MongoDB: db.conversations.insert_one()
       ├─> agent_id, question, answer, timestamp
       └─> Qwen Learning: db.qwen_learning_{agent_id}.insert_one()
           └─> Pentru învățare ulterioară

7. SERVER → Return Răspuns
   └─> CLIENT → Primește răspuns + metadata
```

**Componente implicate:**
- `site_specific_intelligence.py`: SiteSpecificIntelligence
- `task_executor.py`: handle_task_conversation()
- Qwen: http://localhost:9304/v1 (local GPU)
- Qdrant: Vector search pentru context retrieval
- MongoDB: `ai_agents_db.conversations`, `ai_agents_db.qwen_learning_{agent_id}`

**Durată estimată:** 1-5 secunde (depinde de LLM și complexitatea întrebării)

---

## 🔍 Procesul de Discovery Competitori

### Endpoint: `POST /admin/industry/{agent_id}/discover`

**Flux complet:**

```
1. CLIENT → POST Request
   └─> POST /admin/industry/{agent_id}/discover
       Body: {limit: 12, queries: [...]}

2. SERVER → Obține Agent
   └─> MongoDB: agents_collection.find_one({"_id": ObjectId(agent_id)})

3. SERVER → Generează Queries (dacă nu sunt furnizate)
   └─> tools/admin_discovery.py: generate_queries()
       ├─> Obține seed_text din MongoDB (site_content sau site_data)
       ├─> LLM Call → Generează queries de căutare
       └─> Fallback: Queries deterministe dacă LLM eșuează

4. SERVER → Web Search pentru Fiecare Query
   └─> tools/admin_discovery.py: web_search()
       ├─> SERP API sau Search Provider
       ├─> Obține rezultate (URL-uri, titluri, snippets)
       └─> Return: Lista de candidați

5. SERVER → Scorare și Filtrare
   └─> Pentru fiecare candidat:
       ├─> Verifică dacă e deja indexat
       ├─> Calculează relevanță (similaritate cu agent principal)
       └─> Filtrează duplicate și site-uri irelevante

6. SERVER → Return Rezultate
   └─> CLIENT → Primește lista de competitori cu scoruri
       {
           "ok": True,
           "count": X,
           "results": [
               {url, title, score, reason, ...}
           ],
           "queries": [...]
       }
```

**Componente implicate:**
- `tools/admin_discovery.py`: discover_competitors(), web_search(), generate_queries()
- SERP API sau Search Provider
- MongoDB: `ai_agents_db.site_content`, `ai_agents_db.site_data`

**Durată estimată:** 10-30 secunde (depinde de numărul de queries)

---

## 🎯 Procesul de Generare Strategie

### Endpoint: `POST /api/analyze-agent`

**Flux complet:**

```
1. CLIENT → POST Request
   └─> POST /api/analyze-agent
       Body: {agent_id}

2. SERVER → Obține Agent
   └─> MongoDB: agents_collection.find_one({"_id": ObjectId(agent_id)})

3. SERVER → Obține Conținut Site
   └─> Qdrant SAU MongoDB:
       ├─> Qdrant: collection_name = agent.get("vector_collection")
       │   └─> client.scroll() → Obține toate vectorii
       └─> MongoDB: db.site_content.find({"agent_id": agent_id})
           └─> Fallback dacă Qdrant e gol

4. SERVER → Construiește Prompt pentru DeepSeek
   └─> competitive_strategy.py: _build_analysis_prompt()
       ├─> Informații agent (domain, business_type, services)
       ├─> Conținut site (extras din Qdrant/MongoDB)
       └─> Instrucțiuni pentru analiză competitivă

5. SERVER → Generează Strategie cu DeepSeek
   └─> tools/deepseek_client.py: reasoner_chat()
       ├─> DeepSeek API → POST request
       ├─> Model: deepseek-reasoner (cel mai puternic)
       └─> Return: Strategie JSON structurată

6. SERVER → Parse și Validare Strategie
   └─> JSON.parse() → Validează structura
       ├─> services: Lista de servicii identificate
       ├─> target_audience: Audiență țintă
       ├─> competitive_advantages: Avantaje competitive
       ├─> research_priorities: Priorități de cercetare
       └─> expected_outcomes: Rezultate așteptate

7. SERVER → Salvare Strategie
   └─> MongoDB: strategies_collection.replace_one()
       ├─> agent_id, strategy, created_at, updated_at
       └─> Index: {"agent_id": 1} pentru căutare rapidă

8. SERVER → Return Strategie
   └─> CLIENT → Primește strategia completă
       {
           "ok": True,
           "strategy": {...},
           "agent_id": "...",
           "timestamp": "..."
       }
```

**Componente implicate:**
- `competitive_strategy.py`: CompetitiveStrategyGenerator
- `tools/deepseek_client.py`: reasoner_chat()
- DeepSeek API: deepseek-reasoner model
- Qdrant: Vector retrieval pentru conținut
- MongoDB: `ai_agents_db.competitive_strategies`

**Durată estimată:** 10-30 secunde (depinde de mărimea conținutului și DeepSeek API)

---

## 🔌 Integrări Servicii Externe

### MongoDB (Port 27017)

**Colecții principale:**
- `site_agents`: Agenți creați
- `site_data`: Date extrase din site-uri
- `site_content`: Chunks de conținut pentru fiecare agent
- `competitive_strategies`: Strategii competitive generate
- `industry_resources`: Resurse industriale indexate
- `conversations`: Istoric conversații
- `qwen_learning_{agent_id}`: Date de învățare pentru Qwen

**Utilizare:**
- Stocare date structurate
- Fallback pentru Qdrant
- Istoric conversații
- Metadata agenți

### Qdrant (Port 6333, HTTP)

**Colecții:**
- `agent_{agent_id}`: Vectori pentru fiecare agent
  - Vector size: 1024 (BAAI/bge-large-en-v1.5)
  - Distance: COSINE
  - Payload: text, chunk_index, agent_id, url

**Utilizare:**
- Vector search pentru context retrieval
- Semantic similarity search
- RAG (Retrieval-Augmented Generation)

**Configurație:**
- Protocol: HTTP (prefer_grpc=False)
- Timeout: 60 secunde
- Retry: 3 încercări cu exponential backoff

### Qwen (Port 9304, Local GPU)

**Endpoint:** http://localhost:9304/v1

**Utilizare:**
- Sarcini grele (crawling, embeddings, indexing)
- Chat/Conversație
- Generare conținut
- Procesare locală pe GPU

**Model:** qwen2.5 (configurat în env)

### DeepSeek (API Extern)

**Endpoint:** https://api.deepseek.com

**Utilizare:**
- Reasoning și strategie
- Analiză competitivă
- Generare recomandări

**Model:** deepseek-reasoner (cel mai puternic)

**Configurație:**
- API Key: DEEPSEEK_API_KEY (env)
- Timeout: 60 secunde
- Retry: 3 încercări

### HuggingFace Embeddings

**Model:** BAAI/bge-large-en-v1.5

**Utilizare:**
- Generare embeddings pentru Qdrant
- Vector search
- Semantic similarity

**Configurație:**
- Device: CPU
- Normalize embeddings: True
- Vector size: 1024

---

## 🔄 WebSocket-uri Real-Time

### `/ws/create-agent`

**Scop:** Creare agent cu updates în timp real

**Mesaje trimise:**
```json
{
  "status": "progress",
  "message": "Extrag informații din site-ul example.com..."
}
```

**Status-uri:**
- `progress`: Update progres
- `final`: Finalizare cu succes
- `error`: Eroare

**Exemplu mesaj final:**
```json
{
  "status": "final",
  "message": {
    "status": "success",
    "agent_id": "690a3230a55790fced1272cb",
    "details": {
      "content_extracted": "150,000 caractere",
      "vectors_saved": "45 vectori",
      "memory_configured": "✅ Da",
      "collection_created": "✅ Da"
    }
  }
}
```

### `/ws/task/{agent_id}`

**Scop:** Conversație cu agent prin WebSocket

**Mesaje trimise:**
```json
{
  "type": "status",
  "data": "🔍 Caut informații relevante..."
}
```

**Tipuri mesaje:**
- `status`: Update status
- `response`: Răspuns final
- `error`: Eroare

---

## 📈 Fluxuri de Date

### Flux 1: Creare Agent → Indexare → Chat

```
1. Creare Agent
   └─> MongoDB: site_agents, site_data, site_content
   └─> Qdrant: agent_{agent_id} (vectori)

2. Indexare Industrie (opțional)
   └─> MongoDB: competitive_strategies, industry_resources
   └─> Qdrant: agent_{competitor_id} (pentru fiecare competitor)

3. Chat/Conversație
   └─> Qdrant: Search vectori similari
   └─> Qwen: Generează răspuns
   └─> MongoDB: Salvează conversație
```

### Flux 2: Strategie → Discovery → Indexare

```
1. Generare Strategie
   └─> DeepSeek: Analizează agent și generează strategie
   └─> MongoDB: competitive_strategies

2. Discovery Competitori
   └─> Web Search: Folosește strategia pentru queries
   └─> Return: Lista competitori

3. Indexare Competitori
   └─> Pentru fiecare competitor:
       └─> Creare agent (același proces ca Flux 1)
       └─> MongoDB: industry_resources
```

### Flux 3: Qwen Learning

```
1. Conversație
   └─> MongoDB: conversations

2. Qwen Learning (după conversație)
   └─> MongoDB: qwen_learning_{agent_id}
   └─> Pattern analysis
   └─> Context enhancement

3. Îmbunătățire Răspunsuri
   └─> Qwen folosește datele de învățare
   └─> Răspunsuri mai precise și contextuale
```

---

## 🔧 Configurație Environment Variables

```bash
# MongoDB
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=ai_agents_db

# Qdrant
QDRANT_URL=http://127.0.0.1:6333
QDRANT_API_KEY=

# Qwen (Local GPU)
QWEN_BASE_URL=http://localhost:9304/v1
QWEN_API_KEY=local
QWEN_MODEL=qwen2.5

# DeepSeek
DEEPSEEK_API_KEY=sk-...

# Embeddings
EMBEDDING_MODEL=nomic-embed-text
```

---

## 📊 Metrici și Monitoring

### Endpoints de Health Check

- `GET /health`: Health check general
- `GET /ready`: Verificare readiness
- `GET /api/agents/{agent_id}/status`: Status agent specific

### Logging

- Logs: `/srv/hf/ai_agents/server_8083.log`
- Level: INFO, ERROR, WARNING
- Format: `%(asctime)s - %(levelname)s - %(message)s`

---

## 🎯 Concluzii

**Arhitectura aplicației:**
- ✅ FastAPI backend cu REST API și WebSocket
- ✅ MongoDB pentru date structurate
- ✅ Qdrant pentru vector search
- ✅ Qwen local pentru sarcini grele
- ✅ DeepSeek pentru reasoning și strategie
- ✅ HuggingFace embeddings pentru semantic search

**Procese principale:**
1. Creare agent: AutoSiteExtractor → Crawling → Chunking → Qdrant
2. Indexare industrie: Strategie → Discovery → Indexare paralelă
3. Chat: Qdrant search → Qwen generation → Salvare conversație
4. Strategie: DeepSeek analysis → MongoDB storage

**Optimizări:**
- Paralelizare pentru indexare industrie (concurrency parameter)
- Retry logic pentru Qdrant și DeepSeek
- Fallback MongoDB dacă Qdrant eșuează
- Caching pentru embeddings și strategii

---

**Document creat:** 2025-11-06  
**Ultima actualizare:** 2025-11-06

