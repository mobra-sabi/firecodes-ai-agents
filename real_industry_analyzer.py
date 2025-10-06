#!/usr/bin/env python3
import sys
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__)))

from hybrid_intelligence.chatgpt_qwen_pipeline import ChatGPTQwenHybridPipeline
from database.mongodb_handler import MongoDBHandler
import requests

class RealIndustryAnalyzer:
    def __init__(self):
        self.hybrid_pipeline = ChatGPTQwenHybridPipeline()
        self.mongodb = MongoDBHandler()
        
    async def real_analysis_with_active_clusters(self, site_url):
        """Analiză REALĂ folosind clusterele Qwen active"""
        
        print(f"🎯 ANALIZĂ REALĂ pentru {site_url}")
        print("=" * 50)
        
        # 1. Verifică ce clustere sunt active
        cluster_health = self.hybrid_pipeline.check_cluster_health()
        active_clusters = [name for name, health in cluster_health.items() 
                          if health['status'] == 'healthy']
        
        print(f"⚡ Clustere active: {len(active_clusters)}")
        for cluster in active_clusters:
            print(f"  ✅ {cluster}")
            
        if len(active_clusters) < 2:
            print("❌ Nu sunt suficiente clustere pentru analiză reală")
            return None
            
        # 2. Obține conținutul site-ului
        site_content = self.mongodb.get_site_content(site_url)
        if not site_content:
            print(f"❌ Nu există conținut pentru {site_url} în baza de date")
            return None
            
        # 3. ChatGPT Strategic Analysis (REAL)
        print("\n🧠 ChatGPT: Analiză strategică REALĂ...")
        strategic_analysis = await self.real_chatgpt_analysis(site_url, site_content['content'])
        
        # 4. Qwen Clusters Processing (REAL)
        print("\n⚡ Qwen Clusters: Procesare REALĂ...")
        qwen_results = await self.real_qwen_processing(site_content['content'], active_clusters)
        
        # 5. ChatGPT Synthesis (REAL)
        print("\n🎯 ChatGPT: Sinteză REALĂ...")
        final_strategy = await self.real_chatgpt_synthesis(strategic_analysis, qwen_results)
        
        return {
            'site_url': site_url,
            'strategic_analysis': strategic_analysis,
            'qwen_processing': qwen_results,
            'final_strategy': final_strategy,
            'active_clusters_used': active_clusters
        }
        
    async def real_chatgpt_analysis(self, site_url, content):
        """ChatGPT analiză strategică REALĂ"""
        
        try:
            response = await self.hybrid_pipeline.chatgpt_client.chat.completions.acreate(
                model="gpt-4",
                messages=[{
                    "role": "user",
                    "content": f"""ANALIZĂ STRATEGICĂ REALĂ pentru site-ul: {site_url}

Conținut site: {content[:2000]}

Ca expert senior în business intelligence, analizează și oferă:

1. IDENTIFICAREA INDUSTRIEI
   - Industria primară și secundară
   - Poziția în value chain
   - Dimensiunea estimată a pieței

2. ANALIZA COMPETITIVĂ
   - Tipuri de competitori direcți
   - Competitori indirecți
   - Bariere de intrare în piață

3. STRATEGIA DE RESEARCH
   - Keywords pentru căutarea competitorilor
   - Surse de date prioritare
   - Metodologia de monitoring

4. OPORTUNITĂȚI IDENTIFICATE
   - Gap-uri în piață
   - Segmente neexploatate
   - Potențial de parteneriat

Oferă analiză detaliată și actionable pentru fiecare punct."""
                }],
                temperature=0.3,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Eroare ChatGPT: {str(e)}"
        
    async def real_qwen_processing(self, content, active_clusters):
        """Procesare REALĂ cu clusterele Qwen active"""
        
        processing_results = {}
        
        for cluster_name in active_clusters[:3]:  # Folosește primele 3 clustere active
            
            cluster_url = self.hybrid_pipeline.qwen_clusters[cluster_name]
            
            # Prompt specializat pentru fiecare cluster
            specialized_prompts = {
                'content_analysis': f"""Ca specialist în analiza conținutului, extrage din acest site:
                
SERVICII SPECIFICE:
PROCESE DE BUSINESS:
AVANTAJE COMPETITIVE:
TARGET MARKET:
TEHNOLOGII FOLOSITE:

Conținut: {content[:1000]}

Răspunde structurat și detaliat.""",

                'customer_service': f"""Ca expert în customer experience, analizează:
                
TIPURI DE CLIENȚI:
NEVOILE CLIENTULUI:
PROCESUL DE VÂNZARE:
PUNCTE DE CONTACT:
OPPORTUNITIES DE ÎMBUNĂTĂȚIRE:

Conținut: {content[:1000]}

Oferă insights actionabile.""",

                'predictive_analytics': f"""Ca analist de piață, oferă:
                
TREND-URI INDUSTRIEI:
PREVIZIUNI PIAȚĂ:
RISCURI IDENTIFICATE:
OPORTUNITĂȚI VIITOARE:
RECOMANDĂRI STRATEGICE:

Conținut: {content[:1000]}

Bazează-te pe date și evidențe."""
            }
            
            prompt = specialized_prompts.get(cluster_name, f"Analizează acest conținut: {content[:800]}")
            
            try:
                print(f"  🔄 Procesez cu {cluster_name}...")
                
                payload = {
                    "model": "Qwen/Qwen2.5-7B-Instruct",
                    "messages": [
                        {"role": "system", "content": f"Ești specialist în {cluster_name}."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 600,
                    "temperature": 0.2
                }
                
                response = requests.post(f"{cluster_url}/v1/chat/completions", 
                                       json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()['choices'][0]['message']['content']
                    processing_results[cluster_name] = result
                    print(f"    ✅ {cluster_name} completat")
                else:
                    processing_results[cluster_name] = f"Eroare HTTP {response.status_code}"
                    print(f"    ❌ {cluster_name} eșuat")
                    
            except Exception as e:
                processing_results[cluster_name] = f"Eroare: {str(e)}"
                print(f"    ❌ {cluster_name} eroare: {e}")
                
        return processing_results
        
    async def real_chatgpt_synthesis(self, strategic_analysis, qwen_results):
        """Sinteza REALĂ cu ChatGPT"""
        
        qwen_summary = ""
        for cluster, result in qwen_results.items():
            qwen_summary += f"\n{cluster.upper()}: {result[:300]}...\n"
        
        try:
            response = await self.hybrid_pipeline.chatgpt_client.chat.completions.acreate(
                model="gpt-4",
                messages=[{
                    "role": "user", 
                    "content": f"""SINTEZĂ FINALĂ - Business Intelligence Strategy

ANALIZA STRATEGICĂ INIȚIALĂ:
{strategic_analysis}

PROCESARE SPECIALIZATĂ QWEN:
{qwen_summary}

Ca expert senior în consultanță strategică, creează un PLAN DE ACȚIUNE FINAL care să includă:

1. EXECUTIVE SUMMARY
   - Key findings prioritare
   - Recomandări immediate (30 zile)

2. COMPETITIVE INTELLIGENCE ROADMAP
   - Lista exactă de competitori de monitorizat
   - Tools și procese de tracking
   - Alert systems recomandate

3. MARKET OPPORTUNITY PLAN
   - Top 3 oportunități cu impact maxim
   - Resurse necesare pentru fiecare
   - Timeline de implementare

4. AUTOMATION STRATEGY
   - Procese de automatizat cu AI
   - KPI-uri de urmărit
   - Success metrics

Focusează-te pe ACȚIUNI CONCRETE și REZULTATE MĂSURABILE."""
                }],
                temperature=0.2,
                max_tokens=2500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Eroare în sinteza finală: {str(e)}"

async def main():
    analyzer = RealIndustryAnalyzer()
    
    print("🎯 REAL INDUSTRY ANALYZER")
    print("=" * 30)
    
    site_url = input("Site URL pentru analiză reală: ").strip()
    if not site_url:
        site_url = "https://tehnica-antifoc.ro/"
        
    result = await analyzer.real_analysis_with_active_clusters(site_url)
    
    if result:
        print("\n" + "="*80)
        print("📊 REZULTATE ANALIZĂ REALĂ")
        print("="*80)
        print(f"\n🧠 STRATEGIC ANALYSIS:\n{result['strategic_analysis']}")
        print(f"\n⚡ QWEN PROCESSING:")
        for cluster, analysis in result['qwen_processing'].items():
            print(f"\n  {cluster.upper()}: {analysis[:200]}...")
        print(f"\n🎯 FINAL STRATEGY:\n{result['final_strategy']}")

if __name__ == "__main__":
    asyncio.run(main())
