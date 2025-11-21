#!/usr/bin/env python3
"""
Chat DeepSeek pentru agenți - Conectat la Qdrant și MongoDB
Chat-ul se identifică cu agentul și știe tot despre site și business
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from qdrant_client import QdrantClient
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# Fallback: Verifică și în alte locații
if not DEEPSEEK_API_KEY:
    # Încearcă să citească din fișier
    try:
        with open("/srv/hf/ai_agents/.env", "r") as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY="):
                    DEEPSEEK_API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except:
        pass

class AgentChatDeepSeek:
    """Chat DeepSeek conectat la toate informațiile agentului"""
    
    def __init__(self, qdrant_url: str = "http://localhost:9306"):
        self.mongo = MongoClient("mongodb://localhost:27018")
        self.db = self.mongo["ai_agents_db"]
        # Folosește site_agents dacă există, altfel agents
        if "site_agents" in self.db.list_collection_names() and self.db.site_agents.count_documents({}) > 0:
            self.agents_collection = self.db.site_agents
        else:
            self.agents_collection = self.db.agents
        
        # Qdrant pentru context
        try:
            self.qdrant = QdrantClient(url=qdrant_url)
        except Exception as e:
            logger.warning(f"Could not initialize Qdrant client: {e}")
            self.qdrant = None
        
        # Embeddings model pentru search semantic
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            self.embedding_model = SentenceTransformer(
                'sentence-transformers/all-MiniLM-L6-v2',
                device=self.device
            )
            logger.info(f"Embedding model loaded on {self.device}")
        except Exception as e:
            logger.warning(f"Could not load embedding model: {e}")
            self.embedding_model = None
    
    def get_agent_identity(self, agent_id: str) -> Dict:
        """Obține identitatea completă a agentului"""
        try:
            agent = self.agents_collection.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return None
            
            # Extrage toate informațiile relevante
            identity = {
                "domain": agent.get("domain", ""),
                "site_url": agent.get("site_url", ""),
                "industry": agent.get("industry", ""),
                "name": agent.get("name", "Site Agent"),
                "keywords": agent.get("keywords", []),
                "overall_keywords": agent.get("overall_keywords", []),
                "subdomains": agent.get("subdomains", []),
                "chunks_indexed": agent.get("chunks_indexed", 0),
                "pages_indexed": agent.get("pages_indexed", 0),
            }
            
            # Verifică dacă există deepseek_identity în site_agents (dacă nu e deja din site_agents)
            if self.agents_collection.name != "site_agents":
                site_agent = self.db.site_agents.find_one({"domain": identity["domain"]})
                if site_agent:
                    identity["deepseek_identity"] = site_agent.get("deepseek_identity", "")
                    identity["competitive_positioning"] = site_agent.get("competitive_positioning", "")
                    identity["target_market"] = site_agent.get("target_market", "")
            else:
                # Dacă folosim deja site_agents, datele sunt deja în agent
                identity["deepseek_identity"] = agent.get("deepseek_identity", "")
                identity["competitive_positioning"] = agent.get("competitive_positioning", "")
                identity["target_market"] = agent.get("target_market", "")
            
            return identity
        except Exception as e:
            logger.error(f"Error getting agent identity: {e}")
            return None
    
    def get_context_from_qdrant(self, agent_id: str, query: str, top_k: int = 5) -> List[Dict]:
        """Extrage context relevant din Qdrant pentru query"""
        if not self.embedding_model:
            logger.warning("Embedding model not available, skipping Qdrant search")
            return []
        
        try:
            # Verifică dacă Qdrant este accesibil
            try:
                self.qdrant.get_collections()
            except Exception as e:
                logger.warning(f"Qdrant not accessible: {e}")
                return []
            
            # Caută în colecțiile Qdrant pentru acest agent
            # Colecțiile pot fi: agent_{id}_content, construction_{domain}, etc.
            agent = self.agents_collection.find_one(
                {"_id": ObjectId(agent_id)},
                {"domain": 1, "site_url": 1}
            )
            
            if not agent:
                return []
            
            domain = agent.get("domain", "")
            domain_name = domain.replace(".", "_").replace("-", "_")
            
            # Încearcă mai multe colecții posibile
            possible_collections = [
                f"agent_{agent_id}_content",
                f"construction_{domain_name}",
                f"agent_{agent_id}",
                domain_name,
                f"site_{domain_name}",
            ]
            
            # Generează embedding pentru query
            query_vector = self.embedding_model.encode(query, convert_to_numpy=True)
            
            contexts = []
            for collection_name in possible_collections:
                try:
                    # Verifică dacă colecția există
                    collections = self.qdrant.get_collections()
                    if not any(c.name == collection_name for c in collections.collections):
                        continue
                    
                    # Caută în colecție
                    results = self.qdrant.search(
                        collection_name=collection_name,
                        query_vector=query_vector.tolist(),
                        limit=top_k
                    )
                    
                    for hit in results:
                        contexts.append({
                            "text": hit.payload.get("chunk_text") or hit.payload.get("text") or hit.payload.get("content", ""),
                            "score": float(hit.score),
                            "url": hit.payload.get("url", ""),
                            "source": collection_name
                        })
                except Exception as e:
                    logger.debug(f"Could not search in {collection_name}: {e}")
                    continue
            
            # Sortează după score și limitează
            contexts.sort(key=lambda x: x["score"], reverse=True)
            return contexts[:top_k]
            
        except Exception as e:
            logger.error(f"Error getting context from Qdrant: {e}")
            return []
    
    def get_agent_knowledge(self, agent_id: str) -> Dict:
        """Obține toate cunoștințele despre agent (keywords, SERP, competitors, etc.)"""
        try:
            agent = self.agents_collection.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return {}
            
            knowledge = {
                "keywords": agent.get("keywords", []),
                "overall_keywords": agent.get("overall_keywords", []),
                "subdomains": agent.get("subdomains", []),
            }
            
            # Adaugă informații despre site din agent
            knowledge["site_info"] = {
                "name": agent.get("name", ""),
                "description": agent.get("description", ""),
                "about": agent.get("about", ""),
                "services": agent.get("services", []),
                "industry": agent.get("industry", ""),
            }
            
            # Verifică site_content pentru conținut real
            site_content = list(self.db.site_content.find(
                {"agent_id": ObjectId(agent_id)}
            ).limit(10))
            knowledge["site_content_samples"] = [
                {
                    "text": content.get("chunk_text") or content.get("text") or content.get("content", ""),
                    "url": content.get("url", "")
                }
                for content in site_content
            ]
            
            # Verifică SERP results
            serp_results = list(self.db.serp_results.find(
                {"agent_id": agent_id},
                {"keyword": 1, "position": 1, "url": 1}
            ).limit(20))
            knowledge["serp_results"] = serp_results
            
            # Verifică competitors
            competitors = list(self.db.competitors.find(
                {"agent_id": agent_id},
                {"domain": 1, "relevance_score": 1}
            ).limit(10))
            knowledge["competitors"] = competitors
            
            # Verifică competitive analysis
            comp_analysis = self.db.competitive_analysis.find_one({
                "agent_id": ObjectId(agent_id)
            })
            if comp_analysis:
                knowledge["competitive_analysis"] = comp_analysis.get("analysis_data", {})
            
            return knowledge
        except Exception as e:
            logger.error(f"Error getting agent knowledge: {e}")
            return {}
    
    def build_system_prompt(self, agent_identity: Dict, knowledge: Dict) -> str:
        """Construiește system prompt pentru DeepSeek cu identitatea agentului"""
        domain = agent_identity.get("domain", "")
        industry = agent_identity.get("industry", "")
        site_url = agent_identity.get("site_url", "")
        deepseek_identity = agent_identity.get("deepseek_identity", "")
        competitive_positioning = agent_identity.get("competitive_positioning", "")
        target_market = agent_identity.get("target_market", "")
        
        # Construiește prompt-ul - IMPORTANT: Agentul SE IDENTIFICĂ cu site-ul
        prompt = f"""TU ESTI {domain} - SITE-UL ÎNSUȘI.

