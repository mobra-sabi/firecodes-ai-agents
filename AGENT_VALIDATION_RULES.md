# 📋 REGULI DE VALIDARE AGENȚI

## ✅ CERINȚE MINIME PENTRU UN AGENT VALID

Un agent trebuie să îndeplinească **TOATE** cerințele următoare pentru a fi acceptat în sistem:

### 1. **Status** ✅
- `status` = `"ready"`

### 2. **Validare** ✅  
- `validation_passed` = `True`

### 3. **Conținut Minim** ✅
- Minimum **1 chunk** de conținut în MongoDB (`site_content`)
- SAU minimum **1 vector** în Qdrant

### 4. **Informații de Bază** ✅
- `domain` - prezent și valid
- `site_url` - prezent și valid
- `name` - prezent

### 5. **Componente Active** ✅
- `qwen_memory_enabled` = `True`
- `long_chain_integrated` = `True`  
- `langchain_enabled` = `True`

---

## ❌ CE SE ÎNTÂMPLĂ DACĂ UN AGENT NU E VALID?

1. **Agentul e șters automat** din MongoDB
2. **Conținutul asociat e șters** 
3. **Colecția Qdrant e ștearsă**
4. **Nu apare în interfață** (dropdown, liste)
5. **Utilizatorul primește eroare** cu detalii clare

---

## 🎯 FILTRE ACTIVE

### API `/api/agents`
Returnează DOAR agenți cu:
```json
{
  "validation_passed": true,
  "status": "ready"
}
```

### UI Dropdown
Afișează DOAR agenți validați 100%

---

## 🔄 PROCES DE CREARE

```
1. Scraping site → 
2. Generare vectori (GPU) → 
3. Configurare componente → 
4. VALIDARE STRICTĂ → 
5. ✅ SALVARE (dacă valid) SAU ❌ ȘTERGERE (dacă invalid)
```

---

## ✅ AGENȚI ACTUALI VALIDAȚI

Toți agenții din sistem au fost curățați și filtrați:

1. **coneco.ro** ✅
2. **firestopping.ro** ✅
3. **ropaintsolutions.ro** ✅
4. **terrageneralcontractor.ro** ✅

**Total: 4 agenți conformi 100%**

---

*Última actualizare: $(date)*
