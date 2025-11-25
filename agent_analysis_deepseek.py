#!/usr/bin/env python3
"""
Analiză DeepSeek pentru agenți - Descompunere în subdomenii + Generare keywords
Execută la comandă analiza DeepSeek pentru un agent
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import requests

logger = logging.getLogger(__name__)

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# Fallback: Verifică și în alte locații
if not DEEPSEEK_API_KEY:
    try:
        with open("/srv/hf/ai_agents/.env", "r") as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY="):
                    DEEPSEEK_API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except:
        pass

class AgentAnalysisDeepSeek:
    """Analiză DeepSeek pentru descompunerea în subdomenii și generarea keywords"""
    
    def __init__(self):
        # Folosește configurația corectă din .env sau database_config
        from config.database_config import MONGODB_URI, MONGODB_DATABASE
        mongo_uri = os.getenv("MONGODB_URI", MONGODB_URI)
        db_name = os.getenv("MONGODB_DATABASE", MONGODB_DATABASE)
        
        self.mongo = MongoClient(mongo_uri)
        self.db = self.mongo[db_name]
        # Folosește agents (colecția principală folosită de API)
        # site_agents este pentru backup/legacy, dar API-ul folosește agents
        self.agents_collection = self.db.agents
    
    def get_agent_content_summary(self, agent_id: str) -> str:
        """Obține un rezumat al conținutului agentului din Qdrant"""
        try:
            from qdrant_client import QdrantClient
            qdrant = QdrantClient(url="http://localhost:9306")
            
            agent = self.agents_collection.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return ""
            
            domain = agent.get("domain", "").replace(".", "_").replace("-", "_")
            collection_name = f"construction_{domain}"
            
            # Extrage primele 20 de chunks pentru rezumat
            try:
                results = qdrant.scroll(
                    collection_name=collection_name,
                    limit=20,
                    with_payload=True
                )
                
                if results[0]:
                    chunks_text = []
                    for point in results[0]:
                        payload = point.payload
                        chunk_text = payload.get("chunk_text") or payload.get("text") or payload.get("content", "")
                        if chunk_text:
                            chunks_text.append(chunk_text[:300])  # Primele 300 caractere
                    
                    return "\n\n".join(chunks_text[:10])  # Primele 10 chunks
            except:
                pass
            
            return ""
        except Exception as e:
            logger.debug(f"Could not get content summary: {e}")
            return ""
    
    def analyze_subdomains_and_keywords(self, agent_id: str) -> Dict:
        """
        Analizează agentul cu DeepSeek pentru a găsi subdomenii și keywords
        
        Returns:
            {
                "ok": True,
                "subdomains": [
                    {
                        "name": "nume-subdomeniu",
                        "description": "descriere subdomeniu",
                        "keywords": ["keyword1", "keyword2", ...],
                        "suggested_keywords": ["sugestie1", "sugestie2", ...]
                    }
                ],
                "overall_keywords": ["keyword1", "keyword2", ...]
            }
        """
        try:
            agent = self.agents_collection.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return {"ok": False, "error": "Agent not found"}
            
            domain = agent.get("domain", "")
            site_url = agent.get("site_url", "")
            industry = agent.get("industry", "")
            
            # Obține rezumat conținut
            content_summary = self.get_agent_content_summary(agent_id)
            
            # Construiește prompt pentru DeepSeek
            prompt = f"""Analizează site-ul {domain} ({site_url}) și identifică:

1. SUBDOMENII PRINCIPALE:
   Pentru fiecare subdomeniu, identifică:
   - Numele subdomeniului (ex: "servicii", "produse", "despre", "contact")
   - Descrierea subdomeniului (ce conține, ce scop are)
   - 10-15 keywords relevante pentru acel subdomeniu
   - 5-10 sugestii de keywords suplimentare

2. KEYWORDS GENERALE:
   Identifică 20-30 keywords generale relevante pentru întregul site

Format răspuns JSON:
{{
  "subdomains": [
    {{
      "name": "nume-subdomeniu",
      "description": "descriere detaliată",
      "keywords": ["keyword1", "keyword2", ...],
      "suggested_keywords": ["sugestie1", "sugestie2", ...]
    }}
  ],
  "overall_keywords": ["keyword1", "keyword2", ...]
}}

