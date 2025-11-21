# 🗺️ STRATEGIE: Google Rankings Interactive Map + Slave Agents

**Data:** 2025-11-16  
**Obiectiv:** Sistem complet de monitorizare poziții Google + creare agenți slave + hartă interactivă

---

## 🎯 OBIECTIV PRINCIPAL

Crearea unui sistem automat care:

1. ✅ **Ia toate keywords-urile** de la un agent master (din subdomenii)
2. ✅ **Pentru FIECARE keyword** → Face Google Search → Extrage TOP 20 rezultate
3. ✅ **Creează agenți SLAVE** pentru fiecare competitor găsit (auto-scraping)
4. ✅ **Identifică poziția EXACTĂ** a site-ului master în Google pentru fiecare keyword
5. ✅ **Generează hartă interactivă** cu poziții, competitori, gap-uri
6. ✅ **Analiza DeepSeek** → Strategii Google Ads personalizate

---

## 📊 ARHITECTURĂ SISTEM

```
┌─────────────────────────────────────────────────────────────────┐
│                         MASTER AGENT                            │
│                      (crumantech.ro)                            │
│                                                                 │
│  Subdomenii: 3                                                  │
│  Keywords: 25 (5 per subdomain + 10 generale)                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              WORKFLOW: SERP DISCOVERY + SLAVE CREATION          │
│                                                                 │
│  Pentru fiecare keyword (25):                                   │
│    1. Google Search API / Scraping                              │
│    2. Extract TOP 20 rezultate (URL, title, position)           │
│    3. Pentru fiecare rezultat:                                  │
│       a. Check if agent exists (domain deduplication)           │
│       b. Create SLAVE agent (auto-scraping + embeddings)        │
│       c. Link slave → master (relationship)                     │
│    4. Store ranking data (master position per keyword)          │
│                                                                 │
│  Total: 25 keywords × 20 results = ~500 potential slaves        │
│  (după deduplication: ~100-150 unique domains)                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MONGODB COLLECTIONS                          │
│                                                                 │
│  1. site_agents (master + slaves)                               │
│  2. google_rankings:                                            │
│     {                                                           │
│       agent_id: "master_id",                                    │
│       keyword: "reparatii anticorozive",                        │
│       master_position: 12,  # poziția master-ului               │
│       serp_results: [                                           │
│         {                                                       │
│           position: 1,                                          │
│           url: "competitor1.ro",                                │
│           title: "...",                                         │
│           slave_agent_id: "slave_1"                             │
│         },                                                      │
│         ... top 20                                              │
│       ],                                                        │
│       checked_at: "2025-11-16"                                  │
│     }                                                           │
│  3. competitive_strategies:                                     │
│     {                                                           │
│       agent_id: "master_id",                                    │
│       keyword: "...",                                           │
│       master_position: 12,                                      │
│       gap_analysis: {                                           │
│         positions_above: [1-11],                                │
│         direct_competitors: [...],                              │
│         opportunity_keywords: [...]                             │
│       },                                                        │
│       google_ads_strategy: {                                    │
│         bid_recommendations: {...},                             │
│         target_keywords: [...],                                 │
│         budget_allocation: {...}                                │
│       }                                                         │
│     }                                                           │
└─────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                 DEEPSEEK ORCHESTRATION                          │
│                                                                 │
│  1. Analiză completă rankings                                   │
│  2. Identificare gap-uri (keywords unde lipsim din top 10)      │
│  3. Analiza competitorilor pe fiecare poziție                   │
│  4. Generare strategii Google Ads:                              │
│     - Keywords cu potential ridicat (pozitii 11-20)             │
│     - Bid recommendations (CPC estimat)                         │
│     - Budget allocation per keyword/subdomain                   │
│     - Competitor analysis (cine domină)                         │
│  5. Recomandări SEO (pentru organic improvement)                │
└─────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│            FRONTEND: INTERACTIVE RANKINGS MAP                   │
│                                                                 │
│  Component: GoogleRankingsMap.jsx                               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Keyword: "reparatii anticorozive"                      │   │
│  │                                                         │   │
│  │  [1] competitor1.ro          [11] competitor11.ro      │   │
│  │  [2] competitor2.ro          [12] 🎯 crumantech.ro ←  │   │
│  │  [3] competitor3.ro          [13] competitor13.ro      │   │
│  │  [4] competitor4.ro          [14] competitor14.ro      │   │
│  │  [5] competitor5.ro          [15] competitor15.ro      │   │
│  │  [6] competitor6.ro          [16] competitor16.ro      │   │
│  │  [7] competitor7.ro          [17] competitor17.ro      │   │
│  │  [8] competitor8.ro          [18] competitor18.ro      │   │
│  │  [9] competitor9.ro          [19] competitor19.ro      │   │
│  │  [10] competitor10.ro        [20] competitor20.ro      │   │
│  │                                                         │   │
│  │  📊 Gap Analysis:                                       │   │
│  │    • Missing from Top 10 (need 11 positions up)        │   │
│  │    • Opportunity: High (searchable keyword)            │   │
│  │    • Competition: Medium (3/10 direct competitors)     │   │
│  │                                                         │   │
│  │  💡 Google Ads Strategy:                               │   │
│  │    • Recommended Bid: $2.50 - $4.00 CPC               │   │
│  │    • Target Position: 3-5 (ads)                        │   │
│  │    • Monthly Budget: $500 - $800                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Features:                                                      │
│    • Grid vizual pentru toate keywords                          │
│    • Color coding (Top 3 = green, 4-10 = yellow, 11+ = red)    │
│    • Click pe competitor → Vezi agent slave details             │
│    • Filter by subdomain                                        │
│    • Sort by: position, opportunity, competition                │
│    • Export to CSV/PDF                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ IMPLEMENTARE BACKEND

### **1. Google SERP Scraper** (`google_serp_scraper.py`)

```python
class GoogleSerpScraper:
    def search_keyword(self, keyword: str, num_results: int = 20):
        """
        Caută pe Google și returnează TOP 20 rezultate
        Folosește: Brave Search API sau SerpAPI sau custom scraping
        """
        return [
            {
                'position': 1,
                'url': 'https://competitor1.ro',
                'title': '...',
                'snippet': '...',
                'domain': 'competitor1.ro'
            },
            ...
        ]
    
    def find_master_position(self, results: List, master_domain: str):
        """Găsește poziția exactă a master-ului în rezultate"""
        for result in results:
            if master_domain in result['url']:
                return result['position']
        return None  # Nu e în top 20
