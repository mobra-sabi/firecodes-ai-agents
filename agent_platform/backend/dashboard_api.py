#!/usr/bin/env python3
"""
🎯 DASHBOARD API - Mini API pentru dashboard
Returnează date din MongoDB pentru dashboard
"""

import sys
sys.path.insert(0, '/srv/hf/ai_agents')

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone
import json

app = FastAPI(title="Dashboard API")

# Import report API
from report_api import router as report_router
app.include_router(report_router)

# Import workflow monitor
from workflow_monitor import router as workflow_router
app.include_router(workflow_router)

# Import SERP API (NEW!)
try:
    from serp_api_router import router as serp_router
    app.include_router(serp_router)
    print("✅ SERP API router loaded successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not load SERP API router: {e}")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB - Use MongoDB 8.0 on port 27017 (with real data)
mongo = MongoClient('mongodb://localhost:27017/')
db = mongo.ai_agents_db

# Serve static files
app.mount("/static", StaticFiles(directory="/srv/hf/ai_agents/static"), name="static")

# Helper function to convert ObjectId to string
def serialize_doc(doc):
    if doc:
        doc['_id'] = str(doc['_id'])
        if 'master_agent_id' in doc and doc['master_agent_id']:
            doc['master_agent_id'] = str(doc['master_agent_id'])
        if 'created_at' in doc and doc['created_at']:
            doc['created_at'] = doc['created_at'].isoformat() if hasattr(doc['created_at'], 'isoformat') else str(doc['created_at'])
    return doc

@app.get("/")
async def root():
    return {"message": "Dashboard API is running", "endpoints": ["/api/agents", "/api/stats"]}

@app.get("/api/agents")
async def get_agents():
    """Get all agents"""
    try:
        agents = list(db.site_agents.find({}).limit(200))
        agents = [serialize_doc(agent) for agent in agents]
        return agents
    except Exception as e:
        return {"error": str(e), "agents": []}

@app.get("/api/stats")
async def get_stats():
    """Get global statistics"""
    try:
        total_agents = db.site_agents.count_documents({})
        master_agents = db.site_agents.count_documents({"agent_type": "master"})
        slave_agents = db.site_agents.count_documents({"agent_type": "slave"})
        
        # Total chunks
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$chunks_indexed"}}}]
        chunks_result = list(db.site_agents.aggregate(pipeline))
        total_chunks = chunks_result[0]["total"] if chunks_result else 0
        
        # Total keywords
        total_keywords = 0
        for agent in db.site_agents.find({}):
            keywords = agent.get("keywords", [])
            if isinstance(keywords, list):
                total_keywords += len(keywords)
        
        return {
            "total_agents": total_agents,
            "master_agents": master_agents,
            "slave_agents": slave_agents,
            "total_chunks": total_chunks,
            "total_keywords": total_keywords,
            "reports": 0
        }
    except Exception as e:
        return {"error": str(e)}

