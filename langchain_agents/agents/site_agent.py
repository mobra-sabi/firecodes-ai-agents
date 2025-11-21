"""
Site Agent - Agent LangChain complet pentru fiecare site

Fiecare site devine un agent LangChain cu:
- Tool-uri proprii (SearchTool, ScraperTool, InsightTool)
- Memorie persistentă (MongoDB + Qdrant)
- LLM core (Qwen default)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import os

# LangChain imports
try:
    from langchain.agents import initialize_agent, AgentType
    from langchain.agents import AgentExecutor
    from langchain_core.tools import Tool
except ImportError:
    try:
        from langchain.agents import initialize_agent, AgentType, AgentExecutor
        from langchain.tools import Tool
    except ImportError:
        initialize_agent = AgentType = AgentExecutor = Tool = None

from langchain_agents.llm_manager import get_qwen_llm
from langchain_agents.tools.vector_search_tool import VectorSearchTool, create_vector_search_tool
from langchain_agents.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")


class SiteAgent:
    """
    Agent LangChain complet pentru un site
    """
    
    def __init__(self, agent_id: str, agent_config: Dict[str, Any]):
        self.agent_id = agent_id
        self.agent_config = agent_config
        
        # MongoDB
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client.ai_agents_db
        self.agents_collection = self.db.site_agents
        
        # LLM
        self.llm = get_qwen_llm()
        if not self.llm:
            raise RuntimeError("Qwen LLM not available")
        
        # Vector Search Tool
        self.vector_search_tool = create_vector_search_tool(agent_id)
        
        # Memory Manager
        self.memory_manager = MemoryManager(agent_id)
        
        # Tool-uri
        self.tools = self._create_tools()
        
        # Agent Executor
        self.agent_executor = self._create_agent_executor()
        
        logger.info(f"✅ SiteAgent initialized for agent {agent_id}")
    
    def _create_tools(self) -> List[Tool]:
        """
        Creează tool-urile pentru agent
        
        Returns:
            Lista de tool-uri LangChain
        """
        if not Tool:
            logger.warning("⚠️ LangChain Tool not available")
            return []
        
        tools = []
        
        # SearchTool - Căutare semantică în Qdrant
        if self.vector_search_tool:
            search_tool = Tool(
                name="search_site_content",
                description="Caută informații relevante în conținutul site-ului. Folosește când utilizatorul întreabă despre servicii, produse, contact, sau alte informații despre site.",
                func=lambda query: self.vector_search_tool.search_relevant(query, k=5)
            )
            tools.append(search_tool)
        
        # ScraperTool - Citire pagini (simplificat)
        scraper_tool = Tool(
            name="scrape_page",
            description="Citește conținutul unei pagini web. Folosește când trebuie să analizezi o pagină specifică.",
            func=self._scrape_page
        )
        tools.append(scraper_tool)
        
        # InsightTool - Analiză de performanță
        insight_tool = Tool(
            name="analyze_performance",
            description="Analizează performanța site-ului și oferă insights. Folosește când utilizatorul întreabă despre SEO, conversii, sau optimizări.",
            func=self._analyze_performance
        )
        tools.append(insight_tool)
        
        return tools
    
    def _scrape_page(self, url: str) -> str:
        """
        Scrape o pagină web (simplificat)
        
        Args:
            url: URL-ul paginii
        
        Returns:
            Conținutul paginii
        """
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            
            return text[:2000]  # Limitează la 2000 caractere
            
        except Exception as e:
            logger.error(f"❌ Error scraping page {url}: {e}")
            return f"Eroare la citirea paginii: {e}"
    
    def _analyze_performance(self, query: str) -> str:
        """
        Analizează performanța site-ului
        
        Args:
            query: Tipul de analiză solicitat
        
        Returns:
            Insights despre performanță
        """
        try:
            # Obține datele agentului
            agent = self.agents_collection.find_one({"_id": ObjectId(self.agent_id)})
            if not agent:
                return "Agentul nu a fost găsit."
            
            # Analiză simplă bazată pe datele disponibile
            insights = []
            
            # Verifică dacă are vectori în Qdrant
            if agent.get("vector_collection"):
                insights.append("✅ Site-ul are conținut indexat în Qdrant")
            
            # Verifică memorie
            if agent.get("memory_initialized"):
                insights.append("✅ Memoria agentului este inițializată")
            
            # Verifică strategie
            strategy = self.db.competitive_strategies.find_one({"agent_id": self.agent_id})
            if strategy:
                insights.append("✅ Strategie competitivă disponibilă")
            
            return "\n".join(insights) if insights else "Nu sunt suficiente date pentru analiză."
            
        except Exception as e:
            logger.error(f"❌ Error analyzing performance: {e}")
            return f"Eroare la analiză: {e}"
    
    def _create_agent_executor(self) -> Optional[Any]:
        """
        Creează Agent Executor pentru agent
        
        Returns:
            AgentExecutor sau None
        """
        if not initialize_agent or not AgentExecutor:
            logger.warning("⚠️ LangChain agents not available")
            return None
        
        if not self.tools:
            logger.warning("⚠️ No tools available for agent")
            return None
        
        try:
            # Creează agent cu tool-uri
            agent = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # Sau CHAT_CONVERSATIONAL_REACT_DESCRIPTION
                verbose=True,
                memory=self.memory_manager.get_langchain_memory(),
                handle_parsing_errors=True
            )
            
            return agent
            
        except Exception as e:
            logger.error(f"❌ Error creating agent executor: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def ask(self, question: str, conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Răspunde la o întrebare folosind agentul
        
        Args:
            question: Întrebarea utilizatorului
            conversation_history: Istoric conversație (opțional)
        
        Returns:
            Dict cu răspunsul și metadata
        """
        try:
            # Încarcă istoricul în memorie
            if conversation_history:
                self.memory_manager.load_history(conversation_history)
            
            # Execută agent
            if self.agent_executor:
                response = self.agent_executor.run(question)
            else:
                # Fallback: folosește doar LLM
                response = self.llm.invoke(question).content
            
            # Salvează conversația
            await self.memory_manager.save_conversation(question, response)
            
            return {
                "ok": True,
                "response": response,
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error in agent ask: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Obține informații despre agent"""
        agent = self.agents_collection.find_one({"_id": ObjectId(self.agent_id)})
        return {
            "agent_id": self.agent_id,
            "domain": agent.get("domain") if agent else None,
            "tools_count": len(self.tools),
            "memory_initialized": self.memory_manager.is_initialized(),
            "vector_collection": agent.get("vector_collection") if agent else None
        }


def initialize_site_agent(agent_id: str) -> Optional[SiteAgent]:
    """
    Inițializează un agent LangChain pentru un site
    
    Args:
        agent_id: ID-ul agentului
    
    Returns:
        SiteAgent sau None
    """
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client.ai_agents_db
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        
        if not agent:
            logger.error(f"❌ Agent {agent_id} not found")
            return None
        
        agent_config = {
            "domain": agent.get("domain"),
            "business_type": agent.get("business_type", "general"),
            "site_url": agent.get("site_url")
        }
        
        return SiteAgent(agent_id, agent_config)
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize site agent: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

