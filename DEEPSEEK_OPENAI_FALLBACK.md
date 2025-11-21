# ✅ FALLBACK IMPLEMENTAT: DeepSeek → OpenAI

## 🎯 CE AM IMPLEMENTAT

Sistemul acum încearcă **automat** OpenAI dacă DeepSeek nu răspunde sau dă timeout.

---

## 🔧 MODIFICĂRI

### 1️⃣ `.env` - API Keys actualizate

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 2️⃣ `tools/deepseek_client.py` - Fallback logic

**Funcții noi:**
- `_get_openai_key()` - Obține cheia OpenAI din .env
- `reasoner_chat(use_fallback=True)` - Parametru nou pentru fallback

**Flux:**
```
┌─────────────────────┐
│  reasoner_chat()    │
└──────────┬──────────┘
           │
           ▼
   🔄 Încearcă DeepSeek
   (3 retry-uri)
           │
           ├─ ✅ Succes → Returnează răspuns DeepSeek
           │
           └─ ❌ Eșuează (timeout/error)
                      │
                      ▼
              🤖 Fallback OpenAI
              (GPT-4 Turbo)
                      │
                      ├─ ✅ Succes → Returnează răspuns OpenAI
                      │              (marcat cu fallback: true)
                      │
                      └─ ❌ Eșuează → Aruncă eroare cu ambele eșecuri
```

**Cod nou:**

```python
# După 3 retry-uri DeepSeek failed
if use_fallback and last_error:
    logger.info("🤖 Fallback pe OpenAI GPT-4...")
    
    openai_payload = {
        "model": "gpt-4-turbo-preview",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    resp = requests.post(
        f"{OPENAI_BASE}/chat/completions",
        json=openai_payload,
        headers={"Authorization": f"Bearer {_get_openai_key()}"},
        timeout=timeout
    )
    
    return {
        "data": resp.json(), 
        "meta": {
            "duration_s": duration,
            "provider": "openai",
            "fallback": True
        }
    }
```

---

## 📊 UTILIZARE

### Activat implicit (default):
```python
from tools.deepseek_client import reasoner_chat

result = reasoner_chat(
    messages=[...],
    max_tokens=800,
    # use_fallback=True  # <-- DEFAULT
)

# Verifică ce provider a fost folosit
provider = result["meta"]["provider"]  # "deepseek" sau "openai"
fallback = result["meta"].get("fallback", False)

if provider == "openai":
    print("⚠️ A fost folosit OpenAI (DeepSeek nu a răspuns)")
```

### Dezactivat (doar DeepSeek):
```python
result = reasoner_chat(
    messages=[...],
    use_fallback=False  # <-- Aruncă eroare dacă DeepSeek eșuează
)
```

---

## 🎯 UNDE SE APLICĂ AUTOMAT

Fallback-ul funcționează **PESTE TOT** unde se folosește `reasoner_chat`:

| Funcție | Fallback Activ | Comportament |
|---------|----------------|--------------|
| **Chat** (`POST /ask`) | ✅ Yes | Încearcă DeepSeek → OpenAI |
| **Analizează Agent** (`POST /api/analyze-agent`) | ✅ Yes | Încearcă DeepSeek → OpenAI |
| **LangChain Chains** | ✅ Yes | Încearcă DeepSeek → OpenAI |
| **Industry Strategy** | ✅ Yes | Încearcă DeepSeek → OpenAI |

---

## 🔍 LOGGING

**În `server_8083.log` vei vedea:**

```
🔄 DeepSeek API call (attempt 1/3), timeout=180s, max_tokens=800
⚠️ DeepSeek API timeout (attempt 1/3). Retrying în 5s...
🔄 DeepSeek API call (attempt 2/3), timeout=210s, max_tokens=800
⚠️ DeepSeek API timeout (attempt 2/3). Retrying în 10s...
🔄 DeepSeek API call (attempt 3/3), timeout=240s, max_tokens=800
❌ DeepSeek API timeout după 3 încercări
🔄 Încerc fallback pe OpenAI...
🤖 Fallback pe OpenAI GPT-4...
✅ OpenAI API call successful în 3.45s (fallback)
```

---

## ⚠️ COSTURI

**Atenție:** OpenAI GPT-4 este mai scump decât DeepSeek!

- **DeepSeek Reasoner:** ~$0.14 / 1M tokens
- **GPT-4 Turbo:** ~$10.00 / 1M tokens input + $30.00 / 1M tokens output

**Recomandare:** Fallback-ul va fi folosit **DOAR** când DeepSeek nu răspunde, deci doar în situații de urgență.

---

## ✅ AVANTAJE

1. **Zero downtime** - Dacă DeepSeek pică, sistemul continuă cu OpenAI
2. **Transparent** - Frontend-ul nu știe diferența
3. **Marcat clar** - `meta.fallback=true` pentru monitoring
4. **Configarabil** - Poate fi dezactivat per apel

---

## 🧪 TESTARE

```bash
cd /srv/hf/ai_agents
python3 tools/deepseek_client.py
# Sau
python3 << 'EOF'
from tools.deepseek_client import reasoner_chat
result = reasoner_chat([{"role": "user", "content": "Test"}])
print(result["meta"]["provider"])  # deepseek sau openai
EOF
```

---

**Data implementării:** 2025-11-07  
**Status:** ✅ Activ și testat  
**Server:** Repornit cu noile configurări
