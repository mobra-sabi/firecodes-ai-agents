#!/usr/bin/env python3
"""
Script de testare pentru integrarea LangChain în AI Agents Platform

Testează:
- Endpointurile API pentru lanțuri
- Funcționalitatea lanțurilor LangChain
- Integrarea cu agentii existenti
- Conectivitatea DeepSeek/Qwen
- Chain Registry
- Actions module
"""

import sys
import os
import requests
import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Adaugă path-ul proiectului
sys.path.insert(0, '/srv/hf/ai_agents')

BASE_URL = "http://localhost:8083"

class Colors:
    """Culori pentru output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️ {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ️ {msg}{Colors.RESET}")

def print_header(msg: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def test_server_health():
    """Test 1: Verifică dacă serverul răspunde"""
    print_header("TEST 1: Server Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Serverul răspunde (Status: {data.get('overall_status', 'N/A')})")
            
            services = data.get('services', {})
            print_info(f"Servicii disponibile: {len(services)}")
            for service_name, service_data in services.items():
                status = service_data.get('status', 'N/A')
                status_icon = "✅" if status == "healthy" else "❌"
                print(f"   {status_icon} {service_name}: {status}")
            
            return True
        else:
            print_error(f"Serverul răspunde cu status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Eroare la conectarea la server: {e}")
        return False

def test_list_chains():
    """Test 2: Listează lanțurile disponibile"""
    print_header("TEST 2: Listare Lanțuri LangChain")
    
    try:
        response = requests.get(f"{BASE_URL}/chains/list", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                chains = data.get('chains', [])
                print_success(f"Găsite {len(chains)} lanțuri:")
                
                for chain in chains:
                    name = chain.get('name', 'N/A')
                    available = chain.get('available', False)
                    description = chain.get('description', 'No description')
                    
                    status_icon = "✅" if available else "❌"
                    print(f"\n   {status_icon} {Colors.BOLD}{name}{Colors.RESET}")
                    print(f"      Descriere: {description}")
                    print(f"      Disponibil: {'Da' if available else 'Nu'}")
                
                return True, chains
            else:
                print_error(f"Răspuns neașteptat: {data.get('error', 'Unknown error')}")
                return False, []
        else:
            print_error(f"Endpoint răspunde cu status {response.status_code}")
            return False, []
    except Exception as e:
        print_error(f"Eroare: {e}")
        return False, []

def test_chain_preview(chain_name: str):
    """Test 3: Preview pentru un lanț specific"""
    print_header(f"TEST 3: Preview Lanț - {chain_name}")
    
    try:
        response = requests.get(f"{BASE_URL}/chains/{chain_name}/preview", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print_success(f"Preview pentru '{chain_name}' obținut")
                print(f"\n   Descriere: {data.get('description', 'N/A')}")
                print(f"   Disponibil: {'Da' if data.get('available') else 'Nu'}")
                
                inputs = data.get('inputs', [])
                outputs = data.get('outputs', [])
                
                print(f"\n   Input-uri așteptate:")
                for inp in inputs:
                    print(f"      - {inp}")
                
                print(f"\n   Output-uri generate:")
                for out in outputs:
                    print(f"      - {out}")
                
                return True
            else:
                print_error(f"Răspuns neașteptat: {data.get('error', 'Unknown error')}")
                return False
        else:
            print_error(f"Endpoint răspunde cu status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Eroare: {e}")
        return False

def test_get_agents():
    """Test 4: Obține lista de agenți disponibili"""
    print_header("TEST 4: Listare Agenți Disponibili")
    
    try:
        # Încearcă mai multe endpointuri posibile
        endpoints = [
            "/agents/list",
            "/api/agents",
            "/agents"
        ]
        
        agents = []
        for endpoint in endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # Verifică diferite formate de răspuns
                    if isinstance(data, list):
                        agents = data
                    elif isinstance(data, dict):
                        agents = data.get('agents', data.get('data', []))
                    
                    if agents:
                        break
            except:
                continue
        
        if agents:
            print_success(f"Găsiți {len(agents)} agenți:")
            for agent in agents[:5]:  # Afișează primii 5
                agent_id = str(agent.get('_id', agent.get('id', 'N/A')))
                domain = agent.get('domain', 'N/A')
                name = agent.get('name', 'N/A')
                print(f"   - {Colors.BOLD}{name}{Colors.RESET} ({domain})")
                print(f"     ID: {agent_id}")
            
            if len(agents) > 5:
                print(f"\n   ... și încă {len(agents) - 5} agenți")
            
            return True, agents
        else:
            # Încearcă direct din MongoDB
            try:
                from pymongo import MongoClient
                import os
                
                MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
                MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")
                
                client = MongoClient(MONGO_URI)
                db = client[MONGO_DB]
                agents_collection = db.site_agents
                
                agents = list(agents_collection.find().limit(10))
                if agents:
                    print_success(f"Găsiți {len(agents)} agenți (din MongoDB):")
                    for agent in agents[:5]:
                        agent_id = str(agent.get('_id', 'N/A'))
                        domain = agent.get('domain', 'N/A')
                        name = agent.get('name', 'N/A')
                        print(f"   - {Colors.BOLD}{name}{Colors.RESET} ({domain})")
                        print(f"     ID: {agent_id}")
                    
                    return True, agents
            except Exception as e:
                print_warning(f"Nu s-au putut obține agenți: {e}")
            
            print_warning("Nu există agenți disponibili sau endpointul nu este disponibil")
            return False, []
    except Exception as e:
        print_error(f"Eroare: {e}")
        return False, []

def test_run_chain(agent_id: str, chain_name: str, params: Dict[str, Any]):
    """Test 5: Rulează un lanț pentru un agent"""
    print_header(f"TEST 5: Rulare Lanț - {chain_name} pentru Agent {agent_id[:8]}...")
    
    try:
        payload = {
            "params": params,
            "task_id": f"test_{datetime.now(timezone.utc).timestamp()}"
        }
        
        print_info(f"Parametri: {json.dumps(params, indent=2, ensure_ascii=False)}")
        print_info("Se rulează lanțul... (poate dura câteva secunde)")
        
        response = requests.post(
            f"{BASE_URL}/agents/{agent_id}/run_chain/{chain_name}",
            json=payload,
            timeout=120  # Timeout mai mare pentru execuție
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print_success(f"Lanțul '{chain_name}' executat cu succes")
                
                result = data.get('result', {})
                status = result.get('status', 'N/A')
                print(f"\n   Status: {status}")
                
                if status == 'success':
                    chain_result = result.get('result', {})
                    print(f"\n   Rezultat:")
                    print(json.dumps(chain_result, indent=2, ensure_ascii=False)[:500])
                    if len(json.dumps(chain_result, ensure_ascii=False)) > 500:
                        print("   ... (trunchiat)")
                elif status == 'error':
                    error_msg = result.get('message', 'Unknown error')
                    print_error(f"Eroare: {error_msg}")
                
                return True, data
            else:
                print_error(f"Răspuns neașteptat: {data.get('error', 'Unknown error')}")
                return False, None
        else:
            print_error(f"Endpoint răspunde cu status {response.status_code}")
            try:
                error_data = response.json()
                print_error(f"Detalii: {error_data.get('error', 'Unknown error')}")
            except:
                print_error(f"Răspuns: {response.text[:200]}")
            return False, None
    except Exception as e:
        print_error(f"Eroare: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False, None

def test_langchain_integration():
    """Test 6: Testează integrarea LangChain directă"""
    print_header("TEST 6: Integrare LangChain Directă")
    
    try:
        from langchain_agents.chain_registry import get_chain_registry
        from langchain_agents.llm_manager import get_qwen_llm, get_deepseek_llm
        
        print_info("Testare Chain Registry...")
        registry = get_chain_registry()
        chains = registry.list_chains()
        print_success(f"Chain Registry: {len(chains)} lanțuri înregistrate")
        
        print_info("Testare LLM Manager...")
        qwen_llm = get_qwen_llm()
        deepseek_llm = get_deepseek_llm()
        
        print(f"   Qwen LLM: {'✅' if qwen_llm else '❌'}")
        print(f"   DeepSeek LLM: {'✅' if deepseek_llm else '❌'}")
        
        if qwen_llm and deepseek_llm:
            print_success("Toate componentele LangChain sunt disponibile")
            return True
        else:
            print_warning("Unele componente LangChain nu sunt disponibile")
            return False
            
    except Exception as e:
        print_error(f"Eroare la testarea integrării LangChain: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

def test_actions_module():
    """Test 7: Testează modulul Actions"""
    print_header("TEST 7: Modul Actions")
    
    try:
        from actions import ActionExecutor, execute_action_plan, get_action_status
        
        print_success("Module actions importate cu succes")
        
        executor = ActionExecutor()
        connectors = executor.connectors
        
        print_info(f"Conectori disponibili: {len(connectors)}")
        for connector_name in connectors.keys():
            print(f"   ✅ {connector_name}")
        
        return True
    except Exception as e:
        print_error(f"Eroare: {e}")
        import traceback
        print_error(traceback.format_exc())
        return False

def main():
    """Funcția principală de testare"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║     🧪 TESTARE INTEGRARE LANGCHAIN - AI AGENTS PLATFORM      ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")
    
    results = {}
    
    # Test 1: Server Health
    results['server_health'] = test_server_health()
    if not results['server_health']:
        print_error("Serverul nu răspunde! Verifică dacă serverul rulează.")
        return
    
    # Test 2: List Chains
    results['list_chains'], chains = test_list_chains()
    
    # Test 3: Chain Preview
    if chains:
        for chain in chains[:2]:  # Testează primele 2 lanțuri
            chain_name = chain.get('name')
            if chain_name:
                results[f'preview_{chain_name}'] = test_chain_preview(chain_name)
    
    # Test 4: Get Agents
    results['get_agents'], agents = test_get_agents()
    
    # Test 5: Run Chain (dacă există agenți)
    if agents:
        agent = agents[0]
        agent_id = str(agent.get('_id'))
        
        # Testează decision_chain cu un exemplu simplu
        if any(c.get('name') == 'decision_chain' for c in chains):
            test_params = {
                "strategy": {
                    "summary": "Strategie de test pentru verificare funcționalitate",
                    "opportunities": ["Optimizare SEO", "Campanii publicitare"]
                }
            }
            results['run_decision_chain'] = test_run_chain(
                agent_id,
                'decision_chain',
                test_params
            )[0]
    
    # Test 6: LangChain Integration
    results['langchain_integration'] = test_langchain_integration()
    
    # Test 7: Actions Module
    results['actions_module'] = test_actions_module()
    
    # Rezumat final
    print_header("REZUMAT TESTE")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    print(f"\n{Colors.BOLD}Rezultate:{Colors.RESET}")
    print(f"   Total teste: {total_tests}")
    print(f"   {Colors.GREEN}✅ Reușite: {passed_tests}{Colors.RESET}")
    print(f"   {Colors.RED}❌ Eșuate: {total_tests - passed_tests}{Colors.RESET}")
    print(f"   Rata succes: {(passed_tests/total_tests*100):.1f}%")
    
    print(f"\n{Colors.BOLD}Detalii:{Colors.RESET}")
    for test_name, result in results.items():
        status_icon = "✅" if result else "❌"
        print(f"   {status_icon} {test_name}")
    
    if passed_tests == total_tests:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Toate testele au trecut cu succes!{Colors.RESET}\n")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️ Unele teste au eșuat. Verifică logurile de mai sus.{Colors.RESET}\n")

if __name__ == "__main__":
    main()

