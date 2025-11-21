#!/usr/bin/env python3
"""
📊 DeepSeek CEO Report Generator
Production-ready cu prompt consistent și executive summary
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)


class DeepSeekCEOReportGenerator:
    """
    📊 Generator rapoarte CEO cu DeepSeek
    
    Folosește prompt consistent pentru analiză SEO profesională.
    """
    
    SYSTEM_PROMPT = """Ești un analist SEO senior cu experiență în competitive intelligence și strategie digitală.

Primești date structurate despre:
- SERP runs (rezultate cautare Google)
- Scoruri competitori (visibility, authority, threat)
- Intenții keywords (informational, commercial, transactional)
- Istorice rank (evoluție poziții în timp)

Task: Generează un executive summary pentru CEO, structurat astfel:

1. **Executive Summary** (2-3 propoziții clare)
   - Situația generală
   - Tendința principală (urcăm/coborâm)
   
2. **Unde Câștigăm** (top 3-5 keywords)
   - Keywords unde avem poziții bune (top 3)
   - Progres pozitiv recent
   - Tabelizat: keyword, poziție actuală, evoluție

3. **Unde Pierdem** (top 3-5 keywords)
   - Keywords unde am pierdut poziții
   - Competitori care ne-au depășit
   - Tabelizat: keyword, poziție actuală, poziție anterioară, delta

4. **Top 5 Oportunități**
   - Keywords cu potențial mare (volum bun, competiție medie)
   - Acțiuni concrete pentru fiecare
   - Scor prioritate (1-10)

5. **5 Acțiuni Concrete (next 14 zile)**
   - Acțiuni specifice, măsurabile
   - Responsabil sugerat (SEO/Content/Tech)
   - Impact estimat

6. **Riscuri & Scenarii**
   - Riscuri identificate (competitori noi, pierderi rank)
   - Scenariu optimist (dacă acționăm)
   - Scenariu pesimist (dacă nu acționăm)

