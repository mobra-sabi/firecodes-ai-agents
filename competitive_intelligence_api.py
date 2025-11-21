#!/usr/bin/env python3
"""
🎯 COMPETITIVE INTELLIGENCE API
================================
API pentru creare agenți slave din concurență și învățare competitivă

Endpoints:
- POST /api/start-workflow - Start workflow pentru un site master
- GET /api/workflow-status/{workflow_id} - Status workflow
- GET /api/agents - Lista tuturor agenților (master + slaves)
- GET /api/agent/{agent_id} - Detalii agent
- GET /api/master/{master_id}/slaves - Lista slaves pentru master
- GET /api/ci-report/{master_id} - Raport CI pentru master
- GET /api/orgchart/{master_id} - Organogramă master-slave
"""

import asyncio
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import logging

from ceo_master_workflow import CEOMasterWorkflow

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Competitive Intelligence API",
    description="API pentru crearea și gestionarea agenților AI competitive intelligence",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB
mongo = MongoClient("mongodb://localhost:27017/")
db = mongo["ai_agents_db"]

# Workflow tracking
active_workflows = {}


# ============================================================================
# REQUEST MODELS
# ============================================================================

class StartWorkflowRequest(BaseModel):
    site_url: str
    results_per_keyword: int = 15
    parallel_gpu_agents: int = 5


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str  # "running", "completed", "failed"
    current_phase: str
    progress_percentage: int
    master_agent_id: Optional[str] = None
    slaves_created: int = 0
    total_competitors: int = 0
    error: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None


# ============================================================================
# WORKFLOW MANAGEMENT
# ============================================================================

async def run_workflow_background(workflow_id: str, site_url: str, results_per_keyword: int, parallel_gpu_agents: int):
    """
    Rulează workflow-ul în background
    """
    try:
        logger.info(f"🚀 Starting workflow {workflow_id} for {site_url}")
        
        # Update status
        active_workflows[workflow_id] = {
            "status": "running",
            "current_phase": "initialization",
            "progress_percentage": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "site_url": site_url
        }
        
        # Create workflow
        workflow = CEOMasterWorkflow()
        
        # PHASE 1-3: Create master agent (already exists)
        active_workflows[workflow_id].update({
            "current_phase": "phase_1_3_master_creation",
            "progress_percentage": 10
        })
        
        # Find or create master agent
        from urllib.parse import urlparse
        import tldextract
        domain = tldextract.extract(site_url).top_domain_under_public_suffix.lower()
        
        master = db.site_agents.find_one({"domain": domain})
        if not master:
            # Create master agent if doesn't exist
            from tools.construction_agent_creator import ConstructionAgentCreator
            creator = ConstructionAgentCreator()
            creator.create_site_agent(site_url)
            master = db.site_agents.find_one({"domain": domain})
        
        master_agent_id = str(master["_id"])
        
        active_workflows[workflow_id].update({
            "master_agent_id": master_agent_id,
            "progress_percentage": 30
        })
        
        # PHASE 4: DeepSeek decompose site
        active_workflows[workflow_id].update({
            "current_phase": "phase_4_decomposition",
            "progress_percentage": 40
        })
        
        phase4_result = await workflow._phase4_deepseek_decompose_site(master_agent_id)
        keywords = phase4_result.get("overall_keywords", [])
        
        # PHASE 5: Competitor discovery (demo mode)
        active_workflows[workflow_id].update({
            "current_phase": "phase_5_discovery",
            "progress_percentage": 50
        })
        
        # Find competitors from existing agents
        competitors_from_db = list(db.site_agents.find({
            "_id": {"$ne": ObjectId(master_agent_id)},
            "status": "validated",
            "has_embeddings": True
        }).limit(results_per_keyword))
        
        competitors = []
        for i, comp in enumerate(competitors_from_db):
            competitors.append({
                "url": comp.get("site_url"),
                "domain": comp.get("domain"),
                "keyword": keywords[i % len(keywords)] if keywords else f"keyword_{i}",
                "serp_position": i + 2,
                "title": f"Competitor {i+1}",
                "snippet": "Competitor description"
            })
        
        active_workflows[workflow_id].update({
            "total_competitors": len(competitors),
            "progress_percentage": 60
        })
        
        # PHASE 7: Create slave agents
        active_workflows[workflow_id].update({
            "current_phase": "phase_7_slave_creation",
            "progress_percentage": 70
        })
        
        phase7_result = await workflow._phase7_create_competitor_agents_parallel(
            competitors=competitors,
            parallel_count=parallel_gpu_agents,
            master_agent_id=master_agent_id
        )
        
        slave_ids = phase7_result.get("agent_ids", [])
        
        active_workflows[workflow_id].update({
            "slaves_created": len(slave_ids),
            "progress_percentage": 85
        })
        
        # PHASE 8: Master learning + CI Report
        active_workflows[workflow_id].update({
            "current_phase": "phase_8_learning",
            "progress_percentage": 90
        })
        
        phase8_result = await workflow._phase8_create_master_slave_orgchart(
            master_agent_id=master_agent_id,
            slave_agent_ids=slave_ids
        )
        
        # Complete
        active_workflows[workflow_id].update({
            "status": "completed",
            "current_phase": "completed",
            "progress_percentage": 100,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "ci_report_id": phase8_result.get("ci_report_id"),
            "learning_record_id": phase8_result.get("learning_record_id")
        })
        
        logger.info(f"✅ Workflow {workflow_id} completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Workflow {workflow_id} failed: {e}")
        active_workflows[workflow_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat()
        })


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "service": "Competitive Intelligence API",
        "version": "2.0.0"
    }


