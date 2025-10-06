#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from real_industry_analyzer_fixed import RealIndustryAnalyzerFixed
from database.mongodb_handler import MongoDBHandler

class BusinessIntelligenceDashboard:
    def __init__(self):
        self.analyzer = RealIndustryAnalyzerFixed()
        self.mongodb = MongoDBHandler()
        
    async def run_bi_dashboard(self):
        print("📊 BUSINESS INTELLIGENCE DASHBOARD")
        print("=" * 50)
        
        while True:
            print("\n🎯 BI Options:")
            print("1. 🔍 Analizează site nou")
            print("2. 📋 Compară mai multe site-uri")
            print("3. 📈 Trends de industrie")
            print("4. 🎯 Export raport PDF")
            print("5. 🚪 Ieși")
            
            choice = input("\nAlege (1-5): ").strip()
            
            if choice == "1":
                site_url = input("🌐 Site pentru analiză: ")
                await self.analyze_single_site(site_url)
            elif choice == "2":
                await self.compare_multiple_sites()
            elif choice == "3":
                await self.industry_trends()
            elif choice == "4":
                await self.export_pdf_report()
            elif choice == "5":
                break
                
    async def analyze_single_site(self, site_url):
        result = await self.analyzer.real_analysis_with_active_clusters(site_url)
        if result:
            print("✅ Analiză completă - rezultate afișate mai sus")
            
    async def compare_multiple_sites(self):
        print("🔄 Funcție în dezvoltare - comparație multiple site-uri")
        
    async def industry_trends(self):
        print("📈 Funcție în dezvoltare - trends de industrie")
        
    async def export_pdf_report(self):
        print("📄 Funcție în dezvoltare - export PDF")

if __name__ == "__main__":
    dashboard = BusinessIntelligenceDashboard()
    asyncio.run(dashboard.run_bi_dashboard())
