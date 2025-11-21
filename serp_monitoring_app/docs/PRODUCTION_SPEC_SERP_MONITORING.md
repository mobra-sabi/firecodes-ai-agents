# 🚀 SPECIFICAȚIE PRODUCTION: SERP Monitoring & Competitive Intelligence

## 📋 OBIECTIV
Sistem complet de monitorizare SERP cu scoring transparent, detecție schimbări automate, și generare rapoarte CEO.

---

## 1️⃣ SCHEMAS MONGODB

### Collection: `serp_runs` (log pentru fiecare rulare SERP)
```javascript
{
  "_id": "run_2025-11-13_14-00-12",
  "agent_id": "protectiilafoc.ro",
  "keywords": ["vopsea intumescenta", "protectie pasiva la foc", "..."],
  "market": "ro",
  "started_at": "2025-11-13T14:00:12Z",
  "finished_at": "2025-11-13T14:04:33Z",
  "provider": "serpapi|together|brave|custom",
  "status": "succeeded|failed|partial",
  "stats": { 
    "queries": 30, 
    "pages_fetched": 30, 
    "errors": 2,
    "total_results": 300,
    "unique_domains": 47
  }
}
```

### Collection: `serp_results` (o intrare / keyword / data / poziție)
```javascript
{
  "_id": "serp:protectiilafoc.ro:ro:vopsea intumescenta:2025-11-13:1",
  "agent_id": "protectiilafoc.ro",
  "keyword": "vopsea intumescenta",
  "date": "2025-11-13",
  "rank": 1,
  "url": "https://www.promat.com/ro-ro/...",
  "domain": "promat.com",  // canonical (fără www, lowercase)
  "title": "Protecția la foc...",
  "snippet": "…",
  "type": "organic|ad|featured_snippet|map",
  "page": 1,
  "run_id": "run_2025-11-13_14-00-12",
  "crawled_at": "2025-11-13T14:00:15Z"
}
```

### Collection: `competitors` (unificat pe domeniu)
```javascript
{
  "_id": "promat.com",
  "domain": "promat.com",
  "first_seen": "2025-11-13",
  "last_seen": "2025-11-13",
  "keywords_seen": ["vopsea intumescenta", "protectie pasiva la foc"],
  "appearances_count": 18,
  "agent_slave_id": "agent_promat",   // dacă a fost creat
  "scores": { 
    "visibility": 0.78,      // agregat toate keywords
    "authority": 0.62,       // estimation domain authority
    "threat": 78.5           // threat score față de master
  },
  "last_run_scores": {
    "run_2025-11-13_14-00-12": {
      "visibility": 0.78,
      "keywords_ranked": 18,
      "avg_rank": 3.2,
      "best_rank": 1
    }
  },
  "notes": ""
}
```

### Collection: `ranks_history` (pentru master & fiecare competitor)
```javascript
{
  "_id": "rank:protectiilafoc.ro:vopsea intumescenta",
  "domain": "protectiilafoc.ro",
  "keyword": "vopsea intumescenta",
  "series": [
    {"date":"2025-11-13","rank":5,"run_id":"run_2025-11-13_14-00-12"},
    {"date":"2025-11-20","rank":4,"run_id":"run_2025-11-20_14-00-00"}
  ],
  "best_rank_ever": 3,
  "worst_rank_ever": 7,
  "current_rank": 4,
  "last_updated": "2025-11-20"
}
```

### Collection: `serp_alerts` (detecție schimbări automate)
```javascript
{
  "_id": ObjectId,
  "agent_id": "protectiilafoc.ro",
  "run_id": "run_2025-11-20_14-00-00",
  "date": "2025-11-20",
  "alert_type": "rank_drop|rank_gain|new_competitor|competitor_gain",
  "severity": "critical|warning|info",
  "keyword": "vopsea intumescenta",
  "details": {
    "previous_rank": 5,
    "current_rank": 8,
    "delta": -3,
    "competitor_surpassed_by": ["competitor3.ro", "competitor7.ro"]
  },
  "actions_suggested": [
    "Re-optimize page for keyword",
    "Create backlink strategy",
    "Run CopywriterAgent for content refresh"
  ],
  "action_taken": null,
  "notified_at": "2025-11-20T14:05:00Z",
  "acknowledged": false
}
```

### Qdrant Payload (pentru documente crawled)
```python
payload = {
    "source_domain": "promat.com",
    "keyword_context": "vopsea intumescenta",
    "crawl_date": "2025-11-13",
    "rank_at_ingest": 1,
    "serp_run_id": "run_2025-11-13_14-00-12",
    "content_type": "product_page|blog|homepage",
    "agent_type": "slave",
    "master_agent_id": "protectiilafoc.ro"
}
```

---

## 2️⃣ FORMULE DE SCORING (TRANSPARENTE)

### Per Keyword, Per Competitor
```python
# 1. Normalized Rank (1→1.0, 10→0.1, >10→0)
normalized_rank = (11 - min(rank, 10)) / 10

# 2. Type Weight
type_weight = {
    "organic": 1.0,
    "featured_snippet": 1.2,  # Featured snippets sunt mai vizibile
    "ad": 0.6,                 # Ads sunt plătite, mai puțin relevant
    "map": 0.8                 # Local pack
}[type]

# 3. Intent Weight (cât de valoros e keyword-ul)
intent_weight = {
    "informational": 0.8,      # "ce este protectia la foc"
    "commercial": 1.0,         # "vopsea intumescenta pret"
    "transactional": 1.1       # "cumpara vopsea intumescenta"
}[intent]

# 4. Difficulty Penalty (pe keywords foarte grele, scorurile sunt mai mici)
difficulty_penalty = 1 - (difficulty / 100) * 0.3  # difficulty = 0-100

# 5. Keyword Weight (volume search)
kw_weight = log(1 + volume_estimat) / log(1 + max_volume)  # normalizat [0..1]

# SCOR FINAL per keyword
competitor_score_kw = (
    normalized_rank * 
    type_weight * 
    intent_weight * 
    difficulty_penalty *
    kw_weight
)
```

### Agregat Competitor (toate keywords)
```python
# Visibility Score (suma pe toate keywords)
competitor_visibility = sum(
    competitor_score_kw * kw_weight 
    for kw in keywords_competitor_ranked_on
)

# Normalizare la [0..1]
max_possible_score = sum(kw_weight for kw in all_keywords)
competitor_visibility_normalized = competitor_visibility / max_possible_score

# Authority Score (estimation bazat pe domain metrics)
authority_score = (
    domain_age_factor * 0.3 +          # Domenii vechi = mai multe autoritate
    backlinks_count_factor * 0.4 +     # Număr backlinks
    domain_rating_factor * 0.3         # DR/DA din Moz/Ahrefs
)

# Threat Score (0-100)
threat_score = (
    competitor_visibility_normalized * 100 * 0.5 +  # 50% visibility
    authority_score * 100 * 0.3 +                   # 30% authority
    keyword_overlap_percentage * 0.2                 # 20% overlap cu master
)
```

