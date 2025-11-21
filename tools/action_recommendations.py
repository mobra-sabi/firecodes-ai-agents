"""
Action Recommendations Service
Generează recomandări practice de îmbunătățire bazate pe analiza competitorilor
"""

import os
from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

# Import configurație
from config.database_config import MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION

# Import utilități
from tools.site_agent_creator import chat_llm, normalize_domain
from tools.admin_discovery import web_search

load_dotenv()

class ActionRecommendationsService:
    """Serviciu pentru generarea de recomandări practice de îmbunătățire"""
    
    def __init__(self):
        self.mongo = MongoClient(MONGODB_URI)
        self.db = self.mongo[MONGODB_DATABASE]
        self.agents_collection = self.db.site_agents
        self.competitors_collection = self.db.competitors
        self.content_collection = self.db[MONGODB_COLLECTION]
    
    def analyze_competitors_and_generate_recommendations(
        self, 
        agent_id: str,
        focus_areas: Optional[List[str]] = None
    ) -> Dict:
        """
        Analizează competitorii și generează recomandări practice
        
        Args:
            agent_id: ID-ul agentului pentru care generăm recomandări
            focus_areas: Zone de focus (ex: ['seo', 'social_media', 'content', 'ux'])
        
        Returns:
            Dict cu recomandări structurate
        """
        try:
            # 1. Obține agentul
            agent = self.agents_collection.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                return {"ok": False, "error": "agent_not_found"}
            
            domain = agent.get("domain", "")
            site_url = agent.get("site_url", f"https://{domain}")
            
            # 2. Obține competitorii
            competitors = list(self.competitors_collection.find({
                "master_agent_id": ObjectId(agent_id)
            }).limit(10))
            
            # 3. Obține conținutul agentului
            agent_content = self._get_agent_content(agent_id)
            
            # 4. Analizează competitorii
            competitor_analysis = self._analyze_competitors(competitors, domain)
            
            # 5. Generează recomandări pentru fiecare zonă
            focus_areas = focus_areas or ['seo', 'social_media', 'content', 'ux', 'technical']
            
            recommendations = {}
            for area in focus_areas:
                recommendations[area] = self._generate_area_recommendations(
                    area, 
                    agent_content, 
                    competitor_analysis,
                    domain,
                    site_url
                )
            
            # 6. Generează plan de acțiune prioritizat
            action_plan = self._generate_action_plan(recommendations, domain)
            
            return {
                "ok": True,
                "agent_id": agent_id,
                "domain": domain,
                "competitors_analyzed": len(competitors),
                "recommendations": recommendations,
                "action_plan": action_plan,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def _get_agent_content(self, agent_id: str) -> str:
        """Obține conținutul agentului din baza de date"""
        try:
            content_docs = self.content_collection.find({
                "agent_id": ObjectId(agent_id)
            }).limit(20)
            
            content_parts = []
            for doc in content_docs:
                if doc.get("content"):
                    content_parts.append(doc["content"][:500])
            
            return " ".join(content_parts)[:5000]
        except Exception:
            return ""
    
    def _analyze_competitors(self, competitors: List[Dict], own_domain: str) -> Dict:
        """Analizează competitorii și extrage insights"""
        analysis = {
            "total": len(competitors),
            "common_keywords": [],
            "common_features": [],
            "social_media_presence": {},
            "content_themes": [],
            "technical_features": []
        }
        
        # Analizează fiecare competitor
        for comp in competitors:
            comp_domain = comp.get("competitor_domain", "")
            comp_url = comp.get("competitor_url", "")
            
            # Extrage keywords comune
            # (aici ar putea fi o analiză mai complexă)
            
        return analysis
    
    def _generate_area_recommendations(
        self,
        area: str,
        agent_content: str,
        competitor_analysis: Dict,
        domain: str,
        site_url: str
    ) -> Dict:
        """Generează recomandări pentru o zonă specifică"""
        
        if area == "seo":
            return self._generate_seo_recommendations(agent_content, domain, site_url)
        elif area == "social_media":
            return self._generate_social_media_recommendations(domain, site_url)
        elif area == "content":
            return self._generate_content_recommendations(agent_content, competitor_analysis)
        elif area == "ux":
            return self._generate_ux_recommendations(domain, site_url)
        elif area == "technical":
            return self._generate_technical_recommendations(domain, site_url)
        else:
            return {"recommendations": [], "priority": "medium"}
    
    def _generate_seo_recommendations(self, agent_content: str, domain: str, site_url: str) -> Dict:
        """Generează recomandări SEO practice"""
        
        prompt = f"""Analizează site-ul {domain} ({site_url}) și conținutul disponibil și oferă recomandări practice SEO concrete și implementabile.

Conținut site: {agent_content[:2000]}

Generează recomandări în următoarele categorii:
1. Optimizare On-Page (meta tags, headings, keywords)
2. Optimizare Conținut (blog posts, articole, ghiduri)
3. Link Building (strategii de obținere backlinks)
4. Local SEO (dacă e relevant)
5. Performance SEO (viteză, mobile-friendly)

Pentru fiecare recomandare, oferă:
- Titlu clar
- Descriere scurtă (1-2 propoziții)
- Pași concreti de implementare (3-5 pași)
- Impact estimat (High/Medium/Low)
- Timp estimat de implementare

Răspunde în format JSON cu structura:
{{
  "recommendations": [
    {{
      "title": "Titlu recomandare",
      "description": "Descriere",
      "steps": ["Pas 1", "Pas 2", "Pas 3"],
      "impact": "High/Medium/Low",
      "estimated_time": "X zile/săptămâni",
      "category": "On-Page/Content/Links/Local/Performance"
    }}
  ]
}}"""

        try:
            response = chat_llm(prompt, temperature=0.7)
            # Parsează răspunsul JSON
            import json
            import re
            
            # Extrage JSON din răspuns
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                recommendations_data = json.loads(json_match.group())
                return {
                    "area": "SEO",
                    "recommendations": recommendations_data.get("recommendations", []),
                    "total": len(recommendations_data.get("recommendations", []))
                }
        except Exception as e:
            pass
        
        # Fallback: recomandări generice
        return {
            "area": "SEO",
            "recommendations": [
                {
                    "title": "Optimizare Meta Tags",
                    "description": "Adaugă și optimizează meta title și description pentru toate paginile importante",
                    "steps": [
                        "Analizează paginile existente",
                        "Creează meta title optimizate (50-60 caractere)",
                        "Scrie meta descriptions atractive (150-160 caractere)",
                        "Include keywords relevante natural"
                    ],
                    "impact": "High",
                    "estimated_time": "2-3 zile",
                    "category": "On-Page"
                },
                {
                    "title": "Creare Conținut Blog",
                    "description": "Lansează un blog cu articole relevante pentru audiența ta",
                    "steps": [
                        "Identifică topicuri relevante pentru audiență",
                        "Creează un calendar editorial",
                        "Scrie primul articol (minim 1000 cuvinte)",
                        "Publică regulat (1-2 articole/săptămână)"
                    ],
                    "impact": "High",
                    "estimated_time": "1 săptămână pentru setup + continuu",
                    "category": "Content"
                }
            ],
            "total": 2
        }
    
    def _generate_social_media_recommendations(self, domain: str, site_url: str) -> Dict:
        """Generează recomandări pentru rețele sociale"""
        
        prompt = f"""Pentru site-ul {domain} ({site_url}), oferă recomandări practice pentru dezvoltarea prezenței pe rețele sociale și creșterea vizualizărilor.

Generează recomandări pentru:
1. Facebook (pagina de business, postări, ads)
2. Instagram (profil business, stories, reels)
3. LinkedIn (profil companie, postări profesionale)
4. YouTube (canal, video-uri)
5. TikTok (dacă e relevant)

Pentru fiecare platformă, oferă:
- Titlu recomandare
- Descriere
- Pași concreti
- Impact
- Timp estimat

Format JSON:
{{
  "recommendations": [
    {{
      "title": "Titlu",
      "description": "Descriere",
      "steps": ["Pas 1", "Pas 2"],
      "impact": "High/Medium/Low",
      "estimated_time": "X zile",
      "platform": "Facebook/Instagram/etc"
    }}
  ]
}}"""

        try:
            response = chat_llm(prompt, temperature=0.7)
            import json
            import re
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                recommendations_data = json.loads(json_match.group())
                return {
                    "area": "Social Media",
                    "recommendations": recommendations_data.get("recommendations", []),
                    "total": len(recommendations_data.get("recommendations", []))
                }
        except Exception:
            pass
        
        # Fallback
        return {
            "area": "Social Media",
            "recommendations": [
                {
                    "title": "Creează Pagină Facebook Business",
                    "description": "Oferă o prezență profesională pe Facebook pentru a atrage clienți",
                    "steps": [
                        "Creează pagina Facebook Business",
                        "Completează toate informațiile (despre, contact, program)",
                        "Adaugă logo și cover photo profesional",
                        "Publică primul post de prezentare"
                    ],
                    "impact": "High",
                    "estimated_time": "1 zi",
                    "platform": "Facebook"
                },
                {
                    "title": "Lansează Instagram Business",
                    "description": "Folosește Instagram pentru a arăta produsele/serviciile vizual",
                    "steps": [
                        "Creează cont Instagram Business",
                        "Postează 9-12 poze de calitate",
                        "Folosește hashtags relevante",
                        "Interacționează cu followerii"
                    ],
                    "impact": "High",
                    "estimated_time": "2-3 zile pentru setup inițial",
                    "platform": "Instagram"
                }
            ],
            "total": 2
        }
    
    def _generate_content_recommendations(self, agent_content: str, competitor_analysis: Dict) -> Dict:
        """Generează recomandări pentru conținut"""
        
        return {
            "area": "Content",
            "recommendations": [
                {
                    "title": "Creează Ghiduri Practice",
                    "description": "Scrie ghiduri detaliate care răspund la întrebările clienților",
                    "steps": [
                        "Identifică întrebări frecvente ale clienților",
                        "Scrie ghiduri pas-cu-pas",
                        "Adaugă imagini și exemple",
                        "Promovează ghidurile pe social media"
                    ],
                    "impact": "High",
                    "estimated_time": "1 săptămână per ghid"
                },
                {
                    "title": "Creează Video-uri Explicative",
                    "description": "Video-urile au rate de engagement mai mare decât textul",
                    "steps": [
                        "Identifică topicuri pentru video",
                        "Creează script-uri scurte",
                        "Înregistrează video-uri (5-10 minute)",
                        "Publică pe YouTube și social media"
                    ],
                    "impact": "High",
                    "estimated_time": "2-3 zile per video"
                }
            ],
            "total": 2
        }
    
    def _generate_ux_recommendations(self, domain: str, site_url: str) -> Dict:
        """Generează recomandări UX/UI"""
        
        return {
            "area": "UX/UI",
            "recommendations": [
                {
                    "title": "Optimizare Mobile",
                    "description": "Asigură-te că site-ul este perfect optimizat pentru mobile",
                    "steps": [
                        "Testează site-ul pe diferite dispozitive mobile",
                        "Optimizează butoanele și link-urile pentru touch",
                        "Verifică viteza de încărcare pe mobile",
                        "Implementează design responsive"
                    ],
                    "impact": "High",
                    "estimated_time": "1 săptămână"
                },
                {
                    "title": "Îmbunătățire Call-to-Action",
                    "description": "Face butoanele și call-to-action-urile mai vizibile și atractive",
                    "steps": [
                        "Analizează conversiile actuale",
                        "Testează diferite texte și culori",
                        "Plasează CTA-uri strategice",
                        "Măsoară rezultatele"
                    ],
                    "impact": "Medium",
                    "estimated_time": "3-5 zile"
                }
            ],
            "total": 2
        }
    
    def _generate_technical_recommendations(self, domain: str, site_url: str) -> Dict:
        """Generează recomandări tehnice"""
        
        return {
            "area": "Technical",
            "recommendations": [
                {
                    "title": "Optimizare Viteză Site",
                    "description": "Site-urile rapide au rate de conversie mai bune",
                    "steps": [
                        "Optimizează imagini (compresie, format WebP)",
                        "Implementează caching",
                        "Minimizează CSS și JavaScript",
                        "Folosește CDN dacă e posibil"
                    ],
                    "impact": "High",
                    "estimated_time": "3-5 zile"
                },
                {
                    "title": "Implementare SSL/HTTPS",
                    "description": "Securitatea este esențială pentru încrederea clienților",
                    "steps": [
                        "Obține certificat SSL",
                        "Configurează HTTPS",
                        "Redirectează HTTP la HTTPS",
                        "Verifică că toate resursele sunt HTTPS"
                    ],
                    "impact": "High",
                    "estimated_time": "1 zi"
                }
            ],
            "total": 2
        }
    
    def _generate_action_plan(self, recommendations: Dict, domain: str) -> Dict:
        """Generează un plan de acțiune prioritizat"""
        
        all_recs = []
        for area, area_data in recommendations.items():
            for rec in area_data.get("recommendations", []):
                rec["area"] = area
                all_recs.append(rec)
        
        # Sortează după impact și timp
        high_impact = [r for r in all_recs if r.get("impact", "").lower() == "high"]
        medium_impact = [r for r in all_recs if r.get("impact", "").lower() == "medium"]
        low_impact = [r for r in all_recs if r.get("impact", "").lower() == "low"]
        
        # Plan pe 30 de zile
        week1 = high_impact[:3] if len(high_impact) >= 3 else high_impact
        week2 = high_impact[3:6] if len(high_impact) >= 6 else medium_impact[:3]
        week3 = medium_impact[3:6] if len(medium_impact) >= 6 else low_impact[:3]
        week4 = low_impact[:3] if len(low_impact) >= 3 else medium_impact[6:9]
        
        return {
            "total_recommendations": len(all_recs),
            "high_impact_count": len(high_impact),
            "medium_impact_count": len(medium_impact),
            "low_impact_count": len(low_impact),
            "30_day_plan": {
                "week_1": week1,
                "week_2": week2,
                "week_3": week3,
                "week_4": week4
            },
            "quick_wins": [r for r in high_impact if "zi" in r.get("estimated_time", "").lower()][:5]
        }


# Funcție helper pentru API
def generate_action_recommendations(agent_id: str, focus_areas: Optional[List[str]] = None) -> Dict:
    """Funcție helper pentru generarea recomandărilor"""
    service = ActionRecommendationsService()
    return service.analyze_competitors_and_generate_recommendations(agent_id, focus_areas)

