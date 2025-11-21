# 🎯 WORKFLOW COMPLET: Keywords → Google → Competitori → Slave Agents → Monitoring SERP

## 📋 PROCESUL COMPLET (CE TREBUIE SĂ SE ÎNTÂMPLE)

### **FAZA 4: Generare Keywords** ✅ FIXAT
**Status:** ✅ Funcționează și salvează în MongoDB

**Ce se întâmplă:**
```
protectiilafoc.ro
├── Subdomeniu 1: "Protecție pasivă la foc"
│   ├── "protecție la foc structuri metalice București"
│   ├── "termoprotecție vopsea intumescentă"
│   ├── "ignifugare lemn certificată"
│   ├── "sisteme antiincendiu pasive"
│   └── "fire resistant doors Romania"
│
├── Subdomeniu 2: "Protecție activă la foc"
│   ├── "sisteme sprinklere antiincendiu"
│   ├── "detectoare fum certificate"
│   └── ... (5 keywords)
│
├── Subdomeniu 3: "Consultanță și audit"
│   └── ... (5 keywords)
│
├── Subdomeniu 4: "Formare și instruire"
│   └── ... (5 keywords)
│
└── Overall Keywords (10): "protecție la foc", "fire protection", etc.

TOTAL: 30 keywords
```

**Output MongoDB:**
```json
{
  "_id": "6915e1275eb1766cbe71fd4b",
  "domain": "protectiilafoc.ro",
  "keywords": [
    "protecție la foc structuri metalice București",
    "termoprotecție vopsea intumescentă",
    // ... 28 more
  ],
  "subdomains": ["Protecție pasivă la foc", ...],
  "status": "keywords_generated"
}
```

---

### **FAZA 5: Google Search pentru FIECARE Keyword** ⚠️ DE VERIFICAT
**Status:** ✅ Codul există, dar trebuie verificat ce salvează

**Ce TREBUIE să se întâmple:**

#### **5.1. Search Google pentru fiecare keyword** (30 keywords × 10 rezultate = 300 URLs)

```python
# Pentru FIECARE keyword:
keyword = "protecție la foc structuri metalice București"

# Google Search (Brave API sau Google Custom Search)
results = brave_search(keyword, count=10)  # Prima pagină Google

# Rezultate pentru acest keyword:
[
  {
    "position": 1,
    "url": "https://competitor1.ro/protectie-foc",
    "title": "Protecție la foc - Competitor 1",
    "snippet": "Oferim servicii de protecție...",
    "domain": "competitor1.ro"
  },
  {
    "position": 2,
    "url": "https://competitor2.ro/termoprotectie",
    "title": "Termoprotecție structuri - Competitor 2",
    "domain": "competitor2.ro"
  },
  // ... până la poziția 10
]
```

#### **5.2. Deduplicare și agregare competitori**

```python
# Agregăm TOATE rezultatele pentru TOATE keywords
competitors = {}

for keyword in all_keywords:  # 30 keywords
    results = google_search(keyword)  # 10 rezultate/keyword
    
    for position, result in enumerate(results, 1):
        domain = extract_domain(result["url"])
        
        # Exclude marketplace-uri și directoare
        if domain in EXCLUDED_DOMAINS:
            continue
        
        # Exclude masterul (propriul site)
        if domain == "protectiilafoc.ro":
            master_positions.append({
                "keyword": keyword,
                "position": position,
                "url": result["url"]
            })
            continue
        
        # Adaugă/update competitor
        if domain not in competitors:
            competitors[domain] = {
                "domain": domain,
                "urls": [],
                "keywords_ranked": [],
                "positions": [],
                "appearances": 0,
                "best_position": 999,
                "avg_position": 0,
                "threat_score": 0
            }
        
        competitors[domain]["appearances"] += 1
        competitors[domain]["keywords_ranked"].append(keyword)
        competitors[domain]["positions"].append(position)
        competitors[domain]["urls"].append({
            "keyword": keyword,
            "position": position,
            "url": result["url"],
            "title": result["title"],
            "snippet": result["snippet"],
            "discovered_at": datetime.now()
        })
        
        # Update best position
        if position < competitors[domain]["best_position"]:
            competitors[domain]["best_position"] = position
```

#### **5.3. Calcul metrici pentru fiecare competitor**

