# Qdrant Configuration
# Qdrant rulează în Docker pe portul 9306 (mapped de la 6333)
QDRANT_HOST = "localhost"
QDRANT_PORT = 9306  # Portul Docker, nu 6333
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
