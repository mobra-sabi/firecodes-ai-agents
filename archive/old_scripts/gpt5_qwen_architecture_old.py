#!/usr/bin/env python3
"""
GPT-5 + Qwen 2.5 Architecture
Implementează arhitectura completă conform specificațiilor:
- GPT-5: Orchestrator (planner/critic)
- Qwen 2.5: Executor (learning engine/site voice)
- Qdrant: Vector storage
- Brave API: Web search
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import requests
from openai import OpenAI
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class GPT5Plan:
    """Plan generat de GPT-5 (Orchestrator)"""
    mode: str  # "single_step" sau "plan"
    steps: List[Dict[str, Any]]
    guardrails: List[str]
    success_criteria: List[str]
    collection_priority: str  # "faq" sau "pages"

@dataclass
class QwenExecution:
    """Execuție realizată de Qwen 2.5 (Learning Engine)"""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    tool_calls_used: int
    context_used: str

@dataclass
class GPT5Critique:
    """Critică realizată de GPT-5"""
    ok: bool
    issues: List[str]
    missing: List[str]
    suggestions: List[str]

class GPT5QwenArchitecture:
    """Arhitectura completă GPT-5 + Qwen 2.5"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # GPT-5 Client (Orchestrator)
        self.gpt5_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url="https://api.openai.com/v1"
        )
        
        # Qwen 2.5 Client (Learning Engine)
        self.qwen_client = OpenAI(
            api_key="local",
            base_url=os.getenv("QWEN_BASE_URL", "http://localhost:11434/v1")
        )
        
        # Qdrant Client
        from qdrant_client import QdrantClient
        self.qdrant_client = QdrantClient(
            host=config.get("qdrant_host", "localhost"),
            port=config.get("qdrant_port", 9306)
        )
        
        # Brave API
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        
        # Configurații
        self.top_k = config.get("top_k", 6)
        self.confidence_threshold = config.get("confidence_threshold", 0.25)
        self.qwen_temperature = config.get("qwen_temperature", 0.2)
        
        logger.info("✅ GPT-5 + Qwen 2.5 Architecture initialized")
    
    async def process_question(self, question: str, agent_id: str, site_url: str) -> Dict[str, Any]:
        """Procesează o întrebare prin arhitectura completă"""
        start_time = time.time()
        
        try:
            # 1. Router - decide dacă e atomică sau complexă
            router_decision = await self._router(question)
            logger.info(f"🔀 Router decision: {router_decision}")
            
            if router_decision == "single_step":
                # Cale simplă: Qwen direct
                result = await self._single_step_execution(question, agent_id, site_url)
            else:
                # Cale complexă: GPT-5 plan + Qwen execuție + GPT-5 critică
                result = await self._complex_execution(question, agent_id, site_url)
            
            # Adaugă metadata
            result["architecture"] = "gpt5_qwen_hybrid"
            result["processing_time"] = time.time() - start_time
            result["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in GPT-5 + Qwen architecture: {e}")
            return {
                "ok": False,
                "error": str(e),
                "architecture": "gpt5_qwen_hybrid",
                "processing_time": time.time() - start_time
            }
    
    async def _router(self, question: str) -> str:
        """Router simplu - decide între single_step și plan"""
        # Heuristici simple
        complex_keywords = [
            "compară", "analizează", "evaluează", "planifică", "strategie",
            "multiple", "diferite", "opțiuni", "avantaje", "dezavantaje"
        ]
        
        question_lower = question.lower()
        if any(keyword in question_lower for keyword in complex_keywords):
            return "plan"
        
        # Dacă e întrebare atomică
        return "single_step"
    
    async def _single_step_execution(self, question: str, agent_id: str, site_url: str) -> Dict[str, Any]:
        """Execuție simplă cu Qwen 2.5"""
        try:
            # 1. Căutare în Qdrant
            search_results = await self._search_qdrant(question, agent_id, "faq")
            if not search_results:
                search_results = await self._search_qdrant(question, agent_id, "pages")
            
            # 2. Verifică dacă trebuie web search
            web_results = []
            if self._needs_web_search(question):
                web_results = await self._web_search(question)
            
            # 3. Qwen 2.5 execută
            qwen_response = await self._qwen_execute(
                question=question,
                context=search_results,
                web_context=web_results,
                site_url=site_url,
                mode="single_step"
            )
            
            return {
                "ok": True,
                "response": qwen_response.answer,
                "confidence": qwen_response.confidence,
                "sources": qwen_response.sources,
                "web_search_used": len(web_results) > 0,
                "web_sources": web_results,
                "execution_mode": "single_step",
                "llm_used": "qwen2.5"
            }
            
        except Exception as e:
            logger.error(f"❌ Error in single step execution: {e}")
            raise
    
    async def _complex_execution(self, question: str, agent_id: str, site_url: str) -> Dict[str, Any]:
        """Execuție complexă cu GPT-5 plan + Qwen execuție + GPT-5 critică"""
        try:
            # 1. GPT-5 generează plan
            gpt5_plan = await self._gpt5_plan(question, site_url)
            logger.info(f"📋 GPT-5 Plan: {gpt5_plan.mode}")
            
            # 2. Execută planul cu Qwen 2.5
            qwen_execution = await self._execute_plan(gpt5_plan, question, agent_id, site_url)
            logger.info(f"⚡ Qwen execution completed: {qwen_execution.confidence}")
            
            # 3. GPT-5 critică rezultatul
            gpt5_critique = await self._gpt5_critique(
                question=question,
                draft=qwen_execution.answer,
                sources=qwen_execution.sources,
                plan=gpt5_plan
            )
            logger.info(f"🔍 GPT-5 Critique: {gpt5_critique.ok}")
            
            # 4. Dacă critică nu e OK, repară cu Qwen
            if not gpt5_critique.ok and gpt5_critique.suggestions:
                logger.info("🔧 Repairing with Qwen based on GPT-5 critique")
                qwen_execution = await self._qwen_repair(
                    question=question,
                    original_answer=qwen_execution.answer,
                    critique=gpt5_critique,
                    context=qwen_execution.sources
                )
            
            return {
                "ok": True,
                "response": qwen_execution.answer,
                "confidence": qwen_execution.confidence,
                "sources": qwen_execution.sources,
                "execution_mode": "complex",
                "llm_used": "gpt5_qwen_hybrid",
                "plan": asdict(gpt5_plan),
                "critique": asdict(gpt5_critique),
                "web_search_used": False,  # TODO: implement în plan
                "web_sources": []
            }
            
        except Exception as e:
            logger.error(f"❌ Error in complex execution: {e}")
            raise
    
    async def _gpt5_plan(self, question: str, site_url: str) -> GPT5Plan:
        """GPT-5 generează plan de execuție"""
        domain = site_url.replace("https://", "").replace("http://", "").replace("www.", "")
        
        system_prompt = f"""Ești GPT-5, orchestratorul unui sistem AI hibrid. Generează un plan JSON pentru întrebarea utilizatorului.

CONTEXT: Site-ul {domain}
ÎNTREBARE: {question}

Generează un plan JSON cu această structură:
{{
    "mode": "single_step" sau "plan",
    "steps": [
        {{
            "step": 1,
            "action": "search_faq" sau "search_pages" sau "web_search" sau "analyze",
            "query": "query pentru căutare",
            "expected_output": "ce se așteaptă"
        }}
    ],
    "guardrails": ["regula1", "regula2"],
    "success_criteria": ["criteriu1", "criteriu2"],
    "collection_priority": "faq" sau "pages"
}}

Răspunde DOAR cu JSON valid, fără text suplimentar."""

        try:
            response = self.gpt5_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            plan_json = json.loads(response.choices[0].message.content)
            return GPT5Plan(**plan_json)
            
        except Exception as e:
            logger.error(f"❌ Error generating GPT-5 plan: {e}")
            # Fallback plan
            return GPT5Plan(
                mode="single_step",
                steps=[{"step": 1, "action": "search_pages", "query": question, "expected_output": "answer"}],
                guardrails=["be_accurate", "cite_sources"],
                success_criteria=["answer_question", "provide_sources"],
                collection_priority="pages"
            )
    
    async def _execute_plan(self, plan: GPT5Plan, question: str, agent_id: str, site_url: str) -> QwenExecution:
        """Execută planul cu Qwen 2.5"""
        context_parts = []
        sources = []
        
        # Execută fiecare pas din plan
        for step in plan.steps:
            if step["action"] == "search_faq":
                results = await self._search_qdrant(step["query"], agent_id, "faq")
                context_parts.extend([r["content"] for r in results])
                sources.extend(results)
            elif step["action"] == "search_pages":
                results = await self._search_qdrant(step["query"], agent_id, "pages")
                context_parts.extend([r["content"] for r in results])
                sources.extend(results)
            elif step["action"] == "web_search":
                results = await self._web_search(step["query"])
                context_parts.extend([r["description"] for r in results])
                sources.extend(results)
        
        # Qwen execută cu contextul
        return await self._qwen_execute(
            question=question,
            context=sources,
            web_context=[],
            site_url=site_url,
            mode="plan_execution"
        )
    
    async def _qwen_execute(self, question: str, context: List[Dict], web_context: List[Dict], site_url: str, mode: str) -> QwenExecution:
        """Qwen 2.5 execută întrebarea"""
        domain = site_url.replace("https://", "").replace("http://", "").replace("www.", "")
        
        # Pregătește contextul
        context_text = "\n\n".join([
            f"**Sursa {i+1}:** {ctx.get('content', ctx.get('description', ''))}"
            for i, ctx in enumerate(context[:5])  # Limitează la 5 surse
        ])
        
        web_context_text = "\n\n".join([
            f"**Web {i+1}:** {web.get('title', '')} - {web.get('description', '')}"
            for i, web in enumerate(web_context[:3])  # Limitează la 3 surse web
        ])
        
        system_prompt = f"""Ești Qwen 2.5, learning engine-ul și vocea site-ului {domain}.

ROL: Executor și vocea site-ului
MOD: {mode}

CONTEXT SITE-ULUI:
{context_text}

CONTEXT WEB:
{web_context_text}

INSTRUCȚIUNI:
1. Răspunde DOAR din contextul furnizat
2. Dacă nu ai informații suficiente, spui "Nu știu" + pași de verificare
3. Citezi sursele (minim 2 dacă există)
4. Fii concis și precis
5. Temperatura: {self.qwen_temperature} (QA precis)

FORMATARE:
- Folosește emoji-uri: 🔍 📋 💡 📞 ⭐ ❓
- Titluri bold: **Titlu**
- Bullet points: •
- Spațiere între secțiuni

Răspunde în română, ca reprezentant oficial al {domain}."""

        try:
            response = self.qwen_client.chat.completions.create(
                model=os.getenv("QWEN_MODEL", "qwen:latest"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=self.qwen_temperature,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            
            # Calculează confidence pe baza surselor
            confidence = min(0.9, 0.5 + (len(context) * 0.1))
            
            return QwenExecution(
                answer=answer,
                sources=context,
                confidence=confidence,
                tool_calls_used=len(context),
                context_used=context_text[:500] + "..." if len(context_text) > 500 else context_text
            )
            
        except Exception as e:
            logger.error(f"❌ Error in Qwen execution: {e}")
            return QwenExecution(
                answer="Îmi pare rău, nu pot răspunde în acest moment. Te rog să încerci din nou.",
                sources=[],
                confidence=0.0,
                tool_calls_used=0,
                context_used=""
            )
    
    async def _gpt5_critique(self, question: str, draft: str, sources: List[Dict], plan: GPT5Plan) -> GPT5Critique:
        """GPT-5 critică răspunsul generat de Qwen"""
        system_prompt = f"""Ești GPT-5, criticul sistemului AI hibrid. Analizează răspunsul generat.

ÎNTREBARE: {question}
RĂSPUNS GENERAT: {draft}
SURSE: {len(sources)} surse furnizate
PLAN: {plan.mode}

Critică răspunsul și returnează JSON:
{{
    "ok": true/false,
    "issues": ["problema1", "problema2"],
    "missing": ["lipsește1", "lipsește2"],
    "suggestions": ["sugestie1", "sugestie2"]
}}

CRITERII:
1. Răspunsul răspunde la întrebare?
2. Sunt sursele citate corect?
3. Informațiile sunt accurate?
4. Răspunsul este complet?
5. Respectă guardrails-urile: {plan.guardrails}

Răspunde DOAR cu JSON valid."""

        try:
            response = self.gpt5_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            critique_json = json.loads(response.choices[0].message.content)
            return GPT5Critique(**critique_json)
            
        except Exception as e:
            logger.error(f"❌ Error in GPT-5 critique: {e}")
            return GPT5Critique(
                ok=True,
                issues=[],
                missing=[],
                suggestions=[]
            )
    
    async def _qwen_repair(self, question: str, original_answer: str, critique: GPT5Critique, context: List[Dict]) -> QwenExecution:
        """Qwen repară răspunsul pe baza criticii GPT-5"""
        system_prompt = f"""Ești Qwen 2.5. Repară răspunsul pe baza criticii GPT-5.

ÎNTREBARE: {question}
RĂSPUNS ORIGINAL: {original_answer}

CRITICA GPT-5:
- OK: {critique.ok}
- Probleme: {critique.issues}
- Lipsește: {critique.missing}
- Sugestii: {critique.suggestions}

CONTEXT: {len(context)} surse disponibile

Generează un răspuns îmbunătățit care:
1. Rezolvă problemele identificate
2. Adaugă informațiile lipsă
3. Urmează sugestiile
4. Menține acuratețea și citarea surselor

Răspunde în română, formatat frumos cu emoji-uri."""

        try:
            response = self.qwen_client.chat.completions.create(
                model=os.getenv("QWEN_MODEL", "qwen:latest"),
                messages=[{"role": "system", "content": system_prompt}],
                temperature=0.3,  # Puțin mai creativ pentru reparare
                max_tokens=2000
            )
            
            repaired_answer = response.choices[0].message.content
            
            return QwenExecution(
                answer=repaired_answer,
                sources=context,
                confidence=0.8,  # Confidence mai mare după reparare
                tool_calls_used=len(context),
                context_used="repaired"
            )
            
        except Exception as e:
            logger.error(f"❌ Error in Qwen repair: {e}")
            return QwenExecution(
                answer=original_answer,  # Returnează originalul dacă repararea eșuează
                sources=context,
                confidence=0.5,
                tool_calls_used=len(context),
                context_used="repair_failed"
            )
    
    async def _search_qdrant(self, query: str, agent_id: str, collection_type: str) -> List[Dict[str, Any]]:
        """Caută în Qdrant"""
        try:
            collection_name = f"agent_{agent_id}_{collection_type}"
            
            # Generează embedding pentru query
            embedding = await self._generate_embedding(query)
            
            # Caută în Qdrant
            results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=embedding,
                limit=self.top_k,
                score_threshold=self.confidence_threshold
            )
            
            return [
                {
                    "content": result.payload.get("content", ""),
                    "url": result.payload.get("url", ""),
                    "title": result.payload.get("title", ""),
                    "score": result.score
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"❌ Error searching Qdrant: {e}")
            return []
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generează embedding pentru text"""
        try:
            # Folosește OpenAI embeddings
            response = self.gpt5_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}")
            return [0.0] * 1536  # Fallback
    
    async def _web_search(self, query: str) -> List[Dict[str, str]]:
        """Caută pe internet cu Brave API"""
        if not self.brave_api_key:
            return []
        
        try:
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.brave_api_key
            }
            
            params = {"q": query, "count": 3}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers=headers,
                    params=params,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        if "web" in data and "results" in data["web"]:
                            for result in data["web"]["results"]:
                                results.append({
                                    "title": result.get("title", ""),
                                    "url": result.get("url", ""),
                                    "description": result.get("description", ""),
                                    "age": result.get("age", "")
                                })
                        
                        return results
                    else:
                        logger.error(f"❌ Brave API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Error in web search: {e}")
            return []
    
    def _needs_web_search(self, question: str) -> bool:
        """Decide dacă întrebarea necesită web search"""
        web_keywords = [
            "preț", "prețuri", "cost", "actual", "curent", "ultim", "nou",
            "compară", "diferență", "opțiuni", "alternativ"
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in web_keywords)

# Funcție de utilitate pentru crearea arhitecturii
def create_gpt5_qwen_architecture(config: Dict[str, Any] = None) -> GPT5QwenArchitecture:
    """Creează instanța arhitecturii GPT-5 + Qwen 2.5"""
    if config is None:
        config = {
            "qdrant_host": "localhost",
            "qdrant_port": 9306,
            "top_k": 6,
            "confidence_threshold": 0.25,
            "qwen_temperature": 0.2
        }
    
    return GPT5QwenArchitecture(config)

if __name__ == "__main__":
    async def test_architecture():
        architecture = create_gpt5_qwen_architecture()
        
        result = await architecture.process_question(
            question="Ce servicii oferiți?",
            agent_id="test_agent",
            site_url="https://protectiilafoc.ro"
        )
        
        print("🔍 Test Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test_architecture())
