#!/usr/bin/env python3
"""
🎯 DEDEMAN API SCRAPER
======================

Direct API scraping (rapid & eficient!)
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Set
from urllib.parse import urljoin
import time

class DedemanAPIScraper:
    """Scrape Dedeman using their API directly"""
    
    def __init__(self):
        self.base_api = "https://catalog.dedeman.ro/api/live"
        self.base_url = "https://www.dedeman.ro"
        self.scraped_pages = []
        self.visited = set()
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'ro-RO,ro;q=0.9',
            'Referer': 'https://www.dedeman.ro/'
        }
    
    async def scrape_dedeman(self, max_pages: int = 300):
        """Main scraping method"""
        
        print(f"🎯 Starting API-based scraping (target: {max_pages} pages)")
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            
            # STEP 1: Get catalog info
            print(f"\n📍 STEP 1: Getting Catalog Structure...")
            catalog_id = 55  # Black Friday 2025 (from discovery)
            
            # Try to get main catalog
            categories = await self._get_categories(session, catalog_id)
            
            if not categories:
                print("   ⚠️ No categories from catalog 55, trying default...")
                # Try without catalog ID (main site)
                categories = await self._discover_categories(session)
            
            print(f"✅ Found {len(categories)} categories")
            
            # STEP 2: Scrape each category
            print(f"\n📍 STEP 2: Scraping Categories...")
            
            for idx, category in enumerate(categories[:30], 1):  # Limit to 30 categories
                if len(self.scraped_pages) >= max_pages:
                    break
                
                print(f"\n   [{idx}/{min(30, len(categories))}] {category.get('name', 'Unknown')[:40]}")
                
                await self._scrape_category(session, category, max_pages)
                
                print(f"       Progress: {len(self.scraped_pages)}/{max_pages} pages")
        
        print(f"\n✅ Scraping completed!")
        print(f"   Total pages: {len(self.scraped_pages)}")
        
        return self.scraped_pages
    
    async def _get_categories(self, session, catalog_id: int) -> List[Dict]:
        """Get categories from API"""
        
        url = f"{self.base_api}/categories/catalog/{catalog_id}"
        
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    categories = data.get('categories', [])
                    
                    # Add catalog info as a page
                    if data.get('catalog'):
                        catalog_info = data['catalog']
                        self.scraped_pages.append({
                            'url': f"{self.base_url}/catalog/{catalog_id}",
                            'title': catalog_info.get('ro', {}).get('name', 'Dedeman Catalog'),
                            'content': json.dumps(catalog_info, ensure_ascii=False)
                        })
                    
                    return categories
        except Exception as e:
            print(f"   ⚠️ Error getting categories: {e}")
        
        return []
    
    async def _discover_categories(self, session) -> List[Dict]:
        """Discover categories from main API"""
        
        # Try different endpoints
        endpoints = [
            f"{self.base_api}/categories",
            f"{self.base_api}/menu",
            f"{self.base_api}/navigation"
        ]
        
        for endpoint in endpoints:
            try:
                async with session.get(endpoint, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Try to extract categories
                        if isinstance(data, dict):
                            if 'categories' in data:
                                return data['categories']
                            elif 'items' in data:
                                return data['items']
                        elif isinstance(data, list):
                            return data
            except:
                continue
        
        return []
    
    async def _scrape_category(self, session, category: Dict, max_pages: int):
        """Scrape a category"""
        
        if len(self.scraped_pages) >= max_pages:
            return
        
        category_id = category.get('id')
        category_name = category.get('name', 'Unknown')
        
        if not category_id:
            return
        
        # Add category page
        category_url = f"{self.base_url}/category/{category_id}"
        
        if category_url not in self.visited:
            self.visited.add(category_url)
            
            self.scraped_pages.append({
                'url': category_url,
                'title': f"Categorie: {category_name}",
                'content': json.dumps(category, ensure_ascii=False)
            })
        
        # Try to get products for this category
        await self._get_category_products(session, category_id, category_name, max_pages)
    
    async def _get_category_products(self, session, category_id: int, category_name: str, max_pages: int):
        """Get products from a category"""
        
        # Try different product endpoints
        product_endpoints = [
            f"{self.base_api}/products/category/{category_id}",
            f"{self.base_api}/catalog/products/{category_id}",
            f"https://www.dedeman.ro/ro/search?cat={category_id}",
        ]
        
        for endpoint in product_endpoints:
            if len(self.scraped_pages) >= max_pages:
                break
            
            try:
                async with session.get(endpoint, timeout=15) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        
                        if 'json' in content_type:
                            data = await response.json()
                            
                            # Try to extract products
                            products = self._extract_products_from_json(data)
                            
                            if products:
                                print(f"       Found {len(products)} products")
                                
                                for product in products[:20]:  # Max 20 per category
                                    if len(self.scraped_pages) >= max_pages:
                                        break
                                    
                                    await self._add_product_page(product)
                                
                                break  # Found products, stop trying endpoints
                        else:
                            # HTML response - could scrape but skip for now
                            pass
            
            except Exception as e:
                # Silent fail, try next endpoint
                pass
    
    def _extract_products_from_json(self, data: Dict) -> List[Dict]:
        """Extract products from JSON response"""
        
        products = []
        
        # Try various JSON structures
        if isinstance(data, dict):
            # Direct products array
            if 'products' in data:
                products = data['products']
            elif 'items' in data:
                products = data['items']
            elif 'results' in data:
                products = data['results']
            elif 'data' in data:
                if isinstance(data['data'], list):
                    products = data['data']
                elif isinstance(data['data'], dict) and 'products' in data['data']:
                    products = data['data']['products']
        elif isinstance(data, list):
            products = data
        
        return products if isinstance(products, list) else []
    
    async def _add_product_page(self, product: Dict):
        """Add product as a page"""
        
        product_id = product.get('id') or product.get('productId')
        product_name = product.get('name') or product.get('title', 'Product')
        
        if not product_id:
            return
        
        product_url = f"{self.base_url}/ro/product/{product_id}"
        
        if product_url not in self.visited:
            self.visited.add(product_url)
            
            # Build content from product data
            content_parts = [
                f"Produs: {product_name}",
                f"Descriere: {product.get('description', '')}",
                f"Preț: {product.get('price', '')} RON",
                f"Categorie: {product.get('category', '')}",
                f"Brand: {product.get('brand', '')}",
                f"Specificații: {json.dumps(product.get('specs', {}), ensure_ascii=False)}"
            ]
            
            content = "\n".join(filter(None, content_parts))
            
            self.scraped_pages.append({
                'url': product_url,
                'title': product_name,
                'content': content
            })


async def main():
    """CLI interface"""
    import sys
    
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    
    print("=" * 80)
    print("🎯 DEDEMAN API SCRAPER")
    print("=" * 80)
    print(f"Method: Direct API calls (fast & efficient)")
    print(f"Target: {max_pages} pages")
    print("")
    
    scraper = DedemanAPIScraper()
    pages = await scraper.scrape_dedeman(max_pages)
    
    print(f"\n{'='*80}")
    print(f"✅ COMPLETED!")
    print(f"   Pages scraped: {len(pages)}")
    print(f"{'='*80}")
    
    # Save to JSON
    output_file = '/tmp/dedeman_api_scraped.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_pages': len(pages),
            'pages': pages
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved to: {output_file}")
    
    # Show sample
    if pages:
        print(f"\n📄 Sample page:")
        sample = pages[0]
        print(f"   URL: {sample['url']}")
        print(f"   Title: {sample['title']}")
        print(f"   Content: {sample['content'][:200]}...")


if __name__ == "__main__":
    asyncio.run(main())

