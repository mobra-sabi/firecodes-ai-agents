#!/usr/bin/env python3
"""
Script pentru generarea unei propuneri de site nou pentru tehnica-antifoc.ro
bazată pe analiza competitorilor europeni descoperiți.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure local imports work
sys.path.append("/srv/hf/ai_agents")

from llm_helper import call_llm_with_fallback

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Config
AGENT_ID = "69124d1aa55790fced19d30d"
KEYWORD = "passive fire protection"
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27018/")
DB_NAME = os.getenv("MONGODB_DATABASE", "ai_agents_db")

def connect_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

def get_competitor_data(db):
    """Collect data from SERP results regarding the keyword"""
    logger.info("📊 Collecting competitor data...")
    
    # Aggregate unique domains and their titles/descriptions
    pipeline = [
        {
            "$match": {
                "agent_id": AGENT_ID,
                "keyword": KEYWORD
            }
        },
        {
            "$group": {
                "_id": "$domain",
                "titles": {"$addToSet": "$title"},
                "descriptions": {"$addToSet": "$description"},
                "countries": {"$addToSet": "$country"},
                "avg_position": {"$avg": "$position"}
            }
        },
        {"$sort": {"avg_position": 1}},
        {"$limit": 20}
    ]
    
    results = list(db.serp_results.aggregate(pipeline))
    return results

def generate_proposal(competitors):
    """Generate site proposal using LLM"""
    logger.info("🧠 Generating site proposal with DeepSeek...")
    
    competitor_summary = ""
    for comp in competitors:
        competitor_summary += f"- Domain: {comp['_id']}\n"
        competitor_summary += f"  Countries: {', '.join(comp['countries'])}\n"
        competitor_summary += f"  Key Content Topics: {'; '.join(comp['titles'][:3])}\n\n"

    prompt = f"""
    You are an expert Web Architect and SEO Strategist specializing in the construction and fire safety industry.
    
    **Goal:** Create a complete website reconstruction plan for 'tehnica-antifoc.ro' (a Romanian passive fire protection company) based on the best European models we found.
    
    **Context:** We have analyzed top competitors across Europe for the keyword 'passive fire protection'.
    
    **Top Competitors Analyzed:**
    {competitor_summary}
    
    **Task:**
    Propose a modern, high-converting website structure built "from scratch" using these models.
    
    **Requirements:**
    1. **Sitemap Structure:** Detailed hierarchy (Home, Services, Sectors, Knowledge Hub, Contact).
    2. **Homepage Layout:** Key sections needed for trust and conversion.
    3. **Service Pages:** Specific pages derived from competitor analysis (e.g., structural steel protection, fire stopping, etc.).
    4. **Content Strategy:** What unique value propositions (UVPs) should be highlighted?
    5. **Technical Features:** Essential features for this industry (e.g., case studies, certification downloads).
    
    **Format:**
    Return the response in valid JSON format with the following structure:
    {{
        "site_title": "Proposed Site Title",
        "uvp": "Main Unique Value Proposition",
        "sitemap": [
            {{
                "page": "Page Name",
                "url": "/page-url",
                "purpose": "Brief description of page purpose",
                "key_sections": ["Section 1", "Section 2"]
            }}
        ],
        "homepage_structure": [
            {{
                "section": "Hero Section",
                "content_focus": "What to write here"
            }}
        ],
        "recommended_content_topics": ["Topic 1", "Topic 2"]
    }}
    """
    
    response = call_llm_with_fallback(
        prompt=prompt,
        model_preference="deepseek",
        max_tokens=3000,
        temperature=0.7
    )
    
    # Clean code blocks if any
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0].strip()
    elif "```" in response:
        response = response.split("```")[1].split("```")[0].strip()
        
    return json.loads(response)

def save_proposal_to_file(proposal):
    """Save the proposal to a local file instead of DB"""
    filename = "PROPUNERE_SITE_NOU_TEHNICA_ANTIFOC.md"
    
    content = f"""# 🏗️ Propunere Reconstrucție Site: tehnica-antifoc.ro
**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Bazat pe:** Analiza competitorilor europeni (Passive Fire Protection)

## 🎯 Titlu Propus
{proposal.get('site_title', 'N/A')}

## 💎 Unique Value Proposition (UVP)
{proposal.get('uvp', 'N/A')}

## 🗺️ Sitemap Structura
"""
    
    for page in proposal.get('sitemap', []):
        content += f"\n### {page.get('page')} (`{page.get('url')}`)\n"
        content += f"- **Scop:** {page.get('purpose')}\n"
        content += f"- **Secțiuni Cheie:** {', '.join(page.get('key_sections', []))}\n"

    content += "\n## 🏠 Structura Homepage\n"
    for section in proposal.get('homepage_structure', []):
        content += f"- **{section.get('section')}:** {section.get('content_focus')}\n"

    content += "\n## 📚 Teme de Conținut Recomandate\n"
    for topic in proposal.get('recommended_content_topics', []):
        content += f"- {topic}\n"
        
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
        
    logger.info(f"✅ Propunere salvată în fișierul: {filename}")
    return filename

def main():
    db = connect_db()
    
    # 1. Get Competitor Data
    competitors = get_competitor_data(db)
    if not competitors:
        logger.error("❌ No competitor data found! Did you run the research script?")
        return

    logger.info(f"Found {len(competitors)} top competitors to analyze.")
    
    # 2. Generate Proposal
    try:
        proposal = generate_proposal(competitors)
        
        # 3. Save Proposal to FILE ONLY
        filename = save_proposal_to_file(proposal)
        
        # 4. Output Result for User
        print("\n" + "="*50)
        print(f"🚀 PROPOSAL GENERATED & SAVED TO: {filename}")
        print("="*50)
        # print(json.dumps(proposal, indent=2)) # Optional: print to console too
        
    except Exception as e:
        logger.error(f"❌ Failed to generate proposal: {e}")

if __name__ == "__main__":
    main()

