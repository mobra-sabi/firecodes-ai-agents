# 🤖 AI Agents Platform - Multi-User Sessions

## 📋 Prezentare Generală

Acest sistem oferă o interfață web completă pentru gestionarea agenților AI cu sesiuni separate pentru fiecare utilizator. Fiecare utilizator poate crea sesiuni pentru site-uri diferite și poate conversa cu agenții AI specializați pentru fiecare site.

## 🚀 Funcționalități Principale

### 1. **Sistem de Logare**
- Logare simplă cu nume utilizator
- Persistența sesiunilor în browser
- Deconectare sigură

### 2. **Gestionarea Sesiunilor**
- Creare sesiuni noi pentru site-uri diferite
- Comutare între sesiuni fără pierdere de context
- Istoricul sesiunilor per utilizator
- Status tracking pentru fiecare sesiune

### 3. **Crearea Agenților**
- Creare automată de agenți pentru fiecare site
- Asocierea agenților cu sesiunile utilizatorilor
- Delimitarea clară între agenții master și competitori

### 4. **Chat Dedicat**
- Chat separat pentru fiecare sesiune
- Integrare cu ChatGPT pentru răspunsuri inteligente
- Context specific pentru fiecare site
- Istoricul conversațiilor per sesiune

### 5. **Delimitarea Resurselor**
- Fiecare sesiune are resursele sale alocate
- ChatGPT știe exact pentru ce sesiune lucrează
- Qwen poate învăța specific pentru fiecare site
- Memoria separată pentru fiecare utilizator

## 🛠️ Instalare și Pornire

### 1. Pornește Backend-ul
```bash
./start_server.sh
```

### 2. Pornește UI-ul
```bash
./start_ui.sh
```

### 3. Accesează Aplicația
Deschide browserul și navighează la: `http://localhost:8080/ui_interface_with_sessions.html`

## 📱 Cum să Folosești Sistemul

### Pasul 1: Logare
1. Introdu numele tău în câmpul "Nume utilizator"
2. Opțional: introdu email-ul tău
3. Apasă "Conectează-te"

### Pasul 2: Creare Sesiune
1. Introdu URL-ul site-ului în câmpul "Site URL"
2. Opțional: dă un nume sesiunii
3. Apasă "Creează Sesiune Nouă"

### Pasul 3: Creare Agent
1. Selectează sesiunea creată
2. Apasă "Creează Agent" pentru a crea agentul pentru site
3. Așteaptă ca agentul să fie pregătit

### Pasul 4: Chat cu Agentul
1. Odată ce agentul este creat, chat-ul devine activ
2. Întreabă orice despre site-ul tău
3. Agentul va răspunde folosind ChatGPT cu contextul site-ului

### Pasul 5: Comutare între Sesiuni
1. Pentru a lucra cu alt site, creează o sesiune nouă
2. Comută între sesiuni făcând click pe cardurile de sesiuni
3. Fiecare sesiune păstrează contextul său separat

## 🔧 API Endpoints

### Sesiuni
- `POST /admin/industry/create-session` - Creează sesiune nouă
- `GET /admin/industry/sessions/{user_id}` - Obține sesiunile unui utilizator
- `POST /admin/industry/switch-session` - Comută la o sesiune
- `GET /admin/industry/all-sessions` - Vezi toate sesiunile active

### Agenți
- `POST /admin/industry/create-agent` - Creează agent pentru sesiune
- `GET /admin/industry/master-agents` - Obține doar agenții master
- `GET /admin/industry/competitor-agents/{master_agent_id}` - Obține agenții competitori

### Chat
- `POST /admin/industry/{agent_id}/chat` - Chat cu agentul

## 🗄️ Structura Bazei de Date

### Colecția `user_sessions`
```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "site_url": "string",
  "session_name": "string",
  "status": "active|inactive",
  "master_agent_id": "ObjectId",
  "competitor_agents": ["ObjectId"],
  "learning_progress": {
    "strategy_generated": boolean,
    "competitors_found": number,
    "competitors_downloaded": number,
    "competitor_agents_created": number
  },
  "resource_allocation": {
    "qwen_memory_allocated": boolean,
    "chatgpt_orchestration": boolean,
    "vector_memory_active": boolean
  }
}
```

### Colecția `agents`
```json
{
  "_id": "ObjectId",
  "name": "string",
  "site_url": "string",
  "domain": "string",
  "agent_type": "master|competitor",
  "session_id": "string",
  "user_id": "string",
  "master_agent_id": "ObjectId", // pentru competitori
  "parent_agent_id": "ObjectId", // pentru competitori
  "status": "ready|learning|error"
}
```

### Colecția `conversations`
```json
{
  "_id": "ObjectId",
  "agent_id": "ObjectId",
  "session_id": "string",
  "user_message": "string",
  "ai_response": "string",
  "timestamp": "datetime",
  "status": "completed|processing|error"
}
```

## 🎯 Beneficii

### Pentru Utilizatori
- **Sesiuni separate** pentru fiecare site
- **Context păstrat** între sesiuni
- **Chat dedicat** pentru fiecare agent
- **Istoric complet** al conversațiilor

### Pentru Sistem
- **Delimitarea clară** între utilizatori
- **Resursele alocate** corect per sesiune
- **ChatGPT știe** exact pentru ce lucrează
- **Qwen poate învăța** specific pentru fiecare site

### Pentru Dezvoltatori
- **API-uri clare** pentru toate operațiunile
- **Structură modulară** ușor de extins
- **Logging complet** pentru debugging
- **Separarea responsabilităților** între componente

## 🔍 Debugging

### Verifică Statusul Serverului
```bash
curl http://localhost:8083/health
```

### Vezi Logurile
```bash
tail -f server.log
```

### Verifică Sesiunile Active
```bash
curl http://localhost:8083/admin/industry/all-sessions
```

## 🚨 Oprire

### Oprește UI-ul
```bash
./stop_ui.sh
```

### Oprește Totul
```bash
./stop_ui.sh --all
```

## 📞 Suport

Pentru probleme sau întrebări, verifică:
1. Logurile din `server.log`
2. Statusul serverului backend
3. Conexiunea la baza de date MongoDB
4. Configurația API keys în `.env`

---

**🎉 Sistemul este gata de utilizare!** Fiecare utilizator poate acum să aibă sesiuni separate pentru site-uri diferite și să converseze cu agenții AI specializați pentru fiecare site.
