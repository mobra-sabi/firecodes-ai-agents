import requests
import json
from database.mongodb_handler import MongoDBHandler
import sys
import os
import openai
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class FinalAgent:
    def __init__(self, site_url):
        self.site_url = site_url
        self.vllm_url = "http://localhost:9301/v1/completions"
        self.mongodb = MongoDBHandler()
        
        # ChatGPT backup
        self.openai_client = openai.OpenAI(
            api_key="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"
        )
        
        # Încarcă contextul site-ului o singură dată
        self.site_context = self.load_site_context()
        
    def load_site_context(self):
        """Încarcă contextul site-ului din baza de date"""
        context = self.mongodb.get_site_content(self.site_url)
        
        if not context:
            print(f"⚠️ Site {self.site_url} nu este în baza de date")
            return None
            
        print(f"✅ Context încărcat pentru {context.get('title', self.site_url)}")
        return context
        
    def check_vllm_server(self):
        """Verifică dacă VLLM rulează"""
        try:
            response = requests.get("http://localhost:9301/health", timeout=3)
            return response.status_code == 200
        except:
            return False
            
    def answer_question(self, question):
        """Răspunde la întrebare folosind contextul încărcat"""
        
        if not self.site_context:
            return "Ne pare rău, acest site nu este încă în sistemul nostru. Vă rugăm să îl adăugați mai întâi."
            
        # Încearcă VLLM, apoi ChatGPT
        if self.check_vllm_server():
            print("🚀 Răspund cu VLLM (rapid)...")
            return self.answer_with_vllm(question)
        else:
            print("🌐 Răspund cu ChatGPT...")
            return self.answer_with_chatgpt(question)
            
    def answer_with_vllm(self, question):
        """Răspuns rapid cu VLLM"""
        prompt = f"""Ești reprezentantul oficial al site-ului {self.site_context['title']}.

SERVICIILE NOASTRE:
{self.site_context['content'][:1200]}

INSTRUCȚIUNI:
- Răspunde ca site-ul însuși (folosește "noi", "oferim", "la noi")
- Bazează-te strict pe serviciile menționate mai sus
- Fii specific și profesional
- Maxim 80 cuvinte

ÎNTREBAREA CLIENTULUI: {question}

RĂSPUNSUL NOSTRU:"""

        payload = {
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "prompt": prompt,
            "max_tokens": 120,
            "temperature": 0.1,
            "top_p": 0.9
        }
        
        try:
            response = requests.post(self.vllm_url, json=payload, timeout=15)
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['text'].strip()
                
                # Curăță răspunsul
                if answer.startswith('"') and answer.endswith('"'):
                    answer = answer[1:-1]
                    
                return answer
            else:
                return "Avem o problemă tehnică temporară cu serverul nostru."
        except Exception as e:
            return f"Ne pare rău, sistem temporar indisponibil."
            
    def answer_with_chatgpt(self, question):
        """Răspuns cu ChatGPT ca backup"""
        try:
            system_prompt = f"""Ești reprezentantul oficial al site-ului {self.site_context['title']}.

DESPRE NOI:
{self.site_context['content'][:1500]}

IMPORTANT: 
- Răspunde doar ca site-ul însuși
- Folosește "noi oferim", "la noi găsiți" 
- Fii specific despre serviciile noastre
- Maxim 100 cuvinte"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                max_tokens=150,
                temperature=0.2
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return "Ne pare rău, avem o problemă tehnică temporară."
            
    def save_interaction(self, question, answer, feedback=None):
        """Salvează interacțiunea pentru învățare"""
        try:
            interaction = {
                'site_url': self.site_url,
                'question': question,
                'answer': answer,
                'feedback': feedback,
                'timestamp': str(datetime.now())
            }
            
            collection = self.mongodb.db['user_interactions']
            collection.insert_one(interaction)
            print("📚 Interacțiune salvată pentru învățare")
        except Exception as e:
            print(f"⚠️ Eroare la salvarea interacțiunii: {e}")
