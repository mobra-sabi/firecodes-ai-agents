#!/usr/bin/env python3
"""
Google Competitor Discovery - Caută competitori folosind keywords generate de DeepSeek
"""

import os
import logging
import time
from typing import Dict, List, Any, Set
from collections import defaultdict
from urllib.parse import urlparse
from pymongo import MongoClient
from bson import ObjectId
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class GoogleCompetitorDiscovery:
    """
    Descoperă competitori prin Google Search folosind keywords din analiza DeepSeek
    """
    
    # Domenii de exclus (marketplace-uri, directoare, site-uri generice)
    EXCLUDED_DOMAINS = {
        'google.com', 'facebook.com', 'youtube.com', 'linkedin.com',
        'olx.ro', 'publi24.ro', 'amazon.com', 'ebay.com',
        'wikipedia.org', 'paginiaurii.ro', 'paginigalbene.ro',
        'listafirme.ro', 'firme.info', 'bizoo.ro',
        'indaco.ro', 'e-licitatie.ro', 'sicap.ro'
    }
    
    def __init__(self):
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        
        # Google Custom Search API (opțional - dacă ai API key)
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.google_cse_id = os.getenv('GOOGLE_CSE_ID')
        
    def discover_competitors_for_agent(
        self, 
        agent_id: str, 
        results_per_keyword: int = 20,
        use_api: bool = False
    ) -> Dict[str, Any]:
        """
        Descoperă competitori pentru un agent bazat pe analiza DeepSeek existentă
        
        Args:
            agent_id: ID-ul agentului
            results_per_keyword: Câte rezultate per keyword (default 20)
            use_api: Dacă True, folosește Google Custom Search API (mai precis dar limitat)
                    Dacă False, folosește scraping (unlimited dar mai fragil)
        
        Returns:
            Dict cu:
            - competitors: listă de competitori cu scoring
            - keywords_map: mapare keyword -> competitori
            - subdomain_map: mapare subdomeniu -> competitori
            - stats: statistici
        """
        logger.info(f"🔍 Descoperire competitori pentru agent {agent_id}")
        
        # 1. Obține analiza DeepSeek
        analysis = self.db.competitive_analysis.find_one({
            "agent_id": ObjectId(agent_id),
            "analysis_type": "competition_discovery"
        })
        
        if not analysis:
            raise ValueError(f"No competitive analysis found for agent {agent_id}. Run analyze-competition first!")
        
        analysis_data = analysis.get("analysis_data", {})
        subdomains = analysis_data.get("subdomains", [])
        overall_keywords = analysis_data.get("overall_keywords", [])
        
        logger.info(f"📦 {len(subdomains)} subdomenii, {len(overall_keywords)} keywords generale")
        
        # 2. Colectează toate keywords cu metadata
        all_keywords = []
        
        # Keywords per subdomeniu
        for subdomain in subdomains:
            subdomain_name = subdomain.get("name", "unknown")
            keywords = subdomain.get("keywords", [])
            
            for kw in keywords:
                all_keywords.append({
                    "keyword": kw,
                    "subdomain": subdomain_name,
                    "type": "subdomain"
                })
        
        # Keywords generale
        for kw in overall_keywords:
            all_keywords.append({
                "keyword": kw,
                "subdomain": None,
                "type": "general"
            })
        
        logger.info(f"🔑 Total keywords pentru search: {len(all_keywords)}")
        
        # 3. Buffer pentru site-uri descoperite (deduplicare inteligentă)
        discovered_sites = {}  # domain -> site info
        keyword_appearances = defaultdict(list)  # domain -> [keywords unde a apărut]
        subdomain_appearances = defaultdict(set)  # domain -> {subdomenii}
        position_scores = defaultdict(list)  # domain -> [poziții în Google]
        
        # 4. Căutare Google pentru fiecare keyword + SALVARE SERP RESULTS + RANKING
        master_agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
        master_domain = master_agent.get("domain", "") if master_agent else ""
        
        for i, kw_data in enumerate(all_keywords, 1):
            keyword = kw_data["keyword"]
            subdomain = kw_data["subdomain"]
            
            logger.info(f"🔍 [{i}/{len(all_keywords)}] Search: '{keyword}' (subdomain: {subdomain or 'general'})")
            
            # Creează SERP run pentru acest keyword
            serp_run_id = ObjectId()
            serp_run_doc = {
                "_id": serp_run_id,
                "agent_id": ObjectId(agent_id),
                "keyword": keyword,
                "subdomain": subdomain,
                "created_at": datetime.now(timezone.utc),
                "status": "in_progress",
                "results_count": 0
            }
            self.db.serp_runs.insert_one(serp_run_doc)
            
            try:
                if use_api and self.google_api_key:
                    results = self._google_search_api(keyword, results_per_keyword)
                else:
                    results = self._google_search_scraping(keyword, results_per_keyword)
                
                # Procesează rezultatele și SALVEAZĂ în serp_results
                for position, result in enumerate(results, 1):
                    url = result.get("url")
                    domain = self._extract_domain(url)
                    
                    # Skip domenii excluse
                    if self._should_exclude_domain(domain):
                        continue
                    
                    # Skip propriul agent
                    if domain == master_domain:
                        continue
                    
                    # SALVEAZĂ în serp_results cu ranking real
                    serp_result_doc = {
                        "serp_run_id": serp_run_id,
                        "agent_id": ObjectId(agent_id),
                        "keyword": keyword,
                        "rank": position,  # Poziția reală în Google (1-20)
                        "url": url,
                        "domain": domain,
                        "title": result.get("title", ""),
                        "snippet": result.get("description", ""),
                        "result_type": "organic",
                        "is_master": domain == master_domain,
                        "master_domain": master_domain,
                        "created_at": datetime.now(timezone.utc)
                    }
                    self.db.serp_results.insert_one(serp_result_doc)
                    
                    # Adaugă în buffer
                    if domain not in discovered_sites:
                        discovered_sites[domain] = {
                            "domain": domain,
                            "url": url,
                            "title": result.get("title", ""),
                            "description": result.get("description", ""),
                            "first_seen": keyword
                        }
                    
                    # Tracking appearances
                    keyword_appearances[domain].append(keyword)
                    if subdomain:
                        subdomain_appearances[domain].add(subdomain)
                    position_scores[domain].append(position)
                
                # Update SERP run status
                self.db.serp_runs.update_one(
                    {"_id": serp_run_id},
                    {"$set": {
                        "status": "completed",
                        "results_count": len(results)
                    }}
                )
                
                logger.info(f"   ✅ Găsite {len(results)} rezultate, total unique: {len(discovered_sites)}")
                
                # Rate limiting
                time.sleep(0.5)  # Pauză între requests
                
            except Exception as e:
                logger.error(f"   ❌ Eroare la search '{keyword}': {e}")
                # Update SERP run status to failed
                self.db.serp_runs.update_one(
                    {"_id": serp_run_id},
                    {"$set": {
                        "status": "failed",
                        "error": str(e)
                    }}
                )
                continue
        
        # 5. VALIDARE DEEPSEEK pentru fiecare competitor ÎNAINTE de a-l marca ca relevant
        logger.info(f"🤖 Validare DeepSeek pentru {len(discovered_sites)} competitori descoperiți...")
        
        # Obține context master pentru validare
        master_context = self._get_master_context_for_validation(agent_id, subdomains)
        
        competitors = []
        
        for domain, site_info in discovered_sites.items():
            keywords_found = keyword_appearances[domain]
            subdomains_found = list(subdomain_appearances[domain])
            positions = position_scores[domain]
            
            # VALIDARE DEEPSEEK: Analizează dacă competitorul este într-adevăr relevant
            deepseek_validation = self._validate_competitor_with_deepseek(
                competitor_domain=domain,
                competitor_url=site_info["url"],
                competitor_title=site_info["title"],
                competitor_description=site_info["description"],
                keywords_found=keywords_found,
                master_context=master_context,
                master_subdomains=subdomains
            )
            
            # Dacă DeepSeek spune că NU este relevant, skip sau reduce scorul drastic
            if not deepseek_validation.get("is_relevant", False):
                logger.info(f"   ⚠️ {domain}: DeepSeek a marcat ca IRELEVANT - {deepseek_validation.get('reason', 'N/A')}")
                # Poți să-l excludi complet sau să-l penalizezi foarte mult
                # Pentru acum, îl includem dar cu scor foarte mic
                deepseek_validation["relevance_penalty"] = 0.1  # Reduce scorul cu 90%
            else:
                logger.info(f"   ✅ {domain}: DeepSeek a validat ca RELEVANT - {deepseek_validation.get('reason', 'N/A')}")
                deepseek_validation["relevance_penalty"] = 1.0
            
            # Scoring complex CU VALIDARE DeepSeek
            score_data = self._calculate_competitor_score(
                keyword_count=len(keywords_found),
                subdomain_count=len(subdomains_found),
                positions=positions,
                total_keywords=len(all_keywords),
                subdomains_matched=subdomains_found,
                master_subdomains=subdomains  # Subdomeniile descoperite de DeepSeek pentru master
            )
            
            # Aplică penalty-ul de la DeepSeek
            final_score = score_data["score"] * deepseek_validation.get("relevance_penalty", 1.0)
            
            competitor = {
                "domain": domain,
                "url": site_info["url"],
                "title": site_info["title"],
                "description": site_info["description"],
                "score": round(final_score, 2),
                "appearances_count": len(keywords_found),
                "keywords_matched": keywords_found[:10],  # primele 10
                "subdomains_matched": subdomains_found,
                "avg_position": sum(positions) / len(positions) if positions else 0,
                "best_position": min(positions) if positions else 0,
                "first_seen_keyword": site_info["first_seen"],
                # NOU: Validare DeepSeek
                "deepseek_validated": True,
                "deepseek_is_relevant": deepseek_validation.get("is_relevant", False),
                "deepseek_reason": deepseek_validation.get("reason", ""),
                "deepseek_confidence": deepseek_validation.get("confidence", 0),
                # Flaguri de validare existente
                "is_relevant": deepseek_validation.get("is_relevant", False) and score_data["is_relevant"],
                "matched_subdomains": score_data["matched_subdomains"],
                "subdomain_similarity_score": score_data["subdomain_similarity_score"],
                "relevance_penalty": deepseek_validation.get("relevance_penalty", 1.0),
                # Scoruri detaliate
                "keyword_score": score_data["keyword_score"],
                "position_score": score_data["position_score"],
                "subdomain_score": score_data["subdomain_score"],
                # Ranking real din Google
                "rankings_by_keyword": self._get_rankings_by_keyword(domain, agent_id)
            }
            
            competitors.append(competitor)
        
        # 6. Sortează după score
        competitors.sort(key=lambda x: x["score"], reverse=True)
        
        # 7. Creează mapări
        keywords_map = {}
        for domain, keywords in keyword_appearances.items():
            for kw in keywords:
                if kw not in keywords_map:
                    keywords_map[kw] = []
                keywords_map[kw].append(domain)
        
        subdomain_map = {}
        for subdomain in subdomains:
            subdomain_name = subdomain.get("name")
            subdomain_map[subdomain_name] = [
                domain for domain, subs in subdomain_appearances.items()
                if subdomain_name in subs
            ]
        
        # 8. Statistici
        stats = {
            "total_keywords_searched": len(all_keywords),
            "total_sites_discovered": len(discovered_sites),
            "total_competitors": len(competitors),
            "top_competitor": competitors[0]["domain"] if competitors else None,
            "avg_appearances": sum(len(kw) for kw in keyword_appearances.values()) / len(keyword_appearances) if keyword_appearances else 0,
            "subdomains_coverage": {
                subdomain: len(domains) 
                for subdomain, domains in subdomain_map.items()
            }
        }
        
        result = {
            "agent_id": agent_id,
            "competitors": competitors,
            "keywords_map": keywords_map,
            "subdomain_map": subdomain_map,
            "stats": stats,
            "discovered_at": datetime.now(timezone.utc)
        }
        
        # 9. Salvează în MongoDB
        self._save_discovery(agent_id, result)
        
        logger.info(f"✅ Descoperire completă: {len(competitors)} competitori identificați")
        
        return result
    
    def _google_search_scraping(self, query: str, num_results: int = 20) -> List[Dict[str, str]]:
        """
        Google search folosind unified SERP system (Brave/SerpAPI/Bing)
        Auto-fallback între providers disponibili
        """
        try:
            # Import unified SERP search
            import sys
            sys.path.insert(0, '/srv/hf/ai_agents')
            from unified_serp_search import search as unified_search
            
            results = unified_search(query, num_results)
            return results
            
        except ImportError:
            logger.warning("unified_serp_search not found, using fallback")
            return self._direct_google_scraping(query, num_results)
        except Exception as e:
            logger.error(f"Unified SERP search failed: {e}")
            return []
    
    def _serpapi_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Search via SerpAPI"""
        try:
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": os.getenv('SERPAPI_KEY'),
                "num": num_results,
                "gl": "ro",  # Romania
                "hl": "ro"   # Romanian
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("organic_results", [])[:num_results]:
                results.append({
                    "url": item.get("link"),
                    "title": item.get("title"),
                    "description": item.get("snippet", "")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"SerpAPI error: {e}")
            return []
    
    def _direct_google_scraping(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Direct Google scraping (backup method)"""
        try:
            from googlesearch import search
            
            results = []
            for url in search(query, num_results=num_results, lang="ro", region="ro"):
                results.append({
                    "url": url,
                    "title": "",  # Nu putem obține title fără scraping suplimentar
                    "description": ""
                })
            
            return results
            
        except ImportError:
            logger.warning("googlesearch-python not installed. Install: pip install googlesearch-python")
            return []
        except Exception as e:
            logger.error(f"Direct scraping error: {e}")
            return []
    
    def _google_search_api(self, query: str, num_results: int = 20) -> List[Dict[str, str]]:
        """
        Google search via Google Custom Search API
        Necesită API key și CSE ID
        """
        if not self.google_api_key or not self.google_cse_id:
            logger.warning("Google API credentials not found, using scraping instead")
            return self._google_search_scraping(query, num_results)
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            results = []
            
            # API-ul permite max 10 rezultate per request
            for start in range(1, min(num_results + 1, 100), 10):
                params = {
                    "key": self.google_api_key,
                    "cx": self.google_cse_id,
                    "q": query,
                    "num": min(10, num_results - len(results)),
                    "start": start,
                    "gl": "ro",
                    "hl": "ro"
                }
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("items", []):
                    results.append({
                        "url": item.get("link"),
                        "title": item.get("title"),
                        "description": item.get("snippet", "")
                    })
                
                if len(results) >= num_results:
                    break
                    
                time.sleep(0.5)  # Rate limiting
            
            return results[:num_results]
            
        except Exception as e:
            logger.error(f"Google API error: {e}")
            return []
    
    def _extract_domain(self, url: str) -> str:
        """Extrage domeniul principal din URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www.
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return ""
    
    def _should_exclude_domain(self, domain: str) -> bool:
        """Verifică dacă domeniul ar trebui exclus"""
        if not domain:
            return True
        
        # Verifică exact match
        if domain in self.EXCLUDED_DOMAINS:
            return True
        
        # Verifică subdomenii
        for excluded in self.EXCLUDED_DOMAINS:
            if domain.endswith(excluded):
                return True
        
        return False
    
    def _calculate_competitor_score(
        self, 
        keyword_count: int,
        subdomain_count: int,
        positions: List[int],
        total_keywords: int,
        subdomains_matched: List[str] = None,
        master_subdomains: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Calculează scor de relevanță pentru competitor CU VALIDARE bazată pe subdomeniile master-ului
        
        Factori:
        - Câte keywords a apărut (mai multe = mai relevant)
        - Câte subdomenii (diversitate)
        - Poziții în Google (poziții mai bune = mai relevant)
        - VALIDARE: Similaritate cu subdomeniile master-ului (NOU!)
        """
        subdomains_matched = subdomains_matched or []
        master_subdomains = master_subdomains or []
        
        # 1. VALIDARE: Verifică dacă competitorul apare în subdomeniile relevante ale master-ului
        subdomain_similarity_score = 0.0
        matched_subdomain_names = []
        is_relevant = False
        
        if master_subdomains and subdomains_matched:
            # Creează set de nume subdomenii master
            master_subdomain_names = {sd.get("name", "") for sd in master_subdomains}
            
            # Verifică câte subdomenii ale competitorului se potrivesc cu cele ale master-ului
            for competitor_subdomain in subdomains_matched:
                if competitor_subdomain in master_subdomain_names:
                    matched_subdomain_names.append(competitor_subdomain)
                    is_relevant = True
            
            # Scor similaritate: % din subdomeniile master-ului acoperite de competitor
            if master_subdomain_names:
                subdomain_similarity_score = (len(matched_subdomain_names) / len(master_subdomain_names)) * 100
            else:
                subdomain_similarity_score = 0
        
        # 2. Scor keyword coverage (0-100)
        keyword_score = (keyword_count / total_keywords) * 100 if total_keywords > 0 else 0
        
        # 3. Scor poziție medie (1-20 -> 100-5)
        avg_position = sum(positions) / len(positions) if positions else 20
        position_score = max(0, 100 - (avg_position * 5))
        
        # 4. Scor diversitate subdomenii (0-50)
        subdomain_score = min(subdomain_count * 10, 50)
        
        # 5. Scor final (combinație ponderată CU VALIDARE)
        # Dacă competitorul NU este relevant (nu apare în subdomeniile master-ului), reduce scorul cu 70%
        relevance_penalty = 1.0
        if not is_relevant and master_subdomains:
            # Competitorul nu apare în subdomeniile relevante ale master-ului
            relevance_penalty = 0.3  # Reduce scorul cu 70%
        
        final_score = (
            keyword_score * 0.3 +              # 30% importanță
            position_score * 0.3 +              # 30% importanță
            subdomain_score * 0.2 +            # 20% importanță
            subdomain_similarity_score * 0.2   # 20% importanță (NOU!)
        ) * relevance_penalty
        
        return {
            "score": round(final_score, 2),
            "keyword_score": round(keyword_score, 2),
            "position_score": round(position_score, 2),
            "subdomain_score": round(subdomain_score, 2),
            "subdomain_similarity_score": round(subdomain_similarity_score, 2),
            "is_relevant": is_relevant,
            "matched_subdomains": matched_subdomain_names,
            "relevance_penalty": relevance_penalty
        }
    
    def _get_master_context_for_validation(self, agent_id: str, subdomains: List[Dict]) -> Dict[str, Any]:
        """Obține context master pentru validare DeepSeek"""
        agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            return {}
        
        return {
            "domain": agent.get("domain", ""),
            "name": agent.get("name", ""),
            "description": agent.get("description", ""),
            "industry": agent.get("industry", ""),
            "services": agent.get("services", []),
            "subdomains": subdomains
        }
    
    def _validate_competitor_with_deepseek(
        self,
        competitor_domain: str,
        competitor_url: str,
        competitor_title: str,
        competitor_description: str,
        keywords_found: List[str],
        master_context: Dict[str, Any],
        master_subdomains: List[Dict]
    ) -> Dict[str, Any]:
        """
        Validează cu DeepSeek dacă competitorul este într-adevăr relevant
        
        Returns:
            {
                "is_relevant": bool,
                "reason": str,
                "confidence": float (0-1),
                "relevance_penalty": float (0-1)
            }
        """
        try:
            from llm_orchestrator import get_orchestrator
            
            llm = get_orchestrator()
            
            # Construiește prompt pentru DeepSeek
            master_subdomains_text = "\n".join([
                f"- {sd.get('name', '')}: {sd.get('description', '')[:200]}"
                for sd in master_subdomains[:5]
            ])
            
            prompt = f"""Ești un expert în analiză competitivă. Analizează dacă următorul site este un competitor RELEVANT pentru site-ul master.

SITE MASTER:
- Domeniu: {master_context.get('domain', '')}
- Industrie: {master_context.get('industry', '')}
- Descriere: {master_context.get('description', '')[:300]}
- Subdomenii principale:
{master_subdomains_text}

SITE COMPETITOR ANALIZAT:
- Domeniu: {competitor_domain}
- URL: {competitor_url}
- Titlu: {competitor_title}
- Descriere: {competitor_description[:300]}
- Keywords unde a apărut: {', '.join(keywords_found[:5])}

ÎNTREBARE: Acest site este un competitor RELEVANT pentru site-ul master?

Criterii de relevanță:
1. Oferă aceleași servicii/produse?
2. Acoperă aceleași subdomenii?
3. Este în aceeași industrie/nișă?
4. Are similaritate de conținut?

Răspunde în format JSON:
{{
    "is_relevant": true/false,
    "reason": "explicație scurtă (max 100 cuvinte)",
    "confidence": 0.0-1.0,
    "similarity_score": 0.0-1.0
}}"""
            
            response = llm.chat(
                messages=[
                    {"role": "system", "content": "Ești un expert în analiză competitivă. Răspunde DOAR în format JSON."},
                    {"role": "user", "content": prompt}
                ],
                model="deepseek-chat",
                temperature=0.3,
                max_tokens=500
            )
            
            # Parsează răspunsul
            import json
            import re
            
            if isinstance(response, dict):
                content = response.get("content", "")
            else:
                content = str(response)
            
            # Extrage JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                try:
                    validation = json.loads(json_match.group(0))
                    return {
                        "is_relevant": validation.get("is_relevant", False),
                        "reason": validation.get("reason", ""),
                        "confidence": validation.get("confidence", 0.5),
                        "similarity_score": validation.get("similarity_score", 0.0),
                        "relevance_penalty": 1.0 if validation.get("is_relevant", False) else 0.1
                    }
                except:
                    pass
            
            # Fallback: dacă nu poate parsa, consideră relevant dacă are keywords
            return {
                "is_relevant": len(keywords_found) > 0,
                "reason": "Nu s-a putut analiza cu DeepSeek, folosit fallback",
                "confidence": 0.5,
                "similarity_score": 0.5,
                "relevance_penalty": 0.5
            }
            
        except Exception as e:
            logger.warning(f"Eroare la validare DeepSeek pentru {competitor_domain}: {e}")
            # Fallback: consideră relevant dacă are keywords
            return {
                "is_relevant": len(keywords_found) > 0,
                "reason": f"Eroare validare: {str(e)}",
                "confidence": 0.3,
                "similarity_score": 0.3,
                "relevance_penalty": 0.5
            }
    
    def _get_rankings_by_keyword(self, domain: str, agent_id: str) -> Dict[str, int]:
        """Obține ranking-urile reale din Google pentru fiecare keyword"""
        rankings = {}
        
        # Găsește toate SERP results pentru acest domain și agent
        serp_results = list(self.db.serp_results.find({
            "agent_id": ObjectId(agent_id),
            "domain": domain
        }).sort("rank", 1))
        
        for result in serp_results:
            keyword = result.get("keyword", "")
            rank = result.get("rank", 999)
            
            # Păstrează cel mai bun rank pentru fiecare keyword
            if keyword not in rankings or rank < rankings[keyword]:
                rankings[keyword] = rank
        
        return rankings
    
    def _save_discovery(self, agent_id: str, discovery_data: Dict[str, Any]):
        """Salvează descoperirea în MongoDB"""
        
        doc = {
            "agent_id": ObjectId(agent_id),
            "discovery_type": "google_search",
            "discovery_data": discovery_data,
            "created_at": datetime.now(timezone.utc),
            "status": "completed"
        }
        
        # Update sau insert
        self.db.competitor_discovery.update_one(
            {
                "agent_id": ObjectId(agent_id),
                "discovery_type": "google_search"
            },
            {"$set": doc},
            upsert=True
        )
        
        logger.info(f"💾 Descoperire salvată în MongoDB")


def get_discovery_engine():
    """Factory function"""
    return GoogleCompetitorDiscovery()
