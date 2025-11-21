#!/usr/bin/env python3
"""
🧠 Continuous Learner - Procesează toate datele pentru învățare continuă
Salvează diagnosticile, rutele de execuție, rezultatele și interacțiunile
către LLM-ul local (Qwen) pentru fine-tuning
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from bson import ObjectId
import logging
import requests

logger = logging.getLogger(__name__)

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "adbrain_ai")

# Qwen Local
QWEN_VLLM_URL = os.getenv("QWEN_VLLM_URL", "http://localhost:9400")
QWEN_FALLBACK_URL = os.getenv("QWEN_FALLBACK_URL", "http://localhost:9201")

def get_mongo_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]


class ContinuousLearner:
    """
    Procesează toate datele pentru învățare continuă:
    - Diagnosticile
    - Rutele de execuție
    - Rezultatele
    - Interacțiunile utilizatorului
    """
    
    def __init__(self):
        self.db = get_mongo_db()
        self.collection = self.db.interactions
        self.logger = logging.getLogger(f"{__name__}.ContinuousLearner")
        
    def process_for_learning(
        self,
        limit: int = 100,
        include_diagnostics: bool = True,
        include_routes: bool = True,
        include_interactions: bool = True
    ) -> Dict[str, Any]:
        """
        Procesează toate datele pentru învățare
        
        Args:
            limit: Număr maxim de documente de procesat
            include_diagnostics: Include diagnosticile
            include_routes: Include rutele de execuție
            include_interactions: Include interacțiunile
        
        Returns:
            Dict cu statistici procesare
        """
        self.logger.info("🧠 Processing data for continuous learning...")
        
        query = {"processed": False}
        
        # Filtrare după tip
        type_filter = []
        if include_diagnostics:
            type_filter.append("diagnostic")
        if include_routes:
            type_filter.append("execution_route")
        if include_interactions:
            type_filter.append("interaction")
        
        if type_filter:
            query["type"] = {"$in": type_filter}
        
        # Obține documente neprocesate
        documents = list(
            self.collection.find(query)
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        if not documents:
            return {
                "processed": 0,
                "diagnostics": 0,
                "routes": 0,
                "interactions": 0,
                "message": "No new data to process"
            }
        
        # Procesează fiecare document
        processed_ids = []
        stats = {
            "diagnostics": 0,
            "routes": 0,
            "interactions": 0
        }
        
        for doc in documents:
            doc_type = doc.get("type", "interaction")
            
            if doc_type == "diagnostic":
                self._process_diagnostic(doc)
                stats["diagnostics"] += 1
            elif doc_type == "execution_route":
                self._process_execution_route(doc)
                stats["routes"] += 1
            elif doc_type == "interaction":
                self._process_interaction(doc)
                stats["interactions"] += 1
            
            processed_ids.append(doc["_id"])
        
        # Marchează ca procesate
        if processed_ids:
            self.collection.update_many(
                {"_id": {"$in": processed_ids}},
                {"$set": {"processed": True, "processed_at": datetime.now()}}
            )
        
        total_processed = len(processed_ids)
        self.logger.info(f"✅ Processed {total_processed} documents for learning")
        
        return {
            "processed": total_processed,
            **stats,
            "message": f"Processed {total_processed} documents"
        }
    
    def _process_diagnostic(self, doc: Dict[str, Any]):
        """Procesează un diagnostic pentru învățare"""
        diagnostic_type = doc.get("diagnostic_type", "unknown")
        data = doc.get("data", {})
        
        # Creează prompt de învățare din diagnostic
        learning_prompt = f"""Diagnostic: {diagnostic_type}
Data: {json.dumps(data, indent=2)}

Analizează acest diagnostic și învață din el pentru a îmbunătăți procesele viitoare."""
        
        # Salvează ca interacțiune pentru fine-tuning
        self._save_learning_interaction(
            prompt=learning_prompt,
            response="Diagnostic processed for learning",
            context="diagnostic_learning",
            source_doc_id=str(doc["_id"])
        )
    
    def _process_execution_route(self, doc: Dict[str, Any]):
        """Procesează o rută de execuție pentru învățare"""
        route_name = doc.get("route_name", "unknown")
        steps = doc.get("steps", [])
        result = doc.get("result", {})
        
        # Creează prompt de învățare din rută
        steps_text = "\n".join([f"Step {i+1}: {json.dumps(s, indent=2)}" for i, s in enumerate(steps)])
        result_text = json.dumps(result, indent=2)
        
        learning_prompt = f"""Execution Route: {route_name}

