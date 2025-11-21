import pymongo
from pymongo import MongoClient, TEXT
from typing import Dict, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse

# >>> Folosește setările unificate
from config.database_config import (
    MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION
)

def _norm_domain(u: str) -> str:
    try:
        netloc = urlparse(u).netloc or u
        return netloc.lower().lstrip("www.")
    except Exception:
        return (u or "").lower().lstrip("www.")

class MongoDBHandler:
    def __init__(self):
        self.MONGODB_URI = MONGODB_URI
        self.MONGODB_DATABASE = MONGODB_DATABASE
        self.MONGODB_COLLECTION = MONGODB_COLLECTION

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
            col.create_index([("domain", 1), ("text_hash", 1)], unique=False, name="by_domain_hash")
            try:
                col.create_index([("title", TEXT), ("content", TEXT)], name="text_idx")
            except Exception:
                pass
            print("✅ Mongo indexes ensured")
        except Exception as idx_e:
            print(f"⚠️ Could not ensure Mongo indexes: {idx_e}")

    def save_site_content(self, content_data: Dict) -> bool:
        """Salvează/actualizează conținutul unui site în MongoDB (upsert by URL)."""
        try:
            collection = self.db[self.MONGODB_COLLECTION]
            content_data.setdefault("timestamp", datetime.now(timezone.utc))
            if "url" not in content_data:
                raise ValueError("content_data trebuie să conțină 'url'")
            # setează domeniul (ajută la căutări)
            if "domain" not in content_data:
                content_data["domain"] = _norm_domain(content_data["url"])
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

    def get_site_content(self, site_url: str) -> Optional[Dict]:
        """
        Returnează un document reprezentativ pentru un site:
        - întâi caută după domeniu,
        - apoi caută o pagină home (url care se termină cu '/').
        """
        try:
            col = self.db[self.MONGODB_COLLECTION]
            dom = _norm_domain(site_url)

            # 1) orice document pentru domeniu (cel mai recent)
            doc = col.find_one(
                {"domain": dom},
                sort=[("timestamp", -1)],
                projection={"_id": 0, "url": 1, "domain": 1, "title": 1, "content": 1, "description": 1, "timestamp": 1}
            )
            if doc:
                return doc

            # 2) fallback: url ce pare homepage
            doc = col.find_one(
                {"url": {"$regex": rf"^https?://(www\.)?{dom}/?$"}},
                sort=[("timestamp", -1)],
                projection={"_id": 0, "url": 1, "domain": 1, "title": 1, "content": 1, "description": 1, "timestamp": 1}
            )
            return doc
        except Exception as e:
            print(f"⚠️ get_site_content error: {e}")
            return None