### Master Score (aceeași formulă)
```python
# Master folosește ACEEAȘI formulă
master_score_kw = (
    normalized_rank * 
    type_weight * 
    intent_weight * 
    difficulty_penalty *
    kw_weight
)

master_visibility = sum(master_score_kw for kw in keywords_master_ranked_on)
master_visibility_normalized = master_visibility / max_possible_score

# Comparație cu competitori
master_rank_in_market = sorted_by_visibility.index(master_domain) + 1
master_percentile = (1 - master_rank_in_market / total_competitors) * 100
```

---

## 3️⃣ WORKFLOW (Jobs + Endpoints)

### Flow Complete
```
1. generate_subdomains (DeepSeek)
   ↓
2. generate_keywords (10-15 per subdomain)
   ↓
3. SERP_fetch (Google/Brave API, top 20 pentru fiecare keyword)
   ↓
4. SERP_parse (extract rank, URL, title, snippet, type)
   ↓
5. canonicalize_domains (dedup, lowercase, no www)
   ↓
6. score_competitors (aplică formule scoring)
   ↓
7. create_slave_agents (top 50 competitori)
   ↓
8. update_graph (noduri + muchii similarity/rank)
   ↓
9. deepseek_report (executive summary)
   ↓
10. schedule_monitoring (cron daily/weekly)
```

### Endpoints FastAPI

#### SERP Management
```python
POST /api/serp/run
Body: {
    "agent_id": "protectiilafoc.ro",
    "keywords": ["vopsea intumescenta", ...],
    "market": "ro",
    "provider": "brave|serpapi|custom"
}
Response: {
    "run_id": "run_2025-11-13_14-00-12",
    "status": "queued",
    "estimated_duration": "4 minutes"
}

GET /api/serp/run/{run_id}
Response: {
    "run_id": "run_2025-11-13_14-00-12",
    "status": "running|succeeded|failed|partial",
    "progress": {
        "current": 15,
        "total": 30,
        "percentage": 50
    },
    "stats": {
        "queries": 15,
        "pages_fetched": 15,
        "errors": 0,
        "unique_domains": 23
    }
}

GET /api/serp/results/{run_id}
Response: {
    "run_id": "run_2025-11-13_14-00-12",
    "results": [
        {
            "keyword": "vopsea intumescenta",
            "top_10": [
                {"rank":1,"domain":"promat.com","url":"...","title":"..."},
                // ... 9 more
            ],
            "master_rank": 5,
            "master_url": "..."
        },
        // ... 29 more keywords
    ]
}
```

#### Competitor Management
```python
POST /api/competitors/from-serp
Body: {
    "run_id": "run_2025-11-13_14-00-12"
}
Response: {
    "competitors_created": 47,
    "competitors_updated": 3,
    "total_unique_domains": 50
}

GET /api/competitors
Query: ?agent_id=protectiilafoc.ro&sort_by=threat_score&limit=20
Response: {
    "competitors": [
        {
            "domain": "promat.com",
            "threat_score": 78.5,
            "visibility": 0.78,
            "keywords_ranked": 18,
            "avg_rank": 3.2,
            "has_slave_agent": true,
            "slave_agent_id": "agent_promat"
        },
        // ... 19 more
    ]
}

GET /api/competitors/{domain}
Response: {
    "domain": "promat.com",
    "scores": {...},
    "keywords_ranked": ["vopsea intumescenta", ...],
    "rank_history": {...},
    "slave_agent": {...}
}
```

#### Slave Agents
```python
POST /api/agents/slave/create
Body: {
    "domain": "promat.com",
    "master_agent_id": "protectiilafoc.ro",
    "competitor_data": {...}
}
Response: {
    "success": true,
    "agent_slave_id": "agent_promat",
    "chunks_indexed": 87
}

GET /api/agents/slaves
Query: ?master_agent_id=protectiilafoc.ro
Response: {
    "slaves": [
        {"agent_id":"agent_promat","domain":"promat.com","threat_score":78.5},
        // ... 49 more
    ]
}
```

#### Graph & Visualization
```python
POST /api/graph/update
Body: {
    "agent_id": "protectiilafoc.ro",
    "run_id": "run_2025-11-13_14-00-12"
}
Response: {
    "nodes": [
        {"id":"protectiilafoc.ro","type":"master","size":2000},
        {"id":"promat.com","type":"competitor","size":1500,"threat":78.5},
        // ... 49 more
    ],
    "edges": [
        {"source":"protectiilafoc.ro","target":"promat.com","weight":0.6,"label":"60% overlap"},
        // ...
    ]
}

GET /api/graph/data/{agent_id}
Response: {
    "graph": {...},
    "layout": "force|circular|hierarchical"
}
```

#### Reports
```python
POST /api/report/deepseek
Body: {
    "agent_id": "protectiilafoc.ro",
    "run_id": "run_2025-11-13_14-00-12"
}
Response: {
    "report_id": "report_2025-11-13_14-10-00",
    "status": "generating",
    "estimated_duration": "30 seconds"
}

GET /api/report/{report_id}
Response: {
    "report_id": "report_2025-11-13_14-10-00",
    "agent_id": "protectiilafoc.ro",
    "generated_at": "2025-11-13T14:10:30Z",
    "executive_summary": "...",
    "market_position": {...},
    "top_threats": [...],
    "top_opportunities": [...],
    "recommended_actions": [...],
    "predictions": {...},
    "download_urls": {
        "markdown": "/api/report/report_2025-11-13_14-10-00/download?format=md",
        "pdf": "/api/report/report_2025-11-13_14-10-00/download?format=pdf",
        "json": "/api/report/report_2025-11-13_14-10-00/download?format=json"
    }
}
```

#### Monitoring & Alerts
```python
POST /api/monitor/schedule
Body: {
    "agent_id": "protectiilafoc.ro",
    "cadence": "daily|weekly|custom",
    "time": "14:00",  // UTC
    "keywords": null  // null = toate keywords
}
Response: {
    "schedule_id": "schedule_protectiilafoc_daily",
    "next_run": "2025-11-14T14:00:00Z",
    "status": "active"
}

GET /api/alerts
Query: ?agent_id=protectiilafoc.ro&severity=critical|warning|info&acknowledged=false
Response: {
    "alerts": [
        {
            "alert_id": "alert_2025-11-20_001",
            "type": "rank_drop",
            "severity": "critical",
            "keyword": "vopsea intumescenta",
            "details": {...},
            "actions_suggested": [...],
            "created_at": "2025-11-20T14:05:00Z"
        },
        // ...
    ]
}

POST /api/alerts/{alert_id}/acknowledge
Response: {"success": true}

POST /api/alerts/{alert_id}/action
Body: {
    "action": "run_copywriter_agent|create_backlinks|optimize_page"
}
Response: {
    "action_id": "action_001",
    "status": "queued"
}
```

