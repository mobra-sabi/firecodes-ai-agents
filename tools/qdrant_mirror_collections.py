#!/usr/bin/env python3
"""
Qdrant Mirror Collections - Colecții specifice per site pentru Mirror Q/A
Issue 2: Creează colecțiile Qdrant pentru noul site
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, CollectionStatus,
    PointStruct, Filter, FieldCondition, MatchValue,
    CreateCollection, CollectionInfo
)
from qdrant_client.http.exceptions import UnexpectedResponse
import uuid

logger = logging.getLogger(__name__)

class QdrantMirrorCollections:
    """Manager pentru colecțiile Qdrant specifice per site"""
    
    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        self.client = QdrantClient(url=qdrant_url)
        self.embedding_dim = 1536  # BAAI/bge-large-en-v1.5
        
    def generate_site_id(self, domain: str) -> str:
        """Generează un site_id unic bazat pe domeniu"""
        # Normalizează domeniul
        domain_clean = domain.replace("https://", "").replace("http://", "").replace("www.", "")
        domain_clean = domain_clean.replace(".", "_").replace("-", "_")
        
        # Generează ID unic
        timestamp = int(time.time())
        site_id = f"{domain_clean}_{timestamp}"
        
        return site_id
    
    async def create_mirror_collections(self, site_id: str, domain: str) -> Dict[str, Any]:
        """
        Creează colecțiile specifice pentru un site:
        - mem_<site_id>_pages (conținut integral)
        - mem_<site_id>_faq (întrebări validate)
        """
        try:
            logger.info(f"🏗️ Creating mirror collections for site: {site_id}")
            
            collections_created = {}
            
            # 1. Colecția pentru pagini (conținut integral)
            pages_collection = f"mem_{site_id}_pages"
            pages_result = await self._create_pages_collection(pages_collection, domain)
            collections_created["pages"] = pages_result
            
            # 2. Colecția pentru FAQ (întrebări validate)
            faq_collection = f"mem_{site_id}_faq"
            faq_result = await self._create_faq_collection(faq_collection, domain)
            collections_created["faq"] = faq_result
            
            # 3. Salvează metadata în MongoDB
            await self._save_collections_metadata(site_id, domain, collections_created)
            
            result = {
                "site_id": site_id,
                "domain": domain,
                "collections": collections_created,
                "status": "created",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "embedding_dim": self.embedding_dim
            }
            
            logger.info(f"✅ Mirror collections created successfully for {site_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error creating mirror collections: {e}")
            raise
    
    async def _create_pages_collection(self, collection_name: str, domain: str) -> Dict[str, Any]:
        """Creează colecția pentru pagini cu schema completă"""
        try:
            # Verifică dacă colecția există deja
            try:
                collection_info = self.client.get_collection(collection_name)
                logger.info(f"📁 Collection {collection_name} already exists")
                return {
                    "name": collection_name,
                    "status": "exists",
                    "vectors_count": collection_info.vectors_count,
                    "schema": "pages_schema"
                }
            except UnexpectedResponse:
                # Colecția nu există, o creez
                pass
            
            # Creează colecția pentru pagini
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"✅ Created pages collection: {collection_name}")
            
            return {
                "name": collection_name,
                "status": "created",
                "vectors_count": 0,
                "schema": "pages_schema",
                "description": f"Pages content for {domain}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating pages collection {collection_name}: {e}")
            raise
    
    async def _create_faq_collection(self, collection_name: str, domain: str) -> Dict[str, Any]:
        """Creează colecția pentru FAQ cu schema completă"""
        try:
            # Verifică dacă colecția există deja
            try:
                collection_info = self.client.get_collection(collection_name)
                logger.info(f"📁 Collection {collection_name} already exists")
                return {
                    "name": collection_name,
                    "status": "exists",
                    "vectors_count": collection_info.vectors_count,
                    "schema": "faq_schema"
                }
            except UnexpectedResponse:
                # Colecția nu există, o creez
                pass
            
            # Creează colecția pentru FAQ
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"✅ Created FAQ collection: {collection_name}")
            
            return {
                "name": collection_name,
                "status": "created",
                "vectors_count": 0,
                "schema": "faq_schema",
                "description": f"FAQ content for {domain}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating FAQ collection {collection_name}: {e}")
            raise
    
    async def _save_collections_metadata(self, site_id: str, domain: str, collections: Dict[str, Any]) -> None:
        """Salvează metadata colecțiilor în MongoDB"""
        try:
            from pymongo import MongoClient
            
            client = MongoClient('mongodb://localhost:9308')
            db = client['ai_agents_db']
            
            metadata = {
                "site_id": site_id,
                "domain": domain,
                "collections": collections,
                "created_at": datetime.now(timezone.utc),
                "status": "active",
                "schema_version": "1.0"
            }
            
            db.mirror_collections.insert_one(metadata)
            logger.info(f"💾 Saved collections metadata for {site_id}")
            
        except Exception as e:
            logger.error(f"❌ Error saving collections metadata: {e}")
            raise
    
    async def get_collections_info(self, site_id: str) -> Dict[str, Any]:
        """Obține informațiile despre colecțiile unui site"""
        try:
            pages_collection = f"mem_{site_id}_pages"
            faq_collection = f"mem_{site_id}_faq"
            
            collections_info = {}
            
            # Informații colecție pages
            try:
                pages_info = self.client.get_collection(pages_collection)
                collections_info["pages"] = {
                    "name": pages_collection,
                    "vectors_count": pages_info.vectors_count,
                    "status": pages_info.status,
                    "schema": "pages_schema"
                }
            except UnexpectedResponse:
                collections_info["pages"] = {"status": "not_found"}
            
            # Informații colecție FAQ
            try:
                faq_info = self.client.get_collection(faq_collection)
                collections_info["faq"] = {
                    "name": faq_collection,
                    "vectors_count": faq_info.vectors_count,
                    "status": faq_info.status,
                    "schema": "faq_schema"
                }
            except UnexpectedResponse:
                collections_info["faq"] = {"status": "not_found"}
            
            return {
                "site_id": site_id,
                "collections": collections_info,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting collections info: {e}")
            raise
    
    async def delete_mirror_collections(self, site_id: str) -> Dict[str, Any]:
        """Șterge colecțiile unui site"""
        try:
            pages_collection = f"mem_{site_id}_pages"
            faq_collection = f"mem_{site_id}_faq"
            
            deleted_collections = []
            
            # Șterge colecția pages
            try:
                self.client.delete_collection(pages_collection)
                deleted_collections.append(pages_collection)
                logger.info(f"🗑️ Deleted pages collection: {pages_collection}")
            except UnexpectedResponse:
                logger.warning(f"⚠️ Pages collection {pages_collection} not found")
            
            # Șterge colecția FAQ
            try:
                self.client.delete_collection(faq_collection)
                deleted_collections.append(faq_collection)
                logger.info(f"🗑️ Deleted FAQ collection: {faq_collection}")
            except UnexpectedResponse:
                logger.warning(f"⚠️ FAQ collection {faq_collection} not found")
            
            # Șterge metadata din MongoDB
            try:
                from pymongo import MongoClient
                client = MongoClient('mongodb://localhost:9308')
                db = client['ai_agents_db']
                db.mirror_collections.delete_many({"site_id": site_id})
                logger.info(f"🗑️ Deleted metadata for site: {site_id}")
            except Exception as e:
                logger.warning(f"⚠️ Error deleting metadata: {e}")
            
            return {
                "site_id": site_id,
                "deleted_collections": deleted_collections,
                "status": "deleted",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error deleting mirror collections: {e}")
            raise
    
    async def list_all_mirror_collections(self) -> List[Dict[str, Any]]:
        """Listează toate colecțiile mirror"""
        try:
            collections = self.client.get_collections()
            mirror_collections = []
            
            for collection in collections.collections:
                if collection.name.startswith("mem_") and ("_pages" in collection.name or "_faq" in collection.name):
                    # Obține informații detaliate despre colecție
                    try:
                        collection_info = self.client.get_collection(collection.name)
                        mirror_collections.append({
                            "name": collection.name,
                            "vectors_count": collection_info.vectors_count,
                            "status": collection_info.status,
                            "created_at": getattr(collection_info, 'created_at', None)
                        })
                    except Exception as e:
                        mirror_collections.append({
                            "name": collection.name,
                            "vectors_count": 0,
                            "status": "unknown",
                            "created_at": None
                        })
            
            return mirror_collections
            
        except Exception as e:
            logger.error(f"❌ Error listing mirror collections: {e}")
            raise
    
    async def add_faq_to_site(self, site_id: str, question: str, answer: str) -> dict:
        """Adaugă un FAQ în colecția site-ului"""
        try:
            # Generează embedding pentru întrebare și răspuns
            import requests
            
            # Folosește Ollama pentru embeddings (768 dimensiuni)
            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": question
                },
                timeout=10
            )
            
            if response.status_code == 200:
                question_embedding = response.json()["embedding"]
                # Convertește la listă Python pentru serializare JSON
                question_embedding = [float(x) for x in question_embedding]
            else:
                # Fallback la embedding zero
                question_embedding = [0.0] * 768
            
            # Creează punctul pentru FAQ
            import uuid
            faq_point = {
                "id": str(uuid.uuid4()),
                "vector": question_embedding,
                "payload": {
                    "question": question,
                    "answer": answer,
                    "site_id": site_id,
                    "type": "faq",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Adaugă în colecția FAQ
            faq_collection = f"mem_{site_id}_faq"
            
            # Verifică dacă colecția există
            try:
                self.client.get_collection(faq_collection)
            except:
                # Creează colecția dacă nu există
                self.client.create_collection(
                    collection_name=faq_collection,
                    vectors_config={"size": 768, "distance": "Cosine"}
                )
            
            # Adaugă punctul
            self.client.upsert(
                collection_name=faq_collection,
                points=[faq_point]
            )
            
            return {
                "ok": True,
                "message": f"FAQ added to {faq_collection}",
                "question": question,
                "answer": answer,
                "site_id": site_id
            }
            
        except Exception as e:
            logger.error(f"Error adding FAQ to site {site_id}: {e}")
            return {
                "ok": False,
                "error": str(e)
            }

# Funcții de utilitate pentru API
async def create_mirror_collections_for_site(domain: str) -> Dict[str, Any]:
    """Creează colecțiile mirror pentru un site"""
    try:
        collections_manager = QdrantMirrorCollections()
        
        # Generează site_id
        site_id = collections_manager.generate_site_id(domain)
        
        # Creează colecțiile
        result = await collections_manager.create_mirror_collections(site_id, domain)
        
        return {
            "ok": True,
            "message": f"Mirror collections created for {domain}",
            "site_id": site_id,
            "domain": domain,
            "collections": result["collections"],
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating mirror collections for site: {e}")
        return {
            "ok": False,
            "error": str(e)
        }
    
    async def add_faq_to_site(self, site_id: str, question: str, answer: str) -> dict:
        """Adaugă un FAQ în colecția site-ului"""
        try:
            # Generează embedding pentru întrebare și răspuns
            import requests
            
            # Folosește Ollama pentru embeddings (768 dimensiuni)
            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": question
                },
                timeout=10
            )
            
            if response.status_code == 200:
                question_embedding = response.json()["embedding"]
                # Convertește la listă Python pentru serializare JSON
                question_embedding = [float(x) for x in question_embedding]
            else:
                # Fallback la embedding zero
                question_embedding = [0.0] * 768
            
            # Creează punctul pentru FAQ
            import uuid
            faq_point = {
                "id": str(uuid.uuid4()),
                "vector": question_embedding,
                "payload": {
                    "question": question,
                    "answer": answer,
                    "site_id": site_id,
                    "type": "faq",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Adaugă în colecția FAQ
            faq_collection = f"mem_{site_id}_faq"
            
            # Verifică dacă colecția există
            try:
                self.client.get_collection(faq_collection)
            except:
                # Creează colecția dacă nu există
                self.client.create_collection(
                    collection_name=faq_collection,
                    vectors_config={"size": 768, "distance": "Cosine"}
                )
            
            # Adaugă punctul
            self.client.upsert(
                collection_name=faq_collection,
                points=[faq_point]
            )
            
            return {
                "ok": True,
                "message": f"FAQ added to {faq_collection}",
                "question": question,
                "answer": answer,
                "site_id": site_id
            }
            
        except Exception as e:
            logger.error(f"Error adding FAQ to site {site_id}: {e}")
            return {
                "ok": False,
                "error": str(e)
            }

if __name__ == "__main__":
    # Test
    async def test_mirror_collections():
        collections_manager = QdrantMirrorCollections()
        
        # Test cu matari-antifoc.ro
        domain = "matari-antifoc.ro"
        result = await create_mirror_collections_for_site(domain)
        
        print("🧪 Mirror Collections Test:")
        print("=" * 50)
        print(f"Domain: {domain}")
        print(f"Site ID: {result.get('site_id', 'N/A')}")
        print(f"Status: {result.get('status', 'N/A')}")
        print(f"Collections: {result.get('collections', {})}")
    
    asyncio.run(test_mirror_collections())
