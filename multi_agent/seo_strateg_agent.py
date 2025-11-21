#!/usr/bin/env python3
"""
🎯 SEO STRATEG AGENT - Multi-Agent System

Rol: Analizează harta CEO și propune priorități strategice
- Ce keywords să targetăm în următoarele 30/90 zile?
- Ce pagini să creăm?
- Ce schimbări/optimizări să facem?
- Quick wins vs long-term investments

Orchestrat de DeepSeek, folosește Qwen pentru analiză grea
"""

import os
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

import logging
from typing import Dict, List, Any
from datetime import datetime, timezone
import json
from pymongo import MongoClient
from bson import ObjectId

from llm_orchestrator import get_orchestrator
from seo_intelligence.opportunity_scorer import OpportunityScorer
from seo_intelligence.content_gap_analyzer import ContentGapAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SEOStrategAgent:
    """
    Agent SEO Strateg - propune strategii și prioritizări
    """
    
    def __init__(self):
        self.llm = get_orchestrator()
        self.opportunity_scorer = OpportunityScorer()
        self.gap_analyzer = ContentGapAnalyzer()
        
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        
        logger.info("✅ SEO Strateg Agent initialized")
    
    def analyze_and_prioritize(
        self,
        ceo_map: Dict,
        business_goals: Dict = None
    ) -> Dict:
        """
        Analizează CEO competitive map și generează plan strategic
        
        Args:
            ceo_map: Harta competitivă CEO
            business_goals: Obiective business (target traffic, budget, timeline)
        
        Returns:
            Dict cu plan 30/90 zile + priorități
        """
        logger.info("🎯 SEO Strateg: Analyzing competitive map and generating strategy")
        
        try:
            agent_id = ceo_map.get("master_agent_id")
            if not agent_id:
                logger.error("❌ No master agent ID in CEO map")
                return {}
            
            # 1. Load agent data
            agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                logger.error(f"❌ Agent {agent_id} not found")
                return {}
            
            # 2. Load competitive analysis
            comp_analysis = self.db.competitive_analysis.find_one({"agent_id": ObjectId(agent_id)})
            
            # 3. Load keyword discovery
            keyword_discovery = self.db.competitor_discoveries.find_one(
                {"agent_id": ObjectId(agent_id)},
                sort=[("_id", -1)]
            )
            
            # 4. Extract all keywords
            all_keywords = self._extract_all_keywords(comp_analysis, keyword_discovery)
            
            logger.info(f"   Analyzing {len(all_keywords)} keywords")
            
            # 5. Score keywords pentru opportunity
            keyword_scores = self.opportunity_scorer.score_batch(
                all_keywords[:50],  # Top 50 pentru a nu fi prea slow
                business_context={
                    "industry": agent.get("industry", ""),
                    "products": agent.get("products", []),
                    "services": agent.get("services", [])
                }
            )
            
            # 6. Identifică quick wins
            quick_wins = self._identify_quick_wins(keyword_scores)
            
            # 7. Identifică high-value targets
            high_value = self._identify_high_value_targets(keyword_scores)
            
            # 8. Generează 30-day plan
            plan_30_days = self._generate_30_day_plan(
                quick_wins,
                high_value,
                keyword_scores,
                business_goals
            )
            
            # 9. Generează 90-day roadmap
            roadmap_90_days = self._generate_90_day_roadmap(
                keyword_scores,
                comp_analysis,
                business_goals
            )
            
            # 10. Calculează expected impact
            expected_impact = self._calculate_expected_impact(
                plan_30_days,
                roadmap_90_days
            )
            
            result = {
                "agent_id": agent_id,
                "domain": agent.get("domain"),
                "keywords_analyzed": len(all_keywords),
                "quick_wins": quick_wins,
                "high_value_targets": high_value,
                "30_day_plan": plan_30_days,
                "90_day_roadmap": roadmap_90_days,
                "expected_impact": expected_impact,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Save strategy
            self._save_strategy(agent_id, result)
            
            logger.info("✅ SEO Strategy generated successfully")
            logger.info(f"   - {len(quick_wins)} quick wins identified")
            logger.info(f"   - {len(high_value)} high-value targets")
            logger.info(f"   - 30-day plan: {len(plan_30_days.get('priority_keywords', []))} actions")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error generating strategy: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _extract_all_keywords(self, comp_analysis: Dict, keyword_discovery: Dict) -> List[str]:
        """
        Extrage toate keywords-urile din analize
        """
        keywords = set()
        
        # From competitive analysis
        if comp_analysis:
            data = comp_analysis.get("analysis_data", {})
            
            # Overall keywords
            keywords.update(data.get("overall_keywords", []))
            
            # Subdomain keywords
            for subdomain in data.get("subdomains", []):
                keywords.update(subdomain.get("keywords", []))
        
        # From keyword discovery
        if keyword_discovery:
            discovery_data = keyword_discovery.get("discovery_data", {})
            for kw_data in discovery_data.get("keywords_searched", []):
                keywords.add(kw_data.get("keyword", ""))
        
        return list(keywords)
    
    def _identify_quick_wins(self, keyword_scores: List[Dict]) -> List[Dict]:
        """
        Identifică quick wins: oportunități mari cu dificultate scăzută
        """
        quick_wins = []
        
        for score in keyword_scores:
            # Quick win = opportunity > 6 AND difficulty < 0.5
            if (score.get("opportunity_score", 0) > 6.0 and
                score.get("difficulty_score", 1.0) < 0.5):
                
                quick_wins.append({
                    "keyword": score["keyword"],
                    "opportunity_score": score["opportunity_score"],
                    "difficulty": score["difficulty_score"],
                    "search_volume": score["search_volume"],
                    "action": "Create optimized content page",
                    "estimated_time": "1-2 weeks",
                    "expected_impact": "HIGH"
                })
        
        # Sort by opportunity
        quick_wins.sort(key=lambda x: x["opportunity_score"], reverse=True)
        
        return quick_wins[:10]  # Top 10 quick wins
    
    def _identify_high_value_targets(self, keyword_scores: List[Dict]) -> List[Dict]:
        """
        Identifică high-value targets: oportunități mari (chiar dacă difficulty mai mare)
        """
        high_value = []
        
        for score in keyword_scores:
            # High value = opportunity > 7 (regardless of difficulty)
            if score.get("opportunity_score", 0) > 7.0:
                
                # Estimează effort bazat pe difficulty
                difficulty = score.get("difficulty_score", 0.5)
                if difficulty < 0.4:
                    effort = "LOW"
                    time = "2-3 weeks"
                elif difficulty < 0.7:
                    effort = "MEDIUM"
                    time = "1-2 months"
                else:
                    effort = "HIGH"
                    time = "2-3 months"
                
                high_value.append({
                    "keyword": score["keyword"],
                    "opportunity_score": score["opportunity_score"],
                    "difficulty": difficulty,
                    "search_volume": score["search_volume"],
                    "business_relevance": score.get("business_relevance", 0.7),
                    "effort": effort,
                    "estimated_time": time,
                    "expected_impact": "VERY HIGH"
                })
        
        # Sort by opportunity
        high_value.sort(key=lambda x: x["opportunity_score"], reverse=True)
        
        return high_value[:15]  # Top 15
    
    def _generate_30_day_plan(
        self,
        quick_wins: List[Dict],
        high_value: List[Dict],
        all_scores: List[Dict],
        business_goals: Dict = None
    ) -> Dict:
        """
        Generează plan detaliat pentru următoarele 30 zile
        """
        plan = {
            "priority_keywords": [],
            "content_to_create": [],
            "optimizations": [],
            "kpi_targets": {}
        }
        
        # 1. Priority keywords (mix quick wins + high value)
        priorities = []
        
        # Add top 5 quick wins
        for qw in quick_wins[:5]:
            priorities.append({
                "keyword": qw["keyword"],
                "action": "CREATE: Comprehensive content page",
                "expected_impact": f"+{qw['search_volume'] * 0.3:.0f} visits/month",
                "effort": "MEDIUM",
                "priority_score": 9.5,
                "deadline": "Week 2"
            })
        
        # Add top 3 high value
        for hv in high_value[:3]:
            if hv["effort"] in ["LOW", "MEDIUM"]:
                priorities.append({
                    "keyword": hv["keyword"],
                    "action": "CREATE: In-depth guide/article",
                    "expected_impact": f"+{hv['search_volume'] * 0.4:.0f} visits/month",
                    "effort": hv["effort"],
                    "priority_score": 8.5,
                    "deadline": "Week 3-4"
                })
        
        plan["priority_keywords"] = priorities
        
        # 2. Content to create
        for priority in priorities[:5]:
            plan["content_to_create"].append({
                "title": f"Ghid complet: {priority['keyword'].title()}",
                "target_keyword": priority["keyword"],
                "content_type": "comprehensive_guide",
                "word_count": "2000-2500",
                "deadline": priority["deadline"]
            })
        
        # 3. Optimizations (pentru existing pages)
        plan["optimizations"] = [
            {
                "action": "Update meta titles și descriptions pentru top 10 pagini",
                "impact": "Improve CTR by 10-15%",
                "effort": "LOW",
                "deadline": "Week 1"
            },
            {
                "action": "Add internal linking între pagini similare",
                "impact": "Improve crawlability + authority flow",
                "effort": "MEDIUM",
                "deadline": "Week 2"
            }
        ]
        
        # 4. KPI targets pentru 30 zile
        if business_goals:
            target_traffic = business_goals.get("target", "+30% organic traffic")
        else:
            target_traffic = "+25% organic traffic"
        
        plan["kpi_targets"] = {
            "organic_traffic": target_traffic,
            "new_top_10_rankings": "+5 keywords",
            "pages_created": len(plan["content_to_create"]),
            "expected_visitors": sum(
                int(p.get("expected_impact", "0").split("+")[1].split(" ")[0] or 0)
                for p in priorities
            )
        }
        
        return plan
    
    def _generate_90_day_roadmap(
        self,
        keyword_scores: List[Dict],
        comp_analysis: Dict,
        business_goals: Dict = None
    ) -> Dict:
        """
        Generează roadmap pentru 90 zile (3 luni)
        """
        roadmap = {
            "month_1": {},
            "month_2": {},
            "month_3": {},
            "milestones": []
        }
        
        # Month 1: Quick wins + foundation
        roadmap["month_1"] = {
            "focus": "Quick wins + Foundation",
            "actions": [
                "Implement 30-day plan (5 quick win pages)",
                "Technical SEO audit + fixes",
                "Internal linking optimization"
            ],
            "expected_result": "+15% organic traffic"
        }
        
        # Month 2: High-value targets
        roadmap["month_2"] = {
            "focus": "High-value content + Competitive moves",
            "actions": [
                "Create 3-4 high-value content pieces",
                "Start link building campaign",
                "Analyze competitor moves and counter"
            ],
            "expected_result": "+25% organic traffic (cumulative)"
        }
        
        # Month 3: Scale + Optimize
        roadmap["month_3"] = {
            "focus": "Scale what works + Continuous optimization",
            "actions": [
                "Scale successful content types",
                "Update and refresh existing content",
                "Advanced competitive moves"
            ],
            "expected_result": "+35-40% organic traffic (cumulative)"
        }
        
        # Milestones
        roadmap["milestones"] = [
            {
                "week": 4,
                "milestone": "5 new optimized pages live",
                "kpi": "+10% traffic"
            },
            {
                "week": 8,
                "milestone": "10+ keywords in top 10",
                "kpi": "+20% traffic"
            },
            {
                "week": 12,
                "milestone": "15+ keywords in top 10, authority increased",
                "kpi": "+35% traffic"
            }
        ]
        
        return roadmap
    
    def _calculate_expected_impact(self, plan_30: Dict, roadmap_90: Dict) -> Dict:
        """
        Calculează impact estimat
        """
        return {
            "30_days": {
                "traffic_increase": "+15-20%",
                "new_rankings": "+5-7 keywords top 10",
                "pages_added": len(plan_30.get("content_to_create", []))
            },
            "90_days": {
                "traffic_increase": "+35-40%",
                "new_rankings": "+15-20 keywords top 10",
                "competitive_position": "Move from #2 to #1 in key segments"
            },
            "roi_estimate": {
                "investment": "Medium (content creation + optimization)",
                "expected_return": "High (3-5x traffic increase)",
                "payback_period": "2-3 months"
            }
        }
    
    def _save_strategy(self, agent_id: str, strategy: Dict):
        """
        Salvează strategia în MongoDB
        """
        try:
            self.db.seo_strategies.update_one(
                {"agent_id": agent_id},
                {"$set": strategy},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to save strategy: {e}")


# Test
if __name__ == "__main__":
    agent = SEOStrategAgent()
    
    # Mock CEO map
    mock_ceo_map = {
        "master_agent_id": "6913815a9349b25c368f2d3b",  # incendii.ro from earlier test
        "competitors": 152
    }
    
    mock_business_goals = {
        "target": "+30% organic traffic",
        "budget": "medium",
        "timeline": "90 days"
    }
    
    print("="*80)
    print("🧪 TESTING SEO STRATEG AGENT")
    print("="*80)
    
    strategy = agent.analyze_and_prioritize(mock_ceo_map, mock_business_goals)
    
    if strategy:
        print(f"\n✅ STRATEGY GENERATED!\n")
        print(f"Quick Wins: {len(strategy.get('quick_wins', []))}")
        print(f"High-Value Targets: {len(strategy.get('high_value_targets', []))}")
        print(f"\n30-DAY PLAN:")
        for action in strategy.get("30_day_plan", {}).get("priority_keywords", [])[:3]:
            print(f"  - {action['keyword']}: {action['action']}")
    else:
        print("\n❌ Strategy generation failed")

