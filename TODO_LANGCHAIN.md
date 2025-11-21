# 🧠 TODO_LANGCHAIN.md
# Integrare LangChain în AI Agents Platform (cu Qwen + DeepSeek orchestrat)

## ⚙️ 1. INFRASTRUCTURĂ & CONFIG

**Obiectiv:** integrarea completă a LangChain peste arhitectura existentă (Mongo, Qdrant, Qwen, DeepSeek, Orchestrator).

### Taskuri:

- [x] Creează directorul `langchain_agents/` cu subfoldere:
  - `chains/`
  - `agents/`
  - `tools/`
  - `memory/`

- [x] Adaugă fișierul `langchain_agents/__init__.py` pentru importuri centralizate.

- [ ] În `requirements.txt`, confirmă / adaugă:
  ```
  langchain
  langchain-core
  langchain-community
  langchain-openai
  langchain-qdrant
  ```

- [ ] În `config.env`, definește variabile pentru LangChain:
  ```
  LANGCHAIN_CACHE_ENABLED=true
  LANGCHAIN_VERBOSE=false
  ```

- [ ] În `config/settings.yaml`, adaugă secțiunea:
  ```yaml
  langchain:
    memory_provider: "mongo"
    vector_store: "qdrant"
    default_llm: "qwen"
    reasoning_llm: "deepseek"
  ```

---

## 🤖 2. LLM MANAGER – Unificare Qwen + DeepSeek pentru LangChain

**Obiectiv:** permite LangChain să folosească Qwen (Ollama) și DeepSeek ca LLM/ChatModel compatibil.

### Taskuri:

- [x] Creează fișierul `langchain_agents/llm_manager.py`.

- [x] Implementează un manager cu funcții:
  - `get_langchain_llm("qwen")` → returnează client Qwen (via Ollama)
  - `get_langchain_llm("deepseek")` → returnează client DeepSeek (via OpenAI API)

- [ ] Adaugă un parametru `mode` ("fast", "reasoning") pentru a selecta automat modelul potrivit.

- [ ] Adaugă caching cu LangChainLLMCache dacă variabila `LANGCHAIN_CACHE_ENABLED=true`.

---

## 🔄 3. SITE ANALYSIS CHAIN – Analiza completă a unui site

**Obiectiv:** lanț care combină Qwen (sumarizare, clasificare) și DeepSeek (strategie).

### Taskuri:

- [x] Creează `langchain_agents/chains/site_analysis_chain.py`.

- [x] Pași logici:
  - Qwen → rezumă fiecare pagină (`summarize_page_chain`)
  - Qwen → clasifică tipul de pagină (`classify_page_chain`)
  - Qwen → extrage entități (servicii, teme, CTA)
  - DeepSeek → sintetizează analiza într-un raport global (`site_overview_chain`)

- [x] Output final JSON:
  ```json
  {
    "pages_summary": [...],
    "site_focus": "...",
    "strengths": ["..."],
    "weaknesses": ["..."],
    "opportunities": ["..."]
  }
  ```

- [ ] Adaugă suport pentru caching per site (hash bazat pe URL + conținut).

---

## 💼 4. INDUSTRY STRATEGY CHAIN – Strategie concurențială orchestrală

**Obiectiv:** lanț LangChain care generează planul de acțiune competitiv (DeepSeek + Qwen).

### Taskuri:

- [x] Creează `langchain_agents/chains/industry_strategy_chain.py`.

- [x] Pași:
  - Qwen → normalizează serviciile extrase (nume, aliasuri, categorie)
  - DeepSeek → analizează competiția și generează strategie de industrie
  - Qwen → extrage „action items” concrete (format JSON)

- [ ] Rezultatul se salvează în Mongo (colecția `strategies`).

- [ ] Integrează notificări progres prin orchestrator (WebSocket UI).

- [x] Returnează structura:
  ```json
  {
    "strategy_summary": "...",
    "industry_opportunities": [...],
    "action_plan": [
      {"task": "...", "priority": "high", "tool": "google_ads"}
    ]
  }
  ```

---

## 🧩 5. SITE AGENT (LangChain Agent autonom)

**Obiectiv:** fiecare site devine un agent LangChain cu tool-uri proprii.

### Taskuri:

- [x] Creează `langchain_agents/agents/site_agent.py`.

- [x] Initializează agentul cu:
  - memorie vectorială Qdrant (`mem_{site_id}`)
  - tool-uri:
    - `VectorSearchTool`
    - `ScraperTool`
    - `ServiceExtractorTool`
  - LLM default: Qwen

- [x] Comportamente:
  - poate răspunde la întrebări despre site
  - poate analiza performanța paginilor
  - poate propune campanii publicitare

- [ ] Salvează output-ul conversațiilor în Mongo (colecția `episodes`).

---

## 🧠 6. GLOBAL ORCHESTRATOR AGENT

**Obiectiv:** un meta-agent LangChain care decide ce lanț sau model trebuie rulat.

### Taskuri:

- [ ] Creează `langchain_agents/agents/global_orchestrator.py`.

- [ ] Acest agent:
  - primește o cerere (text natural)
  - identifică intenția („analiză site”, „strategie industrie”, „optimizare conținut”)
  - alege lanțul potrivit dintr-un registry (`chain_registry.py`)
  - decide dacă folosește Qwen sau DeepSeek

- [ ] Adaugă fallback:
  - dacă cererea e scurtă → Qwen
  - dacă e complexă → lanț DeepSeek orchestrat

