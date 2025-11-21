#!/usr/bin/env python3
"""
🌐 Live Dashboard Backend - Real-time monitoring pentru toate nodurile AI
Rulează pe port 6000 cu WebSocket pentru updates în timp real
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from qdrant_client import QdrantClient
import psutil
import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# FastAPI app
app = FastAPI(title="Live AI Dashboard", description="Real-time monitoring pentru toate nodurile AI")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"✅ New WebSocket connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"❌ WebSocket disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "adbrain_ai"

def get_mongo_client():
    return MongoClient(MONGO_URI)

def get_mongo_collection():
    client = get_mongo_client()
    db = client[DB_NAME]
    return db.interactions

# Qdrant connection
def get_qdrant_client():
    ports = [9306, 6333]
    for port in ports:
        try:
            client = QdrantClient(host="127.0.0.1", port=port)
            client.get_collections()
            return client, port
        except:
            continue
    return None, None

# ==================== API ENDPOINTS ====================

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main dashboard HTML"""
    with open("/srv/hf/ai_agents/live_dashboard/static/control_center.html", "r") as f:
        return f.read()

@app.get("/monitor", response_class=HTMLResponse)
async def read_monitor():
    """Serve the monitoring dashboard"""
    with open("/srv/hf/ai_agents/live_dashboard/static/index.html", "r") as f:
        return f.read()

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ==================== NODE STATUS ENDPOINTS ====================

@app.get("/api/nodes/all")
async def get_all_nodes_status():
    """Obține statusul tuturor nodurilor într-un singur răspuns"""
    try:
        nodes = {
            "timestamp": datetime.now().isoformat(),
            "mongodb": await get_mongodb_node(),
            "qdrant": await get_qdrant_node(),
            "gpu": await get_gpu_node(),
            "vllm": await get_vllm_nodes(),
            "orchestrator": await get_orchestrator_node(),
            "master_agent": await get_master_agent_node(),
            "serp_app": await get_serp_app_node(),
            "ui_backend": await get_ui_backend_node(),
            "system": await get_system_node()
        }
        return nodes
    except Exception as e:
        logger.error(f"Error getting all nodes: {e}")
        return {"error": str(e)}

async def get_mongodb_node():
    """MongoDB node status"""
    try:
        client = get_mongo_client()
        client.admin.command('ping')
        db = client[DB_NAME]
        collection = db.interactions
        
        total = collection.count_documents({})
        today = collection.count_documents({
            "timestamp": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)}
        })
        
        return {
            "status": "online",
            "total_interactions": total,
            "today_interactions": today,
            "uri": MONGO_URI,
            "database": DB_NAME
        }
    except Exception as e:
        return {"status": "offline", "error": str(e)}

async def get_qdrant_node():
    """Qdrant node status"""
    try:
        client, port = get_qdrant_client()
        if not client:
            return {"status": "offline", "error": "No Qdrant instance found"}
        
        collections = client.get_collections().collections
        mem_auto_points = 0
        
        try:
            mem_auto = client.get_collection("mem_auto")
            mem_auto_points = mem_auto.points_count
        except:
            pass
        
        return {
            "status": "online",
            "port": port,
            "collections_count": len(collections),
            "mem_auto_points": mem_auto_points,
            "collections": [c.name for c in collections[:10]]  # First 10
        }
    except Exception as e:
        return {"status": "offline", "error": str(e)}

async def get_gpu_node():
    """GPU node status"""
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total',
                               '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            return {"status": "error", "error": "nvidia-smi failed"}
        
        gpus = []
        total_mem_used = 0
        total_mem_total = 0
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 6:
                mem_used = float(parts[4])
                mem_total = float(parts[5])
                total_mem_used += mem_used
                total_mem_total += mem_total
                
                gpus.append({
                    "index": parts[0],
                    "name": parts[1],
                    "temp": f"{parts[2]}°C",
                    "utilization": f"{parts[3]}%",
                    "memory_used": f"{mem_used:.0f}MB",
                    "memory_total": f"{mem_total:.0f}MB",
                    "memory_percent": round((mem_used / mem_total) * 100, 1) if mem_total > 0 else 0
                })
        
        total_percent = round((total_mem_used / total_mem_total) * 100, 1) if total_mem_total > 0 else 0
        
        return {
            "status": "online",
            "count": len(gpus),
            "gpus": gpus,
            "total_memory_used": f"{total_mem_used:.0f}MB",
            "total_memory_total": f"{total_mem_total:.0f}MB",
            "total_memory_percent": total_percent
        }
    except Exception as e:
        return {"status": "offline", "error": str(e)}

