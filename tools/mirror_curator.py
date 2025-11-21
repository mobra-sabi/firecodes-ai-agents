"""
Mirror Agent Curator System
Issue 7: Activează Curator pentru actualizarea automată a FAQ-ului
- Monitorizare răspunsuri ≥0.9, promovare în faq
"""

import asyncio
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
from pymongo import MongoClient
import openai
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from sentence_transformers import SentenceTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CuratorCandidate:
    """Candidat pentru promovare în FAQ"""
    question_id: str
    question: str
    answer: str
    confidence: float
    source_url: str
    site_id: str
    timestamp: datetime
    evaluation_score: float
    groundedness_score: float
    helpfulness_score: float
    frequency_count: int
    user_feedback_score: float
    
    def to_dict(self):
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

@dataclass
class CuratorStats:
    """Statistici pentru Curator"""
    site_id: str
    total_monitored: int
    candidates_generated: int
    faq_promotions: int
    rejection_rate: float
    avg_evaluation_score: float
    last_update: datetime
    
    def to_dict(self):
        result = asdict(self)
        result['last_update'] = self.last_update.isoformat()
        return result

class MirrorCurator:
    """Sistem Curator pentru actualizarea automată a FAQ-ului"""
    
    def __init__(self, api_base_url: str = "http://localhost:8083"):
        self.api_base_url = api_base_url
        self.db = MongoClient("mongodb://localhost:27017").mirror_curator
        self.qdrant_client = QdrantClient("localhost", port=6333)
        self.openai_client = openai.OpenAI()
        
        # Model pentru embeddings
        self.embedding_model = SentenceTransformer('BAAI/bge-large-en-v1.5')
        
        # Configurare Curator
        self.confidence_threshold = 0.9
        self.evaluation_threshold = 0.8
        self.frequency_threshold = 3  # Minim 3 apariții pentru promovare
        self.max_faq_size = 100  # Maxim 100 întrebări în FAQ
        
        # Cache pentru performanță
        self.candidate_cache = {}
        self.stats_cache = {}
    
    async def monitor_responses(self, site_id: str, hours_back: int = 24) -> List[CuratorCandidate]:
        """Monitorizează răspunsurile pentru un site în ultimele ore"""
        logger.info(f"🔍 Monitoring responses for {site_id} (last {hours_back}h)")
        
        # Calculează timestamp-ul de început
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        # Caută în conversațiile salvate pentru învățare Qwen
        conversations = list(self.db.qwen_learning_data.find({
            "target_agent_id": {"$regex": f".*{site_id}.*"},
            "timestamp": {"$gte": start_time},
            "confidence": {"$gte": self.confidence_threshold}
        }).sort("timestamp", -1))
        
        candidates = []
        
        for conv in conversations:
            # Verifică dacă este deja în FAQ
            if await self._is_already_in_faq(site_id, conv["question"]):
                continue
            
            # Creează candidat
            candidate = CuratorCandidate(
                question_id=f"candidate_{int(time.time())}_{len(candidates)}",
                question=conv["question"],
                answer=conv["answer"],
                confidence=conv["confidence"],
                source_url=conv.get("source", ""),
                site_id=site_id,
                timestamp=conv["timestamp"],
                evaluation_score=0.0,
                groundedness_score=0.0,
                helpfulness_score=0.0,
                frequency_count=1,
                user_feedback_score=0.0
            )
            
            # Evaluează candidatul
            evaluation = await self._evaluate_candidate(candidate)
            candidate.evaluation_score = evaluation["overall_score"]
            candidate.groundedness_score = evaluation["groundedness"]
            candidate.helpfulness_score = evaluation["helpfulness"]
            
            # Verifică dacă îndeplinește criteriile
            if candidate.evaluation_score >= self.evaluation_threshold:
                candidates.append(candidate)
                logger.info(f"✅ Candidate found: {candidate.question[:50]}... (score: {candidate.evaluation_score:.3f})")
        
        # Verifică frecvența întrebărilor similare
        candidates = await self._check_frequency(candidates)
        
        logger.info(f"📊 Found {len(candidates)} candidates for {site_id}")
        return candidates
    
    async def _evaluate_candidate(self, candidate: CuratorCandidate) -> Dict[str, float]:
        """Evaluează un candidat folosind GPT-5"""
        try:
            evaluation_prompt = f"""
Evaluează următoarea întrebare și răspuns pentru a fi adăugată în FAQ:

ÎNTREBAREA: {candidate.question}
RĂSPUNSUL: {candidate.answer}
ÎNCREDERE: {candidate.confidence}
SURSA: {candidate.source_url}

Criterii de evaluare pentru FAQ:
1. GROUNDEDNESS (0-1): Răspunsul este bazat pe informații concrete și verificabile?
2. HELPFULNESS (0-1): Răspunsul este util și complet pentru utilizatori?
3. CLARITY (0-1): Răspunsul este clar și ușor de înțeles?
4. COMPLETENESS (0-1): Răspunsul acoperă complet întrebarea?
5. RELEVANCE (0-1): Întrebarea este relevantă pentru domeniul site-ului?

Returnează JSON cu scorurile:
{{
    "groundedness": 0.0-1.0,
    "helpfulness": 0.0-1.0,
    "clarity": 0.0-1.0,
    "completeness": 0.0-1.0,
    "relevance": 0.0-1.0,
    "overall_score": 0.0-1.0,
    "reasoning": "explicație scurtă"
}}
"""
            
            gpt_response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Evaluează întrebările și răspunsurile pentru FAQ conform criteriilor specificate. Returnează doar JSON valid."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            evaluation_text = gpt_response.choices[0].message.content.strip()
            
            try:
                evaluation = json.loads(evaluation_text)
                return evaluation
            except json.JSONDecodeError:
                return {
                    "groundedness": 0.5,
                    "helpfulness": 0.5,
                    "clarity": 0.5,
                    "completeness": 0.5,
                    "relevance": 0.5,
                    "overall_score": 0.5,
                    "reasoning": "Error parsing GPT evaluation"
                }
                
        except Exception as e:
            logger.error(f"Error evaluating candidate: {e}")
            return {
                "groundedness": 0.0,
                "helpfulness": 0.0,
                "clarity": 0.0,
                "completeness": 0.0,
                "relevance": 0.0,
                "overall_score": 0.0,
                "reasoning": f"Evaluation error: {str(e)}"
            }
    
    async def _check_frequency(self, candidates: List[CuratorCandidate]) -> List[CuratorCandidate]:
        """Verifică frecvența întrebărilor similare"""
        for candidate in candidates:
            # Caută întrebări similare în istoric
            similar_questions = list(self.db.qwen_learning_data.find({
                "target_agent_id": {"$regex": f".*{candidate.site_id}.*"},
                "question": {"$regex": f".*{candidate.question[:20]}.*", "$options": "i"}
            }))
            
            candidate.frequency_count = len(similar_questions)
            
            # Verifică dacă îndeplinește threshold-ul de frecvență
            if candidate.frequency_count < self.frequency_threshold:
                logger.info(f"⚠️ Candidate rejected - low frequency: {candidate.frequency_count}")
        
        # Returnează doar candidatii cu frecvența suficientă
        return [c for c in candidates if c.frequency_count >= self.frequency_threshold]
    
    async def _is_already_in_faq(self, site_id: str, question: str) -> bool:
        """Verifică dacă întrebarea este deja în FAQ"""
        try:
            faq_collection_name = f"mem_{site_id}_faq"
            
            # Generează embedding pentru întrebare
            question_embedding = self.embedding_model.encode(question).tolist()
            
            # Caută în FAQ
            search_results = self.qdrant_client.search(
                collection_name=faq_collection_name,
                query_vector=question_embedding,
                limit=1,
                score_threshold=0.9
            )
            
            return len(search_results) > 0
            
        except Exception as e:
            logger.error(f"Error checking FAQ: {e}")
            return False
    
    async def promote_to_faq(self, candidate: CuratorCandidate) -> bool:
        """Promovează un candidat în FAQ"""
        try:
            logger.info(f"🚀 Promoting to FAQ: {candidate.question[:50]}...")
            
            faq_collection_name = f"mem_{candidate.site_id}_faq"
            
            # Generează embedding pentru întrebare
            question_embedding = self.embedding_model.encode(candidate.question).tolist()
            
            # Creează point pentru Qdrant
            point = PointStruct(
                id=f"faq_{int(time.time())}_{hash(candidate.question) % 1000000}",
                vector=question_embedding,
                payload={
                    "question": candidate.question,
                    "answer": candidate.answer,
                    "question_id": candidate.question_id,
                    "source_url": candidate.source_url,
                    "confidence": candidate.confidence,
                    "evaluation_score": candidate.evaluation_score,
                    "groundedness_score": candidate.groundedness_score,
                    "helpfulness_score": candidate.helpfulness_score,
                    "frequency_count": candidate.frequency_count,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "promoted_by": "curator_auto",
                    "tags": ["auto_generated", "high_confidence", "frequent_question"]
                }
            )
            
            # Adaugă în Qdrant
            self.qdrant_client.upsert(
                collection_name=faq_collection_name,
                points=[point]
            )
            
            # Salvează în MongoDB pentru tracking
            self.db.faq_promotions.insert_one({
                "question_id": candidate.question_id,
                "site_id": candidate.site_id,
                "question": candidate.question,
                "answer": candidate.answer,
                "promoted_at": datetime.now(timezone.utc),
                "evaluation_score": candidate.evaluation_score,
                "frequency_count": candidate.frequency_count,
                "source": "curator_auto"
            })
            
            logger.info(f"✅ Successfully promoted to FAQ: {candidate.question_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error promoting to FAQ: {e}")
            return False
    
    async def run_curator_cycle(self, site_id: str) -> Dict[str, Any]:
        """Rulează un ciclu complet de curator"""
        logger.info(f"🔄 Starting curator cycle for {site_id}")
        
        start_time = time.time()
        
        # 1. Monitorizează răspunsurile
        candidates = await self.monitor_responses(site_id)
        
        # 2. Promovează candidatii eligibili
        promotions = []
        rejections = []
        
        for candidate in candidates:
            # Verifică dacă FAQ-ul nu este plin
            if await self._get_faq_size(site_id) >= self.max_faq_size:
                logger.warning(f"⚠️ FAQ is full for {site_id}, skipping promotion")
                break
            
            # Încearcă promovarea
            success = await self.promote_to_faq(candidate)
            
            if success:
                promotions.append(candidate)
            else:
                rejections.append(candidate)
        
        # 3. Actualizează statisticile
        await self._update_curator_stats(site_id, len(candidates), len(promotions))
        
        cycle_time = time.time() - start_time
        
        logger.info(f"✅ Curator cycle completed for {site_id}: {len(promotions)} promotions, {len(rejections)} rejections")
        
        return {
            "ok": True,
            "site_id": site_id,
            "cycle_time": cycle_time,
            "candidates_found": len(candidates),
            "promotions": len(promotions),
            "rejections": len(rejections),
            "promoted_questions": [c.question for c in promotions],
            "rejected_questions": [c.question for c in rejections],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _get_faq_size(self, site_id: str) -> int:
        """Returnează dimensiunea FAQ-ului pentru un site"""
        try:
            faq_collection_name = f"mem_{site_id}_faq"
            collection_info = self.qdrant_client.get_collection(faq_collection_name)
            return collection_info.vectors_count
        except Exception as e:
            logger.error(f"Error getting FAQ size: {e}")
            return 0
    
    async def _update_curator_stats(self, site_id: str, total_monitored: int, promotions: int):
        """Actualizează statisticile curator"""
        try:
            stats = CuratorStats(
                site_id=site_id,
                total_monitored=total_monitored,
                candidates_generated=total_monitored,
                faq_promotions=promotions,
                rejection_rate=(total_monitored - promotions) / total_monitored if total_monitored > 0 else 0,
                avg_evaluation_score=0.0,  # Calculat separat
                last_update=datetime.now(timezone.utc)
            )
            
            # Salvează statisticile
            self.db.curator_stats.update_one(
                {"site_id": site_id},
                {"$set": stats.to_dict()},
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error updating curator stats: {e}")
    
    async def get_curator_dashboard(self, site_id: str) -> Dict[str, Any]:
        """Returnează dashboard-ul curator pentru un site"""
        try:
            # Obține statisticile
            stats = self.db.curator_stats.find_one({"site_id": site_id})
            
            # Obține promovările recente
            recent_promotions = list(self.db.faq_promotions.find(
                {"site_id": site_id}
            ).sort("promoted_at", -1).limit(10))
            
            # Obține dimensiunea FAQ-ului
            faq_size = await self._get_faq_size(site_id)
            
            # Obține candidatii în așteptare
            pending_candidates = list(self.db.qwen_learning_data.find({
                "target_agent_id": {"$regex": f".*{site_id}.*"},
                "confidence": {"$gte": self.confidence_threshold},
                "timestamp": {"$gte": datetime.now(timezone.utc) - timedelta(hours=24)}
            }).sort("timestamp", -1).limit(20))
            
            return {
                "ok": True,
                "site_id": site_id,
                "stats": stats or {},
                "faq_size": faq_size,
                "max_faq_size": self.max_faq_size,
                "recent_promotions": recent_promotions,
                "pending_candidates": len(pending_candidates),
                "confidence_threshold": self.confidence_threshold,
                "evaluation_threshold": self.evaluation_threshold,
                "frequency_threshold": self.frequency_threshold,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting curator dashboard: {e}")
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

# Funcții helper pentru API
async def run_curator_cycle_for_site(site_id: str) -> Dict[str, Any]:
    """Rulează ciclul curator pentru un site"""
    curator = MirrorCurator()
    return await curator.run_curator_cycle(site_id)

async def get_curator_dashboard_for_site(site_id: str) -> Dict[str, Any]:
    """Returnează dashboard-ul curator pentru un site"""
    curator = MirrorCurator()
    return await curator.get_curator_dashboard(site_id)

def get_curator_stats() -> Dict[str, Any]:
    """Returnează statistici globale curator"""
    db = MongoClient("mongodb://localhost:27017").mirror_curator
    
    # Calculează statistici globale
    total_sites = len(db.curator_stats.distinct("site_id"))
    total_promotions = db.faq_promotions.count_documents({})
    
    # Calculează promovările recente (ultimele 24h)
    recent_promotions = db.faq_promotions.count_documents({
        "promoted_at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=24)}
    })
    
    return {
        "total_sites": total_sites,
        "total_promotions": total_promotions,
        "recent_promotions_24h": recent_promotions,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
