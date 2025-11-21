#!/usr/bin/env python3
"""
🔔 SERP Alerting System - Slack & Email notifications
Production-ready cu retry logic și formatting
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
import requests
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)


class SERPAlertingSystem:
    """
    🔔 Sistem alerting pentru SERP monitoring
    
    Suportă:
    - Slack webhooks (cu rich formatting/blocks)
    - Email notifications (SendGrid/Mailgun)
    - Retry logic cu exponential backoff
    """
    
    def __init__(
        self,
        slack_webhook_url: Optional[str] = None,
        email_config: Optional[Dict] = None,
        mongo_uri: str = "mongodb://localhost:27017/",
        db_name: str = "ai_agents_db"
    ):
        """
        Initialize alerting system
        
        Args:
            slack_webhook_url: Slack webhook URL (opțional)
            email_config: Config email (provider, api_key, from_email)
            mongo_uri: MongoDB URI
            db_name: Database name
        """
        self.slack_webhook_url = slack_webhook_url
        self.email_config = email_config or {}
        self.mongo = MongoClient(mongo_uri)
        self.db = self.mongo[db_name]
        self.logger = logging.getLogger(f"{__name__}.SERPAlertingSystem")
    
    def send_alert(
        self,
        alert_id: str,
        channels: List[str] = None
    ) -> Dict:
        """
        Trimite alertă pe canalele specificate
        
        Args:
            alert_id: ID alertă din MongoDB
            channels: Lista canale ('slack', 'email'); default: toate disponibile
        
        Returns:
            Dict cu status per canal
        """
        # Obține alertă din MongoDB
        try:
            obj_id = ObjectId(alert_id)
        except:
            obj_id = alert_id
        
        alert = self.db.serp_alerts.find_one({"_id": obj_id})
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        
        # Determine channels
        if channels is None:
            channels = []
            if self.slack_webhook_url:
                channels.append("slack")
            if self.email_config.get("api_key"):
                channels.append("email")
        
        # Send per channel
        results = {}
        
        if "slack" in channels and self.slack_webhook_url:
            try:
                results["slack"] = self._send_slack(alert)
            except Exception as e:
                self.logger.error(f"Slack send failed: {e}")
                results["slack"] = {"status": "error", "error": str(e)}
        
        if "email" in channels and self.email_config.get("api_key"):
            try:
                results["email"] = self._send_email(alert)
            except Exception as e:
                self.logger.error(f"Email send failed: {e}")
                results["email"] = {"status": "error", "error": str(e)}
        
        # Update alert în MongoDB
        self.db.serp_alerts.update_one(
            {"_id": obj_id},
            {"$set": {
                "notification_sent": True,
                "notification_channels": channels,
                "notification_results": results,
                "notification_sent_at": datetime.now(timezone.utc)
            }}
        )
        
        return results
    
    def _send_slack(self, alert: Dict, max_retries: int = 3) -> Dict:
        """
        Trimite alertă pe Slack cu rich formatting
        
        Args:
            alert: Alert document din MongoDB
            max_retries: Număr maxim retries
        
        Returns:
            Dict cu status
        """
        self.logger.info(f"📤 Sending Slack alert for {alert.get('alert_type')}")
        
        # Build Slack message cu blocks
        message = self._build_slack_message(alert)
        
        # Send cu retry logic
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.slack_webhook_url,
                    json=message,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.logger.info(f"✅ Slack alert sent successfully")
                    return {"status": "success", "attempt": attempt + 1}
                else:
                    self.logger.warning(f"Slack returned {response.status_code}: {response.text}")
            
            except Exception as e:
                self.logger.error(f"Slack send attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
        
        return {"status": "failed", "attempts": max_retries}
    
    def _build_slack_message(self, alert: Dict) -> Dict:
        """
        Construiește mesaj Slack cu blocks pentru rich formatting
        
        Args:
            alert: Alert document
        
        Returns:
            Dict payload pentru Slack
        """
        alert_type = alert.get("alert_type", "unknown")
        severity = alert.get("severity", "info")
        keyword = alert.get("keyword", "N/A")
        details = alert.get("details", {})
        actions = alert.get("actions_suggested", [])
        
        # Severity emoji
        severity_emoji = {
            "critical": "🔴",
            "warning": "⚠️",
            "info": "🟢"
        }.get(severity, "📌")
        
        # Alert type emoji
        type_emoji = {
            "rank_drop": "📉",
            "rank_gain": "📈",
            "new_competitor": "🆕",
            "out_of_top10": "❌",
            "into_top10": "✅"
        }.get(alert_type, "📊")
        
        # Build message
        text = f"{severity_emoji} {type_emoji} SERP Alert: {alert_type.replace('_', ' ').title()}"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} SERP Alert: {alert_type.replace('_', ' ').title()}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Keyword:*\n{keyword}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity.upper()}"
                    }
                ]
            }
        ]
        
        # Add details section
        if alert_type in ["rank_drop", "rank_gain"]:
            prev = details.get("previous_rank", "?")
            curr = details.get("current_rank", "?")
            delta = details.get("delta", 0)
            
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Previous Rank:*\n#{prev}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Current Rank:*\n#{curr}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Change:*\n{'+' if delta > 0 else ''}{delta} positions"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Domain:*\n{details.get('domain', 'N/A')}"
                    }
                ]
            })
        
        # Add actions section
        if actions:
            actions_text = "\n".join([f"• {action}" for action in actions[:3]])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Suggested Actions:*\n{actions_text}"
                }
            })
        
        # Add timestamp
        notified_at = alert.get("notified_at")
        if notified_at:
            ts_str = notified_at.strftime("%Y-%m-%d %H:%M UTC") if hasattr(notified_at, 'strftime') else str(notified_at)
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🕐 {ts_str}"
                    }
                ]
            })
        
        return {
            "text": text,  # Fallback text
            "blocks": blocks
        }
    
    def _send_email(self, alert: Dict) -> Dict:
        """
        Trimite alertă prin email (SendGrid sau Mailgun)
        
        Args:
            alert: Alert document
        
        Returns:
            Dict cu status
        """
        provider = self.email_config.get("provider", "sendgrid")
        
        if provider == "sendgrid":
            return self._send_email_sendgrid(alert)
        elif provider == "mailgun":
            return self._send_email_mailgun(alert)
        else:
            raise ValueError(f"Unknown email provider: {provider}")
    
    def _send_email_sendgrid(self, alert: Dict) -> Dict:
        """Send email via SendGrid"""
        # TODO: Implement SendGrid integration
        self.logger.info("📧 SendGrid email (not implemented yet)")
        return {"status": "not_implemented"}
    
    def _send_email_mailgun(self, alert: Dict) -> Dict:
        """Send email via Mailgun"""
        # TODO: Implement Mailgun integration
        self.logger.info("📧 Mailgun email (not implemented yet)")
        return {"status": "not_implemented"}
    
    def send_alert_batch(
        self,
        agent_id: str,
        severity_filter: Optional[str] = None,
        channels: List[str] = None
    ) -> Dict:
        """
        Trimite toate alertele nerecunoscute pentru un agent
        
        Args:
            agent_id: ID agent
            severity_filter: Filtrează după severitate (critical, warning, info)
            channels: Canale de notificare
        
        Returns:
            Dict cu statistici
        """
        query = {
            "agent_id": agent_id,
            "acknowledged": False,
            "notification_sent": {"$ne": True}
        }
        
        if severity_filter:
            query["severity"] = severity_filter
        
        alerts = list(self.db.serp_alerts.find(query))
        
        self.logger.info(f"📤 Sending {len(alerts)} alerts for agent {agent_id}")
        
        results = {
            "total": len(alerts),
            "sent": 0,
            "failed": 0,
            "details": []
        }
        
        for alert in alerts:
            try:
                alert_id = str(alert["_id"])
                res = self.send_alert(alert_id, channels)
                
                # Check if any channel succeeded
                if any(r.get("status") == "success" for r in res.values()):
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                
                results["details"].append({
                    "alert_id": alert_id,
                    "alert_type": alert.get("alert_type"),
                    "result": res
                })
            
            except Exception as e:
                self.logger.error(f"Error sending alert {alert.get('_id')}: {e}")
                results["failed"] += 1
        
        self.logger.info(f"✅ Batch send complete: {results['sent']}/{results['total']} sent")
        
        return results


# CLI pentru testing
if __name__ == "__main__":
    import sys
    import os
    
    # Example Slack webhook URL (din env var)
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    
    if not slack_webhook:
        print("⚠️ SLACK_WEBHOOK_URL not set. Using test mode.")
        print()
        print("To test Slack notifications:")
        print("   export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'")
        print("   python3 serp_alerting.py <agent_id>")
        print()
    
    # Initialize alerting system
    alerter = SERPAlertingSystem(slack_webhook_url=slack_webhook)
    
    if len(sys.argv) < 2:
        print("Usage: python3 serp_alerting.py <agent_id> [severity_filter]")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    severity_filter = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Send batch
    try:
        results = alerter.send_alert_batch(agent_id, severity_filter, channels=["slack"])
        
        print("="*80)
        print("🔔 SERP ALERTING - Batch Send Results")
        print("="*80)
        print()
        print(f"Total alerts: {results['total']}")
        print(f"   Sent: {results['sent']}")
        print(f"   Failed: {results['failed']}")
        print()
        
        if results['details']:
            print("Details:")
            for detail in results['details'][:5]:
                print(f"   - {detail['alert_type']}: {detail['result']}")
        
        print()
        print("="*80)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