```

### **2. Slave Agent Creator** (`slave_agent_creator.py`)

```python
class SlaveAgentCreator:
    def create_from_serp_result(self, serp_result: Dict, master_id: str):
        """
        Creează agent slave din rezultat SERP
        - Scraping site
        - DeepSeek analysis
        - GPU embeddings
        - Link to master
        """
        domain = serp_result['domain']
        url = serp_result['url']
        
        # Check dacă există deja
        existing = db.site_agents.find_one({'domain': domain})
        if existing:
            return existing['_id']
        
        # Scrape + Create
        agent_id = self.create_agent_full_pipeline(
            url=url,
            domain=domain,
            type='slave',
            master_id=master_id
        )
        
        return agent_id
```

### **3. Workflow Orchestrator** (update `workflow_manager.py`)

```python
async def run_serp_discovery_with_slaves(agent_id: str, num_keywords: int = None):
    """
    Workflow complet:
    1. Get keywords from master
    2. For each keyword: Google search
    3. Create slaves for each result
    4. Store rankings
    5. DeepSeek analysis → Strategy
    """
    
    # Step 1: Get keywords
    agent = db.site_agents.find_one({'_id': agent_id})
    comp_analysis = db.competitive_analysis.find_one({'agent_id': agent_id})
    
    keywords = []
    # Extract from subdomains
    for subdomain in comp_analysis.get('subdomains', []):
        keywords.extend(subdomain.get('keywords', []))
    # Add general keywords
    keywords.extend(comp_analysis.get('keywords', []))
    
    if num_keywords:
        keywords = keywords[:num_keywords]
    
    total_keywords = len(keywords)
    logger.info(f"Processing {total_keywords} keywords for agent {agent_id}")
    
    for i, keyword in enumerate(keywords):
        update_workflow_progress(
            workflow_id,
            progress=(i / total_keywords) * 80,
            current_step=f"Processing keyword {i+1}/{total_keywords}: {keyword}"
        )
        
        # Step 2: Google Search
        serp_results = google_scraper.search_keyword(keyword, num_results=20)
        
        # Find master position
        master_position = google_scraper.find_master_position(
            serp_results, 
            agent['domain']
        )
        
        # Step 3: Create slaves
        slave_ids = []
        for result in serp_results:
            slave_id = slave_creator.create_from_serp_result(
                result, 
                master_id=agent_id
            )
            slave_ids.append(slave_id)
        
        # Step 4: Store rankings
        db.google_rankings.insert_one({
            'agent_id': agent_id,
            'keyword': keyword,
            'master_position': master_position,
            'serp_results': serp_results,
            'slave_ids': slave_ids,
            'checked_at': datetime.now()
        })
    
    # Step 5: DeepSeek Strategy Analysis
    update_workflow_progress(
        workflow_id,
        progress=90,
        current_step="Generating Google Ads strategies with DeepSeek..."
    )
    
    strategy = await generate_google_ads_strategy(agent_id)
    
    db.competitive_strategies.insert_one(strategy)
    
    return {
        'keywords_processed': total_keywords,
        'slaves_created': len(slave_ids),
        'rankings_stored': total_keywords
    }
```

### **4. API Endpoints** (add to `agent_api.py`)

```python
@app.get("/api/agents/{agent_id}/google-rankings-map")
async def get_google_rankings_map(agent_id: str):
    """
    Returnează harta completă de rankings pentru vizualizare
    """
    rankings = list(db.google_rankings.find({'agent_id': agent_id}))
    
    map_data = []
    for ranking in rankings:
        map_data.append({
            'keyword': ranking['keyword'],
            'master_position': ranking['master_position'],
            'serp_results': ranking['serp_results'],
            'checked_at': ranking['checked_at']
        })
    
    return {
        'agent_id': agent_id,
        'total_keywords': len(map_data),
        'rankings': map_data
    }

