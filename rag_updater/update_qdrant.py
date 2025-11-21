#!/usr/bin/env python3
"""
🔄 RAG Updater - Actualizează baza vectorială Qdrant cu noile interacțiuni
"""

import os
import json
from datetime import datetime
from typing import List, Dict
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from data_collector.collector import get_interactions_for_training

# Configurare
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "mem_auto"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Lightweight, rapid

def get_embeddings(texts: List[str], model) -> List[List[float]]:
    """Generează embeddings pentru texte"""
    return model.encode(texts, show_progress_bar=True).tolist()


def update_qdrant_collection(
    limit: int = 1000,
    batch_size: int = 100
):
    """
    Actualizează colecția Qdrant cu noile interacțiuni
    
    Args:
        limit: Număr maxim de interacțiuni de procesat
        batch_size: Dimensiune batch pentru embeddings
    """
    print("🔄 Updating Qdrant collection with new interactions...")
    
    # Conectare Qdrant
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # Verifică dacă colecția există
    collections = qdrant.get_collections()
    collection_exists = any(c.name == COLLECTION_NAME for c in collections.collections)
    
    if not collection_exists:
        print(f"📦 Creating collection: {COLLECTION_NAME}")
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=384,  # all-MiniLM-L6-v2 dimension
                distance=Distance.COSINE
            )
        )
    
    # Obține interacțiuni noi (care nu au fost procesate pentru Qdrant)
    interactions = get_interactions_for_training(
        limit=limit,
        topic="orchestrator_auto",
        min_tokens=50
    )
    
    if not interactions:
        print("⚠️  No new interactions to process")
        return
    
    print(f"📊 Processing {len(interactions)} interactions...")
    
    # Load embedding model
    print("🔍 Loading embedding model...")
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Procesează în batch-uri
    points = []
    processed_count = 0
    
    for i in range(0, len(interactions), batch_size):
        batch = interactions[i:i + batch_size]
        
        # Pregătește texte pentru embedding
        texts = []
        metadata_list = []
        
        for interaction in batch:
            # Combină prompt + response pentru context complet
            text = f"{interaction['prompt']}\n\n{interaction['response']}"
            texts.append(text)
            
            metadata_list.append({
                "interaction_id": str(interaction["_id"]),
                "provider": interaction.get("provider", "unknown"),
                "topic": interaction.get("topic", "orchestrator_auto"),
                "timestamp": interaction.get("timestamp", datetime.now()).isoformat(),
                "tokens": interaction.get("tokens", 0)
            })
        
        # Generează embeddings
        print(f"   Processing batch {i//batch_size + 1}/{(len(interactions) + batch_size - 1)//batch_size}...")
        embeddings = get_embeddings(texts, embedding_model)
        
        # Creează points pentru Qdrant
        for j, (embedding, metadata) in enumerate(zip(embeddings, metadata_list)):
            point_id = i + j
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=metadata
                )
            )
        
        processed_count += len(batch)
    
    # Upload points în Qdrant
    if points:
        print(f"📤 Uploading {len(points)} points to Qdrant...")
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        
        print(f"✅ Updated Qdrant collection with {len(points)} new points")
        
        # Statistici
        collection_info = qdrant.get_collection(COLLECTION_NAME)
        print(f"   • Total points: {collection_info.points_count}")
        print(f"   • Vectors config: {collection_info.config.params.vectors}")
    else:
        print("⚠️  No points to upload")


if __name__ == "__main__":
    print("=" * 80)
    print("🔄 UPDATE QDRANT COLLECTION")
    print("=" * 80)
    print()
    
    update_qdrant_collection(
        limit=1000,
        batch_size=100
    )
    
    print()
    print("✅ Qdrant update completed!")