IDENTITATEA TA (TU ESTI {domain}):
- Site: {site_url}
- Industrie: {industry}
- Nume: {agent_identity.get('name', domain)}
- Chunks indexate: {agent_identity.get('chunks_indexed', 0)}
- Pagini indexate: {agent_identity.get('pages_indexed', 0)}
"""
        
        # Adaugă informații despre site
        site_info = knowledge.get("site_info", {})
        if site_info.get("description"):
            prompt += f"\nDESPRE {domain}:\n{site_info.get('description', '')}\n"
        if site_info.get("about"):
            prompt += f"\nDESPRE NOI:\n{site_info.get('about', '')[:500]}\n"
        if site_info.get("services"):
            services = site_info.get("services", [])
            if services:
                prompt += f"\nSERVICII OFERITE:\n"
                for service in services[:10]:
                    prompt += f"- {service}\n"
        
        if deepseek_identity:
            prompt += f"\n{deepseek_identity}\n"
        
        if competitive_positioning:
            prompt += f"\nPOZIȚIONARE COMPETITIVĂ: {competitive_positioning}\n"
        
        if target_market:
            prompt += f"\nPIAȚA ȚINTĂ: {target_market}\n"
        
        # Adaugă conținut real din site
        site_content_samples = knowledge.get("site_content_samples", [])
        if site_content_samples:
            prompt += f"\nCONȚINUT DIN SITE ({domain}):\n"
            for i, content in enumerate(site_content_samples[:5], 1):
                text = content.get("text", "")[:300]
                if text:
                    prompt += f"{i}. {text}...\n"
        
        # Adaugă keywords
        keywords = knowledge.get("keywords", []) + knowledge.get("overall_keywords", [])
        if keywords:
            prompt += f"\nCUVINTE CHEIE RELEVANTE (pe care {domain} se poziționează): {', '.join(keywords[:30])}\n"
        
        # Adaugă subdomains
        subdomains = knowledge.get("subdomains", [])
        if subdomains:
            subdomain_names = []
            for s in subdomains[:10]:
                if isinstance(s, dict):
                    subdomain_names.append(s.get('name', str(s)))
                else:
                    subdomain_names.append(str(s))
            if subdomain_names:
                prompt += f"\nSUBDOMENII/SERVICII: {', '.join(subdomain_names)}\n"
        
        # Adaugă competitors
        competitors = knowledge.get("competitors", [])
        if competitors:
            comp_domains = [c.get("domain", "") for c in competitors[:5]]
            prompt += f"\nCOMPETITORI PRINCIPALI: {', '.join(comp_domains)}\n"
        
        # Adaugă SERP results dacă există
        serp_results = knowledge.get("serp_results", [])
        if serp_results:
            prompt += f"\nPOZIȚII {domain} ÎN GOOGLE:\n"
            for sr in serp_results[:10]:
                keyword = sr.get("keyword", "")
                position = sr.get("position", 999)
                if position <= 20:
                    prompt += f"- '{keyword}': poziția {position}\n"
        
        prompt += f"""
