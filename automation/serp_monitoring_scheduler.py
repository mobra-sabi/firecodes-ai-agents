#!/usr/bin/env python3
"""
⏰ SERP MONITORING SCHEDULER - V3.0

Automated scheduler pentru monitorizare SERP continuă:
- Daily tracking pentru keywords critice
- Weekly tracking pentru toate keywords
- Automatic trend analysis
- Alert system pentru schimbări majore

Folosește APScheduler sau Cron
"""

import os
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

import logging
from typing import Dict, List
from datetime import datetime, timezone
from pymongo import MongoClient

# Scheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    HAS_APSCHEDULER = True
except ImportError:
    logger.warning("⚠️  APScheduler not installed, using manual trigger")
    HAS_APSCHEDULER = False

# Import tracking module
sys.path.insert(0, '/srv/hf/ai_agents/temporal_tracking')
from serp_timeline_tracker import SERPTimelineTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SERPMonitoringScheduler:
    """
    Scheduler automat pentru monitorizare SERP
    """
    
    def __init__(self, use_scheduler: bool = True):
        self.tracker = SERPTimelineTracker()
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        
        self.use_scheduler = use_scheduler and HAS_APSCHEDULER
        self.scheduler = None
        
        if self.use_scheduler:
            self.scheduler = BackgroundScheduler()
            self._setup_jobs()
        
        logger.info(f"✅ SERP Monitoring Scheduler initialized (APScheduler: {self.use_scheduler})")
    
    def start(self):
        """
        Start scheduler
        """
        if self.scheduler:
            self.scheduler.start()
            logger.info("🚀 SERP monitoring scheduler started!")
            logger.info("   Jobs:")
            for job in self.scheduler.get_jobs():
                logger.info(f"     - {job.id}: {job.trigger}")
        else:
            logger.warning("⚠️  Scheduler not available, use manual triggers")
    
    def stop(self):
        """
        Stop scheduler
        """
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("🛑 SERP monitoring scheduler stopped")
    
    def _setup_jobs(self):
        """
        Setup scheduled jobs
        """
        if not self.scheduler:
            return
        
        # DAILY: Track critical keywords (high priority)
        self.scheduler.add_job(
            self.track_critical_keywords,
            CronTrigger(hour=8, minute=0),  # Daily at 8 AM
            id="daily_critical_tracking",
            name="Track Critical Keywords (Daily)",
            max_instances=1
        )
        
        # WEEKLY: Track all keywords
        self.scheduler.add_job(
            self.track_all_keywords,
            CronTrigger(day_of_week=1, hour=9, minute=0),  # Monday 9 AM
            id="weekly_all_tracking",
            name="Track All Keywords (Weekly)",
            max_instances=1
        )
        
        # DAILY: Analyze trends
        self.scheduler.add_job(
            self.analyze_trends_daily,
            CronTrigger(hour=10, minute=0),  # Daily at 10 AM
            id="daily_trend_analysis",
            name="Analyze Trends (Daily)",
            max_instances=1
        )
        
        # WEEKLY: Generate alerts
        self.scheduler.add_job(
            self.generate_weekly_alerts,
            CronTrigger(day_of_week=1, hour=11, minute=0),  # Monday 11 AM
            id="weekly_alerts",
            name="Generate Weekly Alerts",
            max_instances=1
        )
        
        logger.info(f"✅ {len(self.scheduler.get_jobs())} jobs scheduled")
    
    def track_critical_keywords(self):
        """
        Track keywords marcate ca 'critical' sau high priority
        """
        logger.info("📊 [DAILY JOB] Tracking critical keywords...")
        
        try:
            # Get critical keywords pentru fiecare agent
            agents = list(self.db.site_agents.find({"status": "validated"}))
            
            total_tracked = 0
            
            for agent in agents:
                agent_id = str(agent["_id"])
                
                # Get competitive analysis
                comp_analysis = self.db.competitive_analysis.find_one({"agent_id": agent["_id"]})
                
                if not comp_analysis:
                    continue
                
                # Extract critical keywords (first 10 from overall_keywords)
                analysis_data = comp_analysis.get("analysis_data", {})
                critical_keywords = analysis_data.get("overall_keywords", [])[:10]
                
                if critical_keywords:
                    logger.info(f"   Agent {agent.get('domain')}: {len(critical_keywords)} critical keywords")
                    
                    # Track batch
                    snapshots = self.tracker.track_keywords_batch(
                        critical_keywords,
                        agent_id=agent_id,
                        delay=2.0  # 2 seconds delay between requests
                    )
                    
                    total_tracked += len(snapshots)
            
            logger.info(f"✅ [DAILY JOB] Tracked {total_tracked} critical keywords across {len(agents)} agents")
            
        except Exception as e:
            logger.error(f"❌ [DAILY JOB] Error: {e}")
            import traceback
            traceback.print_exc()
    
    def track_all_keywords(self):
        """
        Track TOATE keywords-urile (weekly comprehensive scan)
        """
        logger.info("📦 [WEEKLY JOB] Tracking ALL keywords...")
        
        try:
            agents = list(self.db.site_agents.find({"status": "validated"}))
            
            total_tracked = 0
            
            for agent in agents:
                agent_id = str(agent["_id"])
                
                # Get ALL keywords
                comp_analysis = self.db.competitive_analysis.find_one({"agent_id": agent["_id"]})
                
                if not comp_analysis:
                    continue
                
                analysis_data = comp_analysis.get("analysis_data", {})
                
                # Combine all keywords
                all_keywords = set()
                all_keywords.update(analysis_data.get("overall_keywords", []))
                
                for subdomain in analysis_data.get("subdomains", []):
                    all_keywords.update(subdomain.get("keywords", []))
                
                if all_keywords:
                    keywords_list = list(all_keywords)
                    logger.info(f"   Agent {agent.get('domain')}: {len(keywords_list)} total keywords")
                    
                    # Track în batch-uri de 50
                    batch_size = 50
                    for i in range(0, len(keywords_list), batch_size):
                        batch = keywords_list[i:i+batch_size]
                        
                        snapshots = self.tracker.track_keywords_batch(
                            batch,
                            agent_id=agent_id,
                            delay=2.0
                        )
                        
                        total_tracked += len(snapshots)
                        
                        logger.info(f"     Batch {i//batch_size + 1}: {len(snapshots)} keywords tracked")
            
            logger.info(f"✅ [WEEKLY JOB] Tracked {total_tracked} keywords across {len(agents)} agents")
            
        except Exception as e:
            logger.error(f"❌ [WEEKLY JOB] Error: {e}")
            import traceback
            traceback.print_exc()
    
    def analyze_trends_daily(self):
        """
        Analizează trend-uri zilnic pentru toate keywords critice
        """
        logger.info("📈 [DAILY JOB] Analyzing trends...")
        
        try:
            agents = list(self.db.site_agents.find({"status": "validated"}))
            
            total_analyzed = 0
            trends_summary = {
                "rising": 0,
                "falling": 0,
                "stable": 0
            }
            
            for agent in agents:
                agent_id = str(agent["_id"])
                domain = agent.get("domain")
                
                # Get critical keywords
                comp_analysis = self.db.competitive_analysis.find_one({"agent_id": agent["_id"]})
                
                if not comp_analysis:
                    continue
                
                critical_keywords = comp_analysis.get("analysis_data", {}).get("overall_keywords", [])[:10]
                
                for keyword in critical_keywords:
                    # Analyze trend
                    trend_analysis = self.tracker.analyze_trends(
                        keyword,
                        domain=domain,
                        days=7  # Last 7 days
                    )
                    
                    if trend_analysis and "trend" in trend_analysis:
                        trend = trend_analysis.get("trend")
                        trends_summary[trend] = trends_summary.get(trend, 0) + 1
                        total_analyzed += 1
                        
                        # If significant change, log it
                        velocity = trend_analysis.get("velocity", 0)
                        if abs(velocity) > 1.0:  # More than 1 position/day change
                            logger.info(f"   ⚠️  {domain} / '{keyword}': {trend} (velocity: {velocity:.2f})")
            
            logger.info(f"✅ [DAILY JOB] Analyzed {total_analyzed} keywords")
            logger.info(f"   Rising: {trends_summary['rising']}, Falling: {trends_summary['falling']}, Stable: {trends_summary['stable']}")
            
            # Save summary
            self.db.trend_analysis_log.insert_one({
                "timestamp": datetime.now(timezone.utc),
                "total_analyzed": total_analyzed,
                "trends_summary": trends_summary
            })
            
        except Exception as e:
            logger.error(f"❌ [DAILY JOB] Error: {e}")
            import traceback
            traceback.print_exc()
    
    def generate_weekly_alerts(self):
        """
        Generează alerturi săptămânale pentru schimbări majore
        """
        logger.info("🚨 [WEEKLY JOB] Generating alerts...")
        
        try:
            # Get recent changes (last 7 days)
            changes = self.tracker.get_recent_changes(days=7)
            
            # Group by type
            alerts = {
                "new_entrants": [],
                "major_rank_drops": [],
                "major_rank_rises": [],
                "competitor_moves": []
            }
            
            for change in changes:
                change_type = change.get("change_type")
                
                if change_type == "new_entrant":
                    alerts["new_entrants"].append(change)
                elif change_type == "rank_drop":
                    details = change.get("details", {})
                    if abs(details.get("change", 0)) >= 5:  # Dropped 5+ positions
                        alerts["major_rank_drops"].append(change)
                elif change_type == "rank_rise":
                    details = change.get("details", {})
                    if details.get("change", 0) >= 5:  # Rose 5+ positions
                        alerts["major_rank_rises"].append(change)
            
            # Log alerts
            logger.info(f"✅ [WEEKLY JOB] Alerts generated:")
            logger.info(f"   New entrants: {len(alerts['new_entrants'])}")
            logger.info(f"   Major drops: {len(alerts['major_rank_drops'])}")
            logger.info(f"   Major rises: {len(alerts['major_rank_rises'])}")
            
            # Save alerts
            self.db.weekly_alerts.insert_one({
                "timestamp": datetime.now(timezone.utc),
                "week": datetime.now(timezone.utc).strftime("%Y-W%W"),
                "alerts": alerts,
                "total_alerts": sum(len(v) for v in alerts.values())
            })
            
            # TODO: Send email/Slack notification if critical alerts
            
        except Exception as e:
            logger.error(f"❌ [WEEKLY JOB] Error: {e}")
            import traceback
            traceback.print_exc()
    
    def manual_trigger_all(self):
        """
        Manual trigger pentru toate job-urile (pentru testing)
        """
        logger.info("🔧 Manual trigger: Running all jobs...")
        
        self.track_critical_keywords()
        self.analyze_trends_daily()
        
        logger.info("✅ Manual trigger complete")


