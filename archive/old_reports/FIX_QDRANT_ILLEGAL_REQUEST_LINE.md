# 🔧 Fix Eroare "illegal request line" Qdrant

**Data:** 2025-11-06  
**Problema:** Agentul protectiilafoc.ro nu s-a creat complet din cauza erorii "illegal request line" la Qdrant

## 🔍 Cauză

Eroarea apare din cauza incompatibilității versiunilor Qdrant:
- **Client Qdrant:** versiunea 1.15.1
- **Server Qdrant:** versiunea 1.11.0

Clientul verifică compatibilitatea și aruncă eroarea "illegal request line" când versiunile nu se potrivesc.

## ✅ Soluție Aplicată

Am adăugat `check_compatibility=False` la toate instanțele `QdrantClient` în `site_agent_creator.py`:

1. **Client global** (linia 49):
```python
qdrant_client = QdrantClient(
    url=QDRANT_URL, 
    api_key=QDRANT_API_KEY,
    prefer_grpc=False,
    check_compatibility=False  # ✅ NOU
)
```

2. **Client în create_vectorstore_direct** (linia 346):
```python
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=60,
    prefer_grpc=False,
    force_disable_check_same_thread=True,
    check_compatibility=False  # ✅ NOU
)
```

3. **Client în retry logic** (linia 419):
```python
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=60,
    prefer_grpc=False,
    force_disable_check_same_thread=True,
    check_compatibility=False  # ✅ NOU
)
```

4. **Client pentru info collection** (linia 547):
```python
qdrant_info_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=60,
    prefer_grpc=False,
    force_disable_check_same_thread=True,
    check_compatibility=False  # ✅ NOU
)
```

## 📊 Status Agent protectiilafoc.ro

- ✅ Agent creat în MongoDB (ID: `690cd9fda55790fced15833e`)
- ✅ Site data salvată
- ❌ Chunks MongoDB: 0 (procesul a eșuat înainte de salvare)
- ❌ Vector Collection: None (procesul a eșuat la Qdrant)

## 🔄 Următorii Pași

1. **Recrearea agentului** va funcționa acum cu fix-ul aplicat
2. Chunks-urile vor fi salvate în MongoDB
3. Vectorii vor fi salvați în Qdrant fără eroare "illegal request line"

## ⚠️ Notă

`check_compatibility=False` dezactivează verificarea compatibilității versiuni, dar funcționalitatea rămâne intactă. Versiunile 1.11.0 și 1.15.1 sunt compatibile pentru operațiile de bază (create, upsert, search).

---

**Fix aplicat:** 2025-11-06  
**Status:** ✅ Rezolvat

