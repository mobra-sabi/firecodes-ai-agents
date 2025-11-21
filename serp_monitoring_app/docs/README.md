# 🚀 AI Agent Platform - Platformă Completă de Management Agenți

## 📁 Structură Foldere

```
agent_platform/
├── backend/          # Aplicații backend (FastAPI, workflows)
│   ├── dashboard_api.py
│   ├── ceo_master_workflow.py
│   └── continuous_industry_indexer.py
├── frontend/         # Interfață React modernă
│   ├── src/
│   │   ├── pages/    # Pagini (Dashboard, Agents, AgentDetail)
│   │   ├── components/ # Componente reutilizabile
│   │   └── lib/      # Utilități (API client)
│   └── package.json
├── static/           # Fișiere statice (dashboards HTML)
├── docs/            # Documentație
└── scripts/         # Scripturi de management
    ├── start_backend.sh
    ├── start_frontend.sh
    └── build_frontend.sh
```

## 🎯 Aplicații Principale

### Backend
- **dashboard_api.py** - API REST pentru dashboard (FastAPI)
- **ceo_master_workflow.py** - Workflow complet CEO pentru creare agent master + slave
- **continuous_industry_indexer.py** - Indexare continuă a industriei

### Frontend
- **Dashboard** - Overview cu statistici și agenți recenti
- **Agents** - Listă completă de agenți cu căutare
- **Agent Detail** - Detalii complete pentru fiecare agent

## 🚀 Pornire Aplicație

### Development Mode

```bash
# Terminal 1: Backend API
cd /srv/hf/ai_agents/agent_platform
./scripts/start_backend.sh

# Terminal 2: Frontend
cd /srv/hf/ai_agents/agent_platform
./scripts/start_frontend.sh
```

### Production Mode

```bash
# Build frontend
./scripts/build_frontend.sh

# Start backend (port 5000)
cd backend
python3 dashboard_api.py

# Serve frontend (port 4000)
cd frontend
npx serve -s dist -l 4000
```

## 🌐 Acces

- **Frontend Development**: http://localhost:5173
- **Backend API**: http://localhost:5000
- **API Docs**: http://localhost:5000/docs

## 📊 Features

✅ Dashboard modern cu statistici live
✅ Listă completă de agenți cu căutare
✅ Detalii agenți cu slave-ii asociați
✅ Design responsive și modern
✅ Auto-refresh date (30 secunde)
✅ Animații fluide cu Framer Motion

## 🛠️ Tehnologii

- **Frontend**: React 18 + Vite + Tailwind CSS
- **Backend**: FastAPI (Python)
- **State Management**: Zustand + React Query
- **Animations**: Framer Motion
- **Icons**: Lucide React

## 📝 Note

- Aplicația este organizată într-un folder dedicat pentru ușurință
- Toate scripturile sunt în folderul `scripts/`
- Frontend-ul se conectează automat la backend-ul local
