# Firecodes AI Agents

📌 **Firecodes AI Agents** este o platformă modulară pentru construcția și orchestrarea de agenți AI autonomi, scalabili și distribuiți.  
Proiectul integrează **multi-agent systems**, orchestrare GPU, inteligență de piață, analiză cross-industry și pipeline-uri de învățare automată.

---

## 📂 Structura proiectului

### 🔹 Agenți și orchestrare
- `agents/` – agenți AI individuali, cu roluri și abilități specifice.  
- `multi_agent/` – module pentru coordonarea agenților multipli.  
- `agent_swarm/` – implementare de tip swarm intelligence pentru interacțiunea agenților.  
- `orchestrator/` – orchestratorul central care gestionează taskuri, resurse și comunicarea între agenți.  
- `swarm_intelligence/` – algoritmi pentru auto-organizare și comportamente emergente.

### 🔹 API și integrare
- `api/` – endpointuri pentru acces extern la agenți și orchestrator.  
- `adapters/` – conectori și adaptoare pentru integrarea cu sisteme externe.  
- `client_features/` – module pentru funcționalități orientate către client.  
- `config/` – fișiere de configurare.  

### 🔹 Business & Intelligence
- `business_intelligence/` – analize pentru decizii de business.  
- `ecosystem_discovery/` – detectarea oportunităților într-un ecosistem.  
- `ecosystem_intelligence/` – analiză holistică a ecosistemului AI.  
- `market_intelligence/` – module pentru studii de piață și competiție.  
- `industry_solutions/` – soluții verticale dedicate pe industrii.  
- `cross_industry_analysis/` – analiză comparativă între industrii.  
- `revenue_optimization/` – algoritmi pentru optimizarea veniturilor.

### 🔹 Machine Learning & Data
- `learning/` – pipeline-uri de învățare și modele AI.  
- `training/` – scripturi și proceduri de antrenare.  
- `retrieval/` – RAG & căutare vectorială.  
- `model_marketplace/` – marketplace de modele AI.  
- `optimized/` – variante optimizate ale agenților și modelelor.  
- `digital_beings/` – entități AI autonome cu memorie și comportamente.

### 🔹 Infra & Tools
- `gpu_orchestration/` – orchestrare GPU pentru taskuri distribuite.  
- `tools/` – unelte auxiliare.  
- `scripts/` – scripturi de rulare și automatizare.  
- `scrapers/` & `web_scraping/` – module pentru colectare de date (scraping).  
- `logs/` & `results/` – jurnale de execuție și rezultate.  
- `reports_RO/` – rapoarte generate (în română).  
- `database/` – conectare și structură baze de date.  
- `.secrets/` – configurări private.

---

## 📜 Fișiere principale

- `main_pipeline.py` – pipeline principal pentru orchestrarea agenților și taskurilor.  
- `final_cli.py` / `cli_agent.py` / `cli_smart_agent.py` – interfață CLI pentru rularea agenților.  
- `cli_vllm_agent.py` / `cli_vllm_agent_fixed.py` – CLI pentru agenți LLM.  
- `agent_collaboration_test.py` – test pentru colaborarea între agenți.  
- `preload_agents.py` – script de încărcare inițială a agenților.  
- `ecosystem_builder.py` – builder pentru ecosisteme AI.  
- `digital_beings_launcher.py` – lansator pentru agenți digitali.  
- `business_intelligence_dashboard.py` – dashboard BI.  
- `multi_agent_dashboard.py` – dashboard pentru coordonare multi-agent.  
- `hybrid_dashboard.py` – dashboard pentru hibrid intelligence.  
- `background_cache.py` – sistem de caching.  
- `real_industry_analyzer.py` / `real_industry_analyzer_fixed.py` – analizor pentru industrii reale.  
- `run_supervisor.sh` – script de pornire a supervisor-ului.  
- `test_model.py` – test rapid pentru modele.  

---

## 📊 Documentație și Status
- `PROJECT_STATUS_FIRECODES.md` – document de stare al proiectului.  
- `roadmap/` – plan de dezvoltare și pași următori.  

---

## 🚀 Funcționalități principale

- Orchestrare de agenți AI distribuiți (single-agent și multi-agent).  
- Integrare între **swarm intelligence** și **business intelligence**.  
- Analiză cross-industry și optimizare de venituri.  
- Scraping & colectare de date în timp real.  
- RAG (retrieval augmented generation) și căutare vectorială.  
- Dashboard-uri pentru monitorizare și management.  
- Orchestrare GPU pentru taskuri AI intensive.  

---

## ▶️ Cum rulezi proiectul

1. Clonează repo-ul:
   ```bash
   git clone https://github.com/mobra-sabi/firecodes-ai-agents.git
   cd firecodes-ai-agents
