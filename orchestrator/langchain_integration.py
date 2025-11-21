"""
LangChain Orchestrator Integration - Integrare lanțuri LangChain cu orchestrator

Extinde orchestrator_loop.py pentru a suporta task-uri LangChain.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone

# Importă lanțurile LangChain
try:
    from langchain_agents.chain_registry import get_chain_registry
    from langchain_agents.agents.global_orchestrator import get_global_orchestrator
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logging.warning("⚠️ LangChain agents not available")

logger = logging.getLogger(__name__)


class LangChainTaskExecutor:
    """
    Executor pentru task-uri LangChain în orchestrator
    """
    
    def __init__(self):
        if not LANGCHAIN_AVAILABLE:
            raise RuntimeError("LangChain agents not available")
        
        self.chain_registry = get_chain_registry()
        self.global_orchestrator = get_global_orchestrator()
        logger.info("✅ LangChain Task Executor inițializat")
    
    async def run_chain_task(
        self,
        chain_name: str,
        params: Dict[str, Any],
        task_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Execută un task LangChain cu progres
        
        Args:
            chain_name: Numele lanțului (ex: "site_analysis", "industry_strategy")
            params: Parametrii pentru lanț
            task_id: ID-ul task-ului (pentru tracking)
            progress_callback: Callback pentru progres (opțional)
        
        Returns:
            Rezultatul executării lanțului
        """
        if not task_id:
            task_id = f"langchain_{chain_name}_{datetime.now(timezone.utc).isoformat()}"
        
        logger.info(f"🔄 Executând task LangChain: {chain_name} (ID: {task_id})")
        
        # Notifică progres inițial
        if progress_callback:
            await progress_callback({
                "task_id": task_id,
                "status": "running",
                "chain_name": chain_name,
                "progress": 0,
                "message": f"Încep executarea lanțului {chain_name}..."
            })
        
        try:
            # Obține lanțul din registry
            chain = self.chain_registry.get(chain_name)
            if not chain:
                raise ValueError(f"Lanț '{chain_name}' nu este înregistrat. Lanțuri disponibile: {self.chain_registry.list_chains()}")
            
            # Notifică progres
            if progress_callback:
                await progress_callback({
                    "task_id": task_id,
                    "status": "running",
                    "chain_name": chain_name,
                    "progress": 25,
                    "message": f"Lanț '{chain_name}' găsit, executare..."
                })
            
            # Execută lanțul în funcție de tip
            result = None
            
            if chain_name == "site_analysis":
                # ⭐ NOU: Obține TOATE informațiile despre agent
                agent_id = params.get("agent_id")
                agent_data = await self._get_full_agent_data(agent_id)
                
                content = params.get("content", agent_data.get("site_content", ""))
                if not content:
                    raise ValueError("Parametrul 'content' este necesar pentru site_analysis")
                
                result = await chain.analyze_site(
                    site_content=content,
                    site_url=agent_data.get("domain"),
                    agent_data=agent_data  # ⭐ NOU: Trimite toate informațiile
                )
                
            elif chain_name == "industry_strategy":
                # ⭐ NOU: Obține TOATE informațiile despre agent
                agent_id = params.get("agent_id")
                agent_data = await self._get_full_agent_data(agent_id)
                
                site_content = agent_data.get("site_content", "")
                if not site_content:
                    raise ValueError("Conținutul site-ului nu este disponibil pentru industry_strategy")
                
                result = await chain.generate_strategy(
                    agent_data=agent_data,  # ⭐ NOU: Trimite toate informațiile
                    site_content=site_content
                )
                
            elif chain_name == "decision_chain":
                # ⭐ NOU: Obține TOATE informațiile despre agent
                agent_id = params.get("agent_id")
                agent_data = await self._get_full_agent_data(agent_id)
                
                strategic_output = params.get("strategic_output", {})
                
                if not strategic_output:
                    raise ValueError("Parametrul 'strategic_output' este necesar pentru decision_chain")
                
                result = await chain.generate_action_plan(
                    strategy=strategic_output,
                    agent_data=agent_data  # ⭐ NOU: Trimite toate informațiile
                )
            
            else:
                raise ValueError(f"Tip de lanț necunoscut sau neimplementat: {chain_name}")
            
            # Notifică progres final
            if progress_callback:
                await progress_callback({
                    "task_id": task_id,
                    "status": "completed",
                    "chain_name": chain_name,
                    "progress": 100,
                    "message": f"Lanț '{chain_name}' executat cu succes"
                })
            
            logger.info(f"✅ Task LangChain '{chain_name}' finalizat cu succes (ID: {task_id})")
            
            return {
                "task_id": task_id,
                "chain_name": chain_name,
                "status": "completed",
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Eroare la executarea task-ului LangChain '{chain_name}': {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Notifică eroare
            if progress_callback:
                await progress_callback({
                    "task_id": task_id,
                    "status": "error",
                    "chain_name": chain_name,
                    "progress": 0,
                    "error": str(e),
                    "message": f"Eroare la executarea lanțului '{chain_name}': {e}"
                })
            
            return {
                "task_id": task_id,
                "chain_name": chain_name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def orchestrate_and_execute(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Orchestrează cererea și execută lanțul corespunzător
        
        Args:
            user_request: Cererea utilizatorului (text natural)
            context: Context suplimentar
            task_id: ID-ul task-ului
            progress_callback: Callback pentru progres
        
        Returns:
            Rezultatul complet al orchestrării și executării
        """
        if not task_id:
            task_id = f"orchestrate_{datetime.now(timezone.utc).isoformat()}"
        
        logger.info(f"🎯 Orchestrând cererea: {user_request[:100]}... (ID: {task_id})")
        
        # Notifică progres inițial
        if progress_callback:
            await progress_callback({
                "task_id": task_id,
                "status": "orchestrating",
                "progress": 0,
                "message": "Analizez cererea și identific intenția..."
            })
        
        try:
            # Orchestrează cererea
            orchestration_result = await self.global_orchestrator.orchestrate(user_request, context)
            
            # Notifică progres
            if progress_callback:
                await progress_callback({
                    "task_id": task_id,
                    "status": "orchestrated",
                    "progress": 30,
                    "orchestration": orchestration_result,
                    "message": f"Intenție identificată: {orchestration_result.get('intent')}"
                })
            
            # Dacă există un lanț selectat, execută-l
            chain_name = orchestration_result.get("chain_name")
            if chain_name:
                # Extrage parametrii din context sau cerere
                params = self._extract_chain_params(user_request, context, chain_name)
                
                # Execută lanțul
                chain_result = await self.run_chain_task(
                    chain_name,
                    params,
                    task_id=f"{task_id}_chain",
                    progress_callback=progress_callback
                )
                
                return {
                    "task_id": task_id,
                    "orchestration": orchestration_result,
                    "chain_execution": chain_result,
                    "final_result": chain_result.get("result"),
                    "status": "completed"
                }
            else:
                # Nu există lanț selectat - folosește LLM direct
                llm_model = orchestration_result.get("llm_model", "qwen")
                
                if progress_callback:
                    await progress_callback({
                        "task_id": task_id,
                        "status": "responding",
                        "progress": 50,
                        "message": f"Răspund direct cu {llm_model}..."
                    })
                
                # Folosește Global Orchestrator pentru răspuns direct
                direct_result = await self.global_orchestrator.process_request(user_request, context)
                
                return {
                    "task_id": task_id,
                    "orchestration": orchestration_result,
                    "direct_response": direct_result.get("direct_response"),
                    "status": "completed"
                }
                
        except Exception as e:
            logger.error(f"❌ Eroare în orchestrator: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            if progress_callback:
                await progress_callback({
                    "task_id": task_id,
                    "status": "error",
                    "error": str(e),
                    "message": f"Eroare în orchestrator: {e}"
                })
            
            return {
                "task_id": task_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
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
    
    async def _get_full_agent_data(self, agent_id: str) -> Dict[str, Any]:
        """
        Obține TOATE informațiile despre agent din MongoDB și Qdrant
        
        Args:
            agent_id: ID-ul agentului
        
        Returns:
            Dict cu toate informațiile despre agent
        """
        try:
            from bson import ObjectId
            from database.mongodb_handler import get_mongodb_client
            
            db = get_mongodb_client()
            
            # Obține agentul din MongoDB
            agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return {}
            
            # Obține conținutul site-ului din MongoDB
            site_content_docs = list(db.site_content.find({"agent_id": ObjectId(agent_id)}).limit(100))
            site_content = "\n\n".join([doc.get("content", "") for doc in site_content_docs])
            
            # Obține serviciile identificate
            services = agent.get("services", [])
            if not services:
                # Încearcă să extragă din conținut sau din strategia competitivă
                strategy = db.competitive_strategies.find_one({"agent_id": ObjectId(agent_id)})
                if strategy:
                    services = strategy.get("services", [])
            
            return {
                "agent_id": agent_id,
                "domain": agent.get("domain", ""),
                "business_type": agent.get("business_type", "general"),
                "services": services,
                "site_content": site_content,
                "metadata": {
                    "created_at": agent.get("created_at"),
                    "status": agent.get("status"),
                    "pages_crawled": agent.get("pages_crawled", 0),
                    "total_chunks": len(site_content_docs)
                }
            }
        except Exception as e:
            logger.error(f"❌ Error getting full agent data: {e}")
            return {}


# Singleton instance
_langchain_executor: Optional[LangChainTaskExecutor] = None


def get_langchain_executor() -> Optional[LangChainTaskExecutor]:
    """Returnează instanța singleton a LangChain Task Executor"""
    global _langchain_executor
    if not LANGCHAIN_AVAILABLE:
        logger.warning("⚠️ LangChain not available - LangChain Task Executor cannot be initialized")
        return None
    
    if _langchain_executor is None:
        try:
            _langchain_executor = LangChainTaskExecutor()
        except Exception as e:
            logger.error(f"❌ Failed to initialize LangChain Task Executor: {e}")
            return None
    
    return _langchain_executor


async def run_chain_task(
    chain_name: str,
    params: Dict[str, Any],
    task_id: Optional[str] = None,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Funcție de conveniență pentru executarea unui task LangChain
    
    Args:
        chain_name: Numele lanțului
        params: Parametrii pentru lanț
        task_id: ID-ul task-ului
        progress_callback: Callback pentru progres
    
    Returns:
        Rezultatul executării
    """
    executor = get_langchain_executor()
    if not executor:
        return {
            "status": "error",
            "error": "LangChain Task Executor not available"
        }
    
    return await executor.run_chain_task(chain_name, params, task_id, progress_callback)


async def orchestrate_and_execute(
    user_request: str,
    context: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Funcție de conveniență pentru orchestrarea și executarea unei cereri
    
    Args:
        user_request: Cererea utilizatorului
        context: Context suplimentar
        task_id: ID-ul task-ului
        progress_callback: Callback pentru progres
    
    Returns:
        Rezultatul complet
    """
    executor = get_langchain_executor()
    if not executor:
        return {
            "status": "error",
            "error": "LangChain Task Executor not available"
        }
    
    return await executor.orchestrate_and_execute(user_request, context, task_id, progress_callback)

