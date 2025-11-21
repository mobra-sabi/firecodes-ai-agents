"""
🏗️ Industry Mass Agent Creator - Construcții România
=====================================================

Sistem pentru transformarea întregii industrii de construcții din România
în agenți AI compleți, cu DeepSeek ca orchestrator principal.
"""

import asyncio
import logging
import traceback
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from bson import ObjectId
from llm_orchestrator import LLMOrchestrator
from ceo_master_workflow import CEOMasterWorkflow
from industry_transformation_logger import IndustryTransformationLogger

logger = logging.getLogger(__name__)


class ConstructionIndustryDiscovery:
    """Descoperă companii din industria de construcții din România"""
    
    def __init__(self, mongo_client: MongoClient, llm: LLMOrchestrator, transformation_logger=None):
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.llm = llm
        self.logger = transformation_logger
        
        # Collection pentru companii descoperite
        self.discovered_companies_collection = self.db["construction_companies_discovered"]
        
        logger.info("✅ Construction Industry Discovery initialized")
    
    async def discover_companies_via_deepseek(self, max_companies: int = 500, session_id: str = None) -> List[Dict]:
        """
        Folosește DeepSeek pentru a descoperi companii din construcții
        
        DeepSeek generează o listă de companii relevante din România
        
        Args:
            max_companies: Numărul maxim de companii de descoperit
            progress_callback: Funcție callback pentru progres (opțional)
        """
        try:
            logger.info(f"🔍 Discovering construction companies via DeepSeek (max: {max_companies})")
            
            if self.logger and session_id:
                self.logger.log(session_id, "deepseek_discovery", f"🔍 Încep descoperirea a {max_companies} companii via DeepSeek...")
            
            # Log că începem apelul REAL la DeepSeek
            logger.info(f"📞 Calling REAL DeepSeek API for {max_companies} companies...")
            
            prompt = f"""Ești un expert în industria de construcții din România.

IMPORTANT: Returnează DOAR JSON valid, fără markdown, fără explicații, fără text înainte sau după JSON.

Generază o listă JSON cu {max_companies} de companii importante din industria de construcții din România.

Fiecare companie trebuie să aibă:
- nume_companie: numele complet
- domeniu: domeniul website-ului (ex: companie.ro)
- activitate: tipul de activitate (ex: "Construcții civile", "Instalații", "Proiectare")
- oras: orașul principal
- descriere_scurta: 1-2 propoziții despre companie

Format JSON EXACT (fără markdown, fără ```json):
{{
  "companii": [
    {{
      "nume_companie": "...",
      "domeniu": "...",
      "activitate": "...",
      "oras": "...",
      "descriere_scurta": "..."
    }}
  ]
}}

REGLI STRICTE:
1. Începe direct cu {{ (fără text înainte)
2. Termină cu }} (fără text după)
3. Fără markdown code blocks (```json sau ```)
4. Fără explicații sau comentarii
5. JSON valid și complet

Returnează DOAR JSON-ul de mai sus, nimic altceva."""

            # Apel REAL la DeepSeek API
            logger.info(f"📞 Making REAL API call to DeepSeek...")
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model="deepseek-chat",
                temperature=0.7,
                max_tokens=8000
            )
            
            # Log răspunsul primit
            logger.info(f"📥 DeepSeek API response received (type: {type(response)}, length: {len(str(response))})")
            
            # Parsează răspunsul
            if isinstance(response, dict):
                response_text = response.get("content", str(response))
            else:
                response_text = str(response)
            
            # Log primele 500 caractere pentru debugging
            logger.info(f"📄 Response preview (first 500 chars): {response_text[:500]}")
            
            if self.logger and session_id:
                self.logger.log(
                    session_id,
                    "deepseek_discovery",
                    f"📥 Răspuns REAL DeepSeek primit ({len(response_text)} caractere). Încep parsing JSON...",
                    {"response_length": len(response_text), "response_preview": response_text[:200]}
                )
            
            # Extrage JSON din răspuns
            import json
            import re
            
            companies = []
            
            # Încearcă mai multe metode de parsing
            parse_success = False
            companies = []
            
            # Metoda 1: Parsează întregul răspuns ca JSON
            try:
                data = json.loads(response_text)
                companies = data.get("companii", [])
                if companies:
                    logger.info(f"✅ Metoda 1 SUCCESS: Parsed JSON directly - {len(companies)} companies")
                    parse_success = True
                    if self.logger and session_id:
                        self.logger.log(
                            session_id,
                            "deepseek_discovery",
                            f"✅ JSON parsat cu succes (metoda 1): {len(companies)} companii găsite",
                            {"parsing_method": "direct", "companies_count": len(companies)}
                        )
            except Exception as e1:
                logger.warning(f"⚠️ Metoda 1 failed: {e1}")
            
            # Metoda 2: Elimină markdown și caută JSON
            if not parse_success:
                try:
                    cleaned_text = re.sub(r'```json\s*', '', response_text)
                    cleaned_text = re.sub(r'```\s*', '', cleaned_text)
                    cleaned_text = re.sub(r'^[^{]*', '', cleaned_text)  # Elimină text înainte de {
                    cleaned_text = re.sub(r'[^}]*$', '', cleaned_text)  # Elimină text după }
                    
                    if self.logger and session_id:
                        self.logger.log(
                            session_id,
                            "deepseek_discovery",
                            f"🔄 Încearcă metoda 2: eliminare markdown și regex...",
                            {"cleaned_length": len(cleaned_text)}
                        )
                    
                    # Caută JSON object care conține "companii"
                    json_match = re.search(r'\{[^{]*"companii"\s*:\s*\[[^\]]*\][^}]*\}', cleaned_text, re.DOTALL)
                    if not json_match:
                        # Încearcă un JSON mai mare care poate conține mai multe obiecte
                        json_match = re.search(r'\{.*?"companii".*?\}', cleaned_text, re.DOTALL)
                    
                    if json_match:
                        json_str = json_match.group(0)
                        # Încearcă să găsească sfârșitul corect al JSON-ului
                        brace_count = 0
                        end_pos = 0
                        for i, char in enumerate(json_str):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_pos = i + 1
                                    break
                        if end_pos > 0:
                            json_str = json_str[:end_pos]
                        
                        data = json.loads(json_str)
                        companies = data.get("companii", [])
                        if companies:
                            logger.info(f"✅ Metoda 2 SUCCESS: Parsed JSON from regex - {len(companies)} companies")
                            parse_success = True
                            if self.logger and session_id:
                                self.logger.log(
                                    session_id,
                                    "deepseek_discovery",
                                    f"✅ JSON parsat cu succes (metoda 2): {len(companies)} companii găsite",
                                    {"parsing_method": "regex_with_companii", "companies_count": len(companies)}
                                )
                except Exception as e2:
                    logger.warning(f"⚠️ Metoda 2 failed: {e2}")
            
            # Metoda 3: Caută array-ul de companii direct (mai robust)
            if not parse_success:
                try:
                    # Caută direct array-ul "companii" cu pattern mai robust
                    # Găsește "companii": [ ... ] inclusiv cu nested objects
                    pattern = r'"companii"\s*:\s*\['
                    start_match = re.search(pattern, response_text)
                    if start_match:
                        start_pos = start_match.end()
                        # Găsește sfârșitul array-ului (ultimul ] care închide array-ul)
                        bracket_count = 1
                        end_pos = start_pos
                        i = start_pos
                        while i < len(response_text) and bracket_count > 0:
                            if response_text[i] == '[':
                                bracket_count += 1
                            elif response_text[i] == ']':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    end_pos = i
                                    break
                            i += 1
                        
                        if end_pos > start_pos:
                            array_content = response_text[start_pos:end_pos]
                            # Parsează array-ul complet
                            array_json = '[' + array_content + ']'
                            try:
                                companies_list = json.loads(array_json)
                                for obj in companies_list:
                                    if isinstance(obj, dict) and (obj.get("nume_companie") or obj.get("domeniu")):
                                        companies.append(obj)
                                
                                if companies:
                                    logger.info(f"✅ Metoda 3 SUCCESS: Extracted {len(companies)} companies from array")
                                    parse_success = True
                                    if self.logger and session_id:
                                        self.logger.log(
                                            session_id,
                                            "deepseek_discovery",
                                            f"✅ JSON parsat cu succes (metoda 3): {len(companies)} companii găsite",
                                            {"parsing_method": "array_extraction", "companies_count": len(companies)}
                                        )
                            except Exception as parse_err:
                                logger.warning(f"⚠️ Metoda 3 - array parsing failed: {parse_err}")
                                # Fallback: încearcă să extragă obiecte individuale
                                objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', array_content)
                                for obj_str in objects:
                                    try:
                                        obj = json.loads(obj_str)
                                        if obj.get("nume_companie") or obj.get("domeniu"):
                                            companies.append(obj)
                                    except:
                                        continue
                                
                                if companies:
                                    logger.info(f"✅ Metoda 3 FALLBACK SUCCESS: Extracted {len(companies)} companies")
                                    parse_success = True
                except Exception as e3:
                    logger.warning(f"⚠️ Metoda 3 failed: {e3}")
            
            # Metoda 4: Parsing incremental - găsește primul { și ultimul } valid
            if not parse_success:
                try:
                    start_idx = response_text.find('{')
                    if start_idx >= 0:
                        # Găsește sfârșitul JSON-ului valid
                        brace_count = 0
                        end_idx = start_idx
                        for i in range(start_idx, len(response_text)):
                            if response_text[i] == '{':
                                brace_count += 1
                            elif response_text[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        if end_idx > start_idx:
                            json_str = response_text[start_idx:end_idx]
                            data = json.loads(json_str)
                            companies = data.get("companii", [])
                            if companies:
                                logger.info(f"✅ Metoda 4 SUCCESS: Parsed JSON incrementally - {len(companies)} companies")
                                parse_success = True
                                if self.logger and session_id:
                                    self.logger.log(
                                        session_id,
                                        "deepseek_discovery",
                                        f"✅ JSON parsat cu succes (metoda 4): {len(companies)} companii găsite",
                                        {"parsing_method": "incremental", "companies_count": len(companies)}
                                    )
                except Exception as e4:
                    logger.warning(f"⚠️ Metoda 4 failed: {e4}")
            
            # Dacă toate metodele au eșuat, loghează eroarea
            if not parse_success:
                logger.error(f"❌ TOATE METODELE DE PARSING AU EȘUAT!")
                logger.error(f"Response preview (first 2000 chars): {response_text[:2000]}")
                logger.error(f"Response preview (last 500 chars): {response_text[-500:]}")
                
                if self.logger and session_id:
                    self.logger.log(
                        session_id,
                        "deepseek_discovery",
                        f"❌ EROARE: Nu s-a putut parsa JSON din răspunsul DeepSeek",
                        {
                            "response_preview_start": response_text[:500],
                            "response_preview_end": response_text[-500:],
                            "response_length": len(response_text)
                        }
                    )
            
            logger.info(f"✅ Discovered {len(companies)} companies via DeepSeek")
            
            if self.logger and session_id:
                self.logger.log(session_id, "deepseek_discovery", f"✅ DeepSeek a generat {len(companies)} companii. Încep salvarea...")
            
            # Salvează companiile descoperite
            saved_count = 0
            saved_companies = []
            for company in companies:
                company["discovered_at"] = datetime.now(timezone.utc)
                company["source"] = "deepseek_discovery"
                company["status"] = "pending"
                self.discovered_companies_collection.update_one(
                    {"domeniu": company.get("domeniu")},
                    {"$set": company},
                    upsert=True
                )
                saved_count += 1
                saved_companies.append(company)
                
                # Log fiecare companie descoperită
                if self.logger and session_id:
                    self.logger.log(
                        session_id,
                        "deepseek_discovery",
                        f"📋 Descoperit: {company.get('nume_companie', 'N/A')} ({company.get('domeniu', 'N/A')})",
                        {
                            "company": company.get("nume_companie"),
                            "domain": company.get("domeniu"),
                            "activity": company.get("activitate"),
                            "saved_count": saved_count,
                            "total": len(companies)
                        }
                    )
            
            # Dacă parsing-ul a eșuat dar există companii salvate recent, le recuperăm din DB
            if len(saved_companies) == 0 and not parse_success:
                logger.warning("⚠️ Parsing failed, but checking for recently saved companies...")
                # Recuperează companiile salvate în ultimele 5 minute
                recent_companies = list(
                    self.discovered_companies_collection.find({
                        "discovered_at": {"$gte": datetime.now(timezone.utc) - timedelta(minutes=5)},
                        "source": "deepseek_discovery"
                    })
                )
                if recent_companies:
                    logger.info(f"✅ Found {len(recent_companies)} recently saved companies, using them instead")
                    saved_companies = recent_companies
                    saved_count = len(recent_companies)
            
            if self.logger and session_id:
                self.logger.log(
                    session_id,
                    "deepseek_discovery",
                    f"✅ Descoperire completă: {saved_count} companii salvate în baza de date",
                    {"total_companies": saved_count, "completed": True}
                )
            
            # Returnează companiile salvate (nu cele parse-uite, care pot fi goale)
            return saved_companies
            
        except Exception as e:
            logger.error(f"Error discovering companies: {e}")
            logger.error(traceback.format_exc())
            return []
    
    async def discover_companies_via_web_search(self, keywords: List[str], max_per_keyword: int = 20) -> List[Dict]:
        """
        Descoperă companii prin căutări web (Brave Search API)
        """
        try:
            from google_competitor_discovery import GoogleCompetitorDiscovery
            
            logger.info(f"🔍 Discovering companies via web search for {len(keywords)} keywords")
            
            discovery = GoogleCompetitorDiscovery()
            all_companies = []
            
            for keyword in keywords:
                try:
                    # Caută companii pentru acest keyword
                    results = await discovery.search_keyword(
                        keyword=keyword,
                        num_results=max_per_keyword,
                        country="RO"
                    )
                    
                    for result in results:
                        domain = result.get("domain", "")
                        if domain and domain not in [c.get("domeniu", "") for c in all_companies]:
                            all_companies.append({
                                "nume_companie": domain.replace(".ro", "").replace("www.", "").title(),
                                "domeniu": domain,
                                "activitate": keyword,
                                "oras": "România",
                                "descriere_scurta": f"Companie din domeniul {keyword}",
                                "discovered_at": datetime.now(timezone.utc),
                                "source": "web_search",
                                "status": "pending"
                            })
                    
                    # Pauză între căutări
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"Error searching for keyword {keyword}: {e}")
                    continue
            
            # Salvează companiile descoperite
            for company in all_companies:
                self.discovered_companies_collection.update_one(
                    {"domeniu": company.get("domeniu")},
                    {"$set": company},
                    upsert=True
                )
            
            logger.info(f"✅ Discovered {len(all_companies)} companies via web search")
            return all_companies
            
        except Exception as e:
            logger.error(f"Error in web search discovery: {e}")
            logger.error(traceback.format_exc())
            return []


