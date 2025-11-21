# 🔍 RAPORT: Timeout la creare agent

**Data**: 19 Noiembrie 2025, 16:45 UTC  
**Problema**: "timeout of 30000ms exceeded" când se încearcă crearea unui agent

---

## ❌ PROBLEMA IDENTIFICATĂ

### **Symptom**:
- Frontend-ul trimite request la `/api/agents`
- Request-ul timeout după 30s (configurat în `api.js`: `timeout: 30000`)
- Eroare: "Failed to create agent: timeout of 30000ms exceeded"

### **Teste efectuate**:

1. **Test cu curl (timeout 35s)**:
   ```bash
   curl -X POST http://localhost:8090/api/agents \
     -H "Content-Type: application/json" \
     -d '{"site_url":"https://bioclinica.ro/","industry":"medicina"}' \
     --max-time 35
   ```
   **Rezultat**: ❌ **TIMEOUT după 35s** - endpoint-ul nu răspunde

2. **Test Health Check**:
   ```bash
   curl http://localhost:8090/health --max-time 5
   ```
   **Rezultat**: ❌ **TIMEOUT după 5s** - API-ul este blocat sau foarte lent

3. **Verificare loguri**:
   - Logurile arată că workflow-urile rulează (văd workflow-uri pentru alte agenți)
   - Nu văd erori clare pentru request-ul de creare agent
   - Workflow-urile anterioare au rulat cu succes

---

## 🔍 ANALIZĂ CAUZĂ

### **Cod Endpoint** (`agent_api.py:1277-1346`):

```python
@app.post("/api/agents")
async def create_agent_full_workflow(request: dict = Body(...), background_tasks: BackgroundTasks = None):
    try:
        site_url = request.get("site_url")
        industry = request.get("industry", "")
        
        if not site_url:
            raise HTTPException(status_code=400, detail="site_url is required")
        
        logger.info(f"🚀 Starting FULL AGENT WORKFLOW for: {site_url}")
        
        # Import workflow
        from ceo_master_workflow import CEOMasterWorkflow
        
        workflow = CEOMasterWorkflow()
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{...}"
        
        async def run_full_workflow():
            # ... workflow execution ...
        
        # Rulează în background
        if background_tasks:
            background_tasks.add_task(run_full_workflow)
        else:
            asyncio.create_task(run_full_workflow())
        
        return {
            "ok": True,
            "workflow_id": workflow_id,
            ...
        }
```

### **Probleme identificate**:

1. **❌ Import blocant**: `from ceo_master_workflow import CEOMasterWorkflow` se face la fiecare request
   - Dacă import-ul este lent sau blochează, endpoint-ul nu răspunde
   
2. **❌ Instanțiere workflow**: `workflow = CEOMasterWorkflow()` se face sincron
   - Dacă constructor-ul este lent, blochează request-ul
   
3. **❌ Background task nu e garantat**: Dacă `background_tasks` e None, folosește `asyncio.create_task()`
   - Dar răspunsul ar trebui să fie returnat imediat, înainte de a rula workflow-ul

4. **⚠️ API-ul pare blocat**: Health check timeout după 5s sugerează că API-ul este ocupat sau blocat

---

## 🔧 SOLUȚII PROPUESE

### **Soluția 1: Mărește timeout-ul în frontend** (Temporar)

```javascript
// frontend-pro/src/services/api.js
const api = axios.create({
  baseURL,
  timeout: 60000, // 60s în loc de 30s
  ...
})
```

**Pro**: Rapid de implementat  
**Contra**: Nu rezolvă problema de bază - endpoint-ul tot nu răspunde

---

### **Soluția 2: Returnează răspunsul imediat** (Recomandat)

Modifică endpoint-ul să returneze răspunsul **ÎNAINTE** de a importa și instanția workflow-ul:

```python
@app.post("/api/agents")
async def create_agent_full_workflow(request: dict = Body(...), background_tasks: BackgroundTasks = None):
    try:
        site_url = request.get("site_url")
        industry = request.get("industry", "")
        
        if not site_url:
            raise HTTPException(status_code=400, detail="site_url is required")
        
        # Generează workflow_id imediat
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{site_url.replace('https://', '').replace('http://', '').replace('/', '_')[:30]}"
        
        # RETURNEAZĂ RĂSPUNSUL IMEDIAT
        response = {
            "ok": True,
            "workflow_id": workflow_id,
            "site_url": site_url,
            "industry": industry,
            "message": "Full agent workflow started! Monitor progress in Workflow Monitor.",
            "estimated_time_minutes": "20-45"
        }
        
        # PORNEȘTE WORKFLOW-UL ÎN BACKGROUND (după răspuns)
        async def start_workflow():
            try:
                from ceo_master_workflow import CEOMasterWorkflow
                workflow = CEOMasterWorkflow()
                
                logger.info(f"🔥 WORKFLOW {workflow_id} STARTED pentru {site_url}")
                result = await workflow.execute_full_workflow(
                    site_url=site_url,
                    results_per_keyword=20,
                    parallel_gpu_agents=5
                )
                logger.info(f"✅ WORKFLOW {workflow_id} COMPLETED")
            except Exception as e:
                logger.error(f"❌ WORKFLOW {workflow_id} FAILED: {e}")
        
        # Pornește în background task
        if background_tasks:
            background_tasks.add_task(start_workflow)
        else:
            asyncio.create_task(start_workflow())
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Pro**: Endpoint-ul răspunde imediat (< 1s)  
**Contra**: Necesită modificare cod

---

### **Soluția 3: Verifică dacă API-ul este blocat**

```bash
# Verifică procesele
ps aux | grep uvicorn

# Verifică dacă există request-uri blocate
netstat -an | grep 8090

# Restart API dacă e necesar
pkill -f "uvicorn agent_api"
cd /srv/hf/ai_agents
nohup uvicorn agent_api:app --host 0.0.0.0 --port 8090 --reload > logs/agent_api_restart.log 2>&1 &
```

---

## 📊 DIAGNOSTIC COMPLET

### **Status API**:
- ❌ Health check: TIMEOUT (5s)
- ❌ POST /api/agents: TIMEOUT (35s)
- ⚠️ API pare blocat sau foarte ocupat

### **Workflow-uri existente**:
- ✅ Workflow-uri anterioare au rulat cu succes
- ✅ 3 agenți creați în ultima oră (medialine.com, zitec.com, connsys.ro)
- ⚠️ Nu văd workflow-uri noi pentru bioclinica.ro

### **Frontend**:
- ✅ Request trimis corect la `/api/agents` (după fix)
- ✅ Timeout configurat: 30s
- ❌ Timeout se întâmplă înainte de a primi răspuns

---

## ✅ RECOMANDARE

**Acțiune imediată**:
1. **Restart API** pentru a elibera orice blocaje
2. **Mărește timeout-ul** în frontend la 60s (temporar)
3. **Modifică endpoint-ul** să returneze răspunsul imediat (Soluția 2)

**Acțiune pe termen lung**:
- Mută import-ul `CEOMasterWorkflow` la nivel de modul (nu în funcție)
- Folosește întotdeauna `background_tasks` pentru workflow-uri lungi
- Adaugă logging mai detaliat pentru debugging

---

**Raport generat**: 19 Noiembrie 2025, 16:45 UTC

