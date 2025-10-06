#!/usr/bin/env python3
import sys
import urllib.parse
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__)))

from hybrid_intelligence.chatgpt_qwen_pipeline import ChatGPTQwenHybridPipeline
from database.mongodb_handler import MongoDBHandler
import requests
import openai

class RealIndustryAnalyzerFixed:




    def _fetch_page_text(self, url: str) -> str:

        try:

            resp = requests.get(url, timeout=45, headers={"User-Agent":"Mozilla/5.0"})

            html = resp.text

        except Exception:

            return None

        # strip scripts/styles and tags

        import re as _re

        html = _re.sub(r'<script[^>]*>.*?</script>|<style[^>]*>.*?</style>', ' ', html, flags=_re.I|_re.S)

        txt = _re.sub(r'<[^>]+>', ' ', html)

        txt = _re.sub(r'\s+', ' ', txt).strip()

        return txt or None


    def _normalize_url(self, url: str) -> list:

        u = url.strip()

        p = urllib.parse.urlparse(u)

        scheme = p.scheme or "https"

        domain = (p.netloc or "").lower().replace(":80", "").replace(":443", "")

        path = p.path or "/"

        base = f"{scheme}://{domain}"

        variants = {

            base,

            base + "/",

            f"{scheme}://{domain}{path}",

            f"{scheme}://{domain}{path}".rstrip("/"),

            f"https://{domain}",

            f"https://{domain}/",

            f"http://{domain}",

            f"http://{domain}/",

            f"https://{domain.replace('www.','')}",

            f"https://{domain.replace('www.','')}/",

        }

        return sorted(variants)


    def _find_site_content(self, site_url: str, db):

        variants = self._normalize_url(site_url)

        lowers = [v.lower() for v in variants]

        ors = [

            {"url": {"$in": variants}},

            {"site_url": {"$in": variants}},

            {"canonical_url": {"$in": variants}},

            {"lower_url": {"$in": lowers}},

        ]

        for coll in [

            "industry_sites_content",

            "site_contents",

            "web_content",

            "real_industry_web_content",

            "industry_web_content",

            "site_content",

            "pages",

        ]:

            doc = db[coll].find_one({"$or": ors})

            if doc:

                return doc.get("content") or doc.get("content_text") or doc.get("raw_text")

        return None


    def __init__(self):
        self.pred_client = openai.OpenAI(base_url="http://localhost:9306/v1", api_key=os.getenv("OPENAI_API_KEY", "local-vllm"))

        self.hybrid_pipeline = ChatGPTQwenHybridPipeline()
        self.mongodb = MongoDBHandler()
        # Fix ChatGPT client
        self.openai_client = openai.OpenAI(
            api_key="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"
        )
        
    async def real_analysis_with_active_clusters(self, site_url):
        """Analiză REALĂ folosind clusterele Qwen active"""
        
        print(f"🎯 ANALIZĂ REALĂ FIXATĂ pentru {site_url}")
        print("=" * 50)
        
        # 1. Verifică ce clustere sunt active
        cluster_health = self.hybrid_pipeline.check_cluster_health()
        active_clusters = [name for name, health in cluster_health.items() 
                          if health['status'] == 'healthy']
        
        print(f"⚡ Clustere active: {len(active_clusters)}")
        for cluster in active_clusters:
            print(f"  ✅ {cluster}")
            
        if len(active_clusters) < 1:
            print("❌ Nu sunt clustere active pentru analiză")
            return None
            
        # 2. Obține conținutul site-ului
        site_content = self.mongodb.get_site_content(site_url)
        if not site_content:
            print(f"❌ Nu există conținut pentru {site_url} în baza de date")
            return None
            
        # 3. ChatGPT Strategic Analysis (REAL - FIXED)
        print("\n🧠 ChatGPT: Analiză strategică REALĂ...")
        strategic_analysis = await self.real_chatgpt_analysis_fixed(site_url, site_content['content'])
        
        # 4. Qwen Clusters Processing (REAL)
        print("\n⚡ Qwen Clusters: Procesare REALĂ...")
        qwen_results = await self.real_qwen_processing(site_content['content'], active_clusters)
        
        # 5. ChatGPT Synthesis (REAL - FIXED)
        print("\n🎯 ChatGPT: Sinteză REALĂ...")
        final_strategy = await self.real_chatgpt_synthesis_fixed(strategic_analysis, qwen_results)
        
        return {
            'site_url': site_url,
            'strategic_analysis': strategic_analysis,
            'qwen_processing': qwen_results,
            'final_strategy': final_strategy,
            'active_clusters_used': active_clusters
        }
        
    async def real_chatgpt_analysis_fixed(self, site_url, content):
        """ChatGPT analiză strategică REALĂ - API FIXED"""
        
        try:
            # FIXED: folosește chat.completions.create în loc de acreate
            response = self.openai_client.chat.completions.create(
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

Oferă analiză detaliată și actionabile pentru fiecare punct."""
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
        
        # Limitează la primele 3 clustere active pentru a evita spam
        for cluster_name in active_clusters[:3]:
            
            cluster_url = self.hybrid_pipeline.qwen_clusters[cluster_name]
            
            # Prompt specializat pentru fiecare cluster
            specialized_prompts = {
                'content_analysis': f"""Ca specialist în analiza conținutului, extrage din acest site:
                
SERVICII SPECIFICE oferite:
PROCESE DE BUSINESS utilizate:
AVANTAJE COMPETITIVE identificate:
TARGET MARKET vizat:
TEHNOLOGII FOLOSITE:

Conținut: {content[:1000]}

Răspunde structurat și detaliat pentru fiecare categorie.""",

                'customer_service': f"""Ca expert în customer experience, analizează:
                
TIPURI DE CLIENȚI deserviți:
NEVOILE CLIENTULUI identificate:
PROCESUL DE VÂNZARE utilizat:
PUNCTE DE CONTACT disponibile:
OPORTUNITĂȚI DE ÎMBUNĂTĂȚIRE:

Conținut: {content[:1000]}

Oferă insights actionabile pentru fiecare punct.""",

                'predictive_analytics': f"""Ca analist de piață, oferă:
                
TREND-URI INDUSTRIEI observate:
PREVIZIUNI PIAȚĂ următorii 2 ani:
RISCURI IDENTIFICATE:
OPORTUNITĂȚI VIITOARE:
RECOMANDĂRI STRATEGICE:

Conținut: {content[:1000]}

Bazează-te pe date și evidențe concrete."""
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
                
                response = self.pred_client.chat.completions.create(model="Qwen/Qwen2.5-7B-Instruct", messages=[{"role":"system","content":"Predictive analytics assistant. Return concise, actionable insights."},{"role":"user","content":f"Using site content for {site_url}, predict demand trends, top risks, and recommended actions (bulleted)."}], temperature=0.2)
                
                if response.status_code == 200:
                    result = response.json()['choices'][0]['message']['content']
                    processing_results[cluster_name] = result
                    print(f"    ✅ {cluster_name} completat")
                else:
                    processing_results[cluster_name] = f"Eroare HTTP {response.status_code}"
                    print(f"    ❌ {cluster_name} eșuat - {response.status_code}")
                    
            except Exception as e:
                processing_results[cluster_name] = f"Eroare: {str(e)}"
                print(f"    ❌ {cluster_name} eroare: {e}")
                
        return processing_results
        
    async def real_chatgpt_synthesis_fixed(self, strategic_analysis, qwen_results):
        """Sinteza REALĂ cu ChatGPT - API FIXED"""
        
        qwen_summary = ""
        for cluster, result in qwen_results.items():
            qwen_summary += f"\n{cluster.upper()}: {result[:300]}...\n"
        
        try:
            # FIXED: folosește chat.completions.create în loc de acreate
            response = self.openai_client.chat.completions.create(
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
    analyzer = RealIndustryAnalyzerFixed()
    
    print("🎯 REAL INDUSTRY ANALYZER - FIXED VERSION")
    print("=" * 40)
    
    site_url = input("Site URL pentru analiză reală: ").strip()
    if not site_url:
        site_url = "https://tehnica-antifoc.ro/"
        
    result = await analyzer.real_analysis_with_active_clusters(site_url)
    
    if result:
        print("\n" + "="*80)
        print("📊 REZULTATE ANALIZĂ REALĂ - COMPLETE")
        print("="*80)
        print(f"\n🧠 STRATEGIC ANALYSIS (ChatGPT):\n{result['strategic_analysis']}")
        print(f"\n⚡ QWEN PROCESSING:")
        for cluster, analysis in result['qwen_processing'].items():
            print(f"\n  📋 {cluster.upper()}:\n{analysis[:500]}...")
        print(f"\n🎯 FINAL STRATEGY (ChatGPT):\n{result['final_strategy']}")
        print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(main())
