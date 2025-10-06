from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from database.mongodb_handler import MongoDBHandler
import os
import re

os.environ["CUDA_VISIBLE_DEVICES"] = "0,1,2,3,4,5,6,7,8,9,10"

class SmartSiteAgent:
    def __init__(self, site_url):
        self.site_url = site_url
        self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
        self.model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-7B-Instruct",
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True
        )
        self.mongodb = MongoDBHandler()
        
    def clean_content(self, content):
        """Curăță conținutul de elemente irelevante"""
        # Elimină hashtag-uri, linkuri și text repetitiv
        content = re.sub(r'#\w+', '', content)
        content = re.sub(r'\[.*?\]\(.*?\)', '', content)
        content = re.sub(r'http[s]?://\S+', '', content)
        content = re.sub(r'\s+', ' ', content)
        return content.strip()[:1000]  # Limitează la 1000 caractere relevante
        
    def get_site_context(self):
        return self.mongodb.get_site_content(self.site_url)
        
    def answer_question(self, question):
        context = self.get_site_context()
        if not context:
            return "Nu am informații despre acest site încă."
            
        # Curăță și optimizează conținutul
        clean_content = self.clean_content(context['content'])
        
        # Prompt optimizat și mai precis
        prompt = f"""Ești un reprezentant al companiei {context['title']}.

Informații despre companie:
- Titlu: {context['title']}
- Descriere: {context['description']}
- Servicii: {clean_content}

Un client întreabă: {question}

Instrucțiuni:
1. Răspunde DOAR despre produsele/serviciile companiei
2. Fii specific și profesional
3. Nu include linkuri sau hashtag-uri
4. Oferă informații concrete și utile
5. Răspunde în română, maxim 100 cuvinte

Răspuns profesional:"""

        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs, 
                max_new_tokens=200,
                temperature=0.3,  # Mai conservativ pentru răspunsuri mai precise
                repetition_penalty=1.2,
                do_sample=True
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        answer = response[len(prompt):].strip()
        
        # Curăță răspunsul de text repetitiv
        answer = re.sub(r'#\w+', '', answer)
        answer = re.sub(r'\[.*?\]', '', answer)
        
        return answer[:500]  # Limitează lungimea răspunsului
