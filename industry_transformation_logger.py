"""
📝 Industry Transformation Logger
==================================

Sistem de logging pentru transformarea industriei
Salvează logs în MongoDB pentru afișare live în UI
"""

import logging
from datetime import datetime, timezone
from pymongo import MongoClient
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class IndustryTransformationLogger:
    """Logger pentru transformarea industriei"""
    
    def __init__(self, mongo_client: MongoClient):
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.logs_collection = self.db["industry_transformation_logs"]
        
        # Creează index pentru performanță
        self.logs_collection.create_index([("timestamp", -1)])
        self.logs_collection.create_index([("session_id", 1)])
        
        logger.info("✅ Industry Transformation Logger initialized")
    
    def log(self, session_id: str, stage: str, message: str, data: Optional[Dict] = None):
        """
        Salvează un log entry
        
        Args:
            session_id: ID-ul sesiunii de transformare
            stage: Etapa (deepseek_discovery, web_search, agent_creation, etc.)
            message: Mesajul
            data: Date suplimentare (opțional)
        """
        try:
            entry = {
                "session_id": session_id,
                "stage": stage,
                "message": message,
                "data": data or {},
                "timestamp": datetime.now(timezone.utc)
            }
            self.logs_collection.insert_one(entry)
        except Exception as e:
            logger.error(f"Error logging: {e}")
    
    def get_logs(self, session_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Obține logs pentru o sesiune sau toate logs-urile
        
        Args:
            session_id: ID-ul sesiunii (None pentru toate)
            limit: Numărul maxim de logs
        
        Returns:
            Lista de logs
        """
        try:
            query = {}
            if session_id:
                query["session_id"] = session_id
            
            logs = list(
                self.logs_collection.find(query)
                .sort("timestamp", -1)
                .limit(limit)
            )
            
            for log in logs:
                log["_id"] = str(log["_id"])
                if "timestamp" in log:
                    log["timestamp"] = log["timestamp"].isoformat()
            
            return logs
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return []

