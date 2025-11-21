#!/usr/bin/env python3
"""
🧠 KEYWORD INTENT ANALYZER - SEO Intelligence v2.0

Analizează fiecare keyword pentru:
- Intent: informativ/comercial/tranzacțional/navigațional
- Stadiu funnel: awareness/consideration/decision/post-purchase
- Tip trafic: B2B/B2C/local/global

Folosește Qwen local pentru analiză rapidă + DeepSeek pentru decizii complexe
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

from llm_orchestrator import get_orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KeywordIntentAnalyzer:
    """
    Analizează intent-ul și caracteristicile fiecărui keyword
    """
    
    def __init__(self):
        self.llm = get_orchestrator()  # DeepSeek + Qwen fallback
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        
        logger.info("✅ Keyword Intent Analyzer initialized")
    
    def analyze_intent(self, keyword: str, serp_results: List[Dict] = None, context: Dict = None) -> Dict:
        """
        Analizează intent-ul unui keyword bazat pe keyword text + SERP context
        
        Args:
            keyword: Keyword-ul de analizat
            serp_results: Opțional - rezultate SERP pentru context
            context: Opțional - context business (industrie, produse)
        
        Returns:
            Dict cu intent analysis
        """
        logger.info(f"🔍 Analyzing intent for keyword: '{keyword}'")
        
        # Build prompt pentru LLM
        prompt = self._build_intent_prompt(keyword, serp_results, context)
        
        try:
            # Call LLM (DeepSeek sau Qwen)
            response = self.llm.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ești un expert SEO care analizează intent-ul keyword-urilor. "
                            "Răspunde DOAR cu JSON valid, fără text adițional."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Extract content
            if isinstance(response, dict):
                content = response.get("content", "")
            else:
                content = str(response)
            
            # Parse JSON din răspuns
            analysis = self._parse_llm_response(content, keyword)
            
            # Add metadata
            analysis["keyword"] = keyword
            analysis["analyzed_at"] = datetime.now(timezone.utc).isoformat()
            
            # Save în MongoDB
            self._save_analysis(keyword, analysis)
            
            logger.info(f"✅ Intent analysis complete: {analysis['intent']} / {analysis['funnel_stage']}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing intent: {e}")
            return self._fallback_analysis(keyword)
    
    def analyze_batch(self, keywords: List[str], context: Dict = None) -> List[Dict]:
        """
        Analizează multiple keywords în batch
        """
        logger.info(f"📦 Batch analyzing {len(keywords)} keywords")
        
        results = []
        for i, keyword in enumerate(keywords, 1):
            logger.info(f"  [{i}/{len(keywords)}] Analyzing: {keyword}")
            
            # Check cache
            cached = self._get_cached_analysis(keyword)
            if cached:
                logger.info(f"     ✅ Using cached analysis")
                results.append(cached)
                continue
            
            # Analyze
            analysis = self.analyze_intent(keyword, context=context)
            results.append(analysis)
        
        logger.info(f"✅ Batch analysis complete: {len(results)} keywords")
        return results
    
    def _build_intent_prompt(self, keyword: str, serp_results: List[Dict] = None, context: Dict = None) -> str:
        """
        Construiește prompt pentru LLM
        """
        prompt = f"""Analizează intent-ul următorului keyword SEO:

KEYWORD: "{keyword}"
"""
        
        if context:
            prompt += f"""
CONTEXT BUSINESS:
- Industrie: {context.get('industry', 'N/A')}
- Produse/Servicii: {', '.join(context.get('products', []))}
"""
        
        if serp_results:
            prompt += f"""
TOP SERP RESULTS:
"""
            for i, result in enumerate(serp_results[:5], 1):
                prompt += f"{i}. {result.get('title', 'N/A')}\n"
        
        prompt += """

Analizează keyword-ul și returnează JSON cu următoarea structură:

{
  "intent": "<informativ | comercial | tranzactional | navigational>",
  "funnel_stage": "<awareness | consideration | decision | post-purchase>",
  "traffic_type": "<B2B | B2C | local | global | mixed>",
  "confidence": <0.0-1.0>,
  "reasoning": "<explicație scurtă în română>",
  "modifiers": ["<lista de modificatori: local, urgent, cheap, best, how to, etc>"],
  "user_intent_description": "<ce vrea user-ul când caută asta>"
}

