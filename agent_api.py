# agent_api.py
searcher = None
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, BackgroundTasks, Body, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import requests
import socket
import urllib.robotparser as robotparser
from urllib.parse import urlparse
import asyncio
import logging
import traceback
from datetime import datetime, timezone
from urllib.parse import urlparse

# Încarcă variabilele de mediu din .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv nu este disponibil, folosește variabilele de mediu sistem

def _norm_host(h: str) -> str:
    h = (h or "").strip().lower()
    if h.startswith("www."): h = h[4:]
    return h

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


# existente
# # from site_agent_creator import create_site_agent_ws
# # from task_executor import handle_task_conversation

# admin (competitor discovery + ingest)
# from tools.admin_discovery import ingest_urls, web_search
# from adapters.scraper_adapter import smart_fetch
# from adapters.search_providers import search_serp
# from langchain_openai import ChatOpenAI

# <<< NEW: config DB unificat >>>
from config.database_config import (
    MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION
)

app = FastAPI()

# --- CHAT & UI INTEGRATION ---
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from chat_controller import get_controller

# Mount static files for UI
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    os.makedirs("static", exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    controller = get_controller()
    response = controller.process_user_message(request.message)
    return response

class ActionRequest(BaseModel):
    action: str
    params: Dict[str, Any] = {}

@app.post("/api/execute-action")
async def execute_action(request: ActionRequest):
    """Execută acțiunile confirmate de utilizator în chat"""
    action = request.action
    params = request.params
    
    controller = get_controller()

    if action == "start_scan":
        # TODO: Trigger real workflow via subprocess
        return {"status": "started", "message": f"Scanare simulată pornită pentru {params.get('domain', 'unknown')}"}
    elif action == "generate_report":
        return {"status": "completed", "message": "Raport generat cu succes. Verifică folderul reports/."}
    elif action == "start_briefing_trigger":
        # Activează modul Briefing în Controller
        controller.briefing_mode = True
        controller.briefing_step = 0
        controller.client_data = {}
        return {
            "status": "completed", 
            "message": "Briefing strategic activat. DeepSeek preia controlul."
        }
    
    return {"status": "error", "message": "Acțiune necunoscută"}
# -----------------------------

searcher = None

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

# ------ Health/Ready ------


def _normalize_subdomains(subdomains):
    """Normalizează subdomeniile (convertește string-uri în dicționare)"""
    if not subdomains:
        return []
    
    normalized = []
    for subdomain in subdomains:
        if isinstance(subdomain, dict):
            normalized.append({
                "name": subdomain.get("name", ""),
                "description": subdomain.get("description", ""),
                "keywords": subdomain.get("keywords", []),
                "suggested_keywords": subdomain.get("suggested_keywords", [])
            })
        else:
            # Dacă e string, convertește în dicționar
            normalized.append({
                "name": str(subdomain),
                "description": "",
                "keywords": [],
                "suggested_keywords": []
            })
    return normalized



# Helper function pentru normalizare subdomenii
def _normalize_subdomains(subdomains):
    """Normalizează subdomeniile (convertește string-uri în dicționare)"""
    if not subdomains:
        return []
    
    normalized = []
    for subdomain in subdomains:
        if isinstance(subdomain, dict):
            normalized.append({
                "name": subdomain.get("name", ""),
                "description": subdomain.get("description", ""),
                "keywords": subdomain.get("keywords", []),
                "suggested_keywords": subdomain.get("suggested_keywords", [])
            })
        else:
            normalized.append({
                "name": str(subdomain),
                "description": "",
                "keywords": [],
                "suggested_keywords": []
            })
    return normalized

@app.get("/health")
async def health():
    """
    Returnează statusul sistemului (API, MongoDB, Qdrant)
    """
    try:
        # Verifică MongoDB
        mongodb_status = "healthy"
        mongodb_error = None
        try:
            mongo_client.admin.command("ping")
        except Exception as e:
            mongodb_status = "unhealthy"
            mongodb_error = str(e)[:100]
        
        # Verifică Qdrant
        qdrant_status = "healthy"
        qdrant_error = None
        try:
            from qdrant_client import QdrantClient
            qdrant = QdrantClient(host="localhost", port=9306, timeout=2)
            qdrant.get_collections()
        except Exception as e:
            qdrant_status = "unhealthy"
            qdrant_error = str(e)[:100]
        
        # Overall status
        overall_status = "healthy" if (mongodb_status == "healthy" and qdrant_status == "healthy") else "unhealthy"
        
        return {
            "ok": overall_status == "healthy",
            "overall_status": overall_status,
            "services": {
                "mongodb": {
                    "status": mongodb_status,
                    "error": mongodb_error
                },
                "qdrant": {
                    "status": qdrant_status,
                    "error": qdrant_error
                }
            }
        }
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "ok": False,
            "overall_status": "unhealthy",
            "error": str(e)
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

@app.get("/api/stats")
async def get_stats():
    """
    Returnează statistici despre sistem (agenți, chunks, keywords, etc.)
    """
    try:
        # Numără agenți
        total_agents = agents_collection.count_documents({})
        master_agents = agents_collection.count_documents({"master_agent_id": {"$exists": False}})
        slave_agents = agents_collection.count_documents({"master_agent_id": {"$exists": True}})
        
        # Numără chunks (din toți agenții) - cu error handling
        total_chunks = 0
        try:
            for agent in agents_collection.find({}, {"chunks_indexed": 1}):
                chunks = agent.get("chunks_indexed", 0)
                if isinstance(chunks, (int, float)):
                    total_chunks += int(chunks)
        except Exception as e:
            logger.warning(f"Error counting chunks: {e}")
            total_chunks = 0
        
        # Numără keywords (din toți agenții) - cu error handling
        total_keywords = 0
        try:
            for agent in agents_collection.find({}, {"keywords": 1, "overall_keywords": 1}):
                keywords = agent.get("keywords", [])
                overall_keywords = agent.get("overall_keywords", [])
                if isinstance(keywords, list):
                    total_keywords += len(keywords)
                if isinstance(overall_keywords, list):
                    total_keywords += len(overall_keywords)
        except Exception as e:
            logger.warning(f"Error counting keywords: {e}")
            total_keywords = 0
        
        # Numără competitors (slave agents)
        competitors = slave_agents
        
        # Numără SERP checks (din colecția serp_results)
        serp_checks = db.serp_results.count_documents({}) if "serp_results" in db.list_collection_names() else 0
        
        # Active workflows (din ceo_workflow_executions)
        active_workflows = db.ceo_workflow_executions.count_documents({"status": "in_progress"}) if "ceo_workflow_executions" in db.list_collection_names() else 0
        
        return {
            "ok": True,
            "total_agents": total_agents,
            "master_agents": master_agents,
            "slave_agents": slave_agents,
            "active_agents": total_agents,  # Poți adăuga logică pentru agenți activi
            "chunks": total_chunks,
            "keywords": total_keywords,
            "competitors": competitors,
            "serp_checks": serp_checks,
            "active_workflows": active_workflows
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            "ok": False,
            "error": str(e),
            "total_agents": 0,
            "active_agents": 0,
            "chunks": 0,
            "keywords": 0,
            "competitors": 0,
            "serp_checks": 0,
            "active_workflows": 0
        }
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

# <<< CHANGED: unificare Mongo și colecții >>>
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DATABASE]
# Folosește colecția actuală `site_agents` (agents vechi rămân ca backup)
agents_collection = db.site_agents
conversations_collection = db.conversations
site_content_col = db[MONGODB_COLLECTION]

logger = logging.getLogger("agent_api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

def get_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="CRITICAL: OPENAI_API_KEY is not set. Check config.env/.env file.")
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
        logger.info(f"[CONVERSATION] Saved conversation for agent {agent_id}")
    except Exception as e:
        logger.error(f"[CONVERSATION] Failed to save conversation: {e}")

def get_learning_strategy_prompt(agent_id: str, site_url: str, industry: str, context: str) -> str:
    """Generează promptul pentru strategia de învățare din industrie"""
    return f"""
Ești un expert în analiza industriei și dezvoltarea strategiilor de învățare pentru agenți AI.

AGENT ANALIZAT:
- ID: {agent_id}
- Site: {site_url}
- Industrie detectată: {industry}
- Context din baza de date: {context[:1000]}...

OBIECTIV: Dezvoltă o strategie comprehensivă de învățare pentru acest agent să înțeleagă și să se dezvolte în industria sa.

STRATEGIA TREBUIE SĂ INCLUDE:

1. **ANALIZA INDUSTRIEI:**
   - Identificarea segmentelor de piață
   - Analiza competitorilor directi și indirecți
   - Tendințele și oportunitățile din industrie

2. **PLAN DE ÎNVĂȚARE:**
   - Ce informații să caute și să analizeze
   - Cum să identifice oportunități de dezvoltare
   - Strategii de monitorizare a pieței

3. **ACȚIUNI CONCRETE:**
   - Căutări specifice de a face
   - Site-uri relevante de monitorizat
   - Metrice de urmărit

4. **DEZVOLTARE CONTINUĂ:**
   - Cum să învețe din conversațiile cu utilizatorii
   - Cum să se adapteze la schimbările din industrie
   - Strategii de îmbunătățire continuă

Răspunde cu o strategie detaliată, structurată și acționabilă.
"""

# ------------- UI -------------
@app.get("/", response_class=HTMLResponse)
async def get_ui_root():
    with open("ui_interface_new.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# alias /ui (unele setup-uri folosesc exact acest path)
@app.get("/ui", response_class=HTMLResponse)
async def get_ui_alias():
    with open("ui_interface_new.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/config/api-key-status")
async def api_key_status():
    return {"is_set": bool(os.getenv("OPENAI_API_KEY"))}

# ------------- Agents list -------------
@app.get("/api/agents")
async def get_agents(type: str = None):
    """
    Returnează lista de agenți cu TOATE datele necesare
    Filtru opțional: type=master (doar master agents)
    """
    try:
        query = {}
        if type == "master":
            query["master_agent_id"] = {"$exists": False}
        
        agents = list(agents_collection.find(query).sort("createdAt", -1))
        
        # Formatează agenții cu toate datele
        result = []
        for agent in agents:
            agent_data = {
                "_id": str(agent["_id"]),
                "domain": agent.get("domain", ""),
                "site_url": agent.get("site_url", ""),
                "name": agent.get("name", agent.get("domain", "")),
                "status": agent.get("status", "unknown"),
                "industry": agent.get("industry", ""),
                "chunks_indexed": agent.get("chunks_indexed", 0),
                "pages_indexed": agent.get("pages_indexed", 0),
                "keywords": agent.get("keywords", []),
                "overall_keywords": agent.get("overall_keywords", []),
                "keyword_count": len(agent.get("keywords", [])) + len(agent.get("overall_keywords", [])),
                "createdAt": agent.get("createdAt", agent.get("created_at")),
                "updatedAt": agent.get("updatedAt", agent.get("updated_at")),
            }
            
            # Formatare date
            if isinstance(agent_data.get("createdAt"), datetime):
                agent_data["createdAt"] = agent_data["createdAt"].isoformat()
            if isinstance(agent_data.get("updatedAt"), datetime):
                agent_data["updatedAt"] = agent_data["updatedAt"].isoformat()
            
            # Numără slave agents (competitors)
            slave_count = agents_collection.count_documents({"master_agent_id": str(agent["_id"])})
            agent_data["slave_count"] = slave_count
            
            result.append(agent_data)
        
        return result
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

# ------------- WebSockets -------------
@app.websocket("/ws/create-agent")
async def create_agent_websocket(websocket: WebSocket, url: str):
    await websocket.accept()
    api_key = get_api_key()
    try:
        await create_site_agent_ws(websocket, url, api_key)
    except Exception as e:
        await websocket.send_json({"status": "error", "message": f"Eroare neașteptată: {e}"})
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
    limit   = int(payload.get("limit", 12) or 12)
    queries = payload.get("queries")
    if queries and not isinstance(queries, list):
        queries = None
    res = discover_competitors(agent_id, limit=limit, queries=queries)
    return res


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

    # <<< FIX: citește din colecția corectă de conținut >>>
    try:
        content_docs = site_content_col.find({"agent_id": ObjectId(agent_id)}).limit(5)
        content_parts = []
        for doc in content_docs:
            if doc.get("content"):
                content_parts.append(doc["content"][:500])  # primele 500 caractere
        agent_content = " ".join(content_parts)[:2000]
        logger.info(f"[AUTOEXPAND] Found {len(content_parts)} content docs from DB for agent {agent_id}")
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

    # 2) Query generation cu GPT pe baza contextului
    api_key = get_api_key()
    llm = ChatOpenAI(model_name=os.getenv("LLM_MODEL", "gpt-4o-mini"), openai_api_key=api_key, temperature=0)

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

    # 2) GPT Supervisor select
    api_key = get_api_key()
    llm = ChatOpenAI(model_name=os.getenv("LLM_MODEL", "gpt-4o-mini"), openai_api_key=api_key, temperature=0)
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

@app.post("/admin/industry/{agent_id}/learning-strategy")
def api_generate_learning_strategy(agent_id: str):
    """
    Generează o strategie de învățare pentru agent bazată pe industria sa
    """
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {"ok": False, "error": "agent_not_found"}

        base_domain = agent.get("domain")
        site_url = agent.get("site_url") or (f"https://{base_domain}" if base_domain else None)

        # <<< FIX: citește din colecția corectă de conținut >>>
        agent_content = ""
        try:
            content_docs = site_content_col.find({"agent_id": ObjectId(agent_id)}).limit(5)
            content_parts = []
            for doc in content_docs:
                if doc.get("content"):
                    content_parts.append(doc["content"][:500])
            agent_content = " ".join(content_parts)[:2000]
        except Exception as e:
            logger.warning(f"Could not get agent content from DB: {e}")

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
        llm = ChatOpenAI(model_name=os.getenv("LLM_MODEL", "gpt-4o-mini"), openai_api_key=api_key, temperature=0.3)

        strategy_prompt = get_learning_strategy_prompt(agent_id, site_url, industry, agent_content)

        try:
            response = llm.invoke(strategy_prompt)
            strategy = response.content

            strategy_doc = {
                "agent_id": ObjectId(agent_id),
                "timestamp": datetime.now(timezone.utc),
                "industry": industry,
                "strategy": strategy,
                "context_used": agent_content[:1000]
            }
            db.learning_strategies.insert_one(strategy_doc)

            return {
                "ok": True,
                "agent_id": str(agent.get("_id")),
                "domain": base_domain,
                "industry": industry,
                "strategy": strategy,
                "context_length": len(agent_content)
            }

        except Exception as e:
            logger.error(f"Error generating learning strategy: {e}")
            return {"ok": False, "error": f"strategy_generation_failed: {str(e)}"}

    except Exception as e:
        logger.error(f"Error in learning strategy endpoint: {e}")
        return {"ok": False, "error": f"endpoint_error: {str(e)}"}


# ============================================================================
# ENDPOINT-URI PENTRU CREARE AGENT ȘI LIVE MONITORING
# ============================================================================

@app.post("/api/agents")
async def create_agent_full_workflow(request: dict = Body(...), background_tasks: BackgroundTasks = None):
    """
    Creează un agent complet cu workflow în background.
    Returnează imediat cu workflow_id, apoi rulează workflow-ul în background.
    """
    try:
        site_url = request.get("site_url")
        industry = request.get("industry", "")

        if not site_url:
            raise HTTPException(status_code=400, detail="site_url is required")

        # Generează workflow_id imediat (fără import)
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{site_url.replace('https://', '').replace('http://', '').replace('/', '_')[:30]}"
        
        # Încearcă să găsească agentul dacă există deja (pentru redirect la Live Monitor)
        agent_id = None
        try:
            # Găsește agentul după site_url sau domain (cel mai recent)
            parsed_url = urlparse(site_url)
            domain = parsed_url.netloc.replace('www.', '')
            
            existing_agent = agents_collection.find_one(
                {"$or": [
                    {"domain": domain},
                    {"site_url": site_url}
                ]},
                sort=[("created_at", -1)]
            )
            if existing_agent:
                agent_id = str(existing_agent["_id"])
        except Exception as e:
            logger.debug(f"Could not find existing agent: {e}")
        
        # PREPARE RĂSPUNSUL IMEDIAT (înainte de ORICE altceva)
        response_data = {
            "ok": True,
            "workflow_id": workflow_id,
            "site_url": site_url,
            "industry": industry,
            "message": "Full agent workflow started! Monitor progress in Workflow Monitor.",
            "estimated_time_minutes": "20-45"
        }
        
        # Adaugă agent_id dacă există (pentru redirect imediat la Live Monitor)
        if agent_id:
            response_data["agent_id"] = agent_id
        
        # FUNCȚIE pentru a rula workflow-ul în background (import lazy)
        def start_workflow_background():
            """Pornește workflow-ul în background - import aici pentru a nu bloca request-ul"""
            try:
                logger.info(f"🚀 Starting FULL AGENT WORKFLOW for: {site_url} (workflow_id: {workflow_id})")
                
                # Import LAZY - doar când rulează workflow-ul
                from ceo_master_workflow import CEOMasterWorkflow
                
                # Creează event loop nou pentru background task
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def run_full_workflow():
                    try:
                        logger.info(f"🔥 WORKFLOW {workflow_id} STARTED pentru {site_url}")
                        logger.info(f"   Industry: {industry}")
                        
                        # Detectează automat numărul real de GPU-uri pentru utilizare maximă
                        import torch
                        num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0
                        optimal_parallel = num_gpus + 2 if num_gpus > 0 else 5  # GPU-uri + overhead
                        
                        workflow = CEOMasterWorkflow()
                        result = await workflow.execute_full_workflow(
                            site_url=site_url,
                            results_per_keyword=20,
                            parallel_gpu_agents=optimal_parallel
                        )
                        
                        logger.info(f"✅ WORKFLOW {workflow_id} COMPLETED pentru {site_url}")
                        logger.info(f"   Master Agent: {result.get('master_agent_id')}")
                        logger.info(f"   Slave Agents: {result.get('slave_agents_count', 0)}")
                        logger.info(f"   Keywords: {result.get('keywords_count', 0)}")
                    except Exception as e:
                        logger.error(f"❌ WORKFLOW {workflow_id} FAILED pentru {site_url}: {e}")
                        logger.error(traceback.format_exc())
                
                # Rulează workflow-ul
                loop.run_until_complete(run_full_workflow())
                loop.close()
                
            except Exception as e:
                logger.error(f"❌ Error in background workflow task: {e}")
                logger.error(traceback.format_exc())
        
        # PORNEȘTE WORKFLOW-UL ÎN BACKGROUND (după ce am pregătit răspunsul)
        # IMPORTANT: Folosește threading direct pentru funcții sync cu event loops
        import threading
        thread = threading.Thread(target=start_workflow_background, daemon=True)
        thread.start()
        
        # RETURNEAZĂ RĂSPUNSUL IMEDIAT (fără să aștepte workflow-ul)
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error starting agent workflow: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/by-workflow/{workflow_id}")
async def get_agent_by_workflow(workflow_id: str):
    """Găsește agentul după workflow_id"""
    try:
        # Workflow ID conține site_url, deci putem căuta după domain
        # Format: workflow_20251119_150350_test-final-now.com
        parts = workflow_id.split('_')
        if len(parts) >= 4:
            domain = '_'.join(parts[3:])  # Ultimele părți sunt domain-ul
            
            agent = agents_collection.find_one(
                {"domain": {"$regex": domain, "$options": "i"}},
                sort=[("created_at", -1)]
            )
            
            if agent:
                return {
                    "ok": True,
                    "agent_id": str(agent["_id"]),
                    "domain": agent.get("domain"),
                    "site_url": agent.get("site_url")
                }
        
        return {"ok": False, "message": "Agent not found yet"}
    except Exception as e:
        logger.error(f"Error finding agent by workflow: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/api/agents/by-site-url")
async def get_agent_by_site_url(site_url: str = Query(...)):
    """Găsește agentul după site_url (cel mai recent)"""
    try:
        parsed_url = urlparse(site_url)
        domain = parsed_url.netloc.replace('www.', '')
        
        agent = agents_collection.find_one(
            {"$or": [
                {"domain": domain},
                {"site_url": site_url}
            ]},
            sort=[("created_at", -1)]
        )
        
        if agent:
            return {
                "ok": True,
                "agent_id": str(agent["_id"]),
                "domain": agent.get("domain"),
                "site_url": agent.get("site_url"),
                "status": agent.get("status")
            }
        
        return {"ok": False, "message": "Agent not found"}
    except Exception as e:
        logger.error(f"Error finding agent by site_url: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LIVE PROGRESS TRACKING - Pentru afișare în timp real în UI
# ============================================================================

# Global dict pentru a stoca progresul în memorie (mai rapid decât MongoDB)
_agent_progress_cache = {}

def update_agent_progress(agent_id: str, progress_data: dict):
    """Actualizează progresul unui agent (apelat din workflow-uri)"""
    global _agent_progress_cache
    if agent_id not in _agent_progress_cache:
        _agent_progress_cache[agent_id] = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "logs": []
        }
    
    _agent_progress_cache[agent_id].update(progress_data)
    _agent_progress_cache[agent_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Adaugă log entry dacă există mesaj
    if "message" in progress_data:
        _agent_progress_cache[agent_id]["logs"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": progress_data["message"],
            "step": progress_data.get("current_step", "unknown")
        })
        # Păstrează doar ultimele 100 de log-uri
        _agent_progress_cache[agent_id]["logs"] = _agent_progress_cache[agent_id]["logs"][-100:]


@app.get("/api/agents/{agent_id}/progress")
async def get_agent_progress(agent_id: str):
    """
    Returnează progresul în timp real al creării unui agent.
    Folosit de UI pentru Live Monitor.
    Format compatibil cu LiveMonitor.jsx
    """
    try:
        # Definește pașii standard pentru workflow
        def build_steps(current_step: str, pages: int, embeddings: int, keywords_count: int = 0):
            steps = [
                {
                    "id": "scraping",
                    "name": "🕷️ Web Scraping",
                    "status": "completed" if pages > 0 else ("in_progress" if current_step == "scraping" else "pending"),
                    "progress": 100 if pages > 0 else (50 if current_step == "scraping" else 0),
                    "details": f"{pages} pages extracted" if pages > 0 else "Extracting website content..."
                },
                {
                    "id": "analysis",
                    "name": "🔬 Content Analysis",
                    "status": "completed" if pages > 10 else ("in_progress" if current_step == "analysis" else "pending"),
                    "progress": 100 if pages > 10 else 0,
                    "details": "Analyzing content structure and topics"
                },
                {
                    "id": "embeddings",
                    "name": "🧠 Creating Embeddings",
                    "status": "completed" if embeddings > 0 else ("in_progress" if current_step == "creating_embeddings" else "pending"),
                    "progress": 100 if embeddings > 0 else (50 if current_step == "creating_embeddings" else 0),
                    "details": f"{embeddings} embeddings created" if embeddings > 0 else "Generating vector embeddings..."
                },
                {
                    "id": "keywords",
                    "name": "🔑 Keyword Discovery",
                    "status": "completed" if keywords_count > 0 else "pending",
                    "progress": 100 if keywords_count > 0 else 0,
                    "details": f"{keywords_count} keywords identified" if keywords_count > 0 else "Discovering relevant keywords..."
                },
                {
                    "id": "competitors",
                    "name": "🎯 Competitor Analysis",
                    "status": "pending",
                    "progress": 0,
                    "details": "Analyzing competition landscape..."
                },
                {
                    "id": "strategy",
                    "name": "📋 Strategy Generation",
                    "status": "pending",
                    "progress": 0,
                    "details": "Creating strategic recommendations..."
                }
            ]
            return steps
        
        # 1. Verifică cache-ul în memorie (cel mai rapid)
        if agent_id in _agent_progress_cache:
            cached = _agent_progress_cache[agent_id]
            pages = cached.get("pages_scraped", 0)
            embeddings = cached.get("embeddings_created", 0)
            steps = build_steps(cached.get("current_step", "initializing"), pages, embeddings)
            completed_steps = len([s for s in steps if s["status"] == "completed"])
            overall = int((completed_steps / len(steps)) * 100)
            
            return {
                "ok": True,
                "agent_id": agent_id,
                "domain": cached.get("domain", ""),
                "status": cached.get("status", "in_progress"),
                "current_step": cached.get("current_step", "initializing"),
                "overall_progress": overall,
                "completed_steps": completed_steps,
                "total_steps": len(steps),
                "steps": steps,
                "pages_scraped": pages,
                "embeddings_created": embeddings,
                "message": cached.get("message", "Processing..."),
                "logs": cached.get("logs", [])[-20:],
                "updated_at": cached.get("updated_at"),
                "source": "cache"
            }
        
        # 2. Verifică în MongoDB - colecția agents
        try:
            agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        except:
            agent = None
        
        if agent:
            status = agent.get("status", "unknown")
            # Verifică pages_indexed sau pages_scraped
            pages_scraped = agent.get("pages_indexed", agent.get("pages_scraped", 0))
            if pages_scraped == 0 and "agent_config" in agent:
                pages_scraped = agent.get("agent_config", {}).get("pages_scraped", 0)
            
            embeddings = agent.get("chunks_indexed", agent.get("embeddings_count", agent.get("total_embeddings", 0)))
            keywords = agent.get("keywords", agent.get("overall_keywords", []))
            keywords_count = len(keywords) if isinstance(keywords, list) else 0
            
            # Determină step-ul curent bazat pe date
            if status == "completed" or status == "active":
                current_step = "completed"
            elif embeddings > 0:
                current_step = "creating_embeddings"
            elif pages_scraped > 0:
                current_step = "scraping"
            else:
                current_step = "initializing"
            
            steps = build_steps(current_step, pages_scraped, embeddings, keywords_count)
            completed_steps = len([s for s in steps if s["status"] == "completed"])
            overall = int((completed_steps / len(steps)) * 100) if len(steps) > 0 else 0
            
            # Calculează progres mai detaliat
            if pages_scraped > 0 and embeddings == 0:
                overall = max(overall, 30)  # Minim 30% dacă avem pagini
            if pages_scraped > 50:
                overall = max(overall, 40)
            
            return {
                "ok": True,
                "agent_id": agent_id,
                "domain": agent.get("domain"),
                "site_url": agent.get("site_url"),
                "status": status,
                "current_step": current_step,
                "overall_progress": overall,
                "completed_steps": completed_steps,
                "total_steps": len(steps),
                "steps": steps,
                "pages_scraped": pages_scraped,
                "embeddings_created": embeddings,
                "keywords_count": keywords_count,
                "message": f"Agent {status}. Pages: {pages_scraped}, Embeddings: {embeddings}",
                "source": "mongodb"
            }
        
        # 3. Verifică în colecția workflows
        workflow = db.workflows.find_one(
            {"$or": [
                {"agent_id": agent_id},
                {"_id": agent_id}
            ]},
            sort=[("created_at", -1)]
        )
        
        if workflow:
            steps = build_steps(workflow.get("current_step", "processing"), 0, 0)
            return {
                "ok": True,
                "agent_id": agent_id,
                "domain": workflow.get("domain", ""),
                "status": workflow.get("status", "in_progress"),
                "current_step": workflow.get("current_step", "processing"),
                "overall_progress": workflow.get("progress", {}).get("percent", 50),
                "completed_steps": 0,
                "total_steps": len(steps),
                "steps": steps,
                "message": workflow.get("message", "Workflow in progress..."),
                "source": "workflow"
            }
        
        # 4. Nu s-a găsit nimic - returnează status pending cu steps goale
        steps = build_steps("pending", 0, 0)
        return {
            "ok": True,
            "agent_id": agent_id,
            "domain": "",
            "status": "pending",
            "current_step": "waiting",
            "overall_progress": 0,
            "completed_steps": 0,
            "total_steps": len(steps),
            "steps": steps,
            "message": "Agent creation pending or not found",
            "source": "none"
        }
        
    except Exception as e:
        logger.error(f"Error getting agent progress: {e}")
        return {
            "ok": False,
            "error": str(e),
            "status": "error"
        }


@app.get("/api/agents/{agent_id}/live-logs")
async def get_agent_live_logs(agent_id: str, limit: int = Query(50, ge=1, le=200)):
    """
    Returnează log-urile live ale procesului de creare agent.
    Citește din fișierul de log și filtrează pentru acest agent.
    """
    try:
        logs = []
        
        # 1. Log-uri din cache
        if agent_id in _agent_progress_cache:
            logs.extend(_agent_progress_cache[agent_id].get("logs", []))
        
        # 2. Citește din fișierul de log pentru mai multe detalii
        log_file = "/srv/hf/ai_agents/logs/backend_main.log"
        if os.path.exists(log_file):
            try:
                # Citește ultimele linii din log
                import subprocess
                result = subprocess.run(
                    ["tail", "-500", log_file],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        # Filtrează linii relevante (scraping, embeddings, etc.)
                        if any(keyword in line.lower() for keyword in ["scraperapi", "pagina", "embedding", "gpu", "qdrant", "agent"]):
                            logs.append({
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "message": line[:200],  # Limitează lungimea
                                "step": "log"
                            })
            except Exception as e:
                logger.debug(f"Could not read log file: {e}")
        
        # Returnează ultimele N log-uri
        return {
            "ok": True,
            "agent_id": agent_id,
            "logs": logs[-limit:],
            "total_logs": len(logs)
        }
        
    except Exception as e:
        logger.error(f"Error getting live logs: {e}")
        return {"ok": False, "error": str(e), "logs": []}


@app.get("/api/agents/{agent_id}/stats")
async def get_agent_stats(agent_id: str):
    """
    Returnează statistici detaliate pentru un agent specific.
    Folosit de Live Monitor pentru afișare în timp real.
    """
    try:
        # Caută agentul
        try:
            agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        except:
            agent = None
        
        if not agent:
            # Returnează statistici default dacă agentul nu există încă
            return {
                "ok": True,
                "agent_id": agent_id,
                "status": "pending",
                "pages_scraped": 0,
                "total_pages": 0,
                "embeddings_count": 0,
                "keywords_count": 0,
                "competitors_count": 0,
                "serp_rankings_count": 0,
                "message": "Agent not found or still being created"
            }
        
        # Calculează statistici
        pages_scraped = agent.get("pages_scraped", 0)
        if pages_scraped == 0 and "pages_content" in agent:
            pages_scraped = len(agent.get("pages_content", []))
        
        embeddings = agent.get("embeddings_count", agent.get("total_embeddings", 0))
        keywords = agent.get("keywords", agent.get("overall_keywords", []))
        keywords_count = len(keywords) if isinstance(keywords, list) else 0
        
        # Numără competitorii (slave agents)
        competitors_count = agents_collection.count_documents({"master_agent_id": ObjectId(agent_id)})
        
        # Verifică SERP rankings
        serp_count = 0
        try:
            serp_data = db.serp_rankings.count_documents({"agent_id": agent_id})
            serp_count = serp_data
        except:
            pass
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "domain": agent.get("domain"),
            "site_url": agent.get("site_url"),
            "status": agent.get("status", "unknown"),
            "pages_scraped": pages_scraped,
            "total_pages": agent.get("total_pages", pages_scraped),
            "embeddings_count": embeddings,
            "keywords_count": keywords_count,
            "keywords": keywords[:20] if isinstance(keywords, list) else [],  # Primele 20
            "competitors_count": competitors_count,
            "serp_rankings_count": serp_count,
            "created_at": str(agent.get("created_at", "")),
            "updated_at": str(agent.get("updated_at", ""))
        }
        
    except Exception as e:
        logger.error(f"Error getting agent stats: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/api/stats")
async def get_stats():
    """Returnează statistici pentru dashboard"""
    try:
        # Numără master agents (fără master_agent_id)
        master_agents_count = agents_collection.count_documents({"master_agent_id": {"$exists": False}})
        
        # Numără slave agents (cu master_agent_id)
        slave_agents_count = agents_collection.count_documents({"master_agent_id": {"$exists": True}})
        
        # Total agents
        total_agents = agents_collection.count_documents({})
        
        # Numără keywords totale (din competitive_analysis)
        total_keywords = 0
        try:
            analyses = db["competitive_analysis"].find({})
            for analysis in analyses:
                analysis_data = analysis.get('analysis_data', {})
                total_keywords += len(analysis_data.get('overall_keywords', []))
                for subdomain in analysis_data.get('subdomains', []):
                    total_keywords += len(subdomain.get('keywords', []))
        except Exception as e:
            logger.debug(f"Could not count keywords: {e}")
        
        return {
            "master_agents": master_agents_count,
            "slave_agents": slave_agents_count,
            "total_agents": total_agents,
            "total_keywords": total_keywords
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            "master_agents": 0,
            "slave_agents": 0,
            "total_agents": 0,
            "total_keywords": 0
        }


# ============================================================================
# CHAT DEEPSEEK - Conectat la Qdrant și MongoDB
# ============================================================================

@app.post("/api/agents/{agent_id}/chat")
async def agent_chat(agent_id: str, request: dict = Body(...)):
    """
    Chat DeepSeek cu agentul - conectat la toate informațiile
    Chat-ul se identifică cu agentul și știe tot despre site și business
    """
    try:
        from agent_chat_deepseek import AgentChatDeepSeek
        
        message = request.get("message", "")
        session_id = request.get("session_id")
        
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        
        # Inițializează chat-ul
        chat = AgentChatDeepSeek()
        
        # Apelează chat-ul
        result = chat.chat(agent_id, message, session_id)
        
        if result.get("ok"):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Chat error"))
            
    except Exception as e:
        logger.error(f"Error in agent chat: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/chat/sessions/{session_id}")
async def get_chat_session(agent_id: str, session_id: str):
    """Obține istoricul conversației"""
    try:
        session = db.master_agent_chat_history.find_one({
            "agent_id": agent_id,
            "session_id": session_id
        })
        
        if not session:
            return {"ok": False, "message": "Session not found"}
        
        return {
            "ok": True,
            "messages": session.get("messages", []),
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error getting chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# API EXTERN PENTRU INTEGRARE ÎN SITE
# ============================================================================

@app.post("/api/public/chat/{domain}")
async def public_chat(domain: str, request: dict = Body(...)):
    """
    API PUBLIC pentru chat - poate fi integrat în site-ul original
    Folosește domain-ul pentru a găsi agentul
    """
    try:
        # Găsește agentul după domain
        agent = agents_collection.find_one({"domain": domain})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent_id = str(agent["_id"])
        message = request.get("message", "")
        session_id = request.get("session_id")
        
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        
        # Folosește același chat DeepSeek
        from agent_chat_deepseek import AgentChatDeepSeek
        chat = AgentChatDeepSeek()
        result = chat.chat(agent_id, message, session_id)
        
        if result.get("ok"):
            return {
                "ok": True,
                "response": result["response"],
                "session_id": result["session_id"],
                "timestamp": result["timestamp"]
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Chat error"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in public chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/public/chat/{domain}/info")
async def public_chat_info(domain: str):
    """Informații despre chat-ul disponibil pentru acest domain"""
    try:
        agent = agents_collection.find_one({"domain": domain})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return {
            "ok": True,
            "domain": domain,
            "site_url": agent.get("site_url", ""),
            "chat_available": True,
            "endpoint": f"/api/public/chat/{domain}",
            "chunks_indexed": agent.get("chunks_indexed", 0),
            "status": "ready" if agent.get("chunks_indexed", 0) > 0 else "not_ready"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/status/complete")
async def get_agent_complete_status(agent_id: str):
    """
    Verifică dacă agentul este procesat complet:
    - MongoDB: ✅
    - Qdrant: ✅
    - LangChain: ✅
    """
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        domain = agent.get("domain", "")
        chunks_indexed = agent.get("chunks_indexed", 0)
        
        # Verifică MongoDB
        mongo_status = chunks_indexed > 0
        
        # Verifică Qdrant
        qdrant_status = False
        qdrant_collections = []
        try:
            from qdrant_client import QdrantClient
            qdrant = QdrantClient(url="http://localhost:9306")
            collections = qdrant.get_collections()
            
            # Caută colecții pentru acest agent
            domain_clean = domain.replace(".", "_").replace("-", "_")
            possible_names = [
                f"agent_{agent_id}_content",
                f"construction_{domain_clean}",
                f"agent_{agent_id}",
            ]
            
            for col in collections.collections:
                if col.name in possible_names or domain_clean in col.name:
                    info = qdrant.get_collection(col.name)
                    if info.points_count > 0:
                        qdrant_status = True
                        qdrant_collections.append({
                            "name": col.name,
                            "vectors": info.points_count
                        })
        except Exception as e:
            logger.debug(f"Could not check Qdrant: {e}")
        
        # Verifică LangChain (dacă există chunks în MongoDB și Qdrant)
        langchain_status = mongo_status and qdrant_status
        
        # Status complet
        is_complete = mongo_status and qdrant_status and langchain_status
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "domain": domain,
            "status": {
                "mongodb": mongo_status,
                "qdrant": qdrant_status,
                "langchain": langchain_status,
                "complete": is_complete
            },
            "details": {
                "chunks_indexed": chunks_indexed,
                "qdrant_collections": qdrant_collections,
                "total_vectors": sum(c["vectors"] for c in qdrant_collections)
            }
        }
    except Exception as e:
        logger.error(f"Error getting complete status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT-URI AGENȚI - Corectate pentru date complete
# ============================================================================
# Notă: Endpoint-ul /api/agents este definit mai sus (linia 254)

@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """
    Returnează detalii complete pentru un agent
    """
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Verifică status complet (MongoDB + Qdrant + LangChain)
        chunks_indexed = agent.get("chunks_indexed", 0)
        domain = agent.get("domain", "")
        
        # Verifică Qdrant
        qdrant_status = False
        qdrant_vectors = 0
        try:
            from qdrant_client import QdrantClient
            qdrant = QdrantClient(url="http://localhost:9306")
            collections = qdrant.get_collections()
            
            domain_clean = domain.replace(".", "_").replace("-", "_")
            for col in collections.collections:
                if domain_clean in col.name or agent_id in col.name:
                    info = qdrant.get_collection(col.name)
                    if info.points_count > 0:
                        qdrant_status = True
                        qdrant_vectors += info.points_count
        except:
            pass
        
        # Status complet
        is_complete = chunks_indexed > 0 and qdrant_status
        
        # Calculează keywords totale (din subdomenii + overall_keywords)
        subdomains = _normalize_subdomains(agent.get("subdomains", []))
        overall_keywords = agent.get("overall_keywords", [])
        
        # Extrage toate keywords-urile din subdomenii
        all_subdomain_keywords = []
        for subdomain in subdomains:
            if isinstance(subdomain, dict):
                all_subdomain_keywords.extend(subdomain.get("keywords", []))
        
        # Combina keywords-urile (din subdomenii + overall)
        all_keywords = list(set(all_subdomain_keywords + overall_keywords))  # Remove duplicates
        keyword_count = len(all_keywords)
        
        agent_data = {
            "_id": str(agent["_id"]),
            "domain": agent.get("domain", ""),
            "site_url": agent.get("site_url", ""),
            "name": agent.get("name", agent.get("domain", "")),
            "status": agent.get("status", "unknown"),
            "industry": agent.get("industry", ""),
            "chunks_indexed": chunks_indexed,
            "pages_indexed": agent.get("pages_indexed", 0),
            "keywords": all_subdomain_keywords,  # Keywords din subdomenii
            "overall_keywords": overall_keywords,  # Keywords generale
            "keyword_count": keyword_count,  # Total keywords (fără duplicate)
            "subdomains": subdomains,
            "createdAt": agent.get("createdAt", agent.get("created_at")),
            "updatedAt": agent.get("updatedAt", agent.get("updated_at")),
            "status_complete": {
                "mongodb": chunks_indexed > 0,
                "qdrant": qdrant_status,
                "langchain": is_complete,
                "complete": is_complete,
                "qdrant_vectors": qdrant_vectors
            }
        }
        
        # Numără slave agents
        slave_count = agents_collection.count_documents({"master_agent_id": str(agent["_id"])})
        agent_data["slave_count"] = slave_count
        
        # Adaugă competitors și competitor_count
        competitors = agent.get("competitors", [])
        agent_data["competitors"] = competitors
        agent_data["competitor_count"] = len(competitors) if isinstance(competitors, list) else 0
        
        return agent_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/competitors")
async def get_agent_competitors(agent_id: str, limit: int = Query(default=50, ge=1, le=500)):
    """
    Returnează lista de competitori pentru un agent
    """
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Obține competitorii din array-ul agentului
        competitors_list = agent.get("competitors", [])
        
        # Verifică care competitori sunt deja agenți slave
        slave_agents = list(agents_collection.find({"master_agent_id": str(agent["_id"])}))
        slave_domains = {a.get("domain") for a in slave_agents if a.get("domain")}
        
        # Formatează competitorii cu informații suplimentare
        competitors_data = []
        for competitor_domain in competitors_list[:limit]:
            if isinstance(competitor_domain, str):
                competitors_data.append({
                    "domain": competitor_domain,
                    "url": f"https://{competitor_domain}",
                    "is_slave_agent": competitor_domain in slave_domains,
                    "slave_agent_id": next(
                        (str(a["_id"]) for a in slave_agents if a.get("domain") == competitor_domain),
                        None
                    )
                })
            elif isinstance(competitor_domain, dict):
                # Dacă competitorul este deja un dict cu mai multe informații
                competitors_data.append({
                    "domain": competitor_domain.get("domain", ""),
                    "url": competitor_domain.get("url", f"https://{competitor_domain.get('domain', '')}"),
                    "is_slave_agent": competitor_domain.get("domain", "") in slave_domains,
                    "slave_agent_id": next(
                        (str(a["_id"]) for a in slave_agents if a.get("domain") == competitor_domain.get("domain", "")),
                        None
                    ),
                    **{k: v for k, v in competitor_domain.items() if k not in ["domain", "url"]}
                })
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "domain": agent.get("domain", ""),
            "total_competitors": len(competitors_list),
            "competitors": competitors_data,
            "slave_agents_count": len(slave_domains),
            "unprocessed_count": len(competitors_data) - len([c for c in competitors_data if c.get("is_slave_agent")])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting competitors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/complete/list")
async def get_complete_agents():
    """
    Returnează DOAR agenții complet procesați:
    - chunks_indexed > 0 (MongoDB)
    - Există în Qdrant
    - LangChain activ
    """
    try:
        # Găsește agenții cu chunks
        agents_with_chunks = list(agents_collection.find({
            "chunks_indexed": {"$gt": 0},
            "master_agent_id": {"$exists": False}
        }).sort("createdAt", -1))
        
        # Verifică Qdrant pentru fiecare
        complete_agents = []
        try:
            from qdrant_client import QdrantClient
            qdrant = QdrantClient(url="http://localhost:9306")
            collections = qdrant.get_collections()
            collection_names = [c.name for c in collections.collections]
        except:
            collection_names = []
        
        for agent in agents_with_chunks:
            agent_id = str(agent["_id"])
            domain = agent.get("domain", "").replace(".", "_").replace("-", "_")
            
            # Verifică dacă există în Qdrant
            in_qdrant = any(
                domain in col_name or agent_id in col_name
                for col_name in collection_names
            )
            
            if in_qdrant:
                agent_data = {
                    "_id": agent_id,
                    "domain": agent.get("domain", ""),
                    "site_url": agent.get("site_url", ""),
                    "name": agent.get("name", agent.get("domain", "")),
                    "status": agent.get("status", "unknown"),
                    "industry": agent.get("industry", ""),
                    "chunks_indexed": agent.get("chunks_indexed", 0),
                    "keyword_count": len(agent.get("keywords", [])) + len(agent.get("overall_keywords", [])),
                    "slave_count": agents_collection.count_documents({"master_agent_id": agent_id}),
                    "createdAt": agent.get("createdAt", agent.get("created_at")),
                }
                complete_agents.append(agent_data)
        
        return {
            "total": len(complete_agents),
            "agents": complete_agents
        }
    except Exception as e:
        logger.error(f"Error getting complete agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ANALIZĂ DEEPSEEK - Subdomenii + Keywords (La comandă)
# ============================================================================

@app.post("/api/agents/{agent_id}/analyze")
async def analyze_agent(agent_id: str):
    """
    Declanșează analiza DeepSeek pentru agent:
    - Descompunere în subdomenii
    - Generare keywords pentru fiecare subdomeniu
    - Keywords generale
    """
    try:
        from agent_analysis_deepseek import AgentAnalysisDeepSeek
        
        analyzer = AgentAnalysisDeepSeek()
        result = analyzer.analyze_subdomains_and_keywords(agent_id)
        
        if result.get("ok"):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))
            
    except Exception as e:
        logger.error(f"Error in agent analysis: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/agents/{agent_id}/analyze")
async def analyze_agent_websocket(websocket: WebSocket, agent_id: str):
    """
    Rulează analiza DeepSeek cu updates live prin WebSocket
    Trimite progresul pas cu pas pentru a evita panica utilizatorului
    """
    await websocket.accept()
    try:
        from agent_analysis_deepseek import AgentAnalysisDeepSeek
        import requests
        import json as json_lib
        import re
        
        # Trimite mesaj inițial
        await websocket.send_json({
            "type": "status",
            "message": "🚀 Pornire analiză...",
            "progress": 0
        })
        
        analyzer = AgentAnalysisDeepSeek()
        
        # Obține informații despre agent
        await websocket.send_json({
            "type": "status",
            "message": "📋 Încărcare date agent...",
            "progress": 10
        })
        
        agent = analyzer.agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            await websocket.send_json({
                "type": "error",
                "message": "Agent not found"
            })
            return
        
        domain = agent.get("domain", "")
        
        # Obține conținut
        await websocket.send_json({
            "type": "status",
            "message": f"🔍 Analizare conținut pentru {domain}...",
            "progress": 20
        })
        
        content_summary = analyzer.get_agent_content_summary(agent_id)
        
        # Construiește prompt
        await websocket.send_json({
            "type": "status",
            "message": "📝 Pregătire prompt analiză...",
            "progress": 30
        })
        
        site_url = agent.get("site_url", "")
        industry = agent.get("industry", "")
        
        prompt = f"""Analizează site-ul {domain} ({site_url}) și identifică:

1. SUBDOMENII PRINCIPALE:
   Pentru fiecare subdomeniu, identifică:
   - Numele subdomeniului (ex: "servicii", "produse", "despre", "contact")
   - Descrierea subdomeniului (ce conține, ce scop are)
   - 10-15 keywords relevante pentru acel subdomeniu
   - 5-10 sugestii de keywords suplimentare

2. KEYWORDS GENERALE:
   Identifică 20-30 keywords generale relevante pentru întregul site

Format răspuns JSON:
{{
  "subdomains": [
    {{
      "name": "nume-subdomeniu",
      "description": "descriere detaliată",
      "keywords": ["keyword1", "keyword2", ...],
      "suggested_keywords": ["sugestie1", "sugestie2", ...]
    }}
  ],
  "overall_keywords": ["keyword1", "keyword2", ...]
}}

Conținut site (rezumat):
{content_summary[:2000] if content_summary else "Nu există conținut disponibil"}

Industrie: {industry if industry else "Nespecificată"}
"""
        
        # Apelează DeepSeek
        await websocket.send_json({
            "type": "status",
            "message": "🤖 Trimitere cerere către DeepSeek AI...",
            "progress": 40
        })
        
        # Obține API key din .env sau variabile de mediu
        DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
        if not DEEPSEEK_API_KEY:
            # Fallback: citește direct din .env
            try:
                env_path = os.path.join(os.path.dirname(__file__), ".env")
                if os.path.exists(env_path):
                    with open(env_path, "r") as f:
                        for line in f:
                            if line.startswith("DEEPSEEK_API_KEY="):
                                DEEPSEEK_API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                                break
            except Exception as e:
                logger.error(f"Error reading DEEPSEEK_API_KEY from .env: {e}")
        
        if not DEEPSEEK_API_KEY:
            await websocket.send_json({
                "type": "error",
                "message": "❌ DEEPSEEK_API_KEY nu este setat. Verifică .env file."
            })
            return
        
        DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "Ești un expert în SEO și analiză de site-uri web. Analizezi site-uri și identifici subdomenii și keywords relevante. Răspunde întotdeauna în format JSON valid."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        await websocket.send_json({
            "type": "status",
            "message": "⏳ Așteptare răspuns AI...",
            "progress": 50
        })
        
        # Apelează DeepSeek (fără streaming pentru simplitate)
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            await websocket.send_json({
                "type": "status",
                "message": "✅ Răspuns primit! Procesare rezultate...",
                "progress": 70
            })
            
            data = response.json()
            assistant_message = data["choices"][0]["message"]["content"]
            
            # Extrage JSON din răspuns
            json_match = re.search(r'\{.*\}', assistant_message, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    analysis_result = json_lib.loads(json_str)
                    
                    # Normalizează subdomeniile
                    normalized_subdomains = []
                    for subdomain in analysis_result.get("subdomains", []):
                        if isinstance(subdomain, dict):
                            normalized_subdomains.append({
                                "name": subdomain.get("name", ""),
                                "description": subdomain.get("description", ""),
                                "keywords": subdomain.get("keywords", []),
                                "suggested_keywords": subdomain.get("suggested_keywords", [])
                            })
                        else:
                            normalized_subdomains.append({
                                "name": str(subdomain),
                                "description": "",
                                "keywords": [],
                                "suggested_keywords": []
                            })
                    
                    await websocket.send_json({
                        "type": "status",
                        "message": "💾 Salvare rezultate în baza de date...",
                        "progress": 90
                    })
                    
                    # Salvează în MongoDB
                    analyzer.agents_collection.update_one(
                        {"_id": ObjectId(agent_id)},
                        {
                            "$set": {
                                "subdomains": normalized_subdomains,
                                "overall_keywords": analysis_result.get("overall_keywords", []),
                                "analysis_date": datetime.now(timezone.utc),
                                "analysis_status": "completed"
                            }
                        }
                    )
                    
                    await websocket.send_json({
                        "type": "complete",
                        "message": "✅ Analiză completă cu succes!",
                        "progress": 100,
                        "result": {
                            "ok": True,
                            "subdomains": normalized_subdomains,
                            "overall_keywords": analysis_result.get("overall_keywords", []),
                            "subdomain_count": len(normalized_subdomains),
                            "keyword_count": len(analysis_result.get("overall_keywords", []))
                        }
                    })
                except json_lib.JSONDecodeError as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"❌ Eroare parsare JSON: {str(e)}",
                        "raw_response": assistant_message[:500]
                    })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "❌ Nu s-a găsit JSON în răspuns",
                    "raw_response": assistant_message[:500]
                })
        else:
            await websocket.send_json({
                "type": "error",
                "message": f"❌ Eroare DeepSeek API: {response.status_code}",
                "details": response.text[:200]
            })
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during analysis")
    except Exception as e:
        logger.error(f"Error in WebSocket analysis: {e}")
        logger.error(traceback.format_exc())
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"❌ Eroare: {str(e)}"
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass

