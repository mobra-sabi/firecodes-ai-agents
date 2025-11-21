#!/usr/bin/env python3
"""
💬 Chat API Interface
Interfața principală pentru chat verbal și text
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ChatAPI:
    """API pentru chat"""
    
    def __init__(self, profiles_db, context_memory, intent_planner, actions_executor, tts_service):
        self.profiles_db = profiles_db
        self.context_memory = context_memory
        self.intent_planner = intent_planner
        self.actions_executor = actions_executor
        self.tts_service = tts_service
    
    def process_chat(self, user_id: str, message: str, generate_audio: bool = True) -> Dict[str, Any]:
        """
        Procesează un mesaj de chat
        
        Args:
            user_id: ID-ul utilizatorului
            message: Mesajul text
            generate_audio: Dacă să genereze audio
        
        Returns:
            Dict cu text și audio_path
        """
        try:
            # Detectează intenția
            intent_result = self.intent_planner.detect_intent(
                message,
                user_id=user_id,
                context_memory=self.context_memory
            )
            
            action = intent_result.get("action")
            confidence = intent_result.get("confidence", 0)
            
            # Dacă avem o acțiune clară, execută-o
            if action and confidence >= 0.7:
                # Execută acțiunea
                if action in ["build_jsonl", "start_finetune", "update_qdrant"]:
                    action_result = self.actions_executor.execute_action(
                        action,
                        user_id,
                        callback=lambda job_id, status, result: self.profiles_db.update_job(job_id, status, result)
                    )
                    
                    # Salvează job-ul
                    if action_result.get("success"):
                        job_id = action_result.get("job_id")
                        self.profiles_db.add_job(user_id, action, job_id)
                    
                    # Generează răspuns
                    response_text = self.intent_planner.generate_response(intent_result, action_result)
                elif action == "status_nodes":
                    from controllers.node_controller import get_node_controller
                    node_controller = get_node_controller()
                    status = node_controller.get_system_status()
                    response_text = node_controller.format_status_message(status)
                elif action == "show_recent":
                    recent = self.profiles_db.get_recent_interactions(user_id, limit=5)
                    if recent:
                        response_text = f"Ultimele {len(recent)} interacțiuni: " + ". ".join([
                            f"{item.get('message', '')[:30]}..." for item in recent[:3]
                        ])
                    else:
                        response_text = "Nu ai interacțiuni recente."
                else:
                    response_text = self.intent_planner.generate_response(intent_result)
            else:
                # Nu s-a detectat acțiune clară - folosește orchestrator pentru răspuns inteligent
                from skills.actions import generate_agent_response
                response_text = generate_agent_response(message, {"user_id": user_id})
                action = None
            
            # Salvează interacțiunea
            self.profiles_db.add_interaction(user_id, message, response_text, action)
            self.context_memory.store_interaction(user_id, message, response_text, action)
            
            # Check auto-learning trigger
            try:
                from controllers.auto_trigger import get_auto_trigger
                auto_trigger = get_auto_trigger(threshold=50)
                trigger_result = auto_trigger.check_and_trigger_training()
                
                if trigger_result.get("triggered"):
                    response_text += f"\n\n🚀 Training started automatically - {trigger_result.get('interactions_processed', 0)} interactions processed!"
            except Exception as e:
                logger.warning(f"Auto-trigger check failed: {e}")
            
            # Actualizează preferințe dacă avem acțiune
            if action:
                self.profiles_db.update_preferred_action(user_id, action, True)
            
            # Generează audio
            audio_path = None
            if generate_audio:
                audio_path = self.tts_service.synthesize(response_text)
            
            return {
                "text": response_text,
                "audio_path": audio_path,
                "action": action,
                "confidence": confidence
            }
        except Exception as e:
            logger.error(f"Error processing chat: {e}")
            return {
                "text": f"Am întâmpinat o eroare: {str(e)}",
                "audio_path": None,
                "error": str(e)
            }

