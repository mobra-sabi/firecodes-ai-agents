#!/usr/bin/env python3
"""
🛣️ Master Agent Router
Rutele principale pentru FastAPI
"""

from fastapi import APIRouter, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

from memory.profiles_db import get_profiles_db
from memory.context_memory import get_context_memory
from skills.planning import get_intent_planner
from skills.actions import get_actions_executor
from voice.tts_service import get_tts_service
from voice.stt_service import get_stt_service
from interface.chat_api import ChatAPI
from interface.frontend_bridge import get_frontend_bridge
from controllers.node_controller import get_node_controller
from controllers.learning_controller import get_learning_controller

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
profiles_db = get_profiles_db()
context_memory = get_context_memory()
intent_planner = get_intent_planner()
actions_executor = get_actions_executor()
tts_service = get_tts_service()
stt_service = get_stt_service()
chat_api = ChatAPI(profiles_db, context_memory, intent_planner, actions_executor, tts_service)
frontend_bridge = get_frontend_bridge()
node_controller = get_node_controller()
learning_controller = get_learning_controller(profiles_db, context_memory)


# Request models
class ChatRequest(BaseModel):
    user_id: str
    message: str
    generate_audio: bool = True


class ExecuteRequest(BaseModel):
    action: str
    user_id: str = "default"


class LearnRequest(BaseModel):
    user_id: str


# Routes
@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Endpoint pentru chat verbal și text"""
    try:
        result = chat_api.process_chat(
            request.user_id,
            request.message,
            generate_audio=request.generate_audio
        )
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/chat/audio")
async def chat_audio_endpoint(
    user_id: str,
    audio_file: UploadFile = File(...)
):
    """Endpoint pentru chat cu audio (STT)"""
    try:
        # Salvează audio temporar
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            content = await audio_file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # Transcrie audio
        text = stt_service.transcribe(tmp_path)
        
        # Șterge fișierul temporar
        os.unlink(tmp_path)
        
        if not text:
            return JSONResponse(
                status_code=400,
                content={"error": "Could not transcribe audio"}
            )
        
        # Procesează ca mesaj text
        result = chat_api.process_chat(user_id, text, generate_audio=True)
        
        return JSONResponse(content={
            "transcribed_text": text,
            **result
        })
    except Exception as e:
        logger.error(f"Error in chat audio endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/execute")
async def execute_endpoint(request: ExecuteRequest):
    """Endpoint pentru executarea acțiunilor"""
    try:
        result = actions_executor.execute_action(
            request.action,
            request.user_id,
            callback=lambda job_id, status, result: profiles_db.update_job(job_id, status, result)
        )
        
        if result.get("success"):
            job_id = result.get("job_id")
            profiles_db.add_job(request.user_id, request.action, job_id)
            
            # Generează răspuns verbal
            response_text = f"Sarcina '{request.action}' a fost pornită."
            audio_path = tts_service.synthesize(response_text)
            
            result["response_text"] = response_text
            result["audio_path"] = audio_path
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in execute endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/state")
async def state_endpoint():
    """Endpoint pentru verificarea statusului nodurilor"""
    try:
        status = node_controller.get_system_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Error in state endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/profile/{user_id}")
async def profile_endpoint(user_id: str):
    """Endpoint pentru profilul utilizatorului"""
    try:
        profile = profiles_db.get_profile(user_id)
        recent = profiles_db.get_recent_interactions(user_id, limit=10)
        
        # Convert ObjectId to string
        profile["_id"] = str(profile.get("_id", ""))
        if isinstance(profile.get("created_at"), type):
            profile["created_at"] = profile["created_at"].isoformat()
        if isinstance(profile.get("last_seen"), type):
            profile["last_seen"] = profile["last_seen"].isoformat()
        
        return JSONResponse(content={
            "profile": profile,
            "recent_interactions": recent
        })
    except Exception as e:
        logger.error(f"Error in profile endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/learn")
async def learn_endpoint(request: LearnRequest):
    """Endpoint pentru învățare comportamentală"""
    try:
        patterns = learning_controller.learn_from_interactions(request.user_id)
        
        from datetime import datetime
        current_hour = datetime.now().hour
        suggestion = learning_controller.suggest_action(request.user_id, current_hour)
        
        return JSONResponse(content={
            "patterns": patterns,
            "suggestion": suggestion
        })
    except Exception as e:
        logger.error(f"Error in learn endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/audio/{filename}")
async def get_audio(filename: str):
    """Endpoint pentru obținerea fișierelor audio"""
    import os
    audio_path = os.path.join("/srv/hf/ai_agents/master_agent/voice/output", filename)
    
    if os.path.exists(audio_path):
        return FileResponse(audio_path, media_type="audio/wav")
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "Audio file not found"}
        )


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint pentru comunicare în timp real"""
    await frontend_bridge.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Gestionează mesajele
            message_type = data.get("type")
            
            if message_type == "chat":
                message = data.get("message", "")
                result = chat_api.process_chat(user_id, message, generate_audio=True)
                await websocket.send_json({
                    "type": "response",
                    **result
                })
            elif message_type == "ui_action":
                action = data.get("action")
                action_data = data.get("data", {})
                await frontend_bridge.handle_ui_action(user_id, action, action_data, chat_api)
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        frontend_bridge.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"Error in WebSocket: {e}")
        frontend_bridge.disconnect(websocket, user_id)


