import logging
from typing import List, Dict, Any
from llm_orchestrator import get_orchestrator
from pymongo import MongoClient
import os
import psutil
import json

logger = logging.getLogger(__name__)

class SystemController:
    def __init__(self):
        self.llm = get_orchestrator()
        self.mongo_client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27018/"))
        self.db = self.mongo_client["ai_agents_db"]

    def get_system_status(self) -> str:
        """Colectează statusul live al sistemului pentru a-l da AI-ului"""
        
        # 1. Hardware
        cpu_percent = psutil.cpu_percent()
        ram_percent = psutil.virtual_memory().percent
        
        # 2. Database Stats
        agents_count = self.db.site_agents.count_documents({})
        competitors_count = self.db.site_agents.count_documents({"agent_type": "slave"})
        
        # 3. Running Processes (Simplificat)
        # Verificăm dacă rulează workflow-ul
        workflow_running = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'python' in proc.info['name'] and proc.info['cmdline'] and 'ceo_master_workflow.py' in ' '.join(proc.info['cmdline']):
                    workflow_running = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        status = f"""
STATUS SISTEM:
- Hardware: CPU {cpu_percent}%, RAM {ram_percent}%
- Bază de Date: {agents_count} agenți totali ({competitors_count} competitori)
- Procese Active: {'✅ CEO Workflow (Scraping/Validare)' if workflow_running else '💤 Idle'}
- LLM: Qwen 2.5 72B (Local - 8 GPUs)
"""
        return status

    def process_user_message(self, user_message: str) -> Dict[str, Any]:
        """Procesează mesajul utilizatorului și decide acțiunea"""
        
        system_status = self.get_system_status()
        
        # System Prompt care definește personalitatea de "Controller"
        system_prompt = f"""Ești AI COMMANDER, interfața centrală de control pentru un sistem complex de Business Intelligence.
        
{system_status}

ROLUL TĂU:
1. Să răspunzi la întrebările utilizatorului despre statusul sistemului.
2. Să propui acțiuni concrete pe care utilizatorul le poate confirma.
3. Să fii concis, profesional și strategic.

CAPACITĂȚI (TOOLS) PE CARE LE POȚI PROPUNE (în JSON):
- "start_scan": Pentru a începe o analiză nouă.
- "stop_scan": Pentru a opri procesele curente.
- "generate_report": Pentru a genera rapoarte PDF/Markdown.
- "show_competitors": Pentru a afișa lista competitorilor.

Dacă utilizatorul cere ceva ce necesită o acțiune, RĂSPUNDE ÎN FORMAT JSON astfel:
{{
    "text": "Textul tău explicativ aici...",
    "suggested_actions": [
        {{"label": "Nume Buton 1", "action": "nume_actiune", "params": {{...}}}},
        {{"label": "Nume Buton 2", "action": "nume_actiune", "params": {{...}}}}
    ]
}}

Dacă e doar o discuție, răspunde cu JSON doar cu câmpul "text".
NU folosi markdown code blocks pentru JSON. Returnează JSON pur.
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
            
            # Încercăm să parsăm JSON-ul generat de AI
            content = response if isinstance(response, str) else response.get("content", "")
            
            # Curățare basic
            content = content.strip()
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            try:
                data = json.loads(content)
                return data
            except json.JSONDecodeError:
                # Dacă AI-ul nu a returnat JSON (s-a "prostit"), îl împachetăm noi
                return {"text": content, "suggested_actions": []}
                
        except Exception as e:
            logger.error(f"Chat Controller Error: {e}")
            return {"text": f"Eroare de sistem: {str(e)}", "suggested_actions": []}

# Singleton
_controller = None
def get_controller():
    global _controller
    if _controller is None:
        _controller = SystemController()
    return _controller

