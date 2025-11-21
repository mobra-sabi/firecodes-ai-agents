"""
Learning Pipeline - Processes actions for learning and stores in Qdrant
"""
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import traceback

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("⚠️ Qdrant not available")

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class LearningPipeline:
    """
    Learning Pipeline that:
    1. Processes actions from MongoDB
    2. Generates embeddings using local LLM/GPU
    3. Stores embeddings in Qdrant
    4. Extracts patterns for Qwen learning
    """
    
    def __init__(self, mongo_client: MongoClient, qdrant_client=None, embedding_model=None):
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.qdrant = qdrant_client
        
        # Collections
        self.actions_collection = self.db["orchestrator_actions"]
        self.learning_collection = self.db["orchestrator_learning"]
        self.embeddings_collection = self.db["action_embeddings"]
        
        # Embedding model (local GPU)
        if embedding_model:
            self.embedding_model = embedding_model
        else:
            try:
                # Use local embedding model
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✅ Local embedding model loaded")
            except Exception as e:
                logger.warning(f"⚠️ Could not load embedding model: {e}")
                self.embedding_model = None
        
        # Qdrant collection name
        self.qdrant_collection = "action_embeddings"
        
        # Initialize Qdrant collection
        if self.qdrant and QDRANT_AVAILABLE:
            self._initialize_qdrant_collection()
        
        logger.info("✅ Learning Pipeline initialized")
    
    def _initialize_qdrant_collection(self):
        """Initialize Qdrant collection for action embeddings"""
        try:
            if not self.qdrant:
                return
            
            # Check if collection exists
            collections = self.qdrant.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.qdrant_collection not in collection_names:
                # Create collection
                self.qdrant.create_collection(
                    collection_name=self.qdrant_collection,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created Qdrant collection: {self.qdrant_collection}")
            else:
                logger.info(f"✅ Qdrant collection exists: {self.qdrant_collection}")
                
        except Exception as e:
            logger.error(f"❌ Error initializing Qdrant collection: {e}")
    
    def process_actions_batch(self, limit: int = 100):
        """
        Process a batch of unprocessed actions
        
        Args:
            limit: Maximum number of actions to process
        """
        try:
            # Find unprocessed actions
            unprocessed = list(
                self.actions_collection.find({
                    "processed": False,
                    "ready_for_learning": True
                }).limit(limit)
            )
            
            if not unprocessed:
                logger.debug("No unprocessed actions found")
                return 0
            
            processed_count = 0
            
            for action_doc in unprocessed:
                try:
                    self._process_single_action(action_doc)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"❌ Error processing action {action_doc.get('_id')}: {e}")
                    # Mark as processed to avoid infinite loop
                    self.actions_collection.update_one(
                        {"_id": action_doc["_id"]},
                        {"$set": {"processed": True, "processing_error": str(e)}}
                    )
            
            logger.info(f"✅ Processed {processed_count} actions")
            return processed_count
            
        except Exception as e:
            logger.error(f"❌ Error processing actions batch: {e}")
            logger.error(traceback.format_exc())
            return 0
    
    def _process_single_action(self, action_doc: Dict):
        """Process a single action for learning"""
        action_id = str(action_doc["_id"])
        
        # 1. Generate text representation
        action_text = self._action_to_text(action_doc)
        
        # 2. Generate embedding
        embedding = None
        if self.embedding_model:
            try:
                embedding = self.embedding_model.encode(action_text).tolist()
            except Exception as e:
                logger.error(f"❌ Error generating embedding: {e}")
        
        # 3. Store embedding in Qdrant
        if embedding and self.qdrant and QDRANT_AVAILABLE:
            try:
                point = PointStruct(
                    id=hash(action_id) % (2**63),  # Qdrant requires int64
                    vector=embedding,
                    payload={
                        "action_id": action_id,
                        "action_type": action_doc.get("action_type"),
                        "route": action_doc.get("route"),
                        "timestamp": action_doc.get("timestamp").isoformat() if action_doc.get("timestamp") else None,
                        "text": action_text
                    }
                )
                
                self.qdrant.upsert(
                    collection_name=self.qdrant_collection,
                    points=[point]
                )
                
                logger.debug(f"✅ Stored embedding in Qdrant for action {action_id}")
            except Exception as e:
                logger.error(f"❌ Error storing in Qdrant: {e}")
        
        # 4. Store learning data in MongoDB
        learning_doc = {
            "action_id": action_id,
            "action_text": action_text,
            "embedding_generated": embedding is not None,
            "embedding_dim": len(embedding) if embedding else 0,
            "processed_at": datetime.now(timezone.utc),
            "patterns": self._extract_learning_patterns(action_doc)
        }
        
        self.learning_collection.insert_one(learning_doc)
        
        # 5. Mark action as processed
        self.actions_collection.update_one(
            {"_id": action_doc["_id"]},
            {"$set": {
                "processed": True,
                "embedding_generated": embedding is not None,
                "processed_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.debug(f"✅ Processed action {action_id} for learning")
    
    def _action_to_text(self, action_doc: Dict) -> str:
        """Convert action to text for embedding"""
        parts = []
        
        # Basic info
        parts.append(f"Action: {action_doc.get('action_type', 'unknown')}")
        parts.append(f"Route: {action_doc.get('route', 'unknown')}")
        parts.append(f"Method: {action_doc.get('method', 'unknown')}")
        
        # Context
        if action_doc.get('agent_id'):
            parts.append(f"Agent: {action_doc['agent_id']}")
        if action_doc.get('user_id'):
            parts.append(f"User: {action_doc['user_id']}")
        
        # Request data
        if action_doc.get('request_data'):
            req = action_doc['request_data']
            if isinstance(req, dict):
                # Include meaningful fields
                for key in ['url', 'keyword', 'domain', 'name', 'title', 'query', 'search']:
                    if key in req:
                        value = str(req[key])
                        if len(value) < 200:  # Limit length
                            parts.append(f"{key}: {value}")
        
        # Response data
        if action_doc.get('response_data'):
            resp = action_doc['response_data']
            if isinstance(resp, dict):
                if 'status' in resp:
                    parts.append(f"Result: {resp['status']}")
                if 'message' in resp and len(str(resp['message'])) < 200:
                    parts.append(f"Message: {resp['message']}")
        
        # Status
        status = action_doc.get('status_code', 200)
        parts.append(f"Status: {'success' if status < 400 else 'error'}")
        
        # Duration
        duration = action_doc.get('duration_ms', 0)
        if duration > 0:
            parts.append(f"Duration: {duration:.0f}ms")
        
        return " | ".join(parts)
    
    def _extract_learning_patterns(self, action_doc: Dict) -> List[Dict]:
        """Extract patterns for Qwen learning"""
        patterns = []
        
        # Pattern: Success/Error
        status = action_doc.get('status_code', 200)
        patterns.append({
            "type": "outcome",
            "value": "success" if status < 400 else "error",
            "status_code": status
        })
        
        # Pattern: Performance
        duration = action_doc.get('duration_ms', 0)
        if duration > 0:
            patterns.append({
                "type": "performance",
                "duration_ms": duration,
                "category": "slow" if duration > 1000 else "fast"
            })
        
        # Pattern: Action type
        patterns.append({
            "type": "action_type",
            "value": action_doc.get('action_type', 'unknown')
        })
        
        return patterns
    
    def get_similar_actions(self, action_text: str, limit: int = 10) -> List[Dict]:
        """
        Find similar actions using Qdrant semantic search
        
        Args:
            action_text: Text to search for
            limit: Maximum number of results
        
        Returns:
            List of similar actions
        """
        if not self.embedding_model or not self.qdrant or not QDRANT_AVAILABLE:
            return []
        
        try:
            # Generate embedding for query
            query_embedding = self.embedding_model.encode(action_text).tolist()
            
            # Search in Qdrant
            results = self.qdrant.search(
                collection_name=self.qdrant_collection,
                query_vector=query_embedding,
                limit=limit
            )
            
            # Get action IDs from results
            action_ids = [r.payload.get("action_id") for r in results if r.payload.get("action_id")]
            
            # Fetch actions from MongoDB
            actions = list(
                self.actions_collection.find({
                    "_id": {"$in": [ObjectId(aid) for aid in action_ids if ObjectId.is_valid(aid)]}
                })
            )
            
            # Add similarity scores
            for action in actions:
                action_id = str(action["_id"])
                for result in results:
                    if result.payload.get("action_id") == action_id:
                        action["similarity_score"] = result.score
                        break
            
            return actions
            
        except Exception as e:
            logger.error(f"❌ Error finding similar actions: {e}")
            return []


# Global instance
_learning_pipeline_instance = None

def get_learning_pipeline(mongo_client: MongoClient = None, qdrant_client=None) -> LearningPipeline:
    """Get or create learning pipeline instance"""
    global _learning_pipeline_instance
    if _learning_pipeline_instance is None and mongo_client:
        _learning_pipeline_instance = LearningPipeline(mongo_client, qdrant_client)
    return _learning_pipeline_instance

