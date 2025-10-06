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
    print("⚡ VLLM AI Site Agent - Performanță Maximă pe 11 GPU-uri")
    print("=" * 60)
    
    if not check_vllm_server():
        print("❌ Server VLLM nu rulează!")
        print("Pornește serverul cu:")
        print("CUDA_VISIBLE_DEVICES=\"0,1,2,3,4,5,6,7,8,9,10\" vllm serve Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 9301 --tensor-parallel-size 11")
        return
    
    print("✅ Server VLLM detectat și funcțional")
    
    while True:
        print("\nComenzi disponibile:")
        print("1. Interacționează cu agentul RAPID (URL)")
        print("2. Ieși")
        
        choice = input("\nAlege o opțiune (1-2): ").strip()
        
        if choice == "1":
            url = input("Introdu URL-ul site-ului: ").strip()
            if url:
                agent = VLLMSiteAgent(url)
                context = agent.get_site_context()
                if context:
                    print(f"💬 Agent RAPID pentru: {context.get('title', url)}")
                    print("⚡ Folosește VLLM cu toate 11 GPU-urile")
                    
                    while True:
                        question = input("\nÎntrebarea ta (sau 'înapoi'): ").strip()
                        if question.lower() in ['înapoi', 'back', 'exit']:
                            break
                        if question:
                            print("🚀 Generare răspuns rapid...")
                            answer = agent.answer_question(question)
                            print(f"\n✨ Răspuns: {answer}")
                else:
                    print("❌ Nu există agent pentru acest site.")
        elif choice == "2":
            break

if __name__ == "__main__":
    main()
