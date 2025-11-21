#!/usr/bin/env python3
"""
🎯 DASHBOARD API - Mini API pentru dashboard
Returnează date din MongoDB pentru dashboard
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone
import json

app = FastAPI(title="Dashboard API")

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
        
        return {
            "total_agents": total_agents,
            "master_agents": master_agents,
            "slave_agents": slave_agents,
            "total_chunks": total_chunks
        }
    except Exception as e:
        return {"error": str(e)}

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
    """Frontend-compatible stats endpoint"""
    try:
        # Include both 'agents' and 'site_agents' collections
        total_agents = db.site_agents.count_documents({}) + db.agents.count_documents({})
        master_agents = db.site_agents.count_documents({"agent_type": "master"}) + db.agents.count_documents({"agent_type": "master"})
        slave_agents = db.site_agents.count_documents({"agent_type": "slave"}) + db.agents.count_documents({"agent_type": "slave"})
        
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
            "total_keywords": total_keywords,
            "reports": 0
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/agents")
async def get_agents_frontend():
    """Frontend-compatible agents endpoint"""
    try:
        # Combine both collections
        site_agents = list(db.site_agents.find({}))
        agents_list = list(db.agents.find({}))
        agents = site_agents + agents_list
        result = []
        for agent in agents:
            agent_id = agent["_id"]
            slave_count = 0
            if agent.get("agent_type") == "master":
                slave_count = db.site_agents.count_documents({
                    "master_agent_id": agent_id,
                    "agent_type": "slave"
                })
            
            keywords = agent.get("keywords", [])
            keyword_count = len(keywords) if isinstance(keywords, list) else 0
            
            result.append({
                "_id": str(agent_id),
                "domain": agent.get("domain", ""),
                "site_url": agent.get("site_url", ""),
                "agent_type": agent.get("agent_type", "master"),
                "industry": agent.get("industry", ""),
                "status": agent.get("status", "active"),
                "created_at": agent.get("created_at", datetime.now(timezone.utc).isoformat()),
                "chunks_indexed": agent.get("chunks_indexed", 0),
                "keywords": keywords,
                "keyword_count": keyword_count,
                "slave_count": slave_count,
            })
        return result
    except Exception as e:
        return {"error": str(e), "agents": []}

@app.get("/agents/{agent_id}")
async def get_agent_detail(agent_id: str):
    """Get single agent details"""
    try:
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"error": "Agent not found"}
        return serialize_doc(agent)
    except Exception as e:
        return {"error": str(e)}

@app.get("/agents/{agent_id}/slaves")
async def get_agent_slaves(agent_id: str):
    """Get slaves for a master agent"""
    try:
        slaves = list(db.site_agents.find({
            "master_agent_id": ObjectId(agent_id),
            "agent_type": "slave"
        }))
        return [serialize_doc(slave) for slave in slaves]
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

