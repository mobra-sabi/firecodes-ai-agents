#!/usr/bin/env python3
"""
🏭 CONTINUOUS INDUSTRY INDEXER
Indexează complet o industrie cu agenți paraleli pe toate GPU-urile
DeepSeek决定când industria e complet indexată
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Set
import json
from pymongo import MongoClient
from bson import ObjectId
import time
import multiprocessing

sys.path.insert(0, '/srv/hf/ai_agents')

from ceo_master_workflow import CEOMasterWorkflow
from llm_orchestrator import get_orchestrator

# Brave Search function
def brave_search(query: str, count: int = 10):
    """Wrapper pentru Brave Search - returnează liste de dict-uri cu url, title, snippet"""
    try:
        from tools.serp_client import _brave_search
        urls = _brave_search(query, count=count)
        # Convert to format expected (list of dicts)
        return [{"url": url, "title": "", "snippet": ""} for url in urls]
    except Exception as e:
        print(f"⚠️  Brave Search error: {e}")
        # Fallback: returnează listă goală
        return []

# Configurare
INDUSTRY = "Construcții și Renovări România"
MAX_PARALLEL_AGENTS = 8  # Agenți paraleli simultan
GPU_IDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # Toate GPU-urile
RESULTS_PER_KEYWORD = 15  # Mai multe rezultate pentru descoperire
CHECK_INTERVAL = 300  # Check coverage每 5 minute

# MongoDB - Use MongoDB 8.0 on port 27017 (with real data)
mongo = MongoClient('mongodb://localhost:27017/')
db = mongo.ai_agents_db

# LLM
llm = get_orchestrator()

# Stats globale
stats = {
    "industry": INDUSTRY,
    "started_at": datetime.now(timezone.utc).isoformat(),
    "total_agents_created": 0,
    "total_sites_discovered": 0,
    "total_subdomains_identified": 0,
    "total_keywords_discovered": 0,
    "coverage_percentage": 0.0,
    "status": "running",
    "current_phase": "initialization",
    "agents_in_progress": [],
    "completed_agents": [],
    "discovered_sites": set(),
    "indexed_sites": set(),
    "last_coverage_analysis": None,
    "activity_log": []
}

def save_stats():
    """Salvează stats în JSON pentru monitoring"""
    try:
        export_stats = stats.copy()
        # Convert sets to lists for JSON
        export_stats['discovered_sites'] = list(stats['discovered_sites'])
        export_stats['indexed_sites'] = list(stats['indexed_sites'])
        
        with open('/srv/hf/ai_agents/static/indexing_stats.json', 'w') as f:
            json.dump(export_stats, f, indent=2)
    except Exception as e:
        pass  # Silent fail

def add_log(message, log_type="info"):
    """Adaugă entry în activity log"""
    stats['activity_log'].append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "message": message,
        "type": log_type
    })
    # Keep only last 100
    if len(stats['activity_log']) > 100:
        stats['activity_log'] = stats['activity_log'][-100:]
    save_stats()


def print_banner():
    """Banner inițial"""
    os.system('clear')
    print("="*80)
    print("🏭 CONTINUOUS INDUSTRY INDEXER - LIVE MONITORING")
    print("="*80)
    print(f"🎯 Industry: {INDUSTRY}")
    print(f"🔥 GPU Count: {len(GPU_IDS)}")
    print(f"⚡ Max Parallel: {MAX_PARALLEL_AGENTS}")
    print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
    print("="*80)
    print()


def print_stats():
    """Afișează statistici în timp real"""
    os.system('clear')
    print("="*80)
    print(f"🏭 INDUSTRY INDEXER - {INDUSTRY}")
    print("="*80)
    print(f"⏰ Running since: {stats['started_at'][:19]}")
    print(f"📊 Phase: {stats['current_phase']}")
    print()
    print("📈 PROGRESS:")
    print(f"   Agents Created:       {stats['total_agents_created']}")
    print(f"   Sites Discovered:     {stats['total_sites_discovered']}")
    print(f"   Sites Indexed:        {len(stats['indexed_sites'])}")
    print(f"   Subdomains Found:     {stats['total_subdomains_identified']}")
    print(f"   Keywords Discovered:  {stats['total_keywords_discovered']}")
    print(f"   Coverage:             {stats['coverage_percentage']:.1f}%")
    print()
    print("🔥 ACTIVE AGENTS:")
    for agent in stats['agents_in_progress'][-5:]:  # Last 5
        print(f"   • {agent}")
    print()
    print(f"✅ Completed: {len(stats['completed_agents'])}")
    print("="*80)
    print()


async def ask_deepseek_coverage(discovered_sites: Set[str], indexed_sites: Set[str], 
                                 subdomains: List[str], keywords: List[str]) -> Dict:
    """
    Întreabă DeepSeek dacă industria e complet indexată
    """
    prompt = f"""Analizează coverage-ul industriei "{INDUSTRY}".

