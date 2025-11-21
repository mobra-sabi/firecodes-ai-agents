# 📊 LOGICA DE BUSINESS - AI Agent Platform

## 🎯 CE FACE APLICAȚIA

Aplicația creează și gestionează **agenți AI** care analizează site-uri web pentru **competitive intelligence** și **SEO**.

---

## 🔄 WORKFLOW COMPLET (8 Faze)

### **FAZA 1: Creare Agent Master**
**Input:** URL site (ex: `https://tehnica-antifoc.ro`)
**Proces:**
- Crawl site-ul complet
- Extrage text din toate paginile
- Creează chunks (bucăți de text)
- Generează embeddings cu GPU (Qwen)
- Salvează în Qdrant (vector database)

**Output:** Agent master cu memorie completă despre site

---

### **FAZA 2: Integrare LangChain**
- Agentul devine "inteligent" - poate răspunde la întrebări
- Memorie conversațională
- RAG (Retrieval Augmented Generation)

---

### **FAZA 3: DeepSeek Identificare**
- DeepSeek analizează agentul master
- Devine "vocea" agentului în chat cu admin
- Expert în domeniul site-ului

---

### **FAZA 4: Descompunere Subdomenii + Keywords**
- DeepSeek descompune site-ul în subdomenii
- Pentru fiecare subdomeniu: generează 10-15 keywords
- Keywords sunt optimizate pentru Google Search

**Exemplu:**
- Subdomeniu: `/servicii/protectie-foc`
- Keywords: "protecție pasivă la foc", "vopsea intumescentă H120", etc.

---

### **FAZA 5: Google Search Competitori**
- Pentru fiecare keyword: caută în Google
- Găsește top 10-15 site-uri competitori
- Elimină duplicate (dar notează pozițiile)
- Salvează ranking-ul master vs competitori

**Output:** Listă de competitori descoperiți

---

### **FAZA 6: Hartă Competitivă CEO**
- Creează hartă vizuală: keywords × site-uri
- Notează poziția master pe fiecare keyword
- Calculează oportunități SEO
- Generează raport CEO

---

### **FAZA 7: Transformare Competitori → Agenți AI**
- Pentru fiecare competitor găsit:
  - Crawl site-ul competitor
  - Creează chunks + embeddings
  - Transformă în agent AI (slave)
- Procesare paralelă pe GPU-uri

**Output:** Master agent + N slave agents (competitori)

---

### **FAZA 8: Organogramă + Învățare**
- Master agent învață din slave agents
- Creează organogramă ierarhică
- Generează raport competitive intelligence
- Recomandări strategice

---

## 💼 VALOARE DE BUSINESS

### **Pentru CEO:**
1. **Vizibilitate completă** - știi exact unde ești vs competitori
2. **Oportunități SEO** - keywords unde poți crește rapid
3. **Strategie clară** - "Fă aceste 5 lucruri în următoarele 30 zile"
4. **Monitorizare continuă** - vezi când competitori se schimbă

### **Pentru Business:**
- **ROI clar** - ce keywords aduc cel mai mult trafic
- **Content gap** - ce conținut lipsă vs competitori
- **Pozitionare** - unde ești lider, unde ești în urmă

---

## 🎮 CUM SE FOLOSEȘTE (UI/UX)

### **1. Dashboard**
- **Vizualizează:** Statistici globale (master, slave, keywords, chunks)
- **Acțiuni:** Buton "Create New Master Agent"

### **2. Agents Page**
- **Vizualizează:** Listă toți agenții (master + slave)
- **Acțiuni:**
  - "New Master Agent" → Modal cu formular
  - Click pe agent → Detalii complete
  - Butoane: "View Report", "Restart", "Delete"

### **3. Agent Detail Page**
- **Vizualizează:**
  - Informații agent (chunks, keywords, status)
  - Slave agents (dacă e master)
  - Organogramă vizuală
- **Acțiuni:**
  - "Start CEO Workflow" → Pornește fazele 4-8
  - "Generate Report" → Creează raport PDF/Markdown
  - "View in Qdrant" → Explorează embeddings

