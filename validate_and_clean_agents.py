#!/usr/bin/env python3
"""
Mecanism de validare și curățare agenți
Verifică toți agenții din baza de date și șterge pe cei care nu respectă cerințele:
- Trebuie să aibă conținut în Qdrant SAU MongoDB
- Trebuie să aibă site_url sau domain valid
"""

import os
import sys
import logging
import subprocess
import json
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None

class AgentValidator:
    """Validează și curăță agenții din baza de date"""
    
    def __init__(self):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client[MONGO_DB]
        self.agents_collection = self.db.site_agents
        self.site_content_collection = self.db.site_content
        
        # ⭐ FIX: NU mai folosim QdrantClient - folosim curl direct pentru a evita "illegal request line"
        self.qdrant_url = QDRANT_URL
        self.qdrant_api_key = QDRANT_API_KEY
        logger.info("✅ Qdrant va fi accesat prin curl (evită 'illegal request line')")
    
    def check_agent_has_content(self, agent_id: str, agent_doc: dict) -> bool:
        """
        Verifică dacă agentul are conținut în Qdrant SAU MongoDB
        
        Returns:
            True dacă agentul are conținut, False altfel
        """
        try:
            # Verifică Qdrant cu curl (mai stabil)
            collection_name = agent_doc.get("vector_collection") or f"agent_{agent_id}"
            try:
                import subprocess
                import json
                
                result = subprocess.run(
                    f'curl -s "{QDRANT_URL}/collections/{collection_name}"',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0 and result.stdout:
                    try:
                        data = json.loads(result.stdout)
                        if data.get("status") == "ok":
                            points_count = data.get("result", {}).get("points_count", 0)
                            if points_count > 0:
                                logger.info(f"  ✅ Agent {agent_id} are {points_count} vectori în Qdrant")
                                return True
                    except:
                        pass  # Nu e JSON valid sau colecție nu există
            except:
                pass  # Eroare la verificare Qdrant, continuă cu MongoDB
            
            # Verifică MongoDB
            try:
                agent_id_obj = ObjectId(agent_id)
                content_count = self.site_content_collection.count_documents({"agent_id": agent_id_obj})
            except:
                # Fallback: încearcă cu string
                content_count = self.site_content_collection.count_documents({"agent_id": agent_id})
            
            if content_count > 0:
                logger.info(f"  ✅ Agent {agent_id} are {content_count} chunks în MongoDB")
                return True
            
            # Nu are conținut nici în Qdrant, nici în MongoDB
            logger.warning(f"  ❌ Agent {agent_id} NU are conținut în Qdrant sau MongoDB")
            return False
            
        except Exception as e:
            logger.error(f"  ❌ Eroare la verificarea agentului {agent_id}: {e}")
            return False
    
    def validate_agent(self, agent_doc: dict) -> tuple[bool, str]:
        """
        Validează un agent conform cerințelor
        
        Returns:
            (is_valid, reason)
        """
        agent_id = str(agent_doc.get("_id"))
        domain = agent_doc.get("domain", "")
        site_url = agent_doc.get("site_url", "")
        status = agent_doc.get("status", "")
        
        # ⭐ CRITIC: Dacă agentul este în proces de creare, nu-l șterge
        if status in ["created", "creating"]:
            created_at = agent_doc.get("createdAt") or agent_doc.get("created_at")
            if created_at:
                from datetime import datetime, timezone, timedelta
                if isinstance(created_at, datetime):
                    time_diff = datetime.now(timezone.utc) - created_at
                    if time_diff < timedelta(minutes=5):
                        return True, f"Agent în proces de creare (status: {status}, creat acum {time_diff.total_seconds():.0f} secunde)"
            else:
                # Dacă nu are createdAt dar status este "created", nu-l șterge
                return True, f"Agent în proces de creare (status: {status})"
        
        # Verifică dacă are domain sau site_url
        if not domain and not site_url:
            return False, "Nu are domain sau site_url"
        
        # Verifică dacă are conținut
        has_content = self.check_agent_has_content(agent_id, agent_doc)
        if not has_content:
            return False, "Nu are conținut în Qdrant sau MongoDB"
        
        return True, "Valid"
    
    def delete_agent(self, agent_id: str, agent_doc: dict):
        """Șterge un agent și toate datele asociate"""
        try:
            logger.info(f"🗑️  Șterg agent {agent_id} ({agent_doc.get('domain', 'unknown')})...")
            
            # 1. Șterge din MongoDB - site_agents
            self.agents_collection.delete_one({"_id": ObjectId(agent_id)})
            logger.info(f"  ✅ Șters din site_agents")
            
            # 2. Șterge conținutul din MongoDB - site_content
            try:
                agent_id_obj = ObjectId(agent_id)
                result = self.site_content_collection.delete_many({"agent_id": agent_id_obj})
                logger.info(f"  ✅ Șters {result.deleted_count} chunks din site_content")
            except:
                result = self.site_content_collection.delete_many({"agent_id": agent_id})
                logger.info(f"  ✅ Șters {result.deleted_count} chunks din site_content (string)")
            
            # 3. Șterge din Qdrant (folosind curl)
            collection_name = agent_doc.get("vector_collection") or f"agent_{agent_id}"
            try:
                delete_cmd = [
                    'curl', '-X', 'DELETE',
                    f'{self.qdrant_url}/collections/{collection_name}',
                    '-H', 'Content-Type: application/json',
                    '--silent', '--max-time', '10'
                ]
                subprocess.run(delete_cmd, check=False, timeout=15, capture_output=True)
                logger.info(f"  ✅ Șters colecție Qdrant: {collection_name}")
            except Exception as e:
                logger.warning(f"  ⚠️ Nu s-a putut șterge colecția Qdrant: {e}")
            
            # 4. Șterge strategii competitive
            try:
                self.db.competitive_strategies.delete_many({"agent_id": agent_id})
                logger.info(f"  ✅ Șters strategii competitive")
            except:
                pass
            
            logger.info(f"  ✅ Agent {agent_id} șters complet")
            
        except Exception as e:
            logger.error(f"  ❌ Eroare la ștergerea agentului {agent_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def validate_all_agents(self, dry_run: bool = False) -> dict:
        """
        Validează toți agenții din baza de date
        
        Args:
            dry_run: Dacă True, doar raportează, nu șterge
            
        Returns:
            Dict cu statistici
        """
        logger.info("🔍 Încep validarea tuturor agenților...")
        logger.info("=" * 60)
        
        # Obține toți agenții
        all_agents = list(self.agents_collection.find({}))
        total_agents = len(all_agents)
        
        logger.info(f"📊 Total agenți găsiți: {total_agents}")
        logger.info("=" * 60)
        
        valid_agents = []
        invalid_agents = []
        
        for agent in all_agents:
            agent_id = str(agent.get("_id"))
            domain = agent.get("domain", "unknown")
            
            logger.info(f"\n🔍 Verific agent: {domain} ({agent_id})")
            
            is_valid, reason = self.validate_agent(agent)
            
            if is_valid:
                valid_agents.append(agent)
                logger.info(f"  ✅ VALID: {reason}")
            else:
                invalid_agents.append((agent, reason))
                logger.warning(f"  ❌ INVALID: {reason}")
                
                if not dry_run:
                    self.delete_agent(agent_id, agent)
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 REZULTATE VALIDARE:")
        logger.info("=" * 60)
        logger.info(f"✅ Agenți valizi: {len(valid_agents)}/{total_agents}")
        logger.info(f"❌ Agenți invalizi: {len(invalid_agents)}/{total_agents}")
        
        if invalid_agents:
            logger.info("\n❌ Agenți invalizi:")
            for agent, reason in invalid_agents:
                logger.info(f"  - {agent.get('domain', 'unknown')} ({str(agent.get('_id'))}): {reason}")
        
        return {
            "total_agents": total_agents,
            "valid_agents": len(valid_agents),
            "invalid_agents": len(invalid_agents),
            "invalid_details": [
                {
                    "agent_id": str(agent.get("_id")),
                    "domain": agent.get("domain", "unknown"),
                    "reason": reason
                }
                for agent, reason in invalid_agents
            ]
        }

def main():
    """Funcție principală"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validează și curăță agenții din baza de date")
    parser.add_argument("--dry-run", action="store_true", help="Doar raportează, nu șterge")
    parser.add_argument("--force", action="store_true", help="Șterge fără confirmare")
    
    args = parser.parse_args()
    
    validator = AgentValidator()
    
    if args.dry_run:
        logger.info("🔍 MOD DRY-RUN: Doar raportare, nu se șterge nimic")
    else:
        if not args.force:
            response = input("⚠️  Ești sigur că vrei să ștergi agenții invalizi? (yes/no): ")
            if response.lower() != "yes":
                logger.info("❌ Operație anulată")
                return
    
    results = validator.validate_all_agents(dry_run=args.dry_run)
    
    logger.info("\n" + "=" * 60)
    if args.dry_run:
        logger.info("✅ DRY-RUN finalizat - Nu s-a șters nimic")
    else:
        logger.info(f"✅ Validare finalizată - {results['invalid_agents']} agenți șterși")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()

