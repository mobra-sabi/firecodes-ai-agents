# 💬 API CHAT DEEPSEEK - Integrare în Site

## 🎯 Obiectiv
Chat DeepSeek conectat la toate informațiile agentului (Qdrant, MongoDB, LangChain) care poate fi integrat în site-ul original.

## ✅ Funcționalități

### 1. Chat Intern (Frontend)
- **Endpoint**: `POST /api/agents/{agent_id}/chat`
- **Folosit de**: Frontend-ul aplicației
- **Caracteristici**:
  - DeepSeek ca orchestrator
  - Context din Qdrant (chunks relevante)
  - Identitate agent (se identifică cu compania)
  - Cunoștințe complete (keywords, SERP, competitors)

### 2. API Public (Integrare Externă)
- **Endpoint**: `POST /api/public/chat/{domain}`
- **Folosit de**: Site-ul original (via JavaScript/iframe)
- **Caracteristici**:
  - Acces public (fără autentificare obligatorie)
  - Folosește domain-ul pentru a găsi agentul
  - Același chat DeepSeek cu context complet

### 3. Info Chat
- **Endpoint**: `GET /api/public/chat/{domain}/info`
- **Returnează**: Informații despre disponibilitatea chat-ului

## 📝 Exemple de Utilizare

### Frontend (React)
```javascript
const response = await api.post(`/agents/${agentId}/chat`, {
  message: "Ce servicii oferiți?",
  session_id: sessionId // opțional
})
```

### Site Original (JavaScript)
```javascript
// Chat pentru bioclinica.ro
fetch('https://your-api-domain.com/api/public/chat/bioclinica.ro', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Ce analize medicale oferiți?',
    session_id: 'user_session_123' // opțional
  })
})
.then(res => res.json())
.then(data => {
  console.log(data.response) // Răspuns DeepSeek
})
```

### Widget Chat pentru Site
```html
<!-- Widget chat pentru integrare în site -->
<div id="ai-chat-widget"></div>
<script>
  const domain = window.location.hostname.replace('www.', '');
  const chatApi = 'https://your-api-domain.com/api/public/chat/' + domain;
  
  // Implementare widget chat...
</script>
```

## 🔗 Integrare Completă

### Status Agent
- **Endpoint**: `GET /api/agents/{agent_id}/status/complete`
- **Verifică**: MongoDB ✅ | Qdrant ✅ | LangChain ✅
- **Folosit de**: Indicator în listă ("AI Ready")

### Indicator în Listă
- **Badge**: "AI Ready" (purple) când agentul este procesat complet
- **Condiții**: 
  - `chunks_indexed > 0` (MongoDB)
  - Există colecții în Qdrant
  - LangChain activ

## 🎨 Identitate Agent

Chat-ul se identifică cu agentul:
- **Nume**: Numele companiei
- **Site**: URL-ul site-ului
- **Industrie**: Industria companiei
- **Servicii**: Serviciile oferite
- **Keywords**: Cuvintele cheie relevante
- **Competitori**: Competitorii principali

## 📊 Context Utilizat

Chat-ul folosește:
1. **Qdrant**: Chunks relevante pentru query (search semantic)
2. **MongoDB**: Keywords, SERP results, competitors
3. **DeepSeek Identity**: Identitatea generată de DeepSeek
4. **Competitive Analysis**: Analiza competitivă

## 🔐 Securitate

- **API Public**: Poate fi protejat cu API Key (opțional)
- **Rate Limiting**: Recomandat pentru API public
- **CORS**: Configurat pentru site-ul original

---

**Status**: ✅ Implementat
**Endpoint-uri**: `/api/agents/{id}/chat`, `/api/public/chat/{domain}`

