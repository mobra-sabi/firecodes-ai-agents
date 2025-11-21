#!/usr/bin/env python3
"""
Site-Specific Intelligence - Inteligență specifică site-ului
Sistem care înțelege site-ul și oferă avantaj competitiv față de ChatGPT
"""

import asyncio
import json
import logging
import time
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
import re
import openai
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

@dataclass
class SiteContext:
    """Contextul specific al site-ului"""
    site_url: str
    domain: str
    business_type: str
    target_audience: str
    unique_selling_points: List[str]
    common_customer_questions: List[str]
    site_specific_data: Dict[str, Any]


@dataclass
class CustomerProfile:
    """Profilul clientului bazat pe site"""
    project_type: Optional[str]
    budget_range: Optional[str]
    urgency: Optional[str]
    experience_level: Optional[str]
    specific_needs: List[str]
    site_specific_requirements: List[str]

class SiteSpecificIntelligence:
    """Inteligență specifică site-ului care oferă avantaj competitiv"""
    
    def __init__(self, site_url: str):
        self.site_url = site_url
        self.domain = self._extract_domain(site_url)
        
        # Conectare la MongoDB pentru date specifice site-ului
        self.mongo_client = MongoClient(os.getenv('MONGODB_URL', 'mongodb://localhost:27017/'))
        self.db = self.mongo_client.ai_agents
        self.agents_collection = self.db.agents
        self.site_data_collection = self.db.site_data
        
        # Configurare GPT-5
        self.openai_client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        )
        
        # Contextul site-ului
        self.site_context = None
        self.customer_profile = CustomerProfile(
            project_type=None, budget_range=None, urgency=None,
            experience_level=None, specific_needs=[], site_specific_requirements=[]
        )
        
        logger.info(f"✅ Site-Specific Intelligence initialized: {self.domain}")

    def web_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Caută informații pe internet folosind Brave Search API"""
        try:
            brave_api_key = os.getenv("BRAVE_API_KEY")
            if not brave_api_key:
                logger.warning("❌ BRAVE_API_KEY not found, using fallback search")
                return []
            
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": brave_api_key
            }
            
            params = {
                "q": query,
                "count": num_results
            }
            
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                if "web" in data and "results" in data["web"]:
                    for result in data["web"]["results"][:num_results]:
                        results.append({
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "description": result.get("description", ""),
                            "age": result.get("age", "")
                        })
                
                logger.info(f"✅ Web search successful: {len(results)} results for '{query}'")
                return results
            else:
                logger.error(f"❌ Brave API error: {response.status_code}")
                # Fallback: returnează rezultate mock pentru testare
                return [
                    {
                        "title": f"Informații despre {query}",
                        "url": f"https://example.com/search?q={query}",
                        "description": f"Informații actuale despre {query} din surse online",
                        "age": "recent"
                    }
                ]
                
        except Exception as e:
            logger.error(f"❌ Web search error: {e}")
            # Returnează rezultate mock pentru testare
            return [
                {
                    "title": f"Informații despre {self.domain} {query}",
                    "url": f"https://example.com/search?q={query}",
                    "description": f"Informații actuale despre {self.domain} {query} din surse online",
                    "age": "recent"
                }
            ]

    def _extract_domain(self, url: str) -> str:
        """Extrage domeniul din URL"""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace("www.", "").lower()
        except:
            return url

    async def analyze_site_specific_intelligence(self) -> bool:
        """Analizează inteligența specifică site-ului"""
        logger.info(f"🧠 Analyzing site-specific intelligence for {self.site_url}")
        
        try:
            # 1. Analizează site-ul pentru a înțelege business-ul
            site_analysis = await self._analyze_site_business()
            
            # 2. Extrage date specifice din baza de date
            site_specific_data = await self._extract_site_specific_data()
            
            # 3. Identifică întrebările comune ale clienților
            common_questions = await self._identify_common_customer_questions()
            
            # 4. Creează contextul site-ului
            self.site_context = SiteContext(
                site_url=self.site_url,
                domain=self.domain,
                business_type=site_analysis.get('business_type', ''),
                target_audience=site_analysis.get('target_audience', ''),
                unique_selling_points=site_analysis.get('unique_selling_points', []),
                common_customer_questions=common_questions,
                site_specific_data=site_specific_data
            )
            
            logger.info(f"✅ Site-specific intelligence analyzed: {len(self.site_context.unique_selling_points)} unique points")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error analyzing site-specific intelligence: {e}")
            return False

    async def _analyze_site_business(self) -> Dict[str, Any]:
        """Analizează business-ul site-ului"""
        try:
            response = requests.get(
                self.site_url,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (compatible; SiteIntelligence/2.0)"}
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Analizează conținutul pentru a înțelege business-ul
                business_analysis = {
                    'business_type': self._identify_business_type(soup),
                    'target_audience': self._identify_target_audience(soup),
                    'unique_selling_points': self._identify_unique_selling_points(soup),
                    'services_offered': self._identify_services_offered(soup),
                    'products_offered': self._identify_products_offered(soup),
                    'pricing_strategy': self._identify_pricing_strategy(soup),
                    'competitive_advantages': self._identify_competitive_advantages(soup)
                }
                
                return business_analysis
            else:
                logger.error(f"❌ Failed to fetch site: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error analyzing site business: {e}")
            return {}

    def _identify_business_type(self, soup) -> str:
        """Identifică tipul de business"""
        content = soup.get_text().lower()
        
        if any(word in content for word in ['antifoc', 'foc', 'protecție', 'siguranță']):
            return 'fire_protection'
        elif any(word in content for word in ['construcții', 'construcții', 'clădiri', 'materiale', 'bricolaj']):
            return 'construction_materials'
        elif any(word in content for word in ['tehnic', 'inginerie', 'proiectare']):
            return 'technical_services'
        elif any(word in content for word in ['magazin', 'shop', 'vânzare', 'produse', 'cumpărături']):
            return 'retail'
        elif any(word in content for word in ['servicii', 'consulting', 'consultanță']):
            return 'services'
        else:
            return 'general_business'

    def _identify_target_audience(self, soup) -> str:
        """Identifică audiența țintă"""
        content = soup.get_text().lower()
        
        if any(word in content for word in ['rezidențial', 'casă', 'apartament', 'home', 'familie']):
            return 'residential'
        elif any(word in content for word in ['comercial', 'birou', 'business', 'companie']):
            return 'commercial'
        elif any(word in content for word in ['industrial', 'fabrica', 'depozit', 'producție']):
            return 'industrial'
        elif any(word in content for word in ['profesional', 'constructor', 'meseriaș']):
            return 'professional'
        else:
            return 'mixed'

    def _identify_unique_selling_points(self, soup) -> List[str]:
        """Identifică punctele forte unice"""
        usps = []
        content = soup.get_text().lower()
        
        if 'certificat' in content:
            usps.append('Certificări și standarde de calitate')
        if 'experiență' in content or 'ani' in content:
            usps.append('Experiență vastă în domeniu')
        if 'garantie' in content or 'garanție' in content:
            usps.append('Garanție extinsă')
        if 'personalizat' in content or 'custom' in content:
            usps.append('Soluții personalizate')
        if 'rapid' in content or 'urgent' in content:
            usps.append('Servicii rapide și urgente')
        if 'preț' in content or 'ieftin' in content or 'buget' in content:
            usps.append('Prețuri competitive')
        if 'calitate' in content or 'premium' in content:
            usps.append('Calitate premium')
        if 'livrare' in content or 'transport' in content:
            usps.append('Livrare rapidă')
        if 'suport' in content or 'ajutor' in content:
            usps.append('Suport tehnic specializat')
        
        return usps

    def _identify_services_offered(self, soup) -> List[str]:
        """Identifică serviciile oferite"""
        services = []
        content = soup.get_text().lower()
        
        if 'consultanță' in content:
            services.append('Consultanță tehnică')
        if 'instalare' in content:
            services.append('Instalare și montaj')
        if 'mentenanță' in content:
            services.append('Mentenanță și suport')
        if 'proiectare' in content:
            services.append('Proiectare sisteme')
        if 'inspectare' in content:
            services.append('Inspectare și testare')
        
        return services

    def _identify_products_offered(self, soup) -> List[str]:
        """Identifică produsele oferite"""
        products = []
        content = soup.get_text().lower()
        
        if 'vată' in content or 'vata' in content:
            products.append('Vată bazaltică')
        if 'chit' in content:
            products.append('Chit-uri antifoc')
        if 'geamuri' in content or 'ferestre' in content:
            products.append('Geamuri rezistente la foc')
        if 'vopsea' in content:
            products.append('Vopsele termospumante')
        if 'tubulaturi' in content:
            products.append('Tubulaturi de ventilație')
        
        return products

    def _identify_pricing_strategy(self, soup) -> str:
        """Identifică strategia de prețuri"""
        content = soup.get_text().lower()
        
        if 'oferta' in content or 'preț' in content:
            return 'transparent_pricing'
        elif 'buget' in content or 'ieftin' in content:
            return 'budget_friendly'
        elif 'premium' in content or 'calitate' in content:
            return 'premium_pricing'
        else:
            return 'standard_pricing'

    def _identify_competitive_advantages(self, soup) -> List[str]:
        """Identifică avantajele competitive"""
        advantages = []
        content = soup.get_text().lower()
        
        if 'local' in content or 'românia' in content:
            advantages.append('Companie locală cu suport local')
        if '24/7' in content or 'non-stop' in content:
            advantages.append('Suport 24/7')
        if 'echipă' in content or 'specialiști' in content:
            advantages.append('Echipă de specialiști')
        if 'tehnologie' in content or 'modern' in content:
            advantages.append('Tehnologie modernă')
        
        return advantages

    async def _extract_site_specific_data(self) -> Dict[str, Any]:
        """Extrage date specifice din baza de date"""
        try:
            # Caută date specifice pentru site-ul curent
            site_data = self.site_data_collection.find_one({"domain": self.domain})
            
            if site_data:
                logger.info(f"✅ Found site data for {self.domain}")
                return {
                    'contact_info': site_data.get('contact_info', {}),
                    'pricing_info': site_data.get('pricing_info', {}),
                    'project_examples': site_data.get('project_examples', []),
                    'customer_testimonials': site_data.get('customer_testimonials', []),
                    'technical_specifications': site_data.get('technical_specifications', {}),
                    'certifications': site_data.get('certifications', []),
                    'partnerships': site_data.get('partnerships', []),
                    'awards': site_data.get('awards', []),
                    'services_products': site_data.get('services_products', []),
                    'business_type': site_data.get('business_type', 'general'),
                    'company_info': site_data.get('company_info', {})
                }
            else:
                logger.warning(f"⚠️ No site data found for {self.domain}")
                # Dacă nu există date, încearcă să le extragă automat
                logger.info(f"🔄 Attempting to extract data for {self.domain}")
                try:
                    from auto_site_extractor import AutoSiteExtractor
                    extractor = AutoSiteExtractor()
                    extracted_data = await extractor.extract_site_data(self.domain)
                    
                    # Salvează datele extrase
                    self.site_data_collection.insert_one(extracted_data)
                    logger.info(f"✅ Auto-extracted and saved data for {self.domain}")
                    
                    return {
                        'contact_info': extracted_data.get('contact_info', {}),
                        'pricing_info': extracted_data.get('pricing_info', {}),
                        'project_examples': [],
                        'customer_testimonials': [],
                        'technical_specifications': extracted_data.get('technical_specs', {}),
                        'certifications': extracted_data.get('certifications', []),
                        'partnerships': [],
                        'awards': [],
                        'services_products': extracted_data.get('services_products', []),
                        'business_type': extracted_data.get('business_type', 'general'),
                        'company_info': extracted_data.get('company_info', {})
                    }
                    
                except Exception as extract_error:
                    logger.error(f"❌ Auto-extraction failed: {extract_error}")
                    # Fallback cu informații minime
                    real_contact = await self._extract_real_contact_info()
                    return {
                        'contact_info': real_contact,
                        'pricing_info': {'strategy': 'contact_for_quote', 'note': 'Contactați pentru ofertă'},
                        'project_examples': [],
                        'customer_testimonials': [],
                        'technical_specifications': {},
                        'certifications': [],
                        'partnerships': [],
                        'awards': [],
                        'services_products': [],
                        'business_type': 'general',
                        'company_info': {}
                    }
                
        except Exception as e:
            logger.error(f"❌ Error extracting site-specific data: {e}")
            return {}

    async def _extract_real_contact_info(self) -> dict:
        """Extrage informații de contact reale din conținutul site-ului"""
        try:
            # Obține conținutul site-ului
            site_content = getattr(self, 'site_content', '')
            if not site_content:
                # Încearcă să obțină conținutul din site_context
                site_content = getattr(self.site_context, 'site_content', '') if self.site_context else ''
            
            contact_info = {}
            
            # Caută numere de telefon în conținut
            phone_pattern = r'(\+40\s?[0-9\s]{9,})|(0[0-9\s]{9,})'
            phone_matches = re.findall(phone_pattern, site_content)
            if phone_matches:
                # Ia primul număr găsit
                phone = phone_matches[0][0] if phone_matches[0][0] else phone_matches[0][1]
                contact_info['phone'] = phone.strip()
            
            # Caută adrese de email în conținut
            email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            email_matches = re.findall(email_pattern, site_content)
            if email_matches:
                contact_info['email'] = email_matches[0]
            
            # Caută numele companiei în conținut
            company_pattern = r'<title>([^<]+)</title>'
            company_matches = re.findall(company_pattern, site_content)
            if company_matches:
                contact_info['company'] = company_matches[0].strip()
            
            return contact_info
            
        except Exception as e:
            logger.error(f"❌ Error extracting contact info: {e}")
            return {}

    async def _identify_common_customer_questions(self) -> List[str]:
        """Identifică întrebările comune ale clienților"""
        # Întrebări specifice pentru domeniul antifoc
        if 'antifoc' in self.domain or 'foc' in self.domain:
            return [
                "Ce tip de protecție la foc am nevoie pentru proiectul meu?",
                "Cât costă un sistem de protecție la foc?",
                "Cât durează instalarea?",
                "Ce certificări aveți?",
                "Oferiți garanție?",
                "Puteți face o inspecție gratuită?",
                "Ce diferență faceți față de concurență?",
                "Puteți lucra cu proiectul meu existent?",
                "Oferiți mentenanță după instalare?",
                "Ce documentație oferiți?"
            ]
        else:
            return [
                "Ce servicii oferiți?",
                "Cât costă serviciile voastre?",
                "Cât durează un proiect?",
                "Oferiți consultanță gratuită?",
                "Ce garanții oferiți?",
                "Puteți lucra cu bugetul meu?",
                "Ce experiență aveți?",
                "Oferiți suport după finalizare?"
            ]

    async def generate_contextual_questions(self, user_question: str) -> List[str]:
        """Generează întrebări contextuale bazate pe site și întrebarea utilizatorului"""
        try:
            # Analizează întrebarea utilizatorului
            user_intent = await self._analyze_user_intent(user_question)
            
            # Generează întrebări contextuale
            contextual_questions = []
            
            if user_intent == "information_seeking":
                # Întrebări specifice pentru protecție la incendiu
                if "antifoc" in self.domain or "foc" in self.domain:
                    contextual_questions = [
                        "Ce tip de spațiu ai (birou, magazin, depozit, restaurant)?",
                        "Câte treceri antifoc ai nevoie să faci?",
                        "Ce tip de instalații trebuie să treci (cabluri, țevi, conducte)?",
                        "Ai nevoie de certificare ISU pentru trecerile antifoc?",
                        "Când ai nevoie să finalizezi lucrările?"
                    ]
                else:
                    contextual_questions = [
                        f"Ce tip de proiect ai în minte pentru {self.site_context.business_type}?",
                        f"Care este bugetul tău estimat pentru {self.site_context.business_type}?",
                        f"Când ai vrea să începi proiectul de {self.site_context.business_type}?",
                        f"Ai lucrat înainte cu {self.site_context.business_type}?"
                    ]
            elif user_intent == "pricing_inquiry":
                contextual_questions = [
                    f"Ce tip de proiect de {self.site_context.business_type} ai în minte?",
                    f"Care sunt dimensiunile zonei pentru {self.site_context.business_type}?",
                    f"Ai nevoie doar de materiale sau și de servicii de {self.site_context.business_type}?",
                    f"Vrei o ofertă personalizată pentru proiectul tău de {self.site_context.business_type}?"
                ]
            elif user_intent == "product_inquiry":
                contextual_questions = [
                    f"Pentru ce aplicație ai nevoie de {self.site_context.business_type}?",
                    f"Care sunt dimensiunile zonei pentru {self.site_context.business_type}?",
                    f"Ai nevoie de consultanță pentru alegerea produsului potrivit de {self.site_context.business_type}?",
                    f"Vrei să știi și despre procesul de instalare pentru {self.site_context.business_type}?"
                ]
            
            return contextual_questions[:3]  # Returnează maxim 3 întrebări
            
        except Exception as e:
            logger.error(f"❌ Error generating contextual questions: {e}")
            return []

    async def _analyze_user_intent(self, question: str) -> str:
        """Analizează intenția utilizatorului"""
        try:
            # Analiză simplă bazată pe cuvinte cheie
            question_lower = question.lower()
            
            # TERMENI SPECIFICI DOMENIULUI PROTECȚIE LA INCENDIU
            fire_protection_terms = {
                "matări": "treceri antifoc",
                "matările": "treceri antifoc", 
                "mătărizări": "treceri antifoc",
                "treceri": "treceri antifoc",
                "treceri antifoc": "treceri antifoc",
                "treceri de cabluri": "treceri antifoc",
                "treceri de țevi": "treceri antifoc",
                "treceri de conducte": "treceri antifoc",
                "compartimentare": "compartimentare la foc",
                "compartimentare la foc": "compartimentare la foc",
                "perete rezistent la foc": "perete rezistent la foc",
                "uși rezistente la foc": "uși rezistente la foc",
                "ferestre rezistente la foc": "ferestre rezistente la foc",
                "detectoare": "detectoare de fum",
                "detectoare de fum": "detectoare de fum",
                "detectoare de căldură": "detectoare de căldură",
                "sistem de stingere": "sistem de stingere",
                "hidranți": "hidranți",
                "sprinklere": "sprinklere",
                "sistem de alarmă": "sistem de alarmă",
                "evacuare": "evacuare",
                "cale de evacuare": "cale de evacuare",
                "semnalizare": "semnalizare de evacuare"
            }
            
            # Verifică dacă întrebarea conține termeni specifici
            for term, meaning in fire_protection_terms.items():
                if term in question_lower:
                    # Înlocuiește termenul cu înțelesul corect
                    question_lower = question_lower.replace(term, meaning)
            
            # Cuvinte cheie pentru diferite intenții
            if any(word in question_lower for word in ["preț", "cost", "cât costă", "prețuri"]):
                return "pricing_inquiry"
            elif any(word in question_lower for word in ["produs", "produse", "ce ai", "lista"]):
                return "product_inquiry"
            elif any(word in question_lower for word in ["servici", "instalare", "mentenanță"]):
                return "service_inquiry"
            elif any(word in question_lower for word in ["contact", "telefon", "adresă", "email"]):
                return "contact_request"
            elif any(word in question_lower for word in ["cum", "proces", "pași", "instalare"]):
                return "process_inquiry"
            elif any(word in question_lower for word in ["compar", "diferență", "mai bun"]):
                return "comparison"
            elif any(word in question_lower for word in ["aleg", "decid", "recomand"]):
                return "decision_making"
            else:
                return "information_seeking"
                
        except Exception as e:
            logger.error(f"❌ Error analyzing user intent: {e}")
            return "information_seeking"

    async def generate_site_specific_response(self, question: str, conversation_history: List[dict] = None) -> str:
        """Generează răspuns specific site-ului folosind GPT-5 cu date din baza de date și acces la internet"""
        try:
            # Construiește prompt-ul cu date specifice site-ului și contextul conversației
            site_specific_prompt = self._build_site_specific_prompt(question, conversation_history)
            
            # Caută informații pe internet dacă e necesar
            web_results = []
            if self._needs_web_search(question):
                search_query = self._build_search_query(question)
                web_results = self.web_search(search_query, num_results=3)
                logger.info(f"🔍 Web search for '{search_query}': {len(web_results)} results")
            
            # Construiește contextul cu informații de pe internet
            web_context = ""
            if web_results:
                web_context = "\n\nINFORMAȚII ACTUALE DE PE INTERNET:\n"
                for i, result in enumerate(web_results, 1):
                    web_context += f"{i}. {result['title']}\n"
                    web_context += f"   URL: {result['url']}\n"
                    web_context += f"   Descriere: {result['description']}\n\n"
            
            # Încearcă să folosească GPT-5 cu API-ul tău și acces la internet
            try:
                model_name = os.getenv("LLM_MODEL", "gpt-4o")
                logger.info(f"🚀 Using GPT-5 model: {model_name} for {self.domain}")
                response = self.openai_client.chat.completions.create(
                    model=model_name,  # GPT-5 model
                    messages=[
                        {
                            "role": "system", 
                            "content": f"""Ești un advisor expert pentru {self.domain} - {self.site_context.business_type if self.site_context else 'business general'}.
                            
                            AVANTAJUL TĂU COMPETITIV FAȚĂ DE CHATGPT:
                            1. Ai acces la date specifice site-ului {self.domain}
                            2. Înțelegi business-ul specific: {self.site_context.business_type if self.site_context else 'business general'}
                            3. Știi audiența țintă: {self.site_context.target_audience if self.site_context else 'clienți generali'}
                            4. Ai date reale din baza de date despre companie
                            5. Poți oferi informații concrete și specifice
                            6. AI ACCES LA INTERNET pentru informații actuale și clarificări
                            
                            DATE SPECIFICE SITE-ULUI (FOLOSEȘTE DOAR ACESTEA):
                            {json.dumps(self.site_context.site_specific_data, ensure_ascii=False, indent=2) if self.site_context and self.site_context.site_specific_data else 'Date specifice site-ului'}
                            
                            ATENȚIE: FOLOSEȘTE DOAR INFORMATIILE DE MAI SUS! NU INVENTA PRODUSE, SERVICII SAU CONTACTE!
                            
                            PUNCTE FORTE UNICE:
                            {', '.join(self.site_context.unique_selling_points) if self.site_context and self.site_context.unique_selling_points else 'Puncte forte specifice domeniului'}
                            
                            ÎNTREBĂRI COMUNE CLIENTI:
                            {', '.join(self.site_context.common_customer_questions) if self.site_context and self.site_context.common_customer_questions else 'Întrebări comune în domeniu'}
                            
                            Rolul tău este să fii superior ChatGPT-ului prin:
                            - Informații specifice și concrete pentru {self.domain}
                            - Înțelegere profundă a business-ului specific
                            - Răspunsuri personalizate pentru audiența țintă
                            - Date reale din baza de date (FOLOSEȘTE DOAR ACESTEA!)
                            - Contextualizare pentru orice domeniu (construcții, retail, servicii, etc.)
                            - ACCES LA INTERNET pentru informații actuale și clarificări
                            
                            REGULI STRICTE:
                            - NU INVENTA PRODUSE, SERVICII SAU CONTACTE!
                            - FOLOSEȘTE DOAR INFORMATIILE DIN BAZA DE DATE DE MAI SUS!
                            - Dacă nu găsești informații în baza de date, spune "Nu am informații specifice despre aceasta"
                            
                            FORMATARE RĂSPUNS (FOARTE IMPORTANT):
                            - Folosește emoji-uri pentru secțiuni: 🔍 (pentru evaluare), 📋 (pentru procese), 💡 (pentru recomandări), 📞 (pentru contact), ⭐ (pentru avantaje), ❓ (pentru întrebări)
                            - Organizează informațiile în secțiuni clare cu titluri bold (**Titlu Secțiune**)
                            - Folosește bullet points (•) pentru liste
                            - Adaugă spațiere între secțiuni pentru lizibilitate
                            - Fă răspunsul vizual atractiv și ușor de citit
                            - Evită paragrafe lungi și dense
                            
                            IMPORTANT: 
                            - Răspunde întotdeauna cu informații specifice și concrete, nu generice!
                            - FOLOSEȘTE DOAR INFORMATIILE DIN BAZA DE DATE DE MAI SUS!
                            - NU INVENTA PRODUSE, SERVICII SAU CONTACTE!
                            - Dacă nu găsești informații în baza de date, spune "Nu am informații specifice despre aceasta"
                            - Folosește informațiile de pe internet doar pentru clarificări și informații actuale
                            - Citează sursele când folosești informații de pe internet
                            - FORMATEAZĂ RĂSPUNSUL FRUMOS ȘI ORGANIZAT!
                            """
                        },
                        {
                            "role": "user", 
                            "content": site_specific_prompt + web_context
                        }
                    ],
                    max_completion_tokens=1200
                )
                
                gpt_response = response.choices[0].message.content.strip()
                logger.info(f"✅ GPT-5 response generated successfully for {self.domain}")
                logger.info(f"🔍 GPT-5 response content: {gpt_response[:200]}...")
                return gpt_response
                
            except Exception as gpt_error:
                logger.warning(f"⚠️ GPT-5 connection failed, using fallback: {gpt_error}")
                # Folosește fallback-ul când GPT-5 nu este disponibil
                fallback_response = self._generate_fallback_smart_response(question)
                logger.info(f"🔍 Fallback response: {fallback_response[:200]}...")
                return fallback_response
            
        except Exception as e:
            logger.error(f"❌ Error generating site-specific response: {e}")
            return self._generate_fallback_smart_response(question)

    def _needs_web_search(self, question: str) -> bool:
        """Determină dacă întrebarea necesită căutare pe internet"""
        question_lower = question.lower()
        
        # Cuvinte cheie care indică nevoia de informații actuale
        web_search_keywords = [
            "preț", "prețuri", "cost", "costuri", "cât costă",
            "actual", "recent", "nou", "ultimul", "cel mai nou",
            "tendințe", "trend", "piață", "competiție",
            "lege", "regulament", "normă", "standard",
            "eveniment", "expoziție", "târg", "conferință",
            "stoc", "disponibilitate", "livrare", "transport",
            "reducere", "promoție", "oferta", "discount",
            "termoprotectie", "structuri metalice", "45 min", "minute",
            "rezistență", "foc", "antifoc", "protecție"
        ]
        
        # Verifică dacă întrebarea conține cuvinte cheie pentru web search
        for keyword in web_search_keywords:
            if keyword in question_lower:
                return True
        
        # Verifică dacă întrebarea pare să necesite informații actuale
        if any(word in question_lower for word in ["ce se întâmplă", "ce e nou", "ultimele", "actuale"]):
            return True
        
        # Declanșează web search pentru întrebări complexe despre prețuri
        if any(keyword in question_lower for keyword in ["preț", "cost", "oferta"]):
            return True
            
        # Declanșează web search pentru întrebări tehnice specifice
        if any(keyword in question_lower for keyword in ["termoprotectie", "structuri metalice", "45 min"]):
            return True
            
        return False

    def _build_search_query(self, question: str) -> str:
        """Construiește query-ul de căutare pe internet"""
        # Adaugă contextul site-ului la query
        domain_context = f"{self.domain} "
        
        # Extrage cuvintele cheie din întrebare
        question_lower = question.lower()
        
        # Adaugă cuvinte cheie specifice domeniului
        if "leroymerlin" in self.domain or "dedeman" in self.domain:
            domain_context += "construcții materiale "
        elif "antifoc" in self.domain:
            domain_context += "protecție la foc "
        
        # Construiește query-ul final
        search_query = domain_context + question
        
        # Limitează lungimea query-ului
        if len(search_query) > 100:
            search_query = search_query[:100] + "..."
            
        return search_query

    def _generate_fallback_smart_response(self, question: str) -> str:
        """Generează răspuns inteligent fără GPT-5 - GENERALIZAT PENTRU TOATE DOMENIILE"""
        question_lower = question.lower().strip()
        
        # Răspunsuri specifice pentru întrebări despre produse
        if any(word in question_lower for word in ["produse", "produsele", "ce produse", "ce ai"]):
            # Răspunsuri specifice pentru hidroizolații
            if any(word in question_lower for word in ["hidroizola", "hidroizolatii", "etanșare", "membrane", "bituminoase"]):
                return f"""🏗️ **HIDROIZOLAȚII COMPLETE - {self.domain}:**

