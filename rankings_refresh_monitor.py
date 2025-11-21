#!/usr/bin/env python3
"""
Rankings Refresh Monitor - Sistem automat de reactualizare rankings
Monitorizează periodic pozițiile și ajustează campaniile Google Ads
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List
from pymongo import MongoClient
from bson import ObjectId
from google_serp_scraper import GoogleSerpScraper

logger = logging.getLogger(__name__)

class RankingsRefreshMonitor:
    """
    Monitorizare automată rankings + ajustare campanii
    """
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client['ai_agents_db']
        self.scraper = GoogleSerpScraper()
    
    def should_refresh(self, last_checked: datetime, refresh_interval_hours: int = 24) -> bool:
        """Check dacă trebuie să refresh rankings"""
        if not last_checked:
            return True
        
        time_diff = datetime.now() - last_checked
        return time_diff.total_seconds() > (refresh_interval_hours * 3600)
    
    def refresh_keyword_ranking(self, agent_id: str, keyword: str) -> Dict:
        """
        Refresh ranking pentru un singur keyword
        
        Returns:
            Dict cu:
            - old_position
            - new_position
            - change (+/-)
            - action_needed (bool)
        """
        # Get old ranking
        old_ranking = self.db.google_rankings.find_one(
            {'agent_id': agent_id, 'keyword': keyword},
            sort=[('checked_at', -1)]
        )
        
        old_position = old_ranking.get('master_position') if old_ranking else None
        
        # Get agent domain
        agent = self.db.site_agents.find_one({'_id': ObjectId(agent_id)})
        master_domain = agent.get('domain')
        
        # Scrape fresh data
        logger.info(f"🔍 Refreshing ranking for keyword: '{keyword}'")
        serp_results = self.scraper.search_keyword(keyword, num_results=20)
        
        # Find new position
        new_position = self.scraper.find_master_position(serp_results, master_domain)
        
        # Calculate change
        if old_position and new_position:
            change = old_position - new_position  # Positive = moved up
        elif new_position:
            change = None  # New entry
        else:
            change = None  # Still not in top 20
        
        # Determine if action needed
        action_needed = False
        action_type = None
        
        if change and change < -3:
            # Dropped 3+ positions
            action_needed = True
            action_type = "URGENT: Position dropped significantly"
        elif new_position and new_position > 10:
            # Outside top 10
            action_needed = True
            action_type = "Consider increasing ads budget"
        elif new_position and 4 <= new_position <= 10:
            # In top 10 but not top 3
            action_needed = True
            action_type = "Push to top 3 with targeted ads"
        
        # Store new ranking
        new_ranking_doc = {
            'agent_id': agent_id,
            'keyword': keyword,
            'master_position': new_position,
            'previous_position': old_position,
            'position_change': change,
            'serp_results': serp_results,
            'checked_at': datetime.now(),
            'action_needed': action_needed,
            'action_type': action_type
        }
        
        self.db.google_rankings.insert_one(new_ranking_doc)
        
        # Log change
        if change:
            if change > 0:
                logger.info(f"✅ {keyword}: {old_position} → {new_position} (↑ +{change})")
            else:
                logger.warning(f"⚠️  {keyword}: {old_position} → {new_position} (↓ {change})")
        else:
            logger.info(f"📊 {keyword}: New position {new_position}")
        
        return {
            'keyword': keyword,
            'old_position': old_position,
            'new_position': new_position,
            'change': change,
            'action_needed': action_needed,
            'action_type': action_type
        }
    
    def refresh_all_rankings(self, agent_id: str, force: bool = False) -> Dict:
        """
        Refresh toate rankings pentru un agent
        """
        logger.info(f"🔄 Starting rankings refresh for agent {agent_id}...")
        
        # Get all keywords
        rankings = list(self.db.google_rankings.find(
            {'agent_id': agent_id},
            sort=[('checked_at', -1)]
        ))
        
        # Group by keyword (get latest per keyword)
        keywords_map = {}
        for r in rankings:
            kw = r['keyword']
            if kw not in keywords_map:
                keywords_map[kw] = r
        
        # Refresh each keyword
        results = []
        actions_needed = []
        
        for keyword, old_ranking in keywords_map.items():
            # Check if should refresh
            if not force and not self.should_refresh(old_ranking.get('checked_at'), refresh_interval_hours=24):
                logger.info(f"⏭️  Skipping {keyword} (recently checked)")
                continue
            
            # Refresh
            result = self.refresh_keyword_ranking(agent_id, keyword)
            results.append(result)
            
            if result['action_needed']:
                actions_needed.append(result)
            
            # Rate limiting
            time.sleep(2)
        
        summary = {
            'agent_id': agent_id,
            'keywords_refreshed': len(results),
            'actions_needed': len(actions_needed),
            'results': results,
            'recommendations': actions_needed,
            'refreshed_at': datetime.now()
        }
        
        # Store summary
        self.db.rankings_refresh_history.insert_one(summary)
        
        logger.info(f"✅ Refresh complete: {len(results)} keywords, {len(actions_needed)} need action")
        
        return summary
    
    def adjust_campaigns_based_on_rankings(self, agent_id: str) -> Dict:
        """
        Ajustează campaniile Google Ads bazat pe rankings actualizate
        
        Logica:
        - Poziție scăzută (>15) → Crește bid cu 20%
        - Poziție medie (11-15) → Crește bid cu 10%
        - Poziție bună (4-10) → Menține bid
        - Top 3 → Scade bid cu 10% (optimizare cost)
        """
        logger.info(f"📊 Analyzing rankings for campaign adjustments...")
        
        # Get latest rankings
        rankings = list(self.db.google_rankings.find(
            {'agent_id': agent_id},
            sort=[('checked_at', -1)]
        ))
        
        # Group by keyword (latest)
        keywords_map = {}
        for r in rankings:
            kw = r['keyword']
            if kw not in keywords_map or r['checked_at'] > keywords_map[kw]['checked_at']:
                keywords_map[kw] = r
        
        adjustments = []
        
        for keyword, ranking in keywords_map.items():
            position = ranking.get('master_position')
            previous = ranking.get('previous_position')
            
            if not position:
                # Not in top 20
                adjustment = {
                    'keyword': keyword,
                    'action': 'CREATE_CAMPAIGN',
                    'reason': 'Not ranking, launch ads',
                    'suggested_bid': '$4.00 - $6.00',
                    'priority': 'HIGH'
                }
            elif position > 15:
                adjustment = {
                    'keyword': keyword,
                    'action': 'INCREASE_BID_20%',
                    'reason': f'Position {position} - need boost',
                    'current_position': position,
                    'priority': 'HIGH'
                }
            elif position > 10:
                adjustment = {
                    'keyword': keyword,
                    'action': 'INCREASE_BID_10%',
                    'reason': f'Position {position} - push to top 10',
                    'current_position': position,
                    'priority': 'MEDIUM'
                }
            elif position > 3:
                adjustment = {
                    'keyword': keyword,
                    'action': 'MAINTAIN_BID',
                    'reason': f'Position {position} - good, maintain',
                    'current_position': position,
                    'priority': 'LOW'
                }
            else:
                adjustment = {
                    'keyword': keyword,
                    'action': 'DECREASE_BID_10%',
                    'reason': f'Position {position} - top 3, optimize cost',
                    'current_position': position,
                    'priority': 'LOW'
                }
            
            # Add change info
            if previous and position:
                change = previous - position
                adjustment['position_change'] = change
                if change < -3:
                    adjustment['priority'] = 'URGENT'
            
            adjustments.append(adjustment)
        
        # Store recommendations
        campaign_adjustments = {
            'agent_id': agent_id,
            'adjustments': adjustments,
            'total_keywords': len(adjustments),
            'high_priority': sum(1 for a in adjustments if a.get('priority') == 'HIGH'),
            'urgent': sum(1 for a in adjustments if a.get('priority') == 'URGENT'),
            'generated_at': datetime.now()
        }
        
        self.db.campaign_adjustments.insert_one(campaign_adjustments)
        
        logger.info(f"✅ Campaign adjustments generated: {len(adjustments)} actions")
        
        return campaign_adjustments


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    monitor = RankingsRefreshMonitor()
    
    agent_id = "691a19dd2772e8833c819084"
    
    print(f"\n🧪 Testing Rankings Refresh Monitor...")
    print(f"Agent ID: {agent_id}")
    
    # Test refresh single keyword
    print(f"\n📊 Testing single keyword refresh...")
    result = monitor.refresh_keyword_ranking(agent_id, "reparatii anticorozive")
    print(f"Result: {result}")

