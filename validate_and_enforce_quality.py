#!/usr/bin/env python3
"""
Validare și Curățare Agenți - STRICT MODE
=========================================

Verifică TOȚI agenții din baza de date și șterge pe cei neconformi.

Criterii de conformitate:
1. >= 5 chunks de conținut în MongoDB
2. >= 3 servicii extrase
3. created_at definit
4. status != "creating" sau "failed"
5. Collection Qdrant existentă (opțional)

Rulare:
    python3 validate_and_enforce_quality.py
    python3 validate_and_enforce_quality.py --dry-run  # Doar verifică, nu șterge
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import subprocess
import json

from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")

# Criterii de conformitate
MIN_CONTENT_CHUNKS = 5
MIN_SERVICES = 3
GRACE_PERIOD_MINUTES = 5  # Nu șterge agenții creați în ultimele 5 minute


class AgentQualityValidator:
    def __init__(self, dry_run=False):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client[MONGO_DB]
        self.agents_collection = self.db.site_agents
        self.dry_run = dry_run
        
    def _check_qdrant_collection(self, collection_name: str) -> Dict[str, Any]:
        """Verifică dacă collection-ul Qdrant există și are puncte."""
        try:
            result = subprocess.run(
                ["curl", "-s", f"{QDRANT_URL}/collections/{collection_name}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get("status") == "ok" and data.get("result"):
                    points_count = data["result"].get("points_count", 0)
                    return {"exists": True, "points_count": points_count}
            
            return {"exists": False, "points_count": 0}
        except Exception as e:
            logger.warning(f"Nu pot verifica Qdrant pentru {collection_name}: {e}")
            return {"exists": False, "points_count": 0}
    
    def validate_agent(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validează un agent conform criteriilor de calitate.
        
        Returns:
            {
                "valid": bool,
                "reasons": List[str],  # Motive pentru invalidare
                "warnings": List[str],  # Avertismente (nu invalidează)
                "stats": Dict  # Statistici agent
            }
        """
        agent_id = agent["_id"]
        domain = agent.get("domain", "unknown")
        status = agent.get("status", "unknown")
        created_at = agent.get("created_at")
        
        reasons = []
        warnings = []
        stats = {}
        
        # 1. Verifică status
        if status in ["creating", "failed", "error"]:
            # Dacă e recent (< 5 minute), nu-l șterge
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        created_dt = created_at
                    
                    age_minutes = (datetime.now(timezone.utc) - created_dt).total_seconds() / 60
                    
                    if age_minutes < GRACE_PERIOD_MINUTES:
                        warnings.append(f"Status '{status}' dar creat recent ({age_minutes:.1f} min)")
                        return {"valid": True, "reasons": [], "warnings": warnings, "stats": stats}
                except Exception as e:
                    logger.warning(f"Nu pot parsa created_at pentru {domain}: {e}")
            
            reasons.append(f"Status invalid: '{status}'")
        
        # 2. Verifică created_at
        if not created_at:
            reasons.append("Lipsește created_at")
            stats["created_at"] = None
        else:
            stats["created_at"] = str(created_at)
        
        # 3. Verifică conținut în MongoDB
        content_count = self.db.site_content.count_documents({"agent_id": agent_id})
        stats["content_chunks"] = content_count
        
        if content_count < MIN_CONTENT_CHUNKS:
            reasons.append(f"Conținut insuficient: {content_count} chunks (minim {MIN_CONTENT_CHUNKS})")
        
        # 4. Verifică servicii
        services = agent.get("services", [])
        services_count = len(services) if isinstance(services, list) else 0
        stats["services_count"] = services_count
        
        if services_count < MIN_SERVICES:
            # Verifică și în site_data
            site_data = self.db.site_data.find_one({"domain": domain})
            if site_data:
                services_products = site_data.get("services_products", [])
                if isinstance(services_products, list) and len(services_products) >= MIN_SERVICES:
                    warnings.append(f"Servicii în site_data: {len(services_products)}")
                    stats["services_in_site_data"] = len(services_products)
                else:
                    reasons.append(f"Servicii insuficiente: {services_count} (minim {MIN_SERVICES})")
            else:
                reasons.append(f"Servicii insuficiente: {services_count} (minim {MIN_SERVICES})")
        
        # 5. Verifică Qdrant (opțional, doar warning)
        qdrant_collection = f"mem_{agent_id}"
        qdrant_info = self._check_qdrant_collection(qdrant_collection)
        stats["qdrant_exists"] = qdrant_info["exists"]
        stats["qdrant_points"] = qdrant_info["points_count"]
        
        if not qdrant_info["exists"] or qdrant_info["points_count"] == 0:
            warnings.append(f"Qdrant: {qdrant_info['points_count']} puncte")
        
        # 6. Verifică integrare Long Chain
        if not agent.get("long_chain_integrated"):
            warnings.append("Nu este integrat în Long Chain")
        
        # 7. Verifică memorie Qwen
        if not agent.get("memory_initialized"):
            warnings.append("Memorie Qwen neinițializată")
        
        is_valid = len(reasons) == 0
        
        return {
            "valid": is_valid,
            "reasons": reasons,
            "warnings": warnings,
            "stats": stats
        }
    
    def delete_agent(self, agent: Dict[str, Any]) -> bool:
        """Șterge un agent și toate datele asociate."""
        if self.dry_run:
            logger.info(f"[DRY-RUN] Ar șterge agent {agent.get('domain')}")
            return True
        
        agent_id = agent["_id"]
        domain = agent.get("domain", "unknown")
        
        try:
            logger.info(f"🗑️  Șterg agent {domain} (ID: {agent_id})...")
            
            # 1. Șterge din MongoDB
            self.agents_collection.delete_one({"_id": agent_id})
            deleted_content = self.db.site_content.delete_many({"agent_id": agent_id}).deleted_count
            deleted_site_data = self.db.site_data.delete_many({"domain": domain}).deleted_count
            deleted_strategies = self.db.competitive_strategies.delete_many({"agent_id": agent_id}).deleted_count
            
            logger.info(f"   MongoDB: agent + {deleted_content} content + {deleted_site_data} site_data + {deleted_strategies} strategies")
            
            # 2. Șterge din Qdrant
            qdrant_collection = f"mem_{agent_id}"
            try:
                result = subprocess.run(
                    ["curl", "-s", "-X", "DELETE", f"{QDRANT_URL}/collections/{qdrant_collection}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info(f"   Qdrant: collection {qdrant_collection} șters")
            except Exception as e:
                logger.warning(f"   Eroare la ștergerea Qdrant: {e}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Eroare la ștergerea agent {domain}: {e}")
            return False
    
    def add_quality_flag(self, agent: Dict[str, Any], validation_result: Dict[str, Any]):
        """Adaugă flag de calitate în document."""
        if self.dry_run:
            return
        
        try:
            self.agents_collection.update_one(
                {"_id": agent["_id"]},
                {
                    "$set": {
                        "quality_validated": True,
                        "quality_validation_date": datetime.now(timezone.utc),
                        "quality_stats": validation_result["stats"],
                        "quality_warnings": validation_result["warnings"]
                    }
                }
            )
        except Exception as e:
            logger.error(f"Eroare la adăugarea flag calitate: {e}")
    
    async def validate_all_agents(self) -> Dict[str, Any]:
        """Validează toți agenții și șterge pe cei neconformi."""
        logger.info("🔍 Încep validarea tuturor agenților...")
        
        agents = list(self.agents_collection.find({}))
        
        stats = {
            "total": len(agents),
            "valid": 0,
            "invalid": 0,
            "deleted": 0,
            "errors": 0,
            "details": []
        }
        
        for agent in agents:
            domain = agent.get("domain", "unknown")
            agent_id = str(agent["_id"])
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Validare agent: {domain} (ID: {agent_id})")
            
            validation = self.validate_agent(agent)
            
            detail = {
                "domain": domain,
                "agent_id": agent_id,
                "valid": validation["valid"],
                "reasons": validation["reasons"],
                "warnings": validation["warnings"],
                "stats": validation["stats"]
            }
            
            if validation["valid"]:
                logger.info(f"✅ Agent VALID")
                stats["valid"] += 1
                
                # Adaugă flag de calitate
                self.add_quality_flag(agent, validation)
                
                if validation["warnings"]:
                    logger.warning(f"⚠️  Avertismente:")
                    for warning in validation["warnings"]:
                        logger.warning(f"   - {warning}")
            else:
                logger.error(f"❌ Agent INVALID")
                stats["invalid"] += 1
                
                logger.error(f"Motive:")
                for reason in validation["reasons"]:
                    logger.error(f"   - {reason}")
                
                # Șterge agent invalid
                if self.delete_agent(agent):
                    stats["deleted"] += 1
                    detail["deleted"] = True
                else:
                    stats["errors"] += 1
                    detail["deleted"] = False
            
            # Afișează statistici
            logger.info(f"Statistici agent:")
            for key, value in validation["stats"].items():
                logger.info(f"   {key}: {value}")
            
            stats["details"].append(detail)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 REZUMAT VALIDARE:")
        logger.info(f"   Total agenți: {stats['total']}")
        logger.info(f"   ✅ Valizi: {stats['valid']}")
        logger.info(f"   ❌ Invalizi: {stats['invalid']}")
        logger.info(f"   🗑️  Șterși: {stats['deleted']}")
        logger.info(f"   ⚠️  Erori: {stats['errors']}")
        
        return stats


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Validare și curățare agenți")
    parser.add_argument("--dry-run", action="store_true", help="Doar verifică, nu șterge")
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🔍 MOD DRY-RUN: Nicio modificare nu va fi făcută")
    
    validator = AgentQualityValidator(dry_run=args.dry_run)
    stats = await validator.validate_all_agents()
    
    return stats


if __name__ == "__main__":
    asyncio.run(main())

