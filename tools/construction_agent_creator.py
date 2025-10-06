#!/usr/bin/env python3
import os, sys, json, argparse, re, time
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
from datetime import datetime
import asyncio

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
    def __init__(self):
        # AI Models
        self.gpt4 = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.qwen = openai.OpenAI(base_url="http://localhost:9301/v1", api_key="local-vllm")
        
        # Databases
        self.qdrant = QdrantClient("localhost", port=6333)
        self.mongo = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo.construction_intelligence
        
        # Collections
        self.sites_collection = self.db.company_sites
        self.services_collection = self.db.construction_services
        self.competitors_collection = self.db.competitors
        self.regulations_collection = self.db.regulations
        self.agents_collection = self.db.site_agents
        
        # Embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
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

    def analyze_construction_site(self, site_url: str) -> Dict:
        """Analizează un site de construcții și identifică serviciile"""
        print(f"🔍 Analizez site-ul de construcții: {site_url}")
        
        # Scraping complet site
        site_data = self.scrape_construction_site(site_url)
        
        # GPT-4 analizează și categorisează serviciile
        services_analysis = self.gpt4_analyze_construction_services(site_data, site_url)
        
        # Salvează în baza de date
        self.save_site_analysis(site_url, site_data, services_analysis)
        
        return services_analysis

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

    def scrape_single_page(self, url: str, headers: dict) -> Optional[Dict]:
        """Scraping pentru o singură pagină cu focus pe construcții"""
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
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
            resp = self.gpt4.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            
            content = resp.choices[0].message.content.strip()
            content = re.sub(r'^```[a-z]*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
            
            analysis = json.loads(content)
            print("✅ GPT-4 a analizat serviciile de construcții")
            return analysis
            
        except Exception as e:
            print(f"⚠️ Eroare GPT-4 analiză: {e}")
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
            
            # Creează embeddings pentru Qdrant
            self.create_site_embeddings(domain, site_data, analysis)
            
            print(f"✅ Analiză salvată pentru {domain}")
            
        except Exception as e:
            print(f"⚠️ Eroare salvare analiză: {e}")

    def create_site_embeddings(self, domain: str, site_data: Dict, analysis: Dict):
        """Creează embeddings pentru site și analiză"""
        try:
            # Text pentru embedding
            embedding_text = f"""
            {analysis.get('company_analysis', {}).get('company_name', '')}
            {' '.join([s.get('service_name', '') for s in analysis.get('services_identified', [])])}
            {' '.join([s.get('description', '') for s in analysis.get('services_identified', [])])}
            {analysis.get('company_analysis', {}).get('main_location', '')}
            """
            
            # Generează embedding
            embedding = self.embedding_model.encode(embedding_text).tolist()
            
            # Salvează în Qdrant
            point = PointStruct(
                id=hash(domain) % (2**63),
                vector=embedding,
                payload={
                    "domain": domain,
                    "company_name": analysis.get('company_analysis', {}).get('company_name', ''),
                    "services": [s.get('service_name', '') for s in analysis.get('services_identified', [])],
                    "categories": [s.get('category', '') for s in analysis.get('services_identified', [])],
                    "location": analysis.get('company_analysis', {}).get('main_location', ''),
                    "timestamp": time.time()
                }
            )
            
            self.qdrant.upsert(collection_name="construction_sites", points=[point])
            print(f"✅ Embeddings create pentru {domain}")
            
        except Exception as e:
            print(f"⚠️ Eroare creare embeddings: {e}")

    def create_site_agent(self, site_url: str) -> Dict:
        """Creează agentul AI specializat pentru site-ul de construcții"""
        print(f"🤖 Creez agent AI pentru site-ul: {site_url}")
        
        # Analizează site-ul
        analysis = self.analyze_construction_site(site_url)
        
        # Creează personalitatea agentului
        agent_config = self.create_agent_personality(analysis)
        
        # Salvează agentul
        self.save_agent_config(site_url, agent_config)
        
        print(f"✅ Agent AI creat pentru {site_url}")
        return agent_config

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
            agent_record = {
                "domain": domain,
                "site_url": site_url,
                "agent_config": agent_config,
                "agent_type": "construction_specialist",
                "status": "active",
                "created_at": datetime.now(),
                "last_updated": datetime.now()
            }
            
            self.agents_collection.replace_one(
                {"domain": domain},
                agent_record,
                upsert=True
            )
            
            print(f"✅ Configurație agent salvată pentru {domain}")
            
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
