#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Configurează toate GPU-urile
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1,2,3,4,5,6,7,8,9,10"

from agents.site_agent_optimized import OptimizedSiteAgent
from main_pipeline import process_site_to_ai_agent

def main():
    print("🚀 AI Site Agent CLI - Optimizat pentru 11 GPU-uri")
    print("=" * 50)
    
    while True:
        print("\nComenzi disponibile:")
        print("1. Procesează un site nou (URL)")
        print("2. Interacționează cu un agent existent (URL)")
        print("3. Ieși")
        
        choice = input("\nAlege o opțiune (1-3): ").strip()
        
        if choice == "1":
            url = input("Introdu URL-ul site-ului: ").strip()
            if url:
                result = process_site_to_ai_agent(url)
                if result:
                    print(f"✅ Agent creat pentru: {result['url']}")
                else:
                    print("❌ Eroare la crearea agentului")
                    
        elif choice == "2":
            url = input("Introdu URL-ul site-ului: ").strip()
            if url:
                print("🔄 Încărcare agent pe toate GPU-urile...")
                agent = OptimizedSiteAgent(url)
                context = agent.get_site_context()
                if context:
                    print(f"💬 Interacționează cu agentul pentru: {context.get('title', url)}")
                    print("⚡ Agent distribuit pe 11 GPU-uri pentru performanță maximă")
                    
                    while True:
                        question = input("\nÎntrebarea ta (sau 'înapoi' pentru a reveni): ").strip()
                        if question.lower() in ['înapoi', 'back', 'exit', 'quit']:
                            break
                        if question:
                            print("🧠 Generare răspuns pe toate GPU-urile...")
                            answer = agent.answer_question(question)
                            print(f"\n🤖 Răspuns: {answer}")
                else:
                    print("❌ Nu există agent pentru acest site. Procesează-l mai întâi.")
                    
        elif choice == "3":
            print("👋 La revedere!")
            break
        else:
            print("❌ Opțiune invalidă")

if __name__ == "__main__":
    main()
