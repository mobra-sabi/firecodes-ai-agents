#!/usr/bin/env python3
"""
Improved Crawler cu multiple strategii de fallback
Funcționează pe orice tip de site
"""

import asyncio
import logging
from urllib.parse import urlparse, urljoin
from typing import Dict, List, Optional, Tuple
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import requests
import re

logger = logging.getLogger(__name__)

class ImprovedCrawler:
    """
    Crawler robust cu multiple strategii de fallback
    """
    
    def __init__(self, max_pages: int = 50, timeout_per_page: int = 5):
        self.max_pages = max_pages
        self.timeout_per_page = timeout_per_page
        self.media_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
            '.pdf', '.zip', '.rar', '.mp4', '.avi', '.mp3', '.wav'
        ]
    
    def _is_valid_url(self, url: str, base_domain: str) -> bool:
        """Verifică dacă URL-ul e valid pentru crawling"""
        try:
            parsed = urlparse(url)
            
            # Verifică domeniul
            if parsed.netloc.replace('www.', '') != base_domain.replace('www.', ''):
                return False
            
            # Exclude media
            if any(url.lower().endswith(ext) for ext in self.media_extensions):
                return False
            
            # Exclude anchor links
            if '#' in parsed.path and not parsed.query:
                return False
            
            # Exclude common non-content paths
            excluded_patterns = [
                '/wp-admin/', '/wp-content/', '/wp-includes/',
                '/admin/', '/login', '/cart', '/checkout',
                '/account', '/my-account'
            ]
            if any(pattern in parsed.path.lower() for pattern in excluded_patterns):
                return False
            
            return True
        except:
            return False
    
    def _clean_text(self, html: str) -> str:
        """Extrage și curăță text din HTML"""
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Elimină scripturi, stiluri, etc.
            for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
                tag.decompose()
            
            # Extrage text
            text = soup.get_text(" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            
            return text
        except:
            return ""
    
    async def crawl_with_playwright(self, base_url: str, websocket=None) -> Dict:
        """
        Strategie 1: Playwright (pentru site-uri dinamice, SPA)
        """
        logger.info("🌐 Strategia 1: Playwright")
        
        pages_data = []
        visited = set()
        to_visit = {base_url}
        base_domain = urlparse(base_url).netloc
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                while to_visit and len(visited) < self.max_pages:
                    url = to_visit.pop()
                    
                    if url in visited:
                        continue
                    
                    visited.add(url)
                    
                    try:
                        # Încarcă pagina cu timeout scurt
                        response = await asyncio.to_thread(
                            page.goto,
                            url,
                            timeout=self.timeout_per_page * 1000,
                            wait_until='domcontentloaded'
                        )
                        
                        if response and response.status >= 400:
                            logger.warning(f"⚠️  HTTP {response.status}: {url}")
                            continue
                        
                        # Așteaptă un pic pentru JavaScript
                        await asyncio.to_thread(page.wait_for_timeout, 500)
                        
                        # Extrage conținut
                        html = await asyncio.to_thread(page.content)
                        text = self._clean_text(html)
                        
                        # Verificare: Text valid?
                        if len(text) < 100:
                            logger.debug(f"⏭️  Skip (text prea scurt): {url}")
                            continue
                        
                        pages_data.append({
                            'url': url,
                            'text': text,
                            'length': len(text)
                        })
                        
                        if websocket:
                            await websocket.send_json({
                                "status": "CRAWLER_STATUS",
                                "message": f"Scanat: {url} ({len(text)} caractere)"
                            })
                        
                        # Extrage link-uri
                        links = await asyncio.to_thread(
                            page.evaluate,
                            "Array.from(document.querySelectorAll('a')).map(a => a.href)"
                        )
                        
                        for link in links:
                            if self._is_valid_url(link, base_domain):
                                to_visit.add(link)
                        
                    except PlaywrightTimeout:
                        logger.warning(f"⏱️  Timeout: {url}")
                    except Exception as e:
                        logger.warning(f"❌ Eroare {url}: {e}")
                
                browser.close()
        
        except Exception as e:
            logger.error(f"❌ Playwright failed: {e}")
            raise
        
        return {
            'pages': pages_data,
            'total_pages': len(pages_data),
            'total_chars': sum(p['length'] for p in pages_data)
        }
    
    async def crawl_with_requests(self, base_url: str, websocket=None) -> Dict:
        """
        Strategie 2: Requests + BeautifulSoup (pentru site-uri statice)
        """
        logger.info("📄 Strategia 2: Requests + BeautifulSoup")
        
        pages_data = []
        visited = set()
        to_visit = {base_url}
        base_domain = urlparse(base_url).netloc
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        try:
            while to_visit and len(visited) < self.max_pages:
                url = to_visit.pop()
                
                if url in visited:
                    continue
                
                visited.add(url)
                
                try:
                    response = session.get(url, timeout=self.timeout_per_page)
                    
                    if response.status_code >= 400:
                        logger.warning(f"⚠️  HTTP {response.status_code}: {url}")
                        continue
                    
                    # Parse HTML
                    soup = BeautifulSoup(response.text, "html.parser")
                    text = self._clean_text(response.text)
                    
                    # Verificare: Text valid?
                    if len(text) < 100:
                        logger.debug(f"⏭️  Skip (text prea scurt): {url}")
                        continue
                    
                    pages_data.append({
                        'url': url,
                        'text': text,
                        'length': len(text)
                    })
                    
                    if websocket:
                        await websocket.send_json({
                            "status": "CRAWLER_STATUS",
                            "message": f"Scanat: {url} ({len(text)} caractere)"
                        })
                    
                    # Extrage link-uri
                    for link in soup.find_all('a', href=True):
                        full_url = urljoin(url, link['href'])
                        if self._is_valid_url(full_url, base_domain):
                            to_visit.add(full_url)
                
                except requests.Timeout:
                    logger.warning(f"⏱️  Timeout: {url}")
                except Exception as e:
                    logger.warning(f"❌ Eroare {url}: {e}")
        
        except Exception as e:
            logger.error(f"❌ Requests strategy failed: {e}")
            raise
        
        return {
            'pages': pages_data,
            'total_pages': len(pages_data),
            'total_chars': sum(p['length'] for p in pages_data)
        }
    
    async def smart_crawl(self, url: str, websocket=None) -> Dict:
        """
        Încearcă crawling cu fallback automat între strategii
        """
        logger.info(f"🚀 Începe smart crawling pentru: {url}")
        
        strategies = [
            ("Playwright", self.crawl_with_playwright),
            ("Requests", self.crawl_with_requests)
        ]
        
        last_error = None
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"🔄 Încerc strategia: {strategy_name}")
                result = await strategy_func(url, websocket)
                
                # Verificare: Avem suficient conținut?
                if result['total_pages'] >= 2 and result['total_chars'] >= 1000:
                    logger.info(f"✅ Succes cu {strategy_name}: {result['total_pages']} pagini, {result['total_chars']} caractere")
                    return result
                else:
                    logger.warning(f"⚠️  {strategy_name} a reușit parțial: doar {result['total_pages']} pagini")
                    
            except Exception as e:
                logger.warning(f"❌ {strategy_name} failed: {e}")
                last_error = e
                continue
        
        # Toate strategiile au eșuat
        raise ValueError(f"Toate strategiile de crawling au eșuat. Ultimă eroare: {last_error}")

# Funcție helper pentru folosire ușoară
async def improved_crawl_site(url: str, max_pages: int = 50, websocket=None) -> Dict:
    """
    Crawling inteligent cu fallback automat
    """
    crawler = ImprovedCrawler(max_pages=max_pages)
    return await crawler.smart_crawl(url, websocket)

