#!/usr/bin/env python3
"""
📊 Data Collector - Salvează toate interacțiunile orchestratorului
Folosit pentru fine-tuning și învățare automată
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pymongo import MongoClient
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "adbrain_ai")
COLLECTION_NAME = "interactions"

def get_mongo_collection():
    """Obține colecția MongoDB pentru interacțiuni"""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    # Creează indexuri pentru performanță
    collection.create_index([("timestamp", -1)])
    collection.create_index([("provider", 1)])
    collection.create_index([("topic", 1)])
    collection.create_index([("processed", 1)])
    
    return collection


def save_diagnostic(
    diagnostic_type: str,
    data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Salvează un diagnostic în MongoDB pentru învățare
    
    Args:
        diagnostic_type: Tip diagnostic (system_check, execution_route, error, etc.)
        data: Datele diagnosticului
        metadata: Metadata suplimentară
    
    Returns:
        ID-ul diagnosticului salvat
    """
    try:
        collection = get_mongo_collection()
        
        diagnostic = {
            "type": "diagnostic",
            "diagnostic_type": diagnostic_type,
            "data": data,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc),
            "processed": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = collection.insert_one(diagnostic)
        diagnostic_id = str(result.inserted_id)
        
        logger.info(f"✅ Saved diagnostic {diagnostic_id} (type: {diagnostic_type})")
        
        return diagnostic_id
        
    except Exception as e:
        logger.error(f"❌ Error saving diagnostic: {e}")
        return ""


def save_execution_route(
    route_name: str,
    steps: List[Dict[str, Any]],
    result: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Salvează o rută de execuție pentru învățare
    
    Args:
        route_name: Numele rutei (ex: "serp_monitoring", "agent_creation")
        steps: Lista de pași executați
        result: Rezultatul final
        metadata: Metadata suplimentară
    
    Returns:
        ID-ul rutei salvate
    """
    try:
        collection = get_mongo_collection()
        
        execution_route = {
            "type": "execution_route",
            "route_name": route_name,
            "steps": steps,
            "result": result,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc),
            "processed": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = collection.insert_one(execution_route)
        route_id = str(result.inserted_id)
        
        logger.info(f"✅ Saved execution route {route_id} (name: {route_name})")
        
        return route_id
        
    except Exception as e:
        logger.error(f"❌ Error saving execution route: {e}")
        return ""


def save_interaction(
    prompt: str,
    provider_name: str,
    response_text: str,
    topic: str = "orchestrator_auto",
    metadata: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    tokens: Optional[int] = None,
    success: bool = True,
    execution_route: Optional[str] = None,
    diagnostic_context: Optional[Dict[str, Any]] = None,
    agent_id: Optional[str] = None
) -> str:
    """
    Salvează o interacțiune în MongoDB
    
    Args:
        prompt: Prompt-ul trimis
        response_text: Răspunsul primit
        provider_name: Numele provider-ului (deepseek, together, kimi, etc.)
        topic: Topic-ul interacțiunii (default: orchestrator_auto)
        metadata: Metadata suplimentară
        model: Modelul folosit
        tokens: Număr de tokens
        success: Dacă interacțiunea a reușit
    
    Returns:
        ID-ul interacțiunii salvate
    """
    try:
        collection = get_mongo_collection()
        
        # Merge agent_id in metadata if provided
        final_metadata = metadata or {}
        if agent_id:
            final_metadata["agent_id"] = agent_id
        
        interaction = {
            "type": "interaction",
            "timestamp": datetime.now(timezone.utc),
            "prompt": prompt,
            "response": response_text,
            "provider": provider_name,
            "model": model or provider_name,
            "topic": topic,
            "tokens": tokens or 0,
            "success": success,
            "processed": False,  # Pentru fine-tuning
            "execution_route": execution_route,  # Link către rută de execuție
            "diagnostic_context": diagnostic_context,  # Context diagnostic
            "metadata": final_metadata,
            "agent_id": agent_id,  # Direct field for easy querying
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = collection.insert_one(interaction)
        interaction_id = str(result.inserted_id)
        
        logger.info(f"✅ Saved interaction {interaction_id} from {provider_name} (topic: {topic})")
        
        return interaction_id
        
    except Exception as e:
        logger.error(f"❌ Error saving interaction: {e}")
        return ""


def get_interactions_for_training(
    limit: int = 1000,
    topic: Optional[str] = None,
    provider: Optional[str] = None,
    min_tokens: int = 50
) -> list:
    """
    Obține interacțiuni pentru fine-tuning
    
    Args:
        limit: Număr maxim de interacțiuni
        topic: Filtrare după topic
        provider: Filtrare după provider
        min_tokens: Minimum tokens în răspuns
    
    Returns:
        Lista de interacțiuni
    """
    collection = get_mongo_collection()
    
    query = {
        "success": True,
        "processed": False,
        "tokens": {"$gte": min_tokens}
    }
    
    if topic:
        query["topic"] = topic
    
    if provider:
        query["provider"] = provider
    
    interactions = list(
        collection.find(query)
        .sort("timestamp", -1)
        .limit(limit)
    )
    
    logger.info(f"📊 Found {len(interactions)} interactions for training")
    
    return interactions


def mark_as_processed(interaction_ids: list):
    """Marchează interacțiunile ca procesate"""
    collection = get_mongo_collection()
    
    result = collection.update_many(
        {"_id": {"$in": [ObjectId(id) for id in interaction_ids]}},
        {"$set": {"processed": True, "processed_at": datetime.now(timezone.utc)}}
    )
    
    logger.info(f"✅ Marked {result.modified_count} interactions as processed")


if __name__ == "__main__":
    # Test collector
    print("🧪 Testing Data Collector...")
    
    test_id = save_interaction(
        prompt="Test prompt pentru collector",
        provider_name="test",
        response_text="Test response pentru verificare funcționalitate",
        topic="test",
        tokens=100
    )
    
    print(f"✅ Test interaction saved with ID: {test_id}")
    
    # Verifică MongoDB
    collection = get_mongo_collection()
    count = collection.count_documents({})
    print(f"📊 Total interactions in database: {count}")

