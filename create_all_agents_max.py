#!/usr/bin/env python3
"""Creare masivă de agenți cu configurație MAXIMĂ"""

import asyncio
from site_agent_creator import create_agent_logic
import time

SITES = [
    "https://www.ropaintsolutions.ro/",
    "https://firestopping.ro/",
    "https://coneco.ro/"
]

async def create_all():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  🚀 CREARE MASIVĂ: 3 AGENȚI CU CONFIGURAȚIE MAXIMĂ                  ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print("📋 CONFIGURAȚIE PENTRU FIECARE AGENT:")
    print("   ✅ Vectori Qdrant (GPU-accelerated)")
    print("   ✅ Qwen Memory & Learning")
    print("   ✅ Long Chain Integration")
    print("   ✅ LangChain enabled")
    print("   ✅ Context semantic complet")
    print("   ✅ Validare strictă")
    print()
    print(f"⏱️  Timp estimat: ~3-5 minute per agent")
    print(f"   Total: ~15 minute pentru toți 3")
    print()
    print("="*70)
    
    results = []
    total_start = time.time()
    
    for idx, url in enumerate(SITES, 1):
        print()
        print("="*70)
        print(f"🚀 AGENT {idx}/{len(SITES)}: {url}")
        print("="*70)
        
        start = time.time()
        
        try:
            result = await create_agent_logic(
                url=url,
                api_key="test",
                loop=None,
                websocket=None
            )
            
            elapsed = time.time() - start
            
            print()
            print(f"✅ SUCCES în {elapsed:.1f}s!")
            print(f"   Agent ID: {result.get('agent_id')}")
            print(f"   Nume: {result.get('name')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Validare: {'✅ PASSED' if result.get('validation_passed') else '❌ FAILED'}")
            
            summary = result.get('summary', {})
            print(f"   Caractere: {summary.get('content_extracted', 0):,}")
            print(f"   Servicii: {result.get('services_count', 0)}")
            
            results.append({
                'url': url,
                'success': True,
                'agent_id': result.get('agent_id'),
                'time': elapsed,
                'result': result
            })
            
        except Exception as e:
            elapsed = time.time() - start
            print(f"\n❌ EROARE după {elapsed:.1f}s: {e}")
            results.append({
                'url': url,
                'success': False,
                'error': str(e),
                'time': elapsed
            })
    
    total_elapsed = time.time() - total_start
    
    print()
    print("="*70)
    print("📊 REZUMAT FINAL")
    print("="*70)
    print()
    
    success_count = sum(1 for r in results if r['success'])
    
    for idx, result in enumerate(results, 1):
        status = "✅" if result['success'] else "❌"
        print(f"{status} {idx}. {result['url']}")
        if result['success']:
            print(f"      ID: {result['agent_id']}")
            print(f"      Timp: {result['time']:.1f}s")
        else:
            print(f"      Eroare: {result.get('error', 'Unknown')}")
        print()
    
    print("="*70)
    print(f"✅ Agenți creați cu succes: {success_count}/{len(SITES)}")
    print(f"⏱️  Timp total: {total_elapsed:.1f}s ({total_elapsed/60:.1f} minute)")
    print("="*70)
    
    return results

if __name__ == "__main__":
    results = asyncio.run(create_all())
