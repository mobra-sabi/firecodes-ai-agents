"""
Global Orchestrator Agent - Agent meta LangChain pentru routing inteligent

Acest agent decide ce lanț sau model trebuie rulat în funcție de cererea utilizatorului.
Folosește DeepSeek pentru reasoning și Qwen pentru taskuri rapide.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import os

# LangChain imports
try:
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
    from langchain_core.runnables import RunnablePassthrough, RunnableLambda
except ImportError:
    ChatPromptTemplate = MessagesPlaceholder = None
    HumanMessage = AIMessage = SystemMessage = None
    StrOutputParser = JsonOutputParser = None
    RunnablePassthrough = RunnableLambda = None
    logging.warning("⚠️ LangChain components not fully available for GlobalOrchestrator")

from langchain_agents.llm_manager import get_deepseek_llm, get_qwen_llm
from langchain_agents.chain_registry import ChainRegistry, get_chain_registry

logger = logging.getLogger(__name__)


class GlobalOrchestrator:
    """
    Agent meta care decide ce lanț sau model trebuie rulat
    """
    
    def __init__(self):
        self.deepseek_llm = get_deepseek_llm()
        self.qwen_llm = get_qwen_llm()
        self.chain_registry = get_chain_registry()
        
        # Verifică dacă LLM-urile sunt disponibile
        if not self.deepseek_llm:
            logger.warning("⚠️ DeepSeek LLM nu este disponibil - va folosi Qwen pentru reasoning")
            self.deepseek_llm = self.qwen_llm  # Fallback la Qwen
        
        if not self.qwen_llm:
            logger.error("❌ Qwen LLM nu este disponibil - Global Orchestrator nu poate funcționa")
            raise RuntimeError("Qwen LLM is required for Global Orchestrator")
        
        self.orchestrator_chain = self._build_orchestrator_chain()
        
        logger.info("✅ Global Orchestrator Agent inițializat")
    
    def _build_orchestrator_chain(self):
        """Construiește lanțul orchestrator"""
        if not all([ChatPromptTemplate, StrOutputParser, JsonOutputParser, RunnablePassthrough]):
            logger.error("⚠️ LangChain components not fully available for orchestrator chain")
            return None
        
        if not self.deepseek_llm:
            logger.warning("⚠️ DeepSeek LLM not available - using Qwen for orchestrator")
            llm_to_use = self.qwen_llm
        else:
            llm_to_use = self.deepseek_llm
        
        # Prompt pentru identificarea intenției și selecția lanțului
        orchestrator_prompt = ChatPromptTemplate.from_messages([
            ("system", """Ești un orchestrator inteligent pentru o platformă multi-agent.

Ai la dispoziție următoarele lanțuri:
- site_analysis: Analiză completă a unui site (Qwen + DeepSeek)
- industry_strategy: Strategie competitivă pentru industrie (DeepSeek + Qwen)
- decision_chain: Plan de acțiune concret din strategie (Qwen)

Ai la dispoziție următoarele modele:
- qwen: Rapid, local, pentru taskuri simple și sumarizare
- deepseek: Puternic, pentru reasoning strategic și analize complexe

