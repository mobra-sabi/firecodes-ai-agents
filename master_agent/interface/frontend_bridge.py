#!/usr/bin/env python3
"""
🌉 Frontend Bridge
WebSocket bridge între UI și Master Agent
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, List
import json
import logging

logger = logging.getLogger(__name__)


class FrontendBridge:
    """Bridge pentru comunicare WebSocket cu frontend-ul"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, WebSocket] = {}  # user_id -> WebSocket
    
    async def connect(self, websocket: WebSocket, user_id: str = "default"):
        """Conectează un client WebSocket"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_connections[user_id] = websocket
        logger.info(f"WebSocket connected for user: {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str = "default"):
        """Deconectează un client"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id in self.user_connections:
            del self.user_connections[user_id]
        logger.info(f"WebSocket disconnected for user: {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], user_id: str):
        """Trimite mesaj către un utilizator specific"""
        if user_id in self.user_connections:
            websocket = self.user_connections[user_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Trimite mesaj către toți clienții"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
                disconnected.append(connection)
        
        # Șterge conexiunile deconectate
        for conn in disconnected:
            self.active_connections.remove(conn)
    
    async def handle_ui_action(self, user_id: str, action: str, data: Dict[str, Any], chat_api):
        """
        Gestionează o acțiune din UI
        
        Args:
            user_id: ID-ul utilizatorului
            action: Acțiunea (ex: "button_click", "autopilot_on")
            data: Datele acțiunii
            chat_api: Instanță ChatAPI pentru procesare
        """
        try:
            # Dacă e autopilot activat, trimite la chat
            profile = chat_api.profiles_db.get_profile(user_id)
            if profile.get("autopilot", False) and action == "button_click":
                button_name = data.get("button", "")
                message = f"Click pe butonul {button_name}"
                
                # Procesează ca mesaj chat
                result = chat_api.process_chat(user_id, message, generate_audio=True)
                
                # Trimite răspunsul înapoi la UI
                await self.send_personal_message({
                    "type": "agent_response",
                    "text": result["text"],
                    "audio_path": result.get("audio_path"),
                    "action": result.get("action")
                }, user_id)
        except Exception as e:
            logger.error(f"Error handling UI action: {e}")


# Singleton instance
_frontend_bridge_instance = None

def get_frontend_bridge() -> FrontendBridge:
    """Get singleton instance"""
    global _frontend_bridge_instance
    if _frontend_bridge_instance is None:
        _frontend_bridge_instance = FrontendBridge()
    return _frontend_bridge_instance


