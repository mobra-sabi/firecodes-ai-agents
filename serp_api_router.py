#!/usr/bin/env python3
"""
🎯 SERP API Router - FastAPI endpoints pentru SERP Monitoring
Production-ready cu WebSocket support
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import asyncio
import logging
from enum import Enum

from serp_ingest import SERPScorer, canonical_domain
from serp_mongodb_schemas import SERPMongoDBSchemas

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/serp", tags=["SERP Monitoring"])

# Initialize components
scorer = SERPScorer()
schemas = SERPMongoDBSchemas()

# Active WebSocket connections (pentru live progress)
active_connections: Dict[str, List[WebSocket]] = {}


# ============================================================================
# MODELS (Pydantic)
# ============================================================================

class SERPRunRequest(BaseModel):
    """Request body pentru POST /api/serp/run"""
    agent_id: str = Field(..., description="ID agent master")
    keywords: List[str] = Field(..., description="Lista keywords de căutat")
    market: str = Field(default="ro", description="Piață (ro, us, uk, etc.)")
    provider: str = Field(default="brave", description="Provider SERP (brave, serpapi, custom)")
    results_per_keyword: int = Field(default=10, description="Câte rezultate per keyword (1-20)")


class SERPRunResponse(BaseModel):
    """Response pentru POST /api/serp/run"""
    run_id: str
    status: str
    estimated_duration: str
    agent_id: str
    keywords_count: int


class SERPRunStatus(str, Enum):
    """Status-uri posibile pentru SERP run"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"


class SERPRunStatusResponse(BaseModel):
    """Response pentru GET /api/serp/run/{run_id}"""
    run_id: str
    status: SERPRunStatus
    progress: Dict[str, Any]
    stats: Dict[str, Any]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


class CompetitorResponse(BaseModel):
    """Response pentru competitor"""
    domain: str
    threat_score: float
    visibility: float
    keywords_ranked: int
    avg_rank: float
    best_rank: int
    has_slave_agent: bool
    slave_agent_id: Optional[str]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/run", response_model=SERPRunResponse)
async def start_serp_run(
    request: SERPRunRequest,
    background_tasks: BackgroundTasks
):
    """
    🚀 START SERP RUN
    
    Pornește un SERP fetch job pentru keywords-urile specificate.
    Job-ul rulează în background și poate fi monitorizat prin:
    - GET /api/serp/run/{run_id} - polling status
    - WS /api/serp/ws/{run_id} - live progress
    
    Args:
        request: SERPRunRequest cu agent_id, keywords, market, provider
    
    Returns:
        SERPRunResponse cu run_id și status initial
    """
    logger.info(f"🚀 Starting SERP run for agent {request.agent_id} with {len(request.keywords)} keywords")
    
    # Validare
    if not request.keywords:
        raise HTTPException(status_code=400, detail="Keywords list cannot be empty")
    
    if request.results_per_keyword < 1 or request.results_per_keyword > 20:
        raise HTTPException(status_code=400, detail="results_per_keyword must be between 1 and 20")
    
    # Creează run în MongoDB
    run_id = schemas.insert_serp_run(
        agent_id=request.agent_id,
        keywords=request.keywords,
        market=request.market,
        provider=request.provider
    )
    
    # Estimare durată (2-3 secunde per keyword)
    estimated_seconds = len(request.keywords) * 2.5
    estimated_duration = f"{int(estimated_seconds // 60)}m {int(estimated_seconds % 60)}s"
    
    # Pornește job în background
    background_tasks.add_task(
        execute_serp_run,
        run_id=run_id,
        agent_id=request.agent_id,
        keywords=request.keywords,
        market=request.market,
        provider=request.provider,
        results_per_keyword=request.results_per_keyword
    )
    
    return SERPRunResponse(
        run_id=run_id,
        status="queued",
        estimated_duration=estimated_duration,
        agent_id=request.agent_id,
        keywords_count=len(request.keywords)
    )


