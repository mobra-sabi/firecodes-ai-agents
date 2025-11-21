#!/usr/bin/env python3
"""
🤖 CREARE SLAVE AGENTS INTELIGENȚI
==================================

Creează slave agents de calitate pentru competitori cu:
1. Specificații clare (cine sunt, ce fac)
2. Keywords care i-au descoperit
3. Metadata pentru învățare și comparație
4. Integrare în master-slave architecture
"""

import subprocess
import os
import time
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from typing import Dict, List, Any

class IntelligentSlaveAgentCreator:
    """Creează slave agents cu metadata completă pentru învățare"""
    
    def __init__(self):
        self.mongo = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo.ai_agents_db
    
    def create_slave_agents_from_serp(
        self,
        master_agent_id: str,
        max_slaves: int = 15,
        min_relevance_score: float = 25.0
    ):
        """
        Creează slave agents din rezultatele SERP
        
        Args:
            master_agent_id: ID-ul agentului master
            max_slaves: Maxim câți slave agents să creeze
            min_relevance_score: Score minim de relevanță (0-100)
        """
        
        print("=" * 80)
        print("🤖 CREARE SLAVE AGENTS INTELIGENȚI")
        print("=" * 80)
        
        # 1. Get master agent
        master = self.db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
        if not master:
            raise ValueError(f"Master agent {master_agent_id} not found")
        
        master_domain = master.get('domain', 'unknown')
        print(f"\n🎯 Master Agent: {master_domain}")
        
        # 2. Get SERP discovery results
        serp_results = self.db.serp_discovery_results.find_one(
            {"agent_id": master_agent_id}
        )
        
        if not serp_results:
            print("❌ Nu există rezultate SERP pentru acest agent!")
            return
        
        # 3. Filter și sortează competitori
        competitors = serp_results.get('potential_competitors', [])
        
        # Filter by score
        eligible = [
            c for c in competitors
            if c.get('relevance_score', 0) >= min_relevance_score
        ]
        
        # Sort by score
        eligible.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Limit
        selected = eligible[:max_slaves]
        
        print(f"\n📊 Competitori disponibili: {len(competitors)}")
        print(f"   Eligibili (score >= {min_relevance_score}%): {len(eligible)}")
        print(f"   Selectați pentru procesare: {len(selected)}")
        
        # 4. Creează fiecare slave agent
        stats = {
            "total": len(selected),
            "created": 0,
            "existed": 0,
            "failed": 0,
            "start_time": time.time()
        }
        
        for idx, competitor in enumerate(selected, 1):
            print(f"\n{'='*80}")
            print(f"🤖 [{idx}/{len(selected)}] Procesez: {competitor['domain']}")
            print(f"{'='*80}")
            
            success = self._create_single_slave_agent(
                master_agent_id,
                master_domain,
                competitor,
                idx
            )
            
            if success == "created":
                stats["created"] += 1
            elif success == "existed":
                stats["existed"] += 1
            else:
                stats["failed"] += 1
            
            # Pauză între agenți
            if idx < len(selected):
                time.sleep(5)
        
        # 5. Raport final
        elapsed = time.time() - stats["start_time"]
        
        print(f"\n{'='*80}")
        print(f"📊 RAPORT FINAL")
        print(f"{'='*80}")
        print(f"   Total procesați: {stats['total']}")
        print(f"   ✅ Creați: {stats['created']}")
        print(f"   ♻️ Existenți: {stats['existed']}")
        print(f"   ❌ Eșuați: {stats['failed']}")
        print(f"   ⏱️ Timp total: {elapsed/60:.1f} minute")
        print(f"   📊 Rată succes: {(stats['created']+stats['existed'])/stats['total']*100:.1f}%")
        
        return stats
    
    def _create_single_slave_agent(
        self,
        master_agent_id: str,
        master_domain: str,
        competitor: Dict,
        index: int
    ) -> str:
        """
        Creează un singur slave agent
        
        Returns:
            "created", "existed", sau "failed"
        """
        
        domain = competitor['domain']
        url = competitor['url']
        score = competitor.get('relevance_score', 0)
        keywords = competitor.get('keywords_matched', [])
        
        print(f"   Domain: {domain}")
        print(f"   URL: {url}")
        print(f"   Score: {score:.1f}%")
        print(f"   Keywords: {', '.join(keywords[:3])}")
        
        # 1. Check dacă agentul există deja
        existing = self.db.site_agents.find_one({"domain": domain})
        
        if existing:
            slave_id = existing['_id']
            print(f"   ♻️ Agent exists: {slave_id}")
            
            # Update metadata chiar dacă există
            self._update_slave_metadata(existing, competitor, master_domain)
            
            # Create/update relationship
            self._create_master_slave_relationship(
                master_agent_id,
                str(slave_id),
                competitor,
                master_domain
            )
            
            return "existed"
        
        # 2. Creează agent nou
        print(f"\n   🚀 Creez agent nou...")
        
        try:
            env = {
                **os.environ,
                "MONGODB_URI": "mongodb://localhost:27017",
                "QDRANT_URL": "http://localhost:9306"
            }
            
            result = subprocess.run(
                [
                    'python3',
                    '/srv/hf/ai_agents/tools/construction_agent_creator.py',
                    '--url', url,
                    '--mode', 'create_agent'
                ],
                capture_output=True,
                text=True,
                timeout=600,  # 10 min
                env=env
            )
            
            if result.returncode == 0:
                # Găsește agentul creat
                new_agent = self.db.site_agents.find_one(
                    {"domain": domain},
                    sort=[("created_at", -1)]
                )
                
                if new_agent:
                    slave_id = new_agent['_id']
                    
                    print(f"   ✅ Agent creat: {slave_id}")
                    print(f"      Chunks: {new_agent.get('chunks_indexed', 0)}")
                    
                    # Update metadata
                    self._update_slave_metadata(new_agent, competitor, master_domain)
                    
                    # Create relationship
                    self._create_master_slave_relationship(
                        master_agent_id,
                        str(slave_id),
                        competitor,
                        master_domain
                    )
                    
                    return "created"
                else:
                    print(f"   ❌ Agent creat dar nu găsit în DB")
                    return "failed"
            else:
                print(f"   ❌ Creare eșuată: exit code {result.returncode}")
                if result.stderr:
                    print(f"      Error: {result.stderr[:200]}")
                return "failed"
                
        except subprocess.TimeoutExpired:
            print(f"   ❌ Timeout (>10 min)")
            return "failed"
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return "failed"
    
    def _update_slave_metadata(
        self,
        agent: Dict,
        competitor: Dict,
        master_domain: str
    ):
        """Update agent cu metadata pentru învățare"""
        
        agent_id = agent['_id']
        
        # Metadata pentru învățare
        learning_metadata = {
            "discovered_via": {
                "master_domain": master_domain,
                "keywords": competitor.get('keywords_matched', []),
                "relevance_score": competitor.get('relevance_score', 0),
                "appearances": competitor.get('appearances', 0),
                "discovery_method": "serp_search",
                "discovered_at": competitor.get('discovered_at', datetime.now())
            },
            "competitive_profile": {
                "is_competitor": True,
                "market_position": self._determine_market_position(
                    competitor.get('relevance_score', 0)
                ),
                "keyword_overlap": len(competitor.get('keywords_matched', [])),
                "serp_visibility": competitor.get('appearances', 0)
            },
            "learning_signals": {
                "should_monitor": True,
                "priority": "high" if competitor.get('relevance_score', 0) > 60 else "medium",
                "learn_from_services": True,
                "learn_from_content": True,
                "learn_from_keywords": True
            }
        }
        
        # Update în MongoDB
        self.db.site_agents.update_one(
            {"_id": agent_id},
            {
                "$set": {
                    "agent_type": "competitor_slave",
                    "learning_metadata": learning_metadata,
                    "last_metadata_update": datetime.now()
                }
            }
        )
        
        print(f"   📝 Metadata updated pentru învățare")
    
    def _create_master_slave_relationship(
        self,
        master_id: str,
        slave_id: str,
        competitor: Dict,
        master_domain: str
    ):
        """Creează relationship master-slave cu metadata completă"""
        
        relationship = {
            "master_id": ObjectId(master_id),
            "slave_id": ObjectId(slave_id),
            "relationship_type": "competitor",
            "status": "active",
            "created_at": datetime.now(),
            
            # Metadata competitor
            "competitor_data": {
                "domain": competitor['domain'],
                "url": competitor['url'],
                "relevance_score": competitor.get('relevance_score', 0),
                "appearances": competitor.get('appearances', 0),
                "keywords_matched": competitor.get('keywords_matched', []),
                "discovered_via": "serp_discovery"
            },
            
            # Learning objectives
            "learning_objectives": {
                "analyze_services": True,
                "analyze_content_strategy": True,
                "analyze_keywords": True,
                "analyze_market_position": True,
                "generate_improvement_plan": True
            },
            
            # Comparison metrics
            "comparison_enabled": True,
            "last_comparison": None,
            "improvement_suggestions": []
        }
        
        self.db.agent_relationships.replace_one(
            {
                "master_id": ObjectId(master_id),
                "slave_id": ObjectId(slave_id)
            },
            relationship,
            upsert=True
        )
        
        print(f"   🔗 Relationship created: master-slave")
    
    def _determine_market_position(self, score: float) -> str:
        """Determină poziția în piață bazată pe score"""
        if score >= 75:
            return "leader"
        elif score >= 50:
            return "strong_competitor"
        elif score >= 25:
            return "relevant_competitor"
        else:
            return "minor_competitor"


def main():
    """Run script"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python create_intelligent_slave_agents.py <master_agent_id> [max_slaves] [min_score]")
        sys.exit(1)
    
    master_id = sys.argv[1]
    max_slaves = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    min_score = float(sys.argv[3]) if len(sys.argv) > 3 else 25.0
    
    creator = IntelligentSlaveAgentCreator()
    stats = creator.create_slave_agents_from_serp(master_id, max_slaves, min_score)
    
    if stats:
        print(f"\n✅ COMPLETED!")
    else:
        print(f"\n❌ FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()

