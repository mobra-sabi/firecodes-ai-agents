#!/usr/bin/env python3
"""
🔍 CONTENT GAP ANALYZER - SEO Intelligence v2.0

Identifică ce au competitorii și tu nu:
- Sub-teme neacoperite
- Tipuri de content lipsă (ghiduri, FAQ, case studies)
- Întrebări din People Also Ask neacoperite
- Content roadmap prioritizat

Folosește Qwen pentru comparație semantică
"""

import os
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

import logging
from typing import Dict, List, Any
from datetime import datetime, timezone
import json
import re
from pymongo import MongoClient
from collections import Counter

from llm_orchestrator import get_orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentGapAnalyzer:
    """
    Analizează gaps în content strategy vs competitori
    """
    
    def __init__(self):
        self.llm = get_orchestrator()
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        
        logger.info("✅ Content Gap Analyzer initialized")
    
    def analyze_gaps(
        self,
        master_content: Dict,
        competitor_contents: List[Dict],
        keywords: List[str] = None
    ) -> Dict:
        """
        Analizează gaps între master site și competitori
        
        Args:
            master_content: Content de pe site-ul master
            competitor_contents: List de content de la competitori
            keywords: Optional - keywords pentru context
        
        Returns:
            Dict cu gap analysis și content roadmap
        """
        logger.info(f"🔍 Analyzing content gaps vs {len(competitor_contents)} competitors")
        
        try:
            # 1. Identifică missing subtopics
            missing_subtopics = self._find_missing_subtopics(
                master_content,
                competitor_contents
            )
            
            # 2. Identifică missing content types
            missing_content_types = self._find_missing_content_types(
                master_content,
                competitor_contents
            )
            
            # 3. Extrage unanswered questions
            unanswered_questions = self._extract_unanswered_questions(
                master_content,
                competitor_contents,
                keywords
            )
            
            # 4. Generează content roadmap
            content_roadmap = self._generate_content_roadmap(
                missing_subtopics,
                missing_content_types,
                unanswered_questions
            )
            
            result = {
                "master_domain": master_content.get("domain", "N/A"),
                "competitors_analyzed": len(competitor_contents),
                "missing_subtopics": missing_subtopics,
                "missing_content_types": missing_content_types,
                "unanswered_questions": unanswered_questions,
                "content_roadmap": content_roadmap,
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Save în MongoDB
            self._save_analysis(master_content.get("domain"), result)
            
            logger.info(f"✅ Gap analysis complete:")
            logger.info(f"   - {len(missing_subtopics)} missing subtopics")
            logger.info(f"   - {len(missing_content_types)} missing content types")
            logger.info(f"   - {len(unanswered_questions)} unanswered questions")
            logger.info(f"   - {len(content_roadmap)} content recommendations")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error analyzing gaps: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _find_missing_subtopics(
        self,
        master_content: Dict,
        competitor_contents: List[Dict]
    ) -> List[Dict]:
        """
        Identifică sub-teme pe care competitorii le au și master nu
        """
        # Extract topics from master
        master_topics = set()
        for page in master_content.get("pages", []):
            title = page.get("title", "").lower()
            content = page.get("content", "").lower()
            
            # Extract key phrases (simple approach)
            words = re.findall(r'\b\w{4,}\b', title + " " + content)
            master_topics.update(words)
        
        # Extract topics from competitors
        competitor_topics = Counter()
        competitor_topics_detail = {}
        
        for comp in competitor_contents:
            comp_domain = comp.get("domain", "unknown")
            comp_topics = set()
            
            for page in comp.get("pages", []):
                title = page.get("title", "").lower()
                content = page.get("content", "").lower()
                
                words = re.findall(r'\b\w{4,}\b', title + " " + content)
                comp_topics.update(words)
            
            # Topics that competitor has but master doesn't
            unique_to_comp = comp_topics - master_topics
            
            for topic in unique_to_comp:
                competitor_topics[topic] += 1
                if topic not in competitor_topics_detail:
                    competitor_topics_detail[topic] = []
                competitor_topics_detail[topic].append(comp_domain)
        
        # Filter pentru topics care apar la multiple competitors = important
        missing = []
        for topic, count in competitor_topics.most_common(20):
            if count >= 2:  # Apare la cel puțin 2 competitori
                missing.append({
                    "topic": topic,
                    "competitors_covering": count,
                    "competitor_domains": competitor_topics_detail[topic][:3],
                    "opportunity_score": min(count / len(competitor_contents), 1.0),
                    "recommended_content_type": self._suggest_content_type(topic)
                })
        
        return missing
    
    def _find_missing_content_types(
        self,
        master_content: Dict,
        competitor_contents: List[Dict]
    ) -> Dict:
        """
        Identifică tipuri de content pe care competitorii le au și master nu
        """
        content_types = {
            "case_studies": ["studiu de caz", "proiect", "realizare", "portofoliu"],
            "faq": ["întrebări", "raspunsuri", "faq", "frequently asked"],
            "guides": ["ghid", "tutorial", "pas cu pas", "cum să"],
            "comparisons": ["comparație", "vs", "versus", "diferența"],
            "pricing": ["preț", "prețuri", "tarif", "cost", "oferta"],
            "testimonials": ["testimonial", "review", "păreri", "experiență client"]
        }
        
        # Check master
        master_has = {ct: 0 for ct in content_types}
        for page in master_content.get("pages", []):
            title = page.get("title", "").lower()
            content = page.get("content", "").lower()
            text = title + " " + content
            
            for ct, keywords in content_types.items():
                if any(kw in text for kw in keywords):
                    master_has[ct] += 1
        
        # Check competitors
        competitors_have = {ct: [] for ct in content_types}
        for comp in competitor_contents:
            comp_domain = comp.get("domain", "unknown")
            
            for page in comp.get("pages", []):
                title = page.get("title", "").lower()
                content = page.get("content", "").lower()
                text = title + " " + content
                
                for ct, keywords in content_types.items():
                    if any(kw in text for kw in keywords):
                        if comp_domain not in competitors_have[ct]:
                            competitors_have[ct].append(comp_domain)
        
        # Find gaps
        missing = {}
        for ct in content_types:
            comp_count = len(competitors_have[ct])
            master_count = master_has[ct]
            
            if comp_count > 0 and master_count == 0:
                impact = "HIGH" if comp_count >= 3 else "MEDIUM" if comp_count >= 2 else "LOW"
                
                missing[ct] = {
                    "competitors_have": comp_count,
                    "you_have": master_count,
                    "impact": impact,
                    "competitor_examples": competitors_have[ct][:3]
                }
        
        return missing
    
    def _extract_unanswered_questions(
        self,
        master_content: Dict,
        competitor_contents: List[Dict],
        keywords: List[str] = None
    ) -> List[str]:
        """
        Extrage întrebări comune pe care competitorii le răspund dar master nu
        
        De asemenea generează întrebări relevante bazate pe keywords
        """
        questions = []
        
        # Extract from competitor content
        for comp in competitor_contents:
            for page in comp.get("pages", []):
                content = page.get("content", "")
                title = page.get("title", "")
                
                # Find questions in content
                found_questions = re.findall(
                    r'[CcDdSs][eu][m cât de ce].*?\?',
                    content + " " + title
                )
                questions.extend(found_questions)
        
        # Deduplicate și clean
        unique_questions = list(set(q.strip() for q in questions if len(q) > 10))
        
        # Check dacă master răspunde la acestea
        master_text = " ".join(
            p.get("content", "") + " " + p.get("title", "")
            for p in master_content.get("pages", [])
        ).lower()
        
        unanswered = []
        for q in unique_questions[:20]:  # Top 20
            # Check dacă întrebarea sau cuvinte cheie din ea apar în master
            q_keywords = set(re.findall(r'\b\w{4,}\b', q.lower()))
            overlap = sum(1 for kw in q_keywords if kw in master_text)
            
            # Dacă overlap < 30%, probabil nu răspunde
            if overlap / len(q_keywords) < 0.3 if q_keywords else True:
                unanswered.append(q)
        
        # Generate additional questions from keywords
        if keywords:
            for kw in keywords[:10]:
                generated = self._generate_questions_for_keyword(kw)
                unanswered.extend(generated)
        
        return unanswered[:15]  # Return top 15
    
    def _generate_questions_for_keyword(self, keyword: str) -> List[str]:
        """
        Generează întrebări comune pentru un keyword
        """
        question_templates = [
            f"Cât costă {keyword}?",
            f"Cum funcționează {keyword}?",
            f"Ce este {keyword}?",
            f"De ce am nevoie de {keyword}?",
            f"Cum aleg {keyword}?"
        ]
        
        return question_templates[:2]  # Return 2 per keyword
    
    def _generate_content_roadmap(
        self,
        missing_subtopics: List[Dict],
        missing_content_types: Dict,
        unanswered_questions: List[str]
    ) -> List[Dict]:
        """
        Generează content roadmap prioritizat
        """
        roadmap = []
        priority = 1
        
        # HIGH PRIORITY: Missing content types with HIGH impact
        for ct, info in missing_content_types.items():
            if info.get("impact") == "HIGH":
                roadmap.append({
                    "priority": priority,
                    "title": self._generate_content_title(ct),
                    "type": ct,
                    "reason": f"{info['competitors_have']} competitori au acest tip de content",
                    "estimated_impact": "HIGH",
                    "target_keywords": []
                })
                priority += 1
        
        # MEDIUM PRIORITY: Top missing subtopics
        for subtopic in missing_subtopics[:5]:
            roadmap.append({
                "priority": priority,
                "title": self._generate_content_title_from_topic(subtopic["topic"]),
                "type": subtopic["recommended_content_type"],
                "reason": f"Topic găsit la {subtopic['competitors_covering']} competitori",
                "estimated_impact": "MEDIUM",
                "target_keywords": [subtopic["topic"]]
            })
            priority += 1
        
        # LOW PRIORITY: FAQ pages pentru unanswered questions
        if unanswered_questions:
            roadmap.append({
                "priority": priority,
                "title": "FAQ: Întrebări frecvente despre protecție la foc",
                "type": "faq",
                "reason": f"{len(unanswered_questions)} întrebări neacoperite",
                "estimated_impact": "MEDIUM",
                "questions_to_answer": unanswered_questions[:10]
            })
        
        return roadmap
    
    def _suggest_content_type(self, topic: str) -> str:
        """
        Sugerează tip de content pentru un topic
        """
        topic_lower = topic.lower()
        
        if any(w in topic_lower for w in ["pret", "cost", "tarif"]):
            return "pricing_guide"
        elif any(w in topic_lower for w in ["cum", "ghid", "tutorial"]):
            return "guide"
        elif any(w in topic_lower for w in ["vs", "comparatie", "diferenta"]):
            return "comparison"
        else:
            return "article"
    
    def _generate_content_title(self, content_type: str) -> str:
        """
        Generează titlu pentru un tip de content
        """
        titles = {
            "case_studies": "Studii de caz: Proiecte de protecție la foc realizate",
            "faq": "Întrebări frecvente despre protecție la foc",
            "guides": "Ghid complet: Protecție la foc pentru clădiri",
            "comparisons": "Comparație: Tipuri de sisteme antiincendiu",
            "pricing": "Prețuri și tarife: Servicii protecție la foc",
            "testimonials": "Păreri clienți: Experiențe cu serviciile noastre"
        }
        return titles.get(content_type, f"Content: {content_type}")
    
    def _generate_content_title_from_topic(self, topic: str) -> str:
        """
        Generează titlu pentru un topic
        """
        return f"Ghid: {topic.title()}"
    
    def _save_analysis(self, domain: str, analysis: Dict):
        """
        Salvează analiza în MongoDB
        """
        try:
            self.db.content_gap_analysis.update_one(
                {"master_domain": domain},
                {"$set": analysis},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to save analysis: {e}")


# Test
if __name__ == "__main__":
    analyzer = ContentGapAnalyzer()
    
    # Mock data pentru test
    master_content = {
        "domain": "incendii.ro",
        "pages": [
            {"title": "Verificare instalatii", "content": "Content despre verificare..."},
            {"title": "Audit PSI", "content": "Content despre audit..."}
        ]
    }
    
    competitor_contents = [
        {
            "domain": "speedfire.ro",
            "pages": [
                {"title": "Studiu de caz: Centru comercial", "content": "Proiect realizat..."},
                {"title": "Preturi sisteme antiincendiu", "content": "Tarife..."},
                {"title": "FAQ protectie incendiu", "content": "Întrebări frecvente..."}
            ]
        },
        {
            "domain": "protectiilafoc.ro",
            "pages": [
                {"title": "Ghid: Cum obtii avizul ISU", "content": "Pas cu pas..."},
                {"title": "Proiecte realizate", "content": "Studii de caz..."},
                {"title": "Certificari ISO", "content": "Content despre certificări..."}
            ]
        }
    ]
    
    print("="*80)
    print("🧪 TESTING CONTENT GAP ANALYZER")
    print("="*80)
    
    result = analyzer.analyze_gaps(master_content, competitor_contents)
    
    print(f"\n📊 CONTENT GAP ANALYSIS:\n")
    print(f"Missing Subtopics: {len(result.get('missing_subtopics', []))}")
    print(f"Missing Content Types: {len(result.get('missing_content_types', {}))}")
    print(f"Unanswered Questions: {len(result.get('unanswered_questions', []))}")
    
    print(f"\n📝 CONTENT ROADMAP ({len(result.get('content_roadmap', []))} items):\n")
    for item in result.get("content_roadmap", [])[:5]:
        print(f"{item['priority']}. {item['title']}")
        print(f"   Type: {item['type']}")
        print(f"   Impact: {item['estimated_impact']}")
        print(f"   Reason: {item['reason']}")
        print()

