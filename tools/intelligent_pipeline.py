#!/usr/bin/env python3
import os, sys, json, argparse, re, time
from langchain_ollama import OllamaEmbeddings
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Set, Optional
import openai
import tldextract
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup
from collections import deque
import concurrent.futures
from dataclasses import dataclass
import hashlib
import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL","nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434")
def get_embedder():
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)


@dataclass
class LLMEndpoint:
    url: str
    port: int
    client: openai.OpenAI
    model_type: str
    active: bool = True
    response_time: float = 0.0
    load_score: float = 0.0

class UltraOptimizedPipeline:
    def __init__(self):
        self.llm_endpoints = [
            LLMEndpoint("http://localhost:9301/v1", 9301, openai.OpenAI(base_url="http://localhost:9301/v1", api_key="local-vllm"), "7B"),
            LLMEndpoint("http://localhost:9302/v1", 9302, openai.OpenAI(base_url="http://localhost:9302/v1", api_key="local-vllm"), "7B"),
            LLMEndpoint("http://localhost:9303/v1", 9303, openai.OpenAI(base_url="http://localhost:9303/v1", api_key="local-vllm"), "7B"),
            LLMEndpoint("http://localhost:9304/v1", 9304, openai.OpenAI(base_url="http://localhost:9304/v1", api_key="local-vllm"), "7B"),
            LLMEndpoint("http://localhost:9310/v1", 9310, openai.OpenAI(base_url="http://localhost:9310/v1", api_key="local-vllm"), "14B"),
        ]
        
        self.gpt4 = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.qdrant = QdrantClient("localhost", port=6333,)
        self.init_qdrant_collections()
        
        self.mongo = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo.ai_agents
        self.collection = self.db.universal_site_pages
        self.init_mongodb_indexes()
        
        self.response_cache = {}
        self.context_cache = {}
        self.embedding_model = None
        
        print(f"🚀 Ultra Pipeline inițializat cu {len(self.llm_endpoints)} endpoints")

    def init_qdrant_collections(self):
        collections = [("website_embeddings", 384), ("page_summaries", 384), ("business_insights", 768)]
        for name, size in collections:
            try:
                self.qdrant.get_collection(name)
                print(f"✅ Colecția Qdrant '{name}' există")
            except:
                self.qdrant.create_collection(collection_name=name, vectors_config=VectorParams(size=size, distance=Distance.COSINE))
                print(f"✅ Colecția Qdrant '{name}' creată")

    def init_mongodb_indexes(self):
        indexes = [([("domain", 1)], {}), ([("domain", 1), ("scraped_at", -1)], {}), ([("title", "text"), ("content", "text")], {}), ([("industry", 1), ("domain", 1)], {})]
        for index_spec, options in indexes:
            try:
                self.collection.create_index(index_spec, **options)
            except Exception as e:
                print(f"⚠️ Index {index_spec}: {e}")
        print("✅ Indexuri MongoDB avansate create")

    def get_embedding_model(self):
        if self.embedding_model is None:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Model embeddings încărcat")
        return self.embedding_model

    def get_optimal_endpoint(self, task_complexity: str = "medium") -> LLMEndpoint:
        if task_complexity == "complex":
            endpoints_14b = [ep for ep in self.llm_endpoints if ep.model_type == "14B" and ep.active]
            if endpoints_14b:
                return min(endpoints_14b, key=lambda x: x.load_score)
        
        endpoints_7b = [ep for ep in self.llm_endpoints if ep.model_type == "7B" and ep.active]
        if endpoints_7b:
            return min(endpoints_7b, key=lambda x: x.load_score)
        
        active_endpoints = [ep for ep in self.llm_endpoints if ep.active]
        if active_endpoints:
            return min(active_endpoints, key=lambda x: x.load_score)
        
        for ep in self.llm_endpoints:
            ep.active = True
        return self.llm_endpoints[0]

    def benchmark_all_endpoints(self):
        print("🔄 Benchmark complet al cluster-ului vLLM...")
        
        def test_single_endpoint(endpoint):
            try:
                start_time = time.time()
                resp = endpoint.client.chat.completions.create(
                    model="Qwen/Qwen2.5-7B-Instruct" if endpoint.model_type == "7B" else "Qwen/Qwen2.5-14B-Instruct",
                    messages=[{"role": "user", "content": "test rapid"}],
                    max_tokens=10
                )
                response_time = time.time() - start_time
                endpoint.response_time = response_time
                endpoint.active = True
                endpoint.load_score = response_time
                return endpoint.port, response_time, endpoint.model_type
            except Exception as e:
                print(f"⚠️ Endpoint {endpoint.port} ({endpoint.model_type}) nu răspunde: {e}")
                endpoint.active = False
                endpoint.load_score = float('inf')
                return endpoint.port, float('inf'), endpoint.model_type
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.llm_endpoints)) as executor:
            futures = {executor.submit(test_single_endpoint, ep): ep for ep in self.llm_endpoints}
            for future in concurrent.futures.as_completed(futures):
                port, speed, model_type = future.result()
                if speed != float('inf'):
                    print(f"  ✅ Port {port} ({model_type}): {speed:.3f}s")
                else:
                    print(f"  ❌ Port {port} ({model_type}): Nu răspunde")

    def create_plan_with_gpt4(self, site_url: str) -> Dict:
        prompt = f"""Analizează site-ul: {site_url}

Răspunde DOAR cu un JSON valid cu această structură exactă (fără markdown, fără explicații):

{{
  "industry_analysis": {{
    "suspected_industry": "industria identificată în română",
    "target_pages": ["/pagini", "/importante"],
    "competitor_research": {{
      "keywords_for_search": ["cuvinte", "cheie"],
      "potential_competitors": ["competitori.ro", "reali.com"]
    }},
    "business_questions": ["întrebări", "de", "business"]
  }},
  "scraping_strategy": {{
    "max_pages": 150,
    "max_depth": 4,
    "priority_patterns": ["/despre", "/servicii"],
    "skip_patterns": ["/wp-content", "/.jpg"]
  }},
  "analysis_focus": ["servicii", "produse", "clienți"],
  "chat_personality": "expert în industria identificată"
}}"""

        try:
            resp = self.gpt4.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=800
            )
            
            content = resp.choices[0].message.content.strip()
            content = re.sub(r'^```[a-z]*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
            
            plan = json.loads(content)
            print(f"✅ GPT-4 a creat planul cu succes")
            return plan
        except:
            print(f"⚠️ Eroare GPT-4, folosesc planul de rezervă")
            return self._default_plan()

    def _default_plan(self) -> Dict:
        return {
            "industry_analysis": {
                "suspected_industry": "comerț electronic", 
                "target_pages": ["/", "/despre", "/servicii", "/produse", "/contact"],
                "competitor_research": {"keywords_for_search": ["produse", "servicii", "clienți"], "potential_competitors": []},
                "business_questions": ["Ce produse oferă?", "Cine sunt clienții?", "Care sunt avantajele?"]
            },
            "scraping_strategy": {"max_pages": 100, "max_depth": 3, "priority_patterns": ["/despre", "/servicii", "/produse"], "skip_patterns": ["/wp-content", "/wp-admin", "/.jpg", "/.pdf", "/.png"]},
            "analysis_focus": ["servicii", "produse", "clienți", "avantaje"],
            "chat_personality": "expert în comerț electronic român"
        }

    def create_embeddings_batch(self, pages_data: List[Dict], domain: str):
        try:
            model = self.get_embedding_model()
            texts = [f"{page['title']} {page['content'][:1000]}" for page in pages_data]
            embeddings = model.encode(texts, batch_size=32, show_progress_bar=True)
            
            points = []
            for page, embedding in zip(pages_data, embeddings):
                point = PointStruct(
                    id=hash(page['url']) % (2**63),
                    vector=embedding.tolist(),
                    payload={"url": page['url'], "domain": domain, "title": page['title'], "content": page['content'][:500], "timestamp": time.time()}
                )
                points.append(point)
            
            self.qdrant.upsert(collection_name="website_embeddings", points=points)
            print(f"✅ {len(points)} embeddings create în batch pentru {domain}")
        except Exception as e:
            print(f"⚠️ Eroare la batch embeddings: {e}")

    def scrape_page_parallel(self, url: str, headers: dict) -> Optional[Dict]:
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code != 200:
                return None
                
            soup = BeautifulSoup(resp.content, 'html.parser')
            title = soup.find('title')
            title = title.get_text().strip() if title else "Fără titlu"
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            
            for elem in soup(["script", "style", "nav", "footer", "header", "aside"]):
                elem.decompose()
            
            content = soup.get_text()
            content = re.sub(r'\s+', ' ', content).strip()
            
            links = [urljoin(url, link['href']) for link in soup.find_all('a', href=True)]
            
            return {"url": url, "title": title, "description": description, "content": content[:4000], "links": links, "scraped_at": time.time()}
        except Exception as e:
            print(f"  ⚠️ Eroare la {url}: {e}")
            return None

    def scrape_site_enterprise(self, site_url: str, max_pages: int = 50) -> bool:
        print(f"🕷️ Scraping enterprise pentru {site_url}...")
        
        domain = tldextract.extract(site_url).top_domain_under_public_suffix.lower()
        visited = set()
        queue = deque([site_url])
        pages_data = []
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            while queue and len(pages_data) < max_pages:
                batch_urls = []
                for _ in range(min(20, len(queue), max_pages - len(pages_data))):
                    if queue:
                        url = queue.popleft()
                        if url not in visited:
                            visited.add(url)
                            batch_urls.append(url)
                
                if not batch_urls:
                    break
                
                futures = {executor.submit(self.scrape_page_parallel, url, headers): url for url in batch_urls}
                
                for future in concurrent.futures.as_completed(futures):
                    page_data = future.result()
                    if page_data:
                        page_data["domain"] = domain
                        pages_data.append(page_data)
                        
                        for link in page_data.get("links", []):
                            if (domain in link and link not in visited and 
                                not any(skip in link for skip in ['.jpg', '.pdf', '.png', 'javascript:', 'mailto:'])):
                                queue.append(link)
                        
                        print(f"  ✅ Pagina {len(pages_data)}: {page_data['title'][:50]}...")
        
        if pages_data:
            clean_pages = [page.copy() for page in pages_data]
            for page in clean_pages:
                page.pop('links', None)
            
            self.collection.insert_many(clean_pages)
            print(f"✅ {len(clean_pages)} pagini salvate în MongoDB")
            self.create_embeddings_batch(clean_pages, domain)
            
        return len(pages_data) > 0

    def semantic_search_qdrant(self, query: str, domain: str = None, limit: int = 5) -> List[Dict]:
        try:
            model = self.get_embedding_model()
            query_embedding = model.encode(query).tolist()
            
            query_filter = None
            if domain:
                query_filter = Filter(must=[FieldCondition(key="domain", match=MatchValue(value=domain))])
            
            results = self.qdrant.search(
                collection_name="website_embeddings",
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit,
                with_payload=True
            )
            
            return [{"score": hit.score, **hit.payload} for hit in results]
        except Exception as e:
            print(f"⚠️ Eroare căutare semantică: {e}")
            return []

    def chat_with_semantic_context(self, question: str, site_url: str, personality: str) -> str:
        domain = tldextract.extract(site_url).top_domain_under_public_suffix.lower()
        
        semantic_results = self.semantic_search_qdrant(question, domain, limit=10)
        mongo_context = self.get_site_context_optimized(site_url, max_tokens=2000)
        
        semantic_context = "\n".join([f"=== {result['title']} ===\n{result['content']}" for result in semantic_results])
        combined_context = f"{mongo_context}\n\nREZULTATE SEMANTICE:\n{semantic_context}"
        
        endpoint = self.get_optimal_endpoint("complex")
        model_name = "Qwen/Qwen2.5-14B-Instruct" if endpoint.model_type == "14B" else "Qwen/Qwen2.5-7B-Instruct"
        
        prompt = f"""Ești {personality}. Ai acces la informații complete despre un site web.

CONTEXT COMPLET:
{combined_context[:6000]}

ÎNTREBAREA UTILIZATORULUI: {question}

INSTRUCȚIUNI:
- Răspunde DOAR în română
- Folosește contextul pentru răspuns precis
- Fii profesional și detaliat

RĂSPUNS:"""

        try:
            start_time = time.time()
            resp = endpoint.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            response_time = time.time() - start_time
            endpoint.load_score = response_time
            
            print(f"⚡ Răspuns semantic cu {endpoint.model_type} în {response_time:.3f}s")
            return resp.choices[0].message.content.strip()
        except Exception as e:
            endpoint.active = False
            return f"Eroare la generarea răspunsului: {str(e)}"

    def get_site_context_optimized(self, site_url: str, max_tokens: int = 3000) -> str:
        domain = tldextract.extract(site_url).top_domain_under_public_suffix.lower()
        
        pages = list(self.collection.find(
            {"domain": {"$regex": domain, "$options": "i"}},
            {"title": 1, "content": 1, "url": 1, "description": 1, "_id": 0}
        ).sort([("scraped_at", -1)]).limit(25))
        
        if not pages:
            print(f"⚠️ Nu s-au găsit date pentru {domain}")
            if self.scrape_site_enterprise(site_url, max_pages=30):
                pages = list(self.collection.find(
                    {"domain": {"$regex": domain, "$options": "i"}},
                    {"title": 1, "content": 1, "url": 1, "description": 1, "_id": 0}
                ).sort([("scraped_at", -1)]).limit(25))
        
        if not pages:
            return f"Nu s-au putut obține informații despre {site_url}."
        
        print(f"📄 Context din {len(pages)} pagini pentru {domain}")
        
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 2
        
        def advanced_priority(page):
            url = page.get('url', '').lower()
            title = page.get('title', '').lower()
            
            if any(p in url for p in ['/', 'index', 'home']) or 'home' in title:
                return 1
            elif any(p in url for p in ['/despre', '/about', '/servicii', '/services']):
                return 2
            elif any(p in url for p in ['/produse', '/products', '/categorii']):
                return 3
            else:
                return 4
        
        pages.sort(key=advanced_priority)
        
        for page in pages:
            title = page.get('title', 'Fără titlu')[:100]
            description = page.get('description', '')[:200]
            content = page.get('content', '')[:800]
            
            page_text = f"=== {title} ===\n"
            if description:
                page_text += f"DESCRIERE: {description}\n"
            page_text += f"{content}\n\n"
            
            if total_chars + len(page_text) > max_chars:
                break
                
            context_parts.append(page_text)
            total_chars += len(page_text)
        
        context = "".join(context_parts)
        print(f"📝 Context optimizat: {len(context)} caractere")
        return context

    def auto_generate_embeddings(self):
        print("🔄 Generez embeddings pentru toate site-urile existente...")
        
        domains = self.collection.distinct("domain")
        print(f"📊 Găsite {len(domains)} domenii unice")
        
        for domain in domains:
            try:
                existing = self.qdrant.scroll(
                    collection_name="website_embeddings",
                    scroll_filter=Filter(must=[FieldCondition(key="domain", match=MatchValue(value=domain))]),
                    limit=1
                )
                
                if existing[0]:
                    print(f"  ⏭️ {domain} - embeddings existente")
                    continue
                
                pages = list(self.collection.find({"domain": domain}, {"title": 1, "content": 1, "url": 1, "_id": 0}).limit(50))
                
                if pages:
                    self.create_embeddings_batch(pages, domain)
                    time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Eroare la {domain}: {e}")
        
        print("✅ Procesare embeddings completă")

    def run_plan_mode(self, site_url: str):
        print(f"🎯 Creez plan pentru {site_url} cu GPT-4...")
        plan = self.create_plan_with_gpt4(site_url)
        
        print(f"✅ GPT-4 a creat planul pentru {site_url}")
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        
        domain = tldextract.extract(site_url).top_domain_under_public_suffix.replace('.', '_')
        plan_file = f"/home/mobra/ai_agents/results/plan_{domain}.json"
        
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Plan salvat în: {plan_file}")

    def run_chat_mode(self, site_url: str, question: str):
        print(f"💬 Răspund la întrebarea despre {site_url}...")
        
        self.benchmark_all_endpoints()
        
        domain = tldextract.extract(site_url).top_domain_under_public_suffix.replace('.', '_')
        plan_file = f"/home/mobra/ai_agents/results/plan_{domain}.json"
        
        try:
            with open(plan_file, 'r', encoding='utf-8') as f:
                plan = json.load(f)
            personality = plan.get('chat_personality', 'asistent prietenos în română')
        except:
            personality = 'expert în business din România'
        
        answer = self.chat_with_semantic_context(question, site_url, personality)
        print(f"\n🤖 {answer}")

    def run_benchmark_mode(self):
        print("🏁 Mod benchmark - testez performanța sistemului...")
        
        self.benchmark_all_endpoints()
        
        start_time = time.time()
        count = self.collection.count_documents({})
        mongo_time = time.time() - start_time
        print(f"📊 MongoDB: {count} documente, căutare în {mongo_time:.3f}s")
        
        try:
            start_time = time.time()
            info = self.qdrant.get_collection("website_embeddings")
            qdrant_time = time.time() - start_time
            points = getattr(info, "points_count", getattr(info, "vectors_count", 0))
            print(f"🔍 Qdrant: {points} puncte, info în {qdrant_time:.3f}s")
        except:
            print("🔍 Qdrant: Colecția nu există")

def main():
    parser = argparse.ArgumentParser(description='Pipeline Inteligent AI Ultra-Optimizat')
    parser.add_argument('--url', required=True, help='URL-ul site-ului')
    parser.add_argument('--mode', choices=['plan', 'chat', 'benchmark', 'embeddings'], required=True, help='Modul de funcționare')
    parser.add_argument('--question', help='Întrebare pentru modul chat')
    
    args = parser.parse_args()
    
    if args.mode == 'chat' and not args.question:
        print("❌ Modul chat necesită --question")
        sys.exit(1)
    
    pipeline = UltraOptimizedPipeline()
    
    if args.mode == 'plan':
        pipeline.run_plan_mode(args.url)
    elif args.mode == 'chat':
        pipeline.run_chat_mode(args.url, args.question)
    elif args.mode == 'benchmark':
        pipeline.run_benchmark_mode()
    elif args.mode == 'embeddings':
        pipeline.auto_generate_embeddings()

if __name__ == "__main__":
    main()