```python
for domain, data in competitors.items():
    # Average Position
    data["avg_position"] = sum(data["positions"]) / len(data["positions"])
    
    # Keyword Overlap cu masterul
    master_keywords = set(all_keywords)
    competitor_keywords = set(data["keywords_ranked"])
    data["keyword_overlap"] = len(master_keywords & competitor_keywords)
    data["overlap_percentage"] = (data["keyword_overlap"] / len(master_keywords)) * 100
    
    # Threat Score (0-100)
    # Formula: 
    # - Appearances (30%)
    # - Average Position (40%) - poziții mai bune = threat mai mare
    # - Keyword Overlap (30%)
    
    appearances_score = min((data["appearances"] / len(all_keywords)) * 100, 100)
    position_score = max(0, 100 - (data["avg_position"] * 10))  # Pos 1 = 90, Pos 10 = 0
    overlap_score = data["overlap_percentage"]
    
    data["threat_score"] = (
        appearances_score * 0.3 +
        position_score * 0.4 +
        overlap_score * 0.3
    )
    
    # Visibility Score (cât de vizibil e în SERP)
    data["visibility_score"] = sum([
        (11 - pos) * 10  # Pos 1 = 100, Pos 2 = 90, ..., Pos 10 = 10
        for pos in data["positions"]
    ]) / len(data["positions"])
```

#### **5.4. Salvare în MongoDB**

```json
// Colecția: competitor_discoveries
{
  "_id": ObjectId,
  "master_agent_id": "6915e1275eb1766cbe71fd4b",
  "discovered_at": "2025-11-13T18:00:00Z",
  "discovery_phase": "phase5_google_search",
  
  // Statistici generale
  "stats": {
    "total_keywords_searched": 30,
    "total_urls_found": 300,
    "unique_competitors": 47,
    "excluded_domains": 23,
    "master_appearances": 12  // câte ori masterul apare în SERP
  },
  
  // Poziții masterul
  "master_positions": [
    {
      "keyword": "protecție la foc București",
      "position": 3,
      "url": "https://protectiilafoc.ro/servicii",
      "title": "..."
    },
    // ... 11 more (masterul apare pe 12 din 30 keywords)
  ],
  
  // TOȚI competitorii descoperiți
  "competitors": [
    {
      "domain": "competitor1.ro",
      "appearances": 18,  // apare pe 18 din 30 keywords
      "keywords_ranked": ["keyword1", "keyword2", ...],
      "best_position": 1,
      "avg_position": 3.2,
      "keyword_overlap": 18,
      "overlap_percentage": 60.0,
      "threat_score": 78.5,
      "visibility_score": 82.3,
      
      // TOATE URL-urile descoperite pentru acest competitor
      "urls": [
        {
          "keyword": "protecție la foc structuri metalice",
          "position": 1,
          "url": "https://competitor1.ro/protectie-foc-structuri",
          "title": "Protecție la foc structuri metalice",
          "snippet": "Oferim servicii complete...",
          "discovered_at": "2025-11-13T18:00:15Z"
        },
        {
          "keyword": "termoprotecție vopsea intumescentă",
          "position": 2,
          "url": "https://competitor1.ro/vopsea-intumescenta",
          "title": "Vopsea intumescentă certificată",
          "snippet": "...",
          "discovered_at": "2025-11-13T18:00:18Z"
        }
        // ... 16 more URLs
      ]
    },
    {
      "domain": "competitor2.ro",
      "appearances": 15,
      "threat_score": 65.2,
      // ...
    }
    // ... 45 more competitors
  ]
}
```

**❓ ÎNTREBARE:** Codul actual salvează așa? **→ DE VERIFICAT!**

---

### **FAZA 6: Raport Competitiv CEO** ✅ EXISTĂ
**Status:** ✅ Codul există în `competitive_strategy.py`

**Ce se întâmplă:**

#### **6.1. Ranking competitori (Top 20 cel mai periculoși)**

```python
# Sortare după threat_score
top_competitors = sorted(
    competitors.values(), 
    key=lambda x: x["threat_score"], 
    reverse=True
)[:20]

# Output:
# 1. competitor1.ro - Threat: 78.5 - Appearances: 18/30 - Avg Pos: 3.2
# 2. competitor2.ro - Threat: 65.2 - Appearances: 15/30 - Avg Pos: 4.8
# ...
# 20. competitor20.ro - Threat: 42.1 - Appearances: 8/30 - Avg Pos: 7.3
```

#### **6.2. Analiza gap-urilor (keywords unde masterul lipsește)**

```python
keyword_gaps = []

for keyword in all_keywords:
    master_found = any(
        pos["keyword"] == keyword 
        for pos in master_positions
    )
    
    if not master_found:
        # Masterul NU apare pe acest keyword!
        # Cine apare?
        top_3_on_keyword = [
            comp for comp in competitors.values()
            if keyword in comp["keywords_ranked"]
        ]
        top_3_on_keyword.sort(key=lambda x: min([
            url["position"] for url in x["urls"] if url["keyword"] == keyword
        ]))[:3]
        
        keyword_gaps.append({
            "keyword": keyword,
            "master_missing": True,
            "opportunity_score": 85,  # High opportunity!
            "top_3_competitors": [
                {
                    "domain": comp["domain"],
                    "position": min([u["position"] for u in comp["urls"] if u["keyword"] == keyword])
                }
                for comp in top_3_on_keyword
            ]
        })
```

