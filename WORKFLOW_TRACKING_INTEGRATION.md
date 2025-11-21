# 🔄 INTEGRARE WORKFLOW TRACKING ÎN WORKFLOW-URI EXISTENTE

## 📋 OVERVIEW

Sistemul de tracking workflow monitorizează fiecare pas din planul de implementare și generează rapoarte detaliate.

## 🎯 PAȘI PENTRU INTEGRARE

### 1. Import Workflow Tracker

```python
from workflow_tracking_system import get_workflow_tracker, WorkflowStep, StepStatus

# Obține tracker instance
workflow_tracker = get_workflow_tracker()
```

### 2. Track Înainte de Execuție

```python
# Începe tracking
workflow_tracker.track_step(
    step=WorkflowStep.CREATE_MASTER,
    agent_id=agent_id,
    status=StepStatus.IN_PROGRESS,
    details={"url": url, "started_at": datetime.now(timezone.utc).isoformat()}
)
```

### 3. Track După Execuție (Success)

```python
try:
    # Execută operația
    result = create_master_agent(url)
    
    # Marchează ca completat
    workflow_tracker.complete_step(
        step=WorkflowStep.CREATE_MASTER,
        agent_id=agent_id,
        details={
            "agent_id": result["agent_id"],
            "chunks_created": result["chunks_count"],
            "embeddings_generated": result["embeddings_count"]
        },
        metadata={"duration_seconds": result.get("duration", 0)}
    )
except Exception as e:
    # Marchează ca eșuat
    workflow_tracker.fail_step(
        step=WorkflowStep.CREATE_MASTER,
        agent_id=agent_id,
        error=str(e),
        error_traceback=traceback.format_exc(),
        details={"url": url}
    )
    raise
```

## 📝 EXEMPLE DE INTEGRARE

### Exemplu 1: Create Master Agent

```python
async def create_agent_full_workflow(url: str):
    agent_id = None
    
    try:
        # Track: CREATE_MASTER
        workflow_tracker.track_step(
            step=WorkflowStep.CREATE_MASTER,
            status=StepStatus.IN_PROGRESS,
            details={"url": url}
        )
        
        # Execută crearea
        agent = await create_master_agent(url)
        agent_id = agent["_id"]
        
        workflow_tracker.complete_step(
            step=WorkflowStep.CREATE_MASTER,
            agent_id=agent_id,
            details={"agent_id": agent_id, "domain": agent["domain"]}
        )
        
        # Track: CRAWL_SPLIT_EMBED
        workflow_tracker.track_step(
            step=WorkflowStep.CRAWL_SPLIT_EMBED,
            agent_id=agent_id,
            status=StepStatus.IN_PROGRESS
        )
        
        # Execută crawl + embed
        chunks = await crawl_and_embed(url, agent_id)
        
        workflow_tracker.complete_step(
            step=WorkflowStep.CRAWL_SPLIT_EMBED,
            agent_id=agent_id,
            details={"chunks_count": len(chunks)}
        )
        
        # Track: QDRANT_STORAGE
        workflow_tracker.track_step(
            step=WorkflowStep.QDRANT_STORAGE,
            agent_id=agent_id,
            status=StepStatus.IN_PROGRESS
        )
        
        # Store în Qdrant
        await store_in_qdrant(agent_id, chunks)
        
        workflow_tracker.complete_step(
            step=WorkflowStep.QDRANT_STORAGE,
            agent_id=agent_id,
            details={"vectors_stored": len(chunks)}
        )
        
        return agent
        
    except Exception as e:
        if agent_id:
            workflow_tracker.fail_step(
                step=WorkflowStep.CREATE_MASTER,
                agent_id=agent_id,
                error=str(e),
                error_traceback=traceback.format_exc()
            )
        raise
```

### Exemplu 2: SERP Run

```python
async def run_serp_for_agent(agent_id: str, keywords: List[str]):
    try:
        # Track: SERP_RUN_ALL_KW
        workflow_tracker.track_step(
            step=WorkflowStep.SERP_RUN_ALL_KW,
            agent_id=agent_id,
            status=StepStatus.IN_PROGRESS,
            details={"keywords_count": len(keywords)}
        )
        
        # Execută SERP
        results = await serp_scheduler.run_serp(agent_id, keywords)
        
        workflow_tracker.complete_step(
            step=WorkflowStep.SERP_RUN_ALL_KW,
            agent_id=agent_id,
            details={
                "keywords_processed": len(keywords),
                "results_found": len(results),
                "competitors_discovered": len(set(r["domain"] for r in results))
            }
        )
        
        # Track: SERP_RESULTS_VISIBILITY
        workflow_tracker.track_step(
            step=WorkflowStep.SERP_RESULTS_VISIBILITY,
            agent_id=agent_id,
            status=StepStatus.IN_PROGRESS
        )
        
        # Calculează visibility
        visibility = calculate_visibility(results)
        
        workflow_tracker.complete_step(
            step=WorkflowStep.SERP_RESULTS_VISIBILITY,
            agent_id=agent_id,
            details={
                "master_visibility": visibility["master"],
                "top_competitor": visibility["top_competitor"]
            }
        )
        
        return results
        
    except Exception as e:
        workflow_tracker.fail_step(
            step=WorkflowStep.SERP_RUN_ALL_KW,
            agent_id=agent_id,
            error=str(e),
            error_traceback=traceback.format_exc()
        )
        raise
```

