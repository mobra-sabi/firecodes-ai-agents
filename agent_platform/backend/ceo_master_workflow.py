#!/usr/bin/env python3
"""
🎯 CEO MASTER WORKFLOW - Sistem complet de creare agent master + competitive intelligence

WORKFLOW COMPLET:
================
1. FAZA 1: Creare Agent Master din site cu Qwen GPU paralel + chunks Qdrant
2. FAZA 2: Integrare LangChain pentru orchestrare + memorie conversație  
3. FAZA 3: DeepSeek devine 'vocea' agent-ului master + identificare completă
4. FAZA 4: DeepSeek descompune site în subdomenii + generare keywords (10-15/subdomeniu)
5. FAZA 5: Google Search pentru fiecare keyword + descoperire competitori
6. FAZA 6: Creare Hartă Competitivă CEO (ranking per keyword + poziție master)
7. FAZA 7: Transformare competitori în agenți AI (paralel GPU)
8. FAZA 8: Organogramă master-slave cu raportare ierarhică

Utilizare:
    python3 ceo_master_workflow.py --site-url https://example.com --mode full
"""

import asyncio
import sys
import os
import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import argparse

# Import componente existente
sys.path.insert(0, '/srv/hf/ai_agents')
from tools.construction_agent_creator import ConstructionAgentCreator
from deepseek_competitive_analyzer import DeepSeekCompetitiveAnalyzer
from google_competitor_discovery import GoogleCompetitorDiscovery
from competitive_strategy import CompetitiveStrategyGenerator
from qdrant_context_enhancer import get_context_enhancer
from llm_orchestrator import get_orchestrator
from langchain_agent_integration import LangChainAgent, LangChainAgentManager
from master_slave_learning_system import MasterSlaveLearningSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CEOMasterWorkflow:
    """
    Workflow-ul complet CEO pentru creare agent master + competitive intelligence
    """
    
    def __init__(self):
        # Use MongoDB 8.0 on port 27017 (with real data)
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        
        # Componente
        self.agent_creator = ConstructionAgentCreator()
        self.deepseek_analyzer = DeepSeekCompetitiveAnalyzer()
        self.google_discovery = GoogleCompetitorDiscovery()
        self.strategy_generator = CompetitiveStrategyGenerator()
        self.context_enhancer = get_context_enhancer()
        self.llm = get_orchestrator()
        self.langchain_manager = LangChainAgentManager()
        self.learning_system = MasterSlaveLearningSystem()  # NEW!
        
        logger.info("✅ CEO Master Workflow initialized")
    
    async def execute_full_workflow(
        self, 
        site_url: str,
        results_per_keyword: int = 15,
        parallel_gpu_agents: int = 5
    ) -> Dict[str, Any]:
        """
        Execută workflow-ul COMPLET CEO
        
        Args:
            site_url: URL-ul site-ului master
            results_per_keyword: Câte rezultate Google per keyword (default 15)
            parallel_gpu_agents: Câți agenți să proceseze în paralel pe GPU (default 5)
        
        Returns:
            Dict cu toate rezultatele workflow-ului
        """
        logger.info("="*80)
        logger.info("🎯 CEO MASTER WORKFLOW - START")
        logger.info("="*80)
        logger.info(f"Site URL: {site_url}")
        logger.info(f"Results per keyword: {results_per_keyword}")
        logger.info(f"Parallel GPU agents: {parallel_gpu_agents}")
        
        workflow_start = time.time()
        results = {
            "site_url": site_url,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "phases": {}
        }
        
        try:
            # =================================================================
            # FAZA 1: Creare Agent Master cu Qwen GPU paralel + chunks Qdrant
            # =================================================================
            logger.info("\n" + "="*80)
            logger.info("📍 FAZA 1/8: Creare Agent Master (Qwen GPU + Qdrant)")
            logger.info("="*80)
            
            phase1_start = time.time()
            master_agent_result = await self._phase1_create_master_agent(site_url)
            phase1_duration = time.time() - phase1_start
            
            results["phases"]["phase1_master_agent"] = {
                "status": "completed" if master_agent_result["success"] else "failed",
                "duration_seconds": round(phase1_duration, 2),
                "agent_id": master_agent_result.get("agent_id"),
                "chunks_created": master_agent_result.get("chunks_count", 0),
                "pages_scraped": master_agent_result.get("pages_count", 0)
            }
            
            if not master_agent_result["success"]:
                raise Exception(f"Phase 1 failed: {master_agent_result.get('error')}")
            
            master_agent_id = master_agent_result["agent_id"]
            logger.info(f"✅ FAZA 1 COMPLETĂ! Agent Master ID: {master_agent_id}")
            
            # =================================================================
            # FAZA 2: Integrare LangChain pentru orchestrare + memorie
            # =================================================================
            logger.info("\n" + "="*80)
            logger.info("📍 FAZA 2/8: Integrare LangChain (Orchestrare + Memorie)")
            logger.info("="*80)
            
            phase2_start = time.time()
            langchain_result = await self._phase2_integrate_langchain(master_agent_id)
            phase2_duration = time.time() - phase2_start
            
            results["phases"]["phase2_langchain"] = {
                "status": "completed" if langchain_result["success"] else "failed",
                "duration_seconds": round(phase2_duration, 2),
                "memory_enabled": langchain_result.get("memory_enabled"),
                "conversation_id": langchain_result.get("conversation_id")
            }
            
            logger.info(f"✅ FAZA 2 COMPLETĂ! LangChain integrat cu memorie")
            
            # =================================================================
            # FAZA 3: DeepSeek devine 'vocea' agentului master
            # =================================================================
            logger.info("\n" + "="*80)
            logger.info("📍 FAZA 3/8: DeepSeek devine 'vocea' Agent Master")
            logger.info("="*80)
            
            phase3_start = time.time()
            voice_result = await self._phase3_deepseek_voice_integration(master_agent_id)
            phase3_duration = time.time() - phase3_start
            
            results["phases"]["phase3_deepseek_voice"] = {
                "status": "completed" if voice_result["success"] else "failed",
                "duration_seconds": round(phase3_duration, 2),
                "personality_created": voice_result.get("personality_created"),
                "identity_document": voice_result.get("identity_document")
            }
            
            logger.info(f"✅ FAZA 3 COMPLETĂ! DeepSeek identificat cu agent master")
            
            # =================================================================
            # FAZA 4: DeepSeek descompune site în subdomenii + keywords
            # =================================================================
            logger.info("\n" + "="*80)
            logger.info("📍 FAZA 4/8: DeepSeek descompune site (Subdomenii + Keywords)")
            logger.info("="*80)
            
            phase4_start = time.time()
            analysis_result = await self._phase4_deepseek_decompose_site(master_agent_id)
            phase4_duration = time.time() - phase4_start
            
            results["phases"]["phase4_site_decomposition"] = {
                "status": "completed" if analysis_result["success"] else "failed",
                "duration_seconds": round(phase4_duration, 2),
                "subdomains_count": len(analysis_result.get("subdomains", [])),
                "keywords_per_subdomain": [
                    {
                        "subdomain": sd["name"],
                        "keywords_count": len(sd.get("keywords", []))
                    }
                    for sd in analysis_result.get("subdomains", [])
                ],
                "total_keywords": sum(len(sd.get("keywords", [])) for sd in analysis_result.get("subdomains", []))
            }
            
            logger.info(f"✅ FAZA 4 COMPLETĂ! {len(analysis_result.get('subdomains', []))} subdomenii, "
                       f"{results['phases']['phase4_site_decomposition']['total_keywords']} keywords")
            
            # =================================================================
            # FAZA 5: Google Search pentru fiecare keyword
            # =================================================================
            logger.info("\n" + "="*80)
            logger.info("📍 FAZA 5/8: Google Search pentru keywords + Descoperire competitori")
            logger.info("="*80)
            
            phase5_start = time.time()
            discovery_result = await self._phase5_google_search_competitors(
                master_agent_id, 
                results_per_keyword
            )
            phase5_duration = time.time() - phase5_start
            
            results["phases"]["phase5_competitor_discovery"] = {
                "status": "completed" if discovery_result["success"] else "failed",
                "duration_seconds": round(phase5_duration, 2),
                "competitors_found": len(discovery_result.get("competitors", [])),
                "keywords_searched": discovery_result.get("keywords_searched", 0),
                "total_urls_analyzed": discovery_result.get("total_urls_analyzed", 0)
            }
            
            logger.info(f"✅ FAZA 5 COMPLETĂ! {len(discovery_result.get('competitors', []))} competitori descoperiți")
            
            # =================================================================
            # FAZA 6: Creare Hartă Competitivă CEO
            # =================================================================
            logger.info("\n" + "="*80)
            logger.info("📍 FAZA 6/8: Creare Hartă Competitivă CEO (Ranking + Poziții)")
            logger.info("="*80)
            
            phase6_start = time.time()
            ceo_map_result = await self._phase6_create_ceo_competitive_map(
                master_agent_id,
                discovery_result.get("competitors", []),
                analysis_result.get("subdomains", [])
            )
            phase6_duration = time.time() - phase6_start
            
            results["phases"]["phase6_ceo_map"] = {
                "status": "completed" if ceo_map_result["success"] else "failed",
                "duration_seconds": round(phase6_duration, 2),
                "map_id": ceo_map_result.get("map_id"),
                "master_position_avg": ceo_map_result.get("master_position_avg"),
                "market_coverage": ceo_map_result.get("market_coverage")
            }
            
            logger.info(f"✅ FAZA 6 COMPLETĂ! Hartă CEO creată (ID: {ceo_map_result.get('map_id')})")
            
            # =================================================================
            # FAZA 7: Transformare competitori în agenți AI (paralel GPU)
            # =================================================================
            logger.info("\n" + "="*80)
            logger.info("📍 FAZA 7/8: Transformare competitori în agenți AI (Paralel GPU)")
            logger.info("="*80)
            
            phase7_start = time.time()
            agents_creation_result = await self._phase7_create_competitor_agents_parallel(
                discovery_result.get("competitors", []),
                parallel_gpu_agents,
                master_agent_id=master_agent_id  # Pass master ID!
            )
            phase7_duration = time.time() - phase7_start
            
            results["phases"]["phase7_competitor_agents"] = {
                "status": "completed" if agents_creation_result["success"] else "failed",
                "duration_seconds": round(phase7_duration, 2),
                "agents_created": len(agents_creation_result.get("agent_ids", [])),
                "failed_agents": len(agents_creation_result.get("failed", [])),
                "parallel_gpu_count": parallel_gpu_agents
            }
            
            logger.info(f"✅ FAZA 7 COMPLETĂ! {len(agents_creation_result.get('agent_ids', []))} agenți competitori creați")
            
            # =================================================================
            # FAZA 8: Organogramă master-slave cu raportare ierarhică
            # =================================================================
            logger.info("\n" + "="*80)
            logger.info("📍 FAZA 8/8: Organogramă Master-Slave + Raportare Ierarhică")
            logger.info("="*80)
            
            phase8_start = time.time()
            orgchart_result = await self._phase8_create_master_slave_orgchart(
                master_agent_id,
                agents_creation_result.get("agent_ids", [])
            )
            phase8_duration = time.time() - phase8_start
            
            results["phases"]["phase8_orgchart"] = {
                "status": "completed" if orgchart_result["success"] else "failed",
                "duration_seconds": round(phase8_duration, 2),
                "orgchart_id": orgchart_result.get("orgchart_id"),
                "total_agents": orgchart_result.get("total_agents"),
                "hierarchy_levels": orgchart_result.get("hierarchy_levels")
            }
            
            logger.info(f"✅ FAZA 8 COMPLETĂ! Organogramă creată cu {orgchart_result.get('total_agents')} agenți")
            
            # =================================================================
            # FINALIZARE WORKFLOW
            # =================================================================
            workflow_duration = time.time() - workflow_start
            
            results["status"] = "completed"
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            results["total_duration_seconds"] = round(workflow_duration, 2)
            results["total_duration_minutes"] = round(workflow_duration / 60, 2)
            
            logger.info("\n" + "="*80)
            logger.info("🎉 CEO MASTER WORKFLOW - COMPLETED!")
            logger.info("="*80)
            logger.info(f"⏱️  Total duration: {results['total_duration_minutes']:.2f} minutes")
            logger.info(f"🎯 Master Agent ID: {master_agent_id}")
            logger.info(f"📊 Competitori descoperiți: {len(discovery_result.get('competitors', []))}")
            logger.info(f"🤖 Agenți competitori creați: {len(agents_creation_result.get('agent_ids', []))}")
            logger.info(f"🗺️  Hartă CEO ID: {ceo_map_result.get('map_id')}")
            logger.info(f"📈 Organogramă ID: {orgchart_result.get('orgchart_id')}")
            logger.info("="*80)
            
            # Salvează rezultatele complete în MongoDB
            self.db.ceo_workflow_executions.insert_one(results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ CEO Workflow failed: {e}")
            import traceback
            traceback.print_exc()
            
            results["status"] = "failed"
            results["error"] = str(e)
            results["end_time"] = datetime.now(timezone.utc).isoformat()
            results["total_duration_seconds"] = round(time.time() - workflow_start, 2)
            
            return results
    
    # =========================================================================
    # IMPLEMENTARE FAZE INDIVIDUALE
    # =========================================================================
    
    async def _phase1_create_master_agent(self, site_url: str) -> Dict[str, Any]:
        """
        FAZA 1: Creare Agent Master cu Qwen GPU paralel + chunks Qdrant
        """
        try:
            logger.info(f"🚀 Creare agent master pentru {site_url}")
            logger.info(f"   📦 Qwen GPU paralel + Qdrant chunks")
            
            # Extract domain din URL
            from urllib.parse import urlparse
            domain = urlparse(site_url).netloc.replace('www.', '')
            
            # Verifică dacă agentul există deja
            existing_agent = self.db.site_agents.find_one({"domain": domain}, sort=[("_id", -1)])
            
            if existing_agent and existing_agent.get("chunks_indexed", 0) > 0:
                logger.info(f"✅ Agent existent găsit pentru {domain}")
                agent_id = str(existing_agent["_id"])
            else:
                # Folosește construction_agent_creator care deja are:
                # - Scraping cu BeautifulSoup/Playwright
                # - Generare embeddings pe GPU
                # - Upload chunks la Qdrant
                # - Salvare în MongoDB
                
                result = self.agent_creator.create_site_agent(site_url)
                
                # Găsește agentul după domain (construction_agent_creator poate returna ID invalid)
                agent = self.db.site_agents.find_one({"domain": domain}, sort=[("_id", -1)])
                
                if not agent:
                    return {
                        "success": False,
                        "error": "Agent creation failed - not found in MongoDB"
                    }
                
                agent_id = str(agent["_id"])
                logger.info(f"✅ Agent nou creat cu ID: {agent_id}")
            
            # Obține detalii agent
            agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
            
            return {
                "success": True,
                "agent_id": agent_id,
                "chunks_count": agent.get("chunks_indexed", 0),
                "pages_count": agent.get("pages_indexed", 0),
                "domain": agent.get("domain")
            }
                
        except Exception as e:
            logger.error(f"❌ Phase 1 failed: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    async def _phase2_integrate_langchain(self, agent_id: str) -> Dict[str, Any]:
        """
        FAZA 2: Integrare LangChain pentru orchestrare + memorie
        """
        try:
            logger.info(f"🔗 Integrare LangChain pentru agent {agent_id}")
            
            # Creează LangChain agent cu memorie
            langchain_agent = await self.langchain_manager.create_agent(
                agent_id=agent_id,
                memory_type="conversation_buffer_window",
                memory_k=10  # Ultimele 10 conversații
            )
            
            # Creează prima conversație de test
            conversation_id = await langchain_agent.start_conversation()
            
            return {
                "success": True,
                "memory_enabled": True,
                "conversation_id": conversation_id,
                "agent_id": agent_id
            }
            
        except Exception as e:
            logger.error(f"❌ Phase 2 failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _phase3_deepseek_voice_integration(self, agent_id: str) -> Dict[str, Any]:
        """
        FAZA 3: DeepSeek devine 'vocea' agentului master + identificare completă
        """
        try:
            logger.info(f"🎤 DeepSeek devine vocea agentului {agent_id}")
            
            # Obține context complet agent
            full_context = self.deepseek_analyzer.get_full_agent_context(agent_id)
            
            # Prompt pentru DeepSeek să se identifice cu agentul
            identity_prompt = f"""
Ești DeepSeek, dar acum vei deveni VOCEA OFICIALĂ și IDENTITATEA acestui site:

SITE: {full_context['agent_info']['domain']}
URL: {full_context['agent_info']['site_url']}

CONȚINUTUL COMPLET AL SITE-ULUI:
{full_context['content_full'][:10000]}

SERVICII IDENTIFICATE:
{json.dumps(full_context['services'], indent=2, ensure_ascii=False)}

CONTACT:
{json.dumps(full_context['contact_info'], indent=2, ensure_ascii=False)}

TASK-UL TĂU:
===========
Creează un "DOCUMENT DE IDENTITATE" complet pentru tine ca agent AI al acestui site.

Trebuie să incluzi:
1. **Personalitate și ton de comunicare** (prietenos, profesional, tehnic, etc.)
2. **Expertize principale** (în ce domenii ești expert)
3. **Misiune și valori** (ce reprezinți pentru clienți)
4. **Capability statement** (ce poți face pentru utilizatori)
5. **Communication guidelines** (cum răspunzi la întrebări)
6. **Unique selling points** (ce te diferențiază de concurență)
7. **Target audience** (cu cine vorbești)

Răspunde în format JSON cu acest document de identitate.
"""
            
            # Trimite la DeepSeek
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": "Ești un expert în brand identity și AI agent personality design."},
                    {"role": "user", "content": identity_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parsează răspunsul
            try:
                if isinstance(response, dict):
                    content = response.get("content", "")
                else:
                    content = str(response)
                
                # Încearcă să extragă JSON
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    identity_doc = json.loads(json_match.group(0))
                else:
                    identity_doc = {"raw_response": content}
            except:
                identity_doc = {"raw_response": content}
            
            # Salvează documentul de identitate în MongoDB
            self.db.site_agents.update_one(
                {"_id": ObjectId(agent_id)},
                {"$set": {
                    "deepseek_identity": identity_doc,
                    "deepseek_voice_enabled": True,
                    "last_identity_update": datetime.now(timezone.utc)
                }}
            )
            
            return {
                "success": True,
                "personality_created": True,
                "identity_document": identity_doc
            }
            
        except Exception as e:
            logger.error(f"❌ Phase 3 failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _phase4_deepseek_decompose_site(self, agent_id: str) -> Dict[str, Any]:
        """
        FAZA 4: DeepSeek descompune site în subdomenii + generare keywords
        """
        try:
            logger.info(f"🔬 DeepSeek descompune site-ul agentului {agent_id}")
            
            # Folosește DeepSeekCompetitiveAnalyzer existent
            analysis = self.deepseek_analyzer.analyze_for_competition_discovery(agent_id)
            
            # Salvează analiza
            self.db.competitive_analysis.insert_one({
                "agent_id": ObjectId(agent_id),
                "analysis_type": "competition_discovery",
                "analysis_data": analysis,
                "created_at": datetime.now(timezone.utc)
            })
            
            return {
                "success": True,
                "subdomains": analysis.get("subdomains", []),
                "overall_keywords": analysis.get("overall_keywords", []),
                "industry": analysis.get("industry")
            }
            
        except Exception as e:
            logger.error(f"❌ Phase 4 failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _phase5_google_search_competitors(
        self, 
        agent_id: str, 
        results_per_keyword: int
    ) -> Dict[str, Any]:
        """
        FAZA 5: Google Search pentru fiecare keyword + descoperire competitori
        """
        try:
            logger.info(f"🔍 Google Search pentru agent {agent_id}")
            
            # Folosește GoogleCompetitorDiscovery existent
            discovery = self.google_discovery.discover_competitors_for_agent(
                agent_id=agent_id,
                results_per_keyword=results_per_keyword,
                use_api=False  # Folosește scraping pentru unlimited queries
            )
            
            # Salvează rezultatele
            self.db.competitor_discoveries.insert_one({
                "agent_id": ObjectId(agent_id),
                "discovery_data": discovery,
                "created_at": datetime.now(timezone.utc)
            })
            
            return {
                "success": True,
                "competitors": discovery.get("competitors", []),
                "keywords_searched": len(discovery.get("keywords_map", {})),
                "total_urls_analyzed": discovery.get("stats", {}).get("total_urls_found", 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Phase 5 failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _phase6_create_ceo_competitive_map(
        self,
        master_agent_id: str,
        competitors: List[Dict],
        subdomains: List[Dict]
    ) -> Dict[str, Any]:
        """
        FAZA 6: Creare Hartă Competitivă CEO cu ranking pe fiecare keyword
        """
        try:
            logger.info(f"🗺️  Creare hartă competitivă CEO pentru agent {master_agent_id}")
            
            # Structură hartă CEO
            ceo_map = {
                "master_agent_id": master_agent_id,
                "created_at": datetime.now(timezone.utc),
                "subdomains": subdomains,
                "competitors": competitors,
                "keyword_rankings": {},
                "market_analysis": {}
            }
            
            # Calculează ranking per keyword pentru master vs competitori
            # (continuare în următoarea parte...)
            
            # Salvează harta
            map_result = self.db.ceo_competitive_maps.insert_one(ceo_map)
            
            return {
                "success": True,
                "map_id": str(map_result.inserted_id),
                "master_position_avg": 0,  # TODO: calculează
                "market_coverage": 0  # TODO: calculează
            }
            
        except Exception as e:
            logger.error(f"❌ Phase 6 failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _phase7_create_competitor_agents_parallel(
        self,
        competitors: List[Dict],
        parallel_count: int,
        master_agent_id: str = None
    ) -> Dict[str, Any]:
        """
        FAZA 7: Transformare competitori în SLAVE AGENTS (paralel GPU)
        IMPORTANT: Competitorii devin SLAVES care învață MASTER-ul!
        """
        try:
            logger.info(f"🤖 Creare {len(competitors)} SLAVE AGENTS competitori (paralel pe {parallel_count} GPU-uri)")
            logger.info(f"   Master Agent ID: {master_agent_id}")
            
            slave_ids = []
            failed = []
            
            # Process competitors in batches
            for i, competitor in enumerate(competitors[:parallel_count]):
                logger.info(f"   [{i+1}/{len(competitors)}] Processing: {competitor.get('domain', 'unknown')}")
                
                try:
                    # Create SLAVE agent using learning system
                    result = await self.learning_system.create_slave_from_competitor(
                        competitor_url=competitor.get("url"),
                        master_agent_id=master_agent_id,
                        keyword=competitor.get("keyword", "unknown"),
                        serp_position=competitor.get("serp_position", 0)
                    )
                    
                    if result.get("success"):
                        slave_ids.append(result["slave_agent_id"])
                        logger.info(f"      ✅ SLAVE created: {result['slave_agent_id']}")
                    else:
                        failed.append({
                            "url": competitor.get("url"),
                            "error": result.get("error")
                        })
                        logger.warning(f"      ❌ Failed: {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"      ❌ Exception: {e}")
                    failed.append({
                        "url": competitor.get("url"),
                        "error": str(e)
                    })
            
            logger.info(f"✅ Phase 7 completed: {len(slave_ids)} slaves created, {len(failed)} failed")
            
            return {
                "success": True,
                "agent_ids": slave_ids,
                "failed": failed,
                "total_processed": len(competitors)
            }
            
        except Exception as e:
            logger.error(f"❌ Phase 7 failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _phase8_create_master_slave_orgchart(
        self,
        master_agent_id: str,
        slave_agent_ids: List[str]
    ) -> Dict[str, Any]:
        """
        FAZA 8: MASTER învață din SLAVES + Generare Raport CI pentru CEO
        IMPORTANT: Master extrage knowledge din toți competitorii!
        """
        try:
            logger.info(f"🧠 MASTER învață din {len(slave_agent_ids)} SLAVES")
            logger.info(f"   Master Agent ID: {master_agent_id}")
            
            # STEP 1: Master learns from ALL slaves
            logger.info("   STEP 1/3: Learning from all slaves...")
            learning_result = await self.learning_system.master_learns_from_all_slaves(
                master_agent_id
            )
            
            if not learning_result.get("success"):
                logger.warning(f"   ⚠️  Learning failed: {learning_result.get('error')}")
            else:
                logger.info(f"   ✅ Learning completed!")
                logger.info(f"      Slaves analyzed: {learning_result.get('slaves_analyzed')}")
            
            # STEP 2: Generate Competitive Intelligence Report for CEO
            logger.info("   STEP 2/3: Generating CI Report for CEO...")
            ci_report_result = await self.learning_system.generate_competitive_intelligence_report(
                master_agent_id
            )
            
            if not ci_report_result.get("success"):
                logger.warning(f"   ⚠️  CI Report generation failed: {ci_report_result.get('error')}")
                ci_report_id = None
            else:
                ci_report_id = ci_report_result["report"]["report_id"]
                logger.info(f"   ✅ CI Report generated: {ci_report_id}")
            
            # STEP 3: Create hierarchical structure in DB
            logger.info("   STEP 3/3: Creating organizational structure...")
            orgchart = {
                "master_id": ObjectId(master_agent_id),
                "slave_ids": [ObjectId(sid) for sid in slave_agent_ids],
                "total_agents": 1 + len(slave_agent_ids),
                "hierarchy_levels": 2,
                "learning_completed": learning_result.get("success", False),
                "ci_report_id": ci_report_id,
                "created_at": datetime.now(timezone.utc)
            }
            
            result = self.db.agent_hierarchies.insert_one(orgchart)
            orgchart_id = str(result.inserted_id)
            
            logger.info(f"   ✅ Organizational chart created: {orgchart_id}")
            
            # Get slaves info for summary
            slaves = await self.learning_system.get_slaves_for_master(master_agent_id)
            
            logger.info(f"✅ Phase 8 completed!")
            logger.info(f"   Organization:")
            logger.info(f"      1 MASTER → {len(slave_agent_ids)} SLAVES")
            logger.info(f"   Learning: {'✅ Completed' if learning_result.get('success') else '❌ Failed'}")
            logger.info(f"   CI Report: {'✅ Generated' if ci_report_id else '❌ Failed'}")
            
            return {
                "success": True,
                "orgchart_id": orgchart_id,
                "total_agents": 1 + len(slave_agent_ids),
                "hierarchy_levels": 2,
                "learning_completed": learning_result.get("success", False),
                "learning_record_id": learning_result.get("learning_record_id"),
                "ci_report_id": ci_report_id,
                "slaves_info": slaves,
                "aggregated_insights": learning_result.get("aggregated_insights", "")[:500]  # Preview
            }
            
        except Exception as e:
            logger.error(f"❌ Phase 8 failed: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}


async def main():
    """Main function cu argparse"""
    parser = argparse.ArgumentParser(description='CEO Master Workflow')
    parser.add_argument('--site-url', required=True, help='URL site master')
    parser.add_argument('--results-per-keyword', type=int, default=15, help='Rezultate Google per keyword')
    parser.add_argument('--parallel-gpu', type=int, default=5, help='Agenți paralel pe GPU')
    
    args = parser.parse_args()
    
    workflow = CEOMasterWorkflow()
    result = await workflow.execute_full_workflow(
        site_url=args.site_url,
        results_per_keyword=args.results_per_keyword,
        parallel_gpu_agents=args.parallel_gpu
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