- [ ] Înregistrează agentul global în `agent_api.py` pentru endpoint `/global/orchestrate`.

---

## 📦 7. TOOL-URI LANGCHAIN PERSONALIZATE

**Obiectiv:** permite agenților să interacționeze cu resursele platformei.

### Taskuri:

- [x] Creează `langchain_agents/tools/` și adaugă tool-uri:
  - `VectorSearchTool` – căutare în Qdrant
  - `ScraperTool` – extrage text dintr-un URL
  - `SEOAuditTool` – mic raport SEO pe baza conținutului
  - `CompetitorTool` – caută competitori similari (folosește `search_providers.py`)
  - `InsightTool` – extrage insight-uri din Mongo (`agent_repository`)

- [x] Fiecare tool are descriere clară (`name`, `description`, `func`) pentru LangChain `Tool()`.

---

## 🧩 8. MEMORY MANAGER

**Obiectiv:** sincronizează memoria LangChain (short-term) cu Mongo + Qdrant (long-term).

### Taskuri:

- [x] Creează `langchain_agents/memory/memory_manager.py`.

- [x] Implementează clase:
  - `AgentShortMemory` – conversațională (LangChain BufferMemory)
  - `AgentLongMemory` – salvată în Mongo și Qdrant

- [ ] Integrează salvarea automată la finalul fiecărei sesiuni (via OrchestratorLoop).

- [x] Expune funcții:
  - `load_memory(agent_id)`
  - `sync_memory(agent_id, data)`
  - `clear_memory(agent_id)`

---

## ⚡ 9. INTEGRARE CU ORCHESTRATOR

**Obiectiv:** să rulezi lanțurile LangChain ca taskuri async.

### Taskuri:

- [ ] În `orchestrator/orchestrator_loop.py`:
  - extinde `run_task()` astfel încât să poată apela lanțuri LangChain.
  - adaugă `run_chain_task(chain_name, params)` pentru taskurile de tip LangChain.

- [x] Creează `langchain_agents/chain_registry.py` care mapează:
  ```python
  {
    "site_analysis": SiteAnalysisChain,
    "industry_strategy": IndustryStrategyChain
  }
  ```

- [ ] Asigură-te că progresul fiecărui lanț este raportat prin WebSocket (`ws/tasks/{id}`).

---

## 🧠 10. DECISION CHAIN (Plan de acțiune concret)

**Obiectiv:** extrage din outputul DeepSeek acțiuni clare, executabile.

### Taskuri:

- [x] Creează `langchain_agents/chains/decision_chain.py`.

- [x] Input: strategia completă de industrie (text).

- [x] Qwen interpretează și generează JSON cu acțiuni:
  ```json
  [
    {"action": "Creează campanie Google Ads", "service": "stingere incendii"},
    {"action": "Optimizează pagină SEO", "page": "/servicii/protectie-foc"}
  ]
  ```

- [ ] Outputul devine un „ActionPlan” trimis către modulul `actions/` (în viitor).

---

## 🧰 11. UI & API INTEGRARE

**Obiectiv:** expune lanțurile LangChain direct în interfața platformei.

### Taskuri:

- [ ] În `agent_api.py`, adaugă endpointuri:
  - `/agents/{id}/run_chain/{chain_name}`
  - `/chains/{chain_name}/preview`

- [ ] În `static/main_interface.html`, adaugă:
  - buton „Rulare Lanț LangChain”
  - indicator progres (WebSocket)

- [ ] În `agent_status.html`, afișează:
  - lanțuri disponibile
  - stare LLM local (Qwen)
  - stare LLM remote (DeepSeek)

---

## 🧭 12. ACT-TO-ACTION – Faza de execuție

**Obiectiv:** conectează outputurile LangChain la acțiuni reale (Google Ads, WordPress etc).

### Taskuri:

- [ ] Creează directorul `actions/`.

- [ ] Adaugă conectori:
  - `google_ads_connector.py`
  - `wordpress_connector.py`
  - `seo_api_connector.py`

- [ ] Fiecare primește un `ActionPlan` JSON și execută automat taskurile.

- [ ] Leagă execuția de `decision_chain.py` — dacă apare acțiunea „creează campanie”, declanșează jobul corespunzător.

- [ ] Adaugă monitorizare în Mongo (colecția `executed_actions`).

---

## 🧩 13. TESTE & VERIFICĂRI

### Taskuri finale:

- [ ] Testează fiecare lanț individual:
  - `SiteAnalysisChain`
  - `IndustryStrategyChain`
  - `DecisionChain`

- [ ] Verifică persistenta memoriei în Mongo/Qdrant.

- [ ] Rulează orchestrator async + UI live pentru 1 site.

- [ ] Confirmă că Qwen face toate joburile „light” local.

- [ ] Confirmă că DeepSeek intră doar pentru reasoning strategic.

---

## 🏁 14. FUTURE PHASES

Opționale (dar recomandate):

- [ ] Adaugă LangGraph pentru fluxuri adaptive.

- [ ] Adaugă „agent marketplaces” (agenți ce colaborează între site-uri).

- [ ] Adaugă scoring de performanță (agenții care evoluează autonom).

- [ ] Conectează platforma la API-uri externe (Search Console, Analytics, CRM).

---

## 📊 Status General

- ✅ **Completat:** 8/14 secțiuni principale
- 🔄 **În progres:** 0/14 secțiuni
- ⏳ **Până acum:** Infrastructură de bază, Chains, Agents, Tools, Memory

---

**Ultima actualizare:** 2025-11-06

