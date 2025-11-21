#!/usr/bin/env python3
"""
🧠 MASTER-SLAVE LEARNING SYSTEM
================================

System pentru ca Master Agent să învețe din Slave Agents (competitori)

WORKFLOW:
1. Competitor găsit prin Google Search → creat ca SLAVE agent
2. SLAVE agents sunt linked la MASTER
3. MASTER poate să "interrogheze" SLAVES
4. MASTER învață strategii, tactici, best practices
5. MASTER generează insights competitive

Features:
- Master learns from slaves' content
- Comparative analysis automation
- Best practices extraction
- Competitive intelligence reports
- Strategic recommendations
"""

import asyncio
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import logging

sys.path.insert(0, '/srv/hf/ai_agents')
from llm_orchestrator import get_orchestrator
from qdrant_context_enhancer import get_context_enhancer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MasterSlaveLearningSystem:
    """
    Sistem pentru ca Master să învețe din Slaves (competitori)
    """
    
    def __init__(self):
        # Folosește configurația din config.database_config
        from config.database_config import MONGODB_URI, MONGODB_DATABASE
        self.mongo = MongoClient(MONGODB_URI)
        self.db = self.mongo[MONGODB_DATABASE]
        self.llm = get_orchestrator()
        self.context_enhancer = get_context_enhancer()
        logger.info("✅ Master-Slave Learning System initialized")
    
    async def create_slave_from_competitor(
        self,
        competitor_url: str,
        master_agent_id: str,
        keyword: str,
        serp_position: int,
        gpu_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Creează SLAVE agent dintr-un competitor găsit prin Google Search
        
        Args:
            competitor_url: URL-ul competitorului
            master_agent_id: ID-ul Master agent-ului
            keyword: Keyword-ul pe care a fost găsit
            serp_position: Poziția în SERP (1-15)
        
        Returns:
            Dict cu slave agent info
        """
        try:
            logger.info(f"🔄 Creare SLAVE agent pentru competitor: {competitor_url} (GPU {gpu_id if gpu_id is not None else 0})")
            
            # Import construction agent creator
            from tools.construction_agent_creator import ConstructionAgentCreator
            
            # IMPORTANT: Creează un nou instance pentru fiecare task
            # Astfel fiecare task poate folosi un GPU diferit simultan
            creator = ConstructionAgentCreator()
            
            # ✅ FIX: Folosește metoda async create_agent_from_url care folosește corect MongoDB
            # IMPORTANT: Rulează find_one în executor pentru a nu bloca event loop-ul
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Obține industry-ul master agent-ului (rulează în executor pentru a nu bloca)
            master_agent = await loop.run_in_executor(
                None,
                lambda: self.db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
            )
            industry = master_agent.get("industry", "") if master_agent else ""
            
            # Log pentru debugging - verifică GPU ID
            logger.info(f"   🎯 Task pentru {competitor_url[:50]}... - GPU ID primit: {gpu_id}")
            
            # Crează agent (scraping + embeddings + Qdrant) folosind metoda corectă
            agent_result = await creator.create_agent_from_url(
                site_url=competitor_url,
                industry=industry,
                master_agent_id=master_agent_id,
                gpu_id=gpu_id  # Pasează GPU ID pentru distribuție
            )
            
            if not agent_result.get("ok") or not agent_result.get("agent_id"):
                error_msg = agent_result.get("error", "Unknown error")
                raise Exception(f"Failed to create competitor agent: {error_msg}")
            
            slave_agent_id = agent_result["agent_id"]
            
            # UPDATE agent to mark as SLAVE (dacă nu a fost deja setat de create_agent_from_url)
            self.db.site_agents.update_one(
                {"_id": ObjectId(slave_agent_id)},
                {
                    "$set": {
                        "agent_type": "slave",
                        "master_agent_id": ObjectId(master_agent_id),
                        "competitive_info": {
                            "found_by_keyword": keyword,
                            "serp_position": serp_position,
                            "relevance_score": 50,  # Default, va fi actualizat de analiza relevanței
                            "created_at": datetime.now(timezone.utc)
                        },
                        "created_as_slave_at": datetime.now(timezone.utc),
                        "last_updated": datetime.now(timezone.utc)
                    }
                }
            )
            
            # CREATE master-slave relationship
            relationship = {
                "master_id": ObjectId(master_agent_id),
                "slave_id": ObjectId(slave_agent_id),
                "relationship_type": "competitor",
                "discovered_via": keyword,
                "serp_position": serp_position,
                "created_at": datetime.now(timezone.utc),
                "status": "active"
            }
            
            self.db.master_slave_relationships.insert_one(relationship)
            
            logger.info(f"✅ SLAVE agent created: {slave_agent_id}")
            logger.info(f"   Linked to MASTER: {master_agent_id}")
            logger.info(f"   Keyword: {keyword} (position {serp_position})")
            
            return {
                "success": True,
                "slave_agent_id": str(slave_agent_id),
                "master_agent_id": str(master_agent_id),
                "keyword": keyword,
                "serp_position": serp_position
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating slave agent: {e}")
            return {
                "success": False,
                "error": str(e),
                "competitor_url": competitor_url
            }
    
    async def get_slaves_for_master(self, master_agent_id: str) -> List[Dict[str, Any]]:
        """
        Găsește toți SLAVE agents pentru un MASTER
        """
        try:
            master_oid = ObjectId(master_agent_id)
            
            # Get all slave relationships
            relationships = list(self.db.master_slave_relationships.find({
                "master_id": master_oid,
                "status": "active"
            }))
            
            slaves = []
            for rel in relationships:
                slave = self.db.site_agents.find_one({"_id": rel["slave_id"]})
                if slave:
                    slaves.append({
                        "agent_id": str(slave["_id"]),
                        "domain": slave.get("domain"),
                        "site_url": slave.get("site_url"),
                        "keyword": rel.get("discovered_via"),
                        "serp_position": rel.get("serp_position"),
                        "has_content": slave.get("has_content", False),
                        "has_embeddings": slave.get("has_embeddings", False)
                    })
            
            logger.info(f"📊 Found {len(slaves)} slave agents for master {master_agent_id}")
            return slaves
            
        except Exception as e:
            logger.error(f"❌ Error getting slaves: {e}")
            return []
    
    async def master_learns_from_slave(
        self,
        master_agent_id: str,
        slave_agent_id: str,
        learning_focus: str = "all"
    ) -> Dict[str, Any]:
        """
        MASTER învață din SLAVE (competitor)
        
        Args:
            master_agent_id: ID Master
            slave_agent_id: ID Slave (competitor)
            learning_focus: Ce să învețe ("seo", "content", "pricing", "all")
        
        Returns:
            Dict cu insights și learnings
        """
        try:
            logger.info(f"🧠 Master {master_agent_id} învață din Slave {slave_agent_id}")
            logger.info(f"   Focus: {learning_focus}")
            
            # Get master and slave data
            master = self.db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
            slave = self.db.site_agents.find_one({"_id": ObjectId(slave_agent_id)})
            
            if not master or not slave:
                raise Exception("Master or Slave not found")
            
            # Get content from both (from Qdrant)
            master_content = await self._get_agent_content_summary(master_agent_id)
            slave_content = await self._get_agent_content_summary(slave_agent_id)
            
            # Generate learning insights using LLM
            learning_prompt = self._create_learning_prompt(
                master_domain=master.get("domain"),
                slave_domain=slave.get("domain"),
                master_content=master_content,
                slave_content=slave_content,
                focus=learning_focus
            )
            
            # Generate insights using LLM
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": "You are a competitive intelligence AI analyst."},
                    {"role": "user", "content": learning_prompt}
                ],
                temperature=0.7,
                max_tokens=3000
            )
            
            # Extract content from response
            if isinstance(response, dict):
                insights = response.get("content", str(response))
            else:
                insights = str(response)
            
            # Save learning record
            learning_record = {
                "master_id": ObjectId(master_agent_id),
                "slave_id": ObjectId(slave_agent_id),
                "learning_focus": learning_focus,
                "insights": insights,
                "learned_at": datetime.now(timezone.utc)
            }
            
            self.db.master_learnings.insert_one(learning_record)
            
            logger.info(f"✅ Master learned from slave!")
            logger.info(f"   Insights generated: {len(insights)} bytes")
            
            return {
                "success": True,
                "master_id": master_agent_id,
                "slave_id": slave_agent_id,
                "insights": insights,
                "learning_record_id": str(learning_record["_id"])
            }
            
        except Exception as e:
            logger.error(f"❌ Error in learning process: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def master_learns_from_all_slaves(
        self,
        master_agent_id: str
    ) -> Dict[str, Any]:
        """
        MASTER învață din TOȚI slaves simultan
        Agregare insights de la toți competitorii
        """
        try:
            logger.info(f"🧠 Master {master_agent_id} învață din TOȚI slaves")
            
            # Get all slaves
            slaves = await self.get_slaves_for_master(master_agent_id)
            
            if not slaves:
                return {
                    "success": False,
                    "message": "No slaves found for this master"
                }
            
            logger.info(f"   Processing {len(slaves)} slave agents...")
            
            # Learn from each slave
            all_insights = []
            for slave in slaves:
                result = await self.master_learns_from_slave(
                    master_agent_id,
                    slave["agent_id"],
                    learning_focus="all"
                )
                if result.get("success"):
                    all_insights.append({
                        "slave_domain": slave["domain"],
                        "keyword": slave["keyword"],
                        "insights": result["insights"]
                    })
            
            # Generate aggregated competitive intelligence
            aggregated_insights = await self._aggregate_insights(
                master_agent_id,
                all_insights
            )
            
            # Save comprehensive learning
            comprehensive_learning = {
                "master_id": ObjectId(master_agent_id),
                "total_slaves_analyzed": len(slaves),
                "individual_insights": all_insights,
                "aggregated_insights": aggregated_insights,
                "learned_at": datetime.now(timezone.utc)
            }
            
            self.db.master_comprehensive_learnings.insert_one(comprehensive_learning)
            
            logger.info(f"✅ Master learned from ALL {len(slaves)} slaves!")
            
            return {
                "success": True,
                "master_id": master_agent_id,
                "slaves_analyzed": len(slaves),
                "aggregated_insights": aggregated_insights,
                "learning_record_id": str(comprehensive_learning["_id"])
            }
            
        except Exception as e:
            logger.error(f"❌ Error in comprehensive learning: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_agent_content_summary(self, agent_id: str) -> str:
        """
        Extrage summary al conținutului unui agent din Qdrant
        """
        try:
            # Get top content chunks from Qdrant
            agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return ""
            
            domain = agent.get("domain", "")
            
            # Query Qdrant for content
            collection_name = f"construction_{domain.replace('.', '_')}"
            
            # Get content directly from MongoDB instead (fallback)
            content_docs = list(self.db.site_content.find(
                {"agent_id": ObjectId(agent_id)}
            ).limit(10))
            
            # Combine content
            summary = "\n".join([
                doc.get("content", doc.get("text", ""))[:200]
                for doc in content_docs
            ])
            return summary[:2000]  # Limit to 2000 chars
            
        except Exception as e:
            logger.error(f"Error getting content summary: {e}")
            return ""
    
    def _create_learning_prompt(
        self,
        master_domain: str,
        slave_domain: str,
        master_content: str,
        slave_content: str,
        focus: str
    ) -> str:
        """
        Crează prompt pentru LLM să genereze learning insights
        """
        prompt = f"""You are a competitive intelligence AI analyzing a competitor.

YOUR COMPANY (MASTER): {master_domain}
COMPETITOR (SLAVE): {slave_domain}

YOUR CONTENT OVERVIEW:
{master_content[:1000]}

COMPETITOR CONTENT OVERVIEW:
{slave_content[:1000]}

ANALYSIS FOCUS: {focus}

Generate detailed insights about what YOUR COMPANY can learn from this COMPETITOR:

1. **SEO Strategy:**
   - What keywords are they targeting?
   - Content structure and organization
   - What can we adopt?

2. **Content Strategy:**
   - Types of content they create
   - Writing style and tone
   - Value propositions

3. **Service/Product Offerings:**
   - What do they offer that we don't?
   - Unique selling points
   - Pricing indicators (if visible)

4. **User Experience:**
   - Site structure
   - Navigation patterns
   - Call-to-actions

5. **Actionable Recommendations:**
   - Top 3 things we should implement immediately
   - Long-term strategic moves
   - Competitive advantages we can create

Be specific and actionable. Focus on practical insights.
"""
        return prompt
    
    async def _aggregate_insights(
        self,
        master_agent_id: str,
        all_insights: List[Dict[str, Any]]
    ) -> str:
        """
        Agregare insights de la toți competitors în raport strategic
        """
        try:
            # Create aggregation prompt
            insights_text = "\n\n".join([
                f"COMPETITOR: {insight['slave_domain']} (Keyword: {insight['keyword']})\n{insight['insights']}"
                for insight in all_insights
            ])
            
            aggregation_prompt = f"""You are a strategic business analyst. You've analyzed {len(all_insights)} competitors.

INDIVIDUAL COMPETITOR INSIGHTS:
{insights_text[:5000]}

Generate a STRATEGIC EXECUTIVE SUMMARY for the CEO:

1. **Market Position Analysis:**
   - Where do we stand vs. competitors?
   - Key competitive threats
   - Market opportunities

2. **Common Patterns Across Competitors:**
   - What are ALL competitors doing?
   - Industry trends we're missing
   - Standard practices we should adopt

3. **Competitive Advantages Identified:**
   - What makes top competitors successful?
   - Unique approaches worth studying
   - Innovation opportunities

4. **Strategic Recommendations:**
   - IMMEDIATE ACTIONS (this week)
   - SHORT-TERM STRATEGY (this month)
   - LONG-TERM VISION (this quarter)

5. **Risk Assessment:**
   - What if we don't act?
   - Competitor movement predictions
   - Market shift warnings

Make it CEO-friendly: clear, actionable, strategic.
"""
            
            # Generate aggregated insights
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": "You are a strategic business analyst and CEO advisor."},
                    {"role": "user", "content": aggregation_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            # Extract content
            if isinstance(response, dict):
                aggregated = response.get("content", str(response))
            else:
                aggregated = str(response)
            return aggregated
            
        except Exception as e:
            logger.error(f"Error aggregating insights: {e}")
            return "Error generating aggregated insights"
    
    async def generate_competitive_intelligence_report(
        self,
        master_agent_id: str
    ) -> Dict[str, Any]:
        """
        Generează raport complet de Competitive Intelligence
        pentru CEO cu toate learnings de la slaves
        """
        try:
            logger.info(f"📊 Generating CI Report for master {master_agent_id}")
            
            # Get master info
            master = self.db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
            if not master:
                raise Exception("Master not found")
            
            # Get all slaves
            slaves = await self.get_slaves_for_master(master_agent_id)
            
            # Get latest comprehensive learning
            latest_learning = self.db.master_comprehensive_learnings.find_one(
                {"master_id": ObjectId(master_agent_id)},
                sort=[("learned_at", -1)]
            )
            
            # Create report
            report = {
                "report_id": str(ObjectId()),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "master_agent": {
                    "domain": master.get("domain"),
                    "site_url": master.get("site_url")
                },
                "competitors_analyzed": len(slaves),
                "competitors_list": [
                    {
                        "domain": s["domain"],
                        "keyword": s["keyword"],
                        "serp_position": s["serp_position"]
                    }
                    for s in slaves
                ],
                "strategic_insights": latest_learning.get("aggregated_insights") if latest_learning else "No learning data yet",
                "keywords_covered": list(set([s["keyword"] for s in slaves])),
                "total_keywords": len(set([s["keyword"] for s in slaves]))
            }
            
            # Save report
            self.db.competitive_intelligence_reports.insert_one(report)
            
            logger.info(f"✅ CI Report generated: {report['report_id']}")
            
            return {
                "success": True,
                "report": report
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating CI report: {e}")
            return {
                "success": False,
                "error": str(e)
            }


async def main():
    """
    Example usage of Master-Slave Learning System
    """
    system = MasterSlaveLearningSystem()
    
    # Example: Create slave from competitor
    result = await system.create_slave_from_competitor(
        competitor_url="https://example-competitor.com",
        master_agent_id="master_id_here",
        keyword="renovari bucuresti",
        serp_position=3
    )
    
    print(f"Slave creation: {result}")
    
    # Example: Master learns from all slaves
    learning_result = await system.master_learns_from_all_slaves("master_id_here")
    print(f"Learning result: {learning_result}")
    
    # Example: Generate CI report
    report = await system.generate_competitive_intelligence_report("master_id_here")
    print(f"CI Report: {report}")


if __name__ == "__main__":
    asyncio.run(main())