**Output gap analysis:**
```
Keywords unde masterul LIPSEȘTE (oportunități MARI):
1. "sisteme sprinklere antiincendiu" 
   → Top 3: competitor1.ro (Pos 1), competitor5.ro (Pos 2), competitor12.ro (Pos 3)
   → OPPORTUNITY SCORE: 85/100

2. "detectoare fum certificate"
   → Top 3: ...
   → OPPORTUNITY SCORE: 82/100

... (18 keywords unde masterul nu apare)
```

#### **6.3. Hartă vizuală competitivă** (NetworkX + Matplotlib)

```python
import networkx as nx
import matplotlib.pyplot as plt

G = nx.Graph()

# Nod central: Masterul
G.add_node("protectiilafoc.ro", 
    node_color='red', 
    node_size=2000,
    label="MASTER\nThreat: N/A"
)

# Top 20 competitori
for i, comp in enumerate(top_competitors[:20], 1):
    G.add_node(comp["domain"], 
        node_color='blue' if comp["threat_score"] > 70 else 'green',
        node_size=1000 + (comp["appearances"] * 20),
        label=f"{comp['domain']}\nThreat: {comp['threat_score']:.1f}"
    )
    
    # Conexiune = keyword overlap
    if comp["overlap_percentage"] > 30:
        G.add_edge("protectiilafoc.ro", comp["domain"],
            weight=comp["overlap_percentage"] / 100,
            label=f"{comp['overlap_percentage']:.0f}%"
        )

# Salvează PNG
plt.figure(figsize=(20, 15))
nx.draw_networkx(G, with_labels=True)
plt.savefig("/tmp/competitive_map_protectiilafoc.png")
```

#### **6.4. Raport CEO (Markdown + PDF)**

```markdown
# 📊 RAPORT COMPETITIVE INTELLIGENCE
**Agent Master:** protectiilafoc.ro
**Data:** 2025-11-13 18:00
**Keywords Analizate:** 30
**Competitori Descoperiți:** 47

---

## 🎯 EXECUTIVE SUMMARY
- **Poziție medie master în SERP:** 5.2 (pe 12 keywords)
- **Coverage:** 40% (masterul apare pe doar 12 din 30 keywords)
- **Top Threat:** competitor1.ro (Threat Score: 78.5)
- **Oportunități identificate:** 18 keywords cu potențial mare

---

## 🏆 TOP 20 COMPETITORI CEL MAI PERICULOȘI

| # | Competitor | Threat | Appearances | Avg Pos | Overlap |
|---|------------|--------|-------------|---------|---------|
| 1 | competitor1.ro | 78.5 | 18/30 (60%) | 3.2 | 60% |
| 2 | competitor2.ro | 65.2 | 15/30 (50%) | 4.8 | 50% |
| ... | ... | ... | ... | ... | ... |

---

## 🚨 KEYWORD GAP ANALYSIS (Oportunități MARI)

### Keywords unde masterul LIPSEȘTE complet:
1. **"sisteme sprinklere antiincendiu"** ⚠️ HIGH PRIORITY
   - Top 3: competitor1.ro (Pos 1), competitor5.ro (Pos 2)
   - Volume estimat: MARE
   - **ACȚIUNE:** Creează pagină dedicată + SEO optimization

2. **"detectoare fum certificate"** ⚠️ HIGH PRIORITY
   - Top 3: competitor3.ro (Pos 1), competitor7.ro (Pos 3)
   - **ACȚIUNE:** Adaugă secțiune detectoare

... (16 more keywords)

---

## 📈 POZIȚII MASTERUL ÎN SERP

### Keywords unde masterul APARE:
1. **"protecție la foc București"** - Poziția 3 ✅ BINE
2. **"ignifugare lemn"** - Poziția 7 ⚠️ ÎMBUNĂTĂȚIRE
3. **"termoprotecție"** - Poziția 9 ⚠️ ÎMBUNĂTĂȚIRE
... (9 more)

### Keywords unde masterul AR TREBUI să apară dar lipsește: 18

---

## 💡 RECOMANDĂRI CEO

### PRIORITATE ÎNALTĂ (1-3 luni):
1. ✅ **Creează conținut pentru cele 18 keywords lipsă**
   - SEO-optimized landing pages
   - Blog posts + case studies
   - Target: Intrare în Top 10 pentru 10+ keywords noi

2. ✅ **Îmbunătățește poziții pe keywords existente**
   - Target: Mută de pe poziția 7-9 pe poziția 3-5
   - Focus: "ignifugare lemn", "termoprotecție"

3. ✅ **Monitorizare SERP continuă**
   - Track zilnic poziții pentru toate cele 30 keywords
   - Alertă dacă competitor1.ro crește threat score

### PRIORITATE MEDIE (3-6 luni):
4. ✅ **Backlink strategy**
   - Competitor1.ro are 120+ backlinks
   - Masterul: doar 45 backlinks
   - Target: +50 backlinks de calitate

---

## 🎨 HARTĂ COMPETITIVĂ
![Competitive Map](competitive_map_protectiilafoc.png)

---

**Generat automat de DeepSeek Competitive Intelligence System**
```

