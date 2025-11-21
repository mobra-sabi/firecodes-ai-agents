# Ghid Chat cu Agenți

**Data:** 2025-01-30  
**Scop:** Ghid pentru utilizarea interfeței de chat cu agenții

## 🎯 INTERFAȚĂ CHAT DISPONIBILĂ

### URL-ul interfeței:
```
http://localhost:8083/chat
```
sau
```
http://127.0.0.1:8083/chat
```

## 📋 FUNCȚIONALITĂȚI CHAT

### 1. **Selectare Agent**
- Dropdown pentru selectarea agentului
- Informații despre agent (domain, business_type)
- Mesaj de bun venit din partea agentului

### 2. **Conversație**
- Trimite întrebări în text
- Primește răspunsuri contextuale
- **Menținere context:** Conversația este menținută între mesaje
- **History:** Sistemul ține minte întreaga conversație

### 3. **Caracteristici Avansate**
- ✅ **Web Search Integration:** Agentul poate căuta informații pe internet
- ✅ **Surse:** Afișare surse pentru răspunsuri
- ✅ **Confidence Score:** Indică nivelul de încredere al răspunsului
- ✅ **Contextual Questions:** Sugestii de întrebări de următor
- ✅ **Site Context:** Informații despre business type, target audience

## 🔧 ENDPOINT-URI DISPONIBILE

### 1. GET `/chat`
**Descriere:** Returnează interfața de chat HTML
```bash
curl http://localhost:8083/chat
```

### 2. POST `/ask`
**Descriere:** Trimite o întrebare agentului
**Body:**
```json
{
  "question": "Ce produse oferiți?",
  "agent_id": "68e629bb5a7057c4b1b2f4da",
  "conversation_history": [
    {"role": "user", "content": "Salut"},
    {"role": "assistant", "content": "Salut! Cu ce te pot ajuta?"}
  ]
}
```

**Răspuns:**
```json
{
  "ok": true,
  "response": "Oferim matări antifoc, vopsea termospumantă...",
  "confidence": 0.98,
  "reasoning": "Site-specific intelligence pentru domain.ro",
  "sources": [{"url": "https://domain.ro", "score": 0.95}],
  "web_search_used": false,
  "web_sources": [],
  "agent_id": "68e629bb5a7057c4b1b2f4da",
  "llm_used": "deepseek-chat",
  "timestamp": "2025-01-30T12:00:00Z",
  "guardrails": {
    "passed": true,
    "message": "All security checks passed",
    "confidence_check": true
  },
  "contextual_questions": ["Care sunt prețurile?", "Cum pot plasa o comandă?"],
  "competitive_advantage": "...",
  "site_context": {
    "business_type": "fire-protection",
    "target_audience": "construction-companies",
    "unique_selling_points": ["..."]
  }
}
```

## 💬 EXEMPLU UTILIZARE

### Via Browser:
1. Deschide browser la `http://localhost:8083/chat`
2. Selectează un agent din dropdown
3. Trimite întrebări în câmpul de text
4. Primește răspunsuri contextuale

### Via cURL:
```bash
curl -X POST http://localhost:8083/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Ce produse oferiți?",
    "agent_id": "68e629bb5a7057c4b1b2f4da"
  }'
```

### Via Python:
```python
import requests

response = requests.post(
    "http://localhost:8083/ask",
    json={
        "question": "Ce produse oferiți?",
        "agent_id": "68e629bb5a7057c4b1b2f4da",
        "conversation_history": []
    }
)

data = response.json()
if data["ok"]:
    print(f"Răspuns: {data['response']}")
    print(f"Confidence: {data['confidence']}")
else:
    print(f"Eroare: {data['error']}")
```

## 🎨 INTERFAȚA UI

Interfața de chat include:
- **Design modern:** Gradient background, glassmorphism
- **Mesaje:** Diferențiere vizuală între user și assistant
- **Avatare:** Colorate diferit pentru user vs assistant
- **Loading indicator:** Afișează când agentul procesează
- **Surse:** Afișare link-uri către surse
- **Web search:** Indicator când se folosește web search

## 📊 FUNCȚIONALITĂȚI AVANSATE

### 1. **Conversation History**
Interfața menține automat istoricul conversației și îl trimite la fiecare request pentru context complet.

### 2. **Site-Specific Intelligence**
Fiecare agent are acces la:
- Conținutul site-ului (via embeddings în Qdrant)
- Informații despre business type
- Target audience
- Unique selling points

### 3. **Web Search Integration**
Agentul poate căuta informații pe internet când:
- Informația nu este disponibilă în conținutul site-ului
- Este necesară informație actualizată
- Întrebarea necesită informații generale

### 4. **Guardrails & Security**
Fiecare răspuns este verificat:
- ✅ Security checks
- ✅ Confidence threshold
- ✅ Content filtering

## 🚀 ACCESARE RAPIDĂ

### Pentru testare:
```bash
# Verifică dacă serverul rulează
curl http://localhost:8083/health

# Accesează interfața de chat
# Deschide în browser: http://localhost:8083/chat
```

### Pentru dezvoltare:
Interfața se află în:
- **Frontend:** `/srv/hf/ai_agents/static/chat.html`
- **Backend:** `/srv/hf/ai_agents/agent_api.py` (endpoints `/chat` și `/ask`)

---

**Status:** ✅ **INTERFAȚĂ CHAT FUNCȚIONALĂ ȘI DISPONIBILĂ**