**Membrane bituminoase**
• Membrane SBS și APP pentru acoperișuri
• Membrane autoadezive și cu flacără
• Grosimi: 3mm, 4mm, 5mm
• Aplicații: Acoperișuri, terase, balcoane

**Membrane sintetice (PVC, TPO, EPDM)**
• Membrane elastice pentru terase
• Rezistență UV și intemperii
• Aplicații: Terase, piscine, rezervoare

**Vopsele hidroizolante**
• Vopsele elastice pentru terase
• Vopsele pentru băi și spații umede
• Aplicații: Terase, băi, subsoluri

**Chituri și mastice**
• Chituri poliuretanice și acrilice
• Mastice pentru etanșare joncțiuni
• Aplicații: Joncțiuni, treceri, etanșări

**Folii de protecție**
• Folii PEHD pentru fundații
• Bariere de vapori
• Aplicații: Fundații, pereți, tavane

**Sisteme complete**
• Sisteme de hidroizolație pentru terase
• Sisteme pentru băi și spații umede
• Sisteme pentru acoperișuri

💡 **Vrei să știi mai multe despre un tip specific de hidroizolație?** Întreabă-mă despre aplicații, prețuri, sau specificații tehnice!"""
            # Răspuns dinamic bazat pe tipul de business detectat
            if self.site_context and self.site_context.business_type == "fire_protection":
                return f"""🔥 **PRODUSE ANTIINCENDIU - {self.domain.upper()}:**