@router.get("/run/{run_id}", response_model=SERPRunStatusResponse)
async def get_serp_run_status(run_id: str):
    """
    📊 GET SERP RUN STATUS
    
    Obține status-ul și progresul unui SERP run.
    
    Args:
        run_id: ID-ul run-ului
    
    Returns:
        SERPRunStatusResponse cu status, progress, stats
    """
    # Caută run în MongoDB
    run = schemas.db.serp_runs.find_one({"_id": run_id})
    
    if not run:
        raise HTTPException(status_code=404, detail=f"SERP run {run_id} not found")
    
    # Calculează progress
    total_keywords = len(run.get("keywords", []))
    queries_done = run.get("stats", {}).get("queries", 0)
    percentage = (queries_done / total_keywords * 100) if total_keywords > 0 else 0
    
    progress = {
        "current": queries_done,
        "total": total_keywords,
        "percentage": round(percentage, 1)
    }
    
    return SERPRunStatusResponse(
        run_id=run_id,
        status=run.get("status", "unknown"),
        progress=progress,
        stats=run.get("stats", {}),
        started_at=run.get("started_at"),
        finished_at=run.get("finished_at")
    )


@router.get("/results/{run_id}")
async def get_serp_results(run_id: str):
    """
    📋 GET SERP RESULTS
    
    Obține rezultatele SERP pentru un run finalizat.
    Returnează rezultate grupate per keyword cu top 10 (sau top N).
    
    Args:
        run_id: ID-ul run-ului
    
    Returns:
        Dict cu:
        - run_id: ID run
        - results: Lista rezultate per keyword
        - master_stats: Statistici master agent
    """
    # Verifică dacă run-ul există
    run = schemas.db.serp_runs.find_one({"_id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail=f"SERP run {run_id} not found")
    
    # Obține agent_id
    agent_id = run.get("agent_id")
    agent = schemas.db.site_agents.find_one({"_id": agent_id})
    if not agent:
        agent = schemas.db.agents.find_one({"_id": agent_id})
    
    master_domain = agent.get("domain", "") if agent else ""
    
    # Obține toate rezultatele SERP pentru acest run
    serp_results = list(schemas.db.serp_results.find({"run_id": run_id}))
    
    # Grupează per keyword
    results_by_keyword = {}
    for result in serp_results:
        keyword = result.get("keyword")
        if keyword not in results_by_keyword:
            results_by_keyword[keyword] = {
                "keyword": keyword,
                "top_results": [],
                "master_rank": None,
                "master_url": None
            }
        
        # Adaugă la top results
        results_by_keyword[keyword]["top_results"].append({
            "rank": result.get("rank"),
            "domain": result.get("domain"),
            "url": result.get("url"),
            "title": result.get("title", ""),
            "snippet": result.get("snippet", ""),
            "type": result.get("type", "organic")
        })
        
        # Dacă e masterul, salvează poziția
        if result.get("domain") == master_domain:
            results_by_keyword[keyword]["master_rank"] = result.get("rank")
            results_by_keyword[keyword]["master_url"] = result.get("url")
    
    # Sortează top results per keyword
    for kw_data in results_by_keyword.values():
        kw_data["top_results"].sort(key=lambda x: x["rank"])
    
    # Calculează statistici master
    master_appearances = sum(1 for kw_data in results_by_keyword.values() if kw_data["master_rank"])
    master_avg_rank = None
    if master_appearances > 0:
        master_ranks = [kw_data["master_rank"] for kw_data in results_by_keyword.values() if kw_data["master_rank"]]
        master_avg_rank = sum(master_ranks) / len(master_ranks)
    
    return {
        "run_id": run_id,
        "agent_id": agent_id,
        "master_domain": master_domain,
        "results": list(results_by_keyword.values()),
        "master_stats": {
            "keywords_ranked": master_appearances,
            "total_keywords": len(results_by_keyword),
            "coverage_percentage": round(master_appearances / len(results_by_keyword) * 100, 1) if results_by_keyword else 0,
            "avg_rank": round(master_avg_rank, 2) if master_avg_rank else None
        }
    }


@router.post("/competitors/from-serp")
async def create_competitors_from_serp(
    run_id: str,
    background_tasks: BackgroundTasks
):
    """
    🎯 CREATE COMPETITORS FROM SERP
    
    Analizează rezultatele SERP și creează/update competitori în MongoDB.
    Folosește formulele de scoring pentru visibility și threat.
    
    Args:
        run_id: ID-ul run-ului SERP
    
    Returns:
        Dict cu statistici: competitors_created, competitors_updated
    """
    logger.info(f"🎯 Creating competitors from SERP run {run_id}")
    
    # Verifică run
    run = schemas.db.serp_runs.find_one({"_id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail=f"SERP run {run_id} not found")
    
    if run.get("status") != "succeeded":
        raise HTTPException(status_code=400, detail=f"SERP run must be in 'succeeded' status")
    
    # Obține agent și keywords
    agent_id = run.get("agent_id")
    agent = schemas.db.site_agents.find_one({"_id": agent_id})
    if not agent:
        agent = schemas.db.agents.find_one({"_id": agent_id})
    
    master_domain = agent.get("domain", "")
    all_keywords = run.get("keywords", [])
    
    # Obține rezultate SERP
    serp_results = list(schemas.db.serp_results.find({"run_id": run_id}))
    
    # Exclude masterul din competitori
    competitor_results = [r for r in serp_results if r.get("domain") != master_domain]
    
    # Calculează visibility scores
    visibility_scores = scorer.aggregate_visibility(competitor_results, normalize=False)
    
    # Creează/update competitori
    competitors_created = 0
    competitors_updated = 0
    
    for comp_data in visibility_scores:
        domain = comp_data["domain"]
        
        # Verifică dacă există deja
        existing = schemas.db.competitors.find_one({"_id": domain})
        
        # Calculează threat score (simplified - fără authority deocamdată)
        visibility_normalized = comp_data["visibility_score"]
        keyword_overlap_pct = (comp_data["keywords_count"] / len(all_keywords)) * 100
        
        threat_score = scorer.calculate_threat_score(
            visibility_score=visibility_normalized,
            authority_score=0.5,  # Default/placeholder
            keyword_overlap_percentage=keyword_overlap_pct
        )
        
        scores = {
            "visibility": visibility_normalized,
            "authority": 0.5,  # Placeholder
            "threat": threat_score
        }
        
        # Upsert competitor
        schemas.upsert_competitor(
            domain=domain,
            keywords_seen=comp_data.get("keywords", []),
            scores=scores,
            agent_slave_id=None  # Va fi populat când se creează slave agent
        )
        
        if existing:
            competitors_updated += 1
        else:
            competitors_created += 1
    
    logger.info(f"✅ Created {competitors_created} competitors, updated {competitors_updated}")
    
    return {
        "competitors_created": competitors_created,
        "competitors_updated": competitors_updated,
        "total_unique_domains": len(visibility_scores)
    }


@router.get("/competitors", response_model=List[CompetitorResponse])
async def get_competitors(
    agent_id: str,
    sort_by: str = "threat_score",
    limit: int = 20
):
    """
    📊 GET COMPETITORS
    
    Obține lista competitorilor pentru un agent, sortați după threat score.
    
    Args:
        agent_id: ID agent master
        sort_by: Camp de sortare (threat_score, visibility, keywords_ranked)
        limit: Număr maxim rezultate
    
    Returns:
        Lista CompetitorResponse
    """
    # Map sort_by to MongoDB field
    sort_field_map = {
        "threat_score": "scores.threat",
        "visibility": "scores.visibility",
        "keywords_ranked": "keywords_seen"
    }
    
    sort_field = sort_field_map.get(sort_by, "scores.threat")
    
    # Query competitori
    # Note: Pentru production, ar trebui să avem o legătură agent_id -> competitors
    # Deocamdată returnăm toți competitorii sortați
    competitors = list(schemas.db.competitors.find({}).sort(sort_field, -1).limit(limit))
    
    result = []
    for comp in competitors:
        result.append(CompetitorResponse(
            domain=comp.get("domain", ""),
            threat_score=comp.get("scores", {}).get("threat", 0),
            visibility=comp.get("scores", {}).get("visibility", 0),
            keywords_ranked=len(comp.get("keywords_seen", [])),
            avg_rank=0.0,  # TODO: Calculate from serp_results
            best_rank=99,  # TODO: Calculate from serp_results
            has_slave_agent=comp.get("agent_slave_id") is not None,
            slave_agent_id=comp.get("agent_slave_id")
        ))
    
    return result


@router.websocket("/ws/{run_id}")
async def websocket_serp_progress(websocket: WebSocket, run_id: str):
    """
    🔌 WEBSOCKET LIVE PROGRESS
    
    WebSocket endpoint pentru progress în timp real al unui SERP run.
    
    Message format:
        {
            "type": "progress|status|log|complete|error",
            "data": {
                "current": 5,
                "total": 30,
                "percentage": 16.7,
                "message": "Processing keyword 5/30: vopsea intumescenta"
            }
        }
    
    Args:
        run_id: ID-ul run-ului de monitorizat
    """
    await websocket.accept()
    
    # Adaugă la conexiuni active
    if run_id not in active_connections:
        active_connections[run_id] = []
    active_connections[run_id].append(websocket)
    
    logger.info(f"🔌 WebSocket connected for run {run_id}")
    
    try:
        # Trimite status initial
        run = schemas.db.serp_runs.find_one({"_id": run_id})
        if run:
            await websocket.send_json({
                "type": "status",
                "data": {
                    "status": run.get("status", "unknown"),
                    "message": f"Connected to SERP run {run_id}"
                }
            })
        
        # Keep connection alive și așteaptă mesaje
        while True:
            try:
                # Primește mesaje de la client (ping/pong)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Răspunde la ping cu status update
                if data == "ping":
                    run = schemas.db.serp_runs.find_one({"_id": run_id})
                    if run:
                        total_kw = len(run.get("keywords", []))
                        queries = run.get("stats", {}).get("queries", 0)
                        
                        await websocket.send_json({
                            "type": "progress",
                            "data": {
                                "current": queries,
                                "total": total_kw,
                                "percentage": round(queries / total_kw * 100, 1) if total_kw > 0 else 0,
                                "status": run.get("status", "unknown")
                            }
                        })
            
            except asyncio.TimeoutError:
                # Timeout - verifică dacă run-ul e încă activ
                run = schemas.db.serp_runs.find_one({"_id": run_id})
                if run and run.get("status") in ["succeeded", "failed"]:
                    await websocket.send_json({
                        "type": "complete",
                        "data": {
                            "status": run.get("status"),
                            "message": f"SERP run {run_id} completed"
                        }
                    })
                    break
    
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected for run {run_id}")
    
    finally:
        # Remove from active connections
        if run_id in active_connections:
            active_connections[run_id].remove(websocket)
            if not active_connections[run_id]:
                del active_connections[run_id]


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def execute_serp_run(
    run_id: str,
    agent_id: str,
    keywords: List[str],
    market: str,
    provider: str,
    results_per_keyword: int
):
    """
    🔄 EXECUTE SERP RUN (Background Task)
    
    Execută SERP fetch pentru toate keywords-urile.
    Actualizează progresul în MongoDB și trimite updates prin WebSocket.
    
    Args:
        run_id: ID run
        agent_id: ID agent
        keywords: Lista keywords
        market: Piață
        provider: Provider SERP
        results_per_keyword: Număr rezultate per keyword
    """
    logger.info(f"🔄 Executing SERP run {run_id} with {len(keywords)} keywords")
    
    try:
        # Update status la running
        schemas.update_serp_run_status(run_id, "running")
        
        # Broadcast prin WebSocket
        await broadcast_to_websockets(run_id, {
            "type": "status",
            "data": {
                "status": "running",
                "message": f"Starting SERP fetch for {len(keywords)} keywords"
            }
        })
        
        queries_done = 0
        errors = 0
        total_results = 0
        unique_domains = set()
        
        # Pentru fiecare keyword
        for idx, keyword in enumerate(keywords, 1):
            try:
                logger.info(f"📊 Fetching SERP for keyword {idx}/{len(keywords)}: {keyword}")
                
                # TODO: Aici ar trebui să apelăm Brave API sau alt provider
                # Deocamdată simulăm cu date mock
                await asyncio.sleep(1)  # Simulare API call
                
                # Mock results (în production, acestea vin din Brave API)
                mock_results = generate_mock_serp_results(keyword, results_per_keyword)
                
                # Salvează rezultate în MongoDB
                for rank, result in enumerate(mock_results, 1):
                    domain = canonical_domain(result["url"])
                    unique_domains.add(domain)
                    
                    schemas.insert_serp_result(
                        run_id=run_id,
                        agent_id=agent_id,
                        keyword=keyword,
                        rank=rank,
                        url=result["url"],
                        domain=domain,
                        title=result.get("title", ""),
                        snippet=result.get("snippet", ""),
                        result_type=result.get("type", "organic")
                    )
                    total_results += 1
                
                # Update rank history pentru master (dacă apare)
                master_result = next((r for r in mock_results if agent_id in r["url"]), None)
                if master_result:
                    rank = mock_results.index(master_result) + 1
                    schemas.update_rank_history(
                        domain=agent_id,
                        keyword=keyword,
                        rank=rank,
                        run_id=run_id
                    )
                
                queries_done += 1
                
                # Broadcast progress
                await broadcast_to_websockets(run_id, {
                    "type": "progress",
                    "data": {
                        "current": queries_done,
                        "total": len(keywords),
                        "percentage": round(queries_done / len(keywords) * 100, 1),
                        "message": f"Processed keyword {queries_done}/{len(keywords)}: {keyword}"
                    }
                })
            
            except Exception as e:
                logger.error(f"❌ Error fetching SERP for keyword {keyword}: {e}")
                errors += 1
        
        # Finalizare
        status = "succeeded" if errors == 0 else "partial" if queries_done > 0 else "failed"
        
        schemas.update_serp_run_status(
            run_id=run_id,
            status=status,
            stats={
                "queries": queries_done,
                "pages_fetched": queries_done,
                "errors": errors,
                "total_results": total_results,
                "unique_domains": len(unique_domains)
            }
        )
        
        # Broadcast complete
        await broadcast_to_websockets(run_id, {
            "type": "complete",
            "data": {
                "status": status,
                "stats": {
                    "queries": queries_done,
                    "errors": errors,
                    "total_results": total_results,
                    "unique_domains": len(unique_domains)
                }
            }
        })
        
        logger.info(f"✅ SERP run {run_id} completed: {status}")
    
    except Exception as e:
        logger.error(f"❌ Fatal error in SERP run {run_id}: {e}")
        schemas.update_serp_run_status(run_id, "failed")
        
        await broadcast_to_websockets(run_id, {
            "type": "error",
            "data": {
                "message": f"SERP run failed: {str(e)}"
            }
        })


async def broadcast_to_websockets(run_id: str, message: dict):
    """Broadcast message to all WebSocket connections pentru un run_id"""
    if run_id in active_connections:
        for websocket in active_connections[run_id]:
            try:
                await websocket.send_json(message)
            except:
                pass  # Connection might be closed


def generate_mock_serp_results(keyword: str, count: int) -> List[Dict]:
    """
    Generate mock SERP results pentru testing
    TODO: Replace cu Brave API call real
    """
    mock_domains = [
        "promat.com", "competitor1.ro", "competitor2.ro",
        "competitor3.com", "competitor4.ro", "competitor5.com",
        "competitor6.ro", "competitor7.com", "competitor8.ro", "competitor9.com"
    ]
    
    results = []
    for i in range(min(count, len(mock_domains))):
        results.append({
            "url": f"https://{mock_domains[i]}/page-{keyword.replace(' ', '-')}",
            "title": f"{keyword.title()} - {mock_domains[i]}",
            "snippet": f"Oferim servicii de {keyword}...",
            "type": "organic"
        })
    
    return results


# ============================================================================
# ALERTS MANAGEMENT
# ============================================================================

@router.get("/alerts")
async def get_alerts(
    agent_id: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = 50
):
    """
    📢 GET ALERTS
    
    Obține lista alertelor pentru monitoring SERP.
    
    Args:
        agent_id: Filtrează după agent (opțional)
        acknowledged: Filtrează după status acknowledged (opțional)
        severity: Filtrează după severitate (critical, warning, info)
        limit: Număr maxim rezultate
    
    Returns:
        Lista alerte sortate descrescător după dată
    """
    query = {}
    
    if agent_id:
        query["agent_id"] = agent_id
    
    if acknowledged is not None:
        query["acknowledged"] = acknowledged
    
    if severity:
        query["severity"] = severity
    
    # Query MongoDB
    alerts = list(
        schemas.db.serp_alerts
        .find(query)
        .sort("notified_at", -1)
        .limit(limit)
    )
    
    # Format response
    result = []
    for alert in alerts:
        result.append({
            "id": str(alert["_id"]),
            "agent_id": alert.get("agent_id"),
            "run_id": alert.get("run_id"),
            "alert_type": alert.get("alert_type"),
            "severity": alert.get("severity"),
            "keyword": alert.get("keyword"),
            "details": alert.get("details", {}),
            "actions_suggested": alert.get("actions_suggested", []),
            "action_taken": alert.get("action_taken"),
            "notified_at": alert.get("notified_at").isoformat() if alert.get("notified_at") else None,
            "acknowledged": alert.get("acknowledged", False),
            "acknowledged_at": alert.get("acknowledged_at").isoformat() if alert.get("acknowledged_at") else None
        })
    
    return result


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, action_taken: Optional[str] = None):
    """
    ✅ ACKNOWLEDGE ALERT
    
    Marchează o alertă ca fiind acknowledged (văzută/procesată).
    
    Args:
        alert_id: ID-ul alertei
        action_taken: Acțiunea luată (opțional)
    
    Returns:
        Alertă actualizată
    """
    from bson import ObjectId
    
    try:
        obj_id = ObjectId(alert_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid alert_id format")
    
    # Update alert
    update_doc = {
        "acknowledged": True,
        "acknowledged_at": datetime.now(timezone.utc)
    }
    
    if action_taken:
        update_doc["action_taken"] = action_taken
    
    result = schemas.db.serp_alerts.update_one(
        {"_id": obj_id},
        {"$set": update_doc}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    # Return updated alert
    alert = schemas.db.serp_alerts.find_one({"_id": obj_id})
    
    return {
        "id": str(alert["_id"]),
        "acknowledged": alert.get("acknowledged"),
        "acknowledged_at": alert.get("acknowledged_at").isoformat() if alert.get("acknowledged_at") else None,
        "action_taken": alert.get("action_taken")
    }


# ============================================================================
# AGENT MANAGEMENT
# ============================================================================

@router.post("/agents/slave/create")
async def create_slave_agent(
    domain: str,
    master_agent_id: str,
    background_tasks: BackgroundTasks
):
    """
    🤖 CREATE SLAVE AGENT
    
    Creează un slave agent pentru un competitor detectat în SERP.
    
    Args:
        domain: Domeniul competitorului
        master_agent_id: ID-ul agent-ului master
    
    Returns:
        Slave agent creat
    """
    logger.info(f"🤖 Creating slave agent for domain: {domain}")
    
    # Verifică dacă există deja slave pentru acest domeniu
    existing = schemas.db.agents.find_one({
        "domain": domain,
        "agent_type": "slave",
        "master_agent_id": master_agent_id
    })
    
    if existing:
        return {
            "agent_id": str(existing["_id"]),
            "domain": domain,
            "status": "already_exists",
            "message": f"Slave agent already exists for {domain}"
        }
    
    # Creează slave agent
    from bson import ObjectId
    
    agent_doc = {
        "domain": domain,
        "site_url": f"https://{domain}",
        "agent_type": "slave",
        "master_agent_id": master_agent_id,
        "created_at": datetime.now(timezone.utc),
        "status": "created",
        "chunks_indexed": 0,
        "keywords": [],
        "competitor": True
    }
    
    result = schemas.db.agents.insert_one(agent_doc)
    agent_id = str(result.inserted_id)
    
    # Update competitor cu agent_slave_id
    schemas.db.competitors.update_one(
        {"_id": domain},
        {"$set": {"agent_slave_id": agent_id}}
    )
    
    # TODO: Trigger crawling în background
    # background_tasks.add_task(crawl_competitor_site, agent_id, domain)
    
    logger.info(f"✅ Slave agent created: {agent_id} for {domain}")
    
    return {
        "agent_id": agent_id,
        "domain": domain,
        "status": "created",
        "message": f"Slave agent created for {domain}"
    }


@router.post("/graph/update")
async def update_graph(agent_id: str, run_id: str):
    """
    📊 UPDATE GRAPH
    
    Actualizează graful de competitori bazat pe rezultatele SERP.
    Creează noduri și muchii între master și competitori.
    
    Args:
        agent_id: ID agent master
        run_id: ID run SERP
    
    Returns:
        Statistici graf (noduri, muchii)
    """
    logger.info(f"📊 Updating graph for agent {agent_id}, run {run_id}")
    
    # Obține master agent
    from bson import ObjectId
    try:
        master_id = ObjectId(agent_id) if isinstance(agent_id, str) else agent_id
    except:
        master_id = agent_id
    
    master = schemas.db.site_agents.find_one({"_id": master_id})
    if not master:
        master = schemas.db.agents.find_one({"_id": master_id})
    
    if not master:
        raise HTTPException(status_code=404, detail=f"Master agent {agent_id} not found")
    
    master_domain = master.get("domain", "")
    
    # Obține competitori din SERP
    serp_results = list(schemas.db.serp_results.find({"run_id": run_id}))
    
    # Grupează per domeniu
    domains = {}
    for result in serp_results:
        domain = result.get("domain")
        if domain and domain != master_domain:
            if domain not in domains:
                domains[domain] = {
                    "keywords": [],
                    "avg_rank": [],
                    "appearances": 0
                }
            domains[domain]["keywords"].append(result.get("keyword"))
            domains[domain]["avg_rank"].append(result.get("rank", 99))
            domains[domain]["appearances"] += 1
    
    # Calculează similarity și creează edges
    edges_created = 0
    
    for domain, data in domains.items():
        # Keyword overlap (Jaccard similarity)
        master_keywords = set(master.get("keywords", []))
        comp_keywords = set(data["keywords"])
        
        if master_keywords and comp_keywords:
            intersection = len(master_keywords & comp_keywords)
            union = len(master_keywords | comp_keywords)
            similarity = intersection / union if union > 0 else 0
        else:
            similarity = 0
        
        # Average rank
        avg_rank = sum(data["avg_rank"]) / len(data["avg_rank"]) if data["avg_rank"] else 99
        
        # Edge weight (inverse of rank difference)
        edge_weight = 1.0 / (1.0 + abs(5 - avg_rank))  # 5 = target rank
        
        # Salvează edge în MongoDB (opțional - pentru vizualizare graf)
        edge_doc = {
            "master_domain": master_domain,
            "competitor_domain": domain,
            "run_id": run_id,
            "similarity": similarity,
            "avg_rank": avg_rank,
            "edge_weight": edge_weight,
            "keywords_overlap": list(master_keywords & comp_keywords),
            "created_at": datetime.now(timezone.utc)
        }
        
        # Update sau insert
        schemas.db.competitor_edges.update_one(
            {
                "master_domain": master_domain,
                "competitor_domain": domain
            },
            {"$set": edge_doc},
            upsert=True
        )
        
        edges_created += 1
    
    logger.info(f"✅ Graph updated: {len(domains)} nodes, {edges_created} edges")
    
    return {
        "agent_id": agent_id,
        "run_id": run_id,
        "nodes": len(domains) + 1,  # +1 pentru master
        "edges": edges_created,
        "master_domain": master_domain,
        "competitors": list(domains.keys())
    }


@router.post("/monitor/schedule")
async def schedule_monitoring(
    agent_id: str,
    cadence: str = "daily"
):
    """
    ⏰ SCHEDULE MONITORING
    
    Programează monitoring SERP automat pentru un agent.
    
    Args:
        agent_id: ID agent master
        cadence: Frecvență (daily, weekly, monthly)
    
    Returns:
        Confirmare schedule
    """
    logger.info(f"⏰ Scheduling {cadence} monitoring for agent {agent_id}")
    
    # Verifică agent există
    from bson import ObjectId
    try:
        obj_id = ObjectId(agent_id) if isinstance(agent_id, str) else agent_id
    except:
        obj_id = agent_id
    
    agent = schemas.db.site_agents.find_one({"_id": obj_id})
    if not agent:
        agent = schemas.db.agents.find_one({"_id": obj_id})
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    # Validare cadence
    valid_cadences = ["daily", "weekly", "monthly"]
    if cadence not in valid_cadences:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cadence. Must be one of: {', '.join(valid_cadences)}"
        )
    
    # Salvează schedule în MongoDB
    schedule_doc = {
        "agent_id": agent_id,
        "cadence": cadence,
        "enabled": True,
        "created_at": datetime.now(timezone.utc),
        "last_run": None,
        "next_run": None  # Calculat de scheduler
    }
    
    # Update sau insert
    result = schemas.db.monitoring_schedules.update_one(
        {"agent_id": agent_id},
        {"$set": schedule_doc},
        upsert=True
    )
    
    logger.info(f"✅ Monitoring scheduled: {cadence} for agent {agent_id}")
    
    return {
        "agent_id": agent_id,
        "cadence": cadence,
        "enabled": True,
        "message": f"Monitoring scheduled: {cadence}",
        "note": "Scheduler will pick this up on next run"
    }


@router.post("/report/deepseek")
async def generate_ceo_report(
    agent_id: str,
    run_id: Optional[str] = None,
    use_deepseek: bool = False
):
    """
    📊 GENERATE CEO REPORT
    
    Generează executive summary report pentru CEO folosind DeepSeek.
    
    Args:
        agent_id: ID agent master
        run_id: ID run SERP (opțional - folosește ultimul dacă lipsește)
        use_deepseek: Dacă True, folosește DeepSeek API; altfel generează report basic
    
    Returns:
        CEO report complet cu executive summary, oportunități, acțiuni
    """
    logger.info(f"📊 Generating CEO report for agent {agent_id}")
    
    try:
        # Import generator
        import sys
        sys.path.insert(0, '/srv/hf/ai_agents')
        from deepseek_ceo_report import DeepSeekCEOReportGenerator
        
        # Generate report
        generator = DeepSeekCEOReportGenerator()
        result = generator.generate_report(agent_id, run_id, use_deepseek)
        
        logger.info(f"✅ CEO report generated: {result['report_id']}")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Error generating CEO report: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SERP API",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

