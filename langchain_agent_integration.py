#!/usr/bin/env python3
"""
LangChain Agent Integration - Integrare completă LangChain pentru fiecare agent
Fiecare agent are propria memorie, conversații și învățare în cadrul LangChain
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import os
from llm_orchestrator import get_orchestrator

# LangChain imports - adaptat pentru versiuni diferite
try:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
except ImportError:
    try:
        from langchain.schema import HumanMessage, AIMessage, SystemMessage
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    except ImportError:
        # Fallback minimal
        HumanMessage = AIMessage = SystemMessage = None
        ChatPromptTemplate = MessagesPlaceholder = None

# Setup logger EARLY (before using it in imports)
logger = logging.getLogger(__name__)

# LangChain Memory și Chains - încearcă mai multe locații
try:
    from langchain_classic.memory import ConversationBufferMemory, ConversationSummaryMemory
    from langchain_classic.chains import ConversationChain
    logger.info("✅ Using langchain-classic for memory and chains")
except ImportError:
    try:
        from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
        from langchain.chains import ConversationChain
        logger.info("✅ Using langchain for memory and chains")
    except ImportError:
        ConversationBufferMemory = ConversationSummaryMemory = ConversationChain = None
        logger.warning("⚠️ ConversationBufferMemory and ConversationChain not available - using fallback")
from langchain_community.vectorstores import Qdrant as LangchainQdrant
from langchain_community.chat_models import ChatOpenAI
from langchain_openai import ChatOpenAI as LangChainChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings as LCHFEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Qwen Memory pentru învățare
from qwen_memory import QwenMemory

load_dotenv(override=True)

# Logger already defined above (line ~31)

class LangChainAgent:
    """
    Agent integrat complet în LangChain
    Fiecare agent are propria memorie, conversații și învățare
    """
    
    def __init__(self, agent_id: str, agent_config: Dict[str, Any]):
        self.agent_id = agent_id
        self.agent_config = agent_config
        
        # 🎭 LLM Orchestrator cu DeepSeek + fallback
        self.llm_orchestrator = get_orchestrator()
        logger.info(f"🎭 LLM Orchestrator initialized for agent {agent_id}")
        
        # MongoDB pentru chat-uri și memorie
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.mongo_client = MongoClient(self.mongo_uri)
        self.db = self.mongo_client.ai_agents_db
        self.agent_memory_collection = self.db[f"agent_{agent_id}_memory"]  # Colecție specifică agent
        self.conversations_collection = self.db[f"agent_{agent_id}_conversations"]  # Conversații specifice
        
        # Qwen Memory pentru învățare - separată pentru fiecare agent
        self.qwen_memory = QwenMemory(agent_id=agent_id)
        logger.info(f"✅ Qwen Memory initialized for agent {agent_id}")
        
        # LangChain Memory - Memorie separată pentru fiecare agent (dacă disponibil)
        if ConversationBufferMemory:
            self.memory = ConversationBufferMemory(
                memory_key="history",
                return_messages=True,
                input_key="input"
            )
        else:
            self.memory = None
            logger.warning(f"⚠️ ConversationBufferMemory not available - using fallback")
        
        # LangChain Summarization Memory pentru conversații lungi (dacă disponibil)
        if ConversationSummaryMemory:
            llm = self._get_llm()
            if llm:
                self.summary_memory = ConversationSummaryMemory(
                    llm=llm,
                    memory_key="chat_history",
                    return_messages=True
                )
            else:
                self.summary_memory = None
        else:
            self.summary_memory = None
        
        # Setup embeddings pentru vector store
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Qdrant pentru vector store specific agent
        self.qdrant_url = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = f"agent_{agent_id}_langchain"
        
        # Setup Qdrant client
        self.qdrant_client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key,
            prefer_grpc=True,
            force_disable_check_same_thread=True
        )
        
        # Vector store LangChain pentru fiecare agent
        self.vectorstore = None
        
        # LLM pentru LangChain (folosește DeepSeek sau Qwen)
        self.llm = self._get_llm()
        
        # LangChain Conversation Chain
        self.conversation_chain = None
        
        # Initialize vector store
        self._initialize_vector_store()
        
        # Initialize conversation chain
        self._initialize_conversation_chain()
        
        # Load memory from MongoDB
        asyncio.create_task(self._load_memory_from_db())
    
    def _get_llm(self):
        """Obține LLM-ul pentru LangChain (DeepSeek sau Qwen)"""
        try:
            # Folosește DeepSeek pentru LangChain
            openai_api_key = os.getenv("OPENAI_API_KEY")
            openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
            
            return LangChainChatOpenAI(
                model=os.getenv("LLM_MODEL", "deepseek-chat"),
                openai_api_key=openai_api_key,
                openai_api_base=openai_base_url,
                temperature=0.7,
                max_tokens=2000
            )
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            return None
    
    def _initialize_vector_store(self):
        """Inițializează vector store LangChain pentru agent"""
        try:
            # Verifică dacă colecția există
            try:
                collection_info = self.qdrant_client.get_collection(self.collection_name)
                points = getattr(collection_info, "points_count", getattr(collection_info, "vectors_count", 0))
                logger.info(f"✅ Vector store exists for agent {self.agent_id}: {points} points")
            except:
                # Creează colecție nouă
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
                )
                logger.info(f"✅ Created vector store for agent {self.agent_id}")
            
            # Creează LangChain vector store
            self.vectorstore = LangchainQdrant(
                client=self.qdrant_client,
                collection_name=self.collection_name,
                embedding=self.embeddings
            )
            
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
            self.vectorstore = None
    
    def _initialize_conversation_chain(self):
        """Inițializează LangChain Conversation Chain pentru agent"""
        try:
            if not self.llm:
                logger.warning(f"⚠️ LLM not available for agent {self.agent_id}")
                return
            
            # Prompt template pentru conversație cu context agent (dacă LangChain este disponibil)
            if ChatPromptTemplate and self.memory:
                domain = self.agent_config.get("domain", "unknown")
                agent_name = self.agent_config.get("name", "Agent")
                
                try:
                    prompt_template = ChatPromptTemplate.from_messages([
                        SystemMessage(content=f"""Ești {agent_name}, un asistent AI specializat pentru {domain}.