Steps executed:
{steps_text}

Result:
{result_text}

Analizează această rută de execuție și învață din ea pentru a optimiza procesele viitoare."""
        
        # Salvează ca interacțiune pentru fine-tuning
        self._save_learning_interaction(
            prompt=learning_prompt,
            response="Execution route processed for learning",
            context="route_learning",
            source_doc_id=str(doc["_id"])
        )
    
    def _process_interaction(self, doc: Dict[str, Any]):
        """Procesează o interacțiune pentru învățare"""
        # Interacțiunile sunt deja în format corect pentru fine-tuning
        # Doar verificăm dacă au context suplimentar
        execution_route = doc.get("execution_route")
        diagnostic_context = doc.get("diagnostic_context")
        
        if execution_route or diagnostic_context:
            # Adaugă context la prompt pentru învățare mai bună
            prompt = doc.get("prompt", "")
            if execution_route:
                prompt = f"[Execution Route: {execution_route}]\n{prompt}"
            if diagnostic_context:
                prompt = f"[Diagnostic Context: {json.dumps(diagnostic_context)}]\n{prompt}"
            
            # Update document cu prompt îmbunătățit
            self.collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"enhanced_prompt": prompt, "has_context": True}}
            )
    
    def _save_learning_interaction(
        self,
        prompt: str,
        response: str,
        context: str,
        source_doc_id: str
    ):
        """Salvează o interacțiune de învățare"""
        learning_doc = {
            "type": "interaction",
            "prompt": prompt,
            "response": response,
            "provider": "qwen-local-learning",
            "topic": "continuous_learning",
            "context": context,
            "source_doc_id": source_doc_id,
            "timestamp": datetime.now(),
            "processed": False,
            "created_at": datetime.now().isoformat()
        }
        
        self.collection.insert_one(learning_doc)
    
    def send_to_qwen_local(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        use_learning_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Trimite prompt către Qwen local pentru învățare
        
        Args:
            prompt: Prompt-ul de trimis
            context: Context suplimentar (diagnostic, route, etc.)
            use_learning_mode: Dacă să salveze interacțiunea pentru învățare
        
        Returns:
            Răspuns de la Qwen
        """
        # Construiește mesajul cu context
        system_prompt = """Ești un asistent AI care învață continuu din diagnosticile sistemului, 
rutele de execuție și interacțiunile utilizatorilor. Folosește aceste informații pentru a îmbunătăți 
răspunsurile tale și a oferi soluții mai bune."""
        
        if context:
            context_text = json.dumps(context, indent=2)
            full_prompt = f"""Context:
{context_text}

User Request:
{prompt}"""
        else:
            full_prompt = prompt
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ]
        
        # Încearcă Qwen pe port 9400 (72B), apoi 9201 (7B)
        for port in [9400, 9201]:
            try:
                response = requests.post(
                    f"http://localhost:{port}/v1/chat/completions",
                    json={
                        "model": "Qwen2.5-72B" if port == 9400 else "Qwen2.5-7B",
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Salvează interacțiunea pentru învățare
                    if use_learning_mode:
                        self._save_learning_interaction(
                            prompt=full_prompt,
                            response=content,
                            context="qwen_local_learning",
                            source_doc_id="live"
                        )
                    
                    return {
                        "success": True,
                        "content": content,
                        "model": f"Qwen-{port}",
                        "port": port,
                        "tokens": data.get("usage", {}).get("total_tokens", 0)
                    }
            except Exception as e:
                self.logger.warning(f"Qwen on port {port} failed: {e}")
                continue
        
        return {
            "success": False,
            "error": "Qwen local not available on ports 9400 or 9201"
        }


def get_continuous_learner() -> ContinuousLearner:
    """Get singleton learner instance"""
    global _learner_instance
    if '_learner_instance' not in globals():
        _learner_instance = ContinuousLearner()
    return _learner_instance


if __name__ == "__main__":
    # Test continuous learner
    print("🧠 Testing Continuous Learner...")
    
    learner = ContinuousLearner()
    
    # Test process
    stats = learner.process_for_learning(limit=50)
    print(f"✅ Processed: {stats}")
    
    # Test Qwen local
    result = learner.send_to_qwen_local(
        prompt="Analizează statusul sistemului și oferă recomandări",
        context={"gpu_usage": "1%", "vllm_status": "restarting"}
    )
    print(f"✅ Qwen response: {result.get('success', False)}")


