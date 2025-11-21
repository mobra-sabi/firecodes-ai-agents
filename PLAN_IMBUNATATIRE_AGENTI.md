# 🎯 PLAN ÎMBUNĂTĂȚIRE PROCES CREARE AGENȚI

## Obiectiv
Proces robust de creare agenți care:
- ✅ Funcționează pe ORICE tip de site
- ✅ Are verificări la fiecare pas
- ✅ Garantează că DeepSeek primește date de calitate
- ✅ Se auto-validează înainte de marcare ca "ready"

---

## 📋 ETAPE IMPLEMENTARE

### 1. ÎMBUNĂTĂȚIRE CRAWLING (site_agent_creator.py)
**Status:** 🔄 IN PROGRESS

**Probleme actuale:**
- ❌ Unele site-uri dau 0 chunks (protectiaantifoc.ro, romstal.ro)
- ❌ Crawler se blochează pe site-uri dinamice
- ❌ Nu detectează când un site e down/inaccesibil
- ❌ Nu extrage corect serviciile

**Soluții:**
- ✅ Adaugă multiple strategii de scraping:
  1. Playwright (actual)
  2. Requests + BeautifulSoup (fallback)
  3. Selenium (fallback final)
- ✅ Detectează tip site (static, SPA, WordPress, etc.)
- ✅ Timeout-uri mai scurte (5s per pagină)
- ✅ Retry logic pentru fiecare pagină
- ✅ Verificare după fiecare pagină: text_length > 100

**Cod de adăugat:**
```python
async def smart_crawl_with_fallbacks(url, websocket):
    """
    Încearcă mai multe strategii de crawling
    """
    strategies = [
        ("playwright", crawl_with_playwright),
        ("requests", crawl_with_requests),
        ("selenium", crawl_with_selenium)
    ]
    
    for name, func in strategies:
        try:
            result = await func(url, websocket)
            if result['chunks'] >= 2:  # Minim 2 chunks
                return result
        except Exception as e:
            logger.warning(f"Strategy {name} failed: {e}")
            continue
    
    raise ValueError("Toate strategiile de crawling au eșuat")
```

---

### 2. VERIFICĂRI OBLIGATORII LA FIECARE PAS
**Status:** ⏳ PENDING

**Verificări de adăugat:**

#### A. După Auto Site Extractor:
```python
# Verificare: Avem minim 5 servicii?
if len(extracted_services) < 2:
    logger.warning("Prea puține servicii extrase, încerc analiza manuală")
    # Fallback: Analizează conținut cu Qwen pentru a detecta servicii
```

#### B. După Crawling:
```python
# Verificare: Avem minim 2 pagini cu conținut?
valid_pages = [p for p in pages if len(p['text']) > 100]
if len(valid_pages) < 2:
    raise ValueError(f"Site incomplet: doar {len(valid_pages)} pagini valide")
```

#### C. După Salvare MongoDB:
```python
# Verificare: Datele sunt în DB?
saved_chunks = db.site_content.count_documents({"agent_id": agent_id})
if saved_chunks < 2:
    raise ValueError(f"Salvare incompletă: doar {saved_chunks} chunks în DB")
```

#### D. După Creare Qdrant:
```python
# Verificare: Vectorii sunt în Qdrant? (dacă disponibil)
if qdrant_available:
    vector_count = check_qdrant_vectors(collection_name)
    if vector_count < saved_chunks - 1:  # Tolerăm 1 diferență
        logger.warning(f"Vectori incompleți: {vector_count}/{saved_chunks}")
```

---

### 3. ASIGURARE CALITATE PENTRU DEEPSEEK
**Status:** ⏳ PENDING

**Cerințe minime pentru un agent valid:**
```python
AGENT_QUALITY_REQUIREMENTS = {
    "min_content_chunks": 2,
    "min_total_characters": 1000,
    "min_services": 1,
    "required_fields": ["domain", "site_url", "status", "created_at"],
    "required_metadata": ["business_type", "contact_info"]
}

def validate_agent_quality(agent_id):
    """
    Verifică dacă agentul respectă cerințele minime
    """
    agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
    content = list(db.site_content.find({"agent_id": ObjectId(agent_id)}))
    
    checks = {
        "chunks": len(content) >= 2,
        "content_length": sum(len(c.get('content', '')) for c in content) >= 1000,
        "services": len(agent.get('services', [])) >= 1,
        "fields": all(agent.get(f) for f in ["domain", "site_url", "status"]),
        "created_at": agent.get('created_at') is not None
    }
    
    return all(checks.values()), checks
```

