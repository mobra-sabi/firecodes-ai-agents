#!/usr/bin/env python3
"""
🎨 Backend API pentru UI Auto-Learning Dashboard
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
import subprocess
import json
import os
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Auto-Learning Dashboard API")

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "adbrain_ai")

def get_mongo_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]


@app.get("/api/stats/interactions")
async def get_interaction_stats():
    """Statistici interacțiuni"""
    try:
        db = get_mongo_db()
        collection = db.interactions
        
        total = collection.count_documents({})
        today = collection.count_documents({
            "timestamp": {"$gte": datetime.now() - timedelta(days=1)}
        })
        by_provider = list(collection.aggregate([
            {"$group": {"_id": "$provider", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]))
        by_topic = list(collection.aggregate([
            {"$group": {"_id": "$topic", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]))
        
        return {
            "total": total,
            "today": today,
            "by_provider": {item["_id"]: item["count"] for item in by_provider},
            "by_topic": {item["_id"]: item["count"] for item in by_topic}
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/interactions")
async def get_interactions(limit: int = 50, skip: int = 0):
    """Lista interacțiuni"""
    try:
        db = get_mongo_db()
        collection = db.interactions
        
        interactions = list(
            collection.find()
            .sort("timestamp", -1)
            .skip(skip)
            .limit(limit)
        )
        
        # Convert ObjectId to string
        for item in interactions:
            item["_id"] = str(item["_id"])
            if isinstance(item.get("timestamp"), datetime):
                item["timestamp"] = item["timestamp"].isoformat()
        
        return {"interactions": interactions, "total": collection.count_documents({})}
    except Exception as e:
        logger.error(f"Error getting interactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dataset/status")
async def get_dataset_status():
    """Status dataset JSONL"""
    try:
        jsonl_path = "/srv/hf/ai_agents/datasets/training_data.jsonl"
        
        if not os.path.exists(jsonl_path):
            return {
                "exists": False,
                "size": 0,
                "lines": 0,
                "last_modified": None
            }
        
        stat = os.stat(jsonl_path)
        with open(jsonl_path, "r") as f:
            lines = sum(1 for _ in f)
        
        return {
            "exists": True,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "lines": lines,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting dataset status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/finetuning/status")
async def get_finetuning_status():
    """Status fine-tuning"""
    try:
        output_dir = "/srv/hf/ai_agents/fine_tuning/output"
        log_dir = "/srv/hf/ai_agents/logs"
        
        model_exists = os.path.exists(output_dir) and os.listdir(output_dir)
        
        # Găsește ultimul log
        latest_log = None
        if os.path.exists(log_dir):
            log_files = [f for f in os.listdir(log_dir) if f.startswith("fine_tune_")]
            if log_files:
                latest_log = max(log_files, key=lambda f: os.path.getmtime(os.path.join(log_dir, f)))
        
        return {
            "model_exists": model_exists,
            "output_dir": output_dir,
            "latest_log": latest_log,
            "log_path": os.path.join(log_dir, latest_log) if latest_log else None
        }
    except Exception as e:
        logger.error(f"Error getting finetuning status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/qdrant/status")
async def get_qdrant_status():
    """Status Qdrant collection"""
    try:
        import requests
        
        # Încearcă pe ambele porturi
        for port in [6333, 9306]:
            try:
                response = requests.get(f"http://127.0.0.1:{port}/collections/mem_auto", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "connected": True,
                        "port": port,
                        "points_count": data.get("result", {}).get("points_count", 0),
                        "vectors_count": data.get("result", {}).get("vectors_count", 0),
                        "config": data.get("result", {}).get("config", {})
                    }
            except:
                continue
        
        return {"connected": False, "error": "Not reachable on ports 6333 or 9306"}
    except Exception as e:
        return {"connected": False, "error": str(e)}


@app.post("/api/actions/build_jsonl")
async def action_build_jsonl():
    """Acțiune: Build JSONL"""
    try:
        result = subprocess.run(
            ["python3", "/srv/hf/ai_agents/fine_tuning/build_jsonl.py"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/actions/train")
async def action_train():
    """Acțiune: Start fine-tuning"""
    try:
        result = subprocess.Popen(
            ["bash", "/srv/hf/ai_agents/fine_tuning/train_qwen.sh"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return {
            "success": True,
            "pid": result.pid,
            "message": "Fine-tuning started in background"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/actions/update_qdrant")
async def action_update_qdrant():
    """Acțiune: Update Qdrant"""
    try:
        result = subprocess.run(
            ["python3", "/srv/hf/ai_agents/rag_updater/update_qdrant.py"],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/actions/test_orchestrator")
async def action_test_orchestrator():
    """Acțiune: Test orchestrator (generează interacțiune)"""
    try:
        import sys
        sys.path.insert(0, "/srv/hf/ai_agents")
        from llm_orchestrator import get_orchestrator
        
        orch = get_orchestrator()
        result = orch.chat([
            {"role": "user", "content": "Explică în 2 propoziții ce este protecția anticorozivă."}
        ])
        
        return {
            "success": result.get("success", False),
            "provider": result.get("provider", "unknown"),
            "response": result.get("content", "")[:200],
            "tokens": result.get("tokens", 0)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/orchestrator/stats")
async def get_orchestrator_stats():
    """Statistici orchestrator"""
    try:
        import sys
        sys.path.insert(0, "/srv/hf/ai_agents")
        from llm_orchestrator import get_orchestrator
        
        orch = get_orchestrator()
        stats = orch.get_stats()
        
        return stats
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/system/processes")
async def get_system_processes():
    """Lista toate procesele relevante din aplicație"""
    try:
        import psutil
        
        processes = []
        relevant_keywords = [
            "uvicorn", "serp", "scheduler", "python", "mongod", "qdrant",
            "agent_api", "dashboard_api", "backend_api", "vllm", "qwen"
        ]
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent', 'status']):
            try:
                pinfo = proc.info
                cmdline = ' '.join(pinfo.get('cmdline', [])) if pinfo.get('cmdline') else ''
                
                # Verifică dacă procesul este relevant
                is_relevant = any(keyword.lower() in cmdline.lower() or keyword.lower() in pinfo.get('name', '').lower() 
                                 for keyword in relevant_keywords)
                
                if is_relevant:
                    processes.append({
                        "pid": pinfo['pid'],
                        "name": pinfo['name'],
                        "cmdline": cmdline[:200],  # Trunchiază pentru UI
                        "cpu": round(pinfo.get('cpu_percent', 0), 1),
                        "memory": round(pinfo.get('memory_percent', 0), 1),
                        "status": pinfo.get('status', 'unknown')
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sortează după CPU
        processes.sort(key=lambda x: x['cpu'], reverse=True)
        
        return {"processes": processes, "count": len(processes)}
    except ImportError:
        # Fallback dacă psutil nu e instalat
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            processes = []
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 11:
                    cmd = ' '.join(parts[10:])
                    if any(kw in cmd.lower() for kw in ["uvicorn", "serp", "scheduler", "mongod", "qdrant", "python", "vllm"]):
                        processes.append({
                            "pid": parts[1],
                            "cpu": parts[2],
                            "memory": parts[3],
                            "cmdline": cmd[:200]
                        })
            
            return {"processes": processes, "count": len(processes)}
        except Exception as e:
            return {"error": str(e), "processes": []}
    except Exception as e:
        return {"error": str(e), "processes": []}


@app.get("/api/system/mongodb")
async def get_mongodb_status():
    """Status MongoDB"""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.server_info()  # Test connection
        
        db = client[DB_NAME]
        stats = db.command("dbStats")
        
        collections = db.list_collection_names()
        
        # Count documents per collection
        collection_counts = {}
        for coll_name in collections[:10]:  # Primele 10
            try:
                collection_counts[coll_name] = db[coll_name].count_documents({})
            except:
                pass
        
        return {
            "connected": True,
            "database": DB_NAME,
            "collections": len(collections),
            "collections_list": collections[:20],
            "collection_counts": collection_counts,
            "data_size": stats.get("dataSize", 0),
            "storage_size": stats.get("storageSize", 0)
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}


@app.get("/api/system/qdrant")
async def get_qdrant_full_status():
    """Status complet Qdrant"""
    try:
        import requests
        
        # Încearcă mai întâi pe port 6333, apoi 9306 (Docker mapping)
        ports_to_try = [6333, 9306]
        qdrant_url = None
        working_port = None
        
        for port in ports_to_try:
            try:
                test_resp = requests.get(f"http://127.0.0.1:{port}/collections", timeout=2)
                if test_resp.status_code == 200:
                    qdrant_url = f"http://127.0.0.1:{port}"
                    working_port = port
                    break
            except:
                continue
        
        if not qdrant_url:
            return {"connected": False, "error": "Qdrant not reachable on ports 6333 or 9306"}
        
        # Collections list
        collections_resp = requests.get(f"{qdrant_url}/collections", timeout=5)
        collections_data = collections_resp.json() if collections_resp.status_code == 200 else {}
        
        # mem_auto collection details
        mem_auto_resp = requests.get(f"{qdrant_url}/collections/mem_auto", timeout=5)
        mem_auto_data = mem_auto_resp.json() if mem_auto_resp.status_code == 200 else {}
        
        return {
            "connected": True,
            "port": working_port,
            "collections": collections_data.get("result", {}).get("collections", []),
            "mem_auto": {
                "points_count": mem_auto_data.get("result", {}).get("points_count", 0),
                "vectors_count": mem_auto_data.get("result", {}).get("vectors_count", 0),
                "config": mem_auto_data.get("result", {}).get("config", {})
            }
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}


@app.get("/api/system/gpu")
async def get_gpu_status():
    """Status GPU-uri"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            gpus = []
            total_mem_used = 0
            total_mem = 0
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 6:
                        mem_used = int(parts[2])
                        mem_total = int(parts[3])
                        total_mem_used += mem_used
                        total_mem += mem_total
                        gpus.append({
                            "index": parts[0],
                            "name": parts[1],
                            "memory_used": parts[2],
                            "memory_total": parts[3],
                            "utilization": parts[4],
                            "temperature": parts[5],
                            "memory_percent": round((mem_used / mem_total) * 100, 1) if mem_total > 0 else 0
                        })
            return {
                "available": True,
                "gpus": gpus,
                "count": len(gpus),
                "total_memory_used": total_mem_used,
                "total_memory": total_mem,
                "total_memory_percent": round((total_mem_used / total_mem) * 100, 1) if total_mem > 0 else 0
            }
        else:
            return {"available": False, "error": "nvidia-smi failed"}
    except FileNotFoundError:
        return {"available": False, "error": "nvidia-smi not found"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.get("/api/system/vllm")
async def get_vllm_status():
    """Status vLLM services"""
    try:
        import requests
        
        vllm_ports = {
            9201: "Qwen 7B",
            9400: "Qwen 72B",
            9301: "Alternative"
        }
        
        status = {}
        for port, name in vllm_ports.items():
            try:
                resp = requests.get(f"http://localhost:{port}/v1/models", timeout=2)
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("data", [])
                    status[port] = {
                        "online": True,
                        "name": name,
                        "models": [m.get("id") for m in models],
                        "model_count": len(models)
                    }
                else:
                    status[port] = {"online": False, "name": name, "error": f"HTTP {resp.status_code}"}
            except Exception as e:
                status[port] = {"online": False, "name": name, "error": str(e)[:100]}
        
        # Check systemd service
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "vllm@qwen2.5-7b.service"],
                capture_output=True,
                text=True,
                timeout=2
            )
            service_active = result.stdout.strip() == "active"
        except:
            service_active = False
        
        return {
            "services": status,
            "systemd_active": service_active,
            "service_name": "vllm@qwen2.5-7b.service"
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/system/serp_app")
async def get_serp_app_status():
    """Status aplicație SERP Monitoring"""
    try:
        import requests
        
        # Check SERP API health
        health_resp = requests.get("http://localhost:5000/api/serp/health", timeout=2)
        health_ok = health_resp.status_code == 200
        
        # Check scheduler process
        scheduler_running = False
        try:
            result = subprocess.run(
                ["pgrep", "-f", "serp_scheduler"],
                capture_output=True,
                timeout=2
            )
            scheduler_running = result.returncode == 0
        except:
            pass
        
        return {
            "api_running": health_ok,
            "api_port": 5000,
            "scheduler_running": scheduler_running,
            "dashboard_url": "http://localhost:5000/static/serp_admin.html"
        }
    except Exception as e:
        return {"api_running": False, "error": str(e)}


@app.get("/api/system/ports")
async def get_ports_status():
    """Status porturi folosite"""
    try:
        import socket
        
        ports_to_check = {
            5000: "SERP API",
            5001: "Auto-Learning UI",
            6333: "Qdrant (native)",
            9306: "Qdrant (Docker)",
            8000: "Agent API",
            9201: "vLLM Qwen 7B",
            9400: "Qwen vLLM 72B",
            27017: "MongoDB"
        }
        
        port_status = {}
        for port, name in ports_to_check.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            port_status[port] = {
                "name": name,
                "open": result == 0
            }
        
        return {"ports": port_status}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/system/diagnostic")
async def get_system_diagnostic():
    """Diagnostic complet al sistemului"""
    try:
        diagnostic = {
            "timestamp": datetime.now().isoformat(),
            "gpu": await get_gpu_status(),
            "vllm": await get_vllm_status(),
            "mongodb": await get_mongodb_status(),
            "qdrant": await get_qdrant_full_status(),
            "serp_app": await get_serp_app_status(),
            "ports": await get_ports_status(),
            "orchestrator": await get_orchestrator_stats()
        }
        
        # Salvează diagnosticul pentru învățare
        try:
            import sys
            sys.path.insert(0, "/srv/hf/ai_agents")
            from data_collector.collector import save_diagnostic
            save_diagnostic(
                diagnostic_type="system_full",
                data=diagnostic,
                metadata={"source": "ui_dashboard"}
            )
        except Exception as e:
            logger.warning(f"Failed to save diagnostic: {e}")
        
        # Adaugă recomandări
        recommendations = []
        
        if not diagnostic["vllm"].get("services", {}).get("9201", {}).get("online"):
            recommendations.append("⚠️ vLLM pe port 9201 nu răspunde - verifică: systemctl status vllm@qwen2.5-7b")
        
        if not diagnostic["qdrant"].get("connected"):
            recommendations.append("⚠️ Qdrant offline - verifică: docker ps | grep qdrant")
        
        gpu_usage = diagnostic["gpu"].get("total_memory_percent", 0)
        if gpu_usage < 5:
            recommendations.append(f"⚠️ GPU-uri aproape nefolosite ({gpu_usage}%) - vLLM nu pornește corect")
        
        if diagnostic["orchestrator"].get("total_calls", 0) == 0:
            recommendations.append("💡 Orchestratorul nu a făcut niciun call - testează din UI")
        
        diagnostic["recommendations"] = recommendations
        
        return diagnostic
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/actions/process_learning")
async def action_process_learning():
    """Acțiune: Procesează date pentru învățare continuă"""
    try:
        import sys
        sys.path.insert(0, "/srv/hf/ai_agents")
        from learning_loop.continuous_learner import get_continuous_learner
        
        learner = get_continuous_learner()
        stats = learner.process_for_learning(limit=100)
        
        return {
            "success": True,
            "stats": stats,
            "message": f"Processed {stats.get('processed', 0)} documents for learning"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/actions/query_qwen_local")
async def action_query_qwen_local(request: Dict[str, Any]):
    """Acțiune: Trimite query către Qwen local pentru învățare"""
    try:
        import sys
        sys.path.insert(0, "/srv/hf/ai_agents")
        from learning_loop.continuous_learner import get_continuous_learner
        
        learner = get_continuous_learner()
        prompt = request.get("prompt", "")
        context = request.get("context", {})
        
        result = learner.send_to_qwen_local(
            prompt=prompt,
            context=context,
            use_learning_mode=True
        )
        
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/system/all")
async def get_all_system_status():
    """Status complet al tuturor nodurilor"""
    try:
        processes = await get_system_processes()
        mongodb = await get_mongodb_status()
        qdrant = await get_qdrant_full_status()
        gpu = await get_gpu_status()
        serp = await get_serp_app_status()
        ports = await get_ports_status()
        vllm = await get_vllm_status()
        
        return {
            "processes": processes,
            "mongodb": mongodb,
            "qdrant": qdrant,
            "gpu": gpu,
            "serp_app": serp,
            "ports": ports,
            "vllm": vllm,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve dashboard HTML"""
    dashboard_path = os.path.join(os.path.dirname(__file__), "static", "dashboard.html")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/agents/learning-stats")
async def get_all_agents_learning_stats():
    """Get learning stats for all agents"""
    try:
        import sys
        sys.path.insert(0, "/srv/hf/ai_agents")
        from data_collector.collector import get_agent_stats
        from pymongo import MongoClient
        
        # Get all agents
        client = MongoClient("mongodb://localhost:27017/")
        db = client.ai_agents_db
        agents = list(db.site_agents.find({}, {"_id": 1, "domain": 1}))
        
        stats = []
        for agent in agents:
            agent_id = str(agent["_id"])
            agent_stats = get_agent_stats(agent_id)
            agent_stats["domain"] = agent.get("domain", "unknown")
            stats.append(agent_stats)
        
        return {"agents": stats, "total": len(stats)}
    except Exception as e:
        return {"error": str(e), "agents": [], "total": 0}


@app.get("/api/agent/{agent_id}/learning-stats")
async def get_agent_learning_stats(agent_id: str):
    """Get learning statistics for specific agent"""
    try:
        import sys
        sys.path.insert(0, "/srv/hf/ai_agents")
        from data_collector.collector import get_agent_stats, get_agent_interactions
        
        stats = get_agent_stats(agent_id)
        recent = get_agent_interactions(agent_id, limit=5)
        
        # Convert ObjectId and datetime to string
        for interaction in recent:
            if "_id" in interaction:
                interaction["_id"] = str(interaction["_id"])
            if "timestamp" in interaction:
                interaction["timestamp"] = interaction["timestamp"].isoformat() if hasattr(interaction["timestamp"], "isoformat") else str(interaction["timestamp"])
        
        stats["recent_interactions"] = recent
        
        return stats
    except Exception as e:
        return {"error": str(e), "agent_id": agent_id}
