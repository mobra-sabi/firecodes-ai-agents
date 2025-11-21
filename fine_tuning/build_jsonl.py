#!/usr/bin/env python3
"""
🔄 Build JSONL - Convertește interacțiunile din MongoDB în format JSONL pentru fine-tuning
"""

import os
import json
from datetime import datetime
from data_collector.collector import get_interactions_for_training, mark_as_processed
from bson import ObjectId

# Configurare
OUTPUT_DIR = "/srv/hf/ai_agents/datasets"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "training_data.jsonl")
MIN_INTERACTIONS = 100  # Minimum pentru fine-tuning

def format_for_training(interaction: dict) -> dict:
    """
    Formatează o interacțiune pentru fine-tuning Qwen
    
    Format Qwen:
    {
        "messages": [
            {"role": "user", "content": "prompt"},
            {"role": "assistant", "content": "response"}
        ]
    }
    """
    return {
        "messages": [
            {"role": "user", "content": interaction["prompt"]},
            {"role": "assistant", "content": interaction["response"]}
        ]
    }


def build_jsonl_dataset(
    limit: int = 5000,
    topic: str = "orchestrator_auto",
    min_tokens: int = 50
) -> str:
    """
    Construiește dataset JSONL din MongoDB
    
    Args:
        limit: Număr maxim de interacțiuni
        topic: Topic-ul interacțiunilor
        min_tokens: Minimum tokens în răspuns
    
    Returns:
        Path-ul fișierului JSONL creat
    """
    print("🔄 Building JSONL dataset from MongoDB...")
    
    # Obține interacțiuni
    interactions = get_interactions_for_training(
        limit=limit,
        topic=topic,
        min_tokens=min_tokens
    )
    
    if len(interactions) < MIN_INTERACTIONS:
        print(f"⚠️  Only {len(interactions)} interactions found (minimum: {MIN_INTERACTIONS})")
        print("   Skipping JSONL build. Need more data.")
        return ""
    
    # Creează directorul dacă nu există
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Scrie JSONL
    interaction_ids = []
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for interaction in interactions:
            # Convertește ObjectId în string
            if isinstance(interaction["_id"], ObjectId):
                interaction_ids.append(str(interaction["_id"]))
            else:
                interaction_ids.append(interaction["_id"])
            
            # Formatează pentru training
            training_example = format_for_training(interaction)
            
            # Scrie linie JSONL
            f.write(json.dumps(training_example, ensure_ascii=False) + "\n")
    
    # Marchează ca procesate
    if interaction_ids:
        mark_as_processed(interaction_ids)
    
    file_size = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)  # MB
    print(f"✅ Created JSONL dataset: {OUTPUT_FILE}")
    print(f"   • Interactions: {len(interactions)}")
    print(f"   • File size: {file_size:.2f} MB")
    
    return OUTPUT_FILE


if __name__ == "__main__":
    print("=" * 80)
    print("🔄 BUILD JSONL DATASET FOR FINE-TUNING")
    print("=" * 80)
    print()
    
    jsonl_file = build_jsonl_dataset(
        limit=5000,
        topic="orchestrator_auto",
        min_tokens=50
    )
    
    if jsonl_file:
        print()
        print("✅ Dataset ready for fine-tuning!")
        print(f"   File: {jsonl_file}")
    else:
        print()
        print("⚠️  Not enough data for fine-tuning yet.")


