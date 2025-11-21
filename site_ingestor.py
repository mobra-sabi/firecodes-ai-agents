#!/usr/bin/env python3
"""
Site Ingestor - Percepție & Înțelegere Site
Implementează crawling, curățare, chunking și indexare semantică
"""

import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import urllib.robotparser as robotparser
import time
import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path

# Vector DB și embeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# MongoDB
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

@dataclass
class SitePage:
    """Reprezintă o pagină scraped din site"""
    url: str
    title: str
    content: str
    metadata: Dict
    timestamp: datetime
    chunk_id: Optional[str] = None

@dataclass
class SiteChunk:
    """Reprezintă un chunk de text pentru indexare"""
    content: str
    metadata: Dict
    embedding: Optional[List[float]] = None
    chunk_id: Optional[str] = None

class SiteIngestor:
    """Ingestor comprehensiv pentru site-uri web"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.visited_urls = set()
        self.site_pages = []
        self.chunks = []
        
        # Setup embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Setup text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.get('chunk_size', 1000),
            chunk_overlap=config.get('chunk_overlap', 200),
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""]
        )
        
        # Setup Qdrant
        self.qdrant_client = QdrantClient(
            host=config.get('qdrant_host', 'localhost'),
            port=config.get('qdrant_port', 9306)
        )
        
        # Setup MongoDB
        self.mongo_client = MongoClient(config.get('mongodb_uri', 'mongodb://localhost:9308'))
        self.db = self.mongo_client[config.get('mongodb_db', 'ai_agents_db')]
        
        # Session pentru requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.get('user_agent', 'Mozilla/5.0 (compatible; SiteAI/1.0)'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })
    
    async def ingest_site(self, site_url: str, agent_id: str) -> Dict:
        """
        Ingest complet al unui site web
        """
        logger.info(f"Starting site ingestion for {site_url}")
        
        try:
            # 1. Verifică robots.txt
            await self._check_robots_txt(site_url)
            
            # 2. Crawl site-ul
            await self._crawl_site(site_url)
            
            # 3. Procesează și curăță conținutul
            await self._process_content()
            
            # 4. Creează chunks
            await self._create_chunks()
            
            # 5. Generează embeddings
            await self._generate_embeddings()
            
            # 6. Indexează în Qdrant
            await self._index_in_qdrant(agent_id)
            
            # 7. Salvează în MongoDB
            await self._save_to_mongodb(agent_id)
            
            result = {
                'status': 'success',
                'pages_scraped': len(self.site_pages),
                'chunks_created': len(self.chunks),
                'total_content_length': sum(len(page.content) for page in self.site_pages),
                'agent_id': agent_id
            }
            
            logger.info(f"Site ingestion completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Site ingestion failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'agent_id': agent_id
            }
    
    async def _check_robots_txt(self, site_url: str):
        """Verifică robots.txt pentru a respecta regulile site-ului"""
        try:
            robots_url = urljoin(site_url, '/robots.txt')
            response = self.session.get(robots_url, timeout=10)
            
            if response.status_code == 200:
                rp = robotparser.RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                
                # Verifică dacă avem permisiunea să crawl
                if not rp.can_fetch('*', site_url):
                    logger.warning(f"Robots.txt blocks crawling for {site_url}")
                    # Continuă oricum, dar cu respect pentru rate limiting
                    
        except Exception as e:
            logger.warning(f"Could not check robots.txt: {e}")
    
    async def _crawl_site(self, site_url: str):
        """Crawl comprehensiv al site-ului"""
        base_domain = urlparse(site_url).netloc
        urls_to_visit = [site_url]
        max_pages = self.config.get('max_pages', int(os.getenv("MAX_CRAWL_PAGES", "200")))
        
        page_count = 0
        while urls_to_visit and page_count < max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in self.visited_urls:
                continue
                
            self.visited_urls.add(current_url)
            page_count += 1
            
            logger.info(f"Crawling page {page_count}/{max_pages}: {current_url}")
            
            try:
                # Rate limiting
                time.sleep(self.config.get('rate_limit', 1))
                
                response = self.session.get(current_url, timeout=30)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extrage informații
                page = await self._extract_page_info(soup, current_url)
                if page:
                    self.site_pages.append(page)
                
                # Găsește link-uri noi
                if page_count < max_pages:
                    new_urls = await self._find_internal_links(soup, current_url, base_domain)
                    urls_to_visit.extend(new_urls[:5])  # Limitează link-urile noi
                
            except Exception as e:
                logger.warning(f"Error crawling {current_url}: {e}")
                continue
    
    async def _extract_page_info(self, soup: BeautifulSoup, url: str) -> Optional[SitePage]:
        """Extrage informații dintr-o pagină HTML"""
        try:
            # Elimină elemente nedorite
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # Extrage titlul
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            # Extrage meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            
            # Extrage conținutul principal
            main_content = ""
            for selector in ['main', 'article', '.content', '.main-content', '.container', 'body']:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        text = element.get_text(separator=' ', strip=True)
                        if len(text) > len(main_content):
                            main_content = text
            
            # Curăță conținutul
            main_content = re.sub(r'\s+', ' ', main_content).strip()
            
            if len(main_content) < 100:  # Ignoră pagini cu prea puțin conținut
                return None
            
            # Extrage metadata
            metadata = {
                'title': title,
                'description': description,
                'url': url,
                'content_length': len(main_content),
                'language': self._detect_language(main_content),
                'extracted_at': datetime.now(timezone.utc).isoformat()
            }
            
            return SitePage(
                url=url,
                title=title,
                content=main_content,
                metadata=metadata,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.warning(f"Error extracting page info from {url}: {e}")
            return None
    
    async def _find_internal_links(self, soup: BeautifulSoup, current_url: str, base_domain: str) -> List[str]:
        """Găsește link-uri interne pentru crawling suplimentar"""
        internal_links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(current_url, href)
            
            # Verifică dacă e link intern
            if (urlparse(full_url).netloc == base_domain and 
                full_url not in self.visited_urls and
                '#' not in full_url.split('/')[-1] and
                not any(x in full_url for x in ['?', 'mailto:', 'tel:', '.pdf', '.doc', '.jpg', '.png'])):
                internal_links.append(full_url)
        
        return list(set(internal_links))  # Elimină duplicatele
    
    def _detect_language(self, text: str) -> str:
        """Detectează limba textului"""
        romanian_indicators = ['și', 'sau', 'pentru', 'prin', 'despre', 'este', 'sunt', 'cu', 'la', 'de']
        english_indicators = ['and', 'or', 'for', 'through', 'about', 'is', 'are', 'with', 'at', 'of']
        
        text_lower = text.lower()
        
        ro_count = sum(1 for word in romanian_indicators if word in text_lower)
        en_count = sum(1 for word in english_indicators if word in text_lower)
        
        return 'romanian' if ro_count > en_count else 'english' if en_count > ro_count else 'mixed'
    
    async def _process_content(self):
        """Procesează și curăță conținutul extras"""
        logger.info(f"Processing {len(self.site_pages)} pages")
        
        for page in self.site_pages:
            # Curăță conținutul
            page.content = self._clean_text(page.content)
            
            # Actualizează metadata
            page.metadata['processed_length'] = len(page.content)
            page.metadata['word_count'] = len(page.content.split())
    
    def _clean_text(self, text: str) -> str:
        """Curăță textul de elemente nedorite"""
        # Elimină caractere speciale
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', ' ', text)
        
        # Normalizează spațiile
        text = re.sub(r'\s+', ' ', text)
        
        # Elimină liniile goale
        text = re.sub(r'\n\s*\n', '\n', text)
        
        return text.strip()
    
    async def _create_chunks(self):
        """Creează chunks din conținutul paginilor"""
        logger.info("Creating chunks from content")
        
        for page in self.site_pages:
            # Creează chunks din conținutul paginii
            page_chunks = self.text_splitter.split_text(page.content)
            
            for i, chunk_text in enumerate(page_chunks):
                if len(chunk_text.strip()) < self.config.get('min_chunk_size', 100):
                    continue
                
                chunk_metadata = {
                    **page.metadata,
                    'chunk_index': i,
                    'total_chunks': len(page_chunks),
                    'chunk_length': len(chunk_text)
                }
                
                chunk = SiteChunk(
                    content=chunk_text,
                    metadata=chunk_metadata,
                    chunk_id=f"{page.url}_{i}"
                )
                
                self.chunks.append(chunk)
        
        logger.info(f"Created {len(self.chunks)} chunks")
    
    async def _generate_embeddings(self):
        """Generează embeddings pentru chunks"""
        logger.info(f"Generating embeddings for {len(self.chunks)} chunks")
        
        # Extrage textele pentru embedding
        texts = [chunk.content for chunk in self.chunks]
        
        # Generează embeddings în batch-uri
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.embeddings.embed_documents(batch_texts)
            
            # Asociază embeddings cu chunks
            for j, embedding in enumerate(batch_embeddings):
                chunk_index = i + j
                if chunk_index < len(self.chunks):
                    self.chunks[chunk_index].embedding = embedding
        
        logger.info("Embeddings generated successfully")
    
    async def _index_in_qdrant(self, agent_id: str):
        """Indexează chunks în Qdrant"""
        logger.info(f"Indexing {len(self.chunks)} chunks in Qdrant")
        
        collection_name = f"agent_{agent_id}_content"
        
        try:
            # Creează colecția dacă nu există
            collections = self.qdrant_client.get_collections()
            if collection_name not in [col.name for col in collections.collections]:
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=1024,  # Dimensiunea embedding-ului BGE
                        distance=Distance.COSINE
                    )
                )
            
            # Pregătește punctele pentru indexare
            points = []
            for i, chunk in enumerate(self.chunks):
                if chunk.embedding:
                    point = PointStruct(
                        id=i,
                        vector=chunk.embedding,
                        payload={
                            'content': chunk.content,
                            'metadata': chunk.metadata,
                            'chunk_id': chunk.chunk_id,
                            'agent_id': agent_id
                        }
                    )
                    points.append(point)
            
            # Indexează în batch-uri
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch_points = points[i:i + batch_size]
                self.qdrant_client.upsert(
                    collection_name=collection_name,
                    points=batch_points
                )
            
            logger.info(f"Successfully indexed {len(points)} chunks in Qdrant")
            
        except Exception as e:
            logger.error(f"Error indexing in Qdrant: {e}")
            raise
    
    async def _save_to_mongodb(self, agent_id: str):
        """Salvează datele în MongoDB"""
        logger.info("Saving data to MongoDB")
        
        try:
            # Salvează paginile
            pages_data = []
            for page in self.site_pages:
                page_data = {
                    'agent_id': ObjectId(agent_id),
                    'url': page.url,
                    'title': page.title,
                    'content': page.content,
                    'metadata': page.metadata,
                    'timestamp': page.timestamp,
                    'source': 'site_ingestor'
                }
                pages_data.append(page_data)
            
            if pages_data:
                self.db.site_content.insert_many(pages_data)
            
            # Salvează chunks
            chunks_data = []
            for chunk in self.chunks:
                chunk_data = {
                    'agent_id': ObjectId(agent_id),
                    'content': chunk.content,
                    'metadata': chunk.metadata,
                    'chunk_id': chunk.chunk_id,
                    'embedding': chunk.embedding,
                    'timestamp': datetime.now(timezone.utc),
                    'source': 'site_ingestor'
                }
                chunks_data.append(chunk_data)
            
            if chunks_data:
                self.db.site_chunks.insert_many(chunks_data)
            
            logger.info(f"Saved {len(pages_data)} pages and {len(chunks_data)} chunks to MongoDB")
            
        except Exception as e:
            logger.error(f"Error saving to MongoDB: {e}")
            raise

# Funcție helper pentru a rula ingest
async def run_site_ingest(site_url: str, agent_id: str, config: Dict = None) -> Dict:
    """Funcție helper pentru a rula ingest-ul unui site"""
    if config is None:
        config = {
            'max_pages': 20,
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'rate_limit': 1,
            'user_agent': 'Mozilla/5.0 (compatible; SiteAI/1.0)',
            'qdrant_url': 'http://localhost:9306',
            'mongodb_uri': 'mongodb://localhost:9308',
            'mongodb_db': 'ai_agents_db'
        }
    
    ingestor = SiteIngestor(config)
    return await ingestor.ingest_site(site_url, agent_id)

if __name__ == "__main__":
    # Test
    import asyncio
    
    async def test():
        result = await run_site_ingest("https://www.dedeman.ro/", "test_agent_123")
        print(json.dumps(result, indent=2))
    
    asyncio.run(test())