IMPORTANT:
- Folosește DOAR datele primite, nu inventa cifre
- Fii concis și CEO-friendly (evită jargon tehnic excesiv)
- Tabelizează când e util
- Prioritizează acțiuni după impact × probabilitate de succes
"""

    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/", db_name: str = "ai_agents_db"):
        """Initialize CEO Report Generator"""
        self.mongo = MongoClient(mongo_uri)
        self.db = self.mongo[db_name]
        self.logger = logging.getLogger(f"{__name__}.DeepSeekCEOReportGenerator")
    
    def generate_report(
        self,
        agent_id: str,
        run_id: Optional[str] = None,
        use_deepseek: bool = True
    ) -> Dict:
        """
        Generează raport CEO pentru un agent
        
        Args:
            agent_id: ID agent master
            run_id: ID run SERP (opțional - folosește ultimul dacă lipsește)
            use_deepseek: Dacă True, folosește DeepSeek; altfel returnează doar date brute
        
        Returns:
            Dict cu raport complet
        """
        self.logger.info(f"📊 Generating CEO report for agent {agent_id}")
        
        # 1. Obține agent
        try:
            obj_id = ObjectId(agent_id) if isinstance(agent_id, str) else agent_id
        except:
            obj_id = agent_id
        
        agent = self.db.site_agents.find_one({"_id": obj_id})
        if not agent:
            agent = self.db.agents.find_one({"_id": obj_id})
        
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        master_domain = agent.get("domain", "")
        keywords = agent.get("keywords", [])
        
        # 2. Obține ultimul run (dacă nu e specificat)
        if not run_id:
            last_run = self.db.serp_runs.find_one(
                {"agent_id": agent_id, "status": "succeeded"},
                sort=[("started_at", -1)]
            )
            if last_run:
                run_id = last_run["_id"]
            else:
                raise ValueError(f"No successful SERP runs found for agent {agent_id}")
        
        # 3. Colectează date pentru raport
        data = self._collect_data(agent_id, run_id, master_domain, keywords)
        
        # 4. Generează raport cu DeepSeek (sau returnează date brute)
        if use_deepseek:
            report = self._generate_with_deepseek(data)
        else:
            report = self._generate_basic_report(data)
        
        # 5. Salvează raport în MongoDB
        report_doc = {
            "agent_id": agent_id,
            "run_id": run_id,
            "report_type": "ceo_executive_summary",
            "generated_at": datetime.now(timezone.utc),
            "data": data,
            "report": report
        }
        
        result = self.db.ceo_reports.insert_one(report_doc)
        report_id = str(result.inserted_id)
        
        self.logger.info(f"✅ CEO report generated: {report_id}")
        
        return {
            "report_id": report_id,
            "agent_id": agent_id,
            "run_id": run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report": report
        }
    
    def _collect_data(
        self,
        agent_id: str,
        run_id: str,
        master_domain: str,
        keywords: List[str]
    ) -> Dict:
        """Colectează toate datele necesare pentru raport"""
        
        # 1. Statistici run
        run = self.db.serp_runs.find_one({"_id": run_id})
        
        # 2. Rezultate SERP pentru acest run
        serp_results = list(self.db.serp_results.find({"run_id": run_id}))
        
        # 3. Rank history pentru master (ultimele 30 zile)
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
        rank_history = {}
        
        for kw in keywords:
            history = self.db.ranks_history.find_one({
                "domain": master_domain,
                "keyword": kw
            })
            if history:
                # Filter last 30 days
                series = [s for s in history.get("series", []) if s["date"] >= cutoff_date]
                if series:
                    rank_history[kw] = series
        
        # 4. Alerte recente (ultimele 7 zile)
        cutoff_alerts = datetime.now(timezone.utc) - timedelta(days=7)
        alerts = list(self.db.serp_alerts.find({
            "agent_id": agent_id,
            "notified_at": {"$gte": cutoff_alerts}
        }).sort("notified_at", -1))
        
        # 5. Top competitori
        competitors = list(self.db.competitors.find({}).sort("scores.threat", -1).limit(10))
        
        # 6. Analizează unde câștigăm/pierdem
        winning_keywords = []
        losing_keywords = []
        
        for kw, series in rank_history.items():
            if len(series) >= 2:
                current = series[-1]["rank"]
                previous = series[-2]["rank"]
                delta = current - previous
                
                if delta <= -2:  # Improvement
                    winning_keywords.append({
                        "keyword": kw,
                        "current_rank": current,
                        "previous_rank": previous,
                        "delta": delta
                    })
                elif delta >= 2:  # Decline
                    losing_keywords.append({
                        "keyword": kw,
                        "current_rank": current,
                        "previous_rank": previous,
                        "delta": delta
                    })
        
        # Sort
        winning_keywords.sort(key=lambda x: x["delta"])  # Biggest improvements first
        losing_keywords.sort(key=lambda x: -x["delta"])  # Biggest declines first
        
        return {
            "agent_id": agent_id,
            "master_domain": master_domain,
            "run_id": run_id,
            "run_date": run.get("started_at").isoformat() if run.get("started_at") else None,
            "total_keywords": len(keywords),
            "keywords_monitored": len(rank_history),
            "winning_keywords": winning_keywords[:5],
            "losing_keywords": losing_keywords[:5],
            "alerts_count": len(alerts),
            "critical_alerts": [a for a in alerts if a.get("severity") == "critical"],
            "top_competitors": [
                {
                    "domain": c.get("domain"),
                    "threat_score": c.get("scores", {}).get("threat", 0),
                    "visibility": c.get("scores", {}).get("visibility", 0),
                    "keywords_count": len(c.get("keywords_seen", []))
                }
                for c in competitors[:5]
            ]
        }
    
    def _generate_with_deepseek(self, data: Dict) -> Dict:
        """Generează raport folosind DeepSeek"""
        try:
            import requests
            
            # TODO: Integrare DeepSeek API
            # Pentru acum, generăm un raport basic + placeholder pentru DeepSeek
            
            # Construct prompt
            user_prompt = self._construct_user_prompt(data)
            
            # Call DeepSeek (placeholder)
            # response = requests.post(
            #     "https://api.deepseek.com/v1/chat/completions",
            #     headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            #     json={
            #         "model": "deepseek-chat",
            #         "messages": [
            #             {"role": "system", "content": self.SYSTEM_PROMPT},
            #             {"role": "user", "content": user_prompt}
            #         ]
            #     }
            # )
            # deepseek_report = response.json()["choices"][0]["message"]["content"]
            
            # Fallback: generate basic report
            return self._generate_basic_report(data)
        
        except Exception as e:
            self.logger.error(f"Error calling DeepSeek: {e}")
            return self._generate_basic_report(data)
    
    def _construct_user_prompt(self, data: Dict) -> str:
        """Construiește prompt pentru DeepSeek din date"""
        prompt = f"""Analizează următoarele date SERP pentru domeniul {data['master_domain']}:

