import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scrapers.site_scraper import SiteScraper

def test_scraping():
    # Testează cu un site real
    scraper = SiteScraper("https://example.com")
    content = scraper.scrape_content()
    
    if content:
        print("✅ Scraping reușit!")
        print(f"Titlu: {content['title']}")
        print(f"URL: {content['url']}")
        print(f"Conținut lungime: {len(content['content'])} caractere")
    else:
        print("❌ Scraping eșuat!")

if __name__ == "__main__":
    test_scraping()
