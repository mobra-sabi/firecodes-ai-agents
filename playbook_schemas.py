#!/usr/bin/env python3
"""
📋 SEO Playbook MongoDB Schemas
Production-ready pentru Action Engine (FAZA 3)
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from bson import ObjectId


# ============================================================================
# PLAYBOOK SCHEMA
# ============================================================================

class PlaybookKPI(BaseModel):
    """KPI pentru măsurare success playbook"""
    name: str  # Ex: "rank_delta", "CTR", "time_on_page", "leads"
    target_value: float  # Ex: 5.0 (pentru rank_delta)
    current_value: Optional[float] = None
    unit: str  # Ex: "positions", "%", "seconds", "count"
    priority: Literal["critical", "high", "medium", "low"] = "medium"


class PlaybookAction(BaseModel):
    """Acțiune individuală din playbook"""
    action_id: str  # Ex: "A1", "A2", "A3"
    type: Literal[
        "content_creation",
        "onpage_optimization",
        "internal_linking",
        "schema_markup",
        "ab_testing",
        "technical_seo"
    ]
    title: str  # Ex: "Creează ghid complet 'vopsea intumescentă H120'"
    description: str  # Descriere detaliată
    agent: str  # Ex: "CopywriterAgent", "OnPageOptimizer"
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"] = "pending"
    deadline: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    assigned_keywords: List[str] = []
    parameters: Dict = {}  # Parametri specifici agentului
    dependencies: List[str] = []  # Liste action_id dependente
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None  # Output acțiune


class PlaybookGuardrails(BaseModel):
    """Guardrails pentru siguranță și rollback"""
    max_changes_per_day: int = 5
    require_approval: bool = False
    rollback_on_rank_drop: int = 5  # Rollback dacă rank drop > 5 poziții
    noindex_threshold: int = 10  # Dacă rank drop > 10 → noindex temporar
    blacklist_keywords: List[str] = []  # Keywords de evitat
    min_content_quality_score: float = 0.7  # 0-1
    max_keyword_density: float = 0.03  # 3%


class SEOPlaybook(BaseModel):
    """
    🎯 SEO Playbook complet pentru un agent
    
    Generat de DeepSeek pe baza:
    - SERP analysis
    - Competitor intelligence
    - Content gaps
    - Ranking opportunities
    """
    playbook_id: str = Field(default_factory=lambda: str(ObjectId()))
    agent_id: str  # Master agent ID
    title: str  # Ex: "DELEXPERT.EU - Sprint SEO 14 zile"
    description: str
    
    # Objectives
    objectives: List[str] = []  # Ex: ["Rank top 5 pe KW principal", "CTR ≥ 4.5%"]
    kpis: List[PlaybookKPI] = []
    
    # Actions
    actions: List[PlaybookAction] = []
    total_actions: int = 0
    completed_actions: int = 0
    
    # Timeline
    sprint_duration_days: int = 14
    start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_date: Optional[datetime] = None
    
    # Guardrails
    guardrails: PlaybookGuardrails = Field(default_factory=PlaybookGuardrails)
    
    # Status
    status: Literal["draft", "active", "paused", "completed", "cancelled"] = "draft"
    
    # Metadata
    created_by: str = "DeepSeek"  # Agent care a generat playbook
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Results
    results: Optional[Dict] = None  # Rezultate finale playbook


# ============================================================================
# ACTION EXECUTION SCHEMA
# ============================================================================

class ActionExecution(BaseModel):
    """
    📊 Track execuție acțiune individuală
    Salvat separat în `action_executions` collection
    """
    execution_id: str = Field(default_factory=lambda: str(ObjectId()))
    playbook_id: str
    action_id: str
    agent_id: str  # Master agent
    
    # Agent execution
    executor_agent: str  # Ex: "CopywriterAgent"
    executor_model: str  # Ex: "qwen2.5-72b"
    
    # Status
    status: Literal["queued", "running", "completed", "failed", "cancelled"] = "queued"
    progress: float = 0.0  # 0-100
    
    # Timing
    queued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Input/Output
    input_parameters: Dict = {}
    output_result: Optional[Dict] = None
    
    # Monitoring
    logs: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    
    # KPI Impact
    kpi_before: Optional[Dict] = None  # KPIs înaintea acțiunii
    kpi_after: Optional[Dict] = None   # KPIs după acțiune
    impact_score: Optional[float] = None  # -1 to +1


# ============================================================================
# CONTENT GAP SCHEMA (pentru Playbook Generator)
# ============================================================================

class ContentGap(BaseModel):
    """
    🔍 Gap de conținut identificat de DeepSeek
    """
    keyword: str
    gap_type: Literal["missing_content", "thin_content", "outdated", "low_quality"]
    priority: Literal["critical", "high", "medium", "low"]
    opportunity_score: float  # 0-100
    
    # Analysis
    current_state: str  # Descriere situație curentă
    recommended_action: str  # Ce trebuie făcut
    estimated_traffic_gain: Optional[int] = None
    
    # Competitors
    top_competitors: List[str] = []  # Domains care performează bine
    competitor_content_length: Optional[int] = None  # Avg words
    
    # Keywords related
    related_keywords: List[str] = []
    search_intent: Literal["informational", "commercial", "transactional", "navigational"] = "informational"


# ============================================================================
# OPPORTUNITY SCHEMA
# ============================================================================

class SEOOpportunity(BaseModel):
    """
    💡 Oportunitate SEO identificată
    """
    opportunity_id: str = Field(default_factory=lambda: str(ObjectId()))
    agent_id: str
    
    type: Literal[
        "quick_win",          # Rank 11-15, ușor de îmbunătățit
        "content_gap",        # Lipsește conținut
        "featured_snippet",   # Oportunitate snippet
        "competitor_weakness", # Competitor slab pe keyword
        "rising_keyword"      # Keyword în creștere
    ]
    
    keyword: str
    current_position: Optional[int] = None
    target_position: int  # Ex: 5
    
    # Scoring
    opportunity_score: float  # 0-100
    difficulty: float  # 0-100
    roi_estimate: float  # 0-100
    
    # Details
    title: str
    description: str
    recommended_actions: List[str] = []
    
    # Status
    status: Literal["identified", "planned", "in_progress", "achieved", "dismissed"] = "identified"
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# MONGODB INDEXES (pentru performance)
# ============================================================================

PLAYBOOK_INDEXES = [
    {"keys": [("agent_id", 1), ("status", 1)], "name": "agent_status_idx"},
    {"keys": [("created_at", -1)], "name": "created_desc_idx"},
    {"keys": [("status", 1), ("start_date", -1)], "name": "status_date_idx"}
]

ACTION_EXECUTION_INDEXES = [
    {"keys": [("playbook_id", 1), ("status", 1)], "name": "playbook_status_idx"},
    {"keys": [("agent_id", 1), ("created_at", -1)], "name": "agent_created_idx"},
    {"keys": [("status", 1), ("queued_at", 1)], "name": "queue_idx"}
]

OPPORTUNITY_INDEXES = [
    {"keys": [("agent_id", 1), ("status", 1)], "name": "agent_status_idx"},
    {"keys": [("opportunity_score", -1)], "name": "score_desc_idx"},
    {"keys": [("type", 1), ("status", 1)], "name": "type_status_idx"}
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_playbook_indexes(db):
    """Creează indexuri MongoDB pentru playbook collections"""
    db.playbooks.create_indexes([{"keys": k["keys"], "name": k["name"]} for k in PLAYBOOK_INDEXES])
    db.action_executions.create_indexes([{"keys": k["keys"], "name": k["name"]} for k in ACTION_EXECUTION_INDEXES])
    db.seo_opportunities.create_indexes([{"keys": k["keys"], "name": k["name"]} for k in OPPORTUNITY_INDEXES])
    print("✅ Playbook indexes created")


def playbook_to_dict(playbook: SEOPlaybook) -> Dict:
    """Convert Pydantic model to MongoDB dict"""
    return playbook.model_dump(mode='json')


def action_execution_to_dict(execution: ActionExecution) -> Dict:
    """Convert ActionExecution to MongoDB dict"""
    return execution.model_dump(mode='json')


if __name__ == "__main__":
    # Test schemas
    playbook = SEOPlaybook(
        agent_id="691a34b65774faae88a735a1",
        title="DELEXPERT.EU - Sprint SEO 14 zile",
        description="Plan automat generat de DeepSeek pentru îmbunătățire ranking",
        objectives=[
            "Rank top 5 pe 'protecție pasivă la foc București'",
            "CTR ≥ 4.5%",
            "Leads +20%"
        ],
        kpis=[
            PlaybookKPI(name="rank_delta", target_value=5.0, unit="positions", priority="critical"),
            PlaybookKPI(name="CTR", target_value=4.5, unit="%", priority="high"),
            PlaybookKPI(name="leads", target_value=20.0, unit="%", priority="medium")
        ],
        actions=[
            PlaybookAction(
                action_id="A1",
                type="content_creation",
                title="Creează ghid complet 'Protecție pasivă la foc București - Ghid 2025'",
                description="Ghid de 2000+ cuvinte cu FAQ, imagini, schema JSON-LD",
                agent="CopywriterAgent",
                priority="critical",
                estimated_hours=3.0,
                assigned_keywords=["protecție pasivă la foc București"],
                parameters={
                    "target_word_count": 2000,
                    "include_faq": True,
                    "include_schema": True
                }
            )
        ],
        total_actions=1
    )
    
    print("✅ Playbook schema valid:")
    print(playbook.model_dump_json(indent=2))

