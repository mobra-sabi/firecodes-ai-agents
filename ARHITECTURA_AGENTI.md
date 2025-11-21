# 🏗️ ARHITECTURA COMPLETĂ AI AGENTS PLATFORM

## 📋 PLAN DE IMPLEMENTARE

### 1. FLUXUL PRINCIPAL DE CONVERSATIE

```
USER → GPT (Orchestrator) → Agent Selectat → Qwen (Learning) → Răspuns
```

### 2. COMPONENTELE CHEIE

#### A. **GPT - Orchestrator Principal**
- **Rol**: Planifică, orchestrează, gestionează conversația
- **Responsabilități**:
  - Analizează întrebarea utilizatorului
  - Decide ce informații sunt necesare
  - Coordonează cu agentul selectat
  - Generează răspunsul final
  - Gestionează contextul conversației

#### B. **Agent Selectat (MongoDB)**
- **Rol**: Depozitul de cunoștințe pentru site-ul specific
- **Conține**:
  - Conținutul complet al site-ului (ingestat)
  - Embeddings pentru căutare semantică
  - Istoricul conversațiilor
  - Metadatele site-ului
  - Configurațiile specifice

#### C. **Qwen - Learning Engine**
- **Rol**: Învață și procesează datele site-ului
- **Responsabilități**:
  - Procesează conținutul site-ului
  - Generează embeddings
  - Caută informații relevante
  - Învață din conversații noi

### 3. FLUXUL DETALIAT

#### Pasul 1: User Input
```
User: "Ce servicii oferiți pentru protecția la foc?"
```

#### Pasul 2: GPT Orchestrator
```
GPT analizează:
- Ce agent este selectat? (tehnica-antifoc.ro)
- Ce informații sunt necesare?
- Cum să formulez query-ul pentru Qwen?
```

#### Pasul 3: Agent Selection & Data Retrieval
```
GPT → MongoDB Agent:
- Agent ID: 68f732b6f86c99d4d127ea88
- Domain: tehnica-antifoc.ro
- Conținut: [toate paginile site-ului]
- Embeddings: [vectori pentru căutare]
```

#### Pasul 4: Qwen Learning & Search
```
Qwen primește:
- Query: "servicii protecție la foc"
- Conținutul site-ului
- Embeddings pentru căutare semantică

Qwen returnează:
- Informații relevante din site
- Sursele (URL-uri)
- Nivelul de încredere
```

#### Pasul 5: GPT Final Response
```
GPT primește de la Qwen:
- Informațiile găsite
- Sursele
- Contextul

GPT generează:
- Răspunsul final pentru user
- Citează sursele
- Menține contextul conversației
```

### 4. STRUCTURA DATELOR AGENT

```json
{
  "agent_id": "68f732b6f86c99d4d127ea88",
  "name": "Agent pentru tehnica-antifoc.ro",
  "domain": "tehnica-antifoc.ro",
  "site_url": "https://www.tehnica-antifoc.ro",
  
  "content": {
    "pages": [
      {
        "url": "https://www.tehnica-antifoc.ro/servicii",
        "title": "Servicii",
        "content": "Conținutul complet al paginii...",
        "embeddings": [0.1, 0.2, ...]
      }
    ],
    "total_pages": 25,
    "last_updated": "2025-10-21T12:00:00Z"
  },
  
  "conversations": [
    {
      "user_message": "Ce servicii oferiți?",
      "assistant_response": "Oferim servicii de...",
      "sources": ["https://www.tehnica-antifoc.ro/servicii"],
      "timestamp": "2025-10-21T12:00:00Z"
    }
  ],
  
  "learning_data": {
    "keywords": ["protecție la foc", "servicii", "instalații"],
    "faq": ["Întrebări frecvente..."],
    "insights": ["Analize și observații..."]
  }
}
```

### 5. API ENDPOINTS

#### A. Chat cu Agent
```
POST /api/chat/{agent_id}
{
  "message": "Ce servicii oferiți?",
  "user_id": "user123",
  "session_id": "session456"
}
```

#### B. Răspunsul
```json
{
  "response": "Oferim servicii complete de protecție la foc...",
  "sources": [
    "https://www.tehnica-antifoc.ro/servicii",
    "https://www.tehnica-antifoc.ro/despre-noi"
  ],
  "confidence": 0.95,
  "agent_id": "68f732b6f86c99d4d127ea88",
  "timestamp": "2025-10-21T12:00:00Z"
}
```

### 6. CONFIGURAȚIA SISTEMULUI

#### A. GPT Configuration
```env
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2000
```

#### B. Qwen Configuration
```env
QWEN_API_KEY=local
QWEN_BASE_URL=http://localhost:11434/v1
QWEN_MODEL=qwen:latest
QWEN_TEMPERATURE=0.3
```

#### C. MongoDB Configuration
```env
MONGODB_URI=mongodb://localhost:9308/
MONGODB_DATABASE=ai_agents_db
MONGODB_COLLECTION=agents
```

### 7. FLUXUL DE IMPLEMENTARE

#### Faza 1: Configurare GPT ca Orchestrator
- [ ] Actualizează endpoint-ul `/ask` să folosească GPT
- [ ] Configurează GPT să primească datele de la agent
- [ ] Implementează logica de orchestare

#### Faza 2: Integrare Qwen ca Learning Engine
- [ ] Configurează Qwen să proceseze conținutul site-ului
- [ ] Implementează căutarea semantică cu Qwen
- [ ] Conectează Qwen la MongoDB pentru date

#### Faza 3: Conectare Agent Selectat
- [ ] Implementează selecția agentului din UI
- [ ] Conectează agentul la GPT și Qwen
- [ ] Testează fluxul complet

#### Faza 4: Optimizare și Testare
- [ ] Optimizează performanța
- [ ] Implementează cache-ul
- [ ] Testează cu multiple agenți

### 8. EXEMPLE DE CONVERSATIE

#### Exemplu 1: Întrebare simplă
```
User: "Ce servicii oferiți?"
GPT: "Să verific în baza de cunoștințe a site-ului..."
GPT → Qwen: "Caută informații despre servicii"
Qwen → GPT: "Am găsit: servicii de protecție la foc, instalații, mentenanță"
GPT → User: "Oferim servicii complete de protecție la foc, incluzând instalații și mentenanță. [Sursa: /servicii]"
```

#### Exemplu 2: Întrebare complexă
```
User: "Cât costă o instalație de protecție la foc pentru o casă?"
GPT: "Să caut informații despre prețuri și instalații..."
GPT → Qwen: "Caută informații despre prețuri, instalații, case"
Qwen → GPT: "Am găsit: prețuri de la 2000 RON, depinde de suprafață"
GPT → User: "Prețurile pentru instalații de protecție la foc pentru case încep de la 2000 RON, dar variază în funcție de suprafață și complexitate. [Sursa: /preturi]"
```

### 9. MONITORIZARE ȘI LOGGING

#### A. Logs GPT
- Întrebări primite
- Deciziile de orchestare
- Răspunsurile generate
- Timpul de procesare

#### B. Logs Qwen
- Query-urile de căutare
- Rezultatele găsite
- Nivelul de încredere
- Timpul de procesare

#### C. Logs Agent
- Accesările la date
- Actualizările de conținut
- Conversațiile salvate
- Performanța

### 10. SECURITATE ȘI CONFORMITATE

#### A. Autentificare
- Verificare API key pentru GPT
- Validare agent_id
- Rate limiting

#### B. Audit
- Log toate conversațiile
- Monitorizează accesările
- Rapoarte de utilizare

#### C. Conformitate
- GDPR compliance
- PII scrubbing
- Data retention policies


