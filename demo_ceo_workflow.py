#!/usr/bin/env python3
"""
🎯 DEMO CEO MASTER WORKFLOW - Demonstrație completă a sistemului

Acest script demonstrează toate cele 8 faze ale workflow-ului CEO într-un mod interactiv.
"""

import asyncio
import sys
import json
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

sys.path.insert(0, '/srv/hf/ai_agents')
from ceo_master_workflow import CEOMasterWorkflow


def print_section(title: str, color: str = "36"):
    """Print a formatted section title"""
    print(f"\n\033[{color};1m{'='*80}\033[0m")
    print(f"\033[{color};1m{title.center(80)}\033[0m")
    print(f"\033[{color};1m{'='*80}\033[0m\n")


def print_success(message: str):
    """Print success message"""
    print(f"\033[32m✅ {message}\033[0m")


def print_info(message: str):
    """Print info message"""
    print(f"\033[34mℹ️  {message}\033[0m")


def print_warning(message: str):
    """Print warning message"""
    print(f"\033[33m⚠️  {message}\033[0m")


def print_error(message: str):
    """Print error message"""
    print(f"\033[31m❌ {message}\033[0m")


async def demo_phase_by_phase(site_url: str):
    """
    Demo workflow fază cu fază cu explicații detaliate
    """
    print_section("🎯 CEO MASTER WORKFLOW - DEMO INTERACTIV", "35")
    print_info(f"Site Master: {site_url}")
    print_info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    workflow = CEOMasterWorkflow()
    mongo = MongoClient("mongodb://localhost:27017/")
    db = mongo.ai_agents_db
    
    # ========================================================================
    # FAZA 1: Creare Agent Master
    # ========================================================================
    print_section("📍 FAZA 1/8: CREARE AGENT MASTER", "36")
    print_info("Acest pas include:")
    print("  1. 🕷️  Web scraping (BeautifulSoup + Playwright)")
    print("  2. 🧩 Chunking content (500-1000 caractere per chunk)")
    print("  3. 🧠 Generate embeddings pe GPU (all-MiniLM-L6-v2)")
    print("  4. 📦 Upload la Qdrant vector database")
    print("  5. 💾 Save în MongoDB cu metadata\n")
    
    input("👉 Press ENTER to start FAZA 1...")
    
    phase1_result = await workflow._phase1_create_master_agent(site_url)
    
    if phase1_result["success"]:
        print_success(f"Agent Master creat cu succes!")
        print_info(f"   Agent ID: {phase1_result['agent_id']}")
        print_info(f"   Chunks: {phase1_result['chunks_count']}")
        print_info(f"   Pages: {phase1_result['pages_count']}")
        print_info(f"   Domain: {phase1_result['domain']}")
        master_agent_id = phase1_result["agent_id"]
    else:
        print_error(f"FAZA 1 failed: {phase1_result['error']}")
        return
    
    # ========================================================================
    # FAZA 2: LangChain Integration
    # ========================================================================
    print_section("📍 FAZA 2/8: LANGCHAIN INTEGRATION", "36")
    print_info("Acest pas include:")
    print("  1. 🔗 Creare LangChain agent cu memorie")
    print("  2. 💭 Configuration conversation buffer (ultimele 10 mesaje)")
    print("  3. 🎭 Setup personality layer")
    print("  4. 🗃️  Initialize conversation state\n")
    
    input("👉 Press ENTER to start FAZA 2...")
    
    phase2_result = await workflow._phase2_integrate_langchain(master_agent_id)
    
    if phase2_result["success"]:
        print_success("LangChain integration completă!")
        print_info(f"   Memory enabled: {phase2_result['memory_enabled']}")
        print_info(f"   Conversation ID: {phase2_result['conversation_id']}")
    else:
        print_warning(f"FAZA 2 partial: {phase2_result.get('error', 'N/A')}")
    
    # ========================================================================
    # FAZA 3: DeepSeek Voice
    # ========================================================================
    print_section("📍 FAZA 3/8: DEEPSEEK VOICE INTEGRATION", "36")
    print_info("Acest pas include:")
    print("  1. 🎤 DeepSeek Reasoner primește TOT contextul agentului")
    print("  2. 🧬 Creează 'Document de Identitate' complet")
    print("  3. 🎭 Definește personalitate, ton, expertize")
    print("  4. 💬 Setup communication guidelines\n")
    
    input("👉 Press ENTER to start FAZA 3...")
    
    phase3_result = await workflow._phase3_deepseek_voice_integration(master_agent_id)
    
    if phase3_result["success"]:
        print_success("DeepSeek voice integration completă!")
        print_info("   Identity document creat ✅")
        
        # Afișează un sample din identity
        identity = phase3_result.get("identity_document", {})
        if isinstance(identity, dict) and "personality" in identity:
            print_info(f"   Personality: {identity.get('personality', 'N/A')[:100]}...")
    else:
        print_warning(f"FAZA 3 partial: {phase3_result.get('error', 'LLM API keys issue')}")
    
    # ========================================================================
    # FAZA 4: Site Decomposition
    # ========================================================================
    print_section("📍 FAZA 4/8: SITE DECOMPOSITION + KEYWORDS", "36")
    print_info("Acest pas include:")
    print("  1. 🔬 DeepSeek analizează conținutul complet")
    print("  2. 🗂️  Identifică subdomenii de business")
    print("  3. 🔑 Generează 10-15 keywords per subdomeniu")
    print("  4. 📊 Creează keywords generale pentru industrie\n")
    
    input("👉 Press ENTER to start FAZA 4...")
    
    phase4_result = await workflow._phase4_deepseek_decompose_site(master_agent_id)
    
    if phase4_result["success"]:
        print_success("Site decomposition completă!")
        subdomains = phase4_result.get("subdomains", [])
        overall_keywords = phase4_result.get("overall_keywords", [])
        
        print_info(f"   Subdomenii identificate: {len(subdomains)}")
        for i, sd in enumerate(subdomains[:3], 1):
            print(f"     {i}. {sd.get('name', 'N/A')} ({len(sd.get('keywords', []))} keywords)")
        
        if len(subdomains) > 3:
            print(f"     ... și încă {len(subdomains) - 3} subdomenii")
        
        print_info(f"   Keywords generale: {len(overall_keywords)}")
        print(f"     Exemple: {', '.join(overall_keywords[:5])}")
    else:
        print_error(f"FAZA 4 failed: {phase4_result.get('error')}")
        return
    
    # ========================================================================
    # FAZA 5: Google Search
    # ========================================================================
    print_section("📍 FAZA 5/8: GOOGLE SEARCH + COMPETITOR DISCOVERY", "36")
    print_info("Acest pas include:")
    print("  1. 🔍 Google/Brave Search pentru fiecare keyword")
    print("  2. 📊 Tracking poziție în SERP pentru master")
    print("  3. 🎯 Identificare competitori relevanți")
    print("  4. 🚫 Filtering (exclude marketplace-uri, directoare)")
    print("  5. 📈 Scoring competitori (frequency, position, relevance)\n")
    
    total_keywords = len(overall_keywords) + sum(len(sd.get("keywords", [])) for sd in subdomains)
    print_warning(f"Acest pas va face {total_keywords} queries la Google/Brave!")
    print_warning("Poate dura câteva minute...")
    
    input("👉 Press ENTER to start FAZA 5...")
    
    phase5_result = await workflow._phase5_google_search_competitors(
        master_agent_id, 
        results_per_keyword=5  # Doar 5 pentru demo
    )
    
    if phase5_result["success"]:
        competitors = phase5_result.get("competitors", [])
        print_success(f"Competitor discovery completă!")
        print_info(f"   Competitori descoperiți: {len(competitors)}")
        print_info(f"   Keywords searched: {phase5_result.get('keywords_searched', 0)}")
        print_info(f"   Total URLs analyzed: {phase5_result.get('total_urls_analyzed', 0)}")
        
        if len(competitors) > 0:
            print_info("   Top 3 competitori:")
            for i, comp in enumerate(competitors[:3], 1):
                print(f"     {i}. {comp.get('domain', 'N/A')} (score: {comp.get('relevance_score', 0):.2f})")
        else:
            print_warning("   ⚠️  Niciun competitor găsit (posibil API issue)")
    else:
        print_warning(f"FAZA 5 partial: {phase5_result.get('error', 'API issue')}")
        competitors = []
    
    # ========================================================================
    # FAZA 6: CEO Map
    # ========================================================================
    print_section("📍 FAZA 6/8: CEO COMPETITIVE MAP", "36")
    print_info("Acest pas include:")
    print("  1. 🗺️  Creare hartă competitivă")
    print("  2. 📊 Calculare ranking master vs competitori")
    print("  3. 📈 Market coverage analysis")
    print("  4. 💡 Strategic insights\n")
    
    input("👉 Press ENTER to start FAZA 6...")
    
    phase6_result = await workflow._phase6_create_ceo_competitive_map(
        master_agent_id,
        competitors,
        subdomains
    )
    
    if phase6_result["success"]:
        print_success("CEO Competitive Map creată!")
        print_info(f"   Map ID: {phase6_result['map_id']}")
        print_info(f"   Master average position: {phase6_result.get('master_position_avg', 'N/A')}")
        print_info(f"   Market coverage: {phase6_result.get('market_coverage', 'N/A')}")
    else:
        print_error(f"FAZA 6 failed: {phase6_result.get('error')}")
    
    # ========================================================================
    # FAZA 7: Parallel Agent Creation
    # ========================================================================
    print_section("📍 FAZA 7/8: PARALLEL AGENT CREATION", "36")
    print_info("Acest pas include:")
    print("  1. 🤖 Creare agenți AI pentru toți competitorii")
    print("  2. 🎮 Procesare paralelă pe 5 GPU-uri (RTX 3080 Ti)")
    print("  3. ⚡ 5x speedup vs procesare secvențială")
    print("  4. 💾 Save în MongoDB ca 'slave agents'\n")
    
    if len(competitors) == 0:
        print_warning("Niciun competitor pentru procesare (skip FAZA 7)")
    else:
        print_warning(f"Acest pas va crea {len(competitors)} agenți în paralel!")
        print_warning("Poate dura mult timp (5-10 minute per agent)...")
        
        response = input("👉 Vrei să rulezi FAZA 7? (y/n): ")
        
        if response.lower() == 'y':
            phase7_result = await workflow._phase7_create_competitor_agents_parallel(
                competitors,
                parallel_count=5
            )
            
            if phase7_result["success"]:
                print_success("Parallel agent creation completă!")
                print_info(f"   Agenți creați: {len(phase7_result.get('agent_ids', []))}")
                print_info(f"   Failed: {len(phase7_result.get('failed', []))}")
            else:
                print_error(f"FAZA 7 failed: {phase7_result.get('error')}")
        else:
            print_warning("FAZA 7 skipped by user")
    
    # ========================================================================
    # FAZA 8: Orgchart
    # ========================================================================
    print_section("📍 FAZA 8/8: MASTER-SLAVE ORGCHART", "36")
    print_info("Acest pas include:")
    print("  1. 📊 Creare organogramă ierarhică")
    print("  2. 🔗 Link master → slaves")
    print("  3. 📈 Setup raportare și metrics")
    print("  4. 💾 Save în MongoDB\n")
    
    input("👉 Press ENTER to start FAZA 8...")
    
    # Get actual agent IDs from MongoDB
    slave_agents = list(db.site_agents.find({
        "relationship": "competitor_of",
        "master_agent_id": ObjectId(master_agent_id)
    }))
    slave_agent_ids = [str(agent["_id"]) for agent in slave_agents]
    
    phase8_result = await workflow._phase8_create_master_slave_orgchart(
        master_agent_id,
        slave_agent_ids
    )
    
    if phase8_result["success"]:
        print_success("Master-Slave Orgchart creată!")
        print_info(f"   Orgchart ID: {phase8_result['orgchart_id']}")
        print_info(f"   Total agents: {phase8_result['total_agents']}")
        print_info(f"   Hierarchy levels: {phase8_result['hierarchy_levels']}")
    else:
        print_error(f"FAZA 8 failed: {phase8_result.get('error')}")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print_section("🎊 WORKFLOW COMPLET - FINAL SUMMARY", "32")
    
    # Get final stats from MongoDB
    agent = db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
    ceo_map = db.ceo_competitive_maps.find_one({}, sort=[("_id", -1)])
    orgchart = db.master_slave_orgcharts.find_one({}, sort=[("_id", -1)])
    
    print_success("Toate fazele completate!\n")
    
    print("📊 REZULTATE FINALE:")
    print(f"   🎯 Master Agent: {agent.get('domain')}")
    print(f"   📦 Chunks indexed: {agent.get('chunks_indexed', 0)}")
    print(f"   🗂️  Subdomenii: {len(subdomains)}")
    print(f"   🔑 Total keywords: {total_keywords}")
    print(f"   🏢 Competitori descoperiți: {len(competitors)}")
    print(f"   🤖 Slave agents creați: {len(slave_agent_ids)}")
    print(f"   🗺️  CEO Map ID: {ceo_map.get('_id') if ceo_map else 'N/A'}")
    print(f"   📊 Orgchart ID: {orgchart.get('_id') if orgchart else 'N/A'}")
    
    print("\n💡 URMĂTORII PAȘI:")
    print("   1. Vizualizează CEO Map în dashboard")
    print("   2. Query slave agents pentru competitive intelligence")
    print("   3. Run chat cu master agent")
    print("   4. Generate rapoarte comparative")
    
    print_section("✨ DEMO COMPLET! ✨", "35")


