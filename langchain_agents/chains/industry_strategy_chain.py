"""
Industry Strategy Chain - Lanț LangChain pentru generarea strategiei competitive

TOATE operațiunile folosesc DeepSeek și primește TOATE informațiile despre agent.
"""

import logging
from typing import Dict, Any, Optional, List
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

from langchain_agents.llm_manager import get_deepseek_llm  # ⭐ SCHIMBAT: Doar DeepSeek

logger = logging.getLogger(__name__)


class IndustryStrategyChain:
    """
    Lanț LangChain pentru generarea strategiei competitive
    Folosește DeepSeek pentru toate operațiunile
    """
    
    def __init__(self):
        self.deepseek_llm = get_deepseek_llm()  # ⭐ SCHIMBAT: Doar DeepSeek
        
        if not self.deepseek_llm:
            logger.error("❌ Failed to initialize DeepSeek LLM for IndustryStrategyChain")
            raise RuntimeError("DeepSeek LLM not available")
    
    def create_chain(self) -> Optional[Any]:
        """
        Creează lanțul complet de strategie cu DeepSeek
        """
        if not ChatPromptTemplate or not StrOutputParser:
            logger.error("❌ LangChain components not available")
            return None
        
        try:
            # ⭐ NOU: Un singur prompt complet cu TOATE informațiile despre agent
            strategy_prompt = ChatPromptTemplate.from_messages([
                ("system", """Ești un strateg competitiv expert care analizează piețe și generează strategii.

INFORMAȚII COMPLETE DESPRE AGENT:
- Domain: {domain}
- Business Type: {business_type}
- Servicii identificate: {services}
- Conținut complet site: {site_content}
- Metadata agent: {agent_metadata}

Generează o strategie competitivă COMPLETĂ bazată pe TOATE informațiile despre agent:
1. Analiza pieței (dimensiune, tendințe, oportunități)
2. Poziționare competitivă (unde se situează în piață)
3. Avantaje competitive identificate
4. Oportunități de creștere
5. Amenințări și riscuri
6. Direcții strategice (pe termen scurt, mediu, lung)
7. Priorități de cercetare competitivă
8. Rezultate așteptate
9. Plan de acțiuni concret (immediate, short-term, medium-term, long-term)

Returnează JSON structurat:
{{
    "market_analysis": {{
        "market_size": "...",
        "trends": ["...", "..."],
        "opportunities": ["...", "..."]
    }},
    "competitive_positioning": "...",
    "competitive_advantages": ["...", "..."],
    "growth_opportunities": ["...", "..."],
    "threats": ["...", "..."],
    "strategic_directions": {{
        "short_term": ["...", "..."],
        "medium_term": ["...", "..."],
        "long_term": ["...", "..."]
    }},
    "research_priorities": [
        {{"priority": "high|medium|low", "area": "...", "reason": "..."}}
    ],
    "expected_outcomes": ["...", "..."],
    "action_plan": {{
        "immediate_actions": [
            {{"action": "...", "resources": "...", "impact": "...", "difficulty": "...", "priority": "..."}}
        ],
        "short_term_actions": [...],
        "medium_term_actions": [...],
        "long_term_actions": [...],
        "action_plan_summary": "..."
    }}
}}"""),
                ("human", "Generează strategia competitivă completă bazată pe toate informațiile despre agent:")
            ])
            
            if JsonOutputParser:
                chain = strategy_prompt | self.deepseek_llm | JsonOutputParser()  # ⭐ SCHIMBAT: DeepSeek
            else:
                chain = strategy_prompt | self.deepseek_llm | StrOutputParser()  # ⭐ SCHIMBAT: DeepSeek
            
            logger.info("✅ IndustryStrategyChain created successfully with DeepSeek")
            return chain
            
        except Exception as e:
            logger.error(f"❌ Error creating IndustryStrategyChain: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def generate_strategy(
        self,
        agent_data: Dict[str, Any],
        site_content: str
    ) -> Dict[str, Any]:
        """
        Generează strategia competitivă pentru un agent cu TOATE informațiile
        
        Args:
            agent_data: TOATE informațiile despre agent (domain, business_type, services, metadata)
            site_content: Conținutul site-ului
        
        Returns:
            Dict cu strategia completă
        """
        try:
            chain = self.create_chain()
            if not chain:
                return {
                    "ok": False,
                    "error": "Failed to create strategy chain"
                }
            
            # ⭐ NOU: Pregătește TOATE informațiile despre agent
            services = agent_data.get("services", [])
            if isinstance(services, list):
                services = ", ".join(services[:30])  # Primele 30 servicii
            
            inputs = {
                "domain": agent_data.get("domain", ""),
                "business_type": agent_data.get("business_type", "general"),
                "services": services or "Nu specificat",
                "site_content": site_content[:30000],  # Limitează pentru prompt
                "agent_metadata": str(agent_data.get("metadata", {}))[:5000]  # Limitează metadata
            }
            
            # Invoke chain
            if callable(chain):
                result = chain(inputs)
            elif hasattr(chain, 'ainvoke'):
                result = await chain.ainvoke(inputs)
            else:
                result = chain.invoke(inputs)
            
            return {
                "ok": True,
                "result": result,
                "agent_id": agent_data.get("agent_id"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating strategy: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Funcție de conveniență
def create_industry_strategy_chain() -> Optional[IndustryStrategyChain]:
    """Creează o instanță IndustryStrategyChain"""
    try:
        return IndustryStrategyChain()
    except Exception as e:
        logger.error(f"❌ Failed to create IndustryStrategyChain: {e}")
        return None

