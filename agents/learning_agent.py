import requests
import json
from database.mongodb_handler import MongoDBHandler
import sys
import os
import openai
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from learning.continuous_learning_manager import ContinuousLearningManager

class LearningAgent:
    def __init__(self, site_url):
        self.site_url = site_url
        self.vllm_url = "http://localhost:9301/v1/completions"
        self.mongodb = MongoDBHandler()
        self.learning_manager = ContinuousLearningManager()
        
        # ChatGPT backup
        self.openai_client = openai.OpenAI(
            api_key="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"
        )
        
    def get_site_context(self):
        return self.mongodb.get_site_content(self.site_url)
        
    def check_vllm_server(self):
        """Verifică dacă serverul VLLM rulează"""
        try:
            response = requests.get("http://localhost:9301/health", timeout=5)
            return response.status_code == 200
        except:
            return False
        
    def answer_with_chatgpt(self, question, context):
        """Folosește ChatGPT ca backup"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": f"Ești consultant expert la {context['title']}. Servicii: {context['content'][:800]}"
                    },
                    {
                        "role": "user", 
                        "content": question
                    }
                ],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Eroare ChatGPT: {str(e)}"
        
    def answer_question_with_learning(self, question):
        """Răspunde la întrebare și învață din interacțiune"""
        context = self.get_site_context()
        if not context:
            return "Nu am informații despre acest site încă."
            
        # Încearcă VLLM mai întâi
        if self.check_vllm_server():
            print("🚀 Folosesc VLLM (Qwen local)...")
            answer = self.answer_with_vllm(question, context)
        else:
            print("🌐 VLLM indisponibil, folosesc ChatGPT...")
            answer = self.answer_with_chatgpt(question, context)
        
        # Salvează interacțiunea pentru învățare
        self.learning_manager.process_user_interaction(
            self.site_url, question, answer
        )
        
        return answer
        
    def answer_with_vllm(self, question, context):
        """Răspunde cu VLLM"""
        prompt = f"""Ești consultant expert la {context['title']}.

Servicii disponibile: {context['content'][:800]}

Întrebarea clientului: {question}

Răspunde profesional, specific și concis (maxim 100 cuvinte):"""

        payload = {
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "prompt": prompt,
            "max_tokens": 150,
            "temperature": 0.3,
            "top_p": 0.9
        }
        
        try:
            response = requests.post(self.vllm_url, json=payload, timeout=20)
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['text'].strip()
            else:
                return "Eroare la serverul VLLM."
        except Exception as e:
            return f"Eroare VLLM: {str(e)}"
            
    def provide_feedback(self, question, answer, feedback):
        """Permite utilizatorului să ofere feedback"""
        self.learning_manager.process_user_interaction(
            self.site_url, question, answer, feedback
        )
        print(f"✅ Feedback înregistrat: {feedback}")
