"""
DeepSeek Orchestrator - Central orchestrator for all application flows
Monitors, learns, and makes decisions based on all actions
"""
import os
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import traceback

from llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)


class DeepSeekOrchestrator:
    """
    Central orchestrator that:
    1. Monitors all actions in the application
    2. Makes decisions using DeepSeek
    3. Stores actions in MongoDB for learning
    4. Generates embeddings for Qdrant
    5. Learns from patterns and optimizes flows
    """
    
    def __init__(self, mongo_client: MongoClient, qdrant_client=None):
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.qdrant = qdrant_client
        
        # Collections
        self.actions_collection = self.db["orchestrator_actions"]
        self.learning_collection = self.db["orchestrator_learning"]
        self.decisions_collection = self.db["orchestrator_decisions"]
        self.patterns_collection = self.db["orchestrator_patterns"]
        
        # LLM Orchestrator (DeepSeek primary)
        self.llm = LLMOrchestrator()
        
        # Initialize collections with indexes
        self._initialize_indexes()
        
        logger.info("✅ DeepSeek Orchestrator initialized")
    
    def _initialize_indexes(self):
        """Create indexes for performance"""
        try:
            self.actions_collection.create_index([("timestamp", -1)])
            self.actions_collection.create_index([("action_type", 1)])
            self.actions_collection.create_index([("agent_id", 1)])
            self.actions_collection.create_index([("user_id", 1)])
            self.actions_collection.create_index([("route", 1)])
            
            self.learning_collection.create_index([("timestamp", -1)])
            self.learning_collection.create_index([("action_id", 1)])
            self.learning_collection.create_index([("pattern_type", 1)])
            
            self.decisions_collection.create_index([("timestamp", -1)])
            self.decisions_collection.create_index([("action_id", 1)])
            
            logger.info("✅ Orchestrator indexes created")
        except Exception as e:
            logger.warning(f"⚠️ Error creating indexes: {e}")
    
    def log_action(
        self,
        action_type: str,
        route: str,
        method: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        request_data: Optional[Dict] = None,
        response_data: Optional[Dict] = None,
        status_code: int = 200,
        duration_ms: float = 0,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Log an action to MongoDB
        
        Returns:
            action_id: MongoDB document ID
        """
        try:
            action_doc = {
                "action_type": action_type,  # api_call, agent_creation, serp_search, etc.
                "route": route,
                "method": method,
                "user_id": user_id,
                "agent_id": agent_id,
                "request_data": request_data or {},
                "response_data": response_data or {},
                "status_code": status_code,
                "duration_ms": duration_ms,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc),
                "processed": False,  # For learning pipeline
                "embedding_generated": False
            }
            
            result = self.actions_collection.insert_one(action_doc)
            action_id = str(result.inserted_id)
            
            # Trigger async learning processing
            self._process_action_for_learning(action_id, action_doc)
            
            logger.debug(f"📝 Action logged: {action_type} on {route} (ID: {action_id})")
            return action_id
            
        except Exception as e:
            logger.error(f"❌ Error logging action: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def _process_action_for_learning(self, action_id: str, action_doc: Dict):
        """
        Process action for learning:
        1. Generate embedding
        2. Store in Qdrant
        3. Extract patterns
        4. Update learning collection
        """
        try:
            # Generate text representation for embedding
            action_text = self._action_to_text(action_doc)
            
            # Generate embedding (async - will be done by learning pipeline)
            # For now, mark as ready for processing
            self.actions_collection.update_one(
                {"_id": ObjectId(action_id)},
                {"$set": {"ready_for_learning": True}}
            )
            
            # Extract immediate patterns
            self._extract_patterns(action_id, action_doc)
            
        except Exception as e:
            logger.error(f"❌ Error processing action for learning: {e}")
    
    def _action_to_text(self, action_doc: Dict) -> str:
        """Convert action to text for embedding"""
        parts = [
            f"Action: {action_doc.get('action_type', 'unknown')}",
            f"Route: {action_doc.get('route', 'unknown')}",
            f"Method: {action_doc.get('method', 'unknown')}",
        ]
        
        if action_doc.get('agent_id'):
            parts.append(f"Agent: {action_doc['agent_id']}")
        
        if action_doc.get('request_data'):
            # Include key request data
            req = action_doc['request_data']
            if isinstance(req, dict):
                for key in ['url', 'keyword', 'domain', 'name', 'title']:
                    if key in req:
                        parts.append(f"{key}: {req[key]}")
        
        if action_doc.get('response_data'):
            resp = action_doc['response_data']
            if isinstance(resp, dict):
                if 'status' in resp:
                    parts.append(f"Status: {resp['status']}")
                if 'message' in resp:
                    parts.append(f"Message: {resp['message']}")
        
        return " | ".join(parts)
    
    def _extract_patterns(self, action_id: str, action_doc: Dict):
        """Extract patterns from action"""
        try:
            patterns = []
            
            # Pattern: Route frequency
            route = action_doc.get('route', '')
            patterns.append({
                "pattern_type": "route_frequency",
                "value": route,
                "action_id": action_id
            })
            
            # Pattern: Action type frequency
            action_type = action_doc.get('action_type', '')
            patterns.append({
                "pattern_type": "action_type_frequency",
                "value": action_type,
                "action_id": action_id
            })
            
            # Pattern: Response time
            duration = action_doc.get('duration_ms', 0)
            if duration > 0:
                patterns.append({
                    "pattern_type": "response_time",
                    "value": duration,
                    "action_id": action_id,
                    "category": "slow" if duration > 1000 else "fast"
                })
            
            # Pattern: Error patterns
            if action_doc.get('status_code', 200) >= 400:
                patterns.append({
                    "pattern_type": "error",
                    "value": action_doc.get('status_code'),
                    "action_id": action_id,
                    "route": route
                })
            
            # Store patterns
            if patterns:
                self.patterns_collection.insert_many(patterns)
                
        except Exception as e:
            logger.error(f"❌ Error extracting patterns: {e}")
    
    def make_decision(
        self,
        context: Dict,
        available_actions: List[str],
        goal: str
    ) -> Dict:
        """
        Use DeepSeek to make a decision based on context and available actions
        
        Args:
            context: Current context (agent_id, state, recent actions, etc.)
            available_actions: List of available actions
            goal: Goal to achieve
        
        Returns:
            Decision with action, reasoning, and confidence
        """
        try:
            # Build prompt for DeepSeek
            prompt = self._build_decision_prompt(context, available_actions, goal)
            
            # Get recent actions for context
            recent_actions = self._get_recent_actions(
                agent_id=context.get('agent_id'),
                limit=10
            )
            
            # Add recent actions to context
            context_with_history = {
                **context,
                "recent_actions": recent_actions
            }
            
            # Call DeepSeek
            response = self.llm.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI orchestrator that makes intelligent decisions based on context and available actions. Analyze the situation and choose the best action."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Parse response
            decision = self._parse_decision_response(response, context)
            
            # Store decision
            decision_doc = {
                "context": context,
                "available_actions": available_actions,
                "goal": goal,
                "decision": decision,
                "timestamp": datetime.now(timezone.utc),
                "action_id": context.get("action_id")
            }
            self.decisions_collection.insert_one(decision_doc)
            
            logger.info(f"🎯 Decision made: {decision.get('action')} (confidence: {decision.get('confidence', 0)})")
            return decision
            
        except Exception as e:
            logger.error(f"❌ Error making decision: {e}")
            logger.error(traceback.format_exc())
            return {
                "action": available_actions[0] if available_actions else "wait",
                "reasoning": f"Error: {str(e)}",
                "confidence": 0.0
            }
    
    def _build_decision_prompt(self, context: Dict, available_actions: List[str], goal: str) -> str:
        """Build prompt for DeepSeek decision-making"""
        prompt_parts = [
            f"Goal: {goal}",
            f"\nContext:",
            json.dumps(context, indent=2),
            f"\nAvailable Actions:",
            "\n".join([f"- {action}" for action in available_actions]),
            f"\n\nAnalyze the context and choose the best action to achieve the goal.",
            "Respond in JSON format:",
            '{"action": "chosen_action", "reasoning": "explanation", "confidence": 0.0-1.0}'
        ]
        return "\n".join(prompt_parts)
    
    def _parse_decision_response(self, response: str, context: Dict) -> Dict:
        """Parse DeepSeek response into decision dict"""
        try:
            # Try to extract JSON from response
            if isinstance(response, str):
                # Find JSON in response
                import re
                json_match = re.search(r'\{[^{}]*\}', response)
                if json_match:
                    decision = json.loads(json_match.group())
                else:
                    # Fallback: extract action from text
                    decision = {
                        "action": response.split()[0] if response else "wait",
                        "reasoning": response,
                        "confidence": 0.5
                    }
            else:
                decision = response
            
            # Validate decision
            if not isinstance(decision, dict):
                decision = {"action": "wait", "reasoning": str(decision), "confidence": 0.5}
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ Error parsing decision response: {e}")
            return {
                "action": "wait",
                "reasoning": f"Parse error: {str(e)}",
                "confidence": 0.0
            }
    
    def _get_recent_actions(self, agent_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get recent actions for context"""
        try:
            query = {}
            if agent_id:
                query["agent_id"] = agent_id
            
            actions = list(
                self.actions_collection
                .find(query)
                .sort("timestamp", -1)
                .limit(limit)
            )
            
            # Convert ObjectId to string
            for action in actions:
                action["_id"] = str(action["_id"])
            
            return actions
            
        except Exception as e:
            logger.error(f"❌ Error getting recent actions: {e}")
            return []
    
    def get_insights(self, agent_id: Optional[str] = None, days: int = 7) -> Dict:
        """
        Get insights from actions:
        - Most used routes
        - Average response times
        - Error rates
        - Action patterns
        """
        try:
            from datetime import timedelta
            
            query = {
                "timestamp": {
                    "$gte": datetime.now(timezone.utc) - timedelta(days=days)
                }
            }
            if agent_id:
                query["agent_id"] = agent_id
            
            # Aggregate insights
            pipeline = [
                {"$match": query},
                {
                    "$group": {
                        "_id": "$action_type",
                        "count": {"$sum": 1},
                        "avg_duration": {"$avg": "$duration_ms"},
                        "error_count": {
                            "$sum": {
                                "$cond": [{"$gte": ["$status_code", 400]}, 1, 0]
                            }
                        }
                    }
                },
                {"$sort": {"count": -1}}
            ]
            
            insights = list(self.actions_collection.aggregate(pipeline))
            
            return {
                "period_days": days,
                "agent_id": agent_id,
                "insights": insights,
                "total_actions": sum(i["count"] for i in insights),
                "error_rate": sum(i["error_count"] for i in insights) / max(sum(i["count"] for i in insights), 1)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting insights: {e}")
            return {"error": str(e)}


# Global instance
_orchestrator_instance = None

def get_orchestrator(mongo_client: MongoClient = None, qdrant_client=None) -> DeepSeekOrchestrator:
    """Get or create orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None and mongo_client:
        _orchestrator_instance = DeepSeekOrchestrator(mongo_client, qdrant_client)
    return _orchestrator_instance

