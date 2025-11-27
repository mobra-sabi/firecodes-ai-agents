import logging
from typing import List, Dict, Any
from llm_orchestrator import get_orchestrator
from pymongo import MongoClient
import os
import psutil
import json
import datetime

logger = logging.getLogger(__name__)

class SystemController:
    def __init__(self):
        self.llm = get_orchestrator()
        self.mongo_client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27018/"))
        self.db = self.mongo_client["ai_agents_db"]
        
        # Stare conversație
        self.briefing_mode = False
        self.briefing_step = 0
        self.current_domain = None
        self.client_data = {}
        
        self.briefing_questions = [
            "Să începem cu începutul. Cum se numește compania ta și care este site-ul web principal?",
            "Câți angajați are echipa ta în acest moment? (Asta mă ajută să calibrez strategiile de HR)",
            "Care sunt principalele 3 servicii sau produse care îți aduc cei mai mulți bani acum?",
            "Care este cea mai mare durere a ta în business acum? (ex: lipsă lead-uri, clienți care nu plătesc, haos organizatoric)",
            "Cu ce materiale sau furnizori lucrezi preponderent? (Voi scana piața pentru prețuri mai bune)",
            "Care este marja de profit țintită pe care vrei să o atingem împreună?"
        ]

    def get_system_status(self) -> str:
        """Colectează statusul live al sistemului"""
        try:
            cpu_percent = psutil.cpu_percent()
            ram_percent = psutil.virtual_memory().percent
            agents_count = self.db.site_agents.count_documents({})
            competitors_count = self.db.site_agents.count_documents({"agent_type": "slave"})
            
            workflow_running = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'python' in proc.info['name'] and proc.info['cmdline'] and 'ceo_master_workflow.py' in ' '.join(proc.info['cmdline']):
                        workflow_running = True
                except: pass
                    
            status = f"""
STATUS SISTEM:
- Hardware: CPU {cpu_percent}%, RAM {ram_percent}%
- Bază de Date: {agents_count} agenți totali ({competitors_count} competitori)
- Procese Active: {'✅ CEO Workflow (Scraping/Validare)' if workflow_running else '💤 Idle'}
- LLM: Qwen 2.5 72B (Local - 8 GPUs)
"""
            return status
        except:
            return "Status: Online"

    def process_user_message(self, user_message: str) -> Dict[str, Any]:
        """Procesează mesajul utilizatorului"""
        
        # Comandă explicită pentru start briefing
        if "start briefing" in user_message.lower() or "configurează compania" in user_message.lower():
            self.briefing_mode = True
            self.briefing_step = 0
            self.client_data = {}
            return {
                "text": f"👋 Salut! Sunt asistentul tău executiv AI. Hai să configurăm profilul afacerii tale pentru a genera strategii personalizate.\n\n{self.briefing_questions[0]}",
                "suggested_actions": []
            }

        # Logică Briefing
        if self.briefing_mode:
            # Salvăm răspunsul anterior
            if self.briefing_step < len(self.briefing_questions):
                question = self.briefing_questions[self.briefing_step]
                self.client_data[f"q_{self.briefing_step}"] = user_message
                
                # Încercăm să extragem domeniul din primul răspuns
                if self.briefing_step == 0:
                    import re
                    domain_match = re.search(r'[\w\-\.]+\.[a-z]{2,}', user_message)
                    if domain_match:
                        self.current_domain = domain_match.group(0)
            
            # Trecem la următorul pas
            self.briefing_step += 1
            
            if self.briefing_step < len(self.briefing_questions):
                return {
                    "text": self.briefing_questions[self.briefing_step],
                    "suggested_actions": []
                }
            else:
                # Finalizare Briefing
                self.briefing_mode = False
                self.save_client_profile()
                return {
                    "text": f"✅ Perfect! Am salvat profilul companiei. \n\nAm activat modulul **'Daily Hints'**. De mâine vei primi sugestii strategice bazate pe acești parametri.\n\nAcum, vrei să scanez concurența pentru {self.current_domain}?",
                    "suggested_actions": [
                        {"label": "🚀 Pornește Scanare Competitori", "action": "start_scan", "params": {"domain": self.current_domain}},
                        {"label": "📊 Arată Dashboard", "action": "show_dashboard", "params": {}}
                    ]
                }

        # Logică Standard (Qwen Chat)
        system_status = self.get_system_status()
        
        system_prompt = f"""Ești AI COMMANDER, interfața centrală de control.
        
{system_status}

ROL: Asistent Executiv de Business. Răspunde scurt și la obiect.
Dacă utilizatorul vrea să își configureze firma, propune acțiunea "start_briefing".

Dacă utilizatorul cere ceva ce necesită o acțiune, RĂSPUNDE ÎN FORMAT JSON:
{{
    "text": "Textul tău...",
    "suggested_actions": [ {{"label": "...", "action": "...", "params": {{}} }} ]
}}

Altfel, JSON simplu cu "text".
NU folosi markdown code blocks.
"""

        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response if isinstance(response, str) else response.get("content", "")
            
            # Curățare JSON
            content = content.strip()
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            try:
                data = json.loads(content)
                return data
            except json.JSONDecodeError:
                return {"text": content, "suggested_actions": [
                    {"label": "📝 Start Configurare Companie", "action": "start_briefing_trigger", "params": {}}
                ]}
                
        except Exception as e:
            logger.error(f"Chat Controller Error: {e}")
            return {"text": f"Eroare sistem: {str(e)}", "suggested_actions": []}

    def save_client_profile(self):
        """Salvează datele colectate în DB"""
        try:
            profile = {
                "domain": self.current_domain,
                "raw_briefing": self.client_data,
                "created_at": datetime.datetime.now(),
                "status": "active",
                "modules": {
                    "daily_hints": True,
                    "competitor_watch": True
                }
            }
            self.db.client_profiles.insert_one(profile)
            logger.info(f"Client profile saved for {self.current_domain}")
        except Exception as e:
            logger.error(f"Error saving profile: {e}")

# Singleton
_controller = None
def get_controller():
    global _controller
    if _controller is None:
        _controller = SystemController()
    return _controller
