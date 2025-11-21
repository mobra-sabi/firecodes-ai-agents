"""
Industry Indexer - Indexare automată a competitorilor și resurselor industriale
Faza 1: Indexare Bază
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Import funcțiile existente
from site_agent_creator import create_agent_logic, send_status as send_status_creator
from competitor_discovery import discover_competitors_from_strategy
from competitive_strategy import strategy_generator

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
agents_collection = db.site_agents
industry_resources_collection = db.industry_resources
strategies_collection = db.competitive_strategies


async def index_industry_for_agent(
    agent_id: str,
    max_sites: int = 20,
    concurrency: int = 8,
    loop=None,
    websocket=None
) -> Dict[str, Any]:
    """
    Indexează industria completă pentru un agent:
    1. Obține strategia competitivă DeepSeek
    2. Descoperă competitori folosind web search
    3. Indexează fiecare site descoperit
    
    Args:
        agent_id: ID-ul agentului principal
        max_sites: Număr maxim de site-uri de indexat
        loop: Event loop pentru async
        websocket: WebSocket pentru status updates
    
    Returns:
        Dict cu rezultatele indexării
    """
    try:
        logger.info(f"🚀 Încep indexarea industriei pentru agent {agent_id}...")
        
        if websocket:
            await send_status_creator(websocket, "progress", "🚀 Încep indexarea industriei...")
        
        # 1. Obține agentul principal
        agent = agents_collection.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise ValueError(f"Agent {agent_id} nu există")
        
        main_domain = agent.get("domain", "")
        main_url = agent.get("site_url", f"https://{main_domain}")
        
        logger.info(f"   Agent principal: {main_domain}")
        
        if websocket:
            await send_status_creator(websocket, "progress", f"📋 Obțin strategia competitivă pentru {main_domain}...")
        
        # 2. Obține strategia competitivă DeepSeek
        strategy_doc = strategies_collection.find_one({"agent_id": agent_id})
        if not strategy_doc:
            # Dacă nu există strategie, o generează acum
            logger.info(f"   ⚠️ Nu există strategie - generează strategie competitivă...")
            if websocket:
                await send_status_creator(websocket, "progress", "🤖 Generez strategie competitivă cu DeepSeek...")
            
            strategy = await strategy_generator.analyze_agent_and_generate_strategy(agent_id)
        else:
            strategy = strategy_doc.get("strategy", {})
        
        if not strategy:
            raise ValueError(f"Nu s-a putut obține strategia pentru agent {agent_id}")
        
        logger.info(f"   ✅ Strategie obținută: {len(strategy.get('services', []))} servicii identificate")
        
        if websocket:
            await send_status_creator(websocket, "progress", f"✅ Strategie obținută: {len(strategy.get('services', []))} servicii")
        
        # 3. Descoperă competitori folosind strategia
        if websocket:
            await send_status_creator(websocket, "progress", "🔍 Descoper competitori prin web search...")
        
        # Exclude domain-ul principal
        exclude_domains = {main_domain}
        discovered_sites = discover_competitors_from_strategy(
            strategy,
            exclude_domains=exclude_domains
        )
        
        # Limitează la max_sites
        discovered_sites = discovered_sites[:max_sites]
        
        logger.info(f"   ✅ Descoperit {len(discovered_sites)} site-uri pentru indexare")
        
        if websocket:
            await send_status_creator(websocket, "progress", f"✅ Descoperit {len(discovered_sites)} site-uri pentru indexare")
        
        # 4. Indexează fiecare site descoperit (PARALEL, cu limită de concurență)
        indexed_sites: List[Dict[str, Any]] = []
        failed_sites: List[Dict[str, Any]] = []

        sem = asyncio.Semaphore(max(1, int(concurrency)))

        async def _index_one(idx: int, site_info: Dict[str, Any]) -> Dict[str, Any]:
            url = site_info.get("url", "")
            domain = site_info.get("domain", "")
            service_name = site_info.get("service_name", "")
            async with sem:
                logger.info(f"   [{idx}/{len(discovered_sites)}] Indexez: {domain} (serviciu: {service_name})")
                if websocket:
                    await send_status_creator(websocket, "progress", f"📊 [{idx}/{len(discovered_sites)}] Indexez: {domain}...")
                try:
                    result = await index_site_as_industry_resource(
                        url=url,
                        main_agent_id=agent_id,
                        service_name=service_name,
                        discovery_info=site_info,
                        loop=loop,
                        websocket=websocket
                    )
                    if result.get("success"):
                        logger.info(
                            f"      ✅ Indexat: {domain} ({result.get('chunks_count', 0)} chunks, {result.get('vectors_count', 0)} vectors)"
                        )
                        return {
                            "ok": True,
                            "url": url,
                            "domain": domain,
                            "service_name": service_name,
                            "resource_id": result.get("resource_id"),
                            "chunks_count": result.get("chunks_count", 0),
                            "vectors_count": result.get("vectors_count", 0),
                        }
                    else:
                        return {"ok": False, "url": url, "domain": domain, "error": result.get("error", "Unknown")}
                except Exception as e:
                    logger.error(f"      ❌ Eroare la indexarea {domain}: {e}")
                    return {"ok": False, "url": url, "domain": domain, "error": str(e)}

        tasks = [_index_one(i, info) for i, info in enumerate(discovered_sites, 1)]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        for r in results:
            if r.get("ok"):
                indexed_sites.append({
                    "url": r["url"],
                    "domain": r["domain"],
                    "service_name": r["service_name"],
                    "agent_id": r.get("resource_id"),
                    "chunks_count": r.get("chunks_count", 0),
                    "vectors_count": r.get("vectors_count", 0)
                })
            else:
                failed_sites.append({"url": r.get("url"), "domain": r.get("domain"), "error": r.get("error", "Unknown")})
        
        # 5. Salvează rezumatul indexării
        summary = {
            "main_agent_id": agent_id,
            "main_domain": main_domain,
            "total_discovered": len(discovered_sites),
            "total_indexed": len(indexed_sites),
            "total_failed": len(failed_sites),
            "indexed_sites": indexed_sites,
            "failed_sites": failed_sites,
            "indexing_date": datetime.now(timezone.utc),
            "strategy_used": {
                "services_count": len(strategy.get("services", [])),
                "strategy_date": strategy_doc.get("created_at") if strategy_doc else None
            }
        }
        
        # Salvează în MongoDB
        industry_resources_collection.insert_one(summary)
        
        logger.info(f"✅ Indexarea industriei finalizată:")
        logger.info(f"   Total descoperit: {len(discovered_sites)}")
        logger.info(f"   Total indexat cu succes: {len(indexed_sites)}")
        logger.info(f"   Total eșuat: {len(failed_sites)}")
        
        if websocket:
            await send_status_creator(websocket, "final", {
                "message": f"✅ Indexarea industriei finalizată!",
                "summary": {
                    "total_discovered": len(discovered_sites),
                    "total_indexed": len(indexed_sites),
                    "total_failed": len(failed_sites)
                }
            })
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Eroare la indexarea industriei: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        if websocket:
            await send_status_creator(websocket, "error", f"❌ Eroare: {e}")
        
        raise


async def index_site_as_industry_resource(
    url: str,
    main_agent_id: str,
    service_name: str,
    discovery_info: Dict[str, Any],
    loop=None,
    websocket=None
) -> Dict[str, Any]:
    """
    Indexează un site ca resursă industrială (fără să creeze agent complet)
    Folosește logica de indexare din create_agent_logic dar salvează cu tag 'industry_resource'
    """
    try:
        from site_agent_creator import (
            crawl_and_scrape_site,
            _norm_domain_from_url,
            db,
            QDRANT_URL,
            QDRANT_API_KEY,
            embeddings
        )
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from bson import ObjectId
        from datetime import datetime, timezone
        
        domain = _norm_domain_from_url(url)
        
        # 1. Crawl site-ul
        content = await asyncio.to_thread(crawl_and_scrape_site, url, loop, websocket)
        if not content:
            return {"success": False, "error": "Content extraction failed"}
        
        # 2. Chunk content
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=50000,
            chunk_overlap=5000,
            length_function=len
        )
        chunks = text_splitter.split_text(content)
        
        # 3. Salvează în MongoDB
        site_content_docs = []
        for i, chunk in enumerate(chunks):
            site_content_docs.append({
                "agent_id": main_agent_id,  # Link la agentul principal
                "resource_type": "industry_resource",
                "resource_url": url,
                "resource_domain": domain,
                "service_name": service_name,
                "chunk_index": i,
                "content": chunk,
                "url": url,
                "discovery_info": discovery_info,
                "metadata": {
                    "total_chunks": len(chunks),
                    "chunk_index": i,
                    "timestamp": datetime.now(timezone.utc)
                },
                "created_at": datetime.now(timezone.utc)
            })
        
        if site_content_docs:
            db.site_content.insert_many(site_content_docs)
            logger.info(f"      ✅ Salvat {len(site_content_docs)} chunks în MongoDB")
        
        # 4. Generează embeddings și salvează în Qdrant
        collection_name = f"industry_{main_agent_id}"
        
        try:
            qdrant_client = QdrantClient(
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                prefer_grpc=True,
                force_disable_check_same_thread=True
            )
            
            # Verifică dacă colecția există, altfel o creează
            try:
                qdrant_client.get_collection(collection_name)
            except:
                qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=1024,
                        distance=Distance.COSINE
                    )
                )
            
            # Generează embeddings și salvează
            points = []
            for i, chunk in enumerate(chunks):
                embedding = embeddings.embed_query(chunk)
                points.append(PointStruct(
                    id=f"{domain}_{i}",  # ID unic pentru fiecare chunk
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "content": chunk,
                        "chunk_index": i,
                        "agent_id": main_agent_id,
                        "resource_type": "industry_resource",
                        "resource_url": url,
                        "resource_domain": domain,
                        "service_name": service_name,
                        "url": url
                    }
                ))
            
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            logger.info(f"      ✅ Salvat {len(points)} vectors în Qdrant")
            
        except Exception as e:
            logger.warning(f"      ⚠️ Eroare Qdrant pentru {domain}: {e}")
            # Continuă chiar dacă Qdrant eșuează
        
        # 5. Salvează metadatele resursei
        resource_doc = {
            "main_agent_id": main_agent_id,
            "resource_type": "industry_resource",
            "resource_url": url,
            "resource_domain": domain,
            "service_name": service_name,
            "discovery_info": discovery_info,
            "chunks_count": len(chunks),
            "vectors_count": len(chunks),  # Aproximativ (după Qdrant upsert)
            "indexing_date": datetime.now(timezone.utc),
            "status": "indexed"
        }
        
        db.industry_resources.insert_one(resource_doc)
        
        return {
            "success": True,
            "resource_id": str(resource_doc.get("_id", "")),
            "chunks_count": len(chunks),
            "vectors_count": len(chunks),
            "domain": domain
        }
        
    except Exception as e:
        logger.error(f"❌ Eroare la indexarea resursei {url}: {e}")
        return {"success": False, "error": str(e)}


