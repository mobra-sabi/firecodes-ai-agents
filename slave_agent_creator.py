#!/usr/bin/env python3
"""
Slave Agent Creator - Creează automat agenți SLAVE pentru competitori
Folosește același pipeline ca master agents dar cu flag type='slave'
"""

import logging
from typing import Dict, Optional, List
from pymongo import MongoClient
from bson import ObjectId
import requests
from datetime import datetime
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class SlaveAgentCreator:
    """
    Creator automat de agenți slave pentru competitori
    """
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client['ai_agents_db']
        self.agents_col = self.db['site_agents']
    
    def check_agent_exists(self, domain: str) -> Optional[str]:
        """
        Verifică dacă există deja un agent pentru acest domain
        
        Returns:
            Agent ID dacă există, None altfel
        """
        existing = self.agents_col.find_one({'domain': domain})
        if existing:
            logger.info(f"✅ Agent already exists for {domain}: {existing['_id']}")
            return str(existing['_id'])
        return None
    
    def scrape_basic_content(self, url: str) -> Dict:
        """
        Scraping simplificat pentru conținut de bază
        (pentru slave agents nu facem analiza completă)
        """
        try:
            logger.info(f"🔍 Scraping content from: {url}")
            
            response = requests.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=15
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch {url}: {response.status_code}")
                return {}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic info
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ''
            
            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '').strip() if meta_desc else ''
            
            # Body text (limited)
            body = soup.find('body')
            body_text = body.get_text(separator=' ', strip=True)[:5000] if body else ''
            
            return {
                'url': url,
                'title': title_text,
                'description': description,
                'content': body_text,
                'content_length': len(body_text)
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {}
    
    def create_slave_agent(
        self,
        domain: str,
        url: str,
        title: str,
        description: str,
        master_id: str,
        serp_position: Optional[int] = None
    ) -> str:
        """
        Creează agent slave pentru un competitor
        
        Args:
            domain: Domain competitor
            url: URL competitor
            title: Title din SERP
            description: Description din SERP
            master_id: ID master agent
            serp_position: Poziția în SERP (opțional)
        
        Returns:
            Slave agent ID
        """
        try:
            # Check if exists
            existing_id = self.check_agent_exists(domain)
            if existing_id:
                # Update relationship if needed
                self.agents_col.update_one(
                    {'_id': ObjectId(existing_id)},
                    {
                        '$addToSet': {'master_ids': master_id},
                        '$set': {'updated_at': datetime.now()}
                    }
                )
                return existing_id
            
            logger.info(f"🤖 Creating SLAVE agent for: {domain}")
            
            # Scrape content (basic)
            scraped = self.scrape_basic_content(url)
            
            # Create agent document
            agent_doc = {
                '_id': str(ObjectId()),
                'domain': domain,
                'url': url,
                'name': title or domain,
                'description': description,
                'type': 'slave',  # IMPORTANT: mark as slave
                'master_ids': [master_id],  # Can have multiple masters
                'status': 'created',
                'scraped_content': scraped.get('content', ''),
                'content_length': scraped.get('content_length', 0),
                'serp_position': serp_position,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'metadata': {
                    'source': 'serp_discovery',
                    'scraping_method': 'basic',
                    'has_embeddings': False
                }
            }
            
            # Insert
            self.agents_col.insert_one(agent_doc)
            
            logger.info(f"✅ Slave agent created: {agent_doc['_id']} for {domain}")
            
            return agent_doc['_id']
            
        except Exception as e:
            logger.error(f"Error creating slave agent for {domain}: {e}")
            raise
    
    def create_from_serp_result(
        self,
        serp_result: Dict,
        master_id: str
    ) -> str:
        """
        Creează slave agent din rezultat SERP
        
        Args:
            serp_result: Dict cu info SERP (position, url, title, description, domain)
            master_id: ID master agent
        
        Returns:
            Slave agent ID
        """
        return self.create_slave_agent(
            domain=serp_result['domain'],
            url=serp_result['url'],
            title=serp_result['title'],
            description=serp_result.get('description', ''),
            master_id=master_id,
            serp_position=serp_result.get('position')
        )
    
    def batch_create_from_serp_results(
        self,
        serp_results: List[Dict],
        master_id: str
    ) -> List[str]:
        """
        Creează multiple slave agents din rezultate SERP
        
        Returns:
            List of slave agent IDs
        """
        slave_ids = []
        
        for result in serp_results:
            try:
                slave_id = self.create_from_serp_result(result, master_id)
                slave_ids.append(slave_id)
            except Exception as e:
                logger.error(f"Failed to create slave for {result.get('domain')}: {e}")
                continue
        
        logger.info(f"✅ Created {len(slave_ids)} slave agents for master {master_id}")
        return slave_ids
    
    def get_slave_statistics(self, master_id: str) -> Dict:
        """
        Obține statistici despre slave agents pentru un master
        """
        slaves = list(self.agents_col.find({
            'master_ids': master_id,
            'type': 'slave'
        }))
        
        return {
            'total_slaves': len(slaves),
            'domains': [s['domain'] for s in slaves],
            'with_embeddings': sum(1 for s in slaves if s.get('metadata', {}).get('has_embeddings', False)),
            'created_today': sum(
                1 for s in slaves 
                if s.get('created_at', datetime.min).date() == datetime.now().date()
            )
        }


# Test function
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    creator = SlaveAgentCreator()
    
    # Test cu un SERP result mock
    test_result = {
        'position': 1,
        'url': 'https://example.com/page',
        'title': 'Example Company - Test',
        'description': 'This is a test description',
        'domain': 'example.com'
    }
    
    test_master_id = "test_master_12345"
    
    print(f"\n🧪 Testing slave creation...")
    slave_id = creator.create_from_serp_result(test_result, test_master_id)
    print(f"✅ Slave created: {slave_id}")
    
    # Get stats
    stats = creator.get_slave_statistics(test_master_id)
    print(f"\n📊 Slave statistics:")
    print(f"   Total slaves: {stats['total_slaves']}")
    print(f"   Domains: {stats['domains']}")