@app.post("/api/start-workflow")
async def start_workflow(request: StartWorkflowRequest, background_tasks: BackgroundTasks):
    """
    Start workflow pentru creare agenți slave și învățare competitivă
    """
    try:
        # Generate workflow ID
        workflow_id = str(ObjectId())
        
        # Add to background tasks
        background_tasks.add_task(
            run_workflow_background,
            workflow_id,
            request.site_url,
            request.results_per_keyword,
            request.parallel_gpu_agents
        )
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": "Workflow started successfully",
            "site_url": request.site_url
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflow-status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """
    Obține status-ul unui workflow
    """
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return active_workflows[workflow_id]


@app.get("/api/agents")
async def get_all_agents():
    """
    Lista tuturor agenților (master + slaves)
    """
    try:
        agents = list(db.site_agents.find(
            {"status": "validated"},
            {"_id": 1, "domain": 1, "site_url": 1, "agent_type": 1, 
             "chunks_indexed": 1, "has_embeddings": 1, "created_at": 1,
             "master_agent_id": 1, "discovered_via_keyword": 1, "serp_position": 1}
        ).sort("created_at", -1))
        
        # Convert ObjectId to string
        for agent in agents:
            agent["_id"] = str(agent["_id"])
            if "master_agent_id" in agent:
                agent["master_agent_id"] = str(agent["master_agent_id"])
        
        # Separate masters and slaves
        masters = [a for a in agents if a.get("agent_type") == "master"]
        slaves = [a for a in agents if a.get("agent_type") == "slave"]
        
        return {
            "total": len(agents),
            "masters": len(masters),
            "slaves": len(slaves),
            "agents": {
                "masters": masters,
                "slaves": slaves
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/{agent_id}")
async def get_agent_details(agent_id: str):
    """
    Detalii complete despre un agent
    """
    try:
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Convert ObjectId to string
        agent["_id"] = str(agent["_id"])
        if "master_agent_id" in agent:
            agent["master_agent_id"] = str(agent["master_agent_id"])
        
        return agent
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/master/{master_id}/slaves")
async def get_master_slaves(master_id: str):
    """
    Lista slaves pentru un master
    """
    try:
        # Get relationships
        relationships = list(db.master_slave_relationships.find({
            "master_id": ObjectId(master_id),
            "status": "active"
        }))
        
        slaves = []
        for rel in relationships:
            slave = db.site_agents.find_one({"_id": rel["slave_id"]})
            if slave:
                slave["_id"] = str(slave["_id"])
                slave["keyword"] = rel.get("discovered_via")
                slave["serp_position"] = rel.get("serp_position")
                slaves.append(slave)
        
        return {
            "master_id": master_id,
            "total_slaves": len(slaves),
            "slaves": slaves
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ci-report/{master_id}")
async def get_ci_report(master_id: str):
    """
    Raport Competitive Intelligence pentru master
    """
    try:
        # Get master
        master = db.site_agents.find_one({"_id": ObjectId(master_id)})
        if not master:
            raise HTTPException(status_code=404, detail="Master agent not found")
        
        # Get latest CI report
        report = db.competitive_intelligence_reports.find_one(
            {"master_agent.domain": master.get("domain")},
            sort=[("generated_at", -1)]
        )
        
        if not report:
            raise HTTPException(status_code=404, detail="No CI report found for this master")
        
        # Convert ObjectId to string
        report["_id"] = str(report["_id"])
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/orgchart/{master_id}")
async def get_orgchart(master_id: str):
    """
    Organogramă master-slave pentru vizualizare
    """
    try:
        # Get master
        master = db.site_agents.find_one({"_id": ObjectId(master_id)})
        if not master:
            raise HTTPException(status_code=404, detail="Master agent not found")
        
        # Get slaves
        relationships = list(db.master_slave_relationships.find({
            "master_id": ObjectId(master_id),
            "status": "active"
        }))
        
        slaves = []
        for rel in relationships:
            slave = db.site_agents.find_one({"_id": rel["slave_id"]})
            if slave:
                slaves.append({
                    "id": str(slave["_id"]),
                    "domain": slave.get("domain"),
                    "site_url": slave.get("site_url"),
                    "keyword": rel.get("discovered_via"),
                    "serp_position": rel.get("serp_position"),
                    "chunks": slave.get("chunks_indexed", 0)
                })
        
        # Create orgchart structure
        orgchart = {
            "master": {
                "id": str(master["_id"]),
                "domain": master.get("domain"),
                "site_url": master.get("site_url"),
                "chunks": master.get("chunks_indexed", 0),
                "type": "master"
            },
            "slaves": slaves,
            "total_slaves": len(slaves),
            "total_chunks": master.get("chunks_indexed", 0) + sum(s["chunks"] for s in slaves)
        }
        
        return orgchart
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_global_stats():
    """
    Statistici globale ale sistemului
    """
    try:
        total_agents = db.site_agents.count_documents({"status": "validated"})
        total_masters = db.site_agents.count_documents({"agent_type": "master"})
        total_slaves = db.site_agents.count_documents({"agent_type": "slave"})
        total_relationships = db.master_slave_relationships.count_documents({"status": "active"})
        total_reports = db.competitive_intelligence_reports.count_documents({})
        
        return {
            "total_agents": total_agents,
            "masters": total_masters,
            "slaves": total_slaves,
            "relationships": total_relationships,
            "ci_reports": total_reports,
            "active_workflows": len([w for w in active_workflows.values() if w.get("status") == "running"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001, log_level="info")