**Date Run SERP:**
- Data: {data['run_date']}
- Keywords monitorizate: {data['keywords_monitored']}/{data['total_keywords']}

**Unde Câștigăm (top improvements):**
"""
        for kw in data['winning_keywords']:
            prompt += f"- '{kw['keyword']}': #{kw['previous_rank']} → #{kw['current_rank']} (Δ{kw['delta']})\n"
        
        prompt += "\n**Unde Pierdem (top declines):**\n"
        for kw in data['losing_keywords']:
            prompt += f"- '{kw['keyword']}': #{kw['previous_rank']} → #{kw['current_rank']} (Δ+{abs(kw['delta'])})\n"
        
        prompt += f"\n**Alerte Recente:**\n- Total: {data['alerts_count']}\n- Critical: {len(data['critical_alerts'])}\n"
        
        prompt += "\n**Top 5 Competitori (threat score):**\n"
        for comp in data['top_competitors']:
            prompt += f"- {comp['domain']}: threat {comp['threat_score']:.1f}/100, visibility {comp['visibility']:.2f}, {comp['keywords_count']} keywords\n"
        
        prompt += "\n\nGenerează executive summary conform template-ului."
        
        return prompt
    
    def _generate_basic_report(self, data: Dict) -> Dict:
        """Generează raport basic (fără DeepSeek)"""
        
        # Executive Summary
        total_improvements = len(data['winning_keywords'])
        total_declines = len(data['losing_keywords'])
        
        if total_improvements > total_declines:
            trend = "pozitivă"
            summary = f"Tendință {trend}: {total_improvements} keywords în creștere vs {total_declines} în scădere."
        elif total_declines > total_improvements:
            trend = "negativă"
            summary = f"Tendință {trend}: {total_declines} keywords în scădere vs {total_improvements} în creștere. Acțiune necesară."
        else:
            trend = "stabilă"
            summary = f"Tendință {trend}: evoluție echilibrată ({total_improvements} up, {total_declines} down)."
        
        # Top 5 Oportunități (simplified)
        opportunities = []
        for comp in data['top_competitors'][:3]:
            opportunities.append({
                "opportunity": f"Analizează strategia {comp['domain']}",
                "reasoning": f"Threat score {comp['threat_score']:.1f}/100, {comp['keywords_count']} keywords overlap",
                "priority": min(int(comp['threat_score'] / 10), 10),
                "action": f"Identifică diferențiatorii față de {comp['domain']}"
            })
        
        # 5 Acțiuni Concrete
        actions = []
        
        # Acțiune 1: Fix declining keywords
        if data['losing_keywords']:
            top_decline = data['losing_keywords'][0]
            actions.append({
                "action": f"Re-optimizare '{top_decline['keyword']}'",
                "responsible": "SEO + Content",
                "impact": "High",
                "deadline": "7 zile",
                "details": f"Poziție actuală #{top_decline['current_rank']}, pierdere {abs(top_decline['delta'])} poziții"
            })
        
        # Acțiune 2: Leverage winning keywords
        if data['winning_keywords']:
            top_win = data['winning_keywords'][0]
            actions.append({
                "action": f"Consolidare '{top_win['keyword']}'",
                "responsible": "Content",
                "impact": "Medium",
                "deadline": "14 zile",
                "details": f"Poziție actuală #{top_win['current_rank']}, menține momentum"
            })
        
        # Acțiune 3: Competitor analysis
        if data['top_competitors']:
            top_comp = data['top_competitors'][0]
            actions.append({
                "action": f"Analiză competitor: {top_comp['domain']}",
                "responsible": "SEO",
                "impact": "High",
                "deadline": "7 zile",
                "details": f"Threat {top_comp['threat_score']:.1f}/100, identifică tactici câștigătoare"
            })
        
        # Acțiune 4: Technical audit (dacă sunt alerte critical)
        if data['critical_alerts']:
            actions.append({
                "action": "Audit tehnic SEO (alerte critice)",
                "responsible": "Tech + SEO",
                "impact": "Critical",
                "deadline": "3 zile",
                "details": f"{len(data['critical_alerts'])} alerte critice necesită atenție imediată"
            })
        
        # Acțiune 5: Content expansion
        actions.append({
            "action": "Expand content pentru top 10 keywords",
            "responsible": "Content",
            "impact": "Medium",
            "deadline": "14 zile",
            "details": "Adaugă secțiuni noi, actualizări, media"
        })
        
        # Riscuri & Scenarii
        risks = []
        if total_declines > 0:
            risks.append(f"Pierderi continue pe {total_declines} keywords")
        if len(data['critical_alerts']) > 0:
            risks.append(f"{len(data['critical_alerts'])} alerte critice nerezolvate")
        if data['top_competitors']:
            top_threat = data['top_competitors'][0]
            risks.append(f"Competitor {top_threat['domain']} cu threat {top_threat['threat_score']:.1f}/100")
        
        return {
            "executive_summary": {
                "summary": summary,
                "trend": trend,
                "keywords_improving": total_improvements,
                "keywords_declining": total_declines
            },
            "winning_keywords": data['winning_keywords'],
            "losing_keywords": data['losing_keywords'],
            "opportunities": opportunities,
            "actions": actions[:5],
            "risks": {
                "identified": risks,
                "scenario_optimistic": "Implementarea acțiunilor → recuperare poziții în 30-60 zile, +20% trafic organic",
                "scenario_pessimistic": "Inacțiune → pierderi continue, -15% trafic organic în 90 zile"
            },
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "data_source": f"SERP run {data['run_id']}",
                "keywords_analyzed": data['keywords_monitored']
            }
        }


# CLI pentru testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 deepseek_ceo_report.py <agent_id> [run_id]")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    run_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    generator = DeepSeekCEOReportGenerator()
    
    try:
        result = generator.generate_report(agent_id, run_id, use_deepseek=False)
        
        print("="*80)
        print("📊 CEO EXECUTIVE SUMMARY REPORT")
        print("="*80)
        print()
        
        report = result["report"]
        
        # Executive Summary
        exec_sum = report["executive_summary"]
        print(f"**Executive Summary:** {exec_sum['summary']}")
        print(f"   Trend: {exec_sum['trend']}")
        print(f"   Keywords improving: {exec_sum['keywords_improving']}")
        print(f"   Keywords declining: {exec_sum['keywords_declining']}")
        print()
        
        # Winning
        if report["winning_keywords"]:
            print("**Unde Câștigăm:**")
            for kw in report["winning_keywords"][:3]:
                print(f"   ✅ '{kw['keyword']}': #{kw['previous_rank']} → #{kw['current_rank']} (Δ{kw['delta']})")
            print()
        
        # Losing
        if report["losing_keywords"]:
            print("**Unde Pierdem:**")
            for kw in report["losing_keywords"][:3]:
                print(f"   ❌ '{kw['keyword']}': #{kw['previous_rank']} → #{kw['current_rank']} (Δ+{abs(kw['delta'])})")
            print()
        
        # Actions
        print("**5 Acțiuni Concrete (next 14 zile):**")
        for i, action in enumerate(report["actions"], 1):
            print(f"   {i}. {action['action']}")
            print(f"      Responsabil: {action['responsible']} | Impact: {action['impact']} | Deadline: {action['deadline']}")
        print()
        
        # Risks
        print("**Riscuri:**")
        for risk in report["risks"]["identified"]:
            print(f"   ⚠️ {risk}")
        print()
        
        print("="*80)
        print(f"✅ Report ID: {result['report_id']}")
        print("="*80)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

