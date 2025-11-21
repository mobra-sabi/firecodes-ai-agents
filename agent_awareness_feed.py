"""
Agent Awareness Feed - Log continuu de învățare
Oferă conștiință de TIMP și pattern-uri
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ai_agents_db")


class AgentAwarenessFeed:
    """Gestionează feed-ul de conștiință pentru fiecare agent"""
    
    def __init__(self):
        self.mongo = MongoClient(MONGODB_URI)
        self.db = self.mongo[MONGODB_DATABASE]
        self.feed_collection = self.db.agent_awareness_feed
        self.serp_results_collection = self.db.serp_results
        self.site_agents_collection = self.db.site_agents
    
    def add_discovery(self, agent_id: str, discovery: str, category: str = "general", metadata: Optional[Dict] = None) -> bool:
        """
        Adaugă o descoperire în feed
        
        Args:
            agent_id: ID-ul agentului
            discovery: Descrierea descoperirii
            category: Categoria (competitor, pattern, anomaly, trend, etc.)
            metadata: Metadata suplimentară
        """
        try:
            feed_entry = {
                "agent_id": str(agent_id),
                "discovery": discovery,
                "category": category,
                "metadata": metadata or {},
                "discovered_at": datetime.now(timezone.utc),
                "importance": self._calculate_importance(discovery, category)
            }
            
            self.feed_collection.insert_one(feed_entry)
            
            logger.info(f"Discovery added to feed for agent {agent_id}: {discovery[:50]}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding discovery to feed for agent {agent_id}: {e}")
            return False
    
    def _calculate_importance(self, discovery: str, category: str) -> str:
        """Calculează importanța descoperirii"""
        importance_keywords = {
            "high": ["scădere bruscă", "competitor nou", "anomalie", "risc", "oportunitate majoră"],
            "medium": ["schimbare", "tendință", "pattern", "evoluție"],
            "low": ["observație", "notă", "informație"]
        }
        
        discovery_lower = discovery.lower()
        
        for level, keywords in importance_keywords.items():
            if any(keyword in discovery_lower for keyword in keywords):
                return level
        
        return "low"
    
    def detect_new_competitors(self, agent_id: str) -> List[Dict[str, Any]]:
        """Detectează competitori noi în rezultatele SERP"""
        try:
            # Obține ultimele rezultate SERP
            recent_serp = list(self.serp_results_collection.find({
                "agent_id": str(agent_id),
                "check_date": {"$gte": datetime.now(timezone.utc) - timedelta(days=7)}
            }).sort("check_date", -1).limit(200))
            
            if not recent_serp:
                return []
            
            # Obține competitorii cunoscuți
            agent = self.site_agents_collection.find_one({"_id": ObjectId(agent_id)})
            known_competitors = set(agent.get("competitors", []) if agent else [])
            
            # Extrage domenii noi din rezultate
            new_domains = set()
            for result in recent_serp:
                url = result.get("url", "")
                if url:
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc
                        if domain and domain not in known_competitors:
                            new_domains.add(domain)
                    except:
                        pass
            
            discoveries = []
            for domain in new_domains:
                discovery = f"Competitor nou detectat: {domain}"
                self.add_discovery(
                    agent_id,
                    discovery,
                    category="competitor",
                    metadata={"domain": domain, "first_seen": datetime.now(timezone.utc)}
                )
                discoveries.append({
                    "domain": domain,
                    "discovery": discovery,
                    "discovered_at": datetime.now(timezone.utc)
                })
            
            return discoveries
            
        except Exception as e:
            logger.error(f"Error detecting new competitors for agent {agent_id}: {e}")
            return []
    
    def detect_patterns(self, agent_id: str) -> List[Dict[str, Any]]:
        """Detectează pattern-uri în date"""
        try:
            recent_serp = list(self.serp_results_collection.find({
                "agent_id": str(agent_id),
                "check_date": {"$gte": datetime.now(timezone.utc) - timedelta(days=30)}
            }).sort("check_date", -1).limit(500))
            
            if not recent_serp:
                return []
            
            patterns = []
            
            # Pattern: Keywords care cresc constant
            keyword_trends = {}
            for result in recent_serp:
                keyword = result.get("keyword", "")
                position = result.get("position", 0)
                if keyword and position:
                    if keyword not in keyword_trends:
                        keyword_trends[keyword] = []
                    keyword_trends[keyword].append({
                        "position": position,
                        "date": result.get("check_date")
                    })
            
            for keyword, positions in keyword_trends.items():
                if len(positions) >= 5:
                    recent_avg = sum([p["position"] for p in positions[:5]]) / 5
                    older_avg = sum([p["position"] for p in positions[5:10]]) / 5 if len(positions) >= 10 else recent_avg
                    
                    if older_avg > recent_avg and (older_avg - recent_avg) > 5:
                        pattern = f"Keyword '{keyword}' în creștere constantă: {older_avg:.1f} → {recent_avg:.1f}"
                        self.add_discovery(agent_id, pattern, category="pattern", metadata={"keyword": keyword})
                        patterns.append({"pattern": pattern, "keyword": keyword})
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting patterns for agent {agent_id}: {e}")
            return []
    
    def detect_anomalies(self, agent_id: str) -> List[Dict[str, Any]]:
        """Detectează anomalii în date"""
        try:
            recent_serp = list(self.serp_results_collection.find({
                "agent_id": str(agent_id),
                "check_date": {"$gte": datetime.now(timezone.utc) - timedelta(days=7)}
            }).sort("check_date", -1).limit(100))
            
            if not recent_serp:
                return []
            
            anomalies = []
            
            # Anomalie: Scădere bruscă în ranking
            for i in range(1, len(recent_serp)):
                current = recent_serp[i-1]
                previous = recent_serp[i]
                
                current_pos = current.get("position", 0)
                previous_pos = previous.get("position", 0)
                
                if current_pos > 0 and previous_pos > 0:
                    drop = current_pos - previous_pos
                    if drop > 10:  # Scădere de peste 10 poziții
                        anomaly = f"Scădere bruscă detectată: {previous_pos} → {current_pos} pentru keyword '{current.get('keyword', 'unknown')}'"
                        self.add_discovery(
                            agent_id,
                            anomaly,
                            category="anomaly",
                            metadata={
                                "keyword": current.get("keyword"),
                                "drop": drop,
                                "from": previous_pos,
                                "to": current_pos
                            }
                        )
                        anomalies.append({"anomaly": anomaly, "drop": drop})
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies for agent {agent_id}: {e}")
            return []
    
    def get_feed(self, agent_id: str, hours: int = 24, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obține feed-ul pentru un agent"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            query = {
                "agent_id": str(agent_id),
                "discovered_at": {"$gte": cutoff_time}
            }
            
            if category:
                query["category"] = category
            
            feed = list(self.feed_collection.find(query).sort("discovered_at", -1).limit(100))
            
            for entry in feed:
                entry["_id"] = str(entry["_id"])
            
            return feed
            
        except Exception as e:
            logger.error(f"Error getting feed for agent {agent_id}: {e}")
            return []
    
    def get_summary(self, agent_id: str, days: int = 7) -> Dict[str, Any]:
        """Obține un rezumat al feed-ului"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            feed = list(self.feed_collection.find({
                "agent_id": str(agent_id),
                "discovered_at": {"$gte": cutoff_time}
            }))
            
            summary = {
                "total_discoveries": len(feed),
                "by_category": {},
                "by_importance": {"high": 0, "medium": 0, "low": 0},
                "recent_discoveries": []
            }
            
            for entry in feed:
                category = entry.get("category", "unknown")
                summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
                
                importance = entry.get("importance", "low")
                summary["by_importance"][importance] = summary["by_importance"].get(importance, 0) + 1
            
            # Primele 10 descoperiri recente
            summary["recent_discoveries"] = [
                {
                    "discovery": e.get("discovery", ""),
                    "category": e.get("category", ""),
                    "importance": e.get("importance", ""),
                    "discovered_at": e.get("discovered_at")
                }
                for e in sorted(feed, key=lambda x: x.get("discovered_at", datetime.min), reverse=True)[:10]
            ]
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting feed summary for agent {agent_id}: {e}")
            return {}

