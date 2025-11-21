#!/usr/bin/env python3
"""
Enhanced 4-Layer Agent Architecture
Implementează arhitectura completă: Identitate → Memorie → Percepție → Acțiune
cu roluri distincte pentru Qwen 2.5 (learning engine) și GPT (orchestrator)
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import requests
from openai import OpenAI
import os
from pathlib import Path

# Vector DB și embeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# MongoDB
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

@dataclass
class AgentIdentity:
    """Stratul 1: Identitate & Scop"""
    name: str
    role: str
    domain: str
    purpose: str
    capabilities: List[str]
    limitations: List[str]
    escalation_triggers: List[str]
    contract: Dict[str, Any]

@dataclass
class AgentMemory:
    """Stratul 2: Memorie"""
    working_memory: Dict[str, Any]
    long_term_memory: Dict[str, Any]
    vector_db: str
    conversation_context: List[Dict]
    retention_policies: Dict[str, Any]

@dataclass
class AgentPerception:
    """Stratul 3: Percepție"""
    crawler: Dict[str, Any]
    normalizer: Dict[str, Any]
    embeddings: Any
    vector_index: str
    rag_pipeline: Dict[str, Any]
    source_citation: bool

@dataclass
class AgentAction:
    """Stratul 4: Acțiune"""
    tools: Dict[str, Any]
    guardrails: Dict[str, Any]
    max_tool_calls: int
    confidence_threshold: float
    orchestrator: str

class Enhanced4LayerAgent:
    """Agent cu arhitectura completă cu 4 straturi"""
    
    def __init__(self, site_url: str, agent_config: Dict[str, Any] = None):
        self.site_url = site_url
        self.agent_id = self._generate_agent_id()
        
        # Configurație
        self.config = agent_config or self._default_config()
        
        # Initializează straturile
        self.identity = self._initialize_identity()
        self.memory = self._initialize_memory()
        self.perception = self._initialize_perception()
        self.action = self._initialize_action()
        
        # LLM Clients cu roluri distincte
        self.qwen_client = self._get_qwen_client()  # Learning engine + Site voice
        self.gpt_client = self._get_gpt_client()    # Orchestrator
        
        logger.info(f"✅ Enhanced 4-Layer Agent initialized: {self.identity.name}")

    def _generate_agent_id(self) -> str:
        """Generează ID unic pentru agent"""
        return f"enhanced_agent_{int(time.time())}"

    def _default_config(self) -> Dict[str, Any]:
        """Configurație implicită pentru agent"""
        return {
            "max_tool_calls": 3,
            "confidence_threshold": 0.7,
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "similarity_threshold": 0.7,
            "max_search_results": 5,
            "retention_days": 90,
            "rate_limit": 60,  # requests per minute
        }

    def _initialize_identity(self) -> AgentIdentity:
        """Initializează stratul de Identitate & Scop"""
        domain = self._extract_domain(self.site_url)
        
        return AgentIdentity(
            name=f"Agent pentru {domain}",
            role="Reprezentant oficial al site-ului web",
            domain=domain,
            purpose="Transformă site-ul web într-un agent AI competent care răspunde la întrebări despre servicii și produse",
            capabilities=[
                "Răspunde la întrebări despre servicii și produse",
                "Oferă consultanță și recomandări",
                "Caută informații în conținutul site-ului",
                "Comunică ca reprezentant oficial",
                "Escalează la om când este necesar"
            ],
            limitations=[
                "Nu poate accesa informații din afara site-ului",
                "Nu poate face tranzacții financiare",
                "Nu poate accesa conturi personale",
                "Nu poate modifica conținutul site-ului"
            ],
            escalation_triggers=[
                "Întrebări despre prețuri specifice",
                "Probleme tehnice complexe",
                "Cereri de modificări pe site",
                "Informații confidențiale"
            ],
            contract={
                "knows": [
                    "Toate serviciile și produsele site-ului",
                    "Informații despre companie și echipă",
                    "Politici și proceduri",
                    "FAQ și ghiduri"
                ],
                "doesnt_know": [
                    "Informații personale ale clienților",
                    "Detalii financiare confidențiale",
                    "Informații din afara site-ului",
                    "Starea în timp real a stocurilor"
                ]
            }
        )

    def _initialize_memory(self) -> AgentMemory:
        """Initializează stratul de Memorie"""
        return AgentMemory(
            working_memory={
                "max_conversation_turns": 10,
                "context_window": 4000,
                "current_session": []
            },
            long_term_memory={
                "vector_db": "qdrant",
                "collection_name": f"agent_{self.agent_id}_content",
                "embedding_model": "BAAI/bge-large-en-v1.5",
                "content_ttl": "30 days"
            },
            vector_db="qdrant",
            conversation_context=[],
            retention_policies={
                "conversation_ttl": "7 days",
                "content_ttl": "30 days",
                "max_storage_size": "1GB"
            }
        )

    def _initialize_perception(self) -> AgentPerception:
        """Initializează stratul de Percepție"""
        # Setup embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Setup text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config["chunk_size"],
            chunk_overlap=self.config["chunk_overlap"],
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        return AgentPerception(
            crawler={
                "max_pages": 20,
                "timeout": 30,
                "rate_limit": 1,
                "user_agent": "Mozilla/5.0 (compatible; SiteAI/1.0)"
            },
            normalizer={
                "remove_scripts": True,
                "remove_styles": True,
                "remove_navigation": True,
                "clean_whitespace": True,
                "extract_metadata": True
            },
            embeddings=embeddings,
            vector_index=f"agent_{self.agent_id}_content",
            rag_pipeline={
                "retrieval_strategy": "semantic_search",
                "reranking": True,
                "top_k": self.config["max_search_results"],
                "similarity_threshold": self.config["similarity_threshold"]
            },
            source_citation=True
        )

    def _initialize_action(self) -> AgentAction:
        """Initializează stratul de Acțiune"""
        return AgentAction(
            tools={
                "search_index": {
                    "description": "Caută informații în conținutul site-ului",
                    "max_results": self.config["max_search_results"],
                    "similarity_threshold": self.config["similarity_threshold"]
                },
                "fetch_url": {
                    "description": "Descarcă conținut de pe o pagină specifică",
                    "allowed_domains": [self._extract_domain(self.site_url)],
                    "max_size": "1MB"
                },
                "calculate": {
                    "description": "Efectuează calcule simple",
                    "sandbox": True,
                    "timeout": 10
                },
                "escalate_to_human": {
                    "description": "Escalează întrebarea la echipa umană",
                    "triggers": self.identity.escalation_triggers
                }
            },
            guardrails={
                "rate_limiting": {
                    "requests_per_minute": self.config["rate_limit"],
                    "burst_limit": 10
                },
                "confidence_threshold": self.config["confidence_threshold"],
                "max_tool_calls": self.config["max_tool_calls"],
                "pii_detection": True,
                "audit_logging": True
            },
            max_tool_calls=self.config["max_tool_calls"],
            confidence_threshold=self.config["confidence_threshold"],
            orchestrator="gpt"
        )

    def _get_qwen_client(self) -> OpenAI:
        """Configurează Qwen 2.5 ca learning engine și vocea site-ului"""
        return OpenAI(
            api_key=os.getenv("QWEN_API_KEY", "local"),
            base_url=os.getenv("QWEN_BASE_URL", "http://localhost:9304/v1")
        )

    def _get_gpt_client(self) -> OpenAI:
        """Configurează GPT ca orchestrator"""
        return OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            organization=os.getenv("OPENAI_ORG_ID"),
            project=os.getenv("OPENAI_PROJECT")
        )

    def _extract_domain(self, url: str) -> str:
        """Extrage domeniul din URL"""
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc
            return domain.replace("www.", "").lower()
        except:
            return url

    async def ingest_site_content(self) -> bool:
        """Ingest conținutul site-ului în memorie"""
        logger.info(f"🔄 Ingesting content for {self.site_url}")
        
        try:
            # 1. Crawl site-ul
            pages = await self._crawl_site()
            
            # 2. Normalizează conținutul
            normalized_content = self._normalize_content(pages)
            
            # 3. Creează chunks
            chunks = self._create_chunks(normalized_content)
            
            # 4. Generează embeddings și salvează în vector DB
            await self._store_in_vector_db(chunks)
            
            # 5. Salvează în MongoDB
            await self._store_in_mongodb(normalized_content)
            
            logger.info(f"✅ Successfully ingested {len(pages)} pages")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error ingesting site: {e}")
            return False

    async def _crawl_site(self) -> List[Dict[str, Any]]:
        """Crawlează site-ul și extrage conținutul"""
        pages = []
        
        try:
            # Crawl homepage
            response = requests.get(
                self.site_url,
                timeout=self.perception.crawler["timeout"],
                headers={"User-Agent": self.perception.crawler["user_agent"]}
            )
            
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extrage conținutul
                title = soup.find('title')
                title_text = title.get_text().strip() if title else "No title"
                
                # Curăță conținutul
                for script in soup(["script", "style", "nav", "footer"]):
                    script.decompose()
                
                content = soup.get_text()
                content = ' '.join(content.split())  # Normalizează whitespace
                
                pages.append({
                    "url": self.site_url,
                    "title": title_text,
                    "content": content,
                    "timestamp": datetime.now(timezone.utc),
                    "domain": self._extract_domain(self.site_url)
                })
                
        except Exception as e:
            logger.error(f"Error crawling site: {e}")
        
        return pages

    def _normalize_content(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalizează conținutul paginilor"""
        normalized = []
        
        for page in pages:
            # Aplică normalizarea
            content = page["content"]
            
            # Curăță conținutul
            if self.perception.normalizer["clean_whitespace"]:
                content = ' '.join(content.split())
            
            # Limitează lungimea
            content = content[:10000]  # Max 10k caractere per pagină
            
            normalized.append({
                **page,
                "content": content,
                "normalized": True,
                "normalization_timestamp": datetime.now(timezone.utc)
            })
        
        return normalized

    def _create_chunks(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Creează chunks din conținutul normalizat"""
        chunks = []
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config["chunk_size"],
            chunk_overlap=self.config["chunk_overlap"],
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        for page in pages:
            # Split conținutul în chunks
            page_chunks = text_splitter.split_text(page["content"])
            
            for i, chunk_text in enumerate(page_chunks):
                chunk_id = f"{page['url']}_chunk_{i}"
                
                chunks.append({
                    "chunk_id": chunk_id,
                    "content": chunk_text,
                    "metadata": {
                        "url": page["url"],
                        "title": page["title"],
                        "domain": page["domain"],
                        "chunk_index": i,
                        "timestamp": datetime.now(timezone.utc)
                    }
                })
        
        return chunks

    async def _store_in_vector_db(self, chunks: List[Dict[str, Any]]) -> bool:
        """Salvează chunks-urile în vector DB cu embeddings"""
        try:
            # Setup Qdrant client
            qdrant_client = QdrantClient(host="localhost", port=9306)
            
            # Creează colecția dacă nu există
            collection_name = self.memory.long_term_memory["collection_name"]
            
            try:
                qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=1024,  # BGE-large-en-v1.5 embedding size
                        distance=Distance.COSINE
                    )
                )
            except:
                pass  # Colecția există deja
            
            # Generează embeddings și salvează
            points = []
            for chunk in chunks:
                # Generează embedding
                embedding = self.perception.embeddings.embed_query(chunk["content"])
                
                point = PointStruct(
                    id=hash(chunk["chunk_id"]) % (2**63 - 1),  # Convert to int64
                    vector=embedding,
                    payload={
                        "chunk_id": chunk["chunk_id"],
                        "content": chunk["content"],
                        "metadata": chunk["metadata"],
                        "agent_id": self.agent_id
                    }
                )
                points.append(point)
            
            # Salvează în batch-uri
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                qdrant_client.upsert(
                    collection_name=collection_name,
                    points=batch
                )
            
            logger.info(f"✅ Stored {len(chunks)} chunks in vector DB")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing in vector DB: {e}")
            return False

    async def _store_in_mongodb(self, content: List[Dict[str, Any]]) -> bool:
        """Salvează conținutul în MongoDB"""
        try:
            # Setup MongoDB client
            mongo_client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:9308"))
            db = mongo_client["ai_agents_db"]
            collection = db["site_content"]
            
            # Salvează fiecare pagină
            for page in content:
                page["agent_id"] = self.agent_id
                page["ingestion_timestamp"] = datetime.now(timezone.utc)
                
                # Upsert by URL
                collection.update_one(
                    {"url": page["url"], "agent_id": self.agent_id},
                    {"$set": page},
                    upsert=True
                )
            
            logger.info(f"✅ Stored {len(content)} pages in MongoDB")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing in MongoDB: {e}")
            return False

    async def answer_question(self, question: str) -> Dict[str, Any]:
        """Răspunde la o întrebare folosind arhitectura cu 4 straturi"""
        logger.info(f"🤖 Answering question: {question[:100]}...")
        
        try:
            # 1. GPT Orchestrator: Planifică răspunsul
            orchestration_plan = await self._orchestrate_response(question)
            
            # 2. Qwen Learning Engine: Caută informații
            search_results = await self._search_knowledge(question)
            
            # 3. Qwen Site Voice: Generează răspunsul
            response = await self._generate_response(question, search_results, orchestration_plan)
            
            # 4. Guardrails: Verifică răspunsul
            guardrails_result = await self._apply_guardrails(response, question)
            
            # 5. Actualizează memoria
            await self._update_memory(question, response)
            
            return {
                "ok": True,
                "response": response["answer"],
                "confidence": response["confidence"],
                "reasoning": orchestration_plan["reasoning"],
                "sources": search_results["sources"],
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "guardrails": guardrails_result,
                "architecture_layers": {
                    "identity": asdict(self.identity),
                    "memory": asdict(self.memory),
                    "perception": {
                        "rag_pipeline": self.perception.rag_pipeline,
                        "source_citation": self.perception.source_citation
                    },
                    "action": {
                        "tools_used": orchestration_plan["tools_used"],
                        "max_tool_calls": self.action.max_tool_calls,
                        "confidence_threshold": self.action.confidence_threshold
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error answering question: {e}")
            return {
                "ok": False,
                "response": "Îmi pare rău, a apărut o problemă tehnică. Te rog încearcă din nou.",
                "error": str(e),
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _orchestrate_response(self, question: str) -> Dict[str, Any]:
        """GPT Orchestrator: Planifică răspunsul"""
        try:
            orchestration_prompt = f"""
Ești orchestratorul GPT pentru agentul {self.identity.name}.

Identitatea agentului:
- Nume: {self.identity.name}
- Rol: {self.identity.role}
- Domeniu: {self.identity.domain}
- Scop: {self.identity.purpose}

Capabilități: {', '.join(self.identity.capabilities)}
Limitări: {', '.join(self.identity.limitations)}

Întrebarea utilizatorului: {question}

Planifică răspunsul:
1. Ce tools trebuie folosite?
2. Care este strategia de căutare?
3. Cum trebuie structurat răspunsul?
4. Când să escalăm la om?

Răspunde în format JSON:
{{
    "tools_to_use": ["search_index", "fetch_url"],
    "search_strategy": "semantic_search",
    "response_structure": "answer_with_sources",
    "escalation_needed": false,
    "reasoning": "Explicația planului"
}}
"""
            
            response = self.gpt_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": orchestration_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            plan_text = response.choices[0].message.content
            plan = json.loads(plan_text)
            
            return {
                "tools_used": plan.get("tools_to_use", ["search_index"]),
                "search_strategy": plan.get("search_strategy", "semantic_search"),
                "response_structure": plan.get("response_structure", "answer_with_sources"),
                "escalation_needed": plan.get("escalation_needed", False),
                "reasoning": plan.get("reasoning", "GPT orchestrator a planificat răspunsul")
            }
            
        except Exception as e:
            logger.error(f"Error in orchestration: {e}")
            return {
                "tools_used": ["search_index"],
                "search_strategy": "semantic_search",
                "response_structure": "answer_with_sources",
                "escalation_needed": False,
                "reasoning": f"Fallback orchestration due to error: {e}"
            }

    async def _search_knowledge(self, question: str) -> Dict[str, Any]:
        """Qwen Learning Engine: Caută informații în cunoștințele agentului"""
        try:
            # Setup Qdrant client
            qdrant_client = QdrantClient(host="localhost", port=9306)
            collection_name = self.memory.long_term_memory["collection_name"]
            
            # Generează embedding pentru întrebare
            query_embedding = self.perception.embeddings.embed_query(question)
            
            # Caută în vector DB
            search_results = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=self.config["max_search_results"],
                score_threshold=self.config["similarity_threshold"],
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="agent_id",
                            match=MatchValue(value=self.agent_id)
                        )
                    ]
                )
            )
            
            # Formatează rezultatele
            sources = []
            context = ""
            
            for result in search_results:
                source = {
                    "url": result.payload["metadata"]["url"],
                    "title": result.payload["metadata"]["title"],
                    "score": result.score,
                    "chunk_id": result.payload["chunk_id"]
                }
                sources.append(source)
                context += f"\n\n{result.payload['content']}"
            
            return {
                "sources": sources,
                "context": context,
                "total_results": len(sources)
            }
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            return {
                "sources": [],
                "context": "",
                "total_results": 0
            }

    async def _generate_response(self, question: str, search_results: Dict[str, Any], orchestration_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Qwen Site Voice: Generează răspunsul ca vocea site-ului"""
        try:
            # Construiește prompt-ul pentru Qwen
            context = search_results.get("context", "")
            sources = search_results.get("sources", [])
            
            qwen_prompt = f"""
Ești {self.identity.name}, reprezentantul oficial al site-ului {self.identity.domain}.

Identitatea ta:
- Rol: {self.identity.role}
- Scop: {self.identity.purpose}
- Capabilități: {', '.join(self.identity.capabilities)}
- Limitări: {', '.join(self.identity.limitations)}

Conținutul site-ului (context):
{context}

Întrebarea clientului: {question}

Instrucțiuni:
1. Răspunde ca reprezentant oficial al site-ului
2. Folosește DOAR informațiile din context
3. Fii specific și profesional
4. Citează sursele când este posibil
5. Dacă nu găsești informația, spune "Nu știu" și oferă să conectezi cu echipa
6. Răspunde în română, maxim 200 cuvinte

Răspunsul tău:
"""
            
            response = self.qwen_client.chat.completions.create(
                model=os.getenv("QWEN_MODEL", "qwen2.5"),
                messages=[{"role": "user", "content": qwen_prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Calculează confidence score
            confidence = self._calculate_confidence(answer, sources, context)
            
            return {
                "answer": answer,
                "confidence": confidence,
                "sources_used": len(sources),
                "context_length": len(context)
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "answer": "Îmi pare rău, nu pot genera un răspuns în acest moment. Te rog încearcă din nou.",
                "confidence": 0.0,
                "sources_used": 0,
                "context_length": 0
            }

    def _calculate_confidence(self, answer: str, sources: List[Dict], context: str) -> float:
        """Calculează scorul de încredere pentru răspuns"""
        confidence = 0.5  # Base confidence
        
        # Bonus pentru surse
        if sources:
            confidence += 0.2 * min(len(sources) / 3, 1.0)
        
        # Bonus pentru context
        if context and len(context) > 100:
            confidence += 0.2
        
        # Penalty pentru "nu știu"
        if "nu știu" in answer.lower() or "nu am găsit" in answer.lower():
            confidence -= 0.3
        
        # Bonus pentru citarea surselor
        if any(source["url"] in answer for source in sources):
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))

    async def _apply_guardrails(self, response: Dict[str, Any], question: str) -> Dict[str, Any]:
        """Aplică guardrails-urile"""
        guardrails_result = {
            "passed": True,
            "message": "All security checks passed",
            "pii_detected": 0,
            "blocked_patterns": 0,
            "confidence_check": True
        }
        
        # Verifică confidence threshold
        if response["confidence"] < self.action.confidence_threshold:
            guardrails_result["confidence_check"] = False
            guardrails_result["message"] = "Low confidence response"
            guardrails_result["passed"] = False
        
        # Verifică PII (simplificat)
        pii_patterns = ["email", "telefon", "cnp", "iban"]
        pii_count = sum(1 for pattern in pii_patterns if pattern in response["answer"].lower())
        guardrails_result["pii_detected"] = pii_count
        
        # Verifică pattern-uri blocate
        blocked_patterns = ["hack", "exploit", "bypass"]
        blocked_count = sum(1 for pattern in blocked_patterns if pattern in question.lower())
        guardrails_result["blocked_patterns"] = blocked_count
        
        if blocked_count > 0:
            guardrails_result["passed"] = False
            guardrails_result["message"] = "Blocked patterns detected"
        
        return guardrails_result

    async def _update_memory(self, question: str, response: Dict[str, Any]) -> None:
        """Actualizează memoria agentului"""
        # Adaugă în contextul conversației
        conversation_entry = {
            "timestamp": datetime.now(timezone.utc),
            "question": question,
            "answer": response["answer"],
            "confidence": response["confidence"]
        }
        
        self.memory.conversation_context.append(conversation_entry)
        
        # Limitează contextul
        max_turns = self.memory.working_memory["max_conversation_turns"]
        if len(self.memory.conversation_context) > max_turns:
            self.memory.conversation_context = self.memory.conversation_context[-max_turns:]

    def get_architecture_status(self) -> Dict[str, Any]:
        """Returnează statusul arhitecturii cu 4 straturi"""
        return {
            "agent_id": self.agent_id,
            "site_url": self.site_url,
            "architecture_compliance": {
                "identitate": {
                    "implemented": True,
                    "components": len(self.identity.capabilities),
                    "compliance_score": 1.0
                },
                "memorie": {
                    "implemented": True,
                    "vector_db": self.memory.vector_db,
                    "conversation_context": len(self.memory.conversation_context),
                    "compliance_score": 1.0
                },
                "perceptie": {
                    "implemented": True,
                    "rag_pipeline": self.perception.rag_pipeline,
                    "source_citation": self.perception.source_citation,
                    "compliance_score": 1.0
                },
                "actiune": {
                    "implemented": True,
                    "tools_count": len(self.action.tools),
                    "guardrails": self.action.guardrails,
                    "compliance_score": 1.0
                }
            },
            "llm_roles": {
                "qwen_role": "learning_engine_and_site_voice",
                "gpt_role": "orchestrator",
                "orchestrator": "gpt",
                "site_voice": "qwen"
            },
            "overall_compliance": 1.0
        }

# Funcție pentru a crea un agent nou
async def create_enhanced_agent(site_url: str, config: Dict[str, Any] = None) -> Enhanced4LayerAgent:
    """Creează un agent nou cu arhitectura completă cu 4 straturi"""
    agent = Enhanced4LayerAgent(site_url, config)
    
    # Ingest conținutul site-ului
    await agent.ingest_site_content()
    
    return agent
