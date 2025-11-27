import asyncio
import logging
import os
import gzip
import json
import time
import tldextract
from datetime import datetime, timezone
from pymongo import MongoClient, UpdateOne
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

# Import local
import ro_crawler_config as config
from adapters.hybrid_scraper import get_hybrid_scraper
from adapters.lambda_scraper import LambdaScraper

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/srv/hf/ro_index/logs/crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("EternalCrawler")

class EternalCrawler:
    def __init__(self):
        self.mongo = MongoClient(config.MONGO_URI)
        self.db = self.mongo[config.DB_NAME]
        self.queue = self.db[config.COLLECTION_QUEUE]
        self.sites = self.db[config.COLLECTION_SITES]
        
        # Select Scraper Strategy
        if getattr(config, 'USE_AWS_LAMBDA', False):
            logger.info("🌩️ POWER UP: Using AWS Lambda Swarm for scraping!")
            self.scraper = LambdaScraper()
            self.is_lambda = True
        else:
            logger.info("🐌 Using Local Scraper")
            self.scraper = get_hybrid_scraper()
            self.is_lambda = False
        
        # Cache pentru numărătoare
        self.domain_counts = {}
        self._last_cache_cleanup = time.time()
        
        # Asigură indexuri
        self.queue.create_index("url", unique=True)
        self.queue.create_index("status")
        self.queue.create_index("priority")
        
        self.check_seed()

    def check_seed(self):
        """Dacă coada e goală, adaugă semințe"""
        if self.queue.count_documents({}) == 0:
            logger.info("🌱 Coada e goală. Seeding initial...")
            seeds = [
                "https://www.listafirme.ro", "https://www.emag.ro", "https://www.dedeman.ro",
                "https://www.hotnews.ro", "https://www.digi24.ro", "https://www.bizoo.ro",
                "https://www.paginiaurii.ro", "https://www.olx.ro", "https://www.autovit.ro",
                "https://www.romania-insider.com", "https://cursdeguvernare.ro",
                "https://www.constructii-romania.ro", "https://www.bricodepot.ro",
                "https://www.hornbach.ro", "https://www.leroymerlin.ro"
            ]
            self.add_to_queue(seeds, priority=100)

    def add_to_queue(self, urls, priority=10, source_url=None):
        """Adaugă URL-uri în coadă (bulk)"""
        ops = []
        for url in urls:
            if not url.startswith('http'): continue
            ext = tldextract.extract(url)
            domain_full = f"{ext.domain}.{ext.suffix}"
            
            if f".{ext.suffix}" not in config.ALLOWED_TLDS and ext.suffix != 'ro':
                continue
            if domain_full in config.BLOCKED_DOMAINS:
                continue

            ops.append(UpdateOne(
                {"url": url},
                {"$setOnInsert": {
                    "url": url,
                    "domain": domain_full,
                    "status": "pending",
                    "priority": priority,
                    "source": source_url,
                    "added_at": datetime.now(timezone.utc),
                    "attempts": 0
                }},
                upsert=True
            ))
        
        if ops:
            try:
                result = self.queue.bulk_write(ops, ordered=False)
                if result.upserted_count > 0:
                    logger.info(f"➕ Added {result.upserted_count} new URLs to queue from {source_url}")
            except Exception as e:
                logger.error(f"Error adding to queue: {e}")

    async def process_url(self, url_doc):
        """Procesează un singur URL"""
        url = url_doc['url']
        domain = url_doc.get('domain')
        
        # Cleanup cache periodic
        if time.time() - self._last_cache_cleanup > 3600:
            self.domain_counts = {}
            self._last_cache_cleanup = time.time()
            
        # Verifică limita de pagini per domeniu
        if domain not in self.domain_counts:
            count = self.sites.count_documents({"domain": domain})
            self.domain_counts[domain] = count
            
        if self.domain_counts.get(domain, 0) >= config.MAX_PAGES_PER_DOMAIN:
            logger.info(f"⏭️ Skipping {url} (Domain limit reached: {self.domain_counts.get(domain, 0)})")
            self.queue.update_one(
                {"_id": url_doc['_id']},
                {"$set": {"status": "completed", "reason": "limit_reached", "completed_at": datetime.now(timezone.utc)}}
            )
            return False
        
        logger.info(f"🕷️ Crawling: {url}")
        
        try:
            # 1. Fetch (Lambda or Local)
            content = await self.scraper.fetch_page(url)
            
            if not content or len(content) < 500:
                raise Exception("Empty or too short content")
            
            # 2. Parse & Extract Links
            soup = BeautifulSoup(content, 'html.parser')
            title = soup.title.string.strip() if soup.title else "No Title"
            
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                parsed = urlparse(full_url)
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if len(clean_url) > 10:
                    links.add(clean_url)
            
            # 3. Save Raw Data (Compressed)
            filename = f"{config.STORAGE_PATH}/{domain}_{int(time.time())}.html.gz"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with gzip.open(filename, 'wt', encoding='utf-8') as f:
                f.write(content)
            
            # 4. Update DB
            self.sites.update_one(
                {"url": url},
                {"$set": {
                    "domain": domain,
                    "title": title,
                    "storage_path": filename,
                    "scraped_at": datetime.now(timezone.utc),
                    "outbound_links_count": len(links),
                    "content_length": len(content)
                }},
                upsert=True
            )
            
            self.domain_counts[domain] = self.domain_counts.get(domain, 0) + 1
            
            self.queue.update_one(
                {"_id": url_doc['_id']},
                {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc)}}
            )
            
            new_priority = max(1, url_doc.get('priority', 10) - 1)
            self.add_to_queue(list(links), priority=new_priority, source_url=url)
            
            return True
            
        except Exception as e:
            logger.warning(f"❌ Failed {url}: {e}")
            self.queue.update_one(
                {"_id": url_doc['_id']},
                {
                    "$set": {"status": "failed", "last_error": str(e)},
                    "$inc": {"attempts": 1}
                }
            )
            return False

    async def worker(self, worker_id):
        """Bucla infinită a unui worker"""
        logger.info(f"👷 Worker {worker_id} started")
        
        while True:
            job = self.queue.find_one_and_update(
                {
                    "status": "pending", 
                    "attempts": {"$lt": 3}
                },
                {"$set": {"status": "processing", "worker": worker_id, "started_at": datetime.now(timezone.utc)}},
                sort=[("priority", -1)],
                return_document=True
            )
            
            if not job:
                logger.info(f"💤 Worker {worker_id} sleeping (no jobs)...")
                await asyncio.sleep(5)
                continue
                
            await self.process_url(job)
            # La Lambda nu avem nevoie de delay, dar punem 0.1s ca să nu explodăm logurile
            await asyncio.sleep(0.1)

    async def run(self):
        """Lansează flota de workeri"""
        logger.info(f"🚀 Starting Eternal Crawler with {config.CONCURRENT_WORKERS} workers (Lambda Mode: {getattr(config, 'USE_AWS_LAMBDA', False)})")
        
        tasks = []
        for i in range(config.CONCURRENT_WORKERS):
            tasks.append(self.worker(i))
            
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    crawler = EternalCrawler()
    try:
        asyncio.run(crawler.run())
    except KeyboardInterrupt:
        logger.info("🛑 Crawler stopped by user")