### **4. Reports Page**
- **Vizualizează:** Listă rapoarte generate
- **Acțiuni:**
  - Download PDF
  - Download JSON
  - Download Graph PNG
  - "Generate New Report"

---

## 🔘 BUTOANE NECESARE

### **Dashboard:**
1. ✅ "Create New Master Agent" (modal)
2. ✅ "View All Agents" (link)
3. ✅ "View Reports" (link)
4. ⚠️ "Refresh Stats" (manual refresh)
5. ⚠️ "Export Data" (CSV/JSON)

### **Agents Page:**
1. ✅ "New Master Agent" (modal)
2. ⚠️ "Filter by Type" (master/slave)
3. ⚠️ "Sort by" (date, chunks, status)
4. ⚠️ Acțiuni pe fiecare agent card:
   - "View Details"
   - "Start Workflow"
   - "Generate Report"
   - "Delete"

### **Agent Detail:**
1. ⚠️ "Start CEO Workflow" (fazele 4-8)
2. ⚠️ "Generate Report"
3. ⚠️ "View Organogram"
4. ⚠️ "Chat with Agent" (DeepSeek)
5. ⚠️ "Export Data"

### **Reports:**
1. ✅ Download buttons (PDF, JSON, PNG)
2. ⚠️ "Generate New Report"
3. ⚠️ "Compare Reports"

---

## 📋 ENDPOINT-URI API

### **Agents:**
- `GET /agents` - Listă toți agenții
- `GET /agents/{id}` - Detalii agent
- `GET /agents/{id}/slaves` - Slave agents
- `POST /agents` - Creează agent nou
- `DELETE /agents/{id}` - Șterge agent

### **Workflow:**
- `POST /workflow/start` - Pornește CEO workflow
- `GET /workflow/progress` - Status workflow
- `POST /workflow/stop` - Oprește workflow

### **Reports:**
- `GET /api/reports/` - Listă rapoarte
- `GET /api/reports/{domain}` - Download raport
- `POST /api/reports/generate/{agent_id}` - Generează raport

### **Stats:**
- `GET /stats` - Statistici globale

---

## 🎯 FLUXUL COMPLET (User Journey)

1. **User deschide Dashboard**
   - Vezi statistici
   - Click "Create New Master Agent"

2. **Modal apare:**
   - Input: URL site
   - Click "Start Workflow"
   - Backend pornește Faza 1-3

3. **Dashboard se actualizează:**
   - Agent apare în listă
   - Status: "Indexing..." → "Validated"

4. **User click pe agent:**
   - Vezi detalii
   - Click "Start CEO Workflow"
   - Backend pornește Faza 4-8

5. **Workflow rulează:**
   - Progress bar în UI
   - Log-uri live
   - Slave agents se creează

6. **Workflow complet:**
   - Organogramă generată
   - Raport disponibil
   - User poate download raport

---

## ✅ CE AM LIVRAT ACUM

### **Funcțional:**
- ✅ Dashboard cu statistici live
- ✅ Listă agenți cu căutare
- ✅ Pagină rapoarte
- ✅ Responsive design
- ✅ Auto-refresh

### **Lipsesc (de adăugat):**
- ⚠️ Modal "Create Agent" (butonul există dar nu face nimic)
- ⚠️ Buton "Start Workflow" pe agent detail
- ⚠️ Progress tracking pentru workflow
- ⚠️ Acțiuni pe agenți (delete, restart)
- ⚠️ Chat cu agent (DeepSeek)
- ⚠️ Export funcționalități

---

## 🚀 NEXT STEPS

1. **Adaugă Modal Create Agent** → Formular cu URL input
2. **Adaugă Workflow Start** → Buton care pornește CEO workflow
3. **Adaugă Progress Tracking** → WebSocket pentru log-uri live
4. **Adaugă Acțiuni** → Delete, Restart, Export pe fiecare agent
5. **Adaugă Chat** → Interfață DeepSeek pentru fiecare agent

