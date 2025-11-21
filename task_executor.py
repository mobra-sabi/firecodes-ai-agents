import os
import json
import asyncio
import logging
import requests
from typing import List

from starlette.websockets import WebSocketDisconnect
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
# from langchain.agents.factory import create_agent  # Deprecated in langchain 1.0+
from langchain_core.tools import StructuredTool

from agent_tools import get_tools_for_agent
from pymongo import MongoClient
from llm_orchestrator import get_orchestrator

# Compat pentru excepția de parsing (diferențe între versiuni LangChain)
try:
    from langchain_core.exceptions import OutputParserException
except Exception:
    try:
        from langchain.schema.output_parser import OutputParserException  # older
    except Exception:
        class OutputParserException(Exception):
            pass

# Mesaje pentru fallback direct pe LLM
try:
    from langchain_core.messages import SystemMessage, HumanMessage
except Exception:
    SystemMessage = None
    HumanMessage = None

logger = logging.getLogger("task_executor")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:9308/")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.ai_agents_db


async def send_ws_message(websocket, type_, data):
    await websocket.send_json({"type": type_, "data": data})


async def send_status(ws, text: str):
    try:
        await ws.send_json({"type": "status", "data": text})
    except Exception:
        # dacă socketul e închis, ignorăm
        pass


class DiscoverInput(BaseModel):
    limit: int = Field(10, ge=1, le=50, description="Câte rezultate să încerce să găsească")


class IngestInput(BaseModel):
    urls: List[str] = Field(..., description="Lista de URL-uri de ingerat ca agenți")
    max_pages: int = Field(3, ge=1, le=50, description="Număr maxim de pagini de scanat per site")


def make_discover_tool(agent_id: str, base_url: str, ws, loop):
    def _run(limit: int = 10) -> str:
        try:
            asyncio.run_coroutine_threadsafe(send_status(ws, f"🔎 Discover start (limit={limit})"), loop)
        except Exception:
            pass
        try:
            r = requests.post(
                f"{base_url}/admin/industry/{agent_id}/discover",
                json={"limit": int(limit)},
                timeout=300,
            )
            r.raise_for_status()
            data = r.json()
            try:
                asyncio.run_coroutine_threadsafe(
                    send_status(ws, f"🔎 Discover done: {data.get('count', 0)} candidați"),
                    loop,
                )
            except Exception:
                pass
            return json.dumps(
                {"ok": True, "results": data.get("results", []), "queries": data.get("queries", [])},
                ensure_ascii=False,
            )
        except Exception as e:
            try:
                asyncio.run_coroutine_threadsafe(send_status(ws, f"❗ Discover error: {e}"), loop)
            except Exception:
                pass
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    return StructuredTool.from_function(
        name="discover_industry",
        description=(
            "Descoperă competitori pentru site-ul curent. Returnează candidați {url, score, reason}. "
            "Folosește când vrei extindere de cunoaștere."
        ),
        func=_run,
        args_schema=DiscoverInput,
        return_direct=False,
    )


def make_ingest_tool(agent_id: str, base_url: str, ws, loop):
    def _run(urls: List[str], max_pages: int = 3) -> str:
        try:
            asyncio.run_coroutine_threadsafe(
                send_status(ws, f"📥 Ingest start ({len(urls)} URL-uri, max_pages={max_pages})"),
                loop,
            )
        except Exception:
            pass
        try:
            r = requests.post(
                f"{base_url}/admin/industry/{agent_id}/ingest",
                json={"urls": urls, "max_pages": int(max_pages)},
                timeout=900,
            )
            r.raise_for_status()
            data = r.json()
            try:
                asyncio.run_coroutine_threadsafe(
                    send_status(ws, f"📥 Ingest done: {data.get('created_count', 0)} agenți creați"),
                    loop,
                )
            except Exception:
                pass
            return json.dumps(
                {"ok": True, "created": data.get("created", []), "created_count": data.get("created_count", 0)},
                ensure_ascii=False,
            )
        except Exception as e:
            try:
                asyncio.run_coroutine_threadsafe(send_status(ws, f"❗ Ingest error: {e}"), loop)
            except Exception:
                pass
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    return StructuredTool.from_function(
        name="ingest_sites",
        description=(
            "Ingerează URL-uri ca agenți noi (creează agenți și scanează pagini). "
            "Folosește după discover pentru top 2–3 URL-uri."
        ),
        func=_run,
        args_schema=IngestInput,
        return_direct=False,
    )


