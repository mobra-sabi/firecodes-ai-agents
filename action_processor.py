#!/usr/bin/env python3
"""
🔄 Action Processor - Worker pentru procesarea acțiunilor din queue
Rulează în background și procesează acțiunile automat
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional
from pymongo import MongoClient
from bson import ObjectId

from actions_queue_manager import ActionsQueueManager, ActionStatus
from action_agents import get_agent, AVAILABLE_AGENTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActionProcessor:
    """Worker pentru procesarea acțiunilor din queue"""
    
    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        db_name: str = "ai_agents_db",
        poll_interval: int = 5
    ):
        self.mongo = MongoClient(mongo_uri)
        self.db = self.mongo[db_name]
        self.queue_manager = ActionsQueueManager(self.mongo)
        self.poll_interval = poll_interval
        self.running = False
        self.logger = logging.getLogger(f"{__name__}.ActionProcessor")
        
    async def process_action(self, action: Dict) -> Dict:
        """Procesează o acțiune"""
        action_id = action["_id"]
        action_type = action["action_type"]
        agent_id = action["agent_id"]
        
        self.logger.info(f"🔄 Processing action {action_id}: {action_type} for agent {agent_id}")
        
        try:
            # Update status to running
            self.queue_manager.update_action_status(action_id, ActionStatus.RUNNING.value)
            
            # Map action type to agent class
            action_type_map = {
                "onpage_optimize": "OnPageOptimizer",
                "content_create": "CopywriterAgent",
                "schema_generate": "SchemaGenerator",
                "interlink_suggest": "LinkSuggester"
            }
            
            agent_class_name = action_type_map.get(action_type)
            if not agent_class_name:
                # Try get_agent function
                agent_class = get_agent(action_type)
                if not agent_class:
                    raise ValueError(f"No agent available for action type: {action_type}")
            else:
                # Import and get class directly
                from action_agents import OnPageOptimizer, CopywriterAgent, SchemaGenerator, LinkSuggester
                agent_class_map = {
                    "OnPageOptimizer": OnPageOptimizer,
                    "CopywriterAgent": CopywriterAgent,
                    "SchemaGenerator": SchemaGenerator,
                    "LinkSuggester": LinkSuggester
                }
                agent_class = agent_class_map.get(agent_class_name)
                if not agent_class:
                    raise ValueError(f"Agent class {agent_class_name} not found")
            
            # Create agent instance
            action_agent = agent_class()
            
            # Prepare action dict for execute_action
            action_dict = {
                "action_id": action_id,
                "title": f"{action_type.replace('_', ' ').title()}",
                "description": f"Execute {action_type} for agent {agent_id}",
                "assigned_keywords": action.get("action_data", {}).get("keywords", []),
                **action.get("action_data", {})
            }
            
            # Execute action
            result = await action_agent.execute_action(
                action=action_dict,
                agent_id=agent_id,
                playbook_id=None  # Not from playbook
            )
            
            if result["success"]:
                # Update status to completed
                self.queue_manager.update_action_status(
                    action_id,
                    ActionStatus.COMPLETED.value,
                    result=result["result"],
                    error=None
                )
                self.logger.info(f"✅ Action {action_id} completed successfully")
                return {"success": True, "result": result}
            else:
                # Update status to failed
                error_msg = "; ".join(result.get("errors", ["Unknown error"]))
                self.queue_manager.update_action_status(
                    action_id,
                    ActionStatus.FAILED.value,
                    result=None,
                    error=error_msg
                )
                self.logger.error(f"❌ Action {action_id} failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"❌ Action {action_id} error: {error_msg}")
            
            # Update status to failed
            self.queue_manager.update_action_status(
                action_id,
                ActionStatus.FAILED.value,
                result=None,
                error=error_msg
            )
            
            return {"success": False, "error": error_msg}
    
    async def process_queue(self):
        """Procesează acțiunile din queue continuu"""
        self.running = True
        self.logger.info("🚀 Action Processor started")
        
        while self.running:
            try:
                # Get next action
                action = self.queue_manager.get_next_action()
                
                if action:
                    self.logger.info(f"📋 Found action to process: {action['_id']} ({action['action_type']})")
                    await self.process_action(action)
                else:
                    # No actions to process, wait
                    await asyncio.sleep(self.poll_interval)
                    
            except Exception as e:
                self.logger.error(f"❌ Error in process_queue: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        """Oprește procesorul"""
        self.running = False
        self.logger.info("🛑 Action Processor stopped")


async def main():
    """Main entry point"""
    processor = ActionProcessor()
    
    try:
        await processor.process_queue()
    except KeyboardInterrupt:
        processor.stop()
        logger.info("👋 Action Processor stopped by user")


if __name__ == "__main__":
    asyncio.run(main())

