#!/usr/bin/env python3
"""
🔥 DEDEMAN HYBRID SCRAPER
==========================

Hybrid approach:
1. Use API to get category structure (fast)
2. Use Playwright to navigate and extract products (complete)
"""

import asyncio
import aiohttp
from playwright.async_api import async_playwright
import json
from typing import List, Dict
import time

class DedemanHybridScraper:
    """Hybrid API + Playwright scraper"""
    
    def __init__(self):
        self.base_api = "https://catalog.dedeman.ro/api/live"
        self.base_url = "https://www.dedeman.ro"
        self.scraped_pages = []
        self.visited = set()
        
        self.browser = None
        self.context = None
        self.page = None
    
    async def start_browser(self):
        """Initialize browser"""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        self.page = await self.context.new_page()
        
        print("✅ Browser ready")
    
    async def close_browser(self):
        """Close browser"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def scrape_dedeman(self, max_pages: int = 300):
        """Main scraping workflow"""
        
        print(f"🔥 Starting HYBRID scraping (target: {max_pages} pages)")
        
        try:
            await self.start_browser()
            
            # STEP 1: Load homepage to get real navigation
            print(f"\n📍 STEP 1: Loading Homepage...")
            await self.page.goto('https://www.dedeman.ro', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # Extract homepage content
            await self._scrape_current_page('https://www.dedeman.ro', 'Homepage')
            
            # STEP 2: Extract navigation menu links
            print(f"\n📍 STEP 2: Extracting Navigation...")
            category_links = await self._extract_navigation_links()
            
            print(f"✅ Found {len(category_links)} category links")
            
            # STEP 3: Visit each category
            print(f"\n📍 STEP 3: Visiting Categories...")
            
            for idx, link in enumerate(category_links[:30], 1):  # Limit to 30
                if len(self.scraped_pages) >= max_pages:
                    break
                
                print(f"\n   [{idx}/{min(30, len(category_links))}] {link['text'][:40]}")
                print(f"       URL: {link['url'][:60]}...")
                
                await self._scrape_category_page(link['url'], link['text'], max_pages)
                
                print(f"       Progress: {len(self.scraped_pages)}/{max_pages} pages")
            
        finally:
            await self.close_browser()
        
        print(f"\n✅ Scraping completed!")
        print(f"   Total pages: {len(self.scraped_pages)}")
        
        return self.scraped_pages
    
    async def _extract_navigation_links(self) -> List[Dict]:
        """Extract navigation links from page"""
        
        links = await self.page.evaluate('''() => {
            const found = [];
            
            // Try to find main navigation/menu
            const selectors = [
                'nav a',
                '.nav a',
                '.navigation a',
                '.menu a',
                '[role="navigation"] a',
                '.categories a',
                'header a'
            ];
            
            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                elements.forEach(a => {
                    const href = a.href;
                    const text = a.textContent.trim();
                    
                    // Filter: only dedeman.ro links, skip cart/login/etc
                    if (href && text && 
                        href.includes('dedeman.ro') && 
                        href.includes('/ro/') &&
                        !href.includes('cart') &&
                        !href.includes('login') &&
                        !href.includes('account')) {
                        
                        found.push({ url: href, text: text });
                    }
                });
            }
            
            // Deduplicate
            const unique = [];
            const seen = new Set();
            
            for (const item of found) {
                if (!seen.has(item.url)) {
                    seen.add(item.url);
                    unique.push(item);
                }
            }
            
            return unique;
        }''')
        
        # Show sample
        for i, link in enumerate(links[:10], 1):
            print(f"      {i}. {link['text'][:30]} → {link['url'][:50]}...")
        
        if len(links) > 10:
            print(f"      ... (+{len(links) - 10} more)")
        
        return links
    
    async def _scrape_category_page(self, url: str, title: str, max_pages: int):
        """Scrape a category page"""
        
        if len(self.scraped_pages) >= max_pages:
            return
        
        if url in self.visited:
            return
        
        self.visited.add(url)
        
        try:
            # Navigate to category
            await self.page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await asyncio.sleep(2)
            
            # Check if it's a product listing page
            product_count = await self.page.evaluate('''() => {
                return document.querySelectorAll('[class*="product"], [data-product]').length;
            }''')
            
            if product_count > 0:
                print(f"       Found {product_count} products on page")
                
                # Scroll to load more
                for _ in range(3):
                    await self.page.evaluate('window.scrollBy(0, 800)')
                    await asyncio.sleep(0.5)
                
                # Extract product links
                product_links = await self.page.evaluate('''() => {
                    const links = new Set();
                    
                    // Find product cards/items
                    const products = document.querySelectorAll('[class*="product"], [data-product], .item');
                    
                    products.forEach(prod => {
                        const link = prod.querySelector('a[href*="/ro/"]');
                        if (link && link.href) {
                            links.add(link.href);
                        }
                    });
                    
                    return Array.from(links);
                }''')
                
                print(f"       Extracted {len(product_links)} product links")
                
                # Visit product pages
                for prod_url in product_links[:10]:  # Max 10 per category
                    if len(self.scraped_pages) >= max_pages:
                        break
                    
                    await self._scrape_product_page(prod_url)
            else:
                # Regular page, just scrape content
                await self._scrape_current_page(url, title)
        
        except Exception as e:
            print(f"       ⚠️ Error: {e}")
    
    async def _scrape_product_page(self, url: str):
        """Scrape individual product"""
        
        if url in self.visited:
            return
        
        self.visited.add(url)
        
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(1)
            
            # Extract content
            title = await self.page.title()
            
            # Try to get main content
            text = await self.page.evaluate('''() => {
                // Try to find main product container
                const main = document.querySelector('main, .main, .product, [role="main"]');
                if (main) {
                    return main.innerText;
                }
                return document.body.innerText;
            }''')
            
            if text and len(text) > 100:
                self.scraped_pages.append({
                    'url': url,
                    'title': title,
                    'content': text[:5000]  # Limit size
                })
                
                print(f"         ✅ {title[:50]}...")
        
        except Exception as e:
            print(f"         ⚠️ Skip: {e}")
    
    async def _scrape_current_page(self, url: str, title: str = None):
        """Scrape current page content"""
        
        if url in self.visited:
            return
        
        self.visited.add(url)
        
        try:
            if not title:
                title = await self.page.title()
            
            text = await self.page.evaluate('''() => {
                return document.body.innerText;
            }''')
            
            if text and len(text) > 100:
                self.scraped_pages.append({
                    'url': url,
                    'title': title,
                    'content': text
                })
        
        except Exception as e:
            print(f"       ⚠️ Error scraping page: {e}")


async def main():
    """CLI"""
    import sys
    
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    
    print("=" * 80)
    print("🔥 DEDEMAN HYBRID SCRAPER")
    print("=" * 80)
    print(f"Method: API structure + Playwright navigation")
    print(f"Target: {max_pages} pages")
    print("")
    
    scraper = DedemanHybridScraper()
    pages = await scraper.scrape_dedeman(max_pages)
    
    print(f"\n{'='*80}")
    print(f"✅ COMPLETED!")
    print(f"   Pages scraped: {len(pages)}")
    print(f"{'='*80}")
    
    # Save
    output_file = '/tmp/dedeman_hybrid_scraped.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_pages': len(pages),
            'pages': pages
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())

