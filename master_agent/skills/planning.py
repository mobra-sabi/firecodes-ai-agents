#!/usr/bin/env python3
"""
🧠 Planning & Intent Detection
Detectează intențiile utilizatorului și mapează către acțiuni
"""

import re
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Patterns pentru detectarea intențiilor
INTENT_PATTERNS = {
    "build_jsonl": [
        r"export.*jsonl",
        r"constru.*dataset",
        r"genereaz.*jsonl",
        r"creeaz.*dataset",
        r"build.*jsonl"
    ],
    "start_finetune": [
        r"porne.*fine.?tun",
        r"start.*fine.?tun",
        r"antren.*model",
        r"train.*model",
        r"fine.?tun.*acum"
    ],
    "update_qdrant": [
        r"actualiz.*qdrant",
        r"update.*qdrant",
        r"refresh.*qdrant",
        r"reîncarc.*vector",
        r"actualiz.*vector"
    ],
    "status_nodes": [
        r"status.*nod",
        r"verific.*nod",
        r"arat.*status",
        r"ce.*status",
        r"show.*status",
        r"verific.*sistem"
    ],
    "show_recent": [
        r"arat.*recent",
        r"ultime.*interac",
        r"istoric",
        r"ce.*am.*făcut",
        r"show.*recent"
    ],
    "summarize_feedback": [
        r"sumar",
        r"rezumat",
        r"feedback",
        r"concluz",
        r"summarize"
    ]
}

# Acțiuni disponibile
AVAILABLE_ACTIONS = [
    "build_jsonl",
    "start_finetune",
    "update_qdrant",
    "status_nodes",
    "show_recent",
    "summarize_feedback"
]


class IntentPlanner:
    """Planner pentru detectarea intențiilor și planificarea acțiunilor"""
    
    def __init__(self):
        self.compiled_patterns = {}
        for action, patterns in INTENT_PATTERNS.items():
            self.compiled_patterns[action] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def detect_intent(self, message: str, user_id: str = None, context_memory=None) -> Dict[str, Any]:
        """
        Detectează intenția din mesaj
        
        Args:
            message: Mesajul utilizatorului
            user_id: ID-ul utilizatorului (pentru context)
            context_memory: Instanță ContextMemory pentru similaritate
        
        Returns:
            Dict cu intent, action, confidence
        """
        message_lower = message.lower()
        
        # Verifică patternuri regex
        intent_scores = {}
        for action, patterns in self.compiled_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(message_lower):
                    score += 1
            if score > 0:
                intent_scores[action] = score
        
        # Verifică similaritate cu interacțiuni anterioare (dacă avem context)
        if context_memory and user_id:
            try:
                similar = context_memory.find_similar_intentions(user_id, message, limit=3)
                for item in similar:
                    action = item.get("action")
                    if action and action in AVAILABLE_ACTIONS:
                        score = item.get("score", 0)
                        if score > 0.7:  # Threshold pentru similaritate
                            intent_scores[action] = intent_scores.get(action, 0) + score
            except Exception as e:
                logger.warning(f"Error in similarity search: {e}")
        
        # Determină intenția cu cea mai mare încredere
        if intent_scores:
            best_action = max(intent_scores.items(), key=lambda x: x[1])
            confidence = best_action[1] / max(intent_scores.values()) if max(intent_scores.values()) > 0 else 0
            
            return {
                "intent": best_action[0],
                "action": best_action[0],
                "confidence": min(confidence, 1.0),
                "all_scores": intent_scores
            }
        
        # Nu s-a detectat intenție clară
        return {
            "intent": None,
            "action": None,
            "confidence": 0.0,
            "message": "Nu am înțeles exact ce vrei să fac. Poți reformula?"
        }
    
    def generate_response(self, intent_result: Dict[str, Any], action_result: Optional[Dict[str, Any]] = None) -> str:
        """
        Generează răspuns verbal bazat pe intenție și rezultat
        
        Args:
            intent_result: Rezultatul detectării intenției
            action_result: Rezultatul execuției acțiunii (dacă există)
        
        Returns:
            Textul răspunsului
        """
        intent = intent_result.get("intent")
        confidence = intent_result.get("confidence", 0)
        
        # Dacă nu s-a detectat intenție
        if not intent or confidence < 0.5:
            return intent_result.get("message", "Nu am înțeles exact ce vrei să fac. Poți reformula?")
        
        # Dacă avem rezultat de la acțiune
        if action_result:
            if action_result.get("success"):
                action = action_result.get("action")
                
                responses = {
                    "build_jsonl": "Am pornit exportul dataset-ului în format JSONL. Te voi anunța când se termină.",
                    "start_finetune": "Am pornit fine-tuningul modelului. Acest proces poate dura ceva timp. Te voi anunța când se termină.",
                    "update_qdrant": "Am pornit actualizarea bazei vectoriale Qdrant. Te voi anunța când se termină.",
                    "status_nodes": "Verific statusul nodurilor sistemului...",
                    "show_recent": "Îți arăt interacțiunile recente...",
                    "summarize_feedback": "Generez un rezumat al feedback-ului..."
                }
                
                return responses.get(action, f"Am executat acțiunea '{action}' cu succes.")
            else:
                error = action_result.get("error", "Eroare necunoscută")
                return f"Am întâmpinat o problemă la executarea acțiunii: {error}"
        
        # Răspunsuri pentru intenții detectate (înainte de execuție)
        if confidence < 0.8:
            action = intent_result.get("action")
            return f"Cred că vrei să {action}. Confirmi că să pornesc acțiunea?"
        
        # Încredere mare - confirmă direct
        action = intent_result.get("action")
        action_names = {
            "build_jsonl": "exportul dataset-ului JSONL",
            "start_finetune": "fine-tuningul modelului",
            "update_qdrant": "actualizarea bazei vectoriale Qdrant",
            "status_nodes": "verificarea statusului nodurilor",
            "show_recent": "afișarea interacțiunilor recente",
            "summarize_feedback": "generarea rezumatului"
        }
        
        return f"Am înțeles. Pornesc {action_names.get(action, action)} acum."


# Singleton instance
_intent_planner_instance = None

def get_intent_planner() -> IntentPlanner:
    """Get singleton instance"""
    global _intent_planner_instance
    if _intent_planner_instance is None:
        _intent_planner_instance = IntentPlanner()
    return _intent_planner_instance


