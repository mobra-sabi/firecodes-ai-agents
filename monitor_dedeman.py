#!/usr/bin/env python3
"""
📊 DEDEMAN AGENT MONITOR
Real-time monitoring pentru crearea agentului
"""

import time
import os
from pymongo import MongoClient

def monitor_dedeman():
    """Monitor dedeman.ro agent creation"""
    
    mongo = MongoClient("mongodb://localhost:27017/")
    db = mongo.ai_agents_db
    
    print("=" * 80)
    print("📊 DEDEMAN.RO AGENT MONITOR")
    print("=" * 80)
    print("")
    
    # Check for agent
    agent = db.site_agents.find_one({"domain": "dedeman.ro"})
    
    if not agent:
        print("⏳ Agent not yet created...")
        print("   Process is likely scraping pages...")
        print("")
        print("🔍 Checking log file...")
        
        if os.path.exists('/tmp/dedeman_agent.log'):
            print("")
            print("=" * 80)
            print("📋 LAST 30 LINES OF LOG:")
            print("=" * 80)
            os.system('tail -30 /tmp/dedeman_agent.log')
        else:
            print("   ⚠️ Log file not found")
        
        return False
    
    # Agent exists
    agent_id = str(agent['_id'])
    
    print(f"✅ AGENT FOUND!")
    print(f"   ID: {agent_id}")
    print(f"   Domain: {agent.get('domain', 'N/A')}")
    print(f"   Status: {agent.get('status', 'N/A')}")
    print("")
    
    print("📊 AGENT DATA:")
    print(f"   Pages indexed: {agent.get('pages_indexed', 0):,}")
    print(f"   Chunks indexed: {agent.get('chunks_indexed', 0):,}")
    print(f"   Has embeddings: {agent.get('has_embeddings', False)}")
    print(f"   Validation passed: {agent.get('validation_passed', False)}")
    print("")
    
    # Check CI progress
    serp = db.serp_discovery_results.find_one({"agent_id": agent_id})
    relationships = db.agent_relationships.count_documents({"master_id": agent['_id']})
    improvement = db.improvement_plans.find_one({"master_agent_id": agent_id})
    actionable = db.actionable_plans.find_one({"master_agent_id": agent_id})
    
    print("🧠 COMPETITIVE INTELLIGENCE:")
    print(f"   SERP Discovery: {'✅' if serp else '⏳ Pending'}")
    if serp:
        print(f"      Keywords: {serp.get('total_keywords', 0)}")
        print(f"      Competitors: {len(serp.get('potential_competitors', []))}")
    
    print(f"   Slave Agents: {'✅' if relationships > 0 else '⏳ Pending'}")
    if relationships > 0:
        print(f"      Count: {relationships}")
    
    print(f"   Improvement Plan: {'✅' if improvement else '⏳ Pending'}")
    print(f"   Actionable Plan: {'✅' if actionable else '⏳ Pending'}")
    print("")
    
    # Links
    print("🔗 LINKS:")
    print(f"   Dashboard: http://100.66.157.27:5000/static/competitive_intelligence_dashboard.html?agent={agent_id}")
    print(f"   Chat: http://100.66.157.27:5000/static/chat.html?agent_id={agent_id}")
    print(f"   Control Panel: http://100.66.157.27:5000/static/master_control_panel.html")
    print("")
    
    # Completion status
    if serp and relationships > 0 and improvement and actionable:
        print("=" * 80)
        print("🎉 AGENT CREATION COMPLETED!")
        print("=" * 80)
        return True
    else:
        print("=" * 80)
        print("⏳ STILL PROCESSING...")
        print("=" * 80)
        return False

if __name__ == "__main__":
    while True:
        os.system('clear')
        completed = monitor_dedeman()
        
        if completed:
            print("\n✅ Monitoring complete!")
            break
        
        print("\n⏳ Refreshing in 30 seconds... (Ctrl+C to stop)")
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped.")
            break