async def handle_task_conversation(websocket, api_key: str, agent_id: str, site_url: str, initial_strategy: str):
    await send_status(websocket, "Inițializez agentul cu unelte...")

    # LLM: temperatură mică, stabil
    llm = ChatOpenAI(
        model_name=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        openai_api_key=api_key,
        temperature=0,
    )

    # Unelte de bază pentru agent (ex. RAG/retriever pentru site)
    base_tools = get_tools_for_agent(agent_id) or []

    # Unelte Admin expuse conversației (discover + ingest)
    loop = asyncio.get_running_loop()
    BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://127.0.0.1:8083")
    discover_tool = make_discover_tool(agent_id, BASE_URL, websocket, loop)
    ingest_tool = make_ingest_tool(agent_id, BASE_URL, websocket, loop)

    tools = [discover_tool, ingest_tool] + list(base_tools)

    # Instructăm ferm agentul să NU halucineze și să folosească întâi uneltele
    SAFETY_INSTRUCTIONS = (
        "Instrucțiuni generale (respectă-le în orice răspuns): "
        "1) Răspunde EXCLUSIV în limba română, concis și direct. "
        f"2) Folosește DOAR informații din site-ul curent ({site_url}); dacă informația nu e încă disponibilă, "
        "trebuie să folosești uneltele (tools) pentru a căuta/recupera conținutul relevant. "
        "3) NU inventa produse/denumiri; dacă nu ai dovezi din conținut, spune explicit ce îți lipsește și cere să scanezi/apelezi uneltele. "
        "4) Pentru extindere: "
        "   - Apelează mai întâi discover_industry(limit=8..12). "
        "   - Selectează 2–3 URL-uri cu scor mare și apelează ingest_sites(urls=[...], max_pages=3). "
        "   - Explică pe scurt ce ai creat. "
        "5) Când finalizezi, oferă un răspuns clar pentru utilizator."
    )

    # 1) Încarcă contextul agentului + rezumat scurt pentru LLM
    try:
        agent_doc = db.agents.find_one({"_id": __import__("bson").ObjectId(agent_id)})
    except Exception:
        agent_doc = None
    summary_lines = []
    if agent_doc:
        summary_lines.append(f"Agent: {agent_doc.get('name') or ''} domain={agent_doc.get('domain') or ''} site_url={agent_doc.get('site_url') or ''}")
        # extrage câteva bucăți de conținut din vector store, dacă există tool search_site
        try:
            if base_tools:
                snippet = ""  # păstrăm loc pentru viitoare extrageri din RAG
                if snippet:
                    summary_lines.append(f"Snippet: {snippet[:400]}")
        except Exception:
            pass
    context_summary = "\n".join([s for s in summary_lines if s])

    # 2) Propunere inițială de strategie afișată în chat
    proposal_prompt = (
        "Ești un orchestrator. Primești un website și trebuie să propui direcții de căutare și înțelegere a industriei.\n"
        f"Website: {site_url}\n"
        f"Context agent (din DB):\n{context_summary}\n\n"
        "Propune 3-5 direcții concrete (puncte) care includ: interogări SERP, tipuri de pagini de analizat, competitori probabili, și ce metrici să colectăm. Răspuns scurt, în română."
    )
    try:
        proposal = await llm.ainvoke(proposal_prompt) if hasattr(llm, "ainvoke") else await asyncio.to_thread(llm.invoke, proposal_prompt)
        proposal_text = getattr(proposal, "content", str(proposal))
    except Exception:
        proposal_text = "(nu am reușit să generez o propunere acum)"

    await send_ws_message(websocket, "assistant", f"Propunere inițială de strategie:\n{proposal_text}")

    # Agent cu function calling (mai robust decât parsere text)
    # agent_graph = create_agent(  # Deprecated in langchain 1.0+
    #     model=llm,
    #     tools=tools,
    #     system_prompt=SAFETY_INSTRUCTIONS,
    #     debug=True,
    # )
    agent_graph = None  # TODO: replace with langchain 1.0+ agent creation

    # Mesaj de întâmpinare în română
    greeting = f"Bună! Sunt consilierul pentru {site_url}. Cu ce te pot ajuta în strategia „{initial_strategy}”?"
    await send_status(websocket, f"Agent pregătit pentru {site_url}.")
    await send_status(websocket, "Unelte active: discover_industry, ingest_sites")
    await send_ws_message(websocket, "assistant", greeting)

    # Sistem/fallback pentru răspuns direct fără unelte (în caz de erori interne)
    SAFE_SYS = (
        "Vei răspunde EXCLUSIV în limba română, concis, util și fără preambuluri despre faptul că ești un AI. "
        "Folosește DOAR informații din site-ul curent. Dacă nu le ai, spune ce îți lipsește și cere permisiunea să scanezi/apelezi uneltele."
    )

    try:
        while True:
            try:
                user_message = await websocket.receive_text()
            except WebSocketDisconnect:
                logger.info("WebSocket closed by client")
                return

            await send_ws_message(websocket, "user", user_message)

            guided_input = f"{SAFETY_INSTRUCTIONS}\n\nÎntrebare utilizator: {user_message}"

            try:
                # rulează sincron într-un thread, pentru a nu bloca event loop-ul
                from langchain_core.messages import HumanMessage
                messages = [HumanMessage(content=guided_input)]
                if agent_graph:
                    result = await asyncio.to_thread(agent_graph.invoke, {"messages": messages})
                else:
                    # Fallback direct pe LLM dacă agent_graph nu e disponibil
                    result = await llm.ainvoke(messages) if hasattr(llm, "ainvoke") else await asyncio.to_thread(llm.invoke, messages)
                    result = {"messages": [result]} if not isinstance(result, dict) else result
                
                # Extrage ultimul mesaj AI din rezultat
                if isinstance(result, dict) and "messages" in result:
                    messages = result["messages"]
                    ai_text = ""
                    for msg in reversed(messages):
                        if hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_calls"):
                            ai_text = msg.content
                            break
                else:
                    ai_text = str(result) if result else ""
                
                if not ai_text:
                    ai_text = "Nu am reușit să generez un răspuns util pe baza conținutului disponibil."
                await send_ws_message(websocket, "assistant", ai_text)

            except OutputParserException:
                # Fallback: răspuns direct pe LLM (fără tooluri), în română
                logger.warning("OutputParserException - fallback direct pe LLM.")
                if hasattr(llm, "ainvoke"):
                    if SystemMessage and HumanMessage:
                        msg = await llm.ainvoke([SystemMessage(content=SAFE_SYS), HumanMessage(content=user_message)])
                        ai_text = getattr(msg, "content", str(msg))
                    else:
                        ai_text = (await llm.ainvoke(f"{SAFE_SYS}\n\nÎntrebare: {user_message}")).content
                else:
                    def _call_llm():
                        if SystemMessage and HumanMessage:
                            m = llm.invoke([SystemMessage(content=SAFE_SYS), HumanMessage(content=user_message)])
                            return getattr(m, "content", str(m))
                        return llm.invoke(f"{SAFE_SYS}\n\nÎntrebare: {user_message}").content
                    ai_text = await asyncio.to_thread(_call_llm)

                await send_ws_message(websocket, "assistant", ai_text)

            except WebSocketDisconnect:
                logger.info("WebSocket closed by client")
                return

            except Exception as e:
                logger.exception("Eroare agent:")
                try:
                    await send_ws_message(
                        websocket, "error",
                        f"Eroare în agent: {e}. Dacă problema persistă, încearcă din nou sau cere scanarea paginilor relevante."
                    )
                except Exception:
                    # WS poate fi deja închis
                    pass

    except Exception as e:
        logger.info(f"Conexiune WS închisă sau altă eroare: {e}")
        try:
            await send_ws_message(websocket, "error", str(e))
        except Exception:
            pass
