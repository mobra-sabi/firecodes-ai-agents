#!/usr/bin/env python3
"""Test pentru analiza competitivă cu DeepSeek"""

import asyncio
import sys
from deepseek_competitive_analyzer import get_analyzer

async def test_analysis(agent_id: str):
    """Test analiză competitivă pentru un agent"""
    
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  🧪 TEST: Analiză Competitivă cu DeepSeek                           ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    
    analyzer = get_analyzer()
    
    # Step 1: Vezi contextul complet
    print("📊 STEP 1: Obținere context complet...")
    print("-" * 70)
    
    context = analyzer.get_full_agent_context(agent_id)
    
    print(f"Agent: {context['agent_info']['domain']}")
    print(f"URL: {context['agent_info']['site_url']}")
    print(f"Chunks: {context['stats']['total_chunks']}")
    print(f"Caractere: {context['stats']['total_characters']:,}")
    print(f"Servicii: {context['stats']['services_count']}")
    print(f"Vector context: {'✅ DA' if context['stats']['has_vector_context'] else '❌ NU'}")
    print()
    
    # Step 2: Rulează analiza
    print("🎯 STEP 2: Analiză cu DeepSeek...")
    print("-" * 70)
    print("⏳ Așteptați 1-2 minute...")
    print()
    
    try:
        result = analyzer.analyze_for_competition_discovery(agent_id)
        
        print("✅ ANALIZĂ COMPLETĂ!")
        print("=" * 70)
        print()
        
        # Afișează rezultatele
        print(f"🏭 INDUSTRIE: {result.get('industry', 'N/A')}")
        print(f"🎯 PIAȚĂ ȚINTĂ: {result.get('target_market', 'N/A')}")
        print()
        
        subdomains = result.get('subdomains', [])
        print(f"📦 SUBDOMENII IDENTIFICATE: {len(subdomains)}")
        print()
        
        for i, subdomain in enumerate(subdomains, 1):
            print(f"{i}. {subdomain.get('name', 'N/A')}")
            print(f"   📝 {subdomain.get('description', 'N/A')}")
            
            keywords = subdomain.get('keywords', [])
            if keywords:
                print(f"   🔍 Cuvinte cheie ({len(keywords)}):")
                for kw in keywords[:5]:
                    print(f"      • {kw}")
            print()
        
        overall_kw = result.get('overall_keywords', [])
        print(f"🌐 CUVINTE CHEIE GENERALE ({len(overall_kw)}):")
        for kw in overall_kw[:10]:
            print(f"   • {kw}")
        print()
        
        print("=" * 70)
        print("✅ Test finalizat cu succes!")
        print()
        print("💡 Următorii pași:")
        print("   1. Folosește cuvintele cheie pentru Google search")
        print("   2. Identifică competitori")
        print("   3. Analizează competitorii")
        
        return result
        
    except Exception as e:
        print(f"\n❌ EROARE: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        agent_id = sys.argv[1]
    else:
        # Default: coneco.ro (are cel mai mult conținut)
        agent_id = "6910d564c5a351f416f077ed"
        print(f"ℹ️  Folosesc agent_id default: {agent_id} (coneco.ro)")
        print()
    
    asyncio.run(test_analysis(agent_id))
