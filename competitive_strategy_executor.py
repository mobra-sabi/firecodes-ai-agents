#!/usr/bin/env python3
"""
Executor pentru strategia competitivă:
- SERP search pentru fiecare keyword
- Creare slave agents pentru primele 20 site-uri
- Ranking și hartă competitivă
"""

import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import asyncio

logger = logging.getLogger(__name__)

class CompetitiveStrategyExecutor:
    """Execută strategia competitivă: SERP + Slave Agents + Ranking"""
    
    def __init__(self):
        from config.database_config import MONGODB_URI, MONGODB_DATABASE
        mongo_uri = os.getenv("MONGODB_URI", MONGODB_URI)
        db_name = os.getenv("MONGODB_DATABASE", MONGODB_DATABASE)
        
        self.mongo = MongoClient(mongo_uri)
        self.db = self.mongo[db_name]
        # Folosește site_agents dacă există, altfel agents
        collections = self.db.list_collection_names()
        if 'site_agents' in collections:
            self.agents_collection = self.db.site_agents
        else:
            self.agents_collection = self.db.agents
        self.serp_results_collection = self.db.serp_results
        self.competitive_map_collection = self.db.competitive_map
    
    async def execute_strategy(
        self,
        agent_id: str,
        keywords: List[str],
        results_per_keyword: int = 20
    ) -> Dict:
        """
        Execută strategia competitivă completă
        
        Args:
            agent_id: ID-ul agentului master
            keywords: Lista de keywords pentru analiză
            results_per_keyword: Câte rezultate Google per keyword (default 20)
        
        Returns:
            {
                "ok": True,
                "keywords_processed": 5,
                "sites_found": 100,
                "slave_agents_created": 20,
                "competitive_map": {...}
            }
        """
        try:
            agent = self.agents_collection.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return {"ok": False, "error": "Agent not found"}
            
            domain = agent.get("domain", "")
            
            # 1. SERP Search pentru fiecare keyword - OPTIMIZAT PARALEL
            logger.info(f"🔍 Starting PARALLEL SERP search for {len(keywords)} keywords")
            
            from unified_serp_search import search as unified_search
            from urllib.parse import urlparse
            
            async def search_keyword(keyword: str):
                """Caută un keyword și returnează rezultatele"""
                try:
                    logger.info(f"   Searching: {keyword}")
                    # Folosește funcția search din unified_serp_search (are cache!)
                    # Dacă search este sync, rulează în thread pool pentru paralelism
                    loop = asyncio.get_event_loop()
                    serp_results = await loop.run_in_executor(
                        None,
                        lambda: unified_search(
                            query=keyword,
                            num_results=results_per_keyword
                        )
                    )
                    
                    # Transformă rezultatele în formatul așteptat
                    formatted_results = []
                    for i, result in enumerate(serp_results):
                        url = result.get("url", "")
                        parsed = urlparse(url)
                        domain = parsed.netloc.replace("www.", "")
                        
                        formatted_result = {
                            "url": url,
                            "title": result.get("title", ""),
                            "position": i + 1,
                            "domain": domain,
                            "snippet": result.get("description", ""),
                            "keyword": keyword
                        }
                        formatted_results.append(formatted_result)
                    
                    # Salvează rezultatele în MongoDB (batch pentru performanță)
                    if formatted_results:
                        bulk_ops = []
                        for result in formatted_results:
                            bulk_ops.append({
                                "updateOne": {
                                    "filter": {
                                        "agent_id": agent_id,
                                        "keyword": keyword,
                                        "url": result.get("url", "")
                                    },
                                    "update": {
                                        "$set": {
                                            "agent_id": agent_id,
                                            "keyword": keyword,
                                            "url": result.get("url", ""),
                                            "title": result.get("title", ""),
                                            "position": result.get("position", 0),
                                            "domain": result.get("domain", ""),
                                            "snippet": result.get("snippet", ""),
                                            "search_date": datetime.now(timezone.utc)
                                        }
                                    },
                                    "upsert": True
                                }
                            })
                        
                        if bulk_ops:
                            self.serp_results_collection.bulk_write(bulk_ops)
                    
                    return formatted_results
                    
                except Exception as e:
                    logger.error(f"Error searching keyword {keyword}: {e}")
                    return []
            
            # Procesare PARALELĂ - 10 keywords simultan (optimizat pentru API rate limits)
            batch_size = 10
            all_serp_results = []
            keywords_processed = 0
            
            for i in range(0, len(keywords), batch_size):
                batch = keywords[i:i+batch_size]
                logger.info(f"   Processing batch {i//batch_size + 1}/{(len(keywords)-1)//batch_size + 1}: {len(batch)} keywords")
                
                # Rulează batch-ul în paralel
                batch_results = await asyncio.gather(*[search_keyword(kw) for kw in batch])
                
                # Adaugă rezultatele
                for results in batch_results:
                    all_serp_results.extend(results)
                    keywords_processed += 1
                
                logger.info(f"   ✅ Batch completed: {keywords_processed}/{len(keywords)} keywords processed")
            
            # 2. Extrage site-uri unice și calculează ranking cu detalii complete
            unique_sites = {}
            keyword_site_mapping = {}  # Mapare keyword → lista de site-uri cu poziții
            
            for result in all_serp_results:
                site_domain = result.get("domain", "")
                if not site_domain or site_domain == domain:
                    continue
                
                keyword = result.get("keyword", "")
                position = result.get("position", 100)
                
                # Construiește maparea keyword → site-uri
                if keyword not in keyword_site_mapping:
                    keyword_site_mapping[keyword] = []
                
                keyword_site_mapping[keyword].append({
                    "domain": site_domain,
                    "position": position,
                    "url": result.get("url", f"https://{site_domain}"),
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", "")
                })
                
                # Construiește structura de site-uri unice
                if site_domain not in unique_sites:
                    unique_sites[site_domain] = {
                        "domain": site_domain,
                        "appearances": 0,
                        "best_position": 100,
                        "keywords": [],
                        "keyword_positions": [],  # Lista de {keyword, position}
                        "total_rank": 0
                    }
                
                unique_sites[site_domain]["appearances"] += 1
                if position < unique_sites[site_domain]["best_position"]:
                    unique_sites[site_domain]["best_position"] = position
                
                if keyword not in unique_sites[site_domain]["keywords"]:
                    unique_sites[site_domain]["keywords"].append(keyword)
                
                # Salvează keyword și poziția pentru acest site
                unique_sites[site_domain]["keyword_positions"].append({
                    "keyword": keyword,
                    "position": position
                })
                
                # Calculează rank (mai mic = mai bun)
                unique_sites[site_domain]["total_rank"] += position
            
            # Sortează după ranking (mai mic = mai competitiv)
            sorted_sites = sorted(
                unique_sites.values(),
                key=lambda x: (x["total_rank"] / max(x["appearances"], 1), x["best_position"])
            )
            
            # 3. Salvează site-urile găsite FĂRĂ să creeze agenții automat
            logger.info(f"📊 Found {len(sorted_sites)} unique sites. Saving for review...")
            
            # Pregătește datele pentru hartă (fără slave_agent_id încă)
            competitive_map_data = []
            for i, site in enumerate(sorted_sites):
                # Verifică dacă există deja agent pentru acest site
                existing_slave = self.agents_collection.find_one({
                    "domain": site["domain"],
                    "master_agent_id": agent_id
                })
                
                competitive_map_data.append({
                    "domain": site["domain"],
                    "url": f"https://{site['domain']}",
                    "rank": i + 1,
                    "appearances": site["appearances"],
                    "best_position": site["best_position"],
                    "total_rank": site["total_rank"],
                    "keywords": site["keywords"],
                    "keyword_positions": site.get("keyword_positions", []),  # Lista de {keyword, position}
                    "relevance_score": 100 - (i * 2),  # Scor de relevanță (va fi actualizat de DeepSeek)
                    "selected": False,  # Utilizatorul va selecta
                    "slave_agent_id": str(existing_slave["_id"]) if existing_slave else None,
                    "has_agent": existing_slave is not None
                })
            
            # 4. Salvează harta competitivă (fără agenți creați încă)
            self.competitive_map_collection.update_one(
                {"master_agent_id": agent_id},
                {
                    "$set": {
                        "master_agent_id": agent_id,
                        "domain": domain,
                        "keywords_used": keywords,
                        "sites_found": len(unique_sites),
                        "slave_agents_created": 0,  # Nu creăm agenți automat
                        "competitive_map": competitive_map_data,
                        "keyword_site_mapping": keyword_site_mapping,  # Mapare keyword → site-uri cu poziții
                        "status": "pending_review",  # Așteaptă review de la utilizator
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            
            return {
                "ok": True,
                "keywords_processed": keywords_processed,
                "sites_found": len(unique_sites),
                "slave_agents_created": 0,  # Nu creăm agenți automat
                "competitive_map": competitive_map_data,
                "message": f"Strategy executed: {keywords_processed} keywords, {len(unique_sites)} sites found. Review and select sites to create agents."
            }
            
        except Exception as e:
            logger.error(f"Error executing competitive strategy: {e}")
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}

