#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from agents.vllm_agent import VLLMSiteAgent
import requests

def check_vllm_server():
    try:
        response = requests.get("http://localhost:9301/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    print("⚡ VLLM AI Site Agent - Versiune Îmbunătățită")
    print("=" * 50)
    
    if not check_vllm_server():
        print("❌ Server VLLM nu rulează!")
        return
    
    print("✅ Server VLLM detectat și funcțional")
    
    while True:
        print("\nComenzi disponibile:")
        print("1. Interacționează cu agentul (URL)")
        print("2. Ieși")
        
        choice = input("\nAlege o opțiune (1-2): ").strip()
        
        if choice == "1":
            url = input("Introdu URL-ul site-ului: ").strip()
            if url:
                agent = VLLMSiteAgent(url)
                context = agent.get_site_context()
                if context:
                    print(f"💬 Agent pentru: {context.get('title', url)}")
                    print("📝 Scrie întrebări despre serviciile companiei")
                    print("⚠️ Pentru a ieși, scrie: 'exit', 'quit' sau 'stop'")
                    
                    while True:
                        question = input("\n❓ Întrebarea ta: ").strip()
                        
                        # Verifică comenzi de ieșire
                        if question.lower() in ['exit', 'quit', 'stop', 'inapoi', 'înapoi']:
                            print("👋 Revin la meniul principal...")
                            break
                            
                        if question:
                            print("🚀 Generez răspuns...")
                            answer = agent.answer_question(question)
                            
                            # Curăță răspunsul de text duplicat
                            clean_answer = answer.split('\n')[0][:200]
                            print(f"\n✨ Răspuns: {clean_answer}")
                else:
                    print("❌ Nu există informații pentru acest site.")
                    
        elif choice == "2":
            print("👋 La revedere!")
            break
        else:
            print("❌ Opțiune invalidă. Alege 1 sau 2.")

if __name__ == "__main__":
    main()
