#!/usr/bin/env python3
"""
🏗️ DEDEMAN DEEP SCRAPER
=======================

Deep scraping pentru React SPA sites:
- Category navigation
- Product listing pages
- Scroll to load more
- Dynamic content wait
"""

import asyncio
from playwright.async_api import async_playwright
from typing import List, Dict, Set
import json
import time
from urllib.parse import urljoin, urlparse

class DedemanDeepScraper:
    """Deep scraper pentru Dedeman.ro"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.visited_urls: Set[str] = set()
        self.scraped_pages: List[Dict] = []
        
    async def start(self):
        """Start browser"""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='ro-RO'
        )
        
        # Stealth mode
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        print("✅ Browser started (deep mode)")
    
    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def scrape_dedeman(self, max_pages: int = 300):
        """
        Deep scrape Dedeman.ro
        
        Strategy:
        1. Start from homepage
        2. Extract main categories
        3. Navigate each category
        4. Scroll & load more in listings
        5. Extract product pages
        """
        
        await self.start()
        
        try:
            page = await self.context.new_page()
            
            # STEP 1: Homepage + Categories
            print(f"\n📍 STEP 1: Extracting Categories")
            await page.goto('https://www.dedeman.ro', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)  # Wait for React
            
            # Extract categories from menu
            categories = await self._extract_categories(page)
            print(f"✅ Found {len(categories)} categories")
            
            # STEP 2: Scrape each category
            print(f"\n📥 STEP 2: Scraping Categories")
            
            for idx, category in enumerate(categories[:20], 1):  # Limit to 20 categories
                if len(self.scraped_pages) >= max_pages:
                    break
                
                print(f"\n   [{idx}/{min(20, len(categories))}] Category: {category['name']}")
                print(f"       URL: {category['url'][:60]}...")
                
                await self._scrape_category(page, category, max_pages)
                
                # Progress
                print(f"       Progress: {len(self.scraped_pages)}/{max_pages} pages")
            
            await page.close()
            
            print(f"\n✅ Deep scraping completed!")
            print(f"   Total pages: {len(self.scraped_pages)}")
            
            return self.scraped_pages
            
        finally:
            await self.close()
    
    async def _extract_categories(self, page) -> List[Dict]:
        """Extract category links from menu"""
        
        categories = []
        
        try:
            # Method 1: Navigation menu
            category_links = await page.evaluate('''() => {
                const links = [];
                
                // Try main navigation
                const nav = document.querySelector('nav, .nav, .navigation, [role="navigation"]');
                if (nav) {
                    const as = nav.querySelectorAll('a');
                    as.forEach(a => {
                        if (a.href && a.textContent.trim()) {
                            links.push({
                                name: a.textContent.trim(),
                                url: a.href
                            });
                        }
                    });
                }
                
                // Try category menu
                const catMenu = document.querySelector('.categories, .category-menu, [class*="categor"]');
                if (catMenu) {
                    const as = catMenu.querySelectorAll('a');
                    as.forEach(a => {
                        if (a.href && a.textContent.trim()) {
                            links.push({
                                name: a.textContent.trim(),
                                url: a.href
                            });
                        }
                    });
                }
                
                // Fallback: All links
                if (links.length === 0) {
                    const allLinks = document.querySelectorAll('a[href*="/ro/"]');
                    allLinks.forEach(a => {
                        const href = a.href;
                        const text = a.textContent.trim();
                        if (text && href.includes('/ro/') && !href.includes('cart') && !href.includes('login')) {
                            links.push({ name: text, url: href });
                        }
                    });
                }
                
                return links;
            }''')
            
            # Deduplicate
            seen = set()
            for cat in category_links:
                if cat['url'] not in seen and 'dedeman.ro' in cat['url']:
                    seen.add(cat['url'])
                    categories.append(cat)
            
            print(f"   Extracted {len(categories)} unique categories")
            
            # Debug: show first 10
            for i, cat in enumerate(categories[:10], 1):
                print(f"      {i}. {cat['name'][:40]}")
            
        except Exception as e:
            print(f"   ⚠️ Error extracting categories: {e}")
        
        return categories
    
    async def _scrape_category(self, page, category: Dict, max_pages: int):
        """Scrape a category page with pagination"""
        
        if len(self.scraped_pages) >= max_pages:
            return
        
        try:
            # Navigate to category
            await page.goto(category['url'], wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Check if it's a listing page
            is_listing = await page.evaluate('''() => {
                return document.querySelectorAll('[class*="product"], [class*="item"]').length > 5;
            }''')
            
            if is_listing:
                # Extract product links
                product_links = await self._extract_product_links(page)
                print(f"       Found {len(product_links)} products")
                
                # Scrape products
                for product_url in product_links[:50]:  # Max 50 per category
                    if len(self.scraped_pages) >= max_pages:
                        break
                    
                    if product_url not in self.visited_urls:
                        await self._scrape_product_page(page, product_url)
            else:
                # Scrape the page itself
                await self._scrape_current_page(page, category['url'])
            
        except Exception as e:
            print(f"       ⚠️ Error: {e}")
    
    async def _extract_product_links(self, page) -> List[str]:
        """Extract product links from listing page"""
        
        # Try to load more by scrolling
        for _ in range(3):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)
        
        # Extract links
        links = await page.evaluate('''() => {
            const urls = new Set();
            
            // Find product cards/items
            const products = document.querySelectorAll('[class*="product"], [class*="item"], [data-product]');
            
            products.forEach(prod => {
                const link = prod.querySelector('a[href*="/ro/"]');
                if (link && link.href) {
                    urls.add(link.href);
                }
            });
            
            // Fallback: any product-looking links
            if (urls.size === 0) {
                const allLinks = document.querySelectorAll('a[href*="/ro/p"]');
                allLinks.forEach(a => urls.add(a.href));
            }
            
            return Array.from(urls);
        }''')
        
        return links
    
    async def _scrape_product_page(self, page, url: str):
        """Scrape individual product page"""
        
        if url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(1)
            
            # Extract content
            title = await page.title()
            text = await page.inner_text('body')
            
            if text and len(text) > 100:
                self.scraped_pages.append({
                    "url": url,
                    "title": title,
                    "content": text[:5000]  # Limit size
                })
                
                print(f"       ✅ Scraped: {title[:50]}...")
        
        except Exception as e:
            print(f"       ⚠️ Skip: {url[:60]} - {e}")
    
    async def _scrape_current_page(self, page, url: str):
        """Scrape current page content"""
        
        if url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        
        try:
            title = await page.title()
            text = await page.inner_text('body')
            
            if text and len(text) > 100:
                self.scraped_pages.append({
                    "url": url,
                    "title": title,
                    "content": text
                })
        
        except Exception as e:
            print(f"       ⚠️ Error scraping page: {e}")


async def main():
    """CLI interface"""
    import sys
    
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    
    print("=" * 80)
    print("🏗️ DEDEMAN DEEP SCRAPER")
    print("=" * 80)
    print(f"Target pages: {max_pages}")
    print("")
    
    scraper = DedemanDeepScraper()
    pages = await scraper.scrape_dedeman(max_pages)
    
    print(f"\n{'='*80}")
    print(f"✅ COMPLETED!")
    print(f"   Pages scraped: {len(pages)}")
    print(f"{'='*80}")
    
    # Save to JSON for inspection
    with open('/tmp/dedeman_scraped.json', 'w', encoding='utf-8') as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved to: /tmp/dedeman_scraped.json")


if __name__ == "__main__":
    asyncio.run(main())

