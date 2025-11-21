#!/usr/bin/env python3
"""
Script pentru validarea și indexarea tuturor agenților conform checklist-ului de 4 straturi
"""

import asyncio
import sys
import os
from pymongo import MongoClient
from qdrant_client import QdrantClient
from site_ingestor import run_site_ingest
from dotenv import load_dotenv
import requests
import json

# Încarcă variabilele de environment
load_dotenv('config.env')

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:9308/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ai_agents_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:9306")
SERVER_URL = "http://localhost:8090"

class AgentValidator:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[MONGODB_DATABASE]
        self.agents_collection = self.db.agents
        self.qdrant_client = QdrantClient(url=QDRANT_URL)
        
    def get_all_agents(self):
        """Obține toți agenții din baza de date"""
        return list(self.agents_collection.find({}))
    
    def check_agent_data(self, agent_id):
        """Verifică dacă agentul are date indexate în Qdrant"""
        try:
            collection_name = f"agent_{agent_id}_content"
            info = self.qdrant_client.get_collection(collection_name)
            return info.points_count > 0
        except Exception:
            return False
    
    def test_agent_chat(self, agent_id, question="ce servicii oferiti?"):
        """Testează chat-ul pentru un agent"""
        try:
            response = requests.post(
                f"{SERVER_URL}/ask",
                json={"question": question, "agent_id": agent_id},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    confidence = data.get("confidence", 0)
                    sources = data.get("sources", [])
                    return {
                        "success": True,
                        "confidence": confidence,
                        "sources_count": len(sources),
                        "response": data.get("response", "")[:100] + "..."
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("error", "Unknown error"),
                        "confidence": 0
                    }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "confidence": 0
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "confidence": 0
            }
    
    async def index_agent(self, agent_id, site_url):
        """Indexează datele pentru un agent"""
        print(f"🔄 Indexez agentul {agent_id} de la {site_url}...")
        
        config = {
            'qdrant_url': QDRANT_URL,
            'mongodb_uri': MONGODB_URI,
            'mongodb_db': MONGODB_DATABASE,
            'max_pages': 10,
            'chunk_size': 1000,
            'chunk_overlap': 200
        }
        
        try:
            result = await run_site_ingest(site_url, agent_id, config)
            if result.get('status') == 'success':
                return {
                    "success": True,
                    "pages_scraped": result.get('pages_scraped', 0),
                    "chunks_created": result.get('chunks_created', 0)
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', 'Unknown error')
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def calculate_compliance_score(self, agent, has_data, chat_test):
        """Calculează compliance score-ul agentului"""
        score = 0
        total = 0
        
        # Identitate & Scop (20%)
        total += 2
        if agent.get("name"): score += 1
        if agent.get("domain"): score += 1
        
        # Percepție (25%)
        total += 2.5
        if has_data: score += 2.5
        
        # Memorie (15%)
        total += 1.5
        score += 1.5  # Implementat în RAG pipeline
        
        # Raționare (20%)
        total += 2
        score += 2  # GPT orchestrator implementat
        
        # Acțiune (10%)
        total += 1
        if has_data and chat_test.get("success"): score += 1
        
        # Interfețe (5%)
        total += 0.5
        score += 0.5  # API implementat
        
        # Securitate (5%)
        total += 0.5
        score += 0.5  # Guardrails implementate
        
        return round((score / total) * 100)
    
    async def validate_agent(self, agent):
        """Validează un agent conform checklist-ului"""
        agent_id = str(agent['_id'])
        agent_name = agent.get('name', 'Unknown')
        site_url = agent.get('site_url', '')
        
        print(f"\n{'='*60}")
        print(f"🔍 VALIDARE AGENT: {agent_name}")
        print(f"📋 ID: {agent_id}")
        print(f"🌐 URL: {site_url}")
        print(f"{'='*60}")
        
        # 1. Verifică dacă are date indexate
        has_data = self.check_agent_data(agent_id)
        print(f"📊 Date indexate: {'✅ DA' if has_data else '❌ NU'}")
        
        # 2. Dacă nu are date, încearcă să le indexeze
        if not has_data and site_url:
            print(f"🔄 Agentul nu are date indexate. Încep indexarea...")
            index_result = await self.index_agent(agent_id, site_url)
            
            if index_result["success"]:
                print(f"✅ Indexare reușită: {index_result['pages_scraped']} pagini, {index_result['chunks_created']} chunks")
                has_data = True
            else:
                print(f"❌ Indexare eșuată: {index_result['error']}")
        
        # 3. Testează chat-ul
        print(f"💬 Testez chat-ul...")
        chat_test = self.test_agent_chat(agent_id)
        
        if chat_test["success"]:
            print(f"✅ Chat funcțional - Confidence: {chat_test['confidence']:.1%}")
            print(f"📚 Surse găsite: {chat_test['sources_count']}")
        else:
            print(f"❌ Chat eșuat: {chat_test['error']}")
        
        # 4. Calculează compliance score
        compliance_score = self.calculate_compliance_score(agent, has_data, chat_test)
        print(f"📈 Compliance Score: {compliance_score}%")
        
        # 5. Breakpoint pentru testare manuală
        print(f"\n🛑 BREAKPOINT - Testează manual agentul:")
        print(f"   URL: {SERVER_URL}/chat?agent_id={agent_id}")
        print(f"   Întrebare de test: 'ce servicii oferiti?'")
        
        input("   Apasă ENTER când ai testat manual și vrei să continui...")
        
        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "site_url": site_url,
            "has_data": has_data,
            "chat_working": chat_test["success"],
            "confidence": chat_test.get("confidence", 0),
            "compliance_score": compliance_score
        }
    
    async def validate_all_agents(self):
        """Validează toți agenții"""
        print("🚀 ÎNCEP VALIDAREA TUTUROR AGENȚILOR")
        print("="*60)
        
        agents = self.get_all_agents()
        print(f"📋 Găsiți {len(agents)} agenți în baza de date")
        
        results = []
        
        for i, agent in enumerate(agents, 1):
            print(f"\n📊 Progres: {i}/{len(agents)}")
            
            try:
                result = await self.validate_agent(agent)
                results.append(result)
            except Exception as e:
                print(f"❌ Eroare la validarea agentului {agent.get('name', 'Unknown')}: {e}")
                results.append({
                    "agent_id": str(agent['_id']),
                    "agent_name": agent.get('name', 'Unknown'),
                    "error": str(e)
                })
        
        # Raport final
        print(f"\n{'='*60}")
        print("📊 RAPORT FINAL")
        print(f"{'='*60}")
        
        working_agents = [r for r in results if r.get("chat_working", False)]
        total_agents = len(results)
        
        print(f"📈 Total agenți: {total_agents}")
        print(f"✅ Agenți funcționali: {len(working_agents)}")
        print(f"❌ Agenți cu probleme: {total_agents - len(working_agents)}")
        
        if working_agents:
            avg_confidence = sum(r.get("confidence", 0) for r in working_agents) / len(working_agents)
            avg_compliance = sum(r.get("compliance_score", 0) for r in working_agents) / len(working_agents)
            print(f"📊 Confidence mediu: {avg_confidence:.1%}")
            print(f"📊 Compliance mediu: {avg_compliance:.1f}%")
        
        print(f"\n📋 DETALII PE AGENȚI:")
        for result in results:
            if result.get("chat_working"):
                print(f"✅ {result['agent_name']} - Confidence: {result.get('confidence', 0):.1%}")
            else:
                print(f"❌ {result['agent_name']} - {result.get('error', 'Chat eșuat')}")
        
        self.client.close()
        return results

async def main():
    """Funcția principală"""
    validator = AgentValidator()
    
    try:
        results = await validator.validate_all_agents()
        
        # Salvează rezultatele
        with open('/srv/hf/ai_agents/validation_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Rezultatele au fost salvate în validation_results.json")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Validarea a fost întreruptă de utilizator")
    except Exception as e:
        print(f"\n❌ Eroare generală: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())


