import asyncio
import logging
import random
from fake_useragent import UserAgent
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import os

logger = logging.getLogger(__name__)

# API-ul vechi pentru fallback
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "820779501af9bd24225220463179d59b")

class HybridScraper:
    def __init__(self):
        self.ua = UserAgent()
        
    async def fetch_page(self, url: str, use_cache: bool = True) -> str:
        """
        Smart Fetch: Try Local (Free) -> Fallback to API (Paid)
        """
        # 1. Încearcă Local cu Playwright
        try:
            logger.info(f"🕵️ HybridScraper: Trying LOCAL fetch for {url}")
            content = await self._fetch_local(url)
            if content and len(content) > 500:
                logger.info(f"✅ LOCAL fetch success! Saved API credit.")
                return content
            else:
                logger.warning(f"⚠️ Local content too short/empty. Switching to API.")
        except Exception as e:
            logger.warning(f"⚠️ Local fetch failed ({str(e)}). Switching to API.")

        # 2. Fallback la ScraperAPI
        return await self._fetch_api(url)

    async def _fetch_local(self, url: str) -> str:
        async with async_playwright() as p:
            # Lansăm browser "Stealth"
            browser = await p.chromium.launch(headless=True)
            
            # Context cu User-Agent real
            context = await browser.new_context(
                user_agent=self.ua.random,
                viewport={'width': 1920, 'height': 1080},
                java_script_enabled=True
            )
            
            page = await context.new_page()
            
            try:
                # Navigare cu timeout 30s
                response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                
                # Verificăm status code
                if response.status in [403, 429, 503]:
                    raise Exception(f"Blocked by server (Status {response.status})")
                
                # Așteptăm puțin să se încarce JS dynamic (dacă e cazul)
                await page.wait_for_timeout(2000)
                
                # Extragem conținut
                content = await page.content()
                
                # Curățăm resurse
                await browser.close()
                
                return content
                
            except Exception as e:
                await browser.close()
                raise e

    async def _fetch_api(self, url: str) -> str:
        """Fallback la ScraperAPI"""
        logger.info(f"💸 HybridScraper: Using API for {url}")
        import requests
        
        payload = {
            'api_key': SCRAPER_API_KEY, 
            'url': url, 
            'render': 'true' # Necesită JS rendering
        }
        
        try:
            # Folosim requests sincorn într-un executor asincron
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.get('http://api.scraperapi.com', params=payload, timeout=60))
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"❌ API fetch failed: {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"❌ API fetch error: {e}")
            return ""

# Singleton
_scraper = None
def get_hybrid_scraper():
    global _scraper
    if _scraper is None:
        _scraper = HybridScraper()
    return _scraper

