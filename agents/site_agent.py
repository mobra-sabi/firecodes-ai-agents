from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from database.mongodb_handler import MongoDBHandler
from database.qdrant_vectorizer import QdrantVectorizer

class SiteAgent:
    def __init__(self, site_url):
        self.site_url = site_url
        self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B")
        self.model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-7B")
        self.mongodb = MongoDBHandler()
        self.qdrant = QdrantVectorizer()
        
    def get_site_context(self):
        """Retrieve site content from MongoDB"""
        return self.mongodb.get_site_content(self.site_url)
        
    def answer_question(self, question):
        """Answer questions about the site using Qwen 2.5"""
        # Get site context
        context = self.get_site_context()
        if not context:
            return "I don't have information about this site yet."
            
        # Create prompt with site context
        prompt = f"""
        Based on the following website content, answer the question.
        
        Website Title: {context['title']}
        Website Description: {context['description']}
        Website Content: {context['content'][:2000]}
        
        Question: {question}
        
        Answer as if you are the website itself:
        """
        
        # Generate response using Qwen
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=500, temperature=0.7)
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
        return response[len(prompt):]  # Return only the generated part
        
    def learn_from_interaction(self, question, answer):
        """Learn from interactions to improve responses"""
        # This would implement continuous learning
        print("🧠 Learning from interaction...")
        # Implementation for fine-tuning or storing interaction patterns
        pass