**✅ Acest raport SE GENEREAZĂ deja!**

---

### **FAZA 7: Transformare Competitori → Slave Agents** ✅ FUNCȚIONEAZĂ
**Status:** ✅ Codul există și funcționează

**Ce se întâmplă:**

#### **7.1. Selecție competitori pentru transformare**

```python
# Doar TOP competitorii (threat score > 50 SAU top 50)
selected_competitors = [
    comp for comp in competitors.values()
    if comp["threat_score"] > 50
][:50]

# Dacă sunt mai puțin de 50, ia primii 50
if len(selected_competitors) < 50:
    all_sorted = sorted(competitors.values(), key=lambda x: x["threat_score"], reverse=True)
    selected_competitors = all_sorted[:50]

logger.info(f"📋 Selectați {len(selected_competitors)} competitori pentru transformare în slave agents")
```

#### **7.2. Creare slave agents (PARALEL GPU)**

```python
# Batch processing: 5 agents în paralel pe GPU-uri
BATCH_SIZE = 5

for i in range(0, len(selected_competitors), BATCH_SIZE):
    batch = selected_competitors[i:i+BATCH_SIZE]
    
    # Creează 5 agents simultan (pe 5 GPU-uri diferite)
    tasks = []
    for competitor in batch:
        task = create_slave_agent(
            domain=competitor["domain"],
            master_agent_id=master_agent_id,
            competitor_data=competitor  # Include threat_score, positions, etc.
        )
        tasks.append(task)
    
    # Wait for batch
    results = await asyncio.gather(*tasks)
    
    logger.info(f"✅ Batch {i//BATCH_SIZE + 1}/{len(selected_competitors)//BATCH_SIZE} completat")
```

#### **7.3. Pentru FIECARE slave agent:**

```python
async def create_slave_agent(domain, master_agent_id, competitor_data):
    """
    Transformă un competitor în slave agent
    """
    # 1. Scraping site competitor
    content = await scrape_site(f"https://{domain}")
    
    # 2. Chunking (500 tokens/chunk)
    chunks = chunk_content(content, chunk_size=500)
    
    # 3. Generare embeddings (GPU - Qwen)
    embeddings = await generate_embeddings_gpu(chunks, gpu_id=get_free_gpu())
    
    # 4. Salvare în Qdrant
    collection_name = f"slave_{domain.replace('.', '_')}"
    await qdrant.upsert(collection_name, embeddings)
    
    # 5. Salvare în MongoDB
    slave_doc = {
        "_id": ObjectId(),
        "domain": domain,
        "site_url": f"https://{domain}",
        "agent_type": "slave",
        "master_agent_id": ObjectId(master_agent_id),
        "status": "created",
        "created_at": datetime.now(),
        "chunks_indexed": len(chunks),
        
        # ❗ IMPORTANT: Date competitive din Faza 5
        "competitive_data": {
            "threat_score": competitor_data["threat_score"],
            "appearances": competitor_data["appearances"],
            "avg_position": competitor_data["avg_position"],
            "best_position": competitor_data["best_position"],
            "keyword_overlap": competitor_data["keyword_overlap"],
            "visibility_score": competitor_data["visibility_score"],
            "keywords_ranked": competitor_data["keywords_ranked"],
            
            # TOATE URL-urile descoperite în SERP
            "serp_urls": competitor_data["urls"]  # Array cu toate pozițiile
        },
        
        # Keywords (va fi populat în Faza 4 pentru slave, dacă rulăm analiza)
        "keywords": [],
        
        # Metadata
        "industry": "same_as_master",
        "qdrant_collection": collection_name
    }
    
    db.site_agents.insert_one(slave_doc)
    
    logger.info(f"✅ Slave agent creat: {domain} (Threat: {competitor_data['threat_score']:.1f})")
    
    return {
        "success": True,
        "agent_id": str(slave_doc["_id"]),
        "domain": domain,
        "chunks": len(chunks)
    }
```

**✅ Acest proces FUNCȚIONEAZĂ deja!**

---

### **FAZA 8: Învățare Master-Slave + Raport Final DeepSeek** ✅ PARȚIAL
**Status:** ✅ Există, dar **DE ÎMBUNĂTĂȚIT cu DeepSeek**

**Ce TREBUIE să se întâmplă:**

#### **8.1. Masterul învață de la slave-uri**

