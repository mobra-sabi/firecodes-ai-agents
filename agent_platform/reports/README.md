# 📊 Generator Rapoarte CEO Workflow

Generator complet de rapoarte profesionale pentru CEO Workflow V2.0.

## 🎯 Funcționalități

- ✅ Parsează log-uri workflow și extrage date structurate
- ✅ Generează rapoarte Markdown profesionale
- ✅ Export JSON pentru integrare API
- ✅ Generează organigramă PNG (master-slave agents)
- ✅ Export PDF (opțional, cu weasyprint)
- ✅ API endpoints pentru integrare dashboard
- ✅ Dashboard React pentru vizualizare rapoarte

## 📁 Structură

```
reports/
├── parser/
│   └── log_parser.py          # Parser pentru log-uri
├── generator/
│   └── report_generator.py    # Generator principal
├── templates/
│   └── report_template.md      # Template Markdown
├── utils/
│   └── pdf_export.py          # Export PDF
├── output/                     # Rapoarte generate
└── generate_report.py          # Script CLI
```

## 🚀 Utilizare

### 1. Generare raport din log

```bash
cd /srv/hf/ai_agents/agent_platform/reports
python3 generate_report.py /path/to/log_file.txt
```

### 2. Cu director custom

```bash
python3 generate_report.py /path/to/log_file.txt --output-dir custom_output
```

### 3. Generare PDF

```bash
python3 utils/pdf_export.py output/protectiilafoc.ro_report.md
```

## 📋 Format Log Așteptat

Log-ul trebuie să conțină:

```
🎯 SITE TESTAT: https://example.com
📅 DATA: 2025-11-13
⏱️  DURATĂ TOTALĂ: 4.20 minute

1️⃣ AGENT MASTER CREAT:
   Domain: example.com
   Status: validated
   Chunks Indexed: 470

2️⃣ SLAVE AGENTS CREAȚI:
   1. competitor1.com
      - Status: validated
      - Chunks: 869
```

## 🔌 API Endpoints

### Lista rapoarte

```bash
GET /api/reports/
```

### Obține raport

```bash
GET /api/reports/{domain}?format=json|markdown|pdf|graph
```

### Generează raport din agent

```bash
POST /api/reports/generate/{agent_id}
```

## 📊 Formate Generate

### Markdown (`{domain}_report.md`)

Raport complet cu:
- Metadate & versiuni
- Rezultate master/slave
- Calitate & acoperire
- SEO Intelligence
- Content Gap
- Performanță sistem
- Next Best Actions
- Organigramă
- Alerte & probleme
- Audit & diferențe

### JSON (`{domain}_report.json`)

```json
{
  "run_id": "...",
  "site": "https://...",
  "agents": {
    "master": {...},
    "slaves": [...]
  },
  "seo": {
    "keywords": 85,
    "opportunities": [...]
  },
  "actions": [...]
}
```

### PNG Graph (`{domain}_graph.png`)

Organigramă vizuală master-slave cu:
- Noduri colorate (master=albastru, slaves=violet)
- Muchii cu direcție
- Labels cu număr chunks

### JSON Graph (`{domain}_graph.json`)

```json
{
  "nodes": [...],
  "edges": [...]
}
```

## 🛠️ Dependențe

```bash
pip install networkx matplotlib markdown weasyprint
```

## 📝 Exemple

### Python

```python
from reports.generator.report_generator import ReportGenerator

generator = ReportGenerator("log.txt", "output/")
results = generator.generate_all()

print(f"Markdown: {results['markdown']}")
print(f"JSON: {results['json']}")
print(f"Graph: {results['graph']}")
```

### API Integration

```javascript
// Frontend React
const { data } = await api.get('/api/reports/')
const reports = data.reports

// Download PDF
const response = await api.get(`/api/reports/${domain}?format=pdf`, {
  responseType: 'blob'
})
```

## 🎨 Dashboard Integration

Pagina `/reports` în frontend React:
- Listă toate rapoartele
- Butoane download (JSON, MD, PDF, PNG)
- Preview grafic
- Integrare cu agenți

## 📈 Extensii Viitoare

- [ ] Export Excel/CSV
- [ ] Email automation
- [ ] Scheduled reports
- [ ] Comparison reports (vs. runda anterioară)
- [ ] Interactive charts (Plotly)

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'parser'"

```bash
export PYTHONPATH=/srv/hf/ai_agents/agent_platform/reports:$PYTHONPATH
```

### "networkx/matplotlib nu sunt instalate"

```bash
pip install networkx matplotlib
```

### PDF generation fails

```bash
pip install weasyprint markdown
# Pe Ubuntu/Debian: sudo apt-get install libcairo2 libpango-1.0-0
```

## 📞 Support

Pentru probleme sau întrebări, verifică:
- Log-urile în `output/`
- API responses în browser DevTools
- MongoDB pentru date agenți

