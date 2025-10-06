import asyncio
import json
from enum import Enum
from datetime import datetime
import uuid
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class MessageType(Enum):
    DIRECT_QUESTION = "direct_question"
    COLLABORATION_REQUEST = "collaboration_request"
    KNOWLEDGE_SHARE = "knowledge_share"
    MARKET_UPDATE = "market_update"
    OPPORTUNITY_ALERT = "opportunity_alert"
    EXPERTISE_REQUEST = "expertise_request"

class AgentCommunicationProtocol:
    """Protocol de comunicare între agenți AI"""
    
    def __init__(self):
        self.message_queue = asyncio.Queue()
        self.active_conversations = {}
        self.message_history = []
        
    async def send_agent_message(self, sender_agent_id, recipient_agent_id, message_type, content, context=None):
        """Trimite mesaj între agenți"""
        
        message = {
            'message_id': str(uuid.uuid4()),
            'sender': sender_agent_id,
            'recipient': recipient_agent_id,
            'type': message_type.value,
            'content': content,
            'context': context or {},
            'timestamp': datetime.now().isoformat(),
            'status': 'sent'
        }
        
        await self.message_queue.put(message)
        self.message_history.append(message)
        
        print(f"📨 Mesaj trimis: {sender_agent_id} → {recipient_agent_id} ({message_type.value})")
        
        return message['message_id']
        
    async def broadcast_to_network(self, sender_agent_id, message_type, content, target_industry=None):
        """Broadcast mesaj către rețeaua de agenți"""
        
        broadcast_message = {
            'message_id': str(uuid.uuid4()),
            'sender': sender_agent_id,
            'type': 'broadcast',
            'message_type': message_type.value,
            'content': content,
            'target_industry': target_industry,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"📢 Broadcast de la {sender_agent_id}: {message_type.value}")
        
        return broadcast_message['message_id']
        
    async def create_collaboration_session(self, question, primary_agent_id):
        """Creează sesiune de colaborare între agenți"""
        
        collaboration_session = {
            'session_id': str(uuid.uuid4()),
            'question': question,
            'primary_agent': primary_agent_id,
            'start_time': datetime.now().isoformat(),
            'participants': [primary_agent_id],
            'messages': [],
            'final_answer': None,
            'status': 'active'
        }
        
        self.active_conversations[collaboration_session['session_id']] = collaboration_session
        
        print(f"🤝 Sesiune colaborare creată: {collaboration_session['session_id']}")
        
        return collaboration_session
        
    def get_communication_stats(self):
        """Statistici despre comunicarea între agenți"""
        
        return {
            'total_messages': len(self.message_history),
            'active_conversations': len(self.active_conversations),
            'message_types': {
                msg_type.value: len([m for m in self.message_history if m['type'] == msg_type.value])
                for msg_type in MessageType
            },
            'recent_activity': self.message_history[-5:] if self.message_history else []
        }
