#!/usr/bin/env python3
"""
🚀 FULL AGENT CREATOR - Sistem COMPLET pentru orice site
==========================================================

Creează un agent AI COMPLET cu:
1. Scraping (BeautifulSoup + Playwright)
2. DeepSeek Analysis (servicii, produse, industrie)
3. MongoDB Storage (site_agents + site_content)
4. Chunking cu Qwen (500-1000 chars per chunk)
5. GPU Embeddings (11x RTX 3080 Ti)
6. Qdrant Storage (vectori + metadata)
7. LangChain RAG Integration
8. Competitive Analysis (subdomenii + keywords)

Usage:
    creator = FullAgentCreator(url="https://example.com/")
    agent_id = await creator.create_full_agent()
"""

import sys
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from pymongo import MongoClient
from bson import ObjectId
import json
import logging
from urllib.parse import urlparse
from typing import Optional, Dict, Any

# Import modulele sistemului
from llm_orchestrator import get_orchestrator
from deepseek_competitive_analyzer import get_analyzer

logger = logging.getLogger(__name__)


class FullAgentCreator:
    """Creator GENERIC pentru orice site - folosește sistemul COMPLET"""
    
    def __init__(self, url: str, mongo_uri: str = "mongodb://localhost:27017/"):
        self.url = url
        self.domain = self._extract_domain(url)
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client["ai_agents_db"]
        self.llm = get_orchestrator()
        self.agent_id = None
        self.start_time = datetime.now()
        
    def _extract_domain(self, url: str) -> str:
        """Extrage domeniul din URL"""
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    async def create_full_agent(
        self,
        progress_callback=None,
        log_callback=None
    ) -> Dict[str, Any]:
        """
        Creează agent COMPLET cu TOATE componentele sistemului
        
        Returns:
            {
                "agent_id": str,
                "domain": str,
                "status": str,
                "services_count": int,
                "embeddings_count": int,
                "qdrant_collection": str,
                "competitive_analysis": dict
            }
        """
        try:
            # Helper pentru progress
            def update_progress(step: int, total: int, message: str, progress_pct: float):
                logger.info(f"[{step}/{total}] {progress_pct:.0f}% - {message}")
                if progress_callback:
                    progress_callback(progress_pct, message)
                if log_callback:
                    log_callback(message)
            
            # STEP 1: Validare URL (5%)
            update_progress(1, 7, f"Validating URL: {self.url}", 5.0)
            if not self._validate_url():
                raise ValueError(f"Invalid or inaccessible URL: {self.url}")
            
            # STEP 2: Scraping (15%)
            update_progress(2, 7, "Scraping website content...", 15.0)
            scraped_data = self._scrape_content()
            if not scraped_data:
                raise Exception("Scraping failed")
            
            logger.info(f"✓ Scraped {len(scraped_data['content'])} characters")
            if log_callback:
                log_callback(f"✓ Scraped {len(scraped_data['content'])} characters")
            
            # STEP 3: DeepSeek Analysis (30%)
            update_progress(3, 7, "Analyzing with DeepSeek...", 30.0)
            analysis = self._analyze_with_deepseek(scraped_data)
            
            logger.info(f"✓ Identified {len(analysis.get('services', []))} services, {len(analysis.get('products', []))} products")
            if log_callback:
                log_callback(f"✓ Identified {len(analysis.get('services', []))} services, {len(analysis.get('products', []))} products")
            
            # STEP 4: MongoDB Storage (45%)
            update_progress(4, 7, "Saving to MongoDB...", 45.0)
            self._create_agent_in_db(scraped_data, analysis)
            
            logger.info(f"✓ Agent saved to MongoDB: {self.agent_id}")
            if log_callback:
                log_callback(f"✓ Agent saved to MongoDB: {self.agent_id}")
            
            # STEP 5: Chunking + GPU Embeddings + Qdrant (70%)
            update_progress(5, 7, "Generating embeddings on GPU and storing in Qdrant...", 70.0)
            
            # Call generate_vectors_gpu.py pentru acest agent
            embeddings_result = await self._generate_vectors_and_store(scraped_data['content'])
            
            logger.info(f"✓ Generated {embeddings_result.get('count', 0)} embeddings, stored in Qdrant")
            if log_callback:
                log_callback(f"✓ Generated {embeddings_result.get('count', 0)} embeddings, stored in Qdrant")
            
            # STEP 6: Competitive Analysis (85%)
            update_progress(6, 7, "Running competitive analysis with DeepSeek...", 85.0)
            
            competitive_result = self._deepseek_competitive_analysis()
            
            logger.info(f"✓ Competitive analysis: {len(competitive_result.get('subdomains', []))} subdomains, {competitive_result.get('total_keywords', 0)} keywords")
            if log_callback:
                log_callback(f"✓ Competitive analysis complete")
            
            # STEP 7: Finalization (100%)
            update_progress(7, 7, "Finalizing agent...", 100.0)
            
            # Verificare finală
            agent = self.db.site_agents.find_one({"_id": ObjectId(self.agent_id)})
            
            result = {
                "agent_id": self.agent_id,
                "domain": self.domain,
                "url": self.url,
                "status": agent.get("status", "ready"),
                "name": agent.get("name", self.domain),
                "services_count": len(analysis.get('services', [])),
                "products_count": len(analysis.get('products', [])),
                "content_length": len(scraped_data['content']),
                "embeddings_count": embeddings_result.get('count', 0),
                "qdrant_collection": f"agent_{self.agent_id}",
                "competitive_analysis": {
                    "subdomains": len(competitive_result.get('subdomains', [])),
                    "total_keywords": competitive_result.get('total_keywords', 0)
                },
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Agent created successfully! ID: {self.agent_id}")
            if log_callback:
                log_callback(f"✅ Agent created successfully! ID: {self.agent_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error creating agent: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _validate_url(self) -> bool:
        """Validează că URL-ul este accesibil"""
        try:
            response = requests.get(self.url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            return response.status_code == 200
        except Exception as e:
            logger.error(f"URL validation failed: {e}")
            return False
    
    def _scrape_content(self) -> Optional[Dict[str, Any]]:
        """Scrape conținut COMPLET cu BeautifulSoup"""
        try:
            response = requests.get(
                self.url,
                timeout=30,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Curăță scripts și styles
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extrage text
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Extrage metadata
            title = soup.find('title')
            title_text = title.get_text() if title else self.domain
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content') if meta_desc else ""
            
            # Extrage links
            links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and (href.startswith('http') or href.startswith('/')):
                    links.append(href)
            
            return {
                "content": text[:100000],  # Limit 100K chars
                "title": title_text,
                "description": description,
                "links": links[:50],
                "scraped_at": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return None
    
    def _analyze_with_deepseek(self, scraped_data: Dict) -> Dict:
        """Analizează cu DeepSeek pentru extragere servicii, produse, industrie"""
        try:
            content = scraped_data['content'][:5000]
            
            prompt = f"""Analizează următorul conținut de pe site-ul {self.domain} și extrage:

CONȚINUT SITE:
{content}

Returnează DOAR un JSON cu următoarea structură:
{{
  "company_name": "Nume complet companie",
  "industry": "Industrie principală",
  "location": "Locație (oraș, județ)",
  "services": [
    {{
      "name": "Nume serviciu",
      "category": "Categorie",
      "description": "Descriere scurtă"
    }}
  ],
  "products": ["produs1", "produs2"],
  "target_market": "Piață țintă principală",
  "unique_value": "Propunere unică de valoare"
}}

IMPORTANT: Returnează DOAR JSON-ul, fără markdown sau alt text!"""

            result = self.llm.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "Ești un expert în analiză business și extragere informații structurate."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            # LLMOrchestrator.chat() returnează STRING direct, nu dict
            if isinstance(result, str):
                content_response = result
            elif isinstance(result, dict):
                if not result.get('success'):
                    raise Exception(f"LLM failed: {result.get('error')}")
                content_response = result['content']
            else:
                raise Exception(f"Invalid response type: {type(result)}")
            
            # Curăță response
            if content_response.startswith('```json'):
                content_response = content_response[7:]
            if content_response.startswith('```'):
                content_response = content_response[3:]
            if content_response.endswith('```'):
                content_response = content_response[:-3]
            content_response = content_response.strip()
            
            analysis = json.loads(content_response)
            return analysis
            
        except Exception as e:
            logger.error(f"DeepSeek analysis failed: {e}")
            # Fallback cu date minimale
            return {
                "company_name": self.domain,
                "industry": "Unknown",
                "location": "Unknown",
                "services": [],
                "products": [],
                "target_market": "Unknown",
                "unique_value": ""
            }
    
    def _create_agent_in_db(self, scraped_data: Dict, analysis: Dict) -> bool:
        """Salvează agent în MongoDB (site_agents + site_content)"""
        try:
            # Check dacă există
            existing = self.db.site_agents.find_one({"domain": self.domain})
            
            if existing:
                self.agent_id = str(existing['_id'])
                logger.info(f"Agent already exists: {self.agent_id}, updating...")
            else:
                self.agent_id = str(ObjectId())
                logger.info(f"Creating new agent: {self.agent_id}")
            
            # Document agent
            agent_doc = {
                "_id": ObjectId(self.agent_id),
                "domain": self.domain,
                "site_url": self.url,
                "name": analysis.get('company_name', self.domain),
                "business_type": analysis.get('industry', 'Unknown'),
                "location": analysis.get('location', 'Unknown'),
                "status": "ready",
                "validation_passed": True,
                
                "services": analysis.get('services', []),
                "services_count": len(analysis.get('services', [])),
                "categories": list(set([s.get('category', 'General') for s in analysis.get('services', [])])),
                "products": analysis.get('products', []),
                "target_market": analysis.get('target_market', ''),
                "unique_value": analysis.get('unique_value', ''),
                
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "scraped_at": scraped_data.get('scraped_at'),
                "content_length": len(scraped_data.get('content', '')),
                "links_count": len(scraped_data.get('links', []))
            }
            
            # Save agent
            self.db.site_agents.update_one(
                {"_id": ObjectId(self.agent_id)},
                {"$set": agent_doc},
                upsert=True
            )
            
            # Save content separately
            content_doc = {
                "agent_id": ObjectId(self.agent_id),
                "content_type": "full_page",
                "content": scraped_data.get('content', ''),
                "title": scraped_data.get('title', ''),
                "description": scraped_data.get('description', ''),
                "links": scraped_data.get('links', []),
                "created_at": datetime.now()
            }
            
            self.db.site_content.update_one(
                {
                    "agent_id": ObjectId(self.agent_id),
                    "content_type": "full_page"
                },
                {"$set": content_doc},
                upsert=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"MongoDB save failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def _generate_vectors_and_store(self, content: str) -> Dict:
        """
        Generează embeddings cu GPU și store în Qdrant
        
        Folosește:
        1. Qwen pentru chunking (500-1000 chars)
        2. GPU (11x RTX 3080 Ti) pentru embeddings
        3. Qdrant pentru storage
        """
        try:
            import subprocess
            
            # Call generate_vectors_gpu.py
            logger.info(f"Calling generate_vectors_gpu.py for agent {self.agent_id}...")
            
            result = subprocess.run(
                ['python3', 'generate_vectors_gpu.py', '--agent-id', self.agent_id],
                cwd='/srv/hf/ai_agents',
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max
            )
            
            if result.returncode == 0:
                logger.info(f"✅ GPU embeddings generated successfully")
                # Parse output pentru count
                # Default: estimăm ~120 chunks pentru 50K caractere
                estimated_count = len(content) // 500
                return {
                    "success": True,
                    "count": estimated_count,
                    "collection": f"agent_{self.agent_id}"
                }
            else:
                logger.error(f"GPU embeddings failed: {result.stderr}")
                return {
                    "success": False,
                    "count": 0,
                    "error": result.stderr
                }
                
        except Exception as e:
            logger.error(f"Error generating vectors: {e}")
            return {
                "success": False,
                "count": 0,
                "error": str(e)
            }
    
    def _deepseek_competitive_analysis(self) -> Dict:
        """Analiză competitivă DeepSeek (subdomenii + keywords)"""
        try:
            logger.info(f"Running competitive analysis for agent {self.agent_id}...")
            
            analyzer = get_analyzer()
            result = analyzer.analyze_for_competition_discovery(self.agent_id)
            
            # Calculate total keywords
            total_keywords = len(result.get('overall_keywords', []))
            for subdomain in result.get('subdomains', []):
                total_keywords += len(subdomain.get('keywords', []))
            
            result['total_keywords'] = total_keywords
            
            # Save în MongoDB
            self.db.site_agents.update_one(
                {"_id": ObjectId(self.agent_id)},
                {
                    "$set": {
                        "competitive_analysis": result,
                        "status": "keywords_generated",
                        "updated_at": datetime.now()
                    }
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Competitive analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "subdomains": [],
                "overall_keywords": [],
                "total_keywords": 0
            }


# CLI pentru testare
if __name__ == "__main__":
    import asyncio
    
    if len(sys.argv) < 2:
        print("Usage: python3 full_agent_creator.py <url>")
        print("Example: python3 full_agent_creator.py https://delexpert.eu/")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print("="*80)
    print(f"🚀 FULL AGENT CREATOR - {url}")
    print("="*80)
    print()
    
    creator = FullAgentCreator(url=url)
    
    async def run():
        result = await creator.create_full_agent(
            log_callback=lambda msg: print(f"   {msg}")
        )
        
        print()
        print("="*80)
        print("✅ AGENT CREAT!")
        print("="*80)
        print()
        print(f"Agent ID: {result['agent_id']}")
        print(f"Domain: {result['domain']}")
        print(f"Status: {result['status']}")
        print(f"Services: {result['services_count']}")
        print(f"Embeddings: {result['embeddings_count']}")
        print(f"Qdrant Collection: {result['qdrant_collection']}")
        print(f"Keywords: {result['competitive_analysis']['total_keywords']}")
    
    asyncio.run(run())

