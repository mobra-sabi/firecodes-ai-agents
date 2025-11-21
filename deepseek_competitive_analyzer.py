#!/usr/bin/env python3
"""
DeepSeek Competitive Analyzer - Primește TOT contextul agentului și generează analiză strategică
"""

import json
import logging
from typing import Dict, List, Any
from pymongo import MongoClient
from bson import ObjectId

# Import modulele existente
from qdrant_context_enhancer import get_context_enhancer
from llm_orchestrator import get_orchestrator

logger = logging.getLogger(__name__)

class DeepSeekCompetitiveAnalyzer:
    """
    Analizator competitiv care folosește DeepSeek cu TOT contextul disponibil
    """
    
    def __init__(self):
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client["ai_agents_db"]
        self.context_enhancer = get_context_enhancer()
        self.llm = get_orchestrator()  # 🎭 LLM Orchestrator cu DeepSeek + fallback
        
    def get_full_agent_context(self, agent_id: str) -> Dict[str, Any]:
        """
        Obține TOATE datele despre agent din MongoDB + Qdrant
        
        Returns:
            Dict cu:
            - agent_info: date de bază
            - content_chunks: conținut complet din MongoDB
            - vector_context: context semantic din Qdrant
            - services: servicii identificate
            - contact_info: informații de contact
        """
        agent = self.db.site_agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # 1. Date de bază agent
        agent_info = {
            "domain": agent.get("domain"),
            "site_url": agent.get("site_url"),
            "name": agent.get("name"),
            "business_type": agent.get("business_type", "general"),
            "status": agent.get("status"),
            "validation_passed": agent.get("validation_passed")
        }
        
        # 2. Conținut complet din MongoDB
        content_chunks = list(self.db.site_content.find({"agent_id": ObjectId(agent_id)}))
        total_content = "\n\n".join([
            chunk.get("content", "") 
            for chunk in content_chunks 
            if chunk.get("content")
        ])
        
        # 3. Context semantic din Qdrant (topics relevante)
        vector_context = {}
        try:
            # Construiește numele corect al collection-ului
            domain = agent.get("domain", "").replace(".", "_")
            collection_name = f"construction_{domain}"
            
            logger.info(f"🔍 Folosesc Qdrant collection: {collection_name}")
            
            topics = [
                "servicii și produse principale",
                "puncte forte și avantaje",
                "clienți și piață țintă",
                "domenii de activitate",
                "expertize și specializări"
            ]
            
            for topic in topics:
                try:
                    contexts = self.context_enhancer.get_context_for_query(
                        query=topic,
                        collection_name=collection_name,
                        top_k=3
                    )
                    vector_context[topic] = contexts
                except Exception as topic_error:
                    logger.warning(f"Could not get context for topic '{topic}': {topic_error}")
                    vector_context[topic] = []
                
        except Exception as e:
            logger.warning(f"Could not get vector context: {e}")
            vector_context = {}
        
        # 4. Servicii
        services = agent.get("services", [])
        
        # 5. Contact info
        contact_info = agent.get("contact_info", {})
        
        # 6. Statistici
        stats = {
            "total_chunks": len(content_chunks),
            "total_characters": len(total_content),
            "services_count": len(services),
            "has_vector_context": bool(vector_context)
        }
        
        return {
            "agent_info": agent_info,
            "content_full": total_content[:50000],  # Limită pentru token efficiency
            "content_chunks_count": len(content_chunks),
            "vector_context": vector_context,
            "services": services,
            "contact_info": contact_info,
            "stats": stats
        }
    
    def analyze_for_competition_discovery(self, agent_id: str) -> Dict[str, Any]:
        """
        TASK 1: Descompune site-ul în subdomenii și generează cuvinte cheie pentru Google search
        
        Returns:
            {
                "subdomains": [
                    {
                        "name": "...",
                        "description": "...",
                        "keywords": ["...", "..."]
                    }
                ],
                "overall_keywords": ["...", "..."],
                "industry": "...",
                "target_market": "..."
            }
        """
        logger.info(f"🎯 Analizez agent {agent_id} pentru descoperire competiție...")
        
        # Obține TOT contextul
        full_context = self.get_full_agent_context(agent_id)
        
        # Construiește prompt pentru DeepSeek
        prompt = self._build_competition_discovery_prompt(full_context)
        
        # Trimite la DeepSeek
        logger.info(f"📤 Trimit context complet către DeepSeek ({len(prompt)} caractere)")
        
        try:
            # 🎭 Folosim Orchestrator cu DeepSeek + fallback
            response = self.llm.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "Ești un expert în analiză competitivă și strategii de marketing. "
                                   "Analizezi site-uri web și identifici domenii de activitate, servicii, "
                                   "și generezi cuvinte cheie pentru descoperirea concurenței pe Google."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.7
            )
            
            # LLMOrchestrator.chat() returnează STRING direct, nu dict
            if isinstance(response, str):
                result = self._parse_deepseek_response(response)
            elif isinstance(response, dict) and response.get("success"):
                # Fallback pentru cazul în care ar returna dict
                result = self._parse_deepseek_response(response["content"])
            else:
                raise Exception(f"LLM failed: Invalid response type {type(response)}")
            
            # Salvează analiza în MongoDB
            self._save_analysis(agent_id, result)
            
            logger.info(f"✅ Analiză completă pentru {agent_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Eroare la analiza DeepSeek: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _build_competition_discovery_prompt(self, context: Dict[str, Any]) -> str:
        """Construiește prompt structurat pentru DeepSeek"""
        
        agent_info = context["agent_info"]
        content = context["content_full"]
        services = context["services"]
        vector_context = context["vector_context"]
        
        # Construiește secțiunea de servicii
        services_text = ""
        if services:
            services_text = "\n**SERVICII IDENTIFICATE:**\n"
            for i, svc in enumerate(services[:20], 1):
                if isinstance(svc, dict):
                    name = svc.get("service_name") or svc.get("name", "")
                    desc = svc.get("description", "")
                    services_text += f"{i}. {name}\n"
                    if desc:
                        services_text += f"   Descriere: {desc[:200]}\n"
                else:
                    services_text += f"{i}. {svc}\n"
        
        # Construiește context semantic
        semantic_context = ""
        if vector_context:
            semantic_context = "\n**CONTEXT SEMANTIC DIN QDRANT (cele mai relevante informații):**\n"
            for topic, contexts in vector_context.items():
                if contexts:
                    semantic_context += f"\n• {topic.upper()}:\n"
                    for ctx in contexts[:2]:
                        semantic_context += f"  - {ctx['text'][:300]}...\n"
        
        prompt = f"""Analizează acest site web pentru a identifica subdomenii de activitate și cuvinte cheie pentru Google search.

═══════════════════════════════════════════════════════════════════════

**INFORMAȚII DESPRE SITE:**
- Domeniu: {agent_info['domain']}
- URL: {agent_info['site_url']}
- Nume: {agent_info['name']}
- Tip business: {agent_info['business_type']}

{services_text}

{semantic_context}

**CONȚINUT COMPLET AL SITE-ULUI:**
{content[:30000]}

═══════════════════════════════════════════════════════════════════════

**TASK: DESCOMPUNERE ÎN SUBDOMENII ȘI GENERARE CUVINTE CHEIE**

Te rog să analizezi site-ul și să returnezi un JSON cu următoarea structură:

{{
  "industry": "numele industriei principale (ex: protecție la foc, construcții, etc)",
  "target_market": "piața țintă principală",
  "subdomains": [
    {{
      "name": "Nume subdomeniu (ex: Protecție pasivă la foc)",
      "description": "Descriere frumoasă și detaliată a subdomeniului, ce servicii include, pentru cine e destinat, ce probleme rezolvă (2-3 propoziții)",
      "main_services": ["serviciu1", "serviciu2"],
      "keywords": [
        "cuvânt cheie 1 pentru Google search",
        "cuvânt cheie 2 pentru Google search",
        "cuvânt cheie 3 pentru Google search"
      ]
    }}
  ],
  "overall_keywords": [
    "cuvinte cheie generale pentru toată industria",
    "folosite pentru a găsi competitori generali"
  ],
  "competitive_positioning": "Cum se poziționează compania în piață (1-2 propoziții)"
}}

**INSTRUCȚIUNI:**
1. Identifică 3-7 subdomenii principale de activitate
2. Pentru fiecare subdomeniu, scrie o descriere clară și atrăgătoare
3. Generează 5-10 cuvinte cheie SPECIFICE pentru fiecare subdomeniu
4. Cuvintele cheie trebuie să fie:
   - Specifice domeniului (nu generice)
   - Utile pentru Google search (combină serviciu + industrie + locație dacă e relevant)
   - În română (dacă site-ul e în română)
   - Variații: singular/plural, sinonime
5. Adaugă 10-15 cuvinte cheie generale pentru toată industria

**EXEMPLU DE CUVINTE CHEIE BUNE:**
- "protecție la foc structuri metalice București"
- "termoprotecție vopsea intumescentă"
- "ignifugare lemn certificată"
- "sisteme antiincendiu pasive"

**RETURNEAZĂ DOAR JSON-UL, FĂRĂ MARKDOWN SAU ALT TEXT!**
"""
        
        return prompt
    
    def _parse_deepseek_response(self, response: Any) -> Dict[str, Any]:
        """Parsează răspunsul de la DeepSeek"""
        
        # Extrage conținutul
        content = ""
        if isinstance(response, dict):
            if "data" in response:
                choices = response["data"].get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
            elif "content" in response:
                content = response["content"]
            else:
                content = str(response)
        else:
            content = str(response)
        
        # Curăță JSON (elimină markdown code blocks dacă există)
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parsează JSON
        try:
            result = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Content: {content[:500]}")
            # Returnează structură minimă
            return {
                "industry": "unknown",
                "target_market": "unknown",
                "subdomains": [],
                "overall_keywords": [],
                "competitive_positioning": "Analiză incompletă",
                "_raw_response": content[:1000]
            }
    
    def _save_analysis(self, agent_id: str, analysis: Dict[str, Any]):
        """Salvează analiza în MongoDB"""
        from datetime import datetime, timezone
        
        doc = {
            "agent_id": ObjectId(agent_id),
            "analysis_type": "competition_discovery",
            "analysis_data": analysis,
            "created_at": datetime.now(timezone.utc),
            "status": "completed"
        }
        
        # Salvează în colecția competitive_analysis
        self.db.competitive_analysis.update_one(
            {
                "agent_id": ObjectId(agent_id),
                "analysis_type": "competition_discovery"
            },
            {"$set": doc},
            upsert=True
        )
        
        # ✅ FIX: Extrage și salvează keywords în documentul agentului
        all_keywords = []
        subdomains_list = []
        keywords_per_subdomain = {}
        
        # Extrage keywords din subdomenii
        for subdomain in analysis.get("subdomains", []):
            subdomain_name = subdomain.get("name", "")
            subdomain_keywords = subdomain.get("keywords", [])
            
            if subdomain_name:
                subdomains_list.append(subdomain_name)
                keywords_per_subdomain[subdomain_name] = subdomain_keywords
                all_keywords.extend(subdomain_keywords)
        
        # Adaugă keywords generale
        overall_keywords = analysis.get("overall_keywords", [])
        all_keywords.extend(overall_keywords)
        
        # Update agent cu keywords, subdomenii și industrie
        update_doc = {
            "keywords": all_keywords,
            "subdomains": subdomains_list,
            "keywords_per_subdomain": keywords_per_subdomain,
            "overall_keywords": overall_keywords,
            "industry": analysis.get("industry", ""),
            "target_market": analysis.get("target_market", ""),
            "competitive_positioning": analysis.get("competitive_positioning", ""),
            "keywords_generated_at": datetime.now(timezone.utc),
            "status": "keywords_generated"
        }
        
        # Update în ambele colecții (site_agents și agents)
        result = self.db.site_agents.update_one(
            {"_id": ObjectId(agent_id)},
            {"$set": update_doc}
        )
        
        if result.matched_count == 0:
            # Încearcă în colecția agents dacă nu e în site_agents
            self.db.agents.update_one(
                {"_id": ObjectId(agent_id)},
                {"$set": update_doc}
            )
        
        logger.info(f"💾 Analiză salvată în MongoDB pentru agent {agent_id}")
        logger.info(f"✅ Salvate {len(all_keywords)} keywords ({len(subdomains_list)} subdomenii) în agent!")


# Factory function
def get_analyzer():
    """Get or create analyzer instance"""
    return DeepSeekCompetitiveAnalyzer()
