#!/usr/bin/env python3
"""
🚀 COMPLETE SERP DISCOVERY + FULL SLAVE AGENTS - DELEXPERT.EU
==============================================================

Execută TOT procesul CAP-COADĂ:
1. Get keywords din competitive analysis
2. Pentru fiecare keyword:
   - Google Search (Brave API) → TOP 20
   - Find master position
   - Pentru fiecare competitor:
     * FULL SLAVE AGENT creation:
       - Scraping (BeautifulSoup)
       - DeepSeek analysis
       - GPU Chunking cu Qwen (ports 9400/9201)
       - GPU Embeddings (11x RTX 3080 Ti)
       - Qdrant storage
       - MongoDB storage
3. Rankings map
4. Google Ads strategy (DeepSeek)

ZERO FAKE! TOTUL REAL!
"""

import sys
import time
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import sistemul REAL
from google_serp_scraper import GoogleSerpScraper
from full_agent_creator import FullAgentCreator  # Pentru slave agents!
from google_ads_strategy_generator import GoogleAdsStrategyGenerator

class CompleteSerpDiscoveryRunner:
    """Runner COMPLET pentru SERP Discovery + FULL Slave Agents"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        
        # Get agent
        self.agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not self.agent:
            raise ValueError(f"Agent {agent_id} not found!")
        
        self.master_domain = self.agent.get('domain')
        
        # Initialize components
        self.serp_scraper = GoogleSerpScraper()
        self.strategy_generator = GoogleAdsStrategyGenerator()
        
        logger.info(f"✅ Initialized for agent {agent_id} ({self.master_domain})")
    
    def get_keywords(self) -> list:
        """Extrage TOATE keywords din competitive analysis"""
        comp = self.agent.get('competitive_analysis')
        if not comp:
            raise ValueError("No competitive analysis found!")
        
        keywords = []
        
        # From subdomains
        for subdomain in comp.get('subdomains', []):
            keywords.extend(subdomain.get('keywords', []))
        
        # Overall keywords
        keywords.extend(comp.get('overall_keywords', []))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        logger.info(f"✅ Extracted {len(unique_keywords)} unique keywords")
        return unique_keywords
    
    async def create_full_slave_agent(self, url: str, keyword: str, position: int) -> str:
        """
        Creează un FULL SLAVE AGENT pentru un competitor
        
        Uses:
        - BeautifulSoup scraping
        - DeepSeek analysis
        - GPU Chunking cu Qwen
        - GPU Embeddings (11x RTX 3080 Ti)
        - Qdrant storage
        - MongoDB storage
        """
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check if slave already exists
            existing = self.db.site_agents.find_one({
                "domain": domain,
                "master_agent_id": self.agent_id
            })
            
            if existing:
                logger.info(f"   ✓ Slave agent already exists for {domain}")
                return str(existing['_id'])
            
            logger.info(f"   🤖 Creating FULL slave agent for {domain}...")
            
            # Use FullAgentCreator (REAL system!)
            creator = FullAgentCreator(url=url)
            
            # Create agent with progress logging
            def log_progress(pct, msg):
                logger.info(f"      [{pct:.0f}%] {msg}")
            
            result = await creator.create_full_agent(
                progress_callback=log_progress,
                log_callback=lambda msg: logger.info(f"      {msg}")
            )
            
            slave_id = result['agent_id']
            
            # Mark as slave and link to master
            self.db.site_agents.update_one(
                {"_id": ObjectId(slave_id)},
                {
                    "$set": {
                        "is_slave": True,
                        "master_agent_id": self.agent_id,
                        "discovered_from_keyword": keyword,
                        "serp_position": position,
                        "updated_at": datetime.now()
                    }
                }
            )
            
            logger.info(f"   ✅ Slave agent created: {slave_id}")
            return slave_id
            
        except Exception as e:
            logger.error(f"   ❌ Error creating slave for {url}: {e}")
            return None
    
    async def process_keyword(self, keyword: str, keyword_num: int, total_keywords: int):
        """Process un keyword: SERP search + FULL slave agents"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 [{keyword_num}/{total_keywords}] KEYWORD: {keyword}")
        logger.info(f"{'='*80}\n")
        
        try:
            # 1. Google Search (Brave API)
            logger.info(f"   📡 Searching Google via Brave API...")
            serp_results = self.serp_scraper.search_keyword(keyword, num_results=20)
            
            if not serp_results:
                logger.warning(f"   ⚠️  No SERP results for '{keyword}'")
                return
            
            logger.info(f"   ✅ Found {len(serp_results)} SERP results")
            
            # 2. Find master position
            master_position = None
            for i, result in enumerate(serp_results, 1):
                url = result.get('url', '')
                if self.master_domain in url:
                    master_position = i
                    logger.info(f"   🎯 Master agent position: #{i}")
                    break
            
            if not master_position:
                logger.info(f"   ℹ️  Master not in TOP 20 for '{keyword}'")
            
            # 3. Save SERP results
            serp_doc = {
                "master_agent_id": self.agent_id,
                "keyword": keyword,
                "master_position": master_position,
                "results": serp_results,
                "total_results": len(serp_results),
                "timestamp": datetime.now()
            }
            
            self.db.serp_results.insert_one(serp_doc)
            logger.info(f"   ✅ SERP results saved to MongoDB")
            
            # 4. Create FULL slave agents for each competitor
            logger.info(f"\n   🤖 Creating FULL SLAVE AGENTS for {len(serp_results)} competitors...")
            
            slave_ids = []
            for i, result in enumerate(serp_results, 1):
                url = result.get('url')
                
                # Skip master
                if self.master_domain in url:
                    continue
                
                logger.info(f"\n   [{i}/{len(serp_results)}] {url}")
                
                try:
                    slave_id = await self.create_full_slave_agent(url, keyword, i)
                    if slave_id:
                        slave_ids.append(slave_id)
                except Exception as e:
                    logger.error(f"      ❌ Failed: {e}")
                    continue
                
                # Rate limiting
                time.sleep(2)
            
            logger.info(f"\n   ✅ Created {len(slave_ids)} FULL slave agents for keyword '{keyword}'")
            
        except Exception as e:
            logger.error(f"   ❌ Error processing keyword '{keyword}': {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def run_complete(self, max_keywords: int = None):
        """Rulează procesul COMPLET"""
        logger.info("\n" + "="*80)
        logger.info("🚀 STARTING COMPLETE SERP DISCOVERY + FULL SLAVE AGENTS")
        logger.info("="*80)
        logger.info(f"\nMaster Agent: {self.agent_id}")
        logger.info(f"Domain: {self.master_domain}")
        logger.info(f"Status: {self.agent.get('status')}")
        logger.info("")
        
        # Get keywords
        keywords = self.get_keywords()
        
        if max_keywords:
            keywords = keywords[:max_keywords]
            logger.info(f"⚠️  Limited to first {max_keywords} keywords")
        
        total_keywords = len(keywords)
        logger.info(f"📊 Total keywords to process: {total_keywords}")
        logger.info("")
        
        start_time = time.time()
        
        # Process each keyword
        for i, keyword in enumerate(keywords, 1):
            await self.process_keyword(keyword, i, total_keywords)
        
        # Final statistics
        elapsed = time.time() - start_time
        
        logger.info("\n" + "="*80)
        logger.info("📊 FINAL STATISTICS")
        logger.info("="*80)
        
        serp_count = self.db.serp_results.count_documents({"master_agent_id": self.agent_id})
        slave_count = self.db.site_agents.count_documents({"master_agent_id": self.agent_id})
        
        logger.info(f"\n✅ SERP Results: {serp_count}")
        logger.info(f"✅ FULL Slave Agents: {slave_count}")
        logger.info(f"⏱️  Duration: {elapsed/60:.1f} minutes")
        
        # Generate Google Ads Strategy
        logger.info(f"\n🎯 Generating Google Ads Strategy with DeepSeek...")
        try:
            strategy = self.strategy_generator.generate_google_ads_strategy(self.agent_id)
            logger.info(f"✅ Google Ads Strategy generated!")
        except Exception as e:
            logger.error(f"❌ Strategy generation failed: {e}")
        
        logger.info("\n" + "="*80)
        logger.info("✅ COMPLETE SERP DISCOVERY FINISHED!")
        logger.info("="*80)
        logger.info("")
        
        return {
            "keywords_processed": total_keywords,
            "serp_results": serp_count,
            "slave_agents": slave_count,
            "duration_minutes": elapsed/60
        }


if __name__ == "__main__":
    import asyncio
    
    agent_id = "691a34b65774faae88a735a1"  # delexpert.eu
    
    # Limit to 5 keywords for faster testing (remove limit for full run)
    max_keywords = 5  # Set to None for all 30 keywords
    
    runner = CompleteSerpDiscoveryRunner(agent_id)
    
    result = asyncio.run(runner.run_complete(max_keywords=max_keywords))
    
    print("\n" + "="*80)
    print("🎉 DONE!")
    print("="*80)
    print(f"\nKeywords Processed: {result['keywords_processed']}")
    print(f"SERP Results: {result['serp_results']}")
    print(f"FULL Slave Agents: {result['slave_agents']}")
    print(f"Duration: {result['duration_minutes']:.1f} minutes")
    print("")

