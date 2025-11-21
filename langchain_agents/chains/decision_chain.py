"""
Decision Chain - Lanț LangChain pentru transformarea strategiilor în acțiuni concrete

După ce DeepSeek generează strategia, DeepSeek procesează și extrage măsuri concrete.
TOATE informațiile despre agent trebuie trimise la DeepSeek.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# LangChain imports
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
except ImportError:
    try:
        from langchain.prompts import ChatPromptTemplate
        from langchain.schema.output_parser import StrOutputParser
        JsonOutputParser = None
    except ImportError:
        ChatPromptTemplate = StrOutputParser = None
        JsonOutputParser = None

from langchain_agents.llm_manager import get_deepseek_llm  # ⭐ SCHIMBAT: DeepSeek în loc de Qwen

logger = logging.getLogger(__name__)


class DecisionChain:
    """
    Lanț LangChain pentru transformarea strategiilor în acțiuni concrete
    Folosește DeepSeek pentru toate operațiunile
    """
    
    def __init__(self):
        self.deepseek_llm = get_deepseek_llm()  # ⭐ SCHIMBAT: DeepSeek în loc de Qwen
        
        if not self.deepseek_llm:
            logger.error("❌ Failed to initialize DeepSeek LLM for DecisionChain")
            self.chain = None
            return
        
        self.chain = self.create_chain()
    
    def create_chain(self) -> Optional[Any]:
        """
        Creează lanțul de decizie cu DeepSeek
        """
        if not ChatPromptTemplate or not StrOutputParser:
            logger.error("❌ LangChain components not available")
            return None
        
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Ești un expert în transformarea strategiilor în acțiuni concrete executabile.

INFORMAȚII COMPLETE DESPRE AGENT:
- Domain: {domain}
- Business Type: {business_type}
- Servicii identificate: {services}
- Conținut site: {site_content}
- Strategie competitivă: {strategy}

Transformă strategia în acțiuni concrete, prioritizate și executabile bazate pe TOATE informațiile despre agent.
Fiecare acțiune trebuie să fie:
- Specifică și clară
- Măsurabilă
- Realizabilă
- Relevante pentru obiectivul strategic
- Bazată pe serviciile și conținutul real al agentului

Generează un plan de acțiuni JSON:
{{
    "immediate_actions": [
        {{
            "action": "Descriere clară a acțiunii",
            "priority": "high|medium|low",
            "resources_needed": ["...", "..."],
            "expected_impact": "...",
            "difficulty": "easy|medium|hard",
            "estimated_time": "...",
            "success_metrics": ["...", "..."],
            "related_service": "..."
        }}
    ],
    "short_term_actions": [...],
    "medium_term_actions": [...],
    "long_term_actions": [...],
    "action_plan_summary": "Rezumat al planului de acțiuni",
    "next_steps": ["...", "..."]
}}"""),
                ("human", "Generează planul de acțiuni bazat pe toate informațiile despre agent:")
            ])
            
            if JsonOutputParser:
                chain = prompt | self.deepseek_llm | JsonOutputParser()  # ⭐ SCHIMBAT: DeepSeek
            else:
                chain = prompt | self.deepseek_llm | StrOutputParser()  # ⭐ SCHIMBAT: DeepSeek
            
            logger.info("✅ DecisionChain created successfully with DeepSeek")
            return chain
            
        except Exception as e:
            logger.error(f"❌ Error creating DecisionChain: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def generate_action_plan(self, strategy: Dict[str, Any], agent_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generează plan de acțiuni din strategie cu TOATE informațiile despre agent
        
        Args:
            strategy: Strategia competitivă generată
            agent_data: TOATE informațiile despre agent (domain, services, site_content, etc.)
        
        Returns:
            Dict cu planul de acțiuni
        """
        if not self.chain:
            return {
                "ok": False,
                "error": "Decision chain not initialized"
            }
        
        try:
            # ⭐ NOU: Pregătește TOATE informațiile despre agent
            agent_info = agent_data or {}
            site_content = agent_info.get("site_content", "")[:20000]  # Limitează pentru prompt
            services = agent_info.get("services", [])
            if isinstance(services, list):
                services = ", ".join(services[:20])  # Primele 20 servicii
            
            inputs = {
                "strategy": str(strategy) if not isinstance(strategy, str) else strategy,
                "domain": agent_info.get("domain", "unknown"),
                "business_type": agent_info.get("business_type", "general"),
                "services": services or "Nu specificat",
                "site_content": site_content or "Nu disponibil"
            }
            
            # Invoke chain async
            if hasattr(self.chain, 'ainvoke'):
                result = await self.chain.ainvoke(inputs)
            else:
                result = self.chain.invoke(inputs)
            
            return {
                "ok": True,
                "action_plan": result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating action plan: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Funcție de conveniență
def create_decision_chain() -> Optional[DecisionChain]:
    """Creează o instanță DecisionChain"""
    try:
        return DecisionChain()
    except Exception as e:
        logger.error(f"❌ Failed to create DecisionChain: {e}")
        return None

