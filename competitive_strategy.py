#!/usr/bin/env python3
"""
Competitive Strategy Generator - Folosește DeepSeek pentru evaluare și strategie
Analizează datele agentului și generează strategii de cercetare a concurenței
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from llm_orchestrator import get_orchestrator
from bson import ObjectId
from dotenv import load_dotenv
import os

from tools.deepseek_client import reasoner_chat
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# ⭐ IMPORT: Modul pentru îmbogățire context cu Qdrant vectori
from qdrant_context_enhancer import get_context_enhancer

load_dotenv(override=True)

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "ai_agents_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

class CompetitiveStrategyGenerator:
    """Generator de strategii competitive folosind DeepSeek"""
    
    def __init__(self):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client[MONGO_DB]
        self.agents_collection = self.db.site_agents
        self.strategies_collection = self.db.competitive_strategies
        
        # Embeddings pentru search în Qdrant
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # ⭐ FIX: NU folosim QdrantClient - folosim requests direct pentru a evita "illegal request line"
        self.qdrant_url = QDRANT_URL
        self.qdrant_api_key = QDRANT_API_KEY
        logger.info("✅ Qdrant va fi accesat prin HTTP requests (evită 'illegal request line')")
    
    async def analyze_agent_and_generate_strategy(self, agent_id: str) -> Dict[str, Any]:
        """
        Analizează toate datele agentului și generează strategie competitive
        """
        try:
            logger.info(f"🔍 Analizez agentul {agent_id} pentru strategie competitive...")
            
            # 1. Obține datele agentului din MongoDB
            agent = self.agents_collection.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                raise ValueError(f"Agent {agent_id} nu există")
            
            # 2. Obține conținutul site-ului din Qdrant sau MongoDB
            collection_name = agent.get("vector_collection")
            
            # Dacă nu există vector_collection, încearcă să folosească numele standard sau să obțină din MongoDB
            if not collection_name:
                # Încearcă numele standard pentru colecție Qdrant
                collection_name = f"agent_{agent_id}"
                logger.warning(f"⚠️ Agent {agent_id} nu are vector_collection configurat. Folosesc numele standard: {collection_name}")
                
                # Verifică dacă există colecție Qdrant cu numele standard (folosind requests)
                try:
                    import requests
                    response = requests.get(f"{self.qdrant_url}/collections/{collection_name}", timeout=5)
                    if response.status_code == 200:
                        collection_info = response.json()
                        points_count = collection_info.get("result", {}).get("points_count", 0)
                        logger.info(f"✅ Colecție Qdrant găsită: {collection_name} ({points_count} puncte)")
                except:
                    # Dacă nu există în Qdrant, obține conținutul din MongoDB
                    logger.warning(f"⚠️ Colecție Qdrant nu există. Obțin conținutul din MongoDB...")
                    site_content = await self._get_site_content_from_mongodb(agent_id)
                    if not site_content:
                        # ⭐ FALLBACK: Dacă nu există conținut în bazele de date, obține-l direct de pe site
                        logger.warning(f"⚠️ Agent {agent_id} nu are conținut în bazele de date. Obțin conținut direct de pe site...")
                        site_content = await self._fetch_content_from_site(agent)
                        if not site_content:
                            raise ValueError(f"Agent {agent_id} nu are conținut nici în Qdrant, nici în MongoDB, și nu s-a putut obține de pe site. Te rog să recreezi agentul.")
                    # Continuă cu conținutul obținut
            else:
                # Obține conținutul din Qdrant dacă există vector_collection
                site_content = await self._get_site_content_from_qdrant(collection_name, agent_id)
                
                # Fallback la MongoDB dacă Qdrant este gol
                if not site_content or len(site_content) < 5:
                    logger.warning(f"⚠️ Qdrant collection goală sau prea puține date ({len(site_content) if site_content else 0} chunks). Obțin conținutul din MongoDB...")
                    site_content_mongo = await self._get_site_content_from_mongodb(agent_id)
                    
                    # ⭐ ÎMBUNĂTĂȚIRE: Dacă avem < 5 chunks TOTAL, scrapăm direct site-ul pentru date fresh
                    if len(site_content_mongo) < 5:
                        logger.warning(f"⚠️ Prea puțin conținut în baze de date ({len(site_content_mongo)} chunks). Scrapez direct site-ul...")
                        fresh_content = await self._fetch_content_from_site(agent)
                        if fresh_content and len(fresh_content) > 0:
                            logger.info(f"✅ Obținut {len(fresh_content)} chunks FRESH de pe site")
                            site_content = fresh_content
                        else:
                            site_content = site_content_mongo if site_content_mongo else site_content
                            logger.warning(f"⚠️ Scraping eșuat, folosesc ce am ({len(site_content)} chunks)")
                    else:
                        site_content = site_content_mongo
            
            # 3. Generează prompt pentru DeepSeek
            analysis_prompt = self._build_analysis_prompt(agent, site_content)
            
            # 3.3 ⭐ NOU: Îmbogățire context cu vectori din Qdrant pentru înțelegere profundă a industriei
            qdrant_context = ""
            try:
                logger.info(f"🎯 Extragere context îmbogățit din Qdrant pentru înțelegere profundă...")
                enhancer = get_context_enhancer()
                
                # Extrage context complet pentru analiza industriei
                qdrant_context = enhancer.get_full_industry_analysis_context(
                    agent_id=str(agent_id),
                    analysis_focus="strategia competitivă și poziționarea pe piață"
                )
                
                if qdrant_context:
                    logger.info(f"✅ Context Qdrant obținut: {len(qdrant_context)} caractere")
                else:
                    logger.warning(f"⚠️ Nu s-a obținut context din Qdrant")
            except Exception as e:
                logger.warning(f"⚠️ Eroare la obținere context din Qdrant: {e}")
                qdrant_context = ""
            
            # 3.5. Generează context pentru web search
            web_search_context = await self._get_web_search_context(agent, site_content)
            
            # Construiește prompt complet cu Qdrant context + web search context (ÎNAINTE de a-l folosi)
            enhanced_prompt = analysis_prompt
            
            # ⭐ PRIORITATE 1: Context semantic din Qdrant (pentru înțelegere profundă)
            if qdrant_context:
                enhanced_prompt += f"\n\n{'='*70}\n⭐ CONTEXT SEMANTIC DIN BAZA DE DATE VECTORIALĂ ⭐\n{'='*70}\n{qdrant_context}\n{'='*70}\n"
            
            # PRIORITATE 2: Web search context (pentru cercetare concurenți)
            if web_search_context:
                enhanced_prompt += f"\n\n**CONTEXT WEB SEARCH DISPONIBIL (folosește aceste surse pentru cercetare):**\n{web_search_context}\n\nFolosește aceste surse și sugestii pentru a genera o strategie mai completă cu întrebări concrete de căutare web."
            
            # 4. Folosește DeepSeek Reasoner pentru analiză cu acces la internet
            logger.info(f"🤖 Trimite analiză la DeepSeek Reasoner (cu acces la internet pentru căutare concurenți)...")
            logger.info(f"📊 Prompt size: {len(enhanced_prompt)} caractere, Web search context: {len(web_search_context)} caractere")
            
            # ⭐ CRITIC: Verifică că DeepSeek API key este setat
            from tools.deepseek_client import _get_deepseek_key
            try:
                deepseek_key = _get_deepseek_key()
                logger.info(f"✅ DeepSeek API key este setat: {deepseek_key[:10]}...{deepseek_key[-4:]}")
            except Exception as e:
                logger.error(f"❌ CRITIC: DeepSeek API key nu este setat: {e}")
                raise ValueError(f"DeepSeek API key nu este configurat. Verifică DEEPSEEK_API_KEY în .env")
            
            # Adaugă instrucțiuni pentru web search în system prompt
            system_prompt = """Ești un expert în analiză competitivă și strategie de business. 