```python
# Pentru FIECARE slave agent (50 competitori):
for slave in slave_agents:
    # Extrage insights din slave
    slave_insights = await extract_competitive_insights(slave_id)
    
    # Compară cu masterul
    comparison = await compare_master_vs_slave(master_id, slave_id)
    
    # Identifică best practices
    best_practices.append(comparison["advantages_slave"])
```

#### **8.2. DeepSeek analizează ȘI generează raport final**

```python
# 🎯 AICI vine DeepSeek!
prompt = f"""
Ești un expert în competitive intelligence. Analizează datele despre masterul și cei 50 competitori.

**MASTER AGENT:**
- Domain: protectiilafoc.ro
- Keywords: 30
- Poziții SERP: 12 keywords (avg pos 5.2)
- Chunks indexed: 470

**TOP 5 COMPETITORI (SLAVE AGENTS):**
1. competitor1.ro - Threat: 78.5 - Apare pe 18/30 keywords - Avg Pos: 3.2
2. competitor2.ro - Threat: 65.2 - Apare pe 15/30 keywords - Avg Pos: 4.8
... (48 more)

**KEYWORD GAP ANALYSIS:**
- Masterul lipsește pe 18 keywords
- Oportunități identificate: {list(keyword_gaps)}

**CONȚINUT ANALIZAT:**
- Master: {master_content_summary}
- Top 3 Slaves: {slave_content_summaries}

**TASK:**
Generează un raport CEO cu:
1. **Executive Summary** (2-3 propoziții)
2. **Poziția actuală în piață** (quote: "Masterul ocupă poziția X din Y competitori")
3. **Threat-uri principale** (top 3 competitori + de ce sunt periculoși)
4. **Oportunități** (top 5 keywords + de ce sunt importante)
5. **Acțiuni recomandate** (5-7 acțiuni concrete, prioritizate)
6. **Predicții** (ce se va întâmpla în 3-6 luni dacă NU acționăm)

Returnează JSON.
"""

deepseek_report = llm.chat(messages=[
    {"role": "system", "content": "Ești un consultant strategic senior."},
    {"role": "user", "content": prompt}
], max_tokens=4000)
```

**Output DeepSeek:**
```json
{
  "executive_summary": "Protectiilafoc.ro se află pe locul 8 din 47 competitori, cu o acoperire de doar 40% din keywords-urile cheie. Principalul threat este competitor1.ro (78.5 threat score), care domină 60% din keywords-uri cu poziții medii de 3.2. Există 18 oportunități mari de a crește vizibilitatea prin conținut țintit.",
  
  "market_position": {
    "rank": 8,
    "out_of": 47,
    "coverage": "40%",
    "avg_position": 5.2,
    "assessment": "MEDIU - Potențial de îmbunătățire mare"
  },
  
  "top_threats": [
    {
      "competitor": "competitor1.ro",
      "threat_score": 78.5,
      "why_dangerous": "Domină 60% din keywords, poziții excelente (avg 3.2), conținut bogat și optimizat SEO",
      "recommendation": "Monitorizare zilnică, studiu conținut lor pentru best practices"
    },
    // ... 2 more
  ],
  
  "top_opportunities": [
    {
      "keyword": "sisteme sprinklere antiincendiu",
      "priority": "FOARTE MARE",
      "why_important": "Volume mare, master lipsește complet, competiția nu e dominantă (top 3 au scoruri apropiate)",
      "estimated_traffic": "500-800 vizitatori/lună",
      "action": "Creează landing page dedicată + 3 blog posts + case study"
    },
    // ... 4 more
  ],
  
  "recommended_actions": [
    {
      "priority": 1,
      "action": "Creează 18 pagini noi pentru keywords lipsă",
      "effort": "MARE",
      "impact": "FOARTE MARE",
      "timeline": "1-2 luni",
      "estimated_results": "+40% traffic în 3 luni"
    },
    // ... 6 more
  ],
  
  "predictions": {
    "if_no_action": "În 3-6 luni, competitor1.ro va consolida poziția dominantă, masterul va rămâne pe locul 8-10, pierdere potențială de 30-40% din clienți noi față de competitori",
    "if_action_taken": "Cu implementarea recomandărilor, masterul poate urca pe locul 3-5 în 6 luni, +60-80% traffic organic, +30-50% conversii"
  }
}
```

**❓ ÎNTREBARE:** Raportul DeepSeek se generează? **→ DE VERIFICAT!**

---

### **FAZA 9: MONITORIZARE CONTINUĂ SERP + GRAFICE** ⚠️ LIPSEȘTE PARȚIAL!
**Status:** ⚠️ Codul există (`temporal_tracking/serp_timeline_tracker.py`) dar **NU e integrat în workflow**

**Ce TREBUIE să se întâmplă:**

#### **9.1. Tracking zilnic poziții SERP**