# Frontend-compatible endpoints (without /api prefix)
@app.get("/stats")
async def get_stats_frontend():
    """Frontend-compatible stats endpoint - includes both collections"""
    try:
        # Count all agents from both collections
        total_agents = db.site_agents.count_documents({}) + db.agents.count_documents({})
        
        # Count masters - handle various formats
        master_agents = (
            db.site_agents.count_documents({"agent_type": "master"}) +
            db.agents.count_documents({
                "$and": [
                    {"agent_type": {"$ne": "slave"}},
                    {"agent_type": {"$ne": "competitor"}},
                    {"competitor": {"$ne": True}},
                    {"master_agent_id": {"$exists": False}},
                    {"parent_agent_id": {"$exists": False}}
                ]
            })
        )
        
        # Count slaves - include competitors
        slave_agents = (
            db.site_agents.count_documents({"agent_type": "slave"}) +
            db.agents.count_documents({
                "$or": [
                    {"agent_type": "slave"},
                    {"agent_type": "competitor"},
                    {"competitor": True},
                    {"master_agent_id": {"$exists": True}},
                    {"parent_agent_id": {"$exists": True}}
                ]
            })
        )
        
        # Total chunks - from both collections
        pipeline_site = [{"$group": {"_id": None, "total": {"$sum": "$chunks_indexed"}}}]
        chunks_site = list(db.site_agents.aggregate(pipeline_site))
        chunks_site_total = chunks_site[0]["total"] if chunks_site else 0
        
        pipeline_agents = [{"$group": {"_id": None, "total": {"$sum": "$chunks_indexed"}}}]
        chunks_agents = list(db.agents.aggregate(pipeline_agents))
        chunks_agents_total = chunks_agents[0]["total"] if chunks_agents else 0
        total_chunks = chunks_site_total + chunks_agents_total
        
        # Total keywords - calculate from all agents' keywords arrays (both collections)
        total_keywords = 0
        for agent in db.site_agents.find({}):
            keywords = agent.get("keywords", [])
            if isinstance(keywords, list):
                total_keywords += len(keywords)
        for agent in db.agents.find({}):
            keywords = agent.get("keywords", [])
            if isinstance(keywords, list):
                total_keywords += len(keywords)
        
        # Frontend expects: master_agents, slave_agents, total_agents, total_keywords, reports
        return {
            "master_agents": master_agents,
            "slave_agents": slave_agents,
            "total_agents": total_agents,
            "total_chunks": total_chunks,
            "total_keywords": total_keywords,
            "reports": 0
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/agents")
async def get_agents_frontend():
    """Frontend-compatible agents endpoint - returns ALL agents from both collections"""
    try:
        # Combine both collections - NO LIMIT, get all agents
        site_agents = list(db.site_agents.find({}))
        agents_list = list(db.agents.find({}))
        agents = site_agents + agents_list
        
        result = []
        for agent in agents:
            try:
                agent_id = agent["_id"]
                
                # Determine agent_type - handle various formats
                agent_type = agent.get("agent_type", "")
                if not agent_type or agent_type == "N/A":
                    # Try to infer from other fields
                    if agent.get("competitor") or agent.get("parent_agent_id") or agent.get("master_agent_id"):
                        agent_type = "slave"
                    else:
                        agent_type = "master"
                
                # Normalize agent_type
                if agent_type in ["competitor", "slave"]:
                    agent_type = "slave"
                elif agent_type not in ["master", "slave"]:
                    agent_type = "master"  # Default to master
                
                slave_count = 0
                if agent_type == "master":
                    # Count slaves from both collections
                    # site_agents uses master_agent_id
                    # agents uses parent_agent_id
                    slave_count = (
                        db.site_agents.count_documents({
                            "master_agent_id": agent_id,
                            "agent_type": "slave"
                        }) +
                        db.agents.count_documents({
                            "$and": [
                                {
                                    "$or": [
                                        {"master_agent_id": agent_id},
                                        {"parent_agent_id": agent_id}
                                    ]
                                },
                                {
                                    "$or": [
                                        {"agent_type": "slave"},
                                        {"agent_type": "competitor"},
                                        {"agent_type": {"$exists": False}}
                                    ]
                                }
                            ]
                        })
                    )
                
                keywords = agent.get("keywords", [])
                keyword_count = len(keywords) if isinstance(keywords, list) else 0
                
                # Get domain - try multiple fields
                domain = agent.get("domain", "")
                if not domain:
                    site_url = agent.get("site_url", "")
                    if site_url:
                        # Extract domain from URL
                        if "://" in site_url:
                            domain = site_url.split("//")[-1].split("/")[0]
                        else:
                            domain = site_url.split("/")[0]
                    else:
                        domain = str(agent_id)[:12]  # Fallback to ID
                
                # Get status - prioritize existing status
                status = agent.get("status", "")
                if not status or status in ["active", "N/A"]:
                    # Try to infer status from chunks
                    chunks = agent.get("chunks_indexed", 0)
                    if chunks > 0:
                        status = "ready"
                    else:
                        status = "created"
                
                # Normalize status
                if status in ["migrated", "ready"]:
                    status = "ready"
                elif status not in ["validated", "ready", "created"]:
                    status = "created"
                
                # Normalize created_at to ISO string
                created_at = agent.get("created_at", datetime.now(timezone.utc))
                if isinstance(created_at, datetime):
                    created_at_str = created_at.isoformat()
                elif isinstance(created_at, str):
                    created_at_str = created_at
                else:
                    created_at_str = datetime.now(timezone.utc).isoformat()
                
                result.append({
                    "_id": str(agent_id),
                    "domain": domain,
                    "site_url": agent.get("site_url", ""),
                    "agent_type": agent_type,
                    "industry": agent.get("industry", ""),
                    "status": status,
                    "created_at": created_at_str,
                    "chunks_indexed": agent.get("chunks_indexed", 0),
                    "keywords": keywords,
                    "keyword_count": keyword_count,
                    "slave_count": slave_count,
                })
            except Exception as e:
                # Skip agents that cause errors, but log them
                print(f"Error processing agent {agent.get('_id', 'unknown')}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Sort by created_at descending (newest first) - all are now strings
        result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return result
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc(), "agents": []}

@app.get("/api/workflow-progress")
async def get_workflow_progress():
    """Get current workflow progress"""
    try:
        # Hardcoded pentru daibau.ro workflow
        master_id = "6913cc489349b25c3690e9a3"
        
        slaves_created = db.site_agents.count_documents({
            "master_agent_id": ObjectId(master_id),
            "agent_type": "slave"
        })
        
        total_expected = 279
        percentage = (slaves_created / total_expected) * 100
        
        # Get last slave created
        last_slave = db.site_agents.find_one(
            {"master_agent_id": ObjectId(master_id), "agent_type": "slave"},
            sort=[("created_at", -1)]
        )
        
        return {
            "active": True,
            "master_domain": "daibau.ro",
            "slaves_created": slaves_created,
            "total_expected": total_expected,
            "percentage": round(percentage, 1),
            "eta_hours": round((total_expected - slaves_created) * 2 / 60, 1),
            "last_slave": serialize_doc(last_slave) if last_slave else None
        }
    except Exception as e:
        return {"error": str(e), "active": False}

# Frontend-compatible endpoints (without /api prefix)
@app.get("/stats")
async def get_stats_frontend():
    """Frontend-compatible stats endpoint - includes both collections"""
    try:
        # Count all agents from both collections
        total_agents = db.site_agents.count_documents({}) + db.agents.count_documents({})
        
        # Count masters - handle various formats
        master_agents = (
            db.site_agents.count_documents({"agent_type": "master"}) +
            db.agents.count_documents({
                "$and": [
                    {"agent_type": {"$ne": "slave"}},
                    {"agent_type": {"$ne": "competitor"}},
                    {"competitor": {"$ne": True}},
                    {"master_agent_id": {"$exists": False}}
                ]
            })
        )
        
        # Count slaves - include competitors
        slave_agents = (
            db.site_agents.count_documents({"agent_type": "slave"}) +
            db.agents.count_documents({
                "$or": [
                    {"agent_type": "slave"},
                    {"agent_type": "competitor"},
                    {"competitor": True},
                    {"master_agent_id": {"$exists": True}}
                ]
            })
        )
        
        # Total chunks - from both collections
        pipeline_site = [{"$group": {"_id": None, "total": {"$sum": "$chunks_indexed"}}}]
        chunks_site = list(db.site_agents.aggregate(pipeline_site))
        chunks_site_total = chunks_site[0]["total"] if chunks_site else 0
        
        pipeline_agents = [{"$group": {"_id": None, "total": {"$sum": "$chunks_indexed"}}}]
        chunks_agents = list(db.agents.aggregate(pipeline_agents))
        chunks_agents_total = chunks_agents[0]["total"] if chunks_agents else 0
        total_chunks = chunks_site_total + chunks_agents_total
        
        # Total keywords - calculate from all agents' keywords arrays (both collections)
        total_keywords = 0
        for agent in db.site_agents.find({}):
            keywords = agent.get("keywords", [])
            if isinstance(keywords, list):
                total_keywords += len(keywords)
        for agent in db.agents.find({}):
            keywords = agent.get("keywords", [])
            if isinstance(keywords, list):
                total_keywords += len(keywords)
        
        # Frontend expects: master_agents, slave_agents, total_agents, total_keywords, reports
        return {
            "master_agents": master_agents,
            "slave_agents": slave_agents,
            "total_agents": total_agents,
            "total_chunks": total_chunks,
            "total_keywords": total_keywords,
            "reports": 0
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/agents")
async def get_agents_frontend():
    """Frontend-compatible agents endpoint - returns ALL agents from both collections"""
    try:
        # Combine both collections - NO LIMIT, get all agents
        site_agents = list(db.site_agents.find({}))
        agents_list = list(db.agents.find({}))
        agents = site_agents + agents_list
        
        result = []
        for agent in agents:
            try:
                agent_id = agent["_id"]
                
                # Determine agent_type - handle various formats
                agent_type = agent.get("agent_type", "")
                if not agent_type or agent_type == "N/A":
                    # Try to infer from other fields
                    if agent.get("competitor") or agent.get("parent_agent_id") or agent.get("master_agent_id"):
                        agent_type = "slave"
                    else:
                        agent_type = "master"
                
                # Normalize agent_type
                if agent_type in ["competitor", "slave"]:
                    agent_type = "slave"
                elif agent_type not in ["master", "slave"]:
                    agent_type = "master"  # Default to master
                
                slave_count = 0
                if agent_type == "master":
                    # Count slaves from both collections
                    # site_agents uses master_agent_id
                    # agents uses parent_agent_id
                    slave_count = (
                        db.site_agents.count_documents({
                            "master_agent_id": agent_id,
                            "agent_type": "slave"
                        }) +
                        db.agents.count_documents({
                            "$and": [
                                {
                                    "$or": [
                                        {"master_agent_id": agent_id},
                                        {"parent_agent_id": agent_id}
                                    ]
                                },
                                {
                                    "$or": [
                                        {"agent_type": "slave"},
                                        {"agent_type": "competitor"},
                                        {"agent_type": {"$exists": False}}
                                    ]
                                }
                            ]
                        })
                    )
                
                keywords = agent.get("keywords", [])
                keyword_count = len(keywords) if isinstance(keywords, list) else 0
                
                # Get domain - try multiple fields
                domain = agent.get("domain", "")
                if not domain:
                    site_url = agent.get("site_url", "")
                    if site_url:
                        # Extract domain from URL
                        if "://" in site_url:
                            domain = site_url.split("//")[-1].split("/")[0]
                        else:
                            domain = site_url.split("/")[0]
                    else:
                        domain = str(agent_id)[:12]  # Fallback to ID
                
                # Get status - prioritize existing status
                status = agent.get("status", "")
                if not status or status in ["active", "N/A"]:
                    # Try to infer status from chunks
                    chunks = agent.get("chunks_indexed", 0)
                    if chunks > 0:
                        status = "ready"
                    else:
                        status = "created"
                
                # Normalize status
                if status in ["migrated", "ready"]:
                    status = "ready"
                elif status not in ["validated", "ready", "created"]:
                    status = "created"
                
                # Normalize created_at to ISO string
                created_at = agent.get("created_at", datetime.now(timezone.utc))
                if isinstance(created_at, datetime):
                    created_at_str = created_at.isoformat()
                elif isinstance(created_at, str):
                    created_at_str = created_at
                else:
                    created_at_str = datetime.now(timezone.utc).isoformat()
                
                result.append({
                    "_id": str(agent_id),
                    "domain": domain,
                    "site_url": agent.get("site_url", ""),
                    "agent_type": agent_type,
                    "industry": agent.get("industry", ""),
                    "status": status,
                    "created_at": created_at_str,
                    "chunks_indexed": agent.get("chunks_indexed", 0),
                    "keywords": keywords,
                    "keyword_count": keyword_count,
                    "slave_count": slave_count,
                })
            except Exception as e:
                # Skip agents that cause errors, but log them
                print(f"Error processing agent {agent.get('_id', 'unknown')}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Sort by created_at descending (newest first) - all are now strings
        result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return result
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc(), "agents": []}

@app.get("/agents/{agent_id}")
async def get_agent_detail(agent_id: str):
    """Get single agent details - search in both collections"""
    try:
        # Try site_agents first
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            # Try agents collection
            agent = db.agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"error": "Agent not found"}
        return serialize_doc(agent)
    except Exception as e:
        return {"error": str(e)}

@app.get("/agents/{agent_id}/slaves")
async def get_agent_slaves(agent_id: str):
    """Get slaves for a master agent - search in both collections"""
    try:
        master_id = ObjectId(agent_id)
        
        # Get slaves from both collections
        slaves_site = list(db.site_agents.find({
            "master_agent_id": master_id,
            "agent_type": "slave"
        }))
        
        slaves_agents = list(db.agents.find({
            "$and": [
                {
                    "$or": [
                        {"master_agent_id": master_id},
                        {"parent_agent_id": master_id}
                    ]
                },
                {
                    "$or": [
                        {"agent_type": "slave"},
                        {"agent_type": "competitor"},
                        {"agent_type": {"$exists": False}}
                    ]
                }
            ]
        }))
        
        slaves = slaves_site + slaves_agents
        return [serialize_doc(slave) for slave in slaves]
    except Exception as e:
        return {"error": str(e)}

@app.post("/agents")
async def create_agent(request: Request):
    """Create a new master agent"""
    try:
        from urllib.parse import urlparse
        from datetime import datetime, timezone
        
        body = await request.json()
        site_url = body.get("site_url", "").strip()
        if not site_url:
            return {"error": "site_url is required"}
        
        # Validate URL
        try:
            parsed = urlparse(site_url if site_url.startswith("http") else f"https://{site_url}")
            domain = parsed.netloc or parsed.path.split("/")[0]
        except:
            return {"error": "Invalid URL format"}
        
        # Check if agent already exists
        existing = db.site_agents.find_one({"site_url": site_url})
        if existing:
            return {"error": "Agent already exists", "agent_id": str(existing["_id"])}
        
        # Create agent document
        agent_doc = {
            "domain": domain,
            "site_url": site_url,
            "agent_type": "master",
            "status": "created",
            "created_at": datetime.now(timezone.utc),
            "chunks_indexed": 0,
            "keywords": [],
        }
        
        result = db.site_agents.insert_one(agent_doc)
        agent_id = result.inserted_id
        
        # Start workflow in background (Phase 1-3)
        import subprocess
        import os
        workflow_script = "/srv/hf/ai_agents/agent_platform/backend/ceo_master_workflow.py"
        if os.path.exists(workflow_script):
            subprocess.Popen([
                "python3", workflow_script, site_url
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return {
            "success": True,
            "agent_id": str(agent_id),
            "message": "Agent created. Workflow started in background."
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/workflow/start")
async def start_workflow(request: Request):
    """Start CEO workflow for an existing master agent"""
    try:
        body = await request.json()
        agent_id = body.get("agent_id")
        if not agent_id:
            return {"error": "agent_id is required"}
        
        # Get agent
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"error": "Agent not found"}
        
        if agent.get("agent_type") != "master":
            return {"error": "Workflow can only be started for master agents"}
        
        site_url = agent.get("site_url")
        if not site_url:
            return {"error": "Agent missing site_url"}
        
        # Start workflow in background (Phase 4-8)
        import subprocess
        import os
        workflow_script = "/srv/hf/ai_agents/agent_platform/backend/ceo_master_workflow.py"
        if os.path.exists(workflow_script):
            subprocess.Popen([
                "python3", workflow_script, site_url, "--phases", "4-8"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {
                "success": True,
                "message": "CEO Workflow started. Check progress in agent details."
            }
        else:
            return {"error": "Workflow script not found"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Dashboard API on port 5000...")
    print("📊 Endpoints:")
    print("   GET  /api/agents")
    print("   GET  /api/stats")
    print("   GET  /api/workflow-progress")
    print("   Static files: /static/*")
    uvicorn.run(app, host="0.0.0.0", port=5000)

