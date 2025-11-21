# 🔑 Setup DeepSeek API Key

## Problema
Chat-ul returnează eroare: `401 - Authentication Fails`

## Soluție

### 1. Obține API Key de la DeepSeek
- Accesează: https://platform.deepseek.com/
- Creează cont sau loghează-te
- Obține API key din dashboard

### 2. Setează API Key

#### Opțiunea 1: Environment Variable
```bash
export DEEPSEEK_API_KEY='sk-your-api-key-here'
```

#### Opțiunea 2: Fișier .env
Creează `/srv/hf/ai_agents/.env`:
```
DEEPSEEK_API_KEY=sk-your-api-key-here
```

#### Opțiunea 3: Permanent în sistem
Adaugă în `/etc/environment` sau `~/.bashrc`:
```bash
export DEEPSEEK_API_KEY='sk-your-api-key-here'
```

### 3. Verifică
```bash
python3 << 'EOF'
import os
api_key = os.getenv("DEEPSEEK_API_KEY", "")
if api_key:
    print(f"✅ API Key setat ({len(api_key)} caractere)")
else:
    print("❌ API Key NU este setat")
EOF
```

### 4. Repornește API-ul
```bash
pkill -f "uvicorn agent_api"
nohup python3 -m uvicorn agent_api:app --host 0.0.0.0 --port 8090 > logs/agent_api.log 2>&1 &
```

## Format API Key
- Trebuie să înceapă cu `sk-`
- Exemplu: `sk-1234567890abcdef...`

## Test
După setare, testează chat-ul:
```bash
curl -X POST http://localhost:8090/api/agents/{agent_id}/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Test"}'
```

---

**Notă**: Fără API key valid, chat-ul nu va funcționa.

