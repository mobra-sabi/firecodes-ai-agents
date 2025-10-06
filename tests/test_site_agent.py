import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agents.site_agent import SiteAgent

def test_site_agent():
    """Testează funcționalitatea agentului AI pentru site"""
    
    # Creează un agent pentru example.com (presupunem că deja a fost procesat)
    agent = SiteAgent("https://example.com")
    
    # Testează obținerea contextului
    context = agent.get_site_context()
    print("🔍 Context site:")
    if context:
        print(f"   Titlu: {context.get('title', 'N/A')}")
        print(f"   URL: {context.get('url', 'N/A')}")
        print("✅ Context obținut cu succes")
    else:
        print("⚠️ Nu există context pentru acest site")
    
    # Testează răspunsul la o întrebare (dacă avem context)
    if context:
        question = "What is this website about?"
        answer = agent.answer_question(question)
        print(f"\n❓ Întrebare: {question}")
        print(f"🤖 Răspuns: {answer[:200]}...")
        print("✅ Agentul a generat un răspuns")

if __name__ == "__main__":
    test_site_agent()
