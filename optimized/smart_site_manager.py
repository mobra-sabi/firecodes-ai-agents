import hashlib
from database.mongodb_handler import MongoDBHandler
from database.qdrant_vectorizer import QdrantVectorizer
from scrapers.site_scraper import SiteScraper
from training.data_generator import TrainingDataGenerator
import uuid
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class SmartSiteManager:
    def __init__(self):
        self.mongodb = MongoDBHandler()
        self.qdrant = QdrantVectorizer()
        self.data_generator = TrainingDataGenerator()
        
    def is_site_processed(self, site_url):
        """Verifică dacă site-ul a fost deja procesat"""
        existing = self.mongodb.get_site_content(site_url)
        return existing is not None
        
    def process_site_smart(self, site_url):
        """Procesează site-ul doar dacă nu există deja"""
        
        if self.is_site_processed(site_url):
            print(f"✅ Site {site_url} deja procesat în sistem")
            return True
            
        print(f"🆕 Site nou {site_url} - încep procesarea...")
        
        # 1. Scraping
        scraper = SiteScraper(site_url)
        content = scraper.scrape_content()
        
        if not content:
            print(f"❌ Nu s-a putut scrapa {site_url}")
            return False
            
        # 2. Salvare MongoDB
        content_id = str(uuid.uuid4())  # UUID valid pentru Qdrant
        content['_id'] = content_id
        mongo_result = self.mongodb.save_site_content(content)
        
        # 3. Vectorizare Qdrant (cu UUID corect)
        try:
            embedding = self.qdrant.vectorize_content(content)
            metadata = {
                'url': content['url'],
                'title': content['title'],
                'processed_at': str(content['timestamp'])
            }
            self.qdrant.store_embedding(content_id, embedding, metadata)
            print("✅ Vectorizare în Qdrant completă")
        except Exception as e:
            print(f"⚠️ Eroare vectorizare (continuăm fără): {e}")
            
        # 4. Generare date de antrenament (în background)
        print("🎓 Generez date de antrenament...")
        training_data = self.data_generator.generate_training_data(site_url, 20)
        
        if training_data:
            filename = f"site_{content_id}.jsonl"
            self.save_training_data(training_data, filename)
            
        print(f"✅ Site {site_url} procesat complet și salvat")
        return True
        
    def save_training_data(self, data, filename):
        """Salvează datele de antrenament"""
        import os
        import json
        
        filepath = os.path.join(os.path.dirname(__file__), '..', 'training', filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for item in data:
                    training_item = {
                        "instruction": item['question'],
                        "input": "",
                        "output": item['answer']
                    }
                    json.dump(training_item, f, ensure_ascii=False)
                    f.write('\n')
            print(f"💾 Date antrenament salvate: {filename}")
        except Exception as e:
            print(f"❌ Eroare la salvarea antrenament: {e}")
