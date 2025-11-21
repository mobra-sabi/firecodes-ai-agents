#!/usr/bin/env python3
"""
Agent AI General cu DeepSeek pentru Task Execution
Poate executa task-uri prin chat: comenzi shell, API calls, file operations, etc.
"""

import os
import json
import logging
import subprocess
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId

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


class TaskAIAgent:
    """Agent AI general care poate executa task-uri prin chat"""
    
    def __init__(self):
        self.mongo = MongoClient("mongodb://localhost:27018")
        self.db = self.mongo["ai_agents_db"]
        self.chat_history_collection = self.db.get_collection("task_ai_chat_history")
        
    def build_system_prompt(self) -> str:
        """Construiește system prompt pentru agentul AI"""
        return """Ești un asistent AI prietenos și consultativ care ajută utilizatorii să rezolve task-uri prin conversație naturală.

🎯 FILOSOFIA TA:
- Fii UMAN și PRIETENOS, nu un robot tehnic
- ÎNTREABĂ înainte de a executa acțiuni complexe sau multiple
- EXPLICĂ clar ce poți face și ce limitări ai
- OFERĂ ALTERNATIVE și SUGESTII, nu doar execuții automate
- Fii TRANSPARENT despre ce faci și de ce

📋 CAPABILITĂȚILE TALE (ce poți face):

1. **Comenzi Shell** (cu restricții de securitate):
   - Poți rula comenzi shell simple și sigure
   - Exemple: `ls`, `cat`, `grep`, `curl`, `head`, `tail`, `wc`, `find`
   - NU poți: `rm -rf`, `format`, `shutdown`, comenzi periculoase
   - Întreabă utilizatorul înainte de comenzi complexe sau multiple

2. **Apeluri API** (doar localhost pentru securitate):
   - Poți face request-uri HTTP către servicii locale
   - Exemple: verificare health, status, date din backend
   - NU poți: apeluri către servicii externe fără permisiune

3. **Operații pe Fișiere** (doar citire din `/srv/hf/ai_agents`):
   - Poți citi fișiere din directorul proiectului
   - Exemple: `read_file("agent_api.py")`, `read_file("config.py")`
   - NU poți: scriere, ștergere, modificare fără permisiune explicită

4. **Interogări Database** (MongoDB):
   - Poți interoga colecții permise: `site_agents`, `agents`, `serp_results`, etc.
   - Exemple: numărare agenți, listare date, căutări simple
   - NU poți: modificări, ștergeri, operații de scriere

5. **Automatizare Task-uri**:
   - Poți combina mai multe acțiuni pentru task-uri complexe
   - Dar ÎNTREABĂ utilizatorul înainte de a executa workflow-uri multiple

🔄 FLUXUL TĂU DE LUCRU:

1. **Primul mesaj de la utilizator**:
   - Salută prietenos
   - Explică BRIEF ce poți face
   - Oferă exemple de task-uri pe care le poți rezolva
   - NU executa nimic automat!

2. **Când utilizatorul cere un task**:
   - ANALIZEAZĂ cererea
   - Dacă e clar și simplu → explică ce vei face și execută
   - Dacă e complex sau necesită multiple acțiuni → ÎNTREABĂ:
     * "Vrei să execut X, Y și Z? Sau preferi doar X?"
     * "Această acțiune va face [descriere]. Continuăm?"
     * "Am nevoie de clarificări: [întrebare]"

3. **Înainte de execuție**:
   - Explică BRIEF ce vei face
   - Dacă e o acțiune complexă, confirmă cu utilizatorul
   - NU executa mai multe acțiuni simultan fără confirmare

4. **După execuție**:
   - Prezintă rezultatele clar și structurat
   - Explică ce înseamnă rezultatele
   - Oferă următorii pași sau sugestii

📝 FORMAT PENTRU EXECUȚIE:
Când trebuie să execuți o acțiune, folosește:
```json
{
  "action": "execute",
  "type": "shell|api|file|database",
  "command": "...",
  "parameters": {...}
}
```

⚠️ REGULI STRICTE:
- NU executa niciodată fără să explici ce faci
- NU executa mai mult de 1-2 acțiuni simultan fără confirmare
- NU executa comenzi periculoase (blocate automat)
- ÎNTREABĂ dacă nu ești sigur
- Fii TRANSPARENT despre limitări

💬 STILUL TĂU:
- Conversațional și prietenos
- Explicări clare, fără jargon tehnic excesiv
- Răspunde în limba utilizatorului (română sau engleză)
- Folosește emoji-uri moderat pentru claritate
- Fii concis dar complet

🎓 EXEMPLU DE INTERACȚIUNE CORECTĂ:

Utilizator: "Analizează industria mea pentru tehnica-antifoc.ro"

Tu (CORECT):
"Bună! Pot să te ajut să analizezi industria ta. 

Înainte de a începe, vreau să clarific ce vrei exact:
1. Vrei să analizez site-ul tău (structură, conținut, SEO)?
2. Vrei să caut concurenți similari?
3. Vrei o analiză completă (site + concurenți + recomandări)?

Sau preferi să încep cu o analiză rapidă a site-ului tău și apoi continuăm cu concurenții?

Ce preferi?"

NU (GREȘIT):
"Excelent! Voi analiza industria ta și concurența. Voi executa mai multe acțiuni: [execuție automată fără confirmare]"

---
Răspunde întotdeauna în limba utilizatorului și fii consultativ, nu automat!
"""
    
    def execute_shell_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Execută o comandă shell (cu restricții de securitate)"""
        # Lista de comenzi periculoase
        dangerous_commands = [
            "rm -rf", "format", "mkfs", "dd if=", "shutdown", "reboot",
            "> /dev/sd", "mkfs", "fdisk", "parted", "> /etc/", "chmod 777"
        ]
        
        command_lower = command.lower()
        for dangerous in dangerous_commands:
            if dangerous in command_lower:
                return {
                    "ok": False,
                    "error": f"Comandă periculoasă detectată: {dangerous}",
                    "output": None
                }
        
        try:
            # Execută comanda cu timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd="/srv/hf/ai_agents"
            )
            
            return {
                "ok": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": f"Timeout: comanda a depășit {timeout} secunde",
                "output": None
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "output": None
            }
    
    def execute_api_call(self, method: str, url: str, params: Optional[Dict] = None, 
                        headers: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Execută un API call HTTP"""
        try:
            # Validare URL (doar localhost sau servicii interne)
            if not url.startswith(("http://localhost", "http://127.0.0.1", "https://api.deepseek.com")):
                return {
                    "ok": False,
                    "error": "Doar URL-uri locale sunt permise pentru securitate",
                    "response": None
                }
            
            method = method.upper()
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return {
                    "ok": False,
                    "error": f"Metodă HTTP neacceptată: {method}",
                    "response": None
                }
            
            return {
                "ok": response.status_code < 400,
                "status_code": response.status_code,
                "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "headers": dict(response.headers)
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "response": None
            }
    
    def read_file(self, file_path: str, max_lines: int = 100) -> Dict[str, Any]:
        """Citește un fișier (cu restricții)"""
        # Validare: doar fișiere din /srv/hf/ai_agents
        if not file_path.startswith("/srv/hf/ai_agents"):
            return {
                "ok": False,
                "error": "Doar fișiere din /srv/hf/ai_agents sunt accesibile",
                "content": None
            }
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                content = "".join(lines[:max_lines])
                if len(lines) > max_lines:
                    content += f"\n... (fișierul are {len(lines)} linii, afișate primele {max_lines})"
            
            return {
                "ok": True,
                "content": content,
                "total_lines": len(lines)
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "content": None
            }
    
    def query_database(self, collection: str, query: Dict, limit: int = 10) -> Dict[str, Any]:
        """Interoghează MongoDB"""
        try:
            # Validare: doar colecții permise
            allowed_collections = [
                "site_agents", "agents", "serp_results", "site_content",
                "competitive_analysis", "workflow_tracking", "actions_queue"
            ]
            
            if collection not in allowed_collections:
                return {
                    "ok": False,
                    "error": f"Colecție nepermisă: {collection}",
                    "results": None
                }
            
            results = list(self.db[collection].find(query).limit(limit))
            
            # Convertește ObjectId în string pentru JSON
            for result in results:
                if "_id" in result:
                    result["_id"] = str(result["_id"])
            
            return {
                "ok": True,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "results": None
            }
    
    def process_action(self, action_data: Dict) -> Dict[str, Any]:
        """Procesează o acțiune cerută de AI"""
        action_type = action_data.get("type")
        command = action_data.get("command")
        parameters = action_data.get("parameters", {})
        
        if action_type == "shell":
            return self.execute_shell_command(command, timeout=parameters.get("timeout", 30))
        elif action_type == "api":
            return self.execute_api_call(
                method=parameters.get("method", "GET"),
                url=command,
                params=parameters.get("params"),
                headers=parameters.get("headers"),
                data=parameters.get("data")
            )
        elif action_type == "file":
            # Acceptă atât "operation" cât și "command" pentru operație
            operation = parameters.get("operation") or command
            file_path = parameters.get("filename") or parameters.get("file_path") or command
            
            if operation == "read" or (not operation and file_path):
                return self.read_file(file_path, max_lines=parameters.get("max_lines", 100))
            else:
                return {
                    "ok": False,
                    "error": f"Operație fișier neacceptată: {operation}",
                    "result": None
                }
        elif action_type == "database":
            # Acceptă colecția din parameters (prioritate) sau din command
            # Dacă command este o operație (count_documents, mongo_count, etc.), folosește parameters
            allowed_collections = [
                "site_agents", "agents", "serp_results", "site_content",
                "competitive_analysis", "workflow_tracking", "actions_queue"
            ]
            
            # Prioritate 1: parameters.collection sau parameters.collection_name
            collection = parameters.get("collection") or parameters.get("collection_name")
            
            # Prioritate 2: command dacă este un nume de colecție valid
            if not collection and command and command in allowed_collections:
                collection = command
            
            # Prioritate 3: command dacă nu e o operație cunoscută
            if not collection and command:
                # Verifică dacă command nu este o operație
                operations = ["count_documents", "mongo_count", "query", "find"]
                if command not in operations:
                    collection = command
            
            if not collection:
                return {
                    "ok": False,
                    "error": "Numele colecției este necesar. Folosește parameters.collection sau parameters.collection_name",
                    "results": None
                }
            return self.query_database(
                collection=collection,
                query=parameters.get("query", {}),
                limit=parameters.get("limit", 10)
            )
        else:
            return {
                "ok": False,
                "error": f"Tip acțiune necunoscut: {action_type}",
                "result": None
            }
    
    def chat(self, message: str, session_id: Optional[str] = None) -> Dict:
        """
        Chat cu agentul AI - poate executa task-uri
        
        Returns:
            {
                "ok": True,
                "response": "...",
                "actions_executed": [...],
                "session_id": "...",
                "timestamp": "..."
            }
        """
        try:
            # Obține istoricul conversației
            if session_id:
                session = self.chat_history_collection.find_one({"session_id": session_id})
                conversation_history = session.get("messages", []) if session else []
            else:
                conversation_history = []
                session_id = str(ObjectId())
            
            # Construiește mesajele pentru DeepSeek
            messages = [
                {"role": "system", "content": self.build_system_prompt()}
            ]
            
            # Adaugă istoricul conversației
            for msg in conversation_history[-10:]:  # Ultimele 10 mesaje
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            
            # Adaugă mesajul curent
            messages.append({"role": "user", "content": message})
            
            # Apelează DeepSeek API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            ai_response = result["choices"][0]["message"]["content"]
            actions_executed = []
            
            # Verifică dacă AI-ul a cerut execuția unei acțiuni
            if "```json" in ai_response:
                # Extrage JSON-ul din răspuns
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
                if json_match:
                    try:
                        action_data = json.loads(json_match.group(1))
                        if action_data.get("action") == "execute":
                            # Execută acțiunea
                            action_result = self.process_action(action_data)
                            actions_executed.append({
                                "type": action_data.get("type"),
                                "command": action_data.get("command"),
                                "result": action_result
                            })
                            
                            # Adaugă rezultatul în răspunsul AI
                            if action_result.get("ok"):
                                ai_response += f"\n\n✅ Acțiune executată cu succes:\n{json.dumps(action_result, indent=2, ensure_ascii=False)}"
                            else:
                                ai_response += f"\n\n❌ Eroare la execuție: {action_result.get('error')}"
                    except json.JSONDecodeError:
                        pass  # Nu e un JSON valid, continuă cu răspunsul normal
            
            # Salvează conversația
            timestamp = datetime.now(timezone.utc).isoformat()
            
            conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": timestamp
            })
            conversation_history.append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": timestamp,
                "actions_executed": actions_executed
            })
            
            self.chat_history_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "session_id": session_id,
                        "messages": conversation_history,
                        "updated_at": timestamp
                    }
                },
                upsert=True
            )
            
            # Convertește actions_executed pentru JSON serialization
            actions_serialized = []
            for action in actions_executed:
                action_copy = action.copy()
                # Convertește orice datetime objects în string
                if "result" in action_copy and isinstance(action_copy["result"], dict):
                    result_copy = action_copy["result"].copy()
                    for key, value in result_copy.items():
                        if isinstance(value, datetime):
                            result_copy[key] = value.isoformat()
                    action_copy["result"] = result_copy
                actions_serialized.append(action_copy)
            
            return {
                "ok": True,
                "response": ai_response,
                "actions_executed": actions_serialized,
                "session_id": session_id,
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error in task AI agent chat: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "ok": False,
                "error": str(e),
                "response": None
            }

