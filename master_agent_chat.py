"""
💬 Master Agent Chat System
============================

Sistem de chat pentru fiecare agent master cu:
- DeepSeek ca orchestrator principal (identificat cu site-ul master)
- Context complet: master agent, slave agents, SERP, rankings, CI
- Qwen learning în paralel (învață din interacțiuni)
- Business insights și recomandări pentru îmbunătățirea site-ului
"""

import logging
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)


class MasterAgentChatContextBuilder:
    """Construiește context complet pentru DeepSeek din toate datele agentului"""
    
    def __init__(self, mongo_client: MongoClient):
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
    
    def build_context(self, agent_id: str) -> Dict[str, Any]:
        """
        Construiește context complet pentru chat:
        - Informații master agent (domain, services, content)
        - Keywords și rankurile din Google
        - Slave agents (competitors) cu rankurile lor
        - Competitive intelligence (CI reports)
        - SERP results și visibility scores
        - Business insights și recomandări
        """
        try:
            # 1. Master Agent Data
            master_agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
            if not master_agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            domain = master_agent.get("domain", "")
            site_url = master_agent.get("site_url", "")
            services = master_agent.get("services", [])
            industry = master_agent.get("industry", "")
            chunks_indexed = master_agent.get("chunks_indexed", 0)
            name = master_agent.get("name", domain)
            description = master_agent.get("description", "")
            about = master_agent.get("about", "")
            
            # Obține chunks din Qdrant pentru a avea informații despre conținut
            site_content_summary = []
            try:
                from qdrant_client import QdrantClient
                qdrant = QdrantClient(url="http://localhost:6333", timeout=2)
                
                # Găsește colecția pentru acest agent
                collections = qdrant.get_collections().collections
                agent_collection = None
                for coll in collections:
                    try:
                        # Caută chunks pentru acest agent
                        result = qdrant.scroll(
                            collection_name=coll.name,
                            scroll_filter={
                                "must": [{
                                    "key": "agent_id",
                                    "match": {"value": agent_id}
                                }]
                            },
                            limit=10,
                            with_payload=True
                        )
                        if result[0]:
                            agent_collection = coll.name
                            # Extrage primele 10 chunks pentru a avea o idee despre conținut
                            for point in result[0][:10]:
                                payload = point.payload
                                chunk_text = payload.get("chunk_text", "")[:200]  # Primele 200 caractere
                                if chunk_text:
                                    site_content_summary.append(chunk_text)
                            break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Could not fetch chunks from Qdrant: {e}")
            
            # 2. Keywords și rankurile din Google
            keywords_data = []
            overall_keywords = master_agent.get("overall_keywords", [])
            subdomains = master_agent.get("subdomains", {})
            
            all_keywords = list(overall_keywords) if overall_keywords else []
            
            # Handle subdomains - can be dict or list
            # If subdomains is a dict with subdomain data containing keywords
            if isinstance(subdomains, dict):
                for subdomain, subdomain_data in subdomains.items():
                    if isinstance(subdomain_data, dict):
                        subdomain_kw = subdomain_data.get("keywords", [])
                        if subdomain_kw:
                            all_keywords.extend(subdomain_kw)
            elif isinstance(subdomains, list):
                # If subdomains is a list, check if items are dicts with keywords
                for subdomain_item in subdomains:
                    if isinstance(subdomain_item, dict):
                        subdomain_kw = subdomain_item.get("keywords", [])
                        if subdomain_kw:
                            all_keywords.extend(subdomain_kw)
                    # If it's a list of strings (subdomain names), skip keywords extraction
                    # Keywords are already in overall_keywords
            
            # 3. SERP Results și Rankings
            serp_data = []
            serp_runs = list(self.db.serp_runs.find({
                "agent_id": ObjectId(agent_id)
            }).sort("created_at", -1).limit(5))
            
            for run in serp_runs:
                run_id = str(run.get("_id"))
                serp_results = list(self.db.serp_results.find({
                    "serp_run_id": run_id
                }).limit(50))
                
                for result in serp_results:
                    keyword = result.get("keyword", "")
                    rank = result.get("rank", 999)
                    result_url = result.get("url", "")
                    result_domain = result.get("domain", "")
                    result_type = result.get("result_type", "organic")
                    
                    serp_data.append({
                        "keyword": keyword,
                        "rank": rank,
                        "url": result_url,
                        "domain": result_domain,
                        "type": result_type,
                        "is_master": result_domain == domain or domain in result_domain
                    })
            
            # 4. Slave Agents (Competitors) cu rankurile lor - DETALIAT
            slave_agents = list(self.db.site_agents.find({
                "master_agent_id": ObjectId(agent_id),
                "is_slave": True
            }))
            
            competitors_data = []
            for slave in slave_agents:
                slave_domain = slave.get("domain", "")
                slave_url = slave.get("site_url", "")
                slave_services = slave.get("services", [])
                slave_name = slave.get("name", slave_domain)
                slave_description = slave.get("description", "")
                slave_keywords = slave.get("overall_keywords", [])
                slave_chunks = slave.get("chunks_indexed", 0)
                
                # Găsește rankurile slave-ului pentru keywords-urile master-ului
                slave_rankings = {}
                for keyword in all_keywords[:30]:  # Primele 30 keywords
                    # Caută în SERP results pentru acest keyword
                    keyword_serp = [s for s in serp_data if s["keyword"] == keyword]
                    for serp_item in keyword_serp:
                        if slave_domain in serp_item["domain"] or serp_item["domain"] in slave_domain:
                            if keyword not in slave_rankings:
                                slave_rankings[keyword] = []
                            slave_rankings[keyword].append({
                                "rank": serp_item["rank"],
                                "url": serp_item["url"],
                                "type": serp_item["type"]
                            })
                
                # Calculează visibility score pentru slave
                slave_visibility = 0
                if slave_rankings:
                    for kw, ranks in slave_rankings.items():
                        best_rank = min([r["rank"] for r in ranks], default=999)
                        if best_rank <= 10:
                            slave_visibility += (11 - best_rank) / 10
                
                competitors_data.append({
                    "domain": slave_domain,
                    "name": slave_name,
                    "url": slave_url,
                    "description": slave_description,
                    "services": slave_services,
                    "keywords": slave_keywords[:20],  # Primele 20 keywords
                    "chunks_indexed": slave_chunks,
                    "rankings": slave_rankings,
                    "total_keywords_ranked": len(slave_rankings),
                    "visibility_score": slave_visibility
                })
            
            # 5. Competitive Intelligence Reports
            ci_reports = list(self.db.ci_reports.find({
                "agent_id": ObjectId(agent_id)
            }).sort("created_at", -1).limit(3))
            
            ci_summary = []
            for report in ci_reports:
                ci_summary.append({
                    "created_at": report.get("created_at", ""),
                    "summary": report.get("summary", ""),
                    "top_competitors": report.get("top_competitors", [])[:5],
                    "recommendations": report.get("recommendations", [])[:5]
                })
            
            # 6. Visibility Scores
            visibility_data = list(self.db.visibility.find({
                "agent_id": ObjectId(agent_id)
            }).sort("created_at", -1).limit(1))
            
            visibility_score = 0
            if visibility_data:
                visibility_score = visibility_data[0].get("total_visibility", 0)
            
            # 7. Construiește context prompt pentru DeepSeek
            context = {
                "master_agent": {
                    "domain": domain,
                    "name": name,
                    "site_url": site_url,
                    "description": description,
                    "about": about,
                    "services": services,
                    "industry": industry,
                    "chunks_indexed": chunks_indexed,
                    "total_keywords": len(all_keywords),
                    "content_summary": site_content_summary[:10]  # Primele 10 chunks
                },
                "keywords": all_keywords[:50],  # Primele 50 keywords
                "serp_data": serp_data[:100],  # Primele 100 SERP results
                "competitors": competitors_data,
                "ci_reports": ci_summary,
                "visibility_score": visibility_score,
                "total_slave_agents": len(slave_agents)
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error building context: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def build_deepseek_prompt(self, context: Dict[str, Any], conversation_history: List[Dict], user_message: str) -> str:
        """
        Construiește prompt complet pentru DeepSeek
        DeepSeek se identifică cu site-ul master și oferă insights business
        IMPORTANT: Folosește DOAR date reale din context, nu inventa informații!
        """
        master = context["master_agent"]
        domain = master["domain"]
        industry = master.get("industry", "")
        
        # Verifică dacă există date reale
        total_keywords = len(context.get("keywords", []))
        total_competitors = len(context.get("competitors", []))
        total_serp = len(context.get("serp_data", []))
        visibility_score = context.get("visibility_score", 0)
        
        prompt = f"""Ești {domain} - un expert în {industry} și reprezinți oficial acest site.

IMPORTANT: Folosește DOAR datele reale furnizate mai jos. NU inventa informații! Dacă o informație nu este menționată, spune clar că nu este disponibilă.

CONTEXT COMPLET DESPRE {domain}:

1. DESPRE SITE:
   - Nume: {master.get("name", domain)}
   - URL: {master.get("site_url", "")}
   - Descriere: {master.get("description", "N/A")}
   - Despre: {master.get("about", "N/A")[:500]}

2. SERVICII ȘI OFERTĂ:
{chr(10).join([f"   - {s}" for s in master.get("services", [])]) if master.get("services") else "   - N/A"}

3. CONȚINUT SITE (din chunks indexate):
"""
        # Adaugă primele 5 chunks pentru a avea context despre conținut
        content_summary = master.get("content_summary", [])
        if content_summary:
            for i, chunk in enumerate(content_summary[:5], 1):
                prompt += f"   {i}. {chunk}...\n"
        else:
            prompt += "   - Chunks nu sunt disponibile momentan\n"
        
        prompt += f"""
4. POZIȚIONARE ÎN GOOGLE (DATE REALE):
   - Total keywords monitorizate: {total_keywords} {"⚠️ Dacă este 0, spune clar că nu există keywords monitorizate!" if total_keywords == 0 else ""}
   - Visibility score: {visibility_score:.2f} {"⚠️ Dacă este 0, spune clar că nu există poziționare în Google!" if visibility_score == 0 else ""}
   - Chunks indexate: {master.get("chunks_indexed", 0)}
   - SERP results disponibile: {total_serp} {"⚠️ Dacă este 0, spune clar că nu există date SERP!" if total_serp == 0 else ""}

5. COMPETITORI (Slave Agents) - DATE REALE:
   - Total competitori monitorizați: {total_competitors} {"⚠️ Dacă este 0, spune clar că nu există competitori monitorizați!" if total_competitors == 0 else ""}
   - Top competitori cu rankuri:
"""
        
        # Adaugă top 10 competitori cu rankurile lor - DETALIAT
        competitors = context.get("competitors", [])[:10]
        if competitors:
            prompt += f"\n   Competitori monitorizați: {len(competitors)}\n"
            for i, comp in enumerate(competitors, 1):
                comp_domain = comp.get("domain", "")
                comp_name = comp.get("name", comp_domain)
                comp_description = comp.get("description", "")
                comp_services = comp.get("services", [])
                comp_keywords = comp.get("keywords", [])
                comp_chunks = comp.get("chunks_indexed", 0)
                comp_rankings = comp.get("rankings", {})
                comp_visibility = comp.get("visibility_score", 0)
                total_ranked = comp.get("total_keywords_ranked", 0)
                
                prompt += f"\n   {i}. {comp_name} ({comp_domain}):\n"
                if comp_description:
                    prompt += f"      - Descriere: {comp_description[:200]}...\n"
                if comp_services:
                    prompt += f"      - Servicii: {', '.join(comp_services[:5])}\n"
                prompt += f"      - Keywords monitorizate: {len(comp_keywords)}\n"
                prompt += f"      - Chunks indexate: {comp_chunks}\n"
                prompt += f"      - Keywords cu rank în Google: {total_ranked}\n"
                prompt += f"      - Visibility score: {comp_visibility:.2f}\n"
                if comp_rankings:
                    # Adaugă top 5 keywords cu rankurile lor
                    sorted_rankings = sorted(comp_rankings.items(), key=lambda x: min([r["rank"] for r in x[1]], default=999))[:5]
                    for kw, ranks in sorted_rankings:
                        best_rank = min([r["rank"] for r in ranks], default=999)
                        prompt += f"      - '{kw}': rank {best_rank}\n"
        else:
            prompt += "\n   - Nu există competitori monitorizați momentan\n"
        
        # Adaugă CI Reports insights
        ci_reports = context.get("ci_reports", [])
        if ci_reports:
            prompt += f"\n6. COMPETITIVE INTELLIGENCE (Ultimele insights):\n"
            for report in ci_reports[:2]:
                summary = report.get("summary", "")
                if summary:
                    prompt += f"   - {summary[:200]}...\n"
                recommendations = report.get("recommendations", [])
                if recommendations:
                    prompt += f"   - Recomandări: {recommendations[0][:100]}...\n"
        
        # Adaugă SERP insights
        serp_data = context.get("serp_data", [])
        master_rankings = [s for s in serp_data if s.get("is_master", False)]
        if master_rankings:
            prompt += f"\n7. POZIȚII MASTER ÎN GOOGLE:\n"
            # Grupează după keyword și arată cel mai bun rank
            kw_ranks = {}
            for item in master_rankings[:10]:
                kw = item["keyword"]
                rank = item["rank"]
                if kw not in kw_ranks or rank < kw_ranks[kw]:
                    kw_ranks[kw] = rank
            
            for kw, rank in list(kw_ranks.items())[:5]:
                prompt += f"   - '{kw}': rank {rank}\n"
        
        # Adaugă istoricul conversației
        if conversation_history:
            prompt += f"\n8. ISTORIC CONVERSAȚIE:\n"
            for msg in conversation_history[-5:]:  # Ultimele 5 mesaje
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    prompt += f"   Utilizator: {content[:150]}...\n"
                else:
                    prompt += f"   {domain}: {content[:150]}...\n"
        
        # Adaugă mesajul utilizatorului
        prompt += f"\n\nMESAJ UTILIZATOR: {user_message}\n\n"
        
        # Instrucțiuni pentru DeepSeek
        prompt += f"""
INSTRUCȚIUNI STRICTE:
1. Răspunde ca reprezentant oficial al {domain}
2. Folosește DOAR datele reale furnizate mai sus - NU inventa informații!
3. Dacă o informație nu este disponibilă (ex: 0 keywords, 0 competitori, 0 visibility), spune clar:
   - "Nu avem încă keywords monitorizate" (nu spune că avem 15 dacă nu sunt în date)
   - "Nu monitorizăm încă competitori" (nu spune că avem competitori dacă nu sunt în date)
   - "Nu avem poziționare în Google încă" (nu spune că avem visibility dacă este 0)
4. Când utilizatorul întreabă despre poziționare, concurență, sau strategie:
   - Menționează DOAR rankurile concrete din datele SERP furnizate
   - Compară DOAR cu competitorii (slave agents) care sunt în date
   - Oferă insights business concrete bazate pe datele reale disponibile
5. Dacă datele sunt incomplete (ex: 0 keywords, 0 competitori), sugerează:
   - "Trebuie să generăm keywords pentru site"
   - "Trebuie să identificăm și să monitorizăm competitori"
   - "Trebuie să rulăm analiza SERP pentru a vedea poziționarea reală"
6. NU inventezi cifre, keywords, sau competitori care nu sunt în datele furnizate!
7. Fii onest despre ce date sunt disponibile și ce lipsește

RĂSPUNS (ca {domain}):
"""
        
        return prompt


class MasterAgentChat:
    """Sistem de chat pentru master agents cu DeepSeek orchestration și Qwen learning"""
    
    def __init__(self, mongo_client: MongoClient, learning_pipeline=None):
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.learning_pipeline = learning_pipeline
        
        # Collections
        self.chat_history_collection = self.db["master_agent_chat_history"]
        self.chat_sessions_collection = self.db["master_agent_chat_sessions"]
        
        # LLM Orchestrator (DeepSeek)
        self.llm = LLMOrchestrator()
        
        # Context Builder
        self.context_builder = MasterAgentChatContextBuilder(mongo_client)
        
        logger.info("✅ Master Agent Chat initialized")
    
    def chat(
        self,
        agent_id: str,
        user_message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Procesează un mesaj de chat pentru un agent master
        
        Args:
            agent_id: ID-ul agentului master
            user_message: Mesajul utilizatorului
            user_id: ID-ul utilizatorului (opțional)
            session_id: ID-ul sesiunii de chat (opțional)
        
        Returns:
            Dict cu response, session_id, și metadata
        """
        try:
            # 1. Construiește context complet
            logger.info(f"Building context for agent {agent_id}")
            context = self.context_builder.build_context(agent_id)
            
            # 2. Obține istoricul conversației
            if session_id:
                conversation_history = list(
                    self.chat_history_collection.find({
                        "session_id": session_id
                    }).sort("timestamp", 1)
                )
            else:
                conversation_history = []
            
            # 3. Construiește prompt pentru DeepSeek
            deepseek_prompt = self.context_builder.build_deepseek_prompt(
                context, conversation_history, user_message
            )
            
            # 4. Generează răspuns cu DeepSeek + Qwen insights în paralel
            logger.info(f"Calling DeepSeek for agent {agent_id} with full context")
            logger.info(f"Context: {len(context.get('keywords', []))} keywords, {len(context.get('competitors', []))} competitors, {len(context.get('serp_data', []))} SERP results")
            
            # DeepSeek - răspuns principal
            deepseek_response = self.llm.chat(
                messages=[{"role": "user", "content": deepseek_prompt}],
                model="deepseek-chat",
                temperature=0.7,
                max_tokens=3000  # Mărit pentru răspunsuri mai detaliate
            )
            
            # Qwen - insights suplimentare în paralel (opțional, dacă este disponibil)
            qwen_insights = None
            try:
                # Încearcă să obțină insights de la Qwen (local LLM)
                # Acest lucru poate fi făcut în paralel sau după DeepSeek
                qwen_prompt = f"""Analizează următoarele date despre {context['master_agent']['domain']}:
- {len(context.get('keywords', []))} keywords monitorizate
- {len(context.get('competitors', []))} competitori
- Visibility score: {context.get('visibility_score', 0):.2f}
- {context['master_agent'].get('chunks_indexed', 0)} chunks indexate

Generează 3-5 insights strategice scurte (max 50 cuvinte fiecare) pentru îmbunătățirea poziționării în Google."""
                
                # Poți adăuga apel la Qwen aici dacă este disponibil
                # qwen_insights = self.llm.chat(..., model="qwen")
            except Exception as e:
                logger.debug(f"Qwen insights not available: {e}")
            
            # Parsează răspunsul (poate fi string sau dict)
            if isinstance(deepseek_response, dict):
                response_text = deepseek_response.get("content", str(deepseek_response))
            else:
                response_text = str(deepseek_response)
            
            # 5. Creează sau actualizează sesiunea
            if not session_id:
                session = {
                    "agent_id": ObjectId(agent_id),
                    "user_id": user_id,
                    "created_at": datetime.now(timezone.utc),
                    "last_message_at": datetime.now(timezone.utc),
                    "message_count": 1
                }
                result = self.chat_sessions_collection.insert_one(session)
                session_id = str(result.inserted_id)
            else:
                self.chat_sessions_collection.update_one(
                    {"_id": ObjectId(session_id)},
                    {
                        "$set": {"last_message_at": datetime.now(timezone.utc)},
                        "$inc": {"message_count": 1}
                    }
                )
            
            # 6. Salvează mesajele în istoric
            user_msg_entry = {
                "session_id": session_id,
                "agent_id": ObjectId(agent_id),
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now(timezone.utc)
            }
            self.chat_history_collection.insert_one(user_msg_entry)
            
            assistant_msg_entry = {
                "session_id": session_id,
                "agent_id": ObjectId(agent_id),
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now(timezone.utc),
                "model": "deepseek-chat",
                "context_used": {
                    "keywords_count": len(context.get("keywords", [])),
                    "competitors_count": len(context.get("competitors", [])),
                    "serp_results_count": len(context.get("serp_data", [])),
                    "visibility_score": context.get("visibility_score", 0)
                }
            }
            self.chat_history_collection.insert_one(assistant_msg_entry)
            
            # 7. Salvează în learning pipeline pentru Qwen (în paralel)
            if self.learning_pipeline:
                try:
                    # Salvează interacțiunea pentru learning
                    learning_entry = {
                        "agent_id": ObjectId(agent_id),
                        "user_message": user_message,
                        "assistant_response": response_text,
                        "context": context,
                        "timestamp": datetime.now(timezone.utc),
                        "source": "master_agent_chat"
                    }
                    self.db.orchestrator_actions.insert_one(learning_entry)
                    logger.info(f"✅ Saved interaction to learning pipeline for Qwen")
                except Exception as e:
                    logger.warning(f"⚠️ Could not save to learning pipeline: {e}")
            
            # 8. Returnează răspuns
            return {
                "response": response_text,
                "session_id": session_id,
                "agent_id": agent_id,
                "context_used": assistant_msg_entry["context_used"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Obține istoricul conversației pentru o sesiune"""
        try:
            messages = list(
                self.chat_history_collection.find({
                    "session_id": session_id
                }).sort("timestamp", 1).limit(limit)
            )
            
            for msg in messages:
                msg["_id"] = str(msg["_id"])
                if "timestamp" in msg:
                    msg["timestamp"] = msg["timestamp"].isoformat()
            
            return messages
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    def get_agent_sessions(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """Obține sesiunile de chat pentru un agent"""
        try:
            sessions = list(
                self.chat_sessions_collection.find({
                    "agent_id": ObjectId(agent_id)
                }).sort("last_message_at", -1).limit(limit)
            )
            
            for session in sessions:
                session["_id"] = str(session["_id"])
                if "created_at" in session:
                    session["created_at"] = session["created_at"].isoformat()
                if "last_message_at" in session:
                    session["last_message_at"] = session["last_message_at"].isoformat()
            
            return sessions
        except Exception as e:
            logger.error(f"Error getting agent sessions: {e}")
            return []

