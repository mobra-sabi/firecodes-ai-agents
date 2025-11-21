#!/usr/bin/env python3
"""Test pentru descoperirea competitorilor via Google"""

import sys
from google_competitor_discovery import get_discovery_engine

def test_discovery(agent_id: str, results_per_keyword: int = 20):
    """Test descoperire competitori"""
    
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  🔍 TEST: Descoperire Competitori via Google Search                 ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    
    engine = get_discovery_engine()
    
    print(f"🎯 Agent ID: {agent_id}")
    print(f"📊 Rezultate per keyword: {results_per_keyword}")
    print()
    print("⏳ Pornesc descoperirea... (va dura câteva minute)")
    print("-" * 70)
    
    try:
        result = engine.discover_competitors_for_agent(
            agent_id=agent_id,
            results_per_keyword=results_per_keyword,
            use_api=False
        )
        
        print("\n✅ DESCOPERIRE COMPLETĂ!")
        print("=" * 70)
        print()
        
        # Statistici
        stats = result.get("stats", {})
        print("📊 STATISTICI:")
        print(f"   • Keywords căutate: {stats.get('total_keywords_searched', 0)}")
        print(f"   • Site-uri descoperite: {stats.get('total_sites_discovered', 0)}")
        print(f"   • Competitori finali: {stats.get('total_competitors', 0)}")
        print(f"   • Top competitor: {stats.get('top_competitor', 'N/A')}")
        print(f"   • Appearances medii: {stats.get('avg_appearances', 0):.2f}")
        print()
        
        # Subdomenii coverage
        coverage = stats.get('subdomains_coverage', {})
        if coverage:
            print("📦 COVERAGE PER SUBDOMENIU:")
            for subdomain, count in coverage.items():
                print(f"   • {subdomain[:50]}: {count} competitori")
            print()
        
        # Top 10 competitori
        competitors = result.get("competitors", [])
        if competitors:
            print(f"🏆 TOP 10 COMPETITORI (din {len(competitors)}):")
            print()
            
            for i, comp in enumerate(competitors[:10], 1):
                print(f"{i}. {comp['domain']} - Score: {comp['score']:.2f}")
                print(f"   📝 {comp['title'][:80]}")
                print(f"   🔗 {comp['url']}")
                print(f"   📊 Apariții: {comp['appearances_count']} | "
                      f"Poziție medie: {comp['avg_position']:.1f} | "
                      f"Best: #{comp['best_position']}")
                
                subdomains = comp.get('subdomains_matched', [])
                if subdomains:
                    print(f"   📦 Subdomenii: {', '.join(subdomains[:3])}")
                
                keywords = comp.get('keywords_matched', [])
                if keywords:
                    print(f"   🔑 Keywords: {', '.join(keywords[:3])}")
                print()
        
        # Mapare keywords
        keywords_map = result.get("keywords_map", {})
        print(f"🗺️  MAPARE KEYWORDS: {len(keywords_map)} keywords")
        print()
        
        print("=" * 70)
        print("✅ Test finalizat cu succes!")
        print()
        print("💡 Următorii pași:")
        print("   1. TASK 3: Scrapează competitorii top (cre ează agenți pentru ei)")
        print("   2. TASK 4: Extrage caracteristici competitive")
        print("   3. TASK 5: Analiză comparativă cu DeepSeek")
        
        return result
        
    except Exception as e:
        print(f"\n❌ EROARE: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        agent_id = sys.argv[1]
        results_per_kw = int(sys.argv[2]) if len(sys.argv) > 2 else 5  # Default 5 pentru test rapid
    else:
        agent_id = "6910d564c5a351f416f077ed"  # coneco.ro
        results_per_kw = 5  # Test rapid cu 5 rezultate
        print(f"ℹ️  Folosesc agent_id default: {agent_id} (coneco.ro)")
        print(f"ℹ️  Test rapid: {results_per_kw} rezultate per keyword")
        print()
    
    test_discovery(agent_id, results_per_kw)
