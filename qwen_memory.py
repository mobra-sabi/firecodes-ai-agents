#!/usr/bin/env python3
"""
Qwen Memory - Memorie persistentă pentru Qwen learning
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import requests

logger = logging.getLogger(__name__)

class QwenMemory:
    """Memorie persistentă pentru Qwen learning"""
    
    def __init__(self, agent_id: str = None):
        """
        Inițializează Qwen Memory pentru un agent specific
        
        Args:
            agent_id: ID-ul agentului (None pentru global)
        """
        self.agent_id = agent_id
        self.mongodb_uri = "mongodb://localhost:27017"
        self.qwen_url = "http://localhost:11434"
        self.mongo_client = MongoClient(self.mongodb_uri)
        self.db = self.mongo_client.ai_agents
        
        # Colecții separate pentru fiecare agent sau global
        if agent_id:
            # Colecții specifice pentru agent
            self.conversations_collection = self.db[f"qwen_conversations_{agent_id}"]
            self.learning_collection = self.db[f"qwen_learning_{agent_id}"]
            logger.info(f"✅ Qwen Memory initialized for agent {agent_id}")
        else:
            # Colecții globale (fallback)
            self.conversations_collection = self.db.qwen_conversations
            self.learning_collection = self.db.qwen_learning
        
    async def save_conversation(self, agent_id: str, user_message: str, qwen_response: str, context: Dict[str, Any] = None) -> bool:
        """Salvează o conversație pentru învățare"""
        try:
            conversation = {
                "agent_id": agent_id,
                "timestamp": datetime.now(timezone.utc),
                "user_message": user_message,
                "qwen_response": qwen_response,
                "context": context or {},
                "learning_potential": self._assess_learning_potential(user_message, qwen_response)
            }
            
            result = self.conversations_collection.insert_one(conversation)
            logger.info(f"Saved conversation for agent {agent_id}: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return False
    
    async def get_learning_context(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Obține contextul de învățare pentru un agent"""
        try:
            conversations = list(self.conversations_collection.find(
                {"agent_id": agent_id},
                sort=[("timestamp", -1)],
                limit=limit
            ))
            
            # Convertește ObjectId la string pentru JSON serialization
            for conv in conversations:
                conv["_id"] = str(conv["_id"])
                conv["timestamp"] = conv["timestamp"].isoformat()
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting learning context: {e}")
            return []
    
    async def learn_from_conversations(self, agent_id: str) -> Dict[str, Any]:
        """Qwen învață din conversațiile anterioare"""
        try:
            # Obține conversațiile recente
            conversations = await self.get_learning_context(agent_id, limit=20)
            
            if not conversations:
                return {
                    "status": "no_data",
                    "message": "No conversations to learn from",
                    "learned_patterns": []
                }
            
            # Analizează pattern-urile de conversație
            patterns = self._analyze_conversation_patterns(conversations)
            
            # Salvează pattern-urile învățate
            learning_entry = {
                "agent_id": agent_id,
                "timestamp": datetime.now(timezone.utc),
                "patterns": patterns,
                "conversation_count": len(conversations),
                "learning_score": self._calculate_learning_score(patterns)
            }
            
            self.learning_collection.insert_one(learning_entry)
            
            return {
                "status": "success",
                "message": f"Learned from {len(conversations)} conversations",
                "learned_patterns": patterns,
                "learning_score": learning_entry["learning_score"]
            }
            
        except Exception as e:
            logger.error(f"Error in learning process: {e}")
            return {
                "status": "error",
                "message": str(e),
                "learned_patterns": []
            }
    
    async def get_enhanced_prompt(self, agent_id: str, base_prompt: str, user_message: str) -> str:
        """Îmbunătățește prompt-ul cu contextul de învățare"""
        try:
            # Obține contextul de învățare
            learning_context = await self.get_learning_context(agent_id, limit=5)
            
            if not learning_context:
                return base_prompt
            
            # Construiește contextul de învățare
            learning_summary = self._build_learning_summary(learning_context)
            
            # Îmbunătățește prompt-ul
            enhanced_prompt = f"""
{base_prompt}

CONTEXT DE ÎNVĂȚARE:
{learning_summary}

INSTRUCȚIUNI PENTRU ÎNVĂȚARE:
- Folosește experiența din conversațiile anterioare pentru a răspunde mai bine
- Adaptează stilul de răspuns la preferințele utilizatorului
- Menține consistența cu răspunsurile anterioare
- Îmbunătățește răspunsul pe baza feedback-ului implicit din conversații
"""
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}")
            return base_prompt
    
    def _assess_learning_potential(self, user_message: str, qwen_response: str) -> float:
        """Evaluează potențialul de învățare al unei conversații"""
        score = 0.0
        
        # Factori care cresc potențialul de învățare
        if len(user_message) > 50:  # Mesaje detaliate
            score += 0.2
        
        if len(qwen_response) > 100:  # Răspunsuri detaliate
            score += 0.2
        
        if any(keyword in user_message.lower() for keyword in ['cum', 'ce', 'de ce', 'când', 'unde']):
            score += 0.2  # Întrebări specifice
        
        if any(keyword in qwen_response.lower() for keyword in ['recomand', 'sugerez', 'pot să', 'te ajut']):
            score += 0.2  # Răspunsuri utile
        
        if 'tehnica-antifoc' in user_message.lower() or 'tehnica-antifoc' in qwen_response.lower():
            score += 0.2  # Context specific site
        
        return min(score, 1.0)
    
    def _analyze_conversation_patterns(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analizează pattern-urile din conversații"""
        patterns = {
            "common_questions": [],
            "response_styles": [],
            "user_preferences": [],
            "domain_specific_terms": []
        }
        
        # Analizează întrebările comune
        questions = [conv["user_message"] for conv in conversations]
        common_words = {}
        for question in questions:
            words = question.lower().split()
            for word in words:
                if len(word) > 3:  # Ignoră cuvintele scurte
                    common_words[word] = common_words.get(word, 0) + 1
        
        patterns["common_questions"] = sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Analizează stilul de răspuns
        responses = [conv["qwen_response"] for conv in conversations]
        response_lengths = [len(resp) for resp in responses]
        patterns["response_styles"] = {
            "avg_length": sum(response_lengths) / len(response_lengths) if response_lengths else 0,
            "uses_emojis": sum(1 for resp in responses if any(emoji in resp for emoji in ['🔍', '📋', '💡', '📞', '⭐'])),
            "uses_formatting": sum(1 for resp in responses if '**' in resp or '•' in resp)
        }
        
        # Analizează termenii specifici domeniului
        domain_terms = ['antifoc', 'protecție', 'foc', 'matări', 'vopsea', 'termospumantă', 'certificare', 'isu']
        for term in domain_terms:
            count = sum(1 for conv in conversations if term in conv["user_message"].lower() or term in conv["qwen_response"].lower())
            if count > 0:
                patterns["domain_specific_terms"].append({"term": term, "frequency": count})
        
        return patterns
    
    def _calculate_learning_score(self, patterns: Dict[str, Any]) -> float:
        """Calculează scorul de învățare"""
        score = 0.0
        
        # Scor bazat pe întrebările comune
        if patterns["common_questions"]:
            score += 0.3
        
        # Scor bazat pe stilul de răspuns
        if patterns["response_styles"]["avg_length"] > 200:
            score += 0.2
        
        if patterns["response_styles"]["uses_emojis"] > 0:
            score += 0.2
        
        if patterns["response_styles"]["uses_formatting"] > 0:
            score += 0.2
        
        # Scor bazat pe termenii specifici
        if patterns["domain_specific_terms"]:
            score += 0.1
        
        return min(score, 1.0)
    
    def _build_learning_summary(self, conversations: List[Dict[str, Any]]) -> str:
        """Construiește un rezumat al învățării"""
        if not conversations:
            return "Nu există conversații anterioare pentru învățare."
        
        summary_parts = []
        
        # Rezumat al întrebărilor recente
        recent_questions = [conv["user_message"][:100] + "..." if len(conv["user_message"]) > 100 else conv["user_message"] 
                          for conv in conversations[:3]]
        summary_parts.append(f"Întrebări recente: {'; '.join(recent_questions)}")
        
        # Rezumat al stilului de răspuns
        avg_length = sum(len(conv["qwen_response"]) for conv in conversations) / len(conversations)
        summary_parts.append(f"Lungimea medie a răspunsurilor: {int(avg_length)} caractere")
        
        # Rezumat al contextului specific
        domain_mentions = sum(1 for conv in conversations 
                            if any(term in conv["user_message"].lower() or term in conv["qwen_response"].lower() 
                                 for term in ['antifoc', 'protecție', 'foc']))
        summary_parts.append(f"Context specific domeniu: {domain_mentions} mențiuni")
        
        return "\n".join(summary_parts)

# Funcție helper pentru a rula memoria
async def save_qwen_conversation(agent_id: str, user_message: str, qwen_response: str, context: Dict[str, Any] = None) -> bool:
    """Salvează o conversație Qwen"""
    memory = QwenMemory()
    return await memory.save_conversation(agent_id, user_message, qwen_response, context)

async def get_qwen_learning_context(agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Obține contextul de învățare Qwen"""
    memory = QwenMemory()
    return await memory.get_learning_context(agent_id, limit)

if __name__ == "__main__":
    import asyncio
    
    async def test_memory():
        memory = QwenMemory()
        
        # Testează salvarea unei conversații
        success = await memory.save_conversation(
            "68e629bb5a7057c4b1b2f4da",
            "Ce produse oferiți?",
            "Oferim matări antifoc, vopsea termospumantă și uși rezistente la foc.",
            {"domain": "tehnica-antifoc.ro"}
        )
        print(f"Conversation saved: {success}")
        
        # Testează învățarea
        learning_result = await memory.learn_from_conversations("68e629bb5a7057c4b1b2f4da")
        print(f"Learning result: {learning_result}")
    
    asyncio.run(test_memory())

