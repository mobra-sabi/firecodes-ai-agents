#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from optimized.smart_site_manager import SmartSiteManager
from agents.final_agent import FinalAgent

def main():
    print("🎯 AI Agent System - Versiunea Finală")
    print("=" * 50)
    
    site_manager = SmartSiteManager()
    
    while True:
        print("\n🚀 Opțiuni:")
        print("1. Adaugă site nou (procesare completă)")
        print("2. Chat cu site existent")
        print("3. Lista site-uri procesate")
        print("4. Ieși")
        
        choice = input("\nAlege (1-4): ").strip()
        
        if choice == "1":
            site_url = input("🌐 URL site nou: ").strip()
            if site_url:
                success = site_manager.process_site_smart(site_url)
                if success:
                    print(f"✅ Site {site_url} gata pentru chat!")
                    
        elif choice == "2":
            site_url = input("🌐 URL site pentru chat: ").strip()
            if site_url:
                agent = FinalAgent(site_url)
                
                if agent.site_context:
                    print(f"\n💬 Chat activ cu {agent.site_context['title']}")
                    print("🎯 Pune întrebări despre serviciile noastre!")
                    print("📝 Scrie 'exit' pentru a ieși\n")
                    
                    while True:
                        question = input("❓ Tu: ").strip()
                        
                        if question.lower() in ['exit', 'ieși', 'quit']:
                            break
                            
                        if question:
                            answer = agent.answer_question(question)
                            print(f"\n🤖 {agent.site_context['title']}: {answer}\n")
                            
                            # Opțional: feedback
                            feedback = input("👍 Răspuns util? (da/nu/skip): ").strip()
                            if feedback.lower() in ['da', 'nu']:
                                agent.save_interaction(question, answer, feedback)
                else:
                    print(f"❌ Site {site_url} nu este în sistem. Adaugă-l mai întâi!")
                    
        elif choice == "3":
            # Lista site-uri procesate
            try:
                sites = site_manager.mongodb.db['site_content'].find({}, {"url": 1, "title": 1})
                print("\n📋 Site-uri procesate:")
                for i, site in enumerate(sites, 1):
                    print(f"{i}. {site.get('title', 'N/A')} - {site['url']}")
            except Exception as e:
                print(f"❌ Eroare la listare: {e}")
                
        elif choice == "4":
            print("👋 La revedere!")
            break
        else:
            print("❌ Opțiune invalidă")

if __name__ == "__main__":
    main()
