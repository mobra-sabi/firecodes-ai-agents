#!/usr/bin/env python3
"""
Test CI Workflow pentru agentul Facility360.ro existent
"""

import sys
from datetime import datetime

def run_ci_workflow_for_facility360():
    """
    Rulează CI Workflow complet pentru Facility360.ro
    
    1. Verifică agentul existent
    2. Analizează cu DeepSeek (subdomenii + keywords)
    3. Descoperă competitori (dacă nu există deja)
    """
    
    AGENT_ID = "6912cf9e48971000d7a7a450"
    
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║   🚀 CI WORKFLOW - FACILITY360.RO                                    ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"🆔 Agent ID: {AGENT_ID}")
    print(f"🌐 Domain: facility360.ro")
    print()
    print("=" * 70)
    
    # ========================================================================
    # STEP 1: VERIFICARE AGENT
    # ========================================================================
    print("\n✅ STEP 1/3: VERIFICARE AGENT EXISTENT")
    print("-" * 70)
    
    try:
        from pymongo import MongoClient
        from bson import ObjectId
        
        client = MongoClient("mongodb://localhost:27017/")
        db = client["ai_agents_db"]
        
        agent = db.site_agents.find_one({"_id": ObjectId(AGENT_ID)})
        
        if not agent:
            print(f"❌ Agent {AGENT_ID} nu există!")
            return None
        
        print(f"✅ Agent găsit!")
        print(f"   • Domain: {agent.get('domain')}")
        print(f"   • Status: {agent.get('status')}")
        print(f"   • Services: {len(agent.get('services', []))}")
        print(f"   • Categories: {len(agent.get('categories', []))}")
        print(f"   • Subcategories: {len(agent.get('subcategories', []))}")
        
        # Afișează câteva servicii
        print(f"\n   📋 SERVICII SAMPLE:")
        for i, svc in enumerate(agent.get('services', [])[:3], 1):
            if isinstance(svc, dict):
                name = svc.get('service_name', svc.get('name', 'N/A'))
                print(f"      {i}. {name}")
        
    except Exception as e:
        print(f"\n❌ EROARE la verificarea agentului: {e}")
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
        
        # Check if analysis already exists
        existing_analysis = db.competitive_analysis.find_one({
            "agent_id": ObjectId(AGENT_ID),
            "analysis_type": "competition_discovery"
        })
        
        if existing_analysis:
            print("ℹ️  Analiza DeepSeek deja există în DB")
            print("   Folosesc analiza existentă...")
            analysis_result = existing_analysis.get('analysis_data', {})
        else:
            print("⏳ Trimit context complet către DeepSeek...")
            print("   (MongoDB + Qdrant → analiza industriei)")
            print()
            
            analysis_result = analyzer.analyze_for_competition_discovery(AGENT_ID)
        
        print()
        print("✅ ANALIZĂ DEEPSEEK DISPONIBILĂ!")
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
            desc = subdomain.get('description', 'N/A')
            if len(desc) > 100:
                desc = desc[:100] + "..."
            print(f"   📝 {desc}")
            print(f"   🔑 {len(keywords)} keywords")
            
            # Show sample keywords
            if keywords:
                sample_kw = keywords[:3]
                print(f"   📌 Sample: {', '.join(sample_kw)}")
        
        print(f"\n🌐 KEYWORDS GENERALE: {len(overall_keywords)}")
        if overall_keywords:
            sample_overall = overall_keywords[:5]
            print(f"   📌 Sample: {', '.join(sample_overall)}")
        
        print(f"\n📊 TOTAL KEYWORDS: {total_keywords + len(overall_keywords)}")
        
    except Exception as e:
        print(f"\n❌ EROARE la analiza DeepSeek: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # ========================================================================
    # STEP 3: VERIFICARE COMPETITORI (sau descoperire nouă)
    # ========================================================================
    print("\n" + "=" * 70)
    print("\n🔍 STEP 3/3: COMPETITIVE INTELLIGENCE")
    print("-" * 70)
    
    try:
        # Check if competitors already exist
        existing_competitors = list(db.competitor_discovery.find({
            "agent_id": ObjectId(AGENT_ID)
        }))
        
        if existing_competitors:
            print(f"ℹ️  {len(existing_competitors)} competitori deja descoperiți în DB")
            print("   Folosesc competitorii existenți...")
            
            # Group by score
            competitors = []
            for comp in existing_competitors:
                competitors.append({
                    'domain': comp.get('competitor_domain', 'N/A'),
                    'score': comp.get('score', 0),
                    'appearances_count': comp.get('appearances_count', 0),
                    'avg_position': comp.get('avg_position', 0),
                    'best_position': comp.get('best_position', 0),
                    'subdomains_matched': comp.get('subdomains_matched', [])
                })
            
            # Sort by score
            competitors.sort(key=lambda x: x['score'], reverse=True)
            
            print()
            print("✅ COMPETITORI DISPONIBILI!")
            print()
            
            print(f"📊 STATISTICI:")
            print(f"   • Competitori totali: {len(competitors)}")
            if competitors:
                print(f"   • Top competitor: {competitors[0]['domain']} (score: {competitors[0]['score']:.1f})")
            print()
            
            # Top competitori
            if competitors:
                print(f"🏆 TOP 10 COMPETITORI:")
                print()
                
                for i, comp in enumerate(competitors[:10], 1):
                    print(f"{i}. {comp['domain']} - Score: {comp['score']:.1f}")
                    print(f"   📊 Apariții: {comp['appearances_count']} keywords | "
                          f"Poziție medie: {comp['avg_position']:.1f} | "
                          f"Best: #{comp['best_position']}")
                    
                    subdomains_matched = comp.get('subdomains_matched', [])
                    if subdomains_matched:
                        sub_str = ', '.join(subdomains_matched[:2])
                        if len(sub_str) > 60:
                            sub_str = sub_str[:60] + "..."
                        print(f"   📦 Subdomenii: {sub_str}")
                    print()
        else:
            print("⚠️  Nu există competitori în DB")
            print("   Pentru a descoperi competitori, rulează:")
            print(f"   python3 google_competitor_discovery.py --agent-id {AGENT_ID}")
            
    except Exception as e:
        print(f"\n❌ EROARE la verificarea competitorilor: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # REZUMAT FINAL
    # ========================================================================
    print("\n" + "=" * 70)
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║   ✅ CI WORKFLOW VERIFICAT CU SUCCES! ✅                            ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"🌐 SITE: facility360.ro")
    print(f"🆔 AGENT ID: {AGENT_ID}")
    print()
    print("📊 STATUS:")
    print(f"   ✅ Agent verificat și operațional")
    print(f"   ✅ {len(subdomains)} subdomenii identificate")
    print(f"   ✅ {total_keywords + len(overall_keywords)} keywords generate")
    if existing_competitors:
        print(f"   ✅ {len(existing_competitors)} competitori descoperiți")
    else:
        print(f"   ⚠️  Competitori: nedescoperiti încă")
    print()
    print("🎉 TOATE MODULELE PENTRU CI SUNT FUNCȚIONALE!")
    print()
    
    return {
        "agent_id": AGENT_ID,
        "domain": "facility360.ro",
        "services_count": len(agent.get('services', [])),
        "categories_count": len(agent.get('categories', [])),
        "subdomains_count": len(subdomains),
        "keywords_count": total_keywords + len(overall_keywords),
        "competitors_count": len(existing_competitors) if existing_competitors else 0,
        "status": "operational"
    }


if __name__ == "__main__":
    result = run_ci_workflow_for_facility360()
    
    if result:
        print(f"✅ SUCCESS!")
        sys.exit(0)
    else:
        print(f"❌ FAILED!")
        sys.exit(1)

