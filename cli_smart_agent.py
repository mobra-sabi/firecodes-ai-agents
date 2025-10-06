#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from agents.smart_site_agent import SmartSiteAgent
from main_pipeline import process_site_to_ai_agent

def main():
    print("🧠 Smart AI Site Agent - Răspunsuri Optimizate")
    print("=" * 50)
    
    while True:
        print("\nComenzi disponibile:")
        print("1. Procesează un site nou (URL)")
        print("2. Interacționează cu agentul inteligent (URL)")
        print("3. Ieși")
        
        choice = input("\nAlege o opțiune (1-3): ").strip()
        
        if choice == "2":
            url = input("Introdu URL-ul site-ului: ").strip()
            if url:
                print("🧠 Încărcare agent inteligent...")
                agent = SmartSiteAgent(url)
                context = agent.get_site_context()
                if context:
                    print(f"💬 Agent inteligent pentru: {context.get('title', url)}")
                    print("⚡ Optimizat pentru răspunsuri precise și relevante")
                    
                    while True:
                        question = input("\nÎntrebarea ta (sau 'înapoi'): ").strip()
                        if question.lower() in ['înapoi', 'back', 'exit']:
                            break
                        if question:
                            print("🤖 Generare răspuns optimizat...")
                            answer = agent.answer_question(question)
                            print(f"\n✨ Răspuns: {answer}")
                else:
                    print("❌ Nu există agent pentru acest site.")
        elif choice == "3":
            break

if __name__ == "__main__":
    main()
