#!/usr/bin/env python3
"""
Google SERP Scraper - Extract TOP 20 results pentru fiecare keyword
Folosește Brave Search API (alternative: SerpAPI, custom scraping)
"""

import os
import requests
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

logger = logging.getLogger(__name__)

class GoogleSerpScraper:
    """
    Scraper pentru Google Search Results
    Folosește Brave Search API pentru a obține rezultate organice
    """
    
    def __init__(self):
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        self.brave_base_url = "https://api.search.brave.com/res/v1/web/search"
        
        if not self.brave_api_key:
            logger.warning("BRAVE_API_KEY not set. SERP scraping will not work.")
    
    def extract_domain(self, url: str) -> str:
        """Extract clean domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www.
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception as e:
            logger.error(f"Error extracting domain from {url}: {e}")
            return url
    
    def search_keyword(
        self, 
        keyword: str, 
        num_results: int = 20,
        country: str = "ALL"
    ) -> List[Dict]:
        """
        Caută pe Google (via Brave) și returnează TOP rezultate
        
        Args:
            keyword: Keyword pentru căutare
            num_results: Număr de rezultate (max 20 per call)
            country: Țara pentru rezultate (ro = România)
        
        Returns:
            List of dicts cu rezultate SERP:
            [
                {
                    'position': 1,
                    'url': 'https://...',
                    'title': '...',
                    'description': '...',
                    'domain': 'example.com'
                },
                ...
            ]
        """
        if not self.brave_api_key:
            logger.error("Brave API key not configured")
            return []
        
        try:
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.brave_api_key
            }
            
            params = {
                "q": keyword,
                "count": min(num_results, 20),  # Brave allows max 20
                "search_lang": "ro",
                "safesearch": "off"
            }
            
            # Only add country if not ALL
            if country and country != "ALL":
                params["country"] = country
            
            logger.info(f"🔍 Searching Brave for: '{keyword}' (country: {country})")
            
            response = requests.get(
                self.brave_base_url,
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Brave API error: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            results = []
            
            # Extract organic results
            web_results = data.get('web', {}).get('results', [])
            
            for i, result in enumerate(web_results[:num_results], 1):
                url = result.get('url', '')
                domain = self.extract_domain(url)
                
                results.append({
                    'position': i,
                    'url': url,
                    'title': result.get('title', ''),
                    'description': result.get('description', ''),
                    'domain': domain
                })
            
            logger.info(f"✅ Found {len(results)} results for '{keyword}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching for '{keyword}': {e}")
            return []
    
    def find_master_position(
        self, 
        results: List[Dict], 
        master_domain: str
    ) -> Optional[int]:
        """
        Găsește poziția exactă a master-ului în rezultate
        
        Args:
            results: Lista de rezultate SERP
            master_domain: Domeniul master-ului (ex: "crumantech.ro")
        
        Returns:
            Poziția (1-20) sau None dacă nu e găsit
        """
        # Normalize master domain
        master_clean = self.extract_domain(f"https://{master_domain}")
        
        for result in results:
            result_domain = result['domain']
            
            # Exact match sau subdomain match
            if result_domain == master_clean or result_domain.endswith(f".{master_clean}"):
                logger.info(f"🎯 Master found at position {result['position']} for domain {master_domain}")
                return result['position']
        
        logger.warning(f"⚠️  Master '{master_domain}' NOT found in top {len(results)} results")
        return None
    
    def batch_search_keywords(
        self, 
        keywords: List[str], 
        num_results: int = 20,
        country: str = "ro"
    ) -> Dict[str, List[Dict]]:
        """
        Caută multiple keywords în batch
        
        Args:
            keywords: Lista de keywords
            num_results: Rezultate per keyword
            country: Țara
        
        Returns:
            Dict mapping keyword → results
        """
        results_map = {}
        
        for i, keyword in enumerate(keywords, 1):
            logger.info(f"[{i}/{len(keywords)}] Searching for: {keyword}")
            
            results = self.search_keyword(
                keyword=keyword,
                num_results=num_results,
                country=country
            )
            
            results_map[keyword] = results
            
            # Rate limiting (Brave has limits)
            if i < len(keywords):
                import time
                time.sleep(1)  # 1 second between requests
        
        return results_map


# Test function
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    scraper = GoogleSerpScraper()
    
    # Test cu un keyword
    test_keyword = "reparatii anticorozive"
    results = scraper.search_keyword(test_keyword, num_results=10)
    
    print(f"\n✅ Results for '{test_keyword}':")
    for result in results:
        print(f"   [{result['position']}] {result['domain']} - {result['title'][:60]}...")
    
    # Test find master
    master_position = scraper.find_master_position(results, "crumantech.ro")
    if master_position:
        print(f"\n🎯 Master found at position: {master_position}")
    else:
        print(f"\n⚠️  Master not found in top {len(results)}")

