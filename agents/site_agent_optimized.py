from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from database.mongodb_handler import MongoDBHandler
from database.qdrant_vectorizer import QdrantVectorizer
import os

# Configurează toate GPU-urile
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1,2,3,4,5,6,7,8,9,10"

class OptimizedSiteAgent:
    def __init__(self, site_url):
        self.site_url = site_url
        self.device_map = "auto"  # Distribuție automată pe toate GPU-urile
        
        # Încarcă modelul distribuit pe toate GPU-urile
        self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
        self.model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-7B-Instruct",
            device_map=self.device_map,
            torch_dtype=torch.float16,
            trust_remote_code=True
        )
        
        self.mongodb = MongoDBHandler()
        self.qdrant = QdrantVectorizer()
        
    def get_site_context(self):
        """Retrieve site content from MongoDB"""
        return self.mongodb.get_site_content(self.site_url)
        
    def answer_question(self, question):
        """Answer questions about the site using Qwen 2.5 distributed"""
        context = self.get_site_context()
        if not context:
            return "Nu am informații despre acest site încă."
            
        # Prompt optimizat
        prompt = f"""Bazându-te pe următorul conținut al site-ului web, răspunde la întrebare.

Titlul site-ului: {context['title']}
Descrierea site-ului: {context['description']}
Conținutul site-ului: {context['content'][:2000]}

Întrebarea: {question}

Răspunde ca și cum ești site-ul web însuși, în română:"""

        # Generare distribuită pe toate GPU-urile
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096)
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=500,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response[len(prompt):].strip()
