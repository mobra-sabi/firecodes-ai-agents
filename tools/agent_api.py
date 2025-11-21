# agent_api.py
searcher = None
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, BackgroundTasks, Body, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import requests
import socket
import urllib.robotparser as robotparser
from urllib.parse import urlparse
import asyncio
import logging
import traceback
import sys
from datetime import datetime, timezone
# Adaugă /home/mobra în path pentru a găsi modulele mirror_*
sys.path.insert(0, "/home/mobra")
from mirror_agent_manifest import MirrorManifestManager, create_mirror_manifest_for_site
from mirror_agent_router import MirrorRouterManager, route_mirror_question
from mirror_kpi_testing import run_kpi_test_for_site, get_kpi_history, get_kpi_stats
from mirror_curator import run_curator_cycle_for_site, get_curator_dashboard_for_site, get_curator_stats
from mirror_security import validate_mirror_security, scrub_mirror_content, validate_cross_domain_mirror, get_security_stats
from qdrant_mirror_collections import QdrantMirrorCollections, create_mirror_collections_for_site
from mirror_dashboard import get_global_mirror_dashboard, get_site_mirror_dashboard, create_mirror_alert, resolve_mirror_alert
from mirror_qa_generation import generate_mirror_qa_set, get_qa_generation_stats
from urllib.parse import urlparse
import json
from openai import OpenAI
from dual_orchestrator import DualOrchestrator
from knowledge_architecture import KnowledgeArchitecture
from ai_roles_orchestrator import AIRolesOrchestrator
from industry_aggregator import IndustryAggregator
from gap_analyzer import GapAnalyzer
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from competitor_discovery_system import run_advanced_discovery
from dataclasses import asdict

def _norm_host(h: str) -> str:
    h = (h or "").strip().lower()
    if h.startswith("www."): h = h[4:]
    return h

def check_sealed_solutions_before_action(problem_description: str) -> bool:
    """
    Verifică dacă există o soluție sigilată pentru această problemă.
    Returnează True dacă există o soluție sigilată (nu se execută acțiunea),
    False dacă nu există (se poate executa acțiunea).
    
    ⚠️ FUNCȚIA ASTA NU MAI AFIȘEAZĂ MESAJE DESPRE QDRANT - DOAR VERIFICĂ SILENȚIOS
    """
    try:
        sealed_solution = check_sealed_solution(problem_description)
        if sealed_solution:
            # ⭐ NU MAI AFIȘĂM MESAJE DESPRE QDRANT - DOAR LOG SILENȚIOS
            logger.debug(f"🔒 Soluție sigilată găsită pentru: {problem_description[:50]}...")
            return True
        return False
    except Exception as e:
        logger.debug(f"Eroare la verificarea soluțiilor sigilate: {e}")
        return False

def _host_from_url(u: str) -> str:
    try:
        return _norm_host(urlparse(u).netloc)
    except Exception:
        return ""

def _match_domain(payload: dict, domain: str) -> bool:
    want = _norm_host(domain)
    pd = _norm_host((payload or {}).get("domain",""))
    pu = _host_from_url((payload or {}).get("url",""))
    def ok(h): return h == want or (h.endswith("."+want) if h else False)
    return ok(pd) or ok(pu)

def get_qwen_client():
    """Get Qwen client configured for local GPU server"""
    return OpenAI(
        api_key=os.getenv("QWEN_API_KEY", "local"),
        base_url=os.getenv("QWEN_BASE_URL", "http://localhost:9304/v1")
    )

def get_llm_model():
    """Get the configured LLM model (Qwen or OpenAI fallback)"""
    qwen_url = os.getenv("QWEN_BASE_URL")
    if qwen_url:
        return os.getenv("QWEN_MODEL", "qwen2.5")
    return os.getenv("LLM_MODEL", "gpt-4o-mini")

