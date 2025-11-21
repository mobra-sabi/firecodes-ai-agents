"""
Site Analysis Chain - Lanț LangChain pentru analiza completă a unui site

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


class SiteAnalysisChain:
    """
    Lanț LangChain pentru analiza completă a unui site
    Folosește DeepSeek pentru toate operațiunile
    """
    
    def __init__(self):
        self.deepseek_llm = get_deepseek_llm()  # ⭐ SCHIMBAT: Doar DeepSeek
        
        if not self.deepseek_llm:
            logger.error("❌ Failed to initialize DeepSeek LLM for SiteAnalysisChain")
            raise RuntimeError("DeepSeek LLM not available")
    
    def create_chain(self) -> Optional[Any]:
        """
        Creează lanțul complet de analiză cu DeepSeek
        """
        if not ChatPromptTemplate or not StrOutputParser:
            logger.error("❌ LangChain components not available")
            return None
        
        try:
            # ⭐ NOU: Un singur prompt complet cu TOATE informațiile despre agent
            analysis_prompt = ChatPromptTemplate.from_messages([
                ("system", """Ești un expert în analiza site-urilor web și strategie digitală.

INFORMAȚII COMPLETE DESPRE AGENT:
- Domain: {domain}
- Business Type: {business_type}
- Servicii identificate: {services}
- Conținut complet site: {site_content}
- Metadata agent: {agent_metadata}

Analizează COMPLET site-ul și generează o analiză strategică detaliată cu:
1. Descriere generală (2-3 propoziții)
2. Servicii/Produse principale (lista detaliată)
3. Tipuri de pagini identificate și structura navigării
4. Puncte forte identificate
5. Puncte slabe identificate
6. Evaluare generală (scor 1-10)
7. Direcții de îmbunătățire (prioritizate)
8. Recomandări SEO
9. Recomandări UX/UI
10. Oportunități de conversie

Returnează JSON structurat:
{{
    "overall_score": 7,
    "description": "...",
    "main_services": ["...", "..."],
    "page_types": [
        {{"type": "Homepage", "description": "...", "count": 1}},
        {{"type": "Servicii", "description": "...", "count": 3}}
    ],
    "navigation_structure": "...",
    "content_depth": "superficial|mediu|profund",
    "strengths": ["...", "..."],
    "weaknesses": ["...", "..."],
    "improvements": [
        {{"priority": "high|medium|low", "area": "...", "action": "...", "impact": "..."}}
    ],
    "seo_recommendations": ["...", "..."],
    "ux_recommendations": ["...", "..."],
    "conversion_opportunities": ["...", "..."]
}}"""),
                ("human", "Generează analiza strategică completă bazată pe toate informațiile despre agent:")
            ])
            
            if JsonOutputParser:
                chain = analysis_prompt | self.deepseek_llm | JsonOutputParser()  # ⭐ SCHIMBAT: DeepSeek
            else:
                chain = analysis_prompt | self.deepseek_llm | StrOutputParser()  # ⭐ SCHIMBAT: DeepSeek
            
            logger.info("✅ SiteAnalysisChain created successfully with DeepSeek")
            return chain
            
        except Exception as e:
            logger.error(f"❌ Error creating SiteAnalysisChain: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def analyze_site(self, site_content: str, site_url: Optional[str] = None, agent_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analizează un site complet cu TOATE informațiile despre agent
        
        Args:
            site_content: Conținutul text al site-ului
            site_url: URL-ul site-ului (opțional)
            agent_data: TOATE informațiile despre agent (domain, services, metadata, etc.)
        
        Returns:
            Dict cu rezultatele analizei
        """
        try:
            chain = self.create_chain()
            if not chain:
                return {
                    "ok": False,
                    "error": "Failed to create analysis chain"
                }
            
            # ⭐ NOU: Pregătește TOATE informațiile despre agent
            agent_info = agent_data or {}
            services = agent_info.get("services", [])
            if isinstance(services, list):
                services = ", ".join(services[:30])  # Primele 30 servicii
            
            inputs = {
                "site_content": site_content[:50000],  # Limitează la 50k caractere
                "site_url": site_url or agent_info.get("domain", "unknown"),
                "domain": agent_info.get("domain", site_url or "unknown"),
                "business_type": agent_info.get("business_type", "general"),
                "services": services or "Nu specificat",
                "agent_metadata": str(agent_info.get("metadata", {}))[:5000]  # Limitează metadata
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
                "site_url": site_url or agent_info.get("domain", "unknown"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing site: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Funcție de conveniență
def create_site_analysis_chain() -> Optional[SiteAnalysisChain]:
    """Creează o instanță SiteAnalysisChain"""
    try:
        return SiteAnalysisChain()
    except Exception as e:
        logger.error(f"❌ Failed to create SiteAnalysisChain: {e}")
        return None

