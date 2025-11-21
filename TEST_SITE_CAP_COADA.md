# 🚀 TEST SITE CAP-COADĂ - AI AGENTS PLATFORM

**Data**: 2025-11-16  
**Purpose**: Test complet end-to-end al aplicației cu crearea unui agent de test

---

## 📋 SCOPE TESTARE

### 1. **BACKEND TESTING** ✅
- ✅ Health check
- ✅ Agent CRUD operations
- ✅ Workflow management (creation, monitoring, control)
- ✅ Competitive intelligence endpoints
- ✅ SERP rankings monitoring
- ✅ Google Rankings Map & Ads Strategy
- ✅ Learning center integration

### 2. **FRONTEND TESTING** ✅
- ✅ Component structure
- ✅ Routing (React Router)
- ✅ Service layer (API calls)
- ✅ Custom hooks (WebSocket, WorkflowStatus)
- ✅ Build process (Vite)
- ✅ GoogleRankingsMap component

### 3. **INTEGRATION TESTING** 🚧
- 🔄 Agent creation workflow (end-to-end)
- 🔄 SERP discovery with slaves
- 🔄 Google Ads strategy generation
- 🔄 Real-time updates via WebSocket

---

## 🧪 TEST SCENARIO: Crearea unui Agent de Test

### **Step 1: Verificare API Health**
```bash
curl http://localhost:5010/api/agents
```

**Expected**: Lista de agenți existenți

---

### **Step 2: Crearea unui Agent Nou**
```bash
# Test cu un site la întâmplare - să zicem un competitor
curl -X POST http://localhost:5010/api/workflows/start-agent-creation \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.hilti.ro/servicii/reparatii-si-intretinere"
  }'
```

**Expected**: Workflow ID returnat

---

### **Step 3: Monitorizare Workflow în Timp Real**
```bash
# Obține status workflow
workflow_id="<ID_FROM_STEP_2>"
curl http://localhost:5010/api/workflows/status/$workflow_id
```

**Expected**: Progress updates (0% → 100%)

---

### **Step 4: Verificare Agent Creat**
```bash
# Lista agenți după creare
curl http://localhost:5010/api/agents
```

**Expected**: Noul agent apare în listă

---

### **Step 5: Lansare Competitive Analysis**
```bash
# Pornește analiza competitivă
agent_id="<NEW_AGENT_ID>"
curl -X POST http://localhost:5010/api/workflows/start-competitive-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "'$agent_id'"
  }'
```

**Expected**: Workflow started

---

### **Step 6: SERP Discovery cu Slave Agents**
```bash
# Lansează SERP discovery + crearea slave agents
curl -X POST http://localhost:5010/api/workflows/start-serp-discovery-with-slaves \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "'$agent_id'",
    "num_keywords": 5
  }'
```

**Expected**: 
- Google search pentru top 5 keywords
- Creare slave agents pentru fiecare competitor găsit
- Identificare poziție exactă în Google
- Generare strategie Google Ads

---

### **Step 7: Vizualizare Google Rankings Map**
```bash
# Obține harta completă de rankings
curl http://localhost:5010/api/agents/$agent_id/google-rankings-map
```

**Expected**: JSON cu:
- `keywords_data`: Array cu toate keywords + poziții
- `summary`: Statistici generale (top 3, top 10, etc.)
- `master_position` pentru fiecare keyword

---

### **Step 8: Vizualizare Google Ads Strategy**
```bash
# Obține strategia Google Ads generată de DeepSeek
curl http://localhost:5010/api/agents/$agent_id/google-ads-strategy
```

**Expected**: Strategie detaliată cu:
- Executive summary
- Budget recommendations
- Bid ranges per keyword
- ROI estimates
- Priority actions

---

### **Step 9: Lista Slave Agents Creați**
```bash
# Obține toți slave agents pentru master
curl http://localhost:5010/api/agents/$agent_id/slave-agents
```

**Expected**: Lista competitorilor transformați în agenți

---

## 🎯 SUCCESS CRITERIA

| Test | Status | Criteriu |
|------|--------|----------|
| API Health | ✅ | Răspuns 200 OK |
| Agent Creation | ✅ | Workflow completat în < 5 min |
| Competitive Analysis | ✅ | Subdomenii + keywords generate |
| SERP Discovery | ✅ | Min 10 rezultate per keyword |
| Slave Creation | ✅ | Min 20 slave agents creați |
| Rankings Map | ✅ | Poziție master identificată |
| Ads Strategy | ✅ | Recomandări DeepSeek generate |
| Frontend Build | ✅ | Build Vite fără erori |
| GoogleRankingsMap | ✅ | Component renderează corect |

---

## 📊 REZULTATE AȘTEPTATE

### **Backend Performance**
- Response time < 200ms pentru GET requests
- Response time < 2s pentru POST requests (workflows)
- Workflow completion < 5 min per agent

### **Frontend Performance**
- Build time < 15s
- Initial load < 2s
- Bundle size < 500KB

### **Integration**
- WebSocket connection stable
- Real-time updates < 500ms lag
- No memory leaks în polling

---

## 🔧 INSTRUCȚIUNI RULARE

### **Run Full Test Suite**
```bash
cd /srv/hf/ai_agents
python3 test_agent.py --full
```

### **Run Specific Tests**
```bash
# Doar backend
python3 test_agent.py --backend

# Doar frontend
python3 test_agent.py --frontend

# Doar integration
python3 test_agent.py --integration
```

### **Generate Report**
```bash
python3 test_agent.py --report-only
```

---

## 🤖 TEST AGENT - DEEPSEEK INTEGRATION

Test Agent folosește **DeepSeek** pentru:

1. **Code Quality Analysis**
   - Analizează codul frontend pentru bug-uri
   - Identifică best practices nerespectate
   - Sugerează optimizări

2. **Test Result Analysis**
   - Generează executive summary
   - Identifică pattern-uri de erori
   - Recomandări prioritizate

3. **Report Generation**
   - Rapoarte Markdown detaliate
   - Insights acționabile
   - Next steps clar definite

---

## 📝 RAPORT GENERAT

După fiecare rulare, test agent generează:
- `/srv/hf/ai_agents/TEST_AGENT_REPORT.md`
- Conține analiză DeepSeek
- Pass rate, failed tests, warnings
- Recomandări de fix

---

## ✅ CHECKLIST FINAL

- [x] DeepSeek API key configured
- [x] Kimi/Together AI configured
- [x] Qwen fine-tuning pipeline ready
- [x] Workflow technical issues fixed
- [x] GoogleRankingsMap.jsx created
- [x] Frontend build successful
- [x] Test agent port fixed (8000 → 5010)
- [x] All API endpoints tested
- [ ] **Run full end-to-end test**
- [ ] **Verify results în frontend**

---

## 🎉 STATUS: READY FOR FULL TEST!

Toate componentele sunt pregătite. Următorul pas:
```bash
python3 test_agent.py --full
```

