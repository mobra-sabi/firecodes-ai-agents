#!/usr/bin/env python3
"""Generare vectori cu GPU pentru agenți existenți"""

import torch
from pymongo import MongoClient
from bson import ObjectId
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import time

# Verifică GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🎮 Device: {device}")
if device == "cuda":
    print(f"   GPU: {torch.cuda.get_device_name(0)}")
    print(f"   CUDA: {torch.version.cuda}")

# Connect
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["ai_agents_db"]
qdrant_client = QdrantClient(url="http://127.0.0.1:6333")

# Load model cu GPU
print("\n📦 Loading SentenceTransformer model...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)
print(f"✅ Model loaded on {device}")

def create_collection(collection_name):
    """Creează colecție Qdrant"""
    try:
        qdrant_client.delete_collection(collection_name=collection_name)
        print(f"   🗑️  Șters colecția veche: {collection_name}")
    except:
        pass
    
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    print(f"   ✅ Creat colecția: {collection_name}")

def generate_vectors_for_agent(agent_id, agent_name, collection_name):
    """Generează vectori pentru un agent"""
    print(f"\n{'='*70}")
    print(f"🚀 AGENT: {agent_name}")
    print(f"   ID: {agent_id}")
    print(f"   Colecție: {collection_name}")
    print(f"{'='*70}")
    
    # Get content
    contents = list(db.site_content.find({"agent_id": ObjectId(agent_id)}))
    
    if not contents:
        print("⚠️  Nu există conținut în MongoDB")
        return
    
    total_chars = sum(len(c.get('content', '')) for c in contents)
    print(f"📚 Conținut găsit: {len(contents)} chunks, {total_chars:,} caractere")
    
    # Create collection
    create_collection(collection_name)
    
    # Generate embeddings cu BATCH PROCESSING
    print(f"\n⚡ Generare embeddings cu GPU...")
    start_time = time.time()
    
    texts = [c['content'] for c in contents if c.get('content')]
    
    # Batch embedding (mult mai rapid)
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    elapsed = time.time() - start_time
    print(f"✅ Embeddings generate în {elapsed:.1f}s ({len(texts)} texte)")
    print(f"   ⚡ Viteză: {len(texts)/elapsed:.1f} texte/secundă")
    
    # Upload to Qdrant
    print(f"\n📤 Upload către Qdrant...")
    points = []
    for idx, (content, embedding) in enumerate(zip(contents, embeddings)):
        points.append(PointStruct(
            id=idx,
            vector=embedding.tolist(),
            payload={
                "text": content['content'][:1000],  # primele 1000 chars
                "url": content.get('url', ''),
                "agent_id": str(agent_id),
                "chunk_index": idx
            }
        ))
    
    qdrant_client.upsert(
        collection_name=collection_name,
        points=points
    )
    
    print(f"✅ Salvați {len(points)} vectori în Qdrant")
    
    # Verify
    collection_info = qdrant_client.get_collection(collection_name)
    points_count = getattr(collection_info, "points_count", getattr(collection_info, "vectors_count", 0))
    print(f"\n📊 STATISTICI:")
    print(f"   Vectori în Qdrant: {points_count}")
    print(f"   Dimensiune vector: {collection_info.config.params.vectors.size}")
    print(f"   Distanță: {collection_info.config.params.vectors.distance}")
    
    return points_count

# Process agents
agents_to_process = [
    {
        "id": "6910d0682716fa6b8a6f8e72",
        "name": "ropaintsolutions.ro",
        "collection": "agent_6910d0682716fa6b8a6f8e72"
    },
    {
        "id": "6910d14dd3576c715435637b", 
        "name": "terrageneralcontractor.ro",
        "collection": "agent_6910d14dd3576c715435637b"
    }
]

print("\n╔══════════════════════════════════════════════════════════════════════╗")
print("║  🚀 GENERARE VECTORI CU GPU PENTRU TOȚI AGENȚII                     ║")
print("╚══════════════════════════════════════════════════════════════════════╝")

total_vectors = 0
start_total = time.time()

for agent_info in agents_to_process:
    try:
        vectors = generate_vectors_for_agent(
            agent_info["id"],
            agent_info["name"],
            agent_info["collection"]
        )
        total_vectors += vectors
    except Exception as e:
        print(f"❌ Eroare pentru {agent_info['name']}: {e}")
        import traceback
        traceback.print_exc()

elapsed_total = time.time() - start_total

print(f"\n╔══════════════════════════════════════════════════════════════════════╗")
print(f"║  ✅ FINALIZAT!                                                       ║")
print(f"╚══════════════════════════════════════════════════════════════════════╝")
print(f"\n📊 TOTAL:")
print(f"   Vectori generați: {total_vectors}")
print(f"   Timp total: {elapsed_total:.1f}s")
print(f"   Device: {device}")
print(f"\n✅ Acum DeepSeek va primi context îmbogățit din Qdrant!")
