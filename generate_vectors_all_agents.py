#!/usr/bin/env python3
"""Generare vectori GPU pentru toți cei 3 agenți"""

import torch
from pymongo import MongoClient
from bson import ObjectId
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import time

# Setup
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🎮 Device: {device}")
if device == "cuda":
    print(f"   GPU: {torch.cuda.get_device_name(0)}")

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["ai_agents_db"]
qdrant_client = QdrantClient(url="http://127.0.0.1:6333", check_compatibility=False)

print("\n📦 Loading model...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)
print(f"✅ Model loaded on {device}")

agents = [
    {"id": "6910d519c5a351f416f076a3", "domain": "ropaintsolutions.ro"},
    {"id": "6910d536c5a351f416f077e6", "domain": "firestopping.ro"},
    {"id": "6910d564c5a351f416f077ed", "domain": "coneco.ro"}
]

print("\n╔══════════════════════════════════════════════════════════════════════╗")
print("║  🚀 GENERARE VECTORI GPU PENTRU TOȚI AGENȚII                        ║")
print("╚══════════════════════════════════════════════════════════════════════╝")

total_vectors = 0
start_total = time.time()

for idx, agent_info in enumerate(agents, 1):
    agent_id = agent_info["id"]
    domain = agent_info["domain"]
    collection_name = f"agent_{agent_id}"
    
    print(f"\n{'='*70}")
    print(f"🚀 AGENT {idx}/3: {domain}")
    print(f"   ID: {agent_id}")
    print(f"{'='*70}")
    
    # Get content
    contents = list(db.site_content.find({"agent_id": ObjectId(agent_id)}))
    
    if not contents:
        print("⚠️  Nu există conținut")
        continue
    
    total_chars = sum(len(c.get('content', '')) for c in contents)
    print(f"📚 Chunks: {len(contents)}, Caractere: {total_chars:,}")
    
    # Create collection
    try:
        qdrant_client.delete_collection(collection_name=collection_name)
    except:
        pass
    
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    print(f"   ✅ Colecție creată: {collection_name}")
    
    # Generate embeddings
    print(f"\n⚡ Generare embeddings cu GPU...")
    start_time = time.time()
    
    texts = [c['content'] for c in contents if c.get('content')]
    
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    elapsed = time.time() - start_time
    print(f"✅ Embeddings în {elapsed:.1f}s ({len(texts)/elapsed:.1f} texte/s)")
    
    # Upload to Qdrant
    print(f"📤 Upload către Qdrant...")
    points = []
    for idx_point, (content, embedding) in enumerate(zip(contents, embeddings)):
        points.append(PointStruct(
            id=idx_point,
            vector=embedding.tolist(),
            payload={
                "text": content['content'][:1000],
                "url": content.get('url', ''),
                "agent_id": str(agent_id),
                "chunk_index": idx_point
            }
        ))
    
    qdrant_client.upsert(collection_name=collection_name, points=points)
    
    collection_info = qdrant_client.get_collection(collection_name)
    points_count = getattr(collection_info, "points_count", getattr(collection_info, "vectors_count", 0))
    print(f"✅ Salvați {points_count} vectori")
    
    total_vectors += points_count

elapsed_total = time.time() - start_total

print(f"\n╔══════════════════════════════════════════════════════════════════════╗")
print(f"║  ✅ FINALIZAT!                                                       ║")
print(f"╚══════════════════════════════════════════════════════════════════════╝")
print(f"\n📊 TOTAL:")
print(f"   Vectori generați: {total_vectors}")
print(f"   Timp total: {elapsed_total:.1f}s")
print(f"   Device: {device}")
print(f"\n✅ Toți agenții au vectori în Qdrant cu context semantic complet!")