def generate_cron_script():
    """
    Generează script bash pentru cron (dacă APScheduler nu e disponibil)
    """
    script = """#!/bin/bash
# SERP Monitoring Cron Jobs

# Daily at 8 AM: Track critical keywords
0 8 * * * cd /srv/hf/ai_agents && python3 -c "from automation.serp_monitoring_scheduler import SERPMonitoringScheduler; s=SERPMonitoringScheduler(use_scheduler=False); s.track_critical_keywords()"

# Monday at 9 AM: Track all keywords
0 9 * * 1 cd /srv/hf/ai_agents && python3 -c "from automation.serp_monitoring_scheduler import SERPMonitoringScheduler; s=SERPMonitoringScheduler(use_scheduler=False); s.track_all_keywords()"

# Daily at 10 AM: Analyze trends
0 10 * * * cd /srv/hf/ai_agents && python3 -c "from automation.serp_monitoring_scheduler import SERPMonitoringScheduler; s=SERPMonitoringScheduler(use_scheduler=False); s.analyze_trends_daily()"

# Monday at 11 AM: Generate alerts
0 11 * * 1 cd /srv/hf/ai_agents && python3 -c "from automation.serp_monitoring_scheduler import SERPMonitoringScheduler; s=SERPMonitoringScheduler(use_scheduler=False); s.generate_weekly_alerts()"
"""
    
    with open("/srv/hf/ai_agents/serp_monitoring_cron.sh", "w") as f:
        f.write(script)
    
    logger.info("✅ Cron script generated: /srv/hf/ai_agents/serp_monitoring_cron.sh")
    logger.info("   To install: crontab serp_monitoring_cron.sh")


# Test & Run
if __name__ == "__main__":
    print("="*80)
    print("🧪 TESTING SERP MONITORING SCHEDULER")
    print("="*80)
    
    scheduler = SERPMonitoringScheduler(use_scheduler=False)
    
    # Manual trigger pentru testing
    print("\n🔧 Running manual trigger (all jobs)...")
    scheduler.manual_trigger_all()
    
    print("\n✨ SERP Monitoring Scheduler ready!")
    print("\nTo run continuously:")
    print("  python3 automation/serp_monitoring_scheduler.py --daemon")
    
    print("\nOr generate cron script:")
    generate_cron_script()

