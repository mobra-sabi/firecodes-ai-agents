"""
Mirror Agent Central Dashboard
Issue 10: Dashboard central pentru toate mirror-urile
- Lista site-uri, scoruri KPI, latențe, alerte
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
from pymongo import MongoClient
import openai
from sentence_transformers import SentenceTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MirrorSiteStatus:
    """Status pentru un site Mirror"""
    site_id: str
    domain: str
    status: str  # "active", "inactive", "error", "provisioning"
    last_activity: datetime
    kpi_score: float
    latency_avg: float
    faq_size: int
    pages_size: int
    security_violations: int
    curator_promotions: int
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self):
        result = asdict(self)
        result['last_activity'] = self.last_activity.isoformat()
        result['created_at'] = self.created_at.isoformat()
        result['updated_at'] = self.updated_at.isoformat()
        return result

@dataclass
class DashboardAlert:
    """Alertă pentru dashboard"""
    alert_id: str
    site_id: str
    alert_type: str  # "performance", "security", "error", "maintenance"
    severity: str  # "low", "medium", "high", "critical"
    message: str
    details: Dict[str, Any]
    created_at: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self):
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        if self.resolved_at:
            result['resolved_at'] = self.resolved_at.isoformat()
        return result

class MirrorDashboardManager:
    """Manager pentru Dashboard-ul central Mirror Agents"""
    
    def __init__(self, api_base_url: str = "http://localhost:8083"):
        self.api_base_url = api_base_url
        self.db = MongoClient("mongodb://localhost:27017").mirror_dashboard
        self.openai_client = openai.OpenAI()
        
        # Cache pentru performanță
        self.site_status_cache = {}
        self.alerts_cache = []
        self.last_update = None
    
    async def get_global_dashboard(self) -> Dict[str, Any]:
        """Returnează dashboard-ul global pentru toate Mirror Agents"""
        logger.info("📊 Generating global Mirror Dashboard")
        
        try:
            # Obține toate site-urile
            sites = await self._get_all_sites()
            
            # Calculează statistici globale
            global_stats = await self._calculate_global_stats(sites)
            
            # Obține alertele active
            active_alerts = await self._get_active_alerts()
            
            # Obține top performers
            top_performers = await self._get_top_performers(sites)
            
            # Obține recent activity
            recent_activity = await self._get_recent_activity()
            
            # Calculează health score
            health_score = await self._calculate_health_score(sites, active_alerts)
            
            dashboard = {
                "ok": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "global_stats": global_stats,
                "sites": [site.to_dict() for site in sites],
                "active_alerts": [alert.to_dict() for alert in active_alerts],
                "top_performers": top_performers,
                "recent_activity": recent_activity,
                "health_score": health_score,
                "last_update": self.last_update.isoformat() if self.last_update else None
            }
            
            logger.info(f"✅ Global dashboard generated: {len(sites)} sites, {len(active_alerts)} alerts")
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating global dashboard: {e}")
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_site_dashboard(self, site_id: str) -> Dict[str, Any]:
        """Returnează dashboard-ul pentru un site specific"""
        logger.info(f"📊 Generating dashboard for site {site_id}")
        
        try:
            # Obține statusul site-ului
            site_status = await self._get_site_status(site_id)
            
            if not site_status:
                return {
                    "ok": False,
                    "error": f"Site {site_id} not found",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Obține statistici detaliate
            detailed_stats = await self._get_detailed_site_stats(site_id)
            
            # Obține alertele pentru site
            site_alerts = await self._get_site_alerts(site_id)
            
            # Obține istoricul KPI
            kpi_history = await self._get_kpi_history(site_id)
            
            # Obține activitatea recentă
            recent_activity = await self._get_site_recent_activity(site_id)
            
            dashboard = {
                "ok": True,
                "site_id": site_id,
                "site_status": site_status.to_dict(),
                "detailed_stats": detailed_stats,
                "alerts": [alert.to_dict() for alert in site_alerts],
                "kpi_history": kpi_history,
                "recent_activity": recent_activity,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"✅ Site dashboard generated for {site_id}")
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating site dashboard: {e}")
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _get_all_sites(self) -> List[MirrorSiteStatus]:
        """Obține toate site-urile Mirror"""
        try:
            # Caută în colecțiile Qdrant pentru a găsi site-urile
            sites = []
            
            # Caută în colecțiile de metadata
            collections_data = self.db.mirror_collections.find({})
            
            for collection_data in collections_data:
                site_id = collection_data.get("site_id")
                domain = collection_data.get("domain")
                
                if site_id and domain:
                    # Obține statusul site-ului
                    site_status = await self._get_site_status(site_id)
                    if site_status:
                        sites.append(site_status)
            
            return sites
            
        except Exception as e:
            logger.error(f"Error getting all sites: {e}")
            return []
    
    async def _get_site_status(self, site_id: str) -> Optional[MirrorSiteStatus]:
        """Obține statusul pentru un site"""
        try:
            # Verifică cache-ul
            if site_id in self.site_status_cache:
                cached_status = self.site_status_cache[site_id]
                if datetime.now(timezone.utc) - cached_status['timestamp'] < timedelta(minutes=5):
                    return cached_status['status']
            
            # Obține datele din baza de date
            site_data = self.db.mirror_sites.find_one({"site_id": site_id})
            
            if not site_data:
                # Încearcă să obțină datele din API
                site_data = await self._fetch_site_data_from_api(site_id)
                if not site_data:
                    return None
            
            # Creează obiectul status
            site_status = MirrorSiteStatus(
                site_id=site_id,
                domain=site_data.get("domain", "unknown"),
                status=site_data.get("status", "unknown"),
                last_activity=site_data.get("last_activity", datetime.now(timezone.utc)),
                kpi_score=site_data.get("kpi_score", 0.0),
                latency_avg=site_data.get("latency_avg", 0.0),
                faq_size=site_data.get("faq_size", 0),
                pages_size=site_data.get("pages_size", 0),
                security_violations=site_data.get("security_violations", 0),
                curator_promotions=site_data.get("curator_promotions", 0),
                created_at=site_data.get("created_at", datetime.now(timezone.utc)),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Adaugă în cache
            self.site_status_cache[site_id] = {
                'status': site_status,
                'timestamp': datetime.now(timezone.utc)
            }
            
            return site_status
            
        except Exception as e:
            logger.error(f"Error getting site status for {site_id}: {e}")
            return None
    
    async def _fetch_site_data_from_api(self, site_id: str) -> Optional[Dict[str, Any]]:
        """Obține datele site-ului din API"""
        try:
            # Încearcă să obțină datele din diferite endpoint-uri
            site_data = {
                "site_id": site_id,
                "status": "active",
                "last_activity": datetime.now(timezone.utc),
                "kpi_score": 0.0,
                "latency_avg": 0.0,
                "faq_size": 0,
                "pages_size": 0,
                "security_violations": 0,
                "curator_promotions": 0,
                "created_at": datetime.now(timezone.utc)
            }
            
            # Obține datele din colecții
            try:
                collections_response = requests.get(
                    f"{self.api_base_url}/mirror-collections/{site_id}",
                    timeout=5
                )
                if collections_response.status_code == 200:
                    collections_data = collections_response.json()
                    if collections_data.get("ok"):
                        collections = collections_data.get("collections", {})
                        site_data["pages_size"] = collections.get("pages", {}).get("vectors_count", 0)
                        site_data["faq_size"] = collections.get("faq", {}).get("vectors_count", 0)
            except:
                pass
            
            # Obține datele din curator
            try:
                curator_response = requests.get(
                    f"{self.api_base_url}/mirror-curator/dashboard/{site_id}",
                    timeout=5
                )
                if curator_response.status_code == 200:
                    curator_data = curator_response.json()
                    if curator_data.get("ok"):
                        site_data["curator_promotions"] = curator_data.get("stats", {}).get("faq_promotions", 0)
            except:
                pass
            
            # Obține datele din securitate
            try:
                security_response = requests.get(
                    f"{self.api_base_url}/mirror-security/dashboard/{site_id}",
                    timeout=5
                )
                if security_response.status_code == 200:
                    security_data = security_response.json()
                    if security_data.get("ok"):
                        site_data["security_violations"] = security_data.get("security_stats", {}).get("total_violations", 0)
            except:
                pass
            
            return site_data
            
        except Exception as e:
            logger.error(f"Error fetching site data from API: {e}")
            return None
    
    async def _calculate_global_stats(self, sites: List[MirrorSiteStatus]) -> Dict[str, Any]:
        """Calculează statisticile globale"""
        if not sites:
            return {
                "total_sites": 0,
                "active_sites": 0,
                "avg_kpi_score": 0.0,
                "avg_latency": 0.0,
                "total_faq_size": 0,
                "total_pages_size": 0,
                "total_security_violations": 0,
                "total_curator_promotions": 0
            }
        
        total_sites = len(sites)
        active_sites = sum(1 for site in sites if site.status == "active")
        avg_kpi_score = sum(site.kpi_score for site in sites) / total_sites
        avg_latency = sum(site.latency_avg for site in sites) / total_sites
        total_faq_size = sum(site.faq_size for site in sites)
        total_pages_size = sum(site.pages_size for site in sites)
        total_security_violations = sum(site.security_violations for site in sites)
        total_curator_promotions = sum(site.curator_promotions for site in sites)
        
        return {
            "total_sites": total_sites,
            "active_sites": active_sites,
            "avg_kpi_score": round(avg_kpi_score, 3),
            "avg_latency": round(avg_latency, 3),
            "total_faq_size": total_faq_size,
            "total_pages_size": total_pages_size,
            "total_security_violations": total_security_violations,
            "total_curator_promotions": total_curator_promotions
        }
    
    async def _get_active_alerts(self) -> List[DashboardAlert]:
        """Obține alertele active"""
        try:
            alerts = []
            
            # Caută alerte în baza de date
            alerts_data = self.db.dashboard_alerts.find({"resolved": False})
            
            for alert_data in alerts_data:
                alert = DashboardAlert(
                    alert_id=alert_data["alert_id"],
                    site_id=alert_data["site_id"],
                    alert_type=alert_data["alert_type"],
                    severity=alert_data["severity"],
                    message=alert_data["message"],
                    details=alert_data["details"],
                    created_at=alert_data["created_at"],
                    resolved=alert_data.get("resolved", False),
                    resolved_at=alert_data.get("resolved_at")
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    async def _get_top_performers(self, sites: List[MirrorSiteStatus]) -> Dict[str, List[Dict[str, Any]]]:
        """Obține top performers"""
        if not sites:
            return {"kpi": [], "latency": [], "faq_size": []}
        
        # Sortează după KPI score
        kpi_sorted = sorted(sites, key=lambda x: x.kpi_score, reverse=True)[:5]
        kpi_top = [{"site_id": site.site_id, "domain": site.domain, "score": site.kpi_score} for site in kpi_sorted]
        
        # Sortează după latență (cea mai mică)
        latency_sorted = sorted(sites, key=lambda x: x.latency_avg)[:5]
        latency_top = [{"site_id": site.site_id, "domain": site.domain, "latency": site.latency_avg} for site in latency_sorted]
        
        # Sortează după mărimea FAQ
        faq_sorted = sorted(sites, key=lambda x: x.faq_size, reverse=True)[:5]
        faq_top = [{"site_id": site.site_id, "domain": site.domain, "faq_size": site.faq_size} for site in faq_sorted]
        
        return {
            "kpi": kpi_top,
            "latency": latency_top,
            "faq_size": faq_top
        }
    
    async def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Obține activitatea recentă"""
        try:
            # Caută activitatea recentă în baza de date
            recent_activity = []
            
            # Caută în logurile de provisioning
            provisioning_logs = self.db.mirror_provisioning_logs.find().sort("timestamp", -1).limit(10)
            for log in provisioning_logs:
                recent_activity.append({
                    "type": "provisioning",
                    "site_id": log.get("site_id"),
                    "domain": log.get("domain"),
                    "message": f"Mirror Agent provisioned for {log.get('domain')}",
                    "timestamp": log.get("timestamp"),
                    "success": log.get("success", False)
                })
            
            # Caută în logurile de curator
            curator_logs = self.db.mirror_curator_logs.find().sort("timestamp", -1).limit(10)
            for log in curator_logs:
                recent_activity.append({
                    "type": "curator",
                    "site_id": log.get("site_id"),
                    "domain": log.get("domain"),
                    "message": f"FAQ promotion: {log.get('promotions', 0)} items",
                    "timestamp": log.get("timestamp"),
                    "success": log.get("success", False)
                })
            
            # Sortează după timestamp
            recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return recent_activity[:20]  # Ultimele 20 activități
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []
    
    async def _calculate_health_score(self, sites: List[MirrorSiteStatus], alerts: List[DashboardAlert]) -> float:
        """Calculează health score-ul global"""
        if not sites:
            return 0.0
        
        # Calculează scorul bazat pe site-uri
        site_scores = []
        for site in sites:
            score = 0.0
            
            # KPI score (40%)
            score += site.kpi_score * 0.4
            
            # Status (30%)
            if site.status == "active":
                score += 0.3
            elif site.status == "inactive":
                score += 0.1
            
            # Latență (20%) - mai mică este mai bună
            latency_score = max(0, 1 - (site.latency_avg / 1000))  # Normalizează la 1s
            score += latency_score * 0.2
            
            # Securitate (10%) - mai puține încălcări este mai bun
            security_score = max(0, 1 - (site.security_violations / 10))  # Normalizează la 10 încălcări
            score += security_score * 0.1
            
            site_scores.append(min(1.0, score))
        
        # Calculează media
        avg_site_score = sum(site_scores) / len(site_scores)
        
        # Ajustează pentru alerte
        alert_penalty = 0.0
        for alert in alerts:
            if alert.severity == "critical":
                alert_penalty += 0.1
            elif alert.severity == "high":
                alert_penalty += 0.05
            elif alert.severity == "medium":
                alert_penalty += 0.02
        
        health_score = max(0.0, avg_site_score - alert_penalty)
        return round(health_score, 3)
    
    async def _get_detailed_site_stats(self, site_id: str) -> Dict[str, Any]:
        """Obține statistici detaliate pentru un site"""
        try:
            stats = {
                "collections": {},
                "router": {},
                "curator": {},
                "security": {},
                "kpi": {}
            }
            
            # Obține datele din colecții
            try:
                collections_response = requests.get(
                    f"{self.api_base_url}/mirror-collections/{site_id}",
                    timeout=5
                )
                if collections_response.status_code == 200:
                    collections_data = collections_response.json()
                    if collections_data.get("ok"):
                        stats["collections"] = collections_data.get("collections", {})
            except:
                pass
            
            # Obține datele din router
            try:
                router_response = requests.get(
                    f"{self.api_base_url}/mirror-router/stats/{site_id}",
                    timeout=5
                )
                if router_response.status_code == 200:
                    router_data = router_response.json()
                    if router_data.get("ok"):
                        stats["router"] = router_data.get("stats", {})
            except:
                pass
            
            # Obține datele din curator
            try:
                curator_response = requests.get(
                    f"{self.api_base_url}/mirror-curator/dashboard/{site_id}",
                    timeout=5
                )
                if curator_response.status_code == 200:
                    curator_data = curator_response.json()
                    if curator_data.get("ok"):
                        stats["curator"] = curator_data.get("stats", {})
            except:
                pass
            
            # Obține datele din securitate
            try:
                security_response = requests.get(
                    f"{self.api_base_url}/mirror-security/dashboard/{site_id}",
                    timeout=5
                )
                if security_response.status_code == 200:
                    security_data = security_response.json()
                    if security_data.get("ok"):
                        stats["security"] = security_data.get("security_stats", {})
            except:
                pass
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting detailed site stats: {e}")
            return {}
    
    async def _get_site_alerts(self, site_id: str) -> List[DashboardAlert]:
        """Obține alertele pentru un site specific"""
        try:
            alerts = []
            alerts_data = self.db.dashboard_alerts.find({"site_id": site_id})
            
            for alert_data in alerts_data:
                alert = DashboardAlert(
                    alert_id=alert_data["alert_id"],
                    site_id=alert_data["site_id"],
                    alert_type=alert_data["alert_type"],
                    severity=alert_data["severity"],
                    message=alert_data["message"],
                    details=alert_data["details"],
                    created_at=alert_data["created_at"],
                    resolved=alert_data.get("resolved", False),
                    resolved_at=alert_data.get("resolved_at")
                )
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting site alerts: {e}")
            return []
    
    async def _get_kpi_history(self, site_id: str) -> List[Dict[str, Any]]:
        """Obține istoricul KPI pentru un site"""
        try:
            kpi_history = []
            kpi_data = self.db.mirror_kpi_results.find({"site_id": site_id}).sort("timestamp", -1).limit(20)
            
            for kpi in kpi_data:
                kpi_history.append({
                    "timestamp": kpi.get("timestamp"),
                    "overall_score": kpi.get("overall_score", 0.0),
                    "groundedness": kpi.get("groundedness", 0.0),
                    "helpfulness": kpi.get("helpfulness", 0.0),
                    "accuracy": kpi.get("accuracy", 0.0),
                    "latency": kpi.get("latency", 0.0),
                    "coverage": kpi.get("coverage", 0.0),
                    "fallback_rate": kpi.get("fallback_rate", 0.0)
                })
            
            return kpi_history
            
        except Exception as e:
            logger.error(f"Error getting KPI history: {e}")
            return []
    
    async def _get_site_recent_activity(self, site_id: str) -> List[Dict[str, Any]]:
        """Obține activitatea recentă pentru un site"""
        try:
            recent_activity = []
            
            # Caută în logurile de curator
            curator_logs = self.db.mirror_curator_logs.find({"site_id": site_id}).sort("timestamp", -1).limit(10)
            for log in curator_logs:
                recent_activity.append({
                    "type": "curator",
                    "message": f"FAQ promotion: {log.get('promotions', 0)} items",
                    "timestamp": log.get("timestamp"),
                    "success": log.get("success", False)
                })
            
            # Caută în logurile de router
            router_logs = self.db.mirror_router_logs.find({"site_id": site_id}).sort("timestamp", -1).limit(10)
            for log in router_logs:
                recent_activity.append({
                    "type": "router",
                    "message": f"Question routed: {log.get('action', 'unknown')}",
                    "timestamp": log.get("timestamp"),
                    "success": log.get("success", False)
                })
            
            # Sortează după timestamp
            recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return recent_activity[:20]
            
        except Exception as e:
            logger.error(f"Error getting site recent activity: {e}")
            return []
    
    async def create_alert(self, site_id: str, alert_type: str, severity: str, 
                          message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Creează o alertă nouă"""
        try:
            alert_id = f"alert_{int(datetime.now().timestamp())}"
            
            alert = DashboardAlert(
                alert_id=alert_id,
                site_id=site_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                details=details or {},
                created_at=datetime.now(timezone.utc)
            )
            
            # Salvează în baza de date
            self.db.dashboard_alerts.insert_one(alert.to_dict())
            
            logger.info(f"🚨 Alert created: {alert_type} - {severity} for {site_id}")
            
            return {
                "ok": True,
                "alert_id": alert_id,
                "alert": alert.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def resolve_alert(self, alert_id: str) -> Dict[str, Any]:
        """Rezolvă o alertă"""
        try:
            result = self.db.dashboard_alerts.update_one(
                {"alert_id": alert_id},
                {
                    "$set": {
                        "resolved": True,
                        "resolved_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Alert resolved: {alert_id}")
                return {
                    "ok": True,
                    "alert_id": alert_id,
                    "resolved": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "ok": False,
                    "error": "Alert not found",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

# Funcții helper pentru API
async def get_global_mirror_dashboard() -> Dict[str, Any]:
    """Returnează dashboard-ul global pentru toate Mirror Agents"""
    dashboard_manager = MirrorDashboardManager()
    return await dashboard_manager.get_global_dashboard()

async def get_site_mirror_dashboard(site_id: str) -> Dict[str, Any]:
    """Returnează dashboard-ul pentru un site specific"""
    dashboard_manager = MirrorDashboardManager()
    return await dashboard_manager.get_site_dashboard(site_id)

async def create_mirror_alert(site_id: str, alert_type: str, severity: str, 
                            message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
    """Creează o alertă nouă pentru Mirror Agent"""
    dashboard_manager = MirrorDashboardManager()
    return await dashboard_manager.create_alert(site_id, alert_type, severity, message, details)

async def resolve_mirror_alert(alert_id: str) -> Dict[str, Any]:
    """Rezolvă o alertă Mirror Agent"""
    dashboard_manager = MirrorDashboardManager()
    return await dashboard_manager.resolve_alert(alert_id)
