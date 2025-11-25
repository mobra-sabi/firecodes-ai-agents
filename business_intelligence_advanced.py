# business_intelligence_advanced.py
"""
🚀 Advanced Business Intelligence Features
- Trend Tracking & History
- Goal Setting & Progress
- AI Content Generator
- ROI Calculator
- Competitor Watchlist
- Checklist System
- PDF Reports
- Notifications
"""

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import os
import json
import logging
import hashlib

logger = logging.getLogger(__name__)

# MongoDB connection
mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
db_name = os.getenv("MONGODB_DATABASE", "ai_agents_db")

client = MongoClient(mongo_uri)
db = client[db_name]


# ============================================================================
# 📊 TREND TRACKING & HISTORY
# ============================================================================

class TrendTracker:
    """Salvează și analizează trenduri în timp"""
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        self.collection = db.position_history
        
    def record_snapshot(self) -> Dict:
        """Salvează un snapshot al poziționării curente"""
        from business_intelligence import PositioningScorer, GapAnalyzer
        
        scorer = PositioningScorer(self.master_agent_id)
        analyzer = GapAnalyzer(self.master_agent_id)
        
        score_data = scorer.calculate_score()
        gaps = analyzer.analyze_content_gaps()
        
        # Obține date despre competitori
        competitors = list(db.site_agents.find({
            "master_agent_id": ObjectId(self.master_agent_id)
        }))
        
        snapshot = {
            "master_agent_id": self.master_agent_id,
            "timestamp": datetime.now(timezone.utc),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "score": score_data.get("score", 0),
            "ranking": score_data.get("ranking", 0),
            "total_competitors": len(competitors),
            "breakdown": score_data.get("breakdown", {}),
            "gaps_count": {
                "keywords": len(gaps.get("keyword_gaps", [])),
                "services": len(gaps.get("service_gaps", [])),
                "topics": len(gaps.get("topic_gaps", []))
            },
            "competitor_stats": {
                "total": len(competitors),
                "avg_pages": sum(c.get("pages_indexed", 0) for c in competitors) // max(len(competitors), 1),
                "avg_chunks": sum(c.get("chunks_indexed", 0) for c in competitors) // max(len(competitors), 1)
            }
        }
        
        # Salvează în DB (update dacă există pentru azi)
        self.collection.update_one(
            {
                "master_agent_id": self.master_agent_id,
                "date": snapshot["date"]
            },
            {"$set": snapshot},
            upsert=True
        )
        
        return snapshot
    
    def get_history(self, days: int = 30) -> List[Dict]:
        """Returnează istoricul ultimelor N zile"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        history = list(self.collection.find({
            "master_agent_id": self.master_agent_id,
            "timestamp": {"$gte": start_date}
        }).sort("timestamp", 1))
        
        # Convertește ObjectId pentru JSON
        for h in history:
            h["_id"] = str(h["_id"])
            h["timestamp"] = h["timestamp"].isoformat() if h.get("timestamp") else None
        
        return history
    
    def get_trend_analysis(self) -> Dict:
        """Analizează trendurile"""
        history = self.get_history(30)
        
        if len(history) < 2:
            return {
                "has_data": False,
                "message": "Nu există suficiente date pentru analiză. Revino mâine."
            }
        
        first = history[0]
        last = history[-1]
        
        score_change = last.get("score", 0) - first.get("score", 0)
        ranking_change = first.get("ranking", 0) - last.get("ranking", 0)  # Invers - mai mic e mai bun
        
        # Calculează trend
        if score_change > 5:
            trend = "up"
            trend_message = f"📈 Excelent! Scorul a crescut cu {score_change} puncte în ultimele {len(history)} zile."
        elif score_change < -5:
            trend = "down"
            trend_message = f"📉 Atenție! Scorul a scăzut cu {abs(score_change)} puncte. Verifică competitorii."
        else:
            trend = "stable"
            trend_message = "➡️ Scorul este stabil. Continuă cu planul de acțiune pentru creștere."
        
        return {
            "has_data": True,
            "period_days": len(history),
            "first_date": first.get("date"),
            "last_date": last.get("date"),
            "score_change": score_change,
            "ranking_change": ranking_change,
            "trend": trend,
            "trend_message": trend_message,
            "history": history,
            "chart_data": {
                "labels": [h.get("date") for h in history],
                "scores": [h.get("score", 0) for h in history],
                "rankings": [h.get("ranking", 0) for h in history]
            }
        }


# ============================================================================
# 🎯 GOAL SETTING & TRACKING
# ============================================================================

class GoalTracker:
    """Sistem de setare și urmărire obiective"""
    
    GOAL_TYPES = {
        "score": {"label": "Scor Poziționare", "unit": "puncte", "icon": "🎯"},
        "ranking": {"label": "Poziție în Clasament", "unit": "loc", "icon": "🏆"},
        "keywords": {"label": "Keywords Acoperite", "unit": "keywords", "icon": "🔑"},
        "pages": {"label": "Pagini Indexate", "unit": "pagini", "icon": "📄"},
        "competitors_analyzed": {"label": "Competitori Analizați", "unit": "competitori", "icon": "👥"}
    }
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        self.collection = db.business_goals
        
    def set_goal(self, goal_type: str, target_value: int, deadline_days: int, notes: str = "") -> Dict:
        """Setează un obiectiv nou"""
        if goal_type not in self.GOAL_TYPES:
            raise ValueError(f"Tip obiectiv invalid. Opțiuni: {list(self.GOAL_TYPES.keys())}")
        
        # Obține valoarea curentă
        current_value = self._get_current_value(goal_type)
        
        goal = {
            "master_agent_id": self.master_agent_id,
            "goal_type": goal_type,
            "target_value": target_value,
            "start_value": current_value,
            "current_value": current_value,
            "deadline": datetime.now(timezone.utc) + timedelta(days=deadline_days),
            "deadline_days": deadline_days,
            "notes": notes,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "progress_history": [{
                "date": datetime.now(timezone.utc),
                "value": current_value
            }]
        }
        
        result = self.collection.insert_one(goal)
        goal["_id"] = str(result.inserted_id)
        
        return goal
    
    def _get_current_value(self, goal_type: str) -> int:
        """Obține valoarea curentă pentru un tip de obiectiv"""
        from business_intelligence import PositioningScorer
        
        master = db.site_agents.find_one({"_id": ObjectId(self.master_agent_id)})
        competitors = db.site_agents.count_documents({
            "master_agent_id": ObjectId(self.master_agent_id)
        })
        
        if goal_type == "score":
            scorer = PositioningScorer(self.master_agent_id)
            return scorer.calculate_score().get("score", 0)
        elif goal_type == "ranking":
            scorer = PositioningScorer(self.master_agent_id)
            return scorer.calculate_score().get("ranking", 999)
        elif goal_type == "keywords":
            return len(master.get("keywords", [])) if master else 0
        elif goal_type == "pages":
            return master.get("pages_indexed", 0) if master else 0
        elif goal_type == "competitors_analyzed":
            return competitors
        
        return 0
    
    def get_goals(self, status: str = None) -> List[Dict]:
        """Returnează toate obiectivele"""
        query = {"master_agent_id": self.master_agent_id}
        if status:
            query["status"] = status
        
        goals = list(self.collection.find(query).sort("created_at", -1))
        
        for goal in goals:
            goal["_id"] = str(goal["_id"])
            goal["created_at"] = goal["created_at"].isoformat() if goal.get("created_at") else None
            goal["deadline"] = goal["deadline"].isoformat() if goal.get("deadline") else None
            
            # Calculează progresul
            current = self._get_current_value(goal["goal_type"])
            goal["current_value"] = current
            
            start = goal.get("start_value", 0)
            target = goal.get("target_value", 0)
            
            if goal["goal_type"] == "ranking":
                # Pentru ranking, mai mic e mai bun
                if start > target:
                    progress = ((start - current) / (start - target)) * 100 if start != target else 100
                else:
                    progress = 0
            else:
                progress = ((current - start) / (target - start)) * 100 if target != start else 100
            
            goal["progress_percent"] = min(100, max(0, int(progress)))
            goal["is_completed"] = goal["progress_percent"] >= 100
            goal["type_info"] = self.GOAL_TYPES.get(goal["goal_type"], {})
            
            # Verifică dacă a expirat
            if goal.get("deadline"):
                deadline = datetime.fromisoformat(goal["deadline"].replace("Z", "+00:00")) if isinstance(goal["deadline"], str) else goal["deadline"]
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                goal["is_overdue"] = datetime.now(timezone.utc) > deadline and not goal["is_completed"]
                goal["days_remaining"] = (deadline - datetime.now(timezone.utc)).days
        
        return goals
    
    def update_goal_progress(self, goal_id: str) -> Dict:
        """Actualizează progresul unui obiectiv"""
        goal = self.collection.find_one({"_id": ObjectId(goal_id)})
        if not goal:
            raise ValueError("Obiectiv negăsit")
        
        current_value = self._get_current_value(goal["goal_type"])
        
        self.collection.update_one(
            {"_id": ObjectId(goal_id)},
            {
                "$set": {"current_value": current_value},
                "$push": {
                    "progress_history": {
                        "date": datetime.now(timezone.utc),
                        "value": current_value
                    }
                }
            }
        )
        
        return {"updated": True, "current_value": current_value}
    
    def complete_goal(self, goal_id: str) -> Dict:
        """Marchează un obiectiv ca completat"""
        self.collection.update_one(
            {"_id": ObjectId(goal_id)},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc)
                }
            }
        )
        return {"status": "completed"}


# ============================================================================
# ✅ CHECKLIST SYSTEM
# ============================================================================

class ActionChecklist:
    """Sistem de checklist pentru acțiuni"""
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        self.collection = db.action_checklists
        
    def create_checklist_from_plan(self, plan: Dict) -> Dict:
        """Creează un checklist din planul de acțiune"""
        items = []
        
        # Quick Wins
        for action in plan.get("quick_wins", {}).get("actions", []):
            items.append({
                "id": action.get("id", hashlib.md5(action["title"].encode()).hexdigest()[:8]),
                "title": action["title"],
                "description": action.get("description", ""),
                "category": "quick_win",
                "priority": "high",
                "estimated_time": action.get("estimated_time", ""),
                "steps": action.get("steps", []),
                "completed": False,
                "completed_at": None
            })
        
        # Medium Term
        for action in plan.get("medium_term", {}).get("actions", []):
            items.append({
                "id": action.get("id", hashlib.md5(action["title"].encode()).hexdigest()[:8]),
                "title": action["title"],
                "description": action.get("description", ""),
                "category": "medium_term",
                "priority": "medium",
                "estimated_time": action.get("estimated_time", ""),
                "steps": action.get("steps", []),
                "completed": False,
                "completed_at": None
            })
        
        # Long Term
        for action in plan.get("long_term", {}).get("actions", []):
            items.append({
                "id": action.get("id", hashlib.md5(action["title"].encode()).hexdigest()[:8]),
                "title": action["title"],
                "description": action.get("description", ""),
                "category": "long_term",
                "priority": "low",
                "estimated_time": action.get("estimated_time", ""),
                "steps": action.get("steps", []),
                "completed": False,
                "completed_at": None
            })
        
        checklist = {
            "master_agent_id": self.master_agent_id,
            "created_at": datetime.now(timezone.utc),
            "items": items,
            "total_items": len(items),
            "completed_items": 0
        }
        
        # Update sau insert
        self.collection.update_one(
            {"master_agent_id": self.master_agent_id},
            {"$set": checklist},
            upsert=True
        )
        
        return checklist
    
    def get_checklist(self) -> Dict:
        """Returnează checklist-ul curent"""
        checklist = self.collection.find_one({"master_agent_id": self.master_agent_id})
        
        if not checklist:
            return {"items": [], "total_items": 0, "completed_items": 0}
        
        checklist["_id"] = str(checklist["_id"])
        checklist["created_at"] = checklist["created_at"].isoformat() if checklist.get("created_at") else None
        
        # Calculează statistici
        completed = sum(1 for item in checklist.get("items", []) if item.get("completed"))
        checklist["completed_items"] = completed
        checklist["progress_percent"] = int((completed / max(checklist["total_items"], 1)) * 100)
        
        return checklist
    
    def toggle_item(self, item_id: str) -> Dict:
        """Toggle completare item"""
        checklist = self.collection.find_one({"master_agent_id": self.master_agent_id})
        if not checklist:
            raise ValueError("Checklist negăsit")
        
        items = checklist.get("items", [])
        for item in items:
            if item["id"] == item_id:
                item["completed"] = not item["completed"]
                item["completed_at"] = datetime.now(timezone.utc) if item["completed"] else None
                break
        
        self.collection.update_one(
            {"master_agent_id": self.master_agent_id},
            {"$set": {"items": items}}
        )
        
        return {"toggled": True, "item_id": item_id}
    
    def add_custom_item(self, title: str, description: str = "", priority: str = "medium") -> Dict:
        """Adaugă un item custom"""
        item = {
            "id": hashlib.md5(f"{title}{datetime.now()}".encode()).hexdigest()[:8],
            "title": title,
            "description": description,
            "category": "custom",
            "priority": priority,
            "estimated_time": "",
            "steps": [],
            "completed": False,
            "completed_at": None
        }
        
        self.collection.update_one(
            {"master_agent_id": self.master_agent_id},
            {
                "$push": {"items": item},
                "$inc": {"total_items": 1}
            },
            upsert=True
        )
        
        return item


# ============================================================================
# 🤖 AI CONTENT GENERATOR
# ============================================================================

class AIContentGenerator:
    """Generează conținut folosind DeepSeek"""
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        
    def _call_deepseek(self, prompt: str, max_tokens: int = 2000) -> str:
        """Apelează DeepSeek API"""
        import requests
        
        if not self.api_key:
            return "Eroare: DEEPSEEK_API_KEY nu este configurat"
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"Eroare API: {response.status_code}"
        except Exception as e:
            return f"Eroare: {str(e)}"
    
    def generate_page_titles(self, keyword: str, count: int = 5) -> List[str]:
        """Generează titluri pentru pagini noi"""
        master = db.site_agents.find_one({"_id": ObjectId(self.master_agent_id)})
        domain = master.get("domain", "") if master else ""
        industry = master.get("industry", "general") if master else "general"
        
        prompt = f"""Generează {count} titluri SEO-optimizate pentru pagini web despre "{keyword}".

