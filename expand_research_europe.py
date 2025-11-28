#!/usr/bin/env python3
"""
Script pentru extinderea research-ului pe Europa pentru tehnica-antifoc.ro
Keyword: "passive fire protection"
Countries: Major European countries
"""

import os
import sys
import logging
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse
import tldextract
from pymongo import MongoClient
from bson import ObjectId

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/europe_research.log")
    ]
)
logger = logging.getLogger(__name__)

# Configuration
AGENT_ID = "69124d1aa55790fced19d30d"  # tehnica-antifoc.ro
KEYWORD = "passive fire protection"
COUNTRIES = [
    "GB", "DE", "FR", "IT", "ES", "NL", "PL", "BE", "SE", "AT", "DK", "FI", "IE", "PT"
]

# Load API Keys
def _load_brave_key() -> str:
    k = (os.getenv("BRAVE_API_KEY") or "").strip()
    if k:
        return k
    for p in (".secrets/brave.key", os.path.expanduser("~/.config/ai_agents/brave.key")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                k = f.read().strip()
                if k:
                    return k
        except FileNotFoundError:
            pass
    return ""

BRAVE_API_KEY = _load_brave_key()
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
DB_NAME = os.getenv("MONGODB_DATABASE", "ai_agents_db")

def connect_db():
    client = MongoClient(MONGODB_URI)
    return client[DB_NAME]

def normalize_domain(url):
    try:
        extracted = tldextract.extract(url)
        return f"{extracted.domain}.{extracted.suffix}"
    except:
        return urlparse(url).netloc

def search_brave_country(query, country_code, num_results=10):
    """Search using Brave API with specific country code"""
    if not BRAVE_API_KEY:
        logger.warning("⚠️ BRAVE_API_KEY not found, skipping Brave search")
        return []

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {
        "q": query,
        "count": min(num_results, 20),
        "country": country_code,
        "safesearch": "off"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        results = []
        web_results = data.get("web", {}).get("results", [])
        
        for item in web_results[:num_results]:
            results.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "position": len(results) + 1,
                "source_country": country_code
            })
        return results
    except Exception as e:
        logger.error(f"❌ Brave search failed for {country_code}: {e}")
        return []

def search_serpapi_country(query, country_code, num_results=10):
    """Search using SerpAPI with specific country code (gl)"""
    if not SERPAPI_KEY:
        logger.warning("⚠️ SERPAPI_KEY not found, skipping SerpAPI search")
        return []

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num_results,
        "gl": country_code.lower(),
        "hl": country_code.lower()
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("organic_results", [])[:num_results]:
            results.append({
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "description": item.get("snippet", ""),
                "position": item.get("position", len(results) + 1),
                "source_country": country_code
            })
        return results
    except Exception as e:
        logger.error(f"❌ SerpAPI search failed for {country_code}: {e}")
        return []

def main():
    logger.info(f"🚀 Starting Europe Research Expansion for agent {AGENT_ID}")
    logger.info(f"🎯 Keyword: '{KEYWORD}'")
    logger.info(f"🌍 Target Countries: {', '.join(COUNTRIES)}")

    db = connect_db()
    
    # 1. Verify Agent
    agent = db.site_agents.find_one({"_id": ObjectId(AGENT_ID)})
    if not agent:
        logger.error("❌ Agent not found!")
        return

    logger.info(f"✅ Found agent: {agent.get('domain')}")

    # Add keyword if not exists
    current_keywords = agent.get("keywords", [])
    if KEYWORD not in current_keywords:
        logger.info(f"➕ Adding keyword '{KEYWORD}' to agent...")
        db.site_agents.update_one(
            {"_id": ObjectId(AGENT_ID)},
            {"$addToSet": {"keywords": KEYWORD}}
        )
    
    # 2. Run Search for Each Country
    total_sites_found = 0
    new_sites_found = 0
    
    # Prepare competitive map update
    competitive_map = db.competitive_map.find_one({"agent_id": AGENT_ID})
    if not competitive_map:
        competitive_map = {
            "agent_id": AGENT_ID,
            "sites": [],
            "keyword_site_mapping": {},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        db.competitive_map.insert_one(competitive_map)
    
    existing_sites_domains = {s.get("domain") for s in competitive_map.get("sites", [])}
    keyword_site_mapping = competitive_map.get("keyword_site_mapping", {})
    
    if KEYWORD not in keyword_site_mapping:
        keyword_site_mapping[KEYWORD] = []

    for country_code in COUNTRIES:
        logger.info(f"🔎 Searching in {country_code}...")
        
        # Try Brave first, then SerpAPI
        results = search_brave_country(KEYWORD, country_code)
        if not results:
            logger.info(f"   ⚠️ Brave failed/empty, trying SerpAPI for {country_code}...")
            results = search_serpapi_country(KEYWORD, country_code)
            
        logger.info(f"   Found {len(results)} results in {country_code}")
            
        for result in results:
            url = result["url"]
            title = result["title"]
            description = result["description"]
            position = result["position"]
            domain = normalize_domain(url)
            
            if not domain:
                continue

            # Save to serp_results
            serp_entry = {
                "agent_id": AGENT_ID,
                "keyword": KEYWORD,
                "url": url,
                "domain": domain,
                "title": title,
                "description": description,
                "position": position,
                "country": country_code,
                "searched_at": datetime.now(timezone.utc)
            }
            
            # Update/Insert SERP Result
            db.serp_results.update_one(
                {"agent_id": AGENT_ID, "keyword": KEYWORD, "url": url, "country": country_code},
                {"$set": serp_entry},
                upsert=True
            )
            
            # Add to Competitive Map Sites
            if domain not in existing_sites_domains:
                site_entry = {
                    "domain": domain,
                    "url": url,
                    "title": title,
                    "description": description,
                    "first_seen_at": datetime.now(timezone.utc),
                    "source_keyword": KEYWORD,
                    "source_country": country_code,
                    "initial_position": position
                }
                logger.info(f"   🆕 New competitor found: {domain} ({country_code})")
                db.competitive_map.update_one(
                    {"agent_id": AGENT_ID},
                    {"$push": {"sites": site_entry}}
                )
                existing_sites_domains.add(domain)
                new_sites_found += 1

            # Add to keyword mapping (allow multiples from diff countries)
            mapping_entry = {
                "domain": domain,
                "position": position,
                "country": country_code,
                "url": url
            }
            
            # Check if this specific entry exists
            exists = False
            for entry in keyword_site_mapping.get(KEYWORD, []):
                if entry.get("domain") == domain and entry.get("country") == country_code:
                    exists = True
                    break
            
            if not exists:
                if KEYWORD not in keyword_site_mapping:
                    keyword_site_mapping[KEYWORD] = []
                keyword_site_mapping[KEYWORD].append(mapping_entry)

            total_sites_found += 1

    # Update keyword mapping in DB
    db.competitive_map.update_one(
        {"agent_id": AGENT_ID},
        {"$set": {
            "keyword_site_mapping": keyword_site_mapping,
            "updated_at": datetime.now(timezone.utc)
        }}
    )

    logger.info("\n🏁 Research Complete!")
    logger.info(f"📊 Total Results Processed: {total_sites_found}")
    logger.info(f"✨ New Unique Competitors: {new_sites_found}")

if __name__ == "__main__":
    main()

