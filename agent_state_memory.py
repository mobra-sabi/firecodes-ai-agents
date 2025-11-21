"""
Agent State Memory - Salvează status, analize, schimbări pentru fiecare agent
Oferă conștiință de SINE și de STARE pentru agenți
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ai_agents_db")


class AgentStateMemory:
    """Gestionează memoria de stare pentru fiecare agent"""
    
    def __init__(self):
        self.mongo = MongoClient(MONGODB_URI)
        self.db = self.mongo[MONGODB_DATABASE]
        self.state_collection = self.db.agent_state_memory
    
    def save_state(self, agent_id: str, state_data: Dict[str, Any]) -> bool:
        """
        Salvează starea curentă a agentului
        
        Args:
            agent_id: ID-ul agentului
            state_data: Dict cu:
                - current_status: str (active, monitoring, analyzing, etc.)
                - last_analysis: dict (ultima analiză efectuată)
                - last_org_chart: dict (ultima organigramă)
                - detected_changes: list (schimbări detectate)
                - seo_health_score: float (0-100)
                - ads_health_score: float (0-100)
                - opportunity_level: float (0-100)
                - risk_level: float (0-100)
                - awareness_notes: list (notițe de conștiință)
        """
        try:
            timestamp = datetime.now(timezone.utc)
            
            state_doc = {
                "agent_id": agent_id,
                "current_status": state_data.get("current_status", "unknown"),
                "last_analysis": state_data.get("last_analysis", {}),
                "last_org_chart": state_data.get("last_org_chart", {}),
                "detected_changes": state_data.get("detected_changes", []),
                "seo_health_score": state_data.get("seo_health_score", 0.0),
                "ads_health_score": state_data.get("ads_health_score", 0.0),
                "opportunity_level": state_data.get("opportunity_level", 0.0),
                "risk_level": state_data.get("risk_level", 0.0),
                "awareness_notes": state_data.get("awareness_notes", []),
                "last_update": timestamp,
                "created_at": timestamp
            }
            
            # Upsert: actualizează dacă există, creează dacă nu
            self.state_collection.update_one(
                {"agent_id": agent_id},
                {"$set": state_doc},
                upsert=True
            )
            
            logger.info(f"State saved for agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving state for agent {agent_id}: {e}")
            return False
    
    def get_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Obține starea curentă a agentului"""
        try:
            state = self.state_collection.find_one({"agent_id": agent_id})
            if state:
                state["_id"] = str(state["_id"])
            return state
        except Exception as e:
            logger.error(f"Error getting state for agent {agent_id}: {e}")
            return None
    
    def update_status(self, agent_id: str, status: str) -> bool:
        """Actualizează doar statusul agentului"""
        try:
            self.state_collection.update_one(
                {"agent_id": agent_id},
                {
                    "$set": {
                        "current_status": status,
                        "last_update": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating status for agent {agent_id}: {e}")
            return False
    
    def add_change(self, agent_id: str, change: Dict[str, Any]) -> bool:
        """Adaugă o schimbare detectată"""
        try:
            change["detected_at"] = datetime.now(timezone.utc)
            self.state_collection.update_one(
                {"agent_id": agent_id},
                {
                    "$push": {"detected_changes": change},
                    "$set": {"last_update": datetime.now(timezone.utc)}
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding change for agent {agent_id}: {e}")
            return False
    
    def add_awareness_note(self, agent_id: str, note: str, category: str = "general") -> bool:
        """Adaugă o notiță de conștiință"""
        try:
            awareness_note = {
                "note": note,
                "category": category,
                "timestamp": datetime.now(timezone.utc)
            }
            self.state_collection.update_one(
                {"agent_id": agent_id},
                {
                    "$push": {"awareness_notes": awareness_note},
                    "$set": {"last_update": datetime.now(timezone.utc)}
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding awareness note for agent {agent_id}: {e}")
            return False
    
    def get_recent_changes(self, agent_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Obține schimbările din ultimele N ore"""
        try:
            state = self.get_state(agent_id)
            if not state:
                return []
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            changes = state.get("detected_changes", [])
            
            recent_changes = [
                change for change in changes
                if change.get("detected_at", datetime.min.replace(tzinfo=timezone.utc)) >= cutoff_time
            ]
            
            return recent_changes
        except Exception as e:
            logger.error(f"Error getting recent changes for agent {agent_id}: {e}")
            return []
    
    def get_all_agents_states(self) -> List[Dict[str, Any]]:
        """Obține starea tuturor agenților"""
        try:
            states = list(self.state_collection.find({}))
            for state in states:
                state["_id"] = str(state["_id"])
            return states
        except Exception as e:
            logger.error(f"Error getting all agents states: {e}")
            return []

