#!/usr/bin/env python3
"""
Chat Memory Integration - Salvare chat-uri și învățare Qwen cu LangChain
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import os

# LangChain imports pentru indexare și învățare - adaptat pentru versiuni diferite
try:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
except ImportError:
    try:
        from langchain.schema import HumanMessage, AIMessage, SystemMessage
    except ImportError:
        HumanMessage = AIMessage = SystemMessage = None

try:
    from langchain.memory import ConversationBufferMemory
    from langchain.chains import ConversationChain
    from langchain.prompts import PromptTemplate
except ImportError:
    ConversationBufferMemory = ConversationChain = PromptTemplate = None

try:
    from langchain_community.vectorstores import Qdrant as LangchainQdrant
except ImportError:
    LangchainQdrant = None

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    HuggingFaceEmbeddings = None
from qdrant_client import QdrantClient

# Qwen Memory
from qwen_memory import QwenMemory

load_dotenv(override=True)

logger = logging.getLogger(__name__)

class ChatMemoryIntegration:
    """Integrare chat memory cu LangChain și Qwen learning"""
    
    def __init__(self, agent_id: str = None):
        """
        Inițializează integrarea chat memory pentru un agent specific
        
        Args:
            agent_id: ID-ul agentului (None pentru global)
        """
        self.agent_id = agent_id
        # MongoDB pentru chat-uri
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.mongo_client = MongoClient(self.mongo_uri)
        self.db = self.mongo_client.ai_agents_db
        self.conversations_collection = self.db.conversations
        self.agent_chat_history = self.db.agent_chat_history  # Nouă colecție pentru istoric detaliat
        
        # Qwen Memory pentru învățare - separată pentru fiecare agent
        self.qwen_memory = QwenMemory(agent_id=agent_id) if agent_id else QwenMemory()
        
        # LangChain embeddings pentru indexare
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Qdrant pentru vector store
        self.qdrant_url = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.qdrant_client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key,
            prefer_grpc=True,
            force_disable_check_same_thread=True
        )
    
    async def save_chat_interaction(
        self,
        agent_id: str,
        user_message: str,
        assistant_response: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Salvează o interacțiune de chat în MongoDB și pregătește pentru învățare
        """
        try:
            # 1. Salvează în MongoDB pentru istoric
            chat_doc = {
                "agent_id": agent_id,
                "timestamp": datetime.now(timezone.utc),
                "user_message": user_message,
                "assistant_response": assistant_response,
                "metadata": metadata or {},
                "session_id": metadata.get("session_id") if metadata else None,
                "message_index": await self._get_next_message_index(agent_id),
                "learning_potential": self._assess_learning_potential(user_message, assistant_response)
            }
            
            result = self.agent_chat_history.insert_one(chat_doc)
            logger.info(f"✅ Chat interaction saved for agent {agent_id}: {result.inserted_id}")
            
            # 2. Salvează în Qwen Memory pentru învățare
            await self.qwen_memory.save_conversation(
                agent_id=agent_id,
                user_message=user_message,
                qwen_response=assistant_response,
                context={
                    "metadata": metadata,
                    "chat_id": str(result.inserted_id),
                    "timestamp": chat_doc["timestamp"].isoformat()
                }
            )
            
            # 3. Indexează în Qdrant pentru search (opțional - pentru conversații importante)
            if chat_doc["learning_potential"] > 0.5:
                await self._index_conversation_for_search(agent_id, user_message, assistant_response)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving chat interaction: {e}")
            return False
    
    async def _get_next_message_index(self, agent_id: str) -> int:
        """Obține următorul index de mesaj pentru un agent"""
        try:
            last_chat = self.agent_chat_history.find_one(
                {"agent_id": agent_id},
                sort=[("message_index", -1)]
            )
            return (last_chat.get("message_index", 0) + 1) if last_chat else 1
        except:
            return 1
    
    def _assess_learning_potential(self, user_message: str, response: str) -> float:
        """Evaluează potențialul de învățare al conversației"""
        score = 0.0
        
        # Factori care cresc potențialul
        if len(user_message) > 50:
            score += 0.2
        if len(response) > 100:
            score += 0.2
        if any(keyword in user_message.lower() for keyword in ['cum', 'ce', 'de ce', 'când', 'unde', 'explică', 'detaliază']):
            score += 0.3
        if any(keyword in response.lower() for keyword in ['recomand', 'sugerez', 'pot să', 'te ajut', 'important', 'atenție']):
            score += 0.3
        
        return min(score, 1.0)
    
    async def _index_conversation_for_search(self, agent_id: str, user_message: str, response: str):
        """Indexează conversația importantă în Qdrant pentru search"""
        try:
            collection_name = f"agent_{agent_id}_conversations"
            
            # Creează colecție dacă nu există
            try:
                self.qdrant_client.get_collection(collection_name)
            except:
                from qdrant_client.models import Distance, VectorParams
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
                )
            
            # Generează embeddings pentru mesajul utilizatorului
            user_embedding = self.embeddings.embed_query(user_message)
            
            # Salvează în Qdrant
            from qdrant_client.models import PointStruct
            point = PointStruct(
                id=int(datetime.now(timezone.utc).timestamp() * 1000),  # ID bazat pe timestamp
                vector=user_embedding,
                payload={
                    "agent_id": agent_id,
                    "user_message": user_message,
                    "assistant_response": response,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            logger.info(f"✅ Conversation indexed in Qdrant for agent {agent_id}")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to index conversation in Qdrant: {e}")
    
    async def get_conversation_history(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """Obține istoricul conversațiilor pentru un agent"""
        try:
            conversations = list(self.agent_chat_history.find(
                {"agent_id": agent_id},
                sort=[("timestamp", -1)],
                limit=limit
            ))
            
            # Convertește ObjectId și datetime pentru JSON
            for conv in conversations:
                conv["_id"] = str(conv["_id"])
                conv["timestamp"] = conv["timestamp"].isoformat()
            
            return list(reversed(conversations))  # Ordine cronologică
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    async def get_learning_context_for_qwen(self, agent_id: str) -> str:
        """
        Obține contextul de învățare pentru Qwen din conversațiile anterioare
        """
        try:
            # Obține conversațiile recente
            conversations = await self.get_conversation_history(agent_id, limit=10)
            
            if not conversations:
                return "Nu există conversații anterioare pentru învățare."
            
            # Construiește contextul
            context_parts = []
            context_parts.append(f"Conversații anterioare cu utilizatorul ({len(conversations)} mesaje):\n")
            
            for i, conv in enumerate(conversations[-5:], 1):  # Ultimele 5 conversații
                context_parts.append(f"{i}. Utilizator: {conv['user_message'][:150]}...")
                context_parts.append(f"   Răspuns: {conv['assistant_response'][:150]}...")
                context_parts.append("")
            
            # Adaugă pattern-uri învățate
            learning_result = await self.qwen_memory.learn_from_conversations(agent_id)
            if learning_result.get("status") == "success":
                patterns = learning_result.get("learned_patterns", {})
                if patterns:
                    context_parts.append("Pattern-uri învățate:")
                    if patterns.get("common_questions"):
                        context_parts.append(f"  - Întrebări comune: {patterns['common_questions'][:3]}")
                    if patterns.get("domain_specific_terms"):
                        context_parts.append(f"  - Termeni specifici: {patterns['domain_specific_terms']}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting learning context: {e}")
            return ""
    
    async def enhance_response_with_learning(
        self,
        agent_id: str,
        base_response: str,
        user_message: str
    ) -> str:
        """
        Îmbunătățește răspunsul folosind contextul de învățare
        """
        try:
            # Obține contextul de învățare
            learning_context = await self.get_learning_context_for_qwen(agent_id)
            
            if not learning_context or "Nu există conversații" in learning_context:
                return base_response
            
            # Folosește Qwen Memory pentru a îmbunătăți prompt-ul
            enhanced_prompt = await self.qwen_memory.get_enhanced_prompt(
                agent_id=agent_id,
                base_prompt=base_response,
                user_message=user_message
            )
            
            return enhanced_prompt if enhanced_prompt != base_response else base_response
            
        except Exception as e:
            logger.warning(f"Failed to enhance response with learning: {e}")
            return base_response

# Funcții helper pentru integrare ușoară - cu Qwen Memory per agent
_agent_memory_cache: Dict[str, ChatMemoryIntegration] = {}

def get_chat_memory_for_agent(agent_id: str) -> ChatMemoryIntegration:
    """Obține sau creează ChatMemoryIntegration pentru un agent specific"""
    if agent_id not in _agent_memory_cache:
        _agent_memory_cache[agent_id] = ChatMemoryIntegration(agent_id=agent_id)
        logger.info(f"✅ Created ChatMemoryIntegration for agent {agent_id}")
    return _agent_memory_cache[agent_id]

async def save_chat(agent_id: str, user_message: str, response: str, metadata: Dict = None) -> bool:
    """Helper pentru salvarea chat-ului - cu Qwen Memory per agent"""
    chat_memory = get_chat_memory_for_agent(agent_id)
    return await chat_memory.save_chat_interaction(agent_id, user_message, response, metadata)

async def get_chat_history(agent_id: str, limit: int = 10) -> List[Dict]:
    """Helper pentru obținerea istoricului - cu Qwen Memory per agent"""
    chat_memory = get_chat_memory_for_agent(agent_id)
    return await chat_memory.get_conversation_history(agent_id, limit)

async def enhance_response(agent_id: str, base_response: str, user_message: str) -> str:
    """Helper pentru îmbunătățirea răspunsului cu învățare - cu Qwen Memory per agent"""
    chat_memory = get_chat_memory_for_agent(agent_id)
    return await chat_memory.enhance_response_with_learning(agent_id, base_response, user_message)

if __name__ == "__main__":
    async def test():
        test_agent_id = "690478e8a55790fced0e6b75"
        
        # Test salvare
        success = await save_chat(
            agent_id=test_agent_id,
            user_message="Ce produse oferiți?",
            response="Oferim matări antifoc, vopsea termospumantă și uși rezistente la foc.",
            metadata={"session_id": "test123"}
        )
        print(f"✅ Saved: {success}")
        
        # Test istoric
        history = await get_chat_history(test_agent_id, limit=5)
        print(f"✅ History: {len(history)} conversations")
        
        # Test learning context
        context = await chat_memory.get_learning_context_for_qwen(test_agent_id)
        print(f"✅ Learning context length: {len(context)}")
    
    asyncio.run(test())

