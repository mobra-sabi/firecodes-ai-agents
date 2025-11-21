"""
Agent Health Score - Calculează scoruri de sănătate pentru fiecare agent
Oferă conștiință de OBIECTIV și de STARE
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ai_agents_db")


class AgentHealthScore:
    """Calculează și gestionează scorurile de sănătate pentru agenți"""
    
    def __init__(self):
        self.mongo = MongoClient(MONGODB_URI)
        self.db = self.mongo[MONGODB_DATABASE]
        self.health_collection = self.db.agent_health_scores
        self.site_agents_collection = self.db.site_agents
        self.serp_results_collection = self.db.serp_results
    
    def calculate_seo_health(self, agent_id: str) -> float:
        """
        Calculează scorul de sănătate SEO (0-100)
        
        Factori:
        - Poziția medie în Google (mai bine = mai mare scor)
        - Numărul de keywords monitorizate
        - Tendința de evoluție (îmbunătățire/scădere)
        - Acoperirea geografică
        """
        try:
            # Obține ultimele rezultate SERP
            recent_serp = list(self.serp_results_collection.find({
                "agent_id": agent_id,
                "check_date": {"$gte": datetime.now(timezone.utc) - timedelta(days=7)}
            }).sort("check_date", -1).limit(100))
            
            if not recent_serp:
                return 50.0  # Scor neutru dacă nu există date
            
            # Calculează poziția medie
            positions = []
            for result in recent_serp:
                if "position" in result and result["position"]:
                    positions.append(result["position"])
            
            if not positions:
                return 50.0
            
            avg_position = sum(positions) / len(positions)
            
            # Convertim poziția în scor (poziția 1 = 100, poziția 10 = 50, poziția 50+ = 0)
            if avg_position <= 1:
                seo_score = 100.0
            elif avg_position <= 3:
                seo_score = 90.0 - (avg_position - 1) * 10
            elif avg_position <= 10:
                seo_score = 80.0 - (avg_position - 3) * 5
            elif avg_position <= 20:
                seo_score = 50.0 - (avg_position - 10) * 2
            else:
                seo_score = max(0.0, 30.0 - (avg_position - 20) * 1)
            
            # Bonus pentru numărul de keywords monitorizate
            keyword_count = len(set([r.get("keyword", "") for r in recent_serp if r.get("keyword")]))
            if keyword_count > 20:
                seo_score = min(100.0, seo_score + 10.0)
            elif keyword_count > 10:
                seo_score = min(100.0, seo_score + 5.0)
            
            return round(seo_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating SEO health for agent {agent_id}: {e}")
            return 50.0
    
    def calculate_ads_health(self, agent_id: str) -> float:
        """
        Calculează scorul de sănătate Google Ads (0-100)
        
        Factori:
        - Prezența campaniilor active
        - Performanța campaniilor
        - Bugetul alocat
        """
        try:
            # Verifică dacă agentul are campanii Google Ads
            agent = self.site_agents_collection.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return 0.0
            
            # TODO: Integrare cu Google Ads API pentru date reale
            # Pentru moment, returnăm un scor bazat pe date disponibile
            ads_data = agent.get("google_ads", {})
            
            if not ads_data:
                return 0.0
            
            # Scor bazat pe prezența datelor
            score = 50.0
            
            if ads_data.get("campaigns_active", 0) > 0:
                score += 30.0
            
            if ads_data.get("budget", 0) > 0:
                score += 20.0
            
            return min(100.0, round(score, 2))
            
        except Exception as e:
            logger.error(f"Error calculating Ads health for agent {agent_id}: {e}")
            return 0.0
    
    def calculate_opportunity_level(self, agent_id: str) -> float:
        """
        Calculează nivelul de oportunitate (0-100)
        
        Factori:
        - Keywords cu potențial de creștere
        - Competitori slabi
        - Tendințe pozitive
        """
        try:
            # Obține date despre competitori
            recent_serp = list(self.serp_results_collection.find({
                "agent_id": agent_id,
                "check_date": {"$gte": datetime.now(timezone.utc) - timedelta(days=30)}
            }).sort("check_date", -1).limit(200))
            
            if not recent_serp:
                return 50.0
            
            opportunity_score = 50.0
            
            # Analizează keywords cu poziții 11-20 (potențial de creștere)
            keywords_potential = []
            for result in recent_serp:
                position = result.get("position", 0)
                if 11 <= position <= 20:
                    keywords_potential.append(result)
            
            if len(keywords_potential) > 10:
                opportunity_score += 20.0
            elif len(keywords_potential) > 5:
                opportunity_score += 10.0
            
            # Analizează tendințe pozitive
            recent_positions = [r.get("position", 0) for r in recent_serp[:50] if r.get("position")]
            older_positions = [r.get("position", 0) for r in recent_serp[50:100] if r.get("position")]
            
            if recent_positions and older_positions:
                recent_avg = sum(recent_positions) / len(recent_positions)
                older_avg = sum(older_positions) / len(older_positions)
                
                if recent_avg < older_avg:  # Îmbunătățire
                    improvement = (older_avg - recent_avg) / older_avg * 100
                    opportunity_score += min(30.0, improvement)
            
            return min(100.0, round(opportunity_score, 2))
            
        except Exception as e:
            logger.error(f"Error calculating opportunity level for agent {agent_id}: {e}")
            return 50.0
    
    def calculate_risk_level(self, agent_id: str) -> float:
        """
        Calculează nivelul de risc (0-100)
        
        Factori:
        - Scăderi bruște în ranking
        - Competitori noi puternici
        - Tendințe negative
        """
        try:
            recent_serp = list(self.serp_results_collection.find({
                "agent_id": agent_id,
                "check_date": {"$gte": datetime.now(timezone.utc) - timedelta(days=30)}
            }).sort("check_date", -1).limit(200))
            
            if not recent_serp:
                return 0.0
            
            risk_score = 0.0
            
            # Analizează scăderi în ranking
            recent_positions = [r.get("position", 0) for r in recent_serp[:50] if r.get("position")]
            older_positions = [r.get("position", 0) for r in recent_serp[50:100] if r.get("position")]
            
            if recent_positions and older_positions:
                recent_avg = sum(recent_positions) / len(recent_positions)
                older_avg = sum(older_positions) / len(older_positions)
                
                if recent_avg > older_avg:  # Scădere
                    decline = (recent_avg - older_avg) / older_avg * 100
                    risk_score += min(50.0, decline)
            
            # Verifică keywords care au scăzut mult
            significant_drops = 0
            for result in recent_serp[:100]:
                position = result.get("position", 0)
                if position > 20:  # Scăzut peste poziția 20
                    significant_drops += 1
            
            if significant_drops > 20:
                risk_score += 30.0
            elif significant_drops > 10:
                risk_score += 15.0
            
            return min(100.0, round(risk_score, 2))
            
        except Exception as e:
            logger.error(f"Error calculating risk level for agent {agent_id}: {e}")
            return 0.0
    
    def calculate_all_scores(self, agent_id: str) -> Dict[str, float]:
        """Calculează toate scorurile pentru un agent"""
        return {
            "seo_health": self.calculate_seo_health(agent_id),
            "ads_health": self.calculate_ads_health(agent_id),
            "opportunity_level": self.calculate_opportunity_level(agent_id),
            "risk_level": self.calculate_risk_level(agent_id),
            "calculated_at": datetime.now(timezone.utc)
        }
    
    def save_health_scores(self, agent_id: str, scores: Dict[str, float]) -> bool:
        """Salvează scorurile de sănătate"""
        try:
            self.health_collection.update_one(
                {"agent_id": agent_id},
                {
                    "$set": {
                        "agent_id": agent_id,
                        **scores,
                        "last_update": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving health scores for agent {agent_id}: {e}")
            return False
    
    def get_health_scores(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Obține scorurile de sănătate"""
        try:
            scores = self.health_collection.find_one({"agent_id": agent_id})
            if scores:
                scores["_id"] = str(scores["_id"])
            return scores
        except Exception as e:
            logger.error(f"Error getting health scores for agent {agent_id}: {e}")
            return None