Context:
- Site: {domain}
- Industrie: {industry}
- Limba: Română

Cerințe:
- Titluri între 50-60 caractere
- Include keyword-ul principal
- Atractive pentru click
- Optimizate pentru Google

Returnează doar titlurile, unul pe linie, fără numerotare."""

        response = self._call_deepseek(prompt, 500)
        titles = [t.strip() for t in response.split("\n") if t.strip() and len(t.strip()) > 10]
        return titles[:count]
    
    def generate_meta_description(self, title: str, keyword: str) -> str:
        """Generează meta description optimizată"""
        prompt = f"""Generează o meta description SEO pentru:
Titlu: {title}
Keyword principal: {keyword}

Cerințe:
- Exact 150-160 caractere
- Include keyword-ul
- Call-to-action implicit
- Limba română

Returnează DOAR meta description-ul, nimic altceva."""

        return self._call_deepseek(prompt, 200).strip()
    
    def generate_article_outline(self, topic: str, target_words: int = 1500) -> Dict:
        """Generează outline pentru articol"""
        master = db.site_agents.find_one({"_id": ObjectId(self.master_agent_id)})
        domain = master.get("domain", "") if master else ""
        
        prompt = f"""Creează un outline detaliat pentru un articol despre "{topic}".

Context:
- Site: {domain}
- Lungime țintă: {target_words} cuvinte
- Limba: Română