SITE-URI DESCOPERITE: {len(discovered_sites)} total
SITE-URI INDEXATE: {len(indexed_sites)} total

SUBDOMENII IDENTIFICATE ({len(subdomains)}):
{', '.join(list(set(subdomains))[:50])}

KEYWORDS DESCOPERITE ({len(keywords)}):
{', '.join(list(set(keywords))[:100])}

TASK:
1. Evaluează dacă coverage-ul este complet pentru această industrie în România
2. Identifică subdomenii/segmente majore care LIPSESC
3. Propune keywords noi pentru descoperire dacă coverage < 90%
4. Determină % coverage estimat (0-100)

Răspunde JSON:
{{
  "coverage_percentage": 0-100,
  "is_complete": true/false,
  "missing_segments": ["segment1", "segment2"],
  "new_keywords_to_explore": ["keyword1", "keyword2"],
  "recommendation": "continue/stop",
  "reasoning": "De ce e complet sau ce lipsește"
}}
"""
    
    try:
        response = await llm.chat(
            messages=[
                {"role": "system", "content": "Ești expert în analiza coverage-ului de piață și indexare industrială."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        if isinstance(response, dict) and response.get("success"):
            content = response.get("content")
            if isinstance(content, str):
                return json.loads(content)
            return content
        
        return {
            "coverage_percentage": 50.0,
            "is_complete": False,
            "missing_segments": [],
            "new_keywords_to_explore": [],
            "recommendation": "continue",
            "reasoning": "DeepSeek API error"
        }
    
    except Exception as e:
        print(f"❌ Error asking DeepSeek: {e}")
        return {
            "coverage_percentage": 50.0,
            "is_complete": False,
            "recommendation": "continue"
        }


async def discover_initial_sites(industry: str, initial_keywords: List[str]) -> List[str]:
    """
    Descoperă site-uri inițiale pentru industrie
    """
    print(f"🔍 Discovering initial sites for: {industry}")
    print(f"   Using {len(initial_keywords)} seed keywords")
    
    discovered = set()
    
    for keyword in initial_keywords:
        try:
            results = brave_search(f"{keyword} România", count=RESULTS_PER_KEYWORD)
            for result in results:
                url = result.get("url", "")
                if url and url.startswith("http"):
                    discovered.add(url)
            
            print(f"   '{keyword}': {len(results)} results")
            time.sleep(1)  # Rate limiting
        
        except Exception as e:
            print(f"   ⚠️ Error searching '{keyword}': {e}")
    
    sites = list(discovered)
    print(f"✅ Discovered {len(sites)} unique sites")
    return sites


async def create_agent_batch(sites: List[str], batch_id: int) -> List[str]:
    """
    Creează batch de agenți în paralel
    """
    print(f"\n🚀 BATCH #{batch_id}: Creating {len(sites)} agents in parallel")
    
    workflow = CEOMasterWorkflow()
    created_agents = []
    
    # Create agents sequentially for now (parallel causing issues with GPU)
    for i, site in enumerate(sites, 1):
        try:
            stats['current_phase'] = f"Batch {batch_id}: Agent {i}/{len(sites)}"
            stats['agents_in_progress'].append(f"{site} (batch {batch_id})")
            print_stats()
            
            print(f"   [{i}/{len(sites)}] Creating agent: {site}")
            
            result = await workflow.execute_full_workflow(
                site_url=site,
                results_per_keyword=RESULTS_PER_KEYWORD,
                parallel_gpu_agents=2  # Moderate parallelism
            )
            
            agent_id = result.get("phases", {}).get("phase1_master_agent", {}).get("agent_id")
            
            if agent_id:
                created_agents.append(agent_id)
                stats['total_agents_created'] += 1
                stats['indexed_sites'].add(site)
                stats['completed_agents'].append(site)
                
                # Extract stats from result
                phase4 = result.get("phases", {}).get("phase4_deepseek_decomposition", {})
                if phase4.get("success"):
                    analysis_data = phase4.get("analysis_data", {})
                    subdomains = analysis_data.get("subdomains", [])
                    overall_keywords = analysis_data.get("overall_keywords", [])
                    
                    stats['total_subdomains_identified'] += len(subdomains)
                    stats['total_keywords_discovered'] += len(overall_keywords)
                    
                    # Add to discovered sets
                    for sd in subdomains:
                        for kw in sd.get("keywords", []):
                            # Could discover new sites from these keywords
                            pass
                
                print(f"   ✅ Agent created: {agent_id}")
                add_log(f"✅ Agent created: {site} → {len(subdomains)} subdomains, {len(overall_keywords)} keywords", "success")
                save_stats()
            else:
                print(f"   ⚠️ Failed to create agent for {site}")
            
            # Remove from in_progress
            stats['agents_in_progress'] = [a for a in stats['agents_in_progress'] if site not in a]
            print_stats()
        
        except Exception as e:
            print(f"   ❌ Error creating agent for {site}: {e}")
            stats['agents_in_progress'] = [a for a in stats['agents_in_progress'] if site not in a]
    
    return created_agents


async def continuous_indexing():
    """
    Loop principal de indexare continuă
    """
    print_banner()
    
    # Initial seed keywords
    seed_keywords = [
        "firma constructii",
        "renovari apartamente",
        "constructii case",
        "amenajari interioare",
        "firma zugraveli",
        "instalatii sanitare",
        "electricieni",
        "firma amenajari",
        "constructii comerciale",
        "renovari blocuri"
    ]
    
    # Phase 1: Discover initial sites
    stats['current_phase'] = "Initial Discovery"
    add_log(f"🔍 Starting discovery for industry: {INDUSTRY}")
    print_stats()
    
    discovered_sites = await discover_initial_sites(INDUSTRY, seed_keywords)
    stats['total_sites_discovered'] = len(discovered_sites)
    stats['discovered_sites'] = set(discovered_sites)
    add_log(f"✅ Discovered {len(discovered_sites)} sites", "success")
    
    print_stats()
    save_stats()
    
    # Phase 2: Continuous indexing loop
    batch_id = 1
    
    while True:
        # Get sites to index (not yet indexed)
        sites_to_index = list(stats['discovered_sites'] - stats['indexed_sites'])
        
        if not sites_to_index:
            print("\n🔍 No more sites to index. Checking coverage...")
        
        # Check coverage with DeepSeek
        all_subdomains = []
        all_keywords = []
        
        # Collect from MongoDB
        agents = list(db.site_agents.find({}))
        for agent in agents:
            comp_analysis = db.competitive_analysis.find_one({"agent_id": agent["_id"]})
            if comp_analysis:
                data = comp_analysis.get("analysis_data", {})
                all_subdomains.extend([sd.get("name", "") for sd in data.get("subdomains", [])])
                all_keywords.extend(data.get("overall_keywords", []))
        
        stats['current_phase'] = "Coverage Check (DeepSeek)"
        add_log("🤖 Asking DeepSeek for coverage analysis...")
        print_stats()
        
        coverage_result = await ask_deepseek_coverage(
            stats['discovered_sites'],
            stats['indexed_sites'],
            all_subdomains,
            all_keywords
        )
        
        stats['coverage_percentage'] = coverage_result.get("coverage_percentage", 0.0)
        stats['last_coverage_analysis'] = coverage_result
        add_log(f"📊 Coverage: {stats['coverage_percentage']:.1f}%", "success")
        save_stats()
        
        print("\n" + "="*80)
        print("🤖 DEEPSEEK COVERAGE ANALYSIS:")
        print("="*80)
        print(f"Coverage: {coverage_result.get('coverage_percentage', 0)}%")
        print(f"Complete: {coverage_result.get('is_complete', False)}")
        print(f"Recommendation: {coverage_result.get('recommendation', 'continue')}")
        print(f"Reasoning: {coverage_result.get('reasoning', 'N/A')}")
        print()
        
        if coverage_result.get("missing_segments"):
            print("Missing Segments:")
            for seg in coverage_result.get("missing_segments", [])[:5]:
                print(f"   • {seg}")
            print()
        
        if coverage_result.get("new_keywords_to_explore"):
            print("New Keywords to Explore:")
            for kw in coverage_result.get("new_keywords_to_explore", [])[:10]:
                print(f"   • {kw}")
            print()
        
        print("="*80)
        
        # Decision: continue or stop?
        if coverage_result.get("is_complete") or coverage_result.get("coverage_percentage", 0) >= 90:
            print("\n🎊 INDUSTRY FULLY INDEXED!")
            stats['status'] = "complete"
            stats['current_phase'] = "Complete"
            print_stats()
            
            # Save final report
            final_report = {
                "industry": INDUSTRY,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "stats": stats,
                "coverage_analysis": coverage_result
            }
            
            db.industry_indexing_reports.insert_one(final_report)
            print(f"\n✅ Final report saved to MongoDB")
            break
        
        # Continue: discover new sites if needed
        new_keywords = coverage_result.get("new_keywords_to_explore", [])
        
        if new_keywords and not sites_to_index:
            print(f"\n🔍 Discovering new sites with {len(new_keywords)} keywords...")
            newly_discovered = await discover_initial_sites(INDUSTRY, new_keywords)
            
            # Add to discovered (only new ones)
            for site in newly_discovered:
                if site not in stats['discovered_sites']:
                    stats['discovered_sites'].add(site)
                    stats['total_sites_discovered'] += 1
            
            sites_to_index = list(stats['discovered_sites'] - stats['indexed_sites'])
            print(f"   Found {len(newly_discovered)} sites ({len(sites_to_index)} new)")
        
        if not sites_to_index:
            print("\n⏸️  No more sites to index and no new keywords. Waiting...")
            await asyncio.sleep(60)
            continue
        
        # Create batch
        batch_size = min(MAX_PARALLEL_AGENTS, len(sites_to_index))
        batch_sites = sites_to_index[:batch_size]
        
        stats['current_phase'] = f"Indexing Batch {batch_id}"
        print_stats()
        
        created = await create_agent_batch(batch_sites, batch_id)
        
        print(f"\n✅ Batch {batch_id} complete: {len(created)} agents created")
        batch_id += 1
        
        # Brief pause between batches
        await asyncio.sleep(10)


if __name__ == "__main__":
    print("="*80)
    print("🚀 CONTINUOUS INDUSTRY INDEXER - STARTING")
    print("="*80)
    print(f"🎯 Industry: {INDUSTRY}")
    print(f"⚡ GPUs: {len(GPU_IDS)}")
    print(f"🔥 Max Parallel: {MAX_PARALLEL_AGENTS}")
    print()
    print("📡 Initializing components...")
    
    # Initialize stats file
    save_stats()
    add_log("🚀 System starting...", "info")
    
    print("✅ Components ready!")
    print("🔄 Starting indexing loop...")
    print()
    
    try:
        asyncio.run(continuous_indexing())
    except KeyboardInterrupt:
        print("\n\n⏹️  Indexing stopped by user")
        print(f"📊 Final stats: {stats['total_agents_created']} agents, {stats['coverage_percentage']:.1f}% coverage")
        stats['status'] = "stopped"
        save_stats()
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        stats['status'] = "error"
        add_log(f"❌ Fatal error: {e}", "error")
        save_stats()