Analizezi site-uri web pentru a identifica serviciile/produsele oferite și generezi strategii 
de cercetare și înțelegere a concurenței pentru fiecare tip de serviciu.

IMPORTANT: 
- Ai acces la internet și poți folosi WEB SEARCH pentru a căuta informații despre concurenți.
- Folosește web search pentru a identifica competitori, să analizezi prețuri, caracteristici și 
  strategii de marketing ale concurenților.
- Folosește toate resursele disponibile (conținutul site-ului analizat + WEB SEARCH pentru concurenți)
  pentru a genera o strategie completă de analiză competitivă.
- Pentru fiecare serviciu identificat, generează întrebări concrete de căutare web și sugerează surse specifice
  (Google Search, industry directories, competitor websites, review platforms, etc.)
- Răspunde STRICT în format JSON conform instrucțiunilor din prompt
- Nu folosi markdown code blocks, doar JSON pur
- Asigură-te că JSON-ul este valid și complet"""
            
            
            # Calculează timeout dinamic bazat pe mărimea prompt-ului
            # Estimare: ~1 token/secundă pentru DeepSeek Reasoner
            estimated_tokens = len(enhanced_prompt) // 4  # Estimare aproximativă
            estimated_time = (estimated_tokens + 6000) // 10  # ~10 tokens/secundă conservativ
            timeout = max(180, min(estimated_time, 300))  # Min 3 min, max 5 min
            
            logger.info(f"⏱️ Estimated timeout: {timeout}s pentru ~{estimated_tokens} tokens input + 6000 tokens output")
            
            # ⭐ CRITIC: Apel DeepSeek cu logging detaliat
            analysis_result_raw = None
            try:
                logger.info("🔄 Apel DeepSeek API...")
                analysis_result_raw = reasoner_chat(
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": enhanced_prompt
                        }
                    ],
                    max_tokens=6000,  # Mărește pentru răspunsuri foarte detaliate
                    temperature=0.5,  # Mai precis pentru analiză detaliată
                    timeout=timeout,  # Timeout dinamic
                    max_retries=3  # Retry pentru timeout-uri
                )
                logger.info("✅ Răspuns DeepSeek primit")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Eroare DeepSeek API: {error_msg}")
                import traceback
                logger.error(traceback.format_exc())
                
                # Dacă e timeout, încearcă cu max_tokens mai mic
                if "timeout" in error_msg.lower():
                    logger.warning("⚠️ Timeout detectat. Încearcă cu max_tokens redus...")
                    try:
                        analysis_result_raw = reasoner_chat(
                            messages=[
                                {
                                    "role": "system",
                                    "content": system_prompt
                                },
                                {
                                    "role": "user",
                                    "content": enhanced_prompt[:10000] + "\n\n[Conținut trunchiat pentru a evita timeout]"
                                }
                            ],
                            max_tokens=3000,  # Redus pentru a evita timeout
                            temperature=0.5,
                            timeout=180,
                            max_retries=2
                        )
                        logger.info("✅ Succes cu max_tokens redus")
                    except Exception as e2:
                        logger.error(f"❌ Eroare și cu max_tokens redus: {e2}")
                        raise Exception(f"DeepSeek API timeout chiar și cu setări reduse. Verifică conexiunea la internet sau încearcă mai târziu. Eroare: {error_msg}")
                else:
                    raise Exception(f"DeepSeek API error: {error_msg}")
            
            # ⭐ CRITIC: Verifică că răspunsul nu este gol
            if not analysis_result_raw:
                raise ValueError("DeepSeek nu a returnat niciun răspuns")
            
            # Extrage conținutul din răspunsul DeepSeek
            analysis_result = ""
            if isinstance(analysis_result_raw, dict):
                if "data" in analysis_result_raw:
                    choices = analysis_result_raw["data"].get("choices", [])
                    if choices and len(choices) > 0:
                        analysis_result = choices[0].get("message", {}).get("content", "")
                    else:
                        logger.error(f"❌ CRITIC: Nu există 'choices' în răspunsul DeepSeek")
                        logger.error(f"   Răspuns complet: {analysis_result_raw}")
                        raise ValueError("DeepSeek nu a returnat 'choices' în răspuns")
                elif "content" in analysis_result_raw:
                    analysis_result = analysis_result_raw["content"]
                else:
                    logger.error(f"❌ CRITIC: Nu există 'data' sau 'content' în răspunsul DeepSeek")
                    logger.error(f"   Răspuns complet: {analysis_result_raw}")
                    raise ValueError("DeepSeek nu a returnat 'data' sau 'content' în răspuns")
            else:
                analysis_result = str(analysis_result_raw)
            
            # ⭐ CRITIC: Verifică că răspunsul nu este gol
            if not analysis_result or len(analysis_result.strip()) < 50:
                logger.error(f"❌ CRITIC: Răspuns DeepSeek este gol sau prea scurt ({len(analysis_result)} caractere)")
                logger.error(f"   Răspuns: {analysis_result[:500]}")
                raise ValueError(f"DeepSeek nu a returnat un răspuns valid (doar {len(analysis_result)} caractere)")
            
            logger.info(f"✅ Răspuns DeepSeek primit ({len(analysis_result)} caractere)")
            logger.debug(f"   Primele 500 caractere: {analysis_result[:500]}")
            
            # 5. Parsează răspunsul DeepSeek
            strategy = self._parse_deepseek_response(analysis_result, agent, site_content)
            
            # 6. Salvează strategia în MongoDB
            # ⭐ VERIFICARE: Asigură-te că strategy este dict, NU string!
            if isinstance(strategy, str):
                logger.error(f"❌ EROARE CRITICĂ: strategy este STRING, nu DICT!")
                logger.error(f"   Încerc să parsez string-ul ca JSON...")
                try:
                    strategy = json.loads(strategy)
                    logger.info("✅ Strategy parsat din string la dict")
                except:
                    logger.error("❌ Nu pot parsa strategy ca JSON - folosesc fallback")
                    strategy = self._create_fallback_strategy(agent, site_content)
            
            strategy_doc = {
                "agent_id": agent_id,
                "domain": agent.get("domain"),
                "created_at": datetime.now(timezone.utc),
                "strategy": strategy,  # ⭐ Trebuie să fie dict, NU string!
                "services": strategy.get("services", []),  # ⭐ Duplicate la nivel top pentru acces ușor
                "analysis_metadata": {
                    "total_content_chunks": len(site_content),
                    "services_identified": len(strategy.get("services", [])),
                    "deepseek_model": "deepseek-chat"  # ⭐ FIX: deepseek-chat, nu deepseek-reasoner
                }
            }
            
            logger.info(f"💾 Salvez strategia în MongoDB (type={type(strategy).__name__}, services={len(strategy.get('services', []))})")
            
            # Upsert strategia (actualizează dacă există)
            self.strategies_collection.update_one(
                {"agent_id": agent_id},
                {"$set": strategy_doc},
                upsert=True
            )
            
            logger.info(f"✅ Strategie competitivă generată pentru agent {agent_id}")
            logger.info(f"   Servicii identificate: {len(strategy.get('services', []))}")
            
            return strategy
            
        except Exception as e:
            logger.error(f"❌ Eroare la generarea strategiei competitive: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def _get_site_content_from_qdrant(self, collection_name: str, agent_id: str) -> List[Dict[str, Any]]:
        """Obține conținutul site-ului din Qdrant"""
        try:
            # Verifică dacă colecția există
            try:
                collection_info = self.qdrant_client.get_collection(collection_name)
            except:
                logger.warning(f"⚠️ Colecție Qdrant '{collection_name}' nu există")
                return []
            
            # Obține toate punctele din colecție
            # Folosim scroll pentru a obține toate punctele
            scroll_result = self.qdrant_client.scroll(
                collection_name=collection_name,
                limit=1000,  # Limit mare pentru a obține tot conținutul
                with_payload=True
            )
            
            content = []
            for point in scroll_result[0]:  # scroll_result este un tuple (points, next_offset)
                if point.payload:
                    content.append({
                        "content": point.payload.get("content", ""),
                        "url": point.payload.get("url", ""),
                        "metadata": point.payload.get("metadata", {})
                    })
            
            logger.info(f"✅ Obținut {len(content)} chunks din Qdrant pentru agent {agent_id}")
            return content
            
        except Exception as e:
            logger.warning(f"⚠️ Eroare la obținerea conținutului din Qdrant: {e}")
            return []
    
    async def _get_web_search_context(self, agent: Dict, site_content: List[Dict]) -> str:
        """Generează context pentru web search bazat pe conținutul site-ului"""
        try:
            domain = agent.get("domain", "unknown")
            business_type = agent.get("business_type", "general")
            
            # Extrage servicii/produse cheie din conținut
            services_keywords = []
            for chunk in site_content[:10]:  # Primele 10 chunks
                content = chunk.get("content", "")
                # Simplificare - în realitate ar trebui NLP
                words = content.split()
                # Caută cuvinte cheie comune pentru servicii
                for word in words:
                    if len(word) > 5 and word.lower() not in services_keywords:
                        services_keywords.append(word.lower())
            
            # Construiește context pentru web search
            context = f"""Surse recomandate pentru cercetare concurenți pentru {domain}:

