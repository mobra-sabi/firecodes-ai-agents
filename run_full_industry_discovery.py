#!/usr/bin/env python3
"""
🏭 FULL INDUSTRY DISCOVERY WORKFLOW
====================================
Workflow complet pentru descoperirea COMPLETĂ a industriei:

1. DeepSeek extrage subdomenii din site master
2. Generează 10-15 keywords per subdomeniu
3. Google Search pentru TOATE keywords (top 10 per keyword)
4. Deduplicare automată + tracking keywords/positions
5. Creare SLAVE agents pentru TOȚI competitorii
6. Master învață din toți slaves
7. Raport CI complet

Expected: 100-200+ slaves pentru un site tipic!
"""

import asyncio
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Any
import json

from ceo_master_workflow import CEOMasterWorkflow
from enhanced_competitor_discovery import EnhancedCompetitorDiscovery


def print_banner(text: str, emoji: str = "🎯"):
    """Print nice banner"""
    line = "=" * 80
    print(f"\n{line}")
    print(f"{emoji} {text}")
    print(f"{line}\n")


async def run_full_industry_discovery(
    master_agent_id: str,
    parallel_gpu: int = 8,
    results_per_keyword: int = 10
):
    """
    Rulează workflow complet de descoperire industrie
    """
    print_banner("FULL INDUSTRY DISCOVERY WORKFLOW", "🏭")
    
    workflow = CEOMasterWorkflow()
    discovery = EnhancedCompetitorDiscovery()
    
    # Get master info
    master = workflow.db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
    if not master:
        print(f"❌ Master agent not found: {master_agent_id}")
        return
    
    print(f"✅ MASTER AGENT:")
    print(f"   Domain: {master.get('domain')}")
    print(f"   URL: {master.get('site_url')}")
    print(f"   Chunks: {master.get('chunks_indexed')}")
    print()
    
    # =========================================================================
    # STEP 1: DeepSeek Decompose Site → Subdomenii + Keywords
    # =========================================================================
    print_banner("STEP 1: DeepSeek Decompose Site", "📍")
    
    try:
        phase4_result = await workflow._phase4_deepseek_decompose_site(master_agent_id)
        
        if not phase4_result.get("success"):
            raise Exception(phase4_result.get("error", "Failed"))
        
        subdomains = phase4_result.get("subdomains", [])
        overall_keywords = phase4_result.get("overall_keywords", [])
        
        print(f"✅ Site Decomposed!")
        print(f"   Subdomenii: {len(subdomains)}")
        print(f"   Overall Keywords: {len(overall_keywords)}")
        print()
        
        # Collect ALL keywords from ALL subdomains
        all_keywords = set(overall_keywords)
        
        print("📋 Subdomenii identificate:")
        for i, subdomain in enumerate(subdomains, 1):
            name = subdomain.get("name", "Unknown")
            kws = subdomain.get("keywords", [])
            all_keywords.update(kws)
            print(f"   {i}. {name}: {len(kws)} keywords")
        
        all_keywords = list(all_keywords)
        print()
        print(f"📊 TOTAL KEYWORDS: {len(all_keywords)}")
        print(f"   Expected competitors: ~{len(all_keywords) * results_per_keyword}")
        print(f"   Expected unique: ~{len(all_keywords) * results_per_keyword // 3}-{len(all_keywords) * results_per_keyword // 2}")
        print()
        
    except Exception as e:
        print(f"❌ Step 1 Failed: {e}")
        print(f"⚠️  Using fallback keywords")
        all_keywords = [
            "renovare apartament", "pret renovare", "firma renovari",
            "amenajari interioare", "constructii case", "firma constructii",
            "renovare la cheie", "proiect renovare", "design interior",
            "renovari complete", "constructii rezidentiale", "renovari bucuresti"
        ]
    
    # Show sample keywords
    print("🔑 Sample Keywords (first 10):")
    for i, kw in enumerate(all_keywords[:10], 1):
        print(f"   {i}. {kw}")
    if len(all_keywords) > 10:
        print(f"   ... and {len(all_keywords) - 10} more")
    print()
    
    # =========================================================================
    # STEP 2: Enhanced Competitor Discovery (Google Search)
    # =========================================================================
    print_banner("STEP 2: Enhanced Competitor Discovery", "🔍")
    
    print(f"🔍 Searching Google for {len(all_keywords)} keywords...")
    print(f"   Results per keyword: {results_per_keyword}")
    print(f"   This may take a few minutes...")
    print()
    
    discovery_data = await discovery.discover_all_competitors(
        master_agent_id=master_agent_id,
        keywords=all_keywords,
        results_per_keyword=results_per_keyword
    )
    
    # Save discovery report
    discovery.save_discovery_report(master_agent_id, discovery_data)
    
    # Print summary
    discovery.print_discovery_summary(discovery_data)
    
    # Get competitors list
    competitors_list = discovery_data["competitors"]
    
    print()
    print(f"✅ Discovery Complete!")
    print(f"   Unique Competitors: {len(competitors_list)}")
    print()
    
    # =========================================================================
    # STEP 3: Create SLAVE Agents for ALL Competitors (Parallel GPU)
    # =========================================================================
    print_banner("STEP 3: Create SLAVE Agents (Parallel GPU)", "🤖")
    
    print(f"🤖 Creating {len(competitors_list)} SLAVE agents...")
    print(f"   Parallel GPU processing: {parallel_gpu} agents at a time")
    print(f"   This will take ~{len(competitors_list) * 2 // parallel_gpu} minutes")
    print()
    
    # Prepare competitors for workflow
    competitors_for_workflow = []
    for comp in competitors_list:
        competitors_for_workflow.append({
            "url": comp["url"],
            "domain": comp["domain"],
            "keyword": ", ".join(comp["found_for_keywords"][:3]),  # First 3 keywords
            "serp_position": comp["average_position"],
            "title": comp["title"],
            "snippet": f"Found for {comp['keyword_count']} keywords, avg position: {comp['average_position']}",
            "metadata": {
                "found_for_keywords": comp["found_for_keywords"],
                "keyword_count": comp["keyword_count"],
                "serp_positions": comp["serp_positions"],
                "average_position": comp["average_position"],
                "best_position": comp["best_position"]
            }
        })
    
    # Create slaves in parallel
    phase7_result = await workflow._phase7_create_competitor_agents_parallel(
        competitors=competitors_for_workflow,
        parallel_count=parallel_gpu,
        master_agent_id=master_agent_id
    )
    
    slave_ids = phase7_result.get("agent_ids", [])
    failed = phase7_result.get("failed", [])
    
    print()
    print(f"✅ STEP 3 COMPLETE!")
    print(f"   Slaves Created: {len(slave_ids)}")
    print(f"   Failed: {len(failed)}")
    print()
    
    if slave_ids:
        print("📋 First 10 Slaves Created:")
        for i, slave_id in enumerate(slave_ids[:10], 1):
            slave = workflow.db.site_agents.find_one({"_id": ObjectId(slave_id)})
            if slave:
                print(f"   {i}. {slave.get('domain')} ({slave.get('chunks_indexed', 0)} chunks)")
        if len(slave_ids) > 10:
            print(f"   ... and {len(slave_ids) - 10} more slaves")
        print()
    
    # =========================================================================
    # STEP 4: Master Learning + CI Report
    # =========================================================================
    print_banner("STEP 4: Master Learning + CI Report", "🧠")
    
    print(f"🧠 Master învață din {len(slave_ids)} slaves...")
    print(f"   This may take ~{len(slave_ids) * 10 // 60} minutes")
    print()
    
    phase8_result = await workflow._phase8_create_master_slave_orgchart(
        master_agent_id=master_agent_id,
        slave_agent_ids=slave_ids
    )
    
    if phase8_result.get("success"):
        print(f"✅ STEP 4 COMPLETE!")
        print()
        
        # Get total slaves (including old ones)
        total_slaves = workflow.db.master_slave_relationships.count_documents({
            "master_id": ObjectId(master_agent_id),
            "status": "active"
        })
        
        print(f"🏢 Organizational Chart:")
        print(f"   MASTER: {master.get('domain')}")
        print(f"   └── {total_slaves} SLAVES")
        print()
        
        if phase8_result.get("learning_completed"):
            print(f"✅ Learning: COMPLETED")
            print(f"   Learning Record ID: {phase8_result.get('learning_record_id')}")
        
        if phase8_result.get("ci_report_id"):
            print(f"✅ CI Report: GENERATED")
            print(f"   Report ID: {phase8_result.get('ci_report_id')}")
        
        print()
    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print_banner("WORKFLOW COMPLETE", "🎉")
    
    # Calculate total chunks
    total_chunks = master.get('chunks_indexed', 0)
    all_slaves = list(workflow.db.site_agents.find({
        "master_agent_id": ObjectId(master_agent_id),
        "agent_type": "slave"
    }))
    
    for slave in all_slaves:
        total_chunks += slave.get('chunks_indexed', 0)
    
    print("📊 FINAL STATISTICS:")
    print(f"   Master Agent: {master.get('domain')}")
    print(f"   Total Keywords Searched: {len(all_keywords)}")
    print(f"   Google Searches: {discovery_data['total_searches']}")
    print(f"   Total Results: {discovery_data['total_results']}")
    print(f"   Unique Competitors: {discovery_data['unique_competitors']}")
    print(f"   NEW Slaves Created: {len(slave_ids)}")
    print(f"   TOTAL Slaves: {len(all_slaves)}")
    print(f"   Failed: {len(failed)}")
    print(f"   Total Chunks (Master + Slaves): {total_chunks:,}")
    print()
    
    print("🗄️  Data Saved in MongoDB:")
    print("   - site_agents (master + slaves)")
    print("   - master_slave_relationships")
    print("   - competitor_discovery_reports")
    print("   - master_learnings")
    print("   - competitive_intelligence_reports")
    print("   - agent_hierarchies")
    print()
    
    print("🌐 View Results:")
    print("   Dashboard: https://graduated-missed-festivals-wearing.trycloudflare.com/static/competitive_intelligence_dashboard.html")
    print()
    
    print("="*80)


async def main():
    """
    Run full industry discovery for daibau.ro
    """
    MASTER_ID = "6913cc489349b25c3690e9a3"  # daibau.ro
    
    await run_full_industry_discovery(
        master_agent_id=MASTER_ID,
        parallel_gpu=8,
        results_per_keyword=10
    )


if __name__ == "__main__":
    asyncio.run(main())

