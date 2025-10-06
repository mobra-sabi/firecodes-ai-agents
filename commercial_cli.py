#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from optimized.smart_site_manager import SmartSiteManager
from agents.enhanced_commercial_agent import EnhancedCommercialAgent

def main():
    print("🎯 AI Commercial Agent System - Versiunea Avansată")
    print("=" * 60)
    
    site_manager = SmartSiteManager()
    
    while True:
        print("\n🚀 Opțiuni:")
        print("1. Adaugă site nou (procesare completă)")
        print("2. Chat comercial cu site existent")
        print("3. Dashboard comercial")
        print("4. Lista site-uri procesate")
        print("5. Ieși")
        
        choice = input("\nAlege (1-5): ").strip()
        
        if choice == "1":
            site_url = input("🌐 URL site nou: ").strip()
            if site_url:
                success = site_manager.process_site_smart(site_url)
                if success:
                    print(f"✅ Site {site_url} gata pentru chat comercial!")
                    
        elif choice == "2":
            site_url = input("🌐 URL site pentru chat comercial: ").strip()
            if site_url:
                agent = EnhancedCommercialAgent(site_url)
                
                if agent.site_context:
                    print(f"\n💼 Chat Comercial Activ cu {agent.site_context['title']}")
                    print("🎯 Agent inteligent pentru:")
                    print("   • Calculare oferte automate")
                    print("   • Programare întâlniri")
                    print("   • Generare propuneri")
                    print("   • Calificare leaduri")
                    print("📝 Scrie 'exit' pentru a ieși\n")
                    
                    conversation_count = 0
                    
                    while True:
                        question = input("❓ Tu: ").strip()
                        
                        if question.lower() in ['exit', 'ieși', 'quit']:
                            break
                            
                        if question:
                            print("🤖 Analizez cererea și generez răspuns comercial...")
                            
                            # Folosește agentul comercial îmbunătățit
                            answer = agent.enhanced_answer(question)
                            intent = agent.analyze_intent(question)
                            details = agent.extract_project_details(question)
                            
                            print(f"\n🤖 {agent.site_context['title']}: {answer}\n")
                            
                            # Salvează interacțiunea îmbunătățită
                            agent.save_enhanced_interaction(question, answer, intent, details)
                            
                            conversation_count += 1
                            
                            # Opțional: feedback și statistici
                            if conversation_count % 3 == 0:
                                feedback = input("👍 Cum evaluați conversația? (excelent/bun/slab/skip): ").strip()
                                if feedback != 'skip':
                                    print(f"✅ Feedback '{feedback}' înregistrat pentru îmbunătățiri!")
                else:
                    print(f"❌ Site {site_url} nu este în sistem. Adaugă-l mai întâi!")
                    
        elif choice == "3":
            print("\n📊 DASHBOARD COMERCIAL")
            print("=" * 40)
            
            try:
                from database.mongodb_handler import MongoDBHandler
                mongodb = MongoDBHandler()
                
                # Statistici rapide
                interactions = mongodb.db['enhanced_interactions'].count_documents({})
                quotes = mongodb.db['quotes'].count_documents({})
                appointments = mongodb.db['appointments'].count_documents({})
                proposals = mongodb.db['proposals'].count_documents({})
                
                print(f"💬 Total interacțiuni: {interactions}")
                print(f"💰 Oferte generate: {quotes}")
                print(f"📅 Întâlniri programate: {appointments}")
                print(f"📋 Propuneri create: {proposals}")
                
                # Leaduri calificate
                qualifications = list(mongodb.db['lead_qualifications'].find().limit(5))
                if qualifications:
                    print(f"\n🎯 Ultimele leaduri calificate:")
                    for i, lead in enumerate(qualifications, 1):
                        print(f"{i}. Score: {lead['score']}/100 - {lead['quality']}")
                        
            except Exception as e:
                print(f"❌ Eroare la încărcarea dashboard-ului: {e}")
                
        elif choice == "4":
            # Lista site-uri procesate
            try:
                sites = site_manager.mongodb.db['site_content'].find({}, {"url": 1, "title": 1})
                print("\n📋 Site-uri procesate pentru chat comercial:")
                for i, site in enumerate(sites, 1):
                    print(f"{i}. {site.get('title', 'N/A')} - {site['url']}")
            except Exception as e:
                print(f"❌ Eroare la listare: {e}")
                
        elif choice == "5":
            print("👋 La revedere! Sistemul comercial AI vă așteaptă!")
            break
        else:
            print("❌ Opțiune invalidă")

if __name__ == "__main__":
    main()
