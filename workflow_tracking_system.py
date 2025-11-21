"""
Workflow Tracking System - Monitorizează fiecare pas din planul de implementare
Generează rapoarte detaliate pentru fiecare trecere prin fiecare punct
"""

import os
import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from pymongo import MongoClient
from bson import ObjectId
import traceback

logger = logging.getLogger(__name__)


class WorkflowStep(Enum):
    """Pașii din planul de implementare"""
    # 1. Obiectiv
    CRAWL_START = "crawl_start"
    CRAWL_COMPLETE = "crawl_complete"
    VECTORS_GENERATED = "vectors_generated"
    SERP_MONITORING_12H = "serp_monitoring_12h"
    AGENT_COMMUNICATION = "agent_communication"
    SEO_PPC_ACTIONS_GENERATED = "seo_ppc_actions_generated"
    AUTO_EXECUTION = "auto_execution"
    
    # 2. Arhitectură
    FASTAPI_ORCHESTRATOR = "fastapi_orchestrator"
    LANGCHAIN_CHAINS = "langchain_chains"
    DEEPSEEK_DECISIONS = "deepseek_decisions"
    QWEN_KIMI_WORKERS = "qwen_kimi_workers"
    MONGODB_STORAGE = "mongodb_storage"
    QDRANT_VECTORS = "qdrant_vectors"
    SERP_PROVIDER = "serp_provider"
    GOOGLE_ADS_API = "google_ads_api"
    UI_DASHBOARD = "ui_dashboard"
    
    # 3. Tipuri de agenți
    MASTER_AGENT_CREATED = "master_agent_created"
    SLAVE_AGENT_CREATED = "slave_agent_created"
    STRATEG_AGENT_DECISION = "strateg_agent_decision"
    COPYWRITER_AGENT = "copywriter_agent"
    ONPAGE_OPTIMIZER = "onpage_optimizer"
    LINK_SUGGESTER = "link_suggester"
    SCHEMA_GENERATOR = "schema_generator"
    ADS_AGENT = "ads_agent"
    
    # 4. Model de date
    AGENTS_COLLECTION = "agents_collection"
    SERP_RUNS_COLLECTION = "serp_runs_collection"
    SERP_RESULTS_COLLECTION = "serp_results_collection"
    RANKS_HISTORY_COLLECTION = "ranks_history_collection"
    VISIBILITY_CALCULATED = "visibility_calculated"
    ORG_GRAPH_UPDATED = "org_graph_updated"
    ACTIONS_QUEUE_UPDATED = "actions_queue_updated"
    PLAYBOOKS_GENERATED = "playbooks_generated"
    EXEC_REPORTS_GENERATED = "exec_reports_generated"
    ALERTS_CREATED = "alerts_created"
    
    # 5. Fluxul principal
    CREATE_MASTER = "create_master"
    CRAWL_SPLIT_EMBED = "crawl_split_embed"
    QDRANT_STORAGE = "qdrant_storage"
    DEEPSEEK_SUBDOMAINS_KEYWORDS = "deepseek_subdomains_keywords"
    SERP_RUN_ALL_KW = "serp_run_all_kw"
    SERP_RESULTS_VISIBILITY = "serp_results_visibility"
    CREATE_SLAVES_TOP_COMPETITORS = "create_slaves_top_competitors"
    SLAVES_CRAWL_EMBED = "slaves_crawl_embed"
    GRAPH_MASTER_SLAVES = "graph_master_slaves"
    DEEPSEEK_REPORT = "deepseek_report"
    ACTION_ENGINE_EXECUTE = "action_engine_execute"
    MONITORING_12H_RERUN = "monitoring_12h_rerun"
    MONITORING_12H_DIFFS = "monitoring_12h_diffs"
    MONITORING_12H_ALERTS = "monitoring_12h_alerts"
    MONITORING_12H_ACTIONS = "monitoring_12h_actions"
    
    # 6. Orchestrare
    ORCHESTRATION_INPUT_SERP = "orchestration_input_serp"
    ORCHESTRATION_INPUT_VISIBILITY = "orchestration_input_visibility"
    ORCHESTRATION_INPUT_GAPS = "orchestration_input_gaps"
    ORCHESTRATION_INPUT_KPI = "orchestration_input_kpi"
    ORCHESTRATION_OUTPUT_PLAYBOOK = "orchestration_output_playbook"
    ORCHESTRATION_OUTPUT_ACTIONS_QUEUE = "orchestration_output_actions_queue"
    ORCHESTRATION_GUARDRAILS = "orchestration_guardrails"
    
    # 7. API Endpoints
    API_AGENT_CREATE = "api_agent_create"
    API_AGENT_INGEST = "api_agent_ingest"
    API_KEYWORDS_GENERATE = "api_keywords_generate"
    API_SERP_RUN = "api_serp_run"
    API_COMPETITORS_FROM_SERP = "api_competitors_from_serp"
    API_GRAPH_UPDATE = "api_graph_update"
    API_REPORT_DEEPSEEK = "api_report_deepseek"
    API_ACTIONS_QUEUE = "api_actions_queue"
    API_ADS_SYNC = "api_ads_sync"
    API_VISIBILITY_LATEST = "api_visibility_latest"
    API_ALERTS = "api_alerts"
    WS_JOBS_LIVE = "ws_jobs_live"
    
    # 8. Scoruri & decizie
    RANK_NORMALIZED = "rank_normalized"
    VISIBILITY_COMPETITOR = "visibility_competitor"
    ICE_ACTIONS_CALCULATED = "ice_actions_calculated"
    
    # 9. Action Engine
    COPYWRITER_NEW_PAGES = "copywriter_new_pages"
    COPYWRITER_FAQ = "copywriter_faq"
    COPYWRITER_SCHEMA_JSONLD = "copywriter_schema_jsonld"
    ONPAGE_H1_META = "onpage_h1_meta"
    ONPAGE_CTA = "onpage_cta"
    ONPAGE_INTERNAL_LINKS = "onpage_internal_links"
    INTERLINKING_SUGGESTIONS = "interlinking_suggestions"
    ADS_CAMPAIGNS_CREATED = "ads_campaigns_created"
    ADS_AD_GROUPS_CREATED = "ads_ad_groups_created"
    EXPERIMENT_AB_STARTED = "experiment_ab_started"
    EXPERIMENT_AB_WINNER = "experiment_ab_winner"
    
    # 10. Monitorizare & alerte
    JOB_RERUN_SERP = "job_rerun_serp"
    JOB_CALCULATE_DIFFS = "job_calculate_diffs"
    JOB_UPDATE_GRAPH = "job_update_graph"
    JOB_REFRESH_PLAYBOOK = "job_refresh_playbook"
    ALERT_RANK_DROP = "alert_rank_drop"
    ALERT_COMPETITOR_NEW = "alert_competitor_new"
    ALERT_CTR_LOW = "alert_ctr_low"
    KPI_RANK_TARGET = "kpi_rank_target"
    KPI_CTR = "kpi_ctr"
    KPI_TIME_ON_PAGE = "kpi_time_on_page"
    KPI_LEADS = "kpi_leads"
    
    # 11. UI Panouri
    UI_OVERVIEW_LOADED = "ui_overview_loaded"
    UI_SERP_HEATMAP = "ui_serp_heatmap"
    UI_TRENDS_RANK = "ui_trends_rank"
    UI_AGENTS_LIST = "ui_agents_list"
    UI_ACTIONS_QUEUE = "ui_actions_queue"
    UI_ALERTS_LIST = "ui_alerts_list"
    
    # 12. Securitate & fiabilitate
    RATE_LIMIT_SERP = "rate_limit_serp"
    PROXY_POOL_ROTATION = "proxy_pool_rotation"
    RETRIES_BACKOFF = "retries_backoff"
    ROBOTS_TOS_RESPECT = "robots_tos_respect"
    AUDIT_LOGS_NDJSON = "audit_logs_ndjson"
    BACKUPS_MONGO_QDRANT = "backups_mongo_qdrant"
    HEALTH_CHECKS = "health_checks"
    METRICS_VRAM_LATENCY = "metrics_vram_latency"
    
    # 13. Google Ads
    ADS_MAP_KW_INTENT = "ads_map_kw_intent"
    ADS_CAMPAIGN_CREATED = "ads_campaign_created"
    ADS_AD_GROUPS_CREATED_FROM_KW = "ads_ad_groups_created_from_kw"
    ADS_KEYWORDS_ADDED = "ads_keywords_added"
    ADS_RSA_ADS_CREATED = "ads_rsa_ads_created"
    ADS_BIDDING_CONFIGURED = "ads_bidding_configured"
    ADS_NEGATIVE_KW_ADDED = "ads_negative_kw_added"
    ADS_GA4_GSC_SYNC = "ads_ga4_gsc_sync"
    
    # 14. Roadmap execuție
    ROADMAP_WEEK1_ENDPOINTS = "roadmap_week1_endpoints"
    ROADMAP_WEEK1_CRAWL_EMBED = "roadmap_week1_crawl_embed"
    ROADMAP_WEEK1_SERP_RUN = "roadmap_week1_serp_run"
    ROADMAP_WEEK1_VISIBILITY = "roadmap_week1_visibility"
    ROADMAP_WEEK1_GRAPH = "roadmap_week1_graph"
    ROADMAP_WEEK1_UI_BASIC = "roadmap_week1_ui_basic"
    ROADMAP_WEEK2_DEEPSEEK_REPORT = "roadmap_week2_deepseek_report"
    ROADMAP_WEEK2_ACTION_ENGINE = "roadmap_week2_action_engine"
    ROADMAP_WEEK2_ALERTS_12H = "roadmap_week2_alerts_12h"
    ROADMAP_WEEK2_DASHBOARD_LIVE = "roadmap_week2_dashboard_live"
    ROADMAP_WEEK3_ADS_AGENT = "roadmap_week3_ads_agent"
    ROADMAP_WEEK3_AB_TESTING = "roadmap_week3_ab_testing"
    ROADMAP_WEEK3_PLAYBOOKS = "roadmap_week3_playbooks"
    ROADMAP_WEEK3_EXPORT_PDF = "roadmap_week3_export_pdf"
    ROADMAP_WEEK4_HARDENING = "roadmap_week4_hardening"
    ROADMAP_WEEK4_GUARDRAILS = "roadmap_week4_guardrails"
    ROADMAP_WEEK4_AUTO_ROLLBACK = "roadmap_week4_auto_rollback"
    ROADMAP_WEEK4_PERF_CACHING = "roadmap_week4_perf_caching"
    
    # 15. Definition of Done
    DOD_AGENTS_CREATED = "dod_agents_created"
    DOD_INDEXED_QDRANT = "dod_indexed_qdrant"
    DOD_SERP_12H_RUNNING = "dod_serp_12h_running"
    DOD_VISIBILITY_GRAPH_UPDATED = "dod_visibility_graph_updated"
    DOD_DEEPSEEK_EXECUTIVE_SUMMARY = "dod_deepseek_executive_summary"
    DOD_DEEPSEEK_NEXT_ACTIONS = "dod_deepseek_next_actions"
    DOD_ACTION_ENGINE_EXECUTE = "dod_action_engine_execute"
    DOD_ADS_AGENT_SYNC = "dod_ads_agent_sync"
    DOD_DASHBOARD_LIVE = "dod_dashboard_live"
    DOD_ALERTS_FUNCTIONAL = "dod_alerts_functional"
    DOD_KPI_TRACKED = "dod_kpi_tracked"


