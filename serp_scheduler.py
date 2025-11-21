#!/usr/bin/env python3
"""
⏰ SERP Scheduler - Monitorizare zilnică automată
Production-ready cu APScheduler + detecție schimbări

Usage:
    python3 serp_scheduler.py --mode daemon
    python3 serp_scheduler.py --mode once --agent-id protectiilafoc.ro
"""

import argparse
import logging
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pymongo import MongoClient

# Import module proprii
sys.path.insert(0, '/srv/hf/ai_agents')
from serp_ingest import SERPScorer, canonical_domain
from serp_mongodb_schemas import SERPMongoDBSchemas

logger = logging.getLogger(__name__)


class SERPMonitor:
    """
    🔍 SERP Monitor - Monitorizare zilnică + detecție schimbări
    
    Funcționalități:
    - Rulare zilnică SERP fetch pentru toți agenții activi
    - Detecție schimbări (rank drops, rank gains, new competitors)
    - Creare alerte automate
    - Trigger acțiuni sugerate
    """
    
    def __init__(self):
        """Initialize SERP Monitor"""
        self.mongo = MongoClient('mongodb://localhost:27017/')
        self.db = self.mongo.ai_agents_db
        self.schemas = SERPMongoDBSchemas()
        self.scorer = SERPScorer()
        self.logger = logging.getLogger(f"{__name__}.SERPMonitor")
    
    async def monitor_agent(self, agent_id: str) -> Dict:
        """
        🔍 Monitorizează un agent (SERP fetch + analiză schimbări)
        
        Args:
            agent_id: ID agent master (poate fi string sau ObjectId)
        
        Returns:
            Dict cu statistici: run_id, alerts_created, changes_detected
        """
        self.logger.info(f"🔍 Starting SERP monitoring for agent {agent_id}")
        
        # 1. Obține agent și keywords
        from bson import ObjectId
        try:
            query_id = ObjectId(agent_id) if isinstance(agent_id, str) else agent_id
        except:
            query_id = agent_id
        
        agent = self.db.site_agents.find_one({"_id": query_id})
        if not agent:
            agent = self.db.agents.find_one({"_id": query_id})
        
        if not agent:
            self.logger.error(f"❌ Agent {agent_id} not found")
            return {"error": "Agent not found"}
        
        keywords = agent.get("keywords", [])
        if not keywords:
            self.logger.warning(f"⚠️ Agent {agent_id} has no keywords")
            return {"error": "No keywords"}
        
        master_domain = agent.get("domain", "")
        
        # 2. Creează SERP run
        run_id = self.schemas.insert_serp_run(
            agent_id=agent_id,
            keywords=keywords,
            market="ro",
            provider="brave"
        )
        
        self.logger.info(f"📊 Created SERP run {run_id} for {len(keywords)} keywords")
        
        # 3. Fetch SERP results (simulat - în production folosim Brave API)
        try:
            await self._fetch_serp_results(run_id, agent_id, keywords, master_domain)
        except Exception as e:
            self.logger.error(f"❌ Error fetching SERP: {e}")
            self.schemas.update_serp_run_status(run_id, "failed")
            return {"error": str(e), "run_id": run_id}
        
        # 4. Analizează schimbări și creează alerte
        alerts_created = await self._detect_changes_and_alert(run_id, agent_id, keywords, master_domain)
        
        # 5. Update competitori
        await self._update_competitors(run_id, agent_id)
        
        self.logger.info(f"✅ SERP monitoring completed for {agent_id}: {alerts_created} alerts")
        
        return {
            "run_id": run_id,
            "agent_id": agent_id,
            "keywords_monitored": len(keywords),
            "alerts_created": alerts_created,
            "status": "succeeded"
        }
    
    async def _fetch_serp_results(
        self,
        run_id: str,
        agent_id: str,
        keywords: List[str],
        master_domain: str
    ):
        """
        Fetch SERP results pentru toate keywords
        
        TODO: În production, înlocuiește cu Brave API call real
        """
        self.logger.info(f"🔄 Fetching SERP for {len(keywords)} keywords...")
        
        total_results = 0
        unique_domains = set()
        
        # Import REAL SERP scraper
        from google_serp_scraper import GoogleSerpScraper
        serp_scraper = GoogleSerpScraper()
        
        for keyword in keywords:
            self.logger.info(f"🔍 Searching REAL SERP for: {keyword}")
            
            # REAL Brave API call (NO MORE MOCKS!)
            try:
                real_results = serp_scraper.search(query=keyword, count=20)
                
                if not real_results:
                    self.logger.warning(f"⚠️ No SERP results for keyword: {keyword}")
                    continue
                
            except Exception as e:
                self.logger.error(f"❌ SERP search failed for '{keyword}': {e}")
                continue
            
            # Salvează în MongoDB
            for rank, result in enumerate(real_results, 1):
                domain = canonical_domain(result["url"])
                unique_domains.add(domain)
                
                self.schemas.insert_serp_result(
                    run_id=run_id,
                    agent_id=agent_id,
                    keyword=keyword,
                    rank=rank,
                    url=result["url"],
                    domain=domain,
                    title=result.get("title", ""),
                    snippet=result.get("snippet", ""),
                    result_type=result.get("type", "organic")
                )
                total_results += 1
            
            # Update rank history pentru master
            master_result = next((r for r in real_results if master_domain in r["url"]), None)
            if master_result:
                rank = real_results.index(master_result) + 1
                self.schemas.update_rank_history(
                    domain=master_domain,
                    keyword=keyword,
                    rank=rank,
                    run_id=run_id
                )
        
        # Update run status
        self.schemas.update_serp_run_status(
            run_id=run_id,
            status="succeeded",
            stats={
                "queries": len(keywords),
                "pages_fetched": len(keywords),
                "errors": 0,
                "total_results": total_results,
                "unique_domains": len(unique_domains)
            }
        )
        
        self.logger.info(f"✅ Fetched {total_results} SERP results, {len(unique_domains)} unique domains")
    
    async def _detect_changes_and_alert(
        self,
        run_id: str,
        agent_id: str,
        keywords: List[str],
        master_domain: str
    ) -> int:
        """
        🔍 Detectează schimbări și creează alerte
        
        Tipuri alerte:
        - rank_drop: Master scade 3+ poziții
        - rank_gain: Master urcă 3+ poziții
        - new_competitor: Nou competitor în Top 3
        - competitor_gain: Competitor urcă în Top 3
        - out_of_top10: Master iese din Top 10
        - into_top10: Master intră în Top 10
        
        Returns:
            Număr alerte create
        """
        self.logger.info(f"🔍 Detecting changes for agent {agent_id}...")
        
        alerts_created = 0
        
        for keyword in keywords:
            # Obține istoric rank pentru master + acest keyword
            history = self.db.ranks_history.find_one({
                "domain": master_domain,
                "keyword": keyword
            })
            
            if not history or len(history.get("series", [])) < 2:
                # Nu avem istoric suficient
                continue
            
            # Compară ultimele 2 run-uri
            series = sorted(history["series"], key=lambda x: x["date"], reverse=True)
            current_rank = series[0]["rank"]
            previous_rank = series[1]["rank"]
            delta = current_rank - previous_rank
            
            # 1. Rank drop (master scade)
            if delta >= 3:
                alert_id = self.schemas.create_alert(
                    agent_id=agent_id,
                    run_id=run_id,
                    alert_type="rank_drop",
                    severity="critical" if delta >= 5 else "warning",
                    keyword=keyword,
                    details={
                        "previous_rank": previous_rank,
                        "current_rank": current_rank,
                        "delta": delta,
                        "domain": master_domain
                    },
                    actions_suggested=[
                        "Re-optimize page content",
                        "Check technical SEO issues",
                        "Analyze competitor content",
                        "Build quality backlinks"
                    ]
                )
                alerts_created += 1
                self.logger.warning(
                    f"🔴 RANK DROP: {master_domain} - '{keyword}' "
                    f"#{previous_rank} → #{current_rank} (Δ{delta})"
                )
            
            # 2. Rank gain (master urcă)
            elif delta <= -3:
                alert_id = self.schemas.create_alert(
                    agent_id=agent_id,
                    run_id=run_id,
                    alert_type="rank_gain",
                    severity="info",
                    keyword=keyword,
                    details={
                        "previous_rank": previous_rank,
                        "current_rank": current_rank,
                        "delta": delta,
                        "domain": master_domain
                    },
                    actions_suggested=[
                        "Monitor and maintain improvements",
                        "Document what worked"
                    ]
                )
                alerts_created += 1
                self.logger.info(
                    f"🟢 RANK GAIN: {master_domain} - '{keyword}' "
                    f"#{previous_rank} → #{current_rank} (Δ{delta})"
                )
            
            # 3. Out of Top 10
            if previous_rank <= 10 and current_rank > 10:
                alert_id = self.schemas.create_alert(
                    agent_id=agent_id,
                    run_id=run_id,
                    alert_type="out_of_top10",
                    severity="critical",
                    keyword=keyword,
                    details={
                        "previous_rank": previous_rank,
                        "current_rank": current_rank,
                        "domain": master_domain
                    },
                    actions_suggested=[
                        "URGENT: Re-optimize page",
                        "Check for technical issues",
                        "Run CopywriterAgent to refresh content"
                    ]
                )
                alerts_created += 1
                self.logger.critical(
                    f"🔴 OUT OF TOP 10: {master_domain} - '{keyword}' "
                    f"#{previous_rank} → #{current_rank}"
                )
            
            # 4. Into Top 10
            elif previous_rank > 10 and current_rank <= 10:
                alert_id = self.schemas.create_alert(
                    agent_id=agent_id,
                    run_id=run_id,
                    alert_type="into_top10",
                    severity="info",
                    keyword=keyword,
                    details={
                        "previous_rank": previous_rank,
                        "current_rank": current_rank,
                        "domain": master_domain
                    },
                    actions_suggested=[
                        "Continue optimization",
                        "Monitor competitors"
                    ]
                )
                alerts_created += 1
                self.logger.info(
                    f"🟢 INTO TOP 10: {master_domain} - '{keyword}' "
                    f"#{previous_rank} → #{current_rank}"
                )
        
        # 5. Detectează new competitors în Top 3
        # TODO: Implementare detectare new competitors
        
        return alerts_created
    
    async def _update_competitors(self, run_id: str, agent_id: str):
        """Update competitori bazat pe SERP results"""
        self.logger.info(f"🎯 Updating competitors from run {run_id}...")
        
        # Obține agent și keywords
        from bson import ObjectId
        try:
            query_id = ObjectId(agent_id) if isinstance(agent_id, str) else agent_id
        except:
            query_id = agent_id
        
        agent = self.db.site_agents.find_one({"_id": query_id})
        if not agent:
            agent = self.db.agents.find_one({"_id": query_id})
        
        master_domain = agent.get("domain", "")
        all_keywords = agent.get("keywords", [])
        
        # Obține rezultate SERP (exclude master)
        serp_results = list(self.db.serp_results.find({"run_id": run_id}))
        competitor_results = [r for r in serp_results if r.get("domain") != master_domain]
        
        # Calculează visibility scores
        visibility_scores = self.scorer.aggregate_visibility(competitor_results, normalize=False)
        
        # Update competitori
        for comp_data in visibility_scores:
            domain = comp_data["domain"]
            visibility_normalized = comp_data["visibility_score"]
            keyword_overlap_pct = (comp_data["keywords_count"] / len(all_keywords)) * 100
            
            threat_score = self.scorer.calculate_threat_score(
                visibility_score=visibility_normalized,
                authority_score=0.5,
                keyword_overlap_percentage=keyword_overlap_pct
            )
            
            scores = {
                "visibility": visibility_normalized,
                "authority": 0.5,
                "threat": threat_score
            }
            
            self.schemas.upsert_competitor(
                domain=domain,
                keywords_seen=comp_data.get("keywords", []),
                scores=scores,
                agent_slave_id=None
            )
        
        self.logger.info(f"✅ Updated {len(visibility_scores)} competitors")
    
    async def monitor_all_agents(self):
        """
        🔍 Monitorizează toți agenții activi
        
        Rulează SERP monitoring pentru toți masterii care au keywords.
        """
        self.logger.info("🔍 Starting SERP monitoring for all active agents...")
        
        # Obține toți masterii cu keywords
        masters = []
        
        # Din site_agents
        site_masters = list(self.db.site_agents.find({
            "agent_type": "master",
            "keywords": {"$exists": True, "$ne": []}
        }))
        masters.extend(site_masters)
        
        # Din agents
        agents_masters = list(self.db.agents.find({
            "agent_type": {"$ne": "slave"},
            "keywords": {"$exists": True, "$ne": []}
        }))
        masters.extend(agents_masters)
        
        self.logger.info(f"📊 Found {len(masters)} agents to monitor")
        
        results = []
        for agent in masters:
            agent_id = str(agent["_id"])
            try:
                result = await self.monitor_agent(agent_id)
                results.append(result)
            except Exception as e:
                self.logger.error(f"❌ Error monitoring agent {agent_id}: {e}")
                results.append({"agent_id": agent_id, "error": str(e)})
        
        self.logger.info(f"✅ Monitoring completed for {len(results)} agents")
        return results


