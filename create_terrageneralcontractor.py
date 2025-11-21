#!/usr/bin/env python3
"""Creare agent pentru terrageneralcontractor.ro"""

import asyncio
from site_agent_creator import create_agent_logic

async def create():
    print("🚀 CREARE AGENT: terrageneralcontractor.ro")
    print("="*70)
    
    try:
        url = "https://terrageneralcontractor.ro/"
        
        result = await create_agent_logic(
            url=url,
            api_key="test",
            loop=None,
            websocket=None
        )
        
        print("\n" + "="*70)
        print("✅ AGENT CREAT CU SUCCES!")
        print("="*70)
        print(f"   Agent ID: {result.get('agent_id')}")
        print(f"   Nume: {result.get('name')}")
        print(f"   Domain: {result.get('domain')}")
        print(f"   Status: {result.get('status')}")
        print(f"   Validare: {'✅ PASSED' if result.get('validation_passed') else '❌ FAILED'}")
        print()
        print("📊 STATISTICI:")
        summary = result.get('summary', {})
        print(f"   Caractere: {summary.get('content_extracted', 0):,}")
        print(f"   Vectori: {summary.get('vectors_saved', 0)}")
        print(f"   Memorie: {'✅' if summary.get('memory_configured') else '❌'}")
        print(f"   Qwen: {'✅' if summary.get('qwen_integrated') else '❌'}")
        print(f"   Long Chain: {'✅' if summary.get('long_chain_integrated') else '❌'}")
        print(f"   Servicii: {result.get('services_count', 0)}")
        print("="*70)
        
        return result
        
    except Exception as e:
        print(f"\n❌ EROARE: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(create())
    
    if result and result.get('validation_passed'):
        print("\n🎉 SUCCES TOTAL! Agent complet funcțional!")
    else:
        print("\n⚠️  Verifică logurile pentru detalii")
