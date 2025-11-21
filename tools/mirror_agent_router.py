#!/usr/bin/env python3
"""
Mirror Agent Router - Logică routing inteligentă pentru agentul Mirror
Issue 5: Configurează routerul pentru agentul Mirror Q/A
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import requests
import json

logger = logging.getLogger(__name__)

class RoutingDecision(Enum):
    """Deciziile de routing"""
    FAQ_RESPONSE = "faq_response"
    PAGES_SEARCH = "pages_search"
    DONT_KNOW = "dont_know"
    ESCALATE = "escalate"

@dataclass
class RoutingResult:
    """Rezultatul routing-ului"""
    decision: RoutingDecision
    confidence: float
    similarity_score: float
    reasoning: str
    sources: List[Dict[str, Any]]
    fallback_used: bool = False
    processing_time: float = 0.0

@dataclass
class RouterConfig:
    """Configurația router-ului"""
    faq_similarity_threshold: float = 0.83
    pages_similarity_threshold: float = 0.70
    min_confidence_threshold: float = 0.5
    max_sources: int = 5
    enable_fallback: bool = True
    enable_escalation: bool = True
    escalation_threshold: float = 0.3

class MirrorAgentRouter:
    """Router inteligent pentru agentul Mirror"""
    
    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        self.client = QdrantClient(url=qdrant_url)
        self.config = RouterConfig()
        self.routing_stats = {
            "total_requests": 0,
            "faq_responses": 0,
            "pages_searches": 0,
            "dont_know_responses": 0,
            "escalations": 0,
            "avg_processing_time": 0.0
        }
    
    async def route_question(self, question: str, site_id: str, manifest: Dict[str, Any]) -> RoutingResult:
        """
        Routează o întrebare către cea mai bună sursă de răspuns
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔄 Routing question for site {site_id}: {question[:50]}...")
            
            # 1. Încearcă mai întâi FAQ-ul
            faq_result = await self._search_faq(question, site_id)
            
            if faq_result["similarity_score"] >= self.config.faq_similarity_threshold:
                processing_time = time.time() - start_time
                self._update_stats("faq_responses", processing_time)
                
                return RoutingResult(
                    decision=RoutingDecision.FAQ_RESPONSE,
                    confidence=faq_result["confidence"],
                    similarity_score=faq_result["similarity_score"],
                    reasoning=f"FAQ match found with similarity {faq_result['similarity_score']:.3f}",
                    sources=faq_result["sources"],
                    processing_time=processing_time
                )
            
            # 2. Dacă FAQ-ul nu este suficient, caută în pages
            pages_result = await self._search_pages(question, site_id)
            
            if pages_result["similarity_score"] >= self.config.pages_similarity_threshold:
                processing_time = time.time() - start_time
                self._update_stats("pages_searches", processing_time)
                
                return RoutingResult(
                    decision=RoutingDecision.PAGES_SEARCH,
                    confidence=pages_result["confidence"],
                    similarity_score=pages_result["similarity_score"],
                    reasoning=f"Pages match found with similarity {pages_result['similarity_score']:.3f}",
                    sources=pages_result["sources"],
                    processing_time=processing_time
                )
            
            # 3. Dacă nici pages nu este suficient, verifică dacă trebuie să escaladez
            max_similarity = max(faq_result["similarity_score"], pages_result["similarity_score"])
            
            if max_similarity < self.config.escalation_threshold and self.config.enable_escalation:
                processing_time = time.time() - start_time
                self._update_stats("escalations", processing_time)
                
                return RoutingResult(
                    decision=RoutingDecision.ESCALATE,
                    confidence=0.1,
                    similarity_score=max_similarity,
                    reasoning=f"Similarity too low ({max_similarity:.3f}), escalating to human",
                    sources=[],
                    processing_time=processing_time
                )
            
            # 4. Fallback la "Nu știu"
            processing_time = time.time() - start_time
            self._update_stats("dont_know_responses", processing_time)
            
            fallback_response = self._get_fallback_response(manifest, max_similarity)
            
            return RoutingResult(
                decision=RoutingDecision.DONT_KNOW,
                confidence=0.2,
                similarity_score=max_similarity,
                reasoning=f"Low similarity ({max_similarity:.3f}), using fallback response",
                sources=[],
                fallback_used=True,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"❌ Error in routing: {e}")
            processing_time = time.time() - start_time
            
            return RoutingResult(
                decision=RoutingDecision.DONT_KNOW,
                confidence=0.0,
                similarity_score=0.0,
                reasoning=f"Routing error: {str(e)}",
                sources=[],
                fallback_used=True,
                processing_time=processing_time
            )
    
    async def _search_faq(self, question: str, site_id: str) -> Dict[str, Any]:
        """Caută în colecția FAQ"""
        try:
            faq_collection = f"mem_{site_id}_faq"
            
            # Verifică dacă colecția există
            try:
                collection_info = self.client.get_collection(faq_collection)
            except Exception:
                logger.warning(f"⚠️ FAQ collection {faq_collection} not found")
                return {
                    "similarity_score": 0.0,
                    "confidence": 0.0,
                    "sources": []
                }
            
            # Generează embedding pentru întrebare
            question_embedding = await self._generate_embedding(question)
            
            # Caută în FAQ
            search_results = self.client.search(
                collection_name=faq_collection,
                query_vector=question_embedding,
                limit=self.config.max_sources,
                score_threshold=self.config.pages_similarity_threshold
            )
            
            if not search_results:
                return {
                    "similarity_score": 0.0,
                    "confidence": 0.0,
                    "sources": []
                }
            
            # Calculează confidence bazat pe cel mai bun rezultat
            best_score = search_results[0].score
            confidence = min(0.95, best_score * 1.2)  # Boost pentru FAQ
            
            sources = []
            for result in search_results:
                sources.append({
                    "text": result.payload.get("text", ""),
                    "url": result.payload.get("url", ""),
                    "score": result.score,
                    "source_type": "faq"
                })
            
            return {
                "similarity_score": best_score,
                "confidence": confidence,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"❌ Error searching FAQ: {e}")
            return {
                "similarity_score": 0.0,
                "confidence": 0.0,
                "sources": []
            }
    
    async def _search_pages(self, question: str, site_id: str) -> Dict[str, Any]:
        """Caută în colecția pages"""
        try:
            pages_collection = f"mem_{site_id}_pages"
            
            # Verifică dacă colecția există
            try:
                collection_info = self.client.get_collection(pages_collection)
            except Exception:
                logger.warning(f"⚠️ Pages collection {pages_collection} not found")
                return {
                    "similarity_score": 0.0,
                    "confidence": 0.0,
                    "sources": []
                }
            
            # Generează embedding pentru întrebare
            question_embedding = await self._generate_embedding(question)
            
            # Caută în pages
            search_results = self.client.search(
                collection_name=pages_collection,
                query_vector=question_embedding,
                limit=self.config.max_sources,
                score_threshold=self.config.pages_similarity_threshold
            )
            
            if not search_results:
                return {
                    "similarity_score": 0.0,
                    "confidence": 0.0,
                    "sources": []
                }
            
            # Calculează confidence bazat pe cel mai bun rezultat
            best_score = search_results[0].score
            confidence = min(0.90, best_score * 1.1)  # Boost mai mic pentru pages
            
            sources = []
            for result in search_results:
                sources.append({
                    "text": result.payload.get("text", ""),
                    "url": result.payload.get("url", ""),
                    "score": result.score,
                    "source_type": "pages"
                })
            
            return {
                "similarity_score": best_score,
                "confidence": confidence,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"❌ Error searching pages: {e}")
            return {
                "similarity_score": 0.0,
                "confidence": 0.0,
                "sources": []
            }
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generează embedding pentru text"""
        try:
            # Folosește Ollama pentru embeddings (768 dimensiuni)
            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": text
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["embedding"]
            else:
                logger.warning(f"⚠️ Embedding API error: {response.status_code}")
                # Fallback la embedding zero
                return [0.0] * 768
                
        except Exception as e:
            logger.warning(f"⚠️ Error generating embedding: {e}")
            # Fallback la embedding zero
            return [0.0] * 768
    
    def _get_fallback_response(self, manifest: Dict[str, Any], similarity: float) -> str:
        """Generează răspunsul de fallback"""
        try:
            fallback_steps = manifest.get("fallback_steps", {})
            steps = fallback_steps.get("steps", [])
            
            if similarity < 0.3:
                return steps[0] if steps else "Nu pot răspunde la această întrebare cu încredere suficientă."
            elif similarity < 0.5:
                return steps[1] if len(steps) > 1 else steps[0]
            else:
                return steps[2] if len(steps) > 2 else steps[0]
                
        except Exception as e:
            logger.warning(f"⚠️ Error getting fallback response: {e}")
            return "Nu pot răspunde la această întrebare cu încredere suficientă."
    
    def _update_stats(self, decision_type: str, processing_time: float):
        """Actualizează statisticile de routing"""
        self.routing_stats["total_requests"] += 1
        self.routing_stats[f"{decision_type}"] += 1
        
        # Actualizează timpul mediu de procesare
        total_time = self.routing_stats["avg_processing_time"] * (self.routing_stats["total_requests"] - 1)
        self.routing_stats["avg_processing_time"] = (total_time + processing_time) / self.routing_stats["total_requests"]
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Obține statisticile de routing"""
        return {
            "stats": self.routing_stats.copy(),
            "config": {
                "faq_threshold": self.config.faq_similarity_threshold,
                "pages_threshold": self.config.pages_similarity_threshold,
                "escalation_threshold": self.config.escalation_threshold
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Actualizează configurația router-ului"""
        try:
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            logger.info(f"✅ Router config updated: {new_config}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating router config: {e}")
            return False

class MirrorRouterManager:
    """Manager pentru router-ele Mirror"""
    
    def __init__(self):
        self.routers: Dict[str, MirrorAgentRouter] = {}
    
    def get_router(self, site_id: str) -> MirrorAgentRouter:
        """Obține router-ul pentru un site"""
        if site_id not in self.routers:
            self.routers[site_id] = MirrorAgentRouter()
        
        return self.routers[site_id]
    
    async def route_question_for_site(self, question: str, site_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Routează o întrebare pentru un site specific"""
        try:
            router = self.get_router(site_id)
            result = await router.route_question(question, site_id, manifest)
            
            return {
                "ok": True,
                "question": question,
                "site_id": site_id,
                "decision": result.decision.value,
                "confidence": result.confidence,
                "similarity_score": result.similarity_score,
                "reasoning": result.reasoning,
                "sources": result.sources,
                "fallback_used": result.fallback_used,
                "processing_time": result.processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error routing question for site {site_id}: {e}")
            return {
                "ok": False,
                "error": str(e),
                "question": question,
                "site_id": site_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Obține statisticile pentru toate router-ele"""
        all_stats = {}
        for site_id, router in self.routers.items():
            all_stats[site_id] = router.get_routing_stats()
        
        return {
            "routers": all_stats,
            "total_sites": len(self.routers),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Instanță globală
router_manager = MirrorRouterManager()

# Funcții de utilitate pentru API
async def route_mirror_question(question: str, site_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Routează o întrebare pentru agentul Mirror"""
    return await router_manager.route_question_for_site(question, site_id, manifest)

if __name__ == "__main__":
    # Test
    async def test_mirror_router():
        router = MirrorAgentRouter()
        
        # Test cu manifest mock
        manifest = {
            "fallback_steps": {
                "steps": [
                    "Nu pot răspunde la această întrebare cu încredere suficientă.",
                    "Întrebarea depășește domeniul de expertiză al acestui agent.",
                    "Vă rog să reformulați întrebarea sau să contactați suportul tehnic."
                ]
            }
        }
        
        site_id = "matari_antifoc_ro_1761560625"
        question = "Ce servicii oferă Matari Antifoc?"
        
        result = await router.route_question(question, site_id, manifest)
        
        print("🧪 Mirror Router Test:")
        print("=" * 50)
        print(f"Question: {question}")
        print(f"Decision: {result.decision.value}")
        print(f"Confidence: {result.confidence:.3f}")
        print(f"Similarity Score: {result.similarity_score:.3f}")
        print(f"Reasoning: {result.reasoning}")
        print(f"Sources: {len(result.sources)}")
        print(f"Processing Time: {result.processing_time:.3f}s")
    
    asyncio.run(test_mirror_router())
