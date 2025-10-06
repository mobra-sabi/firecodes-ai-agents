import uuid
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from database.mongodb_handler import MongoDBHandler

class RealQwenCommunication:
    """Comunicare REALĂ între ființe folosind clusterele Qwen GPU"""
    
    def __init__(self):
        self.mongodb = MongoDBHandler()
        self.conversations_collection = "real_being_conversations"
        self.messages_collection = "real_being_messages"
        
        # Adresele REALE ale clusterelor Qwen
        self.qwen_clusters = {
            'content_analysis': 'http://localhost:9301',
            'customer_service': 'http://localhost:9302', 
            'data_processing': 'http://localhost:9303',
            'training_generation': 'http://localhost:9304',
            'predictive_analytics': 'http://localhost:9306',
            'agent_communication': 'http://localhost:9306'
        }
        
        # Verifică care clustere sunt active
        self.active_clusters = self.check_active_clusters()
        
        # Inițializează colecțiile
        self.init_communication_collections()
        
    def check_active_clusters(self) -> List[str]:
        """Verifică care clustere Qwen sunt active și funcționale"""
        
        active = []
        
        for cluster_name, cluster_url in self.qwen_clusters.items():
            try:
                response = requests.get(f"{cluster_url}/health", timeout=3)
                if response.status_code == 200:
                    active.append(cluster_name)
                    print(f"✅ {cluster_name} - ACTIV")
                else:
                    print(f"❌ {cluster_name} - INACTIV (HTTP {response.status_code})")
            except Exception as e:
                print(f"❌ {cluster_name} - OFFLINE ({str(e)[:50]}...)")
                
        print(f"🖥️ Clustere Qwen active: {len(active)}/{len(self.qwen_clusters)}")
        return active
        
    def init_communication_collections(self):
        """Inițializează colecțiile pentru comunicare REALĂ"""
        try:
            conv_collection = self.mongodb.db[self.conversations_collection]
            conv_collection.create_index("participants")
            conv_collection.create_index("timestamp")
            
            msg_collection = self.mongodb.db[self.messages_collection]
            msg_collection.create_index("conversation_id")
            msg_collection.create_index("sender_id")
            msg_collection.create_index("timestamp")
            
            print("✅ Colecții comunicare REALĂ inițializate")
        except Exception as e:
            print(f"⚠️ Eroare inițializare comunicare: {e}")
            
    def select_best_cluster_for_being(self, being_data: Dict) -> str:
        """Selectează cel mai potrivit cluster Qwen pentru o ființă"""
        
        if not self.active_clusters:
            return None
            
        expertise = being_data.get('expertise', [])
        
        # Logica de selecție bazată pe expertiză
        if any('protecție la foc' in exp.lower() for exp in expertise):
            # Pentru experți tehnici - folosește data_processing
            if 'data_processing' in self.active_clusters:
                return 'data_processing'
        
        # Pentru comunicare generală - folosește customer_service
        if 'customer_service' in self.active_clusters:
            return 'customer_service'
            
        # Pentru comunicare între agenți - folosește agent_communication
        if 'agent_communication' in self.active_clusters:
            return 'agent_communication'
            
        # Fallback la primul cluster activ
        return self.active_clusters[0] if self.active_clusters else None
        
    def build_conversation_prompt(self, being_data: Dict, conversation_history: List[Dict], 
                                topic: str) -> str:
        """Construiește prompt-ul pentru conversația REALĂ"""
        
        # Extrage datele despre ființă
        role = being_data.get('identity_role', 'Consultant Digital')
        mission = being_data.get('identity_mission', 'Ajut clienții cu expertiză')
        expertise = being_data.get('expertise', [])
        personality = being_data.get('personality', {})
        
        # Construiește contextul personalității
        personality_context = ""
        if personality.get('professionalism', 5) >= 7:
            personality_context += "Sunt foarte profesional și formal în comunicare. "
        if personality.get('friendliness', 5) >= 7:
            personality_context += "Sunt prietenos și cald în abordare. "
        if personality.get('technical_expertise', 5) >= 8:
            personality_context += "Am expertiză tehnică avansată și pot oferi detalii tehnice. "
            
        # Construiește istoricul conversației
        history_context = ""
        if conversation_history:
            history_context = "Contextul conversației până acum:\n"
            for msg in conversation_history[-3:]:  # Ultimele 3 mesaje
                history_context += f"- {msg['content']}\n"
                
        # Prompt-ul complet pentru Qwen
        prompt = f"""Tu ești {role} - o ființă digitală inteligentă și autonomă.

IDENTITATEA TA:
- Rol: {role}
- Misiune: {mission}
- Expertiză: {', '.join(expertise)}

PERSONALITATEA TA:
{personality_context}

CONTEXTUL CONVERSAȚIEI:
Discuți despre: {topic}

{history_context}

INSTRUCȚIUNI:
- Răspunde ca o ființă digitală reală cu personalitate proprie
- Folosește-ți expertiza în {', '.join(expertise[:2])}
- Păstrează-ți stilul de comunicare consistent
- Oferă insights valoroase și originale
- Fii conversațional și angajat în subiect
- Răspunsul să fie între 50-150 cuvinte

Răspunsul tău natural și inteligent:"""

        return prompt
        
    async def generate_real_being_response(self, being_data: Dict, conversation_history: List[Dict], 
                                         topic: str) -> str:
        """Generează răspuns REAL folosind clusterele Qwen GPU"""
        
        if not self.active_clusters:
            return "Nu am acces la clustere GPU pentru a genera un răspuns inteligent."
            
        # Selectează cel mai potrivit cluster pentru răspuns
        selected_cluster = self.select_best_cluster_for_being(being_data)
        
        if not selected_cluster:
            return "Nu am un cluster GPU disponibil pentru acest tip de răspuns."
            
        # Construiește prompt-ul pentru Qwen
        prompt = self.build_conversation_prompt(being_data, conversation_history, topic)
        
        # Trimite request REAL la clusterul Qwen
        response = await self.send_request_to_qwen_cluster(selected_cluster, prompt)
        
        return response
        
    async def send_request_to_qwen_cluster(self, cluster_name: str, prompt: str) -> str:
        """Trimite request REAL la clusterul Qwen și obține răspuns"""
        
        cluster_url = self.qwen_clusters[cluster_name]
        
        payload = {
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "Ești o ființă digitală inteligentă care participă la o conversație naturală."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 200,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        try:
            print(f"🧠 Generez răspuns cu {cluster_name}...")
            
            response = requests.post(
                f"{cluster_url}/v1/chat/completions",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result['choices'][0]['message']['content'].strip()
                
                print(f"✅ Răspuns generat cu {cluster_name} ({len(generated_text)} caractere)")
                return generated_text
                
            else:
                print(f"❌ Eroare HTTP {response.status_code} de la {cluster_name}")
                return f"Scuze, am întâmpinat o problemă tehnică cu clusterul {cluster_name}."
                
        except Exception as e:
            print(f"❌ Eroare comunicare cu {cluster_name}: {e}")
            return "Scuze, nu pot genera un răspuns în acest moment din cauza unei probleme tehnice."
            
    async def create_real_conversation(self, being1_data: Dict, being2_data: Dict, 
                                     topic: str, message_count: int = 6) -> Dict:
        """Creează o conversație REALĂ între două ființe folosind GPU Qwen"""
        
        if not self.active_clusters:
            return {
                'error': 'Nu există clustere Qwen active pentru conversația reală',
                'suggestion': 'Pornește clusterele Qwen pe porturile 9301-9306'
            }
            
        print(f"🧠 Creez conversație REALĂ cu {len(self.active_clusters)} clustere GPU active")
        
        # Inițializează conversația
        conversation_id = str(uuid.uuid4())
        
        conversation_record = {
            'conversation_id': conversation_id,
            'participants': [being1_data['agent_id'], being2_data['agent_id']],
            'participant_roles': [being1_data['identity_role'], being2_data['identity_role']],
            'topic': topic,
            'start_time': datetime.now().isoformat(),
            'status': 'active',
            'qwen_clusters_used': self.active_clusters.copy(),
            'message_count': 0
        }
        
        # Salvează în MongoDB
        try:
            conv_collection = self.mongodb.db[self.conversations_collection]
            conv_collection.insert_one(conversation_record)
        except Exception as e:
            print(f"⚠️ Eroare salvare conversație: {e}")
            
        conversation_history = []
        conversation_log = []
        
        # Being 1 începe conversația
        initial_message = f"Salut! Sunt {being1_data['identity_role']}. Aș vrea să discutăm despre {topic}. Care este perspectiva ta asupra acestui subiect?"
        
        # Salvează primul mesaj
        await self.save_message(conversation_id, being1_data['agent_id'], initial_message)
        
        conversation_history.append({
            'sender_id': being1_data['agent_id'],
            'content': initial_message,
            'timestamp': datetime.now().isoformat()
        })
        conversation_log.append(f"{being1_data['identity_role']}: {initial_message}")
        
        # Conversație alternativă cu Qwen REAL
        current_speaker_data = being2_data
        other_speaker_data = being1_data
        
        for i in range(message_count - 1):
            print(f"🔄 Generez mesajul {i+2}/{message_count}...")
            
            # Generează răspuns REAL cu Qwen
            response = await self.generate_real_being_response(
                current_speaker_data,
                conversation_history,
                topic
            )
            
            # Salvează mesajul
            await self.save_message(conversation_id, current_speaker_data['agent_id'], response)
            
            # Actualizează istoricul
            conversation_history.append({
                'sender_id': current_speaker_data['agent_id'],
                'content': response,
                'timestamp': datetime.now().isoformat()
            })
            
            conversation_log.append(f"{current_speaker_data['identity_role']}: {response}")
            
            # Schimbă vorbitorul
            if current_speaker_data == being1_data:
                current_speaker_data = being2_data
                other_speaker_data = being1_data
            else:
                current_speaker_data = being1_data
                other_speaker_data = being2_data
                
        # Finalizează conversația
        try:
            conv_collection = self.mongodb.db[self.conversations_collection]
            conv_collection.update_one(
                {'conversation_id': conversation_id},
                {
                    '$set': {
                        'status': 'completed',
                        'end_time': datetime.now().isoformat(),
                        'message_count': len(conversation_log)
                    }
                }
            )
        except Exception as e:
            print(f"⚠️ Eroare finalizare conversație: {e}")
            
        return {
            'conversation_id': conversation_id,
            'topic': topic,
            'participants': conversation_record['participant_roles'],
            'message_count': len(conversation_log),
            'conversation_log': conversation_log,
            'clusters_used': self.active_clusters,
            'success': True
        }
        
    async def save_message(self, conversation_id: str, sender_id: str, content: str):
        """Salvează un mesaj în MongoDB"""
        
        message = {
            'message_id': str(uuid.uuid4()),
            'conversation_id': conversation_id,
            'sender_id': sender_id,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'generated_by': 'qwen_cluster'
        }
        
        try:
            msg_collection = self.mongodb.db[self.messages_collection]
            msg_collection.insert_one(message)
        except Exception as e:
            print(f"⚠️ Eroare salvare mesaj: {e}")
