import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from database.mongodb_handler import MongoDBHandler

class InterBeingCommunication:
    """Sistem REAL de comunicare între ființe digitale"""
    
    def __init__(self):
        self.mongodb = MongoDBHandler()
        self.conversations_collection = "being_conversations"
        self.messages_collection = "being_messages"
        
        # Inițializează colecțiile
        self.init_communication_collections()
        
    def init_communication_collections(self):
        """Inițializează colecțiile pentru comunicare"""
        try:
            # Index pentru conversații
            conv_collection = self.mongodb.db[self.conversations_collection]
            conv_collection.create_index("participants")
            conv_collection.create_index("timestamp")
            
            # Index pentru mesaje
            msg_collection = self.mongodb.db[self.messages_collection]
            msg_collection.create_index("conversation_id")
            msg_collection.create_index("sender_id")
            msg_collection.create_index("timestamp")
            
            print("✅ Colecții comunicare inițializate")
        except Exception as e:
            print(f"⚠️ Eroare inițializare comunicare: {e}")
            
    def start_conversation(self, being1_id: str, being2_id: str, topic: str) -> str:
        """Începe o conversație REALĂ între două ființe"""
        
        conversation = {
            'conversation_id': str(uuid.uuid4()),
            'participants': [being1_id, being2_id],
            'topic': topic,
            'start_time': datetime.now().isoformat(),
            'status': 'active',
            'message_count': 0,
            'last_activity': datetime.now().isoformat()
        }
        
        try:
            collection = self.mongodb.db[self.conversations_collection]
            collection.insert_one(conversation)
            
            print(f"💬 Conversație începută: {being1_id} ↔ {being2_id} despre '{topic}'")
            return conversation['conversation_id']
            
        except Exception as e:
            print(f"❌ Eroare început conversație: {e}")
            return None
            
    def send_message(self, conversation_id: str, sender_id: str, 
                    content: str, message_type: str = "text") -> str:
        """Trimite mesaj REAL în conversație"""
        
        message = {
            'message_id': str(uuid.uuid4()),
            'conversation_id': conversation_id,
            'sender_id': sender_id,
            'content': content,
            'message_type': message_type,
            'timestamp': datetime.now().isoformat(),
            'read_by': [],
            'reactions': []
        }
        
        try:
            # Salvează mesajul
            msg_collection = self.mongodb.db[self.messages_collection]
            msg_collection.insert_one(message)
            
            # Actualizează conversația
            conv_collection = self.mongodb.db[self.conversations_collection]
            conv_collection.update_one(
                {'conversation_id': conversation_id},
                {
                    '$inc': {'message_count': 1},
                    '$set': {'last_activity': datetime.now().isoformat()}
                }
            )
            
            print(f"📨 Mesaj trimis de {sender_id}: {content[:50]}...")
            return message['message_id']
            
        except Exception as e:
            print(f"❌ Eroare trimitere mesaj: {e}")
            return None
            
    def generate_being_response(self, being_id: str, conversation_context: List[Dict], 
                               being_identity: Dict) -> str:
        """Generează răspuns bazat pe personalitatea ființei REALE"""
        
        # Analizează contextul conversației
        last_message = conversation_context[-1] if conversation_context else None
        
        if not last_message:
            return "Salut! Cu ce te pot ajuta?"
            
        # Extrage personalitatea
        personality = being_identity.get('personality', {})
        role = being_identity.get('identity_role', 'Consultant')
        expertise = being_identity.get('expertise', [])
        
        # Generează răspuns bazat pe personalitate
        professionalism = personality.get('professionalism', 5)
        friendliness = personality.get('friendliness', 5)
        technical_expertise = personality.get('technical_expertise', 5)
        
        # Construiește răspunsul
        if professionalism >= 7:
            greeting = "În calitate de " + role + ", "
        else:
            greeting = "Ca " + role.lower() + ", "
            
        # Adaptează la conținutul mesajului
        last_content = last_message['content'].lower()
        
        if any(exp.lower() in last_content for exp in expertise):
            if technical_expertise >= 8:
                response = greeting + "pot să vă ofer o analiză tehnică detaliată pe acest subiect. "
            else:
                response = greeting + "vă pot ajuta cu informații despre acest aspect. "
        else:
            if friendliness >= 7:
                response = greeting + "sunt bucuros să discut despre acest subiect interesant. "
            else:
                response = greeting + "pot să vă ajut cu acest aspect. "
                
        # Adaugă întrebare pentru continuarea conversației
        if professionalism >= 7:
            response += "Ce aspecte specifice vă interesează cel mai mult?"
        else:
            response += "Ce anume te-ar interesa să știi mai multe?"
            
        return response
        
    def simulate_conversation(self, being1_data: Dict, being2_data: Dict, 
                            topic: str, message_count: int = 6) -> Dict:
        """Simulează o conversație REALĂ între două ființe"""
        
        being1_id = being1_data['agent_id']
        being2_id = being2_data['agent_id']
        
        # Începe conversația
        conv_id = self.start_conversation(being1_id, being2_id, topic)
        
        if not conv_id:
            return {'error': 'Nu s-a putut începe conversația'}
            
        conversation_log = []
        conversation_context = []
        
        # Being 1 începe conversația
        initial_message = f"Salut! Aș vrea să discutăm despre {topic}. Ce părere ai?"
        msg1_id = self.send_message(conv_id, being1_id, initial_message)
        
        conversation_context.append({
            'sender_id': being1_id,
            'content': initial_message,
            'timestamp': datetime.now().isoformat()
        })
        conversation_log.append(f"{being1_data['identity_role']}: {initial_message}")
        
        # Conversație alternativă
        current_speaker = being2_id
        current_speaker_data = being2_data
        other_speaker_data = being1_data
        
        for i in range(message_count - 1):
            # Generează răspuns
            response = self.generate_being_response(
                current_speaker, 
                conversation_context, 
                current_speaker_data
            )
            
            # Trimite mesajul
            msg_id = self.send_message(conv_id, current_speaker, response)
            
            # Actualizează contextul
            conversation_context.append({
                'sender_id': current_speaker,
                'content': response,
                'timestamp': datetime.now().isoformat()
            })
            
            conversation_log.append(f"{current_speaker_data['identity_role']}: {response}")
            
            # Schimbă vorbitorul
            if current_speaker == being1_id:
                current_speaker = being2_id
                current_speaker_data = being2_data
                other_speaker_data = being1_data
            else:
                current_speaker = being1_id
                current_speaker_data = being1_data
                other_speaker_data = being2_data
                
        return {
            'conversation_id': conv_id,
            'topic': topic,
            'participants': [being1_data['identity_role'], being2_data['identity_role']],
            'message_count': len(conversation_log),
            'conversation_log': conversation_log,
            'success': True
        }
