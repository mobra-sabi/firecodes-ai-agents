#!/usr/bin/env python3
"""
Script pentru unificarea colecțiilor de agenți
Migrează site_agents → agents și asigură integrarea LangChain
"""

import sys
from pymongo import MongoClient
from datetime import datetime, timezone
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def unify_agents_collections():
    """Unifică site_agents în agents"""
    mongo = MongoClient("mongodb://localhost:27017")
    db = mongo["ai_agents_db"]
    
    agents_collection = db.agents
    site_agents_collection = db.site_agents
    
    logger.info("=" * 70)
    logger.info("🔄 UNIFICARE COLECȚII AGENȚI")
    logger.info("=" * 70)
    
    # 1. Verifică starea inițială
    agents_count_before = agents_collection.count_documents({})
    site_agents_count = site_agents_collection.count_documents({})
    
    logger.info(f"\n📊 Stare inițială:")
    logger.info(f"   - agents: {agents_count_before} agenți")
    logger.info(f"   - site_agents: {site_agents_count} agenți")
    
    # 2. Găsește agenții din site_agents care nu sunt în agents
    existing_domains = set(agents_collection.distinct("domain"))
    logger.info(f"\n📊 Domains existente în agents: {len(existing_domains)}")
    
    # 3. Migrează agenții
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    site_agents = list(site_agents_collection.find({}))
    logger.info(f"\n🔄 Începe migrarea {len(site_agents)} agenți...")
    
    for site_agent in site_agents:
        try:
            domain = site_agent.get("domain")
            if not domain:
                skipped_count += 1
                continue
            
            # Verifică dacă există deja
            existing = agents_collection.find_one({"domain": domain})
            if existing:
                # Actualizează agentul existent cu date din site_agents
                update_data = {
                    "site_url": site_agent.get("site_url"),
                    "industry": site_agent.get("industry"),
                    "chunks_indexed": site_agent.get("chunks_indexed", 0),
                    "pages_indexed": site_agent.get("pages_indexed", 0),
                    "keywords": site_agent.get("keywords", []),
                    "overall_keywords": site_agent.get("overall_keywords", []),
                    "subdomains": site_agent.get("subdomains", []),
                    "updatedAt": datetime.now(timezone.utc)
                }
                
                # Actualizează doar câmpurile care lipsesc sau sunt mai noi
                agents_collection.update_one(
                    {"domain": domain},
                    {"$set": update_data}
                )
                skipped_count += 1
                logger.debug(f"   ✅ Actualizat: {domain}")
            else:
                # Creează agent nou
                new_agent = {
                    "domain": domain,
                    "site_url": site_agent.get("site_url", f"https://{domain}"),
                    "industry": site_agent.get("industry", ""),
                    "name": site_agent.get("agent_config", {}).get("name", "Site Agent"),
                    "status": "ready" if site_agent.get("validation_passed") else "migrated",
                    "chunks_indexed": site_agent.get("chunks_indexed", 0),
                    "pages_indexed": site_agent.get("pages_indexed", 0),
                    "keywords": site_agent.get("keywords", []),
                    "overall_keywords": site_agent.get("overall_keywords", []),
                    "subdomains": site_agent.get("subdomains", []),
                    "createdAt": site_agent.get("created_at", datetime.now(timezone.utc)),
                    "updatedAt": datetime.now(timezone.utc),
                    "version": "1.0"
                }
                
                agents_collection.insert_one(new_agent)
                migrated_count += 1
                logger.info(f"   ✅ Migrat: {domain}")
                
        except Exception as e:
            error_count += 1
            logger.error(f"   ❌ Eroare la {site_agent.get('domain', 'unknown')}: {e}")
    
    # 4. Rezultate finale
    agents_count_after = agents_collection.count_documents({})
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ MIGRARE COMPLETĂ")
    logger.info("=" * 70)
    logger.info(f"   - Migrați: {migrated_count} agenți noi")
    logger.info(f"   - Actualizați: {skipped_count} agenți existente")
    logger.info(f"   - Erori: {error_count}")
    logger.info(f"   - Total agents înainte: {agents_count_before}")
    logger.info(f"   - Total agents după: {agents_count_after}")
    logger.info(f"   - Diferență: +{agents_count_after - agents_count_before} agenți")
    
    return {
        "migrated": migrated_count,
        "updated": skipped_count,
        "errors": error_count,
        "total_before": agents_count_before,
        "total_after": agents_count_after
    }

if __name__ == "__main__":
    try:
        result = unify_agents_collections()
        print(f"\n✅ Unificare completă!")
        print(f"   Total agenți: {result['total_after']}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Eroare: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

