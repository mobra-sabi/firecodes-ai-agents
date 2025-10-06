import pymongo
from pymongo import MongoClient, TEXT
from typing import Dict, List, Optional
import json
from datetime import datetime

class MongoDBHandler:
    def __init__(self):
        # Configurație directă fără import extern
        self.MONGODB_URI = "mongodb://localhost:27017/"
        self.MONGODB_DATABASE = "ai_agents_db"
        self.MONGODB_COLLECTION = "site_content"
        
        self.client = MongoClient(self.MONGODB_URI)
        self.db = self.client[self.MONGODB_DATABASE]
        
        # Test conexiunea
        try:
            self.client.admin.command('ping')
            print("✅ Conectat la MongoDB")
        except Exception as e:
            print(f"❌ Eroare conexiune MongoDB: {e}")

        # Ensure indexes (idempotent)
        try:
            col = self.db[self.MONGODB_COLLECTION]
            col.create_index([("url", 1)], unique=True, name="uniq_url")
            col.create_index([("timestamp", -1)], name="ts_desc")
            # Optional text index for quick keyword search
            try:
                col.create_index([("title", TEXT), ("content", TEXT)], name="text_idx")
            except Exception:
                pass
            print("✅ Mongo indexes ensured")
        except Exception as idx_e:
            print(f"⚠️ Could not ensure Mongo indexes: {idx_e}")
    
    def save_site_content(self, content_data: Dict) -> bool:
        """Salvează conținutul unui site în MongoDB"""
        try:
            collection = self.db[self.MONGODB_COLLECTION]
            # Asigură-te că există câmpuri de bază
            content_data.setdefault("timestamp", datetime.utcnow())
            if "url" not in content_data:
                raise ValueError("content_data trebuie să conțină 'url'")
            # Upsert după URL (nu dublăm pagini)
            collection.update_one(
                {"url": content_data["url"]},
                {"$set": content_data},
                upsert=True
            )
            print(f"✅ Conținut salvat/actualizat pentru {content_data.get('url', 'N/A')}")
            return True
        except Exception as e:
            print(f"❌ Eroare la salvarea conținutului: {e}")
            return False

    # … restul metodelor tale existente (ex: combine_content, etc.) …
    # (Nu le-am șters – doar am adăugat importul TEXT și blocul de indexuri.)