async def demo_full_workflow(site_url: str):
    """
    Demo workflow complet (toate fazele automat)
    """
    print_section("🚀 CEO MASTER WORKFLOW - FULL AUTO", "35")
    print_info(f"Site Master: {site_url}")
    
    workflow = CEOMasterWorkflow()
    
    result = await workflow.execute_full_workflow(
        site_url=site_url,
        results_per_keyword=5,  # Doar 5 pentru demo
        parallel_gpu_agents=3    # Doar 3 pentru demo
    )
    
    print("\n" + "="*80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("="*80)


async def main():
    """Main function"""
    print_section("🎯 CEO MASTER WORKFLOW - DEMO", "35")
    print("Alege modul de demo:\n")
    print("  1. Demo INTERACTIV (fază cu fază cu explicații)")
    print("  2. Demo FULL AUTO (toate fazele automat)")
    print("  3. Exit\n")
    
    choice = input("👉 Alege (1/2/3): ")
    
    if choice == "1":
        site_url = input("\n👉 Introdu URL-ul site-ului master: ")
        await demo_phase_by_phase(site_url)
    elif choice == "2":
        site_url = input("\n👉 Introdu URL-ul site-ului master: ")
        await demo_full_workflow(site_url)
    else:
        print_info("Exit!")


if __name__ == "__main__":
    asyncio.run(main())