EXPLICAȚII:
- Intent informativ: user caută informații generale (ghiduri, explicații)
- Intent comercial: user compară opțiuni, cercetează (reviews, comparații)
- Intent tranzacțional: user vrea să cumpere/angajeze acum (cumpără, ofertă, preț)
- Intent navigational: user caută un brand specific

- Awareness: nu știe despre soluție
- Consideration: compară soluții
- Decision: gata să cumpere
- Post-purchase: client existent

Răspunde DOAR cu JSON-ul, fără text adițional.
"""
        
        return prompt
    
    def _parse_llm_response(self, content: str, keyword: str) -> Dict:
        """
        Parsează răspunsul LLM și extrage JSON
        """
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                analysis = json.loads(json_match.group(0))
                
                # Validate fields
                required_fields = ["intent", "funnel_stage", "traffic_type", "confidence"]
                for field in required_fields:
                    if field not in analysis:
                        raise ValueError(f"Missing field: {field}")
                
                return analysis
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            logger.warning(f"⚠️  Failed to parse LLM response: {e}. Using fallback.")
            return self._fallback_analysis(keyword)
    
    def _fallback_analysis(self, keyword: str) -> Dict:
        """
        Fallback analysis bazat pe simple rules dacă LLM fail
        """
        keyword_lower = keyword.lower()
        
        # Detect intent based on keywords
        transactional_keywords = ["cumpara", "cumpar", "pret", "oferta", "comanda", "urgent"]
        commercial_keywords = ["best", "top", "review", "compara", "comparatie"]
        informational_keywords = ["ce este", "cum", "de ce", "ghid", "tutorial"]
        
        if any(k in keyword_lower for k in transactional_keywords):
            intent = "tranzactional"
            funnel_stage = "decision"
        elif any(k in keyword_lower for k in commercial_keywords):
            intent = "comercial"
            funnel_stage = "consideration"
        elif any(k in keyword_lower for k in informational_keywords):
            intent = "informativ"
            funnel_stage = "awareness"
        else:
            intent = "informativ"
            funnel_stage = "awareness"
        
        # Detect traffic type
        if "bucuresti" in keyword_lower or "romania" in keyword_lower or "local" in keyword_lower:
            traffic_type = "local"
        elif "firma" in keyword_lower or "companie" in keyword_lower or "business" in keyword_lower:
            traffic_type = "B2B"
        else:
            traffic_type = "B2C"
        
        return {
            "intent": intent,
            "funnel_stage": funnel_stage,
            "traffic_type": traffic_type,
            "confidence": 0.5,
            "reasoning": "Fallback analysis based on keyword pattern matching",
            "modifiers": [],
            "user_intent_description": f"User searching for '{keyword}'"
        }
    
    def _save_analysis(self, keyword: str, analysis: Dict):
        """
        Salvează analiza în MongoDB pentru cache
        """
        try:
            self.db.keyword_intent_analysis.update_one(
                {"keyword": keyword},
                {"$set": analysis},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to save analysis: {e}")
    
    def _get_cached_analysis(self, keyword: str) -> Dict:
        """
        Obține analiza cached din MongoDB
        """
        try:
            cached = self.db.keyword_intent_analysis.find_one({"keyword": keyword})
            if cached:
                # Check if not too old (30 days)
                if "analyzed_at" in cached:
                    from dateutil import parser
                    analyzed_date = parser.parse(cached["analyzed_at"])
                    age_days = (datetime.now(timezone.utc) - analyzed_date).days
                    if age_days < 30:
                        return cached
            return None
        except Exception as e:
            logger.error(f"Failed to get cached analysis: {e}")
            return None


# Test
if __name__ == "__main__":
    analyzer = KeywordIntentAnalyzer()
    
    # Test keywords
    test_keywords = [
        "protectie la foc pret",
        "cum obtin aviz ISU",
        "firme protectie incendiu bucuresti",
        "best sisteme alarma incendiu"
    ]
    
    print("="*80)
    print("🧪 TESTING KEYWORD INTENT ANALYZER")
    print("="*80)
    
    for keyword in test_keywords:
        print(f"\n📝 Keyword: {keyword}")
        analysis = analyzer.analyze_intent(keyword)
        print(f"   Intent: {analysis['intent']}")
        print(f"   Funnel: {analysis['funnel_stage']}")
        print(f"   Traffic: {analysis['traffic_type']}")
        print(f"   Confidence: {analysis['confidence']}")
        print(f"   Reasoning: {analysis['reasoning'][:100]}...")

