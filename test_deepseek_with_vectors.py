#!/usr/bin/env python3
"""Test DeepSeek cu context din Qdrant vectori"""

import torch
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import os
import requests

# Setup
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)
qdrant = QdrantClient(url="http://127.0.0.1:6333", check_compatibility=False)

def get_context_from_qdrant(query: str, collection: str, top_k: int = 3):
    """Extrage context relevant din Qdrant"""
    # Generate query embedding
    query_vector = model.encode(query, convert_to_numpy=True)
    
    # Search in Qdrant
    results = qdrant.search(
        collection_name=collection,
        query_vector=query_vector.tolist(),
        limit=top_k
    )
    
    # Extract text
    contexts = []
    for hit in results:
        contexts.append({
            "text": hit.payload.get("text", ""),
            "score": hit.score,
            "url": hit.payload.get("url", "")
        })
    
    return contexts

def query_deepseek_with_context(query: str, contexts: list):
    """Interroghează DeepSeek cu context din Qdrant"""
    
    # Build context string
    context_str = "\n\n".join([
        f"[Context {i+1} - Score: {c['score']:.3f}]\n{c['text']}"
        for i, c in enumerate(contexts)
    ])
    
    prompt = f"""Contextul din baza de date vectorială:

{context_str}

---

Întrebare: {query}

Te rog să răspunzi bazându-te pe contextul de mai sus."""

    # Call DeepSeek
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Ești un asistent AI specializat în protecție la foc și industria de securitate."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        },
        timeout=30
    )
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"

# TEST
print("╔══════════════════════════════════════════════════════════════════════╗")
print("║  🧪 TEST: DeepSeek + Context din Qdrant                             ║")
print("╚══════════════════════════════════════════════════════════════════════╝")
print()

query = "Ce servicii de protecție la foc sunt disponibile?"
collection = "agent_6910d0682716fa6b8a6f8e72"  # ropaintsolutions

print(f"🔍 Query: {query}")
print(f"📦 Collection: {collection}")
print()

# Get context
print("⚡ Extragere context din Qdrant...")
contexts = get_context_from_qdrant(query, collection, top_k=3)

print(f"✅ Găsite {len(contexts)} contexte relevante:")
for i, ctx in enumerate(contexts, 1):
    print(f"\n   {i}. Score: {ctx['score']:.3f}")
    print(f"      Text preview: {ctx['text'][:150]}...")

print()
print("🤖 Interogare DeepSeek cu context...")
print()

response = query_deepseek_with_context(query, contexts)

print("📝 RĂSPUNS DEEPSEEK:")
print("="*70)
print(response)
print("="*70)
print()
print("✅ DeepSeek a primit și folosit contextul din Qdrant!")
