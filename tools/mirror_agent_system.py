#!/usr/bin/env python3
"""
Mirror Agent System - Agent în oglindă pentru învățare Qwen
Creează un agent care face Q&A cu agentul nou creat pentru a îmbunătăți învățarea
"""

import asyncio
import requests
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
import random
import time

logger = logging.getLogger(__name__)

class MirrorAgentSystem:
    """Sistem de agent în oglindă pentru învățare Qwen"""
    
    def __init__(self):
        self.api_base_url = "http://localhost:8083"
        self.mongo_client = MongoClient('mongodb://localhost:9308')
        self.db = self.mongo_client['ai_agents_db']
        
        # Template-uri de întrebări pentru diferite tipuri de site-uri
        self.question_templates = {
            "general": [
                "Ce servicii oferă {company_name}?",
                "Cum pot contacta {company_name}?",
                "Care sunt prețurile pentru serviciile {company_name}?",
                "Ce experiență are {company_name} în domeniu?",
                "Care sunt avantajele de a lucra cu {company_name}?",
                "Ce certificări are {company_name}?",
                "În ce zone activează {company_name}?",
                "Cum se calculează costurile la {company_name}?",
                "Ce garanții oferă {company_name}?",
                "Care este procesul de lucru la {company_name}?"
            ],
            "technical": [
                "Ce tehnologii folosește {company_name}?",
                "Care sunt specificațiile tehnice ale produselor {company_name}?",
                "Ce standarde respectă {company_name}?",
                "Cum se instalează produsele {company_name}?",
                "Ce întreținere necesită produsele {company_name}?",
                "Care sunt parametrii de performanță ai produselor {company_name}?",
                "Ce compatibilitate au produsele {company_name}?",
                "Cum se testează calitatea la {company_name}?"
            ],
            "business": [
                "Care este istoria {company_name}?",
                "Cine sunt clienții principali ai {company_name}?",
                "Ce proiecte importante a realizat {company_name}?",
                "Care este viziunea {company_name}?",
                "Ce valori promovează {company_name}?",
                "Cum se dezvoltă {company_name}?",
                "Ce inovații aduce {company_name}?",
                "Care sunt obiectivele {company_name}?"
            ],
            "support": [
                "Ce suport tehnic oferă {company_name}?",
                "Cum pot obține ajutor de la {company_name}?",
                "Ce documentație oferă {company_name}?",
                "Există training-uri la {company_name}?",
                "Cum se rezolvă problemele tehnice la {company_name}?",
                "Ce resurse educaționale oferă {company_name}?",
                "Cum pot deveni partener cu {company_name}?",
                "Ce programe de loialitate are {company_name}?"
            ]
        }
    
    async def create_mirror_agent_session(self, target_agent_id: str) -> Dict[str, Any]:
        """Creează o sesiune de agent în oglindă pentru un agent țintă"""
        try:
            # Obține informațiile agentului țintă
            target_agent = self.db.site_agents.find_one({"_id": ObjectId(target_agent_id)})
            if not target_agent:
                raise Exception(f"Agent țintă nu a fost găsit: {target_agent_id}")
            
            # Creează sesiunea de mirror
            session = {
                "target_agent_id": target_agent_id,
                "target_agent_name": target_agent.get("name", "Unknown"),
                "target_domain": target_agent.get("domain", "unknown.com"),
                "created_at": datetime.now(timezone.utc),
                "status": "active",
                "questions_asked": 0,
                "conversations_generated": 0,
                "learning_data_points": 0
            }
            
            # Salvează sesiunea
            result = self.db.mirror_sessions.insert_one(session)
            session["_id"] = result.inserted_id
            
            logger.info(f"✅ Mirror session created: {session['_id']} for agent {target_agent_id}")
            return session
            
        except Exception as e:
            logger.error(f"❌ Error creating mirror session: {e}")
            raise
    
    async def generate_smart_questions(self, target_agent: Dict[str, Any], question_type: str = "general", count: int = 5) -> List[str]:
        """Generează întrebări inteligente pentru agentul țintă"""
        try:
            company_name = target_agent.get("name", target_agent.get("domain", "compania"))
            domain = target_agent.get("domain", "unknown.com")
            
            # Selectează template-urile bazate pe tipul de întrebare
            templates = self.question_templates.get(question_type, self.question_templates["general"])
            
            # Generează întrebări personalizate
            questions = []
            for template in random.sample(templates, min(count, len(templates))):
                question = template.format(company_name=company_name)
                questions.append(question)
            
            # Adaugă întrebări specifice domeniului
            domain_specific_questions = self._generate_domain_specific_questions(domain, company_name)
            questions.extend(domain_specific_questions[:2])  # Adaugă maxim 2 întrebări specifice
            
            return questions[:count]
            
        except Exception as e:
            logger.error(f"❌ Error generating questions: {e}")
            return []
    
    def _generate_domain_specific_questions(self, domain: str, company_name: str) -> List[str]:
        """Generează întrebări specifice domeniului"""
        domain_keywords = {
            "antifoc": [
                f"Ce tipuri de protecție la foc oferă {company_name}?",
                f"Cum se testează eficiența protecției la foc la {company_name}?",
                f"Ce standarde de siguranță respectă {company_name}?"
            ],
            "constructii": [
                f"Ce tipuri de construcții realizează {company_name}?",
                f"Cum se planifică proiectele la {company_name}?",
                f"Ce materiale folosește {company_name}?"
            ],
            "tehnologie": [
                f"Ce soluții tehnologice oferă {company_name}?",
                f"Cum se implementează tehnologiile la {company_name}?",
                f"Ce inovații tehnice aduce {company_name}?"
            ]
        }
        
        # Caută cuvinte cheie în domeniu
        for keyword, questions in domain_keywords.items():
            if keyword in domain.lower():
                return questions
        
        return []
    
    async def execute_mirror_qa_session(self, session_id: str, max_questions: int = 10) -> Dict[str, Any]:
        """Execută o sesiune de Q&A între agentul în oglindă și agentul țintă"""
        try:
            # Obține sesiunea
            session = self.db.mirror_sessions.find_one({"_id": ObjectId(session_id)})
            if not session:
                raise Exception(f"Mirror session not found: {session_id}")
            
            # Obține agentul țintă
            target_agent = self.db.site_agents.find_one({"_id": ObjectId(session["target_agent_id"])})
            if not target_agent:
                raise Exception(f"Target agent not found: {session['target_agent_id']}")
            
            logger.info(f"🔄 Starting mirror Q&A session for agent: {target_agent['name']}")
            
            # Generează întrebări
            questions = await self.generate_smart_questions(target_agent, "general", max_questions)
            
            conversations = []
            successful_qa = 0
            
            # Execută Q&A pentru fiecare întrebare
            for i, question in enumerate(questions):
                max_retries = 2
                for retry in range(max_retries):
                    try:
                        logger.info(f"❓ Question {i+1}/{len(questions)} (attempt {retry+1}): {question}")
                        
                        # Trimite întrebarea către agentul țintă
                        response = requests.post(
                            f"{self.api_base_url}/ask",
                            json={
                                "question": question,
                                "agent_id": str(session["target_agent_id"])
                            },
                            timeout=60  # Timeout mai mare pentru cereri complexe
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("ok"):
                                answer = data.get("response", "")
                                confidence = data.get("confidence", 0)
                                
                                # Salvează conversația pentru învățare
                                conversation = {
                                    "mirror_session_id": session_id,
                                    "target_agent_id": str(session["target_agent_id"]),
                                    "question": question,
                                    "answer": answer,
                                    "confidence": confidence,
                                    "timestamp": datetime.now(timezone.utc),
                                    "for_qwen_learning": True,
                                    "learning_potential": self._assess_learning_potential(question, answer),
                                    "domain": session["target_domain"]
                                }
                                
                                # Salvează în baza de date
                                self.db.qwen_learning_data.insert_one(conversation)
                                
                                conversations.append(conversation)
                                successful_qa += 1
                                
                                logger.info(f"✅ Q&A {i+1} completed - Confidence: {confidence:.2f}")
                                
                                # Pauză între întrebări pentru a nu suprasolicita sistemul
                                await asyncio.sleep(2)
                                break  # Ieși din retry loop dacă a reușit
                            else:
                                logger.warning(f"⚠️ Q&A {i+1} failed: {data.get('error', 'Unknown error')}")
                                if retry == max_retries - 1:  # Ultima încercare
                                    break
                        else:
                            logger.warning(f"⚠️ Q&A {i+1} HTTP error: {response.status_code}")
                            if retry == max_retries - 1:  # Ultima încercare
                                break
                            
                    except Exception as e:
                        logger.error(f"❌ Error in Q&A {i+1} (attempt {retry+1}): {e}")
                        if retry == max_retries - 1:  # Ultima încercare
                            break
                        await asyncio.sleep(1)  # Pauză între retry-uri
            
            # Actualizează sesiunea
            self.db.mirror_sessions.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$set": {
                        "status": "completed",
                        "questions_asked": len(questions),
                        "conversations_generated": successful_qa,
                        "learning_data_points": len(conversations),
                        "completed_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            result = {
                "session_id": session_id,
                "target_agent_name": target_agent["name"],
                "questions_asked": len(questions),
                "successful_qa": successful_qa,
                "conversations_saved": len(conversations),
                "learning_potential_avg": sum(c["learning_potential"] for c in conversations) / len(conversations) if conversations else 0,
                "conversations": conversations
            }
            
            logger.info(f"🎉 Mirror Q&A session completed: {successful_qa}/{len(questions)} successful")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error executing mirror Q&A session: {e}")
            raise
    
    def _assess_learning_potential(self, question: str, answer: str) -> float:
        """Evaluează potențialul de învățare al unei conversații"""
        try:
            # Factori pentru evaluarea potențialului de învățare
            factors = {
                "answer_length": min(1.0, len(answer) / 500),  # Răspunsuri mai lungi = mai multe informații
                "question_complexity": min(1.0, len(question.split()) / 10),  # Întrebări mai complexe
                "technical_terms": min(1.0, sum(1 for word in answer.split() if len(word) > 8) / 20),  # Termeni tehnici
                "specificity": min(1.0, len([w for w in answer.split() if w.isupper()]) / 10)  # Termeni specifici
            }
            
            # Calculul scorului final
            learning_potential = sum(factors.values()) / len(factors)
            return min(0.9, max(0.1, learning_potential))  # Limitează între 0.1 și 0.9
            
        except Exception:
            return 0.5  # Scor default
    
    async def get_mirror_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Obține statisticile unei sesiuni de mirror"""
        try:
            session = self.db.mirror_sessions.find_one({"_id": ObjectId(session_id)})
            if not session:
                raise Exception(f"Mirror session not found: {session_id}")
            
            # Obține conversațiile generate
            conversations = list(self.db.qwen_learning_data.find({
                "mirror_session_id": session_id
            }))
            
            stats = {
                "session_id": session_id,
                "target_agent_name": session["target_agent_name"],
                "target_domain": session["target_domain"],
                "status": session["status"],
                "created_at": session["created_at"],
                "questions_asked": session.get("questions_asked", 0),
                "conversations_generated": session.get("conversations_generated", 0),
                "learning_data_points": session.get("learning_data_points", 0),
                "avg_learning_potential": sum(c.get("learning_potential", 0) for c in conversations) / len(conversations) if conversations else 0,
                "conversations": conversations
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting mirror session stats: {e}")
            raise

# Funcții de utilitate pentru API
async def create_mirror_agent_for_site(agent_id: str, max_questions: int = 8) -> Dict[str, Any]:
    """Creează un agent în oglindă pentru un agent site și execută Q&A"""
    try:
        mirror_system = MirrorAgentSystem()
        
        # Creează sesiunea de mirror
        session = await mirror_system.create_mirror_agent_session(agent_id)
        
        # Execută Q&A session
        result = await mirror_system.execute_mirror_qa_session(str(session["_id"]), max_questions)
        
        return {
            "ok": True,
            "message": "Mirror agent Q&A session completed successfully",
            "session_id": str(session["_id"]),
            "target_agent_id": agent_id,
            "questions_asked": result["questions_asked"],
            "successful_qa": result["successful_qa"],
            "conversations_saved": result["conversations_saved"],
            "learning_potential_avg": result["learning_potential_avg"],
            "qwen_learning_enhanced": True
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating mirror agent: {e}")
        return {
            "ok": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Test
    async def test_mirror_system():
        mirror_system = MirrorAgentSystem()
        
        # Test cu agentul matari-antifoc
        agent_id = "68ff3bdb0104225c0769a64a"
        result = await create_mirror_agent_for_site(agent_id, max_questions=5)
        
        print("🧪 Mirror Agent System Test:")
        print("=" * 50)
        print(json.dumps(result, indent=2, default=str))
    
    asyncio.run(test_mirror_system())