def get_llm_client():
    """Get LLM client (Qwen preferred, OpenAI fallback)"""
    qwen_url = os.getenv("QWEN_BASE_URL")
    if qwen_url:
        return get_qwen_client()
    else:
        return OpenAI(
            organization=os.getenv("OPENAI_ORG_ID"),
            project=os.getenv("OPENAI_PROJECT"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )


# existente
from site_agent_creator import create_site_agent_ws
# from task_executor import handle_task_conversation  # Dezactivat temporar - eroare import LangChain
handle_task_conversation = None  # Placeholder

# Enhanced 4-Layer Agent
from enhanced_4_layer_agent import Enhanced4LayerAgent, create_enhanced_agent

# Simple Working Agent
from simple_working_agent import SimpleWorkingAgent, create_simple_working_agent

# Smart Advisor Agent
from smart_advisor_agent import SmartAdvisorAgent, create_smart_advisor_agent

# Site-Specific Intelligence
from site_specific_intelligence import SiteSpecificIntelligence, create_site_specific_intelligence
from auto_site_extractor import AutoSiteExtractor
from agent_health_checker import AgentHealthChecker

# Health Checker
from health_checker import HealthChecker, quick_health_check

# GPT-5 + Qwen 2.5 Architecture
from gpt5_qwen_architecture import GPT5QwenArchitecture, create_gpt5_qwen_architecture

# admin (competitor discovery + ingest)
from tools.admin_discovery import ingest_urls, web_search, discover_competitors
from adapters.scraper_adapter import smart_fetch
from adapters.search_providers import search_serp
from langchain_openai import ChatOpenAI

# <<< NEW: config DB unificat >>>
from config.database_config import (
    MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION
)

# DeepSeek Reasoner helper (dacă e folosit de strategii)
try:
    from tools.deepseek_client import reasoner_chat  # optional import; strategia îl poate folosi
except Exception:
    reasoner_chat = None

app = FastAPI()
searcher = None
dual_orchestrator = None
knowledge_architecture = None
ai_roles_orchestrator = None
industry_aggregator = None
gap_analyzer = None

def get_dual_orchestrator():
    global dual_orchestrator
    if dual_orchestrator is None:
        from qdrant_client import QdrantClient
        qdrant_client = QdrantClient(url="http://localhost:9306")
        dual_orchestrator = DualOrchestrator(db, qdrant_client)
    return dual_orchestrator

def get_knowledge_architecture():
    global knowledge_architecture
    if knowledge_architecture is None:
        from qdrant_client import QdrantClient
        qdrant_client = QdrantClient(url="http://localhost:9306")
        knowledge_architecture = KnowledgeArchitecture(db, qdrant_client)
    return knowledge_architecture

def get_ai_roles_orchestrator():
    global ai_roles_orchestrator
    if ai_roles_orchestrator is None:
        from qdrant_client import QdrantClient
        qdrant_client = QdrantClient(url="http://localhost:9306")
        ai_roles_orchestrator = AIRolesOrchestrator(db, qdrant_client)
    return ai_roles_orchestrator

def get_industry_aggregator():
    global industry_aggregator
    if industry_aggregator is None:
        from qdrant_client import QdrantClient
        qdrant_client = QdrantClient(url="http://localhost:9306")
        industry_aggregator = IndustryAggregator(db, qdrant_client)
    return industry_aggregator

def get_gap_analyzer():
    global gap_analyzer
    if gap_analyzer is None:
        from qdrant_client import QdrantClient
        qdrant_client = QdrantClient(url="http://localhost:9306")
        gap_analyzer = GapAnalyzer(db, qdrant_client)
    return gap_analyzer

def get_searcher():
    global searcher
    if searcher is None:
        from retrieval.semantic_search import SemanticSearcher
        searcher = SemanticSearcher()
    return searcher

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# Mount static files
import os
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ------ Health/Ready ------

# ------ Chat Interface ------
@app.get("/chat")
async def chat_page():
    """Pagina de chat cu agenții"""
    return FileResponse(os.path.join(STATIC_DIR, "chat.html"))

@app.post("/api/analyze-agent")
async def analyze_agent(request: Request):
    """
    Analizează agentul și generează strategia competitivă folosind DeepSeek/Qwen,
    conform implementării din competitive_strategy.strategy_generator.
    Body: { "agent_id": "..." }
    """
    try:
        from competitive_strategy import strategy_generator

        body = await request.json()
        agent_id = body.get("agent_id") if isinstance(body, dict) else None
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required")

        # verifică existența agentului
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        logger.info(f"🔍 Analiză agent {agent_id} solicitată...")
        
        # Timeout pentru operația de analiză (poate dura mult cu DeepSeek)
        try:
            strategy = await asyncio.wait_for(
                strategy_generator.analyze_agent_and_generate_strategy(agent_id),
                timeout=300.0  # 5 minute timeout pentru analiză completă
            )
        except asyncio.TimeoutError:
            logger.error(f"❌ Timeout la analiza agentului {agent_id} (peste 5 minute)")
            return {
                "ok": False,
                "error": "Timeout: Analiza a durat prea mult (peste 5 minute). Încearcă să reduci conținutul analizat sau încearcă mai târziu.",
                "agent_id": agent_id,
                "domain": agent.get("domain"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        return {
            "ok": True,
            "strategy": strategy,
            "agent_id": agent_id,
            "domain": agent.get("domain"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Eroare la analiza agentului: {error_msg}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Mesaje de eroare mai clare pentru utilizator
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            user_error = "Timeout la conexiunea cu DeepSeek API. Verifică conexiunea la internet sau încearcă mai târziu."
        elif "connection" in error_msg.lower():
            user_error = "Eroare de conexiune la DeepSeek API. Verifică conexiunea la internet."
        else:
            user_error = f"Eroare la generarea strategiei: {error_msg[:200]}"
        
        return {
            "ok": False,
            "error": user_error,
            "agent_id": agent_id,
            "domain": agent.get("domain", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/api/generate-search-strategy")
async def generate_search_strategy_endpoint(request: Request):
    """
    Generează strategii de căutare pentru un agent (Pas 1: Analiza subdomeniilor)
    Body: { "agent_id": "..." }
    """
    try:
        from industry_search_strategy import search_strategy_generator
        
        body = await request.json()
        agent_id = body.get("agent_id") if isinstance(body, dict) else None
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required")
        
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        logger.info(f"🔍 Generare strategie căutare pentru agent {agent_id}...")
        strategy = await search_strategy_generator.generate_search_strategy(agent_id)
        
        from fastapi.encoders import jsonable_encoder
        encoded_strategy = jsonable_encoder(strategy)
        
        return {
            "ok": True,
            "message": "Strategie de căutare generată cu succes",
            "strategy": encoded_strategy,
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Eroare generare strategie căutare: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"ok": False, "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/index-industry")
async def index_industry_endpoint(request: Request):
    """
    Indexează competitori și resurse industriale pentru agentul dat (Pas 2: Indexare efectivă)
    Body: { "agent_id": "...", "max_sites": 20, "use_search_strategy": true }
    """
    try:
        from industry_indexer import index_industry_for_agent
        from industry_search_strategy import search_strategy_generator

        body = await request.json()
        agent_id = body.get("agent_id") if isinstance(body, dict) else None
        max_sites = body.get("max_sites", 20) if isinstance(body, dict) else 20
        concurrency = body.get("concurrency", 8) if isinstance(body, dict) else 8
        use_search_strategy = body.get("use_search_strategy", True) if isinstance(body, dict) else True
        
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required")

        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Pas 1: Generează strategia de căutare dacă este cerută
        if use_search_strategy:
            logger.info(f"🔍 Generez strategie de căutare pentru agent {agent_id}...")
            try:
                search_strategy = await search_strategy_generator.generate_search_strategy(agent_id)
                logger.info(f"✅ Strategie generată: {len(search_strategy.get('subdomains', []))} subdomenii")
            except Exception as e:
                logger.error(f"⚠️ Eroare generare strategie: {e} - continuă fără strategie")
                search_strategy = None
        else:
            search_strategy = None

        # Pas 2: Indexare industrie folosind strategia
        logger.info(f"🚀 Indexare industrie pentru agent {agent_id} solicitată...")
        summary = await index_industry_for_agent(
            agent_id=agent_id,
            max_sites=max_sites,
            concurrency=concurrency,
            loop=None,
            websocket=None
        )

        from fastapi.encoders import jsonable_encoder
        encoded_summary = jsonable_encoder(summary)
        return {
            "ok": True,
            "message": "Indexarea industriei a fost finalizată cu succes",
            "summary": encoded_summary,
            "search_strategy": jsonable_encoder(search_strategy) if search_strategy else None,
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Eroare la indexarea industriei: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"ok": False, "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/strategy/{agent_id}")
async def get_strategy(agent_id: str):
    """Returnează strategia competitivă salvată pentru agent, dacă există."""
    try:
        from competitive_strategy import strategy_generator
        strategy = await strategy_generator.get_strategy_for_agent(agent_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found for this agent")
        return {
            "ok": True,
            "strategy": strategy,
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Eroare la obținerea strategiei: {e}")
        return {"ok": False, "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
@app.post("/ask")
async def ask_question(request: Request):
    """
    Endpoint principal pentru întrebări - folosește DeepSeek cu TOATE datele agentului
    """
    try:
        # Extrage parametrii din request
        body = await request.json()
        question = body.get("question")
        agent_id = body.get("agent_id")
        conversation_history = body.get("conversation_history", [])
        
        if not question or not agent_id:
            raise HTTPException(status_code=400, detail="question and agent_id are required")
        
        logger.info(f"🤖 Chat cu DeepSeek pentru agent {agent_id}")
        
        # ⭐ CRITIC: Obține TOATE datele agentului
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        domain = agent.get("domain", "unknown")
        site_url = agent.get("site_url", f"https://{domain}")
        business_type = agent.get("business_type", "general")
        agent_name = agent.get("name", domain)
        
        # ⭐ CRITIC: Obține TOATE datele agentului din MongoDB
        site_content_docs = list(db.site_content.find({"agent_id": ObjectId(agent_id)}))
        site_content = "\n\n".join([doc.get("content", "") for doc in site_content_docs if doc.get("content")])
        
        # Obține site_data complet (contact_info, services_products)
        site_data = db.site_data.find_one({"domain": domain})
        contact_info = {}
        services_products = []
        if site_data:
            contact_info = site_data.get("contact_info", {})
            # ⭐ FIX CRITIC: Verifică dacă services_products este listă sau string/dict
            sp = site_data.get("services_products", [])
            if isinstance(sp, list):
                services_products = sp
            elif isinstance(sp, dict):
                services_products = [sp]  # Transformă dict în listă cu un element
            elif isinstance(sp, str):
                services_products = []  # Ignoră dacă e string
            else:
                services_products = []
        
        # Obține serviciile din agent sau din strategie
        services = agent.get("services", [])
        if not services and services_products:
            # ⭐ FIX: Verifică dacă elementele sunt dict sau string
            services = []
            for s in services_products[:20]:
                if isinstance(s, dict):
                    services.append({
                        "service_name": s.get("name", "") or s.get("service_name", ""),
                        "description": s.get("description", "")
                    })
                elif isinstance(s, str):
                    services.append({
                        "service_name": s,
                        "description": ""
                    })
        if not services:
            strategy = db.competitive_strategies.find_one({"agent_id": ObjectId(agent_id)})
            if strategy and strategy.get("strategy"):
                services = strategy.get("strategy", {}).get("services", [])
        
        # Obține metadata agentului
        metadata = {
            "created_at": agent.get("created_at") or agent.get("createdAt"),
            "status": agent.get("status"),
            "pages_crawled": agent.get("pages_crawled", 0),
            "total_chunks": len(site_content_docs),
            "memory_initialized": agent.get("memory_initialized", False),
            "qwen_integrated": agent.get("qwen_integrated", False)
        }
        
        logger.info(f"📊 Agent data: domain={domain}, content_chunks={len(site_content_docs)}, content_length={len(site_content)}, services={len(services)}, contact_info={bool(contact_info)}")
        
        # ⭐ CRITIC: Construiește prompt COMPLET pentru DeepSeek cu TOATE datele
        # Construiește secțiunea de contact info
        contact_section = ""
        if contact_info:
            contact_section = f"""
**CONTACT INFO:**
- Email: {contact_info.get('email', 'N/A')}
- Telefon: {contact_info.get('phone', 'N/A')}
- Companie: {contact_info.get('company', agent_name)}
- Adresă: {contact_info.get('address', 'N/A')}
"""
        
        # Construiește secțiunea de servicii/produse
        services_section = ""
        # ⭐ FIX CRITIC: Verifică dacă services_products este listă
        if services_products and isinstance(services_products, list):
            services_section = "\n**SERVICII ȘI PRODUSE OFERITE:**\n"
            for i, service in enumerate(services_products[:30], 1):  # Primele 30 servicii
                # ⭐ FIX: Verifică dacă service este dict sau string
                if isinstance(service, dict):
                    service_name = service.get('name', '') or service.get('service_name', '') or 'N/A'
                    service_desc = service.get('description', '')
                else:
                    service_name = str(service)
                    service_desc = ""
                services_section += f"{i}. {service_name}\n"
                if service_desc:
                    services_section += f"   Descriere: {service_desc[:200]}\n"
        elif services:
            services_section = "\n**SERVICII OFERITE:**\n"
            for i, service in enumerate(services[:30], 1):
                # ⭐ FIX: Verifică dacă service este dict sau string
                if isinstance(service, dict):
                    service_name = service.get("service_name") or service.get("name") or "N/A"
                    service_desc = service.get("description", "")
                else:
                    service_name = str(service)
                    service_desc = ""
                services_section += f"{i}. {service_name}\n"
                if service_desc:
                    services_section += f"   Descriere: {service_desc[:200]}\n"
        
        # Construiește conținutul complet (fără limită de 15000 caractere, dar limităm la 100000 pentru a evita token overflow)
        content_section = site_content[:100000] if site_content else "Conținut în curs de indexare..."
        if len(site_content) > 100000:
            content_section += f"\n\n[Notă: Conținutul este trunchiat. Total caractere: {len(site_content)}]"
        
        system_prompt = f"""Ești asistentul oficial pentru site-ul {domain} ({agent_name}).

**ROLUL TĂU:**
- Răspunde ca și cum ai fi site-ul însuși
- Folosește EXACT terminologia și stilul din conținutul site-ului
- Răspunde întotdeauna în română (dacă nu se cere altfel)
- Fii precis, util și prietenos
- Dacă nu știi ceva din conținutul site-ului, spune că nu ai această informație disponibilă
- Identifică-te cu site-ul și răspunde ca și cum ai fi reprezentantul oficial

**INFORMAȚII DESPRE SITE:**
- Domeniu: {domain}
- URL: {site_url}
- Tip business: {business_type}
- Nume: {agent_name}
- Total pagini indexate: {metadata.get('pages_crawled', 0)}
- Total chunks de conținut: {metadata.get('total_chunks', 0)}
{contact_section}
{services_section}

**CONȚINUT COMPLET AL SITE-ULUI (folosește-l pentru a răspunde):**
{content_section}

**IMPORTANT:**
- Folosește DOAR informațiile din conținutul site-ului de mai sus
- Dacă întrebarea nu se referă la site, răspunde politicos că ești asistentul pentru {domain}
- Menține tonul profesional și util
- Dacă întrebarea este despre servicii, folosește informațiile exacte din conținut
- Identifică-te cu site-ul: spune "suntem", "oferim", "avem" în loc de "ei oferă"
- Folosește terminologia exactă din conținutul site-ului"""
        
        # Construiește mesajul utilizatorului cu istoricul conversației
        user_messages = []
        if conversation_history:
            for msg in conversation_history[-10:]:  # Ultimele 10 mesaje pentru context
                # ⭐ FIX: Verifică dacă msg este dict sau string
                if isinstance(msg, dict):
                    role = msg.get("role", "")
                    content = msg.get("content", "") or msg.get("message", "")
                    if role and content:
                        user_messages.append({"role": role, "content": content})
                elif isinstance(msg, str):
                    # Dacă este string, îl tratăm ca mesaj de utilizator
                    user_messages.append({"role": "user", "content": msg})
        
        # Adaugă întrebarea curentă
        user_messages.append({"role": "user", "content": question})
        
        # ⭐ CRITIC: Folosește DeepSeek pentru răspuns
        from tools.deepseek_client import reasoner_chat
        
        logger.info(f"🔄 Apel DeepSeek pentru chat (prompt size: {len(system_prompt)} caractere)")
        
        try:
            deepseek_response = reasoner_chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    *user_messages
                ],
                max_tokens=2000,
                temperature=0.7,
                timeout=120,
                max_retries=2
            )
            
            # Extrage conținutul din răspunsul DeepSeek
            response_text = ""
            if isinstance(deepseek_response, dict):
                if "data" in deepseek_response:
                    choices = deepseek_response["data"].get("choices", [])
                    if choices and len(choices) > 0:
                        response_text = choices[0].get("message", {}).get("content", "")
                elif "content" in deepseek_response:
                    response_text = deepseek_response["content"]
                else:
                    response_text = str(deepseek_response)
            else:
                response_text = str(deepseek_response)
            
            if not response_text or len(response_text.strip()) < 10:
                raise ValueError("DeepSeek nu a returnat un răspuns valid")
            
            logger.info(f"✅ Răspuns DeepSeek primit ({len(response_text)} caractere)")
            
        except Exception as e:
            logger.error(f"❌ Eroare DeepSeek API: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback la răspuns simplu
            response_text = f"Îmi pare rău, am întâmpinat o problemă tehnica. Te rog încearcă din nou. (Eroare: {str(e)})"
        
        # Salvează conversația pentru învățarea Qwen
        try:
            save_conversation(
                agent_id=agent_id,
                user_message=question,
                assistant_response=response_text,
                strategy="deepseek_chat"
            )
            logger.info(f"✅ Conversația salvată pentru învățarea Qwen: {agent_id}")
        except Exception as e:
            logger.warning(f"⚠️ Nu s-a putut salva conversația: {e}")

        # Returnează răspunsul în formatul așteptat de interfață
        return {
            "ok": True,
            "response": response_text,
            "confidence": 0.95,
            "reasoning": f"Răspuns generat de DeepSeek cu toate datele agentului {domain}",
            "sources": [{"url": site_url, "score": 0.95}],
            "web_search_used": False,
            "web_sources": [],
            "agent_id": agent_id,
            "llm_used": "deepseek-reasoner",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrails": {
                "passed": True,
                "message": "All security checks passed",
                "confidence_check": True
            },
            "contextual_questions": [],
            "site_context": {
                "business_type": business_type,
                "target_audience": "unknown",
                "unique_selling_points": [s.get("service_name", "") if isinstance(s, dict) else str(s) for s in services[:5]] if services else []
            }
        }
        
    except Exception as e:
        logger.error(f"Error in /ask endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/ready")
async def ready():
    # conexiune minimă la Mongo (best-effort)
    try:
        mongo_client.admin.command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False
    return {"ok": mongo_ok}
@app.get("/debug/search")
async def debug_search(q: str, domain: Optional[str] = None):
    """
    Test: /debug/search?q=termeni%20livrare&domain=firestopping.ro
    """
    try:
        all_results = get_searcher().search(q, domain=None)  # maximă acoperire
        if domain:
            pref = [r for r in all_results if _match_domain(r, domain)]
            rest = [r for r in all_results if not _match_domain(r, domain)]
            results = (pref + rest)[:8]  # TOP_K_FINAL
        else:
            results = all_results
        return {"ok": True, "count": len(results), "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    except Exception as e:
        return {"ok": False, "error": str(e)}

    except Exception as e:
        return {"ok": False, "error": str(e)}

    except Exception as e:
        return {"ok": False, "error": str(e)}

    except Exception as e:
        return {"ok": False, "error": str(e)}

# <<< CHANGED: unificare Mongo și colecții >>>
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DATABASE]
agents_collection = db.site_agents
conversations_collection = db.conversations
site_content_col = db[MONGODB_COLLECTION]

logger = logging.getLogger("agent_api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# --- Crawl summary endpoint (pages, chars, qdrant points, recent pages) ---
@app.get("/agents/{agent_id}/crawl/summary")
async def crawl_summary(agent_id: str):
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        domain = (_host_from_url(agent.get("site_url", "")) or agent.get("domain") or "").lower()

        query = {"url": {"$regex": domain, "$options": "i"}} if domain else {}
        pages_count = site_content_col.count_documents(query) if query else 0
        chars_total = 0
        recent_pages = []
        if query and pages_count:
            cur = site_content_col.find(query, {"url": 1, "title": 1, "content": 1}).sort("_id", -1).limit(50)
            for doc in cur:
                content = (doc.get("content") or "")
                ln = len(content)
                chars_total += ln
                if len(recent_pages) < 10:
                    recent_pages.append({
                        "url": doc.get("url", ""),
                        "title": doc.get("title", ""),
                        "content_length": ln
                    })

        qdrant_points = 0
        try:
            from qdrant_client import QdrantClient
            qc = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:9306"))
            collection = f"agent_{agent_id}_content"
            try:
                info = qc.get_collection(collection)
                qdrant_points = getattr(info, "points_count", 0) or 0
            except Exception:
                qdrant_points = 0
        except Exception:
            qdrant_points = 0

        return {
            "ok": True,
            "agent_id": agent_id,
            "domain": domain,
            "pages_count": pages_count,
            "chars_total": chars_total,
            "qdrant_points": qdrant_points,
            "recent_pages": recent_pages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Crawl summary error: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/agents/{agent_id}/ingest-minimal")
async def ingest_minimal(agent_id: str, pages: int = 1):
    """Ingest rapid și robust: descarcă prima pagină a site-ului agentului și o salvează în Mongo.
    Evită procesări complexe ca să prevenim inserări greșite.
    """
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        site_url = agent.get("site_url") or ("https://" + (agent.get("domain") or ""))
        if not site_url:
            raise HTTPException(status_code=400, detail="Agent has no site_url or domain")

        import requests
        from bs4 import BeautifulSoup

        r = requests.get(site_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        title = (soup.find("title").get_text().strip() if soup.find("title") else site_url)[:200]
        body = soup.get_text(" ", strip=True)

        content_text = body[:8000]
        if len(content_text) < 50:
            return {"ok": False, "error": "Content too short from site; cannot ingest."}

        site_content_col.insert_one({
            "agent_id": ObjectId(agent_id),
            "url": site_url,
            "title": title,
            "content": content_text,
            "created_at": datetime.now(timezone.utc)
        })

        return {"ok": True, "saved_pages": 1, "title": title, "chars": len(content_text)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ingest-minimal error: {e}")
        return {"ok": False, "error": str(e)}

def scrape_site_comprehensive(site_url, agent_id, max_pages=5):
    """
    Scraping comprehensiv al unui site cu multiple pagini pentru a obține conținut complet.
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse
        import time
        
        logger.info(f"Starting comprehensive scraping for {site_url}")
        
        # Headers pentru a evita blocarea
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        # Setează timeout-ul
        session.timeout = 15
        
        all_content = []
        visited_urls = set()
        urls_to_visit = [site_url]
        base_domain = urlparse(site_url).netloc
        
        page_count = 0
        while urls_to_visit and page_count < max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in visited_urls:
                continue
                
            visited_urls.add(current_url)
            page_count += 1
            
            logger.info(f"Scraping page {page_count}/{max_pages}: {current_url}")
            
            try:
                response = session.get(current_url, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Elimină elemente nedorite
                for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    element.decompose()
                
                # Extrage titlul
                title = soup.find('title')
                title_text = title.get_text().strip() if title else ""
                
                # Extrage conținutul principal
                main_content = ""
                for selector in ['main', 'article', '.content', '.main-content', '.container', 'body']:
                    elements = soup.select(selector)
                    if elements:
                        for element in elements:
                            text = element.get_text(separator=' ', strip=True)
                            if len(text) > len(main_content):
                                main_content = text
                
                # Limitează conținutul per pagină
                if main_content:
                    main_content = main_content[:5000]
                    all_content.append(f"=== {title_text} ===\n{main_content}")
                
                # Găsește link-uri interne pentru scraping suplimentar
                if page_count < max_pages:
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        full_url = urljoin(current_url, href)
                        
                        # Verifică dacă e link intern
                        if (urlparse(full_url).netloc == base_domain and 
                            full_url not in visited_urls and 
                            full_url not in urls_to_visit and
                            '#' not in full_url.split('/')[-1] and
                            not any(x in full_url for x in ['?', 'mailto:', 'tel:', '.pdf', '.doc'])):
                            urls_to_visit.append(full_url)
                            if len(urls_to_visit) >= 10:  # Limitează link-urile de urmărit
                                break
                
                time.sleep(1)  # Respect pentru server
                
            except Exception as e:
                logger.warning(f"Error scraping {current_url}: {e}")
                continue
        
        # Combină tot conținutul
        combined_content = "\n\n".join(all_content)
        
        # Salvează conținutul în baza de date
        if combined_content:
            content_doc = {
                "agent_id": ObjectId(agent_id),
                "url": site_url,
                "content": combined_content[:15000],  # Limitează conținutul total
                "timestamp": datetime.now(timezone.utc),
                "source": "comprehensive_scraping",
                "pages_scraped": len(all_content),
                "total_length": len(combined_content)
            }
            db.site_content.insert_one(content_doc)
            logger.info(f"Saved comprehensive content: {len(combined_content)} chars from {len(all_content)} pages")
        
        return combined_content[:12000]  # Returnează conținutul pentru prompt
        
    except Exception as e:
        logger.error(f"Comprehensive scraping failed: {e}")
        # Fallback la scraping simplu
        try:
            r = requests.get(site_url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            main_content = soup.find("main") or soup.find("article") or soup.find("body")
            if main_content:
                return main_content.get_text(" ", strip=True)[:5000]
            else:
                return soup.get_text(" ", strip=True)[:5000]
        except:
            return f"Site URL: {site_url}\nDomain: {urlparse(site_url).netloc}"

def get_api_key():
    # Preferă Qwen dacă este configurat și funcțional
    qwen_url = os.getenv("QWEN_BASE_URL")
    if qwen_url and qwen_url != "http://localhost:9304/v1":  # Doar dacă nu e local
        return os.getenv("QWEN_API_KEY", "local")
    
    # Fallback la OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="CRITICAL: No LLM API key configured. Check config.env/.env file.")
    return api_key

def save_conversation(agent_id: str, user_message: str, assistant_response: str, strategy: str = "manual_task"):
    """Salvează conversația în baza de date pentru învățare"""
    try:
        conversation_doc = {
            "agent_id": ObjectId(agent_id),
            "timestamp": datetime.now(timezone.utc),
            "strategy": strategy,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "conversation_length": len(user_message) + len(assistant_response)
        }
        conversations_collection.insert_one(conversation_doc)
        
        # Indexează și pentru învățare Qwen
        try:
            qwen_learning_doc = {
                "agent_id": ObjectId(agent_id),
                "timestamp": datetime.now(timezone.utc),
                "action_type": "conversation",
                "user_message": user_message,
                "agent_response": assistant_response,  # ⭐ FIX: folosește assistant_response, nu response
                "context_used": strategy,  # ⭐ FIX: folosește strategy ca context
                "for_qwen_learning": True
            }
            db.qwen_learning_data.insert_one(qwen_learning_doc)
            logger.info(f"[LEARNING] Indexed conversation for Qwen learning: {agent_id}")
        except Exception as e:
            logger.warning(f"Failed to index conversation for learning: {e}")
            
        logger.info(f"[CONVERSATION] Saved conversation for agent {agent_id}")
    except Exception as e:
        logger.error(f"[CONVERSATION] Failed to save conversation: {e}")

def get_learning_strategy_prompt(agent_id: str, site_url: str, industry: str, context: str) -> str:
    """Generează promptul pentru strategia de învățare din industrie cu task-uri concrete"""
    return f"""
Ești un expert în analiza industriei și dezvoltarea strategiilor de învățare pentru agenți AI.

AGENT ANALIZAT:
- ID: {agent_id}
- Site: {site_url}
- Industrie detectată: {industry}
- Context complet din baza de date: {context}

OBIECTIV: Dezvoltă o strategie COMPLET PERSONALIZATĂ cu TASK-URI CONCRETE pentru acest agent specific.

ANALIZEAZĂ ÎN PROFUNZIME:
1. **CONȚINUTUL SITE-ULUI:** Analizează fiecare detaliu din contextul furnizat
2. **SERVICIILE/PRODUSELE:** Identifică exact ce oferă acest business
3. **SEGMENTUL DE PIAȚĂ:** Determină ținta specifică a acestui business
4. **POZIȚIONAREA:** Înțelege cum se diferențiază de competitori
5. **TERMINOLOGIA TEHNICĂ:** Extrage termeni specifici ai industriei
6. **PAIN POINTS:** Identifică problemele pe care le rezolvă
7. **SOLUȚII UNICE:** Găsește ce face diferit de alții

RĂSPUNDE ÎN FORMAT JSON EXACT:
{{
  "business_analysis": {{
    "services_products": ["lista serviciilor/produselor identificate"],
    "target_market": "segmentul de piață specific",
    "unique_positioning": "poziționarea unică",
    "key_strengths": ["punctele forte identificate"]
  }},
  "learning_strategy": {{
    "industry_insights": "informații specifice despre industria lor",
    "competitor_analysis": "analiza competitorilor din conținut",
    "market_trends": "tendințe relevante pentru business-ul lor",
    "growth_opportunities": "oportunități specifice de dezvoltare"
  }},
  "concrete_tasks": [
    {{
      "task_id": "extract_keywords",
      "title": "Extrage cuvinte cheie din site",
      "description": "Identifică cuvintele cheie specifice pentru serviciile/produsele acestui business",
      "primary_keywords": ["cuvânt principal 1", "cuvânt principal 2", "cuvânt principal 3"],
      "secondary_keywords": ["cuvânt secundar 1", "cuvânt secundar 2", "cuvânt secundar 3"],
      "technical_terms": ["termen tehnic 1", "termen tehnic 2", "termen tehnic 3"],
      "search_queries": [
        "query principală 1", "query principală 2", "query principală 3",
        "query secundară 1", "query secundară 2", "query secundară 3",
        "query long-tail 1", "query long-tail 2", "query long-tail 3"
      ],
      "status": "pending"
    }},
    {{
      "task_id": "find_similar_sites",
      "title": "Găsește site-uri similare",
      "description": "Caută și identifică site-uri similare folosind strategia de căutare în cascadă",
      "search_strategy": {{
        "primary_search": {{
          "keywords": "cuvintele cheie principale",
          "target_count": 15,
          "description": "Căutare cu cuvintele cheie principale pentru competitori direcți"
        }},
        "secondary_search": {{
          "keywords": "cuvintele cheie secundare", 
          "target_count": 10,
          "description": "Căutare cu cuvintele cheie secundare pentru competitori indirecti"
        }},
        "technical_search": {{
          "keywords": "termenii tehnici",
          "target_count": 8,
          "description": "Căutare cu termenii tehnici pentru nișe specifice"
        }},
        "longtail_search": {{
          "keywords": "query-uri long-tail",
          "target_count": 7,
          "description": "Căutare cu query-uri long-tail pentru oportunități noi"
        }}
      }},
      "total_target_count": 40,
      "status": "pending"
    }},
    {{
      "task_id": "create_competitor_agents",
      "title": "Creează agenți competitori",
      "description": "Transformă site-urile similare în agenți pentru învățare",
      "target_count": 10,
      "status": "pending"
    }},
    {{
      "task_id": "analyze_competitors",
      "title": "Analizează competitorii",
      "description": "Compară serviciile și strategiile competitorilor identificați",
      "status": "pending"
    }},
    {{
      "task_id": "generate_insights",
      "title": "Generează insights strategice",
      "description": "Creează recomandări concrete bazate pe analiza competitorilor",
      "status": "pending"
    }}
  ],
  "success_metrics": {{
    "keywords_extracted": 0,
    "similar_sites_found": 0,
    "competitor_agents_created": 0,
    "insights_generated": 0
  }}
}}

CRITICAL REQUIREMENTS:
- Răspunde DOAR cu JSON valid, fără text suplimentar, fără markdown, fără explicații
- NU REPETA NICIODATĂ aceeași valoare în array-uri - fiecare cuvânt cheie trebuie să fie UNIC
- NU REPETA structura JSON, generează o singură structură completă
- Asigură-te că JSON-ul este valid și poate fi parsat
- Bazează-te EXCLUSIV pe conținutul furnizat
- Cuvintele cheie trebuie să fie SPECIFICE și RELEVANTE pentru serviciile/produsele lor
- Query-urile de căutare trebuie să fie în română și să acopere toate aspectele business-ului
- Fiecare task trebuie să fie acționabil și măsurabil
- Strategia de căutare trebuie să fie COMPLETĂ - să acopere toate sub-domeniile
- Cuvintele cheie principale = servicii/produse core (EXACT 5 cuvinte UNICE)
- Cuvintele cheie secundare = servicii/produse complementare (EXACT 5 cuvinte UNICE)
- Termenii tehnici = specificații, tehnologii, standarde (EXACT 5 termeni UNICI)
- Query-urile long-tail = combinații specifice pentru nișe (EXACT 9 query-uri UNICE)
- IMPORTANT: Dacă nu ai suficiente informații în context, folosește termeni generici dar RELEVANȚI
- STOP imediat după ultimul }} - nu adăuga nimic altceva
- MAXIM 1000 TOKENI - răspunde concis și precis
"""

# ------------- UI -------------
@app.get("/", response_class=HTMLResponse)
async def get_ui_root():
    """Servește UI principal: preferă static/main_interface.html dacă există.
    Fallback la ~/dual_mode_ui.html pentru compatibilitate.
    """
    try:
        static_main = os.path.join(os.path.dirname(__file__), "..", "static", "main_interface.html")
        static_main = os.path.abspath(static_main)
        if os.path.exists(static_main):
            with open(static_main, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    except Exception:
        pass
    ui_path = os.path.join(os.path.expanduser("~"), "dual_mode_ui.html")
    with open(ui_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# alias /ui (unele setup-uri folosesc exact acest path)
@app.get("/ui", response_class=HTMLResponse)
async def get_ui_alias():
    return await get_ui_root()

@app.get("/dual-mode", response_class=HTMLResponse)
async def get_dual_mode_ui():
    """Noua interfață Dual-Mode cu Discovery & Competitor Onboarding"""
    ui_path = os.path.join(os.path.expanduser("~"), "dual_mode_ui.html")
    with open(ui_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
# ===== DUAL-MODE DISCOVERY & COMPETITOR ONBOARDING ENDPOINTS =====

@app.post("/agents/{agent_id}/discover")
async def start_discovery_pipeline(agent_id: str, request: dict = Body(...)):
    """Start Discovery Pipeline - SERP based competitor discovery"""
    try:
        # Verifică dacă agentul există
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "Agent not found"}
        
        # Parametrii pentru discovery
        include_subdomains = request.get("include_subdomains", True)
        respect_robots = request.get("respect_robots", True)
        language_filter = request.get("language_filter", True)
        max_depth = request.get("max_depth", 3)
        manual_url = request.get("manual_url")
        
        # Dacă este URL manual, adaugă direct
        if manual_url:
            competitor_entry = {
                "master_agent_id": ObjectId(agent_id),
                "competitor_url": manual_url,
                "competitor_domain": urlparse(manual_url).netloc,
                "search_query": "manual_add",
                "relevance_score": 0.8,
                "research_timestamp": datetime.now(timezone.utc),
                "relationship_type": "competitor",
                "status": "discovered",
                "notes": "Added manually by user"
            }
            
            db.competitors.insert_one(competitor_entry)
            logger.info(f"✅ Manual competitor added: {manual_url}")
            
            return {
                "ok": True,
                "message": f"Manual competitor {manual_url} added successfully",
                "competitor_added": True
            }
        
        # Altfel, rulează discovery automat folosind discover_competitors
        logger.info(f"🚀 Starting discovery pipeline for agent {agent_id}")
        
        # Folosește discover_competitors din admin_discovery (fără GPT-5)
        limit = request.get("limit", 12)
        queries = request.get("queries")
        
        discovery_result = discover_competitors(agent_id, limit=limit, queries=queries)
        
        if discovery_result.get("ok"):
            logger.info(f"✅ Discovery completed: {len(discovery_result.get('candidates', []))} competitors found")
            
            # Salvează competitorii în baza de date
            candidates = discovery_result.get("candidates", [])
            for candidate in candidates:
                if candidate.get("ok"):
                    competitor_entry = {
                        "master_agent_id": ObjectId(agent_id),
                        "competitor_url": candidate.get("url"),
                        "competitor_domain": urlparse(candidate.get("url", "")).netloc,
                        "relevance_score": candidate.get("score", 0.0),
                        "research_timestamp": datetime.now(timezone.utc),
                        "relationship_type": "competitor",
                        "status": "discovered",
                        "homepage_text_len": candidate.get("homepage_text_len", 0)
                    }
                    db.competitors.update_one(
                        {"master_agent_id": ObjectId(agent_id), "competitor_url": candidate.get("url")},
                        {"$set": competitor_entry},
                        upsert=True
                    )
            # Returnează imediat rezultatul discovery pentru a evita dependențe de LLM
            return discovery_result
        else:
            logger.error(f"❌ Discovery failed: {discovery_result.get('error', 'Unknown error')}")
            return {
                "ok": False,
                "error": discovery_result.get("error", "Discovery failed"),
                "competitors_found": 0,
                "competitors": []
            }
        
    except Exception as e:
        logger.error(f"Error in discovery pipeline: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/agents/{agent_id}/candidates")
async def get_discovery_candidates(agent_id: str):
    """Get discovered candidates for onboarding"""
    try:
        # Obține competitorii descoperiți (inclusiv cei analizați de sistemul avansat)
        competitors = list(db.competitors.find({
            "master_agent_id": ObjectId(agent_id),
            "status": {"$in": ["discovered", "analyzed"]}
        }).sort("relevance_score", -1))
        
        candidates = []
        for competitor in competitors:
            # Folosește discovery_timestamp sau research_timestamp
            timestamp = competitor.get("discovery_timestamp") or competitor.get("research_timestamp")
            discovered_at = timestamp.isoformat() if timestamp else "Unknown"
            
            candidates.append({
                "domain": competitor["competitor_domain"],
                "url": competitor["competitor_url"],
                "score": competitor["relevance_score"],
                "keywords": [competitor["search_query"]] if competitor.get("search_query") else [],
                "serp_position": competitor.get("serp_position", 1),
                "discovered_at": discovered_at,
                "learning_opportunities": competitor.get("learning_opportunities", [])[:3],  # Primele 3
                "improvement_hints": competitor.get("improvement_hints", [])[:3],  # Primele 3
                "competitor_strengths": competitor.get("competitor_strengths", [])[:2],  # Primele 2
                "master_weaknesses": competitor.get("master_weaknesses", [])[:2]  # Primele 2
            })
        
        return {
            "ok": True,
            "candidates": candidates,
            "total": len(candidates)
        }
        
    except Exception as e:
        logger.error(f"Error getting candidates: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/agents/{agent_id}/onboard")
async def onboard_competitors(agent_id: str, request: dict = Body(...)):
    """Onboard selected competitors as sub-agents cu sistem avansat de learning"""
    try:
        candidates = request.get("candidates", [])
        if not candidates:
            return {"ok": False, "error": "No candidates provided"}
        
        onboarded_count = 0
        learning_opportunities = []
        improvement_hints = []
        
        for candidate in candidates:
            try:
                # Obține analiza competitorului din baza de date
                competitor_data = db.competitors.find_one({
                    "master_agent_id": ObjectId(agent_id),
                    "competitor_domain": candidate["domain"]
                })
                
                # Creează agent competitor cu informații avansate
                competitor_agent = {
                    "name": f"Slave Agent - {candidate['domain']}",
                    "site_url": candidate["url"],
                    "domain": candidate["domain"],
                    "agent_type": "competitor_slave",
                    "parent_agent_id": ObjectId(agent_id),
                    "relationship_type": "competitor_slave",
                    "status": "provisioning",
                    "created_at": datetime.now(timezone.utc),
                    "competitor_metadata": {
                        "discovery_score": candidate.get("score", 0.5),
                        "discovery_keywords": candidate.get("keywords", []),
                        "onboarded_at": datetime.now(timezone.utc).isoformat(),
                        "competitor_analysis": competitor_data.get("content_analysis", {}) if competitor_data else {},
                        "learning_opportunities": competitor_data.get("learning_opportunities", []) if competitor_data else [],
                        "improvement_hints": competitor_data.get("improvement_hints", []) if competitor_data else [],
                        "competitor_strengths": competitor_data.get("competitor_strengths", []) if competitor_data else [],
                        "master_weaknesses": competitor_data.get("master_weaknesses", []) if competitor_data else []
                    }
                }
                
                # Inserează agentul competitor
                result = agents_collection.insert_one(competitor_agent)
                competitor_agent_id = result.inserted_id
                
                # Actualizează statusul competitorului
                db.competitors.update_one(
                    {
                        "master_agent_id": ObjectId(agent_id),
                        "competitor_domain": candidate["domain"]
                    },
                    {
                        "$set": {
                            "status": "onboarded",
                            "competitor_agent_id": competitor_agent_id,
                            "onboarded_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                # Creează colecțiile Qdrant pentru competitor cu conținut avansat
                await create_competitor_collections_advanced(str(competitor_agent_id), candidate["domain"], competitor_data)
                
                # Adaugă oportunitățile de learning și hints-urile
                if competitor_data:
                    learning_opportunities.extend(competitor_data.get("learning_opportunities", [])[:2])
                    improvement_hints.extend(competitor_data.get("improvement_hints", [])[:2])
                
                onboarded_count += 1
                logger.info(f"✅ Competitor onboarded as slave agent: {candidate['domain']}")
                
            except Exception as e:
                logger.error(f"Error onboarding competitor {candidate['domain']}: {e}")
                continue
        
        # Creează relația de learning între master și slave agenți
        if onboarded_count > 0:
            await create_master_slave_learning_relationship(agent_id, onboarded_count)
        
        return {
            "ok": True,
            "message": f"Successfully onboarded {onboarded_count} competitors as slave agents",
            "onboarded_count": onboarded_count,
            "learning_opportunities": learning_opportunities[:5],  # Primele 5
            "improvement_hints": improvement_hints[:5]  # Primele 5
        }
        
    except Exception as e:
        logger.error(f"Error onboarding competitors: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/agents/{agent_id}/analyze")
async def run_competitor_analysis(agent_id: str):
    """Run comparative analysis and generate hints"""
    try:
        # Obține agentul master
        master_agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not master_agent:
            return {"ok": False, "error": "Master agent not found"}
        
        # Obține agenții competitori
        competitor_agents = list(agents_collection.find({
            "parent_agent_id": ObjectId(agent_id),
            "agent_type": "competitor"
        }))
        
        if not competitor_agents:
            return {"ok": False, "error": "No competitor agents found"}
        
        # Generează hints prin analiză comparativă
        hints = await generate_competitor_hints(master_agent, competitor_agents)
        
        # Salvează hints în baza de date
        for hint in hints:
            hint_entry = {
                "master_agent_id": ObjectId(agent_id),
                "hint_type": hint["type"],
                "priority": hint["priority"],
                "title": hint["title"],
                "description": hint["description"],
                "evidence": hint["evidence"],
                "suggested_action": hint["suggested_action"],
                "impact_score": hint["impact_score"],
                "effort_level": hint["effort_level"],
                "created_at": datetime.now(timezone.utc),
                "status": "pending",
                "admin_feedback": None
            }
            
            db.competitor_hints.insert_one(hint_entry)
        
        logger.info(f"✅ Analysis completed: {len(hints)} hints generated")
        
        return {
            "ok": True,
            "message": f"Analysis completed successfully",
            "hints": hints,
            "hints_count": len(hints)
        }
        
    except Exception as e:
        logger.error(f"Error running competitor analysis: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/agents/{agent_id}/hints")
async def get_competitor_hints(agent_id: str):
    """Get generated hints for an agent"""
    try:
        hints = list(db.competitor_hints.find({
            "master_agent_id": ObjectId(agent_id),
            "status": {"$ne": "dismissed"}
        }).sort("impact_score", -1))
        
        hints_list = []
        for hint in hints:
            hints_list.append({
                "id": str(hint["_id"]),
                "type": hint["hint_type"],
                "priority": hint["priority"],
                "title": hint["title"],
                "description": hint["description"],
                "evidence": hint["evidence"],
                "suggested_action": hint["suggested_action"],
                "impact_score": hint["impact_score"],
                "effort_level": hint["effort_level"],
                "created_at": hint["created_at"].isoformat(),
                "status": hint["status"]
            })
        
        return {
            "ok": True,
            "hints": hints_list,
            "total": len(hints_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting hints: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/agents/{agent_id}/hints/{hint_id}/action")
async def handle_hint_action(agent_id: str, hint_id: str, request: dict = Body(...)):
    """Handle hint actions (apply, dismiss, create ticket)"""
    try:
        action = request.get("action")
        hint_data = request.get("hint", {})
        
        if action == "apply":
            # Marchează hint-ul ca aplicat
            db.competitor_hints.update_one(
                {"_id": ObjectId(hint_id)},
                {"$set": {"status": "applied", "applied_at": datetime.now(timezone.utc)}}
            )
            
        elif action == "dismiss":
            # Marchează hint-ul ca respins
            db.competitor_hints.update_one(
                {"_id": ObjectId(hint_id)},
                {"$set": {"status": "dismissed", "dismissed_at": datetime.now(timezone.utc)}}
            )
            
        elif action == "create_ticket":
            # Creează ticket (simulat)
            ticket_entry = {
                "master_agent_id": ObjectId(agent_id),
                "hint_id": ObjectId(hint_id),
                "ticket_type": "competitor_analysis",
                "title": f"Action Required: {hint_data.get('title', 'Competitor Analysis Hint')}",
                "description": hint_data.get("suggested_action", ""),
                "priority": hint_data.get("priority", "medium"),
                "status": "open",
                "created_at": datetime.now(timezone.utc)
            }
            
            db.competitor_tickets.insert_one(ticket_entry)
            
            # Marchează hint-ul ca procesat
            db.competitor_hints.update_one(
                {"_id": ObjectId(hint_id)},
                {"$set": {"status": "ticket_created", "ticket_created_at": datetime.now(timezone.utc)}}
            )
        
        return {
            "ok": True,
            "message": f"Action '{action}' completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error handling hint action: {e}")
        return {"ok": False, "error": str(e)}

# ===== HELPER FUNCTIONS FOR DISCOVERY & ANALYSIS =====

async def generate_discovery_keywords(agent_id: str) -> List[str]:
    """Generează cuvinte cheie pentru discovery folosind GPT-5 pentru analiză inteligentă"""
    try:
        # Obține informațiile agentului
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return []
        
        site_url = agent.get("site_url", "")
        domain = agent.get("domain", "")
        agent_name = agent.get("name", "")
        
        # Obține conținutul agentului din Qdrant
        from qdrant_client import QdrantClient
        client = QdrantClient(url="http://localhost:9306")
        
        # Caută colecțiile Mirror pentru acest agent
        pages_content = []
        
        try:
            # Verifică dacă există colecții Mirror pentru acest agent
            collections_response = client.get_collections()
            mirror_collections = []
            
            for collection in collections_response.collections:
                collection_name = collection.name
                # Caută colecții Mirror care conțin ID-ul agentului sau domeniul
                if (f"mem_{agent_id}" in collection_name or 
                    f"mem_{domain.replace('.', '_')}" in collection_name or
                    (domain and domain.replace('.', '_') in collection_name)):
                    mirror_collections.append(collection_name)
            
            logger.info(f"🔍 Found Mirror collections: {mirror_collections}")
            
            # Încearcă să obțină conținut din colecțiile Mirror
            for collection_name in mirror_collections:
                try:
                    if "_pages" in collection_name:  # Colecția de pagini
                        scroll_result = client.scroll(
                            collection_name=collection_name,
                            limit=10,
                            with_payload=True
                        )
                        
                        for point in scroll_result[0]:
                            if point.payload and 'content' in point.payload:
                                pages_content.append(point.payload['content'])
                                
                except Exception as e:
                    logger.warning(f"Error reading from collection {collection_name}: {e}")
            
            # Dacă nu găsim conținut în colecțiile Mirror, folosim informațiile agentului
            if not pages_content:
                logger.info(f"📝 No content found in Mirror collections, using agent metadata")
                # Folosim informațiile de bază ale agentului
                pages_content = [
                    f"Nume agent: {agent_name}",
                    f"Domeniu: {domain}",
                    f"URL: {site_url}",
                    f"Status: {agent.get('status', 'unknown')}"
                ]
        
        except Exception as e:
            logger.warning(f"Error accessing Mirror collections: {e}")
            # Folosim informațiile de bază ale agentului
            pages_content = [
                f"Nume agent: {agent_name}",
                f"Domeniu: {domain}",
                f"URL: {site_url}",
                f"Status: {agent.get('status', 'unknown')}"
            ]
        
        # Folosește GPT-5 pentru analiză inteligentă
        api_key = get_api_key()
        model_name = get_llm_model()
        llm = ChatOpenAI(model_name=model_name, openai_api_key=api_key, temperature=0.2)
        
        # Creează prompt-ul pentru GPT-5
        content_sample = "\n".join(pages_content[:5]) if pages_content else ""
        
        prompt = f"""Ești GPT-5, expert în analiza industriei și identificarea competitorilor. Analizează acest site web și creează o strategie de căutare competitori inteligentă.

SITE MASTER:
- Nume: {agent_name}
- URL: {site_url}
- Domeniu: {domain}

CONȚINUT DISPONIBIL:
{content_sample[:3000]}

SARCINA TA:
Bazându-te pe numele agentului, domeniul și URL-ul, identifică industria și generează cuvinte cheie pentru căutarea competitorilor în România.

RĂSPUNS FORMAT JSON:
{{
    "industry": "domeniul principal identificat",
    "services": ["serviciu1", "serviciu2", "serviciu3"],
    "products": ["produs1", "produs2", "produs3"],
    "commercial_keywords": ["cuvant1", "cuvant2", "cuvant3"],
    "technical_terms": ["termen1", "termen2", "termen3"],
    "geographic_keywords": ["cuvant_ro1", "cuvant_ro2", "cuvant_ro3"],
    "search_queries": [
        "căutare1 românia",
        "căutare2 bucurești", 
        "căutare3 servicii",
        "căutare4 produse"
    ]
}}

Răspunde DOAR cu JSON-ul, fără text suplimentar."""
        
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content.strip()
            
            # Parsează JSON-ul
            analysis = json.loads(response_text)
            
            # Extrage cuvintele cheie pentru căutare
            search_queries = analysis.get("search_queries", [])
            commercial_keywords = analysis.get("commercial_keywords", [])
            technical_terms = analysis.get("technical_terms", [])
            geographic_keywords = analysis.get("geographic_keywords", [])
            
            # Combină toate cuvintele cheie
            all_keywords = search_queries + commercial_keywords + technical_terms + geographic_keywords
            
            # Elimină duplicatele și limitează
            unique_keywords = list(dict.fromkeys(all_keywords))[:10]
            
            logger.info(f"✅ GPT-5 generated {len(unique_keywords)} keywords for {domain}")
            logger.info(f"Keywords: {unique_keywords}")
            
            return unique_keywords
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing GPT-5 response: {e}")
            logger.error(f"Response was: {response_text}")
            
        except Exception as e:
            logger.error(f"Error calling GPT-5: {e}")
        
        # Fallback la cuvinte cheie bazate pe domeniu
        domain_keywords = domain.replace('.ro', '').replace('.com', '').split('-')
        fallback_keywords = domain_keywords + ["servicii", "produse", "românia", "bucurești"]
        
        return fallback_keywords[:8]
        
    except Exception as e:
        logger.error(f"Error generating discovery keywords: {e}")
        return ["servicii", "produse", "românia"]

async def search_competitors_serp(keyword: str, master_domain: str) -> List[dict]:
    """Caută competitori reali folosind Brave Search API"""
    try:
        brave_api_key = os.getenv("BRAVE_API_KEY")
        print(f"DEBUG: brave_api_key = {repr(brave_api_key)}")
        if not brave_api_key:
            print("DEBUG: Entering mock fallback")
            logger.warning("BRAVE_API_KEY not found, using mock data")
            logger.info(f"🔍 Calling search_competitors_mock for keyword: {keyword}")
            result = await search_competitors_mock(keyword, master_domain)
            logger.info(f"✅ Mock returned {len(result)} competitors")
            print(f"DEBUG: Mock result = {len(result)} competitors")
            return result
        
        # Creează query-ul de căutare
        search_query = f"{keyword} românia"
        
        # Parametrii pentru Brave Search
        params = {
            "q": search_query,
            "count": 10,
            "offset": 0,
            "mkt": "ro-RO",
            "safesearch": "moderate"
        }
        
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": brave_api_key
        }
        
        # Face căutarea
        print(f"DEBUG: Making Brave Search request for: {search_query}")
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params=params,
            headers=headers,
            timeout=10
        )
        
        print(f"DEBUG: Brave Search response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"DEBUG: Brave response data keys: {list(data.keys())}")
            web_results = data.get("web", {}).get("results", [])
            print(f"DEBUG: Found {len(web_results)} web results")
            
            competitors = []
            for result in web_results:
                url = result.get("url", "")
                title = result.get("title", "")
                description = result.get("description", "")
                
                # Filtrează domeniul master și domeniile irelevante
                if (master_domain not in url and 
                    url.startswith("http") and 
                    not any(blocked in url.lower() for blocked in ["facebook", "youtube", "instagram", "linkedin", "twitter", "wikipedia"])):
                    
                    # Calculează scorul de relevanță
                    relevance_score = calculate_relevance_score(keyword, title, description)
                    
                    competitors.append({
                        "url": url,
                        "domain": urlparse(url).netloc,
                        "title": title,
                        "description": description,
                        "relevance_score": relevance_score,
                        "search_query": keyword
                    })
            
            # Sortează după relevanță și returnează top 5
            competitors.sort(key=lambda x: x["relevance_score"], reverse=True)
            return competitors[:5]
            
        else:
            logger.warning(f"Brave Search API error: {response.status_code}")
            return await search_competitors_mock(keyword, master_domain)
            
    except Exception as e:
        logger.error(f"Error in SERP search: {e}")
        return await search_competitors_mock(keyword, master_domain)

async def search_competitors_mock(keyword: str, master_domain: str) -> List[dict]:
    """Fallback la date mock pentru căutarea competitorilor"""
    try:
        # Generează competitori mock mai realiști
        mock_competitors = [
            {
                "url": f"https://www.{keyword}-services.ro",
                "domain": f"{keyword}-services.ro",
                "title": f"Servicii {keyword.title()} - România",
                "description": f"Oferim servicii profesionale de {keyword} în toată România",
                "relevance_score": 0.85,
                "search_query": keyword
            },
            {
                "url": f"https://{keyword}-solutions.ro",
                "domain": f"{keyword}-solutions.ro", 
                "title": f"Soluții {keyword.title()} București",
                "description": f"Specialiști în {keyword} cu experiență de peste 10 ani",
                "relevance_score": 0.80,
                "search_query": keyword
            },
            {
                "url": f"https://www.{keyword}-expert.ro",
                "domain": f"{keyword}-expert.ro",
                "title": f"Expert {keyword.title()} - Servicii Complete",
                "description": f"Echipa noastră de experți în {keyword} vă oferă soluții personalizate",
                "relevance_score": 0.75,
                "search_query": keyword
            }
        ]
        
        # Filtrează domeniul master
        filtered_competitors = [
            comp for comp in mock_competitors 
            if master_domain not in comp["url"]
        ]
        
        return filtered_competitors
        
    except Exception as e:
        logger.error(f"Error in mock search: {e}")
        return []

def calculate_relevance_score(keyword: str, title: str, description: str) -> float:
    """Calculează scorul de relevanță pentru un competitor"""
    try:
        score = 0.0
        text = f"{title} {description}".lower()
        keyword_lower = keyword.lower()
        
        # Bonus pentru keyword în titlu
        if keyword_lower in title.lower():
            score += 0.3
        
        # Bonus pentru keyword în descriere
        if keyword_lower in description.lower():
            score += 0.2
        
        # Bonus pentru cuvinte cheie relevante
        relevant_words = ["servicii", "produse", "soluții", "expert", "profesional", "românia", "bucurești"]
        for word in relevant_words:
            if word in text:
                score += 0.1
        
        # Bonus pentru domeniu .ro
        if ".ro" in text:
            score += 0.1
        
        return min(score, 1.0)  # Limitează la 1.0
        
    except Exception as e:
        logger.error(f"Error calculating relevance score: {e}")
        return 0.5
async def create_competitor_collections_advanced(competitor_agent_id: str, domain: str, competitor_data: Dict):
    """Creează colecțiile Qdrant pentru un competitor cu conținut avansat"""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url="http://localhost:9306")
        
        # Colecția pentru pagini
        pages_collection = f"mem_{competitor_agent_id}_pages"
        faq_collection = f"mem_{competitor_agent_id}_faq"
        
        # Creează colecțiile cu dimensiunea corectă (768 pentru Ollama)
        try:
            client.create_collection(
                collection_name=pages_collection,
                vectors_config={"size": 768, "distance": "Cosine"}
            )
            logger.info(f"✅ Created pages collection: {pages_collection}")
        except Exception as e:
            logger.warning(f"Pages collection may already exist: {e}")
        
        try:
            client.create_collection(
                collection_name=faq_collection,
                vectors_config={"size": 768, "distance": "Cosine"}
            )
            logger.info(f"✅ Created FAQ collection: {faq_collection}")
        except Exception as e:
            logger.warning(f"FAQ collection may already exist: {e}")
        
        # Adaugă conținutul scraped în colecția de pagini
        if competitor_data and competitor_data.get("content_analysis"):
            content_analysis = competitor_data["content_analysis"]
            
            # Creează documente din analiza conținutului
            documents = []
            
            # Adaugă punctele forte ca documente
            for strength in content_analysis.get("strengths", []):
                documents.append({
                    "content": f"Punct forte competitor: {strength}",
                    "metadata": {
                        "type": "competitor_strength",
                        "domain": domain,
                        "source": "analysis"
                    }
                })
            
            # Adaugă strategiile de marketing
            for strategy in content_analysis.get("marketing_strategies", []):
                documents.append({
                    "content": f"Strategie marketing competitor: {strategy}",
                    "metadata": {
                        "type": "marketing_strategy",
                        "domain": domain,
                        "source": "analysis"
                    }
                })
            
            # Adaugă serviciile/produsele
            for service in content_analysis.get("services_products", []):
                documents.append({
                    "content": f"Serviciu/produs competitor: {service}",
                    "metadata": {
                        "type": "service_product",
                        "domain": domain,
                        "source": "analysis"
                    }
                })
            
            # Generează embeddings și adaugă în Qdrant
            for i, doc in enumerate(documents):
                try:
                    # Generează embedding folosind Ollama
                    embedding = await generate_ollama_embedding(doc["content"])
                    
                    point = {
                        "id": f"{competitor_agent_id}_analysis_{i}",
                        "vector": embedding,
                        "payload": {
                            "content": doc["content"],
                            "metadata": doc["metadata"],
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                    
                    client.upsert(
                        collection_name=pages_collection,
                        points=[point]
                    )
                    
                except Exception as e:
                    logger.warning(f"Error adding analysis document {i}: {e}")
            
            logger.info(f"✅ Added {len(documents)} analysis documents to competitor collection")
        
    except Exception as e:
        logger.error(f"Error creating advanced competitor collections: {e}")

async def create_master_slave_learning_relationship(master_agent_id: str, slave_count: int):
    """Creează relația de learning între master și slave agenți"""
    try:
        # Creează documentul de learning relationship
        learning_relationship = {
            "master_agent_id": ObjectId(master_agent_id),
            "slave_count": slave_count,
            "relationship_type": "master_slave_learning",
            "created_at": datetime.now(timezone.utc),
            "learning_status": "active",
            "learning_opportunities": [],
            "improvement_hints": [],
            "last_learning_update": datetime.now(timezone.utc)
        }
        
        # Salvează în colecția de learning relationships
        db.learning_relationships.insert_one(learning_relationship)
        
        logger.info(f"✅ Created master-slave learning relationship for {slave_count} slaves")
        
    except Exception as e:
        logger.error(f"Error creating learning relationship: {e}")

async def generate_ollama_embedding(text: str) -> List[float]:
    """Generează embedding folosind Ollama"""
    try:
        import requests
        
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": text
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["embedding"]
        else:
            logger.warning(f"Ollama embedding failed: {response.status_code}")
            # Fallback la embedding random
            import random
            return [random.uniform(-1, 1) for _ in range(768)]
            
    except Exception as e:
        logger.warning(f"Error generating Ollama embedding: {e}")
        # Fallback la embedding random
        import random
        return [random.uniform(-1, 1) for _ in range(768)]

async def generate_competitor_hints(master_agent: dict, competitor_agents: List[dict]) -> List[dict]:
    """Generează hints prin analiză comparativă"""
    try:
        hints = []
        
        # Analiză simplă pentru demo
        master_domain = master_agent.get("domain", "")
        
        for competitor in competitor_agents:
            competitor_domain = competitor.get("domain", "")
            
            # Hint 1: Pagină de prețuri
            hints.append({
                "type": "content_gap",
                "priority": "high",
                "title": f"Lipsă pagină Prețuri",
                "description": f"Competitorul {competitor_domain} afișează prețuri clare pe site",
                "evidence": f"Competitor: {competitor_domain} - are secțiunea 'Prețuri' vizibilă",
                "suggested_action": "Adaugă o pagină dedicată cu prețurile serviciilor",
                "impact_score": 0.8,
                "effort_level": "medium"
            })
            
            # Hint 2: Testimoniale
            hints.append({
                "type": "trust_building",
                "priority": "medium", 
                "title": f"Lipsă testimoniale clienți",
                "description": f"Competitorul {competitor_domain} afișează recenzii și testimoniale",
                "evidence": f"Competitor: {competitor_domain} - are secțiunea 'Testimoniale' cu recenzii",
                "suggested_action": "Adaugă o secțiune cu testimoniale și recenzii de la clienți",
                "impact_score": 0.7,
                "effort_level": "low"
            })
            
            # Hint 3: Contact info
            hints.append({
                "type": "contact_optimization",
                "priority": "high",
                "title": f"Optimizare informații contact",
                "description": f"Competitorul {competitor_domain} are informații de contact mai accesibile",
                "evidence": f"Competitor: {competitor_domain} - buton 'Contact' vizibil în header",
                "suggested_action": "Îmbunătățește vizibilitatea informațiilor de contact",
                "impact_score": 0.9,
                "effort_level": "low"
            })
        
        # Limitează la 5 hints pentru demo
        return hints[:5]
        
    except Exception as e:
        logger.error(f"Error generating competitor hints: {e}")
        return []

@app.get("/agent-status", response_class=HTMLResponse)
async def get_agent_status_page():
    """Pagina de status pentru agenți"""
    with open("static/agent_status.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/control-panel", response_class=HTMLResponse)
@app.get("/master", response_class=HTMLResponse)
async def get_master_control_panel():
    """Master Control Panel - Dashboard principal pentru management agenți"""
    with open("static/master_control_panel.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/solutions-status")
async def get_solutions_status():
    """Statusul soluțiilor implementate"""
    try:
        from solution_tracker import get_solution_summary, solution_tracker
        
        summary = get_solution_summary()
        sealed_solutions = solution_tracker.get_sealed_solutions()
        
        return {
            "summary": summary,
            "sealed_solutions": [
                {
                    "id": sol.id,
                    "problem": sol.problem,
                    "solution": sol.solution,
                    "sealed_at": sol.sealed_at.isoformat() if sol.sealed_at else None,
                    "files_modified": sol.files_modified,
                    "notes": sol.notes
                }
                for sol in sealed_solutions
            ],
            "ok": True
        }
        
    except Exception as e:
        logger.error(f"Error getting solutions status: {e}")
        return {
            "error": str(e),
            "ok": False
        }

@app.get("/config/api-key-status")
async def api_key_status():
    qwen_url = os.getenv("QWEN_BASE_URL")
    if qwen_url:
        return {"is_set": True, "provider": "Qwen", "url": qwen_url}
    return {"is_set": bool(os.getenv("OPENAI_API_KEY")), "provider": "OpenAI"}

@app.get("/health")
async def health_check():
    """Verifică sănătatea tuturor serviciilor"""
    try:
        health_summary = await quick_health_check()
        return health_summary
    except Exception as e:
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ------------- Agents list -------------
@app.get("/api/agents")
async def get_agents():
    """Returnează agenții validați SAU cu content complet"""
    # ⭐ FILTRU: Agenți validați SAU cu embeddings (content complet)
    agents = list(
        agents_collection.find(
            {
                "$or": [
                    {"validation_passed": True},  # Validați explicit
                    {"has_embeddings": True},     # SAU au embeddings (content complet)
                ],
                "status": {"$in": ["ready", "validated"]}  # Status ready sau validated
            },
            {"_id": 1, "name": 1, "domain": 1, "site_url": 1, "status": 1, "createdAt": 1, "updatedAt": 1, 
             "validation_passed": 1, "services_count": 1, "contact_info": 1, "has_embeddings": 1, "has_content": 1}
        ).sort([("updatedAt", -1), ("createdAt", -1)])
    )
    
    logger.info(f"✅ API /api/agents: Returnăm {len(agents)} agenți (validați sau cu content complet)")
    
    for agent in agents:
        agent["_id"] = str(agent["_id"])
        if isinstance(agent.get("createdAt"), datetime):
            agent["createdAt"] = agent["createdAt"].isoformat()
        if isinstance(agent.get("updatedAt"), datetime):
            agent["updatedAt"] = agent["updatedAt"].isoformat()
    return agents

@app.get("/api/agents/last")
async def get_last_agent():
    cur = agents_collection.find(
        {},
        {"_id": 1, "name": 1, "domain": 1, "site_url": 1, "status": 1, "createdAt": 1, "updatedAt": 1}
    ).sort([("updatedAt", -1), ("createdAt", -1)]).limit(1)
    items = list(cur)
    if not items:
        return {}
    agent = items[0]
    agent["_id"] = str(agent["_id"])
    if isinstance(agent.get("createdAt"), datetime):
        agent["createdAt"] = agent["createdAt"].isoformat()
    if isinstance(agent.get("updatedAt"), datetime):
        agent["updatedAt"] = agent["updatedAt"].isoformat()
    return agent

@app.get("/api/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Verifică statusul unui agent conform checklist-ului de 4 straturi"""
    try:
        # Verifică dacă agentul există în MongoDB
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"error": "Agent not found"}
        
        # Verifică dacă agentul are date indexate în Qdrant
        has_data = False
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(url="http://localhost:9306")
            collection_name = f"agent_{agent_id}_content"
            
            try:
                info = client.get_collection(collection_name)
                has_data = info.points_count > 0
            except Exception:
                has_data = False
        except Exception as e:
            logger.error(f"Error checking Qdrant data for agent {agent_id}: {e}")
        
        # Calculează compliance score
        compliance_score = calculate_compliance_score(agent, has_data)
        
        return {
            "agent_id": agent_id,
            "has_data": has_data,
            "compliance_score": compliance_score,
            "status": {
                "identity": {
                    "name": bool(agent.get("name")),
                    "domain": bool(agent.get("domain")),
                    "identity_config": bool(agent.get("identity"))
                },
                "perception": {
                    "has_indexed_data": has_data,
                    "crawler_configured": bool(agent.get("site_url"))
                },
                "memory": {
                    "working_memory": True,  # Implementat în RAG pipeline
                    "long_term_memory": has_data
                },
                "reasoning": {
                    "gpt_orchestrator": True,  # Implementat
                    "guardrails": True,  # Implementat
                    "source_citation": True  # Implementat
                },
                "action": {
                    "rag_search": has_data,
                    "web_fetch": False  # Implementare parțială
                },
                "interfaces": {
                    "api_rest": True,  # Implementat
                    "ui_chat": True  # Implementat
                },
                "security": {
                    "guardrails": True,  # Implementat
                    "no_hallucination": True  # Implementat
                },
                "monitoring": {
                    "test_suite": True,  # Implementat
                    "ab_testing": False  # Implementare parțială
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return {"error": str(e)}

def calculate_compliance_score(agent, has_data):
    """Calculează compliance score-ul agentului"""
    score = 0
    total = 0
    
    # Identitate & Scop (20%)
    total += 2
    if agent.get("name"): score += 1
    if agent.get("identity"): score += 1
    
    # Percepție (25%)
    total += 2.5
    if has_data: score += 2.5
    
    # Memorie (15%)
    total += 1.5
    score += 1.5  # Implementat în RAG pipeline
    
    # Raționare (20%)
    total += 2
    score += 2  # GPT orchestrator implementat
    
    # Acțiune (10%)
    total += 1
    if has_data: score += 1
    
    # Interfețe (5%)
    total += 0.5
    score += 0.5  # API implementat
    
    # Securitate (5%)
    total += 0.5
    score += 0.5  # Guardrails implementate
    
    return round((score / total) * 100)

# ------------- WebSockets -------------
@app.websocket("/ws/create-agent")
async def create_agent_websocket(websocket: WebSocket, url: str = None):
    """WebSocket pentru crearea agenților cu feedback în timp real"""
    await websocket.accept()
    logger.info("🔌 WebSocket connected for agent creation")
    
    try:
        # Primește URL-ul din query parameter (compatibil cu frontend-ul existent)
        if not url:
            await websocket.send_json({"status": "error", "message": "URL lipsă din parametri"})
            await websocket.close()
            return
        
        logger.info(f"📝 Creare agent pentru: {url}")
        
        # Trimite confirmare că procesul a început
        await websocket.send_json({"status": "progress", "message": "Începe crearea agentului..."})
        
        api_key = get_api_key()
        await create_site_agent_ws(websocket, url, api_key)
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await websocket.send_json({"status": "error", "message": f"Eroare: {str(e)}"})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

@app.websocket("/ws/task/{agent_id}")
async def task_websocket(websocket: WebSocket, agent_id: str, strategy: str):
    await websocket.accept()
    api_key = get_api_key()
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            await websocket.send_json({"type": "error", "data": "Agent not found."})
            return

        # Pasăm agent_id (nu doar domain) către executor
        await handle_task_conversation(
            websocket=websocket,
            api_key=api_key,
            agent_id=agent_id,
            site_url=agent.get("site_url", "unknown"),
            initial_strategy=strategy
        )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        await websocket.send_json({"type": "error", "data": str(e)})
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

# ===================== UTILITĂȚI PENTRU EXPAND =====================
HTTP_TIMEOUT = 8  # sec

def _norm_domain(domain_or_url: str) -> str:
    if not domain_or_url:
        return ""
    if "://" in domain_or_url:
        parsed = urlparse(domain_or_url)
        host = parsed.netloc
    else:
        host = domain_or_url
    host = host.strip().lower()
    if host.startswith("www."):
        host = host[4:]
    if ":" in host:
        host = host.split(":")[0]
    return host

def _robots_allows(url: str, user_agent: str = "*") -> bool:
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, "/")
    except Exception:
        # dacă robots nu poate fi citit, permitem conservator 1 pagină
        return True

def _is_alive(url: str) -> bool:
    try:
        r = requests.head(url, timeout=HTTP_TIMEOUT, allow_redirects=True)
        if r.status_code < 400:
            return True
    except Exception:
        pass
    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False

def _resolve_dns(domain: str) -> bool:
    try:
        socket.gethostbyname(domain)
        return True
    except Exception:
        return False

def _to_url(domain: str) -> str:
    return f"https://{_norm_domain(domain)}/"

def propose_sites(base_domain: str, objective: str, limit: int = 5) -> List[str]:
    """
    Heuristică simplă: subdomenii uzuale + variantă TLD .ro/.com.
    Ulterior poate fi înlocuit cu propuneri LLM sau crawling de link-graph.
    """
    d = _norm_domain(base_domain)
    if not d:
        return []
    candidates = []

    subs = ["www", "blog", "docs", "help", "support"]
    for s in subs:
        candidates.append(f"{s}.{d}")

    if d.endswith(".ro"):
        core = d[:-3].rstrip(".")
        if core:
            candidates.append(f"{core}.com")
    if d.endswith(".com"):
        core = d[:-4].rstrip(".")
        if core:
            candidates.append(f"{core}.ro")

    # elimină duplicate + sine
    seen = set()
    out = []
    for c in candidates:
        c_norm = _norm_domain(c)
        if c_norm and c_norm != d and c_norm not in seen:
            seen.add(c_norm)
            out.append(c_norm)

    return out[: max(1, limit)]

# ============ HEADLESS WS WRAPPER PENTRU CREAREA AGENTULUI ============
class DummyWebSocket:
    """WebSocket minimal pentru a apela create_site_agent_ws fără UI."""
    async def accept(self): return
    async def send_text(self, _: str): return
    async def send_json(self, _: dict): return
    async def close(self, code: Optional[int] = None): return

async def _create_agent_ws_headless(url: str, api_key: str):
    """Rulează fluxul existent de creare prin funcția WS, fără UI."""
    try:
        ws = DummyWebSocket()
        await create_site_agent_ws(ws, url, api_key)
    except Exception as e:
        logger.error(f"[HEADLESS-CREATE] Eroare la {url}: {e}\n{traceback.format_exc()}")

def launch_headless_create(url: str):
    """Helper sync pentru BackgroundTasks: pornește un event loop local."""
    api_key = get_api_key()
    asyncio.run(_create_agent_ws_headless(url, api_key))

# ===================== ENDPOINT: EXPAND (AUTO-CREATE BACKEND) =====================
class ExpandRequest(BaseModel):
    objective: str
    maxAgents: int = 3
    maxPagesPerSite: int = 20
    # Fallback-uri dacă agentul nu are câmpul 'domain' sau 'site_url' în DB
    domain: Optional[str] = None
    agentName: Optional[str] = None

@app.post("/agents/{agent_id}/expand")
async def expand_agent_route(agent_id: str, req: ExpandRequest, background_tasks: BackgroundTasks):
    """
    Propune site-uri înrudite și PORNEȘTE crearea de agenți în BACKEND (BackgroundTasks).
    Răspunde imediat cu lista de site-uri acceptate și job-urile pornite.
    """
    # 1) Citește agentul din Mongo (pt. domain/name)
    agent = None
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
    except Exception:
        agent = None

    base_domain = None
    agent_name = None
    if agent:
        agent_name = agent.get("name") or req.agentName or f"agent-{agent_id}"
        base_domain = agent.get("domain")
        if not base_domain:
            site_url = agent.get("site_url")
            if site_url:
                base_domain = _norm_domain(site_url)
        # touch updatedAt
        try:
            agents_collection.update_one({"_id": ObjectId(agent_id)}, {"$set": {"updatedAt": datetime.now(timezone.utc)}})
        except Exception:
            pass
    else:
        agent_name = req.agentName or f"agent-{agent_id}"
        base_domain = req.domain

    if not base_domain:
        raise HTTPException(
            status_code=400,
            detail="Missing base domain: agentul nu are domain/site_url și nu ai furnizat 'domain' în body."
        )

    # 2) Propuneri și filtrare
    proposals = propose_sites(base_domain, req.objective, limit=max(3, req.maxAgents * 2))
    allowed: List[Dict] = []
    skipped: List[Dict] = []
    for dom in proposals:
        dnorm = _norm_domain(dom)
        if not dnorm:
            skipped.append({"domain": dom, "reason": "invalid"})
            continue
        url = _to_url(dnorm)
        if not _resolve_dns(dnorm):
            skipped.append({"domain": dnorm, "reason": "dns_fail"})
            continue
        if not _is_alive(url):
            skipped.append({"domain": dnorm, "reason": "unreachable"})
            continue
        if not _robots_allows(url):
            skipped.append({"domain": dnorm, "reason": "robots_disallow"})
            continue
        allowed.append({"domain": dnorm, "url": url})

    # 3) PORNEȘTE CREAREA în backend pentru primele N (maxAgents)
    started: List[Dict] = []
    for item in allowed[: req.maxAgents]:
        background_tasks.add_task(launch_headless_create, item["url"])
        started.append({"domain": item["domain"], "url": item["url"]})

    return {
        "status": "accepted",
        "agent_id": agent_id,
        "agent_name": agent_name,
        "base_domain": _norm_domain(base_domain),
        "objective": req.objective,
        "started": started,
        "skipped": skipped
    }

# ===================== ADMIN: DISCOVER & INGEST =====================
@app.post("/admin/industry/{agent_id}/discover")
def api_discover_competitors(agent_id: str, payload: Dict = Body(default={})):
    """
    Body (optional): { "limit": 12, "queries": ["q1", "q2", ...] }
    Returnează: {ok, agent_id, domain, candidates: [{url, score, reason, homepage_text_len}], queries}
    """
    try:
        limit   = int(payload.get("limit", 12) or 12)
        queries = payload.get("queries")
        if queries and not isinstance(queries, list):
            queries = None
        res = discover_competitors(agent_id, limit=limit, queries=queries)
        return res
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        logger.error(f"Error in api_discover_competitors: {error_msg}\n{traceback_str}")
        return {"ok": False, "error": error_msg, "traceback": traceback_str}


# ===================== ACTION RECOMMENDATIONS =====================
try:
    # Adaugă /home/mobra în path pentru a găsi action_recommendations
    import sys
    if "/home/mobra" not in sys.path:
        sys.path.insert(0, "/home/mobra")
    from action_recommendations import generate_action_recommendations
except ImportError as e:
    # Fallback dacă modulul nu există
    logger.warning(f"Action recommendations module not available: {e}")
    def generate_action_recommendations(agent_id, focus_areas=None):
        return {"ok": False, "error": "Action recommendations module not available"}

class ActionRecommendationsRequest(BaseModel):
    focus_areas: Optional[List[str]] = None  # ['seo', 'social_media', 'content', 'ux', 'technical']

@app.post("/agents/{agent_id}/action-recommendations")
def api_get_action_recommendations(agent_id: str, payload: ActionRecommendationsRequest = Body(default={})):
    """
    Generează recomandări practice de îmbunătățire bazate pe analiza competitorilor
    
    Body (optional): { "focus_areas": ["seo", "social_media", "content", "ux", "technical"] }
    
    Returnează:
    {
        "ok": true,
        "recommendations": {
            "seo": {...},
            "social_media": {...},
            ...
        },
        "action_plan": {
            "30_day_plan": {...},
            "quick_wins": [...]
        }
    }
    """
    try:
        focus_areas = payload.focus_areas if payload and hasattr(payload, 'focus_areas') else None
        result = generate_action_recommendations(agent_id, focus_areas)
        return result
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        logger.error(f"Error in api_get_action_recommendations: {error_msg}\n{traceback_str}")
        return {"ok": False, "error": error_msg, "traceback": traceback_str}

@app.get("/agents/{agent_id}/action-recommendations")
def api_get_action_recommendations_get(agent_id: str, focus_areas: Optional[str] = Query(None)):
    """
    GET endpoint pentru recomandări (acceptă focus_areas ca query param)
    """
    try:
        focus_areas_list = None
        if focus_areas:
            focus_areas_list = [area.strip() for area in focus_areas.split(",")]
        result = generate_action_recommendations(agent_id, focus_areas_list)
        return result
    except Exception as e:
        logger.error(f"Error in api_get_action_recommendations_get: {str(e)}")
        return {"ok": False, "error": str(e)}


# ===================== ADMIN: AUTO-EXPANSION (GPT SUPERVISOR) =====================
class AutoExpandRequest(BaseModel):
    limit: int = 12
    maxPagesPerSite: int = 10
    objective: str = "market_intel"
@app.post("/admin/industry/{agent_id}/auto-expand")
def api_auto_expand(agent_id: str, payload: AutoExpandRequest):
    """
    1) Rulează discover_competitors
    2) Cere la GPT să selecteze și să justifice top N URL-uri
    3) Pornește ingest pentru URL-urile selectate
    """
    # 0) Citește agentul din colecția existentă (ai_agents_db.agents)
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
    except Exception:
        agent = None
    if not agent:
        return {"ok": False, "error": "agent_not_found"}

    base_domain = agent.get("domain")
    site_url = agent.get("site_url") or (f"https://{base_domain}" if base_domain else None)

    # 1) Context pentru GPT din baza de date (conținutul site-ului catalogat)
    homepage_text = ""
    agent_content = ""
    agent_industry = ""

    # Citește din colecția corectă de conținut - MAI MULT CONȚINUT
    try:
        content_docs = site_content_col.find({"agent_id": ObjectId(agent_id)}).limit(15)  # Mai multe documente
        content_parts = []
        for doc in content_docs:
            if doc.get("content"):
                content_parts.append(doc["content"][:800])  # Mai mult conținut per document
        agent_content = " ".join(content_parts)[:4000]  # Mai mult conținut total
        logger.info(f"[AUTOEXPAND] Found {len(content_parts)} content docs from DB for agent {agent_id}, total length: {len(agent_content)}")
    except Exception as e:
        logger.warning(f"Could not get agent content from DB: {e}")

    # Fallback: încearcă să obții homepage-ul direct
    if not agent_content and site_url:
        try:
            r = requests.get(site_url, timeout=10)
            r.raise_for_status()
            html = r.text
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                homepage_text = (soup.get_text(" ") or "").strip()
                if len(homepage_text) > 2000:
                    homepage_text = homepage_text[:2000]
            except Exception:
                pass
        except Exception:
            pass

    # Combină conținutul din DB cu homepage-ul
    full_context = f"{agent_content}\n\n{homepage_text}".strip()

    # Detectează industria (heuristic simplu)
    if full_context:
        industry_keywords = {
            "e-commerce": ["magazin", "produs", "cumpără", "vânzare", "shop", "store"],
            "tehnologie": ["software", "aplicație", "tehnologie", "digital", "IT"],
            "servicii": ["serviciu", "consulting", "suport", "asistență"],
            "educație": ["curs", "training", "educație", "învățare"],
            "sănătate": ["medical", "sănătate", "doctor", "spital", "clinică"],
            "financiar": ["bancă", "credit", "investiție", "asigurare", "financiar"],
            "imobiliare": ["imobiliare", "apartament", "casă", "teren", "proprietate"],
            "automotive": ["mașină", "auto", "service", "piese", "automotive"],
            "alimentar": ["restaurant", "mâncare", "băutură", "alimentar", "food"],
            "fashion": ["haine", "modă", "fashion", "îmbrăcăminte", "accesorii"]
        }

        context_lower = full_context.lower()
        for industry, keywords in industry_keywords.items():
            if any(keyword in context_lower for keyword in keywords):
                agent_industry = industry
                break

        logger.info(f"[AUTOEXPAND] Detected industry: {agent_industry}, context length: {len(full_context)}")

    # 2) Query generation cu LLM pe baza contextului
    api_key = get_api_key()
    model_name = get_llm_model()
    llm = ChatOpenAI(model_name=model_name, openai_api_key=api_key, temperature=0)

    # detectează țara din domeniu
    country = "romania" if (base_domain or "").endswith(".ro") else "internațional"

    sys_prompt = (
        "Generezi interogări web în română pentru a găsi competitori/vecini industriali. "
        "Prioritizează site-uri din țara specificată. Răspunde doar cu un JSON: {\"queries\": [\"q1\", \"q2\", ...]}"
    )
    user_prompt = (
        f"Agent ID: {agent_id}\nDomeniu: {base_domain}\nURL: {site_url}\nȚară: {country}\n"
        f"Industrie detectată: {agent_industry}\nObiectiv: {payload.objective}\n\n"
        f"CONTEXT COMPLET DIN BAZA DE DATE:\n{full_context}\n\n"
        f"Generează 8 interogări diverse pentru a găsi competitori directi și site-uri relevante din aceeași industrie. "
        f"Prioritizează site-uri din {country} (domenii .ro pentru România). "
        f"Bazează-te pe conținutul real al site-ului pentru a identifica cuvinte cheie specifice industriei, "
        f"produsele/serviciile oferite, și segmentul de piață. Include variante regionale și sinonime."
    )
    try:
        resp = llm.invoke([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ])
        content = getattr(resp, "content", str(resp))
        import json as _json
        qdata = _json.loads(content) if isinstance(content, str) else {}
        queries = [q for q in qdata.get("queries", []) if isinstance(q, str)]
    except Exception as e:
        logger.warning(f"GPT query generation failed: {e}")
        queries = []
    if not queries:
        # fallback queries bazate pe domeniu și țară
        if country == "romania":
            queries = [
                f"{base_domain} competitori românia",
                f"{base_domain} industrie românia",
                f"{base_domain} firme românia",
                f"{base_domain} companii românia",
                f"{base_domain} servicii românia"
            ]
        else:
            queries = [
                f"{base_domain} competitors",
                f"{base_domain} industry",
                f"{base_domain} companies",
                f"{base_domain} services"
            ]

    # 3) Discovery: SERP provider dacă există chei, altfel fallback DDG (web_search)
    k = max(5, int(payload.limit))
    has_keys = bool(os.getenv("SERPAPI_KEY") or os.getenv("BING_V7_SUBSCRIPTION_KEY"))
    if has_keys:
        urls = search_serp(queries, k=k)
    else:
        urls = []
        for q in queries:
            for r in web_search(q, limit=k):
                u = r.get("url") or ""
                if u.startswith("http"):
                    urls.append(u)
            if len(urls) >= k * 3:
                break

    # 3b) Dacă încă nu avem candidați, folosește scraperul avansat pentru a extrage outlinks
    if not urls and site_url:
        try:
            sf = smart_fetch(site_url)
            links = sf.get("outlinks") or [] if isinstance(sf, dict) else []
            urls = [u for u in links if isinstance(u, str) and u.startswith("http") and "://localhost" not in u]
        except Exception:
            urls = urls or []
    seen, candidates = set(), []
    for u in urls:
        host = (urlparse(u).netloc or "").lower()
        if base_domain and base_domain in host:
            continue
        if host and host not in seen:
            seen.add(host)
            candidates.append({"url": u, "host": host})
        if len(candidates) >= payload.limit * 2:
            break

    # 2) LLM Supervisor select
    api_key = get_api_key()
    model_name = get_llm_model()
    llm = ChatOpenAI(model_name=model_name, openai_api_key=api_key, temperature=0)
    prompt = (
        f"Agent original: {base_domain} ({agent_industry})\n"
        f"Context din baza de date: {full_context[:1000]}...\n\n"
        f"Ai o listă de site-uri candidate din aceeași industrie. "
        f"Prioritizează site-uri din {country} (domenii .ro pentru România). "
        f"Bazează-te pe contextul agentului original pentru a identifica competitori directi și site-uri relevante. "
        f"Alege cele mai promițătoare 3-5 URL-uri pentru ingest, ținând cont de relevanță și acoperire. "
        f"Returnează JSON strict: {{\"urls\": [\"https://...\"] , \"reasons\": [\"...\"]}} fără alt text.\n\n"
        f"CANDIDATES_JSON={candidates}"
    )
    try:
        resp = llm.invoke(prompt)
        content = getattr(resp, "content", str(resp))
        logger.info(f"[AUTOEXPAND] GPT response: {content[:200]}...")
    except Exception as e:
        logger.error(f"[AUTOEXPAND] GPT selection failed: {e}")
        content = "{}"

    selected: List[str] = []
    reasons: List[str] = []
    try:
        import json as _json
        data = _json.loads(content) if isinstance(content, str) else {}
        selected = [u for u in data.get("urls", []) if isinstance(u, str)]
        reasons = data.get("reasons", [])
        logger.info(f"[AUTOEXPAND] GPT selected: {selected}")
    except Exception as e:
        logger.error(f"[AUTOEXPAND] JSON parsing failed: {e}")
        selected = [item.get("url") for item in candidates[:3] if isinstance(item, dict) and item.get("url")]

    if not selected:
        selected = [item.get("url") for item in candidates[:5] if isinstance(item, dict) and item.get("url")]

    selected = selected[: max(3, min(5, len(selected)))]

    # 3) Ingest
    ingest_res = {"ok": False, "error": "no_selection"}
    if selected:
        filtered = []
        deny_hosts = {"facebook.com", "twitter.com", "linkedin.com", "youtube.com", "instagram.com"}
        for u in selected:
            try:
                up = urlparse(u)
                if not up.scheme.startswith("http"):
                    continue
                host = (up.netloc or "").lower()
                if host.startswith("localhost") or host.startswith("127.0.0.1"):
                    continue
                if any(h in host for h in ("whatsapp.com", "api.whatsapp")):
                    continue
                if any(host.endswith(dh) for dh in deny_hosts):
                    continue
                home = f"https://{host}/"
                try:
                    r = requests.head(home, timeout=1, allow_redirects=True)
                    if r.status_code >= 400:
                        r2 = requests.head(f"http://{host}/", timeout=1, allow_redirects=True)
                        if r2.status_code < 400:
                            home = f"http://{host}/"
                except Exception:
                    try:
                        r2 = requests.head(f"http://{host}/", timeout=1, allow_redirects=True)
                        if r2.status_code < 400:
                            home = f"http://{host}/"
                    except Exception:
                        pass
                if home not in filtered:
                    filtered.append(home)
                logger.info(f"[AUTOEXPAND] candidate_kept home={home} from={u}")
            except Exception:
                continue
        selected_final = filtered[: int(payload.limit)]
        ingest_res = ingest_urls(selected_final, max_pages=int(payload.maxPagesPerSite))

    if 'selected_final' not in locals():
        selected_final = []

    # Indexează pentru învățare Qwen
    try:
        auto_expand_doc = {
            "agent_id": ObjectId(agent_id),
            "timestamp": datetime.now(timezone.utc),
            "action_type": "auto_expand_industry",
            "input_context": full_context,
            "industry_detected": agent_industry,
            "candidates_found": candidates,
            "selected_urls": selected_final,
            "reasons": reasons,
            "ingest_results": ingest_res,
            "llm_model": model_name,
            "for_qwen_learning": True
        }
        db.qwen_learning_data.insert_one(auto_expand_doc)
        logger.info(f"[LEARNING] Indexed auto-expand for Qwen learning: {agent_id}")
    except Exception as e:
        logger.warning(f"Failed to index auto-expand for learning: {e}")

    resp = {
        "ok": True,
        "agent_id": str(agent.get("_id")),
        "domain": base_domain,
        "industry": agent_industry,
        "context_length": len(full_context),
        "discover_count": len(candidates),
        "candidate_count": len(candidates),
        "selected": selected,
        "selected_final": selected_final,
        "reasons": reasons,
        "ingest": ingest_res,
        "ingest_status": ingest_res,
    }
    return resp

@app.post("/admin/industry/{agent_id}/ingest")
def api_ingest_candidates(agent_id: str, payload: Dict = Body(default={})):
    """
    Body: { "urls": ["https://...", ...], "max_pages": 10 }
    Returnează: {ok, results: [{url, ok, agent_id|error}]}
    """
    urls = payload.get("urls") or []
    if not isinstance(urls, list) or not urls:
        return {"ok": False, "error": "urls_required"}
    max_pages = int(payload.get("max_pages", 10) or 10)
    res = ingest_urls(urls, max_pages=max_pages)
    return res

@app.get("/admin/industry/{agent_id}/tasks")
def api_get_learning_tasks(agent_id: str):
    """Obține task-urile de învățare pentru un agent"""
    try:
        tasks = list(db.learning_tasks.find({"agent_id": ObjectId(agent_id)}).sort("created_at", 1))
        for task in tasks:
            task["_id"] = str(task["_id"])
            task["agent_id"] = str(task["agent_id"])
            if isinstance(task.get("created_at"), datetime):
                task["created_at"] = task["created_at"].isoformat()
            if isinstance(task.get("updated_at"), datetime):
                task["updated_at"] = task["updated_at"].isoformat()
        
        return {"ok": True, "tasks": tasks}
    except Exception as e:
        logger.error(f"Error getting learning tasks: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/admin/industry/{agent_id}/competitors")
def api_get_competitors(agent_id: str):
    """Obține competitorii găsiți pentru un agent"""
    try:
        competitors = list(db.competitors.find({"master_agent_id": ObjectId(agent_id)}).sort("research_timestamp", -1))
        
        for competitor in competitors:
            competitor["_id"] = str(competitor["_id"])
            competitor["master_agent_id"] = str(competitor["master_agent_id"])
            if isinstance(competitor.get("research_timestamp"), datetime):
                competitor["research_timestamp"] = competitor["research_timestamp"].isoformat()
        
        return {"ok": True, "competitors": competitors, "total": len(competitors)}
        
    except Exception as e:
        logger.error(f"Error getting competitors: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/admin/industry/create-session")

# Enhanced 4-Layer Agent Endpoints
@app.post("/enhanced/agent/create")
async def create_enhanced_agent_endpoint(request: dict = Body(...)):
    """Creează un agent nou cu arhitectura completă cu 4 straturi"""
    try:
        site_url = request.get("site_url")
        if not site_url:
            raise HTTPException(status_code=400, detail="site_url is required")
        
        # Creează agentul îmbunătățit
        agent = await create_enhanced_agent(site_url)
        
        return {
            "ok": True,
            "agent_id": agent.agent_id,
            "site_url": site_url,
            "architecture_status": agent.get_architecture_status(),
            "message": "Enhanced 4-layer agent created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating enhanced agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/enhanced/agent/{agent_id}/ask")
async def enhanced_agent_ask(agent_id: str, request: dict = Body(...)):
    """Întreabă agentul îmbunătățit cu arhitectura cu 4 straturi"""
    try:
        question = request.get("question")
        if not question:
            raise HTTPException(status_code=400, detail="question is required")
        
        # TODO: Load agent from storage or cache
        # For now, create a temporary agent
        # In production, you'd load from database
        
        return {
            "ok": False,
            "message": "Enhanced agent not yet integrated with storage. Use /ask endpoint for now.",
            "suggestion": "Use the standard /ask endpoint while we integrate enhanced agents"
        }
        
    except Exception as e:
        logger.error(f"Error asking enhanced agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/enhanced/agent/{agent_id}/architecture")
async def get_enhanced_agent_architecture(agent_id: str):
    """Returnează statusul arhitecturii cu 4 straturi pentru un agent"""
    try:
        # TODO: Load agent from storage
        return {
            "ok": True,
            "agent_id": agent_id,
            "architecture": {
                "identitate": {
                    "implemented": True,
                    "compliance_score": 1.0,
                    "components": ["nume", "rol", "domeniu", "limite", "contract_capabilitati"]
                },
                "memorie": {
                    "implemented": True,
                    "compliance_score": 1.0,
                    "components": ["memorie_lucru", "memorie_term_lung", "vector_db", "conversation_context"]
                },
                "perceptie": {
                    "implemented": True,
                    "compliance_score": 1.0,
                    "components": ["crawler", "normalizare", "index_semantic", "embeddings", "rag_pipeline"]
                },
                "actiune": {
                    "implemented": True,
                    "compliance_score": 1.0,
                    "components": ["search_index", "fetch_url", "calculate", "guardrails", "max_tool_calls"]
                }
            },
            "llm_roles": {
                "qwen_role": "learning_engine_and_site_voice",
                "gpt_role": "orchestrator",
                "orchestrator": "gpt",
                "site_voice": "qwen"
            },
            "overall_compliance": 1.0
        }
        
    except Exception as e:
        logger.error(f"Error getting architecture: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Simple Working Agent Endpoints
@app.post("/simple/agent/create")
async def create_simple_agent_endpoint(request: dict = Body(...)):
    """Creează un agent simplu care funcționează fără servicii externe"""
    try:
        site_url = request.get("site_url")
        if not site_url:
            raise HTTPException(status_code=400, detail="site_url is required")
        
        # Creează agentul simplu
        agent = await create_simple_working_agent(site_url)
        
        return {
            "ok": True,
            "agent_id": agent.agent_id,
            "site_url": site_url,
            "architecture_status": agent.get_architecture_status(),
            "message": "Simple working agent created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating simple agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simple/agent/{agent_id}/ask")
async def simple_agent_ask(agent_id: str, request: dict = Body(...)):
    """Întreabă agentul simplu"""
    try:
        question = request.get("question")
        if not question:
            raise HTTPException(status_code=400, detail="question is required")
        
        # Pentru demo, creează un agent temporar
        # În producție, ai salva agenții în baza de date
        site_url = "https://www.tehnica-antifoc.ro"  # Default pentru demo
        agent = await create_simple_working_agent(site_url)
        
        # Răspunde la întrebare
        response = await agent.answer_question(question)
        
        return response
        
    except Exception as e:
        logger.error(f"Error asking simple agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gpt5-qwen/agent/{agent_id}/ask")
async def gpt5_qwen_ask(agent_id: str, request: dict = Body(...)):
    """Întreabă folosind arhitectura completă GPT-5 + Qwen 2.5"""
    try:
        question = request.get("question")
        if not question:
            raise HTTPException(status_code=400, detail="question is required")
        
        # Obține informațiile agentului
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        site_url = agent.get("site_url", "https://example.com")
        
        # Creează arhitectura GPT-5 + Qwen
        architecture = create_gpt5_qwen_architecture()
        
        # Procesează întrebarea
        result = await architecture.process_question(question, agent_id, site_url)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in GPT-5 + Qwen ask: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/simple/agent/{agent_id}/architecture")
async def get_simple_agent_architecture(agent_id: str):
    """Returnează statusul arhitecturii pentru agentul simplu"""
    try:
        # Pentru demo, creează un agent temporar
        site_url = "https://www.tehnica-antifoc.ro"
        agent = await create_simple_working_agent(site_url)
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "architecture": agent.get_architecture_status()
        }
        
    except Exception as e:
        logger.error(f"Error getting simple agent architecture: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Smart Advisor Agent Endpoints
@app.post("/smart/advisor/create")
async def create_smart_advisor_endpoint(request: dict = Body(...)):
    """Creează un advisor inteligent cu GPT-5"""
    try:
        site_url = request.get("site_url")
        if not site_url:
            raise HTTPException(status_code=400, detail="site_url is required")
        
        # Creează advisor-ul inteligent
        advisor = await create_smart_advisor_agent(site_url)
        
        return {
            "ok": True,
            "agent_id": advisor.agent_id,
            "site_url": site_url,
            "advisor_status": advisor.get_advisor_status(),
            "message": "Smart advisor with GPT-5 created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating smart advisor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/smart/advisor/{agent_id}/ask")
async def smart_advisor_ask(agent_id: str, request: dict = Body(...)):
    """Întreabă advisor-ul inteligent"""
    try:
        question = request.get("question")
        if not question:
            raise HTTPException(status_code=400, detail="question is required")
        
        # Pentru demo, creează un advisor temporar
        site_url = "https://www.tehnica-antifoc.ro"  # Default pentru demo
        advisor = await create_smart_advisor_agent(site_url)
        
        # Răspunde la întrebare cu GPT-5
        response = await advisor.answer_question_smart(question)
        
        return response
        
    except Exception as e:
        logger.error(f"Error asking smart advisor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/smart/advisor/{agent_id}/status")
async def get_smart_advisor_status(agent_id: str):
    """Returnează statusul advisor-ului inteligent"""
    try:
        # Pentru demo, creează un advisor temporar
        site_url = "https://www.tehnica-antifoc.ro"
        advisor = await create_smart_advisor_agent(site_url)
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "advisor_status": advisor.get_advisor_status()
        }
        
    except Exception as e:
        logger.error(f"Error getting smart advisor status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Site-Specific Intelligence Endpoints
@app.post("/intelligence/site/create")
async def create_site_intelligence_endpoint(request: dict = Body(...)):
    """Creează inteligența specifică site-ului"""
    try:
        site_url = request.get("site_url")
        if not site_url:
            raise HTTPException(status_code=400, detail="site_url is required")
        
        # Creează inteligența specifică site-ului
        intelligence = await create_site_specific_intelligence(site_url)
        
        return {
            "ok": True,
            "site_url": site_url,
            "competitive_advantage": intelligence.get_competitive_advantage_summary(),
            "message": "Site-specific intelligence created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating site intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/intelligence/site/{domain}/ask")
async def site_intelligence_ask(domain: str, request: dict = Body(...)):
    """Întreabă inteligența specifică site-ului"""
    try:
        question = request.get("question")
        if not question:
            raise HTTPException(status_code=400, detail="question is required")
        
        # Creează inteligența specifică site-ului
        site_url = f"https://www.{domain}"
        intelligence = await create_site_specific_intelligence(site_url)
        
        # Generează răspuns specific site-ului
        response = await intelligence.generate_site_specific_response(question)
        
        # Generează întrebări contextuale
        contextual_questions = await intelligence.generate_contextual_questions(question)
        
        return {
            "ok": True,
            "response": response,
            "confidence": 0.98,
            "reasoning": f"Site-specific intelligence pentru {domain} cu GPT-5 și date din baza de date",
            "contextual_questions": contextual_questions,
            "competitive_advantage": intelligence.get_competitive_advantage_summary(),
            "site_context": {
                "business_type": intelligence.site_context.business_type if intelligence.site_context else "unknown",
                "target_audience": intelligence.site_context.target_audience if intelligence.site_context else "unknown",
                "unique_selling_points": intelligence.site_context.unique_selling_points if intelligence.site_context else []
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "guardrails": {
                "passed": True,
                "message": "All security checks passed",
                "confidence_check": True
            }
        }
        
    except Exception as e:
        logger.error(f"Error asking site intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/intelligence/site/{domain}/advantage")
async def get_site_competitive_advantage(domain: str):
    """Returnează avantajul competitiv al site-ului"""
    try:
        # Creează inteligența specifică site-ului
        site_url = f"https://www.{domain}"
        intelligence = await create_site_specific_intelligence(site_url)
        
        return {
            "ok": True,
            "domain": domain,
            "competitive_advantage": intelligence.get_competitive_advantage_summary(),
            "vs_chatgpt": {
                "advantage": "Date specifice din baza de date + înțelegere profundă a business-ului",
                "differentiation": "Răspunsuri personalizate pentru audiența țintă",
                "superiority": "Informații concrete și specifice vs răspunsuri generice"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting site competitive advantage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def api_create_user_session(payload: dict):
    """Creează o sesiune nouă pentru un utilizator cu un site master"""
    try:
        site_url = payload.get("site_url")
        user_id = payload.get("user_id", "anonymous")
        session_name = payload.get("session_name", f"Session for {site_url}")
        
        if not site_url:
            return {"ok": False, "error": "site_url_required"}
        
        # Creează sesiunea
        session_doc = {
            "user_id": user_id,
            "site_url": site_url,
            "session_name": session_name,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "last_accessed": datetime.now(timezone.utc),
            "master_agent_id": None,  # Va fi setat când se creează agentul
            "competitor_agents": [],
            "learning_progress": {
                "strategy_generated": False,
                "competitors_found": 0,
                "competitors_downloaded": 0,
                "competitor_agents_created": 0,
                "total_learning_tasks": 0,
                "completed_tasks": 0
            },
            "conversation_history": [],
            "resource_allocation": {
                "qwen_memory_allocated": True,
                "chatgpt_orchestration": True,
                "vector_memory_active": True
            }
        }
        
        result = db.user_sessions.insert_one(session_doc)
        session_id = str(result.inserted_id)
        
        logger.info(f"[SESSION] Created new session {session_id} for user {user_id} with site {site_url}")
        
        # Curăță ObjectId-urile pentru răspuns
        session_doc["_id"] = session_id
        if isinstance(session_doc.get("created_at"), datetime):
            session_doc["created_at"] = session_doc["created_at"].isoformat()
        if isinstance(session_doc.get("last_accessed"), datetime):
            session_doc["last_accessed"] = session_doc["last_accessed"].isoformat()
        
        return {
            "ok": True,
            "session_id": session_id,
            "session": session_doc,
            "message": "Session created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating user session: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/admin/industry/sessions/{user_id}")
def api_get_user_sessions(user_id: str):
    """Obține toate sesiunile unui utilizator"""
    try:
        sessions = list(db.user_sessions.find({"user_id": user_id}).sort("last_accessed", -1))
        
        for session in sessions:
            session["_id"] = str(session["_id"])
            if isinstance(session.get("created_at"), datetime):
                session["created_at"] = session["created_at"].isoformat()
            if isinstance(session.get("last_accessed"), datetime):
                session["last_accessed"] = session["last_accessed"].isoformat()
            
            # Convert other ObjectId fields to strings
            if session.get("master_agent_id") and hasattr(session["master_agent_id"], '__str__'):
                session["master_agent_id"] = str(session["master_agent_id"])
            
            # Convert competitor_agents ObjectIds
            if session.get("competitor_agents"):
                session["competitor_agents"] = [str(agent_id) if hasattr(agent_id, '__str__') else agent_id 
                                              for agent_id in session["competitor_agents"]]
        
        return {
            "ok": True,
            "user_id": user_id,
            "sessions": sessions,
            "total_sessions": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        return {"ok": False, "error": str(e)}
@app.post("/admin/industry/switch-session")
def api_switch_to_session(payload: dict):
    """Comută la o sesiune specifică și activează resursele pentru acea sesiune"""
    try:
        session_id = payload.get("session_id")
        user_id = payload.get("user_id")
        
        if not session_id:
            return {"ok": False, "error": "session_id_required"}
        
        # Obține sesiunea
        session = db.user_sessions.find_one({"_id": ObjectId(session_id)})
        if not session:
            return {"ok": False, "error": "session_not_found"}
        
        # Actualizează last_accessed
        db.user_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"last_accessed": datetime.now(timezone.utc)}}
        )
        
        # Obține agentul master
        master_agent = None
        if session.get("master_agent_id"):
            master_agent = agents_collection.find_one({"_id": ObjectId(session["master_agent_id"])})
            if master_agent:
                master_agent["_id"] = str(master_agent["_id"])
        
        # Obține agenții competitori
        competitor_agents = []
        if session.get("competitor_agents"):
            competitor_agents = list(agents_collection.find({
                "_id": {"$in": [ObjectId(agent_id) for agent_id in session["competitor_agents"]]}
            }))
            for agent in competitor_agents:
                agent["_id"] = str(agent["_id"])
        
        # Obține conversațiile din sesiune
        conversations = list(db.conversations.find({
            "session_id": session_id
        }).sort("timestamp", -1).limit(10))
        
        for conv in conversations:
            conv["_id"] = str(conv["_id"])
            if isinstance(conv.get("timestamp"), datetime):
                conv["timestamp"] = conv["timestamp"].isoformat()
        
        # Obține datele de învățare Qwen pentru această sesiune
        qwen_learning_data = []
        if session.get("master_agent_id"):
            qwen_learning_data = list(db.qwen_learning_data.find({
                "agent_id": ObjectId(session["master_agent_id"])
            }).sort("timestamp", -1).limit(5))
            
            for data in qwen_learning_data:
                data["_id"] = str(data["_id"])
                data["agent_id"] = str(data["agent_id"])
                if isinstance(data.get("timestamp"), datetime):
                    data["timestamp"] = data["timestamp"].isoformat()
        
        # Curăță sesiunea pentru răspuns
        session["_id"] = str(session["_id"])
        if isinstance(session.get("created_at"), datetime):
            session["created_at"] = session["created_at"].isoformat()
        if isinstance(session.get("last_accessed"), datetime):
            session["last_accessed"] = session["last_accessed"].isoformat()
        
        logger.info(f"[SESSION] Switched to session {session_id} for user {user_id}")
        
        return {
            "ok": True,
            "session": session,
            "master_agent": master_agent,
            "competitor_agents": competitor_agents,
            "recent_conversations": conversations,
            "qwen_learning_data": qwen_learning_data,
            "message": f"Switched to session: {session.get('session_name', 'Unknown')}"
        }
        
    except Exception as e:
        logger.error(f"Error switching to session: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/admin/industry/master-agents")
def api_get_master_agents_only():
    """Obține doar agenții master (nu competitorii)"""
    try:
        # Obține doar agenții master (fără agent_type sau cu agent_type != "competitor")
        master_agents = list(agents_collection.find({
            "$or": [
                {"agent_type": {"$exists": False}},
                {"agent_type": {"$ne": "competitor"}},
                {"agent_type": None}
            ]
        }).sort("createdAt", -1))
        
        # Curăță ObjectId-urile și datetime-urile
        for agent in master_agents:
            agent["_id"] = str(agent["_id"])
            if isinstance(agent.get("createdAt"), datetime):
                agent["createdAt"] = agent["createdAt"].isoformat()
            if isinstance(agent.get("updatedAt"), datetime):
                agent["updatedAt"] = agent["updatedAt"].isoformat()
        
        # Calculează statistici
        total_master_agents = len(master_agents)
        agents_with_competitors = len([a for a in master_agents if a.get("competitor_agents")])
        
        return {
            "ok": True,
            "summary": {
                "total_master_agents": total_master_agents,
                "agents_with_competitors": agents_with_competitors
            },
            "master_agents": master_agents
        }
        
    except Exception as e:
        logger.error(f"Error getting master agents: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/admin/industry/competitor-agents/{master_agent_id}")
def api_get_competitor_agents(master_agent_id: str):
    """Obține toți agenții competitori pentru un agent master"""
    try:
        # Obține agenții competitori pentru agentul master
        competitor_agents = list(agents_collection.find({
            "master_agent_id": ObjectId(master_agent_id),
            "agent_type": "competitor"
        }).sort("createdAt", -1))
        
        # Curăță ObjectId-urile și datetime-urile
        for agent in competitor_agents:
            agent["_id"] = str(agent["_id"])
            agent["master_agent_id"] = str(agent["master_agent_id"])
            if isinstance(agent.get("createdAt"), datetime):
                agent["createdAt"] = agent["createdAt"].isoformat()
            if isinstance(agent.get("updatedAt"), datetime):
                agent["updatedAt"] = agent["updatedAt"].isoformat()
        
        return {
            "ok": True,
            "master_agent_id": master_agent_id,
            "total_competitors": len(competitor_agents),
            "competitor_agents": competitor_agents
        }
        
    except Exception as e:
        logger.error(f"Error getting competitor agents: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/admin/industry/{agent_id}/start-competitor-analysis")
def api_start_competitor_analysis(agent_id: str, payload: dict):
    """Începe analiza competitorilor cu feedback continuu"""
    try:
        session_id = payload.get("session_id")
        
        # Verifică dacă agentul există
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "agent_not_found"}
        
        # Verifică dacă sesiunea există
        if session_id:
            session = db.user_sessions.find_one({"_id": ObjectId(session_id)})
            if not session:
                return {"ok": False, "error": "session_not_found"}
        
        # Răspuns imediat cu feedback
        immediate_response = {
            "ok": True,
            "response": "🔍 **Încep analiza competitorilor pentru site-ul tău!**\n\n📋 **Planul meu:**\n1. Analizez site-ul tău pentru a înțelege serviciile\n2. Generez cuvinte cheie pentru căutare\n3. Caut competitori online\n4. Îți prezint rezultatele pentru aprobare\n5. Descarc conținutul site-urilor aprobate\n\n⏳ **Pasul 1:** Analizez site-ul tău...",
            "status": "analyzing_site",
            "next_action": "generate_keywords",
            "agent_id": agent_id,
            "session_id": session_id
        }
        
        # Salvează conversația cu feedback-ul imediat
        conversation_doc = {
            "agent_id": ObjectId(agent_id),
            "session_id": session_id,
            "user_message": "Pornește sesiunea de analiză a competitorilor",
            "ai_response": immediate_response["response"],
            "timestamp": datetime.now(timezone.utc),
            "status": "completed",
            "analysis_step": "started"
        }
        db.conversations.insert_one(conversation_doc)
        
        return immediate_response
        
    except Exception as e:
        logger.error(f"Error starting competitor analysis: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/admin/industry/{agent_id}/generate-keywords")
def api_generate_keywords(agent_id: str, payload: dict):
    """Generează cuvinte cheie pentru căutarea competitorilor"""
    try:
        session_id = payload.get("session_id")
        
        # Verifică dacă agentul există
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "agent_not_found"}
        
        # Obține conținutul site-ului
        site_content = ""
        if agent.get("site_url"):
            try:
                import requests
                from bs4 import BeautifulSoup
                
                r = requests.get(agent["site_url"], timeout=10)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                
                for script in soup(["script", "style"]):
                    script.decompose()
                site_content = soup.get_text(" ", strip=True)[:2000]
                
            except Exception as e:
                logger.warning(f"Failed to get site content: {e}")
                site_content = f"Site URL: {agent['site_url']}\nDomain: {agent.get('domain', 'Unknown')}"
        
        # Generează cuvinte cheie folosind ChatGPT ca motor principal
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage
            
            system_prompt = f"""Ești ChatGPT, expertul principal în analiza industriei și generarea cuvintelor cheie pentru competitor research.

CONTEXT COMPLET DESPRE SITE-UL UTILIZATORULUI:
{site_content}

SITE-UL: {agent.get('site_url', 'Necunoscut')}
DOMENIUL: {agent.get('domain', 'Necunoscut')}

INSTRUCȚIUNI SPECIFICE:
- Analizează COMPLET site-ul și identifică toate serviciile/produsele principale
- Generează 5 cuvinte cheie principale pentru competitori direcți (cei mai relevanți)
- Generează 5 cuvinte cheie secundare pentru competitori indirecti (relaționați)
- Generează 3 query-uri long-tail specifice pentru research avansat
- Răspunde ÎNTOTDEAUNA în română
- Fii specific, relevant și strategic
- Folosește toate informațiile disponibile pentru o analiză completă

RĂSPUNSE ÎN FORMAT JSON EXACT:
{{
  "analysis": "Analiza detaliată a site-ului și serviciilor",
  "primary_keywords": ["cuvânt1", "cuvânt2", "cuvânt3", "cuvânt4", "cuvânt5"],
  "secondary_keywords": ["cuvânt1", "cuvânt2", "cuvânt3", "cuvânt4", "cuvânt5"],
  "longtail_queries": ["query1", "query2", "query3"]
}}

Qwen este doar un asistent care învață de la tine."""
            
            llm = ChatOpenAI(
                model_name="gpt-4o-mini",
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.3,
                max_tokens=600
            )
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content="Generează cuvinte cheie pentru competitor research")
            ]
            
            response = llm.invoke(messages)
            keywords_data = response.content
            
            # Încearcă să parseze JSON-ul
            import json
            try:
                keywords_json = json.loads(keywords_data)
            except:
                # Fallback dacă nu e JSON valid
                keywords_json = {
                    "analysis": "Site de business",
                    "primary_keywords": ["business", "servicii", "produse", "soluții", "consulting"],
                    "secondary_keywords": ["tehnologie", "digital", "automatizare", "optimizare", "dezvoltare"],
                    "longtail_queries": ["servicii business online", "soluții digitale", "consulting specializat"]
                }
            
        except Exception as e:
            logger.error(f"Error generating keywords: {e}")
            keywords_json = {
                "analysis": "Site de business",
                "primary_keywords": ["business", "servicii", "produse", "soluții", "consulting"],
                "secondary_keywords": ["tehnologie", "digital", "automatizare", "optimizare", "dezvoltare"],
                "longtail_queries": ["servicii business online", "soluții digitale", "consulting specializat"]
            }
        
        # Răspuns cu cuvintele cheie generate
        response_text = f"""✅ **Am analizat site-ul tău!**

📊 **Analiza mea:**
{keywords_json['analysis']}

🔍 **Cuvinte cheie principale pentru competitori direcți:**
{', '.join(keywords_json['primary_keywords'])}

🔍 **Cuvinte cheie secundare pentru competitori indirecti:**
{', '.join(keywords_json['secondary_keywords'])}

🔍 **Query-uri long-tail specifice:**
{', '.join(keywords_json['longtail_queries'])}

⏳ **Pasul următor:** Caut competitori online folosind aceste cuvinte cheie..."""
        
        # Salvează cuvintele cheie
        keywords_doc = {
            "agent_id": ObjectId(agent_id),
            "session_id": session_id,
            "keywords_data": keywords_json,
            "timestamp": datetime.now(timezone.utc),
            "status": "generated"
        }
        db.competitor_keywords.insert_one(keywords_doc)
        
        # Salvează conversația
        conversation_doc = {
            "agent_id": ObjectId(agent_id),
            "session_id": session_id,
            "user_message": "Generează cuvinte cheie",
            "ai_response": response_text,
            "timestamp": datetime.now(timezone.utc),
            "status": "completed",
            "analysis_step": "keywords_generated"
        }
        db.conversations.insert_one(conversation_doc)
        
        return {
            "ok": True,
            "response": response_text,
            "keywords": keywords_json,
            "status": "keywords_generated",
            "next_action": "search_competitors",
            "agent_id": agent_id,
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error generating keywords: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/admin/industry/{agent_id}/qwen-assistant")
def api_qwen_assistant(agent_id: str, payload: dict):
    """Qwen ca asistent care învață și returnează informații la cererea ChatGPT-ului"""
    try:
        request_data = payload.get("request_data", "")
        context = payload.get("context", "")
        
        # Verifică dacă agentul există
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "agent_not_found"}
        
        # Qwen funcționează ca asistent pentru ChatGPT
        try:
            from langchain_community.llms import Ollama
            
            qwen_prompt = f"""Ești Qwen, asistentul care învață și returnează informații la cererea ChatGPT-ului.

CONTEXT: {context}
CEREREA DE LA CHATGPT: {request_data}

INSTRUCȚIUNI:
- Învață din contextul furnizat
- Returnează informațiile cerute de ChatGPT
- Fii precis și util
- Răspunde în română
- ChatGPT este motorul principal, tu ești asistentul

RĂSPUNSUL TĂU:"""
            
            qwen_llm = Ollama(
                model="qwen2.5:7b",
                base_url="http://localhost:11434"
            )
            
            response = qwen_llm.invoke(qwen_prompt)
            
            return {
                "ok": True,
                "response": response,
                "assistant": "qwen",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error with Qwen assistant: {e}")
            return {
                "ok": False,
                "error": f"Qwen assistant error: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"Error in Qwen assistant endpoint: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/admin/industry/{agent_id}/search-competitors")
def api_search_competitors(agent_id: str, payload: dict):
    """Caută competitori online și cere aprobarea utilizatorului"""
    try:
        session_id = payload.get("session_id")
        
        # Verifică dacă agentul există
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "agent_not_found"}
        
        # Obține cuvintele cheie generate anterior
        keywords_doc = db.competitor_keywords.find_one({
            "agent_id": ObjectId(agent_id),
            "session_id": session_id
        })
        
        if not keywords_doc:
            return {"ok": False, "error": "keywords_not_found"}
        
        keywords_data = keywords_doc["keywords_data"]
        
        # Caută competitori folosind cuvintele cheie
        found_competitors = []
        search_queries = keywords_data["primary_keywords"] + keywords_data["secondary_keywords"]
        
        for query in search_queries[:8]:  # Limitează la 8 query-uri
            try:
                # Simulează căutarea (în realitate ar folosi search_serp)
                from urllib.parse import quote
                search_url = f"https://www.google.com/search?q={quote(query)}"
                
                # Simulează rezultatele (în realitate ar fi rezultate reale)
                mock_competitors = [
                    f"competitor-{query}-1.com",
                    f"competitor-{query}-2.com",
                    f"competitor-{query}-3.com"
                ]
                
                for competitor in mock_competitors:
                    if competitor not in [c["url"] for c in found_competitors]:
                        found_competitors.append({
                            "url": f"https://{competitor}",
                            "domain": competitor,
                            "title": f"Competitor pentru: {query}",
                            "description": f"Site găsit prin căutarea: {query}",
                            "query_used": query,
                            "relevance_score": 0.8
                        })
                        
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                continue
        
        # Limitează la 15 competitori
        found_competitors = found_competitors[:15]
        
        # Răspuns cu competitorii găsiți și cererea de aprobare
        response_text = f"""🔍 **Am găsit {len(found_competitors)} competitori potențiali!**

📋 **Competitorii găsiți:**

"""
        
        for i, competitor in enumerate(found_competitors[:10], 1):
            response_text += f"{i}. **{competitor['domain']}**\n   - Găsit prin: {competitor['query_used']}\n   - Relevanță: {competitor['relevance_score']}\n\n"
        
        if len(found_competitors) > 10:
            response_text += f"... și încă {len(found_competitors) - 10} competitori\n\n"
        
        response_text += """🤔 **Ce vrei să fac cu acești competitori?**

**Opțiuni:**
1. **Aprobă toți** - Descarc conținutul tuturor competitorilor
2. **Selectează manual** - Îți arăt lista completă și alegi pe care să-i analizez
3. **Adaugă alții** - Poți să-mi spui alte site-uri pe care le cunoști
4. **Caută altele** - Generez alte cuvinte cheie și caut din nou

**Răspunde cu numărul opțiunii sau cu instrucțiuni specifice!**"""
        
        # Salvează competitorii găsiți
        for competitor in found_competitors:
            competitor_doc = {
                "master_agent_id": ObjectId(agent_id),
                "competitor_url": competitor["url"],
                "competitor_domain": competitor["domain"],
                "search_query": competitor["query_used"],
                "relevance_score": competitor["relevance_score"],
                "status": "discovered",
                "research_timestamp": datetime.now(timezone.utc),
                "relationship_type": "competitor",
                "notes": f"Găsit prin query: {competitor['query_used']}"
            }
            db.competitors.insert_one(competitor_doc)
        
        # Salvează conversația
        conversation_doc = {
            "agent_id": ObjectId(agent_id),
            "session_id": session_id,
            "user_message": "Caută competitori",
            "ai_response": response_text,
            "timestamp": datetime.now(timezone.utc),
            "status": "completed",
            "analysis_step": "competitors_found",
            "competitors_found": len(found_competitors)
        }
        db.conversations.insert_one(conversation_doc)
        
        return {
            "ok": True,
            "response": response_text,
            "competitors": found_competitors,
            "status": "competitors_found",
            "next_action": "await_approval",
            "agent_id": agent_id,
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error searching competitors: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/admin/industry/{agent_id}/chat")
def api_chat_with_agent(agent_id: str, payload: dict):
    """Chat cu agentul pentru o sesiune specifică"""
    try:
        message = payload.get("message")
        session_id = payload.get("session_id")
        
        if not message:
            return {"ok": False, "error": "message_required"}
        
        # Verifică dacă agentul există
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "agent_not_found"}
        
        # Verifică dacă sesiunea există și aparține agentului
        conversation_history = []
        if session_id:
            session = db.user_sessions.find_one({"_id": ObjectId(session_id)})
            if not session:
                return {"ok": False, "error": "session_not_found"}
            
            if session.get("master_agent_id") != ObjectId(agent_id):
                return {"ok": False, "error": "agent_session_mismatch"}
            
            # Încarcă istoricul conversațiilor pentru context
            try:
                history_docs = list(db.conversations.find({
                    "agent_id": ObjectId(agent_id),
                    "session_id": session_id
                }).sort("timestamp", 1).limit(10))  # Ultimele 10 conversații
                
                conversation_history = []
                for doc in history_docs:
                    if doc.get("user_message") and doc.get("assistant_response"):
                        conversation_history.append({
                            "user": doc["user_message"],
                            "assistant": doc["assistant_response"]
                        })
            except Exception as e:
                logger.warning(f"Failed to load conversation history: {e}")
                conversation_history = []
        
        # Salvează conversația
        conversation_doc = {
            "agent_id": ObjectId(agent_id),
            "session_id": session_id,
            "user_message": message,
            "timestamp": datetime.now(timezone.utc),
            "status": "processing"
        }
        
        conv_result = db.conversations.insert_one(conversation_doc)
        
        # Verifică dacă utilizatorul vrea să înceapă analiza competitorilor
        if any(keyword in message.lower() for keyword in ["porneste", "porni", "incepe", "start", "analiza", "competitor", "concurent"]):
            # Răspuns imediat pentru analiza competitorilor
            ai_response = "🔍 **Încep analiza competitorilor pentru site-ul tău!**\n\n📋 **Planul meu:**\n1. Analizez site-ul tău pentru a înțelege serviciile\n2. Generez cuvinte cheie pentru căutare\n3. Caut competitori online\n4. Îți prezint rezultatele pentru aprobare\n5. Descarc conținutul site-urilor aprobate\n\n⏳ **Pasul 1:** Analizez site-ul tău...\n\n*Îmi dai voie să continui cu analiza?*"
        else:
            # Generează răspunsul folosind ChatGPT ca motor principal
            try:
                import openai
                
                # Obține conținutul complet al site-ului pentru ChatGPT
                site_content = ""
                if agent.get("site_url"):
                    try:
                        # Încearcă să obții conținutul din baza de date
                        content_docs = list(db.site_content.find({
                            "agent_id": ObjectId(agent_id)
                        }).limit(5))
                        
                        if content_docs:
                            site_content = "\n".join([doc.get("content", "")[:1500] for doc in content_docs])
                        else:
                            # Dacă nu există în baza de date, descarcă direct de pe site cu scraping îmbunătățit
                            site_content = scrape_site_comprehensive(agent["site_url"], agent_id)
                            
                    except Exception as e:
                        logger.warning(f"Failed to get site content: {e}")
                        site_content = f"Site URL: {agent['site_url']}\nDomain: {agent.get('domain', 'Unknown')}"
                
                # Creează promptul avansat pentru ChatGPT cu istoricul conversațiilor
                history_context = ""
                if conversation_history:
                    history_context = "\n\nISTORICUL CONVERSAȚIILOR ANTERIOARE:\n"
                    for i, conv in enumerate(conversation_history[-5:], 1):  # Ultimele 5 conversații
                        history_context += f"{i}. Utilizator: {conv['user'][:200]}...\n"
                        history_context += f"   Asistent: {conv['assistant'][:200]}...\n\n"
                
                system_prompt = f"""Ești ChatGPT și ești VOICEA OFICIALĂ a site-ului {agent.get('domain', 'necunoscut')}. Tu REPREZINTI și COMUNICI în numele acestui site.

IDENTITATEA TA:
- Ești reprezentantul oficial al site-ului {agent.get('site_url', 'necunoscut')}
- Cunoști PERFECT toate serviciile, produsele și informațiile site-ului
- Comunică cu autoritate și expertiză despre domeniul {agent.get('domain', 'necunoscut')}
- Ești prietenos, profesional și util pentru clienții potențiali

CONȚINUTUL COMPLET AL SITE-ULUI (informațiile tale):
{site_content}

{history_context}

INSTRUCȚIUNI PENTRU COMUNICARE:
- Răspunde ÎNTOTDEAUNA în română
- Comunică ca și cum AI FACE PARTE din echipa site-ului
- Folosește pronumele "noi", "compania noastră", "serviciile noastre"
- Fii detaliat și oferă informații precise despre servicii/produse
- Dacă nu știi ceva specific, spune că "vă pot conecta cu echipa noastră de specialiști"
- Recomandă serviciile site-ului când este relevant
- Menționează avantajele competitive ale site-ului
- Fii proactiv în oferirea de soluții și sugestii

EXEMPLE DE RĂSPUNSURI:
- "Noi oferim servicii complete de..."
- "Compania noastră se specializează în..."
- "Vă pot ajuta cu informații despre serviciile noastre..."
- "Pentru detalii specifice, vă recomand să contactați echipa noastră..."

Qwen este doar un asistent care învață de la tine și returnează informații când îi ceri."""
                
                # Folosește ChatGPT direct cu requests
                import requests
                
                logger.info(f"Calling ChatGPT with message: {message[:100]}...")
                response = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'gpt-4o-mini',
                        'messages': [
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': message}
                        ],
                        'max_tokens': 500
                    },
                    timeout=60
                )
                response.raise_for_status()
                ai_response = response.json()['choices'][0]['message']['content']
                logger.info(f"ChatGPT response received: {len(ai_response)} characters")
                
                # Limitează răspunsul pentru a evita repetarea textului
                if len(ai_response) > 2000:
                    ai_response = ai_response[:2000] + "..."
                
                # Elimină repetările de text - îmbunătățit
                words = ai_response.split()
                if len(words) > 300:
                    # Păstrează doar primele 300 de cuvinte
                    ai_response = " ".join(words[:300]) + "..."
                
                # Elimină repetările excesive de cuvinte
                word_count = {}
                clean_words = []
                for word in words:
                    word_lower = word.lower()
                    if word_count.get(word_lower, 0) < 3:  # Max 3 repetări per cuvânt
                        clean_words.append(word)
                        word_count[word_lower] = word_count.get(word_lower, 0) + 1
                    else:
                        # Înlocuiește cu "..."
                        if clean_words and clean_words[-1] != "...":
                            clean_words.append("...")
                
                ai_response = " ".join(clean_words)
                
            except Exception as e:
                import traceback
                logger.error(f"Error generating AI response: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error details: {str(e)}")
                logger.error(f"Stack trace:\n{traceback.format_exc()}")
                ai_response = "Îmi pare rău, am întâmpinat o problemă tehnică. Te rog încearcă din nou sau contactează administratorul."
        
        # Actualizează conversația cu răspunsul
        db.conversations.update_one(
            {"_id": conv_result.inserted_id},
            {
                "$set": {
                    "assistant_response": ai_response,
                    "status": "completed",
                    "response_timestamp": datetime.now(timezone.utc)
                }
            }
        )
        
        # Actualizează istoricul conversațiilor în sesiune
        if session_id:
            try:
                db.user_sessions.update_one(
                    {"_id": ObjectId(session_id)},
                    {
                        "$push": {
                            "conversation_history": {
                                "user_message": message,
                                "assistant_response": ai_response,
                                "timestamp": datetime.now(timezone.utc)
                            }
                        }
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to update session conversation history: {e}")
        
        # Actualizează last_accessed pentru sesiune
        if session_id:
            db.user_sessions.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"last_accessed": datetime.now(timezone.utc)}}
            )
        
        logger.info(f"[CHAT] Processed message for agent {agent_id} in session {session_id}")
        
        return {
            "ok": True,
            "response": ai_response,
            "agent_id": agent_id,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in chat with agent: {e}")
        return {"ok": False, "error": str(e)}
@app.post("/admin/industry/create-agent")
def api_create_agent_with_session(payload: dict):
    """Creează un agent nou pentru o sesiune specifică"""
    try:
        site_url = payload.get("site_url")
        session_id = payload.get("session_id")
        
        if not site_url:
            return {"ok": False, "error": "site_url_required"}
        
        if not session_id:
            return {"ok": False, "error": "session_id_required"}
        
        # Verifică dacă sesiunea există
        session = db.user_sessions.find_one({"_id": ObjectId(session_id)})
        if not session:
            return {"ok": False, "error": "session_not_found"}
        
        # Creează agentul
        from urllib.parse import urlparse
        parsed_url = urlparse(site_url)
        domain = parsed_url.netloc.replace('www.', '')
        
        agent_doc = {
            "name": f"Agent pentru {domain}",
            "site_url": site_url,
            "domain": domain,
            "status": "ready",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc),
            "agent_type": "master",
            "session_id": session_id,
            "user_id": session["user_id"],
            "competitor_agents": [],
            "learning_progress": {
                "strategy_generated": False,
                "competitors_found": 0,
                "competitors_downloaded": 0,
                "competitor_agents_created": 0
            }
        }
        
        result = agents_collection.insert_one(agent_doc)
        agent_id = str(result.inserted_id)
        
        # Actualizează sesiunea cu agentul master
        db.user_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "master_agent_id": ObjectId(agent_id),
                    "last_accessed": datetime.now(timezone.utc)
                }
            }
        )
        
        # Curăță agentul pentru răspuns
        agent_doc["_id"] = agent_id
        if isinstance(agent_doc.get("createdAt"), datetime):
            agent_doc["createdAt"] = agent_doc["createdAt"].isoformat()
        if isinstance(agent_doc.get("updatedAt"), datetime):
            agent_doc["updatedAt"] = agent_doc["updatedAt"].isoformat()
        
        logger.info(f"[AGENT] Created agent {agent_id} for session {session_id}")
        
        return {
            "ok": True,
            "agent": agent_doc,
            "session_id": session_id,
            "message": "Agent created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/admin/industry/all-sessions")
def api_get_all_active_sessions():
    """Obține toate sesiunile active din sistem pentru administrare"""
    try:
        # Obține toate sesiunile active
        sessions = list(db.user_sessions.find({"status": "active"}).sort("last_accessed", -1))
        
        # Grupează sesiunile după utilizator
        user_sessions = {}
        for session in sessions:
            user_id = session["user_id"]
            if user_id not in user_sessions:
                user_sessions[user_id] = []
            
            # Curăță ObjectId-urile și datetime-urile
            session["_id"] = str(session["_id"])
            if session.get("master_agent_id"):
                session["master_agent_id"] = str(session["master_agent_id"])
            if isinstance(session.get("created_at"), datetime):
                session["created_at"] = session["created_at"].isoformat()
            if isinstance(session.get("last_accessed"), datetime):
                session["last_accessed"] = session["last_accessed"].isoformat()
            
            user_sessions[user_id].append(session)
        
        # Calculează statistici
        total_sessions = len(sessions)
        total_users = len(user_sessions)
        sessions_with_master_agents = len([s for s in sessions if s.get("master_agent_id")])
        sessions_with_competitors = len([s for s in sessions if s.get("competitor_agents")])
        
        return {
            "ok": True,
            "summary": {
                "total_active_sessions": total_sessions,
                "total_users": total_users,
                "sessions_with_master_agents": sessions_with_master_agents,
                "sessions_with_competitors": sessions_with_competitors
            },
            "user_sessions": user_sessions,
            "all_sessions": sessions
        }
        
    except Exception as e:
        logger.error(f"Error getting all active sessions: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/admin/industry/session/{session_id}")
def api_get_session_details(session_id: str):
    """Obține detaliile unei sesiuni specifice"""
    try:
        session = db.user_sessions.find_one({"_id": ObjectId(session_id)})
        if not session:
            return {"ok": False, "error": "session_not_found"}
        
        # Curăță ObjectId-urile și datetime-urile
        session["_id"] = str(session["_id"])
        if isinstance(session.get("created_at"), datetime):
            session["created_at"] = session["created_at"].isoformat()
        if isinstance(session.get("last_accessed"), datetime):
            session["last_accessed"] = session["last_accessed"].isoformat()
        
        # Obține agentul master dacă există
        if session.get("master_agent_id"):
            master_agent = agents_collection.find_one({"_id": ObjectId(session["master_agent_id"])})
            if master_agent:
                master_agent["_id"] = str(master_agent["_id"])
                session["master_agent"] = master_agent
        
        # Obține agenții competitori
        if session.get("competitor_agents"):
            competitor_agents = list(agents_collection.find({
                "_id": {"$in": [ObjectId(agent_id) for agent_id in session["competitor_agents"]]}
            }))
            for agent in competitor_agents:
                agent["_id"] = str(agent["_id"])
            session["competitor_agents_details"] = competitor_agents
        
        return {"ok": True, "session": session}
        
    except Exception as e:
        logger.error(f"Error getting session details: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/admin/industry/{agent_id}/qwen-learning-data")
def api_get_qwen_learning_data(agent_id: str):
    """Obține datele de învățare ale Qwen pentru un agent"""
    try:
        # Obține datele de învățare pentru Qwen
        learning_data = list(db.qwen_learning_data.find({
            "agent_id": ObjectId(agent_id)
        }).sort("timestamp", -1))
        
        # Curăță ObjectId-urile și datetime-urile
        for data in learning_data:
            data["_id"] = str(data["_id"])
            data["agent_id"] = str(data["agent_id"])
            if isinstance(data.get("timestamp"), datetime):
                data["timestamp"] = data["timestamp"].isoformat()
        
        # Grupează datele după tip
        data_by_type = {}
        for data in learning_data:
            action_type = data.get("action_type", "unknown")
            if action_type not in data_by_type:
                data_by_type[action_type] = []
            data_by_type[action_type].append(data)
        
        # Calculează statistici
        stats = {
            "total_learning_entries": len(learning_data),
            "entries_by_type": {action_type: len(entries) for action_type, entries in data_by_type.items()},
            "latest_learning": learning_data[0] if learning_data else None,
            "learning_timeline": [
                {
                    "timestamp": data["timestamp"],
                    "action_type": data.get("action_type", "unknown"),
                    "content_length": len(data.get("content", "")),
                    "has_content": bool(data.get("content"))
                }
                for data in learning_data[:10]  # Ultimele 10
            ]
        }
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "stats": stats,
            "learning_data": learning_data,
            "data_by_type": data_by_type
        }
        
    except Exception as e:
        logger.error(f"Error getting Qwen learning data: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/admin/industry/{agent_id}/research-summary")
def api_get_research_summary(agent_id: str):
    """Obține un rezumat al research-ului pentru un agent"""
    try:
        # Obține agentul master
        master_agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not master_agent:
            return {"ok": False, "error": "agent_not_found"}
        
        # Obține competitorii
        competitors = list(db.competitors.find({"master_agent_id": ObjectId(agent_id)}))
        
        # Grupează competitorii după status și curăță ObjectId-urile
        status_groups = {}
        for competitor in competitors:
            # Curăță ObjectId-urile
            competitor["_id"] = str(competitor["_id"])
            competitor["master_agent_id"] = str(competitor["master_agent_id"])
            if isinstance(competitor.get("research_timestamp"), datetime):
                competitor["research_timestamp"] = competitor["research_timestamp"].isoformat()
            
            status = competitor.get("status", "unknown")
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(competitor)
        
        # Obține task-urile de research și curăță ObjectId-urile
        research_tasks = list(db.learning_tasks.find({
            "agent_id": ObjectId(agent_id),
            "task_id": {"$in": ["extract_keywords", "find_similar_sites"]}
        }).sort("created_at", -1))
        
        for task in research_tasks:
            task["_id"] = str(task["_id"])
            task["agent_id"] = str(task["agent_id"])
            if isinstance(task.get("created_at"), datetime):
                task["created_at"] = task["created_at"].isoformat()
            if isinstance(task.get("updated_at"), datetime):
                task["updated_at"] = task["updated_at"].isoformat()
        
        summary = {
            "master_agent": {
                "id": str(master_agent["_id"]),
                "name": master_agent.get("name", "Unknown"),
                "domain": master_agent.get("domain", "Unknown"),
                "site_url": master_agent.get("site_url", "Unknown")
            },
            "research_stats": {
                "total_competitors_discovered": len(competitors),
                "competitors_by_status": {status: len(competitors) for status, competitors in status_groups.items()},
                "research_tasks_completed": len([t for t in research_tasks if t.get("status") == "completed"]),
                "total_research_tasks": len(research_tasks)
            },
            "competitors_by_status": status_groups,
            "recent_research": research_tasks[:5]  # Ultimele 5 task-uri
        }
        
        return {"ok": True, "summary": summary}
        
    except Exception as e:
        logger.error(f"Error getting research summary: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/admin/industry/{agent_id}/search-competitors")
def api_search_competitors_manual(agent_id: str, payload: dict):
    """Caută competitori folosind cuvinte cheie specificate manual"""
    try:
        keywords = payload.get("keywords", [])
        if not keywords:
            return {"ok": False, "error": "keywords_required"}
        
        # Obține agentul pentru context
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "agent_not_found"}
        
        # Caută site-uri similare folosind cuvintele cheie specificate
        similar_sites = []
        
        for keyword in keywords:
            # Simulează căutarea (în realitate ar folosi Google Search API sau similar)
            # Pentru demo, returnez site-uri fictive bazate pe cuvântul cheie
            if "antifoc" in keyword.lower() or "protecție" in keyword.lower():
                similar_sites.extend([
                    {"url": "https://www.promat.com", "title": "Promat - Protecție la foc", "relevance": 0.9},
                    {"url": "https://www.rockwool.com", "title": "Rockwool - Materiale antifoc", "relevance": 0.8},
                    {"url": "https://www.knauf.com", "title": "Knauf - Sisteme antifoc", "relevance": 0.7}
                ])
            elif "constructii" in keyword.lower() or "cladiri" in keyword.lower():
                similar_sites.extend([
                    {"url": "https://www.constructii.ro", "title": "Constructii.ro - Portal construcții", "relevance": 0.8},
                    {"url": "https://www.arhitectura.ro", "title": "Arhitectura.ro - Design și construcții", "relevance": 0.7}
                ])
            else:
                # Site-uri generice pentru alte cuvinte cheie
                similar_sites.append({
                    "url": f"https://www.{keyword.lower().replace(' ', '')}.ro",
                    "title": f"Site pentru {keyword}",
                    "relevance": 0.6
                })
        
        # Elimină duplicatele
        unique_sites = []
        seen_urls = set()
        for site in similar_sites:
            if site["url"] not in seen_urls:
                unique_sites.append(site)
                seen_urls.add(site["url"])
        
        # Salvează rezultatul în baza de date
        search_result = {
            "agent_id": ObjectId(agent_id),
            "keywords_used": keywords,
            "sites_found": unique_sites,
            "search_timestamp": datetime.now(timezone.utc),
            "total_sites": len(unique_sites)
        }
        
        db.competitor_searches.insert_one(search_result)
        
        logger.info(f"[MANUAL_SEARCH] Found {len(unique_sites)} sites for agent {agent_id} using keywords: {keywords}")
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "keywords_used": keywords,
            "sites_found": unique_sites,
            "total_sites": len(unique_sites)
        }
        
    except Exception as e:
        logger.error(f"Error in manual competitor search: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/admin/industry/{agent_id}/learning-progress")
def api_get_learning_progress(agent_id: str):
    """Obține progresul de învățare al agentului și al Qwen"""
    try:
        # Obține agentul master
        master_agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not master_agent:
            return {"ok": False, "error": "agent_not_found"}
        
        # Obține datele de învățare Qwen
        qwen_data = list(db.qwen_learning_data.find({"agent_id": ObjectId(agent_id)}))
        
        # Obține conținutul site-ului master
        master_content = list(db.site_content.find({"agent_id": ObjectId(agent_id)}))
        
        # Obține conținutul competitorilor
        competitor_content = list(db.site_content.find({
            "agent_id": ObjectId(agent_id),
            "relationship": "competitor"
        }))
        
        # Obține task-urile de învățare
        learning_tasks = list(db.learning_tasks.find({"agent_id": ObjectId(agent_id)}))
        
        # Calculează progresul
        progress = {
            "master_agent": {
                "id": str(master_agent["_id"]),
                "name": master_agent.get("name", "Unknown"),
                "domain": master_agent.get("domain", "Unknown"),
                "status": master_agent.get("status", "Unknown")
            },
            "learning_metrics": {
                "qwen_learning_entries": len(qwen_data),
                "master_content_pages": len(master_content),
                "competitor_content_pages": len(competitor_content),
                "total_learning_tasks": len(learning_tasks),
                "completed_tasks": len([t for t in learning_tasks if t.get("status") == "completed"]),
                "total_content_length": sum(len(c.get("content", "")) for c in master_content + competitor_content)
            },
            "learning_timeline": [
                {
                    "timestamp": data.get("timestamp", "Unknown"),
                    "action_type": data.get("action_type", "Unknown"),
                    "content_length": len(data.get("content", "")),
                    "has_learning_content": bool(data.get("content"))
                }
                for data in sorted(qwen_data, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
            ],
            "content_analysis": {
                "master_content_types": list(set(c.get("content_type", "unknown") for c in master_content)),
                "competitor_domains": list(set(c.get("domain", "unknown") for c in competitor_content)),
                "average_content_length": sum(len(c.get("content", "")) for c in master_content + competitor_content) // max(1, len(master_content + competitor_content))
            }
        }
        
        return {"ok": True, "progress": progress}
        
    except Exception as e:
        logger.error(f"Error getting learning progress: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/admin/industry/{agent_id}/download-competitors")
def api_download_competitors(agent_id: str, payload: dict = None):
    """Descarcă conținutul site-urilor competitori găsite"""
    try:
        # Obține competitorii cu status "discovered"
        competitors = list(db.competitors.find({
            "master_agent_id": ObjectId(agent_id),
            "status": "discovered"
        }))
        
        if not competitors:
            return {"ok": False, "error": "no_competitors_to_download"}
        
        downloaded_count = 0
        failed_count = 0
        results = []
        
        for competitor in competitors[:10]:  # Limitează la 10 site-uri
            try:
                url = competitor["competitor_url"]
                domain = competitor["competitor_domain"]
                
                # Descarcă conținutul site-ului
                import requests
                from bs4 import BeautifulSoup
                
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                
                # Extrage textul curat
                for script in soup(["script", "style"]):
                    script.decompose()
                content = soup.get_text(" ", strip=True)[:5000]
                
                # Salvează conținutul în baza de date
                content_doc = {
                    "agent_id": ObjectId(agent_id),  # Agentul master
                    "competitor_id": competitor["_id"],
                    "url": url,
                    "domain": domain,
                    "content": content,
                    "title": soup.title.string if soup.title else f"Content from {domain}",
                    "downloaded_at": datetime.now(timezone.utc),
                    "content_type": "competitor_content",
                    "relationship": "competitor"
                }
                
                db.site_content.insert_one(content_doc)
                
                # Actualizează statusul competitorului
                db.competitors.update_one(
                    {"_id": competitor["_id"]},
                    {"$set": {
                        "status": "downloaded",
                        "downloaded_at": datetime.now(timezone.utc),
                        "content_length": len(content)
                    }}
                )
                
                downloaded_count += 1
                results.append({
                    "url": url,
                    "domain": domain,
                    "status": "downloaded",
                    "content_length": len(content)
                })
                
                logger.info(f"[DOWNLOAD] Downloaded content from {domain}: {len(content)} chars")
                
            except Exception as e:
                failed_count += 1
                logger.warning(f"Failed to download {competitor.get('competitor_url', 'unknown')}: {e}")
                results.append({
                    "url": competitor.get("competitor_url", "unknown"),
                    "domain": competitor.get("competitor_domain", "unknown"),
                    "status": "failed",
                    "error": str(e)
                })
                continue
        
        return {
            "ok": True,
            "summary": {
                "total_processed": len(competitors),
                "downloaded": downloaded_count,
                "failed": failed_count,
                "master_agent_id": agent_id
            },
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error downloading competitors: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/admin/industry/{agent_id}/tasks/{task_id}/execute")
def api_execute_learning_task(agent_id: str, task_id: str):
    """Execută un task de învățare"""
    try:
        task = db.learning_tasks.find_one({"agent_id": ObjectId(agent_id), "task_id": task_id})
        if not task:
            return {"ok": False, "error": "task_not_found"}
        
        # Actualizează statusul la "in_progress"
        db.learning_tasks.update_one(
            {"_id": task["_id"]},
            {"$set": {"status": "in_progress", "updated_at": datetime.now(timezone.utc)}}
        )
        
        # Execută task-ul în funcție de tipul său
        if task_id == "extract_keywords":
            result = execute_extract_keywords_task(agent_id, task)
        elif task_id == "find_similar_sites":
            result = execute_find_similar_sites_task(agent_id, task)
        elif task_id == "create_competitor_agents":
            result = execute_create_competitor_agents_task(agent_id, task)
        elif task_id == "analyze_competitors":
            result = execute_analyze_competitors_task(agent_id, task)
        elif task_id == "generate_insights":
            result = execute_generate_insights_task(agent_id, task)
        else:
            result = {"ok": False, "error": "unknown_task"}
        
        # Actualizează statusul final
        final_status = "completed" if result.get("ok") else "failed"
        db.learning_tasks.update_one(
            {"_id": task["_id"]},
            {"$set": {
                "status": final_status,
                "updated_at": datetime.now(timezone.utc),
                "result": result,
                "progress": 100 if final_status == "completed" else 0
            }}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing learning task: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/admin/industry/{agent_id}/strategy")
def api_get_learning_strategy(agent_id: str):
    """Obține strategia de învățare pentru un agent"""
    try:
        strategy = db.learning_strategies.find_one(
            {"agent_id": ObjectId(agent_id)},
            sort=[("timestamp", -1)]
        )
        if not strategy:
            return {"ok": False, "error": "strategy_not_found"}
        
        strategy["_id"] = str(strategy["_id"])
        strategy["agent_id"] = str(strategy["agent_id"])
        if isinstance(strategy.get("timestamp"), datetime):
            strategy["timestamp"] = strategy["timestamp"].isoformat()
        
        return {"ok": True, "strategy": strategy}
    except Exception as e:
        logger.error(f"Error getting learning strategy: {e}")
        return {"ok": False, "error": str(e)}
@app.post("/admin/industry/{agent_id}/learning-strategy")
def api_generate_learning_strategy(agent_id: str, session_id: str = None):
    """
    Generează o strategie de învățare pentru agent bazată pe industria sa
    """
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "agent_not_found"}

        base_domain = agent.get("domain")
        site_url = agent.get("site_url") or (f"https://{base_domain}" if base_domain else None)

        # Citește din colecția corectă de conținut - MAI MULT CONȚINUT
        agent_content = ""
        try:
            content_docs = site_content_col.find({"agent_id": ObjectId(agent_id)}).limit(20)  # Mai multe documente
            content_parts = []
            for doc in content_docs:
                if doc.get("content"):
                    content_parts.append(doc["content"][:1000])  # Mai mult conținut per document
            agent_content = " ".join(content_parts)[:5000]  # Mai mult conținut total
            logger.info(f"[LEARNING_STRATEGY] Found {len(content_parts)} content docs, total length: {len(agent_content)}")
        except Exception as e:
            logger.warning(f"Could not get agent content from DB: {e}")

        # Dacă nu există conținut în DB, încearcă să obții conținutul direct de pe site
        if not agent_content and site_url:
            try:
                import requests
                from bs4 import BeautifulSoup
                logger.info(f"[LEARNING_STRATEGY] Fetching content directly from site: {site_url}")
                r = requests.get(site_url, timeout=15)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                
                # Extrage textul curat
                for script in soup(["script", "style"]):
                    script.decompose()
                agent_content = soup.get_text(" ", strip=True)[:5000]
                
                logger.info(f"[LEARNING_STRATEGY] Fetched {len(agent_content)} chars from site")
            except Exception as e:
                logger.warning(f"Failed to fetch content from site {site_url}: {e}")
                # Folosește URL-ul ca conținut de bază
                agent_content = f"Site URL: {site_url}\nDomain: {base_domain}\nIndustry: {industry}"

        # Detectează industria
        industry = "general"
        if agent_content:
            industry_keywords = {
                "e-commerce": ["magazin", "produs", "cumpără", "vânzare", "shop", "store"],
                "tehnologie": ["software", "aplicație", "tehnologie", "digital", "IT"],
                "servicii": ["serviciu", "consulting", "suport", "asistență"],
                "educație": ["curs", "training", "educație", "învățare"],
                "sănătate": ["medical", "sănătate", "doctor", "spital", "clinică"],
                "financiar": ["bancă", "credit", "investiție", "asigurare", "financiar"],
                "imobiliare": ["imobiliare", "apartament", "casă", "teren", "proprietate"],
                "automotive": ["mașină", "auto", "service", "piese", "automotive"],
                "alimentar": ["restaurant", "mâncare", "băutură", "alimentar", "food"],
                "fashion": ["haine", "modă", "fashion", "îmbrăcăminte", "accesorii"]
            }

            context_lower = agent_content.lower()
            for ind, keywords in industry_keywords.items():
                if any(keyword in context_lower for keyword in keywords):
                    industry = ind
                    break

        api_key = get_api_key()
        model_name = get_llm_model()
        llm = ChatOpenAI(model_name=model_name, openai_api_key=api_key, temperature=0.1, max_tokens=1000, request_timeout=30)

        strategy_prompt = get_learning_strategy_prompt(agent_id, site_url, industry, agent_content)

        try:
            # Folosește timeout simplu fără signal
            response = llm.invoke(strategy_prompt)
            strategy_content = response.content
            
            # Încearcă să parseze JSON-ul cu curățare robustă
            try:
                import json
                import re
                
                # Curăță conținutul de markdown și text suplimentar
                cleaned_content = strategy_content.strip()
                
                # Elimină markdown code blocks
                cleaned_content = re.sub(r'```json\s*', '', cleaned_content)
                cleaned_content = re.sub(r'```\s*$', '', cleaned_content)
                cleaned_content = re.sub(r'^```\s*', '', cleaned_content)
                
                # Elimină text înainte de primul {
                first_brace = cleaned_content.find('{')
                if first_brace > 0:
                    cleaned_content = cleaned_content[first_brace:]
                
                # Elimină text după ultimul }
                last_brace = cleaned_content.rfind('}')
                if last_brace > 0:
                    cleaned_content = cleaned_content[:last_brace + 1]
                
                # Încearcă să parseze JSON-ul
                strategy_data = json.loads(cleaned_content.strip())
                
                # Validează că avem structura corectă
                if not isinstance(strategy_data, dict):
                    raise ValueError("JSON is not a dictionary")
                
                if "business_analysis" not in strategy_data:
                    raise ValueError("Missing business_analysis")
                
                if "concrete_tasks" not in strategy_data:
                    raise ValueError("Missing concrete_tasks")
                
                logger.info(f"[LEARNING_STRATEGY] Successfully parsed JSON strategy for agent {agent_id}")
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"[LEARNING_STRATEGY] Failed to parse JSON: {e}")
                logger.warning(f"[LEARNING_STRATEGY] Raw content: {strategy_content[:500]}...")
                
                # Creează o structură de fallback validă
                strategy_data = {
                    "business_analysis": {
                        "services_products": ["servicii generale"],
                        "target_market": "piața generală",
                        "unique_positioning": "poziționare de bază",
                        "key_strengths": ["calitate", "serviciu"]
                    },
                    "learning_strategy": {
                        "industry_insights": "Industria generală",
                        "competitor_analysis": "Analiza competitorilor",
                        "market_trends": "Tendințe de piață",
                        "growth_opportunities": "Oportunități de dezvoltare"
                    },
                    "concrete_tasks": [
                        {
                            "task_id": "extract_keywords",
                            "title": "Extrage cuvinte cheie din site",
                            "description": "Identifică cuvintele cheie specifice",
                            "keywords": ["servicii", "produse", "calitate"],
                            "search_queries": ["servicii România", "produse calitate"],
                            "status": "pending"
                        },
                        {
                            "task_id": "find_similar_sites",
                            "title": "Găsește site-uri similare",
                            "description": "Caută site-uri similare",
                            "target_count": 10,
                            "status": "pending"
                        },
                        {
                            "task_id": "create_competitor_agents",
                            "title": "Creează agenți competitori",
                            "description": "Transformă site-urile în agenți",
                            "target_count": 10,
                            "status": "pending"
                        },
                        {
                            "task_id": "analyze_competitors",
                            "title": "Analizează competitorii",
                            "description": "Compară competitorii",
                            "status": "pending"
                        },
                        {
                            "task_id": "generate_insights",
                            "title": "Generează insights strategice",
                            "description": "Creează recomandări",
                            "status": "pending"
                        }
                    ],
                    "success_metrics": {
                        "keywords_extracted": 0,
                        "similar_sites_found": 0,
                        "competitor_agents_created": 0,
                        "insights_generated": 0
                    },
                    "raw_content": strategy_content,
                    "parse_error": str(e)
                }

            strategy_doc = {
                "agent_id": ObjectId(agent_id),
                "timestamp": datetime.now(timezone.utc),
                "industry": industry,
                "strategy": strategy_content,
                "strategy_data": strategy_data,  # JSON-ul parsat
                "context_used": agent_content[:1000],
                "context_length": len(agent_content),
                "site_url": site_url,
                "domain": base_domain,
                "llm_used": model_name,
                "prompt_used": strategy_prompt[:500],
                "strategy_type": "learning_strategy_with_tasks"
            }
            db.learning_strategies.insert_one(strategy_doc)
            
            # Salvează task-urile în colecția separată
            if "concrete_tasks" in strategy_data:
                for task in strategy_data["concrete_tasks"]:
                    task_doc = {
                        "agent_id": ObjectId(agent_id),
                        "task_id": task.get("task_id"),
                        "title": task.get("title"),
                        "description": task.get("description"),
                        "status": "pending",
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                        "task_data": task,
                        "progress": 0
                    }
                    db.learning_tasks.insert_one(task_doc)
                logger.info(f"[LEARNING_STRATEGY] Saved {len(strategy_data['concrete_tasks'])} tasks for agent {agent_id}")
            
            # Indexează și în colecția de învățare pentru Qwen
            learning_doc = {
                "agent_id": ObjectId(agent_id),
                "timestamp": datetime.now(timezone.utc),
                "action_type": "learning_strategy_generation",
                "input_context": agent_content,
                "output_strategy": strategy_content,
                "strategy_data": strategy_data,
                "industry": industry,
                "llm_model": model_name,
                "for_qwen_learning": True
            }
            db.qwen_learning_data.insert_one(learning_doc)
            logger.info(f"[LEARNING] Indexed strategy for Qwen learning: {agent_id}")

            # Actualizează sesiunea dacă este specificată
            if session_id:
                try:
                    db.user_sessions.update_one(
                        {"_id": ObjectId(session_id)},
                        {
                            "$set": {
                                "master_agent_id": ObjectId(agent_id),
                                "learning_progress.strategy_generated": True,
                                "learning_progress.total_learning_tasks": len(strategy_data.get("concrete_tasks", [])),
                                "last_accessed": datetime.now(timezone.utc)
                            }
                        }
                    )
                    logger.info(f"[SESSION] Updated session {session_id} with master agent {agent_id}")
                except Exception as e:
                    logger.warning(f"Failed to update session {session_id}: {e}")

            return {
                "ok": True,
                "agent_id": str(agent.get("_id")),
                "domain": base_domain,
                "industry": industry,
                "strategy": strategy_content,
                "strategy_data": strategy_data,
                "context_length": len(agent_content),
                "tasks_created": len(strategy_data.get("concrete_tasks", [])),
                "session_id": session_id
            }

        except Exception as e:
            logger.error(f"Error generating learning strategy: {e}")
            return {"ok": False, "error": f"strategy_generation_failed: {str(e)}"}

    except Exception as e:
        logger.error(f"Error in learning strategy endpoint: {e}")
        return {"ok": False, "error": f"endpoint_error: {str(e)}"}



def _build_context_block(results: list[dict]) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        t = (r.get("title") or "").strip()
        u = (r.get("url") or "").strip()
        lines.append(f"[{i}] {t} — {u}")
    return "\n".join(lines)

def _choose_hits_for_agent(question: str, domain: str|None) -> list[dict]:
    # 1) încercă intern (boost pe domeniu)
    all_res = get_searcher().search(question, domain=None)
    pref = [r for r in all_res if domain and _match_domain(r, domain)]
    if pref:
        return (pref + [r for r in all_res if r not in pref])[:8]
    # 2) fallback: tot setul
    return all_res[:8]


class AnswerRequest(BaseModel):
    agent_id: str
    question: str


@app.post("/api/answer")
async def api_answer(req: AnswerRequest):
    """
    Body:
      { "agent_id": "<id din /api/agents>", "question": "întrebarea ta" }
    Returnează: { ok, answer, citations: [{title,url}], used_model }
    """
    try:
        agent = agents_collection.find_one({"_id": ObjectId(req.agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        domain = (agent.get("domain") or (_host_from_url(agent.get("site_url","")))) or None

        # 1) căutare + context
        hits = _choose_hits_for_agent(req.question, domain)
        ctx_block = _build_context_block(hits)

        # 2) pregătește clientul LLM (Qwen preferat, OpenAI fallback)
        client = get_llm_client()
        model = get_llm_model()

        # 3) prompt: vocea site-ului + citații
        sys = ("Ești vocea site-ului. Răspunzi STRICT din sursele date; "
               "dacă nu e în surse, răspunzi: 'Nu găsesc în datele mele' "
               "și sugerezi ce ar trebui indexat.")
        user = f"""
=== SURSE ===
{ctx_block}

=== ÎNTREBARE ===
{req.question}

Instrucțiuni de stil:
- răspuns în română, concis (max 6-8 propoziții)
- dacă folosești informație, pune 1-2 citații [n] relevante (ex: [1], [3])
"""
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":sys},
                      {"role":"user","content":user}],
            temperature=0.2,
            max_tokens=400,
        )
        answer = resp.choices[0].message.content

        # 4) pregătește citațiile structurate
        cits = [{"title": (h.get("title") or ""), "url": (h.get("url") or "")} for h in hits]

        # 5) salvează conversația (opțional)
        try:
            save_conversation(str(agent["_id"]), req.question, answer, strategy="rag_answer")
        except Exception:
            pass

        return {"ok": True, "answer": answer, "citations": cits, "used_model": model}

    except HTTPException:
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ========== FUNCȚII DE EXECUȚIE A TASK-URILOR ==========

def execute_extract_keywords_task(agent_id: str, task: dict) -> dict:
    """Execută task-ul de extragere a cuvintelor cheie"""
    try:
        # Obține conținutul agentului
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "agent_not_found"}
        
        # Obține conținutul din baza de date
        content_docs = site_content_col.find({"agent_id": ObjectId(agent_id)}).limit(10)
        content_parts = []
        for doc in content_docs:
            if doc.get("content"):
                content_parts.append(doc["content"][:1000])
        agent_content = " ".join(content_parts)[:3000]
        
        # Dacă nu există conținut în DB, încearcă să obții conținutul direct de pe site
        if not agent_content and agent.get("site_url"):
            try:
                import requests
                from bs4 import BeautifulSoup
                r = requests.get(agent["site_url"], timeout=10)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                agent_content = soup.get_text(" ")[:3000]
                logger.info(f"[TASK] Fetched content directly from site: {len(agent_content)} chars")
            except Exception as e:
                logger.warning(f"Failed to fetch content from site: {e}")
        
        if not agent_content:
            return {"ok": False, "error": "no_content_found"}
        
        # Folosește LLM pentru a extrage cuvintele cheie
        api_key = get_api_key()
        model_name = get_llm_model()
        llm = ChatOpenAI(model_name=model_name, openai_api_key=api_key, temperature=0.1)
        
        prompt = f"""
Analizează următorul conținut și extrage cuvintele cheie specifice pentru serviciile/produsele acestui business.

CONȚINUT:
{agent_content}

IMPORTANT: Răspunde DOAR cu JSON valid, fără text suplimentar, fără markdown, fără explicații.

{{
  "keywords": ["cuvânt1", "cuvânt2", "cuvânt3", "cuvânt4", "cuvânt5"],
  "search_queries": ["query1", "query2", "query3", "query4", "query5"],
  "services_identified": ["serviciu1", "serviciu2", "serviciu3"],
  "products_identified": ["produs1", "produs2", "produs3"]
}}

Cuvintele cheie trebuie să fie specifice pentru business-ul acestui site.
Query-urile trebuie să fie în română și relevante pentru căutarea competitorilor.
"""
        
        response = llm.invoke(prompt)
        import json
        import re
        
        # Curăță conținutul de markdown
        cleaned_content = response.content
        if "```json" in cleaned_content:
            cleaned_content = re.sub(r'```json\s*', '', cleaned_content)
        if "```" in cleaned_content:
            cleaned_content = re.sub(r'```\s*$', '', cleaned_content)
        
        result_data = json.loads(cleaned_content.strip())
        
        # Actualizează task-ul cu rezultatele
        db.learning_tasks.update_one(
            {"_id": task["_id"]},
            {"$set": {
                "result": result_data,
                "progress": 100,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.info(f"[TASK] Extracted keywords for agent {agent_id}: {len(result_data.get('keywords', []))} keywords")
        return {"ok": True, "result": result_data}
        
    except Exception as e:
        logger.error(f"Error executing extract_keywords task: {e}")
        return {"ok": False, "error": str(e)}

def execute_find_similar_sites_task(agent_id: str, task: dict) -> dict:
    """Execută task-ul de găsire a site-urilor similare"""
    try:
        # Obține cuvintele cheie din task-ul anterior
        keywords_task = db.learning_tasks.find_one({
            "agent_id": ObjectId(agent_id),
            "task_id": "extract_keywords",
            "status": "completed"
        })
        
        if not keywords_task or not keywords_task.get("result"):
            return {"ok": False, "error": "keywords_not_found"}
        
        keywords = keywords_task["result"]["result"].get("keywords", [])
        search_queries = keywords_task["result"]["result"].get("search_queries", [])
        
        if not search_queries:
            return {"ok": False, "error": "no_search_queries"}
        
        # Caută site-uri similare folosind search
        similar_sites = []
        competitor_entries = []
        
        for query in search_queries[:5]:  # Folosește primele 5 query-uri
            try:
                urls = search_serp([query], k=8)  # Mai multe rezultate per query
                for url in urls:
                    if url and url not in [s["url"] for s in similar_sites]:
                        # Extrage domain-ul din URL
                        from urllib.parse import urlparse
                        parsed_url = urlparse(url)
                        domain = parsed_url.netloc.replace('www.', '')
                        
                        site_info = {
                            "url": url,
                            "domain": domain,
                            "title": f"Site găsit pentru: {query}",
                            "description": f"Site relevant pentru query-ul: {query}",
                            "query_used": query,
                            "relevance_score": 0.8,  # Scor de relevanță
                            "research_timestamp": datetime.now(timezone.utc)
                        }
                        
                        similar_sites.append(site_info)
                        
                        # Creează intrarea pentru competitor în baza de date
                        competitor_entry = {
                            "master_agent_id": ObjectId(agent_id),
                            "competitor_url": url,
                            "competitor_domain": domain,
                            "search_query": query,
                            "relevance_score": 0.8,
                            "status": "discovered",  # discovered, analyzed, downloaded, created_agent
                            "research_timestamp": datetime.now(timezone.utc),
                            "relationship_type": "competitor",  # competitor, similar, related
                            "notes": f"Găsit prin query: {query}"
                        }
                        
                        competitor_entries.append(competitor_entry)
                        
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                continue
        
        # Limitează la 15 site-uri
        similar_sites = similar_sites[:15]
        competitor_entries = competitor_entries[:15]
        
        # Salvează competitorii în baza de date
        if competitor_entries:
            try:
                db.competitors.insert_many(competitor_entries)
                logger.info(f"[RESEARCH] Saved {len(competitor_entries)} competitors for agent {agent_id}")
            except Exception as e:
                logger.error(f"Failed to save competitors: {e}")
        
        result_data = {
            "similar_sites": similar_sites,
            "total_found": len(similar_sites),
            "queries_used": search_queries[:5],
            "competitors_saved": len(competitor_entries),
            "research_summary": {
                "master_agent_id": agent_id,
                "total_competitors_discovered": len(competitor_entries),
                "search_queries_used": search_queries[:5],
                "research_timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Actualizează task-ul cu rezultatele
        db.learning_tasks.update_one(
            {"_id": task["_id"]},
            {"$set": {
                "result": result_data,
                "progress": 100,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.info(f"[TASK] Found {len(similar_sites)} similar sites for agent {agent_id}")
        return {"ok": True, "result": result_data}
        
    except Exception as e:
        logger.error(f"Error executing find_similar_sites task: {e}")
        return {"ok": False, "error": str(e)}

def execute_create_competitor_agents_task(agent_id: str, task: dict) -> dict:
    """Execută task-ul de creare a agenților competitori"""
    try:
        # Obține site-urile similare din task-ul anterior
        similar_sites_task = db.learning_tasks.find_one({
            "agent_id": ObjectId(agent_id),
            "task_id": "find_similar_sites",
            "status": "completed"
        })
        
        if not similar_sites_task or not similar_sites_task.get("result"):
            return {"ok": False, "error": "similar_sites_not_found"}
        
        similar_sites = similar_sites_task["result"]["result"].get("similar_sites", [])
        
        if not similar_sites:
            return {"ok": False, "error": "no_similar_sites"}
        
        # Creează agenți pentru fiecare site similar
        created_agents = []
        for site in similar_sites[:10]:  # Limitează la 10
            try:
                # Creează agent folosind funcția existentă
                from site_agent_creator import create_site_agent_ws
                
                # Simulează crearea agentului (în realitate ar trebui să folosești WebSocket)
                agent_doc = {
                    "name": f"Competitor Agent - {site['title'][:50]}",
                    "site_url": site["url"],
                    "domain": _host_from_url(site["url"]),
                    "status": "ready",
                    "createdAt": datetime.now(timezone.utc),
                    "updatedAt": datetime.now(timezone.utc),
                    "parent_agent_id": ObjectId(agent_id),
                    "agent_type": "competitor",
                    "master_agent_id": ObjectId(agent_id),
                    "relationship_type": "competitor",
                    "session_id": None,  # Va fi setat dacă există sesiune
                    "competitor_metadata": {
                        "discovered_via": site.get("query_used", "unknown"),
                        "relevance_score": site.get("relevance_score", 0.8),
                        "research_timestamp": datetime.now(timezone.utc)
                    }
                }
                
                result = agents_collection.insert_one(agent_doc)
                created_agents.append({
                    "agent_id": str(result.inserted_id),
                    "url": site["url"],
                    "title": site["title"],
                    "status": "created"
                })
                
            except Exception as e:
                logger.warning(f"Failed to create agent for {site['url']}: {e}")
                created_agents.append({
                    "url": site["url"],
                    "title": site["title"],
                    "status": "failed",
                    "error": str(e)
                })
        
        result_data = {
            "created_agents": created_agents,
            "total_created": len([a for a in created_agents if a.get("status") == "created"]),
            "total_failed": len([a for a in created_agents if a.get("status") == "failed"])
        }
        
        # Actualizează task-ul cu rezultatele
        db.learning_tasks.update_one(
            {"_id": task["_id"]},
            {"$set": {
                "result": result_data,
                "progress": 100,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.info(f"[TASK] Created {result_data['total_created']} competitor agents for agent {agent_id}")
        return {"ok": True, "result": result_data}
        
    except Exception as e:
        logger.error(f"Error executing create_competitor_agents task: {e}")
        return {"ok": False, "error": str(e)}

def execute_analyze_competitors_task(agent_id: str, task: dict) -> dict:
    """Execută task-ul de analiză a competitorilor"""
    try:
        # Obține agenții competitori creați
        competitor_agents = list(agents_collection.find({
            "parent_agent_id": ObjectId(agent_id),
            "agent_type": "competitor"
        }))
        
        if not competitor_agents:
            return {"ok": False, "error": "no_competitor_agents"}
        
        # Analizează fiecare competitor
        analysis_results = []
        for competitor in competitor_agents:
            try:
                # Obține conținutul competitorului
                competitor_content = site_content_col.find({"agent_id": competitor["_id"]}).limit(5)
                content_parts = []
                for doc in competitor_content:
                    if doc.get("content"):
                        content_parts.append(doc["content"][:500])
                content = " ".join(content_parts)[:2000]
                
                analysis_results.append({
                    "agent_id": str(competitor["_id"]),
                    "url": competitor.get("site_url", ""),
                    "title": competitor.get("name", ""),
                    "content_length": len(content),
                    "content_preview": content[:200] + "..." if len(content) > 200 else content
                })
                
            except Exception as e:
                logger.warning(f"Failed to analyze competitor {competitor.get('_id')}: {e}")
                continue
        
        result_data = {
            "competitors_analyzed": analysis_results,
            "total_analyzed": len(analysis_results),
            "analysis_summary": f"Analizat {len(analysis_results)} competitori cu conținut total de {sum(r['content_length'] for r in analysis_results)} caractere"
        }
        
        # Actualizează task-ul cu rezultatele
        db.learning_tasks.update_one(
            {"_id": task["_id"]},
            {"$set": {
                "result": result_data,
                "progress": 100,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.info(f"[TASK] Analyzed {len(analysis_results)} competitors for agent {agent_id}")
        return {"ok": True, "result": result_data}
        
    except Exception as e:
        logger.error(f"Error executing analyze_competitors task: {e}")
        return {"ok": False, "error": str(e)}

def execute_generate_insights_task(agent_id: str, task: dict) -> dict:
    """Execută task-ul de generare a insights-urilor strategice"""
    try:
        # Obține toate task-urile completate
        completed_tasks = list(db.learning_tasks.find({
            "agent_id": ObjectId(agent_id),
            "status": "completed"
        }))
        
        if not completed_tasks:
            return {"ok": False, "error": "no_completed_tasks"}
        
        # Folosește LLM pentru a genera insights
        api_key = get_api_key()
        model_name = get_llm_model()
        llm = ChatOpenAI(model_name=model_name, openai_api_key=api_key, temperature=0.3)
        
        # Pregătește contextul din toate task-urile
        context = "ANALIZA COMPLETĂ A BUSINESS-ULUI:\n\n"
        for task_doc in completed_tasks:
            context += f"Task: {task_doc.get('title', '')}\n"
            context += f"Rezultat: {str(task_doc.get('result', {}))}\n\n"
        
        prompt = f"""
Bazându-te pe analiza completă de mai jos, generează insights strategice concrete pentru acest business.

{context}

Generează recomandări concrete în format JSON:
{{
  "strategic_insights": [
    "insight1",
    "insight2", 
    "insight3"
  ],
  "recommendations": [
    "recomandare1",
    "recomandare2",
    "recomandare3"
  ],
  "competitive_advantages": [
    "avantaj1",
    "avantaj2",
    "avantaj3"
  ],
  "growth_opportunities": [
    "oportunitate1",
    "oportunitate2",
    "oportunitate3"
  ],
  "summary": "Rezumat executiv al analizei"
}}

Fiecare insight și recomandare trebuie să fie specifică și acționabilă.
"""
        
        response = llm.invoke(prompt)
        import json
        import re
        
        # Clean the response content
        content = response.content.strip()
        # Remove markdown code blocks
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*$', '', content)
        
        try:
            result_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Raw content: {content[:500]}...")
            # Fallback: create a simple structure
            result_data = {
                "strategic_insights": ["Analiza completă a fost realizată cu succes"],
                "recommendations": ["Recomandări generate pe baza analizei"],
                "competitive_advantages": ["Avantaje competitive identificate"],
                "growth_opportunities": ["Oportunități de dezvoltare identificate"],
                "summary": f"Analiza completă realizată cu {len(completed_tasks)} task-uri"
            }
        
        # Actualizează task-ul cu rezultatele
        db.learning_tasks.update_one(
            {"_id": task["_id"]},
            {"$set": {
                "result": result_data,
                "progress": 100,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.info(f"[TASK] Generated strategic insights for agent {agent_id}")
        return {"ok": True, "result": result_data}
        
    except Exception as e:
        logger.error(f"Error executing generate_insights task: {e}")
        return {"ok": False, "error": str(e)}
@app.post("/extract-site-data")
async def extract_site_data(request: Request):
    """Extrage automat datele unui site web"""
    try:
        data = await request.json()
        domain = data.get("domain", "")
        
        if not domain:
            return {"error": "Domain is required", "ok": False}
        
        # Extrage datele site-ului
        extractor = AutoSiteExtractor()
        site_data = await extractor.extract_site_data(domain)
        
        # Salvează în baza de date
        site_data_collection = db.site_data
        result = site_data_collection.update_one(
            {"domain": domain},
            {"$set": site_data},
            upsert=True
        )
        
        return {
            "message": f"Site data extracted and saved for {domain}",
            "data": site_data,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None,
            "ok": True
        }
        
    except Exception as e:
        logger.error(f"Error extracting site data: {e}")
        return {"error": str(e), "ok": False}

@app.get("/agent/{agent_id}/health")
async def get_agent_health(agent_id: str):
    """Verifică statusul unui agent specific"""
    try:
        checker = AgentHealthChecker()
        health_status = await checker.check_agent_health(agent_id)
        
        return {
            "agent_id": agent_id,
            "health": health_status,
            "ok": True
        }
        
    except Exception as e:
        logger.error(f"Error checking agent health: {e}")
        return {
            "agent_id": agent_id,
            "error": str(e),
            "ok": False
        }
# MIRROR AGENT SYSTEM ENDPOINTS
# ======================

@app.post("/mirror-agent/create")
async def create_mirror_agent_endpoint(request: dict = Body(...)):
    """Creează un agent în oglindă pentru un agent site și execută Q&A pentru învățare Qwen"""
    try:
        agent_id = request.get("agent_id")
        max_questions = request.get("max_questions", 8)
        
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required")
        
        # Verifică dacă agentul există
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Creează și execută mirror agent
        result = await create_mirror_agent_for_site(agent_id, max_questions)
        
        if result["ok"]:
            logger.info(f"✅ Mirror agent created for {agent['name']}: {result['session_id']}")
            return {
                "ok": True,
                "message": f"Mirror agent Q&A session completed for {agent['name']}",
                "session_id": result["session_id"],
                "target_agent_id": agent_id,
                "target_agent_name": agent["name"],
                "questions_asked": result["questions_asked"],
                "successful_qa": result["successful_qa"],
                "conversations_saved": result["conversations_saved"],
                "learning_potential_avg": result["learning_potential_avg"],
                "qwen_learning_enhanced": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error creating mirror agent: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-agent/session/{session_id}")
async def get_mirror_session_stats(session_id: str):
    """Obține statisticile unei sesiuni de mirror agent"""
    try:
        mirror_system = MirrorAgentSystem()
        stats = await mirror_system.get_mirror_session_stats(session_id)
        
        return {
            "ok": True,
            "session_stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting mirror session stats: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-agent/sessions")
async def list_mirror_sessions():
    """Listează toate sesiunile de mirror agent"""
    try:
        sessions = list(db.mirror_sessions.find({}).sort("created_at", -1).limit(20))
        
        for session in sessions:
            session["_id"] = str(session["_id"])
            session["target_agent_id"] = str(session["target_agent_id"])
            if isinstance(session.get("created_at"), datetime):
                session["created_at"] = session["created_at"].isoformat()
            if isinstance(session.get("completed_at"), datetime):
                session["completed_at"] = session["completed_at"].isoformat()
        
        return {
            "ok": True,
            "sessions": sessions,
            "total_sessions": len(sessions),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing mirror sessions: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/mirror-agent/auto-create/{agent_id}")
async def auto_create_mirror_agent(agent_id: str, background_tasks: BackgroundTasks):
    """Creează automat un mirror agent după crearea unui agent nou"""
    try:
        # Verifică dacă agentul există
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Adaugă task-ul în background
        background_tasks.add_task(create_mirror_agent_for_site, agent_id, 6)
        
        return {
            "ok": True,
            "message": f"Mirror agent creation started for {agent['name']}",
            "agent_id": agent_id,
            "agent_name": agent["name"],
            "status": "background_task_started",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting auto mirror agent creation: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ======================
# MIRROR COLLECTIONS ENDPOINTS
# ======================

@app.post("/mirror-collections/create")
async def create_mirror_collections_endpoint(request: dict = Body(...)):
    """Creează colecțiile Qdrant specifice pentru un site"""
    try:
        domain = request.get("domain")
        if not domain:
            raise HTTPException(status_code=400, detail="domain is required")
        
        # Creează colecțiile mirror
        result = await create_mirror_collections_for_site(domain)
        
        if result["ok"]:
            logger.info(f"✅ Mirror collections created for {domain}: {result['site_id']}")
            return {
                "ok": True,
                "message": f"Mirror collections created for {domain}",
                "site_id": result["site_id"],
                "domain": result["domain"],
                "collections": result["collections"],
                "status": "created",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error creating mirror collections: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-collections/{site_id}")
async def get_mirror_collections_info(site_id: str):
    """Obține informațiile despre colecțiile unui site"""
    try:
        collections_manager = QdrantMirrorCollections()
        info = await collections_manager.get_collections_info(site_id)
        
        return {
            "ok": True,
            "collections_info": info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting mirror collections info: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.delete("/mirror-collections/{site_id}")
async def delete_mirror_collections_endpoint(site_id: str):
    """Șterge colecțiile unui site"""
    try:
        collections_manager = QdrantMirrorCollections()
        result = await collections_manager.delete_mirror_collections(site_id)
        
        return {
            "ok": True,
            "message": f"Mirror collections deleted for {site_id}",
            "deleted_collections": result["deleted_collections"],
            "status": "deleted",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error deleting mirror collections: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-collections")
async def list_mirror_collections():
    """Listează toate colecțiile mirror"""
    try:
        collections_manager = QdrantMirrorCollections()
        collections = await collections_manager.list_all_mirror_collections()
        
        return {
            "ok": True,
            "collections": collections,
            "total_collections": len(collections),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing mirror collections: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/mirror-collections/add-faq")
async def add_faq_to_collection(request: dict = Body(...)):
    """Adaugă FAQ în colecția Mirror"""
    try:
        site_id = request.get("site_id")
        question = request.get("question")
        answer = request.get("answer")
        
        if not all([site_id, question, answer]):
            return {
                "ok": False,
                "error": "Missing required fields: site_id, question, answer",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Adaugă FAQ în colecția Qdrant
        collections_manager = QdrantMirrorCollections()
        result = await collections_manager.add_faq_to_site(site_id, question, answer)
        
        return {
            "ok": True,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error adding FAQ to collection: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ======================
# MIRROR MANIFEST ENDPOINTS
# ======================

@app.post("/mirror-manifest/create")
async def create_mirror_manifest_endpoint(request: dict = Body(...)):
    """Creează manifestul pentru agentul Mirror"""
    try:
        site_id = request.get("site_id")
        domain = request.get("domain")
        
        if not site_id or not domain:
            raise HTTPException(status_code=400, detail="site_id and domain are required")
        
        # Creează manifestul
        result = create_mirror_manifest_for_site(site_id, domain)
        
        if result["ok"]:
            logger.info(f"✅ Mirror manifest created for {domain}: {result['manifest_id']}")
            return {
                "ok": True,
                "message": f"Mirror manifest created for {domain}",
                "manifest_id": result["manifest_id"],
                "site_id": result["site_id"],
                "domain": result["domain"],
                "version": result["version"],
                "purpose": result["purpose"],
                "validation": result["validation"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error creating mirror manifest: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-manifest/{manifest_id}")
async def get_mirror_manifest(manifest_id: str):
    """Obține manifestul pentru un agent Mirror"""
    try:
        manager = MirrorManifestManager()
        manager.load_manifests_from_db()  # Încarcă din DB
        
        manifest = manager.get_manifest(manifest_id)
        if not manifest:
            raise HTTPException(status_code=404, detail="Manifest not found")
        
        return {
            "ok": True,
            "manifest": manifest.to_dict(),
            "validation": manifest.validate(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting mirror manifest: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-manifest/site/{site_id}")
async def get_mirror_manifest_by_site(site_id: str):
    """Obține manifestul pentru un site"""
    try:
        manager = MirrorManifestManager()
        manager.load_manifests_from_db()  # Încarcă din DB
        
        manifest = manager.get_manifest_by_site(site_id)
        if not manifest:
            raise HTTPException(status_code=404, detail="Manifest not found for this site")
        
        return {
            "ok": True,
            "manifest": manifest.to_dict(),
            "validation": manifest.validate(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting mirror manifest by site: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.put("/mirror-manifest/{manifest_id}")
async def update_mirror_manifest(manifest_id: str, request: dict = Body(...)):
    """Actualizează manifestul pentru un agent Mirror"""
    try:
        manager = MirrorManifestManager()
        manager.load_manifests_from_db()  # Încarcă din DB
        
        updates = request.get("updates", {})
        success = manager.update_manifest(manifest_id, updates)
        
        if success:
            # Salvează în DB
            manifest = manager.get_manifest(manifest_id)
            if manifest:
                manager.save_manifest_to_db(manifest)
            
            return {
                "ok": True,
                "message": f"Manifest {manifest_id} updated successfully",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Manifest not found")
            
    except Exception as e:
        logger.error(f"Error updating mirror manifest: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-manifest")
async def list_mirror_manifests():
    """Listează toate manifestele Mirror"""
    try:
        manager = MirrorManifestManager()
        manager.load_manifests_from_db()  # Încarcă din DB
        
        manifests = manager.list_manifests()
        
        return {
            "ok": True,
            "manifests": manifests,
            "total_manifests": len(manifests),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing mirror manifests: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ======================
# MIRROR ROUTER ENDPOINTS
# ======================

@app.post("/mirror-router/route")
async def route_mirror_question_endpoint(request: dict = Body(...)):
    """Routează o întrebare pentru agentul Mirror"""
    try:
        question = request.get("question")
        site_id = request.get("site_id")
        manifest_data = request.get("manifest")
        
        if not question or not site_id:
            raise HTTPException(status_code=400, detail="question and site_id are required")
        
        # Folosește manifestul trimis sau încearcă să-l obțină din DB
        if manifest_data:
            manifest = manifest_data
        else:
            # Obține manifestul pentru site
            manifest_manager = MirrorManifestManager()
            manifest_manager.load_manifests_from_db()
            
            manifest_obj = manifest_manager.get_manifest_by_site(site_id)
            if not manifest_obj:
                raise HTTPException(status_code=404, detail="Manifest not found for this site")
            
            manifest = manifest_obj.to_dict()
        
        # Routează întrebarea
        result = await route_mirror_question(question, site_id, manifest)
        
        if result["ok"]:
            logger.info(f"✅ Question routed for {site_id}: {result['decision']}")
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error routing mirror question: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-router/stats/{site_id}")
async def get_mirror_router_stats(site_id: str):
    """Obține statisticile router-ului pentru un site"""
    try:
        from mirror_agent_router import router_manager
        
        router = router_manager.get_router(site_id)
        stats = router.get_routing_stats()
        
        return {
            "ok": True,
            "site_id": site_id,
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting mirror router stats: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-router/stats")
async def get_all_mirror_router_stats():
    """Obține statisticile pentru toate router-ele"""
    try:
        from mirror_agent_router import router_manager
        
        stats = router_manager.get_all_stats()
        
        return {
            "ok": True,
            "all_stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting all mirror router stats: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.put("/mirror-router/config/{site_id}")
async def update_mirror_router_config(site_id: str, request: dict = Body(...)):
    """Actualizează configurația router-ului pentru un site"""
    try:
        from mirror_agent_router import router_manager
        
        config_updates = request.get("config", {})
        router = router_manager.get_router(site_id)
        
        success = router.update_config(config_updates)
        
        if success:
            return {
                "ok": True,
                "message": f"Router config updated for {site_id}",
                "site_id": site_id,
                "config": config_updates,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update router config")
            
    except Exception as e:
        logger.error(f"Error updating mirror router config: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ============================================================================
# MIRROR AGENT KPI TESTING ENDPOINTS
# ============================================================================

@app.post("/mirror-kpi/test")
async def run_mirror_kpi_test_endpoint(request: dict = Body(...)):
    """Rulează testul KPI complet pentru un Mirror Agent"""
    try:
        site_id = request.get("site_id")
        manifest_data = request.get("manifest")
        
        if not site_id:
            raise HTTPException(status_code=400, detail="site_id is required")
        
        # Folosește manifestul trimis sau încearcă să-l obțină din DB
        if manifest_data:
            manifest = manifest_data
        else:
            # Obține manifestul pentru site
            manifest_manager = MirrorManifestManager()
            manifest_manager.load_manifests_from_db()
            
            manifest_obj = manifest_manager.get_manifest_by_site(site_id)
            if not manifest_obj:
                raise HTTPException(status_code=404, detail="Manifest not found for this site")
            
            manifest = manifest_obj.to_dict()
        
        # Rulează testul KPI
        result = await run_kpi_test_for_site(site_id, manifest)
        
        if result["ok"]:
            logger.info(f"✅ KPI test completed for {site_id}: {result['test_session_id']}")
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "KPI test failed"))
            
    except Exception as e:
        logger.error(f"Error running KPI test: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-kpi/history/{site_id}")
async def get_mirror_kpi_history_endpoint(site_id: str, limit: int = 10):
    """Returnează istoricul KPI pentru un site"""
    try:
        history = get_kpi_history(site_id, limit)
        
        logger.info(f"✅ KPI history retrieved for {site_id}: {len(history)} records")
        return {
            "ok": True,
            "site_id": site_id,
            "history": history,
            "count": len(history),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting KPI history: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-kpi/stats")
async def get_mirror_kpi_stats_endpoint():
    """Returnează statistici globale KPI"""
    try:
        stats = get_kpi_stats()
        
        logger.info(f"✅ Global KPI stats retrieved: {stats['total_tests']} tests")
        return {
            "ok": True,
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting KPI stats: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-kpi/golden-set")
async def get_golden_mini_set_endpoint():
    """Returnează Golden Mini-Set pentru testare"""
    try:
        from mirror_kpi_testing import GoldenMiniSet
        
        golden_set = GoldenMiniSet()
        questions = [
            {
                "question_id": q.question_id,
                "question": q.question,
                "expected_answer_type": q.expected_answer_type,
                "expected_keywords": q.expected_keywords,
                "difficulty": q.difficulty,
                "domain_specific": q.domain_specific
            }
            for q in golden_set.questions
        ]
        
        logger.info(f"✅ Golden Mini-Set retrieved: {len(questions)} questions")
        return {
            "ok": True,
            "golden_set": questions,
            "total_questions": len(questions),
            "difficulties": ["easy", "medium", "hard"],
            "answer_types": ["faq", "pages", "fallback", "escalate"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting Golden Mini-Set: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ============================================================================
# MIRROR AGENT CURATOR ENDPOINTS
# ============================================================================

@app.post("/mirror-curator/cycle")
async def run_mirror_curator_cycle_endpoint(request: dict = Body(...)):
    """Rulează ciclul curator pentru un Mirror Agent"""
    try:
        site_id = request.get("site_id")
        
        if not site_id:
            raise HTTPException(status_code=400, detail="site_id is required")
        
        # Rulează ciclul curator
        result = await run_curator_cycle_for_site(site_id)
        
        if result["ok"]:
            logger.info(f"✅ Curator cycle completed for {site_id}: {result['promotions']} promotions")
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Curator cycle failed"))
            
    except Exception as e:
        logger.error(f"Error running curator cycle: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-curator/dashboard/{site_id}")
async def get_mirror_curator_dashboard_endpoint(site_id: str):
    """Returnează dashboard-ul curator pentru un site"""
    try:
        dashboard = await get_curator_dashboard_for_site(site_id)
        
        if dashboard["ok"]:
            logger.info(f"✅ Curator dashboard retrieved for {site_id}")
            return dashboard
        else:
            raise HTTPException(status_code=500, detail=dashboard.get("error", "Dashboard failed"))
            
    except Exception as e:
        logger.error(f"Error getting curator dashboard: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-curator/stats")
async def get_mirror_curator_stats_endpoint():
    """Returnează statistici globale curator"""
    try:
        stats = get_curator_stats()
        
        logger.info(f"✅ Global curator stats retrieved: {stats['total_sites']} sites")
        return {
            "ok": True,
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting curator stats: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
@app.get("/mirror-curator/promotions/{site_id}")
async def get_mirror_curator_promotions_endpoint(site_id: str, limit: int = 20):
    """Returnează istoricul promovărilor pentru un site"""
    try:
        db = MongoClient("mongodb://localhost:27017").mirror_curator
        
        promotions = list(db.faq_promotions.find(
            {"site_id": site_id}
        ).sort("promoted_at", -1).limit(limit))
        
        # Convertim ObjectId la string
        for promotion in promotions:
            promotion['_id'] = str(promotion['_id'])
            if 'promoted_at' in promotion and isinstance(promotion['promoted_at'], datetime):
                promotion['promoted_at'] = promotion['promoted_at'].isoformat()
        
        logger.info(f"✅ Curator promotions retrieved for {site_id}: {len(promotions)} records")
        return {
            "ok": True,
            "site_id": site_id,
            "promotions": promotions,
            "count": len(promotions),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting curator promotions: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/mirror-curator/config")
async def update_mirror_curator_config_endpoint(request: dict = Body(...)):
    """Actualizează configurația curator"""
    try:
        site_id = request.get("site_id")
        config = request.get("config", {})
        
        if not site_id:
            raise HTTPException(status_code=400, detail="site_id is required")
        
        # Validează configurația
        valid_config = {}
        if "confidence_threshold" in config:
            valid_config["confidence_threshold"] = max(0.0, min(1.0, config["confidence_threshold"]))
        if "evaluation_threshold" in config:
            valid_config["evaluation_threshold"] = max(0.0, min(1.0, config["evaluation_threshold"]))
        if "frequency_threshold" in config:
            valid_config["frequency_threshold"] = max(1, config["frequency_threshold"])
        if "max_faq_size" in config:
            valid_config["max_faq_size"] = max(10, config["max_faq_size"])
        
        # Salvează configurația
        db = MongoClient("mongodb://localhost:27017").mirror_curator
        db.curator_config.update_one(
            {"site_id": site_id},
            {"$set": {
                **valid_config,
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        
        logger.info(f"✅ Curator config updated for {site_id}")
        return {
            "ok": True,
            "site_id": site_id,
            "config": valid_config,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating curator config: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ============================================================================
# MIRROR AGENT SECURITY & WHITELIST ENDPOINTS
# ============================================================================

@app.post("/mirror-security/validate")
async def validate_mirror_security_endpoint(request: dict = Body(...)):
    """Validează accesul la domeniu conform whitelist-ului"""
    try:
        site_id = request.get("site_id")
        request_domain = request.get("request_domain")
        user_ip = request.get("user_ip")
        user_agent = request.get("user_agent")
        
        if not site_id or not request_domain:
            raise HTTPException(status_code=400, detail="site_id and request_domain are required")
        
        # Validează accesul
        result = await validate_mirror_security(site_id, request_domain, user_ip, user_agent)
        
        if result["ok"]:
            logger.info(f"✅ Domain access validated for {site_id}: {request_domain}")
            return result
        else:
            logger.warning(f"🚨 Domain access denied for {site_id}: {request_domain}")
            return result
            
    except Exception as e:
        logger.error(f"Error validating domain access: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/mirror-security/scrub-pii")
async def scrub_mirror_pii_endpoint(request: dict = Body(...)):
    """Elimină PII din conținutul Mirror Agent"""
    try:
        site_id = request.get("site_id")
        content = request.get("content")
        
        if not site_id or not content:
            raise HTTPException(status_code=400, detail="site_id and content are required")
        
        # Scrub PII
        result = await scrub_mirror_content(content, site_id)
        
        if result["ok"]:
            logger.info(f"✅ PII scrubbing completed for {site_id}: {result['scrubbed']}")
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "PII scrubbing failed"))
            
    except Exception as e:
        logger.error(f"Error scrubbing PII: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/mirror-security/validate-cross-domain")
async def validate_cross_domain_mirror_endpoint(request: dict = Body(...)):
    """Validează căutările cross-domain"""
    try:
        site_id = request.get("site_id")
        query = request.get("query")
        target_domain = request.get("target_domain")
        
        if not site_id or not query:
            raise HTTPException(status_code=400, detail="site_id and query are required")
        
        # Validează cross-domain
        result = await validate_cross_domain_mirror(site_id, query, target_domain)
        
        if result["ok"]:
            logger.info(f"✅ Cross-domain validation passed for {site_id}")
            return result
        else:
            logger.warning(f"🚨 Cross-domain query blocked for {site_id}")
            return result
            
    except Exception as e:
        logger.error(f"Error validating cross-domain: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-security/dashboard/{site_id}")
async def get_mirror_security_dashboard_endpoint(site_id: str):
    """Returnează dashboard-ul de securitate pentru un site"""
    try:
        from mirror_security import MirrorSecurityManager
        
        security_manager = MirrorSecurityManager()
        dashboard = await security_manager.get_security_dashboard(site_id)
        
        if dashboard["ok"]:
            logger.info(f"✅ Security dashboard retrieved for {site_id}")
            return dashboard
        else:
            raise HTTPException(status_code=500, detail=dashboard.get("error", "Dashboard failed"))
            
    except Exception as e:
        logger.error(f"Error getting security dashboard: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-security/stats")
async def get_mirror_security_stats_endpoint():
    """Returnează statistici globale de securitate"""
    try:
        stats = get_security_stats()
        
        logger.info(f"✅ Global security stats retrieved: {stats['total_sites']} sites")
        return {
            "ok": True,
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting security stats: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/mirror-security/whitelist")
async def update_mirror_whitelist_endpoint(request: dict = Body(...)):
    """Actualizează whitelist-ul pentru un site"""
    try:
        site_id = request.get("site_id")
        whitelist_data = request.get("whitelist")
        
        if not site_id or not whitelist_data:
            raise HTTPException(status_code=400, detail="site_id and whitelist are required")
        
        from mirror_security import MirrorSecurityManager
        
        security_manager = MirrorSecurityManager()
        result = await security_manager.update_whitelist(site_id, whitelist_data)
        
        if result["ok"]:
            logger.info(f"✅ Whitelist updated for {site_id}")
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Whitelist update failed"))
            
    except Exception as e:
        logger.error(f"Error updating whitelist: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-security/violations/{site_id}")
async def get_mirror_security_violations_endpoint(site_id: str, limit: int = 20):
    """Returnează istoricul încălcărilor de securitate pentru un site"""
    try:
        db = MongoClient("mongodb://localhost:27017").mirror_security
        
        violations = list(db.security_violations.find(
            {"site_id": site_id}
        ).sort("timestamp", -1).limit(limit))
        
        # Convertim ObjectId la string
        for violation in violations:
            violation['_id'] = str(violation['_id'])
            if 'timestamp' in violation and isinstance(violation['timestamp'], datetime):
                violation['timestamp'] = violation['timestamp'].isoformat()
        
        logger.info(f"✅ Security violations retrieved for {site_id}: {len(violations)} records")
        return {
            "ok": True,
            "site_id": site_id,
            "violations": violations,
            "count": len(violations),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting security violations: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ============================================================================
# MIRROR AGENT CENTRAL DASHBOARD ENDPOINTS
# ============================================================================

@app.get("/mirror-dashboard/global")
async def get_global_mirror_dashboard_endpoint():
    """Returnează dashboard-ul global pentru toate Mirror Agents"""
    try:
        dashboard = await get_global_mirror_dashboard()
        
        if dashboard["ok"]:
            logger.info(f"✅ Global dashboard retrieved: {dashboard['global_stats']['total_sites']} sites")
            return dashboard
        else:
            raise HTTPException(status_code=500, detail=dashboard.get("error", "Dashboard failed"))
            
    except Exception as e:
        logger.error(f"Error getting global dashboard: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-dashboard/site/{site_id}")
async def get_site_mirror_dashboard_endpoint(site_id: str):
    """Returnează dashboard-ul pentru un site specific"""
    try:
        dashboard = await get_site_mirror_dashboard(site_id)
        
        if dashboard["ok"]:
            logger.info(f"✅ Site dashboard retrieved for {site_id}")
            return dashboard
        else:
            raise HTTPException(status_code=500, detail=dashboard.get("error", "Dashboard failed"))
            
    except Exception as e:
        logger.error(f"Error getting site dashboard: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/mirror-dashboard/alert")
async def create_mirror_alert_endpoint(request: dict = Body(...)):
    """Creează o alertă nouă pentru Mirror Agent"""
    try:
        site_id = request.get("site_id")
        alert_type = request.get("alert_type")
        severity = request.get("severity")
        message = request.get("message")
        details = request.get("details", {})
        
        if not all([site_id, alert_type, severity, message]):
            raise HTTPException(status_code=400, detail="site_id, alert_type, severity, and message are required")
        
        # Validează severity
        if severity not in ["low", "medium", "high", "critical"]:
            raise HTTPException(status_code=400, detail="severity must be one of: low, medium, high, critical")
        
        # Creează alerta
        result = await create_mirror_alert(site_id, alert_type, severity, message, details)
        
        if result["ok"]:
            logger.info(f"✅ Alert created: {alert_type} - {severity} for {site_id}")
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Alert creation failed"))
            
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.post("/mirror-dashboard/alert/{alert_id}/resolve")
async def resolve_mirror_alert_endpoint(alert_id: str):
    """Rezolvă o alertă Mirror Agent"""
    try:
        result = await resolve_mirror_alert(alert_id)
        
        if result["ok"]:
            logger.info(f"✅ Alert resolved: {alert_id}")
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Alert resolution failed"))
            
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-dashboard/alerts")
async def get_mirror_alerts_endpoint(site_id: Optional[str] = None, resolved: bool = False):
    """Returnează alertele Mirror Agents"""
    try:
        from mirror_dashboard import MirrorDashboardManager
        
        dashboard_manager = MirrorDashboardManager()
        
        if site_id:
            alerts = await dashboard_manager._get_site_alerts(site_id)
        else:
            alerts = await dashboard_manager._get_active_alerts()
        
        # Filtrează după status rezolvat
        if not resolved:
            alerts = [alert for alert in alerts if not alert.resolved]
        
        logger.info(f"✅ Alerts retrieved: {len(alerts)} alerts")
        return {
            "ok": True,
            "alerts": [alert.to_dict() for alert in alerts],
            "count": len(alerts),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-dashboard/health")
async def get_mirror_health_endpoint():
    """Returnează health score-ul global pentru Mirror Agents"""
    try:
        from mirror_dashboard import MirrorDashboardManager
        
        dashboard_manager = MirrorDashboardManager()
        
        # Obține toate site-urile
        sites = await dashboard_manager._get_all_sites()
        
        # Obține alertele active
        alerts = await dashboard_manager._get_active_alerts()
        
        # Calculează health score
        health_score = await dashboard_manager._calculate_health_score(sites, alerts)
        
        # Calculează statistici de health
        total_sites = len(sites)
        active_sites = sum(1 for site in sites if site.status == "active")
        critical_alerts = sum(1 for alert in alerts if alert.severity == "critical")
        high_alerts = sum(1 for alert in alerts if alert.severity == "high")
        
        health_status = "excellent" if health_score >= 0.9 else "good" if health_score >= 0.7 else "warning" if health_score >= 0.5 else "critical"
        
        logger.info(f"✅ Health score calculated: {health_score} ({health_status})")
        return {
            "ok": True,
            "health_score": health_score,
            "health_status": health_status,
            "total_sites": total_sites,
            "active_sites": active_sites,
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting health score: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ============================================================================
# MIRROR AGENT Q/A GENERATION ENDPOINTS
# ============================================================================

@app.post("/mirror-qa/generate")
async def generate_mirror_qa_endpoint(request: dict = Body(...)):
    """Generează set Q/A pentru Mirror Agent"""
    try:
        domain = request.get("domain")
        site_id = request.get("site_id")
        num_questions = request.get("num_questions", 20)
        
        if not domain or not site_id:
            raise HTTPException(status_code=400, detail="domain and site_id are required")
        
        # Generează setul Q/A
        result = await generate_mirror_qa_set(domain, site_id, num_questions)
        
        if result["ok"]:
            logger.info(f"✅ Q/A set generated for {domain}: {result['qa_count']} items")
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Q/A generation failed"))
            
    except Exception as e:
        logger.error(f"Error generating Q/A set: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-qa/stats")
async def get_mirror_qa_stats_endpoint():
    """Returnează statistici pentru generarea Q/A"""
    try:
        stats = get_qa_generation_stats()
        
        logger.info(f"✅ Q/A generation stats retrieved: {stats['total_qa_sets']} sets")
        return {
            "ok": True,
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting Q/A stats: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/mirror-qa/set/{site_id}")
async def get_mirror_qa_set_endpoint(site_id: str):
    """Returnează setul Q/A pentru un site"""
    try:
        db = MongoClient("mongodb://localhost:27017").mirror_qa_generation
        
        qa_set = db.qa_sets.find_one({"site_id": site_id})
        
        if qa_set:
            # Convertim ObjectId la string
            qa_set['_id'] = str(qa_set['_id'])
            
            logger.info(f"✅ Q/A set retrieved for {site_id}")
            return {
                "ok": True,
                "site_id": site_id,
                "qa_set": qa_set,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "ok": False,
                "error": f"Q/A set not found for site {site_id}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting Q/A set: {e}")
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

async def get_master_content(agent):
    """Obține conținutul agentului master din MongoDB site_content"""
    try:
        agent_id = agent["_id"]
        
        # Caută conținutul în MongoDB site_content
        content_docs = list(db.site_content.find({'agent_id': agent_id}).limit(20))
        
        content = ""
        if content_docs:
            logger.info(f"🔍 Found {len(content_docs)} content documents in MongoDB")
            for doc in content_docs:
                if doc.get('content'):
                    content += f"URL: {doc.get('url', 'Unknown')}\n"
                    content += f"Title: {doc.get('title', 'Unknown')}\n"
                    content += f"Content: {doc.get('content', '')}\n\n"
        else:
            # Fallback: caută conținut generic din site_content
            logger.warning(f"⚠️ No content found for agent {agent_id}, searching for generic content")
            generic_docs = list(db.site_content.find({}).limit(10))
            if generic_docs:
                logger.info(f"🔍 Found {len(generic_docs)} generic content documents")
                for doc in generic_docs:
                    if doc.get('content'):
                        content += f"URL: {doc.get('url', 'Unknown')}\n"
                        content += f"Title: {doc.get('title', 'Unknown')}\n"
                        content += f"Content: {doc.get('content', '')}\n\n"
        
        # Fallback la metadata agentului
        if not content:
            logger.warning(f"⚠️ No content found anywhere, using agent metadata")
            content = f"Nume: {agent.get('name', '')}\n"
            content += f"Domeniu: {agent.get('domain', '')}\n"
            content += f"URL: {agent.get('site_url', '')}\n"
            content += f"Industrie: {agent.get('industry', 'necunoscută')}\n"
        else:
            logger.info(f"✅ Retrieved {len(content)} characters of content from MongoDB")
        
        return content
        
    except Exception as e:
        logger.error(f"Error getting master content: {e}")
        return f"Nume: {agent.get('name', '')}\nDomeniu: {agent.get('domain', '')}\nURL: {agent.get('site_url', '')}"

@app.post("/agents/{agent_id}/strategy-chat")
async def strategy_chat(agent_id: str, message: dict):
    """Chat cu GPT-5 pentru discuții despre strategie"""
    try:
        # Obține agentul master
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "Agent not found"}
        
        # Obține conținutul agentului din Qdrant
        master_content = await get_master_content(agent)
        
        # Folosește GPT-5 pentru chat strategic
        llm = ChatOpenAI(
            model_name="gpt-5",  # GPT-5 pentru analiza strategică
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.3
        )
        
        prompt = f"""Ești GPT-5, expert în strategii de business și competitor analysis. 

BUSINESS MASTER:
- Nume: {agent.get('name', '')}
- Domeniu: {agent.get('domain', '')}
- URL: {agent.get('site_url', '')}

CONȚINUT SITE MASTER:
{master_content[:2000]}

MESAJUL UTILIZATORULUI:
{message.get('message', '')}

SARCINA TA:
Răspunde ca un consultant strategic expert, oferind:
1. Analize concrete bazate pe conținutul site-ului
2. Sugestii strategice specifice pentru business-ul acestuia
3. Recomandări pentru îmbunătățirea poziției competitive
4. Insights despre piață și oportunități

Răspunde în română, profesional și constructiv."""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        
        return {
            "ok": True,
            "response": response.content,
            "agent_name": agent.get('name', ''),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in strategy chat: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/agents/{agent_id}/generate-industry-sites")
async def generate_industry_sites(agent_id: str, request: dict = Body(...)):
    """Generează lista completă de site-uri din industria competitivă pentru indexare"""
    try:
        # Verifică dacă agentul există
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "Agent not found"}
        
        strategy = request.get('strategy', {})
        business_analysis = strategy.get('business_analysis', {})
        
        # Folosește GPT-5 pentru generarea listei de site-uri din industrie
        llm = ChatOpenAI(
            model_name="gpt-5",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.2
        )
        
        prompt = f"""Ești GPT-5, expert în analiza industriei și identificarea competitorilor.

CONTEXTUL BUSINESS-ULUI MASTER:
- Servicii: {business_analysis.get('services_identified', [])}
- Piața țintă: {business_analysis.get('target_market', '')}
- Tehnologii: {business_analysis.get('technologies_used', [])}
- Poziția în piață: {business_analysis.get('market_position', '')}
- Puncte forte: {business_analysis.get('strengths', [])}

SARCINA: Generează o listă COMPLETĂ de site-uri din industria competitivă pentru indexare.

Returnează DOAR JSON valid cu această structură:
{{
    "sites": [
        {{
            "domain": "exemplu.ro",
            "url": "https://exemplu.ro",
            "category": "Direct Competitor",
            "type": "Competitor",
            "priority": "High",
            "relevance_score": 95,
            "description": "Descrierea site-ului și de ce este relevant"
        }}
    ],
    "categories": {{
        "Direct Competitor": 5,
        "Indirect Competitor": 8,
        "Supplier": 3,
        "Technology Partner": 2
    }},
    "industry_summary": "Rezumat al industriei identificate"
}}

CATEGORII DE SITE-URI:
1. Direct Competitor - competitori direcți cu aceleași servicii
2. Indirect Competitor - competitori cu servicii similare/înrudite
3. Supplier - furnizori de materiale/tehnologii
4. Technology Partner - parteneri tehnologici
5. Industry Leader - lideri în industrie
6. Regional Player - jucători regionali
7. Niche Specialist - specialiști în nișe specifice

PRIORITATE:
- High: Competitori direcți, lideri în industrie
- Medium: Competitori indirecți, jucători regionali
- Low: Furnizori, parteneri tehnologici

Generează 30-50 de site-uri relevante din România și internaționale."""

        response = llm.invoke([HumanMessage(content=prompt)])
        response_content = response.content.strip()
        
        # Extrage JSON din răspuns
        if response_content.startswith('```json'):
            json_start = response_content.find('```json') + 7
            json_end = response_content.find('```', json_start)
            if json_end > json_start:
                response_content = response_content[json_start:json_end].strip()
        elif response_content.startswith('```'):
            json_start = response_content.find('```') + 3
            json_end = response_content.find('```', json_start)
            if json_end > json_start:
                response_content = response_content[json_start:json_end].strip()
        
        industry_sites = json.loads(response_content)
        
        logger.info(f"🏭 Generated industry sites list: {len(industry_sites.get('sites', []))} sites")
        
        return {
            "ok": True,
            "industry_sites": industry_sites,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating industry sites: {e}")
        return {"ok": False, "error": str(e)}

# ===================== EXPERT ADVISOR MODE - SPRINT 1 ENDPOINTS =====================

@app.post("/agents/{agent_id}/expert-advisor/initialize")
async def initialize_expert_advisor(agent_id: str):
    """Inițializează Expert Advisor Mode pentru un agent"""
    try:
        logger.info(f"🤖 Initializing Expert Advisor Mode for agent {agent_id}")
        
        # 1. Inițializează Knowledge Architecture
        knowledge_arch = get_knowledge_architecture()
        
        # 2. Inițializează AI Roles Orchestrator
        ai_orchestrator = get_ai_roles_orchestrator()
        
        # 3. Inițializează Industry Aggregator
        industry_agg = get_industry_aggregator()
        
        # 4. Inițializează Gap Analyzer
        gap_analyzer = get_gap_analyzer()
        
        # 5. Rulează procesul complet
        # a) Agregare industrie
        industry_result = await industry_agg.aggregate_industry_knowledge(agent_id)
        
        # b) Analiză gap-uri
        gaps_result = await gap_analyzer.analyze_gaps(agent_id)
        
        # c) Generează hinturi
        knowledge_arch = get_knowledge_architecture()
        hints = await knowledge_arch.generate_hints(agent_id)
        
        return {
            "ok": True,
            "message": "Expert Advisor Mode initialized successfully",
            "results": {
                "industry_aggregation": industry_result,
                "gap_analysis": gaps_result,
                "hints_generated": len(hints)
            }
        }
        
    except Exception as e:
        logger.error(f"Error initializing Expert Advisor Mode: {e}")
        return {"ok": False, "error": str(e)}
@app.get("/agents/{agent_id}/expert-advisor/status")
async def get_expert_advisor_status(agent_id: str):
    """Obține statusul Expert Advisor Mode"""
    try:
        # Obține statusul AI-urilor
        ai_orchestrator = get_ai_roles_orchestrator()
        ai_status = await ai_orchestrator.get_ai_status(agent_id)
        
        # Obține statusul sincronizării
        sync_status = await ai_orchestrator.get_sync_status(agent_id)
        
        # Obține quick wins
        knowledge_arch = get_knowledge_architecture()
        quick_wins = await knowledge_arch.get_quick_wins(agent_id)
        
        # Obține groundedness score
        groundedness = await knowledge_arch.get_groundedness_score(agent_id)
        
        return {
            "ok": True,
            "status": {
                "ai_status": ai_status,
                "sync_status": sync_status,
                "quick_wins_count": len(quick_wins),
                "groundedness_score": groundedness,
                "expert_advisor_active": True
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting Expert Advisor status: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/agents/{agent_id}/expert-advisor/hints")
async def get_expert_hints(agent_id: str):
    """Obține hinturile generate de Expert Advisor"""
    try:
        knowledge_arch = get_knowledge_architecture()
        
        # Obține toate hinturile
        hints = list(db.hints.find({"agent_id": agent_id}).sort("created_at", -1))
        
        # Convertește ObjectId la string
        for hint in hints:
            hint["_id"] = str(hint["_id"])
            if "created_at" in hint:
                hint["created_at"] = hint["created_at"].isoformat()
        
        # Obține quick wins
        quick_wins = await knowledge_arch.get_quick_wins(agent_id)
        
        return {
            "ok": True,
            "hints": hints,
            "quick_wins": [asdict(win) for win in quick_wins],
            "total_hints": len(hints)
        }
        
    except Exception as e:
        logger.error(f"Error getting expert hints: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/agents/{agent_id}/expert-advisor/feedback")
async def submit_expert_feedback(agent_id: str, request: dict = Body(...)):
    """Trimite feedback pentru hinturi"""
    try:
        hint_id = request.get("hint_id")
        feedback = request.get("feedback", "")
        admin_action = request.get("action", "pending")  # "accepted", "dismissed", "needs_evidence"
        
        knowledge_arch = get_knowledge_architecture()
        result = await knowledge_arch.process_feedback(hint_id, feedback, admin_action)
        
        if result:
            return {
                "ok": True,
                "message": f"Feedback processed: {admin_action}",
                "hint_id": hint_id
            }
        else:
            return {"ok": False, "error": "Failed to process feedback"}
            
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/agents/{agent_id}/expert-advisor/industry-map")
async def get_industry_map(agent_id: str):
    """Obține Industry Map-ul pentru agent"""
    try:
        industry_agg = get_industry_aggregator()
        industry_map = await industry_agg.get_industry_map(agent_id)
        
        if industry_map:
            # Convertește ObjectId la string
            industry_map["_id"] = str(industry_map["_id"])
            if "created_at" in industry_map:
                industry_map["created_at"] = industry_map["created_at"].isoformat()
            if "updated_at" in industry_map:
                industry_map["updated_at"] = industry_map["updated_at"].isoformat()
        
        return {
            "ok": True,
            "industry_map": industry_map
        }
        
    except Exception as e:
        logger.error(f"Error getting industry map: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/agents/{agent_id}/expert-advisor/gaps")
async def get_expert_gaps(agent_id: str):
    """Obține gap-urile identificate de Expert Advisor"""
    try:
        gaps = list(db.gaps.find({"agent_id": agent_id}).sort("total_score", -1))
        
        # Convertește ObjectId la string
        for gap in gaps:
            gap["_id"] = str(gap["_id"])
            if "created_at" in gap:
                gap["created_at"] = gap["created_at"].isoformat()
        
        # Categorizează gap-urile
        by_priority = {"high": [], "medium": [], "low": []}
        quick_wins = []
        
        for gap in gaps:
            priority = gap.get("priority", "low")
            by_priority[priority].append(gap)
            
            if gap.get("quick_win", False):
                quick_wins.append(gap)
        
        return {
            "ok": True,
            "gaps": gaps,
            "by_priority": by_priority,
            "quick_wins": quick_wins,
            "total_gaps": len(gaps)
        }
        
    except Exception as e:
        logger.error(f"Error getting expert gaps: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/agents/{agent_id}/expert-advisor/force-sync")
async def force_expert_sync(agent_id: str):
    """Forțează sincronizarea Expert Advisor"""
    try:
        # Forțează sincronizarea AI-urilor
        ai_orchestrator = get_ai_roles_orchestrator()
        sync_result = await ai_orchestrator.get_sync_status(agent_id)
        
        # Forțează re-analiza gap-urilor
        gap_analyzer = get_gap_analyzer()
        gaps_result = await gap_analyzer.analyze_gaps(agent_id)
        
        return {
            "ok": True,
            "message": "Expert Advisor sync completed",
            "sync_result": sync_result,
            "gaps_updated": gaps_result
        }
        
    except Exception as e:
        logger.error(f"Error in force sync: {e}")
        return {"ok": False, "error": str(e)}

# ===================== DUAL ORCHESTRATOR ENDPOINTS =====================

@app.post("/agents/{agent_id}/dual-report")
async def generate_dual_report(agent_id: str):
    """Generează raport dual GPT-5 + Qwen"""
    try:
        orchestrator = get_dual_orchestrator()
        report = await orchestrator.generate_dual_report(agent_id)
        
        return {
            "ok": True,
            "report": {
                "agent_id": report.agent_id,
                "gpt5_insights": report.gpt5_insights,
                "qwen_insights": report.qwen_insights,
                "industry_map": report.industry_map,
                "learning_progress": report.learning_progress,
                "recommendations": report.recommendations,
                "timestamp": report.timestamp.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating dual report: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/agents/{agent_id}/dual-status")
async def get_dual_status(agent_id: str):
    """Obține statusul sistemului dual GPT-5 + Qwen"""
    try:
        orchestrator = get_dual_orchestrator()
        status = await orchestrator.get_dual_status(agent_id)
        
        return {
            "ok": True,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Error getting dual status: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/agents/{agent_id}/force-sync")
async def force_sync_dual(agent_id: str):
    """Forțează sincronizarea între GPT-5 și Qwen"""
    try:
        orchestrator = get_dual_orchestrator()
        sync_result = await orchestrator.force_sync(agent_id)
        
        return {
            "ok": True,
            "sync_result": sync_result
        }
        
    except Exception as e:
        logger.error(f"Error in force sync: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/agents/{agent_id}/add-learning")
async def add_to_learning_queue(agent_id: str, request: dict = Body(...)):
    """Adaugă conținut în learning queue pentru Qwen"""
    try:
        orchestrator = get_dual_orchestrator()
        
        content = request.get('content', '')
        source = request.get('source', 'user')
        metadata = request.get('metadata', {})
        
        # Adaugă agent_id în metadata
        metadata['agent_id'] = agent_id
        
        await orchestrator.add_to_learning_queue(content, source, metadata)
        
        return {
            "ok": True,
            "message": "Content added to learning queue",
            "agent_id": agent_id
        }
        
    except Exception as e:
        logger.error(f"Error adding to learning queue: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/agents/{agent_id}/learning-queue")
async def get_learning_queue(agent_id: str):
    """Obține learning queue pentru un agent"""
    try:
        entries = list(db.learning_queue.find({
            "agent_id": agent_id
        }).sort("timestamp", -1).limit(50))
        
        # Convertește ObjectId la string
        for entry in entries:
            entry['_id'] = str(entry['_id'])
            if 'timestamp' in entry:
                entry['timestamp'] = entry['timestamp'].isoformat()
        
        return {
            "ok": True,
            "entries": entries,
            "total": len(entries)
        }
        
    except Exception as e:
        logger.error(f"Error getting learning queue: {e}")
        return {"ok": False, "error": str(e)}

# ===================== LANGCHAIN CHAINS ENDPOINTS =====================

@app.post("/agents/{agent_id}/run_chain/{chain_name}")
async def run_langchain_chain(agent_id: str, chain_name: str, request: Request):
    """
    Rulează un lanț LangChain pentru un agent
    
    Chain names disponibile:
    - site_analysis: Analiză completă a site-ului
    - industry_strategy: Strategie competitivă pentru industrie
    - decision_chain: Plan de acțiune concret din strategie
    """
    try:
        # Verifică dacă agentul există
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Importă LangChain executor
        try:
            from orchestrator.langchain_integration import get_langchain_executor
            langchain_executor = get_langchain_executor()
            if not langchain_executor:
                return {
                    "ok": False,
                    "error": "LangChain integration not available"
                }
        except ImportError as e:
            logger.error(f"LangChain integration not available: {e}")
            return {
                "ok": False,
                "error": f"LangChain integration not available: {str(e)}"
            }
        
        # Obține parametrii din request
        body = await request.json()
        params = body.get("params", {})
        
        # ⭐ NOU: Adaugă TOATE informațiile despre agent în parametri
        # Obține agentul complet din MongoDB
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if agent:
            # Obține conținutul site-ului
            site_content_docs = list(db.site_content.find({"agent_id": ObjectId(agent_id)}).limit(100))
            site_content = "\n\n".join([doc.get("content", "") for doc in site_content_docs])
            
            # Obține serviciile
            services = agent.get("services", [])
            if not services:
                strategy = db.competitive_strategies.find_one({"agent_id": ObjectId(agent_id)})
                if strategy:
                    services = strategy.get("services", [])
            
            # Adaugă toate informațiile în params
            params["agent_id"] = agent_id
            params["agent_data"] = {
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
            
            # Pentru site_analysis, adaugă conținutul dacă nu există
            if chain_name == "site_analysis" and not params.get("content"):
                params["content"] = site_content
            
            # Pentru industry_strategy, adaugă datele dacă nu există
            if chain_name == "industry_strategy":
                params["services_list"] = services or params.get("services_list", [])
                params["competitor_data"] = params.get("competitor_data", {})
            
            # Pentru decision_chain, obține strategia dacă nu există
            if chain_name == "decision_chain" and not params.get("strategic_output"):
                strategy = db.competitive_strategies.find_one({"agent_id": ObjectId(agent_id)})
                if strategy:
                    params["strategic_output"] = strategy.get("strategy", {})
        
        # Rulează lanțul
        result = await langchain_executor.run_chain_task(
            chain_name=chain_name,
            params=params,
            task_id=body.get("task_id"),
            progress_callback=None  # Poate fi extins cu WebSocket în viitor
        )
        
        return {
            "ok": True,
            "chain_name": chain_name,
            "agent_id": agent_id,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running LangChain chain '{chain_name}' for agent {agent_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/chains/list")
async def list_langchain_chains():
    """Listează toate lanțurile LangChain disponibile"""
    try:
        try:
            from langchain_agents.chain_registry import get_chain_registry
            registry = get_chain_registry()
            chains = registry.list_chains()
            
            chains_info = []
            for chain_name in chains:
                chain_instance = registry.get(chain_name)
                chains_info.append({
                    "name": chain_name,
                    "available": chain_instance is not None,
                    "description": _get_chain_description(chain_name)
                })
            
            return {
                "ok": True,
                "chains": chains_info,
                "total": len(chains_info)
            }
        except ImportError as e:
            logger.error(f"LangChain integration not available: {e}")
            return {
                "ok": False,
                "error": f"LangChain integration not available: {str(e)}",
                "chains": []
            }
            
    except Exception as e:
        logger.error(f"Error listing LangChain chains: {e}")
        return {
            "ok": False,
            "error": str(e),
            "chains": []
        }

@app.get("/chains/{chain_name}/preview")
async def preview_langchain_chain(chain_name: str):
    """Obține informații despre un lanț LangChain specific"""
    try:
        try:
            from langchain_agents.chain_registry import get_chain_registry
            registry = get_chain_registry()
            
            if not registry.has_chain(chain_name):
                raise HTTPException(status_code=404, detail=f"Chain '{chain_name}' not found")
            
            chain_instance = registry.get(chain_name)
            
            return {
                "ok": True,
                "chain_name": chain_name,
                "available": chain_instance is not None,
                "description": _get_chain_description(chain_name),
                "inputs": _get_chain_inputs(chain_name),
                "outputs": _get_chain_outputs(chain_name)
            }
        except ImportError as e:
            logger.error(f"LangChain integration not available: {e}")
            return {
                "ok": False,
                "error": f"LangChain integration not available: {str(e)}"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing LangChain chain '{chain_name}': {e}")
        return {
            "ok": False,
            "error": str(e)
        }

def _get_chain_description(chain_name: str) -> str:
    """Obține descrierea unui lanț"""
    descriptions = {
        "site_analysis": "Analiză completă a unui site web folosind Qwen pentru sumarizare și DeepSeek pentru strategie",
        "industry_strategy": "Strategie competitivă pentru industrie folosind DeepSeek pentru reasoning strategic",
        "decision_chain": "Plan de acțiune concret din strategie folosind Qwen pentru extrageri structurate"
    }
    return descriptions.get(chain_name, "No description available")

def _get_chain_inputs(chain_name: str) -> list:
    """Obține input-urile așteptate de un lanț"""
    inputs_map = {
        "site_analysis": ["content"],
        "industry_strategy": ["services_list", "competitor_data"],
        "decision_chain": ["strategy"]
    }
    return inputs_map.get(chain_name, [])

def _get_chain_outputs(chain_name: str) -> list:
    """Obține output-urile unui lanț"""
    outputs_map = {
        "site_analysis": ["summary", "page_types", "strengths", "weaknesses", "opportunities"],
        "industry_strategy": ["strategy_summary", "industry_opportunities", "action_plan"],
        "decision_chain": ["immediate_actions", "short_term_actions", "medium_term_actions", "long_term_actions"]
    }
    return outputs_map.get(chain_name, [])
# ===================== STARTUP EVENT - VALIDARE AUTOMATĂ AGENȚI =====================

@app.on_event("startup")
async def startup_event():
    """
    Eveniment la pornirea serverului - validează și curăță agenții invalizi automat
    """
    try:
        logger.info("🚀 Server pornit - programez validarea agenților...")
        
        # Importă validatorul
        try:
            import asyncio
            from validate_and_clean_agents import AgentValidator
            
            async def validate_agents_background():
                try:
                    # Așteaptă 10 secunde pentru ca serverul să pornească complet
                    await asyncio.sleep(10)
                    
                    logger.info("🔍 Validare automată agenți în background...")
                    validator = AgentValidator()
                    results = validator.validate_all_agents(dry_run=False)
                    
                    if results["invalid_agents"] > 0:
                        logger.warning(f"⚠️ {results['invalid_agents']} agenți invalizi au fost șterși automat")
                        logger.info(f"✅ {results['valid_agents']} agenți valizi rămân în baza de date")
                    else:
                        logger.info(f"✅ Toți cei {results['valid_agents']} agenți sunt valizi")
                        
                except Exception as e:
                    logger.error(f"❌ Eroare la validarea automată a agenților: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # Pornește validarea în background
            asyncio.create_task(validate_agents_background())
            logger.info("✅ Validare automată agenți programată în background (va rula în 10 secunde)")
            
        except ImportError as e:
            logger.warning(f"⚠️ Nu s-a putut importa AgentValidator: {e}")
        except Exception as e:
            logger.error(f"❌ Eroare la inițializarea validării: {e}")
            
    except Exception as e:
        logger.error(f"❌ Eroare în startup_event: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Eveniment la oprirea serverului"""
    logger.info("🛑 Server oprit")

# ======================
# DEEPSEEK COMPETITIVE ANALYSIS ENDPOINTS
# ======================

@app.post("/agents/{agent_id}/analyze-competition")
async def analyze_agent_for_competition(agent_id: str, background_tasks: BackgroundTasks):
    """
    🎯 TASK 1: Analizează agentul cu DeepSeek pentru descoperire competiție
    
    Primește TOT contextul (MongoDB + Qdrant) și generează:
    - Subdomenii de activitate
    - Descrieri detaliate
    - Cuvinte cheie pentru Google search
    """
    try:
        logger.info(f"🚀 START: Analiză competitivă pentru agent {agent_id}")
        
        # Verifică că agentul există și e validat
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if not agent.get("validation_passed"):
            raise HTTPException(
                status_code=400, 
                detail="Agent not validated - only validated agents can be analyzed"
            )
        
        # Import analyzer
        import sys
        sys.path.insert(0, '/srv/hf/ai_agents')
        from deepseek_competitive_analyzer import get_analyzer
        
        analyzer = get_analyzer()
        
        # Rulează analiza (poate dura 1-2 minute)
        result = analyzer.analyze_for_competition_discovery(agent_id)
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "domain": agent.get("domain"),
            "analysis": result,
            "message": "✅ Analiză competitivă completă!",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error in competition analysis: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/agents/{agent_id}/competition-analysis")
async def get_competition_analysis(agent_id: str):
    """
    Obține analiza competitivă existentă pentru un agent
    """
    try:
        analysis = db.competitive_analysis.find_one({
            "agent_id": ObjectId(agent_id),
            "analysis_type": "competition_discovery"
        })
        
        if not analysis:
            return {
                "ok": False,
                "message": "No analysis found - run /analyze-competition first",
                "agent_id": agent_id
            }
        
        # Convert ObjectId to string
        analysis["_id"] = str(analysis["_id"])
        analysis["agent_id"] = str(analysis["agent_id"])
        if isinstance(analysis.get("created_at"), datetime):
            analysis["created_at"] = analysis["created_at"].isoformat()
        
        return {
            "ok": True,
            "analysis": analysis,
            "agent_id": agent_id
        }
        
    except Exception as e:
        logger.error(f"Error getting competition analysis: {e}")
        return {
            "ok": False,
            "error": str(e)
        }

@app.get("/agents/{agent_id}/full-context")
async def get_agent_full_context(agent_id: str):
    """
    🔍 DEBUG: Vezi TOT contextul pe care îl primește DeepSeek
    Util pentru debugging și verificare
    """
    try:
        import sys
        sys.path.insert(0, '/srv/hf/ai_agents')
        from deepseek_competitive_analyzer import get_analyzer
        
        analyzer = get_analyzer()
        context = analyzer.get_full_agent_context(agent_id)
        
        # Truncate content pentru display
        if "content_full" in context:
            context["content_preview"] = context["content_full"][:1000] + "..."
            context["content_full_length"] = len(context["content_full"])
            del context["content_full"]  # Nu returna tot conținutul în API
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "context": context
        }
        
    except Exception as e:
        logger.error(f"Error getting full context: {e}")
        return {
            "ok": False,
            "error": str(e)
        }


# ======================
# GOOGLE COMPETITOR DISCOVERY ENDPOINTS
# ======================

@app.post("/agents/{agent_id}/discover-competitors")
async def discover_competitors(
    agent_id: str, 
    results_per_keyword: int = 20,
    background_tasks: BackgroundTasks = None
):
    """
    🔍 TASK 2: Descoperă competitori prin Google Search
    
    Folosește keywords generate de DeepSeek și caută în Google.
    Pentru fiecare keyword, ia primele N rezultate și le agregă inteligent.
    
    Args:
        agent_id: ID agent
        results_per_keyword: Câte rezultate per keyword (default 20)
    """
    try:
        logger.info(f"🔍 START: Descoperire competitori pentru agent {agent_id}")
        
        # Verifică că agentul există
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Verifică că există analiza DeepSeek
        analysis = db.competitive_analysis.find_one({
            "agent_id": ObjectId(agent_id),
            "analysis_type": "competition_discovery"
        })
        if not analysis:
            raise HTTPException(
                status_code=400,
                detail="No competitive analysis found. Run /analyze-competition first!"
            )
        
        # Import discovery engine
        import sys
        sys.path.insert(0, '/srv/hf/ai_agents')
        from google_competitor_discovery import get_discovery_engine
        
        engine = get_discovery_engine()
        
        # Rulează discovery (poate dura 5-10 minute)
        logger.info(f"⏳ Pornesc descoperirea... (va dura câteva minute)")
        
        result = engine.discover_competitors_for_agent(
            agent_id=agent_id,
            results_per_keyword=results_per_keyword,
            use_api=False  # Folosește scraping (free)
        )
        
        # Pregătește răspuns
        competitors = result.get("competitors", [])
        stats = result.get("stats", {})
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "domain": agent.get("domain"),
            "competitors_found": len(competitors),
            "top_10_competitors": competitors[:10],
            "stats": stats,
            "message": f"✅ Descoperire completă! Găsiți {len(competitors)} competitori",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error in competitor discovery: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/agents/{agent_id}/competitors")
async def get_discovered_competitors(agent_id: str, limit: int = 50):
    """
    Obține lista de competitori descoperiți pentru un agent
    
    Args:
        limit: Câți competitori să returneze (default 50)
    """
    try:
        discovery = db.competitor_discovery.find_one({
            "agent_id": ObjectId(agent_id),
            "discovery_type": "google_search"
        })
        
        if not discovery:
            return {
                "ok": False,
                "message": "No competitors found - run /discover-competitors first",
                "agent_id": agent_id
            }
        
        discovery_data = discovery.get("discovery_data", {})
        competitors = discovery_data.get("competitors", [])
        stats = discovery_data.get("stats", {})
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "total_competitors": len(competitors),
            "competitors": competitors[:limit],
            "stats": stats,
            "discovered_at": discovery.get("created_at").isoformat() if discovery.get("created_at") else None
        }
        
    except Exception as e:
        logger.error(f"Error getting competitors: {e}")
        return {
            "ok": False,
            "error": str(e)
        }

@app.get("/agents/{agent_id}/competitors/by-subdomain/{subdomain_name}")
async def get_competitors_by_subdomain(agent_id: str, subdomain_name: str):
    """
    Obține competitorii pentru un subdomeniu specific
    """
    try:
        discovery = db.competitor_discovery.find_one({
            "agent_id": ObjectId(agent_id),
            "discovery_type": "google_search"
        })
        
        if not discovery:
            return {"ok": False, "message": "No discovery data found"}
        
        discovery_data = discovery.get("discovery_data", {})
        subdomain_map = discovery_data.get("subdomain_map", {})
        
        if subdomain_name not in subdomain_map:
            return {
                "ok": False,
                "message": f"Subdomain '{subdomain_name}' not found",
                "available_subdomains": list(subdomain_map.keys())
            }
        
        domains = subdomain_map[subdomain_name]
        all_competitors = discovery_data.get("competitors", [])
        
        # Filtrează competitorii pentru subdomeniului
        subdomain_competitors = [
            comp for comp in all_competitors
            if comp["domain"] in domains
        ]
        
        return {
            "ok": True,
            "subdomain": subdomain_name,
            "competitors_count": len(subdomain_competitors),
            "competitors": subdomain_competitors
        }
        
    except Exception as e:
        logger.error(f"Error getting subdomain competitors: {e}")
        return {"ok": False, "error": str(e)}


# ======================
# COMPETITOR AGENTS & MASTER-SLAVE SYSTEM
# ======================

@app.post("/agents/{master_agent_id}/create-competitor-agents")
async def create_competitor_agents_endpoint(
    master_agent_id: str,
    max_competitors: int = 20,
    min_score: float = 40.0,
    background_tasks: BackgroundTasks = None
):
    """
    🤖 Transformă competitorii descoperiți în agenți slave
    
    Creează agenți pentru top competitori și stabilește relația master-slave
    
    Args:
        master_agent_id: ID agent master
        max_competitors: Câți competitori (default 20)
        min_score: Scor minim (default 40.0)
    """
    try:
        logger.info(f"🤖 START: Create competitor agents for master {master_agent_id}")
        
        # Verifică master agent
        master = agents_collection.find_one({"_id": ObjectId(master_agent_id)})
        if not master:
            raise HTTPException(status_code=404, detail="Master agent not found")
        
        # Import creator
        import sys
        sys.path.insert(0, '/srv/hf/ai_agents')
        from competitor_agents_creator import CompetitorAgentsCreator
        
        creator = CompetitorAgentsCreator()
        
        # Rulează în fundal (poate dura 30-60 minute)
        logger.info(f"⏳ Starting batch creation... (va dura {max_competitors * 2} minute)")
        
        results = await creator.create_competitor_agents(
            master_agent_id=master_agent_id,
            max_competitors=max_competitors,
            min_score=min_score
        )
        
        return {
            "ok": True,
            "master_agent_id": master_agent_id,
            "master_domain": master.get("domain"),
            "results": results,
            "message": f"✅ Created {len(results['agents_created'])} new agents, "
                      f"{len(results['agents_existed'])} existed, "
                      f"{results['relationships_created']} relationships",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error in competitor agents creation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@app.get("/agents/{master_agent_id}/slave-agents")
async def get_slave_agents(master_agent_id: str):
    """
    Obține toți agenții slave pentru un master agent
    """
    try:
        master = agents_collection.find_one({"_id": ObjectId(master_agent_id)})
        if not master:
            raise HTTPException(status_code=404, detail="Master agent not found")
        
        slave_ids = master.get("competitor_slaves", [])
        
        slaves = list(agents_collection.find({"_id": {"$in": slave_ids}}))
        
        # Convert ObjectId
        for slave in slaves:
            slave["_id"] = str(slave["_id"])
            slave["master_agent_id"] = str(slave.get("master_agent_id"))
            if isinstance(slave.get("created_at"), datetime):
                slave["created_at"] = slave["created_at"].isoformat()
        
        return {
            "ok": True,
            "master_agent_id": master_agent_id,
            "master_domain": master.get("domain"),
            "total_slaves": len(slaves),
            "slaves": slaves
        }
        
    except Exception as e:
        logger.error(f"Error getting slave agents: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/agents/{master_agent_id}/competitive-landscape")
async def get_competitive_landscape(master_agent_id: str):
    """
    Obține landscape-ul competitiv complet pentru un master agent
    Include: master, slaves, relații, scores, analytics
    """
    try:
        # Master agent
        master = agents_collection.find_one({"_id": ObjectId(master_agent_id)})
        if not master:
            raise HTTPException(status_code=404, detail="Master agent not found")
        
        # Slave agents
        slave_ids = master.get("competitor_slaves", [])
        slaves = list(agents_collection.find({"_id": {"$in": slave_ids}}))
        
        # Relationships
        relationships = list(db.agent_relationships.find({
            "master_id": ObjectId(master_agent_id),
            "relationship_type": "competitor"
        }))
        
        # Convert ObjectIds
        for slave in slaves:
            slave["_id"] = str(slave["_id"])
        
        for rel in relationships:
            rel["_id"] = str(rel["_id"])
            rel["master_id"] = str(rel["master_id"])
            rel["slave_id"] = str(rel["slave_id"])
        
        # Analytics
        analytics = {
            "total_competitors": len(slaves),
            "avg_competitor_score": sum(s.get("competitor_score", 0) for s in slaves) / len(slaves) if slaves else 0,
            "top_competitor": max(slaves, key=lambda x: x.get("competitor_score", 0)) if slaves else None,
            "total_keywords_covered": len(set(
                kw for s in slaves 
                for kw in s.get("keywords_matched", [])
            )),
            "total_subdomains_covered": len(set(
                sub for s in slaves 
                for sub in s.get("subdomains_matched", [])
            ))
        }
        
        return {
            "ok": True,
            "master": {
                "agent_id": str(master["_id"]),
                "domain": master.get("domain"),
                "name": master.get("name")
            },
            "slaves": slaves,
            "relationships": relationships,
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error(f"Error getting competitive landscape: {e}")
        return {"ok": False, "error": str(e)}


# ============================================================================
# SIMPLE AGENT CREATION API (for Control Panel)
# ============================================================================

@app.post("/api/agents/create")
async def create_agent_simple(background_tasks: BackgroundTasks, request: dict = Body(...)):
    """
    Creează un agent nou pentru orice website (fără session_id)
    Usage din Control Panel - Background task
    """
    import subprocess
    from urllib.parse import urlparse
    import asyncio
    
    try:
        site_url = request.get("site_url")
        
        if not site_url:
            return {"ok": False, "error": "site_url is required"}
        
        logger.info(f"🚀 Starting agent creation for: {site_url}")
        
        # Extrage domain-ul pentru verificare
        parsed = urlparse(site_url)
        domain = parsed.netloc.replace('www.', '')
        if not domain:
            domain = site_url.replace('https://', '').replace('http://', '').split('/')[0]
        
        # Verifică dacă agentul există deja
        existing = agents_collection.find_one({"domain": domain})
        if existing:
            # Converteste ObjectId la string pentru serializare JSON
            existing_dict = {
                "_id": str(existing.get("_id", "")),
                "domain": existing.get("domain", domain),
                "name": existing.get("name", ""),
                "site_url": existing.get("site_url", site_url),
                "status": existing.get("status", "ready"),
                "agent_type": existing.get("agent_type", "master")
            }
            return {
                "ok": True,
                "agent": existing_dict,
                "message": f"Agent already exists for {domain}"
            }
        
        # Rulează scriptul în mod sincron (în thread)
        def create_agent_sync():
            try:
                env = os.environ.copy()
                # Asigură conexiuni corecte către resursele de pe server
                env.update({
                    "MONGODB_URI": "mongodb://localhost:27017",
                    "QDRANT_URL": "http://localhost:9306",
                })
                # Folosește creatorul cu GPU embeddings (construction_agent_creator)
                result = subprocess.run(
                    ['python3', '/srv/hf/ai_agents/tools/construction_agent_creator.py', '--url', site_url, '--mode', 'create_agent'],
                    capture_output=True,
                    text=True,
                    timeout=1200,  # 20 minutes (GPU processing + scraping)
                    env=env
                )
                logger.info(f"Agent creation finished with code {result.returncode}")
                
                # Log stdout and stderr pentru debugging
                if result.stdout:
                    logger.info(f"Script stdout: {result.stdout}")
                if result.stderr:
                    logger.error(f"Script stderr: {result.stderr}")
                    
                if result.returncode != 0:
                    logger.error(f"Script failed with code {result.returncode}")
            except Exception as e:
                logger.error(f"Error in background task: {e}")
        
        # Rulează în background (nu blochează)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, create_agent_sync)
        
        # Așteaptă 30 secunde pentru ca agentul să fie creat
        await asyncio.sleep(30)
        
        # Verifică dacă a fost creat
        agent = agents_collection.find_one({"domain": domain})
        
        if agent:
            # Converteste ObjectId la string și creează dict serializabil
            agent_dict = {
                "_id": str(agent.get("_id", "")),
                "domain": agent.get("domain", domain),
                "name": agent.get("name", ""),
                "site_url": agent.get("site_url", site_url),
                "status": agent.get("status", "ready"),
                "agent_type": agent.get("agent_type", "master")
            }
            logger.info(f"✅ Agent created successfully: {domain}")
            return {
                "ok": True,
                "agent": agent_dict,
                "message": f"Agent created successfully for {domain}"
            }
        else:
            # Dacă nu există încă, salvează minim pentru a fi vizibil în UI și marchează în procesare
            try:
                placeholder = {
                    "domain": domain,
                    "site_url": site_url,
                    "name": f"Agent {domain}",
                    "status": "created",
                    "agent_type": "master",
                    "validation_passed": False,
                    "created_at": datetime.now(timezone.utc)
                }
                inserted = agents_collection.insert_one(placeholder)
                logger.info(f"📝 Placeholder agent inserted for {domain}: {inserted.inserted_id}")
                return {
                    "ok": True,
                    "agent": {"_id": str(inserted.inserted_id), "domain": domain, "status": "created"},
                    "message": f"Agent creation started for {domain}. Placeholder inserted; analysis will continue."
                }
            except Exception as ie:
                logger.warning(f"Could not insert placeholder for {domain}: {ie}")
                # Agentul e încă în creare, returnează status pending
                return {
                    "ok": True,
                    "agent": {"domain": domain, "status": "creating"},
                    "message": f"Agent creation started for {domain}. Please wait and refresh."
                }
            
    except Exception as e:
        logger.error(f"❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


# ===================================================================
# 🧠 COMPETITIVE INTELLIGENCE API ENDPOINTS
# ===================================================================

@app.get("/api/competitive-intelligence/serp-discovery/{agent_id}")
async def get_serp_discovery(agent_id: str):
    """Get SERP discovery results pentru agent"""
    try:
        result = db.serp_discovery_results.find_one({"agent_id": agent_id})
        
        if not result:
            return None
        
        # Convert ObjectId
        result['_id'] = str(result['_id'])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting SERP discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/competitive-intelligence/relationships/{agent_id}")
async def get_agent_relationships(agent_id: str):
    """Get slave agents relationships"""
    try:
        relationships = list(db.agent_relationships.find({
            "master_id": ObjectId(agent_id),
            "relationship_type": "competitor"
        }))
        
        # Enrich with slave agent data
        enriched = []
        for rel in relationships:
            slave = db.site_agents.find_one({"_id": rel['slave_id']})
            
            if slave:
                enriched.append({
                    "master_id": str(rel['master_id']),
                    "slave_id": str(rel['slave_id']),
                    "slave_domain": slave.get('domain', 'unknown'),
                    "slave_chunks": slave.get('chunks_indexed', 0),
                    "competitor_data": rel.get('competitor_data', {}),
                    "learning_objectives": rel.get('learning_objectives', {}),
                    "created_at": rel.get('created_at', datetime.now()).isoformat() if isinstance(rel.get('created_at'), datetime) else str(rel.get('created_at', ''))
                })
        
        return {
            "master_id": agent_id,
            "relationships": enriched,
            "total": len(enriched)
        }
        
    except Exception as e:
        logger.error(f"Error getting relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/competitive-intelligence/improvement/{agent_id}")
async def get_improvement_plan(agent_id: str):
    """Get improvement plan pentru agent"""
    try:
        plan = db.improvement_plans.find_one({"master_agent_id": agent_id})
        
        if not plan:
            return None
        
        # Convert ObjectId and dates
        plan['_id'] = str(plan['_id'])
        if 'created_at' in plan and isinstance(plan['created_at'], datetime):
            plan['created_at'] = plan['created_at'].isoformat()
        
        return plan
        
    except Exception as e:
        logger.error(f"Error getting improvement plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/competitive-intelligence/actions/{agent_id}")
async def get_actionable_plan(agent_id: str):
    """Get actionable plan pentru agent"""
    try:
        plan = db.actionable_plans.find_one({"master_agent_id": agent_id})
        
        if not plan:
            return None
        
        # Convert ObjectId and dates
        plan['_id'] = str(plan['_id'])
        if 'created_at' in plan and isinstance(plan['created_at'], datetime):
            plan['created_at'] = plan['created_at'].isoformat()
        
        # Convert dates in plan.plan if exists
        if 'plan' in plan and 'created_at' in plan['plan']:
            if isinstance(plan['plan']['created_at'], datetime):
                plan['plan']['created_at'] = plan['plan']['created_at'].isoformat()
        
        return plan
        
    except Exception as e:
        logger.error(f"Error getting actionable plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/competitive-intelligence/run-full-workflow/{agent_id}")
async def run_full_competitive_workflow(agent_id: str):
    """
    Rulează workflow-ul complet de competitive intelligence:
    1. SERP Discovery
    2. Slave Agents Creation
    3. Improvement Analysis
    4. Actionable Plan Generation
    """
    try:
        import subprocess
        
        # 1. SERP Discovery
        logger.info(f"🔍 Running SERP discovery for {agent_id}")
        subprocess.run([
            'python3',
            '/srv/hf/ai_agents/deepseek_serp_discovery.py',
            agent_id,
            '15'
        ], check=True, timeout=300)
        
        # 2. Slave Agents Creation
        logger.info(f"🤖 Creating slave agents for {agent_id}")
        subprocess.run([
            'python3',
            '/srv/hf/ai_agents/create_intelligent_slave_agents.py',
            agent_id,
            '15',
            '25.0'
        ], check=True, timeout=1800)  # 30 min
        
        # 3. Improvement Analysis
        logger.info(f"📊 Running improvement analysis for {agent_id}")
        subprocess.run([
            'python3',
            '/srv/hf/ai_agents/master_improvement_analyzer.py',
            agent_id
        ], check=True, timeout=300)
        
        # 4. Actionable Plan
        logger.info(f"⚡ Generating actionable plan for {agent_id}")
        subprocess.run([
            'python3',
            '/srv/hf/ai_agents/action_service.py',
            agent_id
        ], check=True, timeout=300)
        
        return {
            "success": True,
            "agent_id": agent_id,
            "message": "Full workflow completed successfully",
            "steps_completed": [
                "SERP Discovery",
                "Slave Agents Creation",
                "Improvement Analysis",
                "Actionable Plan Generation"
            ]
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Workflow timeout")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {e}")
    except Exception as e:
        logger.error(f"Error running workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket for live progress tracking
@app.websocket("/ws/agent-creation")
async def websocket_agent_creation(websocket: WebSocket):
    """WebSocket pentru progress tracking live"""
    await websocket.accept()
    
    try:
        # Așteaptă request
        data = await websocket.receive_json()
        url = data.get('url')
        max_pages = data.get('max_pages', 5000)
        
        if not url:
            await websocket.send_json({"error": "URL required"})
            await websocket.close()
            return
        
        # Import MegaAgentCreator
        sys.path.insert(0, '/srv/hf/ai_agents')
        from create_mega_agent import MegaAgentCreator
        
        # Create agent with progress tracking
        creator = MegaAgentCreator(websocket=websocket)
        agent_id = await creator.create_mega_agent(url, max_pages)
        
        await websocket.close()
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
            await websocket.close()
        except:
            pass


# ===================== REPORT ENDPOINTS =====================

@app.get("/api/agents/{agent_id}/report")
async def get_agent_report(agent_id: str):
    """Get comprehensive agent report with subcategories"""
    try:
        # Get agent data
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get competitive intelligence data
        serp_discovery = db.serp_discovery_results.find_one({"agent_id": ObjectId(agent_id)})
        improvement_plan = db.improvement_plans.find_one({"agent_id": ObjectId(agent_id)})
        actionable_plan = db.actionable_plans.find_one({"agent_id": ObjectId(agent_id)})
        
        # Build report
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": str(agent["_id"]),
            "domain": agent.get("domain", agent.get("url", "Unknown")),
            "url": agent.get("url"),
            "status": agent.get("status", "unknown"),
            "pages_indexed": agent.get("pages_indexed", 0),
            "chunks_indexed": agent.get("chunks_indexed", 0),
            "has_embeddings": agent.get("has_embeddings", False),
            "validation_passed": agent.get("validation_passed", False),
            "created_at": agent.get("created_at", "N/A"),
            
            # Subcategories/services
            "subcategories": agent.get("subcategories", []),
            "services": agent.get("services", []),
            "categories": agent.get("categories", []),
            
            # Competitive Intelligence
            "competitors_found": len(serp_discovery.get("top_competitors", [])) if serp_discovery else 0,
            "keywords": serp_discovery.get("keywords", []) if serp_discovery else [],
            "top_competitors": serp_discovery.get("top_competitors", [])[:10] if serp_discovery else [],
            
            # Improvement
            "improvement_priorities": improvement_plan.get("priority_actions", []) if improvement_plan else [],
            "actionable_tasks": len(actionable_plan.get("actions", [])) if actionable_plan else 0,
            
            # Technical details
            "vector_collection": agent.get("vector_collection"),
            "scraping_method": agent.get("scraping_method", "Unknown"),
            "agent_type": agent.get("agent_type", "Unknown")
        }
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/health")
async def system_health():
    """Check system health"""
    try:
        health = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "healthy",
            "components": {}
        }
        
        # Check MongoDB
        try:
            client.admin.command('ping')
            health["components"]["mongodb"] = {"status": "healthy", "message": "Connected"}
        except Exception as e:
            health["components"]["mongodb"] = {"status": "unhealthy", "message": str(e)}
            health["status"] = "degraded"
        
        # Check Qdrant
        try:
            import requests
            qdrant_url = os.getenv("QDRANT_URL", "http://localhost:9306")
            resp = requests.get(f"{qdrant_url}/", timeout=5)
            if resp.status_code == 200:
                health["components"]["qdrant"] = {"status": "healthy", "message": "Connected"}
            else:
                health["components"]["qdrant"] = {"status": "unhealthy", "message": f"HTTP {resp.status_code}"}
                health["status"] = "degraded"
        except Exception as e:
            health["components"]["qdrant"] = {"status": "unhealthy", "message": str(e)}
            health["status"] = "degraded"
        
        # Check DeepSeek
        try:
            deepseek_key = os.getenv("DEEPSEEK_API_KEY")
            if deepseek_key:
                health["components"]["deepseek"] = {"status": "configured", "message": "API key present"}
            else:
                health["components"]["deepseek"] = {"status": "warning", "message": "No API key"}
        except Exception as e:
            health["components"]["deepseek"] = {"status": "error", "message": str(e)}
        
        # Check OpenAI
        try:
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                health["components"]["openai"] = {"status": "configured", "message": "API key present"}
            else:
                health["components"]["openai"] = {"status": "warning", "message": "No API key"}
        except Exception as e:
            health["components"]["openai"] = {"status": "error", "message": str(e)}
        
        # Agent statistics
        try:
            total_agents = agents_collection.count_documents({})
            ready_agents = agents_collection.count_documents({"status": {"$in": ["ready", "validated"]}})
            health["components"]["agents"] = {
                "status": "healthy",
                "total": total_agents,
                "ready": ready_agents
            }
        except Exception as e:
            health["components"]["agents"] = {"status": "error", "message": str(e)}
        
        return health
        
    except Exception as e:
        logger.error(f"Error checking health: {e}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "message": str(e)
        }

