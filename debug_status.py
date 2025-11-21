#!/usr/bin/env python3
"""
🔍 Debug Status Script - Verificare completă a sistemului
Rulează: python3 debug_status.py
"""

import sys
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
from qdrant_client import QdrantClient
import requests

def check_mongodb():
    """Verifică status MongoDB"""
    print("📊 MONGODB STATUS:")
    try:
        mongo = MongoClient("mongodb://localhost:27017")
        db = mongo["ai_agents_db"]
        
        # Test connection
        mongo.admin.command('ping')
        print("  ✅ Connected")
        
        # Collections stats
        collections = {
            "site_agents": db.site_agents.count_documents({}),
            "serp_results": db.serp_results.count_documents({}),
            "orchestrator_actions": db.orchestrator_actions.count_documents({}),
            "playbooks": db.playbooks.count_documents({}),
            "action_executions": db.action_executions.count_documents({}),
            "competitive_analysis": db.competitive_analysis.count_documents({}),
            "serp_runs": db.serp_runs.count_documents({}),
            "rankings_history": db.rankings_history.count_documents({}),
            "master_agent_chat_sessions": db.master_agent_chat_sessions.count_documents({}),
            "construction_companies_discovered": db.construction_companies_discovered.count_documents({}),
            "workflow_tracking": db.workflow_tracking.count_documents({}),
            "orchestrator_patterns": db.orchestrator_patterns.count_documents({}),
            "interactions": db.interactions.count_documents({}),
            "actions_queue": db.actions_queue.count_documents({})
        }
        
        for coll_name, count in collections.items():
            print(f"  {coll_name}: {count:,}")
        
        # Agents structure
        print("\n  🤖 AGENTS STRUCTURE:")
        total_agents = db.site_agents.count_documents({})
        agents_with_site_url = db.site_agents.count_documents({"site_url": {"$exists": True, "$ne": ""}})
        agents_with_domain = db.site_agents.count_documents({"domain": {"$exists": True, "$ne": ""}})
        agents_with_keywords = db.site_agents.count_documents({"keywords": {"$exists": True, "$ne": []}})
        agents_with_embeddings = db.site_agents.count_documents({"has_embeddings": True})
        
        print(f"    Total Agents: {total_agents}")
        print(f"    With site_url: {agents_with_site_url}")
        print(f"    With domain: {agents_with_domain}")
        print(f"    With keywords: {agents_with_keywords}")
        print(f"    With embeddings: {agents_with_embeddings}")
        
        # Actions Queue Status
        print("\n  📋 ACTIONS QUEUE:")
        pending = db.actions_queue.count_documents({"status": "pending"})
        running = db.actions_queue.count_documents({"status": "running"})
        completed = db.actions_queue.count_documents({"status": "completed"})
        failed = db.actions_queue.count_documents({"status": "failed"})
        print(f"    Pending: {pending}")
        print(f"    Running: {running}")
        print(f"    Completed: {completed}")
        print(f"    Failed: {failed}")
        
        if failed > 0:
            print("\n  ❌ RECENT FAILED ACTIONS:")
            failed_actions = list(db.actions_queue.find(
                {"status": "failed"}
            ).sort("created_at", -1).limit(5))
            for action in failed_actions:
                print(f"    - {action.get('action_type')} for agent {action.get('agent_id')}")
                error = action.get('error', 'N/A')
                if len(error) > 100:
                    error = error[:100] + "..."
                print(f"      Error: {error}")
        
        # Recent activity
        print("\n  📈 RECENT ACTIVITY (24h):")
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        recent_serp = db.serp_runs.count_documents({"created_at": {"$gte": yesterday}})
        recent_actions = db.orchestrator_actions.count_documents({"timestamp": {"$gte": yesterday}})
        recent_workflows = db.workflow_tracking.count_documents({"timestamp": {"$gte": yesterday}})
        print(f"    SERP Runs: {recent_serp}")
        print(f"    Orchestrator Actions: {recent_actions}")
        print(f"    Workflow Steps: {recent_workflows}")
        
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def check_qdrant():
    """Verifică status Qdrant"""
    print("\n🔍 QDRANT STATUS:")
    try:
        qdrant = QdrantClient(url="http://localhost:9306", timeout=5)
        collections = qdrant.get_collections()
        print(f"  ✅ Connected (port 9306)")
        print(f"  Total Collections: {len(collections.collections)}")
        
        # Sample collection info
        if collections.collections:
            sample = collections.collections[0]
            print(f"  Sample Collection: {sample.name}")
            try:
                info = qdrant.get_collection(sample.name)
                print(f"    Points: {info.points_count}")
                print(f"    Vectors: {info.vectors_count}")
            except:
                pass
        
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def check_api():
    """Verifică status API"""
    print("\n🌐 API STATUS:")
    try:
        response = requests.get("http://localhost:8090/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ API Running (port 8090)")
            print(f"  Overall Status: {data.get('overall_status', 'unknown')}")
            print(f"  Health: {data.get('health_percentage', 0)}%")
            
            services = data.get('services', {})
            for service_name, service_data in services.items():
                status = service_data.get('status', 'unknown')
                icon = "✅" if status == "healthy" else "⚠️" if status == "degraded" else "❌"
                print(f"    {icon} {service_name}: {status}")
                if service_data.get('error'):
                    print(f"      Error: {service_data['error']}")
            
            return True
        else:
            print(f"  ❌ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def check_frontend():
    """Verifică status Frontend"""
    print("\n💻 FRONTEND STATUS:")
    try:
        response = requests.get("http://localhost:5173", timeout=5)
        if response.status_code == 200:
            print("  ✅ Frontend Running (port 5173)")
            return True
        else:
            print(f"  ⚠️ Frontend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Main entry point"""
    print("=" * 80)
    print("🔍 DEBUG STATUS REPORT")
    print("=" * 80)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    results = {
        "MongoDB": check_mongodb(),
        "Qdrant": check_qdrant(),
        "API": check_api(),
        "Frontend": check_frontend()
    }
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY:")
    print("=" * 80)
    for service, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {service}: {'OK' if status else 'FAILED'}")
    
    all_ok = all(results.values())
    print()
    if all_ok:
        print("✅ All systems operational!")
    else:
        print("⚠️ Some systems have issues - check details above")
    
    print("=" * 80)


if __name__ == "__main__":
    main()

