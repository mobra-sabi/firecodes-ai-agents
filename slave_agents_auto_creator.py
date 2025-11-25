#!/usr/bin/env python3
"""
Slave Agents Auto Creator - Creează slave agents pentru toți competitorii în paralel
"""

import asyncio
import logging
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from full_agent_creator import FullAgentCreator
from typing import List, Dict
import concurrent.futures

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlaveAgentsAutoCreator:
    """
    Creare automată de slave agents pentru competitori
    
    Features:
    1. Procesare paralel pe multiple GPU-uri
    2. Priority queue (top competitori first)
    3. Resume capability (skip existing)
    4. Progress tracking în MongoDB
    """
    
    def __init__(self, max_parallel: int = None):
        """
        Inițializează creator-ul de slave agents
        
        Args:
            max_parallel: Număr maxim de agenți în paralel. Dacă None, detectează automat GPU-urile.
        """
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        
        # Detectează automat numărul de GPU-uri dacă max_parallel nu este specificat
        if max_parallel is None:
            try:
                import torch
                if torch.cuda.is_available():
                    num_gpus = torch.cuda.device_count()
                    overhead_workers = 2  # Pentru I/O, scraping, MongoDB, etc.
                    max_parallel = num_gpus + overhead_workers
                    logger.info(f"✅ GPU-uri detectate: {num_gpus} | Worker-uri paralele: {max_parallel} (optimizat pentru utilizare maximă)")
                else:
                    max_parallel = 5  # Fallback dacă nu există GPU-uri
                    logger.warning("⚠️  Nu s-au detectat GPU-uri, folosind max_parallel=5")
            except (ImportError, Exception) as e:
                max_parallel = 5  # Fallback dacă PyTorch nu este disponibil
                logger.warning(f"⚠️  Nu s-a putut detecta numărul de GPU-uri ({e}), folosind max_parallel=5")
        
        self.max_parallel = max_parallel
        logger.info(f"🚀 SlaveAgentsAutoCreator inițializat cu max_parallel={self.max_parallel}")
        
    async def create_slave_agent(
        self, 
        master_agent_id: str, 
        competitor: Dict
    ) -> Dict:
        """
        Creează un slave agent pentru un competitor
        
        Args:
            master_agent_id: ID-ul agentului master
            competitor: Dict cu domain, score, etc.
            
        Returns:
            {
                "success": bool,
                "slave_id": str,
                "domain": str,
                "chunks": int,
                "error": str (if failed)
            }
        """
        domain = competitor.get("domain")
        url = f"https://{domain}"
        
        logger.info(f"🤖 Creez slave agent pentru: {domain}")
        
        try:
            # Check if already exists
            existing = self.db.site_agents.find_one({
                "domain": domain,
                "master_agent_id": master_agent_id
            })
            
            if existing:
                logger.info(f"   ⏭️  Skip: Agent existent ({existing['_id']})")
                return {
                    "success": True,
                    "slave_id": str(existing["_id"]),
                    "domain": domain,
                    "chunks": existing.get("chunks_indexed", 0),
                    "skipped": True
                }
            
            # Create agent
            creator = FullAgentCreator(url=url)
            result = await creator.create_full_agent()
            
            if result.get("success") or result.get("agent_id"):
                slave_id = result.get("agent_id")
                
                # Set as slave
                self.db.site_agents.update_one(
                    {"_id": ObjectId(slave_id)},
                    {"$set": {
                        "master_agent_id": master_agent_id,
                        "is_slave": True,
                        "agent_type": "slave",
                        "competitor_score": competitor.get("score"),
                        "competitor_rank": competitor.get("best_position")
                    }}
                )
                
                slave = self.db.site_agents.find_one({"_id": ObjectId(slave_id)})
                chunks = slave.get("chunks_indexed", 0)
                
                logger.info(f"   ✅ SUCCESS: {slave_id} ({chunks} chunks)")
                
                return {
                    "success": True,
                    "slave_id": slave_id,
                    "domain": domain,
                    "chunks": chunks
                }
            else:
                error = result.get("error", "Unknown error")
                logger.warning(f"   ⏭️  SKIP: {error}")
                return {
                    "success": False,
                    "domain": domain,
                    "error": error
                }
                
        except Exception as e:
            logger.error(f"   ❌ ERROR: {e}")
            return {
                "success": False,
                "domain": domain,
                "error": str(e)
            }
    
    async def create_slaves_batch(
        self,
        master_agent_id: str,
        competitors: List[Dict],
        max_slaves: int = 50
    ) -> Dict:
        """
        Creează slave agents în batch (paralel)
        
        Args:
            master_agent_id: ID agent master
            competitors: Listă competitori (sorted by score)
            max_slaves: Număr maxim de slaves de creat
            
        Returns:
            {
                "total_created": int,
                "total_failed": int,
                "total_skipped": int,
                "slaves": List[Dict]
            }
        """
        logger.info("="*80)
        logger.info(f"🤖 CREARE SLAVE AGENTS - BATCH")
        logger.info("="*80)
        logger.info(f"   Master: {master_agent_id}")
        logger.info(f"   Competitori: {len(competitors)}")
        logger.info(f"   Max slaves: {max_slaves}")
        logger.info(f"   Paralel: {self.max_parallel}")
        
        # Take only top N competitors
        competitors_to_create = competitors[:max_slaves]
        
        # Create progress tracker
        progress = {
            "master_agent_id": ObjectId(master_agent_id),
            "started_at": datetime.now(timezone.utc),
            "total_competitors": len(competitors_to_create),
            "status": "in_progress"
        }
        progress_id = self.db.slave_creation_progress.insert_one(progress).inserted_id
        
        created = 0
        failed = 0
        skipped = 0
        slaves = []
        
        # Process in batches
        for i in range(0, len(competitors_to_create), self.max_parallel):
            batch = competitors_to_create[i:i+self.max_parallel]
            
            logger.info(f"\n📦 Batch {i//self.max_parallel + 1}: Processing {len(batch)} competitors...")
            
            # Create tasks for parallel execution
            tasks = [
                self.create_slave_agent(master_agent_id, comp)
                for comp in batch
            ]
            
            # Run in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"   Exception: {result}")
                    failed += 1
                elif result.get("success"):
                    if result.get("skipped"):
                        skipped += 1
                    else:
                        created += 1
                    slaves.append(result)
                else:
                    failed += 1
            
            # Update progress
            self.db.slave_creation_progress.update_one(
                {"_id": progress_id},
                {"$set": {
                    "completed": i + len(batch),
                    "created": created,
                    "failed": failed,
                    "skipped": skipped
                }}
            )
            
            logger.info(f"   Progress: {created} created, {skipped} skipped, {failed} failed")
        
        # Final update
        self.db.slave_creation_progress.update_one(
            {"_id": progress_id},
            {"$set": {
                "completed_at": datetime.now(timezone.utc),
                "status": "completed",
                "total_created": created,
                "total_failed": failed,
                "total_skipped": skipped
            }}
        )
        
        logger.info("\n" + "="*80)
        logger.info("✅ BATCH COMPLET!")
        logger.info("="*80)
        logger.info(f"   Creați: {created}")
        logger.info(f"   Existenți (skipped): {skipped}")
        logger.info(f"   Eșuați: {failed}")
        logger.info("="*80)
        
        return {
            "total_created": created,
            "total_failed": failed,
            "total_skipped": skipped,
            "slaves": slaves
        }
    
    async def create_all_slaves_for_agent(
        self,
        agent_id: str,
        max_slaves: int = 50
    ) -> Dict:
        """
        Creează slaves pentru TOȚI competitorii unui agent
        
        Args:
            agent_id: ID agent master
            max_slaves: Câți slaves să creeze (top N by score)
        """
        # Get competitor discovery
        discovery = self.db.competitor_discovery.find_one({
            "agent_id": ObjectId(agent_id),
            "discovery_type": "google_search"
        })
        
        if not discovery:
            logger.error(f"❌ No discovery for agent {agent_id}")
            return {"error": "No discovery found"}
        
        discovery_data = discovery.get("discovery_data", {})
        competitors = discovery_data.get("competitors", [])
        
        logger.info(f"📊 Găsite {len(competitors)} competitori pentru agent {agent_id}")
        
        # Sort by score (best first)
        competitors_sorted = sorted(
            competitors, 
            key=lambda x: x.get("score", 0), 
            reverse=True
        )
        
        # Create slaves
        result = await self.create_slaves_batch(
            master_agent_id=agent_id,
            competitors=competitors_sorted,
            max_slaves=max_slaves
        )
        
        return result


def get_slave_creator():
    """Factory function"""
    return SlaveAgentsAutoCreator()


async def create_slaves_for_master(agent_id: str, max_slaves: int = 50):
    """Helper function pentru creare slaves"""
    creator = SlaveAgentsAutoCreator(max_parallel=5)
    return await creator.create_all_slaves_for_agent(agent_id, max_slaves)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 slave_agents_auto_creator.py <master_agent_id> [max_slaves]")
        print("Example: python3 slave_agents_auto_creator.py 691b06305eb1766cbe71fe13 50")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    max_slaves = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    
    # Run
    asyncio.run(create_slaves_for_master(agent_id, max_slaves))

