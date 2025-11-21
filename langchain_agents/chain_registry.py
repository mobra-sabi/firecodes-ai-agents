"""
Chain Registry - Registry centralizat pentru lanțurile LangChain

Permite înregistrarea și accesarea rapidă a lanțurilor pentru orchestrator.
"""

import logging
from typing import Dict, Any, Optional, Callable
from langchain_agents.chains.site_analysis_chain import SiteAnalysisChain, create_site_analysis_chain
from langchain_agents.chains.industry_strategy_chain import IndustryStrategyChain, create_industry_strategy_chain
from langchain_agents.chains.decision_chain import DecisionChain, create_decision_chain

logger = logging.getLogger(__name__)


class ChainRegistry:
    """
    Registry centralizat pentru lanțurile LangChain
    """
    
    def __init__(self):
        self.chains: Dict[str, Any] = {}
        self._register_default_chains()
    
    def _register_default_chains(self):
        """Înregistrează lanțurile implicite"""
        try:
            # Site Analysis Chain
            site_analysis = create_site_analysis_chain()
            if site_analysis:
                self.register("site_analysis", site_analysis)
            
            # Industry Strategy Chain
            industry_strategy = create_industry_strategy_chain()
            if industry_strategy:
                self.register("industry_strategy", industry_strategy)
            
            # Decision Chain
            decision_chain = create_decision_chain()
            if decision_chain:
                self.register("decision_chain", decision_chain)
            
            logger.info(f"✅ Registered {len(self.chains)} default chains")
            
        except Exception as e:
            logger.error(f"❌ Error registering default chains: {e}")
    
    def register(self, name: str, chain: Any):
        """
        Înregistrează un lanț
        
        Args:
            name: Numele lanțului
            chain: Instanța lanțului
        """
        self.chains[name] = chain
        logger.info(f"✅ Registered chain: {name}")
    
    def get(self, name: str) -> Optional[Any]:
        """
        Obține un lanț înregistrat
        
        Args:
            name: Numele lanțului
        
        Returns:
            Lanțul sau None dacă nu există
        """
        return self.chains.get(name)
    
    def list_chains(self) -> list[str]:
        """Listează toate lanțurile înregistrate"""
        return list(self.chains.keys())
    
    def has_chain(self, name: str) -> bool:
        """Verifică dacă un lanț este înregistrat"""
        return name in self.chains


# Instanță globală
_chain_registry = None

def get_chain_registry() -> ChainRegistry:
    """Obține instanța globală a Chain Registry"""
    global _chain_registry
    if _chain_registry is None:
        _chain_registry = ChainRegistry()
    return _chain_registry

def register_chain(name: str, chain: Any):
    """Funcție de conveniență pentru înregistrarea unui lanț"""
    get_chain_registry().register(name, chain)

def get_chain(name: str) -> Optional[Any]:
    """Funcție de conveniență pentru obținerea unui lanț"""
    return get_chain_registry().get(name)

