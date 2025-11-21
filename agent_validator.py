#!/usr/bin/env python3
"""
Validare automată agenți - verifică că respectă cerințele minime
"""

import logging
from typing import Dict, Tuple
from pymongo import MongoClient
from bson import ObjectId
import os

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.ai_agents_db

# Cerințe minime pentru un agent valid
AGENT_QUALITY_REQUIREMENTS = {
    "min_content_chunks": 2,
    "min_total_characters": 1000,
    "min_services": 1,
    "required_fields": ["domain", "site_url", "status", "created_at"],
    "required_metadata_fields": ["business_type"]
}

def validate_agent_quality(agent_id: str) -> Tuple[bool, Dict[str, bool]]:
    """
    Verifică dacă agentul respectă cerințele minime pentru a fi funcțional
    
    Returns:
        (is_valid, checks_dict)
    """
    try:
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return False, {"error": "Agent not found"}
        
        # Obține conținutul
        content_docs = list(db.site_content.find({"agent_id": ObjectId(agent_id)}))
        
        # Calculează statistici
        total_content_chars = sum(len(doc.get('content', '')) for doc in content_docs)
        services_count = len(agent.get('services', []))
        
        # Verificări individuale
        checks = {
            "min_chunks": len(content_docs) >= AGENT_QUALITY_REQUIREMENTS["min_content_chunks"],
            "min_chars": total_content_chars >= AGENT_QUALITY_REQUIREMENTS["min_total_characters"],
            "min_services": services_count >= AGENT_QUALITY_REQUIREMENTS["min_services"],
            "has_domain": bool(agent.get('domain')),
            "has_site_url": bool(agent.get('site_url')),
            "has_status": bool(agent.get('status')),
            "has_created_at": bool(agent.get('created_at')),
            "has_business_type": bool(agent.get('business_type'))
        }
        
        # Statistici pentru logging
        checks["stats"] = {
            "chunks": len(content_docs),
            "total_chars": total_content_chars,
            "services": services_count,
            "domain": agent.get('domain', 'N/A')
        }
        
        # Agent valid dacă toate verificările principale sunt OK
        is_valid = all([
            checks["min_chunks"],
            checks["min_chars"],
            checks["min_services"],
            checks["has_domain"],
            checks["has_site_url"],
            checks["has_created_at"]
        ])
        
        return is_valid, checks
        
    except Exception as e:
        logger.error(f"❌ Eroare la validarea agentului {agent_id}: {e}")
        return False, {"error": str(e)}

def get_validation_errors(checks: Dict[str, bool]) -> str:
    """
    Generează mesaj de eroare user-friendly din checks
    """
    errors = []
    
    if not checks.get("min_chunks"):
        errors.append(f"Prea puține pagini scanate ({checks.get('stats', {}).get('chunks', 0)} < 2)")
    
    if not checks.get("min_chars"):
        errors.append(f"Prea puțin conținut ({checks.get('stats', {}).get('total_chars', 0)} < 1000 caractere)")
    
    if not checks.get("min_services"):
        errors.append(f"Nu s-au detectat servicii ({checks.get('stats', {}).get('services', 0)} < 1)")
    
    if not checks.get("has_domain"):
        errors.append("Lipsește domeniul")
    
    if not checks.get("has_created_at"):
        errors.append("Lipsește timestamp created_at")
    
    return " | ".join(errors) if errors else "Unknown error"

def mark_agent_as_valid(agent_id: str):
    """
    Marchează agentul ca valid și ready
    """
    from datetime import datetime, timezone
    
    db.site_agents.update_one(
        {"_id": ObjectId(agent_id)},
        {"$set": {
            "status": "ready",
            "validation_passed": True,
            "validated_at": datetime.now(timezone.utc)
        }}
    )
    logger.info(f"✅ Agent {agent_id} marcat ca READY și validat")

def mark_agent_as_incomplete(agent_id: str, checks: Dict):
    """
    Marchează agentul ca incomplet și salvează detalii
    """
    from datetime import datetime, timezone
    
    error_message = get_validation_errors(checks)
    
    db.site_agents.update_one(
        {"_id": ObjectId(agent_id)},
        {"$set": {
            "status": "incomplete",
            "validation_passed": False,
            "validation_errors": error_message,
            "validation_checks": checks,
            "validated_at": datetime.now(timezone.utc)
        }}
    )
    logger.warning(f"⚠️  Agent {agent_id} marcat ca INCOMPLETE: {error_message}")

def validate_and_update_agent(agent_id: str) -> bool:
    """
    Validează agent și actualizează status-ul în funcție de rezultat
    
    Returns:
        True dacă agentul e valid, False altfel
    """
    is_valid, checks = validate_agent_quality(agent_id)
    
    if is_valid:
        mark_agent_as_valid(agent_id)
        stats = checks.get('stats', {})
        logger.info(f"✅ Agent {agent_id} VALID: {stats.get('chunks')} chunks, {stats.get('total_chars')} chars, {stats.get('services')} servicii")
        return True
    else:
        mark_agent_as_incomplete(agent_id, checks)
        error_msg = get_validation_errors(checks)
        logger.error(f"❌ Agent {agent_id} INVALID: {error_msg}")
        return False