async def get_vllm_nodes():
    """vLLM nodes status (9201, 9400)"""
    nodes = {}
    ports = [9201, 9400]
    model_names = ["Qwen2.5-7B", "Qwen2.5-72B"]
    
    for port, model in zip(ports, model_names):
        try:
            resp = requests.get(f"http://localhost:{port}/v1/models", timeout=2)
            if resp.status_code == 200:
                nodes[str(port)] = {
                    "status": "online",
                    "port": port,
                    "model": model,
                    "url": f"http://localhost:{port}"
                }
            else:
                nodes[str(port)] = {"status": "error", "port": port, "model": model, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            nodes[str(port)] = {"status": "offline", "port": port, "model": model, "error": str(e)}
    
    return nodes

async def get_orchestrator_node():
    """LLM Orchestrator status"""
    try:
        # Check if orchestrator process is running
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            cmdline = proc.info.get('cmdline', [])
            if cmdline and 'llm_orchestrator' in ' '.join(cmdline):
                return {
                    "status": "online",
                    "pid": proc.info['pid'],
                    "path": "/srv/hf/ai_agents/llm_orchestrator.py"
                }
        
        # Check if file exists
        if os.path.exists("/srv/hf/ai_agents/llm_orchestrator.py"):
            return {"status": "idle", "path": "/srv/hf/ai_agents/llm_orchestrator.py"}
        
        return {"status": "missing"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def get_master_agent_node():
    """Master Agent status"""
    try:
        # Try any endpoint to see if server responds
        resp = requests.get("http://localhost:5010/api/chat", timeout=2)
        # Even if it returns 405 (Method Not Allowed), it means server is running
        if resp.status_code in [200, 404, 405, 422]:
            return {
                "status": "online",
                "port": 5010,
                "url": "http://localhost:5010"
            }
        else:
            return {"status": "error", "error": f"HTTP {resp.status_code}"}
    except:
        # Check if port is listening
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5010))
        sock.close()
        if result == 0:
            return {"status": "online", "port": 5010, "url": "http://localhost:5010"}
        
        return {"status": "offline"}

async def get_serp_app_node():
    """SERP Monitoring App status"""
    try:
        resp = requests.get("http://localhost:5000/api/serp/health", timeout=2)
        if resp.status_code == 200:
            return {
                "status": "online",
                "port": 5000,
                "url": "http://localhost:5000"
            }
        else:
            return {"status": "error", "error": f"HTTP {resp.status_code}"}
    except:
        # Check if port is listening
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()
        if result == 0:
            return {"status": "online", "port": 5000, "url": "http://localhost:5000"}
        return {"status": "offline"}

async def get_ui_backend_node():
    """Auto-learning UI Backend status"""
    try:
        # Try stats endpoint which we know exists
        resp = requests.get("http://localhost:5001/api/stats/interactions", timeout=2)
        if resp.status_code == 200:
            return {
                "status": "online",
                "port": 5001,
                "url": "http://localhost:5001"
            }
        else:
            return {"status": "error", "error": f"HTTP {resp.status_code}"}
    except:
        # Check if port is listening
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5001))
        sock.close()
        if result == 0:
            return {"status": "online", "port": 5001, "url": "http://localhost:5001"}
        return {"status": "offline"}

