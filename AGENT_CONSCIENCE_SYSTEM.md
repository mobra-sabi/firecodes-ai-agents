# 🧠 Agent Conscience System - Sistem Complet de Conștiință

**Data**: 21 NOV 2025  
**Status**: ✅ **IMPLEMENTAT COMPLET**

---

## 🎯 Ce este "Conștiința" în AI?

**NU este conștiință biologică**, ci **self-awareness + situational awareness**:

- ✅ **Conștiință de SINE** (Self-awareness): Agentul știe cine este, ce date are, ce nu știe, ce trebuie să facă
- ✅ **Conștiință de STARE** (State awareness): Agentul știe ce s-a schimbat în industrie, ce site-uri noi au apărut, cum s-a schimbat ranking-ul
- ✅ **Conștiință de TIMP** (Temporal awareness): Agentul știe istoric 30/90/365 zile, detectează trenduri, vede pattern-uri
- ✅ **Conștiință de OBIECTIV** (Goal awareness): Agentul știe mereu obiectivul principal, ce acțiuni sunt urgente, ce are cel mai mare impact

---

## 📦 Module Implementate

### 1. **agent_state_memory.py** - Memoria de Stare

**Funcționalități:**
- Salvează starea curentă a agentului (status, analize, schimbări)
- Gestionează schimbări detectate
- Adaugă notițe de conștiință
- Obține schimbări recente (ultimele N ore)

**Colecție MongoDB:** `agent_state_memory`

**Structură:**
```python
{
  "agent_id": "...",
  "current_status": "active|monitoring|analyzing",
  "last_analysis": {...},
  "last_org_chart": {...},
  "detected_changes": [...],
  "seo_health_score": 0-100,
  "ads_health_score": 0-100,
  "opportunity_level": 0-100,
  "risk_level": 0-100,
  "awareness_notes": [...],
  "last_update": datetime
}
```

### 2. **agent_health_score.py** - Scoruri de Sănătate

**Funcționalități:**
- Calculează **SEO Health** (0-100) bazat pe poziții Google, keywords, tendințe
- Calculează **Ads Health** (0-100) bazat pe campanii Google Ads
- Calculează **Opportunity Level** (0-100) - keywords cu potențial, competitori slabi
- Calculează **Risk Level** (0-100) - scăderi bruște, competitori noi puternici

**Colecție MongoDB:** `agent_health_scores`

**Algoritmi:**
- SEO Health: Poziție medie → scor (poziția 1 = 100, poziția 10 = 50, poziția 50+ = 0)
- Opportunity: Keywords 11-20, tendințe pozitive
- Risk: Scăderi în ranking, keywords care au scăzut mult

### 3. **agent_self_reflection.py** - Auto-Reflecție cu DeepSeek

**Funcționalități:**
- Agentul se întreabă la fiecare ciclu (12h):
  - Ce s-a schimbat în industrie?
  - Ce s-a schimbat la mine?
  - Ce ar trebui să fac?
  - Cum este progresul meu?
  - Ce mă limitează?
- Folosește DeepSeek pentru analiză profundă
- Extrage insights, recomandări, preocupări, oportunități

**Colecție MongoDB:** `agent_self_reflections`

**Prompt Structure:**
- Context agent (industrie, competitori, keywords)
- Date recente (ultimele 12-24h)
- 5 întrebări de auto-reflecție
- Răspuns structurat cu insights acționabile

### 4. **agent_awareness_feed.py** - Feed de Conștiință

**Funcționalități:**
- Log continuu de învățare
- Detectează competitori noi
- Detectează pattern-uri (keywords în creștere, tendințe)
- Detectează anomalii (scăderi bruște, schimbări neașteptate)
- Categorizează descoperiri (competitor, pattern, anomaly, trend)
- Calculează importanța (high, medium, low)

**Colecție MongoDB:** `agent_awareness_feed`

**Detecții Automate:**
- Competitori noi: Compară domenii din SERP cu competitorii cunoscuți
- Pattern-uri: Keywords care cresc constant (5+ verificări)
- Anomalii: Scăderi de peste 10 poziții între verificări

### 5. **agent_journal.py** - Jurnal Intern

**Funcționalități:**
- Jurnal intern pentru fiecare agent
- Intrări zilnice cu descoperiri, observații, acțiuni
- Rezumate zilnice
- Timeline organizat pe zile
- Statistici (total intrări, pe tipuri, pe zile)
- Generare rezumat memorie (ultimele 90 zile)

