#!/usr/bin/env python3
"""
Sistem refăcut pentru Qdrant - Reindexare vectori pentru toți agenții

Acest script:
1. Verifică toți agenții din MongoDB
2. Pentru fiecare agent, extrage conținutul din MongoDB
3. Generează embeddings și salvează în Qdrant
4. Actualizează vector_collection în MongoDB
"""

import os
import sys
import logging
import asyncio
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_huggingface import HuggingFaceEmbeddings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None

class QdrantReindexer:
    def __init__(self):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client[MONGO_DB]
        self.agents_collection = self.db.site_agents
        self.site_content_collection = self.db.site_content
        
        # Inițializează Qdrant client - nu folosim httpx_client_kwargs (nu e suportat)
        try:
            self.qdrant_client = QdrantClient(
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                prefer_grpc=False,
                check_compatibility=False,
                timeout=60
            )
            # Test conexiune - dacă eșuează, folosim requests direct
            try:
                _ = self.qdrant_client.get_collections()
                logger.info("✅ Conectat la Qdrant cu QdrantClient")
            except:
                logger.warning("⚠️ QdrantClient nu funcționează, folosesc requests direct")
                self.qdrant_client = None
        except Exception as e:
            logger.warning(f"⚠️ Qdrant client nu poate fi inițializat: {e}. Folosesc requests direct")
            self.qdrant_client = None
        
        # Inițializează embeddings
        logger.info("Loading embedding model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        logger.info("✅ Embedding model loaded")
    
    def get_agent_content(self, agent_id: str) -> list:
        """Obține conținutul agentului din MongoDB"""
        chunks = list(self.site_content_collection.find(
            {"agent_id": agent_id},
            sort=[("chunk_index", 1)]
        ))
        return [chunk.get("content", "") for chunk in chunks if chunk.get("content")]
    
    def create_qdrant_collection(self, collection_name: str, force_recreate: bool = False):
        """Creează sau verifică existența colecției Qdrant folosind curl (mai stabil decât requests)"""
        import subprocess
        import json
        import time
        
        # Verifică dacă colecția există cu curl
        try:
            result = subprocess.run(
                ["curl", "-s", f"{QDRANT_URL}/collections/{collection_name}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    if data.get("status") == "ok":
                        existing_points = data.get("result", {}).get("points_count", 0)
                        if force_recreate:
                            logger.info(f"🗑️ Șterge colecția existentă '{collection_name}'...")
                            subprocess.run(
                                ["curl", "-X", "DELETE", "-s", f"{QDRANT_URL}/collections/{collection_name}"],
                                timeout=10
                            )
                        else:
                            logger.info(f"✅ Colecția '{collection_name}' există deja ({existing_points} vectori)")
                            return existing_points
                except:
                    pass  # Nu e JSON valid sau colecția nu există
        except:
            pass  # Eroare la verificare, continuă cu crearea
        
        # Creează colecție nouă cu curl
        logger.info(f"📦 Creează colecție Qdrant '{collection_name}' cu curl...")
        payload = {
            "vectors": {
                "size": 1024,
                "distance": "Cosine"
            }
        }
        
        payload_json = json.dumps(payload)
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Folosește shell=True pentru a evita problemele cu variabilele de mediu
                curl_cmd = f'curl -X PUT "{QDRANT_URL}/collections/{collection_name}" -H "Content-Type: application/json" -d \'{payload_json}\' -s -w "\\nHTTP_CODE:%{{http_code}}"'
                
                result = subprocess.run(
                    curl_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Extrage status code din output
                output = result.stdout
                status_code = 0
                if "HTTP_CODE:" in output:
                    try:
                        status_code = int(output.split("HTTP_CODE:")[-1].strip())
                    except:
                        pass
                
                # Verifică și stderr pentru erori
                error_output = result.stderr
                
                # Verifică status code HTTP
                if status_code in [200, 201]:
                    logger.info(f"✅ Colecția '{collection_name}' creată (HTTP {status_code})")
                    return 0
                
                # IMPORTANT: Verifică ÎNTOTDEAUNA manual dacă colecția există după creare
                # (curl poate returna cod 1 chiar dacă operația a reușit din cauza unor probleme de shell)
                logger.debug(f"Verificare manuală colecție '{collection_name}' după creare...")
                try:
                    check_result = subprocess.run(
                        f'curl -s "{QDRANT_URL}/collections/{collection_name}"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if check_result.returncode == 0 and check_result.stdout:
                        try:
                            check_data = json.loads(check_result.stdout)
                            if check_data.get("status") == "ok":
                                points_count = check_data.get("result", {}).get("points_count", 0)
                                logger.info(f"✅ Colecția '{collection_name}' creată cu succes (verificare manuală: {points_count} vectori)")
                                return points_count
                            else:
                                logger.debug(f"Colecția nu există sau status nu e 'ok': {check_data.get('status')}")
                        except json.JSONDecodeError as e:
                            logger.debug(f"Eroare JSON la verificare: {e}, output: {check_result.stdout[:100]}")
                        except Exception as e:
                            logger.debug(f"Eroare la verificare: {e}")
                    else:
                        logger.debug(f"Verificare eșuată: returncode={check_result.returncode}, stdout={check_result.stdout[:100]}")
                except Exception as e:
                    logger.debug(f"Excepție la verificare manuală: {e}")
                
                # Dacă nici verificarea manuală nu confirmă existența, retry
                error_msg = f"Status HTTP: {status_code}, curl return code: {result.returncode}, stdout: {result.stdout[:100]}"
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Eroare (attempt {attempt + 1}): {error_msg}. Retrying...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    # Ultimă verificare înainte de a arunca eroarea
                    logger.warning(f"⚠️ Ultimă verificare înainte de eroare...")
                    final_check = subprocess.run(
                        f'curl -s "{QDRANT_URL}/collections/{collection_name}"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if final_check.returncode == 0:
                        try:
                            final_data = json.loads(final_check.stdout)
                            if final_data.get("status") == "ok":
                                logger.info(f"✅ Colecția '{collection_name}' există (ultimă verificare)")
                                return final_data.get("result", {}).get("points_count", 0)
                        except:
                            pass
                    
                    raise Exception(f"Failed to create collection after {max_retries} attempts: {error_msg}")
                        
            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Timeout (attempt {attempt + 1}). Retrying în {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise Exception("Timeout after retries")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Eroare (attempt {attempt + 1}): {e}. Retrying...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise
    
    def index_agent_content(self, agent_id: str, agent_doc: dict, force_recreate: bool = False) -> dict:
        """
        Indexează conținutul unui agent în Qdrant
        
        Returns:
            dict cu rezultate: {
                'agent_id': str,
                'collection_name': str,
                'chunks_processed': int,
                'vectors_saved': int,
                'success': bool
            }
        """
        domain = agent_doc.get("domain", "unknown")
        collection_name = f"agent_{agent_id}"
        
        logger.info(f"\n🔍 Indexare agent: {domain} ({agent_id})")
        
        try:
            # Obține conținutul din MongoDB
            chunks = self.get_agent_content(agent_id)
            
            if not chunks:
                logger.warning(f"⚠️ Agent {domain} nu are conținut în MongoDB")
                return {
                    'agent_id': agent_id,
                    'collection_name': collection_name,
                    'chunks_processed': 0,
                    'vectors_saved': 0,
                    'success': False,
                    'error': 'No content in MongoDB'
                }
            
            logger.info(f"📄 Găsite {len(chunks)} chunk-uri în MongoDB")
            
            # Creează sau verifică colecția Qdrant
            existing_points = self.create_qdrant_collection(collection_name, force_recreate)
            
            if not force_recreate and existing_points > 0:
                logger.info(f"⏭️  Colecția '{collection_name}' are deja {existing_points} vectori. Folosește --force pentru reindexare completă.")
                return {
                    'agent_id': agent_id,
                    'collection_name': collection_name,
                    'chunks_processed': len(chunks),
                    'vectors_saved': existing_points,
                    'success': True,
                    'skipped': True
                }
            
            # Generează embeddings și creează points
            logger.info(f"🧮 Generez embeddings pentru {len(chunks)} chunk-uri...")
            points = []
            
            for i, chunk in enumerate(chunks):
                try:
                    # Generează embedding
                    embedding = self.embeddings.embed_query(chunk)
                    
                    # Creează PointStruct
                    points.append(PointStruct(
                        id=i,
                        vector=embedding,
                        payload={
                            'text': chunk,
                            'chunk_index': i,
                            'agent_id': agent_id,
                            'domain': domain,
                            'url': agent_doc.get("site_url", ""),
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                    ))
                    
                    if (i + 1) % 50 == 0:
                        logger.info(f"   Procesat {i + 1}/{len(chunks)} chunk-uri...")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Eroare la procesarea chunk-ului {i}: {e}")
                    continue
            
            if not points:
                logger.error(f"❌ Nu s-au putut genera embeddings pentru agent {domain}")
                return {
                    'agent_id': agent_id,
                    'collection_name': collection_name,
                    'chunks_processed': len(chunks),
                    'vectors_saved': 0,
                    'success': False,
                    'error': 'Failed to generate embeddings'
                }
            
            # Salvează vectorii în Qdrant (în batch-uri pentru performanță)
            logger.info(f"💾 Salvez {len(points)} vectori în Qdrant...")
            batch_size = 50  # Batch mai mic pentru stabilitate
            import requests
            import time
            
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                max_retries = 3
                retry_delay = 1
                
                for attempt in range(max_retries):
                    try:
                        # Folosește curl pentru upsert (mai stabil decât requests)
                        import subprocess
                        import json
                        
                        # Convertește PointStruct la dict pentru JSON
                        batch_dict = []
                        for point in batch:
                            batch_dict.append({
                                "id": point.id,
                                "vector": point.vector,
                                "payload": point.payload
                            })
                        
                        payload_json = json.dumps({"points": batch_dict})
                        
                        curl_cmd = [
                            "curl", "-X", "PUT",
                            f"{QDRANT_URL}/collections/{collection_name}/points",
                            "-H", "Content-Type: application/json",
                            "-d", payload_json,
                            "-s", "-w", "%{http_code}"
                        ]
                        
                        result = subprocess.run(
                            curl_cmd,
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        
                        # Verifică status code
                        output = result.stdout
                        status_code = 0
                        if output and len(output) >= 3:
                            try:
                                status_code = int(output[-3:])
                            except:
                                pass
                        
                        if status_code in [200, 201] or result.returncode == 0:
                            logger.info(f"   ✅ Batch {i//batch_size + 1}/{(len(points)-1)//batch_size + 1} salvat ({len(batch)} vectori)")
                            break  # Succes, iesi din retry loop
                        else:
                            error_msg = f"Status {status_code} sau return code {result.returncode}: {result.stderr[:200] if result.stderr else output[:200]}"
                            if attempt < max_retries - 1:
                                logger.warning(f"⚠️ Eroare batch {i//batch_size + 1} (attempt {attempt + 1}): {error_msg}. Retrying...")
                                time.sleep(retry_delay)
                                retry_delay *= 2
                                continue
                            else:
                                raise Exception(error_msg)
                                
                    except subprocess.TimeoutExpired as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"⚠️ Timeout batch {i//batch_size + 1} (attempt {attempt + 1}): {e}. Retrying în {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            logger.error(f"❌ Timeout la batch-ul {i//batch_size + 1} după {max_retries} încercări")
                            raise
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"⚠️ Eroare batch {i//batch_size + 1} (attempt {attempt + 1}): {e}. Retrying...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            logger.error(f"❌ Eroare la salvarea batch-ului {i//batch_size + 1}: {e}")
                            raise
                
                # Mic delay între batch-uri pentru a nu suprasolicita Qdrant
                if i + batch_size < len(points):
                    time.sleep(0.5)
            
            # Verifică rezultatul folosind curl
            import subprocess
            result = subprocess.run(
                ["curl", "-s", f"{QDRANT_URL}/collections/{collection_name}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    if data.get("status") == "ok":
                        collection_info = data.get("result", {})
                        vectors_count = collection_info.get("points_count", 0)
                    else:
                        vectors_count = len(points)  # Fallback
                except:
                    vectors_count = len(points)  # Fallback
            else:
                vectors_count = len(points)  # Fallback
            
            # Actualizează vector_collection în MongoDB
            self.agents_collection.update_one(
                {"_id": ObjectId(agent_id)},
                {"$set": {
                    "vector_collection": collection_name,
                    "qdrant_indexed": True,
                    "qdrant_indexed_at": datetime.now(timezone.utc),
                    "qdrant_vectors_count": vectors_count
                }}
            )
            
            logger.info(f"✅ Agent {domain} indexat cu succes: {vectors_count} vectori în Qdrant")
            
            return {
                'agent_id': agent_id,
                'collection_name': collection_name,
                'chunks_processed': len(chunks),
                'vectors_saved': vectors_count,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"❌ Eroare la indexarea agentului {domain}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'agent_id': agent_id,
                'collection_name': collection_name,
                'chunks_processed': 0,
                'vectors_saved': 0,
                'success': False,
                'error': str(e)
            }
    
    def reindex_all_agents(self, force_recreate: bool = False):
        """Reindexează toți agenții"""
        logger.info("🚀 Începe reindexarea tuturor agenților în Qdrant...\n")
        
        agents = list(self.agents_collection.find({}))
        total_agents = len(agents)
        
        logger.info(f"📊 Total agenți de indexat: {total_agents}\n")
        
        results = {
            'total': total_agents,
            'success': [],
            'failed': [],
            'skipped': []
        }
        
        for i, agent in enumerate(agents, 1):
            agent_id = str(agent["_id"])
            domain = agent.get("domain", "unknown")
            
            logger.info(f"[{i}/{total_agents}] Procesez agent: {domain}")
            
            result = self.index_agent_content(agent_id, agent, force_recreate)
            
            if result.get('success'):
                if result.get('skipped'):
                    results['skipped'].append(result)
                else:
                    results['success'].append(result)
            else:
                results['failed'].append(result)
        
        # Raport final
        logger.info("\n" + "="*60)
        logger.info("📊 RAPORT FINAL REINDEXARE QDRANT")
        logger.info("="*60)
        logger.info(f"Total agenți: {total_agents}")
        logger.info(f"✅ Indexați cu succes: {len(results['success'])}")
        logger.info(f"⏭️  Săriți (deja indexați): {len(results['skipped'])}")
        logger.info(f"❌ Eșuați: {len(results['failed'])}")
        
        if results['success']:
            total_vectors = sum(r['vectors_saved'] for r in results['success'])
            logger.info(f"📊 Total vectori salvați: {total_vectors}")
        
        logger.info("="*60)
        
        # Salvează raportul
        import json
        report_file = f"/srv/hf/ai_agents/qdrant_reindex_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'summary': {
                    'total_agents': total_agents,
                    'success_count': len(results['success']),
                    'skipped_count': len(results['skipped']),
                    'failed_count': len(results['failed']),
                    'total_vectors': sum(r['vectors_saved'] for r in results['success'])
                },
                'results': results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Raport salvat în: {report_file}")
        
        return results

def main():
    """Funcția principală"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reindexează toți agenții în Qdrant')
    parser.add_argument('--force', action='store_true', help='Forțează reindexarea completă (șterge colecțiile existente)')
    
    args = parser.parse_args()
    
    reindexer = QdrantReindexer()
    results = reindexer.reindex_all_agents(force_recreate=args.force)
    
    # Exit code
    if results['failed']:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()