@app.put("/api/agents/{agent_id}/subdomains/{subdomain_index}")
async def update_subdomain(agent_id: str, subdomain_index: int, request: dict = Body(...)):
    """
    Actualizează un subdomeniu existent
    """
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        subdomains = agent.get("subdomains", [])
        if subdomain_index >= len(subdomains):
            raise HTTPException(status_code=404, detail="Subdomain not found")
        
        # Actualizează subdomeniul
        updated_subdomain = {
            "name": request.get("name", subdomains[subdomain_index].get("name", "")),
            "description": request.get("description", subdomains[subdomain_index].get("description", "")),
            "keywords": request.get("keywords", subdomains[subdomain_index].get("keywords", [])),
            "suggested_keywords": request.get("suggested_keywords", subdomains[subdomain_index].get("suggested_keywords", []))
        }
        
        subdomains[subdomain_index] = updated_subdomain
        
        agents_collection.update_one(
            {"_id": ObjectId(agent_id)},
            {"$set": {"subdomains": subdomains}}
        )
        
        return {"ok": True, "subdomain": updated_subdomain}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subdomain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/subdomains")
async def add_subdomain(agent_id: str, request: dict = Body(...)):
    """
    Adaugă un subdomeniu nou
    """
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        new_subdomain = {
            "name": request.get("name", ""),
            "description": request.get("description", ""),
            "keywords": request.get("keywords", []),
            "suggested_keywords": request.get("suggested_keywords", [])
        }
        
        subdomains = agent.get("subdomains", [])
        subdomains.append(new_subdomain)
        
        agents_collection.update_one(
            {"_id": ObjectId(agent_id)},
            {"$set": {"subdomains": subdomains}}
        )
        
        return {"ok": True, "subdomain": new_subdomain}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding subdomain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/agents/{agent_id}/subdomains/{subdomain_index}")