**Colecție MongoDB:** `agent_journal`

**Tipuri de Intrări:**
- `discovery`: Descoperiri noi
- `reflection`: Auto-reflecții
- `action`: Acțiuni efectuate
- `observation`: Observații
- `daily_summary`: Rezumat zilnic

---

## 🔌 API Endpoints

### State Management
- `GET /api/agents/{id}/conscience/state` - Obține starea curentă
- `POST /api/agents/{id}/conscience/state` - Salvează starea

### Health Scores
- `GET /api/agents/{id}/conscience/health` - Calculează și obține scorurile

### Self-Reflection
- `POST /api/agents/{id}/conscience/reflect` - Trigger auto-reflecție
- `GET /api/agents/{id}/conscience/reflection` - Obține ultima reflecție

### Awareness Feed
- `GET /api/agents/{id}/conscience/awareness?hours=24` - Obține feed-ul
- `POST /api/agents/{id}/conscience/awareness/detect` - Detectează competitori/pattern-uri/anomalii

### Journal
- `GET /api/agents/{id}/conscience/journal?days=30` - Obține jurnalul
- `POST /api/agents/{id}/conscience/journal` - Adaugă intrare

### Summary
- `GET /api/agents/{id}/conscience/summary` - Rezumat complet al conștiinței

---

## 🎨 UI Component

### **AgentConscienceTab.jsx**

**Locație:** `/frontend-pro/src/components/features/conscience/AgentConscienceTab.jsx`

**Funcționalități:**
- Afișează 4 scoruri de sănătate (SEO, Ads, Opportunity, Risk) cu indicatori vizuali
- Afișează starea curentă a agentului
- Afișează ultima auto-reflecție cu insights și recomandări
- Afișează feed-ul de conștiință (ultimele 24h)
- Afișează statistici jurnal
- Buton "Trigger Reflection" pentru auto-reflecție manuală
- Auto-refresh la fiecare 30 secunde

**Integrat în:** `AgentDetail.jsx` ca tab nou "Conscience"

---

## 🔄 Flux de Lucru

### 1. **Inițializare**
```python
# Când se creează un agent nou
state_memory = AgentStateMemory()
state_memory.save_state(agent_id, {
    "current_status": "active",
    "seo_health_score": 0,
    "ads_health_score": 0,
    ...
})
```

### 2. **Actualizare Periodică (12h)**
```python
# Auto-reflecție
reflection = AgentSelfReflection()
reflection.set_state_memory(state_memory)
reflection.perform_reflection(agent_id)

# Calculare scoruri
health_score = AgentHealthScore()
scores = health_score.calculate_all_scores(agent_id)
health_score.save_health_scores(agent_id, scores)

# Detectare conștiință
awareness = AgentAwarenessFeed()
awareness.detect_new_competitors(agent_id)
awareness.detect_patterns(agent_id)
awareness.detect_anomalies(agent_id)
```

### 3. **Jurnal Zilnic**
```python
journal = AgentJournal()
journal.add_daily_summary(agent_id, summary, highlights)
```

---

## 🎯 Ce Obții?

Agentul devine:
- ✅ **Auto-reflexiv** - se întreabă ce s-a schimbat
- ✅ **Orientat spre obiective** - știe mereu ce trebuie să facă
- ✅ **Conștient de evoluția industriei** - detectează competitori noi, pattern-uri
- ✅ **Conștient de rolul său** - știe cine este și ce responsabilități are
- ✅ **Capabil să ia decizii autonome** - bazat pe conștiința sa

---

## 📊 Exemple de Utilizare

### Trigger Auto-Reflecție
```bash
curl -X POST http://localhost:8090/api/agents/{agent_id}/conscience/reflect
```

### Obține Rezumat Complet
```bash
curl http://localhost:8090/api/agents/{agent_id}/conscience/summary
```

### Detectează Conștiință
```bash
curl -X POST http://localhost:8090/api/agents/{agent_id}/conscience/awareness/detect
```

---

## 🚀 Următorii Pași (Opțional)

1. **Scheduler Automat**: Cron job pentru auto-reflecție la fiecare 12h
2. **Alerting**: Notificări când risk_level > 70 sau opportunity_level > 80
3. **Dashboard**: Dashboard centralizat pentru toți agenții
4. **Learning**: Îmbunătățire algoritmi bazat pe feedback
5. **Export**: Export jurnal și reflecții în PDF/Excel

---

**Status**: ✅ **PRODUCTION READY** - Sistem complet de conștiință implementat