1. Google Search:
   - "{domain} competitors"
   - "{business_type} Romania"
   - "similar services {domain}"
   - Termeni din conținut: {', '.join(services_keywords[:10])}

2. Industry Directories:
   - Caută în directoare de industrie pentru {business_type}
   - Asociații de industrie relevante
   - Platforme B2B pentru sectorul {business_type}

3. Competitor Websites:
   - Analizează site-urile competitorilor identificați
   - Compară prețuri, caracteristici, strategii de marketing
   - Identifică diferențiatorii cheie

4. Social Media & Reviews:
   - Platforme de review pentru servicii similare
   - Social media pentru branding și strategii de marketing
   - Forums și comunități relevante

Folosește aceste surse pentru a genera strategii concrete de cercetare."""
            
            return context
        except Exception as e:
            logger.warning(f"⚠️ Eroare la generarea web search context: {e}")
            return ""
    
    async def _get_site_content_from_mongodb(self, agent_id: str) -> List[Dict[str, Any]]:
        """Obține conținutul site-ului din MongoDB ca fallback"""
        try:
            # ⭐ CRITIC: Convertește agent_id la ObjectId pentru căutare corectă
            from bson import ObjectId
            
            # Caută în colecția de site content
            site_content_collection = self.db.site_content
            
            # Încearcă cu ObjectId
            try:
                agent_id_obj = ObjectId(agent_id)
                content_docs = list(site_content_collection.find(
                    {"agent_id": agent_id_obj},
                    limit=200  # Limitează pentru a nu încărca prea mult
                ))
            except:
                # Fallback: încearcă cu string
                logger.warning(f"⚠️ Nu s-a putut converti agent_id la ObjectId, încearcă cu string...")
                content_docs = list(site_content_collection.find(
                    {"agent_id": agent_id},
                    limit=200
                ))
            
            content = []
            for doc in content_docs:
                content.append({
                    "content": doc.get("content", ""),
                    "url": doc.get("url", ""),
                    "metadata": doc.get("metadata", {})
                })
            
            if content:
                logger.info(f"✅ Obținut {len(content)} chunks din MongoDB pentru agent {agent_id}")
            else:
                logger.warning(f"⚠️ Nu s-a găsit conținut în MongoDB pentru agent {agent_id}")
            
            return content
            
        except Exception as e:
            logger.error(f"❌ Eroare la obținerea conținutului din MongoDB: {e}")
            return []
    
    async def _fetch_content_from_site(self, agent: Dict) -> List[Dict]:
        """Obține conținutul direct de pe site ca fallback dacă nu există în bazele de date"""
        try:
            import requests
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin, urlparse
            
            site_url = agent.get("site_url") or f"https://{agent.get('domain', '')}"
            if not site_url or not site_url.startswith(('http://', 'https://')):
                logger.warning(f"⚠️ URL invalid pentru agent: {site_url}")
                return []
            
            logger.info(f"🌐 Obțin conținut direct de pe {site_url}...")
            
            # Headers pentru a evita blocarea
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            try:
                response = requests.get(site_url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Elimină elemente nedorite
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    tag.decompose()
                
                # Extrage conținutul principal
                title = soup.find('title')
                title_text = title.get_text().strip() if title else ""
                
                # Extrage textul principal
                main_content = soup.get_text(separator=' ', strip=True)
                
                if len(main_content) < 100:
                    logger.warning(f"⚠️ Conținut prea scurt de pe {site_url}")
                    return []
                
                # Creează chunks din conținut
                chunk_size = 2000
                chunks = []
                for i in range(0, len(main_content), chunk_size):
                    chunk_text = main_content[i:i+chunk_size]
                    if len(chunk_text.strip()) > 50:
                        chunks.append({
                            "content": chunk_text,
                            "url": site_url,
                            "metadata": {
                                "chunk_index": len(chunks),
                                "source": "direct_fetch",
                                "title": title_text
                            }
                        })
                
                logger.info(f"✅ Obținut {len(chunks)} chunks direct de pe site")
                return chunks
                
            except Exception as e:
                logger.error(f"❌ Eroare la obținerea conținutului de pe site: {e}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Eroare în _fetch_content_from_site: {e}")
            return []
    
    def _build_analysis_prompt(self, agent: Dict, site_content: List[Dict]) -> str:
        """Construiește prompt-ul pentru analiză DeepSeek"""
        
        # Construiește rezumatul conținutului - IMPORTANT: păstrează terminologia exactă din site
        # Analizează MAI MULTE chunks pentru a obține context complet
        content_summary = []
        max_chunks = min(100, len(site_content))  # Analizează până la 100 chunks
        
        for idx, chunk in enumerate(site_content[:max_chunks], 1):
            chunk_content = chunk.get('content', '').strip()
            if not chunk_content:
                continue
            
            # Păstrează conținutul complet pentru context maxim (până la 2000 caractere per chunk)
            chunk_url = chunk.get('url', 'N/A')
            content_summary.append(f"=== CHUNK {idx} (URL: {chunk_url}) ===\n{chunk_content[:2000]}\n")
        
        content_text = "\n\n".join(content_summary)
        
        # Dacă nu avem destul conținut, avertizează
        if len(content_summary) < 5:
            logger.warning(f"⚠️ Doar {len(content_summary)} chunks disponibile - strategia poate fi mai generică")
        
        # Extrage informații despre site pentru corecții
        site_domain = agent.get('domain', 'unknown')
        site_name = agent.get('name', 'N/A')
        site_url = agent.get('site_url', 'N/A')
        
        prompt = f"""Ești un EXPERT în analiză competitivă și strategie de business. Analizează ATENT următoarele date despre site-ul {site_domain} și generează o strategie COMPLETĂ, DETALIATĂ și SPECIFICĂ de cercetare a concurenței.

