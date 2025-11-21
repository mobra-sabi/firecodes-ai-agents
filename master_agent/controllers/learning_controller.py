#!/usr/bin/env python3
"""
🧠 Learning Controller
Gestionează învățarea comportamentală automată
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class LearningController:
    """Controller pentru învățare comportamentală"""
    
    def __init__(self, profiles_db, context_memory):
        self.profiles_db = profiles_db
        self.context_memory = context_memory
    
    def learn_from_interactions(self, user_id: str) -> Dict[str, Any]:
        """
        Analizează interacțiunile utilizatorului și învață patternuri
        
        Args:
            user_id: ID-ul utilizatorului
        
        Returns:
            Dict cu patternuri învățate
        """
        try:
            # Obține profilul
            profile = self.profiles_db.get_profile(user_id)
            
            # Obține interacțiunile recente
            recent = self.profiles_db.get_recent_interactions(user_id, limit=50)
            
            # Analizează patternuri din Qdrant
            patterns = self.context_memory.learn_patterns(user_id)
            
            # Combină cu preferințele existente
            preferred_actions = profile.get("preferred_actions", {})
            
            # Actualizează patternuri
            learned_patterns = {
                "most_common_actions": patterns.get("most_common_actions", {}),
                "preferred_hour": patterns.get("preferred_hour"),
                "total_interactions": len(recent),
                "success_rate": profile.get("success_rate", 0),
                "preferred_actions": preferred_actions
            }
            
            logger.info(f"Learned patterns for user {user_id}: {learned_patterns}")
            
            return learned_patterns
        except Exception as e:
            logger.error(f"Error learning from interactions: {e}")
            return {}
    
    def suggest_action(self, user_id: str, current_time_hour: int = None) -> Dict[str, Any]:
        """
        Sugerează o acțiune bazată pe patternurile utilizatorului
        
        Args:
            user_id: ID-ul utilizatorului
            current_time_hour: Ora curentă (0-23)
        
        Returns:
            Dict cu sugestie
        """
        try:
            patterns = self.learn_from_interactions(user_id)
            
            # Verifică dacă există patternuri
            if not patterns.get("most_common_actions"):
                return {
                    "suggest": False,
                    "message": "Nu am suficiente date pentru sugestii"
                }
            
            # Găsește acțiunea cea mai comună
            most_common = list(patterns.get("most_common_actions", {}).items())
            if not most_common:
                return {"suggest": False}
            
            action, count = most_common[0]
            
            # Verifică dacă e timpul preferat
            preferred_hour = patterns.get("preferred_hour")
            suggest_now = True
            
            if preferred_hour and current_time_hour is not None:
                # Sugerează dacă suntem în intervalul preferat (±1 oră)
                if abs(current_time_hour - preferred_hour) > 1:
                    suggest_now = False
            
            if suggest_now:
                action_names = {
                    "build_jsonl": "exportul dataset-ului JSONL",
                    "start_finetune": "fine-tuningul modelului",
                    "update_qdrant": "actualizarea bazei vectoriale Qdrant"
                }
                
                return {
                    "suggest": True,
                    "action": action,
                    "message": f"De obicei rulezi {action_names.get(action, action)} la această oră. Vrei să o pornesc acum?",
                    "confidence": min(count / 10, 1.0)  # Normalizează
                }
            
            return {"suggest": False}
        except Exception as e:
            logger.error(f"Error suggesting action: {e}")
            return {"suggest": False}


# Singleton instance
_learning_controller_instance = None

def get_learning_controller(profiles_db, context_memory) -> LearningController:
    """Get singleton instance"""
    global _learning_controller_instance
    if _learning_controller_instance is None:
        _learning_controller_instance = LearningController(profiles_db, context_memory)
    return _learning_controller_instance