**🔧 Produse principale:**
• Sisteme de detectare și alarmă la incendiu
• Sisteme de stingere automată (sprinklere, gaz inert)
• Hidranți interiori și exteriori
• Detectoare de fum, căldură și flacără
• Uși și clapete rezistente la foc
• Vopsele ignifuge pentru structuri metalice
• Materiale de compartimentare la foc

**🛡️ Servicii specializate:**
• Proiectare și instalare sisteme PSI
• Certificare ISU și documentație tehnică
• Mentenanță și verificări periodice
• Consultanță tehnică specializată
• Echipamente PSI (extinctoare, pături antifoc)

**📋 Procesul nostru:**
1. **Evaluare tehnică** - analiză riscuri și cerințe
2. **Proiectare** - soluții conforme normelor
3. **Instalare** - execuție profesională
4. **Certificare** - documentație pentru autorități

💡 **Vrei să știi mai multe despre un produs anume?** Întreabă-mă despre specificații, prețuri, sau aplicații!"""
            
            elif self.site_context and self.site_context.business_type == "construction_materials":
                return f"""🔧 **PRODUSE COMPLETE - {self.domain}:**

**Materiale de construcție**
• Cărămizi, blocuri, beton
• Materiale pentru pereți, tavane, fundații
• Gama completă pentru construcții rezidențiale și comerciale