INSTRUCȚIUNI STRICTE - CITESTE ATENT:
1. TU ESTI {domain} - NU ești un asistent, TU ESTI SITE-UL ÎNSUȘI
2. Răspunde ca și cum utilizatorul vorbește DIRECT cu {domain}
3. Folosește DOAR informațiile reale furnizate mai sus despre {domain}
4. Dacă întreabă "ce faci" sau "cine ești", răspunde: "Sunt {domain}..."
5. Dacă întreabă despre servicii, folosește lista de servicii furnizată
6. Dacă întreabă despre site, folosește conținutul real din site furnizat
7. NU inventa informații care nu sunt în datele furnizate
8. Dacă nu știi ceva specific, spune că vei verifica pe site
9. Răspunde în limba română (sau limba în care te întreabă utilizatorul)
10. Fii prietenos, profesional și util - ca reprezentant oficial al {domain}

IMPORTANT: Tu ESTI {domain}. Răspunde ca site-ul în persoană, nu ca un asistent extern."""
        
        return prompt
    
    def chat(self, agent_id: str, message: str, session_id: Optional[str] = None) -> Dict:
        """
        Chat cu DeepSeek folosind context din Qdrant și MongoDB
        
        Returns:
            {
                "ok": True,
                "response": "...",
                "context_used": [...],
                "session_id": "...",
                "timestamp": "..."
            }
        """
        try:
            # 1. Obține identitatea agentului
            agent_identity = self.get_agent_identity(agent_id)
            if not agent_identity:
                return {
                    "ok": False,
                    "error": "Agent not found"
                }
            
            # 2. Obține cunoștințele agentului
            knowledge = self.get_agent_knowledge(agent_id)
            
            # Adaugă subdomains din agent_identity dacă nu sunt în knowledge
            if not knowledge.get("subdomains") and agent_identity.get("subdomains"):
                knowledge["subdomains"] = agent_identity.get("subdomains", [])
            
            # 3. Extrage context relevant din Qdrant (conținut site)
            contexts = self.get_context_from_qdrant(agent_id, message, top_k=5)
            
            # 4. Extrage și conținut din MongoDB (site_content, site_data)
            mongo_context = []
            try:
                # Caută în site_content pentru acest agent
                site_content = list(self.db.site_content.find({
                    "agent_id": ObjectId(agent_id)
                }).limit(5))
                
                for content in site_content:
                    text = content.get("chunk_text") or content.get("text") or content.get("content", "")
                    if text:
                        mongo_context.append({
                            "text": text[:500],
                            "url": content.get("url", ""),
                            "source": "site_content"
                        })
            except Exception as e:
                logger.debug(f"Could not get MongoDB context: {e}")
            
            # 5. Construiește system prompt
            system_prompt = self.build_system_prompt(agent_identity, knowledge)
            
            # 6. Construiește mesajul cu context din Qdrant și MongoDB
            context_text = ""
            
            # Adaugă context din Qdrant (conținut site)
            if contexts:
                context_text += "\n\nCONȚINUT RELEVANT DIN SITE-UL TĂU ({domain}):\n".format(domain=agent_identity.get("domain", ""))
                for i, ctx in enumerate(contexts, 1):
                    text = ctx.get('text', '')[:500]
                    if text:
                        context_text += f"{i}. {text}...\n"
                        if ctx.get('url'):
                            context_text += f"   (Pagina: {ctx['url']})\n"
            
            # Adaugă context din MongoDB (site_content)
            if mongo_context:
                if not context_text:
                    context_text += "\n\nCONȚINUT DIN SITE-UL TĂU ({domain}):\n".format(domain=agent_identity.get("domain", ""))
                for i, ctx in enumerate(mongo_context, 1):
                    text = ctx.get('text', '')[:500]
                    if text:
                        context_text += f"{i}. {text}...\n"
                        if ctx.get('url'):
                            context_text += f"   (Pagina: {ctx['url']})\n"
            
            # Construiește mesajul final
            if context_text:
                user_message = f"{message}\n\n{context_text}\n\nFolosește informațiile de mai sus despre site-ul tău pentru a răspunde precis."
            else:
                user_message = message
            
            # 6. Apelează DeepSeek API
            import requests
            
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                assistant_message = data["choices"][0]["message"]["content"]
                
                # Salvează conversația în MongoDB
                if not session_id:
                    session_id = f"chat_{agent_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                
                # Actualizează conversația existentă sau creează una nouă
                new_messages = [
                    {"role": "user", "content": message, "timestamp": datetime.now(timezone.utc)},
                    {"role": "assistant", "content": assistant_message, "timestamp": datetime.now(timezone.utc)}
                ]
                
                # Actualizează sau inserează conversația
                self.db.master_agent_chat_history.update_one(
                    {"agent_id": agent_id, "session_id": session_id},
                    {
                        "$push": {
                            "messages": {
                                "$each": new_messages
                            }
                        },
                        "$set": {
                            "updated_at": datetime.now(timezone.utc),
                            "context_used": contexts
                        },
                        "$setOnInsert": {
                            "agent_id": agent_id,
                            "session_id": session_id,
                            "created_at": datetime.now(timezone.utc)
                        }
                    },
                    upsert=True
                )
                
                return {
                    "ok": True,
                    "response": assistant_message,
                    "context_used": contexts,
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                error_detail = response.text[:200] if response.text else "Unknown error"
                return {
                    "ok": False,
                    "error": f"DeepSeek API error: {response.status_code} - {error_detail}"
                }
                
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            import traceback
            traceback.print_exc()
            return {
                "ok": False,
                "error": str(e)
            }