```python
# Rulează ZILNIC (cron job sau scheduler)
async def daily_serp_tracking(master_agent_id):
    """
    Tracking zilnic pentru TOATE keywords-urile
    """
    # Obține keywords master
    agent = db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
    keywords = agent["keywords"]  # 30 keywords
    
    # Pentru FIECARE keyword:
    for keyword in keywords:
        # Search Google (sau Brave)
        results = await google_search(keyword, count=20)  # Top 20
        
        # Găsește poziția masterului
        master_position = None
        master_url = None
        for i, result in enumerate(results, 1):
            if agent["domain"] in result["url"]:
                master_position = i
                master_url = result["url"]
                break
        
        # Găsește pozițiile competitorilor
        competitor_positions = []
        for i, result in enumerate(results, 1):
            domain = extract_domain(result["url"])
            
            # E competitor cunoscut?
            slave = db.site_agents.find_one({
                "master_agent_id": ObjectId(master_agent_id),
                "agent_type": "slave",
                "domain": domain
            })
            
            if slave:
                competitor_positions.append({
                    "domain": domain,
                    "slave_agent_id": str(slave["_id"]),
                    "position": i,
                    "url": result["url"],
                    "title": result["title"]
                })
        
        # Salvează snapshot zilnic
        snapshot = {
            "master_agent_id": ObjectId(master_agent_id),
            "keyword": keyword,
            "date": datetime.now().date(),
            "timestamp": datetime.now(),
            
            # Poziția masterului
            "master_position": master_position,
            "master_url": master_url,
            "master_in_top_10": master_position is not None and master_position <= 10,
            "master_in_top_20": master_position is not None and master_position <= 20,
            
            # Competitori în Top 20
            "competitors_in_top_20": competitor_positions,
            "competitors_count": len(competitor_positions),
            
            # Top 3 (pentru quick view)
            "top_3": [
                {
                    "position": i+1,
                    "domain": extract_domain(results[i]["url"]),
                    "url": results[i]["url"],
                    "is_competitor": any(c["position"] == i+1 for c in competitor_positions)
                }
                for i in range(min(3, len(results)))
            ]
        }
        
        # Salvează în MongoDB
        db.serp_tracking.insert_one(snapshot)
        
        logger.info(f"✅ Tracked: {keyword} - Master pos: {master_position or 'N/A'}")
    
    # Calcul metrici zilnice
    daily_summary = {
        "master_agent_id": ObjectId(master_agent_id),
        "date": datetime.now().date(),
        "total_keywords": len(keywords),
        "master_in_top_10": sum(1 for kw in ... if pos <= 10),
        "master_in_top_20": sum(1 for kw in ... if pos <= 20),
        "master_missing": sum(1 for kw in ... if pos is None),
        "avg_position": ...,
        "visibility_score": ...
    }
    
    db.serp_daily_summary.insert_one(daily_summary)
```

#### **9.2. Detectare schimbări importante**

```python
# După fiecare tracking, compară cu ziua anterioară
def detect_significant_changes(master_agent_id, today_snapshots):
    """
    Detectează schimbări semnificative și trimite alerte
    """
    yesterday = datetime.now().date() - timedelta(days=1)
    
    changes = []
    
    for today in today_snapshots:
        keyword = today["keyword"]
        
        # Găsește snapshot-ul de ieri
        yesterday_snap = db.serp_tracking.find_one({
            "master_agent_id": master_agent_id,
            "keyword": keyword,
            "date": yesterday
        })
        
        if not yesterday_snap:
            continue
        
        # Compară poziții
        pos_today = today["master_position"]
        pos_yesterday = yesterday_snap["master_position"]
        
        # Schimbare semnificativă?
        if pos_today and pos_yesterday:
            diff = pos_yesterday - pos_today
            
            if abs(diff) >= 3:  # Mișcare de 3+ poziții
                changes.append({
                    "type": "position_change",
                    "keyword": keyword,
                    "from": pos_yesterday,
                    "to": pos_today,
                    "change": diff,
                    "direction": "up" if diff > 0 else "down",
                    "severity": "high" if abs(diff) >= 5 else "medium"
                })
        
        # Apărut în Top 10?
        if pos_today and pos_today <= 10 and (not pos_yesterday or pos_yesterday > 10):
            changes.append({
                "type": "entered_top_10",
                "keyword": keyword,
                "position": pos_today,
                "severity": "positive"
            })
        
        # Dispărut din Top 10?
        if pos_yesterday and pos_yesterday <= 10 and (not pos_today or pos_today > 10):
            changes.append({
                "type": "dropped_from_top_10",
                "keyword": keyword,
                "severity": "critical"
            })
        
        # Competitor nou în Top 3?
        today_top3_domains = [t["domain"] for t in today["top_3"]]
        yesterday_top3_domains = [t["domain"] for t in yesterday_snap["top_3"]]
        
        new_competitors_top3 = set(today_top3_domains) - set(yesterday_top3_domains)
        if new_competitors_top3:
            for domain in new_competitors_top3:
                changes.append({
                    "type": "new_competitor_top3",
                    "keyword": keyword,
                    "competitor": domain,
                    "severity": "warning"
                })
    
    # Salvează alertele
    if changes:
        alert_doc = {
            "master_agent_id": ObjectId(master_agent_id),
            "date": datetime.now().date(),
            "changes_count": len(changes),
            "changes": changes,
            "severity": "critical" if any(c["severity"] == "critical" for c in changes) else "medium"
        }
        db.serp_alerts.insert_one(alert_doc)
        
        # Trimite notificare (email, Slack, etc.)
        send_alert_notification(alert_doc)
    
    return changes
```