### Exemplu 3: Action Engine

```python
async def execute_action(action_id: str, action_type: str):
    try:
        # Track based on action type
        step_map = {
            "content_create": WorkflowStep.COPYWRITER_NEW_PAGES,
            "onpage_optimize": WorkflowStep.ONPAGE_H1_META,
            "interlink_suggest": WorkflowStep.INTERLINKING_SUGGESTIONS,
            "schema_generate": WorkflowStep.COPYWRITER_SCHEMA_JSONLD,
            "ads_create": WorkflowStep.ADS_CAMPAIGNS_CREATED
        }
        
        step = step_map.get(action_type)
        if not step:
            return
        
        workflow_tracker.track_step(
            step=step,
            agent_id=action_id,
            status=StepStatus.IN_PROGRESS
        )
        
        # Execută acțiunea
        result = await action_orchestrator.execute_action(action_id)
        
        workflow_tracker.complete_step(
            step=step,
            agent_id=action_id,
            details=result
        )
        
        return result
        
    except Exception as e:
        workflow_tracker.fail_step(
            step=step,
            agent_id=action_id,
            error=str(e),
            error_traceback=traceback.format_exc()
        )
        raise
```

## 🔗 LOCAȚII PENTRU INTEGRARE

### Fișiere care trebuie modificate:

1. **`ceo_master_workflow.py`**
   - `execute_full_workflow()` - Track fiecare fază
   - `_phase1_create_master()` - Track CREATE_MASTER
   - `_phase2_integrate_langchain()` - Track LANGCHAIN_CHAINS
   - `_phase3_competitive_analysis()` - Track DEEPSEEK_SUBDOMAINS_KEYWORDS
   - `_phase4_serp_discovery()` - Track SERP_RUN_ALL_KW
   - `_phase5_create_slaves()` - Track CREATE_SLAVES_TOP_COMPETITORS

2. **`full_agent_creator.py`**
   - `create_full_agent()` - Track CRAWL_SPLIT_EMBED, QDRANT_STORAGE

3. **`serp_scheduler.py`**
   - `run_serp_for_agent()` - Track SERP_RUN_ALL_KW, SERP_RESULTS_VISIBILITY

4. **`slave_agents_auto_creator.py`**
   - `create_slave_agent()` - Track SLAVE_AGENT_CREATED
   - `create_all_slaves_for_agent()` - Track CREATE_SLAVES_TOP_COMPETITORS

5. **`action_orchestrator.py`**
   - `execute_playbook()` - Track ACTION_ENGINE_EXECUTE
   - `execute_action()` - Track based on action type

6. **`playbook_generator.py`**
   - `generate_playbook()` - Track DEEPSEEK_REPORT

7. **`org_graph_manager.py`**
   - `update_similarities()` - Track GRAPH_MASTER_SLAVES

8. **`google_ads_manager.py`**
   - `create_campaign()` - Track ADS_CAMPAIGNS_CREATED
   - `sync_from_seo_insights()` - Track ADS_GA4_GSC_SYNC

## 📊 VERIFICARE ÎN UI

După integrare, poți verifica tracking-ul în UI:

1. Navighează la `/workflow-tracker`
2. Vezi toți pașii organizați pe categorii
3. Click pe un pas pentru detalii complete
4. Vezi rapoarte cu success rate, duration, errors

## 🎯 BENEFICII

- ✅ **Vizibilitate completă** - Vezi exact ce se execută și când
- ✅ **Debugging ușor** - Identifică rapid unde eșuează workflow-urile
- ✅ **Rapoarte automate** - Generează rapoarte pentru fiecare agent
- ✅ **Performance tracking** - Măsoară durata fiecărui pas
- ✅ **Error tracking** - Capturează toate erorile cu traceback

## 📝 NOTE

- Tracking-ul este **non-blocking** - nu afectează performanța
- Toate entry-urile sunt salvate în MongoDB (`workflow_tracking` collection)
- Poți filtra pe agent, step, status, sau perioadă de timp
- Rapoartele pot fi exportate în JSON pentru analiză ulterioară

