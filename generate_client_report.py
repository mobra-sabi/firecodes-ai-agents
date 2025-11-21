#!/usr/bin/env python3
"""
Generează raport complet pentru client cu hinturi și acțiuni concrete
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from bson import ObjectId

# Adaugă directorul curent la path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_health_score import AgentHealthScore
from agent_awareness_feed import AgentAwarenessFeed
from agent_state_memory import AgentStateMemory

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ai_agents_db")


def generate_client_report(domain: str):
    """Generează raport complet pentru client"""
    
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]
    
    # Găsește agent
    agent = db.site_agents.find_one({"domain": domain})
    if not agent:
        print(f"❌ Agent nu există pentru {domain}")
        return None
    
    agent_id = str(agent["_id"])
    
    print("=" * 80)
    print(f"📊 RAPORT CLIENT - {domain}")
    print("=" * 80)
    print(f"Data generării: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. Scoruri de sănătate
    print("🎯 SCORURI DE SĂNĂTATE")
    print("-" * 80)
    health = AgentHealthScore()
    scores = health.calculate_all_scores(agent_id)
    health.save_health_scores(agent_id, scores)
    
    print(f"   SEO Health: {scores['seo_health']:.1f}/100")
    if scores['seo_health'] >= 70:
        print("   ✅ Excelent - Site-ul tău are o poziție puternică în Google")
    elif scores['seo_health'] >= 40:
        print("   ⚠️ Mediu - Există potențial de îmbunătățire")
    else:
        print("   ❌ Scăzut - Necesită acțiuni urgente")
    
    print(f"   Opportunity Level: {scores['opportunity_level']:.1f}/100")
    if scores['opportunity_level'] >= 60:
        print("   🚀 Mare potențial de creștere identificat!")
    
    print(f"   Risk Level: {scores['risk_level']:.1f}/100")
    if scores['risk_level'] >= 50:
        print("   ⚠️ Atenție - Există riscuri care necesită monitorizare")
    
    # 2. Keywords analiză
    print("\n📈 ANALIZĂ KEYWORDS")
    print("-" * 80)
    
    recent_serp = list(db.serp_results.find({
        "agent_id": agent_id,
        "check_date": {"$gte": datetime.now(timezone.utc) - timedelta(days=30)}
    }).sort("check_date", -1).limit(1000))
    
    if not recent_serp:
        print("   ⚠️ Nu există date SERP. Rulează SERP monitoring mai întâi.")
        keywords_analysis = {}
        top10 = {}
        potential = {}
        declining = []
    else:
        # Analizează keywords
        keywords_analysis = {}
        for r in recent_serp:
            keyword = r.get("keyword", "")
            position = r.get("position", 0)
            if keyword and position:
                if keyword not in keywords_analysis:
                    keywords_analysis[keyword] = []
                keywords_analysis[keyword].append(position)
        
        # Keywords în top 10
        top10 = {k: sum(v)/len(v) for k, v in keywords_analysis.items() 
                if any(1 <= p <= 10 for p in v)}
        
        # Keywords cu potențial (11-20)
        potential = {k: sum(v)/len(v) for k, v in keywords_analysis.items() 
                    if any(11 <= p <= 20 for p in v) and not any(1 <= p <= 10 for p in v)}
        
        # Keywords care au scăzut
        declining = []
        for keyword, positions in keywords_analysis.items():
            if len(positions) >= 2:
                recent_avg = sum(positions[:5]) / min(5, len(positions))
                older_avg = sum(positions[5:10]) / min(5, len(positions[5:])) if len(positions) >= 10 else recent_avg
                if recent_avg > older_avg + 5:  # Scădere de peste 5 poziții
                    declining.append((keyword, recent_avg, older_avg))
        
        print(f"   Keywords monitorizate: {len(keywords_analysis)}")
        print(f"   Keywords în TOP 10: {len(top10)}")
        print(f"   Keywords cu potențial (11-20): {len(potential)}")
        print(f"   Keywords în scădere: {len(declining)}")
        
        # Top keywords în top 10
        if top10:
            print("\n   ✅ TOP KEYWORDS (în top 10):")
            sorted_top10 = sorted(top10.items(), key=lambda x: x[1])[:10]
            for kw, avg_pos in sorted_top10:
                print(f"      • {kw} - poziția {avg_pos:.1f}")
        
        # Keywords cu potențial
        if potential:
            print("\n   🚀 KEYWORDS CU POTENȚIAL (11-20):")
            sorted_potential = sorted(potential.items(), key=lambda x: x[1])[:10]
            for kw, avg_pos in sorted_potential:
                print(f"      • {kw} - poziția {avg_pos:.1f}")
                print(f"        → Acțiune: Optimizează conținutul pentru acest keyword")
        
        # Keywords în scădere
        if declining:
            print("\n   ⚠️ KEYWORDS ÎN SCĂDERE (necesită atenție):")
            sorted_declining = sorted(declining, key=lambda x: x[1], reverse=True)[:5]
            for kw, recent, older in sorted_declining:
                print(f"      • {kw} - {older:.1f} → {recent:.1f}")
                print(f"        → Acțiune: Analizează ce s-a schimbat și optimizează")
    
    # 3. Competitori
    print("\n🏢 ANALIZĂ COMPETITORI")
    print("-" * 80)
    
    competitors = agent.get("competitors", [])
    if competitors:
        print(f"   Competitori identificați: {len(competitors)}")
        print(f"   Primele 10:")
        for i, comp in enumerate(competitors[:10], 1):
            print(f"      {i}. {comp}")
    else:
        print("   ⚠️ Nu există competitori identificați.")
        print("   → Acțiune: Rulează descoperirea competitorilor")
    
    # 4. Detectare conștiință
    print("\n🔍 DESCOPERIRI RECENTE")
    print("-" * 80)
    
    awareness = AgentAwarenessFeed()
    new_competitors = awareness.detect_new_competitors(agent_id)
    patterns = awareness.detect_patterns(agent_id)
    anomalies = awareness.detect_anomalies(agent_id)
    
    if new_competitors:
        print(f"   🆕 Competitori noi detectați: {len(new_competitors)}")
        for comp in new_competitors[:5]:
            print(f"      • {comp.get('domain', 'N/A')}")
    
    if patterns:
        print(f"   📊 Pattern-uri detectate: {len(patterns)}")
        for pattern in patterns[:3]:
            print(f"      • {pattern.get('pattern', 'N/A')}")
    
    if anomalies:
        print(f"   ⚠️ Anomalii detectate: {len(anomalies)}")
        for anomaly in anomalies[:3]:
            print(f"      • {anomaly.get('anomaly', 'N/A')}")
    
    if not new_competitors and not patterns and not anomalies:
        print("   ℹ️ Nu există descoperiri recente")
    
    # 5. RECOMANDĂRI CONCRETE
    print("\n" + "=" * 80)
    print("💡 RECOMANDĂRI ȘI ACȚIUNI CONCRETE")
    print("=" * 80)
    
    recommendations = []
    
    # Recomandări bazate pe scoruri
    if scores['seo_health'] < 40:
        recommendations.append({
            "prioritate": "URGENT",
            "titlu": "Îmbunătățește poziția în Google",
            "descriere": "Site-ul tău are o poziție scăzută în Google. Acțiuni recomandate:",
            "acțiuni": [
                "Optimizează conținutul pentru keywords principale",
                "Creează conținut nou și relevant",
                "Îmbunătățește viteza site-ului",
                "Asigură-te că site-ul este mobile-friendly"
            ]
        })
    
    if scores['opportunity_level'] >= 60:
        recommendations.append({
            "prioritate": "HIGH",
            "titlu": "Exploatează oportunitățile identificate",
            "descriere": "Ai keywords cu potențial de creștere. Acțiuni recomandate:",
            "acțiuni": [
                "Optimizează conținutul pentru keywords din pozițiile 11-20",
                "Creează pagini dedicate pentru aceste keywords",
                "Construiește backlinks relevante",
                "Promovează conținutul pe social media"
            ]
        })
    
    if potential:
        recommendations.append({
            "prioritate": "MEDIUM",
            "titlu": "Focus pe keywords cu potențial",
            "descriere": f"Ai {len(potential)} keywords aproape de top 10. Acțiuni recomandate:",
            "acțiuni": [
                f"Optimizează pentru: {', '.join(list(potential.keys())[:5])}",
                "Îmbunătățește conținutul existent",
                "Adaugă secțiuni relevante în pagini",
                "Construiește autoritate pentru aceste keywords"
            ]
        })
    
    if declining:
        recommendations.append({
            "prioritate": "HIGH",
            "titlu": "Oprește scăderea pentru keywords importante",
            "descriere": f"Ai {len(declining)} keywords în scădere. Acțiuni recomandate:",
            "acțiuni": [
                f"Analizează ce s-a schimbat pentru: {', '.join([d[0] for d in declining[:3]])}",
                "Verifică dacă competitorii au optimizat pentru aceste keywords",
                "Actualizează conținutul pentru a rămâne relevant",
                "Construiește backlinks noi"
            ]
        })
    
    if not competitors:
        recommendations.append({
            "prioritate": "MEDIUM",
            "titlu": "Identifică competitorii tăi",
            "descriere": "Nu ai competitori identificați. Acțiuni recomandate:",
            "acțiuni": [
                "Rulează descoperirea competitorilor",
                "Analizează ce fac competitorii",
                "Învăță din strategiile lor de succes"
            ]
        })
    
    # Afișează recomandări
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. [{rec['prioritate']}] {rec['titlu']}")
        print(f"   {rec['descriere']}")
        for action in rec['acțiuni']:
            print(f"   ✓ {action}")
    
    if not recommendations:
        print("\n✅ Site-ul tău este în formă bună! Continuă cu optimizări constante.")
    
    # 6. Plan de acțiune pe 30 zile
    print("\n" + "=" * 80)
    print("📅 PLAN DE ACȚIUNE - URMĂTOARELE 30 ZILE")
    print("=" * 80)
    
    print("\n📌 Săptămâna 1-2:")
    print("   • Analizează keywords cu potențial")
    print("   • Optimizează 5-10 pagini principale")
    print("   • Creează conținut nou pentru keywords importante")
    
    print("\n📌 Săptămâna 3-4:")
    print("   • Construiește backlinks relevante")
    print("   • Monitorizează progresul keywords")
    print("   • Ajustează strategia bazat pe rezultate")
    
    print("\n📌 Continuă:")
    print("   • Monitorizează competitorii")
    print("   • Actualizează conținutul regulat")
    print("   • Analizează rapoarte lunare")
    
    print("\n" + "=" * 80)
    print("✅ Raport generat cu succes!")
    print("=" * 80)
    
    return {
        "scores": scores,
        "keywords_analysis": keywords_analysis if recent_serp else {},
        "competitors": competitors,
        "recommendations": recommendations
    }


if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else "tehnica-antifoc.ro"
    generate_client_report(domain)

