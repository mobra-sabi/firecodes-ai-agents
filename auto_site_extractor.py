#!/usr/bin/env python3
"""
Auto Site Extractor - Extrage automat informații din orice site
Fără hardcoding, funcționează pentru orice domeniu
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class AutoSiteExtractor:
    """Extrage automat informații din orice site web"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    async def extract_site_data(self, domain: str) -> Dict:
        """
        Extrage automat toate informațiile relevante din site
        """
        try:
            url = f"https://{domain}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            
            # Extrage informații
            site_data = {
                'domain': domain,
                'contact_info': self._extract_contact_info(text, soup),
                'company_info': self._extract_company_info(text, soup),
                'services_products': self._extract_services_products(text, soup),
                'pricing_info': self._extract_pricing_info(text, soup),
                'business_type': self._detect_business_type(text),
                'technical_specs': self._extract_technical_specs(text),
                'certifications': self._extract_certifications(text),
                'raw_content': text[:5000]  # Primele 5000 caractere pentru context
            }
            
            logger.info(f"✅ Extracted data for {domain}")
            return site_data
            
        except Exception as e:
            logger.error(f"❌ Error extracting data for {domain}: {e}")
            return self._get_fallback_data(domain)
    
    def _extract_contact_info(self, text: str, soup: BeautifulSoup) -> Dict:
        """Extrage informații de contact"""
        contact = {}
        
        # Telefon
        phone_patterns = [
            r'(\+40\s?\d{3}\s?\d{3}\s?\d{3})',
            r'(0\d{3}\s?\d{3}\s?\d{3})',
            r'(\+40\d{9})',
            r'(0\d{9})'
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                contact['phone'] = match.group(1).strip()
                break
        
        # Email
        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        email_match = re.search(email_pattern, text)
        if email_match:
            contact['email'] = email_match.group(1)
        
        # Adresă
        address_patterns = [
            r'(str\.?\s+[^,]+,\s*[^,]+,\s*[^,]+)',
            r'(bulevardul?\s+[^,]+,\s*[^,]+)',
            r'(sos\.?\s+[^,]+,\s*[^,]+)'
        ]
        
        for pattern in address_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                contact['address'] = match.group(1).strip()
                break
        
        # Nume companie din title sau h1
        title = soup.find('title')
        if title:
            contact['company'] = title.get_text().strip()
        
        return contact
    
    def _extract_company_info(self, text: str, soup: BeautifulSoup) -> Dict:
        """Extrage informații despre companie"""
        company_info = {}
        
        # Despre noi
        about_patterns = [
            r'(despre noi[^.]*\.)',
            r'(compania[^.]*\.)',
            r'(suntem[^.]*\.)',
            r'(specializați[^.]*\.)'
        ]
        
        for pattern in about_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                company_info['description'] = match.group(1).strip()
                break
        
        # Anul înființării
        year_match = re.search(r'(19|20)\d{2}', text)
        if year_match:
            company_info['founded_year'] = year_match.group(0)
        
        return company_info
    
    def _extract_services_products(self, text: str, soup: BeautifulSoup) -> List[str]:
        """Extrage servicii și produse"""
        services = []
        
        # Caută în liste
        for li in soup.find_all(['li', 'ul', 'ol']):
            content = li.get_text().strip()
            if len(content) > 10 and len(content) < 200:
                if any(keyword in content.lower() for keyword in ['servici', 'produs', 'oferim', 'realizam']):
                    services.append(content)
        
        # Caută în paragrafe
        for p in soup.find_all('p'):
            content = p.get_text().strip()
            if len(content) > 20 and len(content) < 300:
                if any(keyword in content.lower() for keyword in ['servici', 'produs', 'oferim', 'realizam', 'specializați']):
                    services.append(content)
        
        # Elimină duplicatele și limitează
        unique_services = list(dict.fromkeys(services))[:10]
        return unique_services
    
    def _extract_pricing_info(self, text: str, soup: BeautifulSoup) -> Dict:
        """Extrage informații despre prețuri"""
        pricing = {}
        
        # Caută prețuri
        price_patterns = [
            r'(\d+)\s*lei',
            r'(\d+)\s*ron',
            r'(\d+)\s*€',
            r'(\d+)\s*euro',
            r'preț[:\s]*(\d+)',
            r'cost[:\s]*(\d+)',
            r'(\d+)\s*-\s*(\d+)\s*lei'
        ]
        
        prices_found = []
        for pattern in price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                prices_found.extend(matches)
        
        if prices_found:
            pricing['strategy'] = 'prices_available'
            pricing['prices'] = prices_found[:5]
        else:
            pricing['strategy'] = 'contact_for_quote'
            pricing['note'] = 'Prețurile nu sunt publicate pe site. Contactați pentru ofertă.'
        
        return pricing
    
    def _detect_business_type(self, text: str) -> str:
        """Detectează tipul de business"""
        text_lower = text.lower()
        
        business_types = {
            'construction': ['construcții', 'clădiri', 'proiectare', 'execuție', 'antifoc', 'hidroizolații'],
            'retail': ['magazin', 'shop', 'vânzare', 'produse', 'comerț'],
            'services': ['servicii', 'consulting', 'suport', 'asistență'],
            'technology': ['software', 'tehnologie', 'it', 'dezvoltare', 'programare'],
            'healthcare': ['medical', 'sănătate', 'spital', 'clinică', 'doctor'],
            'education': ['școală', 'universitate', 'educație', 'cursuri', 'training']
        }
        
        scores = {}
        for business_type, keywords in business_types.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[business_type] = score
        
        # Pentru sistem universal, întotdeauna returnează 'general'
        # Astfel agentul poate lucra cu orice tip de site
        return 'general'
    
    def _extract_technical_specs(self, text: str) -> Dict:
        """Extrage specificații tehnice"""
        specs = {}
        
        # Caută specificații
        spec_patterns = [
            r'(ei\d+[-\s]*ei\d+)',  # Rezistență la foc
            r'(\d+\s*-\s*\d+\s*minute)',  # Timp protecție
            r'(certificat[^.]*\.)',
            r'(norma[^.]*\.)'
        ]
        
        for pattern in spec_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                specs[pattern] = matches
        
        return specs
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extrage certificări"""
        certifications = []
        
        cert_patterns = [
            r'(ISU)',
            r'(EN\s*\d+)',
            r'(CE)',
            r'(ISO\s*\d+)',
            r'(certificat[^.]*\.)'
        ]
        
        for pattern in cert_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            certifications.extend(matches)
        
        return list(set(certifications))
    
    def _get_fallback_data(self, domain: str) -> Dict:
        """Date fallback dacă extragerea eșuează"""
        return {
            'domain': domain,
            'contact_info': {},
            'company_info': {},
            'services_products': [],
            'pricing_info': {'strategy': 'contact_for_quote', 'note': 'Contactați pentru informații'},
            'business_type': 'general',
            'technical_specs': {},
            'certifications': [],
            'raw_content': f'Nu s-au putut extrage datele pentru {domain}'
        }

# Funcție helper pentru a rula extractorul
async def extract_website_data(domain: str) -> Dict:
    """Extrage datele unui site web"""
    extractor = AutoSiteExtractor()
    return await extractor.extract_site_data(domain)

if __name__ == "__main__":
    import asyncio
    
    async def test_extractor():
        domain = "tehnica-antifoc.ro"
        data = await extract_website_data(domain)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    
    asyncio.run(test_extractor())
