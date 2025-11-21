"""
💬 DeepSeek Industry Chat - Chat interactiv cu DeepSeek pentru industria de construcții
======================================================================================

Permite discuții cu DeepSeek despre strategia de descoperire și transformare,
iar DeepSeek poate executa acțiuni direct prin aplicație.
"""

import logging
import traceback
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pymongo import MongoClient
from llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)


class DeepSeekIndustryChat:
    """Chat interactiv cu DeepSeek pentru industria de construcții"""
    
    def __init__(self, mongo_client: MongoClient):
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.llm = LLMOrchestrator()
        
        # Collections
        self.chat_history_collection = self.db["deepseek_industry_chat"]
        self.chat_sessions_collection = self.db["deepseek_industry_chat_sessions"]
        
        logger.info("✅ DeepSeek Industry Chat initialized")
    
    def _get_available_actions(self) -> List[Dict]:
        """Returnează lista de acțiuni disponibile pentru DeepSeek"""
        return [
            {
                "name": "discover_companies",
                "description": "Descoperă companii din industria de construcții din România",
                "parameters": {
                    "method": "deepseek sau web_search",
                    "max_companies": "număr maxim de companii",
                    "keywords": "lista de keywords (opțional, pentru web_search)"
                }
            },
            {
                "name": "create_agents",
                "description": "Creează agenți AI pentru companiile descoperite",
                "parameters": {
                    "company_domains": "lista de domenii de companii",
                    "max_parallel": "număr maxim de agenți creați în paralel"
                }
            },
            {
                "name": "get_progress",
                "description": "Obține progresul transformării industriei",
                "parameters": {}
            },
            {
                "name": "get_companies",
                "description": "Obține lista de companii descoperite",
                "parameters": {
                    "status": "pending, agent_created (opțional)",
                    "limit": "număr maxim de companii"
                }
            },
            {
                "name": "get_logs",
                "description": "Obține logs pentru transformarea industriei",
                "parameters": {
                    "session_id": "ID-ul sesiunii (opțional)",
                    "limit": "număr maxim de logs"
                }
            }
        ]
    
    def _execute_action(self, action_name: str, parameters: Dict) -> Dict:
        """
        Execută o acțiune cerută de DeepSeek
        
        Args:
            action_name: Numele acțiunii
            parameters: Parametrii acțiunii
        
        Returns:
            Rezultatul acțiunii
        """
        try:
            if action_name == "discover_companies":
                from industry_mass_agent_creator import ConstructionIndustryOrchestrator
                orchestrator = ConstructionIndustryOrchestrator(self.mongo)
                
                # Rulează descoperirea (sincron, pentru că e rapid)
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if parameters.get("method") == "web_search":
                        companies = loop.run_until_complete(
                            orchestrator.discovery.discover_companies_via_web_search(
                                keywords=parameters.get("keywords", []),
                                max_per_keyword=parameters.get("max_per_keyword", 20)
                            )
                        )
                    else:
                        companies = loop.run_until_complete(
                            orchestrator.discovery.discover_companies_via_deepseek(
                                max_companies=parameters.get("max_companies", 500),
                                session_id=parameters.get("session_id")
                            )
                        )
                    return {
                        "success": True,
                        "action": "discover_companies",
                        "result": {
                            "companies_discovered": len(companies),
                            "companies": companies[:10]  # Primele 10 pentru preview
                        }
                    }
                finally:
                    loop.close()
            
            elif action_name == "create_agents":
                from industry_mass_agent_creator import MassAgentCreator
                creator = MassAgentCreator(self.mongo, self.llm)
                
                # Obține companiile
                company_domains = parameters.get("company_domains", [])
                companies = []
                for domain in company_domains:
                    company = self.db.construction_companies_discovered.find_one({"domeniu": domain})
                    if company:
                        companies.append(company)
                
                if not companies:
                    return {
                        "success": False,
                        "error": "Nu s-au găsit companii pentru domeniile specificate"
                    }
                
                # Creează agenți (în background, pentru că durează)
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        creator.create_mass_agents(
                            companies=companies,
                            max_parallel=parameters.get("max_parallel", 5)
                        )
                    )
                    return {
                        "success": True,
                        "action": "create_agents",
                        "result": result
                    }
                finally:
                    loop.close()
            
            elif action_name == "get_progress":
                total = self.db.construction_companies_discovered.count_documents({})
                pending = self.db.construction_companies_discovered.count_documents({"status": "pending"})
                created = self.db.construction_companies_discovered.count_documents({"status": "agent_created"})
                agents = self.db.site_agents.count_documents({
                    "is_slave": {"$ne": True},
                    "industry": {"$regex": "construct", "$options": "i"}
                })
                
                return {
                    "success": True,
                    "action": "get_progress",
                    "result": {
                        "total_companies": total,
                        "pending": pending,
                        "created": created,
                        "total_agents": agents
                    }
                }
            
            elif action_name == "get_companies":
                query = {}
                if parameters.get("status"):
                    query["status"] = parameters["status"]
                
                limit = parameters.get("limit", 50)
                companies = list(
                    self.db.construction_companies_discovered.find(query)
                    .sort("discovered_at", -1)
                    .limit(limit)
                )
                
                for company in companies:
                    company["_id"] = str(company["_id"])
                    if "discovered_at" in company:
                        company["discovered_at"] = company["discovered_at"].isoformat()
                
                return {
                    "success": True,
                    "action": "get_companies",
                    "result": {
                        "count": len(companies),
                        "companies": companies
                    }
                }
            
            elif action_name == "get_logs":
                from industry_transformation_logger import IndustryTransformationLogger
                logger_instance = IndustryTransformationLogger(self.mongo)
                logs = logger_instance.get_logs(
                    session_id=parameters.get("session_id"),
                    limit=parameters.get("limit", 50)
                )
                
                return {
                    "success": True,
                    "action": "get_logs",
                    "result": {
                        "count": len(logs),
                        "logs": logs[:20]  # Primele 20 pentru preview
                    }
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Acțiune necunoscută: {action_name}"
                }
                
        except Exception as e:
            logger.error(f"Error executing action {action_name}: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    def chat(self, user_message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Procesează un mesaj de chat cu DeepSeek
        
        Args:
            user_message: Mesajul utilizatorului
            session_id: ID-ul sesiunii (opțional)
        
        Returns:
            Dict cu răspunsul DeepSeek și acțiunile executate
        """
        try:
            # Creează sau obține sesiunea
            if not session_id:
                session = {
                    "created_at": datetime.now(timezone.utc),
                    "last_message_at": datetime.now(timezone.utc),
                    "message_count": 1
                }
                result = self.chat_sessions_collection.insert_one(session)
                session_id = str(result.inserted_id)
            else:
                self.chat_sessions_collection.update_one(
                    {"_id": session_id},
                    {
                        "$set": {"last_message_at": datetime.now(timezone.utc)},
                        "$inc": {"message_count": 1}
                    }
                )
            
            # Obține istoricul conversației
            conversation_history = list(
                self.chat_history_collection.find({"session_id": session_id})
                .sort("timestamp", 1)
                .limit(20)
            )
            
            # Construiește prompt pentru DeepSeek
            available_actions = self._get_available_actions()
            
            system_prompt = f"""Ești un expert AI în industria de construcții din România și ai acces la un sistem de transformare a industriei în agenți AI.

ACȚIUNI DISPONIBILE:
{json.dumps(available_actions, indent=2, ensure_ascii=False)}

INSTRUCȚIUNI:
1. Discută cu utilizatorul despre strategia de descoperire și transformare
2. Când utilizatorul cere să descoperi companii sau să creezi agenți, folosește acțiunile disponibile
3. Format pentru acțiuni: {{"action": "nume_acțiune", "parameters": {{...}}}}
4. După executarea unei acțiuni, explică rezultatul utilizatorului
5. Fii proactiv - sugerează strategii și îmbunătățiri

Când vrei să execuți o acțiune, returnează JSON în format:
{{
  "response": "Răspunsul tău verbal",
  "action": {{
    "name": "nume_acțiune",
    "parameters": {{...}}
  }}
}}

Dacă nu execuți acțiuni, returnează doar:
{{
  "response": "Răspunsul tău verbal"
}}"""

            # Construiește mesajele pentru DeepSeek
            messages = [{"role": "system", "content": system_prompt}]
            
            # Adaugă istoricul
            for msg in conversation_history[-10:]:  # Ultimele 10 mesaje
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append({"role": "user", "content": content})
                else:
                    messages.append({"role": "assistant", "content": content})
            
            # Adaugă mesajul utilizatorului
            messages.append({"role": "user", "content": user_message})
            
            # Salvează mesajul utilizatorului
            user_msg_entry = {
                "session_id": session_id,
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now(timezone.utc)
            }
            self.chat_history_collection.insert_one(user_msg_entry)
            
            # Generează răspuns cu DeepSeek
            logger.info(f"Calling DeepSeek for industry chat (session: {session_id})")
            deepseek_response = self.llm.chat(
                messages=messages,
                model="deepseek-chat",
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parsează răspunsul
            if isinstance(deepseek_response, dict):
                # Poate fi dict cu "content" sau direct string în "content"
                response_text = deepseek_response.get("content", "")
                if not response_text:
                    # Încearcă să extragă din alte câmpuri
                    response_text = deepseek_response.get("message", str(deepseek_response))
            else:
                response_text = str(deepseek_response)
            
            # Dacă răspunsul este gol, generează un răspuns default
            if not response_text or len(response_text.strip()) < 10:
                response_text = "Îmi pare rău, nu am putut genera un răspuns. Te rog încearcă din nou."
                logger.warning(f"Empty response from DeepSeek, using default")
            
            # Încearcă să extragă acțiunea din răspuns
            action_result = None
            action_executed = None
            
            try:
                # Caută JSON în răspuns
                import re
                json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    action_json = json.loads(json_match.group(0))
                    if "action" in action_json:
                        action = action_json["action"]
                        action_name = action.get("name")
                        action_params = action.get("parameters", {})
                        
                        # Execută acțiunea
                        logger.info(f"Executing action: {action_name} with params: {action_params}")
                        action_result = self._execute_action(action_name, action_params)
                        action_executed = {
                            "name": action_name,
                            "parameters": action_params,
                            "result": action_result
                        }
                        
                        # Adaugă rezultatul acțiunii la răspuns
                        if action_result.get("success"):
                            response_text += f"\n\n✅ Acțiune executată: {action_name}\n"
                            response_text += f"Rezultat: {json.dumps(action_result.get('result', {}), indent=2, ensure_ascii=False)}"
                        else:
                            response_text += f"\n\n❌ Eroare la executarea acțiunii: {action_result.get('error', 'Unknown error')}"
            except Exception as e:
                logger.warning(f"Could not parse action from response: {e}")
                # Continuă fără acțiune
            
            # Salvează răspunsul DeepSeek
            assistant_msg_entry = {
                "session_id": session_id,
                "role": "assistant",
                "content": response_text,
                "action_executed": action_executed,
                "timestamp": datetime.now(timezone.utc)
            }
            self.chat_history_collection.insert_one(assistant_msg_entry)
            
            return {
                "response": response_text,
                "session_id": session_id,
                "action_executed": action_executed,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in industry chat: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Obține istoricul conversației"""
        try:
            messages = list(
                self.chat_history_collection.find({"session_id": session_id})
                .sort("timestamp", 1)
                .limit(limit)
            )
            
            for msg in messages:
                msg["_id"] = str(msg["_id"])
                if "timestamp" in msg:
                    msg["timestamp"] = msg["timestamp"].isoformat()
            
            return messages
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

