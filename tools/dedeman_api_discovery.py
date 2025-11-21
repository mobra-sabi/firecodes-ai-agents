#!/usr/bin/env python3
"""
🔍 DEDEMAN API DISCOVERY
========================

Reverse engineering Dedeman.ro API endpoints
"""

import asyncio
from playwright.async_api import async_playwright
import json
import re
from typing import List, Dict

class DedemanAPIDiscovery:
    """Discover Dedeman API endpoints"""
    
    def __init__(self):
        self.api_calls = []
        self.product_urls = []
        self.category_urls = []
    
    async def discover(self):
        """Discover API endpoints"""
        
        print("🔍 Starting API Discovery...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            # Intercept network requests
            page.on('request', self._log_request)
            page.on('response', self._log_response)
            
            # STEP 1: Homepage
            print("\n📍 STEP 1: Analyzing Homepage...")
            await page.goto('https://www.dedeman.ro', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # STEP 2: Try to navigate to a category
            print("\n📍 STEP 2: Exploring Categories...")
            
            # Try clicking on menu items
            try:
                # Wait for any navigation menu
                await page.wait_for_selector('nav, .nav, [role="navigation"]', timeout=5000)
                
                # Get all links
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a[href*="/ro/"]'))
                        .map(a => ({href: a.href, text: a.textContent.trim()}))
                        .filter(l => l.text && l.href.includes('dedeman.ro'));
                }''')
                
                print(f"   Found {len(links)} navigation links")
                
                # Try first category link
                if links:
                    category_link = links[0]['href']
                    print(f"   Testing category: {category_link[:60]}...")
                    
                    await page.goto(category_link, wait_until='networkidle', timeout=30000)
                    await asyncio.sleep(3)
                    
                    # Scroll to trigger lazy loading
                    for i in range(3):
                        await page.evaluate('window.scrollBy(0, 500)')
                        await asyncio.sleep(1)
            
            except Exception as e:
                print(f"   ⚠️ Category navigation: {e}")
            
            # STEP 3: Try search
            print("\n📍 STEP 3: Testing Search...")
            
            try:
                # Try to find search input
                search_selectors = [
                    'input[type="search"]',
                    'input[name*="search"]',
                    'input[placeholder*="cauta"]',
                    '.search input'
                ]
                
                for selector in search_selectors:
                    try:
                        await page.fill(selector, 'bormasina', timeout=2000)
                        await page.press(selector, 'Enter')
                        await asyncio.sleep(3)
                        print(f"   ✅ Search triggered with: {selector}")
                        break
                    except:
                        continue
            
            except Exception as e:
                print(f"   ⚠️ Search: {e}")
            
            await browser.close()
            
            # Analyze results
            print(f"\n{'='*80}")
            print("📊 ANALYSIS RESULTS")
            print(f"{'='*80}")
            
            self._analyze_api_calls()
    
    async def _log_request(self, request):
        """Log intercepted request"""
        url = request.url
        
        # Filter API-like requests
        if any(x in url.lower() for x in ['api', 'json', 'graphql', 'ajax', 'rest']):
            self.api_calls.append({
                'type': 'request',
                'method': request.method,
                'url': url,
                'resource_type': request.resource_type
            })
    
    async def _log_response(self, response):
        """Log intercepted response"""
        url = response.url
        
        # Filter API responses
        if any(x in url.lower() for x in ['api', 'json', 'graphql', 'ajax', 'rest']):
            try:
                content_type = response.headers.get('content-type', '')
                
                if 'json' in content_type:
                    # Try to get JSON body
                    try:
                        body = await response.text()
                        self.api_calls.append({
                            'type': 'response',
                            'method': response.request.method,
                            'url': url,
                            'status': response.status,
                            'content_type': content_type,
                            'body_preview': body[:500] if body else None
                        })
                    except:
                        pass
            except:
                pass
    
    def _analyze_api_calls(self):
        """Analyze discovered API calls"""
        
        if not self.api_calls:
            print("❌ No API calls discovered!")
            print("\nDedeman folosește probabil:")
            print("  • Server-side rendering")
            print("  • SAU API calls obfuscate")
            print("  • SAU anti-scraping foarte strict")
            
            print("\n💡 PLAN B: Direct HTML Scraping cu delays lungi")
            return
        
        print(f"\n✅ Discovered {len(self.api_calls)} API calls")
        
        # Group by domain/endpoint
        endpoints = {}
        for call in self.api_calls:
            url = call['url']
            base = url.split('?')[0]  # Remove query params
            
            if base not in endpoints:
                endpoints[base] = []
            endpoints[base].append(call)
        
        print(f"\n📋 Unique endpoints: {len(endpoints)}")
        
        for idx, (endpoint, calls) in enumerate(endpoints.items(), 1):
            print(f"\n   {idx}. {endpoint[:80]}")
            print(f"      Calls: {len(calls)}")
            print(f"      Methods: {set(c['method'] for c in calls)}")
            
            # Show sample response if available
            for call in calls:
                if call.get('body_preview'):
                    print(f"      Response preview: {call['body_preview'][:100]}...")
                    break
        
        # Save to file
        with open('/tmp/dedeman_api_discovery.json', 'w', encoding='utf-8') as f:
            json.dump({
                'total_calls': len(self.api_calls),
                'endpoints': list(endpoints.keys()),
                'calls': self.api_calls
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved to: /tmp/dedeman_api_discovery.json")


async def main():
    """Run discovery"""
    print("="*80)
    print("🔍 DEDEMAN API REVERSE ENGINEERING")
    print("="*80)
    
    discovery = DedemanAPIDiscovery()
    await discovery.discover()
    
    print(f"\n{'='*80}")
    print("✅ Discovery Complete!")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())

