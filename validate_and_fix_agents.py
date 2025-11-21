#!/usr/bin/env python3
"""
Script de verificare și corectare agenți non-conformi

Verifică toți agenții din MongoDB și:
1. Verifică dacă au conținut în Qdrant sau MongoDB
2. Dacă nu au conținut, încearcă să-i recreeze
3. Dacă nu poate fi recreat, îl șterge
"""

import os
import sys
import logging
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None

class AgentValidator:
    def __init__(self):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client[MONGO_DB]
        self.agents_collection = self.db.site_agents
        self.site_content_collection = self.db.site_content
        
        try:
            self.qdrant_client = QdrantClient(
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                prefer_grpc=False,
                check_compatibility=False,
                timeout=10
            )
            logger.info("✅ Conectat la Qdrant")
        except Exception as e:
            logger.error(f"❌ Eroare la conectarea la Qdrant: {e}")
            self.qdrant_client = None
    
    def check_agent_content(self, agent_id: str) -> dict:
        """
        Verifică dacă agentul are conținut în Qdrant sau MongoDB
        
        Returns:
            dict cu status: {
                'has_qdrant': bool,
                'has_mongodb': bool,
                'qdrant_count': int,
                'mongodb_count': int,
                'is_compliant': bool
            }
        """
        result = {
            'has_qdrant': False,
            'has_mongodb': False,
            'qdrant_count': 0,
            'mongodb_count': 0,
            'is_compliant': False
        }
        
        # Verifică MongoDB
        try:
            mongodb_count = self.site_content_collection.count_documents({"agent_id": agent_id})
            result['mongodb_count'] = mongodb_count
            result['has_mongodb'] = mongodb_count > 0
        except Exception as e:
            logger.warning(f"Eroare la verificarea MongoDB pentru agent {agent_id}: {e}")
        
        # Verifică Qdrant
        if self.qdrant_client:
            try:
                agent_doc = self.agents_collection.find_one({"_id": ObjectId(agent_id)})
                if agent_doc:
                    collection_name = agent_doc.get("vector_collection")
                    if collection_name:
                        try:
                            collection_info = self.qdrant_client.get_collection(collection_name)
                            qdrant_count = getattr(collection_info, "points_count", getattr(collection_info, "vectors_count", 0)) if collection_info else 0
                            result['qdrant_count'] = qdrant_count
                            result['has_qdrant'] = qdrant_count > 0
                        except Exception as e:
                            logger.debug(f"Colecția Qdrant '{collection_name}' nu există sau are probleme: {e}")
            except Exception as e:
                logger.warning(f"Eroare la verificarea Qdrant pentru agent {agent_id}: {e}")
        
        # Agentul este conform dacă are conținut în cel puțin unul dintre storage-uri
        result['is_compliant'] = result['has_qdrant'] or result['has_mongodb']
        
        return result
    
    def recreate_agent(self, agent_id: str, agent_doc: dict) -> bool:
        """
        Încearcă să recreeze agentul folosind site_url
        
        Returns:
            bool: True dacă recrearea a reușit
        """
        site_url = agent_doc.get("site_url")
        if not site_url:
            logger.warning(f"Agent {agent_id} nu are site_url, nu poate fi recreat")
            return False
        
        logger.info(f"🔄 Încearcă să recreeze agentul {agent_id} pentru {site_url}...")
        
        try:
            # Șterge agentul existent și datele asociate pentru recreare completă
            logger.info(f"🗑️ Șterge agentul existent pentru recreare completă...")
            self.delete_agent(agent_id, agent_doc)
            
            # Așteaptă puțin pentru a se asigura că ștergerea este completă
            import time
            time.sleep(1)
            
            # Importă funcția de creare agent
            sys.path.insert(0, '/srv/hf/ai_agents')
            from site_agent_creator import create_agent_logic
            
            # Rulează crearea agentului (fără WebSocket)
            import asyncio
            result = asyncio.run(create_agent_logic(
                url=site_url,
                api_key="local",
                loop=None,
                websocket=None
            ))
            
            if result.get("status") in ["created", "existed"]:
                # Verifică dacă noul agent are conținut
                new_agent_id = result.get("agent_id")
                if new_agent_id:
                    content_status = self.check_agent_content(new_agent_id)
                    if content_status['is_compliant']:
                        logger.info(f"✅ Agent {agent_id} recreat cu succes și este conform")
                        return True
                    else:
                        logger.warning(f"⚠️ Agent {agent_id} recreat dar încă nu are conținut")
                        return False
                else:
                    logger.warning(f"⚠️ Recrearea agentului {agent_id} nu a returnat agent_id")
                    return False
            else:
                logger.warning(f"⚠️ Recrearea agentului {agent_id} a eșuat: {result.get('message', 'Unknown')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Eroare la recrearea agentului {agent_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def delete_agent(self, agent_id: str, agent_doc: dict):
        """
        Șterge agentul și toate datele asociate
        """
        logger.warning(f"🗑️ Șterge agentul {agent_id} ({agent_doc.get('domain', 'N/A')})...")
        
        try:
            # Șterge din MongoDB
            self.agents_collection.delete_one({"_id": ObjectId(agent_id)})
            self.site_content_collection.delete_many({"agent_id": agent_id})
            
            # Șterge din Qdrant
            if self.qdrant_client:
                collection_name = agent_doc.get("vector_collection")
                if collection_name:
                    try:
                        self.qdrant_client.delete_collection(collection_name)
                        logger.info(f"✅ Colecția Qdrant '{collection_name}' ștearsă")
                    except Exception as e:
                        logger.debug(f"Colecția Qdrant '{collection_name}' nu există sau nu poate fi ștearsă: {e}")
            
            logger.info(f"✅ Agent {agent_id} șters complet")
            return True
            
        except Exception as e:
            logger.error(f"❌ Eroare la ștergerea agentului {agent_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def validate_all_agents(self, recreate: bool = True, delete_if_failed: bool = True):
        """
        Validează toți agenții și corectează pe cei non-conformi
        
        Args:
            recreate: Dacă True, încearcă să recreeze agenții non-conformi
            delete_if_failed: Dacă True, șterge agenții care nu pot fi recreați
        """
        logger.info("🔍 Începe validarea tuturor agenților...")
        
        # Obține toți agenții
        agents = list(self.agents_collection.find({}))
        total_agents = len(agents)
        
        logger.info(f"📊 Total agenți găsiți: {total_agents}")
        
        compliant_count = 0
        non_compliant_count = 0
        recreated_count = 0
        deleted_count = 0
        
        results = {
            'compliant': [],
            'non_compliant': [],
            'recreated': [],
            'deleted': []
        }
        
        for agent in agents:
            agent_id = str(agent["_id"])
            domain = agent.get("domain", "N/A")
            site_url = agent.get("site_url", "N/A")
            
            logger.info(f"\n🔍 Verifică agent: {domain} ({agent_id})")
            
            # Verifică conținut
            content_status = self.check_agent_content(agent_id)
            
            if content_status['is_compliant']:
                compliant_count += 1
                results['compliant'].append({
                    'agent_id': agent_id,
                    'domain': domain,
                    'qdrant_count': content_status['qdrant_count'],
                    'mongodb_count': content_status['mongodb_count']
                })
                logger.info(f"✅ Agent {domain} este conform (Qdrant: {content_status['qdrant_count']}, MongoDB: {content_status['mongodb_count']})")
            else:
                non_compliant_count += 1
                logger.warning(f"❌ Agent {domain} NU este conform (Qdrant: {content_status['qdrant_count']}, MongoDB: {content_status['mongodb_count']})")
                
                # Încearcă să recreeze
                if recreate:
                    if self.recreate_agent(agent_id, agent):
                        recreated_count += 1
                        results['recreated'].append({
                            'agent_id': agent_id,
                            'domain': domain,
                            'site_url': site_url
                        })
                        # Verifică din nou după recreare
                        content_status_after = self.check_agent_content(agent_id)
                        if content_status_after['is_compliant']:
                            compliant_count += 1
                            non_compliant_count -= 1
                            logger.info(f"✅ Agent {domain} este acum conform după recreare")
                        else:
                            logger.warning(f"⚠️ Agent {domain} încă nu este conform după recreare")
                    else:
                        # Recrearea a eșuat, șterge dacă este permis
                        if delete_if_failed:
                            if self.delete_agent(agent_id, agent):
                                deleted_count += 1
                                results['deleted'].append({
                                    'agent_id': agent_id,
                                    'domain': domain,
                                    'site_url': site_url,
                                    'reason': 'Recreare eșuată'
                                })
                                non_compliant_count -= 1
                else:
                    # Nu se încearcă recrearea, doar se marchează
                    results['non_compliant'].append({
                        'agent_id': agent_id,
                        'domain': domain,
                        'site_url': site_url,
                        'qdrant_count': content_status['qdrant_count'],
                        'mongodb_count': content_status['mongodb_count']
                    })
        
        # Raport final
        logger.info("\n" + "="*60)
        logger.info("📊 RAPORT FINAL VALIDARE AGENȚI")
        logger.info("="*60)
        logger.info(f"Total agenți verificați: {total_agents}")
        logger.info(f"✅ Agenți conformi: {compliant_count}")
        logger.info(f"❌ Agenți non-conformi: {non_compliant_count}")
        if recreate:
            logger.info(f"🔄 Agenți recreați: {recreated_count}")
        if delete_if_failed:
            logger.info(f"🗑️  Agenți șterși: {deleted_count}")
        logger.info("="*60)
        
        # Salvează raportul
        report_file = f"/srv/hf/ai_agents/agent_validation_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        import json
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'summary': {
                    'total_agents': total_agents,
                    'compliant_count': compliant_count,
                    'non_compliant_count': non_compliant_count,
                    'recreated_count': recreated_count,
                    'deleted_count': deleted_count
                },
                'results': results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Raport salvat în: {report_file}")
        
        return {
            'total_agents': total_agents,
            'compliant_count': compliant_count,
            'non_compliant_count': non_compliant_count,
            'recreated_count': recreated_count,
            'deleted_count': deleted_count,
            'report_file': report_file
        }

def main():
    """Funcția principală"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validează și corectează agenții non-conformi')
    parser.add_argument('--no-recreate', action='store_true', help='Nu încearcă să recreeze agenții non-conformi')
    parser.add_argument('--no-delete', action='store_true', help='Nu șterge agenții care nu pot fi recreați')
    
    args = parser.parse_args()
    
    validator = AgentValidator()
    
    results = validator.validate_all_agents(
        recreate=not args.no_recreate,
        delete_if_failed=not args.no_delete
    )
    
    # Exit code bazat pe rezultate
    if results['non_compliant_count'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()

