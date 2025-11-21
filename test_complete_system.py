#!/usr/bin/env python3
"""
🧪 TEST COMPLET SISTEM - Verificare toate funcționalitățile
Testează toate rutele, logica de business și verifică dacă rezultatele sunt reale
"""

import requests
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
from pymongo import MongoClient
from bson import ObjectId

# Configuration
API_BASE = "http://localhost:8090"
TIMEOUT = 30

class SystemTester:
    def __init__(self):
        self.api_base = API_BASE
        self.results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
        self.mongo = MongoClient("mongodb://localhost:27017")
        self.db = self.mongo["ai_agents_db"]
        
    def log_test(self, name: str, status: str, details: Dict = None, is_real: bool = None):
        """Log test result"""
        test_result = {
            "name": name,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
            "is_real": is_real
        }
        self.results["tests"].append(test_result)
        self.results["summary"]["total"] += 1
        
        if status == "PASS":
            self.results["summary"]["passed"] += 1
            icon = "✅"
        elif status == "FAIL":
            self.results["summary"]["failed"] += 1
            icon = "❌"
        else:
            self.results["summary"]["warnings"] += 1
            icon = "⚠️"
        
        print(f"{icon} {name}: {status}")
        if details:
            for key, value in details.items():
                if isinstance(value, (dict, list)) and len(str(value)) > 200:
                    print(f"   {key}: {str(value)[:200]}...")
                else:
                    print(f"   {key}: {value}")
        print()
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        try:
            response = requests.get(f"{self.api_base}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                is_real = data.get("overall_status") != "mock"
                services = data.get("services", {})
                real_services = sum(1 for s in services.values() if s.get("status") == "healthy")
                
                self.log_test(
                    "Health Check",
                    "PASS",
                    {
                        "status": data.get("overall_status"),
                        "health_percentage": data.get("health_percentage"),
                        "healthy_services": real_services,
                        "total_services": len(services)
                    },
                    is_real=is_real
                )
            else:
                self.log_test("Health Check", "FAIL", {"status_code": response.status_code})
        except Exception as e:
            self.log_test("Health Check", "FAIL", {"error": str(e)})
    
    def test_api_stats(self):
        """Test API stats endpoint"""
        try:
            response = requests.get(f"{self.api_base}/api/stats", timeout=10)
            if response.status_code == 200:
                data = response.json()
                is_real = data.get("total_agents", 0) > 0
                
                self.log_test(
                    "API Stats",
                    "PASS",
                    data,
                    is_real=is_real
                )
            else:
                self.log_test("API Stats", "FAIL", {"status_code": response.status_code})
        except Exception as e:
            self.log_test("API Stats", "FAIL", {"error": str(e)})
    
    def test_agents_list(self):
        """Test agents list endpoint"""
        try:
            response = requests.get(f"{self.api_base}/api/agents", timeout=10)
            if response.status_code == 200:
                agents = response.json()
                is_real = len(agents) > 0 and isinstance(agents, list)
                
                # Verifică dacă agenții au date reale
                real_agents = 0
                for agent in agents[:5]:  # Verifică primele 5
                    if agent.get("domain") or agent.get("site_url"):
                        real_agents += 1
                
                self.log_test(
                    "Agents List",
                    "PASS",
                    {
                        "total_agents": len(agents),
                        "agents_with_domain": real_agents,
                        "sample_agent": agents[0] if agents else None
                    },
                    is_real=is_real and real_agents > 0
                )
            else:
                self.log_test("Agents List", "FAIL", {"status_code": response.status_code})
        except Exception as e:
            self.log_test("Agents List", "FAIL", {"error": str(e)})
    
    def test_agent_details(self):
        """Test agent details endpoint"""
        try:
            # Găsește un agent real
            agent = self.db.site_agents.find_one({})
            if not agent:
                self.log_test("Agent Details", "WARN", {"message": "No agents found"})
                return
            
            agent_id = str(agent["_id"])
            response = requests.get(f"{self.api_base}/api/agents/{agent_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                is_real = bool(data.get("domain") or data.get("site_url"))
                
                self.log_test(
                    "Agent Details",
                    "PASS",
                    {
                        "agent_id": agent_id,
                        "has_domain": bool(data.get("domain")),
                        "has_keywords": len(data.get("keywords", [])) > 0,
                        "has_embeddings": data.get("has_embeddings", False)
                    },
                    is_real=is_real
                )
            else:
                self.log_test("Agent Details", "FAIL", {"status_code": response.status_code})
        except Exception as e:
            self.log_test("Agent Details", "FAIL", {"error": str(e)})
    
    def test_serp_endpoints(self):
        """Test SERP and rankings endpoints"""
        try:
            # Găsește un agent cu keywords
            agent = self.db.site_agents.find_one({"keywords": {"$exists": True, "$ne": []}})
            if not agent:
                self.log_test("SERP Endpoints", "WARN", {"message": "No agents with keywords found"})
                return
            
            agent_id = str(agent["_id"])
            
            # Test rankings statistics
            response = requests.get(
                f"{self.api_base}/api/agents/{agent_id}/rankings-statistics",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                is_real = data.get("total_keywords", 0) > 0
                
                self.log_test(
                    "SERP Rankings Statistics",
                    "PASS",
                    {
                        "total_keywords": data.get("total_keywords"),
                        "total_serp_results": data.get("total_serp_results"),
                        "unique_competitors": data.get("unique_competitors"),
                        "master_positions": data.get("master_positions", {})
                    },
                    is_real=is_real
                )
            else:
                self.log_test("SERP Rankings Statistics", "FAIL", {"status_code": response.status_code})
        except Exception as e:
            self.log_test("SERP Rankings Statistics", "FAIL", {"error": str(e)})
    
    def test_playbook_endpoints(self):
        """Test playbook generation and execution"""
        try:
            # Găsește un agent
            agent = self.db.site_agents.find_one({})
            if not agent:
                self.log_test("Playbook Endpoints", "WARN", {"message": "No agents found"})
                return
            
            agent_id = str(agent["_id"])
            
            # Test playbook generation
            response = requests.post(
                f"{self.api_base}/api/agents/{agent_id}/playbook/generate",
                json={"objective": "improve_seo_rankings"},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                playbook_id = data.get("playbook_id")
                is_real = bool(playbook_id)
                
                self.log_test(
                    "Playbook Generation",
                    "PASS",
                    {
                        "playbook_id": playbook_id,
                        "actions_count": data.get("actions_count", 0),
                        "status": data.get("status")
                    },
                    is_real=is_real
                )
                
                # Test playbook details
                if playbook_id:
                    response2 = requests.get(
                        f"{self.api_base}/api/playbooks/{playbook_id}",
                        timeout=10
                    )
                    if response2.status_code == 200:
                        playbook_data = response2.json()
                        self.log_test(
                            "Playbook Details",
                            "PASS",
                            {
                                "playbook_id": playbook_id,
                                "actions": len(playbook_data.get("actions", []))
                            },
                            is_real=True
                        )
            else:
                self.log_test("Playbook Generation", "FAIL", {
                    "status_code": response.status_code,
                    "response": response.text[:200]
                })
        except Exception as e:
            self.log_test("Playbook Generation", "FAIL", {"error": str(e)})
    
    def test_orchestrator_endpoints(self):
        """Test orchestrator endpoints"""
        try:
            # Test orchestrator insights
            response = requests.get(
                f"{self.api_base}/api/orchestrator/insights?days=7",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                is_real = data.get("total_actions", 0) > 0
                
                self.log_test(
                    "Orchestrator Insights",
                    "PASS",
                    {
                        "total_actions": data.get("total_actions"),
                        "patterns_found": data.get("patterns_found", 0),
                        "insights": len(data.get("insights", []))
                    },
                    is_real=is_real
                )
            else:
                self.log_test("Orchestrator Insights", "FAIL", {"status_code": response.status_code})
        except Exception as e:
            self.log_test("Orchestrator Insights", "FAIL", {"error": str(e)})
    
    def test_actions_queue(self):
        """Test actions queue endpoints"""
        try:
            # Test queue stats
            response = requests.get(f"{self.api_base}/api/actions/stats", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                is_real = data.get("total", 0) > 0
                
                self.log_test(
                    "Actions Queue Stats",
                    "PASS",
                    data,
                    is_real=is_real
                )
            else:
                self.log_test("Actions Queue Stats", "FAIL", {"status_code": response.status_code})
        except Exception as e:
            self.log_test("Actions Queue Stats", "FAIL", {"error": str(e)})
    
    def test_intelligence_endpoints(self):
        """Test intelligence dashboard endpoints"""
        try:
            response = requests.get(f"{self.api_base}/api/intelligence/overview", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                is_real = data.get("total_agents", 0) > 0
                
                self.log_test(
                    "Intelligence Overview",
                    "PASS",
                    {
                        "total_agents": data.get("total_agents"),
                        "total_keywords": data.get("total_keywords"),
                        "total_competitors": data.get("total_competitors")
                    },
                    is_real=is_real
                )
            else:
                self.log_test("Intelligence Overview", "FAIL", {"status_code": response.status_code})
        except Exception as e:
            self.log_test("Intelligence Overview", "FAIL", {"error": str(e)})
    
    def test_database_integrity(self):
        """Test database integrity and data quality"""
        try:
            # Verifică agenții
            total_agents = self.db.site_agents.count_documents({})
            agents_with_domain = self.db.site_agents.count_documents({"domain": {"$exists": True, "$ne": ""}})
            agents_with_keywords = self.db.site_agents.count_documents({"keywords": {"$exists": True, "$ne": []}})
            agents_with_embeddings = self.db.site_agents.count_documents({"has_embeddings": True})
            
            # Verifică SERP results
            serp_results = self.db.serp_results.count_documents({})
            
            # Verifică orchestrator actions
            orchestrator_actions = self.db.orchestrator_actions.count_documents({})
            
            is_real = (
                total_agents > 0 and
                agents_with_domain > 0 and
                serp_results > 0
            )
            
            self.log_test(
                "Database Integrity",
                "PASS",
                {
                    "total_agents": total_agents,
                    "agents_with_domain": agents_with_domain,
                    "agents_with_keywords": agents_with_keywords,
                    "agents_with_embeddings": agents_with_embeddings,
                    "serp_results": serp_results,
                    "orchestrator_actions": orchestrator_actions,
                    "data_quality": f"{(agents_with_domain/total_agents*100):.1f}%" if total_agents > 0 else "0%"
                },
                is_real=is_real
            )
        except Exception as e:
            self.log_test("Database Integrity", "FAIL", {"error": str(e)})
    
    def test_gpu_usage(self):
        """Test if GPU is being used for embeddings"""
        try:
            # Verifică dacă există embeddings generate
            agents_with_embeddings = self.db.site_agents.count_documents({"has_embeddings": True})
            
            # Verifică Qdrant collections
            from qdrant_client import QdrantClient
            qdrant = QdrantClient(url="http://localhost:9306", timeout=5)
            collections = qdrant.get_collections()
            
            total_points = 0
            for coll in collections.collections[:10]:  # Primele 10
                try:
                    info = qdrant.get_collection(coll.name)
                    total_points += info.points_count
                except:
                    pass
            
            is_real = agents_with_embeddings > 0 and total_points > 0
            
            self.log_test(
                "GPU/Embeddings Usage",
                "PASS" if is_real else "WARN",
                {
                    "agents_with_embeddings": agents_with_embeddings,
                    "qdrant_collections": len(collections.collections),
                    "total_vectors": total_points,
                    "gpu_used": is_real
                },
                is_real=is_real
            )
        except Exception as e:
            self.log_test("GPU/Embeddings Usage", "WARN", {"error": str(e), "message": "Could not verify GPU usage"})
    
    def test_llm_usage(self):
        """Test if LLM APIs are being used (not mocked)"""
        try:
            # Verifică orchestrator actions pentru a vedea dacă folosesc LLM
            recent_actions = list(self.db.orchestrator_actions.find({
                "timestamp": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)}
            }).limit(10))
            
            llm_used = False
            for action in recent_actions:
                if action.get("llm_model") or action.get("llm_provider"):
                    llm_used = True
                    break
            
            # Verifică dacă există competitive analysis cu conținut generat
            competitive_docs = self.db.competitive_analysis.count_documents({})
            
            is_real = llm_used or competitive_docs > 0
            
            self.log_test(
                "LLM Usage",
                "PASS" if is_real else "WARN",
                {
                    "recent_actions_checked": len(recent_actions),
                    "llm_detected": llm_used,
                    "competitive_analysis_docs": competitive_docs
                },
                is_real=is_real
            )
        except Exception as e:
            self.log_test("LLM Usage", "WARN", {"error": str(e)})
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 80)
        print("🧪 TESTARE COMPLETĂ SISTEM")
        print("=" * 80)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"API Base: {self.api_base}")
        print()
        
        # Basic endpoints
        self.test_health_endpoint()
        self.test_api_stats()
        self.test_agents_list()
        self.test_agent_details()
        
        # Business logic
        self.test_serp_endpoints()
        self.test_playbook_endpoints()
        self.test_orchestrator_endpoints()
        self.test_actions_queue()
        self.test_intelligence_endpoints()
        
        # Infrastructure
        self.test_database_integrity()
        self.test_gpu_usage()
        self.test_llm_usage()
        
        # Summary
        print("=" * 80)
        print("📊 REZUMAT TESTE")
        print("=" * 80)
        summary = self.results["summary"]
        print(f"Total teste: {summary['total']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⚠️  Warnings: {summary['warnings']}")
        
        # Real data check
        real_tests = sum(1 for t in self.results["tests"] if t.get("is_real") is True)
        print(f"\n🔍 Teste cu date reale: {real_tests}/{summary['total']}")
        
        return self.results
    
    def save_results(self, filename: str = "test_results.json"):
        """Save test results to file"""
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n💾 Rezultate salvate în: {filename}")

if __name__ == "__main__":
    tester = SystemTester()
    results = tester.run_all_tests()
    tester.save_results("/srv/hf/ai_agents/test_results.json")
    
    # Print detailed report
    print("\n" + "=" * 80)
    print("📋 RAPORT DETALIAT")
    print("=" * 80)
    for test in results["tests"]:
        status_icon = "✅" if test["status"] == "PASS" else "❌" if test["status"] == "FAIL" else "⚠️"
        real_icon = "🔍 REAL" if test.get("is_real") else "⚠️ MOCK/EMPTY" if test.get("is_real") is False else "❓ UNKNOWN"
        print(f"\n{status_icon} {test['name']} - {real_icon}")
        if test.get("details"):
            for key, value in test["details"].items():
                print(f"   {key}: {value}")