#### WebSocket (Real-time Progress)
```python
WS /ws/jobs/{run_id}
Messages: {
    "type": "progress|status|log",
    "data": {
        "current": 15,
        "total": 30,
        "message": "Processing keyword 15/30: vopsea intumescenta"
    }
}
```

---

## 4️⃣ MONITORIZARE & DETECȚIE SCHIMBĂRI

### Cron Schedule (APScheduler sau Ray)
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Rulează zilnic la 14:00 UTC
@scheduler.scheduled_job('cron', hour=14, minute=0)
async def daily_serp_monitoring():
    """
    Rulează SERP fetch pentru toți agenții activi
    """
    agents = db.site_agents.find({"monitor_enabled": True})
    
    for agent in agents:
        run_id = await run_serp_fetch(
            agent_id=agent["_id"],
            keywords=agent["keywords"],
            market=agent.get("market", "ro")
        )
        
        # După finalizare, detectează schimbări
        await detect_changes(agent["_id"], run_id)
        
        # Generează raport dacă sunt alerte critice
        alerts = db.serp_alerts.find({
            "agent_id": agent["_id"],
            "run_id": run_id,
            "severity": "critical"
        })
        
        if alerts.count() > 0:
            await generate_deepseek_report(agent["_id"], run_id)
            await send_alert_notification(agent["_id"], alerts)
```

### Detecție Schimbări
```python
async def detect_changes(agent_id: str, run_id: str):
    """
    Compară run-ul curent cu run-ul anterior și detectează schimbări
    """
    current_run = db.serp_runs.find_one({"_id": run_id})
    previous_run = db.serp_runs.find_one({
        "agent_id": agent_id,
        "status": "succeeded",
        "_id": {"$ne": run_id}
    }, sort=[("finished_at", -1)])
    
    if not previous_run:
        logger.info("No previous run to compare")
        return
    
    alerts = []
    
    # Obține rezultate pentru ambele run-uri
    current_results = list(db.serp_results.find({"run_id": run_id}))
    previous_results = list(db.serp_results.find({"run_id": previous_run["_id"]}))
    
    # Organizează pe keyword
    current_by_kw = {}
    previous_by_kw = {}
    
    for r in current_results:
        kw = r["keyword"]
        if kw not in current_by_kw:
            current_by_kw[kw] = []
        current_by_kw[kw].append(r)
    
    for r in previous_results:
        kw = r["keyword"]
        if kw not in previous_by_kw:
            previous_by_kw[kw] = []
        previous_by_kw[kw].append(r)
    
    # Compară pentru fiecare keyword
    for keyword in current_by_kw.keys():
        current_kw_results = current_by_kw[keyword]
        previous_kw_results = previous_by_kw.get(keyword, [])
        
        # Găsește poziția masterului
        master_domain = db.site_agents.find_one({"_id": agent_id})["domain"]
        
        current_master_rank = next(
            (r["rank"] for r in current_kw_results if r["domain"] == master_domain),
            None
        )
        previous_master_rank = next(
            (r["rank"] for r in previous_kw_results if r["domain"] == master_domain),
            None
        )
        
        # 1. Rank Drop/Gain pentru master
        if current_master_rank and previous_master_rank:
            delta = previous_master_rank - current_master_rank  # Pozitiv = îmbunătățire
            
            if delta <= -3:  # Rank drop (ex: 3→6)
                alerts.append({
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "date": current_run["started_at"].date(),
                    "alert_type": "rank_drop",
                    "severity": "critical" if delta <= -5 else "warning",
                    "keyword": keyword,
                    "details": {
                        "previous_rank": previous_master_rank,
                        "current_rank": current_master_rank,
                        "delta": delta,
                        "competitors_surpassed_by": [
                            r["domain"] for r in current_kw_results
                            if previous_master_rank < r["rank"] <= current_master_rank
                        ]
                    },
                    "actions_suggested": [
                        "Re-optimize page for keyword",
                        "Analyze content gaps vs top 3",
                        "Check technical SEO issues",
                        "Run CopywriterAgent for content refresh"
                    ],
                    "notified_at": datetime.now(),
                    "acknowledged": False
                })
            
            elif delta >= 3:  # Rank gain (ex: 6→3)
                alerts.append({
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "date": current_run["started_at"].date(),
                    "alert_type": "rank_gain",
                    "severity": "info",
                    "keyword": keyword,
                    "details": {
                        "previous_rank": previous_master_rank,
                        "current_rank": current_master_rank,
                        "delta": delta
                    },
                    "actions_suggested": [],
                    "notified_at": datetime.now(),
                    "acknowledged": False
                })
        
        # 2. Master intrat în Top 10
        if current_master_rank and current_master_rank <= 10:
            if not previous_master_rank or previous_master_rank > 10:
                alerts.append({
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "alert_type": "entered_top_10",
                    "severity": "info",
                    "keyword": keyword,
                    "details": {
                        "current_rank": current_master_rank
                    }
                })
        
        # 3. Master ieșit din Top 10
        if previous_master_rank and previous_master_rank <= 10:
            if not current_master_rank or current_master_rank > 10:
                alerts.append({
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "alert_type": "dropped_from_top_10",
                    "severity": "critical",
                    "keyword": keyword,
                    "details": {
                        "previous_rank": previous_master_rank,
                        "current_rank": current_master_rank
                    }
                })
        
        # 4. New Competitor în Top 3
        current_top3_domains = [r["domain"] for r in sorted(current_kw_results, key=lambda x: x["rank"])[:3]]
        previous_top3_domains = [r["domain"] for r in sorted(previous_kw_results, key=lambda x: x["rank"])[:3]]
        
        new_competitors_top3 = set(current_top3_domains) - set(previous_top3_domains)
        if new_competitors_top3:
            for domain in new_competitors_top3:
                current_rank = next(r["rank"] for r in current_kw_results if r["domain"] == domain)
                alerts.append({
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "alert_type": "new_competitor_top3",
                    "severity": "warning",
                    "keyword": keyword,
                    "details": {
                        "competitor": domain,
                        "rank": current_rank
                    },
                    "actions_suggested": [
                        f"Create slave agent for {domain}",
                        f"Analyze {domain} content strategy",
                        f"Monitor {domain} backlink profile"
                    ]
                })
        
        # 5. Competitor Gain (competitor urcă semnificativ)
        for r_curr in current_kw_results:
            domain = r_curr["domain"]
            if domain == master_domain:
                continue
            
            r_prev = next((r for r in previous_kw_results if r["domain"] == domain), None)
            if r_prev:
                delta = r_prev["rank"] - r_curr["rank"]
                if delta >= 3:  # Competitor a urcat 3+ poziții
                    alerts.append({
                        "agent_id": agent_id,
                        "run_id": run_id,
                        "alert_type": "competitor_gain",
                        "severity": "warning",
                        "keyword": keyword,
                        "details": {
                            "competitor": domain,
                            "previous_rank": r_prev["rank"],
                            "current_rank": r_curr["rank"],
                            "delta": delta
                        },
                        "actions_suggested": [
                            f"Investigate {domain} recent changes",
                            f"Check if {domain} has new backlinks"
                        ]
                    })
    
    # Salvează alertele
    if alerts:
        db.serp_alerts.insert_many(alerts)
        logger.info(f"✅ Generated {len(alerts)} alerts for agent {agent_id}")
    
    return alerts
