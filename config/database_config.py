import os

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ai_agents_db")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "site_content")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "9306"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "mem_ai_agents")
