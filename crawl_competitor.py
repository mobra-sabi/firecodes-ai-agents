import requests
from bs4 import BeautifulSoup
import json
import time

def crawl_site(base_url):
    print(f"Crawling {base_url}...")
    try:
        # Get main page
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; AI_Agent/1.0)'}
        response = requests.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract Menu Items (Services)
        menu_items = []
        nav = soup.find('nav') or soup.find('header')
        if nav:
            links = nav.find_all('a')
            for link in links:
                text = link.get_text(strip=True)
                href = link.get('href')
                if text and href and href.startswith('http'):
                    menu_items.append({'text': text, 'url': href})
        
        # Extract Main Services Content from Homepage
        services = []
        # Look for service lists (usually ul/li or h3 headings)
        content_areas = soup.find_all(['article', 'main', 'div'], class_=lambda x: x and 'content' in x)
        
        for area in content_areas:
            headings = area.find_all(['h2', 'h3'])
            for h in headings:
                services.append(h.get_text(strip=True))

        return {
            "menu": menu_items,
            "headings": services,
            "raw_text": soup.get_text()[:2000] # Sample
        }

    except Exception as e:
        print(f"Error crawling: {e}")
        return None

if __name__ == "__main__":
    data = crawl_site("https://www.isuautorizari.ro/autorizatii-isu/")
    print(json.dumps(data, indent=2, ensure_ascii=False))

