# 🧪 Ghid de Testare - Integrare LangChain

## Testare Rapidă

### 1. Testare automată completă
```bash
cd /srv/hf/ai_agents
python3 test_langchain_integration.py
```

### 2. Testare manuală endpointuri

#### Listează lanțurile disponibile
```bash
curl http://localhost:8083/chains/list | python3 -m json.tool
```

#### Preview pentru un lanț specific
```bash
curl http://localhost:8083/chains/site_analysis/preview | python3 -m json.tool
curl http://localhost:8083/chains/industry_strategy/preview | python3 -m json.tool
curl http://localhost:8083/chains/decision_chain/preview | python3 -m json.tool
```

#### Rulează un lanț pentru un agent
```bash
# Obține ID-ul unui agent
AGENT_ID=$(curl -s http://localhost:8083/agents/list | python3 -c "import sys, json; print(json.load(sys.stdin)['agents'][0]['_id'])")

# Rulează decision_chain
curl -X POST http://localhost:8083/agents/$AGENT_ID/run_chain/decision_chain \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "strategy": {
        "summary": "Strategie de test",
        "opportunities": ["SEO", "Social Media"]
      }
    }
  }' | python3 -m json.tool
```

### 3. Testare Python directă

```python
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

# Test Chain Registry
from langchain_agents.chain_registry import get_chain_registry
registry = get_chain_registry()
print(f"Lanțuri disponibile: {registry.list_chains()}")

# Test LLM Manager
from langchain_agents.llm_manager import get_qwen_llm, get_deepseek_llm
qwen = get_qwen_llm()
deepseek = get_deepseek_llm()
print(f"Qwen: {'✅' if qwen else '❌'}")
print(f"DeepSeek: {'✅' if deepseek else '❌'}")

# Test Decision Chain
from langchain_agents.chains.decision_chain import create_decision_chain
decision_chain = create_decision_chain()
if decision_chain:
    print("✅ Decision Chain creat cu succes")
```

### 4. Testare Actions Module

```python
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

from actions import ActionExecutor, execute_action_plan

executor = ActionExecutor()
print(f"Conectori disponibili: {list(executor.connectors.keys())}")

# Test cu un action plan de exemplu
action_plan = {
    "immediate_actions": [
        {
            "action": "Creează campanie Google Ads",
            "tool": "google_ads",
            "priority": "high"
        }
    ]
}

# result = await execute_action_plan("agent_id", action_plan)
# print(result)
```

## Testare End-to-End

### Scenariu complet: Analiză site → Strategie → Acțiuni

1. **Creează/selectează un agent**
2. **Rulează Site Analysis Chain**
3. **Rulează Industry Strategy Chain** (folosind rezultatele de la pasul 2)
4. **Rulează Decision Chain** (folosind strategia de la pasul 3)
5. **Execută Action Plan** (folosind acțiunile de la pasul 4)

## Verificare Loguri

```bash
# Loguri server
tail -f /srv/hf/ai_agents/server_8083.log | grep -E "LangChain|chain|ERROR"

# Verificare erori
grep -i error /srv/hf/ai_agents/server_8083.log | tail -20
```

## Debugging

### Verificare conectivitate DeepSeek
```bash
python3 test_deepseek_api.py
```

### Verificare Chain Registry
```python
from langchain_agents.chain_registry import get_chain_registry
registry = get_chain_registry()
for chain_name in registry.list_chains():
    chain = registry.get(chain_name)
    print(f"{chain_name}: {'✅' if chain else '❌'}")
```

### Verificare LLM disponibilitate
```python
from langchain_agents.llm_manager import get_qwen_llm, get_deepseek_llm

qwen = get_qwen_llm()
deepseek = get_deepseek_llm()

print(f"Qwen: {qwen is not None}")
print(f"DeepSeek: {deepseek is not None}")
```

