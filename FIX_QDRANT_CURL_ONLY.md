# FIX QDRANT - FOLOSEȘTE DOAR CURL

## Problema

Crearea agentului eșuează cu eroarea "illegal request line" când se încearcă salvarea vectorilor în Qdrant folosind `QdrantClient`. Această eroare apare consistent la pasul de upsert vectori.

## Cauza

`QdrantClient` (din biblioteca `qdrant-client`) folosește `httpx` sau alte biblioteci HTTP care au probleme de compatibilitate cu serverul Qdrant în unele configurații.

## Soluție

Folosește **DOAR `curl` subprocess** pentru TOATE operațiile Qdrant:
1. Creare colecție
2. Upsert puncte
3. Verificare status

## Implementare

Funcția `create_vectorstore_with_curl()` din `site_agent_creator.py` trebuie modificată să folosească DOAR `curl` subprocess pentru TOATE operațiile Qdrant, fără nicio referință la `QdrantClient`.

## Pașii detaliat

### 1. Generează embeddings (PĂSTREAZĂ - FUNCȚIONEAZĂ)
```python
embeddings_list = []
for i, chunk in enumerate(chunks_for_qdrant):
    embedding = embeddings.embed_query(chunk)
    embeddings_list.append({
        'id': i,
        'vector': embedding,
        'payload': {...}
    })
```

### 2. Creează colecție cu curl (ÎN LOC DE QdrantClient)
```python
create_payload = {
    "vectors": {
        "size": 1024,
        "distance": "Cosine"
    }
}

with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
    json.dump(create_payload, f)
    temp_file = f.name

try:
    subprocess.run([
        'curl', '-X', 'PUT',
        f'{qdrant_url}/collections/{collection_name}',
        '-H', 'Content-Type: application/json',
        '--data-binary', f'@{temp_file}'
    ], timeout=30)
finally:
    os.unlink(temp_file)
```

### 3. Upsert puncte cu curl (ÎN LOC DE QdrantClient.upsert)
```python
upsert_payload = {
    "points": [
        {"id": item['id'], "vector": item['vector'], "payload": item['payload']}
        for item in batch
    ]
}

with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
    json.dump(upsert_payload, f)
    temp_file = f.name

try:
    subprocess.run([
        'curl', '-X', 'PUT',
        f'{qdrant_url}/collections/{collection_name}/points',
        '-H', 'Content-Type: application/json',
        '--data-binary', f'@{temp_file}'
    ], timeout=60)
finally:
    os.unlink(temp_file)
```

### 4. Verifică status cu curl (ÎN LOC DE QdrantClient.get_collection)
```python
result = subprocess.run([
    'curl', '-s',
    f'{qdrant_url}/collections/{collection_name}'
], capture_output=True, text=True, timeout=10)

if result.returncode == 0:
    data = json.loads(result.stdout)
    points_count = data.get('result', {}).get('points_count', 0)
```

## IMPORTANT

- **NU folosi `QdrantClient` DELOC**
- **NU folosi `qdrant_client.models`**
- **NU folosi `requests` pentru Qdrant**
- Folosește DOAR `subprocess.run` cu `curl`

## Testare

După modificare, testează crearea unui agent nou. Procesul ar trebui să finalizeze fără eroarea "illegal request line".

