#!/usr/bin/env python3
"""
🧪 TEST KIMI K2 INTEGRATION
===========================

Test Moonshot AI Kimi integration în LLM Orchestrator
"""

import sys
sys.path.insert(0, '/srv/hf/ai_agents')

from llm_orchestrator import get_orchestrator
import json

def print_banner():
    print("=" * 80)
    print("🧪 TEST KIMI K2 (Moonshot AI) INTEGRATION")
    print("=" * 80)
    print()

def test_orchestrator_status():
    """Test 1: Verifică status orchestrator"""
    print("📊 TEST 1: Orchestrator Status")
    print("-" * 80)
    
    orchestrator = get_orchestrator()
    status = orchestrator.get_stats()
    
    print(json.dumps(status, indent=2))
    print()
    
    if "kimi" in status.get("fallback_chain", []):
        print("✅ Kimi is integrated in fallback chain")
    else:
        print("❌ Kimi NOT in fallback chain")
    
    print()

def test_kimi_chat():
    """Test 2: Chat simplu cu Kimi"""
    print("💬 TEST 2: Kimi Chat (Simple)")
    print("-" * 80)
    
    orchestrator = get_orchestrator()
    
    # Check if Kimi API key is configured
    if not orchestrator.kimi_client:
        print("⚠️  KIMI API KEY NOT CONFIGURED")
        print("   Set KIMI_API_KEY environment variable:")
        print("   export KIMI_API_KEY='your-moonshot-api-key'")
        print()
        print("   Or use OpenRouter/Together AI")
        print()
        return False
    
    try:
        response = orchestrator.chat(
            messages=[
                {"role": "user", "content": "Explică într-o propoziție ce este competitive intelligence"}
            ],
            model="kimi",
            temperature=0.7,
            max_tokens=100
        )
        
        if response["success"]:
            print("✅ Kimi Response:")
            print(f"   Provider: {response['provider']}")
            print(f"   Model: {response['model']}")
            print(f"   Tokens: {response['tokens']}")
            if "context_window" in response:
                print(f"   Context: {response['context_window']}")
            print()
            print(f"   Content: {response['content'][:200]}...")
            print()
            return True
        else:
            print(f"❌ Kimi Failed: {response.get('error', 'Unknown error')}")
            print()
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        return False

def test_large_content():
    """Test 3: Procesare conținut mare cu Kimi"""
    print("📄 TEST 3: Large Content Processing (200K context)")
    print("-" * 80)
    
    orchestrator = get_orchestrator()
    
    if not orchestrator.kimi_client:
        print("⚠️  Skipped (no API key)")
        print()
        return False
    
    # Simulează un site cu mult conținut
    large_content = """
    DESPRE NOI:
    Suntem o companie de construcții specializată în renovări și case noi.
    Oferim servicii complete: proiectare, construcție, amenajări interioare.
    
    SERVICII:
    1. Construcție case noi
    2. Renovări complete
    3. Amenajări interioare
    4. Instalații termice și sanitare
    5. Acoperișuri
    6. Izolații termice
    
    PORTOFOLIU:
    - Case rezidențiale: 150+ proiecte
    - Renovări apartamente: 300+ proiecte
    - Comercial: 50+ proiecte
    
    ECHIPA:
    - Arhitecți: 5
    - Ingineri: 10
    - Muncitori: 50+
    
    ZONE ACOPERITE:
    București, Ilfov, Prahova, Brașov
    
    CERTIFICĂRI:
    ISO 9001, ISO 14001, ANRE
    """ * 20  # Repetă pentru a simula conținut mare
    
    try:
        response = orchestrator.process_large_content(
            content=large_content,
            task="Analizează acest site și identifică: 1) Subdomeniile principale, 2) 5 keywords per subdomeniu",
            model="kimi",
            temperature=0.7
        )
        
        if response["success"]:
            print("✅ Large Content Processing:")
            print(f"   Provider: {response['provider']}")
            print(f"   Tokens: {response['tokens']}")
            print()
            print(f"   Response Preview:")
            print(f"   {response['content'][:300]}...")
            print()
            return True
        else:
            print(f"❌ Failed: {response.get('error', 'Unknown error')}")
            print()
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        return False

def test_auto_fallback():
    """Test 4: Auto fallback cu Kimi în lanț"""
    print("🔄 TEST 4: Auto Fallback Chain")
    print("-" * 80)
    
    orchestrator = get_orchestrator()
    
    print("Testing fallback order:")
    print("1. DeepSeek")
    print("2. Kimi (200K context) ← NEW!")
    print("3. OpenAI")
    print("4. Qwen local")
    print()
    
    try:
        response = orchestrator.chat(
            messages=[
                {"role": "user", "content": "Ce este un site web?"}
            ],
            model="auto",  # Automat încearcă în ordine
            temperature=0.7,
            max_tokens=50
        )
        
        print(f"✅ Response from: {response['provider']}")
        print(f"   Model: {response['model']}")
        print(f"   Content: {response['content'][:100]}...")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        return False

def test_statistics():
    """Test 5: Statistici folosire"""
    print("📊 TEST 5: Usage Statistics")
    print("-" * 80)
    
    orchestrator = get_orchestrator()
    stats = orchestrator.get_stats()
    
    print("LLM Usage Statistics:")
    print(f"   Total Calls: {stats['total_calls']}")
    print(f"   DeepSeek: {stats['deepseek_successes']}/{stats['deepseek_calls']}")
    print(f"   Kimi: {stats['kimi_successes']}/{stats['kimi_calls']} ← NEW!")
    print(f"   OpenAI: {stats['openai_successes']}/{stats['openai_calls']}")
    print(f"   Qwen: {stats['qwen_successes']}/{stats['qwen_calls']}")
    print(f"   Success Rate: {stats.get('success_rate', 0)}%")
    print()

def main():
    """Run all tests"""
    print_banner()
    
    results = {
        "orchestrator_status": test_orchestrator_status(),
        "kimi_chat": test_kimi_chat(),
        "large_content": test_large_content(),
        "auto_fallback": test_auto_fallback()
    }
    
    test_statistics()
    
    print("=" * 80)
    print("🏁 TEST RESULTS")
    print("=" * 80)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL/SKIP"
        print(f"{status} - {test_name}")
    
    print()
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"📊 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    elif passed > 0:
        print("⚠️  SOME TESTS FAILED - Check Kimi API key configuration")
    else:
        print("❌ ALL TESTS FAILED - Kimi API key not configured")
    
    print()
    print("💡 To configure Kimi:")
    print("   export KIMI_API_KEY='your-moonshot-api-key'")
    print("   Or see KIMI_INTEGRATION.md for details")
    print()

if __name__ == "__main__":
    main()