Analizează cererea utilizatorului și returnează un JSON cu:
{{
  "intent": "analiză site" | "strategie industrie" | "plan acțiune" | "conversație simplă",
  "chain_name": "site_analysis" | "industry_strategy" | "decision_chain" | null,
  "llm_model": "qwen" | "deepseek",
  "reasoning": "Explicație scurtă de ce ai ales această opțiune",
  "complexity": "low" | "medium" | "high"
}}"""),
            ("user", "{user_request}")
        ])
        
        # Lanț pentru identificarea intenției
        intent_chain = orchestrator_prompt | llm_to_use | JsonOutputParser()
        
        return intent_chain
    
    async def orchestrate(self, user_request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Orchestrează cererea utilizatorului și decide ce lanț/model să folosească
        
        Args:
            user_request: Cererea utilizatorului (text natural)
            context: Context suplimentar (agent_id, site_url, etc.)
        
        Returns:
            Dict cu intenția identificată și lanțul/modelul selectat
        """
        if not self.orchestrator_chain:
            logger.error("❌ Orchestrator chain nu este inițializat")
            return {
                "error": "Orchestrator chain not initialized",
                "fallback": "qwen"
            }
        
        try:
            # Identifică intenția și selectează lanțul/modelul
            intent_result = await self.orchestrator_chain.ainvoke({
                "user_request": user_request
            })
            
            logger.info(f"🎯 Intenție identificată: {intent_result.get('intent')}")
            logger.info(f"   Lanț selectat: {intent_result.get('chain_name')}")
            logger.info(f"   Model selectat: {intent_result.get('llm_model')}")
            logger.info(f"   Complexitate: {intent_result.get('complexity')}")
            
            # Adaugă context
            intent_result["context"] = context or {}
            intent_result["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            return intent_result
            
        except Exception as e:
            logger.error(f"❌ Eroare în orchestrator: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Fallback: folosește Qwen pentru cereri simple
            return {
                "intent": "conversație simplă",
                "chain_name": None,
                "llm_model": "qwen",
                "reasoning": f"Fallback din cauza erorii: {str(e)}",
                "complexity": "low",
                "error": str(e),
                "context": context or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def execute_chain(
        self,
        chain_name: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execută un lanț specific cu parametrii dați
        
        Args:
            chain_name: Numele lanțului (ex: "site_analysis")
            params: Parametrii pentru lanț
            context: Context suplimentar
        
        Returns:
            Rezultatul executării lanțului
        """
        try:
            chain = self.chain_registry.get(chain_name)
            if not chain:
                raise ValueError(f"Lanț '{chain_name}' nu este înregistrat")
            
            logger.info(f"🔄 Executând lanțul '{chain_name}' cu parametrii: {list(params.keys())}")
            
            # Execută lanțul în funcție de tip
            if chain_name == "site_analysis":
                result = await chain.analyze_site(params.get("content", ""))
            elif chain_name == "industry_strategy":
                result = await chain.generate_strategy(
                    params.get("services_list", []),
                    params.get("competitor_data", {})
                )
            elif chain_name == "decision_chain":
                result = await chain.generate_action_plan(params.get("strategic_output", {}))
            else:
                raise ValueError(f"Tip de lanț necunoscut: {chain_name}")
            
            return {
                "chain_name": chain_name,
                "result": result,
                "context": context or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Eroare la executarea lanțului '{chain_name}': {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "chain_name": chain_name,
                "error": str(e),
                "context": context or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def process_request(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Procesează o cerere completă: identifică intenția, execută lanțul și returnează rezultatul
        
        Args:
            user_request: Cererea utilizatorului
            context: Context suplimentar
        
        Returns:
            Rezultatul complet al procesării
        """
        # Pasul 1: Orchestrează cererea
        orchestration_result = await self.orchestrate(user_request, context)
        
        # Pasul 2: Dacă există un lanț selectat, execută-l
        chain_name = orchestration_result.get("chain_name")
        if chain_name:
            # Extrage parametrii din context sau cerere
            params = self._extract_chain_params(user_request, context, chain_name)
            
            # Execută lanțul
            chain_result = await self.execute_chain(chain_name, params, context)
            
            return {
                "orchestration": orchestration_result,
                "chain_execution": chain_result,
                "final_result": chain_result.get("result")
            }
        else:
            # Nu există lanț selectat - folosește LLM direct
            llm_model = orchestration_result.get("llm_model", "qwen")
            llm = self.qwen_llm if llm_model == "qwen" else self.deepseek_llm
            
            # Răspunde direct cu LLM
            try:
                response = await llm.ainvoke(user_request)
                return {
                    "orchestration": orchestration_result,
                    "direct_response": response.content if hasattr(response, 'content') else str(response),
                    "llm_model": llm_model
                }
            except Exception as e:
                logger.error(f"❌ Eroare la răspuns direct cu LLM: {e}")
                return {
                    "orchestration": orchestration_result,
                    "error": str(e)
                }
    
    def _extract_chain_params(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]],
        chain_name: str
    ) -> Dict[str, Any]:
        """
        Extrage parametrii necesari pentru un lanț specific din cerere și context
        
        Args:
            user_request: Cererea utilizatorului
            context: Context suplimentar
            chain_name: Numele lanțului
        
        Returns:
            Dict cu parametrii pentru lanț
        """
        params = {}
        
        if chain_name == "site_analysis":
            # Pentru site_analysis, avem nevoie de conținut
            params["content"] = context.get("content", "") if context else ""
        
        elif chain_name == "industry_strategy":
            # Pentru industry_strategy, avem nevoie de servicii și date competitori
            params["services_list"] = context.get("services_list", []) if context else []
            params["competitor_data"] = context.get("competitor_data", {}) if context else {}
        
        elif chain_name == "decision_chain":
            # Pentru decision_chain, avem nevoie de output strategic
            params["strategic_output"] = context.get("strategic_output", {}) if context else {}
        
        return params


# Singleton instance
_global_orchestrator: Optional[GlobalOrchestrator] = None


def get_global_orchestrator() -> GlobalOrchestrator:
    """Returnează instanța singleton a Global Orchestrator"""
    global _global_orchestrator
    if _global_orchestrator is None:
        _global_orchestrator = GlobalOrchestrator()
    return _global_orchestrator


async def orchestrate_request(
    user_request: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Funcție de conveniență pentru orchestrarea unei cereri
    
    Args:
        user_request: Cererea utilizatorului
        context: Context suplimentar
    
    Returns:
        Rezultatul orchestrării
    """
    orchestrator = get_global_orchestrator()
    return await orchestrator.process_request(user_request, context)

