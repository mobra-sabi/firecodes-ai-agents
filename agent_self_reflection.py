"""
Agent Self Reflection - Agentul se întreabă ce s-a schimbat
Oferă conștiință de TIMP și de STARE
"""

import os
import logging
import json
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ai_agents_db")


class AgentSelfReflection:
    """Gestionează auto-reflecția agentului folosind DeepSeek"""
    
    def __init__(self):
        self.mongo = MongoClient(MONGODB_URI)
        self.db = self.mongo[MONGODB_DATABASE]
        self.reflection_collection = self.db.agent_self_reflections
        self.site_agents_collection = self.db.site_agents
        self.serp_results_collection = self.db.serp_results
        self.state_memory = None  # Va fi injectat
    
    def set_state_memory(self, state_memory):
        """Injectează AgentStateMemory pentru acces la stare"""
        self.state_memory = state_memory
    
    def build_reflection_prompt(self, agent_id: str, agent_data: Dict, recent_data: Dict) -> str:
        """Construiește prompt-ul pentru auto-reflecție"""
        
        prompt = f"""Ești agentul AI pentru site-ul {agent_data.get('site_name', 'unknown')} ({agent_data.get('site_url', 'unknown')}).

CONTEXTUL TĂU:
- Industrie: {agent_data.get('industry', 'unknown')}
- Competitori principali: {', '.join(agent_data.get('competitors', [])[:5])}
- Keywords monitorizate: {len(agent_data.get('keywords', []))}
- Ultima actualizare: {agent_data.get('updated_at', 'unknown')}

DATE RECENTE (ultimele 12-24h):
{json.dumps(recent_data, indent=2, ensure_ascii=False, default=str)}

ÎNTREBĂRI PENTRU AUTO-REFLECȚIE:

1. **Ce s-a schimbat în industrie?**
   - Au apărut competitori noi?
   - Există tendințe noi în piață?
   - Ce pattern-uri observi?

2. **Ce s-a schimbat la mine?**
   - Cum s-a schimbat ranking-ul meu?
   - Ce keywords au evoluat pozitiv/negativ?
   - Există anomalii sau schimbări bruște?

3. **Ce ar trebui să fac?**
   - Care sunt acțiunile cele mai urgente?
   - Ce oportunități văd?
   - Ce riscuri trebuie să monitorizez?

4. **Cum este progresul meu?**
   - Sunt pe drumul corect către obiective?
   - Ce mă limitează?
   - Ce date nu am încă?

5. **Ce observări importante am?**
   - Pattern-uri interesante
   - Anomalii de investigat
   - Recomandări strategice

Răspunde structurat, concis și acționabil. Fii obiectiv și analitic.
"""
        return prompt
    
    def perform_reflection(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Efectuează auto-reflecție pentru agent
        
        Returnează:
        {
            "reflection": "...",
            "insights": [...],
            "recommendations": [...],
            "concerns": [...],
            "opportunities": [...]
        }
        """
        try:
            # Obține datele agentului
            agent = self.site_agents_collection.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                logger.error(f"Agent {agent_id} not found")
                return None
            
            agent_id_str = str(agent_id)
            
            # Obține date recente
            recent_serp = list(self.serp_results_collection.find({
                "agent_id": agent_id_str,
                "check_date": {"$gte": datetime.now(timezone.utc) - timedelta(hours=24)}
            }).sort("check_date", -1).limit(50))
            
            # Obține starea curentă
            current_state = None
            if self.state_memory:
                current_state = self.state_memory.get_state(agent_id_str)
            
            recent_data = {
                "serp_results_count": len(recent_serp),
                "recent_positions": [r.get("position") for r in recent_serp[:10] if r.get("position")],
                "current_state": current_state,
                "recent_changes": self.state_memory.get_recent_changes(agent_id_str, hours=24) if self.state_memory else []
            }
            
            # Construiește prompt-ul
            prompt = self.build_reflection_prompt(agent_id_str, agent, recent_data)
            
            # Apelează DeepSeek
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ești un agent AI care efectuează auto-reflecție. Analizezi datele tale, identifici pattern-uri, și oferi insights acționabile. Fii obiectiv, analitic și strategic."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            reflection_text = result["choices"][0]["message"]["content"]
            
            # Parsează răspunsul pentru a extrage insights structurate
            reflection_data = {
                "agent_id": agent_id_str,
                "reflection": reflection_text,
                "insights": self._extract_insights(reflection_text),
                "recommendations": self._extract_recommendations(reflection_text),
                "concerns": self._extract_concerns(reflection_text),
                "opportunities": self._extract_opportunities(reflection_text),
                "reflected_at": datetime.now(timezone.utc)
            }
            
            # Salvează reflecția
            self.reflection_collection.insert_one(reflection_data)
            
            # Adaugă notițe de conștiință
            if self.state_memory:
                for insight in reflection_data["insights"][:3]:  # Primele 3 insights
                    self.state_memory.add_awareness_note(
                        agent_id_str,
                        insight,
                        category="self_reflection"
                    )
            
            return reflection_data
            
        except Exception as e:
            logger.error(f"Error performing reflection for agent {agent_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_insights(self, text: str) -> List[str]:
        """Extrage insights din text"""
        insights = []
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['observ', 'descoper', 'identific', 'pattern', 'tendință']):
                insights.append(line.strip())
        return insights[:5]  # Maxim 5 insights
    
    def _extract_recommendations(self, text: str) -> List[str]:
        """Extrage recomandări din text"""
        recommendations = []
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['recomand', 'ar trebui', 'sugerez', 'acțiune']):
                recommendations.append(line.strip())
        return recommendations[:5]
    
    def _extract_concerns(self, text: str) -> List[str]:
        """Extrage preocupări din text"""
        concerns = []
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['preocup', 'risc', 'problema', 'scădere', 'anomalie']):
                concerns.append(line.strip())
        return concerns[:5]
    
    def _extract_opportunities(self, text: str) -> List[str]:
        """Extrage oportunități din text"""
        opportunities = []
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['oportunitate', 'potențial', 'creștere', 'îmbunătățire']):
                opportunities.append(line.strip())
        return opportunities[:5]
    
    def get_latest_reflection(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Obține ultima reflecție"""
        try:
            reflection = self.reflection_collection.find_one(
                {"agent_id": str(agent_id)},
                sort=[("reflected_at", -1)]
            )
            if reflection:
                reflection["_id"] = str(reflection["_id"])
            return reflection
        except Exception as e:
            logger.error(f"Error getting latest reflection for agent {agent_id}: {e}")
            return None
    
    def get_reflection_history(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Obține istoricul reflecțiilor"""
        try:
            reflections = list(self.reflection_collection.find(
                {"agent_id": str(agent_id)}
            ).sort("reflected_at", -1).limit(limit))
            
            for reflection in reflections:
                reflection["_id"] = str(reflection["_id"])
            
            return reflections
        except Exception as e:
            logger.error(f"Error getting reflection history for agent {agent_id}: {e}")
            return []

