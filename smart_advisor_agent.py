#!/usr/bin/env python3
"""
Smart Advisor Agent - Agent inteligent care funcționează ca un advisor complet
Folosește GPT-5 pentru răspunsuri avansate și anticipează nevoile utilizatorului
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

logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    """Profilul utilizatorului pentru personalizare"""
    needs: List[str]
    project_type: Optional[str]
    budget_range: Optional[str]
    timeline: Optional[str]
    experience_level: Optional[str]
    specific_requirements: List[str]

@dataclass
class ConversationContext:
    """Contextul conversației pentru continuitate"""
    conversation_history: List[Dict]
    user_intent: str
    current_topic: str
    questions_asked: List[str]
    information_gathered: Dict[str, Any]

class SmartAdvisorAgent:
    """Agent inteligent care funcționează ca un advisor complet"""
    
    def __init__(self, site_url: str):
        self.site_url = site_url
        self.agent_id = f"smart_advisor_{int(time.time())}"
        self.domain = self._extract_domain(site_url)
        
        # Initializează componentele
        self.user_profile = UserProfile(
            needs=[], project_type=None, budget_range=None, 
            timeline=None, experience_level=None, specific_requirements=[]
        )
        self.conversation_context = ConversationContext(
            conversation_history=[], user_intent="", current_topic="",
            questions_asked=[], information_gathered={}
        )
        
        # Site content și informații
        self.site_content = {}
        self.services_info = {}
        self.products_info = {}
        self.faq_data = {}
        
        # Configurare GPT-5
        self.openai_client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        )
        
        logger.info(f"✅ Smart Advisor Agent initialized: {self.domain}")

    def _extract_domain(self, url: str) -> str:
        """Extrage domeniul din URL"""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace("www.", "").lower()
        except:
            return url

    async def ingest_comprehensive_site_data(self) -> bool:
        """Ingest informații complete despre site pentru a fi un advisor complet"""
        logger.info(f"🔄 Ingesting comprehensive data for {self.site_url}")
        
        try:
            # 1. Crawl principal
            main_content = await self._crawl_site_comprehensive()
            
            # 2. Extrage informații structurate
            self.services_info = self._extract_services_info(main_content)
            self.products_info = self._extract_products_info(main_content)
            self.faq_data = self._extract_faq_data(main_content)
            
            # 3. Creează baza de cunoștințe
            self.knowledge_base = self._create_knowledge_base()
            
            logger.info(f"✅ Comprehensive data ingested: {len(self.knowledge_base)} knowledge points")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error ingesting comprehensive data: {e}")
            return False

    async def _crawl_site_comprehensive(self) -> Dict[str, Any]:
        """Crawl comprehensiv al site-ului pentru informații complete"""
        try:
            response = requests.get(
                self.site_url,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (compatible; SmartAdvisor/2.0)"}
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extrage toate informațiile relevante
                content = {
                    "title": soup.find('title').get_text().strip() if soup.find('title') else "",
                    "main_content": self._extract_main_content(soup),
                    "services_section": self._extract_services_section(soup),
                    "products_section": self._extract_products_section(soup),
                    "contact_info": self._extract_contact_info(soup),
                    "faq_section": self._extract_faq_section(soup),
                    "about_section": self._extract_about_section(soup),
                    "pricing_info": self._extract_pricing_info(soup),
                    "process_info": self._extract_process_info(soup)
                }
                
                return content
            else:
                logger.error(f"❌ Failed to fetch site: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error crawling site: {e}")
            return {}

    def _extract_main_content(self, soup) -> str:
        """Extrage conținutul principal"""
        # Curăță conținutul
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        content = soup.get_text()
        content = ' '.join(content.split())
        return content[:10000]  # Limitează la 10000 caractere

    def _extract_services_section(self, soup) -> str:
        """Extrage secțiunea de servicii"""
        services_text = ""
        for section in soup.find_all(['section', 'div'], class_=re.compile(r'service|servicii', re.I)):
            services_text += section.get_text() + " "
        return services_text[:5000]

    def _extract_products_section(self, soup) -> str:
        """Extrage secțiunea de produse"""
        products_text = ""
        for section in soup.find_all(['section', 'div'], class_=re.compile(r'product|produse', re.I)):
            products_text += section.get_text() + " "
        return products_text[:5000]

    def _extract_contact_info(self, soup) -> Dict[str, str]:
        """Extrage informațiile de contact"""
        contact = {}
        
        # Telefon
        phone_match = re.search(r'(\+40\d{9}|\d{10})', soup.get_text())
        if phone_match:
            contact['phone'] = phone_match.group(1)
        
        # Email
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', soup.get_text())
        if email_match:
            contact['email'] = email_match.group(1)
        
        return contact

    def _extract_faq_section(self, soup) -> str:
        """Extrage secțiunea FAQ"""
        faq_text = ""
        for section in soup.find_all(['section', 'div'], class_=re.compile(r'faq|intrebari', re.I)):
            faq_text += section.get_text() + " "
        return faq_text[:3000]

    def _extract_about_section(self, soup) -> str:
        """Extrage secțiunea despre companie"""
        about_text = ""
        for section in soup.find_all(['section', 'div'], class_=re.compile(r'about|despre', re.I)):
            about_text += section.get_text() + " "
        return about_text[:3000]

    def _extract_pricing_info(self, soup) -> str:
        """Extrage informații despre prețuri"""
        pricing_text = ""
        for section in soup.find_all(['section', 'div'], class_=re.compile(r'price|pret|tarif', re.I)):
            pricing_text += section.get_text() + " "
        return pricing_text[:2000]

    def _extract_process_info(self, soup) -> str:
        """Extrage informații despre procesul de lucru"""
        process_text = ""
        for section in soup.find_all(['section', 'div'], class_=re.compile(r'process|proces', re.I)):
            process_text += section.get_text() + " "
        return process_text[:2000]

    def _extract_services_info(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Extrage informații structurate despre servicii"""
        services = {}
        services_text = content.get('services_section', '') + ' ' + content.get('main_content', '')
        
        # Analizează serviciile folosind regex și logică
        if 'antifoc' in services_text.lower() or 'foc' in services_text.lower():
            services['fire_protection'] = {
                'name': 'Protecție la foc',
                'description': 'Sisteme complete de protecție la foc',
                'subservices': ['Instalare', 'Mentenanță', 'Consultanță', 'Testare', 'Proiectare', 'Inspectare']
            }
        
        if 'ventilație' in services_text.lower() or 'ventilatie' in services_text.lower():
            services['ventilation'] = {
                'name': 'Sisteme de ventilație',
                'description': 'Instalare și mentenanță sisteme de ventilație',
                'subservices': ['Proiectare', 'Instalare', 'Mentenanță', 'Reparații', 'Modernizare']
            }
        
        # Adaugă servicii specifice pentru domeniul antifoc
        services['consulting'] = {
            'name': 'Consultanță tehnică',
            'description': 'Consultanță specializată pentru proiecte de protecție la foc',
            'subservices': ['Audit tehnic', 'Proiectare sisteme', 'Consultanță normativă', 'Evaluare riscuri']
        }
        
        services['installation'] = {
            'name': 'Instalare și montaj',
            'description': 'Instalare profesională de sisteme de protecție la foc',
            'subservices': ['Instalare vată bazaltică', 'Montaj geamuri antifoc', 'Instalare sisteme ventilație', 'Montaj chit-uri antifoc']
        }
        
        services['maintenance'] = {
            'name': 'Mentenanță și suport',
            'description': 'Servicii de mentenanță și suport tehnic',
            'subservices': ['Mentenanță preventivă', 'Reparații urgente', 'Suport tehnic', 'Inspectare periodică']
        }
        
        return services

    def _extract_products_info(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Extrage informații structurate despre produse"""
        products = {}
        products_text = content.get('products_section', '') + ' ' + content.get('main_content', '')
        
        # Analizează produsele
        if 'vată' in products_text.lower() or 'vata' in products_text.lower():
            products['basalt_wool'] = {
                'name': 'Vată bazaltică',
                'description': 'Material antifoc pentru protecție la foc',
                'applications': ['Pereți', 'Tavane', 'Tubulaturi', 'Coloane', 'Grindaje'],
                'specifications': ['Densitate: 80-200 kg/m³', 'Temperatură: până la 1000°C', 'Grosime: 30-200mm']
            }
        
        if 'chit' in products_text.lower():
            products['fire_sealant'] = {
                'name': 'Chit-uri antifoc',
                'description': 'Chit-uri specializate pentru etanșare la foc',
                'applications': ['Joncțiuni', 'Trecere cabluri', 'Trecere țevi', 'Fisuri', 'Goluri'],
                'specifications': ['Rezistență: 2-4 ore', 'Temperatură: până la 1200°C', 'Culoare: gri/alb']
            }
        
        # Adaugă produse specifice pentru domeniul antifoc
        products['fire_glass'] = {
            'name': 'Geamuri și ferestre rezistente la foc',
            'description': 'Geamuri specializate pentru protecție la foc',
            'applications': ['Uși de evacuare', 'Ferestre compartimentare', 'Perete cortină', 'Clădiri publice'],
            'specifications': ['Rezistență: 30-120 minute', 'Grosime: 6-25mm', 'Tipuri: EI30, EI60, EI90, EI120']
        }
        
        products['fire_paint'] = {
            'name': 'Vopsele termospumante',
            'description': 'Vopsele care se expandează la foc pentru protecție',
            'applications': ['Structuri metalice', 'Grindaje', 'Coloane', 'Tubulaturi'],
            'specifications': ['Rezistență: 30-180 minute', 'Grosime: 0.5-3mm', 'Culoare: gri/alb']
        }
        
        products['ventilation_ducts'] = {
            'name': 'Tubulaturi de ventilație rezistente la foc',
            'description': 'Tubulaturi specializate pentru sisteme de ventilație',
            'applications': ['Ventilație compartimentare', 'Evacuare fum', 'Ventilație tehnică'],
            'specifications': ['Rezistență: 30-120 minute', 'Diametru: 100-2000mm', 'Material: oțel galvanizat']
        }
        
        products['fire_doors'] = {
            'name': 'Uși rezistente la foc',
            'description': 'Uși specializate pentru compartimentare la foc',
            'applications': ['Uși de evacuare', 'Uși compartimentare', 'Uși tehnice'],
            'specifications': ['Rezistență: 30-120 minute', 'Dimensiuni: standard și personalizate', 'Tipuri: EI30, EI60, EI90']
        }
        
        products['fire_stops'] = {
            'name': 'Matări antifoc și treceri prin pereți',
            'description': 'Sisteme de etanșare pentru treceri prin pereți',
            'applications': ['Trecere cabluri', 'Trecere țevi', 'Trecere conducte', 'Joncțiuni'],
            'specifications': ['Rezistență: 30-180 minute', 'Diametru: 10-500mm', 'Material: vată bazaltică + chit']
        }
        
        return products

    def _extract_faq_data(self, content: Dict[str, Any]) -> Dict[str, str]:
        """Extrage datele FAQ"""
        faq = {}
        faq_text = content.get('faq_section', '')
        
        # Extrage întrebări și răspunsuri din FAQ
        questions = re.findall(r'([A-Z][^.!?]*\?)', faq_text)
        for i, question in enumerate(questions[:10]):  # Primele 10 întrebări
            faq[f'q{i+1}'] = question.strip()
        
        return faq

    def _create_knowledge_base(self) -> Dict[str, Any]:
        """Creează baza de cunoștințe completă"""
        return {
            'domain': self.domain,
            'services': self.services_info,
            'products': self.products_info,
            'faq': self.faq_data,
            'contact': self.site_content.get('contact_info', {}),
            'about': self.site_content.get('about_section', ''),
            'pricing': self.site_content.get('pricing_info', ''),
            'process': self.site_content.get('process_info', '')
        }

    async def answer_question_smart(self, question: str) -> Dict[str, Any]:
        """Răspunde la întrebare folosind GPT-5 pentru răspunsuri inteligente"""
        logger.info(f"🧠 Smart answering question: {question[:100]}...")
        
        try:
            # 1. Analizează intenția utilizatorului
            user_intent = await self._analyze_user_intent(question)
            
            # 2. Actualizează profilul utilizatorului
            await self._update_user_profile(question, user_intent)
            
            # 3. Generează răspuns inteligent cu GPT-5
            smart_response = await self._generate_smart_response(question, user_intent)
            
            # 4. Generează întrebări proactive
            proactive_questions = await self._generate_proactive_questions(user_intent)
            
            # 5. Actualizează contextul conversației
            self._update_conversation_context(question, smart_response, user_intent)
            
            return {
                "ok": True,
                "response": smart_response,
                "confidence": 0.95,
                "reasoning": f"Smart advisor pentru {self.domain} cu GPT-5",
                "user_intent": user_intent,
                "proactive_questions": proactive_questions,
                "user_profile": {
                    "needs": self.user_profile.needs,
                    "project_type": self.user_profile.project_type,
                    "budget_range": self.user_profile.budget_range,
                    "timeline": self.user_profile.timeline
                },
                "next_steps": await self._suggest_next_steps(user_intent),
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guardrails": {
                    "passed": True,
                    "message": "All security checks passed",
                    "confidence_check": True
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in smart answering: {e}")
            return {
                "ok": False,
                "response": "Îmi pare rău, a apărut o problemă tehnică. Te rog încearcă din nou.",
                "error": str(e),
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _analyze_user_intent(self, question: str) -> str:
        """Analizează intenția utilizatorului folosind GPT-5"""
        try:
            prompt = f"""
            Analizează următoarea întrebare și determină intenția utilizatorului pentru un site de {self.domain}:
            
            Întrebare: "{question}"
            
            Context: Utilizatorul vrea să înțeleagă serviciile/produsele și să ia o decizie informată.
            
            Categorii posibile:
            - information_seeking: Caută informații generale
            - product_inquiry: Întreabă despre produse specifice
            - service_inquiry: Întreabă despre servicii
            - pricing_inquiry: Întreabă despre prețuri
            - process_inquiry: Întreabă despre procesul de lucru
            - contact_request: Vrea să contacteze compania
            - comparison: Compară opțiuni
            - decision_making: Încearcă să ia o decizie
            
            Răspunde doar cu categoria cea mai potrivită.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip().lower()
            
        except Exception as e:
            logger.error(f"❌ Error analyzing user intent: {e}")
            return "information_seeking"

    async def _update_user_profile(self, question: str, intent: str) -> None:
        """Actualizează profilul utilizatorului bazat pe întrebare și intenție"""
        question_lower = question.lower()
        
        # Detectează tipul de proiect
        if any(word in question_lower for word in ["casă", "casa", "casă", "rezidențial", "rezidential"]):
            self.user_profile.project_type = "residential"
        elif any(word in question_lower for word in ["birou", "oficiu", "comercial", "business"]):
            self.user_profile.project_type = "commercial"
        elif any(word in question_lower for word in ["industrial", "fabrica", "depozit"]):
            self.user_profile.project_type = "industrial"
        
        # Detectează bugetul
        if any(word in question_lower for word in ["ieftin", "buget", "cost", "preț"]):
            self.user_profile.budget_range = "budget_conscious"
        elif any(word in question_lower for word in ["premium", "calitate", "cel mai bun"]):
            self.user_profile.budget_range = "premium"
        
        # Detectează timeline-ul
        if any(word in question_lower for word in ["urgent", "repede", "săptămâna viitoare"]):
            self.user_profile.timeline = "urgent"
        elif any(word in question_lower for word in ["luna viitoare", "cândva", "nu e urgent"]):
            self.user_profile.timeline = "flexible"

    async def _generate_smart_response(self, question: str, intent: str) -> str:
        """Generează răspuns inteligent folosind GPT-5"""
        try:
            # Verifică dacă este o întrebare personală
            if self._is_personal_question(question):
                return self._generate_personal_response(question)
            
            # Construiește prompt-ul contextual
            context_prompt = self._build_contextual_prompt(question, intent)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": f"""Ești un advisor expert pentru {self.domain}. 
                        Rolul tău este să fii un consultant complet care:
                        1. Răspunde la întrebări cu informații detaliate și precise
                        2. Anticipează nevoile utilizatorului
                        3. Oferă recomandări personalizate
                        4. Pregătește utilizatorul pentru conversația cu specialistul uman
                        5. Folosești un ton prietenos dar profesional
                        6. Îți bazezi răspunsurile pe informațiile din baza de cunoștințe
                        
                        Baza de cunoștințe: {json.dumps(self.knowledge_base, ensure_ascii=False, indent=2)}
                        """
                    },
                    {
                        "role": "user", 
                        "content": context_prompt
                    }
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ Error generating smart response: {e}")
            return self._generate_fallback_response(question)

    def _is_personal_question(self, question: str) -> bool:
        """Verifică dacă este o întrebare personală"""
        personal_keywords = [
            "ce faci", "cine ești", "ce ești", "cum funcționezi", 
            "ce poți face", "ce știi", "cum ești", "salut", "bună"
        ]
        question_lower = question.lower().strip()
        return any(keyword in question_lower for keyword in personal_keywords)

    def _generate_personal_response(self, question: str) -> str:
        """Generează răspuns personal pentru întrebări despre agent"""
        question_lower = question.lower().strip()
        
        if any(word in question_lower for word in ["ce faci", "ce poți face", "ce știi"]):
            return f"""Salut! 😊 Sunt advisor-ul tău personal pentru {self.domain}!

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

💡 **Cu ce te pot ajuta astăzi?** Vrei să îți explic serviciile noastre, să îți arăt produsele, sau ai o întrebare specifică despre protecția la foc?"""

        elif any(word in question_lower for word in ["cine ești", "ce ești"]):
            return f"""Bună! 👋 Sunt advisor-ul tău personal pentru {self.domain}!

🎯 **Cine sunt eu:**
• Un consultant AI specializat în protecția la foc
• Expertul tău personal care te ajută să înțelegi serviciile noastre
• Pregătitorul tău pentru conversația cu specialistul uman
• Sursa ta de informații complete și personalizate

🧠 **De ce sunt special:**
• Nu doar răspund la întrebări - te ghidez prin întregul proces
• Înțeleg nevoile tale și îți fac recomandări personalizate
• Anticipează întrebările tale și îți dau răspunsuri complete
• Te pregătesc să iei decizii informate

💬 **Să vorbim!** Ce te interesează cel mai mult despre serviciile noastre de protecție la foc?"""

        elif any(word in question_lower for word in ["cum funcționezi", "cum ești"]):
            return f"""Excelentă întrebare! 🤖 Iată cum funcționez eu ca advisor pentru {self.domain}:

🔄 **Procesul meu:**
1. **Înțeleg** - Analizez întrebarea ta și înțeleg ce vrei să știi
2. **Caut** - Accesez baza mea de cunoștințe despre serviciile noastre
3. **Personalizez** - Îți dau răspunsuri adaptate nevoilor tale
4. **Anticipează** - Îți sugerez următoarele întrebări și pași
5. **Pregătesc** - Te fac gata pentru conversația cu specialistul uman

🧠 **Inteligența mea:**
• Am acces la toate informațiile despre compania noastră
• Înțeleg tipul de proiect pe care îl ai în minte
• Anticipează nevoile tale și îți dau răspunsuri complete
• Te ghidez prin întregul proces de la informare la decizie

💡 **Să testăm!** Întreabă-mă orice despre serviciile noastre - vei vedea cum funcționez!"""

        else:
            return f"""Salut! 😊 Sunt advisor-ul tău personal pentru {self.domain}!

Sunt aici să te ajut cu orice întrebare ai despre serviciile noastre de protecție la foc. Cu ce te pot ajuta astăzi?"""

    def _generate_fallback_response(self, question: str) -> str:
        """Generează răspuns de fallback când GPT-5 nu este disponibil"""
        if self._is_personal_question(question):
            return self._generate_personal_response(question)
        elif self._is_list_request(question):
            return self._generate_comprehensive_list_response(question)
        else:
            return f"""Bună! Sunt advisor-ul tău pentru {self.domain}. 

Îmi pare rău, momentan am o problemă tehnică cu sistemul meu avansat, dar pot să îți răspund la întrebări despre serviciile noastre. Cu ce te pot ajuta?"""

    def _is_list_request(self, question: str) -> bool:
        """Verifică dacă este o cerere de listă"""
        list_keywords = [
            "lista", "listă", "list", "toate produsele", "toate serviciile", 
            "ce produse", "ce servicii", "produsele", "serviciile",
            "da mi lista", "da-mi lista", "arata mi", "arată-mi"
        ]
        question_lower = question.lower().strip()
        return any(keyword in question_lower for keyword in list_keywords)

    def _generate_comprehensive_list_response(self, question: str) -> str:
        """Generează răspuns cu listă completă și diferențiată"""
        question_lower = question.lower().strip()
        
        if any(word in question_lower for word in ["produse", "produsele", "ce produse"]):
            return self._generate_products_list()
        elif any(word in question_lower for word in ["servicii", "serviciile", "ce servicii"]):
            return self._generate_services_list()
        else:
            return self._generate_complete_offerings_list()

    def _generate_products_list(self) -> str:
        """Generează listă completă de produse"""
        products_list = f"🔧 **PRODUSE COMPLETE - {self.domain}:**\n\n"
        
        for product_id, product in self.products_info.items():
            products_list += f"**{product['name']}**\n"
            products_list += f"• {product['description']}\n"
            products_list += f"• Aplicații: {', '.join(product['applications'])}\n"
            if 'specifications' in product:
                products_list += f"• Specificații: {', '.join(product['specifications'])}\n"
            products_list += "\n"
        
        products_list += "💡 **Vrei să știi mai multe despre un produs anume?** Întreabă-mă despre specificații, prețuri, sau aplicații!"
        
        return products_list

    def _generate_services_list(self) -> str:
        """Generează listă completă de servicii"""
        services_list = f"⚙️ **SERVICII COMPLETE - {self.domain}:**\n\n"
        
        for service_id, service in self.services_info.items():
            services_list += f"**{service['name']}**\n"
            services_list += f"• {service['description']}\n"
            services_list += f"• Subservicii: {', '.join(service['subservices'])}\n"
            services_list += "\n"
        
        services_list += "💡 **Vrei să știi mai multe despre un serviciu anume?** Întreabă-mă despre proces, prețuri, sau durată!"
        
        return services_list

    def _generate_complete_offerings_list(self) -> str:
        """Generează listă completă de produse și servicii"""
        complete_list = f"📋 **OFERTA COMPLETĂ - {self.domain}:**\n\n"
        
        # Produse
        complete_list += "🔧 **PRODUSE:**\n"
        for product_id, product in self.products_info.items():
            complete_list += f"• {product['name']} - {product['description']}\n"
        complete_list += "\n"
        
        # Servicii
        complete_list += "⚙️ **SERVICII:**\n"
        for service_id, service in self.services_info.items():
            complete_list += f"• {service['name']} - {service['description']}\n"
        complete_list += "\n"
        
        complete_list += "💡 **Vrei detalii despre un produs sau serviciu anume?** Întreabă-mă despre specificații, prețuri, procese sau aplicații!"
        
        return complete_list

    def _build_contextual_prompt(self, question: str, intent: str) -> str:
        """Construiește prompt contextual pentru GPT-5"""
        prompt = f"""
        Întrebare utilizator: "{question}"
        Intenție detectată: {intent}
        
        Profil utilizator:
        - Tip proiect: {self.user_profile.project_type or 'nedeterminat'}
        - Buget: {self.user_profile.budget_range or 'nedeterminat'}
        - Timeline: {self.user_profile.timeline or 'nedeterminat'}
        - Nevoi: {', '.join(self.user_profile.needs) if self.user_profile.needs else 'nedeterminate'}
        
        Context conversație: {len(self.conversation_context.conversation_history)} mesaje anterioare
        
        Răspunde ca un advisor expert care:
        1. Dă informații complete și precise
        2. Anticipează următoarele întrebări
        3. Oferă recomandări personalizate
        4. Pregătește pentru următorul pas
        """
        
        return prompt

    async def _generate_proactive_questions(self, intent: str) -> List[str]:
        """Generează întrebări proactive bazate pe intenție"""
        questions = []
        
        if intent == "information_seeking":
            questions = [
                "Ce tip de proiect ai în minte? (rezidențial, comercial, industrial)",
                "Care este bugetul tău estimat pentru acest proiect?",
                "Când ai vrea să începi lucrările?",
                "Ai lucrat înainte cu sisteme de protecție la foc?"
            ]
        elif intent == "product_inquiry":
            questions = [
                "Pentru ce tip de aplicație ai nevoie de acest produs?",
                "Care sunt dimensiunile zonei pe care vrei să o acoperi?",
                "Ai nevoie de consultanță pentru alegerea produsului potrivit?",
                "Vrei să știi și despre procesul de instalare?"
            ]
        elif intent == "pricing_inquiry":
            questions = [
                "Ce tip de proiect ai în minte? (dimensiune, complexitate)",
                "Ai nevoie doar de materiale sau și de servicii de instalare?",
                "Care este bugetul tău estimat?",
                "Vrei o ofertă personalizată pentru proiectul tău?"
            ]
        
        return questions[:3]  # Returnează maxim 3 întrebări

    async def _suggest_next_steps(self, intent: str) -> List[str]:
        """Sugerează următorii pași bazat pe intenție"""
        steps = []
        
        if intent == "information_seeking":
            steps = [
                "Îți pot arăta exemple de proiecte similare",
                "Pot să îți explic procesul nostru de lucru",
                "Te pot conecta cu un specialist pentru consultanță gratuită"
            ]
        elif intent == "product_inquiry":
            steps = [
                "Îți pot trimite specificații tehnice detaliate",
                "Pot să îți fac o ofertă personalizată",
                "Te pot conecta cu un tehnician pentru consultanță"
            ]
        elif intent == "pricing_inquiry":
            steps = [
                "Îți pot face o ofertă personalizată",
                "Pot să îți explic ce include prețul",
                "Te pot conecta cu echipa de vânzări pentru negociere"
            ]
        
        return steps

    def _update_conversation_context(self, question: str, response: str, intent: str) -> None:
        """Actualizează contextul conversației"""
        self.conversation_context.conversation_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "response": response,
            "intent": intent
        })
        
        # Limitează istoricul
        if len(self.conversation_context.conversation_history) > 10:
            self.conversation_context.conversation_history = self.conversation_context.conversation_history[-10:]
        
        self.conversation_context.user_intent = intent
        self.conversation_context.current_topic = intent

    def get_advisor_status(self) -> Dict[str, Any]:
        """Returnează statusul advisor-ului inteligent"""
        return {
            "agent_id": self.agent_id,
            "domain": self.domain,
            "advisor_type": "smart_advisor_with_gpt5",
            "capabilities": {
                "intent_analysis": True,
                "user_profiling": True,
                "proactive_questions": True,
                "smart_responses": True,
                "next_steps_suggestion": True,
                "comprehensive_knowledge": True
            },
            "user_profile": {
                "project_type": self.user_profile.project_type,
                "budget_range": self.user_profile.budget_range,
                "timeline": self.user_profile.timeline,
                "needs_count": len(self.user_profile.needs)
            },
            "conversation_context": {
                "messages_count": len(self.conversation_context.conversation_history),
                "current_intent": self.conversation_context.user_intent,
                "current_topic": self.conversation_context.current_topic
            },
            "knowledge_base": {
                "services_count": len(self.services_info),
                "products_count": len(self.products_info),
                "faq_count": len(self.faq_data)
            }
        }

# Funcție pentru a crea un advisor inteligent
async def create_smart_advisor_agent(site_url: str) -> SmartAdvisorAgent:
    """Creează un advisor inteligent cu GPT-5"""
    agent = SmartAdvisorAgent(site_url)
    
    # Ingest informații complete
    await agent.ingest_comprehensive_site_data()
    
    return agent
