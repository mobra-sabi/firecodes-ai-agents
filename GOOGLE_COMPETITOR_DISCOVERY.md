# 🔍 Google Competitor Discovery - Arhitectură

## 📋 OVERVIEW

Sistemul caută competitori pe Google folosind keywords generate de DeepSeek, 
agregă rezultatele inteligent, și calculează scoring de relevanță.

---

## 🏗️ FLOW COMPLET

```
TASK 1 (DeepSeek Analysis)
    ↓
    Generează keywords per subdomeniu
    ↓
TASK 2 (Google Discovery)
    ↓
    Pentru fiecare keyword:
    ├─ Search Google (top 20 rezultate)
    ├─ Extrage: URL, title, description
    ├─ Adaugă în buffer (deduplicare)
    └─ Track: keyword, subdomain, poziție
    ↓
    Agregare inteligentă:
    ├─ Deduplicare (același site = 1 entry)
    ├─ Scoring (appearances + position + diversity)
    ├─ Filtrare (exclude marketplace-uri, directoare)
    └─ Ranking (cei mai relevanți competitori)
    ↓
    Salvare în MongoDB
    ↓
TASK 3 (Scraping Competitori) ⏳
```

---

## ✨ ÎMBUNĂTĂȚIRI FAȚĂ DE IDEEA INIȚIALĂ

### **1. Deduplicare Inteligentă** ✅
- Același site apare la mai multe keywords → o singură intrare
- Dar trackuim: **la ce keywords a apărut**
- Rezultat: știm ce subdomenii acoperă fiecare competitor

### **2. Scoring Complex** ✅
Formula:
```python
score = (
    keyword_coverage * 40% +     # Câte keywords (diversitate)
    position_score * 40% +        # Poziții în Google (autoritate)
    subdomain_diversity * 20%     # Câte subdomenii (relevanță)
)
```

**Exemplu:**
- Competitor A: apare la 15/60 keywords, poziție medie 3
  → Score: 82.5
- Competitor B: apare la 5/60 keywords, poziție medie 8
  → Score: 45.2

### **3. Filtrare Automată** ✅
Exclude:
- Marketplace-uri (OLX, Amazon, eBay)
- Directoare (Pagini Aurii, Lista Firme)
- Social media (Facebook, LinkedIn)
- Propriul agent

### **4. Mapări Multiple** ✅
- **keywords_map**: keyword → [competitori]
- **subdomain_map**: subdomeniu → [competitori]
- **Permite**: "Cine sunt competitorii mei pe subdomeniul X?"

### **5. Metadata Rica** ✅
Pentru fiecare competitor:
```json
{
  "domain": "competitor.ro",
  "score": 75.3,
  "appearances_count": 12,
  "keywords_matched": ["keyword1", "keyword2", ...],
  "subdomains_matched": ["Subdomeniu A", "Subdomeniu B"],
  "avg_position": 4.5,
  "best_position": 2,
  "title": "Competitor Title",
  "description": "...",
  "url": "https://competitor.ro"
}
```

---

## 🔌 API ENDPOINTS

### **1. POST `/agents/{id}/discover-competitors`**

**Descriere:** Descoperă competitori prin Google search

**Params:**
- `results_per_keyword`: câte rezultate per keyword (default 20)

**Response:**
```json
{
  "ok": true,
  "competitors_found": 45,
  "top_10_competitors": [...],
  "stats": {
    "total_keywords_searched": 60,
    "total_sites_discovered": 120,
    "total_competitors": 45,
    "top_competitor": "competitor1.ro",
    "subdomains_coverage": {...}
  }
}
```

---

### **2. GET `/agents/{id}/competitors`**

**Descriere:** Obține lista completă de competitori

**Params:**
- `limit`: câți competitori (default 50)

**Response:**
```json
{
  "ok": true,
  "total_competitors": 45,
  "competitors": [...],
  "stats": {...}
}
```

---

### **3. GET `/agents/{id}/competitors/by-subdomain/{name}`**

**Descriere:** Filtrează competitori per subdomeniu

**Response:**
```json
{
  "ok": true,
  "subdomain": "Protecție pasivă la foc",
  "competitors_count": 12,
  "competitors": [...]
}
```

---

## 🎯 EXEMPLE DE OUTPUT

