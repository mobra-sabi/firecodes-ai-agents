#!/usr/bin/env python3
"""
Unified SERP Search - Sistem centralizat pentru căutare Google
Suportă: Brave API, SerpAPI, Bing API cu fallback automat
"""

import os
import logging
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ================================================================================
# CONFIGURARE API KEYS (din ENV sau fișiere)
# ================================================================================

def _load_brave_key() -> str:
    """Load Brave API key din ENV sau .secrets"""
    k = (os.getenv("BRAVE_API_KEY") or "").strip()
    if k:
        return k
    for p in (".secrets/brave.key", os.path.expanduser("~/.config/ai_agents/brave.key")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                k = f.read().strip()
                if k:
                    os.environ["BRAVE_API_KEY"] = k
                    return k
        except FileNotFoundError:
            pass
    return ""

# Load keys
BRAVE_API_KEY = _load_brave_key()
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()
BING_API_KEY = os.getenv("BING_V7_SUBSCRIPTION_KEY", "").strip()

# ================================================================================
# CACHE MONGODB (opțional)
# ================================================================================

_CACHE_ENABLED = os.getenv("SERP_CACHE", "1") != "0"
_CACHE_TTL = int(os.getenv("SERP_CACHE_TTL", 30 * 24 * 3600))  # 30 zile default
_cache_collection = None

if _CACHE_ENABLED:
    try:
        from pymongo import MongoClient, ASCENDING
        _mongo_client = MongoClient(os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017"))
        _cache_collection = _mongo_client["ai_agents_db"]["serp_cache"]
        _cache_collection.create_index([("key", ASCENDING)], unique=True)
        _cache_collection.create_index("expires_at", expireAfterSeconds=0)
        logger.info("✅ SERP cache MongoDB enabled")
    except Exception as e:
        logger.warning(f"⚠️  SERP cache disabled: {e}")
        _cache_collection = None

def _cache_key(provider: str, query: str, count: int) -> str:
    return f"{provider}:{count}:{query.strip().lower()}"

def _cache_get(provider: str, query: str, count: int) -> Optional[List[Dict]]:
    """Obține rezultate din cache"""
    if _cache_collection is None:
        return None
    try:
        doc = _cache_collection.find_one(
            {"key": _cache_key(provider, query, count)},
            {"_id": 0, "results": 1, "expires_at": 1}
        )
        if doc and doc.get("expires_at") and doc["expires_at"] > datetime.now(timezone.utc):
            return doc.get("results")
    except Exception as e:
        logger.debug(f"Cache get error: {e}")
    return None

def _cache_put(provider: str, query: str, count: int, results: List[Dict]):
    """Salvează rezultate în cache"""
    if _cache_collection is None:
        return
    try:
        _cache_collection.update_one(
            {"key": _cache_key(provider, query, count)},
            {"$set": {
                "results": results,
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=_CACHE_TTL),
                "updated_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
    except Exception as e:
        logger.debug(f"Cache put error: {e}")

# ================================================================================
# PROVIDERS
# ================================================================================

def _search_brave(query: str, num_results: int = 10) -> List[Dict[str, str]]:
    """
    Brave Search API
    Docs: https://brave.com/search/api/
    Free tier: 2000 queries/month
    """
    if not BRAVE_API_KEY:
        raise ValueError("BRAVE_API_KEY not found")
    
    # Check cache
    cached = _cache_get("brave", query, num_results)
    if cached is not None:
        logger.debug(f"✅ Cache hit: brave/{query[:30]}")
        return cached
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {
        "q": query,
        "count": min(num_results, 20),  # Brave max 20
        "safesearch": "off"
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    # Extract results
    results = []
    web_results = data.get("web", {}).get("results", [])
    
    for item in web_results[:num_results]:
        results.append({
            "url": item.get("url", ""),
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "position": len(results) + 1
        })
    
    # Cache results
    _cache_put("brave", query, num_results, results)
    
    logger.info(f"✅ Brave: {len(results)} results for '{query[:40]}'")
    return results

def _search_serpapi(query: str, num_results: int = 10) -> List[Dict[str, str]]:
    """
    SerpAPI (Google Search API)
    Docs: https://serpapi.com/
    Free tier: 100 searches/month
    """
    if not SERPAPI_KEY:
        raise ValueError("SERPAPI_KEY not found")
    
    # Check cache
    cached = _cache_get("serpapi", query, num_results)
    if cached is not None:
        logger.debug(f"✅ Cache hit: serpapi/{query[:30]}")
        return cached
    
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num_results,
        "gl": "ro",  # Romania
        "hl": "ro"   # Romanian
    }
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    # Extract results
    results = []
    for item in data.get("organic_results", [])[:num_results]:
        results.append({
            "url": item.get("link", ""),
            "title": item.get("title", ""),
            "description": item.get("snippet", ""),
            "position": item.get("position", len(results) + 1)
        })
    
    # Cache results
    _cache_put("serpapi", query, num_results, results)
    
    logger.info(f"✅ SerpAPI: {len(results)} results for '{query[:40]}'")
    return results

def _search_bing(query: str, num_results: int = 10) -> List[Dict[str, str]]:
    """
    Bing Web Search API
    Docs: https://docs.microsoft.com/en-us/bing/search-apis/
    Free tier: 1000 transactions/month
    """
    if not BING_API_KEY:
        raise ValueError("BING_V7_SUBSCRIPTION_KEY not found")
    
    # Check cache
    cached = _cache_get("bing", query, num_results)
    if cached is not None:
        logger.debug(f"✅ Cache hit: bing/{query[:30]}")
        return cached
    
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {
        "Ocp-Apim-Subscription-Key": BING_API_KEY
    }
    params = {
        "q": query,
        "count": num_results,
        "mkt": "ro-RO"  # Romania market
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    # Extract results
    results = []
    for item in data.get("webPages", {}).get("value", [])[:num_results]:
        results.append({
            "url": item.get("url", ""),
            "title": item.get("name", ""),
            "description": item.get("snippet", ""),
            "position": len(results) + 1
        })
    
    # Cache results
    _cache_put("bing", query, num_results, results)
    
    logger.info(f"✅ Bing: {len(results)} results for '{query[:40]}'")
    return results

# ================================================================================
# UNIFIED SEARCH WITH AUTO-FALLBACK
# ================================================================================

def search(
    query: str,
    num_results: int = 10,
    provider_order: Optional[List[str]] = None
) -> List[Dict[str, str]]:
    """
    Search with automatic fallback between providers
    
    Args:
        query: Search query
        num_results: Number of results to return
        provider_order: List of providers to try (default: ["brave", "serpapi", "bing"])
    
    Returns:
        List of search results with url, title, description, position
    
    Raises:
        RuntimeError: If all providers fail
    """
    if not query or not query.strip():
        return []
    
    # Default order: Brave (free/cheap) → SerpAPI (paid) → Bing (paid)
    if provider_order is None:
        order_str = os.getenv("SERP_PROVIDER", "brave,serpapi,bing")
        provider_order = [p.strip().lower() for p in order_str.split(",") if p.strip()]
    
    # Check available providers
    available = []
    if BRAVE_API_KEY and "brave" in provider_order:
        available.append("brave")
    if SERPAPI_KEY and "serpapi" in provider_order:
        available.append("serpapi")
    if BING_API_KEY and "bing" in provider_order:
        available.append("bing")
    
    if not available:
        raise RuntimeError(
            "No SERP API keys configured! Set one of: "
            "BRAVE_API_KEY, SERPAPI_KEY, BING_V7_SUBSCRIPTION_KEY"
        )
    
    # Try providers in order
    last_error = None
    for provider in available:
        try:
            if provider == "brave":
                results = _search_brave(query, num_results)
            elif provider == "serpapi":
                results = _search_serpapi(query, num_results)
            elif provider == "bing":
                results = _search_bing(query, num_results)
            else:
                continue
            
            if results:
                logger.info(f"✅ Used provider: {provider} for '{query[:40]}'")
                return results
                
        except Exception as e:
            logger.warning(f"⚠️  Provider {provider} failed: {e}")
            last_error = e
            
            # Check if we should retry or fallback
            status_code = getattr(getattr(e, "response", None), "status_code", 0)
            if status_code in (401, 403, 429, 500, 502, 503, 504):
                # Auth, rate limit, or server errors → try next provider
                continue
            elif isinstance(e, requests.RequestException):
                # Network errors → try next provider
                continue
            else:
                # Other errors → stop trying
                break
    
    # All providers failed
    raise RuntimeError(
        f"All SERP providers failed. Last error: {last_error}\n"
        f"Tried: {', '.join(available)}"
    )

# ================================================================================
# STATUS & DIAGNOSTICS
# ================================================================================

def get_status() -> Dict[str, Any]:
    """Get status of all SERP providers"""
    return {
        "brave": {
            "configured": bool(BRAVE_API_KEY),
            "key_length": len(BRAVE_API_KEY) if BRAVE_API_KEY else 0
        },
        "serpapi": {
            "configured": bool(SERPAPI_KEY),
            "key_length": len(SERPAPI_KEY) if SERPAPI_KEY else 0
        },
        "bing": {
            "configured": bool(BING_API_KEY),
            "key_length": len(BING_API_KEY) if BING_API_KEY else 0
        },
        "cache": {
            "enabled": _CACHE_ENABLED,
            "mongodb": _cache_collection is not None,
            "ttl_days": _CACHE_TTL / 86400
        }
    }

# ================================================================================
# CLI TEST
# ================================================================================

if __name__ == "__main__":
    import sys
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    query = sys.argv[1] if len(sys.argv) > 1 else "protecție la foc România"
    num = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    print(f"\n🔍 Testing SERP search: '{query}' (num={num})\n")
    
    # Show status
    status = get_status()
    print("📊 Provider Status:")
    for provider, info in status.items():
        if provider == "cache":
            print(f"   • {provider}: {'✅' if info['enabled'] else '❌'}")
        else:
            print(f"   • {provider}: {'✅' if info['configured'] else '❌'} "
                  f"(key_len={info['key_length']})")
    print()
    
    # Test search
    try:
        results = search(query, num)
        print(f"✅ Got {len(results)} results:\n")
        for i, r in enumerate(results[:5], 1):
            print(f"{i}. {r['title'][:70]}")
            print(f"   🔗 {r['url']}")
            print(f"   📝 {r['description'][:100]}...")
            print()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
