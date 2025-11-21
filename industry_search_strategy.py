#!/usr/bin/env python3
"""
Industry Search Strategy Generator - Generează query-uri de căutare inteligente cu DeepSeek
Analizează site-ul, secționează în subdomenii și propune cuvinte cheie pentru fiecare
"""

import asyncio
import json
import logging
from typing import Dict, List, Any
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import os

from tools.deepseek_client import reasoner_chat

load_dotenv(override=True)

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")

class IndustrySearchStrategyGenerator:
    """Generează strategii de căutare pentru indexarea industriei"""
    
    def __init__(self):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client[MONGO_DB]
        self.agents_collection = self.db.site_agents
        self.site_content_collection = self.db.site_content
        self.strategies_collection = self.db.industry_search_strategies
    
    async def generate_search_strategy(self, agent_id: str) -> Dict[str, Any]:
        """
        Analizează site-ul agentului și generează strategii de căutare
        
        Returns:
            {
                "subdomains": [
                    {
                        "name": "Nume subdomeniu",
                        "description": "Descriere",
                        "search_queries": ["query1", "query2", ...],
                        "keywords": ["keyword1", "keyword2", ...]
                    }
                ],
                "overall_strategy": "Strategie generală",
                "priority_areas": ["Area1", "Area2"]
            }
        """
        try:
            logger.info(f"🔍 Generez strategie de căutare pentru agent {agent_id}...")
            
            # 1. Obține datele agentului
            agent = self.agents_collection.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                raise ValueError(f"Agent {agent_id} nu există")
            
            domain = agent.get("domain", "")
            site_url = agent.get("site_url", "")
            
            # 2. Obține conținutul site-ului din MongoDB
            try:
                agent_id_obj = ObjectId(agent_id)
                content_docs = list(self.site_content_collection.find(
                    {"agent_id": agent_id_obj},
                    {"content": 1, "url": 1, "_id": 0}
                ).limit(50))  # Limitează la primele 50 documente
            except:
                content_docs = list(self.site_content_collection.find(
                    {"agent_id": agent_id},
                    {"content": 1, "url": 1, "_id": 0}
                ).limit(50))
            
            if not content_docs:
                logger.warning(f"⚠️ Agent {agent_id} nu are conținut în MongoDB")
                content_text = f"Site: {domain} - {site_url}\n\nConținut minimal disponibil."
            else:
                # Concatenează conținutul (max 50000 caractere pentru DeepSeek)
                content_text = "\n\n".join([
                    f"[URL: {doc.get('url', 'N/A')}]\n{doc.get('content', '')[:2000]}"
                    for doc in content_docs[:20]
                ])[:50000]
            
            logger.info(f"   📄 Conținut extras: {len(content_text)} caractere din {len(content_docs)} documente")
            
            # 3. Obține informații despre servicii (dacă există)
            services = agent.get("services_products", [])
            if isinstance(services, str):
                try:
                    services = json.loads(services)
                except:
                    services = []
            
            services_text = ""
            if services:
                services_text = "\n\nServicii identificate:\n" + "\n".join([
                    f"- {s.get('name', s) if isinstance(s, dict) else s}"
                    for s in services[:10]
                ])
            
            # 4. Construiește prompt pentru DeepSeek
            prompt = f"""Analizează următorul site web și generează o strategie de căutare pentru indexarea competitorilor și resurselor din industrie.

# SITE ANALIZAT
Domain: {domain}
URL: {site_url}
{services_text}

# CONȚINUT SITE
{content_text}

# SARCINA TA
1. **Secționează site-ul în SUBDOMENII/CATEGORII de servicii/produse**
   - Identifică 3-8 subdomenii principale bazate pe conținutul site-ului
   - Fiecare subdomeniu reprezintă o categorie de servicii sau o linie de business

2. **Pentru fiecare subdomeniu, generează:**
   - **search_queries**: 5-10 query-uri de căutare Google pentru a găsi competitori și resurse
     * Exemple: "best [service] providers in Romania", "[service] companies near me", etc.
   - **keywords**: 10-15 cuvinte cheie relevante pentru subdomeniul respectiv
     * Exemple: termeni tehnici, sinonime, variante în română și engleză

3. **Strategie generală:**
   - Recomandări pentru cercetarea industriei
   - Zone prioritare de investigat
   - Oportunități de diferențiere

# FORMAT RĂSPUNS (JSON strict)
{{
  "subdomains": [
    {{
      "name": "Nume subdomeniu (ex: 'Sisteme Antiincendiu')",
      "description": "Descriere scurtă a subdomeniului",
      "search_queries": [
        "query Google 1 pentru găsirea competitorilor",
        "query Google 2",
        "query Google 3",
        "..."
      ],
      "keywords": [
        "keyword1",
        "keyword2",
        "..."
      ]
    }}
  ],
  "overall_strategy": "Strategie generală de cercetare a industriei",
  "priority_areas": [
    "Zona prioritară 1",
    "Zona prioritară 2"
  ]
}}

Returnează DOAR JSON-ul, fără alte explicații."""

            # 5. Apelează DeepSeek
            logger.info("   🤖 Apelez DeepSeek pentru analiza strategică...")
            
            try:
                response = await asyncio.wait_for(
                    reasoner_chat(
                        prompt=prompt,
                        model="deepseek-reasoner",
                        temperature=0.3,
                        max_tokens=8000
                    ),
                    timeout=180.0  # 3 minute timeout
                )
            except asyncio.TimeoutError:
                logger.error("❌ DeepSeek timeout după 3 minute")
                raise ValueError("DeepSeek timeout - procesarea a durat prea mult")
            except Exception as e:
                logger.error(f"❌ Eroare DeepSeek: {e}")
                raise
            
            logger.info(f"   ✅ Răspuns DeepSeek primit: {len(response)} caractere")
            
            # 6. Parsează răspunsul JSON
            try:
                # Extrage JSON din răspuns
                response_clean = response.strip()
                
                # Găsește primul { și ultimul }
                start_idx = response_clean.find('{')
                end_idx = response_clean.rfind('}')
                
                if start_idx == -1 or end_idx == -1:
                    raise ValueError("Răspuns DeepSeek nu conține JSON valid")
                
                json_str = response_clean[start_idx:end_idx+1]
                strategy = json.loads(json_str)
                
                # Validare structură
                if "subdomains" not in strategy:
                    raise ValueError("JSON nu conține câmpul 'subdomains'")
                
                logger.info(f"   ✅ Strategie parsată: {len(strategy.get('subdomains', []))} subdomenii")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Eroare parsare JSON DeepSeek: {e}")
                logger.error(f"Răspuns DeepSeek:\n{response[:1000]}")
                
                # Fallback: creează o strategie minimă
                strategy = {
                    "subdomains": [
                        {
                            "name": f"Servicii {domain}",
                            "description": f"Servicii și produse oferite de {domain}",
                            "search_queries": [
                                f"{domain} competitors",
                                f"companies like {domain}",
                                f"{domain} alternatives",
                                f"best {domain} services",
                                f"{domain} industry Romania"
                            ],
                            "keywords": [
                                domain.split('.')[0],
                                "services",
                                "Romania",
                                "business",
                                "company"
                            ]
                        }
                    ],
                    "overall_strategy": f"Cercetare competitori și resurse pentru {domain}",
                    "priority_areas": ["Competitori direcți", "Furnizori servicii similare"]
                }
            
            # 7. Salvează strategia în MongoDB
            strategy_doc = {
                "agent_id": agent_id,
                "domain": domain,
                "strategy": strategy,
                "created_at": datetime.now(timezone.utc),
                "model": "deepseek-reasoner",
                "status": "completed"
            }
            
            # Upsert
            self.strategies_collection.update_one(
                {"agent_id": agent_id},
                {"$set": strategy_doc},
                upsert=True
            )
            
            logger.info(f"✅ Strategie de căutare salvată pentru agent {agent_id}")
            
            return strategy
            
        except Exception as e:
            logger.error(f"❌ Eroare generare strategie căutare: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

# Instanță globală
search_strategy_generator = IndustrySearchStrategyGenerator()

