#!/usr/bin/env python3
"""
SERP Monitoring Scheduler - Reconfirmare poziții Google la fiecare 12 ore
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from bson import ObjectId
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from google_competitor_discovery import GoogleCompetitorDiscovery
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SERPMonitoringScheduler:
    """
    Scheduler pentru monitorizare SERP - rulează la fiecare 12 ore
    
    Funcții:
    1. Reconfirmă poziții Google pentru TOȚI competitorii
    2. Detectează schimbări majore (±3 poziții)
    3. Generează alerte pentru rank drops
    4. Salvează istoric pozițiilor
    """
    
    def __init__(self):
        self.mongo_client = MongoClient("mongodb://localhost:27018/")
        self.db = self.mongo_client["ai_agents_db"]
        self.scheduler = AsyncIOScheduler()
        self.discovery = GoogleCompetitorDiscovery()
        
    async def monitor_agent_positions(self, agent_id: str) -> Dict:
        """
        Monitorizează poziții SERP pentru un agent master
        
        Returns:
            {
                "agent_id": str,
                "timestamp": datetime,
                "competitors_monitored": int,
                "positions_changed": int,
                "rank_drops": List[Dict],  # Competitori care au scăzut
                "rank_ups": List[Dict],    # Competitori care au crescut
                "new_competitors": List[Dict]
            }
        """
        logger.info(f"🔍 Monitorizare SERP pentru agent {agent_id}")
        
        try:
            # Get previous positions
            previous_discovery = self.db.competitor_discovery.find_one({
                "agent_id": ObjectId(agent_id),
                "discovery_type": "google_search"
            })
            
            if not previous_discovery:
                logger.warning(f"No previous discovery for agent {agent_id}")
                return {"error": "No previous discovery"}
            
            previous_data = previous_discovery.get("discovery_data", {})
            previous_competitors = {
                comp.get("domain"): comp 
                for comp in previous_data.get("competitors", [])
            }
            
            # Run NEW SERP discovery
            logger.info("🔄 Rulez SERP discovery nou...")
            new_result = await self.discovery.discover_competitors_for_agent(
                agent_id=agent_id,
                results_per_keyword=20
            )
            
            new_competitors = {
                comp.get("domain"): comp 
                for comp in new_result.get("competitors", [])
            }
            
            # Detect changes
            rank_drops = []
            rank_ups = []
            new_entries = []
            
            for domain, new_comp in new_competitors.items():
                if domain in previous_competitors:
                    prev_comp = previous_competitors[domain]
                    
                    # Compare positions
                    prev_best = prev_comp.get("best_position", 999)
                    new_best = new_comp.get("best_position", 999)
                    
                    diff = new_best - prev_best
                    
                    if diff >= 3:  # Rank drop (poziție mai proastă)
                        rank_drops.append({
                            "domain": domain,
                            "previous_position": prev_best,
                            "new_position": new_best,
                            "drop": diff
                        })
                    elif diff <= -3:  # Rank up (poziție mai bună)
                        rank_ups.append({
                            "domain": domain,
                            "previous_position": prev_best,
                            "new_position": new_best,
                            "improvement": abs(diff)
                        })
                else:
                    # New competitor
                    new_entries.append({
                        "domain": domain,
                        "position": new_comp.get("best_position"),
                        "score": new_comp.get("score")
                    })
            
            # Save monitoring result
            monitoring_result = {
                "agent_id": ObjectId(agent_id),
                "timestamp": datetime.now(timezone.utc),
                "competitors_monitored": len(new_competitors),
                "positions_changed": len(rank_drops) + len(rank_ups),
                "rank_drops": rank_drops,
                "rank_ups": rank_ups,
                "new_competitors": new_entries,
                "previous_run": previous_discovery.get("created_at")
            }
            
            self.db.serp_monitoring_history.insert_one(monitoring_result)
            
            # Generate alerts for significant changes
            if rank_drops:
                await self._generate_alerts(agent_id, rank_drops, "rank_drop")
            
            if new_entries:
                await self._generate_alerts(agent_id, new_entries, "new_competitor")
            
            logger.info(f"✅ Monitorizare completă pentru {agent_id}")
            logger.info(f"   Competitori: {len(new_competitors)}")
            logger.info(f"   Rank drops: {len(rank_drops)}")
            logger.info(f"   Rank ups: {len(rank_ups)}")
            logger.info(f"   Noi: {len(new_entries)}")
            
            return monitoring_result
            
        except Exception as e:
            logger.error(f"❌ Eroare monitorizare: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    async def _generate_alerts(self, agent_id: str, changes: List[Dict], alert_type: str):
        """Generează alerte pentru schimbări importante"""
        
        alert = {
            "agent_id": ObjectId(agent_id),
            "type": alert_type,
            "timestamp": datetime.now(timezone.utc),
            "changes": changes,
            "severity": "high" if len(changes) > 5 else "medium",
            "status": "new"
        }
        
        self.db.serp_alerts.insert_one(alert)
        
        logger.warning(f"🚨 ALERT: {alert_type} pentru agent {agent_id}")
        for change in changes[:5]:
            logger.warning(f"   {change}")
    
    async def monitor_all_agents(self):
        """Monitorizează TOȚI agenții care au discovery"""
        logger.info("="*80)
        logger.info("🔄 MONITORIZARE SERP - TOȚI AGENȚII")
        logger.info("="*80)
        
        # Find all agents with discovery
        agents_with_discovery = self.db.competitor_discovery.find({
            "discovery_type": "google_search"
        })
        
        total = 0
        for discovery in agents_with_discovery:
            agent_id = str(discovery.get("agent_id"))
            
            logger.info(f"\n📊 Agent {total + 1}: {agent_id}")
            
            try:
                result = await self.monitor_agent_positions(agent_id)
                total += 1
            except Exception as e:
                logger.error(f"Eroare agent {agent_id}: {e}")
        
        logger.info(f"\n✅ Monitorizare completă: {total} agenți")
    
    def schedule_monitoring(self, interval_hours: int = 12):
        """
        Programează monitorizare SERP la interval fix
        
        Args:
            interval_hours: Ore între rulări (default: 12)
        """
        logger.info(f"⏰ Programez monitorizare SERP la fiecare {interval_hours} ore")
        
        # Schedule job
        self.scheduler.add_job(
            self.monitor_all_agents,
            trigger=IntervalTrigger(hours=interval_hours),
            id='serp_monitoring',
            name='SERP Position Monitoring',
            replace_existing=True
        )
        
        # Run immediately once
        self.scheduler.add_job(
            self.monitor_all_agents,
            id='serp_monitoring_initial',
            name='SERP Initial Run'
        )
        
        logger.info("✅ Scheduler configurat!")
    
    def start(self):
        """Start scheduler"""
        logger.info("🚀 Starting SERP Monitoring Scheduler...")
        self.scheduler.start()
        logger.info("✅ Scheduler pornit!")
        
        # Keep running
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Stopping scheduler...")
            self.scheduler.shutdown()


def get_monitoring_scheduler():
    """Factory function"""
    return SERPMonitoringScheduler()


if __name__ == "__main__":
    # Run scheduler
    scheduler = SERPMonitoringScheduler()
    scheduler.schedule_monitoring(interval_hours=12)  # La fiecare 12 ore
    scheduler.start()

