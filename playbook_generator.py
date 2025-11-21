#!/usr/bin/env python3
"""
🎯 SEO Playbook Generator - Powered by DeepSeek
Analizează SERP data + competitor intelligence → generează playbook strategic
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from pymongo import MongoClient
from bson import ObjectId

from playbook_schemas import (
    SEOPlaybook, PlaybookAction, PlaybookKPI, PlaybookGuardrails,
    ContentGap, SEOOpportunity, playbook_to_dict
)

logger = logging.getLogger(__name__)


class PlaybookGenerator:
    """
    🎯 Generator de playbook-uri SEO automate
    
    Folosește:
    - DeepSeek: Analiză strategică + planning
    - SERP data: Rankings, competitors, gaps
    - Competitive intelligence: Oportunități
    """
    
    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        db_name: str = "ai_agents_db"
    ):
        self.mongo = MongoClient(mongo_uri)
        self.db = self.mongo[db_name]
        self.logger = logging.getLogger(f"{__name__}.PlaybookGenerator")
        
        # Import LLM helper (REAL - NO MORE MOCKS!)
        from llm_helper import call_llm_with_fallback
        self.llm = call_llm_with_fallback
        self.logger.info("✅ LLM Helper loaded - REAL DeepSeek/Qwen calls enabled")
    
    async def generate_playbook(
        self,
        agent_id: str,
        sprint_days: int = 14,
        focus_keywords: Optional[List[str]] = None,
        custom_objectives: Optional[List[str]] = None
    ) -> str:
        """
        🎯 Generează playbook SEO complet pentru un agent
        
        Args:
            agent_id: Master agent ID
            sprint_days: Durata sprint (default 14 zile)
            focus_keywords: Keywords specifice (opțional)
            custom_objectives: Obiective custom (opțional)
        
        Returns:
            playbook_id (str)
        """
        self.logger.info(f"🎯 Generating SEO playbook for agent {agent_id}")
        
        # 1. Gather intelligence data
        intelligence = await self._gather_intelligence(agent_id, focus_keywords)
        
        # 2. Analyze with DeepSeek
        strategy = await self._deepseek_strategic_analysis(
            agent_id, 
            intelligence,
            custom_objectives
        )
        
        # 3. Generate actions
        actions = await self._generate_actions(strategy, intelligence)
        
        # 4. Create playbook
        playbook = SEOPlaybook(
            agent_id=agent_id,
            title=strategy.get("title", f"SEO Sprint {sprint_days} days"),
            description=strategy.get("description", "Automated SEO playbook"),
            objectives=strategy.get("objectives", []),
            kpis=self._create_kpis(strategy.get("kpis", [])),
            actions=actions,
            total_actions=len(actions),
            sprint_duration_days=sprint_days,
            guardrails=PlaybookGuardrails()
        )
        
        # 5. Save to MongoDB
        playbook_dict = playbook_to_dict(playbook)
        result = self.db.playbooks.insert_one(playbook_dict)
        playbook_id = str(result.inserted_id)
        
        self.logger.info(f"✅ Playbook {playbook_id} created with {len(actions)} actions")
        return playbook_id
    
    async def _gather_intelligence(
        self,
        agent_id: str,
        focus_keywords: Optional[List[str]] = None
    ) -> Dict:
        """
        📊 Colectează date intelligence pentru playbook
        
        Returns dict cu:
        - agent: Date agent
        - rankings: Statistici SERP
        - competitors: Leaderboard
        - content_gaps: Gap-uri identificate
        - opportunities: Oportunități quick-win
        """
        intelligence = {
            "agent": None,
            "rankings": None,
            "competitors": [],
            "content_gaps": [],
            "opportunities": []
        }
        
        # Agent data
        try:
            obj_id = ObjectId(agent_id)
        except:
            obj_id = agent_id
        
        agent = self.db.site_agents.find_one({"_id": obj_id})
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        intelligence["agent"] = {
            "site_url": agent.get("site_url"),
            "company_name": agent.get("company_name"),
            "industry": agent.get("industry"),
            "services": agent.get("services", [])
        }
        
        # Rankings statistics
        from rankings_monitor import RankingsMonitor
        monitor = RankingsMonitor()
        stats = monitor.calculate_agent_statistics(agent_id)
        intelligence["rankings"] = stats
        
        # Competitor leaderboard
        leaderboard = monitor.get_competitor_leaderboard(agent_id)
        intelligence["competitors"] = leaderboard[:10]  # Top 10
        
        # Content gaps (identify from SERP)
        intelligence["content_gaps"] = self._identify_content_gaps(
            agent_id, 
            stats,
            focus_keywords
        )
        
        # Opportunities (quick wins)
        intelligence["opportunities"] = self._identify_opportunities(
            agent_id,
            stats
        )
        
        return intelligence
    
    def _identify_content_gaps(
        self,
        agent_id: str,
        stats: Dict,
        focus_keywords: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        🔍 Identifică gap-uri de conținut din SERP data
        
        Gap types:
        - missing_content: Keyword unde nu apare în top 20
        - thin_content: Apare slab (pos 11-20)
        - low_quality: Competitors au conținut mai bun
        """
        gaps = []
        
        keywords_detail = stats.get("keywords_detail", [])
        
        for kw_data in keywords_detail:
            keyword = kw_data["keyword"]
            position = kw_data.get("position")
            
            # Skip dacă focus_keywords specificat și nu e în listă
            if focus_keywords and keyword not in focus_keywords:
                continue
            
            gap = None
            
            if position is None:
                # Missing content - nu apare în top 20
                gap = {
                    "keyword": keyword,
                    "gap_type": "missing_content",
                    "priority": "critical",
                    "opportunity_score": 85.0,
                    "current_state": "Not ranking in top 20",
                    "recommended_action": f"Create comprehensive content for '{keyword}'"
                }
            elif position > 10:
                # Thin content - poziție slabă 11-20
                gap = {
                    "keyword": keyword,
                    "gap_type": "thin_content",
                    "priority": "high",
                    "opportunity_score": 70.0,
                    "current_state": f"Ranking at position #{position}",
                    "recommended_action": f"Optimize existing content for '{keyword}'"
                }
            elif position > 3:
                # Medium priority - 4-10
                gap = {
                    "keyword": keyword,
                    "gap_type": "thin_content",
                    "priority": "medium",
                    "opportunity_score": 50.0,
                    "current_state": f"Ranking at position #{position}",
                    "recommended_action": f"Enhance content quality for '{keyword}'"
                }
            
            if gap:
                gaps.append(gap)
        
        return gaps
    
    def _identify_opportunities(
        self,
        agent_id: str,
        stats: Dict
    ) -> List[Dict]:
        """
        💡 Identifică oportunități SEO
        
        Types:
        - quick_win: Rank 11-15
        - featured_snippet: Oportunitate snippet
        - competitor_weakness: Competitor slab
        """
        opportunities = []
        
        keywords_detail = stats.get("keywords_detail", [])
        
        for kw_data in keywords_detail:
            keyword = kw_data["keyword"]
            position = kw_data.get("position")
            
            if position and 11 <= position <= 15:
                # Quick win - aproape de top 10
                opportunities.append({
                    "type": "quick_win",
                    "keyword": keyword,
                    "current_position": position,
                    "target_position": 8,
                    "opportunity_score": 90.0,
                    "difficulty": 30.0,
                    "roi_estimate": 85.0,
                    "title": f"Quick win: Move '{keyword}' to top 10",
                    "description": f"Currently at #{position}, optimize to reach top 10",
                    "recommended_actions": [
                        "Add 500+ words quality content",
                        "Optimize title & meta description",
                        "Add internal links",
                        "Add FAQ schema"
                    ]
                })
        
        return opportunities
    
    async def _deepseek_strategic_analysis(
        self,
        agent_id: str,
        intelligence: Dict,
        custom_objectives: Optional[List[str]] = None
    ) -> Dict:
        """
        🧠 Analiză strategică cu DeepSeek
        
        DeepSeek analizează:
        - Agent profile
        - Current rankings
        - Competitors
        - Content gaps
        - Opportunities
        
        Returns strategic plan cu objectives + recommended actions
        """
        # Build prompt pentru DeepSeek
        prompt = self._build_strategic_prompt(intelligence, custom_objectives)
        
        # Call DeepSeek
        self.logger.info("🧠 Calling DeepSeek for strategic analysis...")
        
        try:
            response = self.llm(
                prompt=prompt,
                model_preference="deepseek",
                max_tokens=4000,
                temperature=0.7
            )
            
            # Parse JSON response
            strategy = json.loads(response)
            
        except Exception as e:
            self.logger.error(f"DeepSeek analysis failed: {e}")
            # Fallback to basic strategy
            strategy = self._fallback_strategy(intelligence)
        
        return strategy
    
    def _build_strategic_prompt(
        self,
        intelligence: Dict,
        custom_objectives: Optional[List[str]] = None
    ) -> str:
        """Construiește prompt strategic pentru DeepSeek"""
        
        agent = intelligence["agent"]
        rankings = intelligence["rankings"]
        gaps = intelligence["content_gaps"]
        opportunities = intelligence["opportunities"]
        
        # Format services (podem fi dict sau string)
        services = agent.get('services', [])
        if services and isinstance(services[0], dict):
            services_str = ', '.join([s.get('name', str(s)) for s in services[:5]])
        else:
            services_str = ', '.join(services[:5]) if services else 'N/A'
        
        prompt = f"""You are an expert SEO strategist. Analyze the following data and create a comprehensive 14-day SEO action plan.

**AGENT PROFILE:**
Company: {agent['company_name']}
Industry: {agent['industry']}
Services: {services_str}

**CURRENT RANKINGS:**
- Total Keywords: {rankings.get('total_keywords', 0)}
- Top 3 positions: {rankings.get('master_positions', {}).get('top_3', 0)}
- Top 10 positions: {rankings.get('master_positions', {}).get('top_10', 0)}
- Average position: #{rankings.get('average_position', 'N/A')}
- Competitors: {rankings.get('unique_competitors', 0)}

**TOP COMPETITORS:**
{self._format_competitors(intelligence.get('competitors', [])[:3])}

**CONTENT GAPS ({len(gaps)}):**
{self._format_gaps(gaps[:5])}

**OPPORTUNITIES ({len(opportunities)}):**
{self._format_opportunities(opportunities[:3])}

{'**CUSTOM OBJECTIVES:**' if custom_objectives else ''}
{chr(10).join(f'- {obj}' for obj in (custom_objectives or []))}

**TASK:**
Generate a JSON response with:
1. "title": Strategic title for this playbook
2. "description": Brief description (2-3 sentences)
3. "objectives": List of 3-5 SMART objectives (specific, measurable)
4. "kpis": List of KPIs to track (name, target_value, unit, priority)
5. "recommended_actions": List of 5-10 prioritized actions with:
   - action_id (A1, A2, etc.)
   - type (content_creation, onpage_optimization, internal_linking, schema_markup)
   - title (concise action title)
   - description (detailed description)
   - priority (critical, high, medium, low)
   - estimated_hours (float)
   - assigned_keywords (list of relevant keywords)

Return ONLY valid JSON, no markdown formatting.
"""
        return prompt
    
    def _format_competitors(self, competitors: List[Dict]) -> str:
        """Format competitors pentru prompt"""
        if not competitors:
            return "None"
        lines = []
        for i, comp in enumerate(competitors, 1):
            lines.append(
                f"{i}. {comp['domain']} - {comp.get('appearances_top_10', 0)} appearances, "
                f"avg position #{comp.get('average_position', 0):.1f}"
            )
        return "\n".join(lines)
    
    def _format_gaps(self, gaps: List[Dict]) -> str:
        """Format content gaps pentru prompt"""
        if not gaps:
            return "None identified"
        lines = []
        for gap in gaps:
            lines.append(
                f"- {gap['keyword']} ({gap['gap_type']}, {gap['priority']} priority): "
                f"{gap['current_state']}"
            )
        return "\n".join(lines)
    
    def _format_opportunities(self, opportunities: List[Dict]) -> str:
        """Format opportunities pentru prompt"""
        if not opportunities:
            return "None identified"
        lines = []
        for opp in opportunities:
            lines.append(
                f"- {opp['keyword']} (#{opp.get('current_position', 'N/A')} → "
                f"#{opp['target_position']}): {opp['title']}"
            )
        return "\n".join(lines)
    
    def _fallback_strategy(self, intelligence: Dict) -> Dict:
        """Strategy fallback dacă DeepSeek fail"""
        gaps = intelligence["content_gaps"]
        opportunities = intelligence["opportunities"]
        
        return {
            "title": "SEO Improvement Sprint - 14 Days",
            "description": "Automated SEO playbook focused on content optimization and ranking improvements",
            "objectives": [
                "Improve average ranking by 3 positions",
                "Increase top 10 keywords by 50%",
                "Close critical content gaps"
            ],
            "kpis": [
                {"name": "rank_delta", "target_value": 3.0, "unit": "positions", "priority": "critical"},
                {"name": "top_10_count", "target_value": 50.0, "unit": "%", "priority": "high"}
            ],
            "recommended_actions": [
                {
                    "action_id": "A1",
                    "type": "content_creation",
                    "title": f"Create content for '{gaps[0]['keyword']}'" if gaps else "Create quality content",
                    "description": "Develop comprehensive SEO-optimized content",
                    "priority": "critical",
                    "estimated_hours": 3.0,
                    "assigned_keywords": [gaps[0]["keyword"]] if gaps else []
                }
            ]
        }
    
    async def _generate_actions(
        self,
        strategy: Dict,
        intelligence: Dict
    ) -> List[PlaybookAction]:
        """
        🎬 Generează lista de PlaybookAction din strategie
        """
        actions = []
        
        recommended = strategy.get("recommended_actions", [])
        
        for rec in recommended:
            action = PlaybookAction(
                action_id=rec.get("action_id", f"A{len(actions)+1}"),
                type=rec.get("type", "content_creation"),
                title=rec.get("title", "Unnamed action"),
                description=rec.get("description", ""),
                agent=self._map_type_to_agent(rec.get("type")),
                priority=rec.get("priority", "medium"),
                estimated_hours=rec.get("estimated_hours", 2.0),
                assigned_keywords=rec.get("assigned_keywords", []),
                parameters=rec.get("parameters", {})
            )
            actions.append(action)
        
        return actions
    
    def _map_type_to_agent(self, action_type: str) -> str:
        """Map action type to executor agent"""
        mapping = {
            "content_creation": "CopywriterAgent",
            "onpage_optimization": "OnPageOptimizer",
            "internal_linking": "LinkSuggester",
            "schema_markup": "SchemaGenerator",
            "ab_testing": "ExperimentRunner",
            "technical_seo": "TechnicalSEOAgent"
        }
        return mapping.get(action_type, "GenericAgent")
    
    def _create_kpis(self, kpi_data: List[Dict]) -> List[PlaybookKPI]:
        """Create PlaybookKPI objects from dict"""
        kpis = []
        for kpi in kpi_data:
            kpis.append(PlaybookKPI(
                name=kpi.get("name", "unknown"),
                target_value=kpi.get("target_value", 0.0),
                unit=kpi.get("unit", ""),
                priority=kpi.get("priority", "medium")
            ))
        return kpis
    
    def get_playbook(self, playbook_id: str) -> Optional[Dict]:
        """Get playbook by ID"""
        try:
            obj_id = ObjectId(playbook_id)
        except:
            obj_id = playbook_id
        
        return self.db.playbooks.find_one({"_id": obj_id})
    
    def update_playbook_status(
        self,
        playbook_id: str,
        status: str,
        updates: Optional[Dict] = None
    ):
        """Update playbook status"""
        try:
            obj_id = ObjectId(playbook_id)
        except:
            obj_id = playbook_id
        
        update_doc = {
            "status": status,
            "updated_at": datetime.now(timezone.utc)
        }
        
        if updates:
            update_doc.update(updates)
        
        self.db.playbooks.update_one(
            {"_id": obj_id},
            {"$set": update_doc}
        )
        
        self.logger.info(f"✅ Playbook {playbook_id} status → {status}")


# ============================================================================
# CLI for testing
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_generate():
        generator = PlaybookGenerator()
        
        # Test pentru delexpert.eu
        agent_id = "691a34b65774faae88a735a1"
        
        print(f"🎯 Generating playbook for agent {agent_id}")
        playbook_id = await generator.generate_playbook(
            agent_id=agent_id,
            sprint_days=14,
            custom_objectives=[
                "Achieve rank top 5 on main keywords",
                "Increase CTR to ≥ 4.5%",
                "Generate +20% leads"
            ]
        )
        
        print(f"\n✅ Playbook created: {playbook_id}")
        
        # Fetch and display
        playbook = generator.get_playbook(playbook_id)
        print(f"\n📋 Playbook: {playbook['title']}")
        print(f"   Objectives: {len(playbook['objectives'])}")
        print(f"   Actions: {len(playbook['actions'])}")
        print(f"   KPIs: {len(playbook['kpis'])}")
        
        for i, action in enumerate(playbook['actions'][:3], 1):
            print(f"\n   Action {i}: {action['title']}")
            print(f"      Type: {action['type']}, Agent: {action['agent']}")
            print(f"      Priority: {action['priority']}, Est: {action['estimated_hours']}h")
    
    asyncio.run(test_generate())