#### **9.3. Generare grafice (Dashboard)**

```python
# Pentru dashboard: generează grafice cu istoric SERP
def generate_serp_evolution_chart(master_agent_id, keyword, days=30):
    """
    Grafic cu evoluția poziției pentru un keyword în ultimele X zile
    """
    snapshots = db.serp_tracking.find({
        "master_agent_id": ObjectId(master_agent_id),
        "keyword": keyword,
        "date": {"$gte": datetime.now().date() - timedelta(days=days)}
    }).sort("date", 1)
    
    dates = []
    master_positions = []
    competitor1_positions = []  # Top threat
    competitor2_positions = []
    
    for snap in snapshots:
        dates.append(snap["date"])
        master_positions.append(snap["master_position"] or 21)  # 21 = not in top 20
        
        # Găsește top 2 competitori
        comps = sorted(snap["competitors_in_top_20"], key=lambda x: x["position"])
        if len(comps) >= 1:
            competitor1_positions.append(comps[0]["position"])
        else:
            competitor1_positions.append(21)
        
        if len(comps) >= 2:
            competitor2_positions.append(comps[1]["position"])
        else:
            competitor2_positions.append(21)
    
    # Chart.js sau Matplotlib
    chart_data = {
        "labels": [d.strftime("%d %b") for d in dates],
        "datasets": [
            {
                "label": "Master (protectiilafoc.ro)",
                "data": master_positions,
                "borderColor": "rgb(255, 99, 132)",
                "backgroundColor": "rgba(255, 99, 132, 0.2)",
            },
            {
                "label": "Competitor #1 (competitor1.ro)",
                "data": competitor1_positions,
                "borderColor": "rgb(54, 162, 235)",
                "backgroundColor": "rgba(54, 162, 235, 0.2)",
            },
            {
                "label": "Competitor #2 (competitor2.ro)",
                "data": competitor2_positions,
                "borderColor": "rgb(75, 192, 192)",
                "backgroundColor": "rgba(75, 192, 192, 0.2)",
            }
        ]
    }
    
    return chart_data
```

**Chart.js example (pentru React dashboard):**
```jsx
import { Line } from 'react-chartjs-2';

function SERPEvolutionChart({ agentId, keyword }) {
  const { data, isLoading } = useQuery({
    queryKey: ['serp-evolution', agentId, keyword],
    queryFn: async () => {
      const res = await api.get(`/api/serp/evolution/${agentId}/${keyword}`);
      return res.data;
    }
  });
  
  if (isLoading) return <Loader />;
  
  return (
    <div className="card">
      <h3>Evoluție SERP: "{keyword}"</h3>
      <Line 
        data={data} 
        options={{
          scales: {
            y: {
              reverse: true,  // Poziția 1 = top
              min: 1,
              max: 20,
              title: { text: 'Poziție în Google' }
            }
          }
        }}
      />
    </div>
  );
}
```

#### **9.4. Dashboard cu toate graficele**

```jsx
// Dashboard SERP Monitoring
function SERPMonitoringDashboard({ agentId }) {
  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard 
          title="Keywords în Top 10" 
          value="12/30" 
          change="+2 față de săptămâna trecută"
          trend="up"
        />
        <StatCard 
          title="Avg Position" 
          value="5.2" 
          change="-0.8 (îmbunătățire)"
          trend="up"
        />
        <StatCard 
          title="Visibility Score" 
          value="68/100" 
          change="+5"
          trend="up"
        />
        <StatCard 
          title="Alerte Active" 
          value="3" 
          change="2 critice"
          trend="warning"
        />
      </div>
      
      {/* Grafic general: evoluție ultim 30 zile */}
      <div className="card">
        <h2>Evoluție Generală (30 zile)</h2>
        <SERPGeneralEvolutionChart agentId={agentId} />
      </div>
      
      {/* Grafice individuale per keyword */}
      <div className="card">
        <h2>Evoluție per Keyword</h2>
        <div className="grid grid-cols-2 gap-4">
          {keywords.map(kw => (
            <SERPEvolutionChart key={kw} agentId={agentId} keyword={kw} />
          ))}
        </div>
      </div>
      
      {/* Alerte recente */}
      <div className="card">
        <h2>Alerte Recente</h2>
        <AlertsList agentId={agentId} />
      </div>
      
      {/* Competitor movements */}
      <div className="card">
        <h2>Mișcări Competitori (Top 5)</h2>
        <CompetitorMovementsList agentId={agentId} />
      </div>
    </div>
  );
}
```

