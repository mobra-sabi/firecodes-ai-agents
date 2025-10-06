import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urljoin, urlparse

class SiteScraper:
    def __init__(self, url):
        # Adaugă scheme automat dacă lipsește
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        self.url = url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def scrape_content(self):
        """Descarcă și parsează conținutul site-ului"""
        try:
            response = self.session.get(self.url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Elimină elementele nedorite
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()
            
            # Extrage informații relevante
            title = soup.find('title').text.strip() if soup.find('title') else ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ""
            
            # Extrage conținutul principal
            content_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            content = ' '.join([elem.get_text().strip() for elem in content_elements])
            
            # Dacă nu găsim conținut în elemente, luăm tot textul
            if not content:
                content = soup.get_text()
                
            return {
                'url': self.url,
                'title': title,
                'description': description,
                'content': content[:10000],  # Limităm pentru eficiență
                'timestamp': time.time()
            }
        except Exception as e:
            print(f"Eroare la scraping: {e}")
            return None
            
    def scrape_multiple_pages(self, max_pages=5):
        """Scrape pagini multiple de pe site"""
        # Implementare pentru scraping pagini multiple
        pages_content = []
        main_content = self.scrape_content()
        if main_content:
            pages_content.append(main_content)
        return pages_content
