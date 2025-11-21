#!/usr/bin/env python3
"""
Auto-Learning Trigger - Pornește training automat când sunt suficiente date
"""

import os
import subprocess
import logging
from datetime import datetime
from pymongo import MongoClient

logger = logging.getLogger(__name__)


class AutoLearningTrigger:
    """Trigger automat pentru fine-tuning când sunt suficiente interacțiuni"""
    
    def __init__(self, threshold: int = 50):
        """
        Args:
            threshold: Numărul minim de interacțiuni pentru training
        """
        self.mongo = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo.adbrain_ai
        self.threshold = threshold
        
        logger.info(f"Auto-learning trigger initialized (threshold: {threshold})")
    
    def check_and_trigger_training(self, agent_id: str = None) -> dict:
        """
        Verifică dacă sunt suficiente interacțiuni și pornește training
        
        Args:
            agent_id: Optional - training pentru agent specific
            
        Returns:
            dict cu status și detalii
        """
        try:
            # Count unprocessed interactions
            query = {"processed": False, "type": "interaction"}
            if agent_id:
                query["agent_id"] = agent_id
            
            unprocessed = self.db.interactions.count_documents(query)
            
            logger.info(f"Unprocessed interactions: {unprocessed}/{self.threshold}")
            
            if unprocessed >= self.threshold:
                logger.info(f"🚀 Threshold reached ({unprocessed}), starting training...")
                return self._start_training(agent_id, unprocessed)
            else:
                return {
                    "triggered": False,
                    "unprocessed": unprocessed,
                    "threshold": self.threshold,
                    "remaining": self.threshold - unprocessed,
                    "message": f"Need {self.threshold - unprocessed} more interactions for training"
                }
        
        except Exception as e:
            logger.error(f"Error checking trigger: {e}")
            return {
                "triggered": False,
                "error": str(e)
            }
    
    def _start_training(self, agent_id: str = None, count: int = 0) -> dict:
        """Pornește procesul de training"""
        try:
            job_id = f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 1. Build JSONL dataset
            logger.info("Step 1: Building JSONL dataset...")
            jsonl_result = subprocess.run(
                ["python3", "/srv/hf/ai_agents/fine_tuning/build_jsonl.py"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if jsonl_result.returncode != 0:
                raise Exception(f"JSONL build failed: {jsonl_result.stderr}")
            
            # 2. Start training (background process)
            logger.info("Step 2: Starting Qwen fine-tuning...")
            training_process = subprocess.Popen(
                ["bash", "/srv/hf/ai_agents/fine_tuning/train_qwen.sh"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 3. Log job în MongoDB
            job_doc = {
                "job_id": job_id,
                "type": "auto_training",
                "agent_id": agent_id,
                "interactions_count": count,
                "status": "started",
                "started_at": datetime.now(),
                "pid": training_process.pid,
                "trigger": "auto"
            }
            
            self.db.agent_jobs.insert_one(job_doc)
            
            logger.info(f"✅ Training started - Job ID: {job_id}, PID: {training_process.pid}")
            
            return {
                "triggered": True,
                "job_id": job_id,
                "pid": training_process.pid,
                "interactions_processed": count,
                "message": f"Training started with {count} interactions",
                "steps": {
                    "jsonl_build": "completed",
                    "training": "started"
                }
            }
            
        except Exception as e:
            logger.error(f"Error starting training: {e}")
            return {
                "triggered": True,
                "error": str(e),
                "message": f"Training failed: {str(e)}"
            }
    
    def get_training_status(self, job_id: str) -> dict:
        """Verifică statusul unui job de training"""
        try:
            job = self.db.agent_jobs.find_one({"job_id": job_id})
            if not job:
                return {"found": False, "message": "Job not found"}
            
            # Check if process is still running
            pid = job.get("pid")
            if pid:
                try:
                    os.kill(pid, 0)  # Check if process exists
                    running = True
                except OSError:
                    running = False
            else:
                running = False
            
            return {
                "found": True,
                "job_id": job_id,
                "status": job.get("status"),
                "started_at": job.get("started_at"),
                "running": running,
                "interactions_count": job.get("interactions_count")
            }
            
        except Exception as e:
            logger.error(f"Error checking status: {e}")
            return {"found": False, "error": str(e)}


# Global instance
_auto_trigger = None


def get_auto_trigger(threshold: int = 50) -> AutoLearningTrigger:
    """Get or create auto trigger instance"""
    global _auto_trigger
    if _auto_trigger is None:
        _auto_trigger = AutoLearningTrigger(threshold=threshold)
    return _auto_trigger


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    trigger = get_auto_trigger(threshold=5)  # Lower threshold for testing
    result = trigger.check_and_trigger_training()
    
    print("\nTrigger result:")
    print(result)