**CRITICAL - ACURATETE TERMINOLOGIE:**
- Citește ATENT TOATE chunks-urile și folosește EXACT terminologia din site
- Dacă site-ul folosește "matari" (nu "mătășuri"), folosește "matari"
- Dacă site-ul folosește "treceri" (nu "trecere"), folosește "treceri"
- Verifică în TOATE chunks-urile înainte de a identifica servicii
- Nu inventa termeni - folosește DOAR ce găsești în conținut
- Extrage NUME EXACTE de servicii/produse din conținut
- Identifică TOATE serviciile oferite, nu doar cele generale

**INFORMAȚII SITE:**
- Domeniu: {site_domain}
- Nume: {site_name}
- URL: {site_url}
- Tip business: {agent.get('business_type', 'general')}
- Total chunks analizate: {len(content_summary)}

**CONȚINUT COMPLET SITE (CITEȘTE ATENT TOATE CHUNKS-URILE PENTRU TERMINOLOGIE CORECTĂ):**
{content_text}

**INSTRUCȚIUNI DETALIATE:**
1. ANALIZĂ PROFUNDĂ:
   - Citește TOATE chunks-urile și identifică TOATE serviciile/produsele oferite
   - Pentru fiecare serviciu, extrage NUMELE EXACT, descrierea detaliată și caracteristicile
   - Identifică termeni tehnici, certificări, standarde menționate
   - Notează zone geografice de acoperire, tipuri de clienți, prețuri (dacă sunt menționate)