**Instalații sanitare**
• Țevi, fitinguri, robinete
• Toalete, chiuvete, băi
• Sisteme complete de instalații

**Instalații electrice**
• Cabluri, prize, întrerupătoare
• Tablouri electrice, siguranțe
• Sisteme de iluminat

**Finisaje interioare**
• Vopsele, tapet, gresie
• Parchet, laminat, covoare
• Accesorii pentru decorare

**Unelte și echipamente**
• Unelte pentru construcții
• Echipamente de protecție
• Accesorii pentru meseriași

💡 **Vrei să știi mai multe despre un produs anume?** Întreabă-mă despre specificații, prețuri, sau aplicații!"""
            
            else:
                # Răspuns generalizat pentru orice domeniu
                return f"""🔧 **PRODUSE COMPLETE - {self.domain}:**

**Produse principale**
• Gama completă de produse specializate
• Soluții personalizate pentru nevoile tale
• Produse de calitate superioară

**Categorii de produse**
• Produse de bază și accesorii
• Soluții complete și sisteme
• Produse premium și specializate

**Servicii asociate**
• Consultanță și suport tehnic
• Instalare și mentenanță
• Garanție și asistență post-vânzare

**Avantaje competitive**
• Calitate garantată
• Prețuri competitive
• Suport tehnic specializat

