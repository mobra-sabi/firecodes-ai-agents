# 🎭 Master Agent - Agent Maestru Verbal

Serviciu FastAPI complet pentru controlul verbal al întregului sistem AI.

## 📋 Descriere

Master Agent este un agent maestru verbal care permite controlul complet al sistemului AI prin conversație naturală. El învață din comportamentul fiecărui utilizator și personalizează răspunsurile și acțiunile.

## 🚀 Pornire

```bash
cd /srv/hf/ai_agents/master_agent
chmod +x start_master_agent.sh
bash start_master_agent.sh
```

Serviciul va rula pe **http://localhost:5010**

## 📡 Endpoints

### 1. Chat Verbal și Text
```bash
POST /api/chat
Content-Type: application/json

{
  "user_id": "admin",
  "message": "pornește fine-tuningul",
  "generate_audio": true
}
```

**Răspuns:**
```json
{
  "text": "Am pornit fine-tuningul modelului...",
  "audio_path": "/voice/output/response_2025-11-14T21-00.wav",
  "action": "start_finetune",
  "confidence": 1.0
}
```

### 2. Chat cu Audio Input
```bash
POST /api/chat/audio
Content-Type: multipart/form-data

user_id=admin
audio_file=@recording.wav
```

### 3. Execută Acțiune
```bash
POST /api/execute
Content-Type: application/json

{
  "action": "build_jsonl",
  "user_id": "admin"
}
```

### 4. Status Noduri
```bash
GET /api/state
```

### 5. Profil Utilizator
```bash
GET /api/profile/{user_id}
```

### 6. Învățare Comportamentală
```bash
POST /api/learn
Content-Type: application/json

{
  "user_id": "admin"
}
```

### 7. WebSocket (Real-time)
```javascript
const ws = new WebSocket('ws://localhost:5010/api/ws/admin');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};

ws.send(JSON.stringify({
  type: "chat",
  message: "pornește fine-tuningul"
}));
```

## 🧠 Funcționalități

### Detectare Intenție
- **NLP simplu** + **regex patterns** + **embedding similarity**
- Mapează mesajele către acțiuni:
  - `build_jsonl` - Export dataset JSONL
  - `start_finetune` - Pornește fine-tuning
  - `update_qdrant` - Actualizează Qdrant
  - `status_nodes` - Verifică status noduri
  - `show_recent` - Arată interacțiuni recente
  - `summarize_feedback` - Rezumat feedback

### Memorie și Profil
- **user_profiles** - Preferințe, istoric, success_rate
- **agent_interactions** - Log complet conversații
- **agent_jobs** - Tracking job-uri în execuție
- Actualizare automată scoruri și patternuri

### Învățare Comportamentală
- Analiză patternuri per user
- Embeddings în Qdrant (`user_memory`)
- Sugestii bazate pe istoric
- Personalizare răspunsuri

### Interfață Vocală
- **STT**: Whisper local (Speech-to-Text)
- **TTS**: Piper sau Coqui (Text-to-Speech)
- Audio files generate în `voice/output/`

### Integrare UI
- WebSocket pentru comunicare real-time
- Autopilot mode (trimite click-uri la agent)
- Bridge cu UI Backend (http://localhost:5001)

## 📁 Structură

```
master_agent/
├── agent_main.py              # FastAPI app principal
├── router.py                  # Rute API
├── agent_config.yaml          # Configurație
├── start_master_agent.sh      # Script pornire
├── memory/
│   ├── profiles_db.py         # Manager profiluri
│   └── context_memory.py      # Memorie contextuală (Qdrant)
├── skills/
│   ├── planning.py            # Detectare intenție
│   └── actions.py             # Executor acțiuni
├── controllers/
│   ├── node_controller.py     # Control noduri
│   └── learning_controller.py # Învățare comportamentală
├── interface/
│   ├── chat_api.py            # API chat
│   └── frontend_bridge.py     # Bridge UI (WebSocket)
├── voice/
│   ├── stt_service.py         # Speech-to-Text
│   └── tts_service.py         # Text-to-Speech
└── logs/
    └── agent_actions.log       # Log acțiuni
```

## 🔧 Configurare

Editează `agent_config.yaml` pentru:
- Port și host
- Conectări (MongoDB, Qdrant, UI Backend, Orchestrator)
- Path-uri scripturi
- Configurație voice (STT/TTS)

## 📊 Logging

Toate acțiunile sunt loggate în:
- `logs/agent_actions.log` - Log detaliat
- `logs/startup.log` - Log pornire

## 🧪 Testare

```bash
# Test chat
curl -X POST http://127.0.0.1:5010/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"admin","message":"pornește fine-tuningul"}'

# Test status
curl http://127.0.0.1:5010/api/state

# Test profil
curl http://127.0.0.1:5010/api/profile/admin
```

## 🎯 Comportament Inteligent

Agentul:
1. **Detectează intenția** din mesaj
2. **Mapează către acțiune** (build_jsonl, fine-tune, etc.)
3. **Confirmă verbal** ce face
4. **Dacă nu e sigur**, cere confirmare
5. **După fiecare acțiune**, adaugă la profil
6. **La următoarea conversație**, personalizează

**Exemplu:**
- User: "pornește fine-tuningul"
- Agent: "Am pornit fine-tuningul modelului. Acest proces poate dura ceva timp. Te voi anunța când se termină."
- (După câteva interacțiuni)
- Agent: "Ultima dată ai lansat fine-tuning la ora 21. Să repet același flux?"

## 📝 Dependențe

```bash
pip install fastapi uvicorn pymongo qdrant-client sentence-transformers
pip install openai-whisper  # Pentru STT
pip install piper-tts       # Pentru TTS (sau TTS pentru Coqui)
```

## 🔗 Integrare

- **MongoDB**: `mongodb://127.0.0.1:27017/adbrain_ai`
- **Qdrant**: `http://127.0.0.1:6333`
- **UI Backend**: `http://127.0.0.1:5001`
- **Orchestrator**: `http://127.0.0.1:18001`

## ✅ Status

Serviciul rulează și este gata de utilizare! 🎉


