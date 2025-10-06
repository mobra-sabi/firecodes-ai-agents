import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from scrapers.site_scraper import SiteScraper
from database.mongodb_handler import MongoDBHandler
from database.qdrant_vectorizer import QdrantVectorizer
import uuid

def process_site_to_ai_agent(url):
    """Pipeline complet: Site → Scraping → MongoDB → Qdrant → Agent AI"""
    
    print(f"🚀 Începem procesarea site-ului: {url}")
    
    # 1. Scraping conținut
    print("🔍 Scraping conținut...")
    scraper = SiteScraper(url)
    content_data = scraper.scrape_content()
    
    if not content_data:
        print("❌ Nu s-a putut scana site-ul")
        return None
    
    print("✅ Conținut extras cu succes")
    
    # 2. Salvare în MongoDB
    print("💾 Salvare în MongoDB...")
    mongodb = MongoDBHandler()
    content_id = str(uuid.uuid4())
    content_data['_id'] = content_id
    mongo_result = mongodb.save_site_content(content_data)
    
    if not mongo_result:
        print("❌ Eroare la salvarea în MongoDB")
        return None
    
    print("✅ Conținut salvat în MongoDB")
    
    # 3. Vectorizare și stocare în Qdrant
    print("🧠 Vectorizare conținut...")
    qdrant = QdrantVectorizer()
    qdrant.create_collection()
    
    # Vectorizare conținut (folosind Qwen 2.5)
    embedding = qdrant.vectorize_content(content_data)
    
    # Stocare în Qdrant
    metadata = {
        'url': content_data['url'],
        'title': content_data['title'],
        'description': content_data['description']
    }
    qdrant.store_embedding(content_id, embedding, metadata)
    
    print("✅ Vectorizare completă")
    print(f"🎉 Agent AI creat pentru site-ul: {url}")
    
    return {
        'content_id': content_id,
        'url': url,
        'title': content_data['title']
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        process_site_to_ai_agent(url)
    else:
        print("Utilizare: python main_pipeline.py <URL_SITE>")
