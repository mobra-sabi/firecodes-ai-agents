#!/usr/bin/env python3
"""
FULL SLAVE AGENT CREATOR - Creează AGENTI AI COMPLETI pentru competitori
===========================================================================

PROCES COMPLET (ca și pentru master agents):
1. Scraping website (BeautifulSoup + Playwright)
2. Chunking (500-1000 caractere)
3. GPU Embeddings (all-MiniLM-L6-v2 pe 11x RTX 3080 Ti)
4. Vector storage în Qdrant
5. MongoDB storage complet
6. LangChain integration
7. Qwen local învață din proces

ORCHESTRAT DE:
- DeepSeek: Analiza și decizie
- Qwen Local: Learning continuu + chunk optimization
"""

import logging
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
from typing import Dict, List, Optional
from bson import ObjectId
import hashlib
import time
import sys
import os
from dotenv import load_dotenv

# Force reload environment
load_dotenv(override=True)

# Import modules necesare
try:
    from scraper import scrape_website
    from chunker import chunk_text
    from embeddings_generator import generate_embeddings_gpu
    from qdrant_storage import store_vectors_qdrant
except ImportError as e:
    print(f"⚠️  Import warning: {e}")
    print("   Some modules may not be available, using fallbacks")

logger = logging.getLogger(__name__)

