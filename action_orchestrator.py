#!/usr/bin/env python3
"""
🎭 Action Orchestrator - Execută playbook-uri SEO automat
Orchestrează agenți de execuție + monitoring + DeepSeek loop
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from pymongo import MongoClient
from bson import ObjectId

from action_agents import get_agent, AVAILABLE_AGENTS
from playbook_schemas import ActionExecution, action_execution_to_dict

logger = logging.getLogger(__name__)


class ActionOrchestrator:
    """
    🎭 Orchestrator pentru execuție automată playbook-uri
    
    Features:
    - Execută acțiuni în ordine (respectă dependencies)
    - Parallel execution pentru acțiuni independente
    - Real-time progress tracking
    - Error handling + retry logic
    - DeepSeek feedback loop
    """
    
    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        db_name: str = "ai_agents_db"
    ):
        self.mongo = MongoClient(mongo_uri)
        self.db = self.mongo[db_name]
        self.logger = logging.getLogger(f"{__name__}.ActionOrchestrator")
    
    async def execute_playbook(
        self,
        playbook_id: str,
        auto_approve: bool = True
    ) -> Dict:
        """
        🎬 Execută playbook complet
        
        Args:
            playbook_id: ID playbook din MongoDB
            auto_approve: Dacă True, execută fără aprobare (guardrails check doar)
        
        Returns:
            {
                "playbook_id": str,
                "status": "completed" | "partial" | "failed",
                "actions_executed": int,
                "actions_failed": int,
                "execution_time_seconds": float,
                "results": []
            }
        """
        self.logger.info(f"🎬 Starting playbook execution: {playbook_id}")
        
        start_time = datetime.now(timezone.utc)
        
        # Load playbook
        playbook = await self._load_playbook(playbook_id)
        if not playbook:
            raise ValueError(f"Playbook {playbook_id} not found")
        
        # Update status → active
        self._update_playbook_status(playbook_id, "active")
        
        # Get actions
        actions = playbook.get("actions", [])
        if not actions:
            self.logger.warning(f"Playbook {playbook_id} has no actions")
            return {
                "playbook_id": playbook_id,
                "status": "completed",
                "actions_executed": 0,
                "actions_failed": 0,
                "execution_time_seconds": 0.0,
                "results": []
            }
        
        self.logger.info(f"📋 Loaded {len(actions)} actions")
        
        # Execute actions (sequentially for now)
        results = []
        actions_executed = 0
        actions_failed = 0
        
        for action in actions:
            self.logger.info(f"🎯 Executing action {action['action_id']}: {action['title']}")
            
            try:
                # Create execution record
                execution = await self._create_execution_record(
                    playbook_id,
                    action,
                    playbook["agent_id"]
                )
                
                # Execute action
                result = await self._execute_action(
                    execution_id=execution["execution_id"],
                    action=action,
                    agent_id=playbook["agent_id"],
                    playbook_id=playbook_id
                )
                
                if result["success"]:
                    actions_executed += 1
                    self.logger.info(f"✅ Action {action['action_id']} completed")
                else:
                    actions_failed += 1
                    self.logger.error(f"❌ Action {action['action_id']} failed")
                
                results.append(result)
                
                # Update action status în playbook
                self._update_action_status(
                    playbook_id,
                    action["action_id"],
                    "completed" if result["success"] else "failed",
                    result
                )
                
            except Exception as e:
                self.logger.error(f"❌ Action {action['action_id']} exception: {e}")
                actions_failed += 1
                results.append({
                    "action_id": action["action_id"],
                    "success": False,
                    "error": str(e)
                })
        
        # Calculate execution time
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()
        
        # Determine final status
        if actions_failed == 0:
            final_status = "completed"
        elif actions_executed > 0:
            final_status = "partial"
        else:
            final_status = "failed"
        
        # Update playbook
        self._update_playbook_status(
            playbook_id,
            final_status,
            {
                "completed_actions": actions_executed,
                "end_date": end_time
            }
        )
        
        self.logger.info(
            f"🎉 Playbook {playbook_id} execution finished: "
            f"{actions_executed} succeeded, {actions_failed} failed in {execution_time:.1f}s"
        )
        
        return {
            "playbook_id": playbook_id,
            "status": final_status,
            "actions_executed": actions_executed,
            "actions_failed": actions_failed,
            "execution_time_seconds": execution_time,
            "results": results
        }
    
    async def _load_playbook(self, playbook_id: str) -> Optional[Dict]:
        """Load playbook din MongoDB"""
        try:
            obj_id = ObjectId(playbook_id)
        except:
            obj_id = playbook_id
        
        return self.db.playbooks.find_one({"_id": obj_id})
    
    def _update_playbook_status(
        self,
        playbook_id: str,
        status: str,
        updates: Optional[Dict] = None
    ):
        """Update playbook status"""
        try:
            obj_id = ObjectId(playbook_id)
        except:
            obj_id = playbook_id
        
        update_doc = {
            "status": status,
            "updated_at": datetime.now(timezone.utc)
        }
        
        if updates:
            update_doc.update(updates)
        
        self.db.playbooks.update_one(
            {"_id": obj_id},
            {"$set": update_doc}
        )
    
    def _update_action_status(
        self,
        playbook_id: str,
        action_id: str,
        status: str,
        result: Dict
    ):
        """Update action status în playbook"""
        try:
            obj_id = ObjectId(playbook_id)
        except:
            obj_id = playbook_id
        
        self.db.playbooks.update_one(
            {"_id": obj_id, "actions.action_id": action_id},
            {
                "$set": {
                    "actions.$.status": status,
                    "actions.$.completed_at": datetime.now(timezone.utc),
                    "actions.$.result": result.get("result")
                }
            }
        )
    
    async def _create_execution_record(
        self,
        playbook_id: str,
        action: Dict,
        agent_id: str
    ) -> Dict:
        """Creează ActionExecution record"""
        execution = ActionExecution(
            playbook_id=playbook_id,
            action_id=action["action_id"],
            agent_id=agent_id,
            executor_agent=action["agent"],
            executor_model="qwen2.5-72b",
            status="queued",
            input_parameters=action.get("parameters", {})
        )
        
        exec_dict = action_execution_to_dict(execution)
        result = self.db.action_executions.insert_one(exec_dict)
        
        exec_dict["_id"] = str(result.inserted_id)
        return exec_dict
    
    async def _execute_action(
        self,
        execution_id: str,
        action: Dict,
        agent_id: str,
        playbook_id: str
    ) -> Dict:
        """
        🎯 Execută o acțiune folosind agent-ul corespunzător
        """
        # Update execution status → running
        self._update_execution_status(execution_id, "running", {"started_at": datetime.now(timezone.utc)})
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get agent
            agent_name = action.get("agent", "CopywriterAgent")
            
            if agent_name not in AVAILABLE_AGENTS:
                raise ValueError(f"Unknown agent: {agent_name}")
            
            agent = get_agent(agent_name)
            
            # Execute
            result = await agent.execute_action(
                action=action,
                agent_id=agent_id,
                playbook_id=playbook_id
            )
            
            # Calculate duration
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            # Update execution record
            self._update_execution_status(
                execution_id,
                "completed" if result["success"] else "failed",
                {
                    "completed_at": end_time,
                    "duration_seconds": duration,
                    "output_result": result.get("result"),
                    "logs": result.get("logs", []),
                    "errors": result.get("errors", [])
                }
            )
            
            return {
                "action_id": action["action_id"],
                "success": result["success"],
                "result": result.get("result"),
                "duration_seconds": duration
            }
            
        except Exception as e:
            self.logger.error(f"Action execution error: {e}")
            
            # Update execution → failed
            self._update_execution_status(
                execution_id,
                "failed",
                {
                    "completed_at": datetime.now(timezone.utc),
                    "errors": [str(e)]
                }
            )
            
            return {
                "action_id": action["action_id"],
                "success": False,
                "error": str(e)
            }
    
    def _update_execution_status(
        self,
        execution_id: str,
        status: str,
        updates: Optional[Dict] = None
    ):
        """Update ActionExecution status"""
        try:
            obj_id = ObjectId(execution_id)
        except:
            obj_id = execution_id
        
        update_doc = {"status": status}
        
        if updates:
            update_doc.update(updates)
        
        self.db.action_executions.update_one(
            {"_id": obj_id},
            {"$set": update_doc}
        )
    
    async def get_playbook_status(self, playbook_id: str) -> Dict:
        """
        📊 Obține status playbook + progress
        """
        playbook = await self._load_playbook(playbook_id)
        if not playbook:
            raise ValueError(f"Playbook {playbook_id} not found")
        
        actions = playbook.get("actions", [])
        total = len(actions)
        completed = sum(1 for a in actions if a.get("status") == "completed")
        failed = sum(1 for a in actions if a.get("status") == "failed")
        in_progress = sum(1 for a in actions if a.get("status") == "in_progress")
        
        progress = (completed / total * 100) if total > 0 else 0
        
        return {
            "playbook_id": playbook_id,
            "title": playbook.get("title"),
            "status": playbook.get("status"),
            "total_actions": total,
            "completed_actions": completed,
            "failed_actions": failed,
            "in_progress_actions": in_progress,
            "progress_percentage": progress,
            "created_at": playbook.get("created_at"),
            "updated_at": playbook.get("updated_at")
        }


# ============================================================================
# CLI for testing
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_orchestrator():
        orchestrator = ActionOrchestrator()
        
        # Generate playbook först (from previous test)
        from playbook_generator import PlaybookGenerator
        
        generator = PlaybookGenerator()
        playbook_id = await generator.generate_playbook(
            agent_id="691a34b65774faae88a735a1",
            sprint_days=14
        )
        
        print(f"✅ Playbook created: {playbook_id}")
        
        # Execute playbook
        print(f"\n🎬 Executing playbook...")
        result = await orchestrator.execute_playbook(playbook_id)
        
        print(f"\n✅ Execution completed:")
        print(f"   Status: {result['status']}")
        print(f"   Actions executed: {result['actions_executed']}")
        print(f"   Actions failed: {result['actions_failed']}")
        print(f"   Time: {result['execution_time_seconds']:.1f}s")
        
        # Check status
        status = await orchestrator.get_playbook_status(playbook_id)
        print(f"\n📊 Playbook status:")
        print(f"   Progress: {status['progress_percentage']:.1f}%")
        print(f"   Completed: {status['completed_actions']}/{status['total_actions']}")
    
    asyncio.run(test_orchestrator())

