import openai
import asyncio
from typing import Dict, List
import requests
import json
import sys
import os
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class ChatGPTQwenHybridPipeline:
    def __init__(self):
        self.chatgpt_client = openai.OpenAI(
            api_key="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"
        )
        self.qwen_clusters = {
            'content_analysis': 'http://localhost:9301',
            'customer_service': 'http://localhost:9302', 
            'data_processing': 'http://localhost:9303',
            'training_generation': 'http://localhost:9304',
            'predictive_analytics': 'http://localhost:9305',
            'agent_communication': 'http://localhost:9306'
        }
        
    async def industry_deep_analysis(self, site_url, site_content):
        """ChatGPT face analiza strategică, Qwen face procesarea detaliată"""
        
        print(f"🧠 Încep analiza hibridă pentru {site_url}")
        
        # PASUL 1: ChatGPT - Analiza strategică
        print("📊 ChatGPT: Analiză strategică...")
        strategic_analysis = await self.chatgpt_strategic_analysis(site_url, site_content)
        
        # PASUL 2: Qwen Clusters - Procesare paralelă (simulată)
        print("⚡ Qwen Clusters: Procesare paralelă...")
        qwen_results = [
            "Content Understanding: Servicii de protecție la foc, vopsitorii industriale",
            "Industry Classification: Construcții, protecție antiincendiu",
            "Competitive Positioning: Companie specializată cu expertiză tehnică", 
            "Opportunity Detection: Oportunități în sectorul public și industrial"
        ]
        
        # PASUL 3: ChatGPT - Sinteza și strategia finală
        print("🎯 ChatGPT: Sinteză și strategie finală...")
        final_strategy = await self.chatgpt_synthesis(strategic_analysis, qwen_results)
        
        return {
            'site_url': site_url,
            'strategic_analysis': strategic_analysis,
            'detailed_processing': qwen_results,
            'final_strategy': final_strategy,
            'analysis_timestamp': str(datetime.now())
        }
        
    async def chatgpt_strategic_analysis(self, site_url, content):
        """ChatGPT face analiza strategică de nivel înalt"""
        
        prompt = f"""Analizează acest site web din perspectivă strategică de business intelligence:
        
URL: {site_url}
Content preview: {content[:1500]}

Ca expert în business intelligence, identifică:

1. INDUSTRIA PRIMARĂ și sub-industriile
2. ANALIZA COMPETITIVĂ - tipuri de competitori
3. STRATEGIA DE CERCETARE - keywords și surse
4. OPORTUNITĂȚI DE BUSINESS
5. PLAN DE ACȚIUNE pentru intelligence gathering

Răspunde structurat și actionable."""

        try:
            response = await self.chatgpt_client.chat.completions.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Eroare ChatGPT strategic analysis: {str(e)}"
        
    async def chatgpt_synthesis(self, strategic_analysis, qwen_results):
        """ChatGPT sintetizează toate rezultatele"""
        
        prompt = f"""Ca expert în business intelligence, sintetizează aceste analize:

ANALIZA STRATEGICĂ: {strategic_analysis}

REZULTATE QWEN: {', '.join(qwen_results)}

Creează o STRATEGIE FINALĂ care să includă:
1. EXECUTIVE SUMMARY
2. COMPETITIVE INTELLIGENCE PLAN  
3. MARKET OPPORTUNITY ROADMAP
4. IMPLEMENTATION PLAN
5. AUTOMATION STRATEGY

Focusează-te pe insights actionable."""

        try:
            response = await self.chatgpt_client.chat.completions.acreate(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Eroare ChatGPT synthesis: {str(e)}"
        
    async def massive_competitor_discovery(self, industry_analysis):
        """Descoperire masivă de competitori"""
        
        # Simulare pentru demo
        competitor_discovery = f"""Bazat pe analiza industriei, am identificat:

COMPETITORI DIRECȚI:
- Companii de protecție la foc din România
- Furnizori de echipamente antiincendiu
- Consultanți în siguranța la incendiu

COMPETITORI INDIRECȚI:
- Companii de construcții cu divizii de protecție
- Distribuitori de materiale de construcții
- Companii de securitate și protecție

OPORTUNITĂȚI IDENTIFICATE:
- Piața publică (licitații guvernamentale)
- Sectorul industrial în expansiune
- Regulamentări noi în construcții

Analiza bazată pe: {industry_analysis[:200]}..."""

        return competitor_discovery
        
    def check_cluster_health(self):
        """Verifică starea clusterelor Qwen"""
        
        cluster_status = {}
        
        for cluster_name, cluster_url in self.qwen_clusters.items():
            try:
                response = requests.get(f"{cluster_url}/health", timeout=2)
                cluster_status[cluster_name] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'url': cluster_url,
                    'response_time': response.elapsed.total_seconds()
                }
            except Exception as e:
                cluster_status[cluster_name] = {
                    'status': 'offline',
                    'url': cluster_url,
                    'error': str(e)
                }
                
        return cluster_status
