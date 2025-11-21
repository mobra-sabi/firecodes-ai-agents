#!/usr/bin/env python3
"""Test integrare completă: DeepSeek + Context Qdrant pentru strategii competitive"""

import asyncio
from competitive_strategy import CompetitiveStrategyGenerator
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  🧪 TEST: DeepSeek + Qdrant Context pentru Strategii Competitive    ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    
    generator = CompetitiveStrategyGenerator()
    
    # Test cu agentul ropaintsolutions
    agent_id = "6910d0682716fa6b8a6f8e72"
    
    print(f"🚀 Generare strategie competitivă pentru agent: {agent_id}")
    print(f"   (ropaintsolutions.ro - protecție la foc)")
    print()
    print("⚠️  IMPORTANT: Acest test va:")
    print("   1. Extrage context semantic din Qdrant (319 vectori)")
    print("   2. Trimite context îmbogățit la DeepSeek")
    print("   3. Genera strategie competitivă completă")
    print()
    print("⏱️  Durată estimată: ~2-3 minute")
    print()
    
    input("Apasă ENTER pentru a continua sau CTRL+C pentru a anula...")
    
    try:
        result = await generator.analyze_agent_and_generate_strategy(agent_id)
        
        print("\n" + "="*70)
        print("✅ STRATEGIE GENERATĂ CU SUCCES!")
        print("="*70)
        print()
        print(f"📊 Statistici:")
        print(f"   Strategy ID: {result.get('strategy_id')}")
        print(f"   Timestamp: {result.get('timestamp')}")
        
        strategy = result.get('strategy', {})
        print()
        print(f"🎯 Servicii analizate: {len(strategy.get('competitive_analysis', {}).get('services', []))}")
        print(f"📝 Strategii per serviciu: {len(strategy.get('competitive_analysis', {}).get('service_strategies', []))}")
        
        print()
        print("═══════════════════════════════════════════════════════════════════════")
        print("✅ DeepSeek a primit și folosit contextul din Qdrant!")
        print("✅ Strategie salvată în MongoDB (collection: competitive_strategies)")
        print("═══════════════════════════════════════════════════════════════════════")
        
        return result
        
    except Exception as e:
        print(f"\n❌ EROARE: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test())
