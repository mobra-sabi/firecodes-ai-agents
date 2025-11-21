"""
Actions Queue Manager
Manages action queue for SEO/PPC actions with priority, status, and execution tracking
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from pymongo import MongoClient
from bson import ObjectId
from enum import Enum

logger = logging.getLogger(__name__)


class ActionStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionType(Enum):
    CONTENT_CREATE = "content_create"
    ONPAGE_OPTIMIZE = "onpage_optimize"
    INTERLINK_SUGGEST = "interlink_suggest"
    SCHEMA_GENERATE = "schema_generate"
    ADS_CREATE = "ads_create"
    ADS_UPDATE = "ads_update"
    EXPERIMENT_RUN = "experiment_run"
    ROLLBACK = "rollback"


class ActionsQueueManager:
    """Manages action queue for automated SEO/PPC actions"""
    
    def __init__(self, mongo_client: MongoClient = None):
        if mongo_client is None:
            mongo_client = MongoClient("mongodb://localhost:27017/")
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.queue_collection = self.db["actions_queue"]
        
        # Create indexes
        self.queue_collection.create_index([("agent_id", 1), ("status", 1)])
        self.queue_collection.create_index([("priority", -1), ("created_at", 1)])
        self.queue_collection.create_index([("status", 1), ("scheduled_at", 1)])
    
    def add_action(
        self,
        agent_id: str,
        action_type: str,
        action_data: Dict,
        priority: int = 50,
        scheduled_at: Optional[datetime] = None,
        depends_on: Optional[List[str]] = None,
        guardrails: Optional[Dict] = None
    ) -> str:
        """
        Add action to queue
        
        Args:
            agent_id: Master agent ID
            action_type: Type of action (ActionType enum value)
            action_data: Action-specific data
            priority: Priority (0-100, higher = more important)
            scheduled_at: When to execute (None = immediate)
            depends_on: List of action IDs this depends on
            guardrails: Safety constraints (max_changes, rollback_on_drop, etc.)
        
        Returns:
            Action ID
        """
        action = {
            "agent_id": agent_id,
            "action_type": action_type,
            "action_data": action_data,
            "priority": priority,
            "status": ActionStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc),
            "scheduled_at": scheduled_at or datetime.now(timezone.utc),
            "started_at": None,
            "completed_at": None,
            "depends_on": depends_on or [],
            "guardrails": guardrails or {},
            "result": None,
            "error": None,
            "retry_count": 0,
            "max_retries": 3
        }
        
        result = self.queue_collection.insert_one(action)
        action_id = str(result.inserted_id)
        
        logger.info(f"✅ Action added to queue: {action_id} ({action_type}) for agent {agent_id}")
        return action_id
    
    def get_next_action(self, agent_id: Optional[str] = None) -> Optional[Dict]:
        """
        Get next action to execute (highest priority, ready to run)
        
        Args:
            agent_id: Optional filter by agent
        
        Returns:
            Action document or None
        """
        query = {
            "status": {"$in": [ActionStatus.PENDING.value, ActionStatus.QUEUED.value]},
            "scheduled_at": {"$lte": datetime.now(timezone.utc)}
        }
        
        if agent_id:
            query["agent_id"] = agent_id
        
        # Get actions with all dependencies completed
        actions = list(self.queue_collection.find(query).sort([
            ("priority", -1),
            ("created_at", 1)
        ]).limit(100))
        
        for action in actions:
            # Check if dependencies are completed
            if action.get("depends_on"):
                deps = action["depends_on"]
                completed = self.queue_collection.count_documents({
                    "_id": {"$in": [ObjectId(dep) for dep in deps]},
                    "status": ActionStatus.COMPLETED.value
                })
                if completed < len(deps):
                    continue  # Dependencies not met
            
            # Mark as queued and return
            self.queue_collection.update_one(
                {"_id": action["_id"]},
                {"$set": {
                    "status": ActionStatus.QUEUED.value,
                    "started_at": datetime.now(timezone.utc)
                }}
            )
            
            action["_id"] = str(action["_id"])
            return action
        
        return None
    
    def update_action_status(
        self,
        action_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Update action status"""
        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc)
        }
        
        if status == ActionStatus.RUNNING.value:
            update_data["started_at"] = datetime.now(timezone.utc)
        elif status in [ActionStatus.COMPLETED.value, ActionStatus.FAILED.value]:
            update_data["completed_at"] = datetime.now(timezone.utc)
            if result:
                update_data["result"] = result
            if error:
                update_data["error"] = error
        
        self.queue_collection.update_one(
            {"_id": ObjectId(action_id)},
            {"$set": update_data}
        )
        
        logger.info(f"✅ Action {action_id} status updated to {status}")
    
    def get_actions_for_agent(
        self,
        agent_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get actions for an agent"""
        query = {"agent_id": agent_id}
        if status:
            query["status"] = status
        
        actions = list(self.queue_collection.find(query).sort("created_at", -1).limit(limit))
        for action in actions:
            action["_id"] = str(action["_id"])
        
        return actions
    
    def calculate_ice_score(self, action: Dict) -> float:
        """
        Calculate ICE score (Impact × Confidence × Ease)
        Higher score = higher priority
        """
        impact = action.get("action_data", {}).get("impact", 5) / 10.0
        confidence = action.get("action_data", {}).get("confidence", 5) / 10.0
        ease = action.get("action_data", {}).get("ease", 5) / 10.0
        
        ice_score = impact * confidence * ease
        return round(ice_score * 100, 2)
    
    def prioritize_actions(self, agent_id: str):
        """Recalculate priorities based on ICE scores"""
        actions = self.get_actions_for_agent(agent_id, status=ActionStatus.PENDING.value)
        
        for action in actions:
            ice_score = self.calculate_ice_score(action)
            # Combine ICE with manual priority
            final_priority = int((ice_score + action.get("priority", 50)) / 2)
            
            self.queue_collection.update_one(
                {"_id": ObjectId(action["_id"])},
                {"$set": {
                    "priority": final_priority,
                    "ice_score": ice_score
                }}
            )
        
        logger.info(f"✅ Prioritized {len(actions)} actions for agent {agent_id}")
    
    def cancel_action(self, action_id: str, reason: str = "Manual cancellation"):
        """Cancel an action"""
        self.queue_collection.update_one(
            {"_id": ObjectId(action_id)},
            {"$set": {
                "status": ActionStatus.CANCELLED.value,
                "error": reason,
                "completed_at": datetime.now(timezone.utc)
            }}
        )
        logger.info(f"✅ Action {action_id} cancelled: {reason}")
    
    def get_queue_stats(self, agent_id: Optional[str] = None) -> Dict:
        """Get queue statistics"""
        query = {}
        if agent_id:
            query["agent_id"] = agent_id
        
        stats = {
            "total": self.queue_collection.count_documents(query),
            "pending": self.queue_collection.count_documents({**query, "status": ActionStatus.PENDING.value}),
            "queued": self.queue_collection.count_documents({**query, "status": ActionStatus.QUEUED.value}),
            "running": self.queue_collection.count_documents({**query, "status": ActionStatus.RUNNING.value}),
            "completed": self.queue_collection.count_documents({**query, "status": ActionStatus.COMPLETED.value}),
            "failed": self.queue_collection.count_documents({**query, "status": ActionStatus.FAILED.value}),
        }
        
        return stats

