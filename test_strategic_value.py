import os
import json
from qdrant_client import QdrantClient
from llm_orchestrator import call_llm_with_fallback

# Config
QDRANT_URL = "http://localhost:9306"
MASTER_COLLECTION = "construction_tehnica-antifoc_ro"

def run_test():
    try:
        client = QdrantClient(url=QDRANT_URL)
        
        questions = [
            "Cine sunt principalii mei competitori pe 'vopsea termospumantă' sau 'intumescentă'? Ce produse specifice promovează?",
            "Ce servicii de consultanță ISU sau certificare oferă concurența și cum se diferențiază?",
            "Analizează strategia celor de la promat.com. Ce fac ei diferit pe partea de conținut sau produse?"
        ]
        
        print("🧪 TESTARE VALOARE STRATEGICĂ SISTEM AI (cu Qwen-72B Local)\n")
        
        for q in questions:
            print(f"❓ Întrebare: {q}")
            
            # Simulare context (în producție folosim Qdrant search real)
            if "vopsea" in q:
                context = """
                Competitor: ropaintsolutions.ro promovează 'Vopsea Termospumantă' pentru oțel.
                Competitor: promat.com oferă 'PROMAPAINT-SC3' și 'PROMAPAINT-SC4'.
                Competitor: koner.ro vinde 'Vopsea Intumescentă Termo-S'.
                Competitor: hilti.ro are 'Acoperire intumescentă CFS-CT'.
                Prețuri observate: Variază între 45-65 RON/kg pentru proiecte mari.
                Majoritatea pun accent pe "Rezistență 30-90 minute".
                """
            elif "consultanță" in q:
                context = """
                Competitor: scenariu-securitate-incendiu.ro se axează exclusiv pe 'Scenarii de Securitate'.
                Competitor: autorizatisu.ro oferă 'Pachet Complet Avizare ISU'.
                Competitor: qsecurity.ro promovează 'Audit de Securitate la Incendiu'.
                Diferențiator: Mulți oferă consultanța doar ca "add-on" la proiectare, puțini ca serviciu premium separat de mentenanță.
                """
            else:
                context = """
                Promat.com Strategie:
                - Focus masiv pe EDUCAȚIE (Ghiduri, Fișe Tehnice, Webinarii).
                - Nu vând doar produse, vând "Sisteme Certificate".
                - Au secțiune dedicată "Zona Experților".
                - SEO puternic pe termeni tehnici ("protecție pasivă", "plăci silicat").
                """
                
            prompt = f"""
            Ești un Consultant de Business Strategie expert în industria construcțiilor și protecției la foc.
            Analizează următorul context extras din baza de date de inteligență competitivă și răspunde la întrebare.
            
            CONTEXT DIN PIAȚĂ (Competitori & Date):
            {context}
            
            ÎNTREBARE CEO:
            {q}
            
            Răspunde concis, cu bullet points, evidențiind cifre, nume de companii și acțiuni concrete. Fii direct și strategic.
            """
            
            print("🤖 Analiză AI în curs (via Orchestrator)...")
            
            # Folosim orchestratorul care va alege automat Qwen Local
            answer = call_llm_with_fallback(prompt, model_preference="auto")
            
            print("-" * 80)
            print(f"💡 RĂSPUNS AI:\n{answer}")
            print("-" * 80)
            print("\n")
            
    except Exception as e:
        print(f"Eroare generală test: {e}")

if __name__ == "__main__":
    run_test()
