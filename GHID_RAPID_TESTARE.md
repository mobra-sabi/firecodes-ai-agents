# 🧪 Ghid Rapid de Testare - LangChain UI

## ⚠️ IMPORTANT: Cum să vezi butoanele LangChain

Butoanele LangChain apar DOAR când ai selectat un agent!

### Pași pentru a vedea butoanele:

1. **Accesează interfața:**
   ```
   http://100.66.157.27:8083
   ```

2. **Selectează un agent:**
   - În panoul din STÂNGA, selectează un agent din dropdown
   - Agentul selectat devine "Agent Master"
   - Panoul din DREAPTA se va actualiza automat

3. **Găsește butoanele LangChain:**
   - În panoul din DREAPTA, secțiunea "🎯 Strategie Competitivă"
   - Scroll down până vezi secțiunea "🔗 Lanțuri LangChain"
   - Acolo vei vedea 3 butoane:
     - 📊 Analiză Site (Qwen + DeepSeek)
     - 💼 Strategie Industrie (DeepSeek)
     - 🎯 Plan Acțiuni (Qwen)

## 🔧 Fix pentru "illegal request line"

Eroarea apare la crearea vectorilor în Qdrant. Am verificat codul și este configurat corect cu HTTP.

### Dacă tot apare eroarea:

1. **Verifică Qdrant:**
   ```bash
   curl http://localhost:6333/collections
   ```

2. **Restartează Qdrant dacă e necesar:**
   ```bash
   # Pe serverul viezure
   sudo systemctl restart qdrant
   ```

3. **Verifică logurile:**
   ```bash
   tail -f /srv/hf/ai_agents/server_8083.log | grep -i qdrant
   ```

## 📋 Testare Completă

### Test 1: Verifică că butoanele apar

1. Accesează: `http://100.66.157.27:8083`
2. Selectează un agent din dropdown (stânga)
3. Verifică că în panoul din dreapta apare:
   - Informații despre agent
   - Secțiunea "🎯 Strategie Competitivă"
   - Secțiunea "🔗 Lanțuri LangChain" cu 3 butoane

### Test 2: Rulează un lanț LangChain

1. Click pe butonul **"🎯 Plan Acțiuni (Qwen)"** (cel mai rapid)
2. Confirmă dacă apare dialogul
3. Așteaptă execuția (30 secunde - 1 minut)
4. Verifică că apare rezultatul în secțiunea "Rezultat Lanț"

### Test 3: Testează crearea agentului

1. Introdu un URL nou în câmpul de creare agent
2. Click pe "Creează Agent Nou"
3. Monitorizează progresul în log
4. Dacă apare "illegal request line", verifică Qdrant

## 🐛 Troubleshooting

### Problema: Nu văd butoanele LangChain

**Soluție:**
- ✅ Asigură-te că ai selectat un agent din dropdown
- ✅ Fă refresh la pagină (F5 sau Ctrl+R)
- ✅ Verifică că JavaScript este activat în browser
- ✅ Deschide Console-ul browserului (F12) și verifică erori

### Problema: "illegal request line" la creare agent

**Soluție:**
- ✅ Verifică că Qdrant rulează: `curl http://localhost:6333/collections`
- ✅ Verifică logurile serverului pentru detalii
- ✅ Restartează serverul dacă e necesar

### Problema: Butoanele nu funcționează

**Soluție:**
- ✅ Verifică Console-ul browserului (F12) pentru erori JavaScript
- ✅ Verifică că serverul răspunde: `curl http://100.66.157.27:8083/health`
- ✅ Verifică Network tab în browser pentru request-uri eșuate

## 📸 Screenshot-uri Așteptate

### Când un agent este selectat, ar trebui să vezi:

```
┌─────────────────────────────────────┐
│  👑 Agent Master                    │
├─────────────────────────────────────┤
│  🤖 Agent Activ: [Nume Agent]      │
│  Domeniu: [domain.ro]               │
│                                     │
│  🎯 Strategie Competitivă           │
│  ┌───────────────────────────────┐ │
│  │ 🤖 Analizează Agent cu        │ │
│  │    DeepSeek                   │ │
│  │ 🚀 Indexează Industria        │ │
│  │                                │ │
│  │ 🔗 Lanțuri LangChain          │ │
│  │ ┌───────────────────────────┐ │ │
│  │ │ 📊 Analiză Site          │ │ │
│  │ │ 💼 Strategie Industrie    │ │ │
│  │ │ 🎯 Plan Acțiuni          │ │ │
│  │ └───────────────────────────┘ │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

## ✅ Checklist Rapid

- [ ] Accesez `http://100.66.157.27:8083`
- [ ] Selectez un agent din dropdown
- [ ] Văd secțiunea "🔗 Lanțuri LangChain"
- [ ] Văd cele 3 butoane LangChain
- [ ] Click pe un buton funcționează
- [ ] Rezultatul apare corect

## 🆘 Dacă tot nu funcționează

1. **Verifică serverul:**
   ```bash
   curl http://100.66.157.27:8083/health
   ```

2. **Verifică logurile:**
   ```bash
   tail -50 /srv/hf/ai_agents/server_8083.log
   ```

3. **Contactează pentru suport** cu:
   - Screenshot-ul paginii
   - Mesajele din Console (F12)
   - Logurile serverului

