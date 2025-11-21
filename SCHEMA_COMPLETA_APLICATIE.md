# 🏗️ SCHEMA COMPLETĂ APLICAȚIE - AI AGENTS PLATFORM

## 🎯 SCOPUL FUNDAMENTAL
**Transformă orice website în Agent AI conversațional cu knowledge base**

---

## 📊 ARHITECTURA COMPLETĂ

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Port 4000: AI Agent Platform (React - Production)                   │
│  ├── Dashboard: Overview, stats, recent agents                       │
│  ├── Agents: Lista agenți, create new, manage                        │
│  ├── AgentDetail: Chat, knowledge base, settings                     │
│  ├── WorkflowMonitor: Progress tracking pentru creare               │
│  └── Reports: CEO reports, competitive intelligence                  │
│                                                                       │
│  Port 5173: Frontend Dev (Vite)                                      │
│  └── Development environment pentru frontend                         │
│                                                                       │
│  Port 5000: SERP Monitoring Admin                                    │
│  └── /static/serp_admin.html - Testing API, monitoring              │
│                                                                       │
│  Port 5001: Auto-Learning UI (NOU)                                   │
│  └── Control pentru fine-tuning, RAG, continuous learning           │
│                                                                       │
│  Port 6000: Live Dashboard (NOU)                                     │
│  └── Monitoring real-time, nodes status, control center             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         API LAYER                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Port 8000: Agent API (FastAPI)                                      │
│  ├── POST /create-site-agent - Creează agent din URL                │
│  ├── GET /agents - Lista agenți                                      │
│  ├── GET /agents/{id} - Detalii agent                               │
│  ├── POST /agents/{id}/chat - Chat cu agent                         │
│  ├── DELETE /agents/{id} - Șterge agent                             │
│  ├── WS /ws/create-agent - WebSocket pentru progress live          │
│  └── GET /docs - Swagger UI                                         │
│                                                                       │
│  Port 5000: SERP Monitoring API                                      │
│  ├── POST /api/serp/run - Start SERP monitoring                     │
│  ├── GET /api/serp/competitors - Lista competitori                  │
│  ├── GET /api/serp/alerts - Alerte rank changes                     │
│  └── POST /api/serp/report/deepseek - Generate CEO report           │
│                                                                       │
│  Port 5010: Master Agent API (NOU)                                   │
│  ├── POST /api/chat - Chat verbal cu Master Agent                   │
│  ├── POST /api/execute - Execute system actions                     │
│  ├── GET /api/state - System status                                 │
│  └── WS /api/ws/{user_id} - WebSocket pentru chat live             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  🕷️ WEB SCRAPING                                                     │
│  ├── BeautifulSoup - HTML parsing                                   │
│  ├── Playwright - Dynamic content                                   │
│  └── Sitemap parsing                                                │
│                                                                       │
│  ✂️ CHUNKING                                                         │
│  ├── 500-1000 chars per chunk                                       │
│  ├── Smart splitting (paragraphs, sentences)                        │
│  └── Metadata extraction                                            │
│                                                                       │
│  🧠 EMBEDDINGS (GPU)                                                 │
│  ├── Model: all-MiniLM-L6-v2                                        │
│  ├── SentenceTransformers                                           │
│  └── Batch processing pe 11 GPU-uri                                 │
│                                                                       │
│  🎭 LLM ORCHESTRATOR                                                 │
│  ├── Kimi K2 70B (primary) - Moonshot AI                            │
│  ├── Together Llama 3.1 70B (fallback 1)                            │
│  ├── DeepSeek (fallback 2)                                          │
│  ├── Qwen 2.5 72B local (fallback 3) - Port 9400                    │
│  └── Qwen 2.5 7B local (emergency) - Port 9201                      │
│                                                                       │
│  📊 COMPETITIVE INTELLIGENCE                                         │
│  ├── Google/Brave Search pentru keywords                            │
│  ├── SERP monitoring (rank tracking)                                │
│  ├── Competitor discovery & scoring                                 │
│  ├── CEO Competitive Maps                                           │
│  └── Automated alerting (Slack/Email)                               │
│                                                                       │
│  🔄 CONTINUOUS LEARNING (NOU)                                        │
│  ├── Data Collector - Salvează toate interacțiunile                 │
│  ├── Build JSONL - Export dataset pentru training                   │
│  ├── Fine-tuning - Training Qwen local                              │
│  ├── RAG Updater - Update Qdrant cu nou knowledge                   │
│  └── Continuous Learner - Process diagnostics & routes              │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                       STORAGE LAYER                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  📦 MONGODB (localhost:27017)                                        │
│  ├── ai_agents_db (PRIMARY)                                         │
│  │   ├── agents (41 agenți)                                         │
│  │   ├── site_agents (9 agenți)                                     │
│  │   ├── conversations (171 conversații)                            │
│  │   ├── site_chunks (227 chunks)                                   │
│  │   ├── serp_runs (7 runs)                                         │
│  │   ├── serp_results                                               │
│  │   ├── serp_alerts                                                │
│  │   ├── competitors                                                │
│  │   ├── competitive_intelligence_reports (2)                       │
│  │   ├── ceo_workflow_executions (2)                                │
│  │   └── ... (35 colecții total)                                    │
│  │                                                                   │
│  ├── adbrain_ai (LEARNING)                                          │
│  │   ├── interactions (9 - toate LLM calls)                         │
│  │   ├── user_profiles (1 - Master Agent users)                     │
│  │   ├── agent_jobs (1 - Background tasks)                          │
│  │   └── agent_interactions (1 - Master Agent chats)                │
│  │                                                                   │
│  └── adbrain_memories (330 docs)                                    │
│                                                                       │
│  🔍 QDRANT (localhost:9306)                                          │
│  ├── Collection per agent (ex: agent_xxx_content)                   │
│  ├── Embeddings 384 dimensions                                      │
│  ├── Cosine similarity search                                       │
│  ├── mem_auto (2 puncte - RAG learning)                             │
│  └── 180+ collections                                               │
│                                                                       │
│  💾 FILESYSTEM                                                       │
│  ├── /srv/hf/ai_agents/datasets/training_data.jsonl                 │
│  ├── /srv/hf/ai_agents/logs/ (toate log-urile)                      │
│  └── /srv/hf/ai_agents/fine_tuning/output/ (modele)                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         GPU LAYER                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  🎮 11x RTX 3080 Ti (12GB each)                                      │
│  ├── Qwen 2.5 72B AWQ (Port 9400)                                   │
│  ├── Qwen 2.5 7B (Port 9201)                                        │
│  ├── SentenceTransformers (embeddings)                              │
│  └── Parallel agent processing                                      │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