async def delete_subdomain(agent_id: str, subdomain_index: int):
    """
    Șterge un subdomeniu
    """
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        subdomains = agent.get("subdomains", [])
        if subdomain_index >= len(subdomains):
            raise HTTPException(status_code=404, detail="Subdomain not found")
        
        subdomains.pop(subdomain_index)
        
        agents_collection.update_one(
            {"_id": ObjectId(agent_id)},
            {"$set": {"subdomains": subdomains}}
        )
        
        return {"ok": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting subdomain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/subdomains/{subdomain_index}/suggest-keywords")
async def suggest_keywords_for_subdomain(agent_id: str, subdomain_index: int):
    """
    Sugerează keywords noi pentru un subdomeniu
    """
    try:
        from agent_analysis_deepseek import AgentAnalysisDeepSeek
        
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        subdomains = agent.get("subdomains", [])
        if subdomain_index >= len(subdomains):
            raise HTTPException(status_code=404, detail="Subdomain not found")
        
        subdomain = subdomains[subdomain_index]
        current_keywords = subdomain.get("keywords", [])
        
        analyzer = AgentAnalysisDeepSeek()
        result = analyzer.suggest_keywords_for_subdomain(
            agent_id,
            subdomain.get("name", ""),
            current_keywords
        )
        
        if result.get("ok"):
            # Adaugă sugestiile la subdomeniu
            subdomain["suggested_keywords"] = result.get("suggested_keywords", [])
            subdomains[subdomain_index] = subdomain
            
            agents_collection.update_one(
                {"_id": ObjectId(agent_id)},
                {"$set": {"subdomains": subdomains}}
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error suggesting keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMPETITIVE STRATEGY - Executare strategie competitivă
# ============================================================================

@app.post("/api/agents/{agent_id}/execute-strategy")
async def execute_competitive_strategy(agent_id: str, request: dict = Body(...)):
    """
    Execută strategia competitivă - DOAR căutare SERP, NU creează agenți:
    - SERP search pentru fiecare keyword
    - Salvează site-urile găsite pentru review
    - Utilizatorul trebuie să aprobe și să selecteze site-urile înainte de creare agenți
    """
    try:
        from competitive_strategy_executor import CompetitiveStrategyExecutor
        import asyncio
        import threading
        
        keywords = request.get("keywords", [])
        results_per_keyword = request.get("results_per_keyword", 20)
        
        if not keywords:
            raise HTTPException(status_code=400, detail="Keywords are required")
        
        executor = CompetitiveStrategyExecutor()
        
        # Rulează în background - DOAR căutare, NU creare agenți
        def run_strategy():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        executor.execute_strategy(
                            agent_id=agent_id,
                            keywords=keywords,
                            results_per_keyword=results_per_keyword
                        )
                    )
                    logger.info(f"✅ Strategy search completed for {agent_id}: {result.get('sites_found', 0)} sites found")
                    return result
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"❌ Error in strategy execution: {e}")
                logger.error(traceback.format_exc())
        
        # Execută în thread separat
        thread = threading.Thread(target=run_strategy, daemon=True)
        thread.start()
        
        # Returnează răspuns imediat - indică că doar căutarea a pornit
        return {
            "ok": True,
            "message": "SERP search started. Sites will be available for review when complete.",
            "keywords_count": len(keywords),
            "estimated_time_minutes": max(1, len(keywords) // 10)  # Paralel (10 keywords/batch) - mult mai rapid!
        }
        
    except Exception as e:
        logger.error(f"Error starting competitive strategy: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/competitive-map")
async def get_competitive_map(agent_id: str):
    """
    Obține harta competitivă pentru agent
    Sincronizează progresul cu numărul real de agenți creați
    """
    try:
        competitive_map = db.competitive_map.find_one({"master_agent_id": agent_id})
        
        if competitive_map:
            # ✅ SINCRONIZARE: Verifică MongoDB pentru slave agents existente și marchează site-urile
            sites = competitive_map.get("competitive_map", [])
            
            # Obține toți slave agents pentru acest master din MongoDB
            slave_agents = list(agents_collection.find({"master_agent_id": ObjectId(agent_id)}))
            slave_agent_domains = {agent.get("domain", "").lower(): str(agent.get("_id")) for agent in slave_agents}
            slave_agent_ids_valid = {str(agent.get("_id")) for agent in slave_agents}
            
            # Marchează site-urile care au deja slave agents în MongoDB
            # Și DEMARCHEAZĂ site-urile care au slave_agent_id invalid
            updated = False
            for site in sites:
                domain = site.get("domain", "").lower()
                current_slave_id = site.get("slave_agent_id")
                
                # Dacă site-ul are un slave_agent_id, verifică dacă este valid
                if current_slave_id and current_slave_id not in slave_agent_ids_valid:
                    # Slave agent ID invalid - demarchează
                    site["has_agent"] = False
                    site["slave_agent_id"] = None
                    updated = True
                    logger.debug(f"⚠️  Demarcat site {domain} - slave_agent_id invalid: {current_slave_id}")
                elif domain in slave_agent_domains:
                    # Site-ul are un slave agent valid în MongoDB
                    slave_id = slave_agent_domains[domain]
                    if not site.get("has_agent", False) or site.get("slave_agent_id") != slave_id:
                        site["has_agent"] = True
                        site["slave_agent_id"] = slave_id
                        updated = True
                        logger.debug(f"✅ Marcat site {domain} ca având agent {slave_id}")
            
            # Salvează actualizarea dacă s-a făcut
            if updated:
                db.competitive_map.update_one(
                    {"master_agent_id": agent_id},
                    {
                        "$set": {
                            "competitive_map": sites,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                logger.info(f"✅ Sincronizat competitive_map cu MongoDB: {len(slave_agent_domains)} slave agents găsite")
            
            # ✅ SINCRONIZARE: Calculează progresul real din site-uri
            selected_sites = [s for s in sites if s.get("selected", False)]
            sites_with_agents = [s for s in sites if s.get("has_agent", False) and s.get("slave_agent_id")]
            
            total_selected = len(selected_sites)
            completed_real = len(sites_with_agents)
            percentage_real = int((completed_real / total_selected) * 100) if total_selected > 0 else 0
            
            # Actualizează progresul în DB dacă este diferit
            current_progress = competitive_map.get("agent_creation_progress", {})
            if current_progress.get("completed", 0) != completed_real:
                db.competitive_map.update_one(
                    {"master_agent_id": agent_id},
                    {
                        "$set": {
                            "agent_creation_progress": {
                                "completed": completed_real,
                                "total": total_selected,
                                "percentage": percentage_real
                            },
                            "slave_agents_created": completed_real,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                logger.info(f"✅ Sincronizat progres: {completed_real}/{total_selected} ({percentage_real}%)")
            
            # Calculează statistici relevanță
            recommended_sites = [s for s in sites if s.get("recommended", False)]
            high_relevance_sites = [s for s in sites if s.get("relevance_score", 0) >= 70]
            analyzed_sites = [s for s in sites if s.get("relevance_score", 50) != 50 or s.get("reasoning", "")]
            
            # ✅ Adaugă progresul execuției strategiei
            execution_progress = competitive_map.get("execution_progress", {}) or {}
            execution_status = competitive_map.get("execution_status", "not_started") or "not_started"
            keywords_processed = competitive_map.get("keywords_processed", 0) or 0
            
            # Debug logging - FORCE LOG
            logger.info(f"📊 Competitive map response for {agent_id}: execution_status={execution_status}, execution_progress={execution_progress}, keywords_processed={keywords_processed}")
            print(f"📊 DEBUG: execution_status={execution_status}, execution_progress={execution_progress}, keywords_processed={keywords_processed}")
            
            response_data = {
                "ok": True,
                "competitive_map": sites,
                "keywords_used": competitive_map.get("keywords_used", []),
                "keyword_site_mapping": competitive_map.get("keyword_site_mapping", {}),  # Keyword → site-uri cu poziții
                "sites_found": competitive_map.get("sites_found", len(sites)),
                "keywords_processed": int(keywords_processed),  # ✅ Keywords procesate - FORCE INT
                "slave_agents_created": completed_real,  # ✅ Număr real
                "execution_status": str(execution_status),  # ✅ Status execuție (running, completed, failed) - FORCE STR
                "execution_progress": dict(execution_progress) if execution_progress else {},  # ✅ Progres execuție {keywords_processed, keywords_total, percentage} - FORCE DICT
                "relevance_analysis_status": competitive_map.get("relevance_analysis_status", "not_started"),
                "relevance_analyzed": competitive_map.get("relevance_analyzed", False),
                "relevance_analysis_date": str(competitive_map.get("relevance_analysis_date")) if competitive_map.get("relevance_analysis_date") else None,  # ✅ Convert datetime to string
                "relevance_analysis_progress": competitive_map.get("relevance_analysis_progress", None),
                "recommended_sites_count": len(recommended_sites),  # ✅ Număr site-uri recomandate
                "high_relevance_sites_count": len(high_relevance_sites),  # ✅ Număr site-uri cu relevance >= 70
                "analyzed_sites_count": len(analyzed_sites),  # ✅ Număr site-uri analizate
                "agent_creation_status": competitive_map.get("agent_creation_status", "not_started"),  # Status creare agenți
                "agent_creation_progress": {  # ✅ Progres sincronizat
                    "completed": completed_real,
                    "total": total_selected,
                    "percentage": percentage_real
                },
                "status": competitive_map.get("agent_creation_status", "not_started"),  # Alias pentru compatibilitate
                "created_at": str(competitive_map.get("created_at")) if competitive_map.get("created_at") else None,  # ✅ Convert datetime to string
                "updated_at": str(competitive_map.get("updated_at")) if competitive_map.get("updated_at") else None  # ✅ Convert datetime to string
            }
            
            # Debug - verifică ce se returnează
            logger.info(f"📊 Response data keys: {list(response_data.keys())}")
            logger.info(f"📊 Response execution_status: {response_data.get('execution_status')}")
            logger.info(f"📊 Response execution_progress: {response_data.get('execution_progress')}")
            logger.info(f"📊 Response keywords_processed: {response_data.get('keywords_processed')}")
            
            # ✅ FORCE JSONResponse pentru a asigura că toate câmpurile sunt returnate
            from fastapi.responses import JSONResponse
            return JSONResponse(content=response_data)
        else:
            return {
                "ok": True,
                "competitive_map": [],
                "keywords_used": [],
                "keyword_site_mapping": {},
                "sites_found": 0,
                "keywords_processed": 0,
                "slave_agents_created": 0,
                "execution_status": "not_started",
                "execution_progress": None
            }
            
    except Exception as e:
        logger.error(f"Error getting competitive map: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/agents/{agent_id}/competitive-map/sites/{site_domain}")
async def update_site_selection(agent_id: str, site_domain: str, request: dict = Body(...)):
    """
    Actualizează selecția unui site (select/deselect) sau adaugă/elimină site-uri
    """
    try:
        competitive_map = db.competitive_map.find_one({"master_agent_id": agent_id})
        if not competitive_map:
            raise HTTPException(status_code=404, detail="Competitive map not found. Run strategy first.")
        
        competitive_map_data = competitive_map.get("competitive_map", [])
        
        # Caută site-ul
        site_index = None
        for i, site in enumerate(competitive_map_data):
            if site.get("domain") == site_domain:
                site_index = i
                break
        
        action = request.get("action", "toggle_selection")
        
        if action == "toggle_selection":
            if site_index is not None:
                # Toggle selection
                competitive_map_data[site_index]["selected"] = not competitive_map_data[site_index].get("selected", False)
            else:
                raise HTTPException(status_code=404, detail="Site not found")
        elif action == "remove":
            if site_index is not None:
                competitive_map_data.pop(site_index)
            else:
                raise HTTPException(status_code=404, detail="Site not found")
        elif action == "add":
            # Adaugă site nou
            new_site = {
                "domain": site_domain,
                "url": request.get("url", f"https://{site_domain}"),
                "rank": len(competitive_map_data) + 1,
                "appearances": 0,
                "best_position": 100,
                "total_rank": 0,
                "keywords": request.get("keywords", []),
                "relevance_score": request.get("relevance_score", 50),
                "selected": True,
                "slave_agent_id": None,
                "has_agent": False
            }
            competitive_map_data.append(new_site)
        
        # Salvează actualizarea
        db.competitive_map.update_one(
            {"master_agent_id": agent_id},
            {
                "$set": {
                    "competitive_map": competitive_map_data,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return {"ok": True, "message": "Site updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating site selection: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/competitive-map/select-recommended")
async def select_recommended_sites(agent_id: str):
    """
    Selectează automat toate site-urile recomandate (recommended = true)
    """
    try:
        competitive_map = db.competitive_map.find_one({"master_agent_id": agent_id})
        if not competitive_map:
            raise HTTPException(status_code=404, detail="Competitive map not found. Run strategy first.")
        
        competitive_map_data = competitive_map.get("competitive_map", [])
        
        # Selectează toate site-urile recomandate care nu au deja agenți
        selected_count = 0
        for site in competitive_map_data:
            if (site.get("recommended", False) and 
                not site.get("selected", False) and 
                not site.get("has_agent", False)):
                site["selected"] = True
                selected_count += 1
        
        # Salvează actualizarea
        db.competitive_map.update_one(
            {"master_agent_id": agent_id},
            {
                "$set": {
                    "competitive_map": competitive_map_data,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return {"ok": True, "message": f"Selected {selected_count} recommended sites successfully", "selected_count": selected_count}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting recommended sites: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/competitive-map/select-multiple")
async def select_multiple_sites(agent_id: str, request: dict = Body(...)):
    """
    Selectează multiple site-uri deodată (pentru performanță)
    """
    try:
        competitive_map = db.competitive_map.find_one({"master_agent_id": agent_id})
        if not competitive_map:
            raise HTTPException(status_code=404, detail="Competitive map not found. Run strategy first.")
        
        competitive_map_data = competitive_map.get("competitive_map", [])
        domains_to_select = request.get("domains", [])
        threshold = request.get("threshold", None)
        
        if threshold is not None:
            # Selectează toate site-urile cu relevanță >= threshold
            selected_count = 0
            for site in competitive_map_data:
                if (site.get("relevance_score", 0) >= threshold and 
                    not site.get("selected", False) and 
                    not site.get("has_agent", False)):
                    site["selected"] = True
                    selected_count += 1
        else:
            # Selectează site-urile specificate
            selected_count = 0
            for domain in domains_to_select:
                for site in competitive_map_data:
                    if site.get("domain") == domain and not site.get("has_agent", False):
                        site["selected"] = True
                        selected_count += 1
                        break
        
        # Salvează actualizarea
        db.competitive_map.update_one(
            {"master_agent_id": agent_id},
            {
                "$set": {
                    "competitive_map": competitive_map_data,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return {"ok": True, "message": f"Selected {selected_count} sites successfully", "selected_count": selected_count}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting multiple sites: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/competitive-map/create-agents")
async def create_agents_from_selected_sites(agent_id: str):
    """
    Creează agenți doar pentru site-urile selectate din competitive map
    Folosește aceeași metodă ca pentru master agents, optimizată pentru paralelism pe GPU
    Înregistrează workflow-ul pentru monitorizare
    """
    try:
        from master_slave_learning_system import MasterSlaveLearningSystem
        import asyncio
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        competitive_map = db.competitive_map.find_one({"master_agent_id": agent_id})
        if not competitive_map:
            raise HTTPException(status_code=404, detail="Competitive map not found. Run strategy first.")
        
        competitive_map_data = competitive_map.get("competitive_map", [])
        selected_sites = [site for site in competitive_map_data if site.get("selected", False)]
        
        if not selected_sites:
            raise HTTPException(status_code=400, detail="No sites selected. Please select sites first.")
        
        # Verifică dacă există deja un proces în curs
        current_status = competitive_map.get("agent_creation_status", "not_started")
        if current_status == "in_progress":
            raise HTTPException(status_code=400, detail="Agent creation is already in progress. Stop it first if you want to restart.")
        
        # ✅ Înregistrează workflow-ul în ceo_workflow_executions pentru monitorizare
        workflow_id = f"slave_creation_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        workflow_doc = {
            "workflow_id": workflow_id,
            "workflow_type": "slave_agent_creation",
            "agent_id": agent_id,
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "progress": {
                "completed": 0,
                "total": len(selected_sites),
                "percentage": 0
            },
            "steps": [
                {
                    "step": "agent_creation",
                    "status": "in_progress",
                    "description": f"Creating {len(selected_sites)} slave agents",
                    "started_at": datetime.now(timezone.utc)
                }
            ]
        }
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Detectează automat numărul real de GPU-uri disponibile
        import torch
        num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0
        reserved_gpu_ids = {6, 7}
        available_gpu_ids = [gpu_id for gpu_id in range(num_gpus) if gpu_id not in reserved_gpu_ids]
        available_gpu_count = len(available_gpu_ids)
        
        overhead_workers = 2  # Pentru I/O, scraping, etc.
        optimal_parallel = available_gpu_count + overhead_workers if available_gpu_count > 0 else 5
        
        parallel_gpu_agents = min(optimal_parallel, len(selected_sites))
        max_parallel_override = int(os.getenv("SLAVE_CREATION_MAX_PARALLEL", "0") or "0")
        if max_parallel_override > 0:
            parallel_gpu_agents = min(max_parallel_override, len(selected_sites))
        logger.info(
            f"🚀 GPU-uri detectate: {num_gpus} | GPU-uri disponibile: {available_gpu_count} "
            f"(rezervate: {sorted(reserved_gpu_ids)}) | Worker-uri paralele: {parallel_gpu_agents}"
        )
        
        db.ceo_workflow_executions.insert_one(workflow_doc)
        logger.info(f"📊 Workflow înregistrat: {workflow_id} pentru {len(selected_sites)} agenți")
        
        # ✅ Înregistrează în workflow_tracking pentru Workflow Tracker
        try:
            from workflow_tracking_system import WorkflowTracker, WorkflowStep, StepStatus
            from config.database_config import MONGODB_URI
            from pymongo import MongoClient
            
            tracking_client = MongoClient(MONGODB_URI)
            workflow_tracker = WorkflowTracker(tracking_client)
            
            # Track începutul creării agenților slave
            workflow_tracker.track_step(
                step=WorkflowStep.SLAVE_AGENT_CREATED,
                agent_id=agent_id,
                status=StepStatus.IN_PROGRESS,
                details={
                    "total_sites": len(selected_sites),
                    "workflow_id": workflow_id
                },
                metadata={
                    "sites_count": len(selected_sites),
                    "parallel_workers": parallel_gpu_agents
                }
            )
            logger.info(f"📊 Workflow tracking activat pentru agent {agent_id}")
        except Exception as e:
            logger.warning(f"⚠️ Nu s-a putut activa workflow tracking: {e}")
        
        # Rulează crearea agenților în background cu paralelism pe GPU (folosind aceeași metodă ca master agents)
        def create_agents():
            try:
                # Filtrează site-urile care nu au deja agenți
                sites_to_process = [
                    site for site in selected_sites 
                    if not (site.get("has_agent") and site.get("slave_agent_id"))
                ]
                
                if not sites_to_process:
                    logger.info("   All sites already have agents")
                    return
                
                sites_target_total = len(sites_to_process)
                start_time = datetime.now(timezone.utc)
                estimated_total_minutes = max(5, sites_target_total * 2)

                def compute_timing(created_count: int):
                    now = datetime.now(timezone.utc)
                    elapsed_minutes = max(0, (now - start_time).total_seconds() / 60)
                    if created_count > 0:
                        avg_time_per_site = elapsed_minutes / created_count
                        remaining_minutes = max(0, avg_time_per_site * max(sites_target_total - created_count, 0))
                    else:
                        remaining_minutes = max(0, estimated_total_minutes - elapsed_minutes)
                    return {
                        "start_time": start_time.isoformat(),
                        "estimated_total_minutes": estimated_total_minutes,
                        "elapsed_minutes": round(elapsed_minutes, 2),
                        "remaining_minutes": round(remaining_minutes, 2),
                        "sites_to_create": sites_target_total,
                        "sites_created": created_count,
                        "last_update": now.isoformat()
                    }
                
                # Setează status "in_progress" la început
                db.competitive_map.update_one(
                    {"master_agent_id": agent_id},
                    {
                        "$set": {
                            "agent_creation_status": "in_progress",
                            "agent_creation_progress": {
                                "completed": 0,
                                "total": len(sites_to_process),
                                "percentage": 0
                            },
                            "agent_creation_timing": compute_timing(0),
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                logger.info(f"🚀 Starting parallel agent creation for {len(sites_to_process)} sites using {parallel_gpu_agents} GPU workers")
                logger.info(f"   Using same method as master agent creation (CEOMasterWorkflow style)")
                
                # Creează event loop pentru async operations
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Folosește MasterSlaveLearningSystem (aceeași metodă ca pentru master agents)
                    learning_system = MasterSlaveLearningSystem()
                    
                    slave_agents_created = 0
                    failed_count = 0
                    
                    # Procesează site-urile în batch-uri paralele (folosind asyncio.gather pentru paralelism real)
                    async def create_agents_parallel():
                        nonlocal slave_agents_created, failed_count
                        
                        # Procesează în batch-uri de parallel_gpu_agents pentru a controla paralelismul
                        # Optimizat pentru utilizare maximă - folosește toate GPU-urile disponibile simultan
                        total_batches = (len(sites_to_process) + parallel_gpu_agents - 1) // parallel_gpu_agents
                        
                        for batch_start in range(0, len(sites_to_process), parallel_gpu_agents):
                            batch_sites = sites_to_process[batch_start:batch_start + parallel_gpu_agents]
                            batch_num = (batch_start // parallel_gpu_agents) + 1
                            
                            logger.info(f"   ⚡ Processing batch {batch_num}/{total_batches} ({len(batch_sites)} sites in parallel on {num_gpus} GPU-uri)")
                            
                            # Creează task-uri pentru batch-ul curent (NU pentru toate deodată)
                            # Distribuie pe GPU-uri diferite pentru utilizare maximă
                            # Numărul de GPU-uri a fost deja detectat mai sus
                            
                            batch_tasks = []
                            for idx, site in enumerate(batch_sites):
                                site_url = site.get("url", f"https://{site['domain']}")
                                keyword = site.get("keywords", [""])[0] if site.get("keywords") else "unknown"
                                position = site.get("best_position", 100)
                                
                                # Distribuie pe GPU-uri disponibile (excludem GPU-urile rezervate pentru Qwen)
                                gpu_id = None
                                if available_gpu_ids:
                                    gpu_id = available_gpu_ids[idx % len(available_gpu_ids)]
                                
                                # Log pentru debugging - verifică distribuția
                                logger.info(f"   📍 Task {batch_start + idx}: {site.get('domain', 'unknown')[:30]}... → GPU {gpu_id}")
                                
                                # Creează coroutine pentru fiecare site în batch cu GPU specific
                                task = learning_system.create_slave_from_competitor(
                                    competitor_url=site_url,
                                    master_agent_id=agent_id,
                                    keyword=keyword,
                                    serp_position=position,
                                    gpu_id=gpu_id  # Pasează GPU ID pentru distribuție
                                )
                                batch_tasks.append((task, site, batch_start + idx, gpu_id))
                            
                            # Rulează batch-ul în paralel - toate GPU-urile active simultan
                            # asyncio.gather rulează toate task-urile simultan, fiecare pe GPU-ul său
                            results = await asyncio.gather(*[task for task, _, _, _ in batch_tasks], return_exceptions=True)
                            
                            # Procesează rezultatele batch-ului
                            for (_, site, idx, gpu_id), result in zip(batch_tasks, results):
                                try:
                                    if isinstance(result, Exception):
                                        raise result
                                    
                                    if result.get("success"):
                                        slave_id = result.get("slave_agent_id")
                                        site["slave_agent_id"] = slave_id
                                        site["has_agent"] = True
                                        slave_agents_created += 1
                                        logger.info(f"   ✅ [{idx+1}/{len(sites_to_process)}] Created agent: {site['domain']} (Total: {slave_agents_created})")
                                        
                                        # ✅ ACTUALIZARE LIVE: Actualizează progresul după fiecare agent creat
                                        sites_with_agents_real = [s for s in competitive_map_data if s.get("has_agent", False) and s.get("slave_agent_id")]
                                        completed_real = len(sites_with_agents_real)
                                        total_selected = len([s for s in competitive_map_data if s.get("selected", False)])
                                        percentage_real = int((completed_real / total_selected) * 100) if total_selected > 0 else 0
                                        
                                        # Actualizează imediat în MongoDB pentru progres live
                                        db.competitive_map.update_one(
                                            {"master_agent_id": agent_id},
                                            {
                                                "$set": {
                                                    "competitive_map": competitive_map_data,
                                                    "slave_agents_created": completed_real,
                                                    "agent_creation_status": "in_progress",
                                                    "agent_creation_progress": {
                                                        "completed": completed_real,
                                                        "total": total_selected,
                                                        "percentage": percentage_real
                                                    },
                                                    "agent_creation_timing": compute_timing(slave_agents_created),
                                                    "updated_at": datetime.now(timezone.utc)
                                                }
                                            }
                                        )
                                        logger.info(f"   📊 Progres LIVE actualizat: {completed_real}/{total_selected} ({percentage_real}%)")
                                        
                                        # ✅ Track fiecare agent creat în workflow_tracking
                                        try:
                                            from workflow_tracking_system import WorkflowTracker, WorkflowStep, StepStatus
                                            from config.database_config import MONGODB_URI
                                            from pymongo import MongoClient
                                            
                                            tracking_client = MongoClient(MONGODB_URI)
                                            workflow_tracker = WorkflowTracker(tracking_client)
                                            
                                            workflow_tracker.complete_step(
                                                step=WorkflowStep.SLAVE_AGENT_CREATED,
                                                agent_id=slave_id,  # Track pentru slave agent
                                                details={
                                                    "master_agent_id": agent_id,
                                                    "domain": site.get("domain"),
                                                    "slave_agent_id": slave_id
                                                }
                                            )
                                        except Exception as e:
                                            logger.debug(f"Workflow tracking skip pentru {site['domain']}: {e}")
                                    else:
                                        failed_count += 1
                                        logger.warning(f"   ❌ [{idx+1}/{len(sites_to_process)}] Failed: {site['domain']} - {result.get('error')}")
                                except Exception as e:
                                    failed_count += 1
                                    logger.error(f"   ❌ [{idx+1}/{len(sites_to_process)}] Exception: {site['domain']} - {e}")
                            
                            # ✅ ACTUALIZARE FINALĂ BATCH: Actualizează progresul după batch complet
                            sites_with_agents_real = [s for s in competitive_map_data if s.get("has_agent", False) and s.get("slave_agent_id")]
                            completed_real = len(sites_with_agents_real)
                            total_selected = len([s for s in competitive_map_data if s.get("selected", False)])
                            percentage_real = int((completed_real / total_selected) * 100) if total_selected > 0 else 0
                            
                            db.competitive_map.update_one(
                                {"master_agent_id": agent_id},
                                {
                                    "$set": {
                                        "competitive_map": competitive_map_data,
                                        "slave_agents_created": completed_real,  # ✅ Număr real
                                        "agent_creation_status": "in_progress",
                                        "agent_creation_progress": {
                                            "completed": completed_real,  # ✅ Progres real
                                            "total": total_selected,
                                            "percentage": percentage_real
                                        },
                                        "agent_creation_timing": compute_timing(slave_agents_created),
                                        "updated_at": datetime.now(timezone.utc)
                                    }
                                }
                            )
                            logger.info(f"   📊 Progres batch finalizat: {completed_real}/{total_selected} ({percentage_real}%)")
                    
                    # Rulează crearea agenților în paralel
                    loop.run_until_complete(create_agents_parallel())
                    
                    # ✅ SINCRONIZARE: Actualizează progresul real din site-uri
                    sites_with_agents_final = [s for s in competitive_map_data if s.get("has_agent", False) and s.get("slave_agent_id")]
                    completed_final = len(sites_with_agents_final)
                    total_selected_final = len([s for s in competitive_map_data if s.get("selected", False)])
                    percentage_final = int((completed_final / total_selected_final) * 100) if total_selected_final > 0 else 0
                    
                    # Actualizare finală în MongoDB
                    db.competitive_map.update_one(
                        {"master_agent_id": agent_id},
                        {
                            "$set": {
                                "competitive_map": competitive_map_data,
                                "slave_agents_created": completed_final,  # ✅ Număr real
                                "agent_creation_status": "completed",
                                "agent_creation_progress": {
                                    "completed": completed_final,  # ✅ Progres real
                                    "total": total_selected_final,
                                    "percentage": percentage_final
                                },
                                "agent_creation_timing": compute_timing(slave_agents_created),
                                "status": "completed",  # Alias pentru compatibilitate
                                "updated_at": datetime.now(timezone.utc)
                            }
                        }
                    )
                    
                    # ✅ Actualizează workflow-ul în ceo_workflow_executions
                    db.ceo_workflow_executions.update_one(
                        {"workflow_id": workflow_id},
                        {
                            "$set": {
                                "status": "completed",
                                "progress": {
                                    "completed": completed_final,
                                    "total": total_selected_final,
                                    "percentage": percentage_final
                                },
                                "steps": [
                                    {
                                        "step": "agent_creation",
                                        "status": "completed",
                                        "description": f"Created {completed_final} slave agents",
                                        "completed_at": datetime.now(timezone.utc)
                                    }
                                ],
                                "updated_at": datetime.now(timezone.utc)
                            }
                        }
                    )
                    
                    # ✅ Completează workflow tracking pentru master agent
                    try:
                        from workflow_tracking_system import WorkflowTracker, WorkflowStep, StepStatus
                        from config.database_config import MONGODB_URI
                        from pymongo import MongoClient
                        
                        tracking_client = MongoClient(MONGODB_URI)
                        workflow_tracker = WorkflowTracker(tracking_client)
                        
                        workflow_tracker.complete_step(
                            step=WorkflowStep.SLAVE_AGENT_CREATED,
                            agent_id=agent_id,
                            details={
                                "total_created": completed_final,
                                "total_processed": len(sites_to_process),
                                "failed": failed_count,
                                "workflow_id": workflow_id
                            }
                        )
                        logger.info(f"📊 Workflow tracking completat pentru agent {agent_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Nu s-a putut completa workflow tracking: {e}")
                    
                    logger.info(f"✅ Created {completed_final} agents for {agent_id} (out of {len(sites_to_process)} processed, {failed_count} failed)")
                    logger.info(f"📊 Workflow {workflow_id} completed")
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"❌ Error creating agents: {e}")
                logger.error(traceback.format_exc())
                db.competitive_map.update_one(
                    {"master_agent_id": agent_id},
                    {
                        "$set": {
                            "agent_creation_status": "failed",
                            "status": "failed",  # Alias pentru compatibilitate
                            "error": str(e),
                            "agent_creation_timing": compute_timing(slave_agents_created),
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                # ✅ Actualizează workflow-ul ca failed
                try:
                    db.ceo_workflow_executions.update_one(
                        {"workflow_id": workflow_id},
                        {
                            "$set": {
                                "status": "failed",
                                "error": str(e),
                                "updated_at": datetime.now(timezone.utc)
                            }
                        }
                    )
                except:
                    pass
                
                # ✅ Actualizează workflow-ul ca failed
                db.ceo_workflow_executions.update_one(
                    {"workflow_id": workflow_id},
                    {
                        "$set": {
                            "status": "failed",
                            "error": str(e),
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
        
        # Execută în thread separat
        thread = threading.Thread(target=create_agents, daemon=True)
        thread.start()
        
        return {
            "ok": True,
            "message": "Agent creation started",
            "workflow_id": workflow_id,
            "sites_selected": len(selected_sites),
            "estimated_time_minutes": len(selected_sites) * 2
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting agent creation: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/competitive-map/stop-creation")
async def stop_agent_creation(agent_id: str):
    """
    Oprește procesul de creare a agenților
    """
    try:
        competitive_map = db.competitive_map.find_one({"master_agent_id": agent_id})
        if not competitive_map:
            raise HTTPException(status_code=404, detail="Competitive map not found.")
        
        # Setează statusul la "stopped" pentru a permite repornirea
        db.competitive_map.update_one(
            {"master_agent_id": agent_id},
            {
                "$set": {
                    "agent_creation_status": "stopped",
                    "status": "stopped",
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.info(f"🛑 Agent creation stopped for {agent_id}")
        
        return {
            "ok": True,
            "message": "Agent creation stopped. You can restart it now."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping agent creation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/competitive-map/analyze-relevance")
async def analyze_sites_relevance(agent_id: str, background_tasks: BackgroundTasks):
    """
    Analizează relevanța site-urilor găsite folosind DeepSeek + Qwen (GPU) pentru procesare paralelă
    Compară site-urile cu industria agentului master și subdomeniile generate
    Folosește Qwen pe GPU pentru procesare batch rapidă
    Rulează în background pentru a evita timeout-uri
    """
    try:
        import threading
        import os
        import requests
        import json as json_lib
        import re
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        # Obține datele agentului master
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        domain = agent.get("domain", "")
        industry = agent.get("industry", "")
        subdomains = agent.get("subdomains", [])
        
        # Obține competitive map
        competitive_map = db.competitive_map.find_one({"master_agent_id": agent_id})
        if not competitive_map:
            raise HTTPException(status_code=404, detail="Competitive map not found. Run strategy first.")
        
        competitive_map_data = competitive_map.get("competitive_map", [])
        
        if not competitive_map_data:
            raise HTTPException(status_code=400, detail="No sites found. Run strategy first.")
        
        # Construiește context pentru analiză
        subdomains_text = ""
        for subdomain in subdomains:
            if isinstance(subdomain, dict):
                subdomains_text += f"- {subdomain.get('name', '')}: {subdomain.get('description', '')}\n"
        
        # Verifică dacă Qwen este disponibil
        QWEN_AVAILABLE = False
        try:
            qwen_response = requests.get("http://localhost:9201/health", timeout=2)
            if qwen_response.status_code == 200:
                QWEN_AVAILABLE = True
        except:
            pass
        
        # Procesare batch cu Qwen (GPU) pentru site-uri multiple
        def analyze_batch_with_qwen(sites_batch, batch_num):
            """Procesează un batch de site-uri cu Qwen pe GPU"""
            if not QWEN_AVAILABLE:
                return None
            
            try:
                sites_list = []
                for site in sites_batch:
                    keyword_strs = []
                    for kp in site.get('keyword_positions', [])[:5]:
                        keyword_strs.append(f"{kp['keyword']} (pos {kp['position']})")
                    sites_list.append(f"- {site['domain']}: {site['appearances']} appearances, keywords: {', '.join(keyword_strs)}")
                sites_text = "\n".join(sites_list)
                
                prompt = f"""Analizează relevanța acestor site-uri pentru industria "{industry}" și site-ul {domain}.

INDUSTRIA ȘI SUBDOMENIILE:
Industrie: {industry}
Subdomenii identificate:
{subdomains_text}

SITE-URI (batch {batch_num}):
{sites_text}

CRITERII DE ANALIZĂ:
1. INDUSTRY_MATCH: Site-ul se potrivește cu industria "{industry}"?
   - Verifică dacă site-ul oferă servicii/produse în aceeași industrie
   - Verifică dacă keywords-urile sunt relevante pentru industrie
   
2. SUBDOMAIN_MATCHES: Care subdomenii se potrivesc?
   - Compară conținutul site-ului cu subdomeniile identificate
   - Ex: dacă site-ul are "servicii", se potrivește cu subdomeniul "servicii"
   
3. RELEVANCE_SCORE (0-100):
   - 90-100: Foarte relevant, aceeași industrie, keywords perfecte
   - 70-89: Relevant, industrie similară, keywords bune
   - 50-69: Parțial relevant, conexiuni slabe
   - 0-49: Nu relevant, industrie diferită
   
4. RECOMMENDED (true/false):
   - true: Site-ul este recomandat pentru creare agent (relevance_score >= 70)
   - false: Site-ul nu este recomandat (relevance_score < 70)

Pentru fiecare site, returnează JSON:
{{
  "sites_relevance": [
    {{
      "domain": "example.com",
      "relevance_score": 85,
      "industry_match": true,
      "subdomain_matches": ["servicii"],
      "reasoning": "Site-ul este relevant pentru că oferă servicii în aceeași industrie și keywords-urile se potrivesc perfect cu subdomeniul 'servicii'.",
      "recommended": true
    }}
  ]
}}"""
                
                qwen_url = "http://localhost:9201/v1/chat/completions"
                payload = {
                    "model": "Qwen/Qwen2.5-7B-Instruct",
                    "messages": [
                        {
                            "role": "system",
                            "content": """Ești un expert în analiză de relevanță pentru SEO. 
Analizezi site-uri și evaluezi relevanța lor folosind criterii STRICTE:
1. INDUSTRY_MATCH: Potrivire cu industria
2. SUBDOMAIN_MATCHES: Potrivire cu subdomeniile
3. RELEVANCE_SCORE: 0-100 (70+ = recommended)
4. RECOMMENDED: true doar dacă score >= 70 ȘI industry_match = true
Răspunde întotdeauna în format JSON valid cu reasoning detaliat."""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
                
                response = requests.post(qwen_url, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        return json_lib.loads(json_match.group(0))
            except Exception as e:
                logger.error(f"Error in Qwen batch {batch_num}: {e}")
            return None
        
        # Procesare cu DeepSeek pentru analiza inițială
        def analyze_with_deepseek(sites_summary_batch):
            """Procesează cu DeepSeek pentru un batch de site-uri"""
            DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
            if not DEEPSEEK_API_KEY:
                return None
            
            prompt = f"""Analizează relevanța site-urilor găsite pentru industria "{industry}" și site-ul {domain}.

INDUSTRIA ȘI SUBDOMENIILE:
Industrie: {industry}
Subdomenii identificate:
{subdomains_text}

SITE-URI GĂSITE:
{chr(10).join(sites_summary_batch)}

CRITERII DE ANALIZĂ (FOARTE IMPORTANT):
1. INDUSTRY_MATCH: Site-ul se potrivește cu industria "{industry}"?
   - Verifică dacă site-ul oferă servicii/produse în aceeași industrie
   - Verifică dacă keywords-urile sunt relevante pentru industrie
   - Ex: pentru "amenajari interioare", site-uri de design interior = relevant
   
2. SUBDOMAIN_MATCHES: Care subdomenii se potrivesc?
   - Compară conținutul site-ului cu subdomeniile identificate
   - Ex: dacă site-ul are "servicii amenajari", se potrivește cu subdomeniul "servicii"
   - Ex: dacă site-ul are "produse mobilier", se potrivește cu subdomeniul "produse"
   
3. RELEVANCE_SCORE (0-100) - CALCULEAZĂ CU PRECIZIE:
   - 90-100: Foarte relevant - aceeași industrie, keywords perfecte, subdomenii se potrivesc
   - 70-89: Relevant - industrie similară, keywords bune, subdomenii parțial
   - 50-69: Parțial relevant - conexiuni slabe, keywords generale
   - 0-49: Nu relevant - industrie diferită, keywords irelevante
   
4. RECOMMENDED (true/false):
   - true: Site-ul este recomandat pentru creare agent (relevance_score >= 70 ȘI industry_match = true)
   - false: Site-ul nu este recomandat (relevance_score < 70 SAU industry_match = false)

Returnează JSON cu structura:
{{
  "sites_relevance": [
    {{
      "domain": "example.com",
      "relevance_score": 85,
      "industry_match": true,
      "subdomain_matches": ["servicii", "produse"],
      "reasoning": "Site-ul este relevant pentru că oferă servicii în aceeași industrie '{industry}', keywords-urile se potrivesc perfect cu subdomeniile 'servicii' și 'produse', și pozițiile bune în căutări indică relevanță.",
      "recommended": true
    }}
  ]
}}

ANALIZEAZĂ TOATE SITE-URILE ȘI RETURNEAZĂ SCORURI PRECISE!"""
            
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": """Ești un expert în analiză de relevanță pentru SEO și competitive intelligence. 
Analizezi site-uri și evaluezi relevanța lor pentru o industrie specifică folosind următoarele criterii STRICTE:

1. INDUSTRY_MATCH: Verifică dacă site-ul oferă servicii/produse în aceeași industrie
2. SUBDOMAIN_MATCHES: Compară keywords-urile site-ului cu subdomeniile identificate
3. RELEVANCE_SCORE: Calculează scor 0-100 bazat pe:
   - Potrivire industrie (40%)
   - Potrivire keywords cu subdomenii (30%)
   - Calitatea keywords-urilor (20%)
   - Pozițiile în căutări (10%)
4. RECOMMENDED: true doar dacă relevance_score >= 70 ȘI industry_match = true

Răspunde întotdeauna în format JSON valid cu reasoning detaliat."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 4000
            }
            
            response = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json_lib.loads(json_match.group(0))
            return None
        
        # Verifică dacă există progres parțial - CONTINUĂ DE UNDE A RĂMAS
        existing_progress = competitive_map.get("relevance_analysis_progress", {})
        existing_analyzed = existing_progress.get("analyzed", 0)
        existing_status = competitive_map.get("relevance_analysis_status", "not_started")
        
        # Dacă analiza este deja completă, nu o reîncepe
        if existing_status == "completed":
            # Verifică dacă toate site-urile sunt de fapt analizate
            actually_analyzed = len([s for s in competitive_map_data 
                                     if s.get("relevance_score", 50) != 50 or s.get("reasoning", "")])
            total_sites = len(competitive_map_data)
            
            if actually_analyzed >= total_sites:
                return {
                    "ok": True,
                    "message": "Relevance analysis already completed. All sites have been analyzed.",
                    "analyzed": actually_analyzed,
                    "total": total_sites,
                    "already_completed": True
                }
            else:
                # Dacă nu toate site-urile sunt analizate, continuă analiza
                logger.info(f"⚠️  Analysis marked as completed but only {actually_analyzed}/{total_sites} sites analyzed. Continuing...")
                # Continuă mai jos pentru a reanaliza site-urile lipsă
        
        # Dacă există progres parțial, continuă de unde a rămas
        if existing_analyzed > 0 and existing_status == "in_progress":
            logger.info(f"🔄 Continuing relevance analysis from {existing_analyzed}/{len(competitive_map_data)} sites")
            # Nu resetează progresul, doar marchează că continuă
            db.competitive_map.update_one(
                {"master_agent_id": agent_id},
                {
                    "$set": {
                        "relevance_analysis_status": "in_progress",
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        else:
            # Prima dată - marchează că analiza a început
            db.competitive_map.update_one(
                {"master_agent_id": agent_id},
                {
                    "$set": {
                        "relevance_analysis_status": "in_progress",
                        "relevance_analysis_started": datetime.now(timezone.utc),
                        "relevance_analysis_progress": {
                            "analyzed": 0,
                            "total": len(competitive_map_data),
                            "percentage": 0
                        },
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        
        # Rulează analiza în background cu updates live
        def run_relevance_analysis():
            try:
                total_sites = len(competitive_map_data)
                
                # CONTINUĂ DE UNDE A RĂMAS - nu reanalizează site-urile deja analizate
                existing_progress = competitive_map.get("relevance_analysis_progress", {})
                analyzed_count = existing_progress.get("analyzed", 0)
                
                # Identifică site-urile deja analizate (au relevance_score != 50 sau au reasoning)
                already_analyzed_domains = set()
                sites_to_analyze = []
                
                for site in competitive_map_data:
                    domain = site.get("domain", "")
                    # Site-ul este deja analizat dacă are relevance_score != 50 SAU are reasoning
                    if (site.get("relevance_score", 50) != 50) or (site.get("reasoning", "")):
                        already_analyzed_domains.add(domain)
                    else:
                        sites_to_analyze.append(site)
                
                logger.info(f"🔄 Continuing analysis: {analyzed_count}/{total_sites} already analyzed, {len(sites_to_analyze)} remaining")
                
                if len(sites_to_analyze) == 0:
                    logger.info("✅ All sites already analyzed! Marking as completed.")
                    db.competitive_map.update_one(
                        {"master_agent_id": agent_id},
                        {
                            "$set": {
                                "relevance_analysis_status": "completed",
                                "relevance_analyzed": True,
                                "relevance_analysis_date": datetime.now(timezone.utc),
                                "relevance_analysis_progress": {
                                    "analyzed": total_sites,
                                    "total": total_sites,
                                    "percentage": 100
                                },
                                "updated_at": datetime.now(timezone.utc)
                            }
                        }
                    )
                    return
                
                # Pregătește site-uri pentru analiză (doar cele neanalizate)
                sites_summary = []
                for site in sites_to_analyze:
                    keyword_positions = site.get("keyword_positions", [])
                    keywords_text = ", ".join([f"{kp['keyword']} (pos {kp['position']})" for kp in keyword_positions[:5]])
                    sites_summary.append(f"- {site['domain']}: {site['appearances']} appearances, keywords: {keywords_text}")
                
                # Procesare hibridă: DeepSeek pentru analiza inițială, Qwen pentru batch-uri
                all_sites_relevance = {}
                
                # 1. Analiză inițială cu DeepSeek (primele 100 neanalizate în batch-uri de 20)
                logger.info(f"🔍 Starting DeepSeek analysis for {min(100, len(sites_summary))} remaining sites...")
                deepseek_batch_size = 20  # Procesează în batch-uri de 20 pentru updates mai des
                deepseek_sites = sites_summary[:100]
                
                for batch_idx in range(0, len(deepseek_sites), deepseek_batch_size):
                    batch_sites = deepseek_sites[batch_idx:batch_idx + deepseek_batch_size]
                    batch_num = (batch_idx // deepseek_batch_size) + 1
                    logger.info(f"🔍 Processing DeepSeek batch {batch_num} ({len(batch_sites)} sites)...")
                    
                    deepseek_result = analyze_with_deepseek(batch_sites)
                    if deepseek_result:
                        for site_rel in deepseek_result.get("sites_relevance", []):
                            all_sites_relevance[site_rel["domain"]] = site_rel
                            analyzed_count += 1
                            
                            # Actualizează site-ul imediat în MongoDB
                            domain_name = site_rel["domain"]
                            for site in competitive_map_data:
                                if site.get("domain") == domain_name:
                                    site["relevance_score"] = site_rel.get("relevance_score", 50)
                                    site["industry_match"] = site_rel.get("industry_match", False)
                                    site["subdomain_matches"] = site_rel.get("subdomain_matches", [])
                                    site["reasoning"] = site_rel.get("reasoning", "")
                                    site["recommended"] = site_rel.get("recommended", False)
                                    break
                    
                    # Salvează progresul după fiecare batch DeepSeek
                    competitive_map_data.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
                    for i, s in enumerate(competitive_map_data):
                        s["rank"] = i + 1
                    
                    db.competitive_map.update_one(
                        {"master_agent_id": agent_id},
                        {
                            "$set": {
                                "competitive_map": competitive_map_data,
                                "relevance_analysis_progress": {
                                    "analyzed": analyzed_count,
                                    "total": total_sites,
                                    "percentage": int((analyzed_count / total_sites) * 100) if total_sites > 0 else 0
                                },
                                "updated_at": datetime.now(timezone.utc)
                            }
                        }
                    )
                    logger.info(f"✅ DeepSeek batch {batch_num} completed: {analyzed_count}/{total_sites} sites analyzed ({int((analyzed_count / total_sites) * 100) if total_sites > 0 else 0}%)")
                
                # 2. Procesare batch cu Qwen pentru restul site-urilor neanalizate (GPU paralel)
                remaining_unanalyzed = sites_to_analyze[100:] if len(sites_to_analyze) > 100 else []
                if QWEN_AVAILABLE and len(remaining_unanalyzed) > 0:
                    logger.info(f"🚀 Processing {len(remaining_unanalyzed)} remaining sites with Qwen (GPU) in batches...")
                    batch_size = 20  # 20 site-uri per batch pentru Qwen
                    remaining_sites = remaining_unanalyzed
                    
                    with ThreadPoolExecutor(max_workers=4) as executor:  # 4 batch-uri în paralel pe GPU
                        futures = []
                        for i in range(0, len(remaining_sites), batch_size):
                            batch = remaining_sites[i:i+batch_size]
                            batch_num = (i // batch_size) + 1
                            future = executor.submit(analyze_batch_with_qwen, batch, batch_num)
                            futures.append((future, batch))
                        
                        for future, batch in futures:
                            try:
                                result = future.result(timeout=90)
                                if result:
                                    for site_rel in result.get("sites_relevance", []):
                                        all_sites_relevance[site_rel["domain"]] = site_rel
                                        analyzed_count += 1
                                        
                                        # Actualizează site-ul imediat în MongoDB
                                        domain_name = site_rel["domain"]
                                        for site in competitive_map_data:
                                            if site.get("domain") == domain_name:
                                                site["relevance_score"] = site_rel.get("relevance_score", 50)
                                                site["industry_match"] = site_rel.get("industry_match", False)
                                                site["subdomain_matches"] = site_rel.get("subdomain_matches", [])
                                                site["reasoning"] = site_rel.get("reasoning", "")
                                                site["recommended"] = site_rel.get("recommended", False)
                                                break
                                        
                                        # Salvează progresul parțial în MongoDB (la fiecare 10 site-uri)
                                        if analyzed_count % 10 == 0:
                                            # Sortează și actualizează rank-urile
                                            competitive_map_data.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
                                            for i, s in enumerate(competitive_map_data):
                                                s["rank"] = i + 1
                                            
                                            db.competitive_map.update_one(
                                                {"master_agent_id": agent_id},
                                                {
                                                    "$set": {
                                                        "competitive_map": competitive_map_data,
                                                        "relevance_analysis_progress": {
                                                            "analyzed": analyzed_count,
                                                            "total": total_sites,
                                                            "percentage": int((analyzed_count / total_sites) * 100)
                                                        },
                                                        "updated_at": datetime.now(timezone.utc)
                                                    }
                                                }
                                            )
                            except Exception as e:
                                logger.error(f"Error processing batch: {e}")
                
                # 3. Finalizează - actualizează toate site-urile care nu au fost analizate
                for site in competitive_map_data:
                    domain_name = site.get("domain", "")
                    if domain_name not in all_sites_relevance:
                        # Default values dacă nu a fost analizat
                        site["relevance_score"] = 50
                        site["industry_match"] = False
                        site["subdomain_matches"] = []
                        site["reasoning"] = "Not analyzed yet"
                        site["recommended"] = False
                
                # Verifică câte site-uri sunt de fapt analizate (au relevance_score != 50 sau reasoning)
                actually_analyzed = sum(1 for s in competitive_map_data 
                                       if s.get("relevance_score", 50) != 50 or s.get("reasoning", ""))
                
                # Actualizează analyzed_count cu numărul real
                analyzed_count = actually_analyzed
                
                # Sortează final după relevanță
                competitive_map_data.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
                
                # Actualizează rank-urile finale
                for i, site in enumerate(competitive_map_data):
                    site["rank"] = i + 1
                
                # Marchează ca completă dacă toate site-urile sunt analizate
                is_completed = analyzed_count >= total_sites
                
                # Salvează final în MongoDB
                db.competitive_map.update_one(
                    {"master_agent_id": agent_id},
                    {
                        "$set": {
                            "competitive_map": competitive_map_data,
                            "relevance_analyzed": is_completed,
                            "relevance_analysis_status": "completed" if is_completed else "in_progress",
                            "relevance_analysis_progress": {
                                "analyzed": analyzed_count,
                                "total": total_sites,
                                "percentage": 100 if is_completed else int((analyzed_count / total_sites) * 100) if total_sites > 0 else 0
                            },
                            "relevance_analysis_date": datetime.now(timezone.utc) if is_completed else competitive_map.get("relevance_analysis_date"),
                            "relevance_analysis_method": "deepseek_qwen_hybrid" if QWEN_AVAILABLE else "deepseek_only",
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                logger.info(f"✅ Relevance analysis {'completed' if is_completed else 'partial'}: {analyzed_count}/{total_sites} sites analyzed ({int((analyzed_count / total_sites) * 100) if total_sites > 0 else 0}%)")
                
                logger.info(f"✅ Relevance analysis completed: {len(all_sites_relevance)} sites analyzed")
            except Exception as e:
                logger.error(f"❌ Error in relevance analysis background task: {e}")
                logger.error(traceback.format_exc())
                db.competitive_map.update_one(
                    {"master_agent_id": agent_id},
                    {
                        "$set": {
                            "relevance_analysis_status": "failed",
                            "relevance_analysis_error": str(e),
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
        
        # Pornește analiza în thread separat
        thread = threading.Thread(target=run_relevance_analysis, daemon=True)
        thread.start()
        
        # Returnează răspuns imediat
        return {
            "ok": True,
            "message": "Relevance analysis started in background. Use polling to check progress.",
            "sites_to_analyze": len(competitive_map_data),
            "estimated_time_minutes": max(2, len(competitive_map_data) // 50)  # ~50 site-uri/minut
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing relevance: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/competitive-map/relevance-mechanism")
async def get_relevance_mechanism(agent_id: str):
    """
    Explică mecanismul de selecție a site-urilor relevante
    """
    try:
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        competitive_map = db.competitive_map.find_one({"master_agent_id": agent_id})
        if not competitive_map:
            return {
                "ok": True,
                "mechanism": {
                    "description": "Mecanismul de selecție a site-urilor relevante",
                    "steps": [
                        {
                            "step": 1,
                            "name": "SERP Search",
                            "description": "Pentru fiecare keyword, se caută primele 20 site-uri în Google",
                            "output": "Lista de site-uri găsite cu keyword-ul și poziția"
                        },
                        {
                            "step": 2,
                            "name": "Analiză Relevanță DeepSeek + Qwen",
                            "description": "AI analizează relevanța fiecărui site folosind criterii stricte",
                            "criteria": {
                                "industry_match": {
                                    "weight": "40%",
                                    "description": "Verifică dacă site-ul oferă servicii/produse în aceeași industrie",
                                    "example": "Pentru 'amenajari interioare', site-uri de design interior = relevant"
                                },
                                "subdomain_matches": {
                                    "weight": "30%",
                                    "description": "Compară keywords-urile site-ului cu subdomeniile identificate",
                                    "example": "Dacă site-ul are 'servicii amenajari', se potrivește cu subdomeniul 'servicii'"
                                },
                                "keyword_quality": {
                                    "weight": "20%",
                                    "description": "Evaluează calitatea keywords-urilor care au găsit site-ul",
                                    "example": "Keywords specifice și relevante = scor mai mare"
                                },
                                "search_positions": {
                                    "weight": "10%",
                                    "description": "Consideră pozițiile în căutări (poziții bune = mai relevant)",
                                    "example": "Poziția 1-5 = mai relevant decât poziția 15-20"
                                }
                            }
                        },
                        {
                            "step": 3,
                            "name": "Calcul Scor Relevanță",
                            "description": "Se calculează un scor de relevanță 0-100 pentru fiecare site",
                            "scoring": {
                                "90-100": "Foarte relevant - aceeași industrie, keywords perfecte, subdomenii se potrivesc",
                                "70-89": "Relevant - industrie similară, keywords bune, subdomenii parțial",
                                "50-69": "Parțial relevant - conexiuni slabe, keywords generale",
                                "0-49": "Nu relevant - industrie diferită, keywords irelevante"
                            }
                        },
                        {
                            "step": 4,
                            "name": "Recomandare",
                            "description": "Site-urile sunt marcate ca 'recommended' dacă îndeplinesc condițiile",
                            "conditions": {
                                "required": [
                                    "relevance_score >= 70",
                                    "industry_match = true"
                                ],
                                "optional": [
                                    "subdomain_matches nu este gol",
                                    "best_position <= 10"
                                ]
                            }
                        },
                        {
                            "step": 5,
                            "name": "Sortare și Ranking",
                            "description": "Site-urile sunt sortate după relevanță (scor descrescător)",
                            "output": "Lista sortată de site-uri cu rank-uri actualizate"
                        }
                    ],
                    "processing_method": competitive_map.get("relevance_analysis_method", "not_analyzed"),
                    "tools_used": {
                        "deepseek": {
                            "purpose": "Analiză inițială pentru primele 100 site-uri",
                            "speed": "Rapid (API extern)",
                            "accuracy": "Foarte bună"
                        },
                        "qwen_gpu": {
                            "purpose": "Procesare batch paralelă pentru restul site-urilor",
                            "speed": "Foarte rapid (GPU local, procesare paralelă)",
                            "accuracy": "Foarte bună",
                            "batch_size": 20,
                            "parallel_batches": 4
                        }
                    }
                },
                "current_status": {
                    "sites_found": competitive_map.get("sites_found", 0) if competitive_map else 0,
                    "sites_analyzed": len([s for s in competitive_map.get("competitive_map", []) if s.get("relevance_score") is not None]) if competitive_map else 0,
                    "recommended_sites": len([s for s in competitive_map.get("competitive_map", []) if s.get("recommended", False)]) if competitive_map else 0,
                    "analysis_date": competitive_map.get("relevance_analysis_date") if competitive_map else None
                }
            }
        
        # Dacă există competitive_map, returnează și statistici
        competitive_map_data = competitive_map.get("competitive_map", [])
        relevance_scores = [s.get("relevance_score", 0) for s in competitive_map_data if s.get("relevance_score") is not None]
        
        return {
            "ok": True,
            "mechanism": {
                "description": "Mecanismul de selecție a site-urilor relevante",
                "steps": [
                    {
                        "step": 1,
                        "name": "SERP Search",
                        "description": "Pentru fiecare keyword, se caută primele 20 site-uri în Google",
                        "output": "Lista de site-uri găsite cu keyword-ul și poziția"
                    },
                    {
                        "step": 2,
                        "name": "Analiză Relevanță DeepSeek + Qwen",
                        "description": "AI analizează relevanța fiecărui site folosind criterii stricte",
                        "criteria": {
                            "industry_match": {
                                "weight": "40%",
                                "description": "Verifică dacă site-ul oferă servicii/produse în aceeași industrie",
                                "example": "Pentru 'amenajari interioare', site-uri de design interior = relevant"
                            },
                            "subdomain_matches": {
                                "weight": "30%",
                                "description": "Compară keywords-urile site-ului cu subdomeniile identificate",
                                "example": "Dacă site-ul are 'servicii amenajari', se potrivește cu subdomeniul 'servicii'"
                            },
                            "keyword_quality": {
                                "weight": "20%",
                                "description": "Evaluează calitatea keywords-urilor care au găsit site-ul",
                                "example": "Keywords specifice și relevante = scor mai mare"
                            },
                            "search_positions": {
                                "weight": "10%",
                                "description": "Consideră pozițiile în căutări (poziții bune = mai relevant)",
                                "example": "Poziția 1-5 = mai relevant decât poziția 15-20"
                            }
                        }
                    },
                    {
                        "step": 3,
                        "name": "Calcul Scor Relevanță",
                        "description": "Se calculează un scor de relevanță 0-100 pentru fiecare site",
                        "scoring": {
                            "90-100": "Foarte relevant - aceeași industrie, keywords perfecte, subdomenii se potrivesc",
                            "70-89": "Relevant - industrie similară, keywords bune, subdomenii parțial",
                            "50-69": "Parțial relevant - conexiuni slabe, keywords generale",
                            "0-49": "Nu relevant - industrie diferită, keywords irelevante"
                        }
                    },
                    {
                        "step": 4,
                        "name": "Recomandare",
                        "description": "Site-urile sunt marcate ca 'recommended' dacă îndeplinesc condițiile",
                        "conditions": {
                            "required": [
                                "relevance_score >= 70",
                                "industry_match = true"
                            ],
                            "optional": [
                                "subdomain_matches nu este gol",
                                "best_position <= 10"
                            ]
                        }
                    },
                    {
                        "step": 5,
                        "name": "Sortare și Ranking",
                        "description": "Site-urile sunt sortate după relevanță (scor descrescător)",
                        "output": "Lista sortată de site-uri cu rank-uri actualizate"
                    }
                ],
                "processing_method": competitive_map.get("relevance_analysis_method", "not_analyzed"),
                "tools_used": {
                    "deepseek": {
                        "purpose": "Analiză inițială pentru primele 100 site-uri",
                        "speed": "Rapid (API extern)",
                        "accuracy": "Foarte bună"
                    },
                    "qwen_gpu": {
                        "purpose": "Procesare batch paralelă pentru restul site-urilor",
                        "speed": "Foarte rapid (GPU local, procesare paralelă)",
                        "accuracy": "Foarte bună",
                        "batch_size": 20,
                        "parallel_batches": 4
                    }
                }
            },
            "current_status": {
                "sites_found": competitive_map.get("sites_found", 0),
                "sites_analyzed": len(relevance_scores),
                "recommended_sites": len([s for s in competitive_map_data if s.get("recommended", False)]),
                "analysis_date": competitive_map.get("relevance_analysis_date"),
                "statistics": {
                    "avg_relevance_score": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0,
                    "min_relevance_score": min(relevance_scores) if relevance_scores else 0,
                    "max_relevance_score": max(relevance_scores) if relevance_scores else 0,
                    "sites_by_score_range": {
                        "90-100": len([s for s in competitive_map_data if 90 <= s.get("relevance_score", 0) <= 100]),
                        "70-89": len([s for s in competitive_map_data if 70 <= s.get("relevance_score", 0) < 90]),
                        "50-69": len([s for s in competitive_map_data if 50 <= s.get("relevance_score", 0) < 70]),
                        "0-49": len([s for s in competitive_map_data if 0 <= s.get("relevance_score", 0) < 50])
                    }
                }
            }
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting relevance mechanism: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# WORKFLOW MONITORING ENDPOINTS
# ============================================================================

@app.get("/api/workflows/active")
async def get_active_workflows():
    """
    Returnează workflow-urile active (în progres)
    """
    try:
        # Verifică workflow-urile din ceo_workflow_executions
        active_workflows = list(db.ceo_workflow_executions.find({
            "status": {"$in": ["in_progress", "running", "pending"]}
        }).sort("created_at", -1).limit(50))
        
        # Verifică și procesul de creare agenți slave din competitive_map
        competitive_maps = list(db.competitive_map.find({
            "agent_creation_status": "in_progress"
        }).sort("updated_at", -1))
        
        workflows_list = []
        
        # Adaugă workflow-urile din ceo_workflow_executions
        for wf in active_workflows:
            workflows_list.append({
                "workflow_id": str(wf.get("_id")),
                "workflow_type": wf.get("workflow_type", "agent_creation"),
                "status": wf.get("status", "in_progress"),
                "agent_id": str(wf.get("agent_id")) if wf.get("agent_id") else None,
                "created_at": wf.get("created_at"),
                "updated_at": wf.get("updated_at"),
                "progress": wf.get("progress", {}),
                "steps": wf.get("steps", [])
            })
        
        # Adaugă procesul de creare agenți slave
        for cm in competitive_maps:
            master_id = cm.get("master_agent_id")
            progress = cm.get("agent_creation_progress", {})
            
            workflows_list.append({
                "workflow_id": f"slave_creation_{master_id}",
                "workflow_type": "slave_agent_creation",
                "status": "in_progress",
                "agent_id": str(master_id) if master_id else None,
                "created_at": cm.get("created_at"),
                "updated_at": cm.get("updated_at"),
                "progress": {
                    "completed": progress.get("completed", 0),
                    "total": progress.get("total", 0),
                    "percentage": progress.get("percentage", 0)
                },
                "description": f"Creating slave agents for master agent {master_id}",
                "steps": [
                    {
                        "step": "agent_creation",
                        "status": "in_progress",
                        "progress": progress
                    }
                ]
            })
        
        return {
            "ok": True,
            "workflows": workflows_list,
            "count": len(workflows_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting active workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflows/recent")
async def get_recent_workflows(limit: int = 50):
    """
    Returnează workflow-urile recente (completate sau eșuate)
    """
    try:
        # Workflow-uri din ceo_workflow_executions
        recent_workflows = list(db.ceo_workflow_executions.find({
            "status": {"$in": ["completed", "failed", "stopped"]}
        }).sort("updated_at", -1).limit(limit))
        
        # Procese de creare agenți slave completate
        completed_maps = list(db.competitive_map.find({
            "agent_creation_status": {"$in": ["completed", "failed", "stopped"]}
        }).sort("updated_at", -1).limit(limit))
        
        workflows_list = []
        
        # Adaugă workflow-urile din ceo_workflow_executions
        for wf in recent_workflows:
            workflows_list.append({
                "workflow_id": str(wf.get("_id")),
                "workflow_type": wf.get("workflow_type", "agent_creation"),
                "status": wf.get("status", "completed"),
                "agent_id": str(wf.get("agent_id")) if wf.get("agent_id") else None,
                "created_at": wf.get("created_at"),
                "updated_at": wf.get("updated_at"),
                "progress": wf.get("progress", {}),
                "steps": wf.get("steps", [])
            })
        
        # Adaugă procesele de creare agenți slave
        for cm in completed_maps:
            master_id = cm.get("master_agent_id")
            progress = cm.get("agent_creation_progress", {})
            status = cm.get("agent_creation_status", "completed")
            
            workflows_list.append({
                "workflow_id": f"slave_creation_{master_id}",
                "workflow_type": "slave_agent_creation",
                "status": status,
                "agent_id": str(master_id) if master_id else None,
                "created_at": cm.get("created_at"),
                "updated_at": cm.get("updated_at"),
                "progress": {
                    "completed": progress.get("completed", 0),
                    "total": progress.get("total", 0),
                    "percentage": progress.get("percentage", 0)
                },
                "description": f"Slave agent creation for master agent {master_id}",
                "steps": [
                    {
                        "step": "agent_creation",
                        "status": status,
                        "progress": progress
                    }
                ]
            })
        
        # Sortează după updated_at
        workflows_list.sort(key=lambda x: x.get("updated_at") or datetime.min, reverse=True)
        
        return {
            "ok": True,
            "workflows": workflows_list[:limit],
            "count": len(workflows_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting recent workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflows/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """
    Returnează statusul unui workflow specific
    """
    try:
        # Verifică dacă este un workflow de creare agenți slave
        if workflow_id.startswith("slave_creation_"):
            master_id = workflow_id.replace("slave_creation_", "")
            competitive_map = db.competitive_map.find_one({"master_agent_id": master_id})
            
            if competitive_map:
                progress = competitive_map.get("agent_creation_progress", {})
                return {
                    "ok": True,
                    "workflow_id": workflow_id,
                    "workflow_type": "slave_agent_creation",
                    "status": competitive_map.get("agent_creation_status", "not_started"),
                    "agent_id": master_id,
                    "progress": progress,
                    "created_at": competitive_map.get("created_at"),
                    "updated_at": competitive_map.get("updated_at")
                }
            else:
                raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Verifică în ceo_workflow_executions
        try:
            workflow = db.ceo_workflow_executions.find_one({"_id": ObjectId(workflow_id)})
        except:
            workflow = None
        
        if workflow:
            return {
                "ok": True,
                "workflow_id": workflow_id,
                "workflow_type": workflow.get("workflow_type", "unknown"),
                "status": workflow.get("status", "unknown"),
                "agent_id": str(workflow.get("agent_id")) if workflow.get("agent_id") else None,
                "progress": workflow.get("progress", {}),
                "steps": workflow.get("steps", []),
                "created_at": workflow.get("created_at"),
                "updated_at": workflow.get("updated_at")
            }
        else:
            raise HTTPException(status_code=404, detail="Workflow not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflow/steps")
async def get_workflow_steps(agent_id: Optional[str] = None, limit: int = 500):
    """
    Returnează pașii workflow-ului din workflow_tracking collection
    """
    try:
        from workflow_tracking_system import WorkflowTracker
        from config.database_config import MONGODB_URI
        from pymongo import MongoClient
        
        client = MongoClient(MONGODB_URI)
        tracker = WorkflowTracker(client)
        
        query = {}
        if agent_id:
            try:
                query["agent_id"] = agent_id
            except:
                pass
        
        # Obține pașii din workflow_tracking
        steps = list(tracker.collection.find(query).sort("timestamp", -1).limit(limit))
        
        # Convertește ObjectId la string
        for step in steps:
            step["_id"] = str(step["_id"])
            if step.get("agent_id"):
                step["agent_id"] = str(step["agent_id"])
        
        return {
            "ok": True,
            "steps": steps,
            "count": len(steps)
        }
        
    except Exception as e:
        logger.error(f"Error getting workflow steps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflow/report")
async def get_workflow_report(agent_id: Optional[str] = None, days: int = 7):
    """
    Returnează raportul workflow-ului pentru ultimele N zile
    """
    try:
        from workflow_tracking_system import WorkflowTracker
        from config.database_config import MONGODB_URI
        from pymongo import MongoClient
        from datetime import timedelta
        
        client = MongoClient(MONGODB_URI)
        tracker = WorkflowTracker(client)
        
        # Calculează data de început
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = {"timestamp": {"$gte": start_date}}
        if agent_id:
            try:
                query["agent_id"] = agent_id
            except:
                pass
        
        # Obține toate entry-urile
        entries = list(tracker.collection.find(query))
        
        # Calculează statistici
        total_entries = len(entries)
        total_completed = len([e for e in entries if e.get("status") == "completed"])
        total_failed = len([e for e in entries if e.get("status") == "failed"])
        total_in_progress = len([e for e in entries if e.get("status") == "in_progress"])
        success_rate = (total_completed / total_entries * 100) if total_entries > 0 else 0
        
        # Grupează după step
        steps_summary = {}
        for entry in entries:
            step_name = entry.get("step") or entry.get("step_name", "unknown")
            if step_name not in steps_summary:
                steps_summary[step_name] = {
                    "total": 0,
                    "completed": 0,
                    "failed": 0,
                    "in_progress": 0
                }
            steps_summary[step_name]["total"] += 1
            status = entry.get("status", "unknown")
            if status == "completed":
                steps_summary[step_name]["completed"] += 1
            elif status == "failed":
                steps_summary[step_name]["failed"] += 1
            elif status == "in_progress":
                steps_summary[step_name]["in_progress"] += 1
        
        return {
            "ok": True,
            "summary": {
                "total_entries": total_entries,
                "total_completed": total_completed,
                "total_failed": total_failed,
                "total_in_progress": total_in_progress,
                "success_rate": round(success_rate, 2)
            },
            "steps": steps_summary,
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Error getting workflow report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ACTIONS QUEUE ENDPOINTS
# ============================================================================

@app.get("/api/actions/queue")
async def get_actions_queue(agent_id: Optional[str] = None, status: Optional[str] = None):
    """
    Returnează coada de acțiuni SEO/PPC
    """
    try:
        query = {}
        if agent_id:
            try:
                query["agent_id"] = ObjectId(agent_id)
            except:
                query["agent_id"] = agent_id
        
        if status:
            query["status"] = status
        
        # Verifică dacă există colecția actions_queue
        if "actions_queue" not in db.list_collection_names():
            # Creează colecția dacă nu există
            db.actions_queue.insert_one({
                "_id": ObjectId(),
                "created_at": datetime.now(timezone.utc),
                "temp": True
            })
            db.actions_queue.delete_one({"temp": True})
            logger.info("✅ Created actions_queue collection")
        
        actions = list(db.actions_queue.find(query).sort("created_at", -1).limit(100))
        
        # Convertește ObjectId la string
        for action in actions:
            action["_id"] = str(action["_id"])
            if action.get("agent_id"):
                action["agent_id"] = str(action["agent_id"])
        
        return {
            "ok": True,
            "actions": actions,
            "count": len(actions)
        }
        
    except Exception as e:
        logger.error(f"Error getting actions queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/actions/stats")
async def get_actions_stats(agent_id: Optional[str] = None):
    """
    Returnează statistici despre acțiuni
    """
    try:
        query = {}
        if agent_id:
            try:
                query["agent_id"] = ObjectId(agent_id)
            except:
                query["agent_id"] = agent_id
        
        if "actions_queue" not in db.list_collection_names():
            return {
                "ok": True,
                "total": 0,
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
                "failed": 0
            }
        
        total = db.actions_queue.count_documents(query)
        pending = db.actions_queue.count_documents({**query, "status": "pending"})
        in_progress = db.actions_queue.count_documents({**query, "status": "in_progress"})
        completed = db.actions_queue.count_documents({**query, "status": "completed"})
        failed = db.actions_queue.count_documents({**query, "status": "failed"})
        
        return {
            "ok": True,
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "failed": failed
        }
        
    except Exception as e:
        logger.error(f"Error getting actions stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/actions")
async def add_action(request: dict = Body(...)):
    """
    Adaugă o acțiune nouă în coadă
    """
    try:
        action = {
            "agent_id": request.get("agent_id"),
            "action_type": request.get("action_type", "seo"),  # seo sau ppc
            "action_name": request.get("action_name", ""),
            "description": request.get("description", ""),
            "status": "pending",
            "priority": request.get("priority", "medium"),  # low, medium, high
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "metadata": request.get("metadata", {})
        }
        
        if action["agent_id"]:
            try:
                action["agent_id"] = ObjectId(action["agent_id"])
            except:
                pass
        
        result = db.actions_queue.insert_one(action)
        action["_id"] = str(result.inserted_id)
        if action.get("agent_id"):
            action["agent_id"] = str(action["agent_id"])
        
        return {
            "ok": True,
            "action": action
        }
        
    except Exception as e:
        logger.error(f"Error adding action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/actions/{action_id}/status")
async def update_action_status(action_id: str, request: dict = Body(...)):
    """
    Actualizează statusul unei acțiuni
    """
    try:
        status = request.get("status")
        if status not in ["pending", "in_progress", "completed", "failed"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        update = {
            "status": status,
            "updated_at": datetime.now(timezone.utc)
        }
        
        if request.get("result"):
            update["result"] = request["result"]
        
        if request.get("error"):
            update["error"] = request["error"]
        
        try:
            result = db.actions_queue.update_one(
                {"_id": ObjectId(action_id)},
                {"$set": update}
            )
        except:
            result = db.actions_queue.update_one(
                {"_id": action_id},
                {"$set": update}
            )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Action not found")
        
        return {
            "ok": True,
            "message": "Action status updated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating action status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ALERTS CENTER ENDPOINTS
# ============================================================================

@app.get("/api/alerts")
async def get_alerts(agent_id: Optional[str] = None, severity: Optional[str] = None, alert_type: Optional[str] = None, status: Optional[str] = None, limit: int = 100):
    """
    Returnează alertele sistemului
    """
    try:
        query = {}
        if agent_id:
            try:
                query["agent_id"] = ObjectId(agent_id)
            except:
                query["agent_id"] = agent_id
        
        if severity:
            query["severity"] = severity  # info, warning, error, critical
        
        if alert_type:
            query["alert_type"] = alert_type  # rank_drop, competitor_new, ctr_low, etc.
        
        # Status poate fi 'active' (default) sau 'resolved'
        if status == "active":
            query["resolved"] = {"$ne": True}
        elif status == "resolved":
            query["resolved"] = True
        
        # Verifică dacă există colecția alerts
        if "alerts" not in db.list_collection_names():
            # Creează colecția dacă nu există
            db.alerts.insert_one({
                "_id": ObjectId(),
                "created_at": datetime.now(timezone.utc),
                "temp": True
            })
            db.alerts.delete_one({"temp": True})
            logger.info("✅ Created alerts collection")
        
        alerts = list(db.alerts.find(query).sort("created_at", -1).limit(limit))
        
        # Convertește ObjectId la string
        for alert in alerts:
            alert["_id"] = str(alert["_id"])
            if alert.get("agent_id"):
                alert["agent_id"] = str(alert["agent_id"])
        
        return {
            "ok": True,
            "alerts": alerts,
            "count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts/stats")
async def get_alerts_stats(agent_id: Optional[str] = None):
    """
    Returnează statistici despre alerte
    """
    try:
        query = {}
        if agent_id:
            try:
                query["agent_id"] = ObjectId(agent_id)
            except:
                query["agent_id"] = agent_id
        
        if "alerts" not in db.list_collection_names():
            return {
                "ok": True,
                "total": 0,
                "critical": 0,
                "error": 0,
                "warning": 0,
                "info": 0,
                "unread": 0
            }
        
        total = db.alerts.count_documents(query)
        critical = db.alerts.count_documents({**query, "severity": "critical"})
        error = db.alerts.count_documents({**query, "severity": "error"})
        warning = db.alerts.count_documents({**query, "severity": "warning"})
        info = db.alerts.count_documents({**query, "severity": "info"})
        unread = db.alerts.count_documents({**query, "read": False})
        
        return {
            "ok": True,
            "total": total,
            "critical": critical,
            "error": error,
            "warning": warning,
            "info": info,
            "unread": unread
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts")
async def create_alert(request: dict = Body(...)):
    """
    Creează o alertă nouă
    """
    try:
        alert = {
            "agent_id": request.get("agent_id"),
            "alert_type": request.get("alert_type", "system"),  # rank_drop, competitor_new, ctr_low, etc.
            "severity": request.get("severity", "info"),  # info, warning, error, critical
            "title": request.get("title", ""),
            "message": request.get("message", ""),
            "read": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "metadata": request.get("metadata", {})
        }
        
        if alert["agent_id"]:
            try:
                alert["agent_id"] = ObjectId(alert["agent_id"])
            except:
                pass
        
        result = db.alerts.insert_one(alert)
        alert["_id"] = str(result.inserted_id)
        if alert.get("agent_id"):
            alert["agent_id"] = str(alert["agent_id"])
        
        return {
            "ok": True,
            "alert": alert
        }
        
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str):
    """
    Marchează o alertă ca fiind citită
    """
    try:
        try:
            result = db.alerts.update_one(
                {"_id": ObjectId(alert_id)},
                {"$set": {"read": True, "updated_at": datetime.now(timezone.utc)}}
            )
        except:
            result = db.alerts.update_one(
                {"_id": alert_id},
                {"$set": {"read": True, "updated_at": datetime.now(timezone.utc)}}
            )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "ok": True,
            "message": "Alert marked as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking alert as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """
    Șterge o alertă
    """
    try:
        try:
            result = db.alerts.delete_one({"_id": ObjectId(alert_id)})
        except:
            result = db.alerts.delete_one({"_id": alert_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "ok": True,
            "message": "Alert deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts/check")
async def check_alerts(request: dict = Body(...)):
    """
    Verifică și generează alerte noi pentru un agent
    """
    try:
        agent_id = request.get("agent_id")
        
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required")
        
        # Aici poți adăuga logica pentru verificarea alertelor
        # De exemplu: verifică rank drops, competitori noi, etc.
        
        # Pentru moment, returnează un mesaj de succes
        return {
            "ok": True,
            "message": "Alerts check completed",
            "alerts_found": 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """
    Marchează o alertă ca fiind recunoscută (acknowledged)
    """
    try:
        try:
            result = db.alerts.update_one(
                {"_id": ObjectId(alert_id)},
                {"$set": {"acknowledged": True, "read": True, "updated_at": datetime.now(timezone.utc)}}
            )
        except:
            result = db.alerts.update_one(
                {"_id": alert_id},
                {"$set": {"acknowledged": True, "read": True, "updated_at": datetime.now(timezone.utc)}}
            )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "ok": True,
            "message": "Alert acknowledged"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, request: dict = Body(...)):
    """
    Rezolvă o alertă
    """
    try:
        resolution = request.get("resolution", "")
        
        update = {
            "resolved": True,
            "resolved_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        if resolution:
            update["resolution"] = resolution
        
        try:
            result = db.alerts.update_one(
                {"_id": ObjectId(alert_id)},
                {"$set": update}
            )
        except:
            result = db.alerts.update_one(
                {"_id": alert_id},
                {"$set": update}
            )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "ok": True,
            "message": "Alert resolved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ORGANIZATION GRAPH ENDPOINTS
# ============================================================================

@app.get("/api/graph/{agent_id}")
async def get_graph(agent_id: str):
    """
    Returnează graful organizațional (master-slave relationships)
    """
    try:
        if not agent_id:
            return {
                "ok": True,
                "nodes": [],
                "edges": [],
                "master": None,
                "slaves": []
            }
        
        try:
            agent_obj_id = ObjectId(agent_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid agent_id")
        
        # Găsește master agent
        master = agents_collection.find_one({"_id": agent_obj_id})
        if not master:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Găsește slave agents
        slaves = list(agents_collection.find({
            "agent_type": "slave",
            "master_agent_id": agent_obj_id
        }))
        
        # Construiește noduri
        nodes = []
        edges = []
        
        # Master node
        nodes.append({
            "id": str(master["_id"]),
            "label": master.get("domain", master.get("site_url", "Unknown")),
            "type": "master",
            "data": {
                "domain": master.get("domain"),
                "industry": master.get("industry"),
                "chunks_indexed": master.get("chunks_indexed", 0),
                "keywords_count": master.get("keywords_count", 0)
            }
        })
        
        # Slave nodes și edges
        for slave in slaves:
            nodes.append({
                "id": str(slave["_id"]),
                "label": slave.get("domain", slave.get("site_url", "Unknown")),
                "type": "slave",
                "data": {
                    "domain": slave.get("domain"),
                    "industry": slave.get("industry"),
                    "chunks_indexed": slave.get("chunks_indexed", 0),
                    "master_agent_id": str(slave.get("master_agent_id"))
                }
            })
            
            # Edge de la master la slave
            edges.append({
                "id": f"{master['_id']}-{slave['_id']}",
                "source": str(master["_id"]),
                "target": str(slave["_id"]),
                "type": "master-slave",
                "label": "slave"
            })
        
        return {
            "ok": True,
            "nodes": nodes,
            "edges": edges,
            "master": {
                "id": str(master["_id"]),
                "domain": master.get("domain"),
                "industry": master.get("industry"),
                "slaves_count": len(slaves)
            },
            "slaves": [{
                "id": str(s["_id"]),
                "domain": s.get("domain"),
                "industry": s.get("industry")
            } for s in slaves]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/graph/update")
async def update_graph(request: dict = Body(...)):
    """
    Actualizează graful organizațional pentru un agent
    """
    try:
        agent_id = request.get("agent_id")
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required")
        
        # Pentru moment, doar returnează graful actualizat
        # În viitor, aici poți adăuga logica pentru recalcularea similarităților, etc.
        
        try:
            agent_obj_id = ObjectId(agent_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid agent_id")
        
        master = agents_collection.find_one({"_id": agent_obj_id})
        if not master:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        slaves = list(agents_collection.find({
            "agent_type": "slave",
            "master_agent_id": agent_obj_id
        }))
        
        return {
            "ok": True,
            "message": "Graph updated",
            "master_id": agent_id,
            "slaves_count": len(slaves)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/graph/{agent_id}/similar")
async def get_similar_slaves(agent_id: str, limit: int = 10):
    """
    Returnează slave agents similari cu master-ul (bazat pe embeddings/similarity)
    """
    try:
        try:
            agent_obj_id = ObjectId(agent_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid agent_id")
        
        master = agents_collection.find_one({"_id": agent_obj_id})
        if not master:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Găsește slave agents
        slaves = list(agents_collection.find({
            "agent_type": "slave",
            "master_agent_id": agent_obj_id
        }).limit(limit))
        
        # Pentru moment, returnează slave-urile direct
        # În viitor, aici poți adăuga logica pentru calcularea similarității bazată pe embeddings
        
        similar_slaves = []
        for slave in slaves:
            similar_slaves.append({
                "id": str(slave["_id"]),
                "domain": slave.get("domain"),
                "industry": slave.get("industry"),
                "similarity_score": 0.85,  # Placeholder - va fi calculat din embeddings
                "chunks_indexed": slave.get("chunks_indexed", 0)
            })
        
        # Sortează după similarity score
        similar_slaves.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return {
            "ok": True,
            "similar_slaves": similar_slaves,
            "count": len(similar_slaves)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting similar slaves: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# GOOGLE ADS ENDPOINTS
# ============================================================================

@app.get("/api/ads/oauth/url")
async def get_ads_oauth_url(agent_id: Optional[str] = None):
    """
    Returnează URL-ul pentru OAuth Google Ads
    """
    try:
        # Pentru moment, returnează un URL placeholder
        # În viitor, aici poți integra cu Google Ads API pentru OAuth
        oauth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        
        return {
            "ok": True,
            "auth_url": oauth_url,
            "message": "OAuth URL generated. Integration with Google Ads API pending."
        }
        
    except Exception as e:
        logger.error(f"Error getting OAuth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ads/accounts/{agent_id}/customer")
async def set_customer_id(agent_id: str, request: dict = Body(...)):
    """
    Setează Customer ID pentru Google Ads
    """
    try:
        customer_id = request.get("customer_id")
        
        if not customer_id:
            raise HTTPException(status_code=400, detail="customer_id is required")
        
        # Verifică dacă există colecția google_ads_config
        if "google_ads_config" not in db.list_collection_names():
            db.google_ads_config.insert_one({
                "_id": ObjectId(),
                "created_at": datetime.now(timezone.utc),
                "temp": True
            })
            db.google_ads_config.delete_one({"temp": True})
            logger.info("✅ Created google_ads_config collection")
        
        # Salvează sau actualizează configurația
        try:
            agent_obj_id = ObjectId(agent_id)
        except:
            agent_obj_id = agent_id
        
        config = {
            "agent_id": agent_obj_id,
            "customer_id": customer_id,
            "updated_at": datetime.now(timezone.utc)
        }
        
        db.google_ads_config.update_one(
            {"agent_id": agent_obj_id},
            {"$set": config},
            upsert=True
        )
        
        return {
            "ok": True,
            "message": "Customer ID set successfully",
            "customer_id": customer_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting customer ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ads/campaigns")
async def get_campaigns(agent_id: Optional[str] = None):
    """
    Returnează campaniile Google Ads pentru un agent
    """
    try:
        query = {}
        if agent_id:
            try:
                query["agent_id"] = ObjectId(agent_id)
            except:
                query["agent_id"] = agent_id
        
        # Verifică dacă există colecția google_ads_campaigns
        if "google_ads_campaigns" not in db.list_collection_names():
            return {
                "ok": True,
                "campaigns": [],
                "count": 0
            }
        
        campaigns = list(db.google_ads_campaigns.find(query).sort("created_at", -1).limit(100))
        
        # Convertește ObjectId la string
        for campaign in campaigns:
            campaign["_id"] = str(campaign["_id"])
            if campaign.get("agent_id"):
                campaign["agent_id"] = str(campaign["agent_id"])
        
        return {
            "ok": True,
            "campaigns": campaigns,
            "count": len(campaigns)
        }
        
    except Exception as e:
        logger.error(f"Error getting campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ads/campaigns")
async def create_campaign(request: dict = Body(...)):
    """
    Creează o campanie Google Ads
    """
    try:
        agent_id = request.get("agent_id")
        campaign_name = request.get("campaign_name")
        budget_amount_micros = request.get("budget_amount_micros", 10000000)
        bidding_strategy = request.get("bidding_strategy", "MAXIMIZE_CONVERSIONS")
        
        if not agent_id or not campaign_name:
            raise HTTPException(status_code=400, detail="agent_id and campaign_name are required")
        
        # Verifică dacă există colecția google_ads_campaigns
        if "google_ads_campaigns" not in db.list_collection_names():
            db.google_ads_campaigns.insert_one({
                "_id": ObjectId(),
                "created_at": datetime.now(timezone.utc),
                "temp": True
            })
            db.google_ads_campaigns.delete_one({"temp": True})
            logger.info("✅ Created google_ads_campaigns collection")
        
        try:
            agent_obj_id = ObjectId(agent_id)
        except:
            agent_obj_id = agent_id
        
        campaign = {
            "agent_id": agent_obj_id,
            "campaign_name": campaign_name,
            "budget_amount_micros": budget_amount_micros,
            "bidding_strategy": bidding_strategy,
            "status": "pending",  # pending, active, paused, removed
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "metadata": request.get("metadata", {})
        }
        
        result = db.google_ads_campaigns.insert_one(campaign)
        campaign["_id"] = str(result.inserted_id)
        if campaign.get("agent_id"):
            campaign["agent_id"] = str(campaign["agent_id"])
        
        return {
            "ok": True,
            "campaign": campaign,
            "message": "Campaign created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ads/sync")
async def sync_from_seo(request: dict = Body(...)):
    """
    Sincronizează campaniile Google Ads din insights SEO
    """
    try:
        agent_id = request.get("agent_id")
        keywords = request.get("keywords")
        intent_filter = request.get("intent_filter", "transactional")
        
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required")
        
        # Aici poți adăuga logica pentru sincronizare
        # De exemplu: generează campanii bazate pe keywords din SEO
        
        # Pentru moment, returnează un mesaj de succes
        return {
            "ok": True,
            "message": "Sync from SEO completed",
            "campaigns_created": 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing from SEO: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# LEARNING CENTER ENDPOINTS
# ============================================================================

@app.get("/api/learning/stats")
async def get_learning_stats():
    """
    Returnează statistici despre learning (conversații, examples, training runs, etc.)
    """
    try:
        # Numără conversații din master_agent_chat_history
        total_conversations = 0
        if "master_agent_chat_history" in db.list_collection_names():
            total_conversations = db.master_agent_chat_history.count_documents({})
        
        # Numără conversații procesate (din processed_examples sau conversations cu flag processed)
        processed_conversations = 0
        if "processed_examples" in db.list_collection_names():
            processed_conversations = db.processed_examples.count_documents({})
        
        # Numără training examples
        training_examples = processed_conversations  # Poți adăuga logică separată dacă e necesar
        
        # Numără JSONL files
        jsonl_files = 0
        if "jsonl_files" in db.list_collection_names():
            jsonl_files = db.jsonl_files.count_documents({})
        
        # Calculează total tokens (aproximativ - 1 conversație = ~100 tokens)
        total_tokens = total_conversations * 100  # Estimare simplă
        
        # Numără training runs
        training_runs = 0
        if "training_runs" in db.list_collection_names():
            training_runs = db.training_runs.count_documents({})
        
        return {
            "ok": True,
            "total_conversations": total_conversations,
            "processed_conversations": processed_conversations,
            "training_examples": training_examples,
            "jsonl_files": jsonl_files,
            "total_tokens": total_tokens,
            "training_runs": training_runs
        }
    except Exception as e:
        logger.error(f"Error getting learning stats: {e}")
        return {
            "ok": False,
            "error": str(e),
            "total_conversations": 0,
            "processed_conversations": 0,
            "training_examples": 0,
            "jsonl_files": 0,
            "total_tokens": 0,
            "training_runs": 0
        }

@app.get("/api/learning/training-status")
async def get_training_status():
    """
    Returnează statusul training-ului curent
    """
    try:
        # Verifică dacă există un training activ
        active_training = None
        if "training_runs" in db.list_collection_names():
            active_training = db.training_runs.find_one({"status": "in_progress"})
        
        if active_training:
            return {
                "ok": True,
                "is_training": True,
                "model_name": active_training.get("model_name", "Unknown"),
                "progress": active_training.get("progress", 0),
                "current_epoch": active_training.get("current_epoch", 0),
                "total_epochs": active_training.get("total_epochs", 0),
                "current_loss": active_training.get("current_loss"),
                "elapsed_time": active_training.get("elapsed_time", "0m"),
                "eta": active_training.get("eta", "Unknown")
            }
        else:
            return {
                "ok": True,
                "is_training": False,
                "message": "No active training session"
            }
    except Exception as e:
        logger.error(f"Error getting training status: {e}")
        return {
            "ok": False,
            "is_training": False,
            "error": str(e)
        }

@app.post("/api/learning/process-data")
async def process_learning_data():
    """
    Procesează conversațiile și extrage training examples
    """
    try:
        # Verifică dacă există colecția processed_examples
        if "processed_examples" not in db.list_collection_names():
            db.processed_examples.insert_one({
                "_id": ObjectId(),
                "created_at": datetime.now(timezone.utc),
                "temp": True
            })
            db.processed_examples.delete_one({"temp": True})
            logger.info("✅ Created processed_examples collection")
        
        # Procesează conversațiile din master_agent_chat_history
        processed_count = 0
        if "master_agent_chat_history" in db.list_collection_names():
            conversations = db.master_agent_chat_history.find({})
            for conv in conversations:
                # Verifică dacă conversația a fost deja procesată
                existing = db.processed_examples.find_one({"conversation_id": str(conv.get("_id"))})
                if not existing:
                    # Creează un training example
                    example = {
                        "conversation_id": str(conv.get("_id")),
                        "agent_id": conv.get("agent_id"),
                        "messages": conv.get("messages", []),
                        "processed_at": datetime.now(timezone.utc),
                        "status": "ready"
                    }
                    db.processed_examples.insert_one(example)
                    processed_count += 1
        
        return {
            "ok": True,
            "message": f"Processed {processed_count} conversations",
            "processed_count": processed_count
        }
    except Exception as e:
        logger.error(f"Error processing learning data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learning/build-jsonl")
async def build_jsonl():
    """
    Construiește fișiere JSONL din training examples
    """
    try:
        # Verifică dacă există colecția jsonl_files
        if "jsonl_files" not in db.list_collection_names():
            db.jsonl_files.insert_one({
                "_id": ObjectId(),
                "created_at": datetime.now(timezone.utc),
                "temp": True
            })
            db.jsonl_files.delete_one({"temp": True})
            logger.info("✅ Created jsonl_files collection")
        
        # Numără examples disponibile
        examples_count = 0
        if "processed_examples" in db.list_collection_names():
            examples_count = db.processed_examples.count_documents({"status": "ready"})
        
        if examples_count == 0:
            return {
                "ok": False,
                "message": "No processed examples available. Process data first.",
                "examples_count": 0
            }
        
        # Creează un fișier JSONL (pentru moment, doar înregistrează în DB)
        jsonl_file = {
            "filename": f"training_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl",
            "examples_count": examples_count,
            "created_at": datetime.now(timezone.utc),
            "status": "ready"
        }
        
        result = db.jsonl_files.insert_one(jsonl_file)
        jsonl_file["_id"] = str(result.inserted_id)
        
        return {
            "ok": True,
            "message": f"JSONL file created with {examples_count} examples",
            "jsonl_file": jsonl_file,
            "examples_count": examples_count
        }
    except Exception as e:
        logger.error(f"Error building JSONL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# INTELLIGENCE ENDPOINTS
# ============================================================================

@app.get("/api/intelligence/overview")
async def get_intelligence_overview():
    """
    Returnează overview-ul pentru Competitive Intelligence
    """
    try:
        # Numără master agents
        total_masters = agents_collection.count_documents({"master_agent_id": {"$exists": False}})
        
        # Numără total keywords (din toți agenții)
        total_keywords = 0
        for agent in agents_collection.find({}, {"keywords": 1, "overall_keywords": 1}):
            total_keywords += len(agent.get("keywords", []))
            total_keywords += len(agent.get("overall_keywords", []))
        
        # Numără competitors (slave agents)
        total_competitors = agents_collection.count_documents({"master_agent_id": {"$exists": True}})
        
        # Numără SERP results
        total_serp_results = db.serp_results.count_documents({}) if "serp_results" in db.list_collection_names() else 0
        
        # Top keywords (din toți agenții)
        keyword_frequency = {}
        for agent in agents_collection.find({}, {"keywords": 1, "overall_keywords": 1, "domain": 1}):
            for kw in agent.get("keywords", []) + agent.get("overall_keywords", []):
                if isinstance(kw, dict):
                    kw_text = kw.get("keyword", kw.get("name", ""))
                else:
                    kw_text = str(kw)
                if kw_text:
                    if kw_text not in keyword_frequency:
                        keyword_frequency[kw_text] = {"frequency": 0, "agents": set()}
                    keyword_frequency[kw_text]["frequency"] += 1
                    keyword_frequency[kw_text]["agents"].add(agent.get("domain", ""))
        
        top_keywords = sorted(
            [{"keyword": k, "frequency": v["frequency"], "agents_count": len(v["agents"])} 
             for k, v in keyword_frequency.items()],
            key=lambda x: x["frequency"],
            reverse=True
        )[:20]
        
        # Top competitors (din competitive_map sau slave agents)
        competitor_frequency = {}
        for agent in agents_collection.find({"master_agent_id": {"$exists": True}}, {"domain": 1}):
            domain = agent.get("domain", "")
            if domain:
                if domain not in competitor_frequency:
                    competitor_frequency[domain] = {"frequency": 0, "score": 0}
                competitor_frequency[domain]["frequency"] += 1
        
        top_competitors = sorted(
            [{"domain": k, "frequency": v["frequency"], "avg_score": 75}  # Placeholder score
             for k, v in competitor_frequency.items()],
            key=lambda x: x["frequency"],
            reverse=True
        )[:20]
        
        return {
            "ok": True,
            "total_masters": total_masters,
            "total_keywords": total_keywords,
            "total_competitors": total_competitors,
            "total_serp_results": total_serp_results,
            "top_keywords": top_keywords,
            "top_competitors": top_competitors
        }
    except Exception as e:
        logger.error(f"Error getting intelligence overview: {e}")
        return {
            "ok": False,
            "error": str(e),
            "total_masters": 0,
            "total_keywords": 0,
            "total_competitors": 0,
            "total_serp_results": 0,
            "top_keywords": [],
            "top_competitors": []
        }

@app.get("/api/intelligence/keywords")
async def get_intelligence_keywords():
    """
    Returnează keyword rankings pentru Competitive Intelligence
    """
    try:
        keywords_list = []
        
        # Extrage keywords din toți master agents
        for agent in agents_collection.find({"master_agent_id": {"$exists": False}}, 
                                            {"domain": 1, "keywords": 1, "overall_keywords": 1}):
            domain = agent.get("domain", "")
            all_keywords = agent.get("keywords", []) + agent.get("overall_keywords", [])
            
            for kw in all_keywords:
                if isinstance(kw, dict):
                    kw_text = kw.get("keyword", kw.get("name", ""))
                else:
                    kw_text = str(kw)
                
                if kw_text:
                    # Caută în serp_results pentru poziție
                    position = None
                    total_results = 0
                    top_competitors = []
                    
                    if "serp_results" in db.list_collection_names():
                        serp = db.serp_results.find_one({"keyword": kw_text, "domain": domain})
                        if serp:
                            position = serp.get("position")
                            total_results = serp.get("total_results", 0)
                            # Extrage top competitors din results
                            results = serp.get("results", [])[:3]
                            top_competitors = [{"domain": r.get("domain", ""), "position": r.get("position", 0)} 
                                             for r in results]
                    
                    keywords_list.append({
                        "keyword": kw_text,
                        "master_domain": domain,
                        "position": position,
                        "total_results": total_results,
                        "top_competitors": top_competitors
                    })
        
        # Sortează după keyword
        keywords_list.sort(key=lambda x: x["keyword"])
        
        return {
            "ok": True,
            "keywords": keywords_list[:100]  # Limitează la 100 pentru performanță
        }
    except Exception as e:
        logger.error(f"Error getting intelligence keywords: {e}")
        return {
            "ok": False,
            "error": str(e),
            "keywords": []
        }

@app.get("/api/intelligence/competitors")
async def get_intelligence_competitors():
    """
    Returnează competitive positioning pentru Competitive Intelligence
    """
    try:
        competitors_dict = {}
        
        # Colectează toți competitorii (slave agents)
        for agent in agents_collection.find({"master_agent_id": {"$exists": True}}, 
                                           {"domain": 1, "master_agent_id": 1, "keywords": 1}):
            domain = agent.get("domain", "")
            master_id = agent.get("master_agent_id")
            
            if domain:
                if domain not in competitors_dict:
                    competitors_dict[domain] = {
                        "domain": domain,
                        "appearances": 0,
                        "total_keywords": 0,
                        "masters_competing": []
                    }
                
                competitors_dict[domain]["appearances"] += 1
                competitors_dict[domain]["total_keywords"] += len(agent.get("keywords", []))
                
                # Găsește master-ul
                if master_id:
                    try:
                        master_obj_id = ObjectId(master_id) if isinstance(master_id, str) else master_id
                        master = agents_collection.find_one({"_id": master_obj_id})
                    except:
                        master = None
                    
                    if master:
                        competitors_dict[domain]["masters_competing"].append({
                            "domain": master.get("domain", ""),
                            "score": 75  # Placeholder
                        })
        
        # Calculează avg_score (placeholder)
        competitors_list = []
        for comp in competitors_dict.values():
            comp["avg_score"] = 75  # Placeholder
            competitors_list.append(comp)
        
        # Sortează după appearances
        competitors_list.sort(key=lambda x: x["appearances"], reverse=True)
        
        return {
            "ok": True,
            "competitors": competitors_list[:100]  # Limitează la 100
        }
    except Exception as e:
        logger.error(f"Error getting intelligence competitors: {e}")
        return {
            "ok": False,
            "error": str(e),
            "competitors": []
        }

@app.get("/api/intelligence/trends")
async def get_intelligence_trends():
    """
    Returnează trends și insights pentru Competitive Intelligence
    """
    try:
        trends_list = []
        top_performers = []
        
        # Colectează trends din master agents
        for agent in agents_collection.find({"master_agent_id": {"$exists": False}}, 
                                            {"domain": 1, "keywords": 1, "createdAt": 1}):
            domain = agent.get("domain", "")
            keywords_count = len(agent.get("keywords", []))
            created_at = agent.get("createdAt", datetime.now(timezone.utc))
            
            # Caută SERP results pentru acest agent
            results_count = 0
            avg_position = None
            if "serp_results" in db.list_collection_names():
                serp_results = list(db.serp_results.find({"domain": domain}).limit(10))
                results_count = len(serp_results)
                if serp_results:
                    positions = [r.get("position") for r in serp_results if r.get("position")]
                    if positions:
                        avg_position = sum(positions) / len(positions)
            
            trends_list.append({
                "master_domain": domain,
                "date": created_at.isoformat() if isinstance(created_at, datetime) else str(created_at),
                "results_count": results_count,
                "avg_position": int(avg_position) if avg_position else None,
                "keywords_tracked": keywords_count
            })
            
            # Adaugă la top performers dacă are poziții bune
            if avg_position and avg_position <= 10:
                kw_list = agent.get("keywords", [])
                kw_text = ""
                if kw_list:
                    first_kw = kw_list[0]
                    if isinstance(first_kw, dict):
                        kw_text = first_kw.get("keyword", first_kw.get("name", ""))
                    else:
                        kw_text = str(first_kw)
                
                top_performers.append({
                    "keyword": kw_text,
                    "domain": domain,
                    "position": int(avg_position)
                })
        
        # Sortează trends după dată
        trends_list.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        # Sortează top performers după poziție
        top_performers.sort(key=lambda x: x.get("position", 999))
        
        return {
            "ok": True,
            "trends": trends_list[:50],  # Ultimele 50
            "insights": {
                "top_performers": top_performers[:10]
            }
        }
    except Exception as e:
        logger.error(f"Error getting intelligence trends: {e}")
        return {
            "ok": False,
            "error": str(e),
            "trends": [],
            "insights": {
                "top_performers": []
            }
        }

# ============================================================================
# SEO REPORTS ENDPOINTS
# ============================================================================

@app.get("/api/reports")
async def get_reports():
    """
    Returnează lista de rapoarte SEO (CI Reports, CEO Reports, CEO Maps)
    """
    try:
        reports = []
        
        # Verifică dacă există colecția seo_reports
        if "seo_reports" not in db.list_collection_names():
            return {
                "ok": True,
                "reports": []
            }
        
        # Colectează rapoarte din seo_reports
        all_reports = list(db.seo_reports.find({}).sort("generated_at", -1).limit(100))
        
        for report in all_reports:
            report_data = {
                "id": str(report.get("_id")),
                "type": report.get("type", "ci_report"),  # ci_report, ceo_report, ceo_map
                "title": report.get("title", "SEO Report"),
                "generated_at": report.get("generated_at", report.get("created_at", datetime.now(timezone.utc))),
                "master_domain": report.get("master_domain", ""),
                "competitors_analyzed": report.get("competitors_analyzed", 0),
                "keywords_covered": report.get("keywords_covered", 0),
                "total_keywords": report.get("total_keywords", 0),
                "subdomains_count": report.get("subdomains_count", 0),
                "competitors_count": report.get("competitors_count", 0)
            }
            
            # Formatare dată
            if isinstance(report_data["generated_at"], datetime):
                report_data["generated_at"] = report_data["generated_at"].isoformat()
            
            reports.append(report_data)
        
        # Dacă nu există rapoarte, generează rapoarte din datele existente
        if len(reports) == 0:
            # Generează rapoarte pentru fiecare master agent
            for agent in agents_collection.find({"master_agent_id": {"$exists": False}}, 
                                               {"domain": 1, "keywords": 1, "overall_keywords": 1, "subdomains": 1}).limit(10):
                domain = agent.get("domain", "")
                if not domain:
                    continue
                
                # Numără competitors (slave agents)
                competitors_count = agents_collection.count_documents({"master_agent_id": str(agent.get("_id"))})
                
                # Numără keywords
                total_keywords = len(agent.get("keywords", [])) + len(agent.get("overall_keywords", []))
                
                # Numără subdomains
                subdomains_count = len(agent.get("subdomains", []))
                
                # Creează CI Report
                ci_report = {
                    "type": "ci_report",
                    "title": f"Competitive Intelligence Report - {domain}",
                    "master_domain": domain,
                    "master_agent": domain,
                    "competitors_analyzed": competitors_count,
                    "total_keywords": total_keywords,
                    "keywords_covered": total_keywords,
                    "generated_at": datetime.now(timezone.utc),
                    "created_at": datetime.now(timezone.utc)
                }
                
                result = db.seo_reports.insert_one(ci_report)
                reports.append({
                    "id": str(result.inserted_id),
                    "type": "ci_report",
                    "title": ci_report["title"],
                    "generated_at": ci_report["generated_at"].isoformat(),
                    "master_domain": domain,
                    "competitors_analyzed": competitors_count,
                    "keywords_covered": total_keywords,
                    "total_keywords": total_keywords
                })
        
        return {
            "ok": True,
            "reports": reports
        }
    except Exception as e:
        logger.error(f"Error getting reports: {e}")
        return {
            "ok": False,
            "error": str(e),
            "reports": []
        }

@app.get("/api/reports/{report_id}")
async def get_report_details(report_id: str, report_type: str = "ci_report"):
    """
    Returnează detaliile unui raport SEO
    """
    try:
        try:
            report_obj_id = ObjectId(report_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid report_id")
        
        report = db.seo_reports.find_one({"_id": report_obj_id})
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Formatează raportul
        report_data = {
            "id": str(report.get("_id")),
            "type": report.get("type", report_type),
            "title": report.get("title", "SEO Report"),
            "generated_at": report.get("generated_at", report.get("created_at", datetime.now(timezone.utc))),
            "master_domain": report.get("master_domain", ""),
            "master_agent": report.get("master_agent", report.get("master_domain", "")),
            "competitors_analyzed": report.get("competitors_analyzed", 0),
            "total_keywords": report.get("total_keywords", 0),
            "keywords_covered": report.get("keywords_covered", 0),
            "subdomains_count": report.get("subdomains_count", 0),
            "competitors_count": report.get("competitors_count", 0),
            "report": report.get("report", ""),
            "data": report.get("data", {}),
            "strategic_insights": report.get("strategic_insights", []),
            "competitors_list": report.get("competitors_list", []),
            "subdomains": report.get("subdomains", []),
            "competitors": report.get("competitors", [])
        }
        
        # Formatare dată
        if isinstance(report_data["generated_at"], datetime):
            report_data["generated_at"] = report_data["generated_at"].isoformat()
        
        # Dacă nu există date detaliate, le generează din baza de date
        if not report_data.get("competitors_list") and report_data.get("master_domain"):
            # Găsește master agent
            master = agents_collection.find_one({"domain": report_data["master_domain"]})
            if master:
                # Găsește slave agents (competitors)
                slaves = list(agents_collection.find({"master_agent_id": str(master.get("_id"))}).limit(20))
                report_data["competitors_list"] = [{"domain": s.get("domain", ""), "score": 75} for s in slaves]
        
        if not report_data.get("subdomains") and report_data.get("master_domain"):
            master = agents_collection.find_one({"domain": report_data["master_domain"]})
            if master:
                subdomains = master.get("subdomains", [])
                if subdomains:
                    report_data["subdomains"] = [s.get("name", str(s)) if isinstance(s, dict) else str(s) for s in subdomains]
        
        return {
            "ok": True,
            **report_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# INDUSTRY TRANSFORMATION ENDPOINTS
# ============================================================================

@app.get("/industry/construction/progress")
async def get_industry_progress():
    """
    Returnează progresul transformării industriei construcții
    """
    try:
        # Verifică dacă există colecția industry_transformation
        if "industry_transformation" not in db.list_collection_names():
            return {
                "ok": True,
                "statistics": {
                    "total_companies_discovered": 0,
                    "companies_pending": 0,
                    "companies_created": 0,
                    "construction_agents_created": 0
                }
            }
        
        # Colectează statistici din colecția industry_transformation
        stats = db.industry_transformation.find_one({"type": "statistics"})
        
        if not stats:
            # Numără agenții din industrie construcții
            construction_agents = agents_collection.count_documents({
                "industry": {"$regex": "construction|construcții|construcții", "$options": "i"}
            })
            
            return {
                "ok": True,
                "statistics": {
                    "total_companies_discovered": 0,
                    "companies_pending": 0,
                    "companies_created": construction_agents,
                    "construction_agents_created": construction_agents
                }
            }
        
        return {
            "ok": True,
            "statistics": {
                "total_companies_discovered": stats.get("total_companies_discovered", 0),
                "companies_pending": stats.get("companies_pending", 0),
                "companies_created": stats.get("companies_created", 0),
                "construction_agents_created": stats.get("construction_agents_created", 0)
            }
        }
    except Exception as e:
        logger.error(f"Error getting industry progress: {e}")
        return {
            "ok": False,
            "error": str(e),
            "statistics": {
                "total_companies_discovered": 0,
                "companies_pending": 0,
                "companies_created": 0,
                "construction_agents_created": 0
            }
        }

@app.get("/industry/construction/companies")
async def get_construction_companies(limit: int = 100):
    """
    Returnează lista de companii din industria construcții
    """
    try:
        # Verifică dacă există colecția industry_companies
        if "industry_companies" not in db.list_collection_names():
            return {
                "ok": True,
                "companies": []
            }
        
        # Colectează companii din colecția industry_companies
        companies = list(db.industry_companies.find({
            "industry": "construction"
        }).limit(limit))
        
        companies_list = []
        for company in companies:
            companies_list.append({
                "id": str(company.get("_id")),
                "name": company.get("name", ""),
                "domain": company.get("domain", ""),
                "status": company.get("status", "pending"),  # pending, processing, completed, failed
                "discovered_at": company.get("discovered_at", company.get("created_at", datetime.now(timezone.utc))).isoformat() if isinstance(company.get("discovered_at"), datetime) else str(company.get("discovered_at", "")),
                "agent_id": str(company.get("agent_id", "")) if company.get("agent_id") else None
            })
        
        return {
            "ok": True,
            "companies": companies_list
        }
    except Exception as e:
        logger.error(f"Error getting construction companies: {e}")
        return {
            "ok": False,
            "error": str(e),
            "companies": []
        }

@app.get("/industry/construction/logs")
async def get_construction_logs(limit: int = 200):
    """
    Returnează logs-urile transformării industriei construcții
    """
    try:
        # Verifică dacă există colecția industry_logs
        if "industry_logs" not in db.list_collection_names():
            return {
                "ok": True,
                "logs": []
            }
        
        # Colectează logs din colecția industry_logs
        logs = list(db.industry_logs.find({
            "industry": "construction"
        }).sort("timestamp", -1).limit(limit))
        
        logs_list = []
        for log in logs:
            logs_list.append({
                "_id": str(log.get("_id")),
                "message": log.get("message", ""),
                "stage": log.get("stage", "info"),  # info, discovery, processing, complete, error, warning
                "timestamp": log.get("timestamp", datetime.now(timezone.utc)).isoformat() if isinstance(log.get("timestamp"), datetime) else str(log.get("timestamp", ""))
            })
        
        return {
            "ok": True,
            "logs": logs_list
        }
    except Exception as e:
        logger.error(f"Error getting construction logs: {e}")
        return {
            "ok": False,
            "error": str(e),
            "logs": []
        }

@app.get("/industry/construction/gpu-recommendations")
async def get_gpu_recommendations():
    """
    Returnează recomandări GPU pentru transformarea industriei
    """
    try:
        # Verifică GPU-urile disponibile (simplificat)
        # În producție, ar trebui să verific GPU-urile reale
        gpu_count = 1  # Presupunem 1 GPU
        total_vram_gb = 24  # Presupunem 24 GB VRAM
        
        # Calculează recomandări bazate pe VRAM
        conservative = max(1, int(total_vram_gb / 8))  # 3 agenți paraleli (8 GB per agent)
        optimal = max(1, int(total_vram_gb / 6))  # 4 agenți paraleli (6 GB per agent)
        aggressive = max(1, int(total_vram_gb / 4))  # 6 agenți paraleli (4 GB per agent)
        
        return {
            "ok": True,
            "recommendations": {
                "hardware": {
                    "gpu_count": gpu_count,
                    "gpu_model": "NVIDIA GPU",
                    "total_vram_gb": total_vram_gb
                },
                "conservative": {
                    "parallel_agents": conservative,
                    "description": "Safe parallel processing"
                },
                "optimal": {
                    "parallel_agents": optimal,
                    "description": "Balanced performance"
                },
                "aggressive": {
                    "parallel_agents": aggressive,
                    "description": "Maximum throughput"
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting GPU recommendations: {e}")
        return {
            "ok": False,
            "error": str(e),
            "recommendations": {}
        }

@app.get("/industry/construction/strategy")
async def get_construction_strategy(method: str = "deepseek", max_companies: int = 500, max_parallel: int = 33):
    """
    Generează strategia DeepSeek pentru transformarea industriei construcții
    """
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            return {
                "ok": False,
                "strategy": "Eroare: DEEPSEEK_API_KEY nu este configurat în .env"
            }
        
        # Construiește prompt-ul pentru DeepSeek
        prompt = f"""Generează o strategie detaliată pentru transformarea industriei construcții din România în agenți AI.

Parametri:
- Metodă descoperire: {method}
- Număr maxim companii: {max_companies}
- Paralelism maxim: {max_parallel}

Strategia trebuie să includă:
1. Metodologia de descoperire a companiilor din industria construcții
2. Criteriile de selecție pentru companii relevante
3. Procesul de transformare a companiilor în agenți AI
4. Optimizări pentru procesare paralelă
5. Recomandări pentru scalare

Răspunde în limba română, structurat și detaliat."""

        # Apelează DeepSeek API
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {deepseek_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ești un expert în transformarea digitală și inteligență artificială pentru industrii."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                strategy = data.get("choices", [{}])[0].get("message", {}).get("content", "Strategie generată")
                
                return {
                    "ok": True,
                    "strategy": strategy
                }
            else:
                return {
                    "ok": False,
                    "strategy": f"Eroare DeepSeek API: {response.status_code} - {response.text[:200]}"
                }
    except Exception as e:
        logger.error(f"Error generating strategy: {e}")
        return {
            "ok": False,
            "strategy": f"Eroare la generarea strategiei: {str(e)}"
        }

@app.post("/industry/construction/transform")
async def start_industry_transformation(request: Request, background_tasks: BackgroundTasks):
    """
    Pornește transformarea industriei construcții
    """
    try:
        # Get request body
        try:
            data = await request.json()
        except:
            data = {}
        
        # Default values
        discovery_method = data.get("discovery_method", "deepseek")
        max_companies = data.get("max_companies", 500)
        max_parallel_agents = data.get("max_parallel_agents", 33)
        
        # Creează colecțiile dacă nu există
        if "industry_transformation" not in db.list_collection_names():
            db.industry_transformation.insert_one({
                "type": "statistics",
                "total_companies_discovered": 0,
                "companies_pending": 0,
                "companies_created": 0,
                "construction_agents_created": 0,
                "created_at": datetime.now(timezone.utc)
            })
        
        if "industry_logs" not in db.list_collection_names():
            db.industry_logs.insert_one({
                "industry": "construction",
                "message": "Initialized",
                "stage": "info",
                "timestamp": datetime.now(timezone.utc)
            })
        
        # Adaugă log pentru pornirea transformării
        transformation_id = str(ObjectId())
        db.industry_logs.insert_one({
            "industry": "construction",
            "message": f"✅ Transformare inițiată: {discovery_method}, max_companies={max_companies}, max_parallel={max_parallel_agents}",
            "stage": "info",
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Pornește transformarea în background
        background_tasks.add_task(
            run_industry_transformation,
            transformation_id,
            discovery_method,
            max_companies,
            max_parallel_agents
        )
        
        return {
            "ok": True,
            "message": "Transformare inițiată cu succes",
            "transformation_id": transformation_id
        }
    except Exception as e:
        logger.error(f"Error starting transformation: {e}")
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/industry/construction/chat")
async def industry_chat(data: dict):
    """
    Chat cu DeepSeek pentru transformarea industriei
    """
    try:
        message = data.get("message", "")
        session_id = data.get("session_id")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            return {
                "ok": False,
                "response": "Eroare: DEEPSEEK_API_KEY nu este configurat"
            }
        
        # Apelează DeepSeek API
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {deepseek_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ești un asistent expert în transformarea industriei construcții în agenți AI. Răspunde în limba română."
                        },
                        {
                            "role": "user",
                            "content": message
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "Răspuns generat")
                
                # Generează session_id dacă nu există
                if not session_id:
                    session_id = str(ObjectId())
                
                return {
                    "ok": True,
                    "response": response_text,
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "ok": False,
                    "response": f"Eroare DeepSeek API: {response.status_code}"
                }
    except Exception as e:
        logger.error(f"Error in industry chat: {e}")
        return {
            "ok": False,
            "response": f"Eroare: {str(e)}"
        }

# ============================================================================
# INDUSTRY TRANSFORMATION BACKGROUND LOGIC
# ============================================================================

async def run_industry_transformation(
    transformation_id: str,
    discovery_method: str,
    max_companies: int,
    max_parallel_agents: int
):
    """
    Rulează transformarea industriei în background
    """
    try:
        from tools.construction_agent_creator import ConstructionAgentCreator
        from dotenv import load_dotenv
        import os
        import httpx
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        load_dotenv()
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        
        # Log: Început descoperire
        db.industry_logs.insert_one({
            "industry": "construction",
            "message": f"🔍 Început descoperire site-uri din industria construcții (max: {max_companies})",
            "stage": "discovery",
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Actualizează statistici
        db.industry_transformation.update_one(
            {"type": "statistics"},
            {"$set": {
                "total_companies_discovered": 0,
                "companies_pending": max_companies,
                "companies_created": 0,
                "construction_agents_created": 0,
                "last_updated": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        
        # Faza 1: Descoperire site-uri cu DeepSeek
        discovered_sites = []
        
        if discovery_method == "deepseek":
            # Folosește DeepSeek pentru a descoperi site-uri relevante
            prompt = f"""Generează o listă de {max_companies} site-uri web din România care fac parte din industria construcțiilor.

Include:
- Companii de construcții generale
- Firme de renovări și amenajări interioare
- Companiile de instalații (electricitate, instalații sanitare, încălzire)
- Firme de zugrăveli și finisaje
- Companiile de construcții rezidențiale și comerciale
- Firme de construcții industriale
- Companiile de construcții rutiere și infrastructură

Pentru fiecare site, returnează DOAR domeniul (ex: exemplu.ro), fără http:// sau www.
Returnează DOAR lista de domenii, unul pe linie, fără numerotare sau alte texte.
Maxim {max_companies} site-uri."""

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {deepseek_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {
                                "role": "system",
                                "content": "Ești un expert în identificarea companiilor din industria construcțiilor din România."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.7,
                        "max_tokens": 4000
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Parsează site-urile din răspuns
                    lines = response_text.strip().split("\n")
                    for line in lines:
                        domain = line.strip()
                        # Elimină http://, https://, www.
                        domain = domain.replace("http://", "").replace("https://", "").replace("www.", "")
                        domain = domain.split("/")[0].strip()
                        
                        # Validare domeniu
                        if domain and "." in domain and len(domain) > 3:
                            # Elimină spații și caractere speciale
                            domain = domain.split()[0] if domain.split() else domain
                            if domain not in discovered_sites:
                                discovered_sites.append(domain)
                    
                    # Limitează la max_companies
                    discovered_sites = discovered_sites[:max_companies]
                    
                    # Salvează site-urile descoperite în MongoDB
                    for domain in discovered_sites:
                        # Verifică dacă site-ul există deja
                        existing = db.industry_companies.find_one({"domain": domain, "industry": "construction"})
                        if not existing:
                            db.industry_companies.insert_one({
                                "domain": domain,
                                "name": domain,
                                "industry": "construction",
                                "status": "pending",
                                "discovered_at": datetime.now(timezone.utc),
                                "transformation_id": transformation_id
                            })
                    
                    # Log: Descoperire completă
                    db.industry_logs.insert_one({
                        "industry": "construction",
                        "message": f"✅ Descoperite {len(discovered_sites)} site-uri relevante",
                        "stage": "discovery",
                        "timestamp": datetime.now(timezone.utc)
                    })
                    
                    # Actualizează statistici
                    db.industry_transformation.update_one(
                        {"type": "statistics"},
                        {"$set": {
                            "total_companies_discovered": len(discovered_sites),
                            "companies_pending": len(discovered_sites),
                            "last_updated": datetime.now(timezone.utc)
                        }}
                    )
        
        # Faza 2: Transformare în agenți AI (în paralel)
        if discovered_sites:
            db.industry_logs.insert_one({
                "industry": "construction",
                "message": f"🚀 Început crearea agenților AI pentru {len(discovered_sites)} site-uri (paralelism: {max_parallel_agents})",
                "stage": "processing",
                "timestamp": datetime.now(timezone.utc)
            })
            
            # Procesează site-urile în batch-uri paralele
            creator = ConstructionAgentCreator()
            completed = 0
            failed = 0
            
            # Procesează în batch-uri
            for i in range(0, len(discovered_sites), max_parallel_agents):
                batch = discovered_sites[i:i + max_parallel_agents]
                
                # Creează agenți în paralel pentru batch-ul curent
                tasks = []
                for domain in batch:
                    site_url = f"https://{domain}" if not domain.startswith("http") else domain
                    tasks.append(create_agent_for_site(creator, site_url, domain, transformation_id))
                
                # Așteaptă batch-ul să se termine
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Procesează rezultatele
                for idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed += 1
                        db.industry_logs.insert_one({
                            "industry": "construction",
                            "message": f"❌ Eroare la crearea agentului pentru {batch[idx]}: {str(result)[:100]}",
                            "stage": "error",
                            "timestamp": datetime.now(timezone.utc)
                        })
                    elif result:
                        completed += 1
                        db.industry_logs.insert_one({
                            "industry": "construction",
                            "message": f"✅ Agent creat cu succes pentru {batch[idx]}",
                            "stage": "processing",
                            "timestamp": datetime.now(timezone.utc)
                        })
                
                # Actualizează progresul
                db.industry_transformation.update_one(
                    {"type": "statistics"},
                    {"$set": {
                        "companies_created": completed,
                        "construction_agents_created": completed,
                        "companies_pending": len(discovered_sites) - completed - failed,
                        "last_updated": datetime.now(timezone.utc)
                    }}
                )
                
                # Log progres
                progress_pct = int((completed + failed) / len(discovered_sites) * 100)
                db.industry_logs.insert_one({
                    "industry": "construction",
                    "message": f"📊 Progres: {completed + failed}/{len(discovered_sites)} ({progress_pct}%) - {completed} succes, {failed} eșecuri",
                    "stage": "processing",
                    "timestamp": datetime.now(timezone.utc)
                })
            
            # Log: Finalizare
            db.industry_logs.insert_one({
                "industry": "construction",
                "message": f"🎉 Transformare completă! {completed} agenți creați cu succes, {failed} eșecuri",
                "stage": "complete",
                "timestamp": datetime.now(timezone.utc)
            })
        else:
            db.industry_logs.insert_one({
                "industry": "construction",
                "message": "⚠️ Nu s-au descoperit site-uri. Verifică configurația DeepSeek.",
                "stage": "warning",
                "timestamp": datetime.now(timezone.utc)
            })
            
    except Exception as e:
        logger.error(f"Error in industry transformation: {e}")
        import traceback
        error_trace = traceback.format_exc()
        db.industry_logs.insert_one({
            "industry": "construction",
            "message": f"❌ Eroare critică în transformare: {str(e)[:200]}",
            "stage": "error",
            "timestamp": datetime.now(timezone.utc)
        })

async def create_agent_for_site(creator, site_url: str, domain: str, transformation_id: str):
    """
    Creează un agent AI pentru un site specific
    """
    try:
        # Import aici pentru a fi sigur că este disponibil
        from concurrent.futures import ThreadPoolExecutor
        
        # Actualizează status-ul site-ului
        db.industry_companies.update_one(
            {"domain": domain, "industry": "construction"},
            {"$set": {"status": "processing"}}
        )
        
        # Creează agentul folosind create_site_agent (metoda principală)
        # Rulează în thread pentru că nu este async
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            agent_result = await loop.run_in_executor(
                executor,
                lambda: creator.create_site_agent(site_url, industry="construction")
            )
        
        # Verifică dacă agentul a fost creat
        if agent_result:
            # Găsește agentul în MongoDB după domain
            from config.database_config import MONGODB_URI, MONGODB_DATABASE
            from pymongo import MongoClient
            temp_client = MongoClient(MONGODB_URI)
            temp_db = temp_client[MONGODB_DATABASE]
            temp_agents = temp_db.site_agents if 'site_agents' in temp_db.list_collection_names() else temp_db.agents
            domain = site_url.replace("https://", "").replace("http://", "").split("/")[0]
            agent = temp_agents.find_one({"domain": domain})
            temp_client.close()
        else:
            agent = None
        
        if agent:
            # Actualizează status-ul site-ului
            db.industry_companies.update_one(
                {"domain": domain, "industry": "construction"},
                {"$set": {
                    "status": "completed",
                    "agent_id": str(agent.get("_id")) if isinstance(agent, dict) else str(agent),
                    "completed_at": datetime.now(timezone.utc)
                }}
            )
            return True
        else:
            db.industry_companies.update_one(
                {"domain": domain, "industry": "construction"},
                {"$set": {"status": "failed"}}
            )
            return False
            
    except Exception as e:
        logger.error(f"Error creating agent for {domain}: {e}")
        db.industry_companies.update_one(
            {"domain": domain, "industry": "construction"},
            {"$set": {"status": "failed"}}
        )
        raise


# ============================================================================
# TASK AI AGENT - Agent AI General cu DeepSeek pentru Task Execution
# ============================================================================

@app.post("/api/task-ai/chat")
async def task_ai_chat(request: dict = Body(...)):
    """
    Chat cu agentul AI general care poate executa task-uri
    Poate executa: comenzi shell, API calls, file operations, database queries, etc.
    """
    try:
        from task_ai_agent import TaskAIAgent
        
        message = request.get("message", "")
        session_id = request.get("session_id")
        
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        
        # Inițializează agentul
        agent = TaskAIAgent()
        
        # Apelează chat-ul (sincron, dar rulează rapid)
        result = agent.chat(message, session_id)
        
        if result.get("ok"):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Chat error"))
            
    except Exception as e:
        logger.error(f"Error in task AI chat: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/task-ai/sessions/{session_id}")
async def get_task_ai_session(session_id: str):
    """Obține istoricul conversației pentru task AI agent"""
    try:
        session = db.task_ai_chat_history.find_one({"session_id": session_id})
        
        if not session:
            return {"ok": False, "message": "Session not found"}
        
        return {
            "ok": True,
            "messages": session.get("messages", []),
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error getting task AI session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/task-ai/sessions")
async def list_task_ai_sessions(limit: int = Query(10, ge=1, le=100)):
    """Listează sesiunile de chat pentru task AI agent"""
    try:
        sessions = list(db.task_ai_chat_history.find(
            {},
            {"session_id": 1, "updated_at": 1, "messages": {"$slice": 1}}
        ).sort("updated_at", -1).limit(limit))
        
        # Convertește ObjectId în string
        for session in sessions:
            if "_id" in session:
                session["_id"] = str(session["_id"])
        
        return {
            "ok": True,
            "sessions": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        logger.error(f"Error listing task AI sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# AGENT CONSCIENCE SYSTEM - Conștiință pentru agenți
# ============================================================================

@app.get("/api/agents/{agent_id}/conscience/state")
async def get_agent_state(agent_id: str):
    """Obține starea curentă a agentului (conștiință de SINE și STARE)"""
    try:
        from agent_state_memory import AgentStateMemory
        
        state_memory = AgentStateMemory()
        state = state_memory.get_state(agent_id)
        
        if not state:
            return {"ok": False, "message": "State not found"}
        
        return {"ok": True, "state": state}
    except Exception as e:
        logger.error(f"Error getting agent state: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/conscience/state")
async def save_agent_state(agent_id: str, state_data: dict = Body(...)):
    """Salvează starea agentului"""
    try:
        from agent_state_memory import AgentStateMemory
        
        state_memory = AgentStateMemory()
        success = state_memory.save_state(agent_id, state_data)
        
        if success:
            return {"ok": True, "message": "State saved"}
        else:
            return {"ok": False, "message": "Failed to save state"}
    except Exception as e:
        logger.error(f"Error saving agent state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/conscience/health")
async def get_agent_health(agent_id: str):
    """Obține scorurile de sănătate ale agentului"""
    try:
        from agent_health_score import AgentHealthScore
        
        health_score = AgentHealthScore()
        scores = health_score.calculate_all_scores(agent_id)
        health_score.save_health_scores(agent_id, scores)
        
        return {"ok": True, "scores": scores}
    except Exception as e:
        logger.error(f"Error getting agent health: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/conscience/reflect")
async def trigger_agent_reflection(agent_id: str):
    """Trigger auto-reflecție pentru agent"""
    try:
        from agent_self_reflection import AgentSelfReflection
        from agent_state_memory import AgentStateMemory
        
        reflection = AgentSelfReflection()
        state_memory = AgentStateMemory()
        reflection.set_state_memory(state_memory)
        
        result = reflection.perform_reflection(agent_id)
        
        if result:
            return {"ok": True, "reflection": result}
        else:
            return {"ok": False, "message": "Reflection failed"}
    except Exception as e:
        logger.error(f"Error triggering reflection: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/conscience/reflection")
async def get_agent_reflection(agent_id: str):
    """Obține ultima reflecție a agentului"""
    try:
        from agent_self_reflection import AgentSelfReflection
        
        reflection = AgentSelfReflection()
        latest = reflection.get_latest_reflection(agent_id)
        
        if latest:
            return {"ok": True, "reflection": latest}
        else:
            return {"ok": False, "message": "No reflection found"}
    except Exception as e:
        logger.error(f"Error getting reflection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/conscience/awareness")
async def get_agent_awareness(agent_id: str, hours: int = Query(24, ge=1, le=168)):
    """Obține feed-ul de conștiință al agentului"""
    try:
        from agent_awareness_feed import AgentAwarenessFeed
        
        awareness = AgentAwarenessFeed()
        feed = awareness.get_feed(agent_id, hours=hours)
        summary = awareness.get_summary(agent_id, days=7)
        
        return {
            "ok": True,
            "feed": feed,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error getting awareness feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/conscience/awareness/detect")
async def detect_awareness(agent_id: str):
    """Detectează competitori noi, pattern-uri, anomalii"""
    try:
        from agent_awareness_feed import AgentAwarenessFeed
        
        awareness = AgentAwarenessFeed()
        
        competitors = awareness.detect_new_competitors(agent_id)
        patterns = awareness.detect_patterns(agent_id)
        anomalies = awareness.detect_anomalies(agent_id)
        
        return {
            "ok": True,
            "discoveries": {
                "new_competitors": competitors,
                "patterns": patterns,
                "anomalies": anomalies
            }
        }
    except Exception as e:
        logger.error(f"Error detecting awareness: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/conscience/journal")
async def get_agent_journal(agent_id: str, days: int = Query(30, ge=1, le=365)):
    """Obține jurnalul agentului"""
    try:
        from agent_journal import AgentJournal
        
        journal = AgentJournal()
        entries = journal.get_entries(agent_id, days=days)
        timeline = journal.get_timeline(agent_id, days=days)
        stats = journal.get_statistics(agent_id, days=days)
        
        return {
            "ok": True,
            "entries": entries,
            "timeline": timeline,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error getting journal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/conscience/journal")
async def add_journal_entry(agent_id: str, entry_data: dict = Body(...)):
    """Adaugă o intrare în jurnal"""
    try:
        from agent_journal import AgentJournal
        
        journal = AgentJournal()
        success = journal.add_entry(
            agent_id,
            entry_data.get("entry", ""),
            entry_data.get("entry_type", "general"),
            entry_data.get("metadata")
        )
        
        if success:
            return {"ok": True, "message": "Entry added"}
        else:
            return {"ok": False, "message": "Failed to add entry"}
    except Exception as e:
        logger.error(f"Error adding journal entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/conscience/summary")
async def get_conscience_summary(agent_id: str):
    """Obține un rezumat complet al conștiinței agentului"""
    try:
        from agent_state_memory import AgentStateMemory
        from agent_health_score import AgentHealthScore
        from agent_self_reflection import AgentSelfReflection
        from agent_awareness_feed import AgentAwarenessFeed
        from agent_journal import AgentJournal
        
        state_memory = AgentStateMemory()
        health_score = AgentHealthScore()
        reflection = AgentSelfReflection()
        awareness = AgentAwarenessFeed()
        journal = AgentJournal()
        
        # Colectează toate datele
        state = state_memory.get_state(agent_id)
        health = health_score.get_health_scores(agent_id)
        latest_reflection = reflection.get_latest_reflection(agent_id)
        awareness_summary = awareness.get_summary(agent_id, days=7)
        journal_stats = journal.get_statistics(agent_id, days=30)
        
        return {
            "ok": True,
            "summary": {
                "state": state,
                "health": health,
                "latest_reflection": latest_reflection,
                "awareness": awareness_summary,
                "journal_stats": journal_stats
            }
        }
    except Exception as e:
        logger.error(f"Error getting conscience summary: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════════════════
#                     BUSINESS CONSULTING AI ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/agents/{agent_id}/consulting/generate-report")
async def generate_consulting_report(agent_id: str, report_type: str = Query("full", enum=["full", "quick", "seo", "expansion"])):
    """Generează un raport de consultanță AI pentru agentul specificat"""
    try:
        import requests as req
        from qdrant_client import QdrantClient
        
        # Get agent data
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        domain = agent.get("domain", "unknown")
        
        # Get competitive map
        cmap = db.competitive_map.find_one({"master_agent_id": agent_id})
        keywords = cmap.get("keywords_used", []) if cmap else []
        competitors = cmap.get("competitive_map", []) if cmap else []
        
        # Get competitor stats
        competitor_stats = []
        for comp in competitors[:15]:
            slave = db.site_agents.find_one({"domain": comp.get("domain")})
            cfg = slave.get("agent_config", {}) if slave else {}
            competitor_stats.append({
                "domain": comp.get("domain"),
                "rank": comp.get("rank", 0),
                "relevance": comp.get("relevance_score", 0),
                "pages": cfg.get("pages_scraped", 0),
                "chunks": cfg.get("embeddings_count", 0)
            })
        
        # Build prompt based on report type
        if report_type == "quick":
            prompt = f"""Analizează rapid competiția pentru {domain} și oferă:
1. Top 5 competitori și ce îi face puternici
2. 3 acțiuni imediate de implementat
3. Keywords de prioritizat

Competitori: {json.dumps(competitor_stats[:10], ensure_ascii=False)}
Keywords: {', '.join(keywords[:20])}"""
        
        elif report_type == "seo":
            prompt = f"""Oferă un audit SEO pentru {domain} bazat pe analiza competiției:
1. Gap analysis keywords
2. Recomandări on-page
3. Strategie de conținut
4. Link building suggestions

Competitori: {json.dumps(competitor_stats, ensure_ascii=False)}
Keywords: {', '.join(keywords)}"""
        
        elif report_type == "expansion":
            prompt = f"""Sugerează strategii de expansiune pentru {domain}:
1. Subdomenii/micrositeuri noi de creat
2. Servicii noi de adăugat
3. Parteneriate B2B recomandate
4. Nișe neexploatate

Competitori: {json.dumps(competitor_stats, ensure_ascii=False)}
Keywords: {', '.join(keywords)}"""
        
        else:  # full
            prompt = f"""Oferă un raport complet de consultanță pentru {domain}:

COMPETITORI ({len(competitor_stats)}):
{json.dumps(competitor_stats, indent=2, ensure_ascii=False)}

KEYWORDS ({len(keywords)}):
{', '.join(keywords[:40])}

Oferă:
1. ÎNTREBĂRI BUSINESS DISCOVERY (15-20 întrebări pentru client)
2. RECOMANDĂRI PE CANALE (digital + tradițional)
3. PLAN DE ACȚIUNE 90 ZILE
4. TEMPLATE OFERTE B2B (3 template-uri)
5. SUBDOMENII SUGERATE (5-7 idei)

Răspunde în română, structurat și acționabil."""

        # Call DeepSeek
        DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
        DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
        
        response = req.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 4000 if report_type == "full" else 2000
            },
            timeout=180
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"DeepSeek API error: {response.text}")
        
        result = response.json()
        report_content = result['choices'][0]['message']['content']
        usage = result.get('usage', {})
        
        # Save to MongoDB
        report_doc = {
            "master_agent_id": agent_id,
            "domain": domain,
            "report_type": report_type,
            "generated_by": "deepseek-chat",
            "generated_at": datetime.now(timezone.utc),
            "content": report_content,
            "metadata": {
                "tokens_input": usage.get('prompt_tokens', 0),
                "tokens_output": usage.get('completion_tokens', 0),
                "competitors_analyzed": len(competitor_stats),
                "keywords_used": len(keywords)
            }
        }
        
        db.consulting_reports.insert_one(report_doc)
        
        return {
            "ok": True,
            "report": report_content,
            "report_type": report_type,
            "metadata": report_doc["metadata"]
        }
        
    except Exception as e:
        logger.error(f"Error generating consulting report: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/consulting/reports")
async def get_consulting_reports(agent_id: str, limit: int = Query(10, ge=1, le=50)):
    """Obține rapoartele de consultanță anterioare"""
    try:
        reports = list(db.consulting_reports.find(
            {"master_agent_id": agent_id},
            {"content": 0}  # Exclude content for list view
        ).sort("generated_at", -1).limit(limit))
        
        for r in reports:
            r["_id"] = str(r["_id"])
        
        return {"ok": True, "reports": reports}
    except Exception as e:
        logger.error(f"Error getting consulting reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/consulting/reports/{report_id}")
async def get_consulting_report(agent_id: str, report_id: str):
    """Obține un raport specific de consultanță"""
    try:
        report = db.consulting_reports.find_one({
            "_id": ObjectId(report_id),
            "master_agent_id": agent_id
        })
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        report["_id"] = str(report["_id"])
        return {"ok": True, "report": report}
    except Exception as e:
        logger.error(f"Error getting consulting report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/{agent_id}/consulting/ask")
async def ask_consulting_question(agent_id: str, question_data: dict = Body(...)):
    """Pune o întrebare specifică consultantului AI"""
    try:
        import requests as req
        
        question = question_data.get("question", "")
        context = question_data.get("context", "")
        
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
        
        # Get agent data for context
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        domain = agent.get("domain", "unknown") if agent else "unknown"
        
        # Get competitive map for context
        cmap = db.competitive_map.find_one({"master_agent_id": agent_id})
        keywords = cmap.get("keywords_used", [])[:20] if cmap else []
        competitors = [c.get("domain") for c in cmap.get("competitive_map", [])[:10]] if cmap else []
        
        prompt = f"""Ești un consultant de afaceri pentru industria construcțiilor din România.

CLIENT: {domain}
COMPETITORI: {', '.join(competitors)}
KEYWORDS: {', '.join(keywords)}

CONTEXT ADIȚIONAL: {context}

ÎNTREBARE CLIENT: {question}

Răspunde în română, concis și cu exemple concrete."""

        # Call DeepSeek
        DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
        DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
        
        response = req.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1500
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"DeepSeek API error: {response.text}")
        
        result = response.json()
        answer = result['choices'][0]['message']['content']
        
        return {
            "ok": True,
            "question": question,
            "answer": answer
        }
        
    except Exception as e:
        logger.error(f"Error asking consulting question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/consulting/discovery-questions")
async def get_discovery_questions(agent_id: str, category: str = Query(None)):
    """Obține întrebările de business discovery pentru client"""
    questions = {
        "team_capacity": [
            "Câți angajați permanenți și colaboratori externi aveți?",
            "Ce specializări tehnice acoperă echipa?",
            "Care este capacitatea maximă lunară de proiecte?",
            "Aveți proiect manager dedicat pentru fiecare lucrare?",
            "Ce echipamente și tehnologii utilizați?"
        ],
        "services_differentiation": [
            "Care sunt cele 3 servicii cu cea mai mare marjă de profit?",
            "Ce tip de proiecte preferați (apartamente, case, spații comerciale)?",
            "Care este principalul factor care vă diferențiază de concurență?",
            "Oferiți garanție pentru lucrările executate?",
            "Aveți parteneriate cu furnizori de materiale?"
        ],
        "clients_market": [
            "Care este profilul clientului ideal (vârstă, venit, locație)?",
            "Ce zonă geografică acoperiți în mod regulat?",
            "Care este bugetul mediu al unui proiect complet?",
            "Care este principalul canal prin care vă găsesc clienții?",
            "Ce procent din venituri provine de la clienți recurenți?"
        ],
        "objectives_resources": [
            "Ce obiective de business aveți pentru următoarele 6-12 luni?",
            "Există un buget alocat pentru marketing și promovare?",
            "Aveți resurse interne pentru gestionarea conținutului online?",
            "Care este punctul de durere cel mai mare în obținerea de noi clienți?",
            "Sunteți deschiși să investiți în instrumente digitale?"
        ]
    }
    
    if category and category in questions:
        return {"ok": True, "category": category, "questions": questions[category]}
    
    return {"ok": True, "questions": questions}


# ============================================================================
# 🎯 BUSINESS INTELLIGENCE ENDPOINTS
# Gap Analysis, Positioning Score, Action Plan, Alerts, AI Coach
# ============================================================================

from business_intelligence import (
    GapAnalyzer, 
    PositioningScorer, 
    ActionPlanGenerator,
    BusinessDiscoveryWizard,
    CompetitorAlertSystem,
    AICoach
)

@app.get("/api/agents/{agent_id}/business-intelligence/gap-analysis")
async def get_gap_analysis(agent_id: str):
    """
    🔍 Gap Analysis - Ce au competitorii și tu nu
    Identifică keywords, servicii și topicuri lipsă
    """
    try:
        analyzer = GapAnalyzer(agent_id)
        content_gaps = analyzer.analyze_content_gaps()
        keyword_opportunities = analyzer.analyze_keyword_opportunities()
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "content_gaps": content_gaps,
            "keyword_opportunities": keyword_opportunities,
            "summary": {
                "total_keyword_gaps": len(content_gaps.get("keyword_gaps", [])),
                "total_service_gaps": len(content_gaps.get("service_gaps", [])),
                "total_topic_gaps": len(content_gaps.get("topic_gaps", [])),
                "total_opportunities": len(keyword_opportunities)
            }
        }
    except Exception as e:
        logger.error(f"Error in gap analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/positioning-score")
async def get_positioning_score(agent_id: str):
    """
    📊 Positioning Score - Scorul tău de poziționare în piață (0-100)
    Include breakdown pe categorii și comparație cu competitorii
    """
    try:
        scorer = PositioningScorer(agent_id)
        score = scorer.calculate_score()
        comparison = scorer.get_comparison_with_top(top_n=3)
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "positioning": score,
            "comparison_with_top": comparison
        }
    except Exception as e:
        logger.error(f"Error calculating positioning score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/action-plan")
async def get_action_plan(agent_id: str):
    """
    📋 Action Plan - Plan de acțiune prioritizat
    Quick Wins, Medium Term, Long Term cu pași concreți
    """
    try:
        generator = ActionPlanGenerator(agent_id)
        plan = generator.generate_plan()
        
        return {
            "ok": True,
            "agent_id": agent_id,
            **plan
        }
    except Exception as e:
        logger.error(f"Error generating action plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/alerts")
async def get_competitor_alerts(agent_id: str):
    """
    🚨 Competitor Alerts - Alerte despre mișcări competitori
    Competitori noi, schimbări poziții, gap-uri critice
    """
    try:
        alert_system = CompetitorAlertSystem(agent_id)
        alerts = alert_system.get_alert_summary()
        
        return {
            "ok": True,
            "agent_id": agent_id,
            **alerts
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/discovery-wizard")
async def get_discovery_wizard(agent_id: str):
    """
    🧙 Business Discovery Wizard - Întrebări pentru personalizare
    Returnează întrebările pentru a înțelege mai bine afacerea
    """
    try:
        questions = BusinessDiscoveryWizard.get_questions()
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "total_questions": len(questions),
            "questions": questions,
            "instructions": "Răspunde la toate întrebările pentru recomandări personalizate"
        }
    except Exception as e:
        logger.error(f"Error getting discovery wizard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class DiscoveryAnswers(BaseModel):
    answers: Dict[str, Any]


@app.post("/api/agents/{agent_id}/business-intelligence/discovery-wizard/submit")
async def submit_discovery_answers(agent_id: str, data: DiscoveryAnswers):
    """
    📝 Submit Discovery Answers - Trimite răspunsurile și primește recomandări personalizate
    """
    try:
        # Obține gap analysis și scor pentru context
        analyzer = GapAnalyzer(agent_id)
        scorer = PositioningScorer(agent_id)
        
        gap_analysis = analyzer.analyze_content_gaps()
        score = scorer.calculate_score()
        
        # Generează recomandări personalizate
        recommendations = BusinessDiscoveryWizard.generate_personalized_recommendations(
            data.answers, gap_analysis, score
        )
        
        # Salvează răspunsurile în DB
        db.business_discovery.update_one(
            {"agent_id": agent_id},
            {
                "$set": {
                    "answers": data.answers,
                    "submitted_at": datetime.now(timezone.utc),
                    "recommendations": recommendations
                }
            },
            upsert=True
        )
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "answers_saved": True,
            **recommendations
        }
    except Exception as e:
        logger.error(f"Error submitting discovery answers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/coach/weekly-checkin")
async def get_weekly_checkin(agent_id: str):
    """
    🤖 AI Coach Weekly Check-in - Verificare săptămânală cu sugestii
    """
    try:
        coach = AICoach(agent_id)
        checkin = coach.get_weekly_checkin()
        
        return {
            "ok": True,
            "agent_id": agent_id,
            **checkin
        }
    except Exception as e:
        logger.error(f"Error getting weekly checkin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CoachQuestion(BaseModel):
    question: str


@app.post("/api/agents/{agent_id}/business-intelligence/coach/ask")
async def ask_ai_coach(agent_id: str, data: CoachQuestion):
    """
    💬 Ask AI Coach - Pune o întrebare coach-ului AI
    """
    try:
        coach = AICoach(agent_id)
        response = coach.ask_coach(data.question)
        
        return {
            "ok": True,
            "agent_id": agent_id,
            **response
        }
    except Exception as e:
        logger.error(f"Error asking AI coach: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/dashboard")
async def get_business_intelligence_dashboard(agent_id: str):
    """
    📊 Full BI Dashboard - Toate datele într-un singur endpoint
    Combină scor, gaps, alerts și sugestii
    """
    try:
        # Colectează toate datele
        scorer = PositioningScorer(agent_id)
        analyzer = GapAnalyzer(agent_id)
        alert_system = CompetitorAlertSystem(agent_id)
        coach = AICoach(agent_id)
        
        score = scorer.calculate_score()
        comparison = scorer.get_comparison_with_top(top_n=3)
        gaps = analyzer.analyze_content_gaps()
        opportunities = analyzer.analyze_keyword_opportunities()
        alerts = alert_system.get_alert_summary()
        
        # Top 3 acțiuni prioritare
        generator = ActionPlanGenerator(agent_id)
        plan = generator.generate_plan()
        top_actions = plan.get("quick_wins", {}).get("actions", [])[:3]
        
        return {
            "ok": True,
            "agent_id": agent_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            
            # Scor principal
            "positioning_score": {
                "score": score["score"],
                "max": 100,
                "ranking": score.get("ranking"),
                "total_competitors": score.get("total_competitors"),
                "interpretation": score.get("interpretation"),
                "breakdown": score.get("breakdown")
            },
            
            # Comparație cu top
            "vs_top_competitors": comparison,
            
            # Sumar gaps
            "gaps_summary": {
                "keyword_gaps": len(gaps.get("keyword_gaps", [])),
                "service_gaps": len(gaps.get("service_gaps", [])),
                "opportunities": len(opportunities),
                "top_keyword_gap": gaps.get("keyword_gaps", [{}])[0] if gaps.get("keyword_gaps") else None,
                "top_service_gap": gaps.get("service_gaps", [{}])[0] if gaps.get("service_gaps") else None
            },
            
            # Alerte
            "alerts": {
                "total": alerts.get("total_alerts", 0),
                "critical": alerts.get("by_severity", {}).get("critical", 0),
                "warning": alerts.get("by_severity", {}).get("warning", 0),
                "latest": alerts.get("alerts", [])[:3]
            },
            
            # Top acțiuni
            "recommended_actions": top_actions,
            
            # Quick stats
            "quick_stats": {
                "your_pages": score.get("breakdown", {}).get("content", {}).get("score", 0),
                "your_keywords": score.get("breakdown", {}).get("keywords", {}).get("score", 0),
                "your_services": score.get("breakdown", {}).get("services", {}).get("score", 0)
            }
        }
    except Exception as e:
        logger.error(f"Error getting BI dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/competitor-comparison/{competitor_domain}")
async def compare_with_competitor(agent_id: str, competitor_domain: str):
    """
    ⚔️ Tu vs Competitor - Comparație directă cu un competitor specific
    """
    try:
        master = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not master:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Găsește competitorul
        competitor = db.site_agents.find_one({
            "master_agent_id": ObjectId(agent_id),
            "domain": {"$regex": competitor_domain, "$options": "i"}
        })
        
        if not competitor:
            raise HTTPException(status_code=404, detail=f"Competitor {competitor_domain} not found")
        
        # Construiește comparația
        comparison = {
            "you": {
                "domain": master.get("domain"),
                "pages": master.get("pages_indexed", 0),
                "keywords": len(master.get("keywords", [])),
                "services": len(master.get("services", [])),
                "chunks": master.get("chunks_indexed", 0),
                "subdomains": len(master.get("subdomains", []))
            },
            "competitor": {
                "domain": competitor.get("domain"),
                "pages": competitor.get("pages_indexed", 0),
                "keywords": len(competitor.get("keywords", [])),
                "services": len(competitor.get("services", [])),
                "chunks": competitor.get("chunks_indexed", 0),
                "subdomains": len(competitor.get("subdomains", []))
            }
        }
        
        # Calculează diferențele
        differences = {}
        for metric in ["pages", "keywords", "services", "chunks", "subdomains"]:
            your_val = comparison["you"][metric]
            comp_val = comparison["competitor"][metric]
            diff = your_val - comp_val
            diff_percent = ((your_val - comp_val) / max(comp_val, 1)) * 100
            
            differences[metric] = {
                "difference": diff,
                "percent": round(diff_percent, 1),
                "winner": "you" if diff > 0 else ("competitor" if diff < 0 else "tie"),
                "label": "📈" if diff > 0 else ("📉" if diff < 0 else "➖")
            }
        
        # Keywords unice
        your_keywords = set(master.get("keywords", []))
        comp_keywords = set(competitor.get("keywords", []))
        
        return {
            "ok": True,
            "comparison": comparison,
            "differences": differences,
            "keywords_analysis": {
                "only_you_have": list(your_keywords - comp_keywords)[:10],
                "only_competitor_has": list(comp_keywords - your_keywords)[:10],
                "both_have": list(your_keywords & comp_keywords)[:10]
            },
            "verdict": {
                "wins": sum(1 for d in differences.values() if d["winner"] == "you"),
                "losses": sum(1 for d in differences.values() if d["winner"] == "competitor"),
                "ties": sum(1 for d in differences.values() if d["winner"] == "tie")
            },
            "recommendations": [
                f"Adaugă {abs(differences['pages']['difference'])} pagini pentru a egala competitorul" 
                if differences['pages']['winner'] == 'competitor' else None,
                f"Targetează {len(comp_keywords - your_keywords)} keywords noi de la competitor"
                if comp_keywords - your_keywords else None
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing with competitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 🚀 ADVANCED BUSINESS INTELLIGENCE ENDPOINTS
# Trend Tracking, Goals, Checklist, AI Content, ROI, Watchlist, Notifications
# ============================================================================

from business_intelligence_advanced import (
    TrendTracker,
    GoalTracker,
    ActionChecklist,
    AIContentGenerator,
    ROICalculator,
    CompetitorWatchlist,
    NotificationSystem
)

# ------------ TREND TRACKING ------------

@app.post("/api/agents/{agent_id}/business-intelligence/trends/snapshot")
async def record_trend_snapshot(agent_id: str):
    """📊 Salvează un snapshot al poziționării curente"""
    try:
        tracker = TrendTracker(agent_id)
        snapshot = tracker.record_snapshot()
        return {"ok": True, "snapshot": snapshot}
    except Exception as e:
        logger.error(f"Error recording snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/trends/history")
async def get_trend_history(agent_id: str, days: int = Query(30)):
    """📈 Returnează istoricul trendurilor"""
    try:
        tracker = TrendTracker(agent_id)
        history = tracker.get_history(days)
        return {"ok": True, "history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Error getting trend history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/trends/analysis")
async def get_trend_analysis(agent_id: str):
    """📊 Analiză completă a trendurilor"""
    try:
        tracker = TrendTracker(agent_id)
        analysis = tracker.get_trend_analysis()
        return {"ok": True, **analysis}
    except Exception as e:
        logger.error(f"Error analyzing trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------ GOAL TRACKING ------------

class GoalCreate(BaseModel):
    goal_type: str
    target_value: int
    deadline_days: int
    notes: Optional[str] = ""


@app.post("/api/agents/{agent_id}/business-intelligence/goals")
async def create_goal(agent_id: str, data: GoalCreate):
    """🎯 Setează un obiectiv nou"""
    try:
        tracker = GoalTracker(agent_id)
        goal = tracker.set_goal(
            data.goal_type,
            data.target_value,
            data.deadline_days,
            data.notes
        )
        return {"ok": True, "goal": goal}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/goals")
async def get_goals(agent_id: str, status: str = Query(None)):
    """📋 Returnează toate obiectivele"""
    try:
        tracker = GoalTracker(agent_id)
        goals = tracker.get_goals(status)
        return {
            "ok": True,
            "goals": goals,
            "goal_types": GoalTracker.GOAL_TYPES
        }
    except Exception as e:
        logger.error(f"Error getting goals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/agents/{agent_id}/business-intelligence/goals/{goal_id}/complete")
async def complete_goal(agent_id: str, goal_id: str):
    """✅ Marchează un obiectiv ca completat"""
    try:
        tracker = GoalTracker(agent_id)
        result = tracker.complete_goal(goal_id)
        return {"ok": True, **result}
    except Exception as e:
        logger.error(f"Error completing goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------ CHECKLIST ------------

@app.post("/api/agents/{agent_id}/business-intelligence/checklist/generate")
async def generate_checklist(agent_id: str):
    """📝 Generează checklist din planul de acțiune"""
    try:
        from business_intelligence import ActionPlanGenerator
        
        generator = ActionPlanGenerator(agent_id)
        plan = generator.generate_plan()
        
        checklist_manager = ActionChecklist(agent_id)
        checklist = checklist_manager.create_checklist_from_plan(plan)
        
        return {"ok": True, "checklist": checklist}
    except Exception as e:
        logger.error(f"Error generating checklist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/checklist")
async def get_checklist(agent_id: str):
    """📋 Returnează checklist-ul curent"""
    try:
        checklist_manager = ActionChecklist(agent_id)
        checklist = checklist_manager.get_checklist()
        return {"ok": True, **checklist}
    except Exception as e:
        logger.error(f"Error getting checklist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/agents/{agent_id}/business-intelligence/checklist/{item_id}/toggle")
async def toggle_checklist_item(agent_id: str, item_id: str):
    """✅ Toggle completare item din checklist"""
    try:
        checklist_manager = ActionChecklist(agent_id)
        result = checklist_manager.toggle_item(item_id)
        return {"ok": True, **result}
    except Exception as e:
        logger.error(f"Error toggling checklist item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ChecklistItemCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    priority: Optional[str] = "medium"


@app.post("/api/agents/{agent_id}/business-intelligence/checklist/item")
async def add_checklist_item(agent_id: str, data: ChecklistItemCreate):
    """➕ Adaugă item custom în checklist"""
    try:
        checklist_manager = ActionChecklist(agent_id)
        item = checklist_manager.add_custom_item(data.title, data.description, data.priority)
        return {"ok": True, "item": item}
    except Exception as e:
        logger.error(f"Error adding checklist item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------ AI CONTENT GENERATOR ------------

class ContentGenerateRequest(BaseModel):
    keyword: str
    count: Optional[int] = 5


@app.post("/api/agents/{agent_id}/business-intelligence/content/titles")
async def generate_titles(agent_id: str, data: ContentGenerateRequest):
    """📝 Generează titluri SEO pentru un keyword"""
    try:
        generator = AIContentGenerator(agent_id)
        titles = generator.generate_page_titles(data.keyword, data.count)
        return {"ok": True, "keyword": data.keyword, "titles": titles}
    except Exception as e:
        logger.error(f"Error generating titles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class MetaDescriptionRequest(BaseModel):
    title: str
    keyword: str


@app.post("/api/agents/{agent_id}/business-intelligence/content/meta-description")
async def generate_meta_description(agent_id: str, data: MetaDescriptionRequest):
    """📄 Generează meta description optimizată"""
    try:
        generator = AIContentGenerator(agent_id)
        description = generator.generate_meta_description(data.title, data.keyword)
        return {"ok": True, "meta_description": description}
    except Exception as e:
        logger.error(f"Error generating meta description: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class OutlineRequest(BaseModel):
    topic: str
    target_words: Optional[int] = 1500


@app.post("/api/agents/{agent_id}/business-intelligence/content/outline")
async def generate_article_outline(agent_id: str, data: OutlineRequest):
    """📑 Generează outline pentru articol"""
    try:
        generator = AIContentGenerator(agent_id)
        outline = generator.generate_article_outline(data.topic, data.target_words)
        return {"ok": True, "topic": data.topic, "outline": outline}
    except Exception as e:
        logger.error(f"Error generating outline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/{agent_id}/business-intelligence/content/ideas")
async def generate_content_ideas(agent_id: str, count: int = Query(10)):
    """💡 Generează idei de conținut bazate pe gaps"""
    try:
        from business_intelligence import GapAnalyzer
        
        analyzer = GapAnalyzer(agent_id)
        gaps = analyzer.analyze_content_gaps()
        
        # Extrage keywords din gaps
        gap_keywords = [g["keyword"] for g in gaps.get("keyword_gaps", [])]
        gap_keywords += [g["service"] for g in gaps.get("service_gaps", [])]
        gap_keywords += [g["topic"] for g in gaps.get("topic_gaps", [])]
        
        generator = AIContentGenerator(agent_id)
        ideas = generator.generate_content_ideas(gap_keywords[:15], count)
        
        return {"ok": True, "ideas": ideas, "based_on_gaps": len(gap_keywords)}
    except Exception as e:
        logger.error(f"Error generating content ideas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------ ROI CALCULATOR ------------

@app.get("/api/agents/{agent_id}/business-intelligence/roi/keyword/{keyword}")
async def calculate_keyword_roi(agent_id: str, keyword: str, position: int = Query(5)):
    """💰 Calculează ROI pentru un keyword"""
    try:
        calculator = ROICalculator(agent_id)
        roi = calculator.calculate_keyword_roi(keyword, position)
        return {"ok": True, **roi}
    except Exception as e:
        logger.error(f"Error calculating keyword ROI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/roi/plan")
async def calculate_plan_roi(agent_id: str):
    """💰 Calculează ROI total pentru planul de acțiune"""
    try:
        from business_intelligence import ActionPlanGenerator
        
        generator = ActionPlanGenerator(agent_id)
        plan = generator.generate_plan()
        
        calculator = ROICalculator(agent_id)
        roi = calculator.calculate_total_plan_roi(plan)
        
        return {"ok": True, **roi}
    except Exception as e:
        logger.error(f"Error calculating plan ROI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------ COMPETITOR WATCHLIST ------------

class WatchlistAdd(BaseModel):
    competitor_domain: str
    notes: Optional[str] = ""


@app.post("/api/agents/{agent_id}/business-intelligence/watchlist")
async def add_to_watchlist(agent_id: str, data: WatchlistAdd):
    """👁️ Adaugă competitor în watchlist"""
    try:
        watchlist = CompetitorWatchlist(agent_id)
        entry = watchlist.add_to_watchlist(data.competitor_domain, data.notes)
        return {"ok": True, "entry": entry}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/watchlist")
async def get_watchlist(agent_id: str):
    """📋 Returnează watchlist-ul"""
    try:
        watchlist = CompetitorWatchlist(agent_id)
        items = watchlist.get_watchlist()
        return {"ok": True, "watchlist": items, "count": len(items)}
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/agents/{agent_id}/business-intelligence/watchlist/{competitor_domain}")
async def remove_from_watchlist(agent_id: str, competitor_domain: str):
    """🗑️ Elimină competitor din watchlist"""
    try:
        watchlist = CompetitorWatchlist(agent_id)
        result = watchlist.remove_from_watchlist(competitor_domain)
        return {"ok": True, **result}
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/leaderboard")
async def get_leaderboard(agent_id: str):
    """🏆 Returnează leaderboard-ul competitorilor"""
    try:
        watchlist = CompetitorWatchlist(agent_id)
        leaderboard = watchlist.get_leaderboard()
        
        # Găsește poziția ta
        your_position = next((e["position"] for e in leaderboard if e.get("is_you")), None)
        
        return {
            "ok": True,
            "leaderboard": leaderboard,
            "total_competitors": len(leaderboard),
            "your_position": your_position
        }
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------ NOTIFICATIONS ------------

@app.get("/api/agents/{agent_id}/business-intelligence/notifications")
async def get_notifications(agent_id: str, unread_only: bool = Query(False), limit: int = Query(50)):
    """🔔 Returnează notificările"""
    try:
        notif_system = NotificationSystem(agent_id)
        notifications = notif_system.get_notifications(unread_only, limit)
        unread_count = notif_system.get_unread_count()
        
        return {
            "ok": True,
            "notifications": notifications,
            "unread_count": unread_count
        }
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/agents/{agent_id}/business-intelligence/notifications/read")
async def mark_notifications_read(agent_id: str, notification_id: str = Query(None)):
    """✅ Marchează notificările ca citite"""
    try:
        notif_system = NotificationSystem(agent_id)
        result = notif_system.mark_as_read(notification_id)
        return {"ok": True, **result}
    except Exception as e:
        logger.error(f"Error marking notifications read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/{agent_id}/business-intelligence/notifications/check")
async def check_and_create_alerts(agent_id: str):
    """🔍 Verifică și creează alerte automate"""
    try:
        notif_system = NotificationSystem(agent_id)
        alerts = notif_system.check_and_create_alerts()
        return {"ok": True, "alerts_created": len(alerts), "alerts": alerts}
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class NotificationSettings(BaseModel):
    email: Optional[str] = ""
    webhook_url: Optional[str] = ""
    email_enabled: Optional[bool] = False
    webhook_enabled: Optional[bool] = False
    alert_types: Optional[List[str]] = ["critical", "warning"]


@app.put("/api/agents/{agent_id}/business-intelligence/notifications/settings")
async def save_notification_settings(agent_id: str, data: NotificationSettings):
    """⚙️ Salvează setările de notificări"""
    try:
        notif_system = NotificationSystem(agent_id)
        result = notif_system.save_settings(data.dict())
        return {"ok": True, **result}
    except Exception as e:
        logger.error(f"Error saving notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/business-intelligence/notifications/settings")
async def get_notification_settings(agent_id: str):
    """⚙️ Returnează setările de notificări"""
    try:
        notif_system = NotificationSystem(agent_id)
        settings = notif_system.get_settings()
        return {"ok": True, "settings": settings}
    except Exception as e:
        logger.error(f"Error getting notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------ PDF REPORTS ------------

from fastapi.responses import StreamingResponse
import io

class ManualCompetitor(BaseModel):
    url: str
    master_agent_id: str

@app.post("/api/competitors/add")
async def add_manual_competitor(data: ManualCompetitor):
    """Adaugă manual un competitor în sistem"""
    try:
        from tools.construction_agent_creator import ConstructionAgentCreator
        creator = ConstructionAgentCreator()
        
        # Folosește funcția async corectă
        result = await creator.create_agent_from_url(
            site_url=data.url,
            master_agent_id=data.master_agent_id,
            gpu_id=0 # Folosește GPU 0 pentru procesare rapidă
        )
        
        return result
    except Exception as e:
        logger.error(f"Error adding manual competitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/competitors/map-data")
async def get_map_data(master_agent_id: str):
    """Returnează datele pentru Harta Interactivă (War Map)"""
    try:
        master_oid = ObjectId(master_agent_id)
        
        # Ia toți competitorii (sclavi)
        slaves = list(db.site_agents.find(
            {"master_agent_id": master_oid, "agent_type": "slave"},
            {"domain": 1, "site_url": 1, "agent_config": 1, "pages_indexed": 1, "chunks_indexed": 1}
        ))
        
        # Ia master-ul
        master = db.site_agents.find_one({"_id": master_oid})
        
        points = []
        
        # Adaugă Master (punct central)
        if master:
            points.append({
                "name": master.get("domain"),
                "url": master.get("site_url"),
                "type": "master",
                "x": master.get("pages_indexed", 0), # Volum conținut
                "y": master.get("chunks_indexed", 0), # Profunzime
                "score": 100,
                "color": "#3b82f6" # Blue
            })
            
        # Adaugă Sclavi
        for slave in slaves:
            # Calculăm scor simplu bazat pe conținut
            pages = slave.get("pages_indexed", 0)
            chunks = slave.get("chunks_indexed", 0)
            
            points.append({
                "name": slave.get("domain"),
                "url": slave.get("site_url"),
                "type": "competitor",
                "x": pages,
                "y": chunks,
                "score": (pages * 10 + chunks) / 100, # Scor estimativ
                "color": "#ef4444" # Red
            })
            
        return {"ok": True, "points": points}
        
    except Exception as e:
        logger.error(f"Error getting map data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/business-intelligence/report/generate")
async def generate_bi_report(agent_id: str, format: str = Query("json")):
    """📄 Generează raport Business Intelligence complet"""
    try:
        from business_intelligence import (
            GapAnalyzer, PositioningScorer, ActionPlanGenerator
        )
        
        # Colectează toate datele
        scorer = PositioningScorer(agent_id)
        analyzer = GapAnalyzer(agent_id)
        plan_generator = ActionPlanGenerator(agent_id)
        watchlist = CompetitorWatchlist(agent_id)
        
        score = scorer.calculate_score()
        comparison = scorer.get_comparison_with_top(3)
        gaps = analyzer.analyze_content_gaps()
        opportunities = analyzer.analyze_keyword_opportunities()
        plan = plan_generator.generate_plan()
        leaderboard = watchlist.get_leaderboard()
        
        # Obține date agent
        master = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "agent": {
                "domain": master.get("domain") if master else "N/A",
                "industry": master.get("industry") if master else "N/A",
                "pages_indexed": master.get("pages_indexed", 0) if master else 0,
                "keywords_count": len(master.get("keywords", [])) if master else 0
            },
            "positioning": {
                "score": score.get("score", 0),
                "ranking": score.get("ranking"),
                "total_competitors": score.get("total_competitors"),
                "interpretation": score.get("interpretation"),
                "breakdown": score.get("breakdown")
            },
            "gaps_analysis": {
                "keyword_gaps": gaps.get("keyword_gaps", [])[:10],
                "service_gaps": gaps.get("service_gaps", [])[:10],
                "topic_gaps": gaps.get("topic_gaps", [])[:10],
                "opportunities": opportunities[:10]
            },
            "action_plan": {
                "quick_wins": plan.get("quick_wins", {}).get("actions", []),
                "medium_term": plan.get("medium_term", {}).get("actions", []),
                "long_term": plan.get("long_term", {}).get("actions", [])
            },
            "competition": {
                "top_competitors": comparison.get("top_competitors", [])[:5],
                "leaderboard_position": next(
                    (e["position"] for e in leaderboard if e.get("is_you")), None
                )
            },
            "recommendations": [
                "Concentrează-te pe Quick Wins pentru rezultate rapide",
                f"Ai {len(gaps.get('keyword_gaps', []))} keywords de adăugat",
                f"Poziția ta în leaderboard: #{next((e['position'] for e in leaderboard if e.get('is_you')), 'N/A')}"
            ]
        }
        
        if format == "html":
            # Generează HTML report
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Business Intelligence Report - {report['agent']['domain']}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; max-width: 900px; margin: 0 auto; padding: 40px; background: #1a1a2e; color: #eee; }}
        h1 {{ color: #8b5cf6; border-bottom: 2px solid #8b5cf6; padding-bottom: 10px; }}
        h2 {{ color: #60a5fa; margin-top: 30px; }}
        .score-card {{ background: linear-gradient(135deg, #8b5cf620, #3b82f620); padding: 30px; border-radius: 15px; text-align: center; margin: 20px 0; }}
        .score {{ font-size: 72px; font-weight: bold; color: #8b5cf6; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .card {{ background: #2d2d44; padding: 20px; border-radius: 10px; }}
        .card h3 {{ margin-top: 0; color: #8b5cf6; }}
        .tag {{ display: inline-block; background: #8b5cf620; color: #8b5cf6; padding: 4px 12px; border-radius: 20px; margin: 4px; font-size: 12px; }}
        .action {{ background: #2d2d44; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #8b5cf6; }}
        .high {{ border-left-color: #22c55e; }}
        .medium {{ border-left-color: #eab308; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #3d3d5c; }}
        th {{ background: #2d2d44; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #3d3d5c; text-align: center; color: #666; }}
    </style>
</head>
<body>
    <h1>📊 Business Intelligence Report</h1>
    <p><strong>Domeniu:</strong> {report['agent']['domain']}</p>
    <p><strong>Generat:</strong> {report['generated_at'][:10]}</p>
    
    <div class="score-card">
        <div class="score">{report['positioning']['score']}</div>
        <div>Scor Poziționare din 100</div>
        <div style="margin-top:10px;">Poziția #{report['positioning']['ranking']} din {report['positioning']['total_competitors']} competitori</div>
    </div>
    
    <h2>📈 Breakdown Scor</h2>
    <div class="grid">
        {''.join(f'<div class="card"><h3>{v.get("label", k)}</h3><div style="font-size:24px;font-weight:bold;">{v.get("score", 0)}/{v.get("max", 25)}</div></div>' for k, v in report['positioning'].get('breakdown', {}).items())}
    </div>
    
    <h2>🔍 Gap Analysis</h2>
    <h3>Keywords Lipsă ({len(report['gaps_analysis']['keyword_gaps'])})</h3>
    <div>{''.join(f'<span class="tag">{g.get("keyword", "")}</span>' for g in report['gaps_analysis']['keyword_gaps'][:10])}</div>
    
    <h3>Servicii Lipsă ({len(report['gaps_analysis']['service_gaps'])})</h3>
    <div>{''.join(f'<span class="tag">{g.get("service", "")}</span>' for g in report['gaps_analysis']['service_gaps'][:10])}</div>
    
    <h2>🚀 Plan de Acțiune</h2>
    <h3>Quick Wins</h3>
    {''.join(f'<div class="action high"><strong>{a.get("title", "")}</strong><br><small>{a.get("description", "")}</small></div>' for a in report['action_plan']['quick_wins'][:5])}
    
    <h3>Termen Mediu</h3>
    {''.join(f'<div class="action medium"><strong>{a.get("title", "")}</strong><br><small>{a.get("description", "")}</small></div>' for a in report['action_plan']['medium_term'][:5])}
    
    <h2>🏆 Top Competitori</h2>
    <table>
        <tr><th>Domeniu</th><th>Scor</th><th>Pagini</th><th>Keywords</th></tr>
        {''.join(f'<tr><td>{c.get("domain", "")}</td><td>{c.get("score", 0)}</td><td>{c.get("pages", 0)}</td><td>{c.get("keywords", 0)}</td></tr>' for c in report['competition']['top_competitors'][:5])}
    </table>
    
    <h2>💡 Recomandări</h2>
    <ul>
        {''.join(f'<li>{r}</li>' for r in report['recommendations'])}
    </ul>
    
    <div class="footer">
        <p>Generat de AI Business Intelligence System</p>
        <p>{report['generated_at']}</p>
    </div>
</body>
</html>
"""
            return StreamingResponse(
                io.BytesIO(html_content.encode()),
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename=bi_report_{report['agent']['domain']}.html"}
            )
        
        return {"ok": True, "report": report}
        
    except Exception as e:
        logger.error(f"Error generating BI report: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 🔌 INTEGRATIONS API
# ==========================================

class IntegrationRequest(BaseModel):
    service: str

@app.get("/api/integrations/status")
async def get_integrations_status():
    """Returnează starea conexiunilor externe"""
    try:
        # TODO: Extrage din DB pentru utilizatorul curent (hardcoded for now for single-tenant)
        profile = db.client_profiles.find_one({}, sort=[("created_at", -1)])
        integrations = profile.get("integrations", {}) if profile else {}
        
        # Default structure
        status = {
            "google_ads": integrations.get("google_ads", {}).get("connected", False),
            "facebook": integrations.get("facebook", {}).get("connected", False),
            "tiktok": integrations.get("tiktok", {}).get("connected", False),
            "analytics": integrations.get("analytics", {}).get("connected", False),
            "email": integrations.get("email", {}).get("connected", False)
        }
        return {"ok": True, "status": status}
    except Exception as e:
        logger.error(f"Integrations status error: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/integrations/connect")
async def connect_integration(data: IntegrationRequest):
    """Conectează un serviciu extern (Simulare OAuth)"""
    try:
        service = data.service
        
        # Actualizează în DB
        db.client_profiles.update_one(
            {}, # Update last profile
            {"$set": {
                f"integrations.{service}": {
                    "connected": True,
                    "connected_at": datetime.now(timezone.utc),
                    "status": "active"
                }
            }},
            upsert=True
        )
        
        return {"ok": True, "message": f"{service} connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/integrations/disconnect")
async def disconnect_integration(data: IntegrationRequest):
    """Deconectează un serviciu extern"""
    try:
        service = data.service
        
        db.client_profiles.update_one(
            {}, 
            {"$set": {f"integrations.{service}.connected": False}}
        )
        
        return {"ok": True, "message": f"{service} disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== PRICING OFFERS SYSTEM ====================
# Sistem de Management Oferte de Preț

from pricing_offers_system import PricingOffersSystem, OfferPDFGenerator

# Pydantic models pentru oferte
class OfferItem(BaseModel):
    name: str
    description: Optional[str] = ""
    quantity: float = 1
    unit: str = "buc"
    unit_price: float = 0
    discount: float = 0
    vat_rate: float = 19

class CreateOfferRequest(BaseModel):
    title: str = "Ofertă de preț"
    description: Optional[str] = ""
    recipient_name: Optional[str] = ""
    recipient_company: Optional[str] = ""
    recipient_email: Optional[str] = ""
    recipient_phone: Optional[str] = ""
    recipient_address: Optional[str] = ""
    items: List[OfferItem] = []
    currency: str = "RON"
    payment_terms: Optional[str] = ""
    delivery_terms: Optional[str] = ""
    warranty_terms: Optional[str] = ""
    notes: Optional[str] = ""
    tags: List[str] = []
    category: str = "general"
    valid_until: Optional[str] = None
    template_id: Optional[str] = None

class GenerateOfferRequest(BaseModel):
    description: str
    context: Optional[Dict] = None

class ImportOfferRequest(BaseModel):
    text: str

class CreateTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    category: str = "general"
    items: List[OfferItem] = []
    payment_terms: Optional[str] = ""
    delivery_terms: Optional[str] = ""
    warranty_terms: Optional[str] = ""
    notes: Optional[str] = ""

class CatalogItemRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    category: str = "general"
    unit: str = "buc"
    unit_price: float = 0
    vat_rate: float = 19

class ClientSettingsRequest(BaseModel):
    company_name: Optional[str] = ""
    company_address: Optional[str] = ""
    company_phone: Optional[str] = ""
    company_email: Optional[str] = ""
    company_logo: Optional[str] = ""
    default_currency: str = "RON"
    default_vat_rate: float = 19
    payment_terms: Optional[str] = ""
    bank_details: Optional[str] = ""


# ===== CLIENT SPACE =====

@app.get("/api/offers/space/{client_id}")
async def get_client_space(client_id: str):
    """Obține spațiul dedicat al clientului"""
    try:
        system = PricingOffersSystem(client_id)
        space = system.get_client_space()
        return {"ok": True, "space": space}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/offers/space/{client_id}/settings")
async def update_client_settings(client_id: str, settings: ClientSettingsRequest):
    """Actualizează setările clientului"""
    try:
        system = PricingOffersSystem(client_id)
        success = system.update_client_settings(settings.dict())
        return {"ok": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== CRUD OFERTE =====

@app.post("/api/offers/{client_id}")
async def create_offer(client_id: str, offer: CreateOfferRequest):
    """Creează o ofertă nouă"""
    try:
        system = PricingOffersSystem(client_id)
        offer_data = offer.dict()
        offer_data["items"] = [item.dict() if hasattr(item, 'dict') else item for item in offer_data.get("items", [])]
        offer_id = system.create_offer(offer_data)
        return {"ok": True, "offer_id": offer_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/offers/{client_id}")
async def list_offers(
    client_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None
):
    """Listează ofertele clientului"""
    try:
        system = PricingOffersSystem(client_id)
        filters = {}
        if status:
            filters["status"] = status
        if category:
            filters["category"] = category
        if search:
            filters["search"] = search
        
        result = system.list_offers(filters=filters, page=page, limit=limit)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/offers/{client_id}/{offer_id}")
async def get_offer(client_id: str, offer_id: str):
    """Obține o ofertă specifică"""
    try:
        system = PricingOffersSystem(client_id)
        offer = system.get_offer(offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Oferta nu există")
        return {"ok": True, "offer": offer}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/offers/{client_id}/{offer_id}")
async def update_offer(client_id: str, offer_id: str, updates: Dict = Body(...)):
    """Actualizează o ofertă"""
    try:
        system = PricingOffersSystem(client_id)
        success = system.update_offer(offer_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="Oferta nu există sau nu a fost modificată")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/offers/{client_id}/{offer_id}")
async def delete_offer(client_id: str, offer_id: str):
    """Șterge o ofertă"""
    try:
        system = PricingOffersSystem(client_id)
        success = system.delete_offer(offer_id)
        if not success:
            raise HTTPException(status_code=404, detail="Oferta nu există")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/offers/{client_id}/{offer_id}/duplicate")
async def duplicate_offer(client_id: str, offer_id: str, modifications: Dict = Body(default={})):
    """Duplică o ofertă existentă"""
    try:
        system = PricingOffersSystem(client_id)
        new_offer_id = system.duplicate_offer(offer_id, modifications)
        return {"ok": True, "offer_id": new_offer_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/offers/{client_id}/{offer_id}/status")
async def update_offer_status(client_id: str, offer_id: str, status: str = Body(..., embed=True)):
    """Actualizează statusul ofertei"""
    try:
        valid_statuses = ["draft", "sent", "accepted", "rejected", "expired"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Status invalid. Valori acceptate: {valid_statuses}")
        
        system = PricingOffersSystem(client_id)
        success = system.update_offer(offer_id, {"status": status})
        return {"ok": success}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== GENERARE AI =====

@app.post("/api/offers/{client_id}/generate")
async def generate_offer_ai(client_id: str, request: GenerateOfferRequest):
    """Generează o ofertă cu AI din descriere text"""
    try:
        system = PricingOffersSystem(client_id)
        offer_data = system.generate_offer_from_description(request.description, request.context)
        return {"ok": True, "offer_data": offer_data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/offers/{client_id}/generate-and-save")
async def generate_and_save_offer(client_id: str, request: GenerateOfferRequest):
    """Generează și salvează o ofertă cu AI"""
    try:
        system = PricingOffersSystem(client_id)
        offer_data = system.generate_offer_from_description(request.description, request.context)
        offer_id = system.create_offer(offer_data)
        return {"ok": True, "offer_id": offer_id, "offer_data": offer_data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/offers/{client_id}/{offer_id}/improve")
async def improve_offer_ai(client_id: str, offer_id: str, instructions: str = Body(default=None, embed=True)):
    """Îmbunătățește o ofertă cu AI"""
    try:
        system = PricingOffersSystem(client_id)
        suggestions = system.improve_offer_with_ai(offer_id, instructions)
        return {"ok": True, "suggestions": suggestions}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/offers/{client_id}/{offer_id}/generate-similar")
async def generate_similar_offer(client_id: str, offer_id: str, adjustments: Dict = Body(default={})):
    """Generează o ofertă similară bazată pe una existentă"""
    try:
        system = PricingOffersSystem(client_id)
        new_offer_id = system.generate_similar_offer(offer_id, adjustments)
        return {"ok": True, "offer_id": new_offer_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== IMPORT =====

@app.post("/api/offers/{client_id}/import")
async def import_offer(client_id: str, request: ImportOfferRequest):
    """Importă o ofertă din text"""
    try:
        system = PricingOffersSystem(client_id)
        offer_id = system.import_from_text(request.text)
        return {"ok": True, "offer_id": offer_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== TEMPLATES =====

@app.post("/api/offers/{client_id}/templates")
async def create_template(client_id: str, template: CreateTemplateRequest):
    """Creează un template de ofertă"""
    try:
        system = PricingOffersSystem(client_id)
        template_data = template.dict()
        template_data["items"] = [item.dict() if hasattr(item, 'dict') else item for item in template_data.get("items", [])]
        template_id = system.create_template(template_data)
        return {"ok": True, "template_id": template_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/offers/{client_id}/templates")
async def list_templates(client_id: str):
    """Listează template-urile disponibile"""
    try:
        system = PricingOffersSystem(client_id)
        templates = system.list_templates()
        return {"ok": True, "templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/offers/{client_id}/templates/{template_id}/create-offer")
async def create_offer_from_template(client_id: str, template_id: str, customizations: Dict = Body(default={})):
    """Creează o ofertă din template"""
    try:
        system = PricingOffersSystem(client_id)
        offer_id = system.create_offer_from_template(template_id, customizations)
        return {"ok": True, "offer_id": offer_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== CATALOG ARTICOLE =====

@app.post("/api/offers/{client_id}/catalog")
async def add_catalog_item(client_id: str, item: CatalogItemRequest):
    """Adaugă un articol în catalog"""
    try:
        system = PricingOffersSystem(client_id)
        item_id = system.add_catalog_item(item.dict())
        return {"ok": True, "item_id": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/offers/{client_id}/catalog")
async def list_catalog_items(client_id: str, category: Optional[str] = None):
    """Listează articolele din catalog"""
    try:
        system = PricingOffersSystem(client_id)
        items = system.list_catalog_items(category)
        return {"ok": True, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== EXPORT PDF =====

@app.get("/api/offers/{client_id}/{offer_id}/export")
async def export_offer_pdf(client_id: str, offer_id: str, format: str = Query("html", regex="^(html|pdf)$")):
    """Exportă oferta în format HTML/PDF"""
    from fastapi.responses import StreamingResponse
    import io
    
    try:
        system = PricingOffersSystem(client_id)
        offer = system.get_offer(offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Oferta nu există")
        
        space = system.get_client_space()
        client_settings = space.get("settings", {}) if space else {}
        
        html_content = OfferPDFGenerator.generate_html(offer, client_settings)
        
        if format == "html":
            return StreamingResponse(
                io.BytesIO(html_content.encode()),
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename=oferta_{offer.get('reference_number', offer_id)}.html"}
            )
        
        # Pentru PDF, returnăm HTML (clientul poate folosi un serviciu de conversie)
        return StreamingResponse(
            io.BytesIO(html_content.encode()),
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=oferta_{offer.get('reference_number', offer_id)}.html"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== STATISTICI =====

@app.get("/api/offers/{client_id}/statistics")
async def get_offer_statistics(client_id: str):
    """Obține statisticile ofertelor"""
    try:
        system = PricingOffersSystem(client_id)
        space = system.get_client_space()
        
        # Statistici detaliate
        pipeline = [
            {"$match": {"client_id": client_id}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total_value": {"$sum": "$total"}
            }}
        ]
        
        from pricing_offers_system import offers_collection
        status_stats = list(offers_collection.aggregate(pipeline))
        
        # Statistici pe categorii
        category_pipeline = [
            {"$match": {"client_id": client_id}},
            {"$group": {
                "_id": "$category",
                "count": {"$sum": 1},
                "total_value": {"$sum": "$total"}
            }}
        ]
        category_stats = list(offers_collection.aggregate(category_pipeline))
        
        # Statistici pe lună
        monthly_pipeline = [
            {"$match": {"client_id": client_id}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"}
                },
                "count": {"$sum": 1},
                "total_value": {"$sum": "$total"}
            }},
            {"$sort": {"_id.year": -1, "_id.month": -1}},
            {"$limit": 12}
        ]
        monthly_stats = list(offers_collection.aggregate(monthly_pipeline))
        
        return {
            "ok": True,
            "statistics": space.get("statistics", {}) if space else {},
            "by_status": {s["_id"]: {"count": s["count"], "value": s["total_value"]} for s in status_stats},
            "by_category": {s["_id"]: {"count": s["count"], "value": s["total_value"]} for s in category_stats},
            "monthly": [{"year": s["_id"]["year"], "month": s["_id"]["month"], "count": s["count"], "value": s["total_value"]} for s in monthly_stats]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 🔔 NOTIFICATIONS / INSIGHTS API
# ==========================================

class NotificationUpdate(BaseModel):
    is_read: bool

@app.get("/api/notifications")
async def get_notifications(
    domain: Optional[str] = None, 
    limit: int = 20, 
    unread_only: bool = False
):
    """Returnează notificările/hints pentru un domeniu"""
    try:
        query = {}
        if domain:
            query["domain"] = domain
        if unread_only:
            query["is_read"] = False
            
        # Conectare la colecția client_notifications
        mongo = MongoClient(MONGODB_URI)
        notifications_coll = mongo[MONGODB_DATABASE]["client_notifications"]
        
        cursor = notifications_coll.find(query).sort("created_at", -1).limit(limit)
        notifications = []
        
        for notif in cursor:
            notifications.append({
                "id": str(notif["_id"]),
                "domain": notif.get("domain"),
                "type": notif.get("type"),
                "message": notif.get("message"),
                "action_item": notif.get("action_item"),
                "priority": notif.get("priority", "medium"),
                "is_read": notif.get("is_read", False),
                "created_at": notif.get("created_at").isoformat() if notif.get("created_at") else None
            })
            
        return {
            "ok": True,
            "count": len(notifications),
            "notifications": notifications
        }
    except Exception as e:
        print(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, update: NotificationUpdate):
    """Marchează o notificare ca citită"""
    try:
        mongo = MongoClient(MONGODB_URI)
        notifications_coll = mongo[MONGODB_DATABASE]["client_notifications"]
        
        result = notifications_coll.update_one(
            {"_id": ObjectId(notification_id)},
            {"": {"is_read": update.is_read}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
            
        return {"ok": True, "message": "Updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 💼 CLIENT PROFILE & OFFERS API
# ==========================================

class ClientProfile(BaseModel):
    employees: int
    materials: List[str]
    suppliers: List[str]
    margin: float = 0.20

class OfferRequest(BaseModel):
    offer_text: str

@app.post("/api/client/profile")
async def update_profile(domain: str, profile: ClientProfile):
    """Actualizează profilul operațional al clientului"""
    try:
        from pricing_offers_system import PricingOffersSystem
        system = PricingOffersSystem()
        system.update_client_profile(domain, profile.dict())
        return {"ok": True, "message": "Profile updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/client/suppliers")
async def get_suppliers(material: str):
    """Caută furnizori alternativi în baza de date"""
    try:
        from pricing_offers_system import PricingOffersSystem
        system = PricingOffersSystem()
        suppliers = system.find_better_suppliers(material)
        return {"ok": True, "count": len(suppliers), "suppliers": suppliers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/client/analyze-offer")
async def analyze_offer(domain: str, request: OfferRequest):
    """Analizează și optimizează o ofertă text"""
    try:
        from pricing_offers_system import PricingOffersSystem
        system = PricingOffersSystem()
        result = system.analyze_and_optimize_offer(domain, request.offer_text)
        return {"ok": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 🧠 DEEP BUSINESS INTELLIGENCE API
# ==========================================

class ProjectData(BaseModel):
    project_name: str
    offer_value: float
    collected_value: float
    costs: float
    category: str
    date: Optional[str] = None

class ActionRequest(BaseModel):
    action_type: str
    details: Dict[str, Any]

@app.post("/api/business/project")
async def add_project(domain: str, project: ProjectData):
    """Adaugă un proiect în istoricul financiar"""
    try:
        from business_intelligence_advanced import BusinessIntelligenceAdvanced
        bi = BusinessIntelligenceAdvanced()
        bi.add_project_history(domain, project.dict())
        return {"ok": True, "message": "Project saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/business/analysis")
async def get_analysis(domain: str):
    """Obține analiza financiară și planul de dezvoltare"""
    try:
        from business_intelligence_advanced import BusinessIntelligenceAdvanced
        bi = BusinessIntelligenceAdvanced()
        analysis = bi.analyze_financial_health(domain)
        
        # Încercăm să generăm planul doar dacă avem analiză validă
        plan = "Planul se generează..."
        if isinstance(analysis, dict):
            plan = bi.generate_growth_plan(domain, analysis)
            
        return {"ok": True, "analysis": analysis, "growth_plan": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/business/execute")
async def execute_action(domain: str, request: ActionRequest):
    """Generează asset-uri de implementare (emailuri, documente)"""
    try:
        from business_intelligence_advanced import BusinessIntelligenceAdvanced
        bi = BusinessIntelligenceAdvanced()
        result = bi.generate_action_assets(domain, request.action_type, request.details)
        return {"ok": True, "generated_content": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