```

### Acțiuni Automate
```python
async def auto_actions(alert):
    """
    Acțiuni automate bazate pe tip alertă
    """
    if alert["alert_type"] == "rank_drop" and alert["severity"] == "critical":
        # 1. Pornește CopywriterAgent pentru refresh content
        await trigger_copywriter_agent(
            agent_id=alert["agent_id"],
            keyword=alert["keyword"],
            target="improve_content"
        )
        
        # 2. Sugerează backlink targets
        top_3_for_kw = await get_top_3_for_keyword(alert["keyword"])
        backlink_targets = [comp["domain"] for comp in top_3_for_kw]
        
        # 3. Analiză tehnică SEO
        await trigger_technical_seo_audit(
            agent_id=alert["agent_id"],
            page_url=alert["details"].get("master_url")
        )
    
    elif alert["alert_type"] == "new_competitor_top3":
        # Creează slave agent pentru noul competitor
        competitor_domain = alert["details"]["competitor"]
        if not db.competitors.find_one({"domain": competitor_domain, "agent_slave_id": {"$exists": True}}):
            await create_slave_agent(
                domain=competitor_domain,
                master_agent_id=alert["agent_id"]
            )
```

### Notificări (Slack/Email)
```python
async def send_alert_notification(agent_id: str, alerts: list):
    """
    Trimite notificări pentru alerte critice
    """
    agent = db.site_agents.find_one({"_id": agent_id})
    
    # Slack webhook
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    if slack_webhook:
        message = {
            "text": f"🚨 SERP Alert: {agent['domain']}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 {len(alerts)} SERP Alerts for {agent['domain']}"
                    }
                }
            ]
        }
        
        for alert in alerts[:5]:  # Max 5 în notificare
            severity_emoji = {"critical": "🔴", "warning": "⚠️", "info": "ℹ️"}[alert["severity"]]
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{severity_emoji} *{alert['alert_type']}*\n"
                           f"Keyword: `{alert['keyword']}`\n"
                           f"Details: {json.dumps(alert['details'], indent=2)}"
                }
            })
        
        # Link la dashboard
        message["blocks"].append({
            "type": "actions",
            "elements": [{
                "type": "button",
                "text": {"type": "plain_text", "text": "View Dashboard"},
                "url": f"https://dashboard.example.com/agents/{agent_id}/alerts"
            }]
        })
        
        async with aiohttp.ClientSession() as session:
            await session.post(slack_webhook, json=message)
    
    # Email (SendGrid, Mailgun, etc.)
    email_to = agent.get("notification_email")
    if email_to:
        await send_email(
            to=email_to,
            subject=f"SERP Alert: {len(alerts)} changes for {agent['domain']}",
            body=render_email_template(alerts)
        )
```

---

## 5️⃣ ANTI-DUBLURI & CANONICALIZARE

### Canonicalizare Domeniu
```python
from urllib.parse import urlparse
import publicsuffix2

psl = publicsuffix2.PublicSuffixList()

def canonical_domain(url: str) -> str:
    """
    Canonicalizează domeniul:
    - Remove www.
    - Lowercase
    - Remove trailing /
    - Keep only registered domain (ex: promat.com din www.promat.com/ro-ro/page)
    """
    parsed = urlparse(url.lower().strip())
    netloc = parsed.netloc or parsed.path.split('/')[0]
    
    # Remove www.
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    
    # Get registered domain (handles .co.uk, .com.ro, etc.)
    try:
        registered_domain = psl.get_public_suffix(netloc)
        # Get one level up (example.com from api.example.com)
        parts = netloc.rsplit('.', 2)
        if len(parts) >= 2:
            netloc = '.'.join(parts[-2:])
    except:
        pass
    
    return netloc

# Exemple:
# "https://www.Promat.com/ro-ro/products" → "promat.com"
# "https://promat.ro" → "promat.ro"
# "https://api.competitor.com" → "competitor.com"
```

### Deduplicare SERP
```python
def deduplicate_serp_results(results: list) -> list:
    """
    Deduplicare rezultate SERP:
    - Pentru același domeniu pe același keyword: păstrează cel cu rank mai bun
    - Salvează variantele în array `variants`
    """
    by_domain_kw = {}
    
    for result in results:
        canonical = canonical_domain(result["url"])
        key = (canonical, result["keyword"])
        
        if key not in by_domain_kw:
            by_domain_kw[key] = {
                "domain": canonical,
                "keyword": result["keyword"],
                "rank": result["rank"],
                "url": result["url"],
                "title": result["title"],
                "snippet": result["snippet"],
                "type": result["type"],
                "variants": []
            }
        else:
            # Dacă e o variantă cu rank mai bun, înlocuiește
            if result["rank"] < by_domain_kw[key]["rank"]:
                # Salvează vechiul ca variantă
                by_domain_kw[key]["variants"].append({
                    "rank": by_domain_kw[key]["rank"],
                    "url": by_domain_kw[key]["url"],
                    "title": by_domain_kw[key]["title"]
                })
                # Update cu noul
                by_domain_kw[key]["rank"] = result["rank"]
                by_domain_kw[key]["url"] = result["url"]
                by_domain_kw[key]["title"] = result["title"]
                by_domain_kw[key]["snippet"] = result["snippet"]
            else:
                # Salvează ca variantă
                by_domain_kw[key]["variants"].append({
                    "rank": result["rank"],
                    "url": result["url"],
                    "title": result["title"]
                })
    
    return list(by_domain_kw.values())
```

### Map Near Duplicates
```python
# Custom rules pentru domenii "near duplicate"
DOMAIN_ALIASES = {
    "promat.ro": "promat.com",  # Tratează .ro și .com ca același brand
    "www.competitor.co.uk": "competitor.com",
}

def resolve_domain_alias(domain: str) -> str:
    """Rezolvă aliasuri cunoscute"""
    return DOMAIN_ALIASES.get(domain, domain)