Răspunde întotdeauna în limba română, profesionist și util.
Folosește contextul din conversațiile anterioare pentru a răspunde mai bine.
Adaptează stilul la preferințele utilizatorului pe baza conversațiilor anterioare."""),
                        MessagesPlaceholder(variable_name="history"),
                        HumanMessage(content="{input}")
                    ])
                    
                    # Creează Conversation Chain cu memorie (dacă disponibil)
                    if ConversationChain:
                        self.conversation_chain = ConversationChain(
                            llm=self.llm,
                            memory=self.memory,
                            prompt=prompt_template,
                            verbose=True
                        )
                    else:
                        self.conversation_chain = None
                        logger.warning(f"⚠️ ConversationChain not available")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to create LangChain chain: {e}")
                    self.conversation_chain = None
            else:
                logger.warning(f"⚠️ LangChain components not available - using fallback")
                self.conversation_chain = None
            
            logger.info(f"✅ Conversation chain initialized for agent {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Error initializing conversation chain: {e}")
            self.conversation_chain = None
    
    async def _load_memory_from_db(self):
        """Încarcă memoria din MongoDB în LangChain Memory"""
        try:
            # Obține ultimele conversații din MongoDB
            conversations = list(self.conversations_collection.find(
                {"agent_id": self.agent_id},
                sort=[("timestamp", 1)],
                limit=20  # Ultimele 20 conversații
            ))
            
            # Adaugă conversațiile în LangChain Memory
            for conv in conversations:
                user_msg = conv.get("user_message", "")
                assistant_msg = conv.get("assistant_response", "")
                
                if user_msg and assistant_msg:
                    self.memory.chat_memory.add_user_message(user_msg)
                    self.memory.chat_memory.add_ai_message(assistant_msg)
            
            logger.info(f"✅ Loaded {len(conversations)} conversations into LangChain memory for agent {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Error loading memory from DB: {e}")
    
    async def save_memory_to_db(self):
        """Salvează memoria LangChain în MongoDB"""
        try:
            # Obține istoricul din LangChain Memory
            memory_history = self.memory.chat_memory.messages
            
            # Salvează în MongoDB
            memory_doc = {
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc),
                "memory_history": [
                    {"role": msg.__class__.__name__.replace("Message", "").lower(), "content": msg.content}
                    for msg in memory_history
                ],
                "memory_type": "langchain_conversation_buffer"
            }
            
            self.agent_memory_collection.insert_one(memory_doc)
            logger.info(f"✅ Saved LangChain memory to MongoDB for agent {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Error saving memory to DB: {e}")
    
    async def process_message(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Procesează un mesaj prin LangChain Conversation Chain
        """
        try:
            # 1. Obține contextul de învățare Qwen
            learning_context = await self.qwen_memory.get_learning_context(self.agent_id, limit=5)
            
            # 2. Construiește prompt-ul cu context
            enhanced_input = user_message
            if learning_context:
                # Adaugă context de învățare
                context_summary = "\n".join([
                    f"Conversație anterioară: {conv['user_message'][:100]}... → {conv['qwen_response'][:100]}..."
                    for conv in learning_context[:3]
                ])
                enhanced_input = f"""CONTEXT DE ÎNVĂȚARE:
{context_summary}

ÎNTREBARE ACTUALĂ:
{user_message}
"""
            
            # 3. Generează răspuns folosind LangChain Conversation Chain (dacă disponibil)
            if self.conversation_chain and self.llm:
                try:
                    response = self.conversation_chain.predict(input=enhanced_input)
                except Exception as e:
                    logger.warning(f"⚠️ LangChain chain failed: {e}")
                    # Fallback: folosește LLM direct
                    if hasattr(self.llm, 'invoke'):
                        messages = [
                            SystemMessage(content=f"Răspunde în română, profesionist și util pentru {self.agent_config.get('domain', 'unknown')}"),
                            HumanMessage(content=enhanced_input)
                        ] if SystemMessage else []
                        if messages:
                            response_obj = self.llm.invoke(messages)
                            response = response_obj.content if hasattr(response_obj, 'content') else str(response_obj)
                        else:
                            response = f"Răspuns pentru agent {self.agent_id}: {user_message}"
                    else:
                        response = f"Răspuns pentru agent {self.agent_id}: {user_message}"
            else:
                # Fallback dacă LangChain nu este disponibil
                response = f"Răspuns pentru agent {self.agent_id}: {user_message}"
            
            # 4. Salvează conversația în MongoDB
            await self._save_conversation(user_message, response, context)
            
            # 5. Indexează conversația în vector store (dacă importantă)
            await self._index_conversation(user_message, response)
            
            # 6. Activează învățarea Qwen - salvează conversația pentru învățare
            try:
                await self.qwen_memory.save_conversation(
                    agent_id=self.agent_id,
                    user_message=user_message,
                    qwen_response=response,
                    context=context
                )
                logger.info(f"✅ Conversation saved in Qwen Memory for agent {self.agent_id}")
                
                # Activează învățarea Qwen din conversații (după fiecare conversație)
                learning_result = await self.qwen_memory.learn_from_conversations(self.agent_id)
                if learning_result.get("status") == "success":
                    logger.info(f"✅ Qwen learned from conversations for agent {self.agent_id}")
                    logger.info(f"   Learned patterns: {len(learning_result.get('learned_patterns', {}))}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save conversation in Qwen Memory: {e}")
            
            # 7. Salvează memoria LangChain în MongoDB (periodic)
            await self.save_memory_to_db()
            
            return {
                "response": response,
                "agent_id": self.agent_id,
                "langchain_used": True,
                "memory_type": "langchain_conversation_buffer",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing message with LangChain: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "response": f"Eroare la procesarea mesajului: {e}",
                "agent_id": self.agent_id,
                "langchain_used": False,
                "error": str(e)
            }
    
    async def _save_conversation(self, user_message: str, response: str, context: Dict = None):
        """Salvează conversația în MongoDB"""
        try:
            conversation_doc = {
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc),
                "user_message": user_message,
                "assistant_response": response,
                "context": context or {},
                "langchain_used": True,
                "memory_type": "langchain_conversation_buffer"
            }
            
            self.conversations_collection.insert_one(conversation_doc)
            logger.info(f"✅ Saved conversation to MongoDB for agent {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
    
    async def _index_conversation(self, user_message: str, response: str):
        """Indexează conversația în vector store pentru search"""
        try:
            if not self.vectorstore:
                return
            
            # Indexează mesajul utilizatorului și răspunsul
            conversation_text = f"Utilizator: {user_message}\nAsistent: {response}"
            
            # Adaugă în vector store
            self.vectorstore.add_texts(
                texts=[conversation_text],
                metadatas=[{
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_message": user_message[:200],  # Trunchiere pentru metadata
                    "assistant_response": response[:200]
                }]
            )
            
            logger.info(f"✅ Indexed conversation in vector store for agent {self.agent_id}")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to index conversation: {e}")
    
    async def search_conversation_history(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Caută în istoricul conversațiilor folosind vector store"""
        try:
            if not self.vectorstore:
                return []
            
            # Caută similarități
            results = self.vectorstore.similarity_search_with_score(query, k=limit)
            
            # Formatează rezultatele
            search_results = []
            for doc, score in results:
                search_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching conversation history: {e}")
            return []


class LangChainAgentManager:
    """
    Manager pentru toți agenții LangChain
    Fiecare agent are propria instanță LangChain
    """
    
    def __init__(self):
        self.agents: Dict[str, LangChainAgent] = {}
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.mongo_client = MongoClient(self.mongo_uri)
        self.db = self.mongo_client.ai_agents_db
        self.agents_collection = self.db.site_agents
    
    async def get_or_create_agent(self, agent_id: str) -> LangChainAgent:
        """
        Obține sau creează un agent LangChain
        """
        if agent_id in self.agents:
            return self.agents[agent_id]
        
        # Obține configurația agentului din MongoDB
        agent_doc = self.agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent_doc:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Creează agent LangChain
        agent_config = {
            "domain": agent_doc.get("domain", "unknown"),
            "name": agent_doc.get("name", "Agent"),
            "memory_initialized": agent_doc.get("memory_initialized", False),
            "memory_config": agent_doc.get("memory_config", {}),
            "vector_collection": agent_doc.get("vector_collection", None)
        }
        
        agent = LangChainAgent(agent_id, agent_config)
        self.agents[agent_id] = agent
        
        logger.info(f"✅ Created LangChain agent for {agent_id}")
        
        return agent
    
    async def process_message(self, agent_id: str, user_message: str, context: Dict = None) -> Dict[str, Any]:
        """Procesează un mesaj pentru un agent specific"""
        agent = await self.get_or_create_agent(agent_id)
        return await agent.process_message(user_message, context)
    
    async def get_conversation_history(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Obține istoricul conversațiilor pentru un agent"""
        agent = await self.get_or_create_agent(agent_id)
        
        # Obține din MongoDB
        conversations = list(agent.conversations_collection.find(
            {"agent_id": agent_id},
            sort=[("timestamp", -1)],
            limit=limit
        ))
        
        # Convertește pentru JSON
        for conv in conversations:
            conv["_id"] = str(conv["_id"])
            conv["timestamp"] = conv["timestamp"].isoformat()
        
        return list(reversed(conversations))


# Instanță globală manager
agent_manager = LangChainAgentManager()

# Funcții helper pentru integrare ușoară
async def process_langchain_message(agent_id: str, user_message: str, context: Dict = None) -> Dict[str, Any]:
    """Helper pentru procesarea mesajelor prin LangChain"""
    return await agent_manager.process_message(agent_id, user_message, context)

async def get_langchain_history(agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Helper pentru obținerea istoricului LangChain"""
    return await agent_manager.get_conversation_history(agent_id, limit)

if __name__ == "__main__":
    async def test():
        test_agent_id = "690478e8a55790fced0e6b75"
        
        # Test creare agent LangChain
        agent = await agent_manager.get_or_create_agent(test_agent_id)
        print(f"✅ Agent created: {agent.agent_id}")
        
        # Test procesare mesaj
        result = await agent.process_message("Ce produse oferiți?")
        print(f"✅ Response: {result['response'][:100]}...")
        
        # Test istoric
        history = await agent_manager.get_conversation_history(test_agent_id, limit=5)
        print(f"✅ History: {len(history)} conversations")
    
    asyncio.run(test())

