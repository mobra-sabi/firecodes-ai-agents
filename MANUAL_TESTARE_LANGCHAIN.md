# 🧪 Manual de Testare - Integrare LangChain

## 📋 Cuprins

1. [Prezentare Generală](#prezentare-generală)
2. [Arhitectură și Fluxuri](#arhitectură-și-fluxuri)
3. [Testare Manuală în UI](#testare-manuală-în-ui)
4. [Testare Automată](#testare-automată)
5. [Testare API Directă](#testare-api-directă)
6. [Scenarii de Testare](#scenarii-de-testare)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Prezentare Generală

Platforma AI Agents integrează **LangChain** pentru a oferi lanțuri de procesare inteligentă care combină:
- **Qwen** (local, GPU) - pentru taskuri grele (crawling, embeddings, sumarizare)
- **DeepSeek** (API) - pentru reasoning strategic și analize complexe
- **Qdrant** - pentru stocare vectorială și RAG
- **MongoDB** - pentru memorie persistentă

### Lanțuri Disponibile

1. **Site Analysis Chain** (`site_analysis`)
   - Input: Conținut site
   - Output: Rezumat, tipuri pagini, puncte forte/slabe, oportunități
   - LLM: Qwen (sumarizare) + DeepSeek (strategie)

2. **Industry Strategy Chain** (`industry_strategy`)
   - Input: Lista servicii, date competitori
   - Output: Strategie competitivă, oportunități industrie, plan acțiuni
   - LLM: DeepSeek (reasoning strategic) + Qwen (normalizare)

3. **Decision Chain** (`decision_chain`)
   - Input: Strategie competitivă
   - Output: Plan acțiuni concrete (immediate, short-term, medium-term, long-term)
   - LLM: Qwen (extrageri structurate)

---

## 🏗️ Arhitectură și Fluxuri

### Diagramă Flux General

```
┌─────────────────────────────────────────────────────────────┐
│                    AI AGENTS PLATFORM                       │
│                  (FastAPI + MongoDB + Qdrant)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │      LangChain Integration Layer       │
        │  (langchain_agents/chain_registry.py) │
        └───────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Site Analysis│   │Industry      │   │ Decision     │
│    Chain     │   │Strategy Chain│   │    Chain     │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│    Qwen      │   │   DeepSeek   │   │   Qdrant     │
│  (Local GPU) │   │   (API)      │   │  (Vectors)   │
└──────────────┘   └──────────────┘   └──────────────┘
```

### Flux Site Analysis Chain

```
┌─────────────┐
│   Input     │  Conținut site
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Qwen      │  Sumarizare conținut
│  (Step 1)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Qwen      │  Clasificare tipuri pagini
│  (Step 2)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  DeepSeek   │  Sinteză strategică
│  (Step 3)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Output    │  JSON cu analiză completă
└─────────────┘
```

### Flux Industry Strategy Chain

```
┌─────────────┐     ┌─────────────┐
│  Servicii   │     │ Competitori  │
│   List      │     │    Data      │
└──────┬──────┘     └──────┬───────┘
       │                   │
       └─────────┬─────────┘
                 │
                 ▼
         ┌─────────────┐
         │   Qwen      │  Normalizare servicii
         │  (Step 1)   │  Extragere keywords
         └──────┬──────┘
                │
                ▼
         ┌─────────────┐
         │  DeepSeek   │  Generare strategie
         │  (Step 2)   │  competitivă
         └──────┬──────┘
                │
                ▼
         ┌─────────────┐
         │   Qwen      │  Extragere acțiuni
         │  (Step 3)   │  concrete (JSON)
         └──────┬──────┘
                │
                ▼
         ┌─────────────┐
         │   Output    │  Strategie + Plan
         └─────────────┘
```

### Flux Decision Chain

```
┌─────────────┐
│  Strategie  │  Strategie competitivă
│  Competitivă│  (din Industry Strategy)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Qwen      │  Transformare în acțiuni
│             │  concrete executabile
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Output    │  Plan acțiuni JSON:
│             │  - immediate_actions
│             │  - short_term_actions
│             │  - medium_term_actions
│             │  - long_term_actions
└─────────────┘
```

---

## 🖥️ Testare Manuală în UI

### Pasul 1: Accesează Interfața

```
http://localhost:8083/
```

### Pasul 2: Selectează un Agent

1. În panoul din stânga, selectează un agent din dropdown
2. Agentul selectat devine "Agent Master"
3. Informațiile agentului apar în panoul din dreapta

### Pasul 3: Rulează Lanțuri LangChain

În panoul "Agent Master", secțiunea "🔗 Lanțuri LangChain":

#### A. Analiză Site (`site_analysis`)

1. Click pe butonul **"📊 Analiză Site (Qwen + DeepSeek)"**
2. Confirmă dacă apare dialogul
3. Așteaptă execuția (poate dura 1-3 minute)
4. Rezultatul apare în secțiunea "Rezultat Lanț"

**Ce să verifici:**
- ✅ Butonul se dezactivează în timpul execuției
- ✅ Apare mesajul "Lanțul LangChain rulează... ⏳"
- ✅ Rezultatul conține: `summary`, `page_types`, `strengths`, `weaknesses`, `opportunities`
- ✅ Rezultatul este formatat JSON

#### B. Strategie Industrie (`industry_strategy`)

1. Click pe butonul **"💼 Strategie Industrie (DeepSeek)"**
2. Confirmă dacă apare dialogul
3. Așteaptă execuția (poate dura 2-5 minute)
4. Rezultatul apare în secțiunea "Rezultat Lanț"

**Ce să verifici:**
- ✅ Rezultatul conține: `strategy_summary`, `industry_opportunities`, `action_plan`
- ✅ Strategia este detaliată și relevantă pentru industrie
- ✅ Planul de acțiuni este structurat

#### C. Plan Acțiuni (`decision_chain`)

1. Click pe butonul **"🎯 Plan Acțiuni (Qwen)"**
2. Așteaptă execuția (poate dura 30 secunde - 1 minut)
3. Rezultatul apare în secțiunea "Rezultat Lanț"

**Ce să verifici:**
- ✅ Rezultatul conține: `immediate_actions`, `short_term_actions`, `medium_term_actions`, `long_term_actions`
- ✅ Fiecare acțiune are: `action`, `priority`, `resources_needed`, `expected_impact`
- ✅ Acțiunile sunt concrete și executabile

### Pasul 4: Verifică Rezultatele

Rezultatele sunt afișate în secțiunea "Rezultat Lanț" sub butoanele LangChain.

**Format așteptat:**
```json
{
  "summary": "...",
  "page_types": [...],
  "strengths": [...],
  "weaknesses": [...],
  "opportunities": [...]
}
```

---

## 🤖 Testare Automată

### Rulare Script Complet

```bash
cd /srv/hf/ai_agents
python3 test_langchain_integration.py
```

**Output așteptat:**
```
✅ Serverul răspunde (Status: healthy)
✅ Găsite 3 lanțuri
✅ Preview pentru 'site_analysis' obținut
✅ Preview pentru 'industry_strategy' obținut
✅ Găsiți X agenți
✅ Lanțul 'decision_chain' executat cu succes
✅ Toate componentele LangChain sunt disponibile
✅ Module actions importate cu succes

🎉 Toate testele au trecut cu succes!
```

### Teste Individuale

#### Test 1: Server Health
```bash
curl http://localhost:8083/health | python3 -m json.tool
```

#### Test 2: Listare Lanțuri
```bash
curl http://localhost:8083/chains/list | python3 -m json.tool
```

#### Test 3: Preview Lanț
```bash
curl http://localhost:8083/chains/site_analysis/preview | python3 -m json.tool
```

#### Test 4: Rulare Lanț
```bash
AGENT_ID="690a19bda55790fced125e48"  # Înlocuiește cu ID-ul unui agent real

curl -X POST http://localhost:8083/agents/$AGENT_ID/run_chain/decision_chain \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "strategy": {
        "summary": "Strategie de test",
        "opportunities": ["SEO", "Social Media"]
      }
    }
  }' | python3 -m json.tool
```

---

## 🔌 Testare API Directă

### Endpointuri Disponibile

#### 1. Listare Lanțuri
```http
GET /chains/list
```

**Răspuns:**
```json
{
  "ok": true,
  "chains": [
    {
      "name": "site_analysis",
      "available": true,
      "description": "Analiză completă a unui site web..."
    }
  ],
  "total": 3
}
```

#### 2. Preview Lanț
```http
GET /chains/{chain_name}/preview
```

**Exemplu:**
```http
GET /chains/decision_chain/preview
```

**Răspuns:**
```json
{
  "ok": true,
  "chain_name": "decision_chain",
  "available": true,
  "description": "Plan de acțiune concret...",
  "inputs": ["strategy"],
  "outputs": ["immediate_actions", "short_term_actions", ...]
}
```

#### 3. Rulare Lanț
```http
POST /agents/{agent_id}/run_chain/{chain_name}
Content-Type: application/json

{
  "params": {
    "strategy": {...}
  },
  "task_id": "optional_task_id"
}
```

**Exemplu Site Analysis:**
```bash
curl -X POST http://localhost:8083/agents/AGENT_ID/run_chain/site_analysis \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "content": "Conținut site de test..."
    }
  }'
```

**Exemplu Industry Strategy:**
```bash
curl -X POST http://localhost:8083/agents/AGENT_ID/run_chain/industry_strategy \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "services_list": ["Serviciu 1", "Serviciu 2"],
      "competitor_data": {}
    }
  }'
```

**Exemplu Decision Chain:**
```bash
curl -X POST http://localhost:8083/agents/AGENT_ID/run_chain/decision_chain \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "strategy": {
        "summary": "Strategie competitivă...",
        "opportunities": ["SEO", "Social Media"]
      }
    }
  }'
```

---

## 📊 Scenarii de Testare

### Scenariu 1: Flux Complet End-to-End

**Obiectiv:** Testează întregul flux de la analiză site până la plan acțiuni

**Pași:**

1. **Creează/Selectează Agent**
   ```bash
   # Folosește UI sau API
   ```

2. **Rulează Site Analysis**
   - Buton: "📊 Analiză Site"
   - Verifică rezultatul conține analiză completă

3. **Rulează Industry Strategy**
   - Buton: "💼 Strategie Industrie"
   - Folosește rezultatele de la Site Analysis
   - Verifică strategia competitivă

4. **Rulează Decision Chain**
   - Buton: "🎯 Plan Acțiuni"
   - Folosește strategia de la Industry Strategy
   - Verifică planul de acțiuni concrete

**Rezultat așteptat:**
- ✅ Toate cele 3 lanțuri rulează cu succes
- ✅ Rezultatele sunt coerente între ele
- ✅ Planul de acțiuni este executabil

### Scenariu 2: Testare Erori

**Obiectiv:** Verifică gestionarea erorilor

**Pași:**

1. **Agent Invalid**
   ```bash
   curl -X POST http://localhost:8083/agents/INVALID_ID/run_chain/decision_chain \
     -H "Content-Type: application/json" \
     -d '{"params": {"strategy": {}}}'
   ```
   **Rezultat așteptat:** `404 Not Found` sau `{"ok": false, "error": "Agent not found"}`

2. **Lanț Invalid**
   ```bash
   curl -X POST http://localhost:8083/agents/AGENT_ID/run_chain/invalid_chain \
     -H "Content-Type: application/json" \
     -d '{"params": {}}'
   ```
   **Rezultat așteptat:** `{"ok": false, "error": "Chain not found"}`

3. **Parametri Invalizi**
   ```bash
   curl -X POST http://localhost:8083/agents/AGENT_ID/run_chain/decision_chain \
     -H "Content-Type: application/json" \
     -d '{"params": {}}'
   ```
   **Rezultat așteptat:** Eroare descriptivă despre parametri lipsă

### Scenariu 3: Testare Performanță

**Obiectiv:** Verifică timpii de răspuns

**Pași:**

1. **Măsoară timpul pentru fiecare lanț**
   ```bash
   time curl -X POST http://localhost:8083/agents/AGENT_ID/run_chain/decision_chain \
     -H "Content-Type: application/json" \
     -d '{"params": {"strategy": {...}}}'
   ```

**Rezultate așteptate:**
- `decision_chain`: < 60 secunde
- `site_analysis`: < 180 secunde
- `industry_strategy`: < 300 secunde

### Scenariu 4: Testare Concurrență

**Obiectiv:** Verifică comportamentul cu multiple request-uri simultane

**Pași:**

1. **Rulează multiple lanțuri simultan**
   ```bash
   # Rulează 3 request-uri în paralel
   for i in {1..3}; do
     curl -X POST http://localhost:8083/agents/AGENT_ID/run_chain/decision_chain \
       -H "Content-Type: application/json" \
       -d '{"params": {"strategy": {...}}}' &
   done
   wait
   ```

**Rezultat așteptat:**
- ✅ Toate request-urile se procesează corect
- ✅ Nu apar erori de concurență
- ✅ Serverul rămâne stabil

---

## 🔧 Troubleshooting

### Problema 1: "LangChain integration not available"

**Cauză:** Modulele LangChain nu sunt instalate sau nu sunt în path

**Soluție:**
```bash
cd /srv/hf/ai_agents
pip install langchain langchain-core langchain-community langchain-openai
```

### Problema 2: "DeepSeek LLM not available"

**Cauză:** `DEEPSEEK_API_KEY` nu este setat sau este invalid

**Soluție:**
```bash
# Verifică .env
cat .env | grep DEEPSEEK

# Setează cheia
export DEEPSEEK_API_KEY="sk-..."
```

### Problema 3: "Qwen LLM not available"

**Cauză:** Serverul Qwen local nu rulează

**Soluție:**
```bash
# Verifică dacă Qwen rulează
curl http://localhost:9304/v1/models

# Pornește Qwen dacă nu rulează
# (depinde de configurația ta)
```

### Problema 4: "Chain not found"

**Cauză:** Lanțul nu este înregistrat în Chain Registry

**Soluție:**
```bash
# Verifică logurile serverului
tail -f server_8083.log | grep chain_registry

# Restartează serverul
./restart_8083.sh
```

### Problema 5: Timeout la rularea lanțurilor

**Cauză:** Lanțurile durează prea mult

**Soluție:**
- Verifică conectivitatea la DeepSeek API
- Verifică dacă Qwen local răspunde rapid
- Reduce complexitatea input-urilor
- Verifică logurile pentru erori

### Problema 6: Rezultate incomplete sau eronate

**Cauză:** LLM-urile nu generează output corect

**Soluție:**
- Verifică prompt-urile în fișierele chain
- Testează LLM-urile individual
- Verifică logurile pentru erori de parsing

---

## 📝 Checklist Testare

### Pre-Testare
- [ ] Serverul rulează (`http://localhost:8083/health`)
- [ ] MongoDB este accesibil
- [ ] Qdrant este accesibil
- [ ] Qwen local rulează
- [ ] DeepSeek API key este setat
- [ ] Există cel puțin un agent în baza de date

### Testare UI
- [ ] Butoanele LangChain apar în interfață
- [ ] Butoanele se dezactivează în timpul execuției
- [ ] Mesajele de loading apar corect
- [ ] Rezultatele sunt afișate corect
- [ ] Erorile sunt afișate corect

### Testare API
- [ ] `GET /chains/list` returnează lista corectă
- [ ] `GET /chains/{name}/preview` funcționează
- [ ] `POST /agents/{id}/run_chain/{name}` rulează lanțurile
- [ ] Răspunsurile sunt în format JSON corect
- [ ] Erorile sunt gestionate corect

### Testare Funcționalitate
- [ ] Site Analysis Chain generează analiză completă
- [ ] Industry Strategy Chain generează strategie
- [ ] Decision Chain generează plan acțiuni
- [ ] Rezultatele sunt coerente între lanțuri
- [ ] Memoria este salvată corect în MongoDB

### Post-Testare
- [ ] Logurile nu conțin erori critice
- [ ] Serverul rămâne stabil după testare
- [ ] Performanța este acceptabilă
- [ ] Toate resursele sunt eliberate corect

---

## 📚 Resurse Suplimentare

- **Documentație LangChain:** https://python.langchain.com/
- **DeepSeek API:** https://platform.deepseek.com/
- **Qwen Local:** Configurarea ta locală
- **Qdrant:** https://qdrant.tech/documentation/

---

## ✅ Concluzie

Acest manual oferă un ghid complet pentru testarea integrării LangChain în platforma AI Agents. Urmează scenariile de testare și verifică checklist-ul pentru a asigura funcționalitatea corectă a tuturor componentelor.

Pentru întrebări sau probleme, consultă secțiunea Troubleshooting sau verifică logurile serverului.