---

## 🔧 CE LIPSEȘTE / TREBUIE IMPLEMENTAT

### ✅ FUNCȚIONEAZĂ DEJA:
1. Generare keywords (✅ fixat)
2. Google Search pentru keywords (✅ există)
3. Deduplicare competitori (✅ există)
4. Calcul scoruri competitive (✅ există)
5. Creare slave agents (✅ există)
6. Raport CEO basic (✅ există)

### ⚠️ TREBUIE VERIFICAT:
1. **Google Search salvează TOATE poziții?**
   - Verifică dacă colecția `competitor_discoveries` conține toate URL-urile
   - Verifică dacă fiecare competitor are array `urls` cu TOATE pozițiile

2. **DeepSeek generează raportul final?**
   - Verifică dacă se apelează DeepSeek pentru analiza finală
   - Verifică dacă există raport în `competitive_reports` collection

### ❌ LIPSEȘTE (TREBUIE IMPLEMENTAT):
1. **Monitorizare SERP continuă**
   - Scheduler pentru tracking zilnic
   - Salvare snapshots zilnice în `serp_tracking` collection
   - Detectare schimbări + alerte

2. **Grafice evoluție SERP**
   - API endpoints pentru date grafice
   - Componente React pentru Chart.js
   - Dashboard dedicat SERP monitoring

3. **Integrare completă în workflow**
   - După Faza 8: pornește scheduler-ul de monitoring
   - Webhook/notificări pentru alerte

---

## 📊 SCHEMA COMPLETĂ BAZE DE DATE

```javascript
// MongoDB Collections:

// 1. site_agents (agenți master + slave)
{
  _id: ObjectId,
  domain: "protectiilafoc.ro",
  agent_type: "master|slave",
  keywords: [...],  // ✅ Fixat!
  competitive_data: {...}  // Pentru slaves
}

// 2. competitor_discoveries (rezultate Google Search)
{
  _id: ObjectId,
  master_agent_id: ObjectId,
  discovered_at: Date,
  competitors: [
    {
      domain: "competitor1.ro",
      threat_score: 78.5,
      urls: [  // ❓ VERIFICĂ dacă există!
        {keyword: "...", position: 1, url: "..."},
        // ... toate pozițiile
      ]
    }
  ]
}

// 3. serp_tracking (snapshots zilnice) ❌ LIPSEȘTE!
{
  _id: ObjectId,
  master_agent_id: ObjectId,
  keyword: "protecție la foc București",
  date: "2025-11-13",
  timestamp: DateTime,
  master_position: 3,
  master_url: "...",
  competitors_in_top_20: [...]
}

// 4. serp_daily_summary ❌ LIPSEȘTE!
{
  _id: ObjectId,
  master_agent_id: ObjectId,
  date: "2025-11-13",
  total_keywords: 30,
  master_in_top_10: 12,
  avg_position: 5.2,
  visibility_score: 68
}

// 5. serp_alerts ❌ LIPSEȘTE!
{
  _id: ObjectId,
  master_agent_id: ObjectId,
  date: "2025-11-13",
  changes: [
    {type: "dropped_from_top_10", keyword: "...", severity: "critical"},
    // ...
  ]
}

// 6. competitive_reports (rapoarte CEO)
{
  _id: ObjectId,
  master_agent_id: ObjectId,
  report_type: "ceo_competitive_intelligence",
  generated_at: Date,
  executive_summary: "...",
  top_threats: [...],
  opportunities: [...],
  recommendations: [...]
}
```

---

## 🚀 NEXT STEPS (Prioritizate)

### PRIORITATE 1: VERIFICARE
1. ✅ Rulează workflow complet pentru un agent
2. ✅ Verifică MongoDB: există `urls` array pentru fiecare competitor?
3. ✅ Verifică dacă DeepSeek generează raport final

### PRIORITATE 2: IMPLEMENTARE MONITORING
1. ❌ Implementează `daily_serp_tracking()`
2. ❌ Implementează `detect_significant_changes()`
3. ❌ Crează scheduler (cron sau APScheduler)
4. ❌ Testează tracking pentru 1 agent

### PRIORITATE 3: DASHBOARD GRAFICE
1. ❌ API endpoints pentru date SERP
2. ❌ Componente React cu Chart.js
3. ❌ Integrare în dashboard principal

---

**Vrei să verific acum dacă Google Search salvează toate pozițiile corect?**