💡 **Vrei să știi mai multe despre produsele noastre?** Întreabă-mă despre specificații, prețuri, sau aplicații!"""
        
        # Răspunsuri specifice pentru întrebări despre servicii
        elif any(word in question_lower for word in ["servicii", "serviciile", "ce servicii", "ce oferi"]):
            # Răspuns generalizat pentru orice domeniu
            return f"""⚙️ **SERVICII COMPLETE - {self.domain.upper()}**

**🔧 Servicii principale**
• Consultanță specializată și suport tehnic
• Implementare și instalare profesională
• Mentenanță și asistență post-vânzare

**📋 Servicii de consultanță**
• Analiză și evaluare nevoi
• Proiectare și planificare
• Consultanță tehnică specializată

**⚡ Servicii de implementare**
• Instalare și montaj profesional
• Configurare și testare
• Pregătire pentru utilizare

**🛠️ Servicii de suport**
• Mentenanță preventivă și curativă
• Suport tehnic și asistență
• Garanție și service

**⭐ Avantaje servicii**
• Echipă de specialiști
• Suport 24/7
• Garanție extinsă

💡 **Vrei să știi mai multe despre serviciile noastre?** Întreabă-mă despre proces, prețuri, sau durată!"""
        
        # Răspunsuri specifice pentru întrebări despre terase și balcoane
        elif any(word in question_lower for word in ["terasa", "terase", "balcon", "balcoane", "recomanzi", "recomandare", "pentru o terasa"]):
            # Răspuns generalizat pentru orice domeniu
            return f"""🏗️ **RECOMANDĂRI SPECIFICE PENTRU TERASA DE BALCON - {self.domain}:**

