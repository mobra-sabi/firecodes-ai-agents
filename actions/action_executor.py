"""
Action Executor - Execută acțiuni din ActionPlan-uri generate de LangChain
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import os

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")


class ActionExecutor:
    """
    Execută acțiuni din ActionPlan-uri generate de Decision Chain
    """
    
    def __init__(self):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client[MONGO_DB]
        self.executed_actions_collection = self.db.executed_actions
        
        # Inițializează conectori
        self.connectors = {}
        self._initialize_connectors()
    
    def _initialize_connectors(self):
        """Inițializează conectorii disponibili"""
        try:
            from actions.google_ads_connector import GoogleAdsConnector
            self.connectors["google_ads"] = GoogleAdsConnector()
            logger.info("✅ Google Ads connector initialized")
        except ImportError:
            logger.warning("⚠️ Google Ads connector not available")
        
        try:
            from actions.wordpress_connector import WordPressConnector
            self.connectors["wordpress"] = WordPressConnector()
            logger.info("✅ WordPress connector initialized")
        except ImportError:
            logger.warning("⚠️ WordPress connector not available")
        
        try:
            from actions.seo_api_connector import SEOAPIConnector
            self.connectors["seo_api"] = SEOAPIConnector()
            logger.info("✅ SEO API connector initialized")
        except ImportError:
            logger.warning("⚠️ SEO API connector not available")
    
    async def execute_action_plan(self, agent_id: str, action_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execută un plan de acțiuni
        
        Args:
            agent_id: ID-ul agentului
            action_plan: Planul de acțiuni din Decision Chain
        
        Returns:
            Dict cu rezultatele execuției
        """
        try:
            results = {
                "agent_id": agent_id,
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "actions": [],
                "success_count": 0,
                "failure_count": 0
            }
            
            # Procesează acțiunile imediate
            immediate_actions = action_plan.get("immediate_actions", [])
            for action in immediate_actions:
                result = await self._execute_single_action(agent_id, action)
                results["actions"].append(result)
                if result.get("success"):
                    results["success_count"] += 1
                else:
                    results["failure_count"] += 1
            
            # Salvează rezultatele în MongoDB
            self.executed_actions_collection.insert_one({
                "agent_id": agent_id,
                "action_plan": action_plan,
                "results": results,
                "status": "completed" if results["failure_count"] == 0 else "partial",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
            
            logger.info(f"✅ Executed action plan for agent {agent_id}: {results['success_count']} success, {results['failure_count']} failures")
            
            return {
                "ok": True,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"❌ Error executing action plan: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "ok": False,
                "error": str(e)
            }
    
    async def _execute_single_action(self, agent_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execută o singură acțiune
        
        Args:
            agent_id: ID-ul agentului
            action: Acțiunea de executat
        
        Returns:
            Dict cu rezultatul execuției
        """
        try:
            action_type = action.get("action", "").lower()
            tool = action.get("tool", "").lower()
            
            # Determină connectorul potrivit
            connector = None
            if "google ads" in action_type or tool == "google_ads":
                connector = self.connectors.get("google_ads")
            elif "wordpress" in action_type or tool == "wordpress":
                connector = self.connectors.get("wordpress")
            elif "seo" in action_type or tool == "seo_api":
                connector = self.connectors.get("seo_api")
            
            if not connector:
                return {
                    "success": False,
                    "error": f"No connector available for action type: {action_type}",
                    "action": action
                }
            
            # Execută acțiunea prin connector
            result = await connector.execute(action, agent_id)
            
            return {
                "success": result.get("success", False),
                "result": result,
                "action": action,
                "executed_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error executing single action: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": action
            }
    
    def get_action_status(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obține statusul acțiunilor executate pentru un agent
        
        Args:
            agent_id: ID-ul agentului
            limit: Numărul maxim de acțiuni de returnat
        
        Returns:
            Listă cu acțiunile executate
        """
        try:
            actions = list(self.executed_actions_collection.find({
                "agent_id": agent_id
            }).sort("created_at", -1).limit(limit))
            
            # Convertește ObjectId la string
            for action in actions:
                action["_id"] = str(action["_id"])
                if "created_at" in action:
                    action["created_at"] = action["created_at"].isoformat()
                if "updated_at" in action:
                    action["updated_at"] = action["updated_at"].isoformat()
            
            return actions
            
        except Exception as e:
            logger.error(f"❌ Error getting action status: {e}")
            return []


# Instanță globală
_action_executor = None

def get_action_executor() -> ActionExecutor:
    """Obține instanța globală a Action Executor"""
    global _action_executor
    if _action_executor is None:
        _action_executor = ActionExecutor()
    return _action_executor

async def execute_action_plan(agent_id: str, action_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Funcție de conveniență pentru executarea unui plan de acțiuni"""
    return await get_action_executor().execute_action_plan(agent_id, action_plan)

def get_action_status(agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Funcție de conveniență pentru obținerea statusului acțiunilor"""
    return get_action_executor().get_action_status(agent_id, limit)

