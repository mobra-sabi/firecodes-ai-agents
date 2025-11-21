# 📘 RAPORT MASTER BUILD — v1.3

**Run ID:** {{run_id}}  
**Start:** {{start_time}} · **Finish:** {{finish_time}} · **Durată:** {{duration}}

---

## 0️⃣ Metadate & Versiuni

- **Site:** {{site_url}}
- **Orchestrator:** CEO Workflow V2.0
- **LLM:** {{llm_model}}
- **Embeddings:** {{embed_model}} (dim={{embed_dim}})
- **Crawl:** depth={{crawl_depth}}, rate={{crawl_rate}} req/s, robots={{robots_respected}}
- **User-Agent:** {{user_agent}}

---

## 1️⃣ Rezultate

- **Master Agent:** {{master_status}} · **{{master_chunks}} chunks**
- **Slave Agents:** **{{slave_count}}** ({{validated_slaves}} validate, {{created_slaves}} în progres)
- **Total Chunks:** **{{total_chunks}}** (Master: {{master_chunks}} · Slaves: {{slave_chunks}})

---

## 2️⃣ Calitate & Acoperire

- **Pagini descoperite:** {{pages_found}} · **indexate:** {{pages_indexed}} · **succes:** {{success_rate}}%
- **Erori:** {{error_count}} ({{error_breakdown}}) — **retry reușit:** {{retry_success}}
- **Chunk size (chars):** p50={{chunk_p50}} · p90={{chunk_p90}}
- **Qdrant:** collection `{{qdrant_collection}}` · **vectors={{vector_count}}** · HNSW(M={{hnsw_m}}, ef={{hnsw_ef}})

---

## 3️⃣ SEO Intelligence (Sinteză)

- **Keywords analizate:** {{keywords_count}}
- **Intent distribuție:** info {{intent_info}}%, comm {{intent_comm}}%, trans {{intent_trans}}%

### **Top Oportunități (Top 5)**

{{#each opportunities}}
{{@index_plus_one}}. **"{{term}}"** — score **{{score}}** (vol ~{{volume}}, diff {{difficulty}}) — *{{intent}}*
{{/each}}

### **Poziții Master pe Keywords Cheie**

| Keyword | Master | {{competitor_1}} | {{competitor_2}} | {{competitor_3}} |
|---------|--------:|----------------:|-----------------:|-----------------:|
{{#each keyword_rankings}}
| {{keyword}} | **{{master_rank}}** | {{rank_1}} | {{rank_2}} | {{rank_3}} |
{{/each}}

---

## 4️⃣ Content Gap (Top 5 Recomandări)

{{#each recommendations}}
- [ ] **{{type}}:** "{{title}}" ({{word_count}}w) — *{{reason}}*
{{/each}}

---

## 5️⃣ Performanță Sistem

- **Crawl:** {{crawl_duration}}s · **Split:** {{split_duration}}s · **Embedding:** {{embed_duration}}s · **Upsert:** {{upsert_duration}}s · **SERP:** {{serp_duration}}s
- **Latență RAG p95:** {{rag_latency_p95}}ms
- **GPU util medie:** {{gpu_utilization}}% · **VRAM peak:** {{vram_peak}}GB
- **Cost API extern:** ${{api_cost}} ({{cost_breakdown}})

---

## 6️⃣ Next Best Actions (ICE Score)

{{#each actions}}
{{@index_plus_one}}. **{{title}}** — Impact **{{impact}}** · Effort **{{effort}}** · **ICE {{ice}}**
{{/each}}

---

## 7️⃣ Organigramă & Hartă Competitori

- **Noduri:** {{node_count}} (1 master + {{slave_count}} slaves) · **Muchii:** {{edge_count}}
- **Grafic:** `reports/{{domain}}_graph.png` · **JSON:** `reports/{{domain}}_graph.json`

### **Structură Master-Slave**

```
{{master_domain}}
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

{{#each alerts}}
- ⚠️ **{{type}}:** {{message}} ({{count}})
{{/each}}

{{#if errors}}
### **Erori Detectate**

{{#each errors}}
- ❌ {{this}}
{{/each}}
{{/if}}

---

## 9️⃣ Audit & Diferențe vs. Runda Anterioară

- **+{{diff_slaves}}** slaves validat
- **+{{diff_chunks}}** chunks
- **Master rank mediu:** {{rank_change}} ({{rank_trend}})
- **Config schimbată:** {{config_changes}}

---

## 🔟 Faze Completate

{{#each phases}}
✅ **{{this}}**
{{/each}}

---

**Generat automat de:** CEO Workflow V2.0 Report Generator  
**Data generării:** {{generated_at}}