class StepStatus(Enum):
    """Status pentru fiecare pas"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class WorkflowTracker:
    """
    Sistem de tracking pentru fiecare pas din planul de implementare
    Generează rapoarte detaliate pentru fiecare trecere
    """
    
    def __init__(self, mongo_client: MongoClient):
        self.mongo = mongo_client
        self.db = mongo_client["ai_agents_db"]
        self.collection = self.db["workflow_tracking"]
        
        # Creează indexuri
        self._initialize_indexes()
        
        logger.info("✅ Workflow Tracker initialized")
    
    def _initialize_indexes(self):
        """Creează indexuri pentru performanță"""
        try:
            self.collection.create_index([("agent_id", 1), ("step", 1), ("timestamp", -1)])
            self.collection.create_index([("step", 1), ("status", 1)])
            self.collection.create_index([("timestamp", -1)])
            self.collection.create_index([("agent_id", 1), ("timestamp", -1)])
            logger.info("✅ Workflow tracking indexes created")
        except Exception as e:
            logger.warning(f"⚠️ Could not create indexes: {e}")
    
    def track_step(
        self,
        step: WorkflowStep,
        agent_id: Optional[str] = None,
        status: StepStatus = StepStatus.IN_PROGRESS,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track un pas din workflow
        
        Args:
            step: Pasul din WorkflowStep enum
            agent_id: ID-ul agentului (dacă aplicabil)
            status: Status-ul pasului
            details: Detalii despre execuție
            error: Mesaj de eroare (dacă există)
            metadata: Metadata suplimentară
        
        Returns:
            ID-ul entry-ului creat
        """
        entry = {
            "step": step.value,
            "step_name": step.name,
            "agent_id": agent_id,
            "status": status.value,
            "timestamp": datetime.now(timezone.utc),
            "details": details or {},
            "error": error,
            "metadata": metadata or {},
            "duration_ms": None,  # Va fi actualizat când se completează
        }
        
        # Dacă există un entry anterior pentru același step și agent, actualizează-l
        if agent_id and status == StepStatus.IN_PROGRESS:
            existing = self.collection.find_one({
                "agent_id": agent_id,
                "step": step.value,
                "status": StepStatus.IN_PROGRESS.value
            })
            if existing:
                entry["_id"] = existing["_id"]
                entry["start_time"] = existing.get("start_time", existing["timestamp"])
                entry["timestamp"] = datetime.now(timezone.utc)
        
        if "_id" in entry:
            self.collection.update_one(
                {"_id": entry["_id"]},
                {"$set": entry}
            )
            entry_id = str(entry["_id"])
        else:
            entry["start_time"] = entry["timestamp"]
            result = self.collection.insert_one(entry)
            entry_id = str(result.inserted_id)
        
        logger.info(f"📊 Tracked step: {step.value} | Agent: {agent_id} | Status: {status.value}")
        
        return entry_id
    
    def complete_step(
        self,
        step: WorkflowStep,
        agent_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Marchează un pas ca fiind completat
        
        Returns:
            True dacă a fost actualizat cu succes
        """
        query = {
            "step": step.value,
            "status": StepStatus.IN_PROGRESS.value
        }
        if agent_id:
            query["agent_id"] = agent_id
        
        entry = self.collection.find_one(query, sort=[("timestamp", -1)])
        
        if not entry:
            # Creează un entry nou dacă nu există
            self.track_step(
                step=step,
                agent_id=agent_id,
                status=StepStatus.COMPLETED,
                details=details,
                metadata=metadata
            )
            return True
        
        # Calculează durata
        start_time = entry.get("start_time", entry["timestamp"])
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        update = {
            "status": StepStatus.COMPLETED.value,
            "timestamp": datetime.now(timezone.utc),
            "duration_ms": duration_ms,
        }
        
        if details:
            update["details"] = {**entry.get("details", {}), **details}
        
        if metadata:
            update["metadata"] = {**entry.get("metadata", {}), **metadata}
        
        result = self.collection.update_one(
            {"_id": entry["_id"]},
            {"$set": update}
        )
        
        logger.info(f"✅ Completed step: {step.value} | Agent: {agent_id} | Duration: {duration_ms:.0f}ms")
        
        return result.modified_count > 0
    
    def fail_step(
        self,
        step: WorkflowStep,
        agent_id: Optional[str] = None,
        error: str = None,
        error_traceback: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Marchează un pas ca fiind eșuat
        
        Returns:
            True dacă a fost actualizat cu succes
        """
        query = {
            "step": step.value,
            "status": StepStatus.IN_PROGRESS.value
        }
        if agent_id:
            query["agent_id"] = agent_id
        
        entry = self.collection.find_one(query, sort=[("timestamp", -1)])
        
        if not entry:
            # Creează un entry nou dacă nu există
            self.track_step(
                step=step,
                agent_id=agent_id,
                status=StepStatus.FAILED,
                error=error,
                details=details
            )
            return True
        
        # Calculează durata
        start_time = entry.get("start_time", entry["timestamp"])
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        update = {
            "status": StepStatus.FAILED.value,
            "timestamp": datetime.now(timezone.utc),
            "duration_ms": duration_ms,
            "error": error,
        }
        
        if error_traceback:
            update["error_traceback"] = error_traceback
        
        if details:
            update["details"] = {**entry.get("details", {}), **details}
        
        result = self.collection.update_one(
            {"_id": entry["_id"]},
            {"$set": update}
        )
        
        logger.error(f"❌ Failed step: {step.value} | Agent: {agent_id} | Error: {error}")
        
        return result.modified_count > 0
    
    def get_agent_steps(
        self,
        agent_id: Optional[str] = None,
        step: Optional[WorkflowStep] = None,
        status: Optional[StepStatus] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Obține toate pașii pentru un agent sau toți agenții
        
        Args:
            agent_id: ID-ul agentului (None pentru toți agenții)
            step: Filtră după step (None pentru toți pașii)
            status: Filtră după status (None pentru toate statusurile)
            limit: Numărul maxim de rezultate
            
        Returns:
            Lista de entry-uri
        """
        query = {}
        if agent_id:
            query["agent_id"] = agent_id
        
        if step:
            query["step"] = step.value
        
        if status:
            query["status"] = status.value
        
        entries = list(
            self.collection.find(query)
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        for entry in entries:
            entry["_id"] = str(entry["_id"])
            if "timestamp" in entry:
                entry["timestamp"] = entry["timestamp"].isoformat()
            if "start_time" in entry:
                entry["start_time"] = entry["start_time"].isoformat()
        
        return entries
    
    def get_step_summary(
        self,
        step: WorkflowStep,
        agent_id: Optional[str] = None,
        days: int = 7
    ) -> Dict:
        """
        Obține un summary pentru un pas specific
        
        Returns:
            Dict cu statistici
        """
        from datetime import timedelta
        
        query = {
            "step": step.value,
            "timestamp": {
                "$gte": datetime.now(timezone.utc) - timedelta(days=days)
            }
        }
        
        if agent_id:
            query["agent_id"] = agent_id
        
        total = self.collection.count_documents(query)
        completed = self.collection.count_documents({**query, "status": StepStatus.COMPLETED.value})
        failed = self.collection.count_documents({**query, "status": StepStatus.FAILED.value})
        in_progress = self.collection.count_documents({**query, "status": StepStatus.IN_PROGRESS.value})
        
        # Calculează durata medie
        completed_entries = list(
            self.collection.find({**query, "status": StepStatus.COMPLETED.value})
            .sort("timestamp", -1)
            .limit(100)
        )
        
        avg_duration = None
        if completed_entries:
            durations = [e.get("duration_ms", 0) for e in completed_entries if e.get("duration_ms")]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return {
            "step": step.value,
            "step_name": step.name,
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "avg_duration_ms": avg_duration,
            "days": days
        }
    
    def generate_report(
        self,
        agent_id: Optional[str] = None,
        steps: Optional[List[WorkflowStep]] = None,
        days: int = 7
    ) -> Dict:
        """
        Generează un raport complet pentru agent sau pentru toți agenții
        
        Returns:
            Dict cu raport complet
        """
        from datetime import timedelta
        
        query = {
            "timestamp": {
                "$gte": datetime.now(timezone.utc) - timedelta(days=days)
            }
        }
        
        if agent_id:
            query["agent_id"] = agent_id
        
        if steps:
            query["step"] = {"$in": [s.value for s in steps]}
        
        entries = list(self.collection.find(query).sort("timestamp", -1))
        
        # Grupează pe step
        steps_summary = {}
        for entry in entries:
            step = entry["step"]
            if step not in steps_summary:
                steps_summary[step] = {
                    "total": 0,
                    "completed": 0,
                    "failed": 0,
                    "in_progress": 0,
                    "entries": []
                }
            
            steps_summary[step]["total"] += 1
            steps_summary[step]["entries"].append({
                "agent_id": entry.get("agent_id"),
                "status": entry["status"],
                "timestamp": entry["timestamp"].isoformat() if isinstance(entry["timestamp"], datetime) else entry["timestamp"],
                "duration_ms": entry.get("duration_ms"),
                "error": entry.get("error"),
                "details": entry.get("details", {})
            })
            
            if entry["status"] == StepStatus.COMPLETED.value:
                steps_summary[step]["completed"] += 1
            elif entry["status"] == StepStatus.FAILED.value:
                steps_summary[step]["failed"] += 1
            elif entry["status"] == StepStatus.IN_PROGRESS.value:
                steps_summary[step]["in_progress"] += 1
        
        # Calculează statistici generale
        total_entries = len(entries)
        total_completed = sum(s["completed"] for s in steps_summary.values())
        total_failed = sum(s["failed"] for s in steps_summary.values())
        
        return {
            "agent_id": agent_id,
            "period_days": days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_entries": total_entries,
                "total_completed": total_completed,
                "total_failed": total_failed,
                "total_in_progress": sum(s["in_progress"] for s in steps_summary.values()),
                "success_rate": (total_completed / total_entries * 100) if total_entries > 0 else 0
            },
            "steps": steps_summary
        }


# Singleton instance
_tracker_instance = None

def get_workflow_tracker(mongo_client: MongoClient = None) -> WorkflowTracker:
    """Get or create workflow tracker instance"""
    global _tracker_instance
    
    if _tracker_instance is None:
        if mongo_client is None:
            mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
            mongo_client = MongoClient(mongo_uri)
        
        _tracker_instance = WorkflowTracker(mongo_client)
    
    return _tracker_instance

