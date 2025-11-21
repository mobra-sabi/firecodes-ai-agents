#!/usr/bin/env python3
"""
Competitor Agents Creator - Transformă competitorii în agenți slave
"""

import asyncio
import logging
from typing import Dict, List, Any
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class CompetitorAgentsCreator:
    """
    Creează agenți pentru competitori și îi marchează ca slave la master agent
    """
    
    def __init__(self):
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
    
    async def create_competitor_agents(
        self,
        master_agent_id: str,
        max_competitors: int = 20,
        min_score: float = 40.0
    ) -> Dict[str, Any]:
        """
        Creează agenți pentru competitori și stabilește relația master-slave
        
        Args:
            master_agent_id: ID-ul agentului master
            max_competitors: Câți competitori să transforme în agenți
            min_score: Scor minim pentru a fi selectat
        
        Returns:
            Dict cu rezultate: agents_created, agents_failed, relationships
        """
        
        # 1. Obține master agent
        master_agent = self.db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
        if not master_agent:
            raise ValueError(f"Master agent {master_agent_id} not found")
        
        master_domain = master_agent.get("domain")
        logger.info(f"🎯 Master agent: {master_domain} ({master_agent_id})")
        
        # 2. Obține competitori descoperiți
        discovery = self.db.competitor_discovery.find_one({
            "agent_id": ObjectId(master_agent_id),
            "discovery_type": "google_search"
        })
        
        if not discovery:
            raise ValueError(f"No competitor discovery found for agent {master_agent_id}")
        
        discovery_data = discovery.get("discovery_data", {})
        competitors = discovery_data.get("competitors", [])
        
        # 3. Filtrează și sortează competitori
        eligible = [
            c for c in competitors 
            if c.get("score", 0) >= min_score
        ]
        eligible.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        selected = eligible[:max_competitors]
        
        logger.info(f"📊 Selected {len(selected)} competitors (score >= {min_score})")
        
        # 4. Creează agenți pentru fiecare competitor
        results = {
            "master_agent_id": master_agent_id,
            "master_domain": master_domain,
            "total_selected": len(selected),
            "agents_created": [],
            "agents_existed": [],
            "agents_failed": [],
            "relationships_created": 0,
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
        from tools.construction_agent_creator import ConstructionAgentCreator
        
        for i, competitor in enumerate(selected, 1):
            domain = competitor.get("domain")
            url = competitor.get("url")
            score = competitor.get("score", 0)
            
            logger.info(f"\n[{i}/{len(selected)}] Creating agent for: {domain} (score: {score:.1f})")
            print(f"\n{'='*70}")
            print(f"🤖 [{i}/{len(selected)}] {domain} - Score: {score:.1f}")
            print(f"🔗 URL: {url}")
            print(f"{'='*70}")
            
            try:
                # Verifică dacă agentul există deja
                existing = self.db.site_agents.find_one({"domain": domain})
                
                if existing:
                    agent_id = str(existing["_id"])
                    logger.info(f"♻️  Agent already existed: {domain}")
                    results["agents_existed"].append({
                        "domain": domain,
                        "agent_id": agent_id,
                        "score": score
                    })
                else:
                    # Creează agent folosind construction_agent_creator
                    import subprocess
                    import os
                    
                    env = {**os.environ, "MONGODB_URI": "mongodb://localhost:27017", "QDRANT_URL": "http://localhost:9306"}
                    
                    result = subprocess.run(
                        ['python3', '/srv/hf/ai_agents/tools/construction_agent_creator.py', '--url', url, '--mode', 'create_agent'],
                        capture_output=True,
                        text=True,
                        timeout=600,  # 10 min per agent
                        env=env
                    )
                    
                    if result.returncode == 0:
                        # Găsește agentul creat
                        agent = self.db.site_agents.find_one({"domain": domain})
                        if agent:
                            agent_id = str(agent["_id"])
                            agent_config = agent.get("agent_config", {})
                            logger.info(f"✅ Agent created: {domain}")
                            results["agents_created"].append({
                                "domain": domain,
                                "agent_id": agent_id,
                                "score": score,
                                "services": len(agent_config.get("services", [])),
                                "content_size": agent.get("chunks_indexed", 0)
                            })
                        else:
                            raise Exception("Agent creat dar nu găsit în DB")
                    else:
                        raise Exception(f"Exit code {result.returncode}: {result.stderr[:200]}")
                
                # 5. Marchează relația master-slave
                self._create_master_slave_relationship(
                    master_agent_id=master_agent_id,
                    slave_agent_id=agent_id,
                    competitor_data=competitor
                )
                
                results["relationships_created"] += 1
                
                # Rate limiting
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error creating agent for {domain}: {e}")
                results["agents_failed"].append({
                    "domain": domain,
                    "url": url,
                    "error": str(e)
                })
                continue
        
        results["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        # 6. Salvează rezultatele
        self._save_batch_results(master_agent_id, results)
        
        return results
    
    def _create_master_slave_relationship(
        self,
        master_agent_id: str,
        slave_agent_id: str,
        competitor_data: Dict[str, Any]
    ):
        """
        Creează relație master-slave între agenți
        """
        
        # 1. Update slave agent cu master reference
        self.db.site_agents.update_one(
            {"_id": ObjectId(slave_agent_id)},
            {"$set": {
                "agent_type": "competitor_slave",
                "master_agent_id": ObjectId(master_agent_id),
                "competitor_score": competitor_data.get("score"),
                "competitor_rank": None,  # Va fi setat mai târziu
                "keywords_matched": competitor_data.get("keywords_matched", []),
                "subdomains_matched": competitor_data.get("subdomains_matched", []),
                "avg_google_position": competitor_data.get("avg_position"),
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        # 2. Update master agent cu slave reference
        self.db.site_agents.update_one(
            {"_id": ObjectId(master_agent_id)},
            {
                "$addToSet": {
                    "competitor_slaves": ObjectId(slave_agent_id)
                },
                "$set": {
                    "has_competitor_analysis": True,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # 3. Salvează relația în colecție separată
        self.db.agent_relationships.update_one(
            {
                "master_id": ObjectId(master_agent_id),
                "slave_id": ObjectId(slave_agent_id)
            },
            {"$set": {
                "master_id": ObjectId(master_agent_id),
                "slave_id": ObjectId(slave_agent_id),
                "relationship_type": "competitor",
                "competitor_data": competitor_data,
                "created_at": datetime.now(timezone.utc),
                "status": "active"
            }},
            upsert=True
        )
        
        logger.info(f"🔗 Created master-slave relationship: {master_agent_id} → {slave_agent_id}")
    
    def _save_batch_results(self, master_agent_id: str, results: Dict[str, Any]):
        """Salvează rezultatele batch-ului în MongoDB"""
        
        self.db.competitor_batch_jobs.insert_one({
            "master_agent_id": ObjectId(master_agent_id),
            "job_type": "create_competitor_agents",
            "results": results,
            "created_at": datetime.now(timezone.utc)
        })
        
        logger.info(f"💾 Batch results saved for master {master_agent_id}")
    
    def get_slave_agents(self, master_agent_id: str) -> List[Dict[str, Any]]:
        """Obține toți agenții slave pentru un master"""
        
        master_agent = self.db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
        if not master_agent:
            return []
        
        slave_ids = master_agent.get("competitor_slaves", [])
        
        slaves = list(self.db.site_agents.find({"_id": {"$in": slave_ids}}))
        
        # Convert ObjectId to string
        for slave in slaves:
            slave["_id"] = str(slave["_id"])
            slave["master_agent_id"] = str(slave.get("master_agent_id"))
        
        return slaves


async def main():
    """CLI pentru creare batch agenți competitori"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 competitor_agents_creator.py <master_agent_id> [max_competitors] [min_score]")
        print()
        print("Example:")
        print("  python3 competitor_agents_creator.py 6910ef1d112d6bca72be0622 20 40.0")
        sys.exit(1)
    
    master_agent_id = sys.argv[1]
    max_competitors = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    min_score = float(sys.argv[3]) if len(sys.argv) > 3 else 40.0
    
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║   🤖 COMPETITOR AGENTS CREATOR - MASTER/SLAVE SYSTEM                ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"🎯 Master Agent ID: {master_agent_id}")
    print(f"📊 Max Competitors: {max_competitors}")
    print(f"📈 Min Score: {min_score}")
    print()
    
    creator = CompetitorAgentsCreator()
    
    results = await creator.create_competitor_agents(
        master_agent_id=master_agent_id,
        max_competitors=max_competitors,
        min_score=min_score
    )
    
    print("\n" + "="*70)
    print("\n✅ BATCH COMPLETED!")
    print()
    print(f"📊 RESULTS:")
    print(f"   • Total selected: {results['total_selected']}")
    print(f"   • Agents created: {len(results['agents_created'])}")
    print(f"   • Agents existed: {len(results['agents_existed'])}")
    print(f"   • Agents failed: {len(results['agents_failed'])}")
    print(f"   • Relationships: {results['relationships_created']}")
    print()
    
    if results['agents_created']:
        print("✅ NEW AGENTS CREATED:")
        for agent in results['agents_created'][:10]:
            print(f"   • {agent['domain']} - Score: {agent['score']:.1f} - Services: {agent['services']}")
    
    if results['agents_existed']:
        print(f"\n♻️  AGENTS ALREADY EXISTED: {len(results['agents_existed'])}")
        for agent in results['agents_existed'][:5]:
            print(f"   • {agent['domain']} - Score: {agent['score']:.1f}")
    
    if results['agents_failed']:
        print(f"\n❌ FAILED: {len(results['agents_failed'])}")
        for agent in results['agents_failed'][:5]:
            print(f"   • {agent['domain']}: {agent.get('error', 'Unknown error')}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
