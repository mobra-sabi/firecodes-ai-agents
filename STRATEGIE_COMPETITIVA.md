# Strategie Competitivă cu DeepSeek

## ✅ Implementat

### Funcționalitate
După crearea unui agent, poți selecta agentul și folosi DeepSeek pentru:
1. **Evaluare completă** a tuturor datelor agentului
2. **Identificare servicii** - DeepSeek analizează site-ul și identifică toate tipurile de servicii/produse
3. **Strategie competitivă** - Pentru fiecare tip de serviciu, DeepSeek generează:
   - Termeni de căutare pentru identificarea competitorilor
   - Strategii de cercetare a concurenței (unde să cauți, ce să cauți)
   - Întrebări-cheie pentru a înțelege concurența
4. **Plan general** - Abordare generală de analiză competitivă

### Componente

#### 1. `competitive_strategy.py`
**Clasa `CompetitiveStrategyGenerator`:**
- `analyze_agent_and_generate_strategy()` - Analizează agentul și generează strategie
- `_get_site_content_from_qdrant()` - Obține conținutul site-ului din Qdrant
- `_build_analysis_prompt()` - Construiește prompt detaliat pentru DeepSeek
- `_parse_deepseek_response()` - Parsează răspunsul DeepSeek și construiește strategia
- `get_strategy_for_agent()` - Obține strategia existentă pentru un agent

**Flow:**
1. Obține datele agentului din MongoDB
2. Obține conținutul site-ului din Qdrant (toate chunks)
3. Construiește prompt detaliat pentru DeepSeek cu:
   - Informații despre site
   - Conținut site (primele chunks)
   - Instrucțiuni clare pentru analiză
4. Trimite la DeepSeek Reasoner pentru analiză
5. Parsează răspunsul JSON din DeepSeek
6. Salvează strategia în MongoDB

#### 2. Endpoints în `agent_api.py`

**`POST /api/analyze-agent`:**
- Primește `agent_id`
- Generează strategie competitivă cu DeepSeek
- Returnează strategia generată

**`GET /api/strategy/{agent_id}`:**
- Obține strategia existentă pentru un agent
- Returnează strategia sau 404 dacă nu există

#### 3. Interfață HTML (`main_interface.html`)

**Secțiune "Strategie Competitivă":**
- Buton: "🤖 Analizează Agent cu DeepSeek"
- Loading indicator când DeepSeek analizează
- Afișare strategie:
  - **Servicii Identificate:** Listă cu fiecare serviciu și strategia sa
  - **Strategie Generală:** Abordare generală și priorități

**Funcții JavaScript:**
- `analyzeAgentWithDeepSeek()` - Trimite cererea de analiză
- `loadCompetitiveStrategy()` - Încarcă strategia existentă la selectarea agentului
- `displayStrategy()` - Afișează strategia în interfață

### Format Strategie

```json
{
  "services": [
    {
      "service_name": "Nume serviciu/produs",
      "description": "Descriere detaliată",
      "search_keywords": ["cuvinte", "cheie", "căutare"],
      "competitive_research_strategy": {
        "where_to_search": ["liste", "de", "surse"],
        "what_to_look_for": ["caracteristici", "să", "caută"],
        "key_questions": ["întrebări", "cheie"]
      },
      "priority": "high/medium/low"
    }
  ],
  "overall_strategy": {
    "competitive_analysis_approach": "Descrierea abordării generale",
    "research_priorities": ["priorități", "de", "cercetare"],
    "expected_outcomes": "Ce ar trebui să descoperim"
  },
  "metadata": {
    "agent_id": "...",
    "domain": "...",
    "analysis_date": "...",
    "total_services": N
  }
}
```

### Flow Complet

1. **Utilizator selectează agent** în panoul din stânga
   - Agentul devine master
   - Sistemul verifică dacă există strategie și o încarcă automat

2. **Utilizator apasă "Analizează Agent cu DeepSeek"**
   - Sistemul trimite cererea la `/api/analyze-agent`
   - DeepSeek Reasoner analizează:
     - Datele agentului din MongoDB
     - Conținutul site-ului din Qdrant
   - DeepSeek generează strategie competitivă
   - Strategia este salvată în MongoDB

3. **Strategia este afișată în interfață**
   - Servicii identificate cu strategiile lor
   - Strategie generală de analiză competitivă

### Prompt DeepSeek

DeepSeek primește:
- Informații despre site (domeniu, nume, URL, tip business)
- Conținut site (primele chunks din Qdrant)
- Instrucțiuni clare pentru:
  1. Identificarea tuturor serviciilor/produselor
  2. Generarea strategiilor de cercetare pentru fiecare serviciu
  3. Crearea unui plan general de analiză competitivă

**Format răspuns:** JSON structurat cu servicii și strategie generală

### Beneficii

✅ **Analiză automată** - DeepSeek analizează automat toate datele agentului  
✅ **Identificare servicii** - Identifică toate tipurile de servicii/produse  
✅ **Strategie detaliată** - Pentru fiecare serviciu, generează strategie completă  
✅ **Plan acțiune** - Strategie generală și priorități pentru cercetarea concurenței  
✅ **Persistență** - Strategia este salvată în MongoDB pentru reutilizare  

---

**Status:** ✅ **IMPLEMENTAT - READY FOR TESTING**

**Link interfață:** `http://100.66.157.27:8083/`

**Utilizare:**
1. Selectează un agent în panoul din stânga
2. Apasă butonul "🤖 Analizează Agent cu DeepSeek" în panoul din dreapta
3. Așteaptă analiza DeepSeek (poate dura 30-60 secunde)
4. Strategia va fi afișată automat în interfață


