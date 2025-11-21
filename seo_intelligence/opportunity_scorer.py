#!/usr/bin/env python3
"""
📊 OPPORTUNITY SCORER - SEO Intelligence v2.0

Calculează opportunity score pentru fiecare keyword:
- search_volume (estimat sau API)
- competition_level (câți competitori solizi)
- difficulty_score (autoritate competitori)
- business_relevance (cât de relevant pentru business)
- opportunity_score = (volume * relevance) / difficulty

Folosește Qwen GPU pentru analiză SERP detaliată
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
import requests

from llm_orchestrator import get_orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpportunityScorer:
    """
    Calculează opportunity score pentru keywords
    """
    
    def __init__(self):
        self.llm = get_orchestrator()
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        
        logger.info("✅ Opportunity Scorer initialized")
    
    def score_keyword(
        self,
        keyword: str,
        serp_data: Dict = None,
        business_context: Dict = None
    ) -> Dict:
        """
        Calculează opportunity score pentru un keyword
        
        Args:
            keyword: Keyword-ul de analizat
            serp_data: Date SERP (rezultate search)
            business_context: Context business (relevance factors)
        
        Returns:
            Dict cu scores și recomandări
        """
        logger.info(f"📊 Scoring keyword: '{keyword}'")
        
        try:
            # 1. Estimează search volume
            search_volume = self._estimate_search_volume(keyword, serp_data)
            
            # 2. Calculează competition level
            competition_level = self._calculate_competition_level(keyword, serp_data)
            
            # 3. Calculează difficulty score
            difficulty_score = self._calculate_difficulty(keyword, serp_data)
            
            # 4. Calculează business relevance
            business_relevance = self._calculate_business_relevance(keyword, business_context)
            
            # 5. Calculează opportunity score final
            opportunity_score = self._calculate_opportunity_score(
                search_volume,
                business_relevance,
                difficulty_score
            )
            
            # 6. Generează recomandare
            recommendation = self._generate_recommendation(
                opportunity_score,
                difficulty_score,
                business_relevance
            )
            
            result = {
                "keyword": keyword,
                "search_volume": search_volume,
                "competition_level": competition_level,
                "difficulty_score": difficulty_score,
                "business_relevance": business_relevance,
                "opportunity_score": opportunity_score,
                "top_competitors": self._extract_top_competitors(serp_data),
                "recommendation": recommendation,
                "scored_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Save în MongoDB
            self._save_score(keyword, result)
            
            logger.info(f"✅ Opportunity score: {opportunity_score:.2f} ({recommendation})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error scoring keyword: {e}")
            return self._fallback_score(keyword)
    
    def score_batch(
        self,
        keywords: List[str],
        serp_data_map: Dict[str, Dict] = None,
        business_context: Dict = None
    ) -> List[Dict]:
        """
        Scorează multiple keywords în batch
        """
        logger.info(f"📦 Batch scoring {len(keywords)} keywords")
        
        results = []
        for i, keyword in enumerate(keywords, 1):
            logger.info(f"  [{i}/{len(keywords)}] Scoring: {keyword}")
            
            # Get SERP data pentru acest keyword
            serp_data = serp_data_map.get(keyword) if serp_data_map else None
            
            # Score
            score = self.score_keyword(keyword, serp_data, business_context)
            results.append(score)
        
        # Sort by opportunity score (descending)
        results.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
        
        logger.info(f"✅ Batch scoring complete: {len(results)} keywords")
        return results
    
    def _estimate_search_volume(self, keyword: str, serp_data: Dict = None) -> int:
        """
        Estimează search volume pentru keyword
        
        Metode:
        1. API call la serviciu de volume (Google Keyword Planner API, etc)
        2. Estimare bazată pe SERP features (dacă apar ads, număr rezultate)
        3. Estimare bazată pe lungime keyword și pattern-uri
        """
        # TODO: Integrate cu API real (Google Keyword Planner, SEMrush, etc)
        
        # FALLBACK: Estimare simplă bazată pe pattern
        keyword_lower = keyword.lower()
        
        # Short keywords (1-2 words) = mai multe căutări
        word_count = len(keyword_lower.split())
        
        # Base volume
        if word_count == 1:
            base = 5000
        elif word_count == 2:
            base = 2000
        elif word_count == 3:
            base = 800
        else:
            base = 300
        
        # Adjust pentru local keywords (mai puține căutări)
        if any(loc in keyword_lower for loc in ["bucuresti", "romania", "cluj", "timisoara"]):
            base = int(base * 0.3)
        
        # Adjust pentru commercial intent (mai multe căutări)
        if any(w in keyword_lower for w in ["pret", "firma", "best", "top"]):
            base = int(base * 1.5)
        
        return base
    
    def _calculate_competition_level(self, keyword: str, serp_data: Dict = None) -> float:
        """
        Calculează nivel de competiție (0-1)
        
        Bazat pe:
        - Număr de competitori în SERP
        - Prezența de ads
        - Diversitate domenii
        """
        if not serp_data or "results" not in serp_data:
            return 0.5  # Default medium competition
        
        results = serp_data.get("results", [])
        
        # Număr rezultate
        num_results = len(results)
        
        # Check pentru ads (indicator de competiție comercială)
        has_ads = serp_data.get("has_ads", False)
        
        # Diversitate domenii (multe domenii diferite = competiție mare)
        domains = set()
        for result in results[:10]:
            domain = self._extract_domain(result.get("url", ""))
            if domain:
                domains.add(domain)
        
        domain_diversity = len(domains) / 10.0 if results else 0.5
        
        # Calculează competition level
        competition = 0.0
        
        # Base pe număr rezultate
        competition += min(num_results / 10.0, 1.0) * 0.4
        
        # Ads indicator
        competition += 0.3 if has_ads else 0.0
        
        # Domain diversity
        competition += domain_diversity * 0.3
        
        return min(competition, 1.0)
    
    def _calculate_difficulty(self, keyword: str, serp_data: Dict = None) -> float:
        """
        Calculează difficulty score (0-1)
        
        Bazat pe:
        - Autoritatea competitorilor (proxy: brand recognition)
        - Calitatea content-ului competitorilor
        - Prezența de branduri mari
        """
        if not serp_data or "results" not in serp_data:
            return 0.5
        
        results = serp_data.get("results", [])[:10]
        
        difficulty = 0.0
        
        # Check pentru big brands (Wikipedia, gov sites, etc)
        big_brands = ["wikipedia", "gov.ro", "edu.ro", ".gov", ".edu"]
        brand_count = 0
        
        for result in results:
            url = result.get("url", "").lower()
            if any(brand in url for brand in big_brands):
                brand_count += 1
        
        # Brand presence increases difficulty
        difficulty += (brand_count / len(results)) * 0.5 if results else 0.0
        
        # Title quality (dacă sunt optimizate = competitori buni)
        optimized_count = 0
        for result in results:
            title = result.get("title", "").lower()
            if keyword.lower() in title:
                optimized_count += 1
        
        difficulty += (optimized_count / len(results)) * 0.3 if results else 0.0
        
        # Default medium-high difficulty
        difficulty += 0.2
        
        return min(difficulty, 1.0)
    
    def _calculate_business_relevance(self, keyword: str, business_context: Dict = None) -> float:
        """
        Calculează business relevance (0-1)
        
        Bazat pe:
        - Alignment cu produse/servicii
        - Intent match (commercial > informational)
        - Target audience match
        """
        if not business_context:
            return 0.7  # Default good relevance
        
        relevance = 0.0
        
        # Check alignment cu produse/servicii
        products = business_context.get("products", [])
        services = business_context.get("services", [])
        
        keyword_lower = keyword.lower()
        
        # Match cu produse
        product_match = any(p.lower() in keyword_lower for p in products)
        service_match = any(s.lower() in keyword_lower for s in services)
        
        if product_match or service_match:
            relevance += 0.4
        
        # Commercial intent keywords = mai relevante
        commercial_words = ["pret", "oferta", "firma", "companie", "cumpara"]
        if any(w in keyword_lower for w in commercial_words):
            relevance += 0.3
        
        # Local keywords = relevante pentru business local
        local_words = ["bucuresti", "romania", "cluj", "timisoara", "local"]
        if any(w in keyword_lower for w in local_words):
            relevance += 0.2
        
        # Industry specific keywords
        industry = business_context.get("industry", "")
        if industry and industry.lower() in keyword_lower:
            relevance += 0.1
        
        return min(relevance + 0.3, 1.0)  # Minimum 0.3
    
    def _calculate_opportunity_score(
        self,
        search_volume: int,
        business_relevance: float,
        difficulty_score: float
    ) -> float:
        """
        Calculează opportunity score final
        
        Formula: (volume_normalized * relevance) / (difficulty + 0.1)
        
        Range: 0-10
        """
        # Normalize volume (0-1 scale)
        volume_normalized = min(search_volume / 10000.0, 1.0)
        
        # Calculate
        if difficulty_score < 0.1:
            difficulty_score = 0.1  # Evită împărțire la 0
        
        opportunity = (volume_normalized * business_relevance) / difficulty_score
        
        # Scale to 0-10
        opportunity = opportunity * 10.0
        
        return min(opportunity, 10.0)
    
    def _generate_recommendation(
        self,
        opportunity_score: float,
        difficulty_score: float,
        business_relevance: float
    ) -> str:
        """
        Generează recomandare bazată pe scores
        """
        if opportunity_score >= 7.0:
            if difficulty_score < 0.5:
                return "HIGH PRIORITY - Excellent opportunity, low difficulty"
            else:
                return "HIGH PRIORITY - High value despite difficulty"
        elif opportunity_score >= 4.0:
            if difficulty_score < 0.5:
                return "MEDIUM PRIORITY - Good quick win"
            else:
                return "MEDIUM PRIORITY - Moderate opportunity"
        else:
            if business_relevance > 0.8:
                return "LOW PRIORITY - High relevance but tough competition"
            else:
                return "LOW PRIORITY - Consider alternatives"
    
    def _extract_top_competitors(self, serp_data: Dict = None) -> List[str]:
        """
        Extrage top competitori din SERP
        """
        if not serp_data or "results" not in serp_data:
            return []
        
        competitors = []
        for result in serp_data.get("results", [])[:5]:
            domain = self._extract_domain(result.get("url", ""))
            if domain:
                competitors.append(domain)
        
        return competitors
    
    def _extract_domain(self, url: str) -> str:
        """
        Extrage domain din URL
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except:
            return ""
    
    def _fallback_score(self, keyword: str) -> Dict:
        """
        Fallback scoring dacă ceva fail
        """
        return {
            "keyword": keyword,
            "search_volume": 1000,
            "competition_level": 0.5,
            "difficulty_score": 0.5,
            "business_relevance": 0.7,
            "opportunity_score": 5.0,
            "top_competitors": [],
            "recommendation": "MEDIUM PRIORITY - Default score (insufficient data)",
            "scored_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _save_score(self, keyword: str, score: Dict):
        """
        Salvează score în MongoDB
        """
        try:
            self.db.keyword_opportunity_scores.update_one(
                {"keyword": keyword},
                {"$set": score},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to save score: {e}")


# Test
if __name__ == "__main__":
    scorer = OpportunityScorer()
    
    # Test keywords
    test_keywords = [
        "protectie la foc pret",
        "sisteme antiincendiu",
        "firme protectie incendiu bucuresti",
        "audit securitate incendiu"
    ]
    
    print("="*80)
    print("🧪 TESTING OPPORTUNITY SCORER")
    print("="*80)
    
    # Mock business context
    business_context = {
        "industry": "protectie incendiu",
        "products": ["stingatoare", "sisteme alarma", "detectoare"],
        "services": ["instalare", "verificare", "audit", "consultanta"]
    }
    
    results = scorer.score_batch(test_keywords, business_context=business_context)
    
    print(f"\n📊 TOP OPPORTUNITIES:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['keyword']}")
        print(f"   Opportunity Score: {result['opportunity_score']:.2f}/10")
        print(f"   Search Volume: {result['search_volume']}")
        print(f"   Difficulty: {result['difficulty_score']:.2f}")
        print(f"   Relevance: {result['business_relevance']:.2f}")
        print(f"   💡 {result['recommendation']}")
        print()

