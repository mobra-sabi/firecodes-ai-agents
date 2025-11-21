#!/usr/bin/env python3
"""
Test Google Rankings Functionality
Testează noile funcționalități pentru Google Rankings Map
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import logging
from google_serp_scraper import GoogleSerpScraper
from slave_agent_creator import SlaveAgentCreator
from google_ads_strategy_generator import GoogleAdsStrategyGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_google_serp_scraper():
    """Test Google SERP Scraper"""
    print("\n" + "="*80)
    print("🧪 TEST 1: Google SERP Scraper")
    print("="*80)
    
    scraper = GoogleSerpScraper()
    
    # Test search
    keyword = "reparatii anticorozive"
    print(f"\n🔍 Searching for: '{keyword}'")
    
    results = scraper.search_keyword(keyword, num_results=10)
    
    if results:
        print(f"✅ Found {len(results)} results:")
        for r in results[:5]:
            print(f"   [{r['position']}] {r['domain']} - {r['title'][:60]}...")
        
        # Test find master
        master_pos = scraper.find_master_position(results, "crumantech.ro")
        if master_pos:
            print(f"\n🎯 Master found at position: {master_pos}")
        else:
            print(f"\n⚠️  Master not in top {len(results)}")
        
        return True
    else:
        print("❌ No results found")
        return False

def test_slave_agent_creator():
    """Test Slave Agent Creator"""
    print("\n" + "="*80)
    print("🧪 TEST 2: Slave Agent Creator")
    print("="*80)
    
    creator = SlaveAgentCreator()
    
    # Mock SERP result
    test_result = {
        'position': 1,
        'url': 'https://test-competitor.ro/page',
        'title': 'Test Competitor - Services',
        'description': 'Professional services',
        'domain': 'test-competitor.ro'
    }
    
    master_id = "691a19dd2772e8833c819084"
    
    print(f"\n🤖 Creating slave agent for: {test_result['domain']}")
    
    try:
        slave_id = creator.create_from_serp_result(test_result, master_id)
        print(f"✅ Slave agent created: {slave_id}")
        
        # Get stats
        stats = creator.get_slave_statistics(master_id)
        print(f"\n📊 Slave statistics:")
        print(f"   Total slaves: {stats['total_slaves']}")
        print(f"   Created today: {stats['created_today']}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_google_ads_strategy():
    """Test Google Ads Strategy Generator"""
    print("\n" + "="*80)
    print("🧪 TEST 3: Google Ads Strategy Generator")
    print("="*80)
    
    generator = GoogleAdsStrategyGenerator()
    
    agent_id = "691a19dd2772e8833c819084"
    
    print(f"\n📊 Analyzing rankings for agent: {agent_id}")
    
    try:
        analysis = generator.analyze_rankings_data(agent_id)
        
        print(f"✅ Analysis complete:")
        print(f"   Total keywords: {analysis['total_keywords']}")
        print(f"   Top 3: {len(analysis['keywords_by_position']['top_3'])}")
        print(f"   Top 10: {len(analysis['keywords_by_position']['top_10'])}")
        print(f"   Opportunities: {len(analysis['opportunities'])}")
        print(f"   Missing: {len(analysis['keywords_by_position']['missing'])}")
        
        if analysis['top_competitors']:
            print(f"\n🏆 Top competitors:")
            for domain, count in list(analysis['top_competitors'].items())[:5]:
                print(f"   • {domain}: {count} keywords")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🚀 GOOGLE RANKINGS FUNCTIONALITY TESTS")
    print("="*80)
    
    results = []
    
    # Test 1: SERP Scraper
    results.append(("SERP Scraper", test_google_serp_scraper()))
    
    # Test 2: Slave Creator
    results.append(("Slave Creator", test_slave_agent_creator()))
    
    # Test 3: Strategy Generator
    results.append(("Strategy Generator", test_google_ads_strategy()))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n📈 Pass Rate: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

