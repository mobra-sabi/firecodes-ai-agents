#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from agents.improved_learning_agent import ImprovedLearningAgent as LearningAgent
from learning.continuous_learning_manager import ContinuousLearningManager

def main():
    print("🧠 Sistem de Învățare Continuă AI")
    print("=" * 50)
    
    learning_manager = ContinuousLearningManager()
    
    while True:
        print("\n🎯 Opțiuni:")
        print("1. Adaugă site nou pentru monitorizare")
        print("2. Interacționează cu agent (cu învățare)")
        print("3. Pornește monitorizarea continuă")
        print("4. Status învățare")
        print("5. Ieși")
        
        choice = input("\nAlege (1-5): ").strip()
        
        if choice == "1":
            site_url = input("URL site: ").strip()
            learning_manager.add_site_for_monitoring(site_url)
            
        elif choice == "2":
            site_url = input("URL site: ").strip()
            agent = LearningAgent(site_url)
            
            print(f"💬 Agent activ pentru {site_url}")
            print("🎓 Fiecare interacțiune contribuie la învățare!")
            
            while True:
                question = input("\n❓ Întrebarea ta (sau 'exit'): ").strip()
                if question.lower() == 'exit':
                    break
                    
                answer = agent.answer_question_with_learning(question)
                print(f"\n🤖 Răspuns: {answer}")
                
                feedback = input("\nFeedback (good/bad/skip): ").strip()
                if feedback in ['good', 'bad']:
                    agent.provide_feedback(question, answer, feedback)
                    
        elif choice == "3":
            print("🚀 Pornesc monitorizarea continuă...")
            learning_manager.start_continuous_learning()
            
        elif choice == "4":
            print(f"📊 În coadă pentru antrenament: {len(learning_manager.training_queue)} întrebări")
            print(f"📡 Site-uri monitorizate: {len(learning_manager.sites_to_monitor)}")
            
        elif choice == "5":
            break

if __name__ == "__main__":
    main()