async def get_system_node():
    """System resource status"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "online",
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used": f"{memory.used / (1024**3):.1f}GB",
            "memory_total": f"{memory.total / (1024**3):.1f}GB",
            "disk_percent": disk.percent,
            "disk_used": f"{disk.used / (1024**3):.1f}GB",
            "disk_total": f"{disk.total / (1024**3):.1f}GB"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ==================== INTERACTIONS ENDPOINTS ====================

@app.get("/api/interactions/recent")
async def get_recent_interactions(limit: int = 50):
    """Obține ultimele interacțiuni"""
    try:
        collection = get_mongo_collection()
        interactions = list(collection.find(
            {"type": "interaction"},
            {"_id": 0, "prompt": 1, "response": 1, "provider": 1, "timestamp": 1, "tokens": 1}
        ).sort("timestamp", -1).limit(limit))
        
        # Convert datetime to string
        for interaction in interactions:
            if "timestamp" in interaction and isinstance(interaction["timestamp"], datetime):
                interaction["timestamp"] = interaction["timestamp"].isoformat()
        
        return {"interactions": interactions, "count": len(interactions)}
    except Exception as e:
        logger.error(f"Error getting recent interactions: {e}")
        return {"interactions": [], "count": 0, "error": str(e)}

@app.get("/api/interactions/stats")
async def get_interactions_stats():
    """Statistici despre interacțiuni"""
    try:
        collection = get_mongo_collection()
        
        # Total
        total = collection.count_documents({"type": "interaction"})
        
        # Today
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        today = collection.count_documents({
            "type": "interaction",
            "timestamp": {"$gte": today_start}
        })
        
        # By provider
        pipeline = [
            {"$match": {"type": "interaction"}},
            {"$group": {"_id": "$provider", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        by_provider = list(collection.aggregate(pipeline))
        
        # By hour (last 24h)
        last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        pipeline_hourly = [
            {"$match": {"type": "interaction", "timestamp": {"$gte": last_24h}}},
            {"$group": {
                "_id": {"$hour": "$timestamp"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        by_hour = list(collection.aggregate(pipeline_hourly))
        
        return {
            "total": total,
            "today": today,
            "by_provider": {item["_id"] or "unknown": item["count"] for item in by_provider},
            "by_hour": {item["_id"]: item["count"] for item in by_hour}
        }
    except Exception as e:
        logger.error(f"Error getting interaction stats: {e}")
        return {"error": str(e)}

# ==================== WEBSOCKET ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pentru live updates"""
    await manager.connect(websocket)
    
    try:
        # Send initial data
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Live Dashboard",
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive and send periodic updates
        while True:
            try:
                # Wait for messages from client (ping/pong)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
                
                # Send back a pong if client sent ping
                if data == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                
            except asyncio.TimeoutError:
                # Send periodic update even if no message received
                nodes_status = await get_all_nodes_status()
                await websocket.send_json({
                    "type": "update",
                    "data": nodes_status,
                    "timestamp": datetime.now().isoformat()
                })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# ==================== BACKGROUND TASKS ====================

async def broadcast_updates():
    """Broadcast periodic updates to all connected clients"""
    while True:
        try:
            await asyncio.sleep(5)  # Every 5 seconds
            
            if not manager.active_connections:
                continue
            
            # Get all nodes status
            nodes_status = await get_all_nodes_status()
            
            # Get recent interaction if any
            collection = get_mongo_collection()
            latest = collection.find_one(
                {"type": "interaction"},
                sort=[("timestamp", -1)]
            )
            
            message = {
                "type": "update",
                "nodes": nodes_status,
                "timestamp": datetime.now().isoformat()
            }
            
            if latest:
                if isinstance(latest.get("timestamp"), datetime):
                    latest["timestamp"] = latest["timestamp"].isoformat()
                message["latest_interaction"] = {
                    "prompt": latest.get("prompt", ""),
                    "response": latest.get("response", "")[:200] + "...",
                    "provider": latest.get("provider", "unknown"),
                    "timestamp": latest.get("timestamp")
                }
            
            await manager.broadcast(message)
            
        except Exception as e:
            logger.error(f"Error in broadcast_updates: {e}")

@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup"""
    logger.info("🚀 Starting Live Dashboard...")
    asyncio.create_task(broadcast_updates())

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Shutting down Live Dashboard...")

# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("LIVE_DASHBOARD_PORT", "6000"))
    
    logger.info(f"""
    ═══════════════════════════════════════════════════════════════
    🌐 LIVE DASHBOARD BACKEND
    ═══════════════════════════════════════════════════════════════
    Port: {port}
    WebSocket: ws://localhost:{port}/ws
    URL: http://localhost:{port}
    ═══════════════════════════════════════════════════════════════
    """)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )

