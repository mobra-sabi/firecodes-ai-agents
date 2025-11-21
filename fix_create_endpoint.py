# Fix pentru endpoint /api/agents/create - Background task

import sys
with open('tools/agent_api.py', 'r') as f:
    content = f.read()

# Găsesc endpoint-ul vechi
old_code = '''@app.post("/api/agents/create")
def create_agent_simple(request: dict = Body(...)):
    """
    Creează un agent nou pentru orice website (fără session_id)
    Usage din Control Panel
    """
    import subprocess
    from urllib.parse import urlparse
    
    try:
        site_url = request.get("site_url")
        
        if not site_url:
            return {"ok": False, "error": "site_url is required"}
        
        logger.info(f"🚀 Creating new agent for: {site_url}")
        
        # Rulează scriptul site_agent_creator.py
        result = subprocess.run(
            ['python3', '/srv/hf/ai_agents/site_agent_creator.py', site_url],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )
        
        if result.returncode == 0:
            # Extrage domain-ul
            parsed = urlparse(site_url)
            domain = parsed.netloc.replace('www.', '')
            if not domain:
                domain = site_url.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Găsește agentul în MongoDB
            agent = agents_collection.find_one({"domain": domain})
            
            if agent:
                agent["_id"] = str(agent["_id"])
                logger.info(f"✅ Agent created successfully: {domain}")
                return {
                    "ok": True,
                    "agent": agent,
                    "message": f"Agent created successfully for {domain}"
                }
            else:
                return {"ok": False, "error": "Agent created but not found in database"}
        else:
            error_msg = result.stderr or "Unknown error during agent creation"
            logger.error(f"❌ Script failed: {error_msg}")
            return {"ok": False, "error": error_msg}
            
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timeout - agent creation took more than 5 minutes"}
    except Exception as e:
        logger.error(f"❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}'''

new_code = '''@app.post("/api/agents/create")
async def create_agent_simple(request: dict = Body(...), background_tasks: BackgroundTasks):
    """
    Creează un agent nou pentru orice website (fără session_id)
    Usage din Control Panel - Background task
    """
    import subprocess
    from urllib.parse import urlparse
    import asyncio
    
    try:
        site_url = request.get("site_url")
        
        if not site_url:
            return {"ok": False, "error": "site_url is required"}
        
        logger.info(f"🚀 Starting agent creation for: {site_url}")
        
        # Extrage domain-ul pentru verificare
        parsed = urlparse(site_url)
        domain = parsed.netloc.replace('www.', '')
        if not domain:
            domain = site_url.replace('https://', '').replace('http://', '').split('/')[0]
        
        # Verifică dacă agentul există deja
        existing = agents_collection.find_one({"domain": domain})
        if existing:
            existing["_id"] = str(existing["_id"])
            return {
                "ok": True,
                "agent": existing,
                "message": f"Agent already exists for {domain}"
            }
        
        # Rulează scriptul în mod sincron (în thread)
        def create_agent_sync():
            try:
                result = subprocess.run(
                    ['python3', '/srv/hf/ai_agents/site_agent_creator.py', site_url],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes
                )
                logger.info(f"Agent creation finished with code {result.returncode}")
                if result.returncode != 0:
                    logger.error(f"Script error: {result.stderr}")
            except Exception as e:
                logger.error(f"Error in background task: {e}")
        
        # Rulează în background (nu blochează)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, create_agent_sync)
        
        # Așteaptă 30 secunde pentru ca agentul să fie creat
        await asyncio.sleep(30)
        
        # Verifică dacă a fost creat
        agent = agents_collection.find_one({"domain": domain})
        
        if agent:
            agent["_id"] = str(agent["_id"])
            logger.info(f"✅ Agent created successfully: {domain}")
            return {
                "ok": True,
                "agent": agent,
                "message": f"Agent created successfully for {domain}"
            }
        else:
            # Agentul e încă în creare, returnează status pending
            return {
                "ok": True,
                "agent": {"domain": domain, "status": "creating"},
                "message": f"Agent creation started for {domain}. Please wait and refresh."
            }
            
    except Exception as e:
        logger.error(f"❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('tools/agent_api.py', 'w') as f:
        f.write(content)
    print("✅ Endpoint actualizat cu success! (async + wait 30s)")
else:
    print("❌ Endpoint-ul nu a fost găsit pentru update")
    sys.exit(1)

