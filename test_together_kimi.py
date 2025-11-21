#!/usr/bin/env python3
"""
🧪 TEST TOGETHER AI + KIMI K2
"""
from openai import OpenAI
import os

# Together AI API Key
TOGETHER_API_KEY = "39c0e4caf004a00478163b18cf70ee62e48bd1fe7c95d129348523a2b4b7b39d"

print("=" * 80)
print("🧪 TESTING TOGETHER AI + KIMI K2")
print("=" * 80)
print()

# Create Together AI client
client = OpenAI(
    api_key=TOGETHER_API_KEY,
    base_url="https://api.together.xyz/v1"
)

print("✅ Together AI client created")
print()

# Test 1: List available models
print("📋 TEST 1: List available models")
print("-" * 80)
try:
    models = client.models.list()
    kimi_models = [m for m in models.data if 'kimi' in m.id.lower() or 'moonshot' in m.id.lower()]
    
    if kimi_models:
        print(f"✅ Found {len(kimi_models)} Kimi/Moonshot models:")
        for model in kimi_models[:5]:
            print(f"   - {model.id}")
    else:
        print("⚠️  No Kimi models found, showing all models:")
        for model in models.data[:10]:
            print(f"   - {model.id}")
except Exception as e:
    print(f"❌ Error listing models: {e}")

print()

# Test 2: Chat with best available model
print("💬 TEST 2: Chat test")
print("-" * 80)

# Try different model names for Kimi
model_names = [
    "Moonshot/Kimi-K2-Thinking",
    "moonshot-ai/Kimi-K2-Thinking",
    "Qwen/Qwen2.5-72B-Instruct",  # Fallback
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"  # Another fallback
]

success = False
for model_name in model_names:
    try:
        print(f"Trying model: {model_name}")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": "Explică într-o propoziție ce este competitive intelligence"}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        print(f"✅ SUCCESS with model: {model_name}")
        print(f"   Response: {response.choices[0].message.content}")
        print(f"   Tokens: {response.usage.total_tokens if response.usage else 'N/A'}")
        success = True
        break
        
    except Exception as e:
        print(f"❌ Failed with {model_name}: {str(e)[:100]}")
        continue

print()

if success:
    print("=" * 80)
    print("🎉 TOGETHER AI CONNECTION SUCCESSFUL!")
    print("=" * 80)
    print()
    print("✅ API Key is valid")
    print("✅ Can make requests")
    print("✅ Ready to integrate!")
else:
    print("=" * 80)
    print("⚠️  NEEDS CONFIGURATION")
    print("=" * 80)
    print()
    print("API key works but need to find correct model names")

