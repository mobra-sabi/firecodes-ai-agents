# 📘 RAPORT MASTER BUILD — v1.3

**Run ID:** 0428e64bb063  
**Start:** 2025-11-13T14:40:00.000Z · **Finish:** None · **Durată:** 3.62 minute

---

## 0️⃣ Metadate & Versiuni

- **Site:** https://tehnica-antifoc.ro
- **Orchestrator:** CEO Workflow V2.0
- **LLM:** Qwen/Kimi
- **Embeddings:** qwen-embed (dim=768)
- **Crawl:** depth=3, rate=3 req/s, robots=da
- **User-Agent:** adbrain/1.0

---

## 1️⃣ Rezultate

- **Master Agent:** validated · **0 chunks**
- **Slave Agents:** **3** (3 validate, 0 în progres)
- **Total Chunks:** **1084** (Master: 0 · Slaves: 1084)

---

## 2️⃣ Calitate & Acoperire

- **Pagini descoperite:** N/A · **indexate:** N/A · **succes:** N/A%
- **Erori:** 0 (N/A) — **retry reușit:** N/A
- **Chunk size (chars):** p50=920 · p90=1240
- **Qdrant:** collection `agent_tehnica-antifoc.ro` · **vectors=1084** · HNSW(M=16, ef=128)

---

## 3️⃣ SEO Intelligence (Sinteză)

- **Keywords analizate:** 85
- **Intent distribuție:** info 48%, comm 32%, trans 20%

### **Top Oportunități (Top 5)**

1. **"vopsea intumescentă H120"** — score **82** (vol ~1200, diff 38) — *transactional*
2. **"protecție pasivă la foc structuri metalice"** — score **77** (vol ~850, diff 42) — *commercial*
3. **"clasificare rezistență la foc R60 R120"** — score **74** (vol ~650, diff 35) — *informational*


### **Poziții Master pe Keywords Cheie**

| Keyword | Master | {{competitor_1}} | {{competitor_2}} | {{competitor_3}} |
|---------|--------:|----------------:|-----------------:|-----------------:|
{{#each keyword_rankings}}
| {{keyword}} | **{{master_rank}}** | {{rank_1}} | {{rank_2}} | {{rank_3}} |
{{/each}}

---

## 4️⃣ Content Gap (Top 5 Recomandări)

- [ ] **Ghid:** "Cum alegi vopseaua intumescentă (H60/H120) + normative" (2,000-2,500w) — *High opportunity score*
- [ ] **Studiu de caz:** "Protecția la foc pentru hale metalice — cost & timpi" (1,500w) — *Competitor gap*


---

## 5️⃣ Performanță Sistem

- **Crawl:** 65s · **Split:** 18s · **Embedding:** 87s · **Upsert:** 21s · **SERP:** 34s
- **Latență RAG p95:** 112ms
- **GPU util medie:** 63% · **VRAM peak:** 19.2GB
- **Cost API extern:** $0.00 (self-host)

---

## 6️⃣ Next Best Actions (ICE Score)

1. **Publică ghidul 'vopsea intumescentă H120'** — Impact **High** · Effort **Low** · **ICE 9.1**
2. **Optimiză pagina 'protecție pasivă' cu secțiune normative** — Impact **High** · Effort **Medium** · **ICE 8.6**


---

## 7️⃣ Organigramă & Hartă Competitori

- **Noduri:** 4 (1 master + 3 slaves) · **Muchii:** N/A
- **Grafic:** `reports/{{domain}}_graph.png` · **JSON:** `reports/{{domain}}_graph.json`

### **Structură Master-Slave**

```
tehnica-antifoc.ro
├── {{slave_1_domain}} ({{slave_1_chunks}} chunks, {{slave_1_status}})
├── {{slave_2_domain}} ({{slave_2_chunks}} chunks, {{slave_2_status}})
{{#if slave_3_domain}}
├── {{slave_3_domain}} ({{slave_3_chunks}} chunks, {{slave_3_status}})
{{/if}}
{{#if slave_4_domain}}
├── {{slave_4_domain}} ({{slave_4_chunks}} chunks, {{slave_4_status}})
{{/if}}
{{#if slave_5_domain}}
└── {{slave_5_domain}} ({{slave_5_chunks}} chunks, {{slave_5_status}})
{{/if}}
```

---

## 8️⃣ Alerte & Probleme



{{#if errors}}
### **Erori Detectate**

{{#each errors}}
- ❌ {{this}}
{{/each}}
{{/if}}

---

## 9️⃣ Audit & Diferențe vs. Runda Anterioară

- **+0** slaves validat
- **+0** chunks
- **Master rank mediu:** N/A (N/A)
- **Config schimbată:** N/A

---

## 🔟 Faze Completate

✅ **Phase 1**
✅ **Phase 2**
✅ **Phase 3**
✅ **Phase 4**
✅ **Phase 5**
✅ **Phase 6**
✅ **Phase 7**
✅ **Phase 8**


---

**Generat automat de:** CEO Workflow V2.0 Report Generator  
**Data generării:** 2025-11-13T14:42:27.065324

