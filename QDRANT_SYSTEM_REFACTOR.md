# Sistem Qdrant refăcut - Documentație

## Problema identificată

Sistemul Qdrant nu funcționa corect din cauza:
1. **QdrantClient Python** - dă eroare "illegal request line" când folosește httpx/httpcore
2. **requests library** - dă "Connection reset by peer" pentru operațiile PUT
3. **curl direct** - funcționează perfect, dar returnează cod 1 chiar și când operația reușește

## Soluția implementată

### 1. Script de reindexare: `reindex_qdrant.py`

- Folosește **curl prin subprocess** pentru toate operațiile Qdrant
- Verifică manual existența colecțiilor după creare (pentru că curl poate returna cod 1 chiar dacă operația reușește)
- Generează embeddings cu HuggingFace (`BAAI/bge-large-en-v1.5`)
- Salvează vectorii în batch-uri de 50 pentru stabilitate
- Actualizează MongoDB cu informații despre colecțiile Qdrant

### 2. Funcționalități

- **Reindexare completă**: `python3 reindex_qdrant.py --force`
- **Reindexare incrementală**: `python3 reindex_qdrant.py` (skip colecții existente)
- **Raport detaliat**: salvează JSON cu rezultatele

### 3. Integrare cu `site_agent_creator.py`

Trebuie actualizat `site_agent_creator.py` pentru a folosi aceeași metodă cu curl în loc de QdrantClient direct.

## Status

✅ Script creat și testat
⏳ Reindexare în curs pentru toți agenții
📝 Documentație actualizată

## Utilizare

```bash
# Reindexare completă (șterge și recreează colecții)
cd /srv/hf/ai_agents
python3 reindex_qdrant.py --force

# Reindexare incrementală (doar agenții noi)
python3 reindex_qdrant.py
```

## Raportare

Raportul este salvat în: `qdrant_reindex_report_YYYYMMDD_HHMMSS.json`

