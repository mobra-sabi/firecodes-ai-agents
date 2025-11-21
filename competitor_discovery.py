"""
Competitor Discovery - Descoperire competitori prin web search
"""

import os
import logging
from typing import List, Dict, Any, Set
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SerpAPI key (opțional, fallback la DuckDuckGo)
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")


def _norm_domain_from_url(url: str) -> str:
    """Normalizează domain dintr-un URL"""
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if ":" in host:
        host = host.split(":")[0]
    return host


def _ddg_search(query: str, limit: int = 15) -> List[Dict[str, str]]:
    """
    Căutare folosind DuckDuckGo HTML (fallback dacă nu există SerpAPI)
    """
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        params = {"q": query, "kl": "ro-ro"}
        
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        
        # DuckDuckGo HTML structure (poate varia)
        for link in soup.select("a.result__a")[:limit]:
            href = link.get("href", "")
            if href and href.startswith("http"):
                title = link.get_text(strip=True)
                if title:
                    results.append({
                        "url": href,
                        "title": title,
                        "source": "duckduckgo"
                    })
        
        logger.info(f"✅ DuckDuckGo: {len(results)} rezultate pentru '{query}'")
        return results
        
    except Exception as e:
        logger.warning(f"⚠️ Eroare DuckDuckGo pentru '{query}': {e}")
        return []


def _serpapi_search(query: str, limit: int = 15) -> List[Dict[str, str]]:
    """
    Căutare folosind SerpAPI (preferat, dacă există cheie API)
    """
    if not SERPAPI_KEY:
        return []
    
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google",
            "q": query,
            "num": limit,
            "api_key": SERPAPI_KEY,
            "hl": "ro",  # Romanian language
            "gl": "ro"   # Romania country
        }
        
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        
        data = resp.json()
        results = []
        
        # Organic results
        for item in data.get("organic_results", [])[:limit]:
            link = item.get("link", "")
            title = item.get("title", "")
            if link and link.startswith("http"):
                results.append({
                    "url": link,
                    "title": title,
                    "source": "serpapi",
                    "snippet": item.get("snippet", "")
                })
        
        logger.info(f"✅ SerpAPI: {len(results)} rezultate pentru '{query}'")
        return results
        
    except Exception as e:
        logger.warning(f"⚠️ Eroare SerpAPI pentru '{query}': {e}")
        return []


def web_search(query: str, limit: int = 15) -> List[Dict[str, str]]:
    """
    Web search - preferă SerpAPI, fallback la DuckDuckGo
    """
    # Încearcă SerpAPI dacă există cheie
    if SERPAPI_KEY:
        results = _serpapi_search(query, limit)
        if results:
            return results
    
    # Fallback la DuckDuckGo
    return _ddg_search(query, limit)


def discover_competitors_from_strategy(strategy: Dict[str, Any], exclude_domains: Set[str] = None) -> List[Dict[str, Any]]:
    """
    Descoperă competitori folosind cuvintele cheie din strategia DeepSeek
    
    Args:
        strategy: Strategia competitivă generată de DeepSeek
        exclude_domains: Set de domenii de exclus (ex: domeniul principal)
    
    Returns:
        Listă de site-uri descoperite pentru indexare
    """
    if exclude_domains is None:
        exclude_domains = set()
    
    discovered_sites = []
    seen_domains = set(exclude_domains)
    
    # Extrage web_search_queries din strategie
    services = strategy.get("services", [])
    
    logger.info(f"🔍 Descoperă competitori pentru {len(services)} servicii...")
    
    for service in services:
        service_name = service.get("service_name", "")
        search_keywords = service.get("search_keywords", [])
        
        # Extrage web_search_queries din competitive_research_strategy
        research_strategy = service.get("competitive_research_strategy", {})
        web_search_queries = research_strategy.get("web_search_queries", [])
        
        # Construiește query-uri de căutare
        all_queries = []
        
        # 1. Query-uri din web_search_queries (cel mai relevant)
        for query_template in web_search_queries:
            # Înlocuiește placeholders
            query = query_template.replace("{service_name}", service_name)
            query = query.replace("{{service_name}}", service_name)
            all_queries.append(query)
        
        # 2. Query-uri din search_keywords
        for keyword in search_keywords[:3]:  # Primele 3 keywords
            query = f"{keyword} Romania"
            all_queries.append(query)
        
        # 3. Query generic pentru serviciu
        if service_name:
            all_queries.append(f"{service_name} Romania")
            all_queries.append(f"{service_name} competitors")
        
        # Elimină duplicate-uri și căută
        unique_queries = list(set(all_queries))
        
        logger.info(f"   Serviciu: {service_name} - {len(unique_queries)} query-uri")
        
        for query in unique_queries:
            try:
                # Execută web search
                results = web_search(query, limit=10)  # Top 10 per query
                
                for result in results:
                    url = result.get("url", "")
                    if not url:
                        continue
                    
                    domain = _norm_domain_from_url(url)
                    
                    # Skip dacă deja am găsit acest domeniu
                    if domain in seen_domains:
                        continue
                    
                    # Skip dacă este în exclude_domains
                    if domain in exclude_domains:
                        continue
                    
                    # Validează URL-ul (doar HTTP/HTTPS)
                    if not url.startswith(("http://", "https://")):
                        continue
                    
                    seen_domains.add(domain)
                    discovered_sites.append({
                        "url": url,
                        "title": result.get("title", ""),
                        "domain": domain,
                        "service_name": service_name,
                        "discovery_query": query,
                        "source": result.get("source", "unknown"),
                        "priority": "high" if "competitor" in query.lower() or "alternative" in query.lower() else "medium"
                    })
                    
                    logger.info(f"   ✅ Descoperit: {domain} (din query: {query})")
                
            except Exception as e:
                logger.warning(f"   ⚠️ Eroare la query '{query}': {e}")
                continue
    
    logger.info(f"✅ Total descoperit: {len(discovered_sites)} site-uri unice pentru indexare")
    
    # Sortează după prioritate
    priority_order = {"high": 0, "medium": 1, "low": 2}
    discovered_sites.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))
    
    return discovered_sites


