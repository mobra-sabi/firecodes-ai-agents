#!/usr/bin/env python3
import os, sys, json, argparse, re, time
from langchain_ollama import OllamaEmbeddings
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Set, Optional
import openai
import tldextract
from dotenv import load_dotenv
load_dotenv()  # Încarcă variabilele de mediu din .env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm_orchestrator import get_orchestrator
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from pymongo import MongoClient
from bson import ObjectId
import requests
from bs4 import BeautifulSoup
from collections import deque
import concurrent.futures
from dataclasses import dataclass
import hashlib
import numpy as np
from sentence_transformers import SentenceTransformer
from datetime import datetime
import asyncio

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL","nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434")
def get_embedder():
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)


@dataclass
class ConstructionService:
    name: str
    category: str
    description: str
    target_market: str
    competition_level: str
    regulations: List[str]
    opportunities: List[str]

class ConstructionAgentCreator:
    # Executor partajat pentru toate instanțele - NU crea unul nou pentru fiecare task
    _shared_executor = None
    
    @classmethod
    def get_executor(cls):
        """Obține executor-ul partajat pentru toate task-urile"""
        if cls._shared_executor is None:
            import concurrent.futures
            cls._shared_executor = concurrent.futures.ThreadPoolExecutor(max_workers=40)
        return cls._shared_executor
    
    def __init__(self):
        # AI Models - 🎭 Orchestrator cu DeepSeek + fallback
        self.llm = get_orchestrator()
        self.gpt4 = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Kept for legacy
        self.qwen = openai.OpenAI(base_url="http://localhost:9301/v1", api_key="local-vllm")  # Kept for legacy
        
        # ScraperAPI pentru scraping robust
        # Încarcă din .env dacă nu este setat în mediu
        self.scraperapi_key = os.getenv("SCRAPERAPI_KEY", "")
        if not self.scraperapi_key:
            # Încearcă să încarce din .env manual
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith("SCRAPERAPI_KEY="):
                            self.scraperapi_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        self.use_scraperapi = bool(self.scraperapi_key)
        if self.use_scraperapi:
            print(f"✅ ScraperAPI activat (key length: {len(self.scraperapi_key)})")
        
        # Databases
        self.qdrant = QdrantClient("localhost", port=9306,)
        # Folosește configurația din config.database_config
        from config.database_config import MONGODB_URI, MONGODB_DATABASE
        self.mongo = MongoClient(MONGODB_URI)
        self.db = self.mongo[MONGODB_DATABASE]
        
        # Collections
        self.sites_collection = self.db.company_sites
        self.services_collection = self.db.construction_services
        self.competitors_collection = self.db.competitors
        self.regulations_collection = self.db.regulations
        self.agents_collection = self.db.site_agents  # ✅ Va salva în ai_agents_db.site_agents
        
        # Embeddings - va fi creat per GPU când este necesar
        # IMPORTANT: Fiecare instance de ConstructionAgentCreator are propriul model
        # Dar trebuie să fie thread-safe pentru paralelism
        self.embedding_models = {}  # Dict: {gpu_id: model} pentru a suporta multiple GPU-uri simultan
        self.embedding_model = None  # Backward compatibility
        self.embedding_model_gpu = None
        
        # Construcții subdominii România
        self.construction_domains = {
            "constructii_generale": {
                "keywords": ["constructii case", "constructii vile", "constructii cladiri", "amenajari"],
                "competitors_search": ["constructii bucuresti", "constructii cluj", "constructii timisoara"],
                "regulations": ["autorizatie constructie", "POT", "CUT", "aviz ISU", "certificat energetic"]
            },
            "renovari_amenajari": {
                "keywords": ["renovari apartamente", "amenajari interioare", "design interior", "renovari case"],
                "competitors_search": ["renovari bucuresti", "amenajari cluj", "design interior romania"],
                "regulations": ["aviz condominium", "autorizatie amenajare", "certificate materiale"]
            },
            "instalatii": {
                "keywords": ["instalatii sanitare", "instalatii electrice", "instalatii gaz", "instalatii termice"],
                "competitors_search": ["instalatori bucuresti", "electricieni autorizati", "instalatii sanitare"],
                "regulations": ["ANRE", "certificat instalator", "aviz distributie gaz", "autorizatie electrica"]
            },
            "acoperisuri": {
                "keywords": ["acoperisuri", "tigla", "tabla", "reparatii acoperis", "hidroizolatie"],
                "competitors_search": ["acoperisuri bucuresti", "tigla cluj", "reparatii acoperis"],
                "regulations": ["garantie acoperis", "certificate materiale", "aviz urbanism"]
            },
            "demolari": {
                "keywords": ["demolari", "excavatii", "terasamente", "decopertare"],
                "competitors_search": ["demolari bucuresti", "excavatii cluj", "terasamente"],
                "regulations": ["aviz demolare", "studiu geotehnic", "masuri siguranta", "gestionare deseuri"]
            },
            "izolatie_termica": {
                "keywords": ["izolatie termica", "termoizolatie", "eficienta energetica", "reabilitare termica"],
                "competitors_search": ["izolatie termica bucuresti", "reabilitare bloc", "eficienta energetica"],
                "regulations": ["certificat energetic", "Casa Verde", "ANL", "fonduri europene"]
            }
        }
        
        self.init_databases()
        print("🏗️ Construction Agent Creator inițializat")

    def init_databases(self):
        """Inițializează colecțiile și indexurile pentru construcții"""
        try:
            # MongoDB indexes
            indexes = [
                (self.sites_collection, [("domain", 1), ("services", 1)]),
                (self.services_collection, [("category", 1), ("competition_level", 1)]),
                (self.competitors_collection, [("service_category", 1), ("location", 1)]),
                (self.regulations_collection, [("domain", 1), ("regulation_type", 1)]),
                (self.agents_collection, [("domain", 1), ("agent_type", 1)])
            ]
            
            for collection, index_spec in indexes:
                try:
                    collection.create_index(index_spec)
                except:
                    pass
            
            # Qdrant collections
            collections = [
                ("construction_sites", 384),
                ("construction_services", 384),
                ("competition_analysis", 384),
                ("regulations_db", 384)
            ]
            
            for name, size in collections:
                try:
                    self.qdrant.get_collection(name)
                except:
                    self.qdrant.create_collection(
                        collection_name=name,
                        vectors_config=VectorParams(size=size, distance=Distance.COSINE)
                    )
            
            print("✅ Baze de date pentru construcții inițializate")
        except Exception as e:
            print(f"⚠️ Eroare inițializare baze de date: {e}")

    def analyze_construction_site_internal(self, site_url: str, site_data: Dict) -> Dict:
        """Analizează site-ul de construcții folosind datele deja scraped (internal method)"""
        print(f"🔍 Analizez site-ul de construcții: {site_url}")
        
        # Verifică dacă scraping-ul a returnat pagini
        if site_data.get('total_pages', 0) == 0 or len(site_data.get('pages', [])) == 0:
            print(f"⚠️ Scraping-ul nu a returnat pagini pentru {site_url}. Folosesc analiză minimă.")
            # Creează analiză minimă bazată pe domain
            domain = site_data.get('domain', tldextract.extract(site_url).top_domain_under_public_suffix.lower())
            services_analysis = self.default_construction_analysis()
            services_analysis['site_content'] = site_data
            services_analysis['embeddings_created'] = 0
        else:
            # GPT-4 analizează și categorisează serviciile doar dacă există conținut
            try:
                services_analysis = self.gpt4_analyze_construction_services(site_data, site_url)
            except Exception as e:
                print(f"⚠️ Eroare la analiza GPT-4: {e}. Folosesc analiză default.")
                services_analysis = self.default_construction_analysis()
            
            # Adaugă site_data în analysis
            services_analysis['site_content'] = site_data
        
        return services_analysis

    def analyze_construction_site(self, site_url: str) -> Dict:
        """Analizează un site de construcții și identifică serviciile"""
        print(f"🔍 Analizez site-ul de construcții: {site_url}")
        
        # Scraping complet site cu error handling
        try:
            site_data = self.scrape_construction_site(site_url)
        except Exception as e:
            print(f"⚠️ Eroare la scraping {site_url}: {e}")
            # Creează site_data minim dacă scraping-ul eșuează
            domain = tldextract.extract(site_url).top_domain_under_public_suffix.lower()
            site_data = {
                "domain": domain,
                "total_pages": 0,
                "pages": [],
                "scraped_at": datetime.now().isoformat()
            }
        
        # Verifică dacă scraping-ul a returnat pagini
        if site_data.get('total_pages', 0) == 0 or len(site_data.get('pages', [])) == 0:
            print(f"⚠️ Scraping-ul nu a returnat pagini pentru {site_url}. Folosesc analiză minimă.")
            # Creează analiză minimă bazată pe domain
            domain = site_data.get('domain', tldextract.extract(site_url).top_domain_under_public_suffix.lower())
            services_analysis = self.default_construction_analysis()
            services_analysis['site_content'] = site_data
            services_analysis['embeddings_created'] = 0
        else:
            # GPT-4 analizează și categorisează serviciile doar dacă există conținut
            try:
                services_analysis = self.gpt4_analyze_construction_services(site_data, site_url)
            except Exception as e:
                print(f"⚠️ Eroare la analiza GPT-4: {e}. Folosesc analiză default.")
                services_analysis = self.default_construction_analysis()
            
            # Adaugă site_data în analysis
            services_analysis['site_content'] = site_data
            
            # Salvează în baza de date (va fi salvat separat în create_agent_from_url)
            # Nu mai salvăm aici pentru a nu bloca
        
        return services_analysis
    
    def analyze_construction_site(self, site_url: str) -> Dict:
        """Analizează site-ul de construcții și creează strategia (legacy method - păstrat pentru compatibilitate)"""
        # Scrape site-ul
        site_data = self.scrape_construction_site(site_url)
        # Analizează
        return self.analyze_construction_site_internal(site_url, site_data)

    def scrape_construction_site(self, site_url: str) -> Dict:
        """Scraping specializat pentru site-uri de construcții"""
        print(f"🕷️ Scraping site construcții: {site_url}")
        
        domain = tldextract.extract(site_url).top_domain_under_public_suffix.lower()
        visited = set()
        queue = deque([site_url])
        pages_data = []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8'
        }
        
        # Keywords specifice construcții pentru prioritizare
        priority_keywords = [
            'servicii', 'constructii', 'amenajari', 'renovari', 'instalatii', 
            'acoperisuri', 'izolatie', 'demolari', 'proiecte', 'portofoliu',
            'despre', 'contact', 'preturi', 'oferta'
        ]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            while queue and len(pages_data) < 100:
                batch_urls = []
                for _ in range(min(15, len(queue), 100 - len(pages_data))):
                    if queue:
                        url = queue.popleft()
                        if url not in visited:
                            visited.add(url)
                            batch_urls.append(url)
                
                if not batch_urls:
                    break
                
                futures = {executor.submit(self.scrape_single_page, url, headers): url for url in batch_urls}
                
                for future in concurrent.futures.as_completed(futures):
                    page_data = future.result()
                    if page_data:
                        page_data["domain"] = domain
                        pages_data.append(page_data)
                        
                        # Prioritizează link-urile cu keywords de construcții
                        priority_links = []
                        normal_links = []
                        
                        for link in page_data.get("links", []):
                            if (domain in link and link not in visited and 
                                not any(skip in link for skip in ['.jpg', '.pdf', '.png', 'javascript:', 'mailto:'])):
                                
                                if any(keyword in link.lower() for keyword in priority_keywords):
                                    priority_links.append(link)
                                else:
                                    normal_links.append(link)
                        
                        # Adaugă link-urile prioritare primul
                        for link in priority_links + normal_links[:5]:
                            queue.append(link)
                        
                        print(f"  ✅ Pagina {len(pages_data)}: {page_data['title'][:60]}...")
        
        return {
            "domain": domain,
            "total_pages": len(pages_data),
            "pages": pages_data,
            "scraped_at": datetime.now().isoformat()
        }

    def scrape_single_page(self, url: str, headers: dict, max_retries: int = 3) -> Optional[Dict]:
        """Scraping pentru o singură pagină cu focus pe construcții"""
        resp = None
        
        # Folosește ScraperAPI dacă este disponibil
        if self.use_scraperapi:
            try:
                scraperapi_url = f"http://api.scraperapi.com?api_key={self.scraperapi_key}&url={requests.utils.quote(url)}"
                print(f"  🔧 Folosind ScraperAPI pentru {url[:60]}...")
                resp = requests.get(scraperapi_url, timeout=30, allow_redirects=True)
                if resp.status_code == 200:
                    # ScraperAPI a reușit, continuă cu procesarea
                    print(f"  ✅ ScraperAPI success pentru {url[:60]} (status: {resp.status_code})")
                    pass
                else:
                    print(f"  ⚠️ ScraperAPI returned status {resp.status_code} pentru {url[:60]}, încerc direct...")
                    resp = None  # Forțează fallback
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                print(f"  ⚠️ ScraperAPI timeout/error pentru {url[:60]}: {type(e).__name__}, încerc direct...")
                resp = None  # Fallback la requests direct
            except Exception as e:
                print(f"  ⚠️ Eroare ScraperAPI pentru {url[:60]}: {e}, încerc direct...")
                resp = None  # Fallback la requests direct
        
        # Fallback la requests direct dacă ScraperAPI nu a funcționat
        if resp is None:
            for attempt in range(max_retries):
                try:
                    resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                    if resp.status_code == 200:
                        break
                    elif resp.status_code in [301, 302, 303, 307, 308]:
                        # Follow redirects
                        url = resp.headers.get('Location', url)
                        continue
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(1 * (attempt + 1))  # Exponential backoff
                            continue
                        return None
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                        requests.exceptions.SSLError, requests.exceptions.TooManyRedirects) as e:
                    if attempt < max_retries - 1:
                        print(f"  ⚠️ Retry {attempt + 1}/{max_retries} pentru {url[:60]}...")
                        time.sleep(1 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        print(f"  ❌ Eroare finală la {url[:60]}: {type(e).__name__}")
                        return None
                except Exception as e:
                    print(f"  ⚠️ Eroare neașteptată la {url[:60]}: {e}")
                    return None
        
        # Verifică dacă avem un răspuns valid
        if resp is None or resp.status_code != 200:
            return None
        
        try:
                
            # Verifică dacă răspunsul este valid HTML
            if not resp.content or len(resp.content) < 100:
                return None
                
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title = title.get_text().strip() if title else "Fără titlu"
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            
            # Extract structured data specific pentru construcții
            services_text = self.extract_construction_services(soup)
            contact_info = self.extract_contact_info(soup)
            
            # Clean content
            for elem in soup(["script", "style", "nav", "footer", "header", "aside"]):
                elem.decompose()
            
            content = soup.get_text()
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Extract links
            links = [urljoin(url, link['href']) for link in soup.find_all('a', href=True)]
            
            return {
                "url": url,
                "title": title,
                "description": description,
                "content": content[:5000],
                "services_detected": services_text,
                "contact_info": contact_info,
                "links": links,
                "scraped_at": time.time()
            }
            
        except Exception as e:
            print(f"  ⚠️ Eroare la {url}: {e}")
            return None

    def extract_construction_services(self, soup: BeautifulSoup) -> List[str]:
        """Extrage servicii de construcții din pagină"""
        services = []
        
        # Keywords pentru detectarea serviciilor
        service_patterns = [
            r'construc[ț|t]i[ei]?\s+(?:case|vil[ei]|cl[ă|a]diri|residen[ț|t]ial[ei]?)',
            r'amenaj[ă|a]ri\s+(?:interior[ei]?|exterior[ei]?)',
            r'renov[ă|a]ri\s+(?:apartament[ei]?|case|vil[ei])',
            r'instalat[,|.]ii?\s+(?:sanitare|electrice|gaz|termice)',
            r'acoperi[s|ș]uri?\s+(?:tigl[ă|a]|tabl[ă|a]|membran[ă|a])',
            r'izola[t|ț]ie?\s+(?:termic[ă|a]|fonic[ă|a]|hidroizola[t|ț]ie)',
            r'demol[ă|a]ri|excava[t|ț]ii|terasamente',
            r'pardoseli\s+(?:epoxidice|industrial[ei]?|decorative)',
            r'zugr[ă|a]veli|vopsitori[ei]?|finisa[j|g]e'
        ]
        
        text = soup.get_text().lower()
        
        for pattern in service_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            services.extend(matches)
        
        return list(set(services))

    def extract_contact_info(self, soup: BeautifulSoup) -> Dict:
        """Extrage informații de contact"""
        contact_info = {}
        
        text = soup.get_text()
        
        # Extract phone numbers
        phone_pattern = r'(?:\+40|0)(?:\s|-)?(?:\d{3})(?:\s|-)?(?:\d{3})(?:\s|-)?(?:\d{3})'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact_info['phones'] = phones
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact_info['emails'] = emails
        
        # Extract addresses (Romanian specific)
        address_patterns = [
            r'(?:str|strada|bd|bulevardul|calea)\s+[A-Za-z\s]+\s+(?:nr|numărul)?\s*\d+',
            r'sector\s+\d+',
            r'(?:bucurești|cluj|timișoara|constanța|iași|craiova|brașov|galați|ploiești|oradea)',
        ]
        
        addresses = []
        for pattern in address_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            addresses.extend(matches)
        
        if addresses:
            contact_info['addresses'] = addresses
        
        return contact_info

    def gpt4_analyze_construction_services(self, site_data: Dict, site_url: str) -> Dict:
        """GPT-4 analizează serviciile de construcții și creează strategia"""
        
        # Construiește contextul pentru GPT-4
        context = self.build_gpt4_context(site_data)
        
        prompt = f"""Analizează acest site de construcții din România și creează o analiză strategică detaliată.

CONTEXT SITE:
{context}

URL: {site_url}

Creează o analiză JSON cu această structură exactă:

{{
  "company_analysis": {{
    "company_name": "numele companiei",
    "main_location": "orașul principal",
    "company_size": "estimare: micro/mic/mediu/mare",
    "years_experience": "estimare ani experiență",
    "unique_selling_points": ["puncte forte identificate"]
  }},
  "services_identified": [
    {{
      "service_name": "nume serviciu",
      "category": "categorie din: constructii_generale|renovari_amenajari|instalatii|acoperisuri|demolari|izolatie_termica",
      "description": "descriere serviciu",
      "target_market": "piața țintă",
      "estimated_demand": "cerere estimată: scăzută|medie|ridicată",
      "competition_level": "competiție: scăzută|medie|ridicată|foarte ridicată",
      "price_positioning": "poziționare preț: budget|mediu|premium",
      "growth_potential": "potențial creștere: scăzut|mediu|ridicat"
    }}
  ],
  "market_opportunities": [
    {{
      "opportunity": "descriere oportunitate",
      "market_size": "dimensiune piață estimată",
      "competition_gap": "goluri în competiție",
      "implementation_difficulty": "dificultate: ușoară|medie|ridicată"
    }}
  ],
  "digital_presence": {{
    "website_quality": "calitate site: slabă|medie|bună|excelentă",
    "seo_optimization": "optimizare SEO: slabă|medie|bună",
    "social_media_present": "prezență social media: da/nu",
    "online_reputation": "reputație online estimată",
    "improvement_areas": ["zone de îmbunătățire"]
  }},
  "agent_personality": {{
    "role": "Specialist în [domeniu principal] cu experiență în România",
    "expertise_areas": ["zone de expertiză"],
    "communication_style": "stil comunicare: profesional|prietenos|tehnic|consultativ",
    "key_knowledge": ["cunoștințe cheie despre piață/legislație"],
    "response_approach": "abordare răspunsuri: practică|strategică|tehnică"
  }}
}}

Analizează în profunzime piața de construcții din România și oferă insights strategice."""

        try:
            # 🎭 Folosim Orchestrator cu DeepSeek + fallback
            resp = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            
            if not resp.get("success"):
                raise Exception(f"LLM failed: {resp.get('error', 'Unknown')}")
            
            content = resp["content"].strip()
            content = re.sub(r'^```[a-z]*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
            
            analysis = json.loads(content)
            print(f"✅ {resp['provider']} a analizat serviciile de construcții")
            return analysis
            
        except Exception as e:
            print(f"⚠️ Eroare LLM analiză: {e}")
            return self.default_construction_analysis()

    def build_gpt4_context(self, site_data: Dict) -> str:
        """Construiește contextul pentru GPT-4 din datele site-ului"""
        context_parts = []
        
        # Adaugă informații generale
        context_parts.append(f"DOMENIU: {site_data['domain']}")
        context_parts.append(f"TOTAL PAGINI: {site_data['total_pages']}")
        
        # Adaugă conținutul cel mai relevant
        for page in site_data['pages'][:10]:  # Primele 10 pagini
            title = page.get('title', '')
            description = page.get('description', '')
            content = page.get('content', '')[:800]  # Primul 800 caractere
            services = page.get('services_detected', [])
            contact = page.get('contact_info', {})
            
            page_context = f"""
PAGINĂ: {title}
DESCRIERE: {description}
SERVICII DETECTATE: {', '.join(services)}
CONTACT: {contact}
CONȚINUT: {content}
---"""
            context_parts.append(page_context)
        
        return '\n'.join(context_parts)

    def default_construction_analysis(self) -> Dict:
        """Analiză de rezervă pentru construcții"""
        return {
            "company_analysis": {
                "company_name": "Companie Construcții",
                "main_location": "România",
                "company_size": "mic",
                "years_experience": "5+",
                "unique_selling_points": ["servicii complete construcții"]
            },
            "services_identified": [{
                "service_name": "Construcții generale",
                "category": "constructii_generale",
                "description": "Servicii de construcții",
                "target_market": "clienți privați",
                "estimated_demand": "ridicată",
                "competition_level": "ridicată",
                "price_positioning": "mediu",
                "growth_potential": "mediu"
            }],
            "market_opportunities": [],
            "digital_presence": {
                "website_quality": "medie",
                "seo_optimization": "medie",
                "social_media_present": "nu",
                "online_reputation": "necunoscută",
                "improvement_areas": ["SEO", "social media"]
            },
            "agent_personality": {
                "role": "Specialist construcții în România",
                "expertise_areas": ["construcții", "renovări"],
                "communication_style": "profesional",
                "key_knowledge": ["piața construcții România"],
                "response_approach": "practică"
            }
        }

    def save_site_analysis(self, site_url: str, site_data: Dict, analysis: Dict):
        """Salvează analiza în bazele de date"""
        domain = tldextract.extract(site_url).top_domain_under_public_suffix.lower()
        
        try:
            # Salvează în MongoDB
            site_record = {
                "domain": domain,
                "url": site_url,
                "analysis": analysis,
                "site_data": site_data,
                "analyzed_at": datetime.now(),
                "status": "analyzed"
            }
            
            self.sites_collection.replace_one(
                {"domain": domain}, 
                site_record, 
                upsert=True
            )
            
            # Salvează serviciile separate
            for service in analysis.get('services_identified', []):
                service_record = {
                    "domain": domain,
                    "service_name": service.get('service_name'),
                    "category": service.get('category'),
                    "service_data": service,
                    "created_at": datetime.now()
                }
                
                self.services_collection.insert_one(service_record)
            
            # Creează embeddings pentru Qdrant (folosește GPU specificat sau implicit)
            gpu_id = getattr(self, '_current_gpu_id', None)
            embeddings_count = self.create_site_embeddings(domain, site_data, analysis, gpu_id=gpu_id)
            
            # ✅ IMPORTANT: Salvează numărul de embeddings în analysis pentru validare
            analysis['embeddings_created'] = embeddings_count
            
            print(f"✅ Analiză salvată pentru {domain}")
            
        except Exception as e:
            print(f"⚠️ Eroare salvare analiză: {e}")

    def get_embedding_model(self, gpu_id: Optional[int] = None):
        """Obține modelul de embeddings pentru GPU-ul specificat"""
        import torch
        
        # Dacă nu este specificat GPU, folosește GPU 0
        if gpu_id is None:
            gpu_id = 0
        
        # Verifică dacă avem deja modelul pentru acest GPU în dict
        if gpu_id in self.embedding_models:
            return self.embedding_models[gpu_id]
        
        # Creează model nou pentru GPU-ul specificat
        # ✅ CORECTARE: Inițializează direct pe device-ul dorit pentru a evita eroarea "meta tensor"
        print(f"🔧 Creând embedding model (instance: {id(self)}) pentru GPU {gpu_id}")
        
        # Mută modelul pe GPU dacă este disponibil
        if torch.cuda.is_available() and gpu_id < torch.cuda.device_count():
            device = f"cuda:{gpu_id}"
            print(f"🔧 Inițializând embedding model direct pe {device}")
            try:
                # ✅ Încearcă să inițializeze direct pe GPU (evită problema "meta tensor")
                model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
            except Exception as e:
                print(f"⚠️ Eroare la inițializare directă pe GPU {gpu_id}: {e}. Folosesc CPU apoi mut pe GPU.")
                # Fallback: inițializează pe CPU și mută manual cu atenție
                model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
                try:
                    # Mută modelul pe GPU - dacă apare eroarea meta tensor, folosește CPU
                    model = model.to(device)
                except Exception as e2:
                    if "meta tensor" in str(e2).lower():
                        print(f"⚠️ Eroare 'meta tensor' detectată. Reinițializez modelul pe CPU.")
                        # Reinițializează modelul complet pe CPU
                        model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
                        device = "cpu"
                    else:
                        print(f"⚠️ Eroare la mutarea modelului pe GPU: {e2}. Folosesc CPU.")
                        device = "cpu"
        else:
            device = "cpu"
            print(f"⚠️ GPU {gpu_id} nu este disponibil, folosesc CPU")
            model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
        self.embedding_models[gpu_id] = model
        
        # Backward compatibility
        self.embedding_model = model
        self.embedding_model_gpu = gpu_id
        
        return model
    
    def create_site_embeddings(self, domain: str, site_data: Dict, analysis: Dict, gpu_id: Optional[int] = None) -> int:
        """Creează embeddings cu GPU pentru FIECARE pagină. Returnează numărul de embeddings create."""
        embeddings_created = 0
        
        # Obține modelul pentru GPU-ul specificat
        embedding_model = self.get_embedding_model(gpu_id)
        
        # Creează collection per agent pentru chunks
        collection_name = f"construction_{domain.replace('.', '_')}"
        
        try:
            # 1. Asigură-te că există collection pentru chunks
            try:
                self.qdrant.get_collection(collection_name)
            except:
                from qdrant_client.models import Distance, VectorParams
                self.qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                print(f"📦 Colecție Qdrant creată: {collection_name}")
            
            # 2. Creează chunks pentru FIECARE pagină
            pages = site_data.get('pages', [])
            print(f"🧩 Creez chunks pentru {len(pages)} pagini pe GPU {gpu_id if gpu_id is not None else 0}...")
            
            points = []
            chunk_id = 0
            
            for page_idx, page in enumerate(pages):
                page_content = page.get('content', '')
                page_url = page.get('url', '')
                
                if not page_content or len(page_content) < 100:
                    continue
                
                # Split în chunks de ~500 caractere
                chunk_size = 500
                overlap = 50
                
                for i in range(0, len(page_content), chunk_size - overlap):
                    chunk_text = page_content[i:i + chunk_size]
                    
                    if len(chunk_text) < 100:  # Skip chunks prea mici
                        continue
                    
                    # Generează embedding cu GPU (SentenceTransformer)
                    embedding = embedding_model.encode(chunk_text).tolist()
                    
                    # Creează point pentru Qdrant
                    point = PointStruct(
                        id=chunk_id,
                        vector=embedding,
                        payload={
                            "domain": domain,
                            "url": page_url,
                            "chunk_text": chunk_text[:500],  # First 500 chars
                            "chunk_index": chunk_id,
                            "page_index": page_idx,
                            "timestamp": time.time()
                        }
                    )
                    points.append(point)
                    chunk_id += 1
                    
                    # Upsert în batch-uri de 100
                    if len(points) >= 100:
                        self.qdrant.upsert(collection_name=collection_name, points=points)
                        embeddings_created += len(points)
                        print(f"   ✅ {embeddings_created} chunks procesate cu GPU...")
                        points = []
            
            # Upsert ultimele chunks
            if points:
                self.qdrant.upsert(collection_name=collection_name, points=points)
                embeddings_created += len(points)
            
            print(f"✅ Total {embeddings_created} embeddings create cu GPU pentru {domain}")
            
            # 3. Creează și embedding pentru summary (backward compatibility)
            summary_text = f"""
            {analysis.get('company_analysis', {}).get('company_name', '')}
            {' '.join([s.get('service_name', '') for s in analysis.get('services_identified', [])])}
            {analysis.get('company_analysis', {}).get('main_location', '')}
            """
            
            summary_embedding = embedding_model.encode(summary_text).tolist()
            summary_point = PointStruct(
                id=hash(domain) % (2**63),
                vector=summary_embedding,
                payload={
                    "domain": domain,
                    "company_name": analysis.get('company_analysis', {}).get('company_name', ''),
                    "services": [s.get('service_name', '') for s in analysis.get('services_identified', [])],
                    "location": analysis.get('company_analysis', {}).get('main_location', ''),
                    "timestamp": time.time()
                }
            )
            self.qdrant.upsert(collection_name="construction_sites", points=[summary_point])
            
        except Exception as e:
            print(f"⚠️ Eroare creare embeddings: {e}")
            import traceback
            traceback.print_exc()
        
        return embeddings_created

    def create_site_agent(self, site_url: str, gpu_id: Optional[int] = None) -> Dict:
        """Creează agentul AI specializat pentru site-ul de construcții"""
        print(f"🤖 Creez agent AI pentru site-ul: {site_url} (GPU {gpu_id if gpu_id is not None else 0})")
        
        # Salvează GPU ID pentru a-l folosi în create_site_embeddings
        self._current_gpu_id = gpu_id
        
        # 1. Scraping site
        site_data = self.scrape_construction_site(site_url)
        
        # 2. Analizează site-ul
        analysis = self.analyze_construction_site_internal(site_url, site_data)
        
        # 3. Extrage domain pentru embeddings
        domain = tldextract.extract(site_url).top_domain_under_public_suffix.lower()
        
        # 4. ✅ CREEAZĂ EMBEDDINGS - aceasta era partea lipsă!
        print(f"🧠 Creez embeddings pentru {domain}...")
        embeddings_count = self.create_site_embeddings(domain, site_data, analysis, gpu_id=gpu_id)
        
        # 5. Extrage statistici din analysis pentru validation
        site_content = analysis.get('site_content', {})
        if isinstance(site_content, dict):
            pages_scraped = len(site_content.get('pages', []))
        else:
            pages_scraped = site_data.get('total_pages', 0)
        
        # 6. Creează personalitatea agentului
        agent_config = self.create_agent_personality(analysis)
        
        # ✅ IMPORTANT: Adaugă statistici pentru validation
        agent_config['pages_scraped'] = pages_scraped
        agent_config['embeddings_count'] = embeddings_count
        
        # 7. Salvează agentul (va seta validation_passed based pe aceste valori)
        self.save_agent_config(site_url, agent_config)
        
        print(f"✅ Agent AI creat pentru {site_url}")
        print(f"   Pages scraped: {pages_scraped}")
        print(f"   Embeddings: {embeddings_count}")
        return agent_config
    
    async def create_agent_from_url(self, site_url: str, industry: str = "", master_agent_id: str = None, gpu_id: Optional[int] = None) -> Dict:
        """Creează agentul AI pentru un site URL (async wrapper pentru integrare cu API)"""
        try:
            # Salvează GPU ID temporar pentru a-l folosi în create_site_embeddings
            self._current_gpu_id = gpu_id
            
            # IMPORTANT: Rulează fiecare operație blocking în executor separat pentru paralelism real
            # Altfel, toate task-urile blochează și rulează secvențial
            import asyncio
            loop = asyncio.get_event_loop()
            executor = self.get_executor()
            
            # Log pentru debugging
            if gpu_id is not None:
                print(f"🚀 Pornind task pentru {site_url[:50]}... pe GPU {gpu_id} în executor")
            
            # Rulează fiecare operație blocking în executor separat pentru paralelism real
            # 1. Scraping (operație blocking I/O)
            site_data = await loop.run_in_executor(
                executor,
                self.scrape_construction_site,
                site_url
            )
            
            # 2. Analiză (operație blocking I/O + LLM)
            analysis = await loop.run_in_executor(
                executor,
                lambda: self.analyze_construction_site_internal(site_url, site_data)
            )
            
            # 3. Salvează analiza în baza de date (operație blocking I/O)
            await loop.run_in_executor(
                executor,
                self.save_site_analysis,
                site_url,
                site_data,
                analysis
            )
            
            # 4. Creare embeddings (operație blocking GPU)
            # IMPORTANT: Trebuie să pasez gpu_id ca keyword argument
            domain = tldextract.extract(site_url).top_domain_under_public_suffix.lower()
            
            # Folosește functools.partial pentru a pasa gpu_id ca keyword argument
            from functools import partial
            embeddings_count = await loop.run_in_executor(
                executor,
                partial(self.create_site_embeddings, domain, site_data, analysis, gpu_id=gpu_id)
            )
            
            # 5. Creează personalitatea agentului (operație non-blocking)
            agent_config = self.create_agent_personality(analysis)
            
            # 6. Extrage statistici
            site_content = analysis.get('site_content', {})
            if isinstance(site_content, dict):
                pages_scraped = len(site_content.get('pages', []))
            else:
                pages_scraped = 0
            
            agent_config['pages_scraped'] = pages_scraped
            agent_config['embeddings_count'] = embeddings_count
            
            # 7. Salvează agentul (operație blocking I/O)
            await loop.run_in_executor(
                executor,
                self.save_agent_config,
                site_url,
                agent_config
            )
            
            print(f"✅ Agent AI creat pentru {site_url}")
            print(f"   Pages scraped: {pages_scraped}")
            print(f"   Embeddings: {embeddings_count}")
            
            if gpu_id is not None:
                print(f"✅ GPU {gpu_id} folosit pentru {site_url}")
            
            # Extrage domain-ul în format complet
            extracted = tldextract.extract(site_url)
            domain = f"{extracted.domain}.{extracted.suffix}".lower()
            
            # Găsește agentul creat în MongoDB
            agent_record = self.agents_collection.find_one({"domain": domain})
            
            if agent_record:
                agent_id = str(agent_record.get("_id"))
                
                # Actualizează cu master_agent_id dacă este furnizat
                if master_agent_id:
                    from bson import ObjectId
                    master_oid = ObjectId(master_agent_id)
                    self.agents_collection.update_one(
                        {"_id": agent_record["_id"]},
                        {
                            "$set": {
                                "master_agent_id": master_oid,
                                "agent_type": "slave",
                                "last_updated": datetime.now()
                            }
                        }
                    )
                
                return {
                    "ok": True,
                    "agent_id": agent_id,
                    "domain": domain,
                    "message": f"Agent created successfully for {domain}",
                    "pages_scraped": pages_scraped,
                    "embeddings_count": embeddings_count
                }
            else:
                return {
                    "ok": False,
                    "error": "Agent record not found after creation"
                }
        except Exception as e:
            import traceback
            print(f"❌ Error creating agent from URL {site_url}: {e}")
            traceback.print_exc()
            return {
                "ok": False,
                "error": str(e)
            }

    def create_agent_personality(self, analysis: Dict) -> Dict:
        """Creează personalitatea agentului bazată pe analiză"""
        
        personality = analysis.get('agent_personality', {})
        services = analysis.get('services_identified', [])
        company = analysis.get('company_analysis', {})
        
        agent_config = {
            "agent_id": f"construction_agent_{int(time.time())}",
            "role": personality.get('role', 'Specialist construcții'),
            "expertise": personality.get('expertise_areas', ['construcții generale']),
            "communication_style": personality.get('communication_style', 'profesional'),
            "knowledge_base": {
                "company_info": company,
                "services_offered": services,
                "market_knowledge": analysis.get('market_opportunities', []),
                "digital_insights": analysis.get('digital_presence', {})
            },
            "response_templates": {
                "greeting": f"Bună ziua! Sunt {personality.get('role', 'specialistul')} acestei companii. Cu ce vă pot ajuta în domeniul construcțiilor?",
                "services_inquiry": "Oferim următoarele servicii principale: {services_list}. Despre care dintre acestea doriți să aflați mai multe?",
                "pricing_inquiry": "Pentru o ofertă personalizată, vă recomand să ne contactați direct. Prețurile variază în funcție de complexitatea proiectului.",
                "recommendation": "Pe baza experienței noastre în piața românească, vă recomand următoarea abordare:"
            },
            "specialized_knowledge": {
                "regulations": self.get_relevant_regulations(services),
                "market_trends": self.get_market_trends(services),
                "best_practices": self.get_best_practices(services)
            },
            "created_at": datetime.now().isoformat()
        }
        
        return agent_config

    def get_relevant_regulations(self, services: List[Dict]) -> List[str]:
        """Obține reglementările relevante pentru serviciile identificate"""
        regulations = []
        
        for service in services:
            category = service.get('category', '')
            if category in self.construction_domains:
                regulations.extend(self.construction_domains[category]['regulations'])
        
        return list(set(regulations))

    def get_market_trends(self, services: List[Dict]) -> List[str]:
        """Obține tendințele pieței pentru serviciile identificate"""
        trends = [
            "Creșterea cererii pentru eficiență energetică",
            "Adoptarea tehnologiilor smart în construcții",
            "Focus pe materiale sustenabile și eco-friendly",
            "Digitalizarea proceselor de proiectare și execuție",
            "Cererea crescută pentru renovări post-pandemie"
        ]
        
        return trends

    def get_best_practices(self, services: List[Dict]) -> List[str]:
        """Obține best practices pentru serviciile identificate"""
        practices = [
            "Respectarea strictă a normelor de siguranță",
            "Utilizarea materialelor certificate",
            "Planificarea detaliată a proiectelor",
            "Comunicarea transparentă cu clienții",
            "Respectarea termenelor și bugetelor"
        ]
        
        return practices

    def save_agent_config(self, site_url: str, agent_config: Dict):
        """Salvează configurația agentului"""
        domain = tldextract.extract(site_url).top_domain_under_public_suffix.lower()
        
        try:
            # Verifică dacă agentul are embeddings și content
            has_embeddings = agent_config.get('embeddings_count', 0) > 0
            has_content = agent_config.get('pages_scraped', 0) > 0
            
            agent_record = {
                "domain": domain,
                "site_url": site_url,
                "agent_config": agent_config,
                "agent_type": "master",  # ✅ Marchează ca master agent
                "status": "validated" if has_embeddings else "created",  # ✅ validated dacă are embeddings
                "validation_passed": has_embeddings,  # ✅ IMPORTANT: Pentru a apărea în listă
                "has_content": has_content,  # ✅ Pentru filtrare
                "has_embeddings": has_embeddings,  # ✅ Pentru filtrare
                "pages_indexed": agent_config.get('pages_scraped', 0),
                "chunks_indexed": agent_config.get('embeddings_count', 0),
                "vector_collection": f"construction_{domain.replace('.', '_')}",  # ✅ Referință la Qdrant
                "created_at": datetime.now(),
                "last_updated": datetime.now()
            }
            
            self.agents_collection.replace_one(
                {"domain": domain},
                agent_record,
                upsert=True
            )
            
            print(f"✅ Configurație agent salvată pentru {domain}")
            print(f"   Has embeddings: {has_embeddings}")
            print(f"   Has content: {has_content}")
            print(f"   Status: {agent_record['status']}")
            
        except Exception as e:
            print(f"⚠️ Eroare salvare agent: {e}")

def main():
    parser = argparse.ArgumentParser(description='Construction Agent Creator')
    parser.add_argument('--url', required=True, help='URL site construcții')
    parser.add_argument('--mode', choices=['analyze', 'create_agent'], required=True, help='Modul de funcționare')
    
    args = parser.parse_args()
    
    creator = ConstructionAgentCreator()
    
    if args.mode == 'analyze':
        result = creator.analyze_construction_site(args.url)
        print("\n🏗️ ANALIZĂ COMPLETĂ:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    elif args.mode == 'create_agent':
        agent_config = creator.create_site_agent(args.url)
        print("\n🤖 AGENT CREAT:")
        print(json.dumps(agent_config, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
