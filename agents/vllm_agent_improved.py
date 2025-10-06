import requests
import json
from database.mongodb_handler import MongoDBHandler
import re

class ImprovedVLLMAgent:
    def __init__(self, site_url):
        self.site_url = site_url
        self.vllm_url = "http://localhost:9301/v1/completions"
        self.mongodb = MongoDBHandler()
        
    def clean_content(self, content):
        content = re.sub(r'#\w+', '', content)
        content = re.sub(r'\[.*?\]\(.*?\)', '', content)
        content = re.sub(r'http[s]?://\S+', '', content)
        content = re.sub(r'\s+', ' ', content)
        return content.strip()[:600]
        
    def get_site_context(self):
        return self.mongodb.get_site_content(self.site_url)
        
    def answer_question(self, question):
        context = self.get_site_context()
        if not context:
            return "Nu am informații despre acest site încă."
            
        clean_content = self.clean_content(context['content'])
        
        # Prompt îmbunătățit pentru răspunsuri mai bune
        prompt = f"""Răspunde ca reprezentant al companiei {context['title']}.

Servicii disponibile: {clean_content}

Întrebarea clientului: {question}

Instrucțiuni:
- Răspunde doar cu informații despre serviciile companiei
- Folosește maxim 50 cuvinte
- Fii specific și profesional
- Nu repeta informații

Răspuns:"""

        payload = {
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "prompt": prompt,
            "max_tokens": 100,
            "temperature": 0.2,
            "top_p": 0.9,
            "stop": ["\n\n", "Instrucțiuni:", "Întrebarea"]
        }
        
        try:
            response = requests.post(self.vllm_url, json=payload, timeout=15)
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['text'].strip()
                
                # Curăță răspunsul
                answer = re.sub(r'\[.*?\]', '', answer)
                answer = re.sub(r'#\w+', '', answer)
                return answer[:200]
            else:
                return "Eroare la generarea răspunsului."
        except Exception as e:
            return f"Eroare de conexiune: {str(e)}"
