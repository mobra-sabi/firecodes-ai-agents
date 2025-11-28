
from pymongo import MongoClient
from datetime import datetime
import os
from enum import Enum
from typing import List, Optional

# --- Configurations ---
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
DB_NAME = "ai_agents_db"

class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class SubscriptionLimits:
    def __init__(self):
        self.limits = {
            SubscriptionTier.FREE: {
                "max_sites": 1,
                "max_competitors": 0,
                "deepseek_access": "basic", 
                "support": "community"
            },
            SubscriptionTier.PRO: {
                "max_sites": 3,
                "max_competitors": 10,
                "deepseek_access": "advanced", 
                "support": "email"
            },
            SubscriptionTier.ENTERPRISE: {
                "max_sites": 999,
                "max_competitors": 999,
                "deepseek_access": "dedicated",
                "support": "dedicated_agent"
            }
        }
    
    def get_limits(self, tier: str):
        return self.limits.get(tier, self.limits[SubscriptionTier.FREE])

class SaasManager:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DB_NAME]
        self.users = self.db.saas_users
        self.limits = SubscriptionLimits()

    def create_user(self, username, password_hash, email=None):
        if self.users.find_one({"username": username}):
            return {"ok": False, "error": "User already exists"}
        
        user_doc = {
            "username": username,
            "password_hash": password_hash, 
            "email": email,
            "tier": SubscriptionTier.FREE,
            "created_at": datetime.now(),
            "master_sites": [],
            "context_memory": []
        }
        self.users.insert_one(user_doc)
        return {"ok": True, "tier": "free"}

    def get_user_profile(self, username):
        user = self.users.find_one({"username": username}, {"_id": 0, "password_hash": 0})
        if not user: return None
        return user

    def check_subscription_limits(self, username):
        """Returns the limits for the user's current tier."""
        user = self.users.find_one({"username": username})
        if not user: 
            return self.limits.get_limits(SubscriptionTier.FREE)
        return self.limits.get_limits(user.get("tier", SubscriptionTier.FREE))

    def add_master_site(self, username, domain):
        user = self.users.find_one({"username": username})
        if not user: return {"ok": False, "error": "User not found"}
        
        limits = self.limits.get_limits(user.get("tier", SubscriptionTier.FREE))
        current_sites = user.get("master_sites", [])
        
        if len(current_sites) >= limits["max_sites"]:
            return {
                "ok": False, 
                "error": f"Limit reached for {user.get('tier', 'free')} tier. Upgrade to add more sites."
            }
            
        if domain in current_sites:
            return {"ok": False, "error": "You already own this site."}
            
        # For demo/MVP allow adding any site, trigger crawl later
        self.users.update_one(
            {"username": username},
            {"$push": {"master_sites": domain}}
        )
        
        return {"ok": True, "message": f"{domain} added to your Master Sites."}

# Singleton
_saas = None
def get_saas_manager():
    global _saas
    if _saas is None:
        _saas = SaasManager()
    return _saas