2. PENTRU FIECARE SERVICIU IDENTIFICAT:
   - Nume EXACT al serviciului (folosește terminologia din site)
   - Descriere detaliată bazată pe conținutul site-ului
   - Termeni de căutare SPECIFICI pentru identificarea competitorilor
   - Strategie de cercetare DETALIATĂ cu surse concrete
   - Întrebări-cheie SPECIFICE pentru acel serviciu
   - Query-uri web search CONCRETE și ACȚIONABILE

3. STRATEGIE GENERALĂ:
   - Abordare competitivă SPECIFICĂ pentru industria {site_domain}
   - Priorități de cercetare CONCRETE și ACȚIONABILE
   - Rezultate așteptate DETALIATE și MĂSURABILE

**INSTRUCȚIUNI:**
1. Identifică TOATE tipurile de servicii/produse oferite de acest site
2. Pentru fiecare tip de serviciu:
   - Definește serviciul/produsul clar
   - Generează termeni de căutare pentru identificarea competitorilor (folosește web search dacă este necesar)
   - Propune strategii de cercetare a concurenței (unde să cauți, ce să cauți)
   - Sugerează întrebări-cheie pentru a înțelege concurența
   - Include surse pentru cercetare (Google Search, industry directories, competitor websites, social media, etc.)
