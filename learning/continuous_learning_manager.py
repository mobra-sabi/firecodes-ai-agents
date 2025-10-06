import os
import sys
import time
import json
import schedule
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scrapers.site_scraper import SiteScraper
from database.mongodb_handler import MongoDBHandler
from database.qdrant_vectorizer import QdrantVectorizer
from training.data_generator import TrainingDataGenerator
from training.fine_tune_qwen import QwenFineTuner

class ContinuousLearningManager:
    def __init__(self):
        self.mongodb = MongoDBHandler()
        self.qdrant = QdrantVectorizer()
        self.data_generator = TrainingDataGenerator()
        self.sites_to_monitor = []
        self.learning_threshold = 50  # Antrenează după 50 întrebări noi
        self.training_queue = []
        
    def add_site_for_monitoring(self, site_url):
        """Adaugă site pentru monitorizare continuă"""
        print(f"📡 Adaug {site_url} pentru monitorizare...")
        
        # Scrapuire inițială
        scraper = SiteScraper(site_url)
        content = scraper.scrape_content()
        
        if content:
            # Salvează în MongoDB
            content_id = self.mongodb.save_site_content(content)
            
            # Vectorizează în Qdrant
            try:
                embedding = self.qdrant.vectorize_content(content)
                metadata = {
                    'url': content['url'],
                    'title': content['title'],
                    'last_updated': datetime.now().isoformat()
                }
                self.qdrant.store_embedding(str(content_id), embedding, metadata)
            except Exception as e:
                print(f"⚠️ Eroare la vectorizare: {e}")
            
            # Generează date de antrenament inițiale
            print("🎓 Generez date de antrenament inițiale...")
            training_data = self.data_generator.generate_training_data(site_url, 30)
            
            if training_data:
                filename = f"auto_{site_url.replace('://', '_').replace('/', '_').replace('.', '_')}.jsonl"
                self.save_training_data(training_data, filename)
            
            self.sites_to_monitor.append(site_url)
            print(f"✅ Site {site_url} adăugat cu succes")
            return True
        else:
            print(f"❌ Nu s-a putut scrapa {site_url}")
            return False
            
    def process_user_interaction(self, site_url, question, answer, user_feedback=None):
        """Procesează o interacțiune utilizator pentru învățare"""
        interaction_data = {
            'site_url': site_url,
            'question': question,
            'answer': answer,
            'user_feedback': user_feedback,
            'timestamp': datetime.now().isoformat()
        }
        
        # Salvează în MongoDB pentru istoricul interacțiunilor
        try:
            collection = self.mongodb.db['user_interactions']
            collection.insert_one(interaction_data)
        except Exception as e:
            print(f"⚠️ Eroare la salvarea interacțiunii: {e}")
        
        # Adaugă la coada de antrenament doar dacă feedback-ul e pozitiv
        if user_feedback == 'good' or user_feedback is None:
            self.training_queue.append({
                'question': question,
                'answer': answer
            })
            
        print(f"📚 Interacțiune salvată. Queue size: {len(self.training_queue)}")
        
        # Verifică dacă e timpul pentru re-antrenare
        if len(self.training_queue) >= self.learning_threshold:
            self.trigger_retraining(site_url)
            
    def trigger_retraining(self, site_url):
        """Declanșează re-antrenarea modelului"""
        print(f"🔥 Declanșez re-antrenarea pentru {site_url}...")
        
        if not self.training_queue:
            print("⚠️ Nu există date în coadă pentru antrenament")
            return
        
        # Salvează datele din coadă
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"continuous_learning_{timestamp}.jsonl"
        
        filepath = os.path.join(os.path.dirname(__file__), '..', 'training', filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for item in self.training_queue:
                    training_item = {
                        "instruction": item['question'],
                        "input": "",
                        "output": item['answer']
                    }
                    json.dump(training_item, f, ensure_ascii=False)
                    f.write('\n')
            
            print(f"💾 Date salvate pentru antrenament: {filepath}")
            
            # Fine-tuning automat (opțional - poate dura mult)
            proceed = input("🔥 Continui cu fine-tuning automat? (y/n): ").strip().lower()
            
            if proceed == 'y':
                try:
                    tuner = QwenFineTuner()
                    model_path = tuner.fine_tune(filepath, f"./models/qwen_improved_{timestamp}")
                    print(f"✅ Re-antrenare completă. Model salvat: {model_path}")
                except Exception as e:
                    print(f"❌ Eroare la fine-tuning: {e}")
            
            # Golește coada
            self.training_queue = []
            
        except Exception as e:
            print(f"❌ Eroare la salvarea datelor: {e}")
            
    def scheduled_site_refresh(self):
        """Actualizează periodic conținutul site-urilor"""
        print("🔄 Actualizare scheduled a site-urilor...")
        
        for site_url in self.sites_to_monitor:
            try:
                scraper = SiteScraper(site_url)
                new_content = scraper.scrape_content()
                
                # Verifică dacă conținutul s-a schimbat
                old_content = self.mongodb.get_site_content(site_url)
                
                if new_content and old_content:
                    if new_content['content'] != old_content['content']:
                        print(f"📝 Conținut nou detectat pentru {site_url}")
                        
                        # Actualizează MongoDB
                        self.mongodb.save_site_content(new_content)
                        
                        # Generează date noi de antrenament
                        new_training_data = self.data_generator.generate_training_data(site_url, 10)
                        if new_training_data:
                            self.training_queue.extend(new_training_data)
                        
            except Exception as e:
                print(f"❌ Eroare la actualizarea {site_url}: {e}")
                
    def get_learning_stats(self):
        """Returnează statistici despre învățare"""
        stats = {
            'sites_monitored': len(self.sites_to_monitor),
            'training_queue_size': len(self.training_queue),
            'learning_threshold': self.learning_threshold,
            'sites_list': self.sites_to_monitor
        }
        return stats
                
    def start_continuous_learning(self):
        """Pornește sistemul de învățare continuă"""
        print("🚀 Pornesc sistemul de învățare continuă...")
        
        if not self.sites_to_monitor:
            print("⚠️ Nu există site-uri de monitorizat. Adaugă primul site!")
            return
        
        print("✅ Sistem de învățare continuă activ!")
        print("📡 Monitorizez site-urile pentru schimbări...")
        print("🎓 Învăț din fiecare interacțiune...")
        print("⏰ Apasă Ctrl+C pentru a opri...")
        
        try:
            while True:
                # Verifică periodic pentru actualizări
                self.scheduled_site_refresh()
                print(f"💤 Aștept 6 ore... (Queue: {len(self.training_queue)} items)")
                time.sleep(21600)  # 6 ore
        except KeyboardInterrupt:
            print("\n👋 Opresc sistemul de învățare continuă...")
            
    def save_training_data(self, data, filename):
        """Salvează date de antrenament"""
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
            print(f"💾 Date salvate: {filepath}")
        except Exception as e:
            print(f"❌ Eroare la salvarea datelor: {e}")
