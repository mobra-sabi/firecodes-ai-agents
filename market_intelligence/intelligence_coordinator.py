import asyncio
import sys
import os
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from hybrid_intelligence.chatgpt_qwen_pipeline import ChatGPTQwenHybridPipeline
from database.mongodb_handler import MongoDBHandler

class IntelligenceCoordinator:
    """Coordonator principal pentru intelligence de piață"""
    
    def __init__(self):
        self.hybrid_pipeline = ChatGPTQwenHybridPipeline()
        self.mongodb = MongoDBHandler()
        
    async def full_industry_analysis(self, seed_site_url):
        """Analiză completă de industrie pornind de la un site seed"""
        
        print(f"🎯 Încep analiza completă pentru {seed_site_url}")
        
        # 1. Obține conținutul site-ului seed
        site_content = self.mongodb.get_site_content(seed_site_url)
        
        if not site_content:
            print(f"❌ Nu găsesc conținutul pentru {seed_site_url} în baza de date")
            return None
            
        # 2. Analiză hibridă ChatGPT + Qwen
        industry_analysis = await self.hybrid_pipeline.industry_deep_analysis(
            seed_site_url, 
            site_content['content']
        )
        
        # 3. Descoperire masivă de competitori
        competitor_discovery = await self.hybrid_pipeline.massive_competitor_discovery(
            industry_analysis['strategic_analysis']
        )
        
        # 4. Salvează rezultatele
        analysis_result = {
            'seed_site_url': seed_site_url,
            'industry_analysis': industry_analysis,
            'competitor_discovery': competitor_discovery,
            'analysis_timestamp': str(datetime.now())
        }
        
        # Salvează în MongoDB
        try:
            collection = self.mongodb.db['industry_intelligence']
            collection.insert_one(analysis_result)
            print("✅ Rezultatele analizei salvate în baza de date")
        except Exception as e:
            print(f"⚠️ Eroare la salvarea rezultatelor: {e}")
            
        return analysis_result
        
    def display_analysis_summary(self, analysis_result):
        """Afișează sumar al analizei"""
        
        if not analysis_result:
            print("❌ Nu există rezultate de afișat")
            return
            
        print("\n" + "="*80)
        print(f"📊 INDUSTRY INTELLIGENCE SUMMARY pentru {analysis_result['seed_site_url']}")
        print("="*80)
        
        # Strategic Analysis Summary
        strategic = analysis_result['industry_analysis']['strategic_analysis']
        print(f"\n🧠 STRATEGIC ANALYSIS (ChatGPT):")
        print(f"   {strategic[:300]}...")
        
        # Detailed Processing Summary
        detailed = analysis_result['industry_analysis']['detailed_processing']
        print(f"\n⚡ DETAILED PROCESSING (Qwen Clusters):")
        
        for i, detail in enumerate(detailed, 1):
            print(f"   {i}. {detail}")
        
        # Final Strategy Summary
        final_strategy = analysis_result['industry_analysis']['final_strategy']
        print(f"\n🎯 FINAL STRATEGY (ChatGPT Synthesis):")
        print(f"   {final_strategy[:400]}...")
        
        # Competitor Discovery Summary
        competitor_disc = analysis_result['competitor_discovery']
        print(f"\n🔍 COMPETITOR DISCOVERY:")
        print(f"   {competitor_disc[:300]}...")
        
        print("\n" + "="*80)

async def main():
    """Test principal pentru Intelligence Coordinator"""
    
    coordinator = IntelligenceCoordinator()
    
    print("🎯 MARKET INTELLIGENCE COORDINATOR")
    print("=" * 50)
    
    # Test cu site-ul existent
    test_site = "https://tehnica-antifoc.ro/"
    
    print(f"🧪 Testez cu site-ul: {test_site}")
    
    # Rulează analiza completă
    analysis_result = await coordinator.full_industry_analysis(test_site)
    
    if analysis_result:
        # Afișează sumarul
        coordinator.display_analysis_summary(analysis_result)
    else:
        print("❌ Analiza a eșuat")

if __name__ == "__main__":
    asyncio.run(main())
