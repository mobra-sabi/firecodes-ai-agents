#!/usr/bin/env python3
"""
🎭 PLAYWRIGHT AGENT CREATOR
===========================

Agent creator folosind Playwright pentru bypass Cloudflare
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from typing import Dict, List
from playwright_scraper import PlaywrightScraper
from construction_agent_creator import ConstructionAgentCreator
from datetime import datetime

class PlaywrightAgentCreator(ConstructionAgentCreator):
    """Agent creator cu Playwright scraping"""
    
    def __init__(self):
        super().__init__()
        self.scraper = None
    
    async def scrape_with_playwright(self, url: str, max_pages: int = 300) -> Dict:
        """
        Scrape site cu Playwright
        
        Returns:
            {
                "pages": [{"url": str, "content": str, "title": str}, ...],
                "pages_scraped": int,
                "domain": str
            }
        """
        
        print(f"🎭 Starting Playwright scraping...")
        print(f"   URL: {url}")
        print(f"   Max pages: {max_pages}")
        
        # Initialize scraper
        self.scraper = PlaywrightScraper(headless=True)
        await self.scraper.start()
        
        try:
            # Step 1: Discover links
            print(f"\n📍 STEP 1: Link Discovery")
            discovered_urls = await self.scraper.discover_links(
                url,
                max_pages=max_pages,
                same_domain_only=True
            )
            
            print(f"✅ Discovered {len(discovered_urls)} URLs")
            
            # Step 2: Scrape pages
            print(f"\n📥 STEP 2: Scraping Pages")
            
            pages = []
            
            def progress_callback(current, total, url):
                print(f"   [{current}/{total}] {url[:60]}...")
            
            results = await self.scraper.scrape_bulk(
                discovered_urls,
                max_concurrent=3,
                delay_between=1.0,
                progress_callback=progress_callback
            )
            
            # Process results
            for result in results:
                if result['success'] and result['text']:
                    pages.append({
                        "url": result['url'],
                        "content": result['text'],
                        "title": result['title']
                    })
            
            print(f"\n✅ Scraped {len(pages)} pages successfully")
            
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')
            
            return {
                "pages": pages,
                "pages_scraped": len(pages),
                "domain": domain
            }
            
        finally:
            await self.scraper.close()
    
    def create_agent_with_playwright(self, url: str, max_pages: int = 300):
        """Create agent using Playwright (synchronous wrapper)"""
        
        print("=" * 80)
        print("🎭 PLAYWRIGHT AGENT CREATOR")
        print("=" * 80)
        print(f"\nURL: {url}")
        print(f"Max pages: {max_pages}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Scrape with Playwright
            site_data = asyncio.run(self.scrape_with_playwright(url, max_pages))
            
            if site_data['pages_scraped'] == 0:
                raise Exception("No pages scraped!")
            
            # Analyze with GPT-4
            print(f"\n🧠 STEP 3: DeepSeek Analysis")
            analysis = self.analyze_construction_site(site_data)
            
            # Create embeddings with GPU
            print(f"\n🎮 STEP 4: GPU Embeddings")
            embeddings_count = self.create_site_embeddings(
                site_data['domain'],
                site_data,
                analysis
            )
            
            # Save to MongoDB
            print(f"\n💾 STEP 5: MongoDB Save")
            agent_config = {
                "company_name": analysis.get('company_analysis', {}).get('company_name', site_data['domain']),
                "services": analysis.get('services_identified', []),
                "pages_scraped": site_data['pages_scraped'],
                "embeddings_count": embeddings_count,
                "analysis_date": datetime.now().isoformat(),
                "scraping_method": "playwright"
            }
            
            self.save_site_analysis(site_data['domain'], analysis)
            self.save_agent_config(url, agent_config)
            
            print(f"\n{'='*80}")
            print(f"✅ AGENT CREATED SUCCESSFULLY!")
            print(f"{'='*80}")
            print(f"Domain: {site_data['domain']}")
            print(f"Pages: {site_data['pages_scraped']}")
            print(f"Chunks: {embeddings_count}")
            print(f"Services: {len(analysis.get('services_identified', []))}")
            
            return {
                "success": True,
                "domain": site_data['domain'],
                "pages": site_data['pages_scraped'],
                "chunks": embeddings_count
            }
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python playwright_agent_creator.py <url> [max_pages]")
        sys.exit(1)
    
    url = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    
    creator = PlaywrightAgentCreator()
    result = creator.create_agent_with_playwright(url, max_pages)
    
    if result['success']:
        print(f"\n✅ SUCCESS!")
        sys.exit(0)
    else:
        print(f"\n❌ FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()