---

### 4. RETRY LOGIC & FALLBACK-URI
**Status:** ⏳ PENDING

**Puncte critice cu retry:**

#### A. Crawling cu Playwright:
```python
@retry(max_attempts=3, delay=2)
async def crawl_page_with_retry(page, url):
    """Retry pentru fiecare pagină"""
    return await page.goto(url, timeout=10000)
```

#### B. Salvare MongoDB:
```python
@retry(max_attempts=5, delay=0.5)
def save_to_mongo_with_retry(collection, data):
    """Retry pentru operații MongoDB"""
    return collection.insert_one(data)
```

#### C. Qdrant (dacă disponibil):
```python
def create_qdrant_with_fallback(chunks, collection_name):
    """Încearcă Qdrant, continuă fără el dacă eșuează"""
    try:
        return create_qdrant_collection(chunks, collection_name)
    except Exception as e:
        logger.warning(f"Qdrant failed: {e}, continuăm fără vectori")
        return {"success": False, "reason": str(e)}
```

---

### 5. TESTARE AUTOMATĂ CU DIVERSE SITE-URI
**Status:** ⏳ PENDING

**Lista site-uri de test:**
```python
TEST_SITES = [
    # Site-uri simple
    "https://example.com",
    "https://www.ropaintsolutions.ro",
    
    # Site-uri WordPress
    "https://www.tehnica-antifoc.ro",
    
    # Site-uri SPA (React/Vue)
    "https://www.rezistentlafoc.ro",
    
    # Site-uri cu anti-scraping
    "https://www.emag.ro",
    
    # Site-uri cu Cloudflare
    "https://www.pcgarage.ro"
]
```

**Script de testare:**
```python
async def test_agent_creation_pipeline():
    results = {"success": [], "failed": []}
    
    for url in TEST_SITES:
        try:
            agent = await create_agent_logic(url)
            is_valid, checks = validate_agent_quality(agent['agent_id'])
            
            if is_valid:
                results["success"].append(url)
            else:
                results["failed"].append({"url": url, "checks": checks})
        except Exception as e:
            results["failed"].append({"url": url, "error": str(e)})
    
    return results
```

---

### 6. VALIDARE AUTOMATĂ ÎNAINTE DE "READY"
**Status:** ⏳ PENDING

**Modificare în `create_agent_logic`:**
```python
async def create_agent_logic(url, ...):
    # ... procesare ...
    
    # ⭐ VERIFICARE FINALĂ ÎNAINTE DE MARCARE CA READY
    is_valid, checks = validate_agent_quality(agent_id)
    
    if not is_valid:
        logger.error(f"Agent {agent_id} NU respectă cerințele: {checks}")
        db.site_agents.update_one(
            {"_id": ObjectId(agent_id)},
            {"$set": {
                "status": "incomplete",
                "validation_errors": checks
            }}
        )
        raise ValueError(f"Agent incomplet: {checks}")
    
    # Doar dacă e valid, marchează ca ready
    db.site_agents.update_one(
        {"_id": ObjectId(agent_id)},
        {"$set": {"status": "ready"}}
    )
```

---

## 📊 METRICI DE SUCCES

Un agent este considerat **VALID** dacă:
- ✅ Are minimum 2 chunks de conținut
- ✅ Total caractere > 1000
- ✅ Are minimum 1 serviciu detectat
- ✅ Are `created_at` timestamp
- ✅ Are `domain`, `site_url`, `status`
- ✅ DeepSeek poate genera o strategie (nu eșuează)

---

## 🚀 PLAN DE EXECUȚIE

1. ✅ Creare document plan (ACEST FIȘIER)
2. 🔄 Implementare `smart_crawl_with_fallbacks`
3. ⏳ Adăugare verificări la fiecare pas
4. ⏳ Implementare `validate_agent_quality`
5. ⏳ Testare cu 10 site-uri diverse
6. ⏳ Ajustări finale bazate pe rezultate
7. ⏳ Documentație actualizată

---

**Data început:** 2025-11-07
**Target finalizare:** 2025-11-07 (același task session)

