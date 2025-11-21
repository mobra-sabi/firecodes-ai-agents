#!/usr/bin/env python3
"""
👤 User Profiles Database Manager
Gestionează profilurile utilizatorilor și istoricul interacțiunilor
"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
DB_NAME = os.getenv("MONGO_DB", "adbrain_ai")


class UserProfilesDB:
    """Manager pentru profilurile utilizatorilor"""
    
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.profiles_collection = self.db.user_profiles
        self.interactions_collection = self.db.agent_interactions
        self.jobs_collection = self.db.agent_jobs
        
        # Creează indexuri
        self.profiles_collection.create_index("user_id", unique=True)
        self.interactions_collection.create_index([("user_id", 1), ("timestamp", -1)])
        self.jobs_collection.create_index([("user_id", 1), ("status", 1)])
    
    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Obține profilul unui utilizator"""
        profile = self.profiles_collection.find_one({"user_id": user_id})
        
        if not profile:
            # Creează profil nou
            profile = {
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                "last_seen": datetime.now(timezone.utc),
                "preferred_actions": {},
                "common_phrases": {},
                "history": [],
                "success_rate": 0.0,
                "total_interactions": 0,
                "preferred_time": None,
                "autopilot": False
            }
            self.profiles_collection.insert_one(profile)
            logger.info(f"✅ Created new profile for user: {user_id}")
        
        return profile
    
    def update_profile(self, user_id: str, updates: Dict[str, Any]):
        """Actualizează profilul utilizatorului"""
        updates["last_seen"] = datetime.now(timezone.utc)
        self.profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": updates},
            upsert=True
        )
        logger.debug(f"Updated profile for user: {user_id}")
    
    def add_interaction(self, user_id: str, message: str, response: str, action: Optional[str] = None):
        """Adaugă o interacțiune în istoric"""
        interaction = {
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc),
            "message": message,
            "response": response,
            "action": action,
            "success": action is not None
        }
        
        self.interactions_collection.insert_one(interaction)
        
        # Actualizează profil
        profile = self.get_profile(user_id)
        total = profile.get("total_interactions", 0) + 1
        
        # Calculează success rate
        successful = self.interactions_collection.count_documents({
            "user_id": user_id,
            "success": True
        })
        success_rate = (successful / total) * 100 if total > 0 else 0
        
        # Actualizează common phrases
        common_phrases = profile.get("common_phrases", {})
        words = message.lower().split()
        for word in words:
            if len(word) > 3:  # Ignoră cuvinte scurte
                common_phrases[word] = common_phrases.get(word, 0) + 1
        
        # Păstrează top 20
        common_phrases = dict(sorted(common_phrases.items(), key=lambda x: x[1], reverse=True)[:20])
        
        self.update_profile(user_id, {
            "total_interactions": total,
            "success_rate": success_rate,
            "common_phrases": common_phrases,
            "last_seen": datetime.now(timezone.utc)
        })
        
        logger.info(f"Added interaction for user: {user_id}")
    
    def update_preferred_action(self, user_id: str, action: str, success: bool):
        """Actualizează preferințele pentru o acțiune"""
        profile = self.get_profile(user_id)
        preferred = profile.get("preferred_actions", {})
        
        if action not in preferred:
            preferred[action] = {"count": 0, "success_count": 0, "last_used": None}
        
        preferred[action]["count"] += 1
        if success:
            preferred[action]["success_count"] += 1
        preferred[action]["last_used"] = datetime.now(timezone.utc)
        
        self.update_profile(user_id, {"preferred_actions": preferred})
    
    def get_recent_interactions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Obține interacțiunile recente"""
        interactions = list(
            self.interactions_collection.find({"user_id": user_id})
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        # Convert ObjectId to string
        for item in interactions:
            item["_id"] = str(item["_id"])
            if isinstance(item.get("timestamp"), datetime):
                item["timestamp"] = item["timestamp"].isoformat()
        
        return interactions
    
    def add_job(self, user_id: str, action: str, job_id: str, status: str = "running"):
        """Adaugă un job în colecție"""
        job = {
            "user_id": user_id,
            "action": action,
            "job_id": job_id,
            "status": status,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        self.jobs_collection.insert_one(job)
        logger.info(f"Added job {job_id} for user {user_id}, action: {action}")
    
    def update_job(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        """Actualizează statusul unui job"""
        update = {
            "status": status,
            "updated_at": datetime.now(timezone.utc)
        }
        if result:
            update["result"] = result
        
        self.jobs_collection.update_one(
            {"job_id": job_id},
            {"$set": update}
        )
        logger.info(f"Updated job {job_id} to status: {status}")


# Singleton instance
_profiles_db_instance = None

def get_profiles_db() -> UserProfilesDB:
    """Get singleton instance"""
    global _profiles_db_instance
    if _profiles_db_instance is None:
        _profiles_db_instance = UserProfilesDB()
    return _profiles_db_instance