Structură necesară:
1. Titlu H1 (include keyword)
2. Introducere (hook + ce va învăța cititorul)
3. 4-6 secțiuni H2 cu:
   - Titlu H2
   - 2-3 puncte cheie
   - Sugestie pentru imagine/grafic
4. Concluzie cu CTA

Format JSON:
{{
  "h1": "...",
  "intro_hook": "...",
  "sections": [
    {{"h2": "...", "key_points": [...], "image_suggestion": "..."}}
  ],
  "conclusion_cta": "..."
}}"""

        response = self._call_deepseek(prompt, 1500)
        
        # Încearcă să parseze JSON
        try:
            # Extrage JSON din răspuns
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"raw_outline": response}
    
    def generate_content_ideas(self, gaps: List[str], count: int = 10) -> List[Dict]:
        """Generează idei de conținut bazate pe gaps"""
        master = db.site_agents.find_one({"_id": ObjectId(self.master_agent_id)})
        domain = master.get("domain", "") if master else ""
        industry = master.get("industry", "general") if master else "general"
        
        gaps_text = ", ".join(gaps[:10])
        
        prompt = f"""Bazat pe aceste gap-uri identificate în analiza competitivă: {gaps_text}

Context:
- Site: {domain}
- Industrie: {industry}

Generează {count} idei de conținut cu:
1. Titlu articol/pagină
2. Tip conținut (articol blog, pagină serviciu, ghid, FAQ, etc.)
3. Keywords țintă (2-3)
4. Prioritate (high/medium/low)
5. Estimare efort (ore)

