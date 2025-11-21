#!/usr/bin/env python3
"""
🖥️ Node Controller
Verifică statusul nodurilor sistemului
"""

import requests
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# URLs
UI_BACKEND_URL = "http://127.0.0.1:5001"
ORCHESTRATOR_URL = "http://127.0.0.1:18001"


class NodeController:
    """Controller pentru verificarea statusului nodurilor"""
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obține statusul complet al sistemului"""
        status = {
            "timestamp": None,
            "ui_backend": {"online": False, "error": None},
            "orchestrator": {"online": False, "error": None},
            "gpu": {"available": False, "error": None},
            "mongodb": {"connected": False, "error": None},
            "qdrant": {"connected": False, "error": None}
        }
        
        # Verifică UI Backend
        try:
            response = requests.get(f"{UI_BACKEND_URL}/api/system/all", timeout=5)
            if response.status_code == 200:
                data = response.json()
                status["ui_backend"]["online"] = True
                status["ui_backend"]["data"] = data
            else:
                status["ui_backend"]["error"] = f"HTTP {response.status_code}"
        except Exception as e:
            status["ui_backend"]["error"] = str(e)
        
        # Verifică Orchestrator (dacă există)
        try:
            response = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=2)
            if response.status_code == 200:
                status["orchestrator"]["online"] = True
        except:
            status["orchestrator"]["error"] = "Not available"
        
        # Verifică GPU prin UI Backend
        try:
            response = requests.get(f"{UI_BACKEND_URL}/api/system/gpu", timeout=5)
            if response.status_code == 200:
                data = response.json()
                status["gpu"]["available"] = data.get("available", False)
                status["gpu"]["data"] = data
        except Exception as e:
            status["gpu"]["error"] = str(e)
        
        # Verifică MongoDB prin UI Backend
        try:
            response = requests.get(f"{UI_BACKEND_URL}/api/system/mongodb", timeout=5)
            if response.status_code == 200:
                data = response.json()
                status["mongodb"]["connected"] = data.get("connected", False)
                status["mongodb"]["data"] = data
        except Exception as e:
            status["mongodb"]["error"] = str(e)
        
        # Verifică Qdrant prin UI Backend
        try:
            response = requests.get(f"{UI_BACKEND_URL}/api/system/qdrant", timeout=5)
            if response.status_code == 200:
                data = response.json()
                status["qdrant"]["connected"] = data.get("connected", False)
                status["qdrant"]["data"] = data
        except Exception as e:
            status["qdrant"]["error"] = str(e)
        
        from datetime import datetime
        status["timestamp"] = datetime.now().isoformat()
        
        return status
    
    def format_status_message(self, status: Dict[str, Any]) -> str:
        """Formatează statusul într-un mesaj verbal"""
        parts = []
        
        if status["ui_backend"]["online"]:
            parts.append("UI Backend este online")
        else:
            parts.append("UI Backend este offline")
        
        if status["gpu"]["available"]:
            gpu_data = status["gpu"].get("data", {})
            count = gpu_data.get("count", 0)
            usage = gpu_data.get("total_memory_percent", 0)
            parts.append(f"GPU-uri: {count} disponibile, {usage}% folosit")
        else:
            parts.append("GPU-uri: indisponibile")
        
        if status["mongodb"]["connected"]:
            parts.append("MongoDB este conectat")
        else:
            parts.append("MongoDB este offline")
        
        if status["qdrant"]["connected"]:
            parts.append("Qdrant este conectat")
        else:
            parts.append("Qdrant este offline")
        
        return ". ".join(parts) + "."


# Singleton instance
_node_controller_instance = None

def get_node_controller() -> NodeController:
    """Get singleton instance"""
    global _node_controller_instance
    if _node_controller_instance is None:
        _node_controller_instance = NodeController()
    return _node_controller_instance