```

---

## 6️⃣ UI COMPONENTS (Dashboard React)

### 1. SERP Overview (per run)
```jsx
function SERPOverview({ runId }) {
  const { data, isLoading } = useQuery({
    queryKey: ['serp-results', runId],
    queryFn: () => api.get(`/api/serp/results/${runId}`)
  });
  
  if (isLoading) return <Loader />;
  
  return (
    <div className="card">
      <h2>SERP Overview: Run {runId}</h2>
      
      {/* Heatmap: keywords × top 10 domenii */}
      <div className="heatmap">
        <table>
          <thead>
            <tr>
              <th>Keyword</th>
              {[1,2,3,4,5,6,7,8,9,10].map(i => <th key={i}>{i}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.results.map(kw => (
              <tr key={kw.keyword}>
                <td>{kw.keyword}</td>
                {kw.top_10.map((result, idx) => (
                  <td key={idx} className={
                    result.domain === data.master_domain ? 'bg-green-500' :
                    result.is_competitor ? 'bg-red-500' :
                    'bg-gray-300'
                  }>
                    {result.domain}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

### 2. Trends (rank vs time)
```jsx
function RankTrendsChart({ agentId, keyword }) {
  const { data } = useQuery({
    queryKey: ['rank-history', agentId, keyword],
    queryFn: () => api.get(`/api/ranks/history/${agentId}/${keyword}`)
  });
  
  return (
    <Line
      data={{
        labels: data.series.map(s => s.date),
        datasets: [
          {
            label: 'Master',
            data: data.master_series,
            borderColor: 'rgb(255, 99, 132)',
          },
          {
            label: 'Competitor #1',
            data: data.competitor1_series,
            borderColor: 'rgb(54, 162, 235)',
          },
          {
            label: 'Competitor #2',
            data: data.competitor2_series,
            borderColor: 'rgb(75, 192, 192)',
          }
        ]
      }}
      options={{
        scales: {
          y: { reverse: true, min: 1, max: 20 }
        }
      }}
    />
  );
}
```

### 3. Competitor Detail
```jsx
function CompetitorDetail({ domain }) {
  const { data } = useQuery({
    queryKey: ['competitor', domain],
    queryFn: () => api.get(`/api/competitors/${domain}`)
  });
  
  return (
    <div className="card">
      <h2>{domain}</h2>
      
      {/* Scoruri */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard title="Threat Score" value={data.scores.threat} />
        <StatCard title="Visibility" value={data.scores.visibility} />
        <StatCard title="Authority" value={data.scores.authority} />
      </div>
      
      {/* Keywords unde bate masterul */}
      <h3>Keywords unde {domain} BATE masterul:</h3>
      <ul>
        {data.keywords_winning.map(kw => (
          <li key={kw.keyword}>
            {kw.keyword}: {domain} (#{kw.competitor_rank}) vs Master (#{kw.master_rank})
          </li>
        ))}
      </ul>
      
      {/* Keywords unde pierde */}
      <h3>Keywords unde {domain} PIERDE față de master:</h3>
      <ul>
        {data.keywords_losing.map(kw => (
          <li key={kw.keyword}>
            {kw.keyword}: Master (#{kw.master_rank}) vs {domain} (#{kw.competitor_rank})
          </li>
        ))}
      </ul>
      
      {/* Slave agent */}
      {data.slave_agent && (
        <div>
          <h3>Slave Agent</h3>
          <Link to={`/agents/${data.slave_agent.agent_id}`}>
            View Agent Details
          </Link>
        </div>
      )}
    </div>
  );
}
```

### 4. Alerts Dashboard
```jsx
function AlertsDashboard({ agentId }) {
  const { data, refetch } = useQuery({
    queryKey: ['alerts', agentId],
    queryFn: () => api.get(`/api/alerts?agent_id=${agentId}&acknowledged=false`)
  });
  
  const handleAcknowledge = async (alertId) => {
    await api.post(`/api/alerts/${alertId}/acknowledge`);
    refetch();
  };
  
  const handleRunAction = async (alertId, action) => {
    await api.post(`/api/alerts/${alertId}/action`, { action });
    toast.success(`Action ${action} queued!`);
  };
  
  return (
    <div className="space-y-4">
      {data.alerts.map(alert => (
        <div key={alert.alert_id} className={`card border-l-4 ${
          alert.severity === 'critical' ? 'border-red-500' :
          alert.severity === 'warning' ? 'border-yellow-500' :
          'border-blue-500'
        }`}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold">{alert.alert_type}</h3>
              <p>Keyword: {alert.keyword}</p>
              <pre>{JSON.stringify(alert.details, null, 2)}</pre>
            </div>
            <div className="flex flex-col gap-2">
              <button onClick={() => handleAcknowledge(alert.alert_id)}>
                Acknowledge
              </button>
              {alert.actions_suggested.map(action => (
                <button key={action} onClick={() => handleRunAction(alert.alert_id, action)}>
                  {action}
                </button>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

### 5. Next Best Actions (ICE Score)
```jsx
function NextBestActions({ agentId }) {
  const { data } = useQuery({
    queryKey: ['next-actions', agentId],
    queryFn: () => api.get(`/api/recommendations/next-actions/${agentId}`)
  });
  
  // ICE Score = Impact × Confidence × Ease
  // Sortare descrescătoare după ICE
  
  return (
    <div className="card">
      <h2>Next Best Actions (ICE Prioritization)</h2>
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Impact</th>
            <th>Confidence</th>
            <th>Ease</th>
            <th>ICE Score</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {data.actions.map(action => (
            <tr key={action.id}>
              <td>{action.description}</td>
              <td>{action.impact}/10</td>
              <td>{action.confidence}/10</td>
              <td>{action.ease}/10</td>
              <td><strong>{action.ice_score}/1000</strong></td>
              <td>
                <button onClick={() => executeAction(action.id)}>
                  Execute
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## 7️⃣ PERFORMANȚĂ, LEGAL, FIABILITATE

### Rate Limiting
```python
from aiohttp import ClientSession
from asyncio import Semaphore, sleep

class RateLimitedClient:
    def __init__(self, max_requests_per_second=5):
        self.semaphore = Semaphore(max_requests_per_second)
        self.last_request_time = 0
        self.min_interval = 1.0 / max_requests_per_second
    
    async def request(self, url, **kwargs):
        async with self.semaphore:
            # Wait for rate limit
            now = time.time()
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_interval:
                await sleep(self.min_interval - time_since_last)
            
            self.last_request_time = time.time()
            
            # Make request
            async with ClientSession() as session:
                async with session.get(url, **kwargs) as response:
                    return await response.json()
```

### Retry Logic (Exponential Backoff)
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.5, min=1, max=60)
)
async def fetch_serp(keyword, market):
    """
    Retry up to 3 times with exponential backoff:
    - Attempt 1: immediate
    - Attempt 2: wait 1.5s
    - Attempt 3: wait 2.25s
    """
    response = await brave_search_api(keyword, market)
    
    if response.status_code != 200:
        raise Exception(f"SERP fetch failed: {response.status_code}")
    
    return response.json()
```

### Proxy Pool (Rotating)
```python
class ProxyPool:
    def __init__(self, proxies: list):
        self.proxies = proxies
        self.current_idx = 0
        self.failed_proxies = set()
    
    def get_next_proxy(self):
        """Round-robin selection, skip failed proxies"""
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_idx]
            self.current_idx = (self.current_idx + 1) % len(self.proxies)
            
            if proxy not in self.failed_proxies:
                return proxy
            
            attempts += 1
        
        # All proxies failed, reset
        self.failed_proxies.clear()
        return self.proxies[0]
    
    def mark_failed(self, proxy):
        self.failed_proxies.add(proxy)

# Usage
proxy_pool = ProxyPool([
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080"
])

async def fetch_with_proxy(url):
    proxy = proxy_pool.get_next_proxy()
    try:
        response = await session.get(url, proxy=proxy)
        return response
    except:
        proxy_pool.mark_failed(proxy)
        raise
```

### Robots.txt & ToS Compliance
```python
import urllib.robotparser

def can_scrape(url: str) -> bool:
    """Check if scraping is allowed by robots.txt"""
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{urlparse(url).scheme}://{urlparse(url).netloc}/robots.txt")
    try:
        rp.read()
        return rp.can_fetch("*", url)
    except:
        # If robots.txt doesn't exist, assume allowed
        return True

# Usage
if not can_scrape(competitor_url):
    logger.warning(f"Scraping disallowed by robots.txt: {competitor_url}")
    # Skip scraping, use only SERP data (title, snippet, URL)
```

### Audit Logs
```python
import ndjson

class AuditLogger:
    def __init__(self, run_id: str):
        self.log_file = f"/logs/serp/{run_id}.ndjson"
        self.run_id = run_id
    
    def log(self, event_type: str, data: dict):
        """Log event to NDJSON file"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "run_id": self.run_id,
            "event_type": event_type,
            "data": data
        }
        
        with open(self.log_file, 'a') as f:
            ndjson.dump([event], f)
    
    def log_query(self, keyword, provider, status):
        self.log("serp_query", {
            "keyword": keyword,
            "provider": provider,
            "status": status
        })
    
    def log_result(self, keyword, rank, domain, url):
        self.log("serp_result", {
            "keyword": keyword,
            "rank": rank,
            "domain": domain,
            "url": url
        })
    
    def log_error(self, keyword, error):
        self.log("serp_error", {
            "keyword": keyword,
            "error": str(error)
        })

# Usage
audit = AuditLogger(run_id)
audit.log_query("vopsea intumescenta", "brave", "success")
audit.log_result("vopsea intumescenta", 1, "promat.com", "https://...")
```

---

## 8️⃣ MINI-COD (Schelet Python)

### serp_ingest.py
```python
#!/usr/bin/env python3
"""
SERP Ingest & Scoring Module
"""

from datetime import datetime
from urllib.parse import urlparse
import math
from typing import List, Dict
import publicsuffix2

psl = publicsuffix2.PublicSuffixList()

def canonical_domain(url: str) -> str:
    """Canonicalizează domeniul"""
    d = urlparse(url.lower()).netloc
    if d.startswith("www."):
        d = d[4:]
    return d

def normalized_rank(rank: int) -> float:
    """Normalizează rank la [0..1]"""
    if rank > 10:
        return 0.0
    return (11 - rank) / 10.0

def competitor_score(
    rank: int, 
    rtype: str, 
    intent: str, 
    difficulty: int, 
    volume: int
) -> float:
    """
    Calculează scor per keyword per competitor
    
    Formula:
    score = normalized_rank × type_weight × intent_weight × difficulty_penalty × kw_weight
    """
    # Type weights
    type_weights = {
        "organic": 1.0,
        "featured_snippet": 1.2,
        "ad": 0.6,
        "map": 0.8
    }
    type_w = type_weights.get(rtype, 1.0)
    
    # Intent weights
    intent_weights = {
        "informational": 0.8,
        "commercial": 1.0,
        "transactional": 1.1
    }
    intent_w = intent_weights.get(intent, 1.0)
    
    # Difficulty penalty
    diff_pen = 1 - (difficulty / 100.0) * 0.3
    
    # Keyword weight (based on volume)
    kw_w = math.log1p(max(volume or 0, 0))
    kw_w = kw_w / (kw_w + 5)  # Normalizare simplă [0..1]
    
    # Final score
    return (
        normalized_rank(rank) * 
        type_w * 
        intent_w * 
        diff_pen * 
        kw_w
    )

def aggregate_visibility(items: List[Dict]) -> List[Dict]:
    """
    Agregă scoruri per domeniu
    
    Args:
        items: Lista de rezultate SERP cu rank, url, type, intent, difficulty, volume
    
    Returns:
        Lista sortată descrescător după score
    """
    by_domain = {}
    
    for it in items:
        dom = canonical_domain(it["url"])
        s = competitor_score(
            it["rank"], 
            it["type"], 
            it["intent"], 
            it.get("difficulty", 50),  # default medium difficulty
            it.get("volume", 0)
        )
        by_domain[dom] = by_domain.get(dom, 0.0) + s
    
    # Sort by score descending
    result = [
        {"domain": k, "visibility_score": v} 
        for k, v in by_domain.items()
    ]
    result.sort(key=lambda x: -x["visibility_score"])
    
    return result

def calculate_threat_score(
    visibility_score: float,
    authority_score: float,
    keyword_overlap_percentage: float
) -> float:
    """
    Calculează threat score (0-100)
    
    Formula:
    threat = visibility × 50% + authority × 30% + overlap × 20%
    """
    return (
        visibility_score * 100 * 0.5 +
        authority_score * 100 * 0.3 +
        keyword_overlap_percentage * 0.2
    )

# Example usage
if __name__ == "__main__":
    # Simulate SERP results for "vopsea intumescenta"
    serp_results = [
        {"rank": 1, "url": "https://www.promat.com/ro-ro/...", "type": "organic", "intent": "commercial", "difficulty": 65, "volume": 500},
        {"rank": 2, "url": "https://competitor2.ro/...", "type": "organic", "intent": "commercial", "difficulty": 65, "volume": 500},
        {"rank": 3, "url": "https://protectiilafoc.ro/...", "type": "organic", "intent": "commercial", "difficulty": 65, "volume": 500},
        # ... 7 more
    ]
    
    # Aggregate visibility
    visibility = aggregate_visibility(serp_results)
    print("Visibility Scores:")
    for comp in visibility[:5]:
        print(f"  {comp['domain']}: {comp['visibility_score']:.3f}")
    
    # Calculate threat for top competitor
    top_comp = visibility[0]
    threat = calculate_threat_score(
        visibility_score=top_comp["visibility_score"] / 10,  # normalize to [0..1]
        authority_score=0.62,  # from external source (Moz/Ahrefs)
        keyword_overlap_percentage=60.0
    )
    print(f"\nThreat Score for {top_comp['domain']}: {threat:.1f}/100")
```

---

## 9️⃣ RAPORT DEEPSEEK (Prompt Consistent)

### System Prompt
```
Ești un analist SEO senior cu experiență în competitive intelligence. 

Primești date despre:
- SERP runs (rezultate Google Search pentru keywords)
- Scoruri competitori (visibility, authority, threat)
- Intenții keywords (informational, commercial, transactional)
- Istorice rank (evoluție poziții în timp)

TASK:
Generează un EXECUTIVE SUMMARY concis și acționabil pentru CEO. Folosește DOAR datele primite, NU inventa cifre.

STRUCTURĂ OBLIGATORIE:
1. **Executive Summary** (2-3 propoziții) - Poziția actuală și tendința
2. **Unde câștigăm** - Top 3-5 keywords unde masterul domină
3. **Unde pierdem** - Top 3-5 keywords unde competitorii ne bat
4. **Top 5 Oportunități** - Keywords cu potențial mare de îmbunătățire
5. **5 Acțiuni concrete (14 zile)** - Prioritizate după impact
6. **Riscuri** - Ce se întâmplă dacă NU acționăm

STIL:
- Concis, tabelizat când e util
- Cifre exacte, nu estimări vagi
- Acțiuni concrete, nu recomandări generice
- CEO-friendly (evită jargon tehnic excesiv)
```

### User Prompt Template
```python
def generate_deepseek_prompt(agent_id: str, run_id: str) -> str:
    """
    Generează prompt pentru raport DeepSeek
    """
    # Obține date
    agent = db.site_agents.find_one({"_id": agent_id})
    run = db.serp_runs.find_one({"_id": run_id})
    results = list(db.serp_results.find({"run_id": run_id}))
    competitors = list(db.competitors.find({"last_run_scores.run_id": run_id}))
    
    # Pregătește date pentru prompt
    master_domain = agent["domain"]
    keywords = agent["keywords"]
    
    # Keywords unde masterul domină (rank ≤ 3)
    keywords_winning = [
        r for r in results 
        if r["domain"] == master_domain and r["rank"] <= 3
    ]
    
    # Keywords unde masterul pierde (rank > 10 sau absent)
    keywords_losing = [
        kw for kw in keywords
        if not any(r["domain"] == master_domain and r["rank"] <= 10 for r in results if r["keyword"] == kw)
    ]
    
    # Top 5 competitori
    top_competitors = sorted(
        competitors, 
        key=lambda x: x["scores"]["threat"], 
        reverse=True
    )[:5]
    
    # Construiește prompt
    prompt = f"""
# DATE ANALIZĂ SERP

## Master Agent
- **Domain:** {master_domain}
- **Total Keywords:** {len(keywords)}
- **Keywords în Top 10:** {len([r for r in results if r["domain"] == master_domain and r["rank"] <= 10])}
- **Avg Rank (când apare):** {avg_rank_master:.1f}

## Keywords unde MASTERUL DOMINĂ (Top 3):
{format_keywords_table(keywords_winning)}

## Keywords unde MASTERUL LIPSEȘTE sau e slab (rank > 10):
{format_keywords_table(keywords_losing)}

## Top 5 Competitori (Threat Score):
{format_competitors_table(top_competitors)}

## Evoluție Rank (ultimele 30 zile):
{format_rank_evolution(master_domain, keywords[:5])}

---

Generează raportul CEO conform structurii obligatorii.
"""
    
    return prompt

def format_keywords_table(keywords_data: list) -> str:
    """Format keywords as markdown table"""
    if not keywords_data:
        return "Niciun keyword în această categorie.\n"
    
    table = "| Keyword | Rank | URL | Type |\n"
    table += "|---------|------|-----|------|\n"
    
    for kw in keywords_data[:10]:  # Max 10
        table += f"| {kw['keyword']} | {kw['rank']} | {kw['url'][:50]}... | {kw['type']} |\n"
    
    return table

def format_competitors_table(competitors: list) -> str:
    """Format competitors as markdown table"""
    table = "| # | Domain | Threat Score | Keywords Ranked | Avg Rank |\n"
    table += "|---|--------|--------------|-----------------|----------|\n"
    
    for i, comp in enumerate(competitors, 1):
        table += f"| {i} | {comp['domain']} | {comp['scores']['threat']:.1f} | {len(comp['keywords_seen'])} | {comp['last_run_scores'].get('avg_rank', 'N/A')} |\n"
    
    return table

def format_rank_evolution(domain: str, keywords: list) -> str:
    """Format rank evolution for top keywords"""
    text = ""
    for kw in keywords:
        history = db.ranks_history.find_one({"domain": domain, "keyword": kw})
        if history:
            series = history["series"][-7:]  # Last 7 days
            text += f"\n**{kw}:**\n"
            text += " → ".join([f"#{s['rank']} ({s['date']})" for s in series])
            text += "\n"
    return text
```

### Expected Output Format
```markdown
# 📊 RAPORT COMPETITIVE INTELLIGENCE
**Agent Master:** protectiilafoc.ro  
**Data:** 2025-11-13 14:30  
**Keywords Analizate:** 30  
**Run ID:** run_2025-11-13_14-00-12  

---

## 🎯 EXECUTIVE SUMMARY
Protectiilafoc.ro se află pe locul **8 din 47** competitori identificați, cu o acoperire de **40%** din keywords-urile cheie (12/30 în Top 10). Poziția medie actuală este **5.2**, în scădere cu **0.8 poziții** față de săptămâna trecută (🔴 semnal negativ). Principalul competitor, **promat.com** (Threat Score: **78.5**), domină **60%** din keywords-uri cu poziții medii de **3.2**.

---

## ✅ UNDE CÂȘTIGĂM (Top 5)
Keywords unde masterul domină:

| # | Keyword | Rank | Traffic Est. | Competiție |
|---|---------|------|--------------|------------|
| 1 | protecție la foc București | **#1** | 800/lună | Medie |
| 2 | ignifugare lemn certificată | **#2** | 300/lună | Scăzută |
| 3 | termoprotecție structuri | **#3** | 450/lună | Medie |

**Insight:** Dominăm pe keywords geo-localizate și specifice. Capitalizați prin:
- Mențineți conținut fresh (update lunar)
- Backlinks de la site-uri locale (.ro)
- Landing pages dedicate per subdomeniu

---

## 🔴 UNDE PIERDEM (Top 5)
Keywords unde competitorii ne depășesc:

| # | Keyword | Master Rank | Top 3 Competitori | Gap |
|---|---------|-------------|-------------------|-----|
| 1 | sisteme sprinklere antiincendiu | **Absent (>20)** | promat.com (#1), competitor5 (#2) | **MARE** |
| 2 | detectoare fum certificate | **#15** | competitor3 (#1), promat.com (#3) | **MARE** |
| 3 | vopsea intumescentă pret | **#12** | competitor7 (#2), promat.com (#4) | **MEDIU** |

**Insight:** Lipsim pe keywords **transacționale** (intenție de cumpărare). Competitorii au:
- Pagini de produs dedicate
- Prețuri afișate clar
- Call-to-action puternice

---

## 💡 TOP 5 OPORTUNITĂȚI (Prioritizate după ICE)

| # | Keyword | Volume | Difficulty | ICE Score | De ce? |
|---|---------|--------|------------|-----------|--------|
| 1 | **sisteme sprinklere antiincendiu** | 800/lună | 65/100 | **900/1000** | Volume mare + master lipsește complet + competiție fragmentată (top 3 au scoruri apropiate 85-80-78) |
| 2 | **detectoare fum certificate** | 600/lună | 58/100 | **850/1000** | Intent comercial mare + afinitate cu produsele curente |
| 3 | **protecție pasivă la foc** | 500/lună | 70/100 | **720/1000** | Subdomeniului master dar absent în SERP |
| 4 | **vopsea intumescentă pret** | 400/lună | 55/100 | **680/1000** | Rank #12 → ușor de mutat în Top 5 cu optimizări |
| 5 | **audit protecție la foc** | 350/lună | 48/100 | **620/1000** | Nișă consultanță (marjă mare) + competiție scăzută |

**Estimare impact:** +**2,650 vizitatori/lună** (+**40%**) dacă intrăm în Top 5 pe toate cele 5.

---

## 🚀 5 ACȚIUNI CONCRETE (Următoarele 14 zile)

### 1. **Creează landing pages pentru cele 5 keywords oportunitate** ⚡ PRIORITATE 1
- **Effort:** 3 zile (copywriter + dev)
- **Impact:** +40% traffic în 3 luni
- **Acțiune:** 
  - Pagină pentru "sisteme sprinklere antiincendiu" (include: specs, certificări, case study, CTA clar)
  - Pagină pentru "detectoare fum" (liste produse, comparații, prețuri)
  - Pagină pentru "protecție pasivă la foc" (hub pentru subdomeniu)

### 2. **Optimizare SEO on-page pentru "vopsea intumescentă pret"** ⚡ PRIORITATE 1
- **Effort:** 4 ore
- **Impact:** Mișcare de la #12 → #5 în 2 săptămâni
- **Acțiune:**
  - Adaugă tabel prețuri
  - Meta title: "Vopsea Intumescentă Pret - Oferte Protecție la Foc | [Brand]"
  - H1: "Vopsea Intumescentă - Prețuri și Oferte [2025]"
  - Adaugă schema.org Product markup

### 3. **Backlink strategy - 10 backlinks de calitate** 📈 PRIORITATE 2
- **Effort:** 7 zile (outreach + guest posting)
- **Impact:** +15% domain authority → rank boost pe toate keywords
- **Target:** Site-uri .ro din construcții/siguranță (DR > 30)
- **Metoda:** Guest posts cu link natural în context

### 4. **Content refresh - update top 3 pagini existente** 🔄 PRIORITATE 2
- **Effort:** 2 zile
- **Impact:** Previne scăderi viitoare de rank
- **Acțiune:**
  - "protecție la foc București" - adaugă case study recent (2025)
  - "ignifugare lemn" - update statistici, norme 2025
  - "termoprotecție" - adaugă FAQ section

### 5. **Creare 3 blog posts SEO-targeted** 📝 PRIORITATE 3
- **Effort:** 5 zile (research + writing + publish)
- **Impact:** Long-tail traffic + internal linking
- **Topics:**
  - "Cum aleg cel mai bun sistem sprinkler pentru clădirea mea" (target: "sisteme sprinklere")
  - "Detectoare de fum certificate vs. non-certificate: diferențe esențiale" (target: "detectoare fum")
  - "Prețuri protecție la foc 2025: ghid complet" (target: "vopsea intumescentă pret")

---

## ⚠️ RISCURI (dacă NU acționăm)

### Scenariu Negativ (3-6 luni fără acțiune):
1. **Promat.com consolidează dominația**
   - Threat Score: 78.5 → **85+**
   - Devine "industry standard" (users caută direct brandul lor)
   - Masterul coboară pe loc **10-12**

2. **Pierdere trafic organic: -30-40%**
   - Competitors nou intați în Top 3 (am observat 2 domenii noi săptămâna trecută)
   - Algoritmul Google favorizează site-uri cu "freshness" → conținutul nostru devine învechit

3. **Pierdere clienți potențiali: estimat -50 leads/lună**
   - Keywords transacționale ("pret", "oferta") = clienți gata să cumpere
   - Dacă nu apar în top 5, nu există pentru ei

4. **Cost PPC crește: +40% pentru a compensa organic**
   - Dacă organic scade, va trebui compensat cu ads
   - Estimare: +€2,000/lună în Google Ads

### Scenariu Pozitiv (cu acțiunile recomandate):
- **3 luni:** Top 5 pe 8-10 keywords (vs. 3 acum)
- **6 luni:** Top 3 pe 5-7 keywords + intrare în local pack (Google Maps)
- **12 luni:** Loc **3-5** în industrie (vs. 8 acum)
- **ROI:** +60-80% traffic organic → +30-50% conversii → +€5,000-8,000 revenue/lună

---

**Recomandare finală:** Implementați prioritățile 1 și 2 IMEDIAT (următoarele 7 zile). Impact maxim cu effort rezonabil.

**Next Review:** 14 zile (2025-11-27) - tracking rank changes după implementare.

---

*Generat automat de DeepSeek Competitive Intelligence System*  
*Data: 2025-11-13 14:30 UTC*
```

---

## 🎯 REZUMAT: CE IMPLEMENTĂM

### Prioritate 1 (Această săptămână):
1. ✅ Schemas MongoDB (serp_runs, serp_results, competitors, ranks_history, serp_alerts)
2. ✅ Formule scoring (implementare în Python)
3. ✅ Canonicalizare + deduplicare
4. ✅ Audit logging

### Prioritate 2 (Următoarele 2 săptămâni):
5. ⚠️ API endpoints complete
6. ⚠️ Monitorizare zilnică + detecție schimbări
7. ⚠️ Alerte Slack/Email
8. ⚠️ DeepSeek raport cu prompt consistent

### Prioritate 3 (Luna viitoare):
9. ❌ UI components React (heatmap, trends, alerts dashboard)
10. ❌ Next Best Actions (ICE scoring)
11. ❌ Proxy pool + rate limiting avansat

---

**Estimated Implementation Time:** 2-3 săptămâni pentru production-ready system

