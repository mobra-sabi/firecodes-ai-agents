import requests
import json
from database.mongodb_handler import MongoDBHandler
import re

class VLLMSiteAgent:
    def __init__(self, site_url):
        self.site_url = site_url
        self.vllm_url = "http://localhost:9301/v1/completions"
        self.mongodb = MongoDBHandler()
        
    def clean_content(self, content):
        """Curăță conținutul de elemente irelevante"""
        content = re.sub(r'#\w+', '', content)
        content = re.sub(r'\[.*?\]\(.*?\)', '', content)
        content = re.sub(r'http[s]?://\S+', '', content)
        content = re.sub(r'\s+', ' ', content)
        return content.strip()[:800]
        
    def get_site_context(self):
        return self.mongodb.get_site_content(self.site_url)
        
    def answer_question(self, question):
        context = self.get_site_context()
        if not context:
            return "Nu am informații despre acest site încă."
            
        clean_content = self.clean_content(context['content'])
        
        prompt = f"""Ești un reprezentant al companiei {context['title']}.

Informații despre companie:
- Servicii: {clean_content}

Întrebarea clientului: {question}

Răspunde profesional în română, maxim 80 cuvinte, doar despre serviciile companiei:"""

        payload = {
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "prompt": prompt,
            "max_tokens": 150,
            "temperature": 0.3,
            "top_p": 0.9
        }
        
        try:
            response = requests.post(self.vllm_url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['text'].strip()
                return answer
            else:
                return "Eroare la generarea răspunsului. Încearcă din nou."
        except Exception as e:
            return f"Eroare de conexiune: {str(e)}"
