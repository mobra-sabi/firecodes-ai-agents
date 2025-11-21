#!/usr/bin/env python3
"""
Google Ads Strategy Generator - Folosește DeepSeek pentru analiza strategica
Generează recomandări Google Ads bazate pe SERP rankings și gap analysis
"""

import logging
import os
from typing import Dict, List
from openai import OpenAI
from pymongo import MongoClient
from datetime import datetime
import json
from dotenv import load_dotenv

# Force reload .env
load_dotenv(override=True)

logger = logging.getLogger(__name__)

class GoogleAdsStrategyGenerator:
    """
    Generează strategii Google Ads folosind DeepSeek
    """
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client['ai_agents_db']
        
        # DeepSeek client
        self.llm_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        )
        self.model = os.getenv("HEAVY_LLM_MODEL", "deepseek-chat")
    
    def analyze_rankings_data(self, agent_id: str) -> Dict:
        """
        Analizează datele de rankings pentru un agent
        
        Returns:
            Dict cu analiza completă:
            - keywords_by_position
            - gaps (keywords unde nu suntem în top 10)
            - opportunities (keywords 11-20)
            - missing (keywords unde nu suntem deloc)
        """
        from bson import ObjectId
        
        # Handle both string and ObjectId
        if isinstance(agent_id, str):
            try:
                agent = self.db.site_agents.find_one({'_id': ObjectId(agent_id)})
            except:
                agent = self.db.site_agents.find_one({'_id': agent_id})
        else:
            agent = self.db.site_agents.find_one({'_id': agent_id})
        
        if not agent:
            logger.error(f"Agent {agent_id} not found in database")
            return {
                'agent_domain': 'unknown',
                'total_keywords': 0,
                'keywords_by_position': {'top_3': [], 'top_10': [], 'top_20': [], 'missing': []},
                'gaps': [],
                'opportunities': [],
                'top_competitors': {}
            }
        
        rankings = list(self.db.google_rankings.find({'agent_id': agent_id}))
        
        analysis = {
            'agent_domain': agent.get('domain'),
            'total_keywords': len(rankings),
            'keywords_by_position': {
                'top_3': [],
                'top_10': [],
                'top_20': [],
                'missing': []
            },
            'gaps': [],
            'opportunities': [],
            'top_competitors': {}
        }
        
        for ranking in rankings:
            keyword = ranking['keyword']
            position = ranking.get('master_position')
            
            if position is None:
                analysis['keywords_by_position']['missing'].append(keyword)
                analysis['gaps'].append({
                    'keyword': keyword,
                    'position': None,
                    'gap': 'Not in top 20',
                    'top_competitor': ranking['serp_results'][0]['domain'] if ranking['serp_results'] else None
                })
            elif position <= 3:
                analysis['keywords_by_position']['top_3'].append(keyword)
            elif position <= 10:
                analysis['keywords_by_position']['top_10'].append(keyword)
            elif position <= 20:
                analysis['keywords_by_position']['top_20'].append(keyword)
                analysis['opportunities'].append({
                    'keyword': keyword,
                    'current_position': position,
                    'gap_to_top_10': position - 10,
                    'potential': 'High' if position <= 15 else 'Medium'
                })
            
            # Count top competitors
            for result in ranking.get('serp_results', [])[:10]:
                domain = result['domain']
                if domain != agent.get('domain'):
                    analysis['top_competitors'][domain] = analysis['top_competitors'].get(domain, 0) + 1
        
        # Sort competitors by frequency
        analysis['top_competitors'] = dict(
            sorted(
                analysis['top_competitors'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        )
        
        return analysis
    
    def generate_google_ads_strategy(self, agent_id: str) -> Dict:
        """
        Generează strategia Google Ads completă folosind DeepSeek
        
        Returns:
            Dict cu strategia completă:
            - gap_analysis
            - priority_keywords
            - bid_recommendations
            - budget_allocation
            - competitor_insights
            - action_plan
        """
        logger.info(f"🧠 Generating Google Ads strategy for agent {agent_id}...")
        
        # Get analysis data
        analysis = self.analyze_rankings_data(agent_id)
        agent = self.db.site_agents.find_one({'_id': agent_id})
        
        # Prepare prompt for DeepSeek
        prompt = f"""
Ești un expert în Google Ads și SEO. Analizează următoarele date de ranking Google și generează o strategie completă de Google Ads.

**AGENT:**
- Domain: {analysis['agent_domain']}
- Industry: {agent.get('industry', 'N/A')}
- Company: {agent.get('name', 'N/A')}

**RANKINGS DATA:**
- Total keywords: {analysis['total_keywords']}
- Top 3: {len(analysis['keywords_by_position']['top_3'])} keywords
- Top 10: {len(analysis['keywords_by_position']['top_10'])} keywords
- Top 20: {len(analysis['keywords_by_position']['top_20'])} keywords
- Missing: {len(analysis['keywords_by_position']['missing'])} keywords

**OPPORTUNITIES (11-20):**
{json.dumps(analysis['opportunities'][:10], indent=2)}

**GAPS (Not in top 10):**
{json.dumps(analysis['gaps'][:10], indent=2)}

**TOP COMPETITORS:**
{json.dumps(analysis['top_competitors'], indent=2)}

Generează o strategie Google Ads completă în format JSON cu următoarea structură:

{{
  "executive_summary": "Rezumat executiv al strategiei (2-3 propoziții)",
  "priority_keywords": [
    {{
      "keyword": "keyword name",
      "current_position": 12,
      "target_position": "3-5 (ads)",
      "priority": "High/Medium/Low",
      "reason": "De ce este prioritar acest keyword",
      "estimated_cpc": "$2.50 - $4.00",
      "estimated_monthly_clicks": "500-800"
    }}
  ],
  "budget_allocation": {{
    "total_monthly_budget": "$3000 - $5000",
    "per_keyword_ranges": {{
      "high_priority": "$300-500",
      "medium_priority": "$150-300",
      "low_priority": "$50-150"
    }},
    "breakdown_by_category": {{}}
  }},
  "competitor_insights": {{
    "main_threats": ["competitor1.ro", "competitor2.ro"],
    "their_strengths": ["..."],
    "our_advantages": ["..."]
  }},
  "action_plan": [
    {{
      "phase": "Phase 1 (Week 1-2)",
      "actions": ["Start with top 5 high-priority keywords", "..."],
      "expected_results": "..."
    }}
  ],
  "kpis": {{
    "target_ctr": "3-5%",
    "target_conversion_rate": "2-4%",
    "target_roi": "300%+"
  }}
}}

Returnează DOAR JSON-ul, fără text suplimentar.
"""
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Google Ads and SEO expert. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            strategy_text = response.choices[0].message.content.strip()
            
            # Parse JSON
            if strategy_text.startswith('```json'):
                strategy_text = strategy_text[7:]
            if strategy_text.endswith('```'):
                strategy_text = strategy_text[:-3]
            
            strategy = json.loads(strategy_text.strip())
            
            # Add metadata
            strategy['agent_id'] = agent_id
            strategy['analysis_data'] = analysis
            strategy['generated_at'] = datetime.now()
            strategy['generated_by'] = 'deepseek'
            
            logger.info(f"✅ Google Ads strategy generated successfully")
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error generating strategy with DeepSeek: {e}")
            
            # Fallback simple strategy
            return {
                'agent_id': agent_id,
                'executive_summary': f"Strategy for {analysis['total_keywords']} keywords with {len(analysis['opportunities'])} immediate opportunities.",
                'analysis_data': analysis,
                'generated_at': datetime.now(),
                'error': str(e)
            }


# Test
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    generator = GoogleAdsStrategyGenerator()
    
    # Test with crumantech agent
    agent_id = "691a19dd2772e8833c819084"
    
    print(f"\n📊 Analyzing rankings data...")
    analysis = generator.analyze_rankings_data(agent_id)
    
    print(f"\n✅ Analysis complete:")
    print(f"   Total keywords: {analysis['total_keywords']}")
    print(f"   Opportunities: {len(analysis['opportunities'])}")
    print(f"   Gaps: {len(analysis['gaps'])}")
    print(f"   Top competitors: {list(analysis['top_competitors'].keys())[:5]}")