# ============================================================================
# SCHEDULER
# ============================================================================

async def scheduled_monitoring():
    """Funcție apelată de scheduler zilnic"""
    logger.info("⏰ Scheduled SERP monitoring triggered")
    monitor = SERPMonitor()
    results = await monitor.monitor_all_agents()
    logger.info(f"✅ Scheduled monitoring completed: {len(results)} agents processed")


def start_scheduler():
    """Start APScheduler în mod daemon"""
    logger.info("🚀 Starting SERP Scheduler...")
    
    # Creează scheduler
    scheduler = AsyncIOScheduler()
    
    # Adaugă job zilnic la 14:00 UTC (17:00 RO)
    scheduler.add_job(
        scheduled_monitoring,
        CronTrigger(hour=14, minute=0),
        id="daily_serp_monitoring",
        name="Daily SERP Monitoring (14:00 UTC)",
        replace_existing=True
    )
    
    # Create event loop BEFORE scheduler.start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start scheduler
    scheduler.start()
    logger.info("✅ Scheduler started - Daily monitoring at 14:00 UTC")
    
    # Keep alive
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Scheduler stopped")
        scheduler.shutdown()
        loop.close()


async def monitor_once(agent_id: Optional[str] = None):
    """Rulează monitoring o singură dată (pentru testing)"""
    monitor = SERPMonitor()
    
    if agent_id:
        logger.info(f"🔍 Running one-time monitoring for agent {agent_id}")
        result = await monitor.monitor_agent(agent_id)
        logger.info(f"✅ Result: {result}")
    else:
        logger.info("🔍 Running one-time monitoring for all agents")
        results = await monitor.monitor_all_agents()
        logger.info(f"✅ Completed: {len(results)} agents monitored")


# ============================================================================
# CLI
# ============================================================================

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="SERP Scheduler - Monitorizare zilnică")
    parser.add_argument(
        "--mode",
        choices=["daemon", "once"],
        default="daemon",
        help="Mod de rulare: daemon (schedule zilnic) sau once (o singură dată)"
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        help="Agent ID pentru mod 'once' (opțional - dacă lipsește, monitorizează toți)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Nivel logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run
    if args.mode == "daemon":
        start_scheduler()
    else:
        asyncio.run(monitor_once(args.agent_id))


if __name__ == "__main__":
    main()