**SOLUȚIA OPTIMĂ: Membrane sintetice PVC/TPO**
• **Membrane PVC** - Cea mai bună alegere pentru terase de balcon
• **Grosime recomandată:** 1.5-2mm pentru rezistență optimă
• **Aplicație:** Lipire cu adeziv special sau sudare cu aer cald
• **Avantaje:** Flexibilitate, rezistență UV, durată de viață 15-20 ani

**ALTERNATIVĂ ECONOMICĂ: Vopsele hidroizolante**
• **Vopsele elastice** pentru terase mici și medii
• **Aplicație:** 2-3 straturi cu pensula sau rulou
• **Avantaje:** Preț accesibil, aplicare simplă, întreținere ușoară
• **Durată:** 5-8 ani cu întreținere periodică

**PREGĂTIREA SUPRAFEȚEI:**
• **Curățare completă** - îndepărtare vechi materiale
• **Nivelare** cu mortar de reparații
• **Primer** pentru aderență optimă
• **Izolație termică** (opțional) - plăci XPS

**ACCESORII NECESARE:**
• **Chituri de etanșare** pentru joncțiuni
• **Bandă de armare** pentru colțuri și treceri
• **Profiluri de fixare** pentru marginile terasei

**PROCES DE APLICARE:**
1. **Pregătire** (1-2 zile) - curățare și nivelare
2. **Aplicare** (1-2 zile) - membrane sau vopsele
3. **Finisare** (1 zi) - chituri și accesorii

💡 **Vrei să știi mai multe despre un pas specific?** Întreabă-mă despre pregătirea suprafeței, aplicarea membranei, sau întreținerea!"""
        
        # Răspunsuri specifice pentru întrebări despre prețuri și oferte
        elif any(word in question_lower for word in ["preț", "prețuri", "cost", "cât costă", "oferta", "oferte", "tabel", "tabelul"]):
            return self._generate_pricing_and_offers_response(question)
        
        # Răspunsuri personale
        elif any(word in question_lower for word in ["ce faci", "cine ești", "ce ești"]):
            return f"""👋 **Salut! Sunt advisor-ul tău personal pentru {self.domain}!**

