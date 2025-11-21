import requests
import sys

# Citește direct din .env
api_key = None
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('DEEPSEEK_API_KEY='):
            api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

if not api_key:
    print("❌ DEEPSEEK_API_KEY nu găsit în .env!")
    sys.exit(1)

print("🔍 TEST DIRECT DEEPSEEK API")
print("="*70)
print(f"✅ API Key găsit: {api_key[:15]}...")
print()

# Test 1: Request FOARTE simplu
payload = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50,
    "temperature": 0.7
}

print("📤 Trimit request simplu...")
print(f"   Model: {payload['model']}")
print()

try:
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=30
    )
    
    print(f"📥 Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅✅✅ SUCCES!")
        data = response.json()
        print(f"   Model folosit: {data.get('model')}")
        print(f"   Răspuns: {data['choices'][0]['message']['content'][:100]}")
    else:
        print(f"❌ EROARE {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"❌ Excepție: {e}")

print("="*70)
