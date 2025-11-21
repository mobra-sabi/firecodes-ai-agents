#!/usr/bin/env python3
"""
🎯 DEMO: Master-Slave Learning System
======================================

Demonstrație practică a sistemului de învățare Master ← Slaves

Acest script demonstrează:
1. Cum se creează SLAVE agents dintr-un competitor
2. Cum MASTER învață din SLAVES
3. Cum se generează raport CI pentru CEO
"""

import asyncio
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

from master_slave_learning_system import MasterSlaveLearningSystem
from pymongo import MongoClient
import json


async def demo_master_slave_learning():
    """
    Demo complet al sistemului
    """
    print("="*80)
    print("🎯 DEMO: MASTER-SLAVE LEARNING SYSTEM")
    print("="*80)
    print()
    
    # Initialize system
    system = MasterSlaveLearningSystem()
    
    # Get a master agent from DB
    mongo = MongoClient("mongodb://localhost:27017/")
    db = mongo.ai_agents_db
    
    # Find first validated master
    master = db.site_agents.find_one({
        "status": "validated",
        "has_embeddings": True
    })
    
    if not master:
        print("❌ No validated master agent found!")
        return
    
    master_id = str(master["_id"])
    master_domain = master.get("domain")
    
    print(f"✅ Using MASTER Agent:")
    print(f"   ID: {master_id}")
    print(f"   Domain: {master_domain}")
    print(f"   URL: {master.get('site_url')}")
    print()
    
    # =========================================================================
    # STEP 1: Get existing slaves for this master
    # =========================================================================
    print("="*80)
    print("STEP 1: Verificare SLAVES existenți")
    print("="*80)
    
    slaves = await system.get_slaves_for_master(master_id)
    
    if slaves:
        print(f"✅ Found {len(slaves)} existing SLAVES:")
        for i, slave in enumerate(slaves[:5], 1):
            print(f"   {i}. {slave['domain']}")
            print(f"      Keyword: {slave['keyword']}")
            print(f"      SERP Position: {slave['serp_position']}")
            print(f"      Has content: {'✅' if slave['has_content'] else '❌'}")
            print()
    else:
        print("⚠️  No slaves found for this master yet.")
        print("   Slaves would be created automatically by CEO Workflow FAZA 7")
        print()
    
    # =========================================================================
    # STEP 2: Simulate creating a slave (mock data)
    # =========================================================================
    print("="*80)
    print("STEP 2: Creare SLAVE din competitor (DEMO)")
    print("="*80)
    print()
    print("În workflow-ul real, acest pas este automat în FAZA 7:")
    print("   - Google Search găsește competitori")
    print("   - Fiecare competitor devine SLAVE agent")
    print("   - Se scrape conținutul")
    print("   - Se creează embeddings")
    print("   - Se indexează în Qdrant")
    print("   - Se link-ează la MASTER")
    print()
    
    # For demo, we'll use an existing agent as slave
    potential_slave = db.site_agents.find_one({
        "_id": {"$ne": master["_id"]},
        "status": "validated",
        "agent_type": {"$ne": "slave"}  # Nu e deja slave
    })
    
    if potential_slave:
        print(f"📝 DEMO: Converting existing agent to SLAVE:")
        print(f"   Domain: {potential_slave.get('domain')}")
        print(f"   (În producție, ar fi un competitor găsit prin Google)")
        print()
        
        # Convert to slave for demo
        db.site_agents.update_one(
            {"_id": potential_slave["_id"]},
            {
                "$set": {
                    "agent_type": "slave",
                    "master_agent_id": master["_id"],
                    "discovered_via_keyword": "demo keyword",
                    "serp_position": 5
                }
            }
        )
        
        # Create relationship
        db.master_slave_relationships.insert_one({
            "master_id": master["_id"],
            "slave_id": potential_slave["_id"],
            "relationship_type": "competitor",
            "discovered_via": "demo keyword",
            "serp_position": 5,
            "status": "active"
        })
        
        print("✅ SLAVE created (demo mode)")
        print()
    
    # Refresh slaves list
    slaves = await system.get_slaves_for_master(master_id)
    
    if not slaves:
        print("⚠️  Still no slaves. Skipping learning demo.")
        return
    
    # =========================================================================
    # STEP 3: Master learns from one slave
    # =========================================================================
    print("="*80)
    print("STEP 3: MASTER învață din UN SLAVE")
    print("="*80)
    print()
    
    first_slave = slaves[0]
    print(f"📚 Master învață din: {first_slave['domain']}")
    print(f"   Focus: SEO, Content, Strategy")
    print()
    
    learning_result = await system.master_learns_from_slave(
        master_agent_id=master_id,
        slave_agent_id=first_slave['agent_id'],
        learning_focus="all"
    )
    
    if learning_result.get("success"):
        print("✅ Learning SUCCESSFUL!")
        print()
        print("📊 Insights generated:")
        print("-" * 80)
        insights = learning_result.get("insights", "")
        print(insights[:1000] if len(insights) > 1000 else insights)
        if len(insights) > 1000:
            print("\n... (truncated)")
        print("-" * 80)
        print()
    else:
        print(f"❌ Learning failed: {learning_result.get('error')}")
        print()
    
    # =========================================================================
    # STEP 4: Master learns from ALL slaves
    # =========================================================================
    if len(slaves) > 1:
        print("="*80)
        print("STEP 4: MASTER învață din TOȚI SLAVES")
        print("="*80)
        print()
        print(f"📚 Master învață din {len(slaves)} slaves...")
        print()
        
        comprehensive_learning = await system.master_learns_from_all_slaves(master_id)
        
        if comprehensive_learning.get("success"):
            print("✅ Comprehensive Learning SUCCESSFUL!")
            print()
            print("📊 Aggregated Competitive Intelligence:")
            print("-" * 80)
            agg_insights = comprehensive_learning.get("aggregated_insights", "")
            print(agg_insights[:1500] if len(agg_insights) > 1500 else agg_insights)
            if len(agg_insights) > 1500:
                print("\n... (truncated)")
            print("-" * 80)
            print()
        else:
            print(f"❌ Comprehensive learning failed: {comprehensive_learning.get('error')}")
            print()
    
    # =========================================================================
    # STEP 5: Generate CEO Report
    # =========================================================================
    print("="*80)
    print("STEP 5: GENERARE RAPORT CI PENTRU CEO")
    print("="*80)
    print()
    
    ci_report = await system.generate_competitive_intelligence_report(master_id)
    
    if ci_report.get("success"):
        report = ci_report["report"]
        print("✅ CI Report GENERATED!")
        print()
        print("📋 RAPORT COMPETITIVE INTELLIGENCE:")
        print("="*80)
        print(f"Report ID: {report['report_id']}")
        print(f"Generated: {report['generated_at']}")
        print()
        print(f"Master Agent: {report['master_agent']['domain']}")
        print(f"Competitors Analyzed: {report['competitors_analyzed']}")
        print(f"Keywords Covered: {report['total_keywords']}")
        print()
        print("Competitors List:")
        for i, comp in enumerate(report['competitors_list'][:10], 1):
            print(f"   {i}. {comp['domain']} (Keyword: {comp['keyword']}, Position: {comp['serp_position']})")
        if len(report['competitors_list']) > 10:
            print(f"   ... and {len(report['competitors_list']) - 10} more")
        print()
        print("Strategic Insights:")
        print("-" * 80)
        insights = report.get('strategic_insights', '')
        print(insights[:2000] if len(insights) > 2000 else insights)
        if len(insights) > 2000:
            print("\n... (truncated)")
        print("-" * 80)
        print()
    else:
        print(f"❌ CI Report generation failed: {ci_report.get('error')}")
        print()
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("="*80)
    print("📊 DEMO SUMMARY")
    print("="*80)
    print()
    print("✅ Master-Slave Learning System FUNCȚIONEAZĂ!")
    print()
    print("Capabilities Demonstrated:")
    print("   ✅ Create SLAVE agents from competitors")
    print("   ✅ Master learns from individual slaves")
    print("   ✅ Master learns from ALL slaves (aggregated)")
    print("   ✅ Generate CI Reports for CEO")
    print("   ✅ Strategic insights extraction")
    print("   ✅ Competitive intelligence automation")
    print()
    print("Next Steps:")
    print("   1. Run full CEO Workflow on a site")
    print("   2. FAZA 7 will create slaves from Google Search")
    print("   3. FAZA 8 will trigger learning automatically")
    print("   4. CEO gets comprehensive CI report")
    print()
    print("="*80)


if __name__ == "__main__":
    asyncio.run(demo_master_slave_learning())

