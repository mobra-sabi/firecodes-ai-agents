import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse

class EnhancedSiteScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def scrape_complete_site(self, max_pages=10):
        """Scrapuire completă a site-ului"""
        all_content = []
        visited_urls = set()
        urls_to_visit = [self.base_url]
        
        print(f"🕷️ Încep scraping complet pentru {self.base_url}")
        
        for i in range(min(max_pages, len(urls_to_visit))):
            if not urls_to_visit:
                break
                
            current_url = urls_to_visit.pop(0)
            if current_url in visited_urls:
                continue
                
            print(f"📄 Scraping pagina {i+1}: {current_url}")
            
            try:
                content = self.scrape_single_page(current_url)
                if content:
                    all_content.append(content)
                    visited_urls.add(current_url)
                    
                    # Găsește link-uri interne pentru scraping suplimentar
                    internal_links = self.find_internal_links(current_url)
                    for link in internal_links[:3]:  # Max 3 link-uri noi per pagină
                        if link not in visited_urls and link not in urls_to_visit:
                            urls_to_visit.append(link)
                            
                time.sleep(1)  # Respect pentru server
                
            except Exception as e:
                print(f"⚠️ Eroare la {current_url}: {e}")
                
        # Combină tot conținutul
        combined_content = self.combine_content(all_content)
        print(f"✅ Scraping complet: {len(all_content)} pagini, {len(combined_content['content'])} caractere")
        
        return combined_content
        
    def scrape_single_page(self, url):
        """Scrapuire o pagină individuală"""
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Elimină elemente nedorite
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
            
        # Extrage informații
        title = soup.find('title').text.strip() if soup.find('title') else ""
        
        # Prioritizează conținutul principal
        main_content = ""
        
        # Încearcă să găsească main content
        for selector in ['main', '.main-content', '#main', '.content', 'article']:
            main_element = soup.select_one(selector)
            if main_element:
                main_content = main_element.get_text(separator=' ', strip=True)
                break
                
        # Dacă nu găsește main, ia din body
        if not main_content:
            main_content = soup.get_text(separator=' ', strip=True)
            
        return {
            'url': url,
            'title': title,
            'content': main_content[:5000]  # Limitează per pagină
        }
        
    def find_internal_links(self, current_url):
        """Găsește link-uri interne pentru scraping suplimentar"""
        try:
            response = self.session.get(current_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            base_domain = urlparse(self.base_url).netloc
            internal_links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(current_url, href)
                
                # Verifică dacă e link intern
                if urlparse(full_url).netloc == base_domain:
                    # Evită link-uri cu parametri sau ancore
                    if not any(x in full_url for x in ['#', '?', 'mailto:', 'tel:']):
                        internal_links.append(full_url)
                        
            return list(set(internal_links))[:5]  # Max 5 link-uri unice
            
        except Exception as e:
            print(f"⚠️ Eroare la găsirea link-urilor: {e}")
            return []
            
    def combine_content(self, all_content):
        """Combină conținutul de pe toate paginile"""
        if not all_content:
            return None
            
        main_page = all_content[0]
        
        # Combină titlurile
        all_titles = [page['title'] for page in all_content if page['title']]
        combined_title = all_titles[0] if all_titles else ""
        
        # Combină conținutul
        all_text = []
        for page in all_content:
            if page['content']:
                all_text.append(f"Pagina {page['url']}: {page['content']}")
                
        combined_content = " | ".join(all_text)
        
        return {
            'url': self.base_url,
            'title': combined_title,
            'content': combined_content[:15000],  # Limita totală
            'pages_scraped': len(all_content),
            'timestamp': time.time()
        }
