#!/usr/bin/env python3
"""
🌐 PREMIUM SCRAPER - Universal Integration
==========================================

Suportă:
- ScraperAPI
- ScrapingBee  
- BrightData
- Apify
- Zyte
- Custom Proxies
"""

import os
import requests
import time
from typing import Dict, List, Optional
from urllib.parse import urlencode, quote

class PremiumScraper:
    """Universal premium scraping service"""
    
    def __init__(self, service: str = "auto", api_key: Optional[str] = None):
        """
        Args:
            service: "scraperapi", "scrapingbee", "brightdata", "apify", "zyte", "auto"
            api_key: API key pentru serviciu
        """
        self.service = service.lower()
        self.api_key = api_key or self._detect_api_key()
        
        if not self.api_key and service != "auto":
            raise ValueError(f"API key required for {service}")
        
        print(f"🌐 PremiumScraper initialized: {self.service}")
    
    def _detect_api_key(self) -> Optional[str]:
        """Auto-detect API key from environment"""
        
        keys = {
            "scraperapi": os.getenv("SCRAPERAPI_KEY"),
            "scrapingbee": os.getenv("SCRAPINGBEE_KEY"),
            "brightdata": os.getenv("BRIGHTDATA_KEY"),
            "apify": os.getenv("APIFY_KEY"),
            "zyte": os.getenv("ZYTE_KEY"),
        }
        
        # If service specified, return its key
        if self.service in keys:
            return keys[self.service]
        
        # Auto-detect: return first available
        for service, key in keys.items():
            if key:
                self.service = service
                print(f"✅ Auto-detected service: {service}")
                return key
        
        return None
    
    def scrape_page(self, url: str, render_js: bool = True, **kwargs) -> Dict:
        """
        Scrape single page via premium service
        
        Args:
            url: Target URL
            render_js: Whether to render JavaScript
            **kwargs: Service-specific parameters
            
        Returns:
            {
                "html": str,
                "status_code": int,
                "url": str,
                "success": bool,
                "service": str
            }
        """
        
        if self.service == "scraperapi":
            return self._scrape_scraperapi(url, render_js, **kwargs)
        elif self.service == "scrapingbee":
            return self._scrape_scrapingbee(url, render_js, **kwargs)
        elif self.service == "brightdata":
            return self._scrape_brightdata(url, render_js, **kwargs)
        elif self.service == "apify":
            return self._scrape_apify(url, render_js, **kwargs)
        elif self.service == "zyte":
            return self._scrape_zyte(url, render_js, **kwargs)
        else:
            raise ValueError(f"Unsupported service: {self.service}")
    
    def scrape_bulk(self, urls: List[str], render_js: bool = True, delay: float = 0) -> List[Dict]:
        """
        Scrape multiple URLs
        
        Args:
            urls: List of URLs to scrape
            render_js: Whether to render JavaScript
            delay: Delay between requests (seconds)
            
        Returns:
            List of scrape results
        """
        results = []
        
        for idx, url in enumerate(urls, 1):
            print(f"🌐 [{idx}/{len(urls)}] Scraping: {url[:60]}...")
            
            try:
                result = self.scrape_page(url, render_js)
                results.append(result)
                
                if result['success']:
                    print(f"   ✅ Success ({len(result['html'])} bytes)")
                else:
                    print(f"   ❌ Failed: {result.get('error', 'Unknown')}")
                
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                results.append({
                    "url": url,
                    "success": False,
                    "error": str(e),
                    "html": "",
                    "status_code": 0
                })
            
            # Rate limiting
            if delay > 0 and idx < len(urls):
                time.sleep(delay)
        
        return results
    
    # ===================================================================
    # SCRAPERAPI
    # ===================================================================
    
    def _scrape_scraperapi(self, url: str, render_js: bool = True, **kwargs) -> Dict:
        """ScraperAPI implementation"""
        
        params = {
            'api_key': self.api_key,
            'url': url,
            'render': 'true' if render_js else 'false',
            'country_code': kwargs.get('country', 'us'),
        }
        
        # Premium features
        if kwargs.get('premium'):
            params['premium'] = 'true'
        
        if kwargs.get('session'):
            params['session_number'] = kwargs['session']
        
        try:
            resp = requests.get(
                'https://api.scraperapi.com/',
                params=params,
                timeout=kwargs.get('timeout', 60)
            )
            
            return {
                "html": resp.text,
                "status_code": resp.status_code,
                "url": url,
                "success": resp.status_code == 200,
                "service": "scraperapi"
            }
            
        except Exception as e:
            return {
                "html": "",
                "status_code": 0,
                "url": url,
                "success": False,
                "error": str(e),
                "service": "scraperapi"
            }
    
    # ===================================================================
    # SCRAPINGBEE
    # ===================================================================
    
    def _scrape_scrapingbee(self, url: str, render_js: bool = True, **kwargs) -> Dict:
        """ScrapingBee implementation"""
        
        params = {
            'api_key': self.api_key,
            'url': url,
            'render_js': 'true' if render_js else 'false',
            'premium_proxy': 'true' if kwargs.get('premium') else 'false',
        }
        
        # Wait for selector (useful for SPAs)
        if kwargs.get('wait_for'):
            params['wait_for'] = kwargs['wait_for']
        
        # Block resources (faster)
        if kwargs.get('block_resources'):
            params['block_resources'] = 'true'
        
        try:
            resp = requests.get(
                'https://app.scrapingbee.com/api/v1/',
                params=params,
                timeout=kwargs.get('timeout', 60)
            )
            
            return {
                "html": resp.text,
                "status_code": resp.status_code,
                "url": url,
                "success": resp.status_code == 200,
                "service": "scrapingbee"
            }
            
        except Exception as e:
            return {
                "html": "",
                "status_code": 0,
                "url": url,
                "success": False,
                "error": str(e),
                "service": "scrapingbee"
            }
    
    # ===================================================================
    # BRIGHTDATA (LUMINATI)
    # ===================================================================
    
    def _scrape_brightdata(self, url: str, render_js: bool = True, **kwargs) -> Dict:
        """BrightData Web Unlocker"""
        
        # BrightData requires proxy authentication
        proxy_url = f"http://brd-customer-{self.api_key}:@brd.superproxy.io:22225"
        
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        try:
            resp = requests.get(
                url,
                proxies=proxies,
                timeout=kwargs.get('timeout', 60)
            )
            
            return {
                "html": resp.text,
                "status_code": resp.status_code,
                "url": url,
                "success": resp.status_code == 200,
                "service": "brightdata"
            }
            
        except Exception as e:
            return {
                "html": "",
                "status_code": 0,
                "url": url,
                "success": False,
                "error": str(e),
                "service": "brightdata"
            }
    
    # ===================================================================
    # APIFY
    # ===================================================================
    
    def _scrape_apify(self, url: str, render_js: bool = True, **kwargs) -> Dict:
        """Apify Web Scraper Actor"""
        
        # Use Apify's Web Scraper actor
        actor_id = kwargs.get('actor_id', 'apify/web-scraper')
        
        run_input = {
            "startUrls": [{"url": url}],
            "proxyConfiguration": {"useApifyProxy": True},
            "renderJavaScript": render_js
        }
        
        try:
            # Start actor run
            resp = requests.post(
                f'https://api.apify.com/v2/acts/{actor_id}/runs',
                params={'token': self.api_key},
                json=run_input,
                timeout=10
            )
            
            if resp.status_code != 201:
                raise Exception(f"Failed to start actor: {resp.status_code}")
            
            run_id = resp.json()['data']['id']
            
            # Wait for completion (polling)
            for _ in range(60):  # Max 60 seconds
                time.sleep(1)
                
                status_resp = requests.get(
                    f'https://api.apify.com/v2/actor-runs/{run_id}',
                    params={'token': self.api_key}
                )
                
                status = status_resp.json()['data']['status']
                
                if status == 'SUCCEEDED':
                    # Get dataset
                    dataset_resp = requests.get(
                        f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items',
                        params={'token': self.api_key}
                    )
                    
                    items = dataset_resp.json()
                    
                    if items:
                        return {
                            "html": items[0].get('html', ''),
                            "status_code": 200,
                            "url": url,
                            "success": True,
                            "service": "apify"
                        }
                
                elif status in ['FAILED', 'ABORTED']:
                    raise Exception(f"Actor run {status}")
            
            raise Exception("Timeout waiting for actor")
            
        except Exception as e:
            return {
                "html": "",
                "status_code": 0,
                "url": url,
                "success": False,
                "error": str(e),
                "service": "apify"
            }
    
    # ===================================================================
    # ZYTE (SCRAPINGHUB)
    # ===================================================================
    
    def _scrape_zyte(self, url: str, render_js: bool = True, **kwargs) -> Dict:
        """Zyte Smart Proxy Manager"""
        
        proxy_url = f"http://{self.api_key}:@proxy.crawlera.com:8011"
        
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        headers = {
            'X-Crawlera-Profile': 'desktop' if render_js else 'pass'
        }
        
        try:
            resp = requests.get(
                url,
                proxies=proxies,
                headers=headers,
                timeout=kwargs.get('timeout', 60)
            )
            
            return {
                "html": resp.text,
                "status_code": resp.status_code,
                "url": url,
                "success": resp.status_code == 200,
                "service": "zyte"
            }
            
        except Exception as e:
            return {
                "html": "",
                "status_code": 0,
                "url": url,
                "success": False,
                "error": str(e),
                "service": "zyte"
            }


