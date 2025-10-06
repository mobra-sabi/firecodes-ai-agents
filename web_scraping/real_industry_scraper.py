#!/usr/bin/env python3
import asyncio
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from database.mongodb_handler import MongoDBHandler
import re
from urllib.parse import urljoin, urlparse
import random

class RealIndustryScraper:
    def __init__(self):
        self.mongodb = MongoDBHandler()
        self.scraped_sites = []
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        self.industry_strategies = {
            'fire_protection': {
                'target_sites': [
                    'firestopping.ro',
                    'tehnica-antifoc.ro',
                    'stingatori.ro'
                ],
                'keywords': ['protecție', 'incendiu', 'stingător', 'siguranță', 'foc']
            },
            'medical': {
                'target_sites': [
                    'sanador.ro',
                    'regina-maria.ro',
                    'medlife.ro'
                ],
                'keywords': ['medical', 'sănătate', 'doctor', 'clinică', 'tratament']
            },
            'construction': {
                'target_sites': [
                    'leroy-merlin.ro',
                    'dedeman.ro',
                    'hornbach.ro'
                ],
                'keywords': ['construcție', 'material', 'proiect', 'amenajare']
            },
            'technology': {
                'target_sites': [
                    'zitec.com',
                    'evozon.com',
                    'softvision.com'
                ],
                'keywords': ['software', 'dezvoltare', 'tehnologie', 'digital']
            }
        }
        
    async def scrape_industry_complete(self, industry: str) -> Dict:
        if industry not in self.industry_strategies:
            return {'error': f'Industria {industry} nu este configurată'}
            
        print(f"🔍 SCRAPING REAL INDUSTRY: {industry.upper()}")
        print("=" * 50)
        
        strategy = self.industry_strategies[industry]
        scraped_data = {
            'industry': industry,
            'start_time': datetime.now().isoformat(),
            'sites_scraped': [],
            'successful_scrapes': 0,
            'failed_scrapes': 0
        }
        
        for site in strategy['target_sites']:
            site_url = f"https://{site}" if not site.startswith('http') else site
            
            try:
                site_data = await self.scrape_single_site(site_url, strategy)
                if site_data:
                    scraped_data['sites_scraped'].append(site_data)
                    scraped_data['successful_scrapes'] += 1
                    
                    self.save_site_data_to_db(site_data)
                    
                    print(f"✅ {site} - {len(site_data.get('content', ''))} caractere")
                else:
                    scraped_data['failed_scrapes'] += 1
                    print(f"❌ {site} - eșuat")
                    
                await asyncio.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"❌ {site} - eroare: {str(e)[:50]}...")
                scraped_data['failed_scrapes'] += 1
                
        return scraped_data
        
    async def scrape_single_site(self, url: str, strategy: Dict) -> Optional[Dict]:
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title = soup.find('title')
            title_text = title.get_text().strip() if title else 'No title'
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            
            main_content = self.extract_main_content(soup)
            industry_keywords = self.extract_industry_keywords(main_content, strategy)
            
            site_data = {
                'url': url,
                'title': title_text,
                'description': description,
                'content': main_content,
                'industry_keywords': industry_keywords,
                'scrape_timestamp': datetime.now().isoformat(),
                'content_length': len(main_content),
                'language': self.detect_language(main_content)
            }
            
            return site_data
            
        except Exception as e:
            print(f"Eroare scraping {url}: {e}")
            return None
            
    def extract_main_content(self, soup: BeautifulSoup) -> str:
        for script in soup(['script', 'style', 'nav', 'header', 'footer']):
            script.decompose()
            
        main_selectors = ['main', 'article', '.content', '.main-content', '.container']
        
        main_content = ''
        for selector in main_selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    text = element.get_text()
                    if len(text) > len(main_content):
                        main_content = text
                        
        if len(main_content) < 500:
            body = soup.find('body')
            if body:
                main_content = body.get_text()
                
        main_content = re.sub(r'\s+', ' ', main_content).strip()
        return main_content[:8000]
        
    def extract_industry_keywords(self, content: str, strategy: Dict) -> List[Dict]:
        content_lower = content.lower()
        found_keywords = []
        
        for keyword in strategy.get('keywords', []):
            if keyword in content_lower:
                frequency = content_lower.count(keyword)
                if frequency > 0:
                    found_keywords.append({'keyword': keyword, 'frequency': frequency})
                    
        found_keywords.sort(key=lambda x: x['frequency'], reverse=True)
        return found_keywords[:10]
        
    def detect_language(self, content: str) -> str:
        romanian_indicators = ['și', 'sau', 'pentru', 'prin', 'despre', 'este']
        english_indicators = ['and', 'or', 'for', 'through', 'about', 'is']
        
        content_lower = content.lower()
        
        ro_count = sum(1 for word in romanian_indicators if word in content_lower)
        en_count = sum(1 for word in english_indicators if word in content_lower)
        
        return 'romanian' if ro_count > en_count else 'english' if en_count > ro_count else 'mixed'
            
    def save_site_data_to_db(self, site_data: Dict):
        try:
            db_data = {
                'url': site_data['url'],
                'title': site_data['title'],
                'description': site_data['description'],
                'content': site_data['content'],
                'industry_keywords': site_data.get('industry_keywords', []),
                'scrape_timestamp': site_data['scrape_timestamp'],
                'content_length': site_data['content_length'],
                'language': site_data.get('language', 'unknown'),
                'scraped_by': 'real_industry_scraper'
            }
            
            success = self.mongodb.save_site_content(db_data)
            
            if success:
                self.scraped_sites.append(site_data['url'])
                
        except Exception as e:
            print(f"Eroare salvare în DB: {e}")

async def main():
    scraper = RealIndustryScraper()
    
    print("🕷️ REAL INDUSTRY WEB SCRAPER")
    print("=" * 40)
    
    industries = list(scraper.industry_strategies.keys())
    
    print("\n📋 Industrii disponibile:")
    for i, industry in enumerate(industries, 1):
        print(f"  {i}. {industry.replace('_', ' ').title()}")
        
    choice = input(f"\nAlege industria (1-{len(industries)}): ").strip()
    
    try:
        choice_num = int(choice)
        
        if 1 <= choice_num <= len(industries):
            selected_industry = industries[choice_num - 1]
            
            print(f"\n🚀 Pornesc scraping pentru {selected_industry}...")
            result = await scraper.scrape_industry_complete(selected_industry)
            
            print(f"\n📊 REZULTATE SCRAPING {selected_industry.upper()}:")
            print("=" * 50)
            print(f"✅ Site-uri scrapate cu succes: {result.get('successful_scrapes', 0)}")
            print(f"❌ Site-uri eșuate: {result.get('failed_scrapes', 0)}")
            
            for site_data in result.get('sites_scraped', []):
                print(f"\n📄 {site_data['url']}:")
                print(f"   📝 Titlu: {site_data['title'][:80]}...")
                print(f"   📊 Conținut: {site_data['content_length']} caractere")
                print(f"   🌐 Limba: {site_data['language']}")
                
                keywords = site_data.get('industry_keywords', [])
                if keywords:
                    top_keywords = [kw['keyword'] for kw in keywords[:3]]
                    print(f"   🔑 Keywords: {', '.join(top_keywords)}")
                    
        else:
            print("❌ Opțiune invalidă")
            
    except ValueError:
        print("❌ Te rog introdu un număr valid")
    except Exception as e:
        print(f"❌ Eroare: {e}")

if __name__ == "__main__":
    asyncio.run(main())
