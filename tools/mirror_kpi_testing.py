"""
Mirror Agent KPI Testing System
Issue 6: KPI și test automat pentru fiecare Mirror nou
- Golden mini-set, groundedness, helpfulness, latență
"""

import asyncio
import time
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import requests
from pymongo import MongoClient
import openai
from sentence_transformers import SentenceTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class KPIMetrics:
    """Metrici KPI pentru Mirror Agent"""
    site_id: str
    test_session_id: str
    timestamp: datetime
    
    # Metrici de performanță
    latency_avg: float
    latency_p95: float
    latency_p99: float
    
    # Metrici de calitate
    groundedness_score: float
    helpfulness_score: float
    accuracy_score: float
    
    # Metrici de acoperire
    faq_coverage: float
    pages_coverage: float
    fallback_rate: float
    
    # Metrici de încredere
    confidence_avg: float
    confidence_std: float
    
    # Rezultate test
    total_questions: int
    successful_answers: int
    failed_answers: int
    
    def to_dict(self):
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

@dataclass
class TestQuestion:
    """Întrebare de test pentru Golden Mini-Set"""
    question_id: str
    question: str
    expected_answer_type: str  # "faq", "pages", "fallback"
    expected_keywords: List[str]
    difficulty: str  # "easy", "medium", "hard"
    domain_specific: bool

class GoldenMiniSet:
    """Set de întrebări de test standard pentru Mirror Agents"""
    
    def __init__(self):
        self.questions = self._create_standard_questions()
    
    def _create_standard_questions(self) -> List[TestQuestion]:
        """Creează setul standard de întrebări de test"""
        return [
            # Întrebări generale (easy)
            TestQuestion(
                question_id="general_001",
                question="Ce servicii oferă această companie?",
                expected_answer_type="pages",
                expected_keywords=["servicii", "oferă", "companie"],
                difficulty="easy",
                domain_specific=False
            ),
            TestQuestion(
                question_id="general_002", 
                question="Cum pot contacta suportul tehnic?",
                expected_answer_type="faq",
                expected_keywords=["contact", "suport", "tehnic"],
                difficulty="easy",
                domain_specific=False
            ),
            TestQuestion(
                question_id="general_003",
                question="Care sunt orele de program?",
                expected_answer_type="faq",
                expected_keywords=["ore", "program", "programul"],
                difficulty="easy",
                domain_specific=False
            ),
            
            # Întrebări specifice domeniului (medium)
            TestQuestion(
                question_id="domain_001",
                question="Ce tipuri de produse/servicii principale oferă?",
                expected_answer_type="pages",
                expected_keywords=["produse", "servicii", "principale"],
                difficulty="medium",
                domain_specific=True
            ),
            TestQuestion(
                question_id="domain_002",
                question="Care sunt prețurile pentru serviciile de bază?",
                expected_answer_type="faq",
                expected_keywords=["prețuri", "servicii", "bază"],
                difficulty="medium",
                domain_specific=True
            ),
            
            # Întrebări complexe (hard)
            TestQuestion(
                question_id="complex_001",
                question="Cum funcționează procesul de comandă și livrare?",
                expected_answer_type="pages",
                expected_keywords=["proces", "comandă", "livrare"],
                difficulty="hard",
                domain_specific=True
            ),
            TestQuestion(
                question_id="complex_002",
                question="Ce garanții oferă pentru produsele/serviciile vândute?",
                expected_answer_type="faq",
                expected_keywords=["garanții", "produse", "servicii"],
                difficulty="hard",
                domain_specific=True
            ),
            
            # Întrebări pentru fallback
            TestQuestion(
                question_id="fallback_001",
                question="Cum pot să devin partener de afaceri?",
                expected_answer_type="fallback",
                expected_keywords=["partener", "afaceri"],
                difficulty="medium",
                domain_specific=False
            ),
            TestQuestion(
                question_id="fallback_002",
                question="Care este politica de confidențialitate GDPR?",
                expected_answer_type="fallback",
                expected_keywords=["confidențialitate", "GDPR", "politică"],
                difficulty="hard",
                domain_specific=False
            ),
            
            # Întrebări pentru escaladare
            TestQuestion(
                question_id="escalate_001",
                question="Cum pot să investesc în companie?",
                expected_answer_type="escalate",
                expected_keywords=["investesc", "companie"],
                difficulty="hard",
                domain_specific=False
            )
        ]
    
    def get_questions_by_difficulty(self, difficulty: str) -> List[TestQuestion]:
        """Returnează întrebările filtrate după dificultate"""
        return [q for q in self.questions if q.difficulty == difficulty]
    
    def get_questions_by_type(self, answer_type: str) -> List[TestQuestion]:
        """Returnează întrebările filtrate după tipul de răspuns așteptat"""
        return [q for q in self.questions if q.expected_answer_type == answer_type]

