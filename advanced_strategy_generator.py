#!/usr/bin/env python3
"""
Advanced Strategy Generator - Strategii per AGENT (master + slaves) per keyword
Generează recomandări specifice pentru fiecare competitor
"""

import logging
import os
from typing import Dict, List
from openai import OpenAI
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import json
from dotenv import load_dotenv

# Force reload .env
load_dotenv(override=True)

logger = logging.getLogger(__name__)

class AdvancedStrategyGenerator:
    """
    Generează strategii avansate pentru:
    - Master agent (overall strategy)
    - Fiecare slave agent (per keyword specific strategy)
    - Recomandări dinamice bazate pe poziții
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
    
    def generate_master_strategy(self, agent_id: str) -> Dict:
        """
        Strategia MASTER - overall pentru toate keywords
        """
        agent = self.db.site_agents.find_one({'_id': ObjectId(agent_id)})
        rankings = list(self.db.google_rankings.find({'agent_id': agent_id}))
        
        # Analiza per keyword
        keywords_analysis = []
        for ranking in rankings:
            keyword = ranking['keyword']
            master_pos = ranking.get('master_position')
            serp_results = ranking.get('serp_results', [])
            
            # Top 3 competitori
            top_competitors = [r['domain'] for r in serp_results[:3] if r['domain'] != agent.get('domain')]
            
            keywords_analysis.append({
                'keyword': keyword,
                'master_position': master_pos,
                'top_competitors': top_competitors,
                'gap_to_top': master_pos - 1 if master_pos else 20,
                'opportunity_level': 'HIGH' if master_pos and 11 <= master_pos <= 15 else 'MEDIUM' if master_pos and master_pos > 15 else 'LOW'
            })
        
        prompt = f"""
Ești un expert în Google Ads și SEO competitive strategy.

**AGENT MASTER:**
Domain: {agent.get('domain')}
Company: {agent.get('name')}
Industry: {agent.get('industry', 'N/A')}

**RANKINGS ANALYSIS:**
{json.dumps(keywords_analysis, indent=2)}

Generează o strategie MASTER completă în format JSON:

{{
  "executive_summary": "Rezumat executiv (2-3 propoziții)",
  "overall_position": {{
    "strengths": ["keyword1", "keyword2"],  // unde suntem în top 3
    "weaknesses": ["keyword3"],  // unde lipsim
    "opportunities": ["keyword4"]  // 11-20 poziție
  }},
  "priority_actions": [
    {{
      "keyword": "keyword name",
      "current_position": 12,
      "target_position": "3-5 ads",
      "action": "Launch Google Ads campaign",
      "estimated_cpc": "$3.50",
      "monthly_budget": "$500",
      "expected_roi": "250%"
    }}
  ],
  "budget_total": "$5000/month",
  "timeline": "3 months to top 10 for priority keywords"
}}

DOAR JSON, fără text suplimentar.
"""
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a Google Ads expert. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            strategy_text = response.choices[0].message.content.strip()
            
            # Parse JSON
            if strategy_text.startswith('```json'):
                strategy_text = strategy_text[7:]
            if strategy_text.endswith('```'):
                strategy_text = strategy_text[:-3]
            
            strategy = json.loads(strategy_text.strip())
            strategy['agent_id'] = agent_id
            strategy['type'] = 'master'
            strategy['generated_at'] = datetime.now()
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error generating master strategy: {e}")
            return {
                'agent_id': agent_id,
                'type': 'master',
                'error': str(e),
                'generated_at': datetime.now()
            }
    
    def generate_slave_strategy(self, slave_id: str, keyword: str, position: int, master_position: int = None) -> Dict:
        """
        Strategia pentru un SLAVE agent specific per keyword
        Cum să compete cu el sau să învețe din el
        """
        slave = self.db.site_agents.find_one({'_id': ObjectId(slave_id)})
        
        if not slave:
            return {}
        
        prompt = f"""
Analizează competitorul și generează strategie.

**COMPETITOR (SLAVE):**
Domain: {slave.get('domain')}
Position for "{keyword}": #{position}
Content: {slave.get('scraped_content', '')[:500]}...

**MASTER POSITION:** {master_position or 'Not in top 20'}

Generează strategie JSON:

{{
  "competitor_domain": "{slave.get('domain')}",
  "keyword": "{keyword}",
  "competitor_position": {position},
  "master_position": {master_position or 'null'},
  "competitor_strengths": ["reason1", "reason2"],
  "how_to_compete": {{
    "seo_improvements": ["action1"],
    "content_gaps": ["what we're missing"],
    "ads_strategy": "Bid higher/lower/exact match?"
  }},
  "learn_from_them": ["insight1", "insight2"]
}}

DOAR JSON.
"""
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a competitive analysis expert. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            strategy_text = response.choices[0].message.content.strip()
            
            if strategy_text.startswith('```json'):
                strategy_text = strategy_text[7:]
            if strategy_text.endswith('```'):
                strategy_text = strategy_text[:-3]
            
            strategy = json.loads(strategy_text.strip())
            strategy['slave_id'] = slave_id
            strategy['type'] = 'slave'
            strategy['generated_at'] = datetime.now()
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error generating slave strategy for {slave_id}: {e}")
            return {
                'slave_id': slave_id,
                'keyword': keyword,
                'type': 'slave',
                'error': str(e)
            }
    
    def generate_all_strategies(self, agent_id: str) -> Dict:
        """
        Generează strategii pentru TOȚI:
        - 1 master strategy
        - N slave strategies (per keyword per slave)
        """
        logger.info(f"🧠 Generating ALL strategies for agent {agent_id}...")
        
        # Master strategy
        master_strategy = self.generate_master_strategy(agent_id)
        
        # Save master strategy
        self.db.agent_strategies.update_one(
            {'agent_id': agent_id, 'type': 'master'},
            {'$set': master_strategy},
            upsert=True
        )
        
        # Slave strategies per keyword
        rankings = list(self.db.google_rankings.find({'agent_id': agent_id}))
        slave_strategies_count = 0
        
        for ranking in rankings:
            keyword = ranking['keyword']
            master_position = ranking.get('master_position')
            serp_results = ranking.get('serp_results', [])
            
            # Top 10 slaves pentru acest keyword
            for result in serp_results[:10]:
                if result['domain'] == self.db.site_agents.find_one({'_id': ObjectId(agent_id)}).get('domain'):
                    continue  # Skip master
                
                # Find slave agent
                slave = self.db.site_agents.find_one({'domain': result['domain'], 'type': 'slave'})
                if not slave:
                    continue
                
                # Generate strategy
                slave_strategy = self.generate_slave_strategy(
                    slave_id=str(slave['_id']),
                    keyword=keyword,
                    position=result['position'],
                    master_position=master_position
                )
                
                # Save
                self.db.agent_strategies.insert_one(slave_strategy)
                slave_strategies_count += 1
        
        logger.info(f"✅ Generated 1 master + {slave_strategies_count} slave strategies")
        
        return {
            'master_strategy': master_strategy,
            'slave_strategies_count': slave_strategies_count,
            'total_strategies': 1 + slave_strategies_count
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    generator = AdvancedStrategyGenerator()
    
    agent_id = "691a19dd2772e8833c819084"
    
    print(f"\n🧪 Testing Advanced Strategy Generator...")
    print(f"Agent ID: {agent_id}")
    
    # Test master strategy
    print(f"\n📊 Generating master strategy...")
    master = generator.generate_master_strategy(agent_id)
    print(f"✅ Master strategy: {json.dumps(master, indent=2, default=str)[:500]}...")

