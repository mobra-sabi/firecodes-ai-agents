#!/usr/bin/env python3
"""
Script de test pentru DeepSeek API
Verifică conectivitatea și identifică probleme
"""

import os
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv

# Încarcă variabilele de mediu
load_dotenv(override=True)

def test_deepseek_api():
    """Testează DeepSeek API și identifică probleme"""
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    if not api_key:
        print("❌ DEEPSEEK_API_KEY sau OPENAI_API_KEY nu este setat")
        print("   💡 Adaugă cheia în fișierul .env")
        return False
    
    print(f"🕐 Test la: {datetime.now().isoformat()}")
    print(f"📋 Configurație:")
    print(f"   API Key: {api_key[:10]}...{api_key[-5:]}")
    print(f"   Base URL: {base_url}")
    print(f"   Model: {model}\n")
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=30.0
        )
        
        # Testează cu modelul specificat
        print(f"🧪 Testez cu {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Test de conectivitate"}],
            max_tokens=20,
            temperature=0.7
        )
        
        print(f"✅ DeepSeek API funcționează perfect!")
        print(f"   Model: {response.model}")
        print(f"   Response: {response.choices[0].message.content}")
        print(f"   Usage: {response.usage.total_tokens} tokens")
        
        return True
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ Eroare DeepSeek API: {error_str}\n")
        
        if "401" in error_str or "authentication" in error_str.lower():
            print("🔍 Problema: Autentificare eșuată")
            print("   💡 Verifică cheia în contul DeepSeek")
            print("   💡 Generează o cheie nouă dacă este necesar")
        elif "429" in error_str or "rate limit" in error_str.lower():
            print("🔍 Problema: Rate limiting")
            print("   💡 Așteaptă câteva minute sau reduce request-urile")
            print("   💡 Verifică planul tău DeepSeek pentru limite")
        elif "quota" in error_str.lower() or "insufficient" in error_str.lower():
            print("🔍 Problema: Cotă epuizată")
            print("   💡 Verifică cota în contul DeepSeek")
            print("   💡 Adaugă credite sau upgrade planul")
        elif "model" in error_str.lower() and "not found" in error_str.lower():
            print("🔍 Problema: Modelul nu este disponibil")
            print("   💡 Folosește 'deepseek-chat' în loc de 'deepseek-reasoner'")
            print("   💡 Verifică disponibilitatea modelului în contul tău")
        else:
            print("🔍 Problema necunoscută")
            print("   💡 Verifică logurile pentru detalii")
        
        import traceback
        print(f"\n📋 Traceback complet:")
        print(traceback.format_exc())
        
        return False

if __name__ == "__main__":
    success = test_deepseek_api()
    exit(0 if success else 1)