🎯 **Ce fac eu:**
• Îți dau informații complete despre serviciile și produsele noastre
• Te ajut să înțelegi ce ai nevoie pentru proiectul tău
• Îți explic procesele și tehnologiile pe care le folosim
• Te pregătesc pentru conversația cu specialistul nostru uman
• Îți fac recomandări personalizate bazate pe nevoile tale

🧠 **Sunt inteligent pentru că:**
• Înțeleg tipul de proiect pe care îl ai în minte
• Anticipează întrebările tale și îți dau răspunsuri complete
• Îți sugerez următorii pași înainte să vorbești cu un specialist
• Am acces la toate informațiile despre compania noastră

💡 **Cu ce te pot ajuta astăzi?** 
Vrei să îți explic serviciile noastre, să îți arăt produsele, sau ai o întrebare specifică?"""
        
        # Răspunsuri specifice pentru termeni din protecția la incendiu
        elif any(word in question_lower for word in ["matări", "matările", "mătărizări", "treceri antifoc"]):
            # Folosește doar informațiile reale din baza de date
            real_contact = self.site_context.site_specific_data.get('contact_info', {})
            phone = real_contact.get('phone', 'Nu disponibil')
            email = real_contact.get('email', 'Nu disponibil')
            company = real_contact.get('company', self.domain.upper())
            
            return f"""🔥 **Trecere antifoc - {company}**

**🔧 Ce înțeleg prin "matări":**
• **Trecere antifoc** = orificiu prin pereți/plafoane pentru instalații
• **Tipuri de treceri:** cabluri, țevi, conducte, cabluri electrice
• **Norme ISU:** conformitate cu P118/3 și MAI Order 163/2007

**📋 Întrebări pentru a te ajuta mai bine:**
1. **Ce tip de spațiu ai?** (birou, magazin, depozit, restaurant)
2. **Câte treceri antifoc ai nevoie?** (numărul aproximativ)
3. **Ce instalații trebuie să treci?** (cabluri, țevi, conducte)
4. **Ai nevoie de certificare ISU?** (pentru autorizații)
5. **Când ai nevoie să finalizezi?** (termenul de execuție)

**⚡ Servicii noastre pentru treceri antifoc:**
• **Proiectare tehnică** - planuri detaliate pentru treceri
• **Execuție profesională** - montaj conform normelor
• **Certificare ISU** - documentație pentru autorități
• **Verificare post-lucrare** - conformitate garantată

**📞 Contact pentru ofertă personalizată:**
• **Telefon:** {phone}
• **Email:** {email}

**💡 Următorul pas:**
Răspunde la întrebările de mai sus și îți fac o ofertă concretă pentru trecerile antifoc!"""
        
        # Răspuns generic inteligent
        else:
            return f"""👋 **Bună! Sunt advisor-ul tău specializat pentru {self.domain}!**

Am acces la informații complete despre serviciile și produsele noastre. 

**💡 Cu ce te pot ajuta astăzi?**
• Produsele și serviciile noastre
• Procesele de lucru
• Prețurile și ofertele
• Cum să îți alegi soluția potrivită

**❓ Ce te interesează cel mai mult?**"""

    def _generate_pricing_and_offers_response(self, question: str) -> str:
        """Generează răspuns cu prețuri și oferte personalizate cu tabele"""
        try:
            # Extrage informații despre produse din întrebare
            products_info = self._extract_products_from_question(question)
            
            # Creează tabel cu oferte personalizate
            offers_table = self._create_personalized_offers_table(products_info)
            
            # Generează răspunsul complet
            response = f"""💰 **PREȚURI ȘI OFERTE PERSONALIZATE - {self.domain.upper()}**

{offers_table}

**📞 CONTACT PENTRU OFERTĂ PERSONALIZATĂ:**
• **Telefon:** +40731309222
• **Email:** info@leroymerlin.ro
• **Website:** https://www.leroymerlin.ro

**🎯 AVANTAJE OFERTĂ PERSONALIZATĂ:**
• Prețuri adaptate la cantitatea comandată
• Oferte speciale pentru proiecte mari
• Consultanță gratuită pentru alegerea produselor
• Garanție extinsă și suport tehnic

**💡 ÎNTREBĂRI URMĂTOARE:**
1. **Disponibilitate în stoc** - Verifică disponibilitatea produselor
2. **Timp de livrare** - Informații despre livrare și transport
3. **Instalare profesională** - Servicii de montaj și instalare
4. **Garanții și suport** - Informații despre garanții și service

**🚀 URMĂTORII PAȘI:**
1. Contactează-ne pentru ofertă personalizată
2. Programează o consultanță gratuită
3. Primește oferta detaliată cu prețuri și termeni
4. Alege soluția potrivită pentru proiectul tău

Vrei să știi mai multe despre un produs specific sau ai nevoie de consultanță pentru alegerea soluției potrivite?"""
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error generating pricing response: {e}")
            # Folosește contactul real
            real_contact = self.site_context.site_specific_data.get('contact_info', {})
            phone = real_contact.get('phone', 'Nu disponibil')
            email = real_contact.get('email', 'Nu disponibil')
            company = real_contact.get('company', self.domain.upper())
            
            return f"""💰 **PREȚURI ȘI OFERTE - {company}**

Pentru prețuri exacte și oferte personalizate, te rog să contactezi echipa noastră:

**📞 CONTACT:**
• **Telefon:** {phone}
• **Email:** {email}

**🎯 OFERTĂ PERSONALIZATĂ:**
• Prețuri adaptate la cantitatea comandată
• Oferte speciale pentru proiecte mari
• Consultanță gratuită
• Garanție extinsă

