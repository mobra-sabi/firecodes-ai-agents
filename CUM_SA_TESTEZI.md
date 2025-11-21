# Cum Să Testezi Indexarea Industriei

## 🎯 Metode de Testare

### Metoda 1: Testare prin Interfață Web (RECOMANDAT)

#### Pași:
1. **Deschide interfața:** `http://100.66.157.27:8083/`
2. **Selectează un agent** din dropdown-ul din stânga
3. **Apasă butonul "🚀 Indexează Industria Completă"** (în panoul din dreapta)
4. **Confirmă** că vrei să continui (procesul poate dura 5-30 minute)
5. **Așteaptă** - vei vedea status în timp real:
   - "Inițializare indexare..."
   - Apoi progresul și rezultatele

#### Ce să verifici:
- ✅ Butonul devine disabled în timpul indexării
- ✅ Status update-uri în timp real
- ✅ Rezultatul final cu statistici (total descoperit, indexat, eșuat)
- ✅ Lista de site-uri indexate

---

### Metoda 2: Testare Directă prin API (curl)

#### Pas 1: Obține agent_id
```bash
# Lista toți agenții
curl http://100.66.157.27:8083/api/agents
```

#### Pas 2: Testează indexarea
```bash
# Înlocuiește AGENT_ID cu ID-ul real
curl -X POST http://100.66.157.27:8083/api/index-industry \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "AGENT_ID",
    "max_sites": 20
  }'
```

#### Răspuns așteptat:
```json
{
  "ok": true,
  "message": "Indexarea industriei a fost finalizată cu succes",
  "summary": {
    "total_discovered": 25,
    "total_indexed": 20,
    "total_failed": 5,
    "indexed_sites": [
      {
        "url": "https://competitor1.com",
        "domain": "competitor1.com",
        "service_name": "Serviciu 1",
        "chunks_count": 50,
        "vectors_count": 50
      }
    ],
    "failed_sites": [...]
  },
  "agent_id": "AGENT_ID",
  "timestamp": "2025-10-31T..."
}
```

---

### Metoda 3: Testare cu Python Script

#### Creează script `test_index_industry.py`:
```python
import requests
import json

# Configurare
BASE_URL = "http://100.66.157.27:8083"
AGENT_ID = "YOUR_AGENT_ID_HERE"  # Înlocuiește cu ID-ul real

# Test indexare
def test_index_industry():
    url = f"{BASE_URL}/api/index-industry"
    payload = {
        "agent_id": AGENT_ID,
        "max_sites": 20
    }
    
    print(f"🚀 Încep indexarea industriei pentru agent {AGENT_ID}...")
    print(f"   Max site-uri: {payload['max_sites']}")
    
    try:
        response = requests.post(url, json=payload, timeout=3600)  # 1 oră timeout
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("ok"):
            summary = data.get("summary", {})
            print("\n✅ Indexare finalizată cu succes!")
            print(f"   Total descoperit: {summary.get('total_discovered', 0)}")
            print(f"   Total indexat: {summary.get('total_indexed', 0)}")
            print(f"   Total eșuat: {summary.get('total_failed', 0)}")
            
            # Afișează site-uri indexate
            indexed = summary.get('indexed_sites', [])
            if indexed:
                print("\n📊 Site-uri indexate:")
                for site in indexed[:10]:  # Primele 10
                    print(f"   - {site.get('domain')} ({site.get('chunks_count', 0)} chunks)")
                if len(indexed) > 10:
                    print(f"   ... și încă {len(indexed) - 10} site-uri")
        else:
            print(f"❌ Eroare: {data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Eroare: {e}")

if __name__ == "__main__":
    test_index_industry()
```

#### Rulează scriptul:
```bash
cd /srv/hf/ai_agents
python3 test_index_industry.py
```

---

## 🔍 Verificare Rezultate

### 1. Verifică MongoDB

```python
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client.ai_agents_db

# Verifică resurse industriale indexate
resources = list(db.industry_resources.find({"main_agent_id": "YOUR_AGENT_ID"}))
print(f"Total resurse industriale: {len(resources)}")

for resource in resources:
    print(f"  - {resource.get('resource_domain')}: {resource.get('chunks_count', 0)} chunks")

# Verifică chunks în site_content
chunks = db.site_content.count_documents({
    "agent_id": "YOUR_AGENT_ID",
    "resource_type": "industry_resource"
})
print(f"\nTotal chunks industria: {chunks}")
```

### 2. Verifică Qdrant

```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://127.0.0.1:6333", prefer_grpc=True)

# Verifică colecția industriei
collection_name = f"industry_YOUR_AGENT_ID"
try:
    info = client.get_collection(collection_name)
    print(f"Colecție Qdrant: {collection_name}")
    print(f"  Total puncte: {info.points_count}")
except:
    print(f"❌ Colecția {collection_name} nu există")
```

### 3. Verifică Log-uri

```bash
# Verifică log-urile serverului
tail -n 100 /srv/hf/ai_agents/server.log | grep -i "index\|industry\|competitor"

# Sau pentru ultimele mesaje
tail -n 50 /srv/hf/ai_agents/server.log
```

---

## ✅ Checklist Testare

### Pre-Test:
- [ ] Serverul rulează (`http://100.66.157.27:8083/`)
- [ ] Agentul există și are strategie competitivă generată
- [ ] MongoDB și Qdrant rulează

### Test:
- [ ] Apelez `/api/index-industry` cu `agent_id` valid
- [ ] Răspunsul conține `ok: true`
- [ ] Rezumatul conține `total_discovered`, `total_indexed`, `total_failed`

### Post-Test:
- [ ] Verific MongoDB - `industry_resources` collection
- [ ] Verific MongoDB - `site_content` cu `resource_type: "industry_resource"`
- [ ] Verific Qdrant - colecția `industry_{agent_id}` există și are puncte
- [ ] Verific log-uri pentru erori

---

## 🐛 Troubleshooting

### Eroare: "Agent not found"
**Cauză:** Agent ID invalid sau agentul nu există
**Soluție:** Verifică că agentul există cu `/api/agents`

### Eroare: "Strategy not found"
**Cauză:** Strategia competitivă nu a fost generată
**Soluție:** Apelează mai întâi `/api/analyze-agent` pentru a genera strategia

### Eroare: "No sites discovered"
**Cauză:** Web search nu a găsit site-uri relevante
**Soluție:** 
- Verifică că SerpAPI key este setat în `.env` (sau folosește DuckDuckGo fallback)
- Verifică că strategia conține `web_search_queries`

### Eroare: "Indexing failed"
**Cauză:** Crawling sau indexarea site-urilor a eșuat
**Soluție:** 
- Verifică log-urile pentru detalii
- Verifică că Playwright este instalat (`playwright install chromium`)
- Verifică că MongoDB și Qdrant rulează

---

## 📊 Durata Estimată

- **Descoperire competitori:** 1-5 minute (depinde de numărul de queries)
- **Indexare fiecare site:** 2-5 minute per site
- **Total (20 site-uri):** 15-30 minute

**Notă:** Durata depinde de:
- Numărul de site-uri descoperite
- Mărimea fiecărui site
- Viteza conexiunii la internet
- Performanțele serverului

---

**Gata pentru testare!** 🚀

**Link interfață:** `http://100.66.157.27:8083/`

**Endpoint API:** `POST /api/index-industry`