def test_scraper():
    """Test premium scraper"""
    
    print("=" * 80)
    print("🧪 TESTING PREMIUM SCRAPER")
    print("=" * 80)
    
    # Test URL
    test_url = "https://www.dedeman.ro"
    
    # Try to initialize
    try:
        scraper = PremiumScraper(service="auto")
        
        print(f"\n✅ Service: {scraper.service}")
        print(f"✅ API Key: {scraper.api_key[:10]}..." if scraper.api_key else "❌ No API key")
        
        if scraper.api_key:
            print(f"\n🌐 Testing with {test_url}...")
            result = scraper.scrape_page(test_url, render_js=True)
            
            if result['success']:
                print(f"✅ SUCCESS!")
                print(f"   HTML size: {len(result['html'])} bytes")
                print(f"   Status: {result['status_code']}")
            else:
                print(f"❌ FAILED: {result.get('error', 'Unknown')}")
        else:
            print("\n⚠️ No API key found in environment.")
            print("   Set one of:")
            print("   export SCRAPERAPI_KEY=your_key")
            print("   export SCRAPINGBEE_KEY=your_key")
            print("   export BRIGHTDATA_KEY=your_key")
            print("   export APIFY_KEY=your_key")
            print("   export ZYTE_KEY=your_key")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_scraper()

