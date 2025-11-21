"""
Organization Graph Manager
Manages master-slave relationships and calculates similarities
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from pymongo import MongoClient
from bson import ObjectId
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

logger = logging.getLogger(__name__)


class OrgGraphManager:
    """Manages organization graph with master-slave relationships and similarities"""
    
    def __init__(self, mongo_client: MongoClient = None, qdrant_client: QdrantClient = None):
        if mongo_client is None:
            mongo_client = MongoClient("mongodb://localhost:27017/")
        if qdrant_client is None:
            qdrant_client = QdrantClient(host="localhost", port=9306)
        
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.graph_collection = self.db["org_graph"]
        self.qdrant = qdrant_client
        
        # Create indexes
        self.graph_collection.create_index([("master_agent_id", 1)])
        self.graph_collection.create_index([("slave_agent_id", 1)])
        self.graph_collection.create_index([("similarity_score", -1)])
    
    def add_relationship(
        self,
        master_agent_id: str,
        slave_agent_id: str,
        relationship_type: str = "competitor",
        metadata: Optional[Dict] = None
    ):
        """Add master-slave relationship"""
        # Check if relationship exists
        existing = self.graph_collection.find_one({
            "master_agent_id": master_agent_id,
            "slave_agent_id": slave_agent_id
        })
        
        if existing:
            # Update existing
            self.graph_collection.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "relationship_type": relationship_type,
                    "metadata": metadata or {},
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            logger.info(f"✅ Updated relationship: {master_agent_id} → {slave_agent_id}")
        else:
            # Create new
            relationship = {
                "master_agent_id": master_agent_id,
                "slave_agent_id": slave_agent_id,
                "relationship_type": relationship_type,
                "metadata": metadata or {},
                "similarity_score": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            self.graph_collection.insert_one(relationship)
            logger.info(f"✅ Added relationship: {master_agent_id} → {slave_agent_id}")
    
    def calculate_similarity(
        self,
        master_agent_id: str,
        slave_agent_id: str
    ) -> float:
        """
        Calculate similarity between master and slave using vector embeddings
        
        Returns:
            Similarity score (0-1)
        """
        try:
            # Get master agent
            master = self.db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
            slave = self.db.site_agents.find_one({"_id": ObjectId(slave_agent_id)})
            
            if not master or not slave:
                return 0.0
            
            master_domain = master.get("domain", "").replace(".", "_")
            slave_domain = slave.get("domain", "").replace(".", "_")
            
            master_collection = f"construction_{master_domain}"
            slave_collection = f"construction_{slave_domain}"
            
            # Get sample vectors from both collections
            try:
                master_points = self.qdrant.scroll(
                    collection_name=master_collection,
                    limit=10
                )[0]
                
                slave_points = self.qdrant.scroll(
                    collection_name=slave_collection,
                    limit=10
                )[0]
                
                if not master_points or not slave_points:
                    return 0.0
                
                # Calculate average similarity
                similarities = []
                for master_point in master_points[:5]:
                    for slave_point in slave_points[:5]:
                        if master_point.vector and slave_point.vector:
                            # Cosine similarity
                            dot_product = np.dot(master_point.vector, slave_point.vector)
                            norm_master = np.linalg.norm(master_point.vector)
                            norm_slave = np.linalg.norm(slave_point.vector)
                            
                            if norm_master > 0 and norm_slave > 0:
                                similarity = dot_product / (norm_master * norm_slave)
                                similarities.append(max(0, similarity))  # Clamp to 0-1
                
                avg_similarity = np.mean(similarities) if similarities else 0.0
                return float(avg_similarity)
            
            except Exception as e:
                logger.warning(f"⚠️ Error calculating vector similarity: {e}")
                # Fallback to keyword overlap
                return self._calculate_keyword_similarity(master_agent_id, slave_agent_id)
        
        except Exception as e:
            logger.error(f"❌ Error calculating similarity: {e}")
            return 0.0
    
    def _calculate_keyword_similarity(
        self,
        master_agent_id: str,
        slave_agent_id: str
    ) -> float:
        """Fallback: calculate similarity based on keyword overlap"""
        try:
            master_analysis = self.db.competitive_analysis.find_one({
                "agent_id": ObjectId(master_agent_id)
            })
            slave_analysis = self.db.competitive_analysis.find_one({
                "agent_id": ObjectId(slave_agent_id)
            })
            
            if not master_analysis or not slave_analysis:
                return 0.0
            
            master_keywords = set(
                master_analysis.get("analysis_data", {}).get("overall_keywords", [])
            )
            slave_keywords = set(
                slave_analysis.get("analysis_data", {}).get("overall_keywords", [])
            )
            
            if not master_keywords or not slave_keywords:
                return 0.0
            
            intersection = master_keywords & slave_keywords
            union = master_keywords | slave_keywords
            
            jaccard_similarity = len(intersection) / len(union) if union else 0.0
            return float(jaccard_similarity)
        
        except Exception as e:
            logger.error(f"❌ Error calculating keyword similarity: {e}")
            return 0.0
    
    def update_similarities(self, master_agent_id: str):
        """Update similarity scores for all slaves of a master"""
        relationships = list(self.graph_collection.find({
            "master_agent_id": master_agent_id
        }))
        
        for rel in relationships:
            slave_id = rel["slave_agent_id"]
            similarity = self.calculate_similarity(master_agent_id, slave_id)
            
            self.graph_collection.update_one(
                {"_id": rel["_id"]},
                {"$set": {
                    "similarity_score": similarity,
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
        
        logger.info(f"✅ Updated {len(relationships)} similarity scores for master {master_agent_id}")
    
    def get_master_graph(self, master_agent_id: str) -> Dict:
        """Get complete graph for a master agent"""
        relationships = list(self.graph_collection.find({
            "master_agent_id": master_agent_id
        }).sort("similarity_score", -1))
        
        nodes = [{"id": master_agent_id, "type": "master"}]
        edges = []
        
        for rel in relationships:
            slave_id = rel["slave_agent_id"]
            nodes.append({
                "id": slave_id,
                "type": "slave",
                "similarity": rel.get("similarity_score", 0),
                "relationship_type": rel.get("relationship_type", "competitor")
            })
            edges.append({
                "from": master_agent_id,
                "to": slave_id,
                "weight": rel.get("similarity_score", 0),
                "type": rel.get("relationship_type", "competitor")
            })
        
        return {
            "master_agent_id": master_agent_id,
            "nodes": nodes,
            "edges": edges,
            "total_slaves": len(relationships),
            "avg_similarity": np.mean([r.get("similarity_score", 0) for r in relationships]) if relationships else 0.0
        }
    
    def get_top_similar_slaves(self, master_agent_id: str, limit: int = 10) -> List[Dict]:
        """Get top similar slaves for a master"""
        relationships = list(self.graph_collection.find({
            "master_agent_id": master_agent_id
        }).sort("similarity_score", -1).limit(limit))
        
        result = []
        for rel in relationships:
            slave = self.db.site_agents.find_one({"_id": ObjectId(rel["slave_agent_id"])})
            if slave:
                result.append({
                    "slave_id": rel["slave_agent_id"],
                    "domain": slave.get("domain", "Unknown"),
                    "similarity_score": rel.get("similarity_score", 0),
                    "relationship_type": rel.get("relationship_type", "competitor")
                })
        
        return result
    
    def find_competitor_clusters(self, master_agent_id: str) -> List[Dict]:
        """Find clusters of similar competitors"""
        relationships = list(self.graph_collection.find({
            "master_agent_id": master_agent_id,
            "similarity_score": {"$gte": 0.5}  # High similarity threshold
        }).sort("similarity_score", -1))
        
        # Simple clustering: group by similarity ranges
        clusters = {
            "high": [],  # 0.8-1.0
            "medium": [],  # 0.5-0.8
            "low": []  # <0.5
        }
        
        for rel in relationships:
            score = rel.get("similarity_score", 0)
            if score >= 0.8:
                clusters["high"].append(rel)
            elif score >= 0.5:
                clusters["medium"].append(rel)
            else:
                clusters["low"].append(rel)
        
        return [
            {"cluster": "high", "count": len(clusters["high"]), "similarity_range": "0.8-1.0"},
            {"cluster": "medium", "count": len(clusters["medium"]), "similarity_range": "0.5-0.8"},
            {"cluster": "low", "count": len(clusters["low"]), "similarity_range": "<0.5"}
        ]

