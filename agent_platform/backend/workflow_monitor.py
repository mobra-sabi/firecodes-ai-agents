#!/usr/bin/env python3
"""
📊 WORKFLOW MONITOR - Monitorizare în timp real a workflow-urilor
"""

from fastapi import APIRouter
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone
from typing import Dict, List, Any
import json

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

# MongoDB
mongo = MongoClient('mongodb://localhost:27017/')
db = mongo.ai_agents_db

@router.get("/logs/{agent_id}")
async def get_workflow_logs(agent_id: str, limit: int = 100):
    """Get workflow logs for an agent"""
    try:
        # Get agent
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            agent = db.agents.find_one({"_id": ObjectId(agent_id)})
        
        if not agent:
            return {"error": "Agent not found", "logs": []}
        
        # Get logs from workflow_logs collection
        logs = list(db.workflow_logs.find({
            "agent_id": ObjectId(agent_id)
        }).sort("timestamp", -1).limit(limit))
        
        result = []
        for log in logs:
            result.append({
                "timestamp": log.get("timestamp", ""),
                "phase": log.get("phase", ""),
                "message": log.get("message", ""),
                "status": log.get("status", "info"),
                "data": log.get("data", {})
            })
        
        return {"logs": result, "agent_id": agent_id}
    except Exception as e:
        return {"error": str(e), "logs": []}

@router.get("/progress/{agent_id}")
async def get_workflow_progress(agent_id: str):
    """Get current workflow progress for an agent"""
    try:
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            agent = db.agents.find_one({"_id": ObjectId(agent_id)})
        
        if not agent:
            return {"error": "Agent not found"}
        
        # Get latest workflow status
        workflow_status = db.workflow_status.find_one({
            "agent_id": ObjectId(agent_id)
        }, sort=[("timestamp", -1)])
        
        if not workflow_status:
            return {
                "agent_id": agent_id,
                "status": "not_started",
                "current_phase": 0,
                "total_phases": 8,
                "progress": 0,
                "message": "Workflow not started"
            }
        
        current_phase = workflow_status.get("current_phase", 0)
        total_phases = 8
        progress = (current_phase / total_phases) * 100
        
        return {
            "agent_id": agent_id,
            "status": workflow_status.get("status", "running"),
            "current_phase": current_phase,
            "total_phases": total_phases,
            "progress": round(progress, 1),
            "message": workflow_status.get("message", ""),
            "phase_details": workflow_status.get("phase_details", {}),
            "timestamp": workflow_status.get("timestamp", "")
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/reports/{agent_id}")
async def get_agent_reports(agent_id: str):
    """Get all reports for an agent"""
    try:
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            agent = db.agents.find_one({"_id": ObjectId(agent_id)})
        
        if not agent:
            return {"error": "Agent not found", "reports": []}
        
        domain = agent.get("domain", "")
        site_url = agent.get("site_url", "")
        
        # Get reports from reports collection
        reports = list(db.reports.find({
            "$or": [
                {"domain": domain},
                {"site_url": site_url},
                {"agent_id": ObjectId(agent_id)}
            ]
        }).sort("generated_at", -1))
        
        result = []
        for report in reports:
            result.append({
                "report_id": str(report["_id"]),
                "domain": report.get("domain", domain),
                "generated_at": report.get("generated_at", ""),
                "report_type": report.get("report_type", "ceo_workflow"),
                "phases_completed": report.get("phases_completed", []),
                "summary": report.get("summary", {})
            })
        
        return {"reports": result, "agent_id": agent_id}
    except Exception as e:
        return {"error": str(e), "reports": []}

