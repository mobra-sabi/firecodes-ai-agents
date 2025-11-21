#!/usr/bin/env python3
"""Test pentru API keys DeepSeek + OpenAI cu fallback"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

print("╔══════════════════════════════════════════════════════════════════════╗")
print("║  🔐 TEST: API KEYS - DeepSeek + OpenAI Fallback                     ║")
print("╚══════════════════════════════════════════════════════════════════════╝")
print()

# Test DeepSeek
deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
print("1️⃣  TEST DeepSeek API")
print("-" * 70)
print(f"   Key: {deepseek_key[:10]}...{deepseek_key[-4:]}")

if deepseek_key:
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {deepseek_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": "Spune 'Hello' în română"}
                ],
                "max_tokens": 50
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            reply = result["choices"][0]["message"]["content"]
            print(f"   ✅ SUCCES! DeepSeek răspunde: {reply}")
            print(f"   Model: {result.get('model', 'N/A')}")
            print(f"   Usage: {result.get('usage', {})}")
        else:
            print(f"   ❌ EROARE: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"   ❌ EROARE: {e}")
else:
    print("   ⚠️  API Key lipsește")

print()

# Test OpenAI
openai_key = os.getenv("OPENAI_API_KEY", "")
print("2️⃣  TEST OpenAI API (Fallback)")
print("-" * 70)
print(f"   Key: {openai_key[:10]}...{openai_key[-4:]}")

if openai_key:
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {"role": "user", "content": "Spune 'Hello' în română"}
                ],
                "max_tokens": 50
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            reply = result["choices"][0]["message"]["content"]
            print(f"   ✅ SUCCES! OpenAI răspunde: {reply}")
            print(f"   Model: {result.get('model', 'N/A')}")
            print(f"   Usage: {result.get('usage', {})}")
        else:
            print(f"   ❌ EROARE: {response.status_code}")
            print(f"   {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ EROARE: {e}")
else:
    print("   ⚠️  API Key lipsește")

print()
print("═══════════════════════════════════════════════════════════════════════")
print("📋 REZULTAT:")
print()

if deepseek_key and openai_key:
    print("✅ Ambele API keys sunt configurate")
    print("✅ Fallback DeepSeek → OpenAI activ")
    print()
    print("🎯 CONFIGURAȚIE FINALĂ:")
    print("   PRIMARY: DeepSeek (deepseek-chat)")
    print("   FALLBACK: OpenAI (gpt-4-turbo-preview)")
else:
    if not deepseek_key:
        print("⚠️  DeepSeek API key lipsește")
    if not openai_key:
        print("⚠️  OpenAI API key lipsește")

print("═══════════════════════════════════════════════════════════════════════")
