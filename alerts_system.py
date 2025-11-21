"""
Alerts System
Complete alerting system for rank drops, new competitors, CTR issues, etc.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from pymongo import MongoClient
from bson import ObjectId
from enum import Enum

logger = logging.getLogger(__name__)


class AlertType(Enum):
    RANK_DROP = "rank_drop"
    COMPETITOR_NEW = "competitor_new"
    CTR_LOW = "ctr_low"
    VISIBILITY_DROP = "visibility_drop"
    KEYWORD_LOST = "keyword_lost"
    ACTION_FAILED = "action_failed"
    SYSTEM_ERROR = "system_error"


class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertsSystem:
    """Complete alerting system for monitoring and notifications"""
    
    def __init__(self, mongo_client: MongoClient = None):
        if mongo_client is None:
            mongo_client = MongoClient("mongodb://localhost:27017/")
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.alerts_collection = self.db["alerts"]
        
        # Create indexes
        self.alerts_collection.create_index([("agent_id", 1), ("status", 1)])
        self.alerts_collection.create_index([("alert_type", 1), ("severity", 1)])
        self.alerts_collection.create_index([("created_at", -1)])
        self.alerts_collection.create_index([("status", 1), ("created_at", -1)])
    
    def create_alert(
        self,
        agent_id: str,
        alert_type: str,
        message: str,
        severity: str = "medium",
        metadata: Optional[Dict] = None,
        auto_action: Optional[str] = None
    ) -> str:
        """
        Create a new alert
        
        Args:
            agent_id: Agent ID
            alert_type: Type of alert (AlertType enum value)
            message: Alert message
            severity: Severity level (AlertSeverity enum value)
            metadata: Additional data
            auto_action: Auto-action to trigger (action_id)
        
        Returns:
            Alert ID
        """
        alert = {
            "agent_id": agent_id,
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "status": "active",
            "metadata": metadata or {},
            "auto_action": auto_action,
            "created_at": datetime.now(timezone.utc),
            "acknowledged_at": None,
            "resolved_at": None,
            "notification_sent": False
        }
        
        result = self.alerts_collection.insert_one(alert)
        alert_id = str(result.inserted_id)
        
        logger.warning(f"🚨 Alert created: {alert_id} ({alert_type}) - {message}")
        
        # Send notification (if configured)
        self._send_notification(alert)
        
        # Trigger auto-action if specified
        if auto_action:
            self._trigger_auto_action(alert_id, auto_action)
        
        return alert_id
    
    def check_rank_drops(
        self,
        agent_id: str,
        threshold: int = 3
    ) -> List[Dict]:
        """
        Check for rank drops >= threshold positions
        
        Args:
            agent_id: Agent ID
            threshold: Minimum drop to trigger alert (default: 3)
        
        Returns:
            List of alerts created
        """
        alerts = []
        
        # Get latest two SERP runs
        runs = list(self.db.serp_runs.find({
            "agent_id": agent_id
        }).sort("created_at", -1).limit(2))
        
        if len(runs) < 2:
            return alerts
        
        latest_run = runs[0]
        previous_run = runs[1]
        
        # Get results for both runs
        latest_results = {
            r["keyword"]: r.get("position")
            for r in self.db.serp_results.find({"run_id": str(latest_run["_id"])})
            if r.get("domain") == self._get_agent_domain(agent_id)
        }
        
        previous_results = {
            r["keyword"]: r.get("position")
            for r in self.db.serp_results.find({"run_id": str(previous_run["_id"])})
            if r.get("domain") == self._get_agent_domain(agent_id)
        }
        
        # Check for drops
        for keyword, current_pos in latest_results.items():
            previous_pos = previous_results.get(keyword)
            
            if previous_pos and current_pos:
                drop = previous_pos - current_pos
                if drop >= threshold:
                    severity = "critical" if drop >= 5 else "high"
                    alert_id = self.create_alert(
                        agent_id=agent_id,
                        alert_type=AlertType.RANK_DROP.value,
                        message=f"Rank drop detected for '{keyword}': #{previous_pos} → #{current_pos} (drop: {drop} positions)",
                        severity=severity,
                        metadata={
                            "keyword": keyword,
                            "previous_position": previous_pos,
                            "current_position": current_pos,
                            "drop": drop
                        },
                        auto_action="rollback" if drop >= 5 else None
                    )
                    alerts.append({"alert_id": alert_id, "keyword": keyword, "drop": drop})
        
        return alerts
    
    def check_new_competitors(
        self,
        agent_id: str,
        top_n: int = 10
    ) -> List[Dict]:
        """Check for new competitors in top N positions"""
        alerts = []
        
        # Get latest SERP run
        latest_run = self.db.serp_runs.find_one({
            "agent_id": agent_id
        }, sort=[("created_at", -1)])
        
        if not latest_run:
            return alerts
        
        # Get top N results
        top_results = list(self.db.serp_results.find({
            "run_id": str(latest_run["_id"]),
            "position": {"$lte": top_n}
        }).sort("position", 1))
        
        # Get known competitors from graph
        known_competitors = set()
        relationships = self.db.org_graph.find({"master_agent_id": agent_id})
        for rel in relationships:
            slave = self.db.site_agents.find_one({"_id": ObjectId(rel["slave_agent_id"])})
            if slave:
                known_competitors.add(slave.get("domain", ""))
        
        # Check for new competitors
        for result in top_results:
            domain = result.get("domain", "")
            if domain and domain not in known_competitors:
                # New competitor detected
                alert_id = self.create_alert(
                    agent_id=agent_id,
                    alert_type=AlertType.COMPETITOR_NEW.value,
                    message=f"New competitor detected in top {top_n}: {domain} (position #{result.get('position')})",
                    severity="high",
                    metadata={
                        "domain": domain,
                        "position": result.get("position"),
                        "keyword": result.get("keyword"),
                        "url": result.get("url")
                    },
                    auto_action="create_slave_agent"
                )
                alerts.append({"alert_id": alert_id, "domain": domain})
        
        return alerts
    
    def check_ctr_low(
        self,
        agent_id: str,
        threshold: float = 0.03  # 3%
    ) -> List[Dict]:
        """Check for low CTR (if GSC data available)"""
        alerts = []
        
        # This would integrate with Google Search Console API
        # For now, placeholder implementation
        
        # TODO: Integrate with GSC API to get actual CTR data
        # gsc_data = self._get_gsc_data(agent_id)
        # for keyword, ctr in gsc_data.items():
        #     if ctr < threshold:
        #         alert_id = self.create_alert(...)
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str, user_id: Optional[str] = None):
        """Acknowledge an alert"""
        self.alerts_collection.update_one(
            {"_id": ObjectId(alert_id)},
            {"$set": {
                "status": "acknowledged",
                "acknowledged_at": datetime.now(timezone.utc),
                "acknowledged_by": user_id
            }}
        )
        logger.info(f"✅ Alert {alert_id} acknowledged")
    
    def resolve_alert(self, alert_id: str, resolution: Optional[str] = None):
        """Resolve an alert"""
        self.alerts_collection.update_one(
            {"_id": ObjectId(alert_id)},
            {"$set": {
                "status": "resolved",
                "resolved_at": datetime.now(timezone.utc),
                "resolution": resolution
            }}
        )
        logger.info(f"✅ Alert {alert_id} resolved")
    
    def get_active_alerts(
        self,
        agent_id: Optional[str] = None,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[Dict]:
        """Get active alerts"""
        query = {"status": "active"}
        
        if agent_id:
            query["agent_id"] = agent_id
        if alert_type:
            query["alert_type"] = alert_type
        if severity:
            query["severity"] = severity
        
        alerts = list(self.alerts_collection.find(query).sort("created_at", -1).limit(100))
        for alert in alerts:
            alert["_id"] = str(alert["_id"])
        
        return alerts
    
    def _get_agent_domain(self, agent_id: str) -> str:
        """Get agent domain"""
        agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
        return agent.get("domain", "") if agent else ""
    
    def _send_notification(self, alert: Dict):
        """Send notification (Slack/Email)"""
        # TODO: Implement Slack/Email notifications
        # For now, just log
        logger.info(f"📧 Notification: {alert['message']} (severity: {alert['severity']})")
    
    def _trigger_auto_action(self, alert_id: str, action_type: str):
        """Trigger automatic action based on alert"""
        # TODO: Integrate with Actions Queue Manager
        logger.info(f"🔧 Auto-action triggered: {action_type} for alert {alert_id}")