class MassAgentCreator:
    """Creează agenți în masă pentru industria de construcții"""
    
    def __init__(self, mongo_client: MongoClient, llm: LLMOrchestrator):
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.llm = llm
        
        # Collections
        self.agents_collection = self.db["site_agents"]
        self.mass_creation_progress = self.db["mass_agent_creation_progress"]
        
        logger.info("✅ Mass Agent Creator initialized")
    
    async def create_agent_for_company(self, company: Dict, priority: int = 0) -> Dict:
        """
        Creează un agent master pentru o companie
        
        Args:
            company: Dict cu datele companiei
            priority: Prioritate (0 = normal, 1 = high)
        
        Returns:
            Dict cu rezultatul creării
        """
        try:
            domain = company.get("domeniu", "")
            if not domain:
                return {"success": False, "error": "No domain provided"}
            
            # Verifică dacă agentul există deja
            existing = self.agents_collection.find_one({"domain": domain})
            if existing:
                return {
                    "success": True,
                    "agent_id": str(existing["_id"]),
                    "status": "already_exists",
                    "domain": domain
                }
            
            # Construiește URL
            if not domain.startswith("http"):
                site_url = f"https://{domain}"
            else:
                site_url = domain
            
            logger.info(f"🏗️ Creating agent for {domain}...")
            
            # Creează agent folosind CEOMasterWorkflow
            workflow = CEOMasterWorkflow()
            result = await workflow.execute_full_workflow(site_url=site_url)
            
            if result.get("status") == "completed":
                agent_id = result.get("agent_id")
                
                # Actualizează compania ca procesată
                self.db.construction_companies_discovered.update_one(
                    {"domeniu": domain},
                    {
                        "$set": {
                            "status": "agent_created",
                            "agent_id": agent_id,
                            "created_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                return {
                    "success": True,
                    "agent_id": agent_id,
                    "status": "created",
                    "domain": domain
                }
            else:
                error = result.get("error", "Unknown error")
                return {
                    "success": False,
                    "error": error,
                    "domain": domain
                }
                
        except Exception as e:
            logger.error(f"Error creating agent for {company.get('domeniu', 'unknown')}: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "domain": company.get("domeniu", "unknown")
            }
    
    async def create_mass_agents(
        self,
        companies: List[Dict],
        max_parallel: Optional[int] = None,  # Auto-calculează dacă None
        batch_id: Optional[str] = None
    ) -> Dict:
        """
        Creează agenți în masă pentru o listă de companii
        
        Args:
            companies: Lista de companii
            max_parallel: Numărul maxim de agenți creați în paralel (None = auto-calculează)
            batch_id: ID-ul batch-ului (opțional)
        
        Returns:
            Dict cu rezultatele
        """
        try:
            # Auto-calculează max_parallel dacă nu este specificat
            if max_parallel is None:
                try:
                    from gpu_optimizer import get_gpu_optimizer
                    optimizer = get_gpu_optimizer(gpu_count=11, gpu_memory_gb=12)
                    max_parallel = optimizer.get_optimal_parallel_count("optimal")
                    logger.info(f"🎯 Auto-calculat max_parallel: {max_parallel} (optim pentru 11x RTX 3080 Ti)")
                except Exception as e:
                    logger.warning(f"⚠️ Could not auto-calculate max_parallel: {e}, using default 20")
                    max_parallel = 20
            
            if not batch_id:
                batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            
            logger.info(f"🏗️ Starting mass agent creation: {len(companies)} companies, {max_parallel} parallel, batch_id: {batch_id}")
            
            # Creează entry pentru tracking
            progress_entry = {
                "batch_id": batch_id,
                "total_companies": len(companies),
                "created": 0,
                "failed": 0,
                "already_exists": 0,
                "in_progress": 0,
                "started_at": datetime.now(timezone.utc),
                "status": "running"
            }
            self.mass_creation_progress.insert_one(progress_entry)
            
            # Procesează companiile în batch-uri paralele
            semaphore = asyncio.Semaphore(max_parallel)
            results = []
            
            async def create_with_semaphore(company):
                async with semaphore:
                    result = await self.create_agent_for_company(company)
                    results.append(result)
                    
                    # Actualizează progresul
                    if result.get("success"):
                        if result.get("status") == "already_exists":
                            self.mass_creation_progress.update_one(
                                {"batch_id": batch_id},
                                {"$inc": {"already_exists": 1}}
                            )
                        else:
                            self.mass_creation_progress.update_one(
                                {"batch_id": batch_id},
                                {"$inc": {"created": 1}}
                            )
                    else:
                        self.mass_creation_progress.update_one(
                            {"batch_id": batch_id},
                            {"$inc": {"failed": 1}}
                        )
            
            # Rulează toate creările
            tasks = [create_with_semaphore(company) for company in companies]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Finalizează progresul
            self.mass_creation_progress.update_one(
                {"batch_id": batch_id},
                {
                    "$set": {
                        "status": "completed",
                        "completed_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            summary = {
                "batch_id": batch_id,
                "total": len(companies),
                "created": sum(1 for r in results if r.get("success") and r.get("status") == "created"),
                "already_exists": sum(1 for r in results if r.get("success") and r.get("status") == "already_exists"),
                "failed": sum(1 for r in results if not r.get("success")),
                "results": results
            }
            
            logger.info(f"✅ Mass agent creation completed: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in mass agent creation: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "batch_id": batch_id
            }


class ConstructionIndustryOrchestrator:
    """Orchestrator principal pentru transformarea industriei de construcții"""
    
    def __init__(self, mongo_client: MongoClient):
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.llm = LLMOrchestrator()
        
        # Initialize logger
        from industry_transformation_logger import IndustryTransformationLogger
        self.logger = IndustryTransformationLogger(mongo_client)
        
        self.discovery = ConstructionIndustryDiscovery(mongo_client, self.llm, self.logger)
        self.creator = MassAgentCreator(mongo_client, self.llm)
        
        logger.info("✅ Construction Industry Orchestrator initialized")
    
    async def transform_entire_industry(
        self,
        discovery_method: str = "deepseek",  # "deepseek" sau "web_search"
        max_companies: int = 500,
        max_parallel_agents: int = 5,
        web_search_keywords: Optional[List[str]] = None
    ) -> Dict:
        """
        Transformă întreaga industrie de construcții în agenți AI
        
        Args:
            discovery_method: Metoda de descoperire ("deepseek" sau "web_search")
            max_companies: Numărul maxim de companii de descoperit
            max_parallel_agents: Numărul maxim de agenți creați în paralel
            web_search_keywords: Keywords pentru web search (dacă discovery_method = "web_search")
        
        Returns:
            Dict cu rezultatele transformării
        """
        try:
            # Generează session ID
            session_id = f"transformation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            
            logger.info(f"🏗️ Starting industry transformation (session: {session_id})...")
            
            if self.logger:
                self.logger.log(session_id, "start", f"🚀 Pornire transformare industrie construcții - {max_companies} companii, {max_parallel_agents} paralel")
            
            # FAZA 1: Descoperire companii
            logger.info("📍 FAZA 1: Descoperire companii...")
            if self.logger:
                self.logger.log(session_id, "discovery_start", f"🔍 FAZA 1: Încep descoperirea companiilor (metodă: {discovery_method})")
            
            if discovery_method == "deepseek":
                companies = await self.discovery.discover_companies_via_deepseek(max_companies=max_companies, session_id=session_id)
            elif discovery_method == "web_search":
                if not web_search_keywords:
                    web_search_keywords = [
                        "constructii romania",
                        "firma constructii",
                        "proiectare constructii",
                        "instalatii sanitare",
                        "instalatii electrice",
                        "tamplarie metalica",
                        "tamplarie pvc",
                        "vopsitorie",
                        "gips-carton",
                        "parchet",
                        "faianta",
                        "constructii civile",
                        "renovari",
                        "amenajari interioare"
                    ]
                companies = await self.discovery.discover_companies_via_web_search(
                    keywords=web_search_keywords,
                    max_per_keyword=20
                )
            else:
                raise ValueError(f"Unknown discovery method: {discovery_method}")
            
            logger.info(f"✅ Discovered {len(companies)} companies")
            
            if self.logger:
                self.logger.log(session_id, "discovery_complete", f"✅ FAZA 1 completă: {len(companies)} companii descoperite")
            
            # FAZA 2: Creare agenți în masă
            logger.info("📍 FAZA 2: Creare agenți în masă...")
            if self.logger:
                self.logger.log(session_id, "creation_start", f"🏗️ FAZA 2: Încep crearea agenților ({max_parallel_agents} paralel)")
            
            creation_result = await self.creator.create_mass_agents(
                companies=companies,
                max_parallel=max_parallel_agents
            )
            
            logger.info("✅ Industry transformation completed!")
            
            if self.logger:
                self.logger.log(
                    session_id,
                    "complete",
                    f"✅ Transformare completă: {creation_result.get('created', 0)} agenți creați, {creation_result.get('failed', 0)} eșuate",
                    creation_result
                )
            
            return {
                "success": True,
                "session_id": session_id,
                "discovery": {
                    "method": discovery_method,
                    "companies_discovered": len(companies)
                },
                "creation": creation_result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error transforming industry: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

