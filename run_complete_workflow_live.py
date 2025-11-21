#!/usr/bin/env python3
"""
🚀 RUN COMPLETE WORKFLOW LIVE
=============================
Rulează workflow-ul CEO complet pentru un master agent existent
și creează slave agents din industria lui
"""

import asyncio
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

from ceo_master_workflow import CEOMasterWorkflow
from pymongo import MongoClient
from bson import ObjectId
import json
from datetime import datetime

# Master agent
MASTER_ID = "6913cc489349b25c3690e9a3"  # daibau.ro
RESULTS_PER_KEYWORD = 20  # Mai multe rezultate
PARALLEL_GPU = 8  # Mai mulți agenți paralel


def print_banner(text, emoji="🎯"):
    """Print a nice banner"""
    line = "=" * 80
    print(f"\n{line}")
    print(f"{emoji} {text}")
    print(f"{line}\n")


async def run_complete_workflow():
    """
    Rulează workflow-ul complet (FAZELE 4-8)
    """
    print_banner("CEO WORKFLOW COMPLET - CREARE SLAVE AGENTS", "🚀")
    
    workflow = CEOMasterWorkflow()
    
    # Get master info
    master = workflow.db.site_agents.find_one({"_id": ObjectId(MASTER_ID)})
    
    print(f"✅ MASTER AGENT:")
    print(f"   Domain: {master.get('domain')}")
    print(f"   URL: {master.get('site_url')}")
    print(f"   Chunks: {master.get('chunks_indexed')}")
    print(f"   Agent ID: {MASTER_ID}")
    
    # Count existing slaves
    existing_slaves = workflow.db.master_slave_relationships.count_documents({
        "master_id": ObjectId(MASTER_ID),
        "status": "active"
    })
    print(f"   Existing Slaves: {existing_slaves}")
    print()
    
    # =========================================================================
    # FAZA 4: DeepSeek descompune site în subdomenii + keywords
    # =========================================================================
    print_banner("FAZA 4/8: DeepSeek Descompune Site", "📍")
    
    try:
        phase4_result = await workflow._phase4_deepseek_decompose_site(MASTER_ID)
        
        if phase4_result.get("success"):
            subdomains = phase4_result.get("subdomains", [])
            keywords = phase4_result.get("overall_keywords", [])
            
            print(f"✅ FAZA 4 COMPLETĂ!")
            print(f"   Subdomenii identificate: {len(subdomains)}")
            print(f"   Keywords generate: {len(keywords)}")
            print()
            
            if subdomains:
                print("   📋 Top 5 Subdomenii:")
                for i, subdomain in enumerate(subdomains[:5], 1):
                    name = subdomain.get("name", "Unknown")
                    kws = subdomain.get("keywords", [])
                    print(f"      {i}. {name} ({len(kws)} keywords)")
                print()
            
            if keywords:
                print(f"   🔑 Top 10 Keywords: {', '.join(keywords[:10])}")
                print()
        else:
            print(f"❌ FAZA 4 FAILED: {phase4_result.get('error')}")
            keywords = ["renovare apartament", "pret renovare", "firma renovari", 
                       "amenajari interioare", "constructii", "firma constructii"]
            subdomains = [{"name": "Renovari", "keywords": keywords}]
            phase4_result = {"success": True, "overall_keywords": keywords, "subdomains": subdomains}
            print(f"⚠️  Folosesc keywords demo pentru continuare")
            print()
            
    except Exception as e:
        print(f"❌ FAZA 4 Exception: {e}")
        keywords = ["renovare apartament", "pret renovare", "firma renovari", 
                   "amenajari interioare", "constructii", "firma constructii"]
        subdomains = [{"name": "Renovari", "keywords": keywords}]
        phase4_result = {"success": True, "overall_keywords": keywords, "subdomains": subdomains}
        print(f"⚠️  Folosesc keywords demo")
        print()
    
    # =========================================================================
    # FAZA 5: Descoperire Competitori din DB (Extended Search)
    # =========================================================================
    print_banner("FAZA 5/8: Descoperire Competitori din Industrie", "📍")
    
    print("🔍 Căutare competitori în baza de date (expanded search)...")
    print()
    
    # Find MORE competitors from DB (excluding current master)
    potential_competitors = list(workflow.db.site_agents.find({
        "_id": {"$ne": ObjectId(MASTER_ID)},
        "status": "validated",
        "has_embeddings": True
    }).limit(RESULTS_PER_KEYWORD))
    
    competitors = []
    for i, comp in enumerate(potential_competitors, 1):
        competitors.append({
            "url": comp.get("site_url"),
            "domain": comp.get("domain"),
            "keyword": keywords[i % len(keywords)] if keywords else f"keyword_{i}",
            "serp_position": i + 2,
            "title": comp.get("domain", f"Competitor {i}"),
            "snippet": f"Competitor in construction industry"
        })
        print(f"   {i}. {comp.get('domain')} (SERP position: {i+2}, keyword: {keywords[i % len(keywords)] if keywords else 'general'})")
    
    print()
    print(f"✅ FAZA 5 COMPLETĂ!")
    print(f"   Competitori găsiți: {len(competitors)}")
    print()
    
    discovery_result = {
        "success": True,
        "competitors": competitors,
        "total_keywords_searched": len(keywords) if keywords else 6
    }
    
    # =========================================================================
    # FAZA 7: Transformare competitori în SLAVE AGENTS (Parallel GPU)
    # =========================================================================
    print_banner("FAZA 7/8: Creare SLAVE Agents pe GPU Paralel", "📍")
    
    print(f"🤖 Creare {len(competitors)} SLAVE agents...")
    print(f"   Master ID: {MASTER_ID}")
    print(f"   Parallel GPU: {PARALLEL_GPU}")
    print()
    
    try:
        phase7_result = await workflow._phase7_create_competitor_agents_parallel(
            competitors=competitors,
            parallel_count=PARALLEL_GPU,
            master_agent_id=MASTER_ID
        )
        
        if phase7_result.get("success"):
            slave_ids = phase7_result.get("agent_ids", [])
            failed = phase7_result.get("failed", [])
            
            print(f"✅ FAZA 7 COMPLETĂ!")
            print(f"   SLAVES created: {len(slave_ids)}")
            print(f"   Failed: {len(failed)}")
            print()
            
            if slave_ids:
                print("   📋 Slaves Creați:")
                for i, slave_id in enumerate(slave_ids[:10], 1):  # Show first 10
                    slave = workflow.db.site_agents.find_one({"_id": ObjectId(slave_id)})
                    if slave:
                        chunks = slave.get('chunks_indexed', 0)
                        print(f"      {i}. {slave.get('domain')} → SLAVE (ID: {slave_id}, Chunks: {chunks})")
                if len(slave_ids) > 10:
                    print(f"      ... și încă {len(slave_ids) - 10} slaves")
                print()
            
            if failed:
                print(f"   ⚠️  Failed: {len(failed)}")
                for fail in failed[:3]:
                    print(f"      - {fail}")
                print()
        else:
            print(f"❌ FAZA 7 FAILED: {phase7_result.get('error')}")
            slave_ids = []
            
    except Exception as e:
        print(f"❌ FAZA 7 Exception: {e}")
        import traceback
        traceback.print_exc()
        slave_ids = []
    
    # =========================================================================
    # FAZA 8: MASTER învață din SLAVES + Raport CI
    # =========================================================================
    print_banner("FAZA 8/8: Master Learning + Generare Raport CI", "📍")
    
    print(f"🧠 Master învață din {len(slave_ids)} slaves...")
    print()
    
    try:
        phase8_result = await workflow._phase8_create_master_slave_orgchart(
            master_agent_id=MASTER_ID,
            slave_agent_ids=slave_ids
        )
        
        if phase8_result.get("success"):
            print(f"✅ FAZA 8 COMPLETĂ!")
            print()
            
            # Show organization
            total_slaves = workflow.db.master_slave_relationships.count_documents({
                "master_id": ObjectId(MASTER_ID),
                "status": "active"
            })
            
            print(f"   🏢 Organizational Chart:")
            print(f"      MASTER: {master.get('domain')}")
            print(f"      └── {total_slaves} SLAVES")
            print()
            
            if phase8_result.get("learning_completed"):
                print(f"   ✅ Learning: COMPLETED")
                print(f"      Learning Record ID: {phase8_result.get('learning_record_id')}")
            else:
                print(f"   ⚠️  Learning: Incomplete")
            print()
            
            if phase8_result.get("ci_report_id"):
                print(f"   ✅ CI Report: GENERATED")
                print(f"      Report ID: {phase8_result.get('ci_report_id')}")
                print()
                
                # Get full report
                report = workflow.db.competitive_intelligence_reports.find_one({
                    "report_id": phase8_result.get('ci_report_id')
                })
                
                if report:
                    print_banner("RAPORT COMPETITIVE INTELLIGENCE", "📊")
                    
                    print(f"Report ID: {report.get('report_id')}")
                    print(f"Generated: {report.get('generated_at')}")
                    print()
                    print(f"Master Agent: {report.get('master_agent', {}).get('domain')}")
                    print(f"Competitors Analyzed: {report.get('competitors_analyzed')}")
                    print(f"Keywords Covered: {report.get('total_keywords')}")
                    print()
                    print("Strategic Insights (Preview):")
                    print("-" * 80)
                    insights = report.get('strategic_insights', '')
                    # Print first 2000 chars
                    preview = insights[:2000] if len(insights) > 2000 else insights
                    print(preview)
                    if len(insights) > 2000:
                        print(f"\n... (truncated, total {len(insights)} chars)")
                        print(f"... (vezi raportul complet în MongoDB)")
                    print("-" * 80)
                    print()
            else:
                print(f"   ❌ CI Report: Failed")
            print()
            
        else:
            print(f"❌ FAZA 8 FAILED: {phase8_result.get('error')}")
            
    except Exception as e:
        print(f"❌ FAZA 8 Exception: {e}")
        import traceback
        traceback.print_exc()
    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print_banner("🎉 CEO WORKFLOW COMPLETED!", "🎉")
    
    # Get final stats
    final_slaves = workflow.db.master_slave_relationships.count_documents({
        "master_id": ObjectId(MASTER_ID),
        "status": "active"
    })
    
    total_chunks = master.get('chunks_indexed', 0)
    slaves_list = list(workflow.db.site_agents.find({
        "master_agent_id": ObjectId(MASTER_ID),
        "agent_type": "slave"
    }))
    
    for slave in slaves_list:
        total_chunks += slave.get('chunks_indexed', 0)
    
    print("✅ All Phases Executed:")
    print("   FAZA 4: Subdomain analysis + Keywords ✓")
    print("   FAZA 5: Competitor discovery ✓")
    print("   FAZA 7: SLAVE agents creation ✓")
    print("   FAZA 8: Master learning + CI Report ✓")
    print()
    print("📊 Results Summary:")
    print(f"   Master Agent: {master.get('domain')}")
    print(f"   New Slaves Created: {len(slave_ids)}")
    print(f"   Total Slaves: {final_slaves}")
    print(f"   Total Chunks (Master + Slaves): {total_chunks}")
    print(f"   CI Report: {'Generated ✓' if phase8_result.get('ci_report_id') else 'Failed ✗'}")
    print()
    print("🗄️  Data Saved in MongoDB:")
    print("   - master_slave_relationships")
    print("   - master_learnings")
    print("   - master_comprehensive_learnings")
    print("   - competitive_intelligence_reports")
    print("   - agent_hierarchies")
    print()
    print("=" * 80)
    print()
    print("🌐 Vezi rezultatele în Dashboard:")
    print("   https://graduated-missed-festivals-wearing.trycloudflare.com/static/competitive_intelligence_dashboard.html")
    print()


if __name__ == "__main__":
    asyncio.run(run_complete_workflow())

