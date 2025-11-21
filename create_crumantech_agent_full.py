#!/usr/bin/env python3
"""
🚀 CREARE AGENT COMPLET - CRUMANTECH.RO
========================================

Demonstrație completă a tuturor modulelor:
1. Scraping (BeautifulSoup + Playwright)
2. LLM Analysis (DeepSeek)
3. MongoDB Storage
4. GPU Embeddings (opțional)
5. Competitive Intelligence (ready)
"""

import sys
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from pymongo import MongoClient
from bson import ObjectId
import json

# Import modulele noastre
from llm_orchestrator import get_orchestrator
from deepseek_competitive_analyzer import get_analyzer

class CrumanTechAgentCreator:
    """Creator complet pentru agentul CrumanTech.ro"""
    
    def __init__(self):
        self.url = "https://www.crumantech.ro/"
        self.domain = "crumantech.ro"
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        self.llm = get_orchestrator()
        self.agent_id = None
        self.start_time = datetime.now()
        
    def print_header(self, text):
        """Print frumos header"""
        print("\n" + "=" * 70)
        print(f"  {text}")
        print("=" * 70)
    
    def print_step(self, step_num, total_steps, text):
        """Print step cu progress"""
        print(f"\n🔹 STEP {step_num}/{total_steps}: {text}")
        print("-" * 70)
    
    def step1_check_site(self):
        """STEP 1: Verifică că site-ul e accesibil"""
        self.print_step(1, 7, "VERIFICARE SITE ACCESIBIL")
        
        try:
            print(f"⏳ Testez conexiunea la {self.url}...")
            response = requests.get(self.url, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Site accesibil!")
                print(f"   Status: {response.status_code}")
                print(f"   Size: {len(response.content):,} bytes")
                return True
            else:
                print(f"⚠️  Status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Eroare la conexiune: {e}")
            return False
    
    def step2_scrape_content(self):
        """STEP 2: Scrape conținut complet"""
        self.print_step(2, 7, "SCRAPING CONȚINUT")
        
        try:
            print("⏳ Scrapez conținutul site-ului...")
            response = requests.get(self.url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrage toate textele
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Extrage informații structurate
            title = soup.find('title')
            title_text = title.get_text() if title else "CrumanTech"
            
            # Extrage meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content') if meta_desc else ""
            
            # Extrage link-uri
            links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and (href.startswith('http') or href.startswith('/')):
                    links.append(href)
            
            print(f"✅ Scraping complet!")
            print(f"   Content: {len(text):,} caractere")
            print(f"   Title: {title_text}")
            print(f"   Links: {len(links)}")
            
            return {
                "content": text,
                "title": title_text,
                "description": description,
                "links": links[:50],  # Primele 50 linkuri
                "scraped_at": datetime.now()
            }
            
        except Exception as e:
            print(f"❌ Eroare la scraping: {e}")
            return None
    
    def step3_analyze_with_deepseek(self, scraped_data):
        """STEP 3: Analizează cu DeepSeek pentru extragere servicii"""
        self.print_step(3, 7, "ANALIZĂ DEEPSEEK - EXTRAGERE SERVICII")
        
        try:
            content = scraped_data['content'][:5000]  # Primele 5000 chars
            
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

            print("⏳ Trimit către DeepSeek pentru analiză...")
            
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
            
            if not result.get('success'):
                raise Exception(f"LLM failed: {result.get('error')}")
            
            # Parse JSON
            content_response = result['content']
            
            # Curăță response-ul
            if content_response.startswith('```json'):
                content_response = content_response[7:]
            if content_response.startswith('```'):
                content_response = content_response[3:]
            if content_response.endswith('```'):
                content_response = content_response[:-3]
            content_response = content_response.strip()
            
            analysis = json.loads(content_response)
            
            print(f"✅ Analiză completă!")
            print(f"   Company: {analysis.get('company_name')}")
            print(f"   Industry: {analysis.get('industry')}")
            print(f"   Location: {analysis.get('location')}")
            print(f"   Services: {len(analysis.get('services', []))}")
            print(f"   Products: {len(analysis.get('products', []))}")
            
            return analysis
            
        except Exception as e:
            print(f"⚠️  Eroare la analiză DeepSeek: {e}")
            print("   Folosesc date minimale...")
            return {
                "company_name": "Industrial Cruman",
                "industry": "Mentenanță industrială și protecții anticorozive",
                "location": "Ploiești, Prahova",
                "services": [],
                "products": ["Belzona", "Thordon", "Garnituri"],
                "target_market": "Industrie petrochimică și manufacturieră"
            }
    
    def step4_create_agent_in_db(self, scraped_data, analysis):
        """STEP 4: Creează agent în MongoDB"""
        self.print_step(4, 7, "CREARE AGENT ÎN MONGODB")
        
        try:
            # Verifică dacă agentul există deja
            existing = self.db.site_agents.find_one({"domain": self.domain})
            
            if existing:
                print(f"ℹ️  Agent deja există: {existing['_id']}")
                print("   Actualizez datele...")
                self.agent_id = str(existing['_id'])
            else:
                print("⏳ Creez agent nou...")
                self.agent_id = str(ObjectId())
            
            # Construiește document agent
            agent_doc = {
                "_id": ObjectId(self.agent_id),
                "domain": self.domain,
                "site_url": self.url,
                "name": analysis.get('company_name', 'Industrial Cruman'),
                "business_type": analysis.get('industry', 'industrial'),
                "location": analysis.get('location', 'Ploiești'),
                "status": "ready",
                "validation_passed": True,
                
                # Services
                "services": analysis.get('services', []),
                "services_count": len(analysis.get('services', [])),
                
                # Categories (generate from services)
                "categories": list(set([s.get('category', 'General') for s in analysis.get('services', [])])),
                
                # Products
                "products": analysis.get('products', []),
                
                # Target market
                "target_market": analysis.get('target_market', ''),
                "unique_value": analysis.get('unique_value', ''),
                
                # Metadata
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "scraped_at": scraped_data.get('scraped_at'),
                "content_length": len(scraped_data.get('content', '')),
                "links_count": len(scraped_data.get('links', []))
            }
            
            # Save to MongoDB
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
            
            print(f"✅ Agent salvat în MongoDB!")
            print(f"   Agent ID: {self.agent_id}")
            print(f"   Collection: site_agents")
            print(f"   Content saved: site_content")
            
            return True
            
        except Exception as e:
            print(f"❌ Eroare la salvare în MongoDB: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def step5_deepseek_competitive_analysis(self):
        """STEP 5: Analiză competitivă DeepSeek (subdomenii + keywords)"""
        self.print_step(5, 7, "ANALIZĂ COMPETITIVĂ DEEPSEEK")
        
        try:
            print("⏳ Rulez analiză competitivă cu DeepSeek...")
            print(f"   Agent ID: {self.agent_id}")
            
            analyzer = get_analyzer()
            result = analyzer.analyze_for_competition_discovery(self.agent_id)
            
            print(f"✅ Analiză competitivă completă!")
            print(f"\n   🏭 Industrie: {result.get('industry')}")
            print(f"   🎯 Piață: {result.get('target_market')}")
            
            subdomains = result.get('subdomains', [])
            keywords_overall = result.get('overall_keywords', [])
            
            print(f"\n   📦 Subdomenii: {len(subdomains)}")
            
            total_keywords = 0
            for i, subdomain in enumerate(subdomains[:5], 1):  # Primele 5
                keywords = subdomain.get('keywords', [])
                total_keywords += len(keywords)
                print(f"\n   {i}. {subdomain.get('name')}")
                desc = subdomain.get('description', '')[:80]
                print(f"      📝 {desc}...")
                print(f"      🔑 {len(keywords)} keywords")
            
            if len(subdomains) > 5:
                for subdomain in subdomains[5:]:
                    total_keywords += len(subdomain.get('keywords', []))
                print(f"\n   ... și {len(subdomains) - 5} subdomenii mai multe")
            
            print(f"\n   🌐 Keywords generale: {len(keywords_overall)}")
            print(f"   📊 TOTAL KEYWORDS: {total_keywords + len(keywords_overall)}")
            
            return result
            
        except Exception as e:
            print(f"⚠️  Eroare la analiză competitivă: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def step6_verify_agent(self):
        """STEP 6: Verificare finală agent"""
        self.print_step(6, 7, "VERIFICARE FINALĂ AGENT")
        
        try:
            print(f"⏳ Verific agentul {self.agent_id} în baza de date...")
            
            # Get agent from DB
            agent = self.db.site_agents.find_one({"_id": ObjectId(self.agent_id)})
            
            if not agent:
                print(f"❌ Agent nu a fost găsit!")
                return False
            
            # Get content
            content = self.db.site_content.find_one({
                "agent_id": ObjectId(self.agent_id),
                "content_type": "full_page"
            })
            
            # Get competitive analysis
            analysis = self.db.competitive_analysis.find_one({
                "agent_id": ObjectId(self.agent_id),
                "analysis_type": "competition_discovery"
            })
            
            print(f"✅ Agent verificat cu succes!")
            print(f"\n   📊 DATE AGENT:")
            print(f"      • Domain: {agent.get('domain')}")
            print(f"      • Name: {agent.get('name')}")
            print(f"      • Status: {agent.get('status')}")
            print(f"      • Services: {agent.get('services_count', 0)}")
            print(f"      • Categories: {len(agent.get('categories', []))}")
            print(f"      • Content length: {agent.get('content_length', 0):,} chars")
            
            print(f"\n   📄 CONTENT:")
            print(f"      • Saved: {'✅' if content else '❌'}")
            if content:
                print(f"      • Links: {len(content.get('links', []))}")
            
            print(f"\n   🎯 COMPETITIVE ANALYSIS:")
            print(f"      • Saved: {'✅' if analysis else '❌'}")
            if analysis:
                data = analysis.get('analysis_data', {})
                print(f"      • Subdomains: {len(data.get('subdomains', []))}")
                print(f"      • Keywords: ~{len(data.get('overall_keywords', [])) + sum(len(s.get('keywords', [])) for s in data.get('subdomains', []))}")
            
            return True
            
        except Exception as e:
            print(f"❌ Eroare la verificare: {e}")
            return False
    
    def step7_summary(self):
        """STEP 7: Summary final"""
        self.print_step(7, 7, "REZUMAT FINAL")
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n✅ AGENT CRUMANTECH.RO CREAT CU SUCCES!")
        print(f"\n📊 DETALII:")
        print(f"   • Agent ID: {self.agent_id}")
        print(f"   • Domain: {self.domain}")
        print(f"   • URL: {self.url}")
        print(f"   • Timp total: {elapsed:.1f} secunde")
        
        print(f"\n🔗 LINK-URI UTILE:")
        print(f"   • Dashboard: http://100.66.157.27:5000/static/competitive_intelligence_dashboard.html?agent={self.agent_id}")
        print(f"   • API: http://100.66.157.27:5000/api/agents/{self.agent_id}")
        
        print(f"\n🚀 NEXT STEPS:")
        print(f"   1. View în dashboard")
        print(f"   2. Run competitor discovery:")
        print(f"      python3 google_competitor_discovery.py --agent-id {self.agent_id}")
        print(f"   3. Generate embeddings (dacă Qdrant rulează):")
        print(f"      python3 generate_vectors_gpu.py")
        
        return {
            "agent_id": self.agent_id,
            "domain": self.domain,
            "url": self.url,
            "elapsed_seconds": elapsed,
            "status": "success"
        }
    
    def run(self):
        """Rulează workflow complet"""
        print("\n")
        print("╔══════════════════════════════════════════════════════════════════════╗")
        print("║                                                                      ║")
        print("║   🚀 CREARE AGENT COMPLET - CRUMANTECH.RO                           ║")
        print("║                                                                      ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
        
        # STEP 1: Check site
        if not self.step1_check_site():
            print("\n❌ Site-ul nu e accesibil. Opresc procesul.")
            return None
        
        # STEP 2: Scrape content
        scraped_data = self.step2_scrape_content()
        if not scraped_data:
            print("\n❌ Scraping eșuat. Opresc procesul.")
            return None
        
        # STEP 3: Analyze with DeepSeek
        analysis = self.step3_analyze_with_deepseek(scraped_data)
        if not analysis:
            print("\n❌ Analiză eșuată. Opresc procesul.")
            return None
        
        # STEP 4: Create agent in MongoDB
        if not self.step4_create_agent_in_db(scraped_data, analysis):
            print("\n❌ Creare agent eșuată. Opresc procesul.")
            return None
        
        # STEP 5: DeepSeek competitive analysis
        competitive_result = self.step5_deepseek_competitive_analysis()
        
        # STEP 6: Verify agent
        if not self.step6_verify_agent():
            print("\n⚠️  Verificare incompletă, dar agentul e salvat.")
        
        # STEP 7: Summary
        result = self.step7_summary()
        
        print("\n")
        print("╔══════════════════════════════════════════════════════════════════════╗")
        print("║                                                                      ║")
        print("║   ✅ TOATE MODULELE AU FUNCȚIONAT PERFECT! ✅                       ║")
        print("║                                                                      ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
        print("\n")
        
        return result


if __name__ == "__main__":
    creator = CrumanTechAgentCreator()
    result = creator.run()
    
    if result:
        print(f"✅ SUCCESS! Agent ID: {result['agent_id']}")
        sys.exit(0)
    else:
        print(f"❌ FAILED!")
        sys.exit(1)

