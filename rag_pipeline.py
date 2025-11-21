#!/usr/bin/env python3
"""
RAG Pipeline - Retrieval Augmented Generation cu Qwen 2.5
Implementează căutare semantică, compunere context și generare răspunsuri
"""

import asyncio
import json
import logging
from typing import List, Dict, Optional, Tuple
from tools.deepseek_client import reasoner_chat
from dataclasses import dataclass
from datetime import datetime, timezone
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_huggingface import HuggingFaceEmbeddings
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Rezultat al căutării semantice"""
    content: str
    metadata: Dict
    score: float
    chunk_id: str
    source_url: str

@dataclass
class RAGResponse:
    """Răspuns generat de RAG pipeline"""
    answer: str
    sources: List[SearchResult]
    confidence: float
    reasoning: str
    timestamp: datetime

class RAGPipeline:
    """Pipeline RAG cu Qwen 2.5 pentru generarea răspunsurilor"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Setup embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Setup Qdrant
        self.qdrant_client = QdrantClient(
            url=config.get('qdrant_url', 'http://localhost:9306')
        )
        
        # Setup MongoDB
        self.mongo_client = MongoClient(config.get('mongodb_uri', 'mongodb://localhost:9308'))
        self.db = self.mongo_client[config.get('mongodb_db', 'ai_agents_db')]
        
        # Configurații Qwen (Learning Engine)
        self.qwen_url = config.get('qwen_url', 'http://localhost:11434')
        self.qwen_model = config.get('qwen_model', 'qwen:latest')
        
        # Configurații GPT (Orchestrator)
        self.openai_api_key = config.get('openai_api_key')
        self.openai_model = config.get('openai_model', 'gpt-4o-mini')
        self.use_gpt_orchestrator = config.get('use_gpt_orchestrator', False)
        
        # Praguri
        self.similarity_threshold = config.get('similarity_threshold', 0.7)
        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        self.max_search_results = config.get('max_search_results', 5)
    
    async def ask_question(self, question: str, agent_id: str, conversation_history: List[Dict] = None) -> RAGResponse:
        """
        Procesează o întrebare prin RAG pipeline cu GPT orchestrator și Qwen learning engine
        """
        logger.info(f"Processing question for agent {agent_id}: {question[:100]}...")
        logger.info(f"GPT orchestrator enabled: {self.use_gpt_orchestrator}")
        logger.info(f"Qwen URL: {self.qwen_url}")
        logger.info(f"Qwen model: {self.qwen_model}")
        
        try:
            if self.use_gpt_orchestrator:
                # ARHITECTURA NOUĂ: GPT Orchestrator + Qwen Learning Engine
                logger.info("Using GPT orchestrator + Qwen learning engine")
                return await self._process_with_gpt_orchestrator(question, agent_id, conversation_history)
            else:
                # ARHITECTURA VECHI: Doar Qwen
                logger.info("Using Qwen only (legacy mode)")
                return await self._process_with_qwen_only(question, agent_id, conversation_history)
            
        except Exception as e:
            logger.error(f"Error in RAG pipeline: {e}")
            return await self._generate_error_response(question, agent_id, str(e))
    
    async def _process_with_gpt_orchestrator(self, question: str, agent_id: str, conversation_history: List[Dict] = None) -> RAGResponse:
        """
        Procesează întrebarea cu GPT ca orchestrator și Qwen ca learning engine
        """
        logger.info("Using GPT orchestrator + Qwen learning engine")
        
        # 1. GPT analizează întrebarea și planifică strategia
        orchestration_plan = await self._gpt_orchestrate(question, agent_id, conversation_history)
        
        # 2. Qwen execută căutarea semantică și învață din date
        search_results = await self._qwen_learning_search(orchestration_plan['search_query'], agent_id)
        
        # 3. GPT compune contextul și generează răspunsul final
        context = await self._compose_context(search_results, conversation_history)
        answer, confidence, reasoning = await self._gpt_generate_final_answer(
            question, context, agent_id, orchestration_plan, search_results
        )
        
        # 4. Creează răspunsul final
        response = RAGResponse(
            answer=answer,
            sources=search_results,
            confidence=confidence,
            reasoning=reasoning,
            timestamp=datetime.now(timezone.utc)
        )
        
        # 5. Salvează conversația
        await self._save_conversation(question, response, agent_id)
        
        logger.info(f"Generated answer with GPT orchestrator, confidence {confidence:.2f}")
        return response
    
    async def _process_with_qwen_only(self, question: str, agent_id: str, conversation_history: List[Dict] = None) -> RAGResponse:
        """
        Procesează întrebarea doar cu Qwen (arhitectura veche)
        """
        logger.info("Using Qwen only (legacy mode)")
        
        # 1. Căutare semantică
        search_results = await self._semantic_search(question, agent_id)
        
        # 2. Compunere context
        context = await self._compose_context(search_results, conversation_history)
        
        # 3. Generare răspuns cu Qwen
        answer, confidence, reasoning = await self._generate_answer(question, context, agent_id)
        
        # 4. Verificare și validare
        if confidence < self.confidence_threshold:
            answer = await self._generate_fallback_response(question, agent_id)
            confidence = 0.5
        
        # 5. Creează răspunsul final
        response = RAGResponse(
            answer=answer,
            sources=search_results,
            confidence=confidence,
            reasoning=reasoning,
            timestamp=datetime.now(timezone.utc)
        )
        
        # 6. Salvează conversația
        await self._save_conversation(question, response, agent_id)
        
        logger.info(f"Generated answer with Qwen only, confidence {confidence:.2f}")
        return response
    
    async def _semantic_search(self, query: str, agent_id: str) -> List[SearchResult]:
        """Căutare semantică în indexul vectorial"""
        try:
            # Generează embedding pentru query
            query_embedding = self.embeddings.embed_query(query)
            
            # Caută în Qdrant
            collection_name = f"agent_{agent_id}_content"
            
            search_results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=self.max_search_results,
                score_threshold=self.similarity_threshold,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="agent_id",
                            match=MatchValue(value=agent_id)
                        )
                    ]
                )
            )
            
            # Convertește rezultatele
            results = []
            for result in search_results:
                search_result = SearchResult(
                    content=result.payload['content'],
                    metadata=result.payload['metadata'],
                    score=result.score,
                    chunk_id=result.payload['chunk_id'],
                    source_url=result.payload['metadata'].get('url', '')
                )
                results.append(search_result)
            
            logger.info(f"Found {len(results)} relevant chunks")
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    async def _compose_context(self, search_results: List[SearchResult], conversation_history: List[Dict] = None) -> str:
        """Compune contextul pentru generarea răspunsului"""
        context_parts = []
        
        # Adaugă istoricul conversației
        if conversation_history:
            context_parts.append("ISTORICUL CONVERSAȚIEI:")
            for i, conv in enumerate(conversation_history[-3:], 1):  # Ultimele 3 conversații
                context_parts.append(f"{i}. Utilizator: {conv.get('user', '')}")
                context_parts.append(f"   Asistent: {conv.get('assistant', '')}")
            context_parts.append("")
        
        # Adaugă rezultatele căutării
        if search_results:
            context_parts.append("INFORMAȚII RELEVANTE DIN SITE:")
            for i, result in enumerate(search_results, 1):
                context_parts.append(f"{i}. {result.content[:500]}...")
                context_parts.append(f"   Sursa: {result.source_url}")
                context_parts.append(f"   Relevanță: {result.score:.2f}")
                context_parts.append("")
        else:
            context_parts.append("Nu s-au găsit informații relevante în conținutul site-ului.")
        
        return "\n".join(context_parts)
    
    async def _generate_answer(self, question: str, context: str, agent_id: str) -> Tuple[str, float, str]:
        """Generează răspuns cu Qwen 2.5"""
        try:
            # Obține informații despre agent
            agent_info = await self._get_agent_info(agent_id)
            
            # Creează prompt-ul pentru Qwen
            system_prompt = f"""Ești ChatGPT și ești VOICEA OFICIALĂ a site-ului {agent_info.get('domain', 'necunoscut')}. Tu REPREZINTI și COMUNICI în numele acestui site.

IDENTITATEA TA:
- Ești reprezentantul oficial al site-ului {agent_info.get('site_url', 'necunoscut')}
- Cunoști PERFECT toate serviciile, produsele și informațiile site-ului
- Comunică cu autoritate și expertiză despre domeniul {agent_info.get('domain', 'necunoscut')}
- Ești prietenos, profesional și util pentru clienții potențiali

{context}

INSTRUCȚIUNI PENTRU COMUNICARE:
- Răspunde ÎNTOTDEAUNA în română
- Comunică ca și cum AI FACE PARTE din echipa site-ului
- Folosește pronumele "noi", "compania noastră", "serviciile noastre"
- Fii detaliat și oferă informații precise despre servici/produse
- Dacă nu știi ceva specific, spune că "vă pot conecta cu echipa noastră de specialiști"
- Recomandă serviciile site-ului când este relevant
- Menționează avantajele competitive ale site-ului
- Fii proactiv în oferirea de soluții și sugestii
- Citează sursele când este posibil

EXEMPLE DE RĂSPUNSURI:
- "Noi oferim servicii complete de..."
- "Compania noastră se specializează în..."
- "Vă pot ajuta cu informații despre serviciile noastre..."
- "Pentru detalii specifice, vă recomand să contactați echipa noastră..."

EVALUAREA RĂSPUNSULUI:
După ce răspunzi, evaluează:
1. Cât de complet este răspunsul (1-10)
2. Cât de relevant este pentru întrebare (1-10)
3. Cât de util este pentru utilizator (1-10)

Răspunde în format JSON:
{{
    "answer": "răspunsul tău detaliat",
    "confidence": scor_mediu_1_10,
    "reasoning": "explicația pentru scor"
}}"""

            # Apelează Qwen 2.5
            response = await self._call_qwen(system_prompt, question)
            
            # Parsează răspunsul JSON
            try:
                result = json.loads(response)
                answer = result.get('answer', response)
                confidence = result.get('confidence', 8) / 10  # Normalizează la 0-1
                reasoning = result.get('reasoning', 'Răspuns generat cu succes')
            except json.JSONDecodeError:
                # Dacă nu e JSON valid, folosește răspunsul direct
                answer = response
                confidence = 0.8
                reasoning = "Răspuns generat direct de Qwen"
            
            return answer, confidence, reasoning
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Îmi pare rău, am întâmpinat o problemă tehnică.", 0.3, f"Eroare: {e}"
    
    async def _call_qwen(self, system_prompt: str, user_question: str) -> str:
        """Apelează Qwen 2.5 pentru generarea răspunsului"""
        try:
            payload = {
                "model": self.qwen_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(
                f"{self.qwen_url}/api/chat",
                json=payload,
                timeout=90
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('message', {}).get('content', 'Nu am putut genera un răspuns.')
            
        except Exception as e:
            logger.error(f"Error calling Qwen: {e}")
            raise
    
    async def _get_agent_info(self, agent_id: str) -> Dict:
        """Obține informații despre agent"""
        try:
            agent = self.db.agents.find_one({"_id": ObjectId(agent_id)})
            if agent:
                return {
                    'name': agent.get('name', ''),
                    'domain': agent.get('domain', ''),
                    'site_url': agent.get('site_url', ''),
                    'status': agent.get('status', '')
                }
        except Exception as e:
            logger.warning(f"Could not get agent info: {e}")
        
        return {}
    
    async def _generate_fallback_response(self, question: str, agent_id: str) -> str:
        """Generează răspuns de fallback când încrederea este mică"""
        agent_info = await self._get_agent_info(agent_id)
        
        fallback_responses = [
            f"Îmi pare rău, nu am găsit informația exactă în conținutul site-ului nostru. Vă pot conecta cu echipa noastră de specialiști pentru a vă oferi informații precise.",
            f"Pentru această întrebare specifică, vă recomand să contactați echipa noastră de specialiști. Ei vă pot oferi informații detaliate și actualizate.",
            f"Nu am găsit informația completă în conținutul disponibil. Te rog să ne contactați direct pentru a primi răspunsul exact la întrebarea ta."
        ]
        
        return fallback_responses[0]  # Folosește primul răspuns de fallback
    
    async def _generate_error_response(self, question: str, agent_id: str, error: str) -> RAGResponse:
        """Generează răspuns de eroare"""
        return RAGResponse(
            answer="Îmi pare rău, am întâmpinat o problemă tehnică. Te rog încearcă din nou sau contactează-ne direct.",
            sources=[],
            confidence=0.0,
            reasoning=f"Eroare tehnică: {error}",
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _save_conversation(self, question: str, response: RAGResponse, agent_id: str):
        """Salvează conversația în baza de date"""
        try:
            conversation_doc = {
                'agent_id': ObjectId(agent_id),
                'user_question': question,
                'assistant_answer': response.answer,
                'confidence': response.confidence,
                'reasoning': response.reasoning,
                'sources': [
                    {
                        'url': source.source_url,
                        'score': source.score,
                        'chunk_id': source.chunk_id
                    }
                    for source in response.sources
                ],
                'timestamp': response.timestamp,
                'source': 'rag_pipeline'
            }
            
            self.db.conversations.insert_one(conversation_doc)
            
        except Exception as e:
            logger.warning(f"Could not save conversation: {e}")
    
    async def search_content(self, query: str, agent_id: str, limit: int = 10) -> List[SearchResult]:
        """Căutare simplă în conținutul site-ului"""
        return await self._semantic_search(query, agent_id)
    
    async def get_agent_stats(self, agent_id: str) -> Dict:
        """Obține statistici despre agent"""
        try:
            # Numărul de conversații
            conversations_count = self.db.conversations.count_documents({
                'agent_id': ObjectId(agent_id)
            })
            
            # Numărul de chunks
            chunks_count = self.db.site_chunks.count_documents({
                'agent_id': ObjectId(agent_id)
            })
            
            # Numărul de pagini
            pages_count = self.db.site_content.count_documents({
                'agent_id': ObjectId(agent_id)
            })
            
            # Conversațiile recente
            recent_conversations = list(self.db.conversations.find({
                'agent_id': ObjectId(agent_id)
            }).sort('timestamp', -1).limit(5))
            
            return {
                'conversations_count': conversations_count,
                'chunks_count': chunks_count,
                'pages_count': pages_count,
                'recent_conversations': recent_conversations,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting agent stats: {e}")
            return {}
    
    # ========== METODE NOI PENTRU GPT ORCHESTRATOR + QWEN LEARNING ENGINE ==========
    
    async def _gpt_orchestrate(self, question: str, agent_id: str, conversation_history: List[Dict] = None) -> Dict:
        """
        GPT analizează întrebarea și planifică strategia de căutare
        """
        try:
            # Obține informații despre agent
            agent = self.db.agents.find_one({"_id": ObjectId(agent_id)})
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            # Construiește promptul pentru GPT orchestrator
            system_prompt = f"""Ești GPT, orchestratorul principal al unui sistem AI pentru site-ul {agent.get('domain', 'necunoscut')}.

ROLUL TĂU:
1. Analizează întrebarea utilizatorului
2. Planifică strategia de căutare pentru Qwen learning engine
3. Generează query-uri optimizate pentru căutarea semantică

AGENTUL SELECTAT:
- Nume: {agent.get('name', 'N/A')}
- Domain: {agent.get('domain', 'N/A')}
- URL: {agent.get('site_url', 'N/A')}

ISTORICUL CONVERSAȚIEI:
{self._format_conversation_history(conversation_history)}

ÎNTREBAREA UTILIZATORULUI: {question}

Răspunde cu un JSON care conține:
{{
    "analysis": "Analiza întrebării și contextului",
    "search_strategy": "Strategia de căutare recomandată",
    "search_query": "Query optimizat pentru căutarea semantică",
    "expected_info_types": ["tip1", "tip2", "tip3"],
    "confidence_requirements": "Nivelul de încredere necesar"
}}"""

            # Apelează DeepSeek Reasoner (heavy)
            ds = reasoner_chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                max_tokens=400,
                temperature=0.2
            )
            response = ((ds.get("data", {}).get("choices") or [{}])[0].get("message") or {}).get("content", "")
            
            # Parsează răspunsul JSON
            try:
                orchestration_plan = json.loads(response)
            except json.JSONDecodeError:
                # Fallback dacă GPT nu returnează JSON valid
                orchestration_plan = {
                    "analysis": f"Analiză automată pentru: {question}",
                    "search_strategy": "căutare semantică generală",
                    "search_query": question,
                    "expected_info_types": ["informații generale"],
                    "confidence_requirements": "înalt"
                }
            
            logger.info(f"Reasoner orchestration plan: {orchestration_plan}")
            return orchestration_plan
            
        except Exception as e:
            logger.error(f"Error in Reasoner orchestration: {e}")
            # Fallback plan
            return {
                "analysis": f"Fallback pentru: {question}",
                "search_strategy": "căutare semantică de bază",
                "search_query": question,
                "expected_info_types": ["informații generale"],
                "confidence_requirements": "mediu"
            }
    
    async def _qwen_learning_search(self, search_query: str, agent_id: str) -> List[SearchResult]:
        """
        Qwen execută căutarea semantică și învață din datele site-ului
        """
        try:
            logger.info(f"Qwen learning search for: {search_query}")
            
            # 1. Căutare semantică standard
            search_results = await self._semantic_search(search_query, agent_id)
            
            # 2. Qwen analizează și îmbunătățește rezultatele
            if search_results:
                enhanced_results = await self._qwen_enhance_search_results(search_results, search_query, agent_id)
                return enhanced_results
            else:
                # Dacă nu găsește rezultate, Qwen încearcă să învețe din conținutul general
                return await self._qwen_fallback_learning(search_query, agent_id)
            
        except Exception as e:
            logger.error(f"Error in Qwen learning search: {e}")
            return []
    
    async def _qwen_enhance_search_results(self, search_results: List[SearchResult], query: str, agent_id: str) -> List[SearchResult]:
        """
        Qwen analizează și îmbunătățește rezultatele căutării
        """
        try:
            # Construiește promptul pentru Qwen
            context_text = "\n\n".join([f"Chunk {i+1}: {result.content}" for i, result in enumerate(search_results[:3])])
            
            qwen_prompt = f"""Ești Qwen, learning engine-ul care analizează și îmbunătățește rezultatele căutării.

QUERY-UL DE CĂUTARE: {query}

REZULTATELE GĂSITE:
{context_text}

Rolul tău:
1. Analizează relevanța fiecărui chunk pentru query
2. Identifică informațiile cheie
3. Sugerează îmbunătățiri pentru căutare

Răspunde cu un JSON:
{{
    "relevance_analysis": "Analiza relevanței rezultatelor",
    "key_information": ["info1", "info2", "info3"],
    "search_improvements": "Sugestii pentru îmbunătățirea căutării",
    "confidence_score": 0.85
}}"""

            # Apelează Qwen
            response = await self._call_qwen_simple(qwen_prompt)
            
            # Parsează răspunsul
            try:
                analysis = json.loads(response)
                logger.info(f"Qwen analysis: {analysis}")
            except json.JSONDecodeError:
                logger.warning("Qwen returned invalid JSON, using original results")
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error in Qwen enhancement: {e}")
            return search_results
    
    async def _qwen_fallback_learning(self, query: str, agent_id: str) -> List[SearchResult]:
        """
        Qwen încearcă să învețe din conținutul general al site-ului
        """
        try:
            # Obține conținutul general al agentului
            agent_content = list(self.db.site_content.find({
                'agent_id': ObjectId(agent_id)
            }).limit(5))
            
            if not agent_content:
                return []
            
            # Construiește promptul pentru Qwen
            content_text = "\n\n".join([f"Pagina {i+1}: {doc.get('content', '')[:500]}..." for i, doc in enumerate(agent_content)])
            
            qwen_prompt = f"""Ești Qwen, learning engine-ul care învață din conținutul site-ului.

QUERY-UL: {query}

CONȚINUTUL SITE-ULUI:
{content_text}

Rolul tău:
1. Analizează conținutul disponibil
2. Identifică informațiile relevante pentru query
3. Generează un rezumat relevant

Răspunde cu un JSON:
{{
    "relevant_content": "Conținutul relevant găsit",
    "summary": "Rezumatul informațiilor relevante",
    "confidence": 0.7
}}"""

            # Apelează Qwen
            response = await self._call_qwen_simple(qwen_prompt)
            
            # Parsează răspunsul
            try:
                analysis = json.loads(response)
                logger.info(f"Qwen fallback learning: {analysis}")
                
                # Creează un SearchResult din analiza Qwen
                if analysis.get('relevant_content'):
                    fallback_result = SearchResult(
                        content=analysis['relevant_content'],
                        metadata={'source': 'qwen_fallback_learning'},
                        score=analysis.get('confidence', 0.7),
                        chunk_id='qwen_fallback',
                        source_url=agent_content[0].get('url', '') if agent_content else ''
                    )
                    return [fallback_result]
                
            except json.JSONDecodeError:
                logger.warning("Qwen fallback returned invalid JSON")
            
            return []
            
        except Exception as e:
            logger.error(f"Error in Qwen fallback learning: {e}")
            return []
    
    async def _gpt_generate_final_answer(self, question: str, context: str, agent_id: str, 
                                       orchestration_plan: Dict, search_results: List[SearchResult]) -> Tuple[str, float, str]:
        """
        GPT generează răspunsul final bazat pe rezultatele de la Qwen
        """
        try:
            # Obține informații despre agent
            agent = self.db.agents.find_one({"_id": ObjectId(agent_id)})
            
            # Construiește promptul pentru GPT
            sources_text = "\n".join([f"- {result.source_url} (scor: {result.score:.2f})" for result in search_results])
            
            system_prompt = f"""Ești GPT, orchestratorul principal care generează răspunsul final pentru site-ul {agent.get('domain', 'necunoscut')}.

AGENTUL SELECTAT:
- Nume: {agent.get('name', 'N/A')}
- Domain: {agent.get('domain', 'N/A')}
- URL: {agent.get('site_url', 'N/A')}

PLANUL DE ORCHESTRARE:
- Analiza: {orchestration_plan.get('analysis', 'N/A')}
- Strategia: {orchestration_plan.get('search_strategy', 'N/A')}
- Tipurile de informații: {orchestration_plan.get('expected_info_types', [])}

CONTEXTUL GĂSIT DE QWEN:
{context}

SURSELE:
{sources_text}

ÎNTREBAREA UTILIZATORULUI: {question}

Rolul tău:
1. Generează un răspuns complet și precis
2. Citează sursele relevante
3. Menține contextul conversației
4. Asigură-te că răspunsul este relevant pentru site-ul specific

Răspunde în română, fiind util și precis. Include sursele în răspuns."""

            # Apelează GPT
            answer = await self._call_openai(system_prompt, question)
            
            # Calculează încrederea bazată pe surse și context
            confidence = self._calculate_confidence(search_results, context, orchestration_plan)
            
            # Generează reasoning-ul
            reasoning = f"GPT orchestrator a generat răspunsul bazat pe {len(search_results)} surse găsite de Qwen learning engine. Planul de orchestrare: {orchestration_plan.get('search_strategy', 'N/A')}"
            
            return answer, confidence, reasoning
            
        except Exception as e:
            logger.error(f"Error in GPT final answer generation: {e}")
            return "Îmi pare rău, nu am putut genera un răspuns complet. Vă rog să încercați din nou.", 0.3, f"Eroare în generarea răspunsului: {str(e)}"
    
    async def _call_openai(self, system_prompt: str, user_message: str) -> str:
        """
        Apelează OpenAI GPT API
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.openai_model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message}
                ],
                'temperature': 0.7,
                'max_tokens': 1000
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return "Eroare la conectarea la OpenAI API"
                
        except Exception as e:
            logger.error(f"Error calling OpenAI: {e}")
            return "Eroare la conectarea la OpenAI API"
    
    async def _call_qwen_simple(self, prompt: str) -> str:
        """
        Apelează Qwen local prin Ollama (versiune simplă cu un singur parametru)
        """
        try:
            data = {
                'model': self.qwen_model,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'stream': False,
                'temperature': 0.3
            }
            
            response = requests.post(
                f'{self.qwen_url}/api/chat',
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['message']['content']
            else:
                logger.error(f"Qwen API error: {response.status_code} - {response.text}")
                return "Eroare la conectarea la Qwen"
                
        except Exception as e:
            logger.error(f"Error calling Qwen: {e}")
            return "Eroare la conectarea la Qwen"
    
    def _format_conversation_history(self, conversation_history: List[Dict] = None) -> str:
        """
        Formatează istoricul conversației pentru prompt
        """
        if not conversation_history:
            return "Nu există istoric de conversație."
        
        formatted = []
        for i, conv in enumerate(conversation_history[-3:], 1):  # Ultimele 3 conversații
            formatted.append(f"Conversația {i}:")
            formatted.append(f"  User: {conv.get('user', '')}")
            formatted.append(f"  Assistant: {conv.get('assistant', '')}")
        
        return "\n".join(formatted)
    
    def _calculate_confidence(self, search_results: List[SearchResult], context: str, orchestration_plan: Dict) -> float:
        """
        Calculează nivelul de încredere al răspunsului
        """
        try:
            # Factorul de bază din surse
            if not search_results:
                return 0.3
            
            # Media scorurilor de similaritate
            avg_score = sum(result.score for result in search_results) / len(search_results)
            
            # Factorul de context (lungimea contextului)
            context_factor = min(len(context) / 1000, 1.0)  # Normalizează la 0-1
            
            # Factorul de plan (calitatea planului de orchestrare)
            plan_factor = 0.8 if orchestration_plan.get('search_strategy') else 0.5
            
            # Calculează încrederea finală
            confidence = (avg_score * 0.5 + context_factor * 0.3 + plan_factor * 0.2)
            
            return min(max(confidence, 0.1), 0.95)  # Limitează între 0.1 și 0.95
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5

# Funcție helper pentru a rula RAG pipeline
async def run_rag_pipeline(question: str, agent_id: str, config: Dict = None) -> RAGResponse:
    """Funcție helper pentru a rula RAG pipeline"""
    if config is None:
        config = {
            'qdrant_url': 'http://localhost:9306',
            'mongodb_uri': 'mongodb://localhost:9308',
            'mongodb_db': 'ai_agents_db',
            'qwen_url': 'http://localhost:11434',
            'qwen_model': 'qwen2.5:7b',
            'similarity_threshold': 0.7,
            'confidence_threshold': 0.7,
            'max_search_results': 5
        }
    
    pipeline = RAGPipeline(config)
    return await pipeline.ask_question(question, agent_id)

if __name__ == "__main__":
    # Test
    import asyncio
    
    async def test():
        response = await run_rag_pipeline(
            "Ce servicii oferiți?",
            "68f683f6f86c99d4d127ea81"
        )
        print(f"Answer: {response.answer}")
        print(f"Confidence: {response.confidence}")
        print(f"Sources: {len(response.sources)}")
    
    asyncio.run(test())