Format JSON array:
[{{"title": "...", "type": "...", "keywords": [...], "priority": "...", "effort_hours": X}}]"""

        response = self._call_deepseek(prompt, 2000)
        
        try:
            import re
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return [{"raw_ideas": response}]


# ============================================================================
# 💰 ROI CALCULATOR
# ============================================================================

class ROICalculator:
    """Calculează ROI pentru acțiuni"""
    
    # Estimări bazate pe industrie (valori medii)
    TRAFFIC_VALUE_PER_VISITOR = 2.5  # RON per vizitator organic
    CONVERSION_RATE = 0.02  # 2% conversie medie
    AVG_ORDER_VALUE = 500  # RON valoare medie comandă
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        
    def calculate_keyword_roi(self, keyword: str, estimated_position: int = 5) -> Dict:
        """Calculează ROI potențial pentru un keyword"""
        # Estimări CTR bazate pe poziție
        ctr_by_position = {
            1: 0.28, 2: 0.15, 3: 0.11, 4: 0.08, 5: 0.06,
            6: 0.05, 7: 0.04, 8: 0.03, 9: 0.03, 10: 0.02
        }
        
        # Estimare volum căutări (simplificat)
        estimated_monthly_searches = 500  # Valoare default
        
        ctr = ctr_by_position.get(estimated_position, 0.02)
        monthly_visitors = int(estimated_monthly_searches * ctr)
        monthly_value = monthly_visitors * self.TRAFFIC_VALUE_PER_VISITOR
        monthly_conversions = monthly_visitors * self.CONVERSION_RATE
        monthly_revenue = monthly_conversions * self.AVG_ORDER_VALUE
        
        return {
            "keyword": keyword,
            "estimated_position": estimated_position,
            "monthly_searches": estimated_monthly_searches,
            "ctr": f"{ctr*100:.1f}%",
            "monthly_visitors": monthly_visitors,
            "traffic_value": f"{monthly_value:.0f} RON",
            "potential_conversions": f"{monthly_conversions:.1f}",
            "potential_revenue": f"{monthly_revenue:.0f} RON",
            "yearly_potential": f"{monthly_revenue * 12:.0f} RON"
        }
    
    def calculate_action_roi(self, action: Dict) -> Dict:
        """Calculează ROI pentru o acțiune din plan"""
        # Estimări bazate pe tipul acțiunii
        impact_multipliers = {
            "HIGH": 3.0,
            "MEDIUM": 1.5,
            "LOW": 0.5
        }
        
        effort_costs = {
            "1-2 ore": 200,
            "2-4 ore": 400,
            "3-5 zile": 2000,
            "1-3 luni": 10000
        }
        
        impact = action.get("impact", "MEDIUM")
        effort = action.get("estimated_time", "2-4 ore")
        
        multiplier = impact_multipliers.get(impact, 1.0)
        cost = effort_costs.get(effort, 500)
        
        # Estimare beneficiu
        base_benefit = 1000  # RON/lună valoare de bază
        monthly_benefit = base_benefit * multiplier
        yearly_benefit = monthly_benefit * 12
        
        roi_percent = ((yearly_benefit - cost) / cost) * 100 if cost > 0 else 0
        payback_months = cost / monthly_benefit if monthly_benefit > 0 else 999
        
        return {
            "action_title": action.get("title", ""),
            "estimated_cost": f"{cost} RON",
            "monthly_benefit": f"{monthly_benefit:.0f} RON",
            "yearly_benefit": f"{yearly_benefit:.0f} RON",
            "roi_percent": f"{roi_percent:.0f}%",
            "payback_months": f"{payback_months:.1f} luni",
            "recommendation": "✅ Recomandată" if roi_percent > 100 else "⚠️ Evaluează cu atenție"
        }
    
    def calculate_total_plan_roi(self, plan: Dict) -> Dict:
        """Calculează ROI total pentru întregul plan"""
        total_cost = 0
        total_yearly_benefit = 0
        actions_roi = []
        
        all_actions = (
            plan.get("quick_wins", {}).get("actions", []) +
            plan.get("medium_term", {}).get("actions", []) +
            plan.get("long_term", {}).get("actions", [])
        )
        
        for action in all_actions:
            roi = self.calculate_action_roi(action)
            actions_roi.append(roi)
            
            # Extrage valori numerice
            cost = int(roi["estimated_cost"].replace(" RON", "").replace(",", ""))
            benefit = int(roi["yearly_benefit"].replace(" RON", "").replace(",", ""))
            
            total_cost += cost
            total_yearly_benefit += benefit
        
        total_roi = ((total_yearly_benefit - total_cost) / total_cost) * 100 if total_cost > 0 else 0
        
        return {
            "total_actions": len(all_actions),
            "total_investment": f"{total_cost:,} RON",
            "total_yearly_benefit": f"{total_yearly_benefit:,} RON",
            "total_roi": f"{total_roi:.0f}%",
            "net_benefit": f"{total_yearly_benefit - total_cost:,} RON",
            "actions_breakdown": actions_roi
        }


# ============================================================================
# 👥 COMPETITOR WATCHLIST
# ============================================================================

class CompetitorWatchlist:
    """Gestionează lista de competitori de urmărit"""
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        self.collection = db.competitor_watchlist
        
    def add_to_watchlist(self, competitor_domain: str, notes: str = "") -> Dict:
        """Adaugă competitor în watchlist"""
        # Găsește competitorul
        competitor = db.site_agents.find_one({
            "master_agent_id": ObjectId(self.master_agent_id),
            "domain": {"$regex": competitor_domain, "$options": "i"}
        })
        
        if not competitor:
            raise ValueError(f"Competitorul {competitor_domain} nu a fost găsit")
        
        entry = {
            "master_agent_id": self.master_agent_id,
            "competitor_id": str(competitor["_id"]),
            "domain": competitor.get("domain"),
            "notes": notes,
            "added_at": datetime.now(timezone.utc),
            "snapshots": [{
                "date": datetime.now(timezone.utc),
                "pages": competitor.get("pages_indexed", 0),
                "chunks": competitor.get("chunks_indexed", 0),
                "keywords": len(competitor.get("keywords", []))
            }]
        }
        
        self.collection.update_one(
            {
                "master_agent_id": self.master_agent_id,
                "competitor_id": str(competitor["_id"])
            },
            {"$set": entry},
            upsert=True
        )
        
        return entry
    
    def get_watchlist(self) -> List[Dict]:
        """Returnează watchlist-ul"""
        watchlist = list(self.collection.find({
            "master_agent_id": self.master_agent_id
        }))
        
        for item in watchlist:
            item["_id"] = str(item["_id"])
            item["added_at"] = item["added_at"].isoformat() if item.get("added_at") else None
            
            # Obține date actuale
            competitor = db.site_agents.find_one({"_id": ObjectId(item["competitor_id"])})
            if competitor:
                current = {
                    "pages": competitor.get("pages_indexed", 0),
                    "chunks": competitor.get("chunks_indexed", 0),
                    "keywords": len(competitor.get("keywords", []))
                }
                item["current"] = current
                
                # Compară cu primul snapshot
                if item.get("snapshots"):
                    first = item["snapshots"][0]
                    item["changes"] = {
                        "pages": current["pages"] - first.get("pages", 0),
                        "chunks": current["chunks"] - first.get("chunks", 0),
                        "keywords": current["keywords"] - first.get("keywords", 0)
                    }
        
        return watchlist
    
    def remove_from_watchlist(self, competitor_domain: str) -> Dict:
        """Elimină competitor din watchlist"""
        result = self.collection.delete_one({
            "master_agent_id": self.master_agent_id,
            "domain": {"$regex": competitor_domain, "$options": "i"}
        })
        
        return {"removed": result.deleted_count > 0}
    
    def get_leaderboard(self) -> List[Dict]:
        """Returnează leaderboard-ul competitorilor"""
        from business_intelligence import PositioningScorer
        
        master = db.site_agents.find_one({"_id": ObjectId(self.master_agent_id)})
        competitors = list(db.site_agents.find({
            "master_agent_id": ObjectId(self.master_agent_id)
        }))
        
        scorer = PositioningScorer(self.master_agent_id)
        
        leaderboard = []
        
        # Adaugă master-ul
        if master:
            master_score = scorer.calculate_score()
            leaderboard.append({
                "domain": master.get("domain"),
                "is_you": True,
                "score": master_score.get("score", 0),
                "pages": master.get("pages_indexed", 0),
                "keywords": len(master.get("keywords", [])),
                "chunks": master.get("chunks_indexed", 0)
            })
        
        # Adaugă competitorii
        for comp in competitors:
            comp_score = scorer._calculate_competitor_score(comp, competitors)
            leaderboard.append({
                "domain": comp.get("domain"),
                "is_you": False,
                "score": comp_score,
                "pages": comp.get("pages_indexed", 0),
                "keywords": len(comp.get("keywords", [])),
                "chunks": comp.get("chunks_indexed", 0)
            })
        
        # Sortează după scor
        leaderboard.sort(key=lambda x: x["score"], reverse=True)
        
        # Adaugă poziții
        for i, entry in enumerate(leaderboard):
            entry["position"] = i + 1
            entry["medal"] = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else ""
        
        return leaderboard


# ============================================================================
# 📧 NOTIFICATION SYSTEM
# ============================================================================

class NotificationSystem:
    """Sistem de notificări"""
    
    def __init__(self, master_agent_id: str):
        self.master_agent_id = master_agent_id
        self.collection = db.notifications
        self.settings_collection = db.notification_settings
        
    def create_notification(self, 
                          notification_type: str, 
                          title: str, 
                          message: str, 
                          severity: str = "info",
                          data: Dict = None) -> Dict:
        """Creează o notificare nouă"""
        notification = {
            "master_agent_id": self.master_agent_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "severity": severity,  # info, warning, critical, success
            "data": data or {},
            "read": False,
            "created_at": datetime.now(timezone.utc)
        }
        
        result = self.collection.insert_one(notification)
        notification["_id"] = str(result.inserted_id)
        
        return notification
    
    def get_notifications(self, unread_only: bool = False, limit: int = 50) -> List[Dict]:
        """Returnează notificările"""
        query = {"master_agent_id": self.master_agent_id}
        if unread_only:
            query["read"] = False
        
        notifications = list(
            self.collection.find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        
        for n in notifications:
            n["_id"] = str(n["_id"])
            n["created_at"] = n["created_at"].isoformat() if n.get("created_at") else None
        
        return notifications
    
    def mark_as_read(self, notification_id: str = None) -> Dict:
        """Marchează notificările ca citite"""
        if notification_id:
            self.collection.update_one(
                {"_id": ObjectId(notification_id)},
                {"$set": {"read": True}}
            )
        else:
            # Marchează toate
            self.collection.update_many(
                {"master_agent_id": self.master_agent_id},
                {"$set": {"read": True}}
            )
        
        return {"marked": True}
    
    def get_unread_count(self) -> int:
        """Returnează numărul de notificări necitite"""
        return self.collection.count_documents({
            "master_agent_id": self.master_agent_id,
            "read": False
        })
    
    def check_and_create_alerts(self) -> List[Dict]:
        """Verifică condiții și creează alerte automate"""
        from business_intelligence import PositioningScorer, CompetitorAlertSystem
        
        alerts_created = []
        
        # Verifică scorul
        scorer = PositioningScorer(self.master_agent_id)
        score = scorer.calculate_score()
        
        # Alertă pentru scor scăzut
        if score.get("score", 100) < 30:
            alert = self.create_notification(
                "score_alert",
                "⚠️ Scor poziționare scăzut",
                f"Scorul tău de poziționare este {score.get('score')}/100. Verifică planul de acțiune.",
                "warning"
            )
            alerts_created.append(alert)
        
        # Verifică alerte competitori
        alert_system = CompetitorAlertSystem(self.master_agent_id)
        comp_alerts = alert_system.check_alerts()
        
        for ca in comp_alerts:
            if ca.get("severity") in ["CRITICAL", "WARNING"]:
                alert = self.create_notification(
                    "competitor_alert",
                    ca.get("title"),
                    ca.get("message"),
                    ca.get("severity").lower(),
                    ca
                )
                alerts_created.append(alert)
        
        return alerts_created
    
    def save_settings(self, settings: Dict) -> Dict:
        """Salvează setările de notificări"""
        self.settings_collection.update_one(
            {"master_agent_id": self.master_agent_id},
            {"$set": {
                "master_agent_id": self.master_agent_id,
                "email": settings.get("email"),
                "webhook_url": settings.get("webhook_url"),
                "email_enabled": settings.get("email_enabled", False),
                "webhook_enabled": settings.get("webhook_enabled", False),
                "alert_types": settings.get("alert_types", ["critical", "warning"]),
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        
        return {"saved": True}
    
    def get_settings(self) -> Dict:
        """Returnează setările de notificări"""
        settings = self.settings_collection.find_one({
            "master_agent_id": self.master_agent_id
        })
        
        if settings:
            settings["_id"] = str(settings["_id"])
            return settings
        
        return {
            "email": "",
            "webhook_url": "",
            "email_enabled": False,
            "webhook_enabled": False,
            "alert_types": ["critical", "warning"]
        }


# Export
__all__ = [
    'TrendTracker',
    'GoalTracker',
    'ActionChecklist',
    'AIContentGenerator',
    'ROICalculator',
    'CompetitorWatchlist',
    'NotificationSystem'
]

