import os

# Configurație RO-INDEX Crawler

# Baza de date
MONGO_URI = "mongodb://localhost:27018/"
DB_NAME = "ro_index_db"
COLLECTION_QUEUE = "crawl_queue"
COLLECTION_SITES = "crawled_sites"

# Stocare
STORAGE_PATH = "/srv/hf/ro_index/raw_html"

# Setări Crawler
MAX_DEPTH = 3  # Cât de adânc intră într-un site (HomePage + 2 clicks)
MAX_PAGES_PER_DOMAIN = 50 # Limită pagini per site (pentru diversitate)
CONCURRENT_WORKERS = 100  # Turbo Mode: 100 workers for 3-day completion
REQUEST_TIMEOUT = 30
USER_AGENT = "RO-IndexBot/1.0 (+http://viezure-server.local)"

# Mod de lucru
USE_AWS_LAMBDA = True  # ACTIVAT!

# Filtre
ALLOWED_TLDS = ['.ro'] # Scanăm doar România momentan
BLOCKED_DOMAINS = ['facebook.com', 'google.com', 'twitter.com', 'instagram.com', 'youtube.com', 'linkedin.com', 'whatsapp.com']
