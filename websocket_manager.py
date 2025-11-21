"""
WebSocket Manager
Manages WebSocket connections for live job logs and real-time updates
"""
import logging
import json
import asyncio
from typing import Dict, Set, Optional
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self, mongo_client: MongoClient = None):
        if mongo_client is None:
            mongo_client = MongoClient("mongodb://localhost:27017/")
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        
        # Active connections: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Subscriptions: {connection_id: Set[subscription_types]}
        self.subscriptions: Dict[str, Set[str]] = {}
        
        # Job logs: {job_id: List[log_entries]}
        self.job_logs: Dict[str, list] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.subscriptions[connection_id] = set()
        logger.info(f"✅ WebSocket connected: {connection_id}")
    
    def disconnect(self, connection_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.subscriptions:
            del self.subscriptions[connection_id]
        logger.info(f"❌ WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: dict, connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                self.disconnect(connection_id)
                return False
        return False
    
    async def broadcast(self, message: dict, subscription_type: Optional[str] = None):
        """Broadcast message to all subscribed connections"""
        disconnected = []
        
        for connection_id, websocket in self.active_connections.items():
            # If subscription_type specified, only send to subscribed connections
            if subscription_type:
                if subscription_type not in self.subscriptions.get(connection_id, set()):
                    continue
            
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for conn_id in disconnected:
            self.disconnect(conn_id)
    
    def subscribe(self, connection_id: str, subscription_type: str):
        """Subscribe connection to a type of updates"""
        if connection_id not in self.subscriptions:
            self.subscriptions[connection_id] = set()
        self.subscriptions[connection_id].add(subscription_type)
        logger.info(f"✅ {connection_id} subscribed to {subscription_type}")
    
    def unsubscribe(self, connection_id: str, subscription_type: str):
        """Unsubscribe connection from a type of updates"""
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id].discard(subscription_type)
        logger.info(f"❌ {connection_id} unsubscribed from {subscription_type}")
    
    async def send_job_log(self, job_id: str, log_entry: dict):
        """Send job log entry to subscribed connections"""
        # Store log entry
        if job_id not in self.job_logs:
            self.job_logs[job_id] = []
        self.job_logs[job_id].append(log_entry)
        
        # Broadcast to subscribers
        message = {
            "type": "job_log",
            "job_id": job_id,
            "log": log_entry,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast(message, subscription_type=f"job_{job_id}")
    
    async def send_workflow_update(self, agent_id: str, update: dict):
        """Send workflow update to subscribed connections"""
        message = {
            "type": "workflow_update",
            "agent_id": agent_id,
            "update": update,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast(message, subscription_type=f"workflow_{agent_id}")
    
    async def send_action_update(self, action_id: str, update: dict):
        """Send action queue update to subscribed connections"""
        message = {
            "type": "action_update",
            "action_id": action_id,
            "update": update,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast(message, subscription_type="actions")
    
    async def send_alert(self, alert: dict):
        """Send alert to subscribed connections"""
        message = {
            "type": "alert",
            "alert": alert,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast(message, subscription_type="alerts")
    
    def get_job_logs(self, job_id: str, limit: int = 100) -> list:
        """Get stored job logs"""
        if job_id in self.job_logs:
            return self.job_logs[job_id][-limit:]
        return []
    
    def get_active_connections_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)

