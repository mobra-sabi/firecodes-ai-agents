# 🎯 DeepSeek Competitive Analysis - Arhitectură

## 📋 OVERVIEW

Sistemul primește **TOT contextul** despre un agent (MongoDB + Qdrant) și folosește **DeepSeek** pentru analize competitive avansate.

---

## 🏗️ ARHITECTURĂ

### **1. Colectare Date (Full Context)**

```
┌─────────────────────────────────────────────────────┐
│  DeepSeekCompetitiveAnalyzer.get_full_agent_context │
└─────────────────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
   ┌─────────┐               ┌──────────┐
   │ MongoDB │               │  Qdrant  │
   └─────────┘               └──────────┘
        │                           │
        ├─ Agent info               ├─ Vector search
        ├─ Content chunks           │  per topics:
        ├─ Services                 │  • Servicii
        └─ Contact info             │  • Avantaje
                                    │  • Expertiză
                                    └─ etc.
```

**Output:** Dict complet cu TOATE datele agentului

---

### **2. Construire Prompt Structurat**

```python
prompt = {
    "Agent Info": {...},
    "Servicii": [...],
    "Context Semantic (Qdrant)": {...},
    "Conținut Complet": "..."
}
```

**Total:** ~30,000-50,000 caractere de context

---

### **3. Trimitere către DeepSeek**

```
Request → DeepSeek API
          │
          ├─ Model: deepseek-chat
          ├─ Max tokens: 4000
          ├─ Temperature: 0.7
          └─ Timeout: 180s
```

---

### **4. Parsare Răspuns JSON**

DeepSeek returnează:

```json
{
  "industry": "...",
  "target_market": "...",
  "subdomains": [
    {
      "name": "...",
      "description": "...",
      "main_services": [...],
      "keywords": [...]
    }
  ],
  "overall_keywords": [...],
  "competitive_positioning": "..."
}
```

---

### **5. Salvare în MongoDB**

```
Collection: competitive_analysis
Document: {
  "agent_id": ObjectId(...),
  "analysis_type": "competition_discovery",
  "analysis_data": {...},
  "created_at": datetime,
  "status": "completed"
}
```

---

## 🔌 API ENDPOINTS

### **1. POST `/agents/{id}/analyze-competition`**

**Descriere:** Rulează analiza competitivă completă

**Request:**
```bash
POST /agents/6910d564c5a351f416f077ed/analyze-competition
```

**Response:**
```json
{
  "ok": true,
  "agent_id": "...",
  "domain": "coneco.ro",
  "analysis": {
    "industry": "protecție la foc",
    "subdomains": [...],
    "overall_keywords": [...]
  }
}
```

---

### **2. GET `/agents/{id}/competition-analysis`**

**Descriere:** Obține analiza existentă

**Response:**
```json
{
  "ok": true,
  "analysis": {
    "agent_id": "...",
    "analysis_data": {...},
    "created_at": "2025-11-09T18:00:00Z"
  }
}
```

---

### **3. GET `/agents/{id}/full-context`**

**Descriere:** 🔍 DEBUG - Vezi tot contextul trimis către DeepSeek

**Response:**
```json
{
  "ok": true,
  "context": {
    "agent_info": {...},
    "stats": {...},
    "vector_context": {...},
    "content_preview": "..."
  }
}
```

---

## 🎯 TASK 1: Descompunere în Subdomenii

### **Input către DeepSeek:**
- Toate datele agentului
- Context semantic din Qdrant
- Servicii identificate

### **Output de la DeepSeek:**

**Pentru fiecare subdomeniu:**
1. **Nume** - ex: "Protecție pasivă la foc"
2. **Descriere frumoasă** - 2-3 propoziții despre ce face, pentru cine, ce probleme rezolvă
3. **Servicii principale** - listă
4. **Cuvinte cheie** - 5-10 keywords pentru Google search

**Plus:**
- Cuvinte cheie generale (10-15)
- Industrie identificată
- Piață țintă
- Poziționare competitivă

---

## 🔍 CUVINTE CHEIE GENERATE

### **Caracteristici:**
- Specifice (nu generice)
- Combină: serviciu + industrie + locație
- În română
- Variații: singular/plural, sinonime

### **Exemple bune:**
```
"protecție la foc structuri metalice București"
"termoprotecție vopsea intumescentă"
"ignifugare lemn certificată"
"sisteme antiincendiu pasive"
```

---

## 🚀 UTILIZARE

### **1. Test rapid:**
```bash
python3 test_competitive_analysis.py [agent_id]
```

### **2. Via API:**
```bash
curl -X POST http://localhost:5000/agents/{agent_id}/analyze-competition
```

### **3. Via interfață web:**
- Click pe agent
- Buton "🎯 Analizează pentru Competiție"
- Așteaptă 1-2 minute
- Vezi rezultatele

---

## 📊 NEXT STEPS

După TASK 1, pot urma:

**TASK 2:** Căutare Google cu cuvintele cheie → identificare competitori

**TASK 3:** Scraping competitori identificați

**TASK 4:** Analiză comparativă (tu vs competitori)

**TASK 5:** Strategii de diferențiere

---

## ✅ AVANTAJE

1. **Context complet** - DeepSeek vede TOATE datele
2. **Semantic search** - folosește Qdrant pentru înțelegere profundă
3. **Scalabil** - funcționează pentru orice industrie
4. **Persistență** - salvează rezultatele în MongoDB
5. **API-first** - ușor de integrat în orice workflow

---

*Creat: 2025-11-09*