class FullSlaveAgentCreator:
    """
    Creează AGENTI AI COMPLETI pentru competitori, nu doar metadata
    """
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client['ai_agents_db']
        self.agents_collection = self.db['site_agents']
        self.chunks_collection = self.db['agent_chunks']
        
        # Stats
        self.agents_created = 0
        self.agents_skipped = 0
        self.agents_failed = 0
        
        logger.info("🤖 Full Slave Agent Creator initialized")
    
    def check_if_agent_exists(self, domain: str) -> Optional[str]:
        """Verifică dacă agentul există deja (deduplication)"""
        existing = self.agents_collection.find_one({'domain': domain})
        if existing:
            return str(existing['_id'])
        return None
    
    def create_full_agent_from_url(
        self,
        url: str,
        title: str,
        domain: str,
        master_agent_id: str,
        keyword: str,
        position: int,
        use_deepseek: bool = True,
        use_qwen_learning: bool = True
    ) -> Optional[str]:
        """
        Creează un AGENT AI COMPLET dintr-un URL
        
        FLOW COMPLET:
        1. Check deduplication
        2. Scraping website (BeautifulSoup + Playwright fallback)
        3. DeepSeek analysis (optional)
        4. Chunking cu Qwen optimization
        5. GPU Embeddings
        6. Qdrant storage
        7. MongoDB storage
        8. Qwen learning din proces
        
        Args:
            url: URL-ul site-ului
            title: Titlul din SERP
            domain: Domain-ul
            master_agent_id: ID master
            keyword: Keyword pentru care a fost găsit
            position: Poziția în Google
            use_deepseek: Folosește DeepSeek pentru analiza
            use_qwen_learning: Qwen învață din proces
            
        Returns:
            agent_id sau None
        """
        
        logger.info(f"🔨 Creating FULL agent for: {domain}")
        
        try:
            # 1. Check deduplication
            existing_id = self.check_if_agent_exists(domain)
            if existing_id:
                logger.info(f"   ⏭️  Agent already exists: {domain} ({existing_id})")
                # Update doar link-ul cu master
                self.agents_collection.update_one(
                    {'_id': ObjectId(existing_id)},
                    {
                        '$addToSet': {'master_ids': master_agent_id},
                        '$set': {'updated_at': datetime.now()}
                    }
                )
                self.agents_skipped += 1
                return existing_id
            
            # 2. Scraping website
            logger.info(f"   📥 Scraping website: {url}")
            start_time = time.time()
            
            try:
                scraped_content = scrape_website(url, use_playwright=False)
                if not scraped_content or len(scraped_content) < 500:
                    logger.warning(f"   ⚠️  Content too short, trying Playwright...")
                    scraped_content = scrape_website(url, use_playwright=True)
            except Exception as e:
                logger.error(f"   ❌ Scraping failed: {e}")
                # Create minimal agent
                return self._create_minimal_agent(domain, url, title, master_agent_id, keyword, position)
            
            scraping_time = time.time() - start_time
            content_length = len(scraped_content)
            logger.info(f"   ✅ Scraped {content_length} chars in {scraping_time:.1f}s")
            
            # 3. DeepSeek analysis (optional, pentru identificare servicii/industrie)
            industry = "Unknown"
            services = []
            
            if use_deepseek and content_length > 1000:
                try:
                    from openai import OpenAI
                    client = OpenAI(
                        api_key=os.getenv('OPENAI_API_KEY'),
                        base_url=os.getenv('OPENAI_BASE_URL', 'https://api.deepseek.com')
                    )
                    
                    prompt = f"""Analizează acest site și identifică:
1. Industria (1-3 cuvinte)
2. Top 3 servicii oferite

Content (primele 2000 chars):
{scraped_content[:2000]}

Răspunde JSON:
{{"industry": "...", "services": ["...", "...", "..."]}}
"""
                    
                    response = client.chat.completions.create(
                        model=os.getenv('LLM_MODEL', 'deepseek-chat'),
                        messages=[
                            {"role": "system", "content": "You are a business analyst."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=200
                    )
                    
                    import json
                    analysis = json.loads(response.choices[0].message.content)
                    industry = analysis.get('industry', 'Unknown')
                    services = analysis.get('services', [])
                    logger.info(f"   🧠 DeepSeek analysis: {industry} | {len(services)} services")
                except Exception as e:
                    logger.warning(f"   ⚠️  DeepSeek analysis failed: {e}")
            
            # 4. Chunking (cu Qwen optimization dacă e disponibil)
            logger.info(f"   ✂️  Chunking content...")
            chunks = chunk_text(scraped_content, chunk_size=800, overlap=100)
            logger.info(f"   ✅ Created {len(chunks)} chunks")
            
            # 5. GPU Embeddings
            logger.info(f"   🧬 Generating embeddings (GPU)...")
            embeddings = []
            try:
                embeddings = generate_embeddings_gpu(chunks)
                logger.info(f"   ✅ Generated {len(embeddings)} embeddings")
            except Exception as e:
                logger.error(f"   ❌ Embeddings failed: {e}")
                # Continue without embeddings
            
            # 6. Create agent în MongoDB
            agent_doc = {
                'domain': domain,
                'site_url': url,
                'name': title,
                'type': 'slave',
                'master_ids': [master_agent_id],
                'industry': industry,
                'services': services,
                'discovered_from': {
                    'keyword': keyword,
                    'position': position,
                    'serp_date': datetime.now()
                },
                'scraped_content': scraped_content[:5000],  # Store preview
                'content_length': content_length,
                'chunks_count': len(chunks),
                'embeddings_count': len(embeddings),
                'status': 'ready' if embeddings else 'no_embeddings',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'scraping_time': scraping_time
            }
            
            result = self.agents_collection.insert_one(agent_doc)
            agent_id = str(result.inserted_id)
            logger.info(f"   ✅ Agent created: {agent_id}")
            
            # 7. Store chunks în MongoDB
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings if embeddings else [None]*len(chunks))):
                chunk_doc = {
                    'agent_id': agent_id,
                    'chunk_index': i,
                    'content': chunk,
                    'embedding': embedding.tolist() if embedding is not None else None,
                    'created_at': datetime.now()
                }
                self.chunks_collection.insert_one(chunk_doc)
            
            # 8. Store în Qdrant (dacă avem embeddings)
            if embeddings:
                try:
                    collection_name = f"agent_{agent_id}"
                    store_vectors_qdrant(
                        collection_name=collection_name,
                        vectors=embeddings,
                        payloads=[{'chunk_index': i, 'content': chunk} for i, chunk in enumerate(chunks)]
                    )
                    logger.info(f"   ✅ Vectors stored in Qdrant: {collection_name}")
                except Exception as e:
                    logger.error(f"   ❌ Qdrant storage failed: {e}")
            
            # 9. Qwen learning (dacă e activat)
            if use_qwen_learning:
                try:
                    self._qwen_learn_from_agent(agent_id, domain, industry, services, keyword)
                except Exception as e:
                    logger.warning(f"   ⚠️  Qwen learning failed: {e}")
            
            self.agents_created += 1
            logger.info(f"   🎉 FULL agent created successfully: {domain}")
            return agent_id
            
        except Exception as e:
            logger.error(f"   ❌ Failed to create agent for {domain}: {e}")
            self.agents_failed += 1
            return None
    
    def _create_minimal_agent(
        self,
        domain: str,
        url: str,
        title: str,
        master_agent_id: str,
        keyword: str,
        position: int
    ) -> Optional[str]:
        """Creează agent minimal când scraping-ul eșuează"""
        logger.info(f"   📝 Creating minimal agent for: {domain}")
        
        try:
            agent_doc = {
                'domain': domain,
                'site_url': url,
                'name': title,
                'type': 'slave',
                'master_ids': [master_agent_id],
                'industry': 'Unknown',
                'services': [],
                'discovered_from': {
                    'keyword': keyword,
                    'position': position,
                    'serp_date': datetime.now()
                },
                'status': 'minimal',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            result = self.agents_collection.insert_one(agent_doc)
            agent_id = str(result.inserted_id)
            logger.info(f"   ✅ Minimal agent created: {agent_id}")
            self.agents_created += 1
            return agent_id
        except Exception as e:
            logger.error(f"   ❌ Minimal agent failed: {e}")
            self.agents_failed += 1
            return None
    
    def _qwen_learn_from_agent(
        self,
        agent_id: str,
        domain: str,
        industry: str,
        services: List[str],
        keyword: str
    ):
        """
        Qwen local învață din procesul de creare agent
        
        Salvează în format JSONL pentru fine-tuning:
        - Domain + Industry mapping
        - Services extraction patterns
        - Keyword → Industry relationships
        """
        logger.info(f"   🧠 Qwen learning from: {domain}")
        
        try:
            # Create learning entry
            learning_doc = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Care este industria pentru site-ul {domain}? Keyword relevant: {keyword}"
                    },
                    {
                        "role": "assistant",
                        "content": f"Site-ul {domain} este în industria: {industry}. Servicii oferite: {', '.join(services)}."
                    }
                ]
            }
            
            # Append to JSONL training file
            import json
            jsonl_path = "/srv/hf/ai_agents/qwen_training_data/slave_agents_learning.jsonl"
            os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)
            
            with open(jsonl_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(learning_doc, ensure_ascii=False) + '\n')
            
            logger.info(f"   ✅ Qwen learning saved to: {jsonl_path}")
        except Exception as e:
            logger.error(f"   ❌ Qwen learning failed: {e}")
    
    def get_stats(self) -> Dict:
        """Returnează statistici despre crearea agenților"""
        return {
            'agents_created': self.agents_created,
            'agents_skipped': self.agents_skipped,
            'agents_failed': self.agents_failed,
            'total_processed': self.agents_created + self.agents_skipped + self.agents_failed,
            'success_rate': f"{(self.agents_created / max(1, self.agents_created + self.agents_failed) * 100):.1f}%"
        }


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    creator = FullSlaveAgentCreator()
    
    # Test cu un URL real
    test_url = "https://protectiilafoc.ro"
    agent_id = creator.create_full_agent_from_url(
        url=test_url,
        title="Protectii la Foc",
        domain="protectiilafoc.ro",
        master_agent_id="test_master_123",
        keyword="protectie la foc",
        position=2,
        use_deepseek=True,
        use_qwen_learning=True
    )
    
    if agent_id:
        print(f"\n✅ Test successful! Agent ID: {agent_id}")
        print(f"\n📊 Stats: {creator.get_stats()}")
    else:
        print("\n❌ Test failed!")