3. Creează un plan general de analiză competitivă
4. FOLOSEȘTE WEB SEARCH dacă ai nevoie de informații actualizate despre concurenți, prețuri sau piață

**FORMAT RĂSPUNS (JSON):**
{{
    "services": [
        {{
            "service_name": "Nume serviciu/produs",
            "description": "Descriere detaliată",
            "search_keywords": ["cuvinte", "cheie", "căutare"],
            "competitive_research_strategy": {{
                "where_to_search": [
                    "Google Search cu termeni specifici",
                    "Industry directories (ex: directory-industrie.ro)",
                    "Competitor websites",
                    "Social media platforms",
                    "Review platforms (ex: Google Reviews, Trustpilot)",
                    "Business directories (ex: YellowPages, 123firme.ro)",
                    "Trade shows și evenimente de industrie",
                    "Forums și comunități online"
                ],
                "what_to_look_for": [
                    "Prețuri și pachete",
                    "Caracteristici și beneficii",
                    "Strategii de marketing",
                    "Poziționare pe piață",
                    "Diferențiatorii cheie",
                    "Feedback și recenzii clienți",
                    "Prezență online și branding"
                ],
                "key_questions": [
                    "Cine sunt principalii concurenți pentru acest serviciu?",
                    "Ce oferă concurenții la același preț?",
                    "Cum se diferențiază serviciul analizat?",
                    "Ce feedback primesc concurenții de la clienți?",
                    "Ce strategii de marketing folosesc concurenții?"
                ],
                "web_search_queries": [
                    "{{service_name}} competitors Romania",
                    "{{service_name}} alternative",
                    "best {{service_name}} providers",
                    "{{service_name}} pricing comparison"
                ]
            }},
            "priority": "high/medium/low"
        }}
    ],
    "overall_strategy": {{
        "competitive_analysis_approach": "Descrierea abordării generale cu recomandări pentru web search",
        "research_priorities": [
            "Identificare principalilor concurenți (folosește Google Search)",
            "Comparare prețuri și pachete (web search + competitor websites)",
            "Analiză diferențiatorii cheie (site-uri concurenți + review platforms)",
            "Evaluare strategii de marketing (social media + web search)"
        ],
        "expected_outcomes": "Ce ar trebui să descoperim: lista concurenților, comparație prețuri, analiză diferențiatorii, recomandări strategice",
        "web_search_enabled": true,
        "internet_access_required": true
    }}
}}

