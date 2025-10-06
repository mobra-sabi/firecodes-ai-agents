import os
from pymongo import MongoClient

def _db():
    mongo = os.getenv("MONGODB_URI","mongodb://127.0.0.1:27017")
    name  = os.getenv("MONGO_DB","ai_agents_db")
    return MongoClient(mongo)[name]

def quick_report(session_new_domains):
    agents = _db()["site_agents"]
    total = agents.estimated_document_count()
    top = list(agents.find({}, {"_id":0,"domain":1,"pages":1}).sort("pages",-1).limit(12))
    return {
        "site_agents_total": total,
        "top_domains": top,
        "session_new_domains": sorted(set(session_new_domains or []))
    }
