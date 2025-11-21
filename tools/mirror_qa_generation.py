"""
Mirror Agent Q/A Generation System
Issue 4: Generează automat un set inițial de Q/A pentru mirror
- 15-20 întrebări frecvente cu validare GPT-5
"""

import asyncio
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
class QAItem:
    """Item Q/A pentru Mirror Agent"""
    question: str
    answer: str
    confidence: float
    category: str
    keywords: List[str]
    created_at: datetime
    validated: bool = False
    validation_score: float = 0.0
    
    def to_dict(self):
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        return result

class MirrorQAGenerator:
    """Generator pentru Q/A automat Mirror Agents"""
    
    def __init__(self, api_base_url: str = "http://localhost:8083"):
        self.api_base_url = api_base_url
        self.db = MongoClient("mongodb://localhost:27017").mirror_qa_generation
        self.openai_client = openai.OpenAI()
        self.embedder = SentenceTransformer('BAAI/bge-large-en-v1.5')
        
        # Template-uri pentru întrebări frecvente
        self.question_templates = {
            "general": [
                "Ce servicii oferă {domain}?",
                "Cum pot contacta {domain}?",
                "Care sunt orele de program ale {domain}?",
                "Unde se află {domain}?",
                "Ce produse vinde {domain}?"
            ],
            "technical": [
                "Cum funcționează serviciile de la {domain}?",
                "Ce tehnologii folosește {domain}?",
                "Cum pot configura serviciile de la {domain}?",
                "Ce documentație există pentru {domain}?",
                "Cum pot rezolva problemele cu {domain}?"
            ],
            "pricing": [
                "Care sunt prețurile pentru serviciile de la {domain}?",
                "Există reduceri la {domain}?",
                "Cum pot plăti pentru serviciile de la {domain}?",
                "Ce opțiuni de plată acceptă {domain}?",
                "Există abonamente la {domain}?"
            ],
            "support": [
                "Cum pot obține suport de la {domain}?",
                "Ce garanții oferă {domain}?",
                "Cum pot raporta o problemă la {domain}?",
                "Există FAQ pentru {domain}?",
                "Cum pot anula serviciile de la {domain}?"
            ]
        }
    
    async def generate_qa_set(self, domain: str, site_id: str, 
                            num_questions: int = 20) -> Dict[str, Any]:
        """Generează un set de Q/A pentru un Mirror Agent"""
        logger.info(f"🤖 Generating Q/A set for {domain} ({site_id})")
        
        try:
            # Generează întrebări
            questions = await self._generate_questions(domain, num_questions)
            
            # Generează răspunsuri
            qa_items = await self._generate_answers(domain, site_id, questions)
            
            # Validează cu GPT-5
            validated_qa = await self._validate_with_gpt5(qa_items)
            
            # Salvează în baza de date
            await self._save_qa_set(site_id, domain, validated_qa)
            
            # Adaugă în colecția FAQ
            await self._add_to_faq_collection(site_id, validated_qa)
            
            logger.info(f"✅ Q/A set generated: {len(validated_qa)} items for {domain}")
            
            return {
                "ok": True,
                "site_id": site_id,
                "domain": domain,
                "qa_count": len(validated_qa),
                "qa_items": [item.to_dict() for item in validated_qa],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating Q/A set: {e}")
            return {
                "ok": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _generate_questions(self, domain: str, num_questions: int) -> List[str]:
        """Generează întrebări pentru domeniu"""
        questions = []
        
        # Adaugă întrebări din template-uri
        for category, templates in self.question_templates.items():
            for template in templates:
                question = template.format(domain=domain)
                questions.append(question)
        
        # Generează întrebări suplimentare cu GPT-5
        try:
            prompt = f"""
            Generează {num_questions - len(questions)} întrebări frecvente pentru site-ul {domain}.
            Întrebările trebuie să fie relevante pentru utilizatorii acestui site.
            Returnează doar întrebările, câte una pe linie.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            additional_questions = response.choices[0].message.content.strip().split('\n')
            questions.extend([q.strip() for q in additional_questions if q.strip()])
            
        except Exception as e:
            logger.warning(f"Failed to generate additional questions: {e}")
        
        # Limitează la numărul dorit
        return questions[:num_questions]
    
    async def _generate_answers(self, domain: str, site_id: str, 
                               questions: List[str]) -> List[QAItem]:
        """Generează răspunsuri pentru întrebări"""
        qa_items = []
        
        for question in questions:
            try:
                # Încearcă să obțină răspunsul din colecția pages
                answer = await self._get_answer_from_pages(site_id, question)
                
                if not answer:
                    # Generează răspuns generic
                    answer = await self._generate_generic_answer(domain, question)
                
                # Calculează confidence
                confidence = await self._calculate_confidence(question, answer)
                
                # Extrage keywords
                keywords = await self._extract_keywords(question)
                
                # Determină categoria
                category = self._categorize_question(question)
                
                qa_item = QAItem(
                    question=question,
                    answer=answer,
                    confidence=confidence,
                    category=category,
                    keywords=keywords,
                    created_at=datetime.now(timezone.utc)
                )
                
                qa_items.append(qa_item)
                
            except Exception as e:
                logger.warning(f"Failed to generate answer for '{question}': {e}")
                continue
        
        return qa_items
    
    async def _get_answer_from_pages(self, site_id: str, question: str) -> Optional[str]:
        """Încearcă să obțină răspunsul din colecția pages"""
        try:
            # Caută în colecția pages
            response = requests.post(
                f"{self.api_base_url}/mirror-router/route",
                json={
                    "site_id": site_id,
                    "question": question
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and data.get("action") == "answer":
                    return data.get("answer", "")
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get answer from pages: {e}")
            return None
    
    async def _generate_generic_answer(self, domain: str, question: str) -> str:
        """Generează răspuns generic pentru întrebare"""
        try:
            prompt = f"""
            Generează un răspuns scurt și util pentru întrebarea: "{question}"
            Context: site-ul {domain}
            Răspunsul trebuie să fie profesional și să ofere informații utile.
            Maxim 100 de cuvinte.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.warning(f"Failed to generate generic answer: {e}")
            return f"Pentru informații despre {question}, vă rugăm să contactați {domain}."
    
    async def _calculate_confidence(self, question: str, answer: str) -> float:
        """Calculează confidence pentru Q/A"""
        try:
            # Calculează similitudinea între întrebare și răspuns
            question_embedding = self.embedder.encode([question])
            answer_embedding = self.embedder.encode([answer])
            
            # Calculează cosine similarity
            import numpy as np
            similarity = np.dot(question_embedding[0], answer_embedding[0]) / (
                np.linalg.norm(question_embedding[0]) * np.linalg.norm(answer_embedding[0])
            )
            
            # Normalizează la 0-1
            confidence = max(0.0, min(1.0, (similarity + 1) / 2))
            
            return round(confidence, 3)
            
        except Exception as e:
            logger.warning(f"Failed to calculate confidence: {e}")
            return 0.5  # Confidence default
    
    async def _extract_keywords(self, question: str) -> List[str]:
        """Extrage keywords din întrebare"""
        try:
            # Extrage cuvintele cheie simple
            words = question.lower().split()
            
            # Filtrează cuvintele comune
            stop_words = {"ce", "cum", "care", "unde", "când", "de", "la", "cu", "pentru", "și", "sau"}
            keywords = [word for word in words if word not in stop_words and len(word) > 2]
            
            return keywords[:5]  # Maxim 5 keywords
            
        except Exception as e:
            logger.warning(f"Failed to extract keywords: {e}")
            return []
    
    def _categorize_question(self, question: str) -> str:
        """Categorizează întrebarea"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["preț", "cost", "plătește", "bani"]):
            return "pricing"
        elif any(word in question_lower for word in ["contact", "telefon", "email", "adresă"]):
            return "contact"
        elif any(word in question_lower for word in ["cum", "funcționează", "configurare"]):
            return "technical"
        elif any(word in question_lower for word in ["suport", "ajutor", "problemă"]):
            return "support"
        else:
            return "general"
    
    async def _validate_with_gpt5(self, qa_items: List[QAItem]) -> List[QAItem]:
        """Validează Q/A cu GPT-5"""
        validated_items = []
        
        for qa_item in qa_items:
            try:
                prompt = f"""
                Validează următoarea pereche Q/A pentru un site web:
                
                Întrebare: {qa_item.question}
                Răspuns: {qa_item.answer}
                
                Evaluează:
                1. Relevanța răspunsului pentru întrebare (0-1)
                2. Calitatea răspunsului (0-1)
                3. Utilitatea pentru utilizatori (0-1)
                
                Returnează doar scorul final (0-1) și "VALID" sau "INVALID".
                Format: SCOR: X.XX STATUS: VALID/INVALID
                """
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=50,
                    temperature=0.3
                )
                
                result = response.choices[0].message.content.strip()
                
                # Parsează rezultatul
                if "VALID" in result:
                    qa_item.validated = True
                    qa_item.validation_score = 0.8  # Scor default pentru valid
                else:
                    qa_item.validated = False
                    qa_item.validation_score = 0.3
                
                validated_items.append(qa_item)
                
            except Exception as e:
                logger.warning(f"Failed to validate Q/A: {e}")
                qa_item.validated = False
                qa_item.validation_score = 0.5
                validated_items.append(qa_item)
        
        return validated_items
    
    async def _save_qa_set(self, site_id: str, domain: str, qa_items: List[QAItem]):
        """Salvează setul Q/A în baza de date"""
        try:
            qa_data = {
                "site_id": site_id,
                "domain": domain,
                "qa_items": [item.to_dict() for item in qa_items],
                "total_count": len(qa_items),
                "validated_count": sum(1 for item in qa_items if item.validated),
                "created_at": datetime.now(timezone.utc)
            }
            
            self.db.qa_sets.insert_one(qa_data)
            logger.info(f"💾 Q/A set saved for {site_id}")
            
        except Exception as e:
            logger.error(f"Failed to save Q/A set: {e}")
    
    async def _add_to_faq_collection(self, site_id: str, qa_items: List[QAItem]):
        """Adaugă Q/A în colecția FAQ"""
        try:
            # Adaugă doar Q/A validate cu confidence mare
            high_confidence_items = [
                item for item in qa_items 
                if item.validated and item.confidence >= 0.7
            ]
            
            if not high_confidence_items:
                logger.warning(f"No high-confidence Q/A items to add to FAQ for {site_id}")
                return
            
            # Adaugă în colecția FAQ prin API
            for item in high_confidence_items:
                try:
                    response = requests.post(
                        f"{self.api_base_url}/mirror-collections/add-faq",
                        json={
                            "site_id": site_id,
                            "question": item.question,
                            "answer": item.answer,
                            "metadata": {
                                "category": item.category,
                                "keywords": item.keywords,
                                "confidence": item.confidence,
                                "validation_score": item.validation_score
                            }
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"✅ Added Q/A to FAQ: {item.question[:50]}...")
                    
                except Exception as e:
                    logger.warning(f"Failed to add Q/A to FAQ: {e}")
                    continue
            
            logger.info(f"📚 Added {len(high_confidence_items)} Q/A items to FAQ for {site_id}")
            
        except Exception as e:
            logger.error(f"Failed to add Q/A to FAQ collection: {e}")

# Funcții helper pentru API
async def generate_mirror_qa_set(domain: str, site_id: str, num_questions: int = 20) -> Dict[str, Any]:
    """Generează set Q/A pentru Mirror Agent"""
    generator = MirrorQAGenerator()
    return await generator.generate_qa_set(domain, site_id, num_questions)

def get_qa_generation_stats() -> Dict[str, Any]:
    """Returnează statistici pentru generarea Q/A"""
    db = MongoClient("mongodb://localhost:27017").mirror_qa_generation
    
    # Calculează statistici
    total_sets = db.qa_sets.count_documents({})
    total_qa_items = sum(doc.get("total_count", 0) for doc in db.qa_sets.find({}))
    total_validated = sum(doc.get("validated_count", 0) for doc in db.qa_sets.find({}))
    
    return {
        "total_qa_sets": total_sets,
        "total_qa_items": total_qa_items,
        "total_validated_items": total_validated,
        "validation_rate": total_validated / total_qa_items if total_qa_items > 0 else 0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
