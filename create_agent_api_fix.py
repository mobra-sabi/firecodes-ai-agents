# Fix pentru endpoint-ul /api/agents/create

import subprocess
import json
from pymongo import MongoClient

def create_agent_via_script(site_url: str):
    """Creează agent folosind scriptul site_agent_creator.py"""
    try:
        # Rulează scriptul
        result = subprocess.run(
            ['python3', '/srv/hf/ai_agents/site_agent_creator.py', site_url],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )
        
        if result.returncode == 0:
            # Extrage domain-ul din URL
            from urllib.parse import urlparse
            parsed = urlparse(site_url)
            domain = parsed.netloc.replace('www.', '') or site_url.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Găsește agentul în MongoDB
            client = MongoClient("mongodb://localhost:27017/")
            db = client['ai_agents']
            agent = db.agents.find_one({"domain": domain})
            
            if agent:
                agent["_id"] = str(agent["_id"])
                return {"ok": True, "agent": agent}
            else:
                return {"ok": False, "error": "Agent created but not found"}
        else:
            return {"ok": False, "error": f"Script failed: {result.stderr}"}
            
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timeout - agent creation took too long"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

print("✅ Helper function ready")
