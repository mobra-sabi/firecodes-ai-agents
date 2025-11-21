#!/usr/bin/env python3
"""
🧠 Context Memory Manager
Gestionează memoria contextuală folosind Qdrant pentru embeddings
"""

import os
from typing import Dict, List, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

# Qdrant connection
QDRANT_HOST = os.getenv("QDRANT_HOST", "127.0.0.1")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "user_memory"

# Embedding model
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")


class ContextMemory:
    """Manager pentru memoria contextuală cu embeddings"""
    
    def __init__(self):
        self.qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        
        # Asigură-te că colecția există
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Creează colecția dacă nu există"""
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if COLLECTION_NAME not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.embedding_model.get_sentence_embedding_dimension(),
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created Qdrant collection: {COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
    
    def store_interaction(self, user_id: str, message: str, response: str, action: Optional[str] = None):
        """Salvează o interacțiune cu embedding"""
        try:
            # Creează embedding pentru mesaj
            text_to_embed = f"{message} {response}"
            vector = self.embedding_model.encode(text_to_embed).tolist()
            
            # Creează ID unic
            from datetime import datetime
            point_id = f"{user_id}_{datetime.now().timestamp()}"
            
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "user_id": user_id,
                    "message": message,
                    "response": response,
                    "action": action,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            self.qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                wait=True,
                points=[point]
            )
            
            logger.debug(f"Stored interaction in Qdrant for user: {user_id}")
        except Exception as e:
            logger.error(f"Error storing interaction: {e}")
    
    def find_similar_intentions(self, user_id: str, message: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Găsește intenții similare din istoric"""
        try:
            # Creează embedding pentru mesajul curent
            vector = self.embedding_model.encode(message).tolist()
            
            # Caută în Qdrant
            results = self.qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=vector,
                query_filter={
                    "must": [{"key": "user_id", "match": {"value": user_id}}]
                },
                limit=limit
            )
            
            similar = []
            for result in results:
                similar.append({
                    "message": result.payload.get("message"),
                    "response": result.payload.get("response"),
                    "action": result.payload.get("action"),
                    "score": result.score
                })
            
            return similar
        except Exception as e:
            logger.error(f"Error finding similar intentions: {e}")
            return []
    
    def learn_patterns(self, user_id: str) -> Dict[str, Any]:
        """Învață patternuri din interacțiunile utilizatorului"""
        try:
            # Obține toate interacțiunile utilizatorului
            results = self.qdrant_client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter={
                    "must": [{"key": "user_id", "match": {"value": user_id}}]
                },
                limit=100
            )
            
            if not results[0]:
                return {}
            
            # Analizează patternuri
            actions = {}
            times = []
            
            for point in results[0]:
                payload = point.payload
                action = payload.get("action")
                if action:
                    actions[action] = actions.get(action, 0) + 1
                
                timestamp = payload.get("timestamp")
                if timestamp:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        times.append(dt.hour)
                    except:
                        pass
            
            # Calculează patternuri
            patterns = {
                "most_common_actions": dict(sorted(actions.items(), key=lambda x: x[1], reverse=True)[:5]),
                "preferred_hour": max(set(times), key=times.count) if times else None,
                "total_interactions": len(results[0])
            }
            
            logger.info(f"Learned patterns for user {user_id}: {patterns}")
            return patterns
        except Exception as e:
            logger.error(f"Error learning patterns: {e}")
            return {}


# Singleton instance
_context_memory_instance = None

def get_context_memory() -> ContextMemory:
    """Get singleton instance"""
    global _context_memory_instance
    if _context_memory_instance is None:
        _context_memory_instance = ContextMemory()
    return _context_memory_instance