Vrei să știi mai multe despre produsele noastre sau ai nevoie de consultanță?"""

    def _extract_products_from_question(self, question: str) -> List[Dict[str, Any]]:
        """Extrage informații despre produse din întrebare"""
        products = []
        question_lower = question.lower()
        
        # Detectează produse specifice
        if "membrană" in question_lower or "membrane" in question_lower:
            if "5mm" in question_lower:
                products.append({
                    "name": "Membrană hidroizolantă 5mm",
                    "type": "Membrană bituminoasă",
                    "thickness": "5mm",
                    "application": "Acoperișuri, terase, balcoane",
                    "price_range": "45-65 lei/m²"
                })
            else:
                products.append({
                    "name": "Membrană hidroizolantă",
                    "type": "Membrană bituminoasă",
                    "thickness": "3-5mm",
                    "application": "Acoperișuri, terase, balcoane",
                    "price_range": "35-65 lei/m²"
                })
        
        if "grund" in question_lower or "primer" in question_lower:
            products.append({
                "name": "Grund bituminos",
                "type": "Primer pentru preparare suprafață",
                "thickness": "0.1-0.3mm",
                "application": "Pregătire suprafață pentru membrane",
                "price_range": "8-15 lei/kg"
            })
        
        if "ardezie" in question_lower:
            products.append({
                "name": "Membrană cu ardezie",
                "type": "Membrană bituminoasă cu ardezie",
                "thickness": "4-5mm",
                "application": "Acoperișuri, terase",
                "price_range": "55-75 lei/m²"
            })
        
        # Produse generice dacă nu se detectează produse specifice
        if not products:
            products = [
                {
                    "name": "Membrane hidroizolante",
                    "type": "Membrane bituminoase",
                    "thickness": "3-5mm",
                    "application": "Acoperișuri, terase, balcoane",
                    "price_range": "35-65 lei/m²"
                },
                {
                    "name": "Grunduri bituminoase",
                    "type": "Primer pentru preparare",
                    "thickness": "0.1-0.3mm",
                    "application": "Pregătire suprafață",
                    "price_range": "8-15 lei/kg"
                }
            ]
        
        return products

    def _create_personalized_offers_table(self, products_info: List[Dict[str, Any]]) -> str:
        """Creează tabel cu oferte personalizate"""
        if not products_info:
            return "**Nu s-au detectat produse specifice în întrebare.**"
        
        table = "**📊 OFERTĂ PERSONALIZATĂ PENTRU PRODUSELE SOLICITATE:**\n\n"
        table += "| Produs | Tip | Grosime | Aplicație | Preț Orientativ |\n"
        table += "|--------|-----|---------|-----------|-----------------|\n"
        
        for product in products_info:
            table += f"| {product['name']} | {product['type']} | {product['thickness']} | {product['application']} | {product['price_range']} |\n"
        
        table += "\n**📋 DETALII OFERTĂ PERSONALIZATĂ:**\n"
        table += "• **Prețuri finale** - Adaptate la cantitatea comandată\n"
        table += "• **Oferte speciale** - Pentru proiecte mari (peste 100m²)\n"
        table += "• **Consultanță gratuită** - Pentru alegerea produselor potrivite\n"
        table += "• **Garanție extinsă** - 10-15 ani pentru membrane\n"
        table += "• **Suport tehnic** - Înainte, în timpul și după instalare\n"
        
        return table

    def _build_site_specific_prompt(self, question: str, conversation_history: List[dict] = None) -> str:
        """Construiește prompt specific site-ului"""
        # Construiește contextul conversației
        conversation_context = ""
        if conversation_history and len(conversation_history) > 0:
            conversation_context = "\n\nCONTEXT CONVERSAȚIE ANTERIOARĂ:\n"
            for i, msg in enumerate(conversation_history[-3:], 1):  # Ultimele 3 mesaje
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                conversation_context += f"{i}. {role.upper()}: {content}\n"
        
        prompt = f"""
        Întrebare utilizator: "{question}"
        {conversation_context}
        
        CONTEXT SITE-SPECIFIC:
        - Business: {self.site_context.business_type}
        - Audiență: {self.site_context.target_audience}
        - Domeniu: {self.domain}
        
        DATE SPECIFICE DIN BAZA DE DATE:
        - Contact: {self.site_context.site_specific_data.get('contact_info', {})}
        - Prețuri: {self.site_context.site_specific_data.get('pricing_info', {})}
        - Certificări: {self.site_context.site_specific_data.get('certifications', [])}
        - Proiecte: {self.site_context.site_specific_data.get('project_examples', [])}
        
        Răspunde ca un advisor superior ChatGPT-ului prin:
        1. Informații specifice și concrete despre {self.domain}
        2. Înțelegere profundă a business-ului {self.site_context.business_type}
        3. Răspunsuri personalizate pentru {self.site_context.target_audience}
        4. Date reale din baza de date
        5. Anticiparea întrebărilor următoare
        6. ȚINE CONTEXTUL CONVERSAȚIEI - nu repeta introduceri generice
        """
        
        return prompt

    def get_competitive_advantage_summary(self) -> Dict[str, Any]:
        """Returnează sumarul avantajului competitiv"""
        return {
            "site_domain": self.domain,
            "business_type": self.site_context.business_type if self.site_context else "unknown",
            "target_audience": self.site_context.target_audience if self.site_context else "unknown",
            "unique_selling_points": self.site_context.unique_selling_points if self.site_context else [],
            "site_specific_data_available": len(self.site_context.site_specific_data) if self.site_context else 0,
            "common_questions_identified": len(self.site_context.common_customer_questions) if self.site_context else 0,
            "competitive_advantages": [
                "Date specifice din baza de date",
                "Înțelegere profundă a business-ului",
                "Răspunsuri personalizate pentru audiența țintă",
                "Informații concrete și specifice",
                "Anticiparea întrebărilor clienților"
            ]
        }

# Funcție pentru a crea inteligența specifică site-ului
async def create_site_specific_intelligence(site_url: str) -> SiteSpecificIntelligence:
    """Creează inteligența specifică site-ului"""
    intelligence = SiteSpecificIntelligence(site_url)
    
    # Analizează inteligența specifică
    await intelligence.analyze_site_specific_intelligence()
    
    return intelligence