### **Statistici:**
```
📊 STATISTICI:
   • Keywords căutate: 60
   • Site-uri descoperite: 120
   • Competitori finali: 45
   • Top competitor: protectielafoc.ro
   • Appearances medii: 8.5

📦 COVERAGE PER SUBDOMENIU:
   • Protecție pasivă la foc: 15 competitori
   • Sisteme compartimentare: 12 competitori
   • Ignifugare materiale: 18 competitori
   ...
```

### **Top Competitori:**
```
🏆 TOP 10 COMPETITORI:

1. protectielafoc.ro - Score: 85.3
   📝 Protecție la foc pentru structuri - Certificat ISU
   🔗 https://protectielafoc.ro
   📊 Apariții: 18 | Poziție medie: 3.2 | Best: #1
   📦 Subdomenii: Protecție pasivă, Compartimentare, Ignifugare
   🔑 Keywords: protecție la foc, vopsea intumescentă, ...

2. fireprotection.ro - Score: 78.9
   ...
```

---

## ⚙️ CONFIGURARE GOOGLE SEARCH

### **Opțiunea 1: Scraping Free (Default)** ✅
- Folosește `googlesearch-python`
- **Avantaje:** Gratuit, unlimited
- **Dezavantaje:** Mai lent, poate fi blocat

**Setup:**
```bash
pip install googlesearch-python
```

### **Opțiunea 2: Google Custom Search API**
- Necesită API key + CSE ID
- **Avantaje:** Rapid, stabil, metadata completă
- **Dezavantaje:** Limitat (100 queries/zi gratuit)

**Setup:**
```bash
export GOOGLE_API_KEY="your-key"
export GOOGLE_CSE_ID="your-cse-id"
```

### **Opțiunea 3: SerpAPI** (Recomandat pentru producție)
- API specializat pentru search
- **Avantaje:** Cel mai robust, metadata completă
- **Dezavantaje:** Platit (dar are free tier: 100 searches/lună)

**Setup:**
```bash
export SERPAPI_KEY="your-serpapi-key"
```

---

## 📊 SCORING ALGORITHM DETALIAT

```python
def calculate_score(competitor):
    # 1. Keyword Coverage (0-100)
    keyword_score = (appearances / total_keywords) * 100
    
    # 2. Position Score (0-100)
    # Poziția 1 = 100 puncte, poziția 20 = 0 puncte
    avg_position = sum(positions) / len(positions)
    position_score = max(0, 100 - (avg_position * 5))
    
    # 3. Subdomain Diversity (0-50)
    # Fiecare subdomeniu = +10 puncte, max 50
    subdomain_score = min(subdomain_count * 10, 50)
    
    # 4. Final Score (weighted average)
    final_score = (
        keyword_score * 0.4 +      # 40% importanță
        position_score * 0.4 +     # 40% importanță
        subdomain_score * 0.2      # 20% importanță
    )
    
    return final_score
```

**Exemplu calculat:**
```
Competitor: fireprotection.ro
- Appearances: 15/60 keywords → 25%
- Avg position: 4.5 → position_score = 77.5
- Subdomains: 3 → subdomain_score = 30

Score = 25*0.4 + 77.5*0.4 + 30*0.2 = 47.0
```

---

## 🚀 NEXT STEPS RECOMANDATE

După TASK 2, pot urma:

### **TASK 3: Scraping Competitori** ⭐
- Folosește același flow ca `site_agent_creator`
- Creează agenți pentru top 10-20 competitori
- Benefit: ai tot contextul lor în MongoDB + Qdrant

### **TASK 4: Extragere Caracteristici Competitive**
- Analizează: prețuri, servicii, USP-uri, testimoniale
- Folosește DeepSeek pentru extragere inteligentă
- Salvează în structură comparabilă

### **TASK 5: Analiză Comparativă**
- DeepSeek compară: TU vs TOP 10 competitori
- Output: puncte forte/slabe, oportunități, amenințări
- Strategii de diferențiere

### **TASK 6: Monitoring Continuu**
- Re-rulează discovery periodic (lunar)
- Detectează: competitori noi, schimbări în ranking
- Alerte automate

---

## ✅ AVANTAJE ARHITECTURĂ

✅ **Deduplicare inteligentă** - Nu pierzi informație
✅ **Scoring complex** - Identifici cei mai relevanți
✅ **Filtrare automată** - Elimină noise-ul
✅ **Mapări multiple** - Flexibilitate în analiză
✅ **API-first** - Ușor de integrat
✅ **Scalabil** - Funcționează pentru orice industrie
✅ **Configurabil** - Multiple surse de date (scraping/API)

---

*Creat: 2025-11-09*
