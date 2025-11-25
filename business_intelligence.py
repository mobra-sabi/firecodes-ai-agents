# business_intelligence.py
"""
🎯 AI Business Intelligence System
- Gap Analysis
- Positioning Score
- Action Plan Generator
- Competitor Alerts
- AI Coach
"""

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import os
import json
import logging

logger = logging.getLogger(__name__)

# MongoDB connection
mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
db_name = os.getenv("MONGODB_DATABASE", "ai_agents_db")

client = MongoClient(mongo_uri)
db = client[db_name]


class GapAnalyzer:
    """Analizează gap-urile între tine și competitori"""
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        self.master_agent = db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
        
    def analyze_content_gaps(self) -> List[Dict]:
        """Identifică conținut pe care competitorii îl au și tu nu"""
        if not self.master_agent:
            return []
            
        master_domain = self.master_agent.get("domain", "")
        master_keywords = set(self.master_agent.get("keywords", []))
        master_services = set(self.master_agent.get("services", []))
        master_pages = self.master_agent.get("pages_indexed", 0)
        
        # Obține toți competitorii
        competitors = list(db.site_agents.find({
            "master_agent_id": ObjectId(self.master_agent_id)
        }))
        
        content_gaps = []
        keyword_frequency = {}
        service_frequency = {}
        topic_frequency = {}
        
        for comp in competitors:
            comp_keywords = comp.get("keywords", [])
            comp_services = comp.get("services", [])
            comp_subdomains = comp.get("subdomains", [])
            
            # Numără keywords pe care competitorii le au
            for kw in comp_keywords:
                if kw and kw not in master_keywords:
                    keyword_frequency[kw] = keyword_frequency.get(kw, 0) + 1
                    
            # Numără servicii pe care competitorii le au
            for svc in comp_services:
                if svc and svc not in master_services:
                    service_frequency[svc] = service_frequency.get(svc, 0) + 1
                    
            # Analizează subdomenii/topicuri
            for sub in comp_subdomains:
                topic = sub.get("name", "") if isinstance(sub, dict) else str(sub)
                if topic:
                    topic_frequency[topic] = topic_frequency.get(topic, 0) + 1
        
        # Sortează și returnează top gaps
        sorted_keywords = sorted(keyword_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
        sorted_services = sorted(service_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
        sorted_topics = sorted(topic_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "keyword_gaps": [
                {"keyword": kw, "competitors_with": count, "your_coverage": 0, "priority": "HIGH" if count >= 3 else "MEDIUM"}
                for kw, count in sorted_keywords
            ],
            "service_gaps": [
                {"service": svc, "competitors_with": count, "recommendation": f"Consideră adăugarea serviciului '{svc}'"}
                for svc, count in sorted_services
            ],
            "topic_gaps": [
                {"topic": topic, "competitors_with": count, "action": f"Creează conținut despre '{topic}'"}
                for topic, count in sorted_topics
            ],
            "page_count_gap": {
                "your_pages": master_pages,
                "competitor_average": sum(c.get("pages_indexed", 0) for c in competitors) // max(len(competitors), 1),
                "competitor_max": max((c.get("pages_indexed", 0) for c in competitors), default=0),
                "recommendation": None
            }
        }
    
    def analyze_keyword_opportunities(self) -> List[Dict]:
        """Identifică keyword-uri cu potențial"""
        if not self.master_agent:
            return []
            
        # Obține competitorii și keywords lor
        competitors = list(db.site_agents.find({
            "master_agent_id": ObjectId(self.master_agent_id)
        }))
        
        master_keywords = set(self.master_agent.get("keywords", []))
        
        opportunities = []
        keyword_data = {}
        
        for comp in competitors:
            comp_keywords = comp.get("keywords", [])
            comp_serp = comp.get("serp_positions", {})
            
            for kw in comp_keywords:
                if kw not in master_keywords:
                    if kw not in keyword_data:
                        keyword_data[kw] = {"count": 0, "positions": []}
                    keyword_data[kw]["count"] += 1
                    
                    # Adaugă poziția dacă există
                    if kw in comp_serp:
                        keyword_data[kw]["positions"].append(comp_serp[kw])
        
        # Calculează oportunități
        for kw, data in keyword_data.items():
            if data["count"] >= 2:  # Cel puțin 2 competitori
                avg_position = sum(data["positions"]) / len(data["positions"]) if data["positions"] else 50
                difficulty = min(100, int(avg_position * 2))  # Estimare simplă
                
                opportunities.append({
                    "keyword": kw,
                    "competitors_ranking": data["count"],
                    "estimated_difficulty": difficulty,
                    "priority": "HIGH" if data["count"] >= 5 and difficulty < 50 else "MEDIUM",
                    "action": f"Creează pagină optimizată pentru '{kw}'"
                })
        
        return sorted(opportunities, key=lambda x: (-x["competitors_ranking"], x["estimated_difficulty"]))[:15]


class PositioningScorer:
    """Calculează scorul de poziționare în piață"""
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        self.master_agent = db.site_agents.find_one({"_id": ObjectId(master_agent_id)})
        
    def calculate_score(self) -> Dict:
        """Calculează scorul general de poziționare (0-100)"""
        if not self.master_agent:
            return {"score": 0, "breakdown": {}}
            
        competitors = list(db.site_agents.find({
            "master_agent_id": ObjectId(self.master_agent_id)
        }))
        
        if not competitors:
            return {"score": 50, "breakdown": {}, "message": "Nu sunt suficienți competitori pentru analiză"}
        
        scores = {}
        
        # 1. Content Score (25 puncte)
        master_pages = self.master_agent.get("pages_indexed", 0)
        avg_pages = sum(c.get("pages_indexed", 0) for c in competitors) / len(competitors)
        content_ratio = min(master_pages / max(avg_pages, 1), 2)  # Cap at 2x
        scores["content"] = min(25, int(content_ratio * 12.5))
        
        # 2. Keyword Coverage Score (25 puncte)
        master_keywords = len(self.master_agent.get("keywords", []))
        avg_keywords = sum(len(c.get("keywords", [])) for c in competitors) / len(competitors)
        keyword_ratio = min(master_keywords / max(avg_keywords, 1), 2)
        scores["keywords"] = min(25, int(keyword_ratio * 12.5))
        
        # 3. Service Diversity Score (25 puncte)
        master_services = len(self.master_agent.get("services", []))
        avg_services = sum(len(c.get("services", [])) for c in competitors) / len(competitors)
        service_ratio = min(master_services / max(avg_services, 1), 2)
        scores["services"] = min(25, int(service_ratio * 12.5))
        
        # 4. Technical Score (25 puncte) - bazat pe chunks/embeddings
        master_chunks = self.master_agent.get("chunks_indexed", 0)
        avg_chunks = sum(c.get("chunks_indexed", 0) for c in competitors) / len(competitors)
        tech_ratio = min(master_chunks / max(avg_chunks, 1), 2)
        scores["technical"] = min(25, int(tech_ratio * 12.5))
        
        total_score = sum(scores.values())
        
        # Calculează ranking
        all_scores = []
        for comp in competitors:
            comp_score = self._calculate_competitor_score(comp, competitors)
            all_scores.append(comp_score)
        all_scores.append(total_score)
        all_scores.sort(reverse=True)
        ranking = all_scores.index(total_score) + 1
        
        return {
            "score": total_score,
            "max_score": 100,
            "ranking": ranking,
            "total_competitors": len(competitors) + 1,
            "breakdown": {
                "content": {"score": scores["content"], "max": 25, "label": "Conținut"},
                "keywords": {"score": scores["keywords"], "max": 25, "label": "Keywords"},
                "services": {"score": scores["services"], "max": 25, "label": "Servicii"},
                "technical": {"score": scores["technical"], "max": 25, "label": "Tehnic"}
            },
            "interpretation": self._interpret_score(total_score),
            "vs_average": {
                "your_score": total_score,
                "competitor_average": int(sum(all_scores[:-1]) / max(len(all_scores) - 1, 1)),
                "difference": total_score - int(sum(all_scores[:-1]) / max(len(all_scores) - 1, 1))
            }
        }
    
    def _calculate_competitor_score(self, comp: Dict, all_competitors: List) -> int:
        """Calculează scorul unui competitor"""
        avg_pages = sum(c.get("pages_indexed", 0) for c in all_competitors) / len(all_competitors)
        avg_keywords = sum(len(c.get("keywords", [])) for c in all_competitors) / len(all_competitors)
        avg_services = sum(len(c.get("services", [])) for c in all_competitors) / len(all_competitors)
        avg_chunks = sum(c.get("chunks_indexed", 0) for c in all_competitors) / len(all_competitors)
        
        content = min(25, int(min(comp.get("pages_indexed", 0) / max(avg_pages, 1), 2) * 12.5))
        keywords = min(25, int(min(len(comp.get("keywords", [])) / max(avg_keywords, 1), 2) * 12.5))
        services = min(25, int(min(len(comp.get("services", [])) / max(avg_services, 1), 2) * 12.5))
        technical = min(25, int(min(comp.get("chunks_indexed", 0) / max(avg_chunks, 1), 2) * 12.5))
        
        return content + keywords + services + technical
    
    def _interpret_score(self, score: int) -> Dict:
        """Interpretează scorul"""
        if score >= 80:
            return {"level": "EXCELLENT", "emoji": "🏆", "message": "Ești lider în piață! Menține poziția."}
        elif score >= 60:
            return {"level": "GOOD", "emoji": "✅", "message": "Poziție bună. Câteva îmbunătățiri te pot duce în top."}
        elif score >= 40:
            return {"level": "AVERAGE", "emoji": "⚠️", "message": "Poziție medie. Ai nevoie de îmbunătățiri semnificative."}
        else:
            return {"level": "NEEDS_WORK", "emoji": "🔴", "message": "Sub medie. Concentrează-te pe gap-uri majore."}
    
    def get_comparison_with_top(self, top_n: int = 3) -> Dict:
        """Compară cu top N competitori"""
        if not self.master_agent:
            return {}
            
        competitors = list(db.site_agents.find({
            "master_agent_id": ObjectId(self.master_agent_id)
        }))
        
        if not competitors:
            return {}
        
        # Sortează competitorii după scor
        scored_competitors = []
        for comp in competitors:
            score = self._calculate_competitor_score(comp, competitors)
            scored_competitors.append({
                "domain": comp.get("domain", "unknown"),
                "score": score,
                "pages": comp.get("pages_indexed", 0),
                "keywords": len(comp.get("keywords", [])),
                "services": len(comp.get("services", [])),
                "chunks": comp.get("chunks_indexed", 0)
            })
        
        scored_competitors.sort(key=lambda x: x["score"], reverse=True)
        top_competitors = scored_competitors[:top_n]
        
        master_data = {
            "domain": self.master_agent.get("domain", "Tu"),
            "score": self.calculate_score()["score"],
            "pages": self.master_agent.get("pages_indexed", 0),
            "keywords": len(self.master_agent.get("keywords", [])),
            "services": len(self.master_agent.get("services", [])),
            "chunks": self.master_agent.get("chunks_indexed", 0)
        }
        
        return {
            "you": master_data,
            "top_competitors": top_competitors,
            "metrics": ["pages", "keywords", "services", "chunks"],
            "metric_labels": {
                "pages": "Pagini indexate",
                "keywords": "Keywords",
                "services": "Servicii",
                "chunks": "Conținut (chunks)"
            }
        }


class ActionPlanGenerator:
    """Generează plan de acțiune prioritizat"""
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        self.gap_analyzer = GapAnalyzer(master_agent_id)
        self.scorer = PositioningScorer(master_agent_id)
        
    def generate_plan(self, business_context: Optional[Dict] = None) -> Dict:
        """Generează plan de acțiune complet"""
        gaps = self.gap_analyzer.analyze_content_gaps()
        opportunities = self.gap_analyzer.analyze_keyword_opportunities()
        score = self.scorer.calculate_score()
        
        actions = []
        
        # 1. Quick Wins - acțiuni cu impact mare și efort mic
        quick_wins = []
        
        # Adaugă keywords lipsă
        for kw_gap in gaps.get("keyword_gaps", [])[:3]:
            quick_wins.append({
                "id": f"kw_{kw_gap['keyword'][:10]}",
                "title": f"Adaugă keyword: {kw_gap['keyword']}",
                "description": f"{kw_gap['competitors_with']} competitori au acest keyword",
                "impact": "HIGH",
                "effort": "LOW",
                "category": "keywords",
                "estimated_time": "1-2 ore",
                "steps": [
                    f"Cercetează intenția de căutare pentru '{kw_gap['keyword']}'",
                    "Identifică pagina potrivită sau creează una nouă",
                    "Optimizează title, meta description și H1",
                    "Adaugă conținut relevant (min. 500 cuvinte)"
                ]
            })
        
        # Adaugă servicii lipsă
        for svc_gap in gaps.get("service_gaps", [])[:2]:
            quick_wins.append({
                "id": f"svc_{svc_gap['service'][:10]}",
                "title": f"Adaugă serviciu: {svc_gap['service']}",
                "description": f"{svc_gap['competitors_with']} competitori oferă acest serviciu",
                "impact": "HIGH",
                "effort": "MEDIUM",
                "category": "services",
                "estimated_time": "2-4 ore",
                "steps": [
                    f"Analizează cum prezintă competitorii serviciul '{svc_gap['service']}'",
                    "Creează pagină dedicată serviciului",
                    "Adaugă prețuri/pachete dacă e posibil",
                    "Include testimoniale relevante"
                ]
            })
        
        # 2. Medium Term - acțiuni cu efort mediu
        medium_term = []
        
        # Content gap
        page_gap = gaps.get("page_count_gap", {})
        if page_gap.get("your_pages", 0) < page_gap.get("competitor_average", 0):
            diff = page_gap["competitor_average"] - page_gap["your_pages"]
            medium_term.append({
                "id": "content_expansion",
                "title": "Extinde conținutul site-ului",
                "description": f"Ai {page_gap['your_pages']} pagini vs media de {page_gap['competitor_average']}",
                "impact": "HIGH",
                "effort": "HIGH",
                "category": "content",
                "estimated_time": "2-4 săptămâni",
                "target": f"Adaugă {diff} pagini noi",
                "steps": [
                    "Identifică topicuri relevante din gap analysis",
                    f"Creează calendar editorial pentru {diff} articole",
                    "Scrie conținut de calitate (min. 800 cuvinte/articol)",
                    "Optimizează pentru SEO fiecare pagină"
                ]
            })
        
        # Topic gaps
        for topic_gap in gaps.get("topic_gaps", [])[:3]:
            medium_term.append({
                "id": f"topic_{topic_gap['topic'][:10]}",
                "title": f"Acoperă topicul: {topic_gap['topic']}",
                "description": f"{topic_gap['competitors_with']} competitori au conținut despre acest topic",
                "impact": "MEDIUM",
                "effort": "MEDIUM",
                "category": "content",
                "estimated_time": "3-5 zile",
                "steps": [
                    f"Cercetează ce scriu competitorii despre '{topic_gap['topic']}'",
                    "Creează outline pentru articol comprehensiv",
                    "Scrie conținut unic și valoros",
                    "Adaugă imagini și elemente vizuale"
                ]
            })
        
        # 3. Long Term - acțiuni strategice
        long_term = []
        
        # Keyword opportunities
        for opp in opportunities[:3]:
            long_term.append({
                "id": f"opp_{opp['keyword'][:10]}",
                "title": f"Targetează: {opp['keyword']}",
                "description": f"{opp['competitors_ranking']} competitori rankează, dificultate: {opp['estimated_difficulty']}%",
                "impact": "HIGH",
                "effort": "HIGH",
                "category": "seo",
                "estimated_time": "1-3 luni",
                "steps": [
                    f"Creează pagină pillar pentru '{opp['keyword']}'",
                    "Construiește cluster de conținut suport",
                    "Obține backlinks relevante",
                    "Monitorizează și optimizează"
                ]
            })
        
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "positioning_score": score["score"],
            "total_actions": len(quick_wins) + len(medium_term) + len(long_term),
            "quick_wins": {
                "title": "🚀 Quick Wins (1-2 săptămâni)",
                "description": "Acțiuni cu impact mare și efort mic",
                "actions": quick_wins
            },
            "medium_term": {
                "title": "📈 Termen Mediu (2-4 săptămâni)",
                "description": "Acțiuni cu efort mediu pentru creștere sustenabilă",
                "actions": medium_term
            },
            "long_term": {
                "title": "🎯 Termen Lung (1-3 luni)",
                "description": "Strategii pentru dominare în piață",
                "actions": long_term
            },
            "priority_order": [
                {"phase": "quick_wins", "focus": "Implementează rapid pentru rezultate imediate"},
                {"phase": "medium_term", "focus": "Construiește fundația pentru creștere"},
                {"phase": "long_term", "focus": "Investește în poziționare pe termen lung"}
            ]
        }


class BusinessDiscoveryWizard:
    """Wizard pentru descoperirea detaliilor afacerii"""
    
    QUESTIONS = [
        {
            "id": "business_type",
            "question": "Ce tip de afacere ai?",
            "type": "select",
            "options": [
                {"value": "services", "label": "Servicii (consultanță, construcții, etc.)"},
                {"value": "ecommerce", "label": "E-commerce (vânzare produse)"},
                {"value": "saas", "label": "SaaS / Software"},
                {"value": "local", "label": "Afacere locală (restaurant, salon, etc.)"},
                {"value": "other", "label": "Altceva"}
            ]
        },
        {
            "id": "employees",
            "question": "Câți angajați ai?",
            "type": "select",
            "options": [
                {"value": "1", "label": "Doar eu"},
                {"value": "2-5", "label": "2-5 angajați"},
                {"value": "6-20", "label": "6-20 angajați"},
                {"value": "21-50", "label": "21-50 angajați"},
                {"value": "50+", "label": "Peste 50 angajați"}
            ]
        },
        {
            "id": "monthly_budget",
            "question": "Care e bugetul lunar pentru marketing?",
            "type": "select",
            "options": [
                {"value": "0-500", "label": "0-500 RON"},
                {"value": "500-2000", "label": "500-2000 RON"},
                {"value": "2000-5000", "label": "2000-5000 RON"},
                {"value": "5000-10000", "label": "5000-10000 RON"},
                {"value": "10000+", "label": "Peste 10000 RON"}
            ]
        },
        {
            "id": "main_goal",
            "question": "Care e obiectivul principal în următoarele 6 luni?",
            "type": "multiselect",
            "options": [
                {"value": "more_clients", "label": "Mai mulți clienți"},
                {"value": "higher_prices", "label": "Prețuri mai mari"},
                {"value": "new_services", "label": "Servicii/produse noi"},
                {"value": "geographic_expansion", "label": "Extindere geografică"},
                {"value": "brand_awareness", "label": "Notorietate brand"},
                {"value": "online_presence", "label": "Prezență online mai bună"}
            ]
        },
        {
            "id": "available_resources",
            "question": "Ce resurse ai disponibile pentru implementare?",
            "type": "multiselect",
            "options": [
                {"value": "time", "label": "Timp (pot lucra eu)"},
                {"value": "money", "label": "Buget pentru externalizare"},
                {"value": "team", "label": "Echipă internă"},
                {"value": "tools", "label": "Unelte/software plătite"}
            ]
        },
        {
            "id": "timeline",
            "question": "În cât timp vrei să vezi rezultate?",
            "type": "select",
            "options": [
                {"value": "1month", "label": "1 lună"},
                {"value": "3months", "label": "3 luni"},
                {"value": "6months", "label": "6 luni"},
                {"value": "12months", "label": "12 luni"}
            ]
        },
        {
            "id": "biggest_challenge",
            "question": "Care e cea mai mare provocare acum?",
            "type": "select",
            "options": [
                {"value": "visibility", "label": "Nu mă găsesc clienții"},
                {"value": "competition", "label": "Competiția e prea mare"},
                {"value": "conversion", "label": "Am vizitatori dar nu cumpără"},
                {"value": "pricing", "label": "Nu știu ce prețuri să pun"},
                {"value": "differentiation", "label": "Nu știu cum să mă diferențiez"}
            ]
        },
        {
            "id": "current_marketing",
            "question": "Ce faci acum pentru marketing?",
            "type": "multiselect",
            "options": [
                {"value": "seo", "label": "SEO / Optimizare site"},
                {"value": "social", "label": "Social media"},
                {"value": "ads", "label": "Reclame plătite (Google, Facebook)"},
                {"value": "content", "label": "Content marketing / Blog"},
                {"value": "email", "label": "Email marketing"},
                {"value": "nothing", "label": "Nimic încă"}
            ]
        }
    ]
    
    @classmethod
    def get_questions(cls) -> List[Dict]:
        """Returnează toate întrebările"""
        return cls.QUESTIONS
    
    @classmethod
    def generate_personalized_recommendations(cls, answers: Dict, gap_analysis: Dict, score: Dict) -> Dict:
        """Generează recomandări personalizate bazate pe răspunsuri"""
        recommendations = []
        priority_focus = []
        
        # Analizează răspunsurile
        budget = answers.get("monthly_budget", "0-500")
        timeline = answers.get("timeline", "6months")
        challenge = answers.get("biggest_challenge", "visibility")
        goals = answers.get("main_goal", [])
        resources = answers.get("available_resources", [])
        
        # Recomandări bazate pe provocarea principală
        if challenge == "visibility":
            priority_focus.append({
                "area": "SEO & Content",
                "reason": "Ai nevoie să fii găsit mai ușor de clienți",
                "actions": [
                    "Optimizează paginile existente pentru keywords relevante",
                    "Creează conținut pentru keyword gaps identificate",
                    "Înregistrează-te pe Google Business Profile"
                ]
            })
        elif challenge == "competition":
            priority_focus.append({
                "area": "Diferențiere",
                "reason": "Trebuie să te evidențiezi față de competitori",
                "actions": [
                    "Identifică ce faci diferit/mai bine decât competitorii",
                    "Creează pagină 'De ce să ne alegi'",
                    "Adaugă testimoniale și studii de caz"
                ]
            })
        elif challenge == "conversion":
            priority_focus.append({
                "area": "Optimizare Conversii",
                "reason": "Ai trafic dar nu convertești",
                "actions": [
                    "Adaugă call-to-action clar pe fiecare pagină",
                    "Simplifică procesul de contact/comandă",
                    "Adaugă elemente de încredere (testimoniale, certificări)"
                ]
            })
        
        # Recomandări bazate pe buget
        if budget in ["0-500", "500-2000"]:
            recommendations.append({
                "type": "budget_tip",
                "message": "Cu buget limitat, concentrează-te pe SEO organic și content marketing - sunt gratuite și au efect pe termen lung."
            })
        else:
            recommendations.append({
                "type": "budget_tip", 
                "message": "Poți combina SEO organic cu campanii Google Ads pentru rezultate mai rapide."
            })
        
        # Recomandări bazate pe timeline
        if timeline == "1month":
            recommendations.append({
                "type": "timeline_tip",
                "message": "Pentru rezultate în 1 lună, concentrează-te pe Quick Wins din planul de acțiune. SEO organic necesită 3-6 luni."
            })
        
        # Recomandări bazate pe gap analysis
        keyword_gaps = gap_analysis.get("keyword_gaps", [])
        if len(keyword_gaps) > 5:
            recommendations.append({
                "type": "gap_alert",
                "message": f"Ai {len(keyword_gaps)} keywords importante pe care competitorii le au și tu nu. Aceasta e o oportunitate mare!"
            })
        
        return {
            "priority_focus": priority_focus,
            "recommendations": recommendations,
            "personalized_score": score,
            "next_steps": [
                "Revizuiește planul de acțiune generat",
                "Începe cu primul Quick Win",
                "Setează reminder pentru check-in săptămânal"
            ],
            "estimated_improvement": {
                "if_implemented": "+15-30 puncte în scorul de poziționare",
                "timeline": timeline
            }
        }


class CompetitorAlertSystem:
    """Sistem de alertare pentru mișcări competitori"""
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        
    def check_alerts(self) -> List[Dict]:
        """Verifică și generează alerte"""
        alerts = []
        
        master = db.site_agents.find_one({"_id": ObjectId(self.master_agent_id)})
        if not master:
            return alerts
            
        competitors = list(db.site_agents.find({
            "master_agent_id": ObjectId(self.master_agent_id)
        }))
        
        master_keywords = set(master.get("keywords", []))
        
        # Alert: Competitori noi
        def is_recent(created_at):
            if not created_at:
                return False
            try:
                # Handle both naive and aware datetimes
                now = datetime.now(timezone.utc)
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                return (now - created_at).days < 7
            except:
                return False
        
        recent_competitors = [c for c in competitors if is_recent(c.get("created_at"))]
        if recent_competitors:
            alerts.append({
                "type": "new_competitor",
                "severity": "INFO",
                "title": f"{len(recent_competitors)} competitori noi identificați",
                "message": f"Am identificat {len(recent_competitors)} competitori noi în ultima săptămână.",
                "competitors": [c.get("domain") for c in recent_competitors],
                "action": "Analizează-i pentru a identifica noi oportunități"
            })
        
        # Alert: Competitori cu mai mult conținut
        master_pages = master.get("pages_indexed", 0)
        bigger_competitors = [c for c in competitors 
                            if c.get("pages_indexed", 0) > master_pages * 1.5]
        if bigger_competitors:
            alerts.append({
                "type": "content_gap",
                "severity": "WARNING",
                "title": "Competitori cu conținut mai bogat",
                "message": f"{len(bigger_competitors)} competitori au cu 50%+ mai mult conținut decât tine.",
                "competitors": [{"domain": c.get("domain"), "pages": c.get("pages_indexed")} 
                              for c in bigger_competitors[:3]],
                "action": "Extinde conținutul site-ului pentru a rămâne competitiv"
            })
        
        # Alert: Keywords comune
        keyword_overlap = {}
        for comp in competitors:
            comp_keywords = set(comp.get("keywords", []))
            overlap = master_keywords & comp_keywords
            if overlap:
                keyword_overlap[comp.get("domain")] = len(overlap)
        
        if keyword_overlap:
            top_overlaps = sorted(keyword_overlap.items(), key=lambda x: x[1], reverse=True)[:3]
            alerts.append({
                "type": "keyword_competition",
                "severity": "INFO",
                "title": "Competiție pe keywords",
                "message": "Acești competitori targetează aceleași keywords ca tine.",
                "data": [{"domain": d, "shared_keywords": c} for d, c in top_overlaps],
                "action": "Monitorizează pozițiile și optimizează conținutul"
            })
        
        return alerts
    
    def get_alert_summary(self) -> Dict:
        """Returnează sumar alerte"""
        alerts = self.check_alerts()
        
        return {
            "total_alerts": len(alerts),
            "by_severity": {
                "critical": len([a for a in alerts if a["severity"] == "CRITICAL"]),
                "warning": len([a for a in alerts if a["severity"] == "WARNING"]),
                "info": len([a for a in alerts if a["severity"] == "INFO"])
            },
            "alerts": alerts,
            "last_check": datetime.now(timezone.utc).isoformat()
        }


class AICoach:
    """AI Coach pentru ghidare proactivă"""
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        self.scorer = PositioningScorer(master_agent_id)
        self.gap_analyzer = GapAnalyzer(master_agent_id)
        
    def get_weekly_checkin(self) -> Dict:
        """Generează check-in săptămânal"""
        score = self.scorer.calculate_score()
        gaps = self.gap_analyzer.analyze_content_gaps()
        
        # Verifică progresul
        progress_data = db.coach_progress.find_one({
            "master_agent_id": self.master_agent_id
        })
        
        previous_score = progress_data.get("last_score", score["score"]) if progress_data else score["score"]
        score_change = score["score"] - previous_score
        
        # Salvează progresul
        db.coach_progress.update_one(
            {"master_agent_id": self.master_agent_id},
            {
                "$set": {
                    "last_score": score["score"],
                    "last_check": datetime.now(timezone.utc),
                    "history": {
                        "$push": {
                            "date": datetime.now(timezone.utc),
                            "score": score["score"]
                        }
                    }
                }
            },
            upsert=True
        )
        
        # Generează mesaj
        if score_change > 5:
            mood = "celebration"
            message = f"🎉 Felicitări! Scorul tău a crescut cu {score_change} puncte! Continuă așa!"
        elif score_change > 0:
            mood = "positive"
            message = f"📈 Progres bun! Ai câștigat {score_change} puncte săptămâna aceasta."
        elif score_change == 0:
            mood = "neutral"
            message = "⚖️ Scorul tău e stabil. Hai să implementăm câteva acțiuni pentru creștere!"
        else:
            mood = "concern"
            message = f"⚠️ Scorul a scăzut cu {abs(score_change)} puncte. Să vedem ce putem îmbunătăți."
        
        # Sugestii pentru săptămâna următoare
        suggestions = []
        keyword_gaps = gaps.get("keyword_gaps", [])
        if keyword_gaps:
            suggestions.append({
                "action": f"Adaugă keyword-ul '{keyword_gaps[0]['keyword']}' pe site",
                "impact": "HIGH",
                "time": "2 ore"
            })
        
        service_gaps = gaps.get("service_gaps", [])
        if service_gaps:
            suggestions.append({
                "action": f"Creează pagină pentru serviciul '{service_gaps[0]['service']}'",
                "impact": "MEDIUM",
                "time": "4 ore"
            })
        
        return {
            "mood": mood,
            "message": message,
            "current_score": score["score"],
            "score_change": score_change,
            "ranking": score.get("ranking", "N/A"),
            "suggestions_for_week": suggestions[:3],
            "motivational_tip": self._get_motivational_tip(score["score"]),
            "next_checkin": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        }
    
    def _get_motivational_tip(self, score: int) -> str:
        """Returnează un tip motivațional"""
        tips = {
            "low": [
                "Fiecare expert a fost cândva un începător. Începe cu pași mici!",
                "Consistența bate talentul. Un mic progres zilnic duce la rezultate mari.",
                "Nu te compara cu alții, compară-te cu tine de ieri."
            ],
            "medium": [
                "Ești pe drumul cel bun! Continuă să implementezi și vei vedea rezultate.",
                "Succesul vine din acțiuni consistente, nu din eforturi sporadice.",
                "Fiecare pagină nouă e o oportunitate de a fi găsit de clienți."
            ],
            "high": [
                "Ești în top! Acum e momentul să consolidezi și să extinzi.",
                "Liderii nu se opresc din învățat. Ce poți face mai bine?",
                "Menține avantajul prin inovație continuă."
            ]
        }
        
        import random
        if score < 40:
            return random.choice(tips["low"])
        elif score < 70:
            return random.choice(tips["medium"])
        else:
            return random.choice(tips["high"])
    
    def ask_coach(self, question: str) -> Dict:
        """Răspunde la întrebări despre afacere"""
        # Colectează context
        score = self.scorer.calculate_score()
        gaps = self.gap_analyzer.analyze_content_gaps()
        
        context = f"""
        Scor poziționare: {score['score']}/100
        Keywords lipsă: {len(gaps.get('keyword_gaps', []))}
        Servicii lipsă: {len(gaps.get('service_gaps', []))}
        """
        
        # Pentru răspunsuri simple, folosim logică locală
        # Pentru întrebări complexe, ar trebui să folosim DeepSeek
        
        response = {
            "question": question,
            "context_used": context,
            "answer": "Bazat pe analiza ta, iată ce recomand...",
            "related_actions": [],
            "follow_up_questions": [
                "Vrei să vezi planul de acțiune detaliat?",
                "Ai nevoie de ajutor cu implementarea?"
            ]
        }
        
        return response


# Export all classes
__all__ = [
    'GapAnalyzer',
    'PositioningScorer', 
    'ActionPlanGenerator',
    'BusinessDiscoveryWizard',
    'CompetitorAlertSystem',
    'AICoach'
]