---

## 🔄 FLUXUL DE CREARE AGENT

1. **USER**: Introduce URL în UI (port 4000)
   ↓
2. **FRONTEND**: Trimite POST la /create-site-agent (port 8000)
   ↓
3. **BACKEND**: 
   - Validează URL
   - Verifică robots.txt
   - Start scraping (BeautifulSoup/Playwright)
   - Progress → WebSocket
   ↓
4. **SCRAPING**: Extrage text, structură, links
   ↓
5. **CHUNKING**: Split în 500-1000 chars
   ↓
6. **EMBEDDINGS**: Generate pe GPU (all-MiniLM-L6-v2)
   ↓
7. **STORAGE**:
   - MongoDB: agent metadata, chunks
   - Qdrant: vector embeddings
   ↓
8. **LLM VOICE**: DeepSeek creează personality
   ↓
9. **AGENT READY**: Disponibil pentru chat
   ↓
10. **DATA COLLECTION**: Toate chat-urile → adbrain_ai.interactions
   ↓
11. **CONTINUOUS LEARNING**: 
    - Build JSONL → Fine-tune Qwen → Update RAG
    - Agent devine mai inteligent

---

## 📡 INTEGRĂRI

- **Slack**: Alerte SERP
- **Email**: CEO reports
- **Google Search API**: Competitor discovery
- **Brave Search**: Alternative SERP
- **OpenAI API**: Fallback LLM
- **DeepSeek API**: Analysis & reasoning
- **Together AI**: Llama 3.1 70B
- **Moonshot AI**: Kimi K2 70B (orchestrator principal)

---

## 🔧 SERVICII ACTIVE

| Port | Service | Status | Purpose |
|------|---------|--------|---------|
| 4000 | Frontend (React) | ✅ | UI principal agents |
| 5000 | SERP API | ✅ | Monitoring SERP |
| 5001 | Auto-Learning UI | ✅ | Control learning |
| 5010 | Master Agent | ✅ | Chat verbal control |
| 5173 | Frontend Dev | ✅ | Development |
| 6000 | Live Dashboard | ✅ | Real-time monitoring |
| 8000 | Agent API | ✅ | CRUD agents + chat |
| 9201 | Qwen 7B vLLM | ❌ | Emergency LLM |
| 9306 | Qdrant | ✅ | Vector DB |
| 9400 | Qwen 72B vLLM | ❌ | Local LLM |
| 27017 | MongoDB | ✅ | Primary database |

---

## 📊 STATISTICI CURENTE

- **Agenți creați**: 41 (agents) + 9 (site_agents) = 50 total
- **Conversații**: 171
- **Chunks indexed**: 227
- **SERP runs**: 7
- **Competitori tracked**: Multiple
- **Learning interactions**: 9
- **Qdrant collections**: 180+

---

## 🎯 CAPABILITĂȚI COMPLETE

✅ Creare agent din orice site
✅ Chat conversațional cu context
✅ SERP monitoring automat
✅ Competitive intelligence
✅ CEO reports automate
✅ Multi-LLM orchestration cu fallback
✅ Continuous learning cu fine-tuning
✅ RAG updates automate
✅ Master Agent verbal
✅ Real-time monitoring
✅ WebSocket live progress
✅ GPU cluster processing (11 GPUs)
✅ Alerting (Slack/Email)

---

## 🔮 URMĂTORII PAȘI (INTEGRARE)

1. Conectare Auto-Learning UI (5001) → Agent Platform (4000)
2. Buton "Train Agent" în AgentDetail.jsx
3. Statistici learning în Dashboard
4. Master Agent widget în toate UI-urile
5. Live metrics în toate dashboards
6. Unificare logs și monitoring

