"""
Memory Manager - Manager pentru sincronizare Mongo ↔ LangChain Memory

Conectează chat_memory_integration.py cu LangChain Memory (ConversationBufferMemory).
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import os

# LangChain Memory imports
try:
    from langchain_classic.memory import ConversationBufferMemory
except ImportError:
    try:
        from langchain.memory import ConversationBufferMemory
    except ImportError:
        ConversationBufferMemory = None

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")


class MemoryManager:
    """
    Manager pentru sincronizare între MongoDB și LangChain Memory
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        # MongoDB
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client.ai_agents_db
        self.conversations_collection = self.db[f"agent_{agent_id}_conversations"]
        self.memory_collection = self.db[f"agent_{agent_id}_memory"]
        
        # LangChain Memory
        if ConversationBufferMemory:
            self.langchain_memory = ConversationBufferMemory(
                memory_key="history",
                return_messages=True,
                input_key="input"
            )
        else:
            self.langchain_memory = None
            logger.warning("⚠️ ConversationBufferMemory not available")
        
        # Încarcă istoricul existent
        self._load_from_mongo()
        
        logger.info(f"✅ MemoryManager initialized for agent {agent_id}")
    
    def _load_from_mongo(self):
        """Încarcă istoricul conversațiilor din MongoDB în LangChain Memory"""
        if not self.langchain_memory:
            return
        
        try:
            # Obține conversațiile recente (ultimele 50)
            conversations = list(
                self.conversations_collection.find()
                .sort("timestamp", -1)
                .limit(50)
            )
            
            # Adaugă în LangChain Memory (în ordine inversă pentru a păstra cronologia)
            for conv in reversed(conversations):
                question = conv.get("question", "")
                answer = conv.get("answer", "")
                
                if question and answer:
                    self.langchain_memory.chat_memory.add_user_message(question)
                    self.langchain_memory.chat_memory.add_ai_message(answer)
            
            logger.info(f"✅ Loaded {len(conversations)} conversations into LangChain memory")
            
        except Exception as e:
            logger.error(f"❌ Error loading memory from MongoDB: {e}")
    
    def get_langchain_memory(self) -> Optional[Any]:
        """Obține instanța LangChain Memory"""
        return self.langchain_memory
    
    def load_history(self, history: List[Dict[str, str]]):
        """
        Încarcă istoric din lista de dicționare
        
        Args:
            history: Lista cu {"role": "user|assistant", "content": "..."}
        """
        if not self.langchain_memory:
            return
        
        try:
            for msg in history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                
                if role == "user":
                    self.langchain_memory.chat_memory.add_user_message(content)
                elif role == "assistant":
                    self.langchain_memory.chat_memory.add_ai_message(content)
            
        except Exception as e:
            logger.error(f"❌ Error loading history: {e}")
    
    async def save_conversation(self, question: str, answer: str):
        """
        Salvează o conversație în MongoDB
        
        Args:
            question: Întrebarea utilizatorului
            answer: Răspunsul agentului
        """
        try:
            # Salvează în MongoDB
            self.conversations_collection.insert_one({
                "agent_id": self.agent_id,
                "question": question,
                "answer": answer,
                "timestamp": datetime.now(timezone.utc)
            })
            
            # Actualizează LangChain Memory (dacă nu e deja adăugat)
            if self.langchain_memory:
                # Verifică dacă mesajele nu sunt deja în memorie
                messages = self.langchain_memory.chat_memory.messages
                if not messages or messages[-2].content != question:
                    self.langchain_memory.chat_memory.add_user_message(question)
                    self.langchain_memory.chat_memory.add_ai_message(answer)
            
            # Salvează snapshot-ul memoriei în MongoDB (periodic)
            await self._save_memory_snapshot()
            
        except Exception as e:
            logger.error(f"❌ Error saving conversation: {e}")
    
    async def _save_memory_snapshot(self):
        """Salvează snapshot-ul memoriei LangChain în MongoDB"""
        if not self.langchain_memory:
            return
        
        try:
            # Obține mesajele din memorie
            messages = self.langchain_memory.chat_memory.messages
            
            # Salvează snapshot
            self.memory_collection.replace_one(
                {"agent_id": self.agent_id, "type": "langchain_buffer"},
                {
                    "agent_id": self.agent_id,
                    "type": "langchain_buffer",
                    "messages_count": len(messages),
                    "last_updated": datetime.now(timezone.utc),
                    "memory_type": "ConversationBufferMemory"
                },
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"❌ Error saving memory snapshot: {e}")
    
    def is_initialized(self) -> bool:
        """Verifică dacă memoria este inițializată"""
        return self.langchain_memory is not None
    
    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obține conversațiile recente
        
        Args:
            limit: Număr maxim de conversații
        
        Returns:
            Lista de conversații
        """
        try:
            conversations = list(
                self.conversations_collection.find()
                .sort("timestamp", -1)
                .limit(limit)
            )
            
            for conv in conversations:
                conv["_id"] = str(conv["_id"])
                if isinstance(conv.get("timestamp"), datetime):
                    conv["timestamp"] = conv["timestamp"].isoformat()
            
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Error getting recent conversations: {e}")
            return []