Conținut site (rezumat):
{content_summary[:2000] if content_summary else "Nu există conținut disponibil"}

Industrie: {industry if industry else "Nespecificată"}
"""
            
            # Verifică dacă API key-ul este setat
            if not DEEPSEEK_API_KEY:
                return {"ok": False, "error": "DEEPSEEK_API_KEY nu este setat. Verifică .env file."}
            
            # Apelează DeepSeek
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ești un expert în SEO și analiză de site-uri web. Analizezi site-uri și identifici subdomenii și keywords relevante. Răspunde întotdeauna în format JSON valid."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 4000
            }
            
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                assistant_message = data["choices"][0]["message"]["content"]
                
                # Extrage JSON din răspuns
                import json
                import re
                
                # Caută JSON în răspuns
                json_match = re.search(r'\{.*\}', assistant_message, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        analysis_result = json.loads(json_str)
                        
                        # Normalizează subdomeniile (asigură că sunt dicționare)
                        normalized_subdomains = []
                        for subdomain in analysis_result.get("subdomains", []):
                            if isinstance(subdomain, dict):
                                normalized_subdomains.append({
                                    "name": subdomain.get("name", ""),
                                    "description": subdomain.get("description", ""),
                                    "keywords": subdomain.get("keywords", []),
                                    "suggested_keywords": subdomain.get("suggested_keywords", [])
                                })
                            else:
                                # Dacă e string, convertește în dicționar
                                normalized_subdomains.append({
                                    "name": str(subdomain),
                                    "description": "",
                                    "keywords": [],
                                    "suggested_keywords": []
                                })
                        
                        # Salvează în MongoDB
                        self.agents_collection.update_one(
                            {"_id": ObjectId(agent_id)},
                            {
                                "$set": {
                                    "subdomains": normalized_subdomains,
                                    "overall_keywords": analysis_result.get("overall_keywords", []),
                                    "analysis_date": datetime.now(timezone.utc),
                                    "analysis_status": "completed"
                                }
                            }
                        )
                        
                        return {
                            "ok": True,
                            "subdomains": normalized_subdomains,
                            "overall_keywords": analysis_result.get("overall_keywords", []),
                            "message": "Analysis completed successfully"
                        }
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        return {"ok": False, "error": f"Invalid JSON response: {e}"}
                else:
                    return {"ok": False, "error": "No JSON found in response"}
            elif response.status_code == 401:
                logger.error(f"DeepSeek API authentication error: {response.text}")
                return {"ok": False, "error": f"DeepSeek API authentication failed (401). Verifică DEEPSEEK_API_KEY în .env file."}
            else:
                logger.error(f"DeepSeek API error {response.status_code}: {response.text}")
                return {"ok": False, "error": f"DeepSeek API error: {response.status_code} - {response.text[:200]}"}
                
        except Exception as e:
            logger.error(f"Error in analysis: {e}")
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
    
    def suggest_keywords_for_subdomain(self, agent_id: str, subdomain_name: str, current_keywords: List[str]) -> Dict:
        """
        Sugerează keywords noi pentru un subdomeniu
        
        Returns:
            {
                "ok": True,
                "suggested_keywords": ["keyword1", "keyword2", ...]
            }
        """
        try:
            agent = self.agents_collection.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return {"ok": False, "error": "Agent not found"}
            
            domain = agent.get("domain", "")
            
            prompt = f"""Site: {domain}
Subdomeniu: {subdomain_name}
Keywords existente: {', '.join(current_keywords[:10])}

Sugerează 10 keywords noi relevante pentru acest subdomeniu, care să fie diferite de cele existente.
Răspunde doar cu o listă de keywords, separate prin virgulă."""
            
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 500
            }
            
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                suggestions_text = data["choices"][0]["message"]["content"]
                
                # Extrage keywords din răspuns
                keywords = [kw.strip() for kw in suggestions_text.replace("\n", ",").split(",") if kw.strip()]
                
                return {
                    "ok": True,
                    "suggested_keywords": keywords[:10]
                }
            else:
                return {"ok": False, "error": f"DeepSeek API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error suggesting keywords: {e}")
            return {"ok": False, "error": str(e)}

