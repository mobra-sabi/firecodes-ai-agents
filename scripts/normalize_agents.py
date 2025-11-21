# scripts/normalize_agents.py
import os
from urllib.parse import urlparse
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:9308/")
client = MongoClient(MONGO_URI)
db = client.ai_agents_db
col = db.agents

def norm_domain(s):
    if not s:
        return None
    host = s.strip().lower()
    if "://" in host:
        host = urlparse(host).netloc
    if host.startswith("www."):
        host = host[4:]
    if ":" in host:
        host = host.split(":")[0]
    return host or None

now = datetime.now(timezone.utc)

bulk = []
for doc in col.find({}):
    _id = doc["_id"]
    domain = doc.get("domain")
    site_url = doc.get("site_url")
    name = doc.get("name")

    if not domain and site_url:
        domain = norm_domain(site_url)

    upd = {}
    if domain and doc.get("domain") != domain:
        upd["domain"] = domain
    if not name and domain:
        upd["name"] = domain
    if "createdAt" not in doc:
        upd["createdAt"] = now
    if "updatedAt" not in doc:
        upd["updatedAt"] = now
    if not doc.get("status"):
        upd["status"] = "ready"  # sau “created”, cum preferi

    if upd:
        upd["updatedAt"] = now
        bulk.append({"_id": _id, "upd": upd})

if bulk:
    from pymongo import UpdateOne
    ops = [UpdateOne({"_id": b["_id"]}, {"$set": b["upd"]}) for b in bulk]
    res = col.bulk_write(ops)
    print("Updated:", res.bulk_api_result)
else:
    print("No changes needed.")

# index pe domain (unicat + sparse ca să ignore recordurile fără domain)
try:
    col.create_index([("domain", ASCENDING)], unique=True, sparse=True, name="uniq_domain")
    print("Index created: uniq_domain")
except Exception as e:
    print("Index create error:", e)
