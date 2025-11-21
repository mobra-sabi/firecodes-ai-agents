#!/usr/bin/env python3
"""
Workflow complet: Creare Agent → Analiza DeepSeek → Google Discovery
"""

import sys
import asyncio
from datetime import datetime

async def complete_competitive_workflow(url: str, results_per_keyword: int = 20):
    """
    Workflow complet de analiză competitivă
    
    1. Creează agent pentru site
    2. Analizează cu DeepSeek (subdomenii + keywords)
    3. Descoperă competitori pe Google
    """
    
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║   🚀 WORKFLOW COMPLET: AGENT → ANALIZĂ → COMPETIȚIE                 ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"🌐 Site: {url}")
    print(f"📊 Rezultate per keyword: {results_per_keyword}")
    print()
    print("=" * 70)
    
    # ========================================================================
    # STEP 1: CREARE AGENT
    # ========================================================================
    print("\n📦 STEP 1/3: CREARE AGENT")
    print("-" * 70)
    
    try:
        from site_agent_creator import create_agent_logic
        
        print("⏳ Pornesc procesul de creare agent...")
        print("   (scraping, vectori, memory, validare)")
        print()
        
        # Creează agent
        loop = asyncio.get_running_loop()
        agent_data = await create_agent_logic(url, api_key="test", loop=loop)
        
        agent_id = agent_data.get('agent_id')
        domain = agent_data.get('domain')
        
        if not agent_id:
            raise Exception("Failed to create agent - no agent_id returned")
        
        print()
        print(f"✅ AGENT CREAT CU SUCCES!")
        print(f"   • Agent ID: {agent_id}")
        print(f"   • Domain: {domain}")
        print(f"   • Status: {agent_data.get('status')}")
        print(f"   • Validare: {agent_data.get('validation_passed')}")
        
        summary = agent_data.get('summary', {})
        print(f"   • Conținut: {summary.get('content_extracted', 0):,} caractere")
        print(f"   • Vectori: {summary.get('vectors_saved', 0)}")
        print(f"   • Servicii: {agent_data.get('services_count', 0)}")
        
    except Exception as e:
        print(f"\n❌ EROARE la crearea agentului: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # ========================================================================
    # STEP 2: ANALIZĂ DEEPSEEK (Subdomenii + Keywords)
    # ========================================================================
    print("\n" + "=" * 70)
    print("\n🎯 STEP 2/3: ANALIZĂ DEEPSEEK - SUBDOMENII + KEYWORDS")
    print("-" * 70)
    
    try:
        from deepseek_competitive_analyzer import get_analyzer
        
        analyzer = get_analyzer()
        
        print("⏳ Trimit context complet către DeepSeek...")
        print("   (MongoDB + Qdrant → analiza industriei)")
        print()
        
        analysis_result = analyzer.analyze_for_competition_discovery(agent_id)
        
        print()
        print("✅ ANALIZĂ DEEPSEEK COMPLETĂ!")
        print()
        
        # Afișează rezultatele
        print(f"🏭 INDUSTRIE: {analysis_result.get('industry', 'N/A')}")
        print(f"🎯 PIAȚĂ ȚINTĂ: {analysis_result.get('target_market', 'N/A')}")
        print()
        
        subdomains = analysis_result.get('subdomains', [])
        overall_keywords = analysis_result.get('overall_keywords', [])
        
        print(f"📦 SUBDOMENII IDENTIFICATE: {len(subdomains)}")
        
        total_keywords = 0
        for i, subdomain in enumerate(subdomains, 1):
            keywords = subdomain.get('keywords', [])
            total_keywords += len(keywords)
            print(f"\n{i}. {subdomain.get('name', 'N/A')}")
            print(f"   📝 {subdomain.get('description', 'N/A')[:100]}...")
            print(f"   🔑 {len(keywords)} keywords")
        
        print(f"\n🌐 KEYWORDS GENERALE: {len(overall_keywords)}")
        print(f"📊 TOTAL KEYWORDS: {total_keywords + len(overall_keywords)}")
        
    except Exception as e:
        print(f"\n❌ EROARE la analiza DeepSeek: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # ========================================================================
    # STEP 3: GOOGLE DISCOVERY (Competitori)
    # ========================================================================
    print("\n" + "=" * 70)
    print("\n🔍 STEP 3/3: GOOGLE DISCOVERY - DESCOPERIRE COMPETITORI")
    print("-" * 70)
    
    try:
        from google_competitor_discovery import get_discovery_engine
        
        engine = get_discovery_engine()
        
        print(f"⏳ Caut competitori pe Google...")
        print(f"   ({total_keywords + len(overall_keywords)} keywords × {results_per_keyword} rezultate)")
        print(f"   ⚠️  Poate dura {((total_keywords + len(overall_keywords)) * 0.5) / 60:.1f}-{((total_keywords + len(overall_keywords)) * 1) / 60:.1f} minute")
        print()
        
        discovery_result = engine.discover_competitors_for_agent(
            agent_id=agent_id,
            results_per_keyword=results_per_keyword,
            use_api=False
        )
        
        print()
        print("✅ DESCOPERIRE COMPETITORI COMPLETĂ!")
        print()
        
        # Statistici
        stats = discovery_result.get('stats', {})
        competitors = discovery_result.get('competitors', [])
        
        print("📊 STATISTICI FINALE:")
        print(f"   • Keywords căutate: {stats.get('total_keywords_searched', 0)}")
        print(f"   • Site-uri descoperite: {stats.get('total_sites_discovered', 0)}")
        print(f"   • Competitori finali: {len(competitors)} (după filtrare + scoring)")
        print(f"   • Top competitor: {stats.get('top_competitor', 'N/A')}")
        print()
        
        # Coverage per subdomeniu
        coverage = stats.get('subdomains_coverage', {})
        if coverage:
            print("📦 COVERAGE PER SUBDOMENIU:")
            for subdomain, count in coverage.items():
                print(f"   • {subdomain[:50]}: {count} competitori")
            print()
        
        # Top 15 competitori
        if competitors:
            print(f"🏆 TOP 15 COMPETITORI (din {len(competitors)}):")
            print()
            
            for i, comp in enumerate(competitors[:15], 1):
                print(f"{i}. {comp['domain']} - Score: {comp['score']:.1f}")
                print(f"   📊 Apariții: {comp['appearances_count']} keywords | "
                      f"Poziție medie: {comp['avg_position']:.1f} | "
                      f"Best: #{comp['best_position']}")
                
                subdomains_matched = comp.get('subdomains_matched', [])
                if subdomains_matched:
                    print(f"   📦 Subdomenii: {', '.join(subdomains_matched[:2])}")
                print()
        
    except Exception as e:
        print(f"\n❌ EROARE la Google Discovery: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # ========================================================================
    # REZUMAT FINAL
    # ========================================================================
    print("=" * 70)
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║   ✅ WORKFLOW COMPLET FINALIZAT CU SUCCES! ✅                       ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"🌐 SITE ANALIZAT: {domain}")
    print(f"🆔 AGENT ID: {agent_id}")
    print()
    print("📊 REZULTATE:")
    print(f"   ✅ Agent creat și validat")
    print(f"   ✅ {len(subdomains)} subdomenii identificate")
    print(f"   ✅ {total_keywords + len(overall_keywords)} keywords generate")
    print(f"   ✅ {len(competitors)} competitori descoperiți")
    print()
    print("💾 DATE SALVATE ÎN MONGODB:")
    print("   • Collection: site_agents")
    print("   • Collection: competitive_analysis")
    print("   • Collection: competitor_discovery")
    print()
    print("🔍 VEZI REZULTATELE:")
    print(f"   • API: http://localhost:5000/agents/{agent_id}/competition-analysis")
    print(f"   • API: http://localhost:5000/agents/{agent_id}/competitors")
    print()
    print("💡 NEXT STEPS:")
    print("   1. TASK 3: Scrapează top 10-20 competitori")
    print("   2. TASK 4: Extrage caracteristici competitive")
    print("   3. TASK 5: Analiză comparativă (TU vs COMPETITORI)")
    print()
    
    return {
        "agent_id": agent_id,
        "domain": domain,
        "analysis": analysis_result,
        "discovery": discovery_result
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        results_per_kw = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    else:
        print("Usage: python3 workflow_complete_competitive_analysis.py <url> [results_per_keyword]")
        print()
        print("Example:")
        print("  python3 workflow_complete_competitive_analysis.py https://tehnica-antifoc.ro 20")
        sys.exit(1)
    
    asyncio.run(complete_competitive_workflow(url, results_per_kw))