class MirrorKPITester:
    """Sistem de testare KPI pentru Mirror Agents"""
    
    def __init__(self, api_base_url: str = "http://localhost:8083"):
        self.api_base_url = api_base_url
        self.golden_set = GoldenMiniSet()
        self.db = MongoClient("mongodb://localhost:27017").mirror_kpi
        self.openai_client = openai.OpenAI()
        
        # Model pentru evaluare groundedness
        self.evaluation_model = SentenceTransformer('BAAI/bge-large-en-v1.5')
    
    async def run_full_kpi_test(self, site_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Rulează testul complet KPI pentru un Mirror Agent"""
        test_session_id = f"kpi_test_{site_id}_{int(time.time())}"
        
        logger.info(f"🚀 Starting KPI test for {site_id} - Session: {test_session_id}")
        
        # 1. Rulează toate întrebările din Golden Mini-Set
        test_results = []
        latencies = []
        
        for question in self.golden_set.questions:
            result = await self._test_single_question(
                question, site_id, manifest, test_session_id
            )
            test_results.append(result)
            latencies.append(result.get('latency', 0))
            
            # Pauză între teste pentru a nu suprasolicita
            await asyncio.sleep(1)
        
        # 2. Calculează metrici KPI
        kpi_metrics = self._calculate_kpi_metrics(
            site_id, test_session_id, test_results, latencies
        )
        
        # 3. Salvează rezultatele
        await self._save_test_results(test_session_id, test_results, kpi_metrics)
        
        # 4. Generează raport
        report = self._generate_kpi_report(kpi_metrics, test_results)
        
        logger.info(f"✅ KPI test completed for {site_id}")
        
        return {
            "ok": True,
            "test_session_id": test_session_id,
            "site_id": site_id,
            "kpi_metrics": kpi_metrics.to_dict(),
            "test_results": test_results,
            "report": report,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _test_single_question(self, question: TestQuestion, site_id: str, 
                                  manifest: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Testează o singură întrebare"""
        start_time = time.time()
        
        try:
            # Trimite întrebarea către router
            response = requests.post(
                f"{self.api_base_url}/mirror-router/route",
                json={
                    "question": question.question,
                    "site_id": site_id,
                    "manifest": manifest
                },
                timeout=30
            )
            
            latency = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Evaluează răspunsul
                evaluation = await self._evaluate_response(
                    question, data, latency
                )
                
                return {
                    "question_id": question.question_id,
                    "question": question.question,
                    "expected_type": question.expected_answer_type,
                    "actual_decision": data.get("decision"),
                    "response": data.get("response", ""),
                    "confidence": data.get("confidence", 0),
                    "latency": latency,
                    "evaluation": evaluation,
                    "success": True
                }
            else:
                return {
                    "question_id": question.question_id,
                    "question": question.question,
                    "expected_type": question.expected_answer_type,
                    "actual_decision": "error",
                    "response": "",
                    "confidence": 0,
                    "latency": latency,
                    "evaluation": {"error": f"HTTP {response.status_code}"},
                    "success": False
                }
                
        except Exception as e:
            latency = time.time() - start_time
            return {
                "question_id": question.question_id,
                "question": question.question,
                "expected_type": question.expected_answer_type,
                "actual_decision": "error",
                "response": "",
                "confidence": 0,
                "latency": latency,
                "evaluation": {"error": str(e)},
                "success": False
            }
    
    async def _evaluate_response(self, question: TestQuestion, response_data: Dict[str, Any], 
                               latency: float) -> Dict[str, Any]:
        """Evaluează un răspuns folosind GPT-5"""
        try:
            # Pregătește prompt-ul pentru evaluare
            evaluation_prompt = f"""
Evaluează următorul răspuns al unui agent AI pentru întrebarea: "{question.question}"

Răspunsul agentului:
- Decizie: {response_data.get('decision', 'N/A')}
- Răspuns: {response_data.get('response', 'N/A')}
- Încredere: {response_data.get('confidence', 0)}
- Latență: {latency:.3f}s

Criterii de evaluare:
1. GROUNDEDNESS (0-1): Răspunsul este bazat pe surse concrete?
2. HELPFULNESS (0-1): Răspunsul este util pentru utilizator?
3. ACCURACY (0-1): Răspunsul este corect pentru întrebare?
4. DECISION_MATCH (0-1): Decizia corespunde cu tipul așteptat?

Tipul așteptat: {question.expected_answer_type}
Cuvinte cheie așteptate: {', '.join(question.expected_keywords)}

Returnează JSON cu scorurile:
{{
    "groundedness": 0.0-1.0,
    "helpfulness": 0.0-1.0,
    "accuracy": 0.0-1.0,
            "decision_match": 0.0-1.0,
    "reasoning": "explicație scurtă"
}}
"""
            
            # Apelează GPT-5 pentru evaluare
            gpt_response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Evaluează răspunsurile agentului AI conform criteriilor specificate. Returnează doar JSON valid."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            evaluation_text = gpt_response.choices[0].message.content.strip()
            
            # Parsează JSON-ul
            try:
                evaluation = json.loads(evaluation_text)
                return evaluation
            except json.JSONDecodeError:
                return {
                    "groundedness": 0.5,
                    "helpfulness": 0.5,
                    "accuracy": 0.5,
                    "decision_match": 0.5,
                    "reasoning": "Error parsing GPT evaluation",
                    "error": "JSON decode error"
                }
                
        except Exception as e:
            logger.error(f"Error evaluating response: {e}")
            return {
                "groundedness": 0.0,
                "helpfulness": 0.0,
                "accuracy": 0.0,
                "decision_match": 0.0,
                "reasoning": f"Evaluation error: {str(e)}",
                "error": str(e)
            }
    
    def _calculate_kpi_metrics(self, site_id: str, session_id: str, 
                              test_results: List[Dict[str, Any]], 
                              latencies: List[float]) -> KPIMetrics:
        """Calculează metricile KPI"""
        
        # Calculează latența
        latencies_sorted = sorted(latencies)
        latency_avg = sum(latencies) / len(latencies) if latencies else 0
        latency_p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)] if latencies_sorted else 0
        latency_p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)] if latencies_sorted else 0
        
        # Calculează scorurile de calitate
        groundedness_scores = []
        helpfulness_scores = []
        accuracy_scores = []
        decision_matches = []
        
        successful_results = [r for r in test_results if r.get('success', False)]
        
        for result in successful_results:
            evaluation = result.get('evaluation', {})
            if 'groundedness' in evaluation:
                groundedness_scores.append(evaluation['groundedness'])
            if 'helpfulness' in evaluation:
                helpfulness_scores.append(evaluation['helpfulness'])
            if 'accuracy' in evaluation:
                accuracy_scores.append(evaluation['accuracy'])
            if 'decision_match' in evaluation:
                decision_matches.append(evaluation['decision_match'])
        
        groundedness_score = sum(groundedness_scores) / len(groundedness_scores) if groundedness_scores else 0
        helpfulness_score = sum(helpfulness_scores) / len(helpfulness_scores) if helpfulness_scores else 0
        accuracy_score = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
        
        # Calculează acoperirea
        faq_count = len([r for r in successful_results if r.get('actual_decision') == 'faq'])
        pages_count = len([r for r in successful_results if r.get('actual_decision') == 'pages'])
        fallback_count = len([r for r in successful_results if r.get('actual_decision') == 'fallback'])
        
        total_successful = len(successful_results)
        faq_coverage = faq_count / total_successful if total_successful > 0 else 0
        pages_coverage = pages_count / total_successful if total_successful > 0 else 0
        fallback_rate = fallback_count / total_successful if total_successful > 0 else 0
        
        # Calculează încrederea
        confidences = [r.get('confidence', 0) for r in successful_results]
        confidence_avg = sum(confidences) / len(confidences) if confidences else 0
        confidence_std = (sum((c - confidence_avg) ** 2 for c in confidences) / len(confidences)) ** 0.5 if confidences else 0
        
        return KPIMetrics(
            site_id=site_id,
            test_session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            latency_avg=latency_avg,
            latency_p95=latency_p95,
            latency_p99=latency_p99,
            groundedness_score=groundedness_score,
            helpfulness_score=helpfulness_score,
            accuracy_score=accuracy_score,
            faq_coverage=faq_coverage,
            pages_coverage=pages_coverage,
            fallback_rate=fallback_rate,
            confidence_avg=confidence_avg,
            confidence_std=confidence_std,
            total_questions=len(test_results),
            successful_answers=len(successful_results),
            failed_answers=len(test_results) - len(successful_results)
        )
    
    async def _save_test_results(self, session_id: str, test_results: List[Dict[str, Any]], 
                               kpi_metrics: KPIMetrics):
        """Salvează rezultatele testului în MongoDB"""
        try:
            # Salvează rezultatele detaliate
            self.db.kpi_test_results.insert_one({
                "session_id": session_id,
                "site_id": kpi_metrics.site_id,
                "test_results": test_results,
                "kpi_metrics": kpi_metrics.to_dict(),
                "created_at": datetime.now(timezone.utc)
            })
            
            # Salvează metricile KPI
            self.db.kpi_metrics.insert_one(kpi_metrics.to_dict())
            
            logger.info(f"✅ KPI test results saved for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error saving KPI test results: {e}")
    
    def _generate_kpi_report(self, kpi_metrics: KPIMetrics, 
                           test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generează raportul KPI"""
        
        # Calculează scorul general
        overall_score = (
            kpi_metrics.groundedness_score * 0.3 +
            kpi_metrics.helpfulness_score * 0.3 +
            kpi_metrics.accuracy_score * 0.2 +
            (1 - kpi_metrics.fallback_rate) * 0.2
        )
        
        # Determină statusul
        if overall_score >= 0.8:
            status = "EXCELLENT"
        elif overall_score >= 0.6:
            status = "GOOD"
        elif overall_score >= 0.4:
            status = "FAIR"
        else:
            status = "POOR"
        
        # Analizează problemele
        issues = []
        if kpi_metrics.latency_avg > 3.0:
            issues.append("High latency")
        if kpi_metrics.groundedness_score < 0.6:
            issues.append("Low groundedness")
        if kpi_metrics.helpfulness_score < 0.6:
            issues.append("Low helpfulness")
        if kpi_metrics.fallback_rate > 0.3:
            issues.append("High fallback rate")
        
        return {
            "overall_score": overall_score,
            "status": status,
            "issues": issues,
            "recommendations": self._generate_recommendations(kpi_metrics, issues),
            "summary": {
                "total_questions": kpi_metrics.total_questions,
                "success_rate": kpi_metrics.successful_answers / kpi_metrics.total_questions if kpi_metrics.total_questions > 0 else 0,
                "avg_latency": kpi_metrics.latency_avg,
                "avg_confidence": kpi_metrics.confidence_avg
            }
        }
    
    def _generate_recommendations(self, kpi_metrics: KPIMetrics, issues: List[str]) -> List[str]:
        """Generează recomandări bazate pe problemele identificate"""
        recommendations = []
        
        if "High latency" in issues:
            recommendations.append("Optimizează căutarea în Qdrant și reduce timeout-urile")
        
        if "Low groundedness" in issues:
            recommendations.append("Îmbunătățește calitatea surselor și verifică citările")
        
        if "Low helpfulness" in issues:
            recommendations.append("Revizuiește răspunsurile pentru a fi mai utile și specifice")
        
        if "High fallback rate" in issues:
            recommendations.append("Extinde baza de cunoștințe și îmbunătățește matching-ul")
        
        if not issues:
            recommendations.append("Mirror Agent funcționează excelent! Continuă monitorizarea.")
        
        return recommendations

# Funcții helper pentru API
async def run_kpi_test_for_site(site_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Rulează testul KPI pentru un site"""
    tester = MirrorKPITester()
    return await tester.run_full_kpi_test(site_id, manifest)

def get_kpi_history(site_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Returnează istoricul KPI pentru un site"""
    db = MongoClient("mongodb://localhost:27017").mirror_kpi
    results = list(db.kpi_metrics.find(
        {"site_id": site_id}
    ).sort("timestamp", -1).limit(limit))
    
    # Convertim ObjectId la string
    for result in results:
        result['_id'] = str(result['_id'])
        if 'timestamp' in result and isinstance(result['timestamp'], datetime):
            result['timestamp'] = result['timestamp'].isoformat()
    
    return results

def get_kpi_stats() -> Dict[str, Any]:
    """Returnează statistici globale KPI"""
    db = MongoClient("mongodb://localhost:27017").mirror_kpi
    
    # Calculează statistici globale
    total_tests = db.kpi_metrics.count_documents({})
    
    if total_tests == 0:
        return {"total_tests": 0, "avg_scores": {}}
    
    # Calculează scorurile medii
    pipeline = [
        {
            "$group": {
                "_id": None,
                "avg_groundedness": {"$avg": "$groundedness_score"},
                "avg_helpfulness": {"$avg": "$helpfulness_score"},
                "avg_accuracy": {"$avg": "$accuracy_score"},
                "avg_latency": {"$avg": "$latency_avg"},
                "avg_confidence": {"$avg": "$confidence_avg"}
            }
        }
    ]
    
    stats = list(db.kpi_metrics.aggregate(pipeline))
    
    if stats:
        return {
            "total_tests": total_tests,
            "avg_scores": stats[0]
        }
    else:
        return {"total_tests": total_tests, "avg_scores": {}}
