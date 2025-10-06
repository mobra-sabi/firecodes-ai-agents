import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Fix import - folosește calea relativă corectă
from database.mongodb_handler import MongoDBHandler

class EpisodeMemory:
    """Sistemul de memorie episodică REAL pentru ființe digitale"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.mongodb = MongoDBHandler()
        self.collection_name = f"memory_{agent_id}"
        
        # Inițializează colecția de memorie în MongoDB
        self.init_memory_collection()
        
    def init_memory_collection(self):
        """Inițializează colecția de memorii în MongoDB"""
        try:
            collection = self.mongodb.db[self.collection_name]
            collection.create_index("timestamp")
            collection.create_index("importance")
            collection.create_index("event_type")
            print(f"✅ Memorie inițializată pentru agent {self.agent_id}")
        except Exception as e:
            print(f"⚠️ Eroare inițializare memorie: {e}")
        
    def create_episode(self, event_type: str, content: str, importance: int = 5, 
                      metadata: Dict = None) -> str:
        """Creează un episod nou în memorie - REAL STORAGE"""
        
        episode = {
            'episode_id': str(uuid.uuid4()),
            'agent_id': self.agent_id,
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'content': content,
            'importance': importance,
            'metadata': metadata or {},
            'access_count': 0,
            'last_accessed': datetime.now().isoformat(),
            'emotional_weight': self.calculate_emotional_weight(event_type, content),
            'keywords': self.extract_keywords(content)
        }
        
        try:
            collection = self.mongodb.db[self.collection_name]
            collection.insert_one(episode)
            print(f"📝 Episod salvat: {event_type} (importance: {importance})")
            return episode['episode_id']
        except Exception as e:
            print(f"❌ Eroare salvare episod: {e}")
            return None
        
    def recall_episodes(self, query: str, limit: int = 5) -> List[Dict]:
        """Rechemă episoade relevante - REAL SEARCH"""
        
        try:
            collection = self.mongodb.db[self.collection_name]
            query_words = query.lower().split()
            
            search_results = list(collection.find({
                '$or': [
                    {'content': {'$regex': query, '$options': 'i'}},
                    {'keywords': {'$in': query_words}},
                    {'event_type': {'$regex': query, '$options': 'i'}}
                ]
            }).sort([('importance', -1), ('timestamp', -1)]).limit(limit))
            
            # Actualizează access_count
            for episode in search_results:
                collection.update_one(
                    {'episode_id': episode['episode_id']},
                    {
                        '$inc': {'access_count': 1},
                        '$set': {'last_accessed': datetime.now().isoformat()}
                    }
                )
                
            print(f"🔍 Găsite {len(search_results)} episoade pentru: '{query}'")
            return search_results
            
        except Exception as e:
            print(f"❌ Eroare căutare episoade: {e}")
            return []
        
    def get_memory_summary(self) -> str:
        """Creează un sumar REAL al memoriilor"""
        
        try:
            collection = self.mongodb.db[self.collection_name]
            
            total_episodes = collection.count_documents({})
            important_episodes = collection.count_documents({'importance': {'$gte': 8}})
            recent_count = collection.count_documents({
                'timestamp': {'$gte': (datetime.now() - timedelta(days=7)).isoformat()}
            })
            
            event_types = collection.distinct('event_type')
            
            summary = f"""📚 SUMAR MEMORIE AGENT {self.agent_id}:

📊 Statistici:
   • Total episoade: {total_episodes}
   • Amintiri importante: {important_episodes}
   • Activitate recentă (7 zile): {recent_count}

🎯 Tipuri evenimente: {', '.join(event_types[:5])}"""
            
            return summary
            
        except Exception as e:
            return f"❌ Eroare generare sumar: {e}"
            
    def calculate_emotional_weight(self, event_type: str, content: str) -> float:
        """Calculează greutatea emoțională"""
        weight = 0.5
        
        positive_words = ['succes', 'excelent', 'mulțumit', 'bun']
        negative_words = ['problemă', 'eroare', 'rău', 'eșec']
        
        content_lower = content.lower()
        
        for word in positive_words:
            if word in content_lower:
                weight += 0.1
                
        for word in negative_words:
            if word in content_lower:
                weight -= 0.1
                
        return max(0, min(1, weight))
        
    def extract_keywords(self, content: str) -> List[str]:
        """Extrage cuvinte cheie"""
        words = content.lower().split()
        stop_words = {'și', 'în', 'de', 'la', 'cu', 'pe', 'pentru', 'din'}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        return keywords[:10]  # Primele 10
