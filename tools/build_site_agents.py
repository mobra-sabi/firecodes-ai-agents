import re
# tools/build_site_agents.py
import os, math
from langchain_ollama import OllamaEmbeddings
from collections import defaultdict
from urllib.parse import urlsplit

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL","nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434")
def get_embedder():
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)


from pymongo import MongoClient, ASCENDING
from qdrant_client import QdrantClient

# -------- Config robuste (fără importuri fragile) --------
QDRANT_HOST = os.getenv("QDRANT_HOST", "127.0.0.1")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "industry_mem")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")  # fallback SAFE

def norm_domain(d: str) -> str:
    d = (d or "").lower()
    return d[4:] if d.startswith("www.") else d

def payload_domain(p):
    p = p or {}
    d = p.get("domain")
    if not d:
        u = p.get("url", "")
        try:
            d = urlsplit(u).netloc
        except:
            d = ""
    return norm_domain(d)

def extract_vector(v):
    if v is None:
        return None
    if isinstance(v, dict):
        for k in ("content","default","text","embedding"):
            if k in v and v[k] is not None:
                return [float(x) for x in v[k]]
        try:
            first = next(iter(v.values()))
            return [float(x) for x in first] if first is not None else None
        except StopIteration:
            return None
    try:
        return [float(x) for x in v]
    except Exception:
        return None

def main():
    qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT,)
    mc = MongoClient(MONGODB_URI)
    db = mc[MONGO_DB]
    agents = db["site_agents"]
    agents.create_index([("domain", ASCENDING)], unique=True)

    sums = defaultdict(lambda: None)
    counts = defaultdict(int)

    next_page = None
    total = 0
    while True:
        pts, next_page = qc.scroll(
            collection_name=QDRANT_COLLECTION,
            with_vectors=True,
            with_payload=True,
            limit=1000,
            offset=next_page
        )
        if not pts:
            break
        for p in pts:
            dom = payload_domain(getattr(p, "payload", {}))
            if not dom:
                continue
            vec = extract_vector(getattr(p, "vector", None))
            if not vec:
                continue
            if sums[dom] is None:
                sums[dom] = vec[:]
            else:
                if len(sums[dom]) != len(vec):
                    continue
                for i, x in enumerate(vec):
                    sums[dom][i] += x
            counts[dom] += 1
            total += 1
        if next_page is None:
            break

    upserts = 0
    for dom, s in sums.items():
        n = counts[dom]
        if not s or n == 0:
            continue
        mean = [x / n for x in s]
        l2 = math.sqrt(sum(x*x for x in mean)) or 1.0
        mean = [x/l2 for x in mean]
        agents.update_one(
            {"domain": dom},
            {"$set": {"domain": dom, "centroid": mean, "pages": n}},
            upsert=True
        )
        upserts += 1

    print(f"OK: {upserts} site agents actualizați (din {len(counts)} domenii, {total} puncte)")

if __name__ == "__main__":
    main()
