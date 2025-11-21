#!/usr/bin/env python3
"""
⚙️ Actions Executor
Execută acțiunile sistemului (build_jsonl, fine-tune, update_qdrant, etc.)
"""

import os
import subprocess
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# Import LLM Orchestrator
import sys
sys.path.insert(0, "/srv/hf/ai_agents")
from llm_orchestrator import LLMOrchestrator

# Paths to scripts
SCRIPTS = {
    "build_jsonl": "/srv/hf/ai_agents/fine_tuning/build_jsonl.py",
    "start_finetune": "/srv/hf/ai_agents/fine_tuning/train_qwen.sh",
    "update_qdrant": "/srv/hf/ai_agents/rag_updater/update_qdrant.py"
}

# Timeouts
TIMEOUTS = {
    "build_jsonl": 300,
    "start_finetune": 3600,
    "update_qdrant": 600
}


class ActionsExecutor:
    """Executor pentru acțiunile sistemului"""
    
    def __init__(self):
        self.running_jobs = {}  # job_id -> thread
    
    def execute_action(self, action: str, user_id: str, callback=None) -> Dict[str, Any]:
        """
        Execută o acțiune în background
        
        Args:
            action: Numele acțiunii (build_jsonl, start_finetune, update_qdrant)
            user_id: ID-ul utilizatorului
            callback: Funcție callback pentru actualizări
        
        Returns:
            Dict cu job_id și status
        """
        if action not in SCRIPTS:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": list(SCRIPTS.keys())
            }
        
        script_path = SCRIPTS[action]
        if not os.path.exists(script_path):
            return {
                "success": False,
                "error": f"Script not found: {script_path}"
            }
        
        # Generează job ID
        job_id = str(uuid.uuid4())
        
        # Pornește execuția în thread separat
        thread = threading.Thread(
            target=self._run_action,
            args=(job_id, action, script_path, user_id, callback),
            daemon=True
        )
        thread.start()
        
        self.running_jobs[job_id] = {
            "thread": thread,
            "action": action,
            "user_id": user_id,
            "status": "running",
            "started_at": datetime.now()
        }
        
        logger.info(f"Started action {action} with job_id: {job_id}")
        
        return {
            "success": True,
            "job_id": job_id,
            "action": action,
            "status": "running",
            "message": f"Action '{action}' started successfully"
        }
    
    def _run_action(self, job_id: str, action: str, script_path: str, user_id: str, callback=None):
        """Rulează acțiunea în thread separat"""
        timeout = TIMEOUTS.get(action, 300)
        
        try:
            # Determinați comanda
            if script_path.endswith('.py'):
                cmd = ["python3", script_path]
            elif script_path.endswith('.sh'):
                cmd = ["bash", script_path]
            else:
                raise ValueError(f"Unknown script type: {script_path}")
            
            # Rulează scriptul
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(script_path)
            )
            
            # Așteaptă finalizarea cu timeout
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return_code = -1
                error_msg = f"Action timed out after {timeout} seconds"
            else:
                error_msg = None
            
            # Actualizează status
            if return_code == 0:
                status = "completed"
                result = {
                    "success": True,
                    "stdout": stdout,
                    "return_code": return_code
                }
            else:
                status = "failed"
                result = {
                    "success": False,
                    "stdout": stdout,
                    "stderr": stderr,
                    "return_code": return_code,
                    "error": error_msg or stderr
                }
            
            self.running_jobs[job_id]["status"] = status
            self.running_jobs[job_id]["result"] = result
            self.running_jobs[job_id]["completed_at"] = datetime.now()
            
            # Callback pentru actualizare în MongoDB
            if callback:
                callback(job_id, status, result)
            
            logger.info(f"Action {action} (job_id: {job_id}) completed with status: {status}")
            
        except Exception as e:
            status = "failed"
            result = {
                "success": False,
                "error": str(e)
            }
            
            self.running_jobs[job_id]["status"] = status
            self.running_jobs[job_id]["result"] = result
            
            if callback:
                callback(job_id, status, result)
            
            logger.error(f"Error executing action {action}: {e}")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Obține statusul unui job"""
        return self.running_jobs.get(job_id)
    
    def list_running_jobs(self) -> List[Dict[str, Any]]:
        """Listează toate job-urile care rulează"""
        return [
            {
                "job_id": job_id,
                "action": info["action"],
                "user_id": info["user_id"],
                "status": info["status"],
                "started_at": info["started_at"].isoformat()
            }
            for job_id, info in self.running_jobs.items()
        ]


# Singleton instance
_actions_executor_instance = None

def get_actions_executor() -> ActionsExecutor:
    """Get singleton instance"""
    global _actions_executor_instance
    if _actions_executor_instance is None:
        _actions_executor_instance = ActionsExecutor()
    return _actions_executor_instance



def generate_agent_response(user_message: str, context: Dict[str, Any]) -> str:
    """
    Generate response using LLM Orchestrator
    Folosește: Kimi K2 70B → Llama 3.1 70B → DeepSeek → Qwen local
    """
    try:
        # Build system prompt
        system_prompt = """Ești Master Agent, un asistent AI inteligent care controlează sistemul de învățare automată.
        
        Poți executa următoarele acțiuni:
        - "build jsonl" sau "exportă date" - Exportă interacțiuni pentru training
        - "start training" sau "pornește fine-tuning" - Pornește antrenarea modelului
        - "update rag" sau "actualizează knowledge" - Actualizează baza vectorială
        - "check status" sau "verifică status" - Verifică statusul sistemului
        - "show stats" sau "arată statistici" - Afișează statistici
        
        Răspunde scurt, clar și prietenos. Confirmă acțiunea și spune ce se întâmplă.
        """
        
        # Initialize orchestrator
        orchestrator = LLMOrchestrator()

        # Call orchestrator (auto fallback: Kimi → Llama → DeepSeek → Qwen)
        response = orchestrator.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model="auto"  # Auto fallback
        )
        
        # Extract response content
        response_text = response.get("content", "Nu am putut genera răspuns.")
        
        # Log provider used
        provider = response.get("provider", "unknown")
        logger.info(f"Master Agent response generated via {provider}")
        
        # Data Collector saves automatically (integrated in orchestrator)
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return f"Am întâmpinat o eroare: {str(e)}"