@app.get("/api/agents/{agent_id}/google-ads-strategy")
async def get_google_ads_strategy(agent_id: str):
    """
    Returnează strategia Google Ads generată de DeepSeek
    """
    strategy = db.competitive_strategies.find_one(
        {'agent_id': agent_id},
        sort=[('created_at', -1)]
    )
    
    if not strategy:
        return {
            'exists': False,
            'message': 'No strategy generated yet'
        }
    
    return {
        'exists': True,
        'strategy': strategy
    }

@app.post("/api/workflows/start-serp-discovery-with-slaves")
async def start_serp_discovery_with_slaves(
    agent_id: str,
    num_keywords: int = None
):
    """
    Pornește workflow-ul complet:
    - SERP discovery
    - Slave creation
    - Rankings analysis
    - Strategy generation
    """
    workflow_id = str(ObjectId())
    
    # Start background task
    background_tasks.add_task(
        run_serp_discovery_with_slaves,
        agent_id=agent_id,
        workflow_id=workflow_id,
        num_keywords=num_keywords
    )
    
    return {
        'workflow_id': workflow_id,
        'status': 'started',
        'message': f'SERP discovery with slaves started for {num_keywords or "all"} keywords'
    }
```

---

## 🎨 IMPLEMENTARE FRONTEND

### **Component: GoogleRankingsMap.jsx**

```jsx
import { useState, useEffect } from 'react'
import { Search, TrendingUp, Target, AlertCircle, CheckCircle } from 'lucide-react'
import { getGoogleRankingsMap, getGoogleAdsStrategy } from '../services/workflows'

const GoogleRankingsMap = ({ agentId }) => {
  const [rankings, setRankings] = useState([])
  const [strategy, setStrategy] = useState(null)
  const [selectedKeyword, setSelectedKeyword] = useState(null)
  const [loading, setLoading] = useState(true)
  
  // ... fetch data, render grid, show strategy
  
  return (
    <div className="space-y-6">
      {/* Keywords Grid */}
      {/* Master Position Highlights */}
      {/* Gap Analysis */}
      {/* Google Ads Strategy */}
    </div>
  )
}
```

---

## 🧪 TEST AGENT UPDATE

```python
# Add to test_agent.py

def test_google_rankings_map_endpoints(self):
    """Test Google Rankings Map functionality"""
    
    # 1. Start SERP discovery with slaves
    self.test_endpoint(
        'POST',
        '/api/workflows/start-serp-discovery-with-slaves',
        'Start SERP Discovery + Slave Creation',
        data={'agent_id': self.agent_id, 'num_keywords': 5},
        expected_keys=['workflow_id', 'status']
    )
    
    # 2. Get rankings map
    self.test_endpoint(
        'GET',
        f'/api/agents/{self.agent_id}/google-rankings-map',
        'Get Google Rankings Map',
        expected_keys=['rankings', 'total_keywords']
    )
    
    # 3. Get Google Ads strategy
    self.test_endpoint(
        'GET',
        f'/api/agents/{self.agent_id}/google-ads-strategy',
        'Get Google Ads Strategy',
        expected_keys=['exists', 'strategy']
    )
```

---

## 📅 PLAN DE IMPLEMENTARE

### **FAZA 1: Backend Core** (2-3 ore)
1. ✅ Google SERP Scraper (Brave API integration)
2. ✅ Slave Agent Creator (auto-scraping pipeline)
3. ✅ Workflow Orchestrator (serp_discovery_with_slaves)
4. ✅ MongoDB collections (google_rankings, competitive_strategies)
5. ✅ API Endpoints (rankings-map, ads-strategy)

### **FAZA 2: DeepSeek Integration** (1-2 ore)
1. ✅ Prompt engineering pentru Google Ads strategy
2. ✅ Gap analysis automation
3. ✅ Bid recommendations algorithm

### **FAZA 3: Frontend** (2-3 ore)
1. ✅ GoogleRankingsMap.jsx component
2. ✅ Interactive grid visualization
3. ✅ Strategy recommendations panel
4. ✅ Export functionality

### **FAZA 4: Testing** (1 ora)
1. ✅ Update test_agent.py
2. ✅ Comprehensive testing
3. ✅ Performance optimization

---

## 🎯 EXPECTED RESULTS

### **Pentru 1 Master Agent (25 keywords):**
- ~500 SERP results (25 × 20)
- ~100-150 unique slave agents (după deduplication)
- 25 ranking entries (1 per keyword)
- 1 comprehensive Google Ads strategy
- Interactive map cu toată informația

### **Benefits:**
- ✅ Vizibilitate completă în Google Search
- ✅ Identificare automată competitori (slaves)
- ✅ Strategii data-driven pentru Google Ads
- ✅ ROI optimization (know exact where to invest)
- ✅ Competitive intelligence la nivel de keyword

---

**Status:** Ready for Implementation  
**Priority:** HIGH  
**Complexity:** HIGH (4-5 ore implementare + testing)

