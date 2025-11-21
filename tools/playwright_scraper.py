#!/usr/bin/env python3
"""
🎭 PLAYWRIGHT SCRAPER - Bypass Cloudflare & JavaScript Sites
=============================================================

Features:
- Headless browser automation
- JavaScript rendering
- Cloudflare bypass
- Anti-detection measures
- Rate limiting
"""

import asyncio
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import time
import random

class PlaywrightScraper:
    """Advanced web scraper using Playwright"""
    
    def __init__(
        self,
        headless: bool = True,
        user_agent: Optional[str] = None,
        viewport: Dict = None
    ):
        """
        Args:
            headless: Run browser in headless mode
            user_agent: Custom user agent
            viewport: Custom viewport size
        """
        self.headless = headless
        self.user_agent = user_agent or self._get_random_user_agent()
        self.viewport = viewport or {"width": 1920, "height": 1080}
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        print(f"🎭 PlaywrightScraper initialized")
        print(f"   Headless: {headless}")
        print(f"   User-Agent: {self.user_agent[:50]}...")
    
    def _get_random_user_agent(self) -> str:
        """Get random realistic user agent"""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        return random.choice(agents)
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
    
    async def start(self):
        """Start browser"""
        if self.browser:
            return
        
        playwright = await async_playwright().start()
        
        # Launch browser with anti-detection
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # Create context with realistic settings
        self.context = await self.browser.new_context(
            user_agent=self.user_agent,
            viewport=self.viewport,
            locale='ro-RO',
            timezone_id='Europe/Bucharest',
            permissions=['geolocation'],
            geolocation={'longitude': 26.1025, 'latitude': 44.4268},  # Bucharest
            extra_http_headers={
                'Accept-Language': 'ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        # Add stealth JavaScript
        await self.context.add_init_script("""
            // Overwrite the `navigator.webdriver` property to make it harder to detect
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Overwrite the `plugins` property to use a custom getter
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Overwrite the `languages` property to use a custom getter
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ro-RO', 'ro', 'en-US', 'en'],
            });
        """)
        
        print("✅ Browser started")
    
    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
            self.context = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        print("✅ Browser closed")
    
    async def scrape_page(
        self,
        url: str,
        wait_for: Optional[str] = None,
        wait_time: float = 2.0,
        screenshot: bool = False
    ) -> Dict:
        """
        Scrape single page
        
        Args:
            url: Target URL
            wait_for: CSS selector to wait for
            wait_time: Additional wait time (seconds)
            screenshot: Take screenshot
            
        Returns:
            {
                "url": str,
                "html": str,
                "text": str,
                "title": str,
                "status": int,
                "success": bool,
                "screenshot": bytes (optional)
            }
        """
        
        if not self.context:
            await self.start()
        
        page = await self.context.new_page()
        
        try:
            # Navigate with retry logic
            response = None
            for attempt in range(3):
                try:
                    response = await page.goto(
                        url,
                        wait_until='domcontentloaded',
                        timeout=30000
                    )
                    break
                except Exception as e:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2)
            
            # Wait for specific selector if provided
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=10000)
                except:
                    pass  # Continue even if selector not found
            
            # Additional wait for dynamic content
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            # Extract content
            html = await page.content()
            text = await page.inner_text('body')
            title = await page.title()
            
            result = {
                "url": url,
                "html": html,
                "text": text,
                "title": title,
                "status": response.status if response else 0,
                "success": True
            }
            
            # Screenshot if requested
            if screenshot:
                result["screenshot"] = await page.screenshot(full_page=True)
            
            return result
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {
                "url": url,
                "html": "",
                "text": "",
                "title": "",
                "status": 0,
                "success": False,
                "error": str(e)
            }
            
        finally:
            await page.close()
    
    async def scrape_bulk(
        self,
        urls: List[str],
        max_concurrent: int = 3,
        delay_between: float = 1.0,
        progress_callback = None
    ) -> List[Dict]:
        """
        Scrape multiple URLs with concurrency control
        
        Args:
            urls: List of URLs
            max_concurrent: Max concurrent pages
            delay_between: Delay between requests (seconds)
            progress_callback: Callback function(current, total, url)
            
        Returns:
            List of scrape results
        """
        
        if not self.context:
            await self.start()
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(idx: int, url: str):
            async with semaphore:
                if progress_callback:
                    progress_callback(idx + 1, len(urls), url)
                
                result = await self.scrape_page(url)
                
                # Random delay
                if idx < len(urls) - 1:
                    await asyncio.sleep(delay_between + random.uniform(0, 0.5))
                
                return result
        
        # Create tasks
        tasks = [
            scrape_with_semaphore(idx, url)
            for idx, url in enumerate(urls)
        ]
        
        # Execute with progress
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter exceptions
        valid_results = []
        for r in results:
            if isinstance(r, Exception):
                print(f"   ❌ Task failed: {r}")
            else:
                valid_results.append(r)
        
        return valid_results
    
    async def discover_links(
        self,
        start_url: str,
        max_pages: int = 100,
        same_domain_only: bool = True,
        exclude_patterns: List[str] = None
    ) -> List[str]:
        """
        Discover links from a starting URL
        
        Args:
            start_url: Starting URL
            max_pages: Max pages to discover
            same_domain_only: Only follow links on same domain
            exclude_patterns: URL patterns to exclude
            
        Returns:
            List of discovered URLs
        """
        
        if not self.context:
            await self.start()
        
        exclude_patterns = exclude_patterns or [
            '/cart', '/checkout', '/login', '/register',
            '.pdf', '.jpg', '.png', '.gif', '.zip'
        ]
        
        visited = set()
        to_visit = [start_url]
        discovered = []
        
        base_domain = urlparse(start_url).netloc
        
        page = await self.context.new_page()
        
        try:
            while to_visit and len(discovered) < max_pages:
                url = to_visit.pop(0)
                
                if url in visited:
                    continue
                
                # Check exclusions
                if any(pattern in url for pattern in exclude_patterns):
                    continue
                
                visited.add(url)
                
                try:
                    print(f"🔍 [{len(discovered)+1}/{max_pages}] Discovering: {url[:60]}...")
                    
                    # Wait for full page load (React/Vue apps need this)
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    
                    # Extra wait for dynamic content
                    await asyncio.sleep(2)
                    
                    # Extract all links
                    try:
                        links = await page.eval_on_selector_all(
                            'a[href]',
                            '(elements) => elements.map(el => el.href)'
                        )
                    except:
                        # Fallback method
                        links = await page.evaluate('''() => {
                            return Array.from(document.querySelectorAll('a[href]'))
                                .map(a => a.href);
                        }''')
                    
                    print(f"      Found {len(links)} links on page")
                    
                    discovered.append(url)
                    
                    # Process links
                    for link in links:
                        # Make absolute
                        abs_link = urljoin(url, link)
                        
                        # Check domain
                        if same_domain_only:
                            if urlparse(abs_link).netloc != base_domain:
                                continue
                        
                        # Check exclusions
                        if any(pattern in abs_link for pattern in exclude_patterns):
                            continue
                        
                        # Add to queue
                        if abs_link not in visited and abs_link not in to_visit:
                            to_visit.append(abs_link)
                    
                    # Small delay
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"   ⚠️ Error: {e}")
                    continue
        
        finally:
            await page.close()
        
        print(f"\n✅ Discovered {len(discovered)} pages")
        
        return discovered


async def test_scraper():
    """Test Playwright scraper"""
    
    print("=" * 80)
    print("🧪 TEST PLAYWRIGHT SCRAPER")
    print("=" * 80)
    
    # Test URL
    test_url = "https://www.dedeman.ro"
    
    async with PlaywrightScraper(headless=True) as scraper:
        # Test single page
        print(f"\n🌐 Testing: {test_url}")
        result = await scraper.scrape_page(test_url, wait_time=3)
        
        if result['success']:
            print(f"✅ SUCCESS!")
            print(f"   Title: {result['title']}")
            print(f"   HTML size: {len(result['html'])} bytes")
            print(f"   Text size: {len(result['text'])} bytes")
            print(f"   Status: {result['status']}")
            print(f"\n   First 200 chars of text:")
            print(f"   {result['text'][:200]}...")
        else:
            print(f"❌ FAILED: {result.get('error', 'Unknown')}")
        
        # Test link discovery
        print(f"\n🔍 Testing link discovery (max 10 pages)...")
        links = await scraper.discover_links(test_url, max_pages=10)
        
        print(f"\n✅ Discovered {len(links)} pages:")
        for idx, link in enumerate(links[:10], 1):
            print(f"   {idx}. {link}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_scraper())

