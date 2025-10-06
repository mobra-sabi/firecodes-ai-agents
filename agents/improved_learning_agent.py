import requests
import json
from database.mongodb_handler import MongoDBHandler
import sys
import os
import openai
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from learning.continuous_learning_manager import ContinuousLearningManager

class ImprovedLearningAgent:
    def __init__(self, site_url):
        self.site_url = site_url
        self.vllm_url = "http://localhost:9301/v1/completions"
        self.mongodb = MongoDBHandler()
        self.learning_manager = ContinuousLearningManager()
        
        # ChatGPT cu prompt îmbunătățit
        self.openai_client = openai.OpenAI(
            api_key="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"
        )
        
    def get_site_context(self):
        return self.mongodb.get_site_content(self.site_url)
        
    def check_vllm_server(self):
        try:
            response = requests.get("http://localhost:9301/health", timeout=5)
            return response.status_code == 200
        except:
            return False
            
    def answer_with_chatgpt(self, question, context):
        """Prompt îmbunătățit pentru ChatGPT"""
        try:
            # Prompt mult mai specific și personalizat
            system_prompt = f"""Ești reprezentantul oficial al site-ului {context['title']}.

DESPRE COMPANIE:
{context['content'][:2000]}

INSTRUCȚIUNI CRITICE:
1. Răspunde DOAR ca și cum ești site-ul însuși - folosește "noi", "oferim", "la noi"
2. Bazează-te STRICT pe informațiile din conținutul site-ului
3. Dacă întrebarea nu se potrivește cu serviciile tale, explică politicos ce faci TU
4. Structurează răspunsul frumos cu bullet points
5. Fii specific despre serviciile tale, nu general
6. Maxim 150 cuvinte, profesional și prietenos

Răspunde ca site-ul {self.site_url}:"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                max_tokens=200,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Ne pare rău, avem o problemă tehnică temporară: {str(e)}"
        
    def answer_question_with_learning(self, question):
        context = self.get_site_context()
        if not context:
            return "Ne pare rău, nu avem încă informații complete despre site."
            
        # Încearcă VLLM mai întâi, apoi ChatGPT
        if self.check_vllm_server():
            print("🚀 Folosesc VLLM (Qwen local)...")
            answer = self.answer_with_vllm(question, context)
        else:
            print("🌐 Folosesc ChatGPT cu prompt îmbunătățit...")
            answer = self.answer_with_chatgpt(question, context)
        
        # Salvează pentru învățare
        self.learning_manager.process_user_interaction(
            self.site_url, question, answer
        )
        
        return answer
        
    def answer_with_vllm(self, question, context):
        # Prompt îmbunătățit și pentru VLLM
        prompt = f"""Tu ești site-ul {context['title']}.

Serviciile tale: {context['content'][:1000]}

Un vizitator întreabă: {question}

Răspunde ca site-ul însuși, folosind "noi oferim", "la noi găsiți", etc.
Bazează-te doar pe serviciile tale reale.
Maxim 100 cuvinte, structurat și profesional:"""

        payload = {
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "prompt": prompt,
            "max_tokens": 150,
            "temperature": 0.2,
            "top_p": 0.9
        }
        
        try:
            response = requests.post(self.vllm_url, json=payload, timeout=20)
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['text'].strip()
            else:
                return "Avem o problemă tehnică temporară."
        except Exception as e:
            return f"Ne pare rău, sistem temporar indisponibil: {str(e)}"
            
    def provide_feedback(self, question, answer, feedback):
        self.learning_manager.process_user_interaction(
            self.site_url, question, answer, feedback
        )
        print(f"✅ Feedback înregistrat: {feedback}")