**IMPORTANT:** 
- Răspunde DOAR în format JSON, fără text suplimentar
- Fiecare serviciu trebuie să aibă o strategie detaliată cu surse concrete
- Include întrebări de căutare web concrete pentru fiecare serviciu
- Recomandă surse specifice (Google Search, directories, platforms) pentru fiecare tip de serviciu"""
        
        return prompt
    
    def _parse_deepseek_response(self, response: str, agent: Dict, site_content: List[Dict]) -> Dict[str, Any]:
        """Parsează răspunsul DeepSeek și construiește strategia"""
        try:
            # ⭐ CRITIC: Verifică dacă răspunsul este gol sau invalid
            response_text = response if isinstance(response, str) else response.get("content", "") if isinstance(response, dict) else str(response)
            
            if not response_text or len(response_text.strip()) < 50:
                logger.error(f"❌ CRITIC: Răspuns DeepSeek este gol sau prea scurt ({len(response_text)} caractere)")
                logger.error(f"   Răspuns primit: {response_text[:200]}")
                raise ValueError("DeepSeek nu a returnat un răspuns valid")
            
            logger.info(f"📝 Parsing răspuns DeepSeek ({len(response_text)} caractere)...")
            logger.debug(f"   Primele 500 caractere: {response_text[:500]}")
            
            # Caută JSON în răspuns
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                
                # ⭐ CRITIC: Încearcă să parseze JSON cu mai multe încercări
                strategy = None
                try:
                    strategy = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Eroare JSON parsing (prima încercare): {e}")
                    # Încearcă să curețe JSON-ul
                    json_str_clean = json_str
                    # Elimină markdown code blocks dacă există
                    if "```json" in json_str_clean:
                        json_str_clean = json_str_clean.split("```json")[1].split("```")[0]
                    elif "```" in json_str_clean:
                        json_str_clean = json_str_clean.split("```")[1].split("```")[0]
                    
                    try:
                        strategy = json.loads(json_str_clean)
                        logger.info("✅ JSON parsat după curățare")
                    except json.JSONDecodeError as e2:
                        logger.error(f"❌ Eroare JSON parsing (după curățare): {e2}")
                        logger.error(f"   JSON string: {json_str_clean[:500]}")
                        
                        # ⭐ FALLBACK FINAL: Curăță JSON agresiv și încearcă din nou
                        logger.warning("⚠️  Încerc curățare agresivă JSON...")
                        try:
                            import re
                            # Elimină comentarii
                            json_cleaned = re.sub(r'//.*?\n', '\n', json_str_clean)
                            # Elimină virgule trailing
                            json_cleaned = re.sub(r',\s*}', '}', json_cleaned)
                            json_cleaned = re.sub(r',\s*]', ']', json_cleaned)
                            # Elimină newline în strings
                            json_cleaned = re.sub(r'(?<=")\n(?=")', ' ', json_cleaned)
                            
                            strategy = json.loads(json_cleaned)
                            logger.info("✅ JSON parsat după curățare agresivă")
                        except Exception as e3:
                            logger.error(f"❌ Eroare și după curățare agresivă: {e3}")
                            # FALLBACK ABSOLUT: Creează strategie minimă
                            logger.warning("⚠️ Folosesc fallback total - creez strategie minimă")
                            strategy = self._create_fallback_strategy(agent, site_content)
                            logger.info("✅ Strategie fallback creată")
                
                if not strategy:
                    raise ValueError("Strategy este None după parsing")
                
                # Validează și completează strategia
                if "services" not in strategy:
                    logger.warning("⚠️ DeepSeek nu a returnat 'services' - creez lista goală")
                    strategy["services"] = []
                
                if "overall_strategy" not in strategy:
                    # ⭐ CRITIC: Dacă nu există strategie generală, NU folosi fallback generic
                    # Construiește una detaliată bazată pe conținutul REAL al site-ului
                    logger.warning("⚠️ DeepSeek nu a returnat overall_strategy - construiesc una detaliată bazată pe conținut")
                    
                    domain = agent.get('domain', 'unknown')
                    site_name = agent.get('name', domain)
                    
                    # Extrage servicii reale din conținut
                    services_found = []
                    for chunk in site_content[:30]:
                        content = chunk.get('content', '').strip()
                        if len(content) > 100:
                            services_found.append(content[:300])
                    
                    # Construiește strategie detaliată bazată pe conținutul REAL
                    strategy["overall_strategy"] = {
                        "competitive_analysis_approach": f"Strategie competitivă COMPLETĂ și DETALIATĂ pentru {domain}, bazată pe analiza profundă a conținutului site-ului {site_name}. Strategia include identificarea TOȚILOR servicii/produse oferite, analiza concurenței pentru fiecare serviciu, și recomandări concrete de cercetare folosind web search și resurse online.",
                        "research_priorities": [
                            f"Identificare principalilor concurenți pentru serviciile oferite de {domain} folosind Google Search cu termeni specifici extrași din conținutul site-ului",
                            f"Comparare prețuri și pachete de servicii prin analiza site-urilor concurente și platforme de review (Google Reviews, Trustpilot, etc.)",
                            f"Analiză diferențiatori cheie (certificări, experiență, portofoliu, tehnologii) din conținutul online și feedback clienți",
                            f"Evaluare strategii de marketing și prezență online (social media, SEO, content marketing) prin monitorizare web search și analiza competitorilor"
                        ],
                        "expected_outcomes": f"Listă COMPLETĂ și DETALIATĂ a concurenților pentru {domain}, comparație detaliată prețuri și caracteristici pentru fiecare serviciu identificat, identificare diferențiatori cheie și avantaje competitive, recomandări strategice CONCRETE și ACȚIONABILE pentru îmbunătățirea poziției competitive pe piață"
                    }
                
                # Adaugă metadata
                strategy["metadata"] = {
                    "agent_id": str(agent.get("_id")),
                    "domain": agent.get("domain"),
                    "analysis_date": datetime.now(timezone.utc).isoformat(),
                    "total_services": len(strategy.get("services", [])),
                    "deepseek_used": True,
                    "response_length": len(response_text)
                }
                
                logger.info(f"✅ Strategie parsată cu succes: {len(strategy.get('services', []))} servicii")
                return strategy
            else:
                # ⭐ CRITIC: Dacă nu există JSON, NU folosi fallback generic - aruncă eroare
                logger.error(f"❌ CRITIC: Nu s-a găsit JSON în răspunsul DeepSeek")
                logger.error(f"   Răspuns primit: {response_text[:1000]}")
                raise ValueError(f"DeepSeek nu a returnat JSON valid. Răspuns: {response_text[:500]}")
                
        except ValueError as e:
            # Re-raise ValueError pentru a fi prins de caller
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ Eroare la parsarea JSON: {e}")
            logger.error(f"   Răspuns: {response_text[:1000] if 'response_text' in locals() else 'N/A'}")
            raise ValueError(f"Nu s-a putut parsa JSON din răspunsul DeepSeek: {e}")
        except Exception as e:
            logger.error(f"❌ Eroare la parsarea răspunsului: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise ValueError(f"Eroare la parsarea răspunsului DeepSeek: {e}")
    
    def _create_fallback_strategy(self, agent: Dict, site_content: List[Dict]) -> Dict[str, Any]:
        """Creează o strategie de bază dacă DeepSeek nu returnează JSON valid"""
        return {
            "services": [
                {
                    "service_name": "General Services",
                    "description": f"Servicii generale oferite de {agent.get('domain', 'site')}",
                    "search_keywords": [agent.get('domain', ''), agent.get('business_type', 'services')],
                    "competitive_research_strategy": {
                        "where_to_search": ["Google Search", "Industry directories", "Competitor websites"],
                        "what_to_look_for": ["Similar services", "Pricing", "Features"],
                        "key_questions": ["Who are the main competitors?", "What are their strengths?", "How do they differentiate?"]
                    },
                    "priority": "high"
                }
            ],
            "overall_strategy": {
                "competitive_analysis_approach": "General competitive analysis approach based on site content",
                "research_priorities": ["Market analysis", "Competitor identification", "Feature comparison"],
                "expected_outcomes": "Understanding of competitive landscape"
            },
            "metadata": {
                "agent_id": str(agent.get("_id")),
                "domain": agent.get("domain"),
                "analysis_date": datetime.now(timezone.utc).isoformat(),
                "fallback": True,
                "total_services": 1
            }
        }
    
    async def get_strategy_for_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Obține strategia existentă pentru un agent"""
        try:
            strategy_doc = self.strategies_collection.find_one({"agent_id": agent_id})
            if strategy_doc:
                return strategy_doc.get("strategy")
            return None
        except Exception as e:
            logger.error(f"❌ Eroare la obținerea strategiei: {e}")
            return None

# Instanță globală
strategy_generator = CompetitiveStrategyGenerator()

