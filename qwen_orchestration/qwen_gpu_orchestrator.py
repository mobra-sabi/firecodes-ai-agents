#!/usr/bin/env python3
"""
⚡ QWEN GPU ORCHESTRATOR - Distributed Processing

Arhitectură:
    DeepSeek (Manager/Orchestrator)
        ↓
    Qwen Workers (GPU 6-10) - Heavy Lifting
        ↓
    DeepSeek (Synthesizer) → CEO

Procesare paralelă pe multiple GPU-uri pentru:
- Keyword intent analysis
- SERP content analysis
- Competitor page analysis
- Content gap detection
- Content generation
"""

import os
import sys
sys.path.insert(0, '/srv/hf/ai_agents')

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime
import requests
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QwenWorker:
    """
    Worker Qwen pe un GPU specific
    """
    
    def __init__(self, gpu_id: int, role: str, qwen_port: int = 9301):
        self.gpu_id = gpu_id
        self.role = role
        self.qwen_url = f"http://localhost:{qwen_port}/v1/chat/completions"
        self.model = "Qwen2.5-72B-Instruct-GPTQ-Int4"
        
        logger.info(f"✅ Qwen Worker initialized: GPU {gpu_id}, Role: {role}")
    
    async def process(self, task: Dict) -> Dict:
        """
        Procesează un task pe acest worker
        """
        try:
            logger.info(f"🔧 GPU {self.gpu_id} ({self.role}): Processing task...")
            
            # Prepare request pentru Qwen
            messages = task.get("messages", [])
            max_tokens = task.get("max_tokens", 1000)
            temperature = task.get("temperature", 0.3)
            
            # Call Qwen API
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(
                self.qwen_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                logger.info(f"✅ GPU {self.gpu_id}: Task completed")
                
                return {
                    "success": True,
                    "gpu_id": self.gpu_id,
                    "role": self.role,
                    "content": content,
                    "task_type": task.get("type")
                }
            else:
                logger.error(f"❌ GPU {self.gpu_id}: Qwen API error {response.status_code}")
                return {
                    "success": False,
                    "gpu_id": self.gpu_id,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"❌ GPU {self.gpu_id}: Exception - {e}")
            return {
                "success": False,
                "gpu_id": self.gpu_id,
                "error": str(e)
            }


class DeepSeekManager:
    """
    DeepSeek ca Manager/Orchestrator
    - Planifică taskuri
    - Distribuie la Qwen workers
    - Sintetizează rezultate
    """
    
    def __init__(self):
        self.deepseek_url = "https://api.deepseek.com/chat/completions"
        self.api_key = os.getenv("DEEPSEEK_API_KEY", open("/srv/hf/ai_agents/.secrets/deepseek.key").read().strip())
        self.model = "deepseek-chat"
        
        logger.info("✅ DeepSeek Manager initialized")
    
    def plan_subtasks(self, main_task: Dict) -> Dict[str, Dict]:
        """
        DeepSeek planifică cum să împartă task-ul pe workers
        
        Args:
            main_task: Task principal (ex: "Analyze competitive landscape")
        
        Returns:
            Dict cu subtask-uri per worker
        """
        task_type = main_task.get("type")
        
        # Planificare bazată pe tip task
        if task_type == "competitive_analysis":
            return self._plan_competitive_analysis(main_task)
        elif task_type == "keyword_analysis":
            return self._plan_keyword_analysis(main_task)
        elif task_type == "content_gap":
            return self._plan_content_gap(main_task)
        else:
            return {}
    
    def _plan_competitive_analysis(self, task: Dict) -> Dict[str, Dict]:
        """
        Planifică competitive analysis pe multiple workers
        """
        competitors = task.get("competitors", [])
        keywords = task.get("keywords", [])
        
        # Distribute pe workers
        subtasks = {}
        
        # GPU 6: Intent analysis pentru keywords
        if keywords:
            subtasks["gpu_6"] = {
                "type": "keyword_intent",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ești expert SEO. Analizează intent-ul keywords."
                    },
                    {
                        "role": "user",
                        "content": f"Analizează intent pentru: {', '.join(keywords[:20])}"
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3
            }
        
        # GPU 7: SERP analysis
        if keywords:
            subtasks["gpu_7"] = {
                "type": "serp_analysis",
                "messages": [
                    {
                        "role": "system",
                        "content": "Analizezi rezultate SERP pentru competitive intelligence."
                    },
                    {
                        "role": "user",
                        "content": f"Analizează SERP pentru: {keywords[0] if keywords else 'N/A'}"
                    }
                ],
                "max_tokens": 1000
            }
        
        # GPU 8-10: Competitor page analysis (paralel pentru multiple competitors)
        for i, competitor in enumerate(competitors[:3], 8):
            subtasks[f"gpu_{i}"] = {
                "type": "competitor_analysis",
                "messages": [
                    {
                        "role": "system",
                        "content": "Analizezi strategic competitors."
                    },
                    {
                        "role": "user",
                        "content": f"Analizează competitor: {competitor.get('domain', 'N/A')}"
                    }
                ],
                "max_tokens": 800
            }
        
        return subtasks
    
    def _plan_keyword_analysis(self, task: Dict) -> Dict[str, Dict]:
        """
        Planifică keyword analysis batch
        """
        keywords = task.get("keywords", [])
        
        # Split keywords între workers
        chunk_size = len(keywords) // 5 + 1
        subtasks = {}
        
        for i in range(5):
            gpu_id = 6 + i
            keyword_chunk = keywords[i*chunk_size:(i+1)*chunk_size]
            
            if keyword_chunk:
                subtasks[f"gpu_{gpu_id}"] = {
                    "type": "keyword_intent",
                    "keywords": keyword_chunk,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Analizezi intent keywords."
                        },
                        {
                            "role": "user",
                            "content": f"Analizează: {', '.join(keyword_chunk)}"
                        }
                    ],
                    "max_tokens": 1500
                }
        
        return subtasks
    
    def _plan_content_gap(self, task: Dict) -> Dict[str, Dict]:
        """
        Planifică content gap analysis
        """
        master_content = task.get("master_content", {})
        competitor_contents = task.get("competitor_contents", [])
        
        subtasks = {}
        
        # GPU 6-8: Fiecare analizează content gap vs 1-2 competitori
        chunk_size = len(competitor_contents) // 3 + 1
        
        for i in range(3):
            gpu_id = 6 + i
            comp_chunk = competitor_contents[i*chunk_size:(i+1)*chunk_size]
            
            if comp_chunk:
                subtasks[f"gpu_{gpu_id}"] = {
                    "type": "content_gap",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Identifici gaps în content strategy."
                        },
                        {
                            "role": "user",
                            "content": f"Compară master content cu {len(comp_chunk)} competitori și identifică gaps."
                        }
                    ],
                    "max_tokens": 1200
                }
        
        return subtasks
    
    def synthesize(self, results: List[Dict]) -> Dict:
        """
        DeepSeek sintetizează rezultatele de la toți workers
        """
        logger.info(f"🔄 DeepSeek synthesizing {len(results)} worker results...")
        
        try:
            # Build synthesis prompt
            synthesis_prompt = "Sintetizează următoarele analize:\n\n"
            
            for i, result in enumerate(results, 1):
                if result.get("success"):
                    synthesis_prompt += f"\n{i}. GPU {result['gpu_id']} ({result['role']}):\n"
                    synthesis_prompt += f"{result['content'][:500]}...\n"
            
            synthesis_prompt += "\nGenereaz un rezumat strategic concis."
            
            # Call DeepSeek pentru synthesis
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Ești un CEO strategist care sintetizează analize complexe."
                    },
                    {
                        "role": "user",
                        "content": synthesis_prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.5
            }
            
            response = requests.post(
                self.deepseek_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                synthesis = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                logger.info("✅ DeepSeek synthesis complete")
                
                return {
                    "success": True,
                    "synthesis": synthesis,
                    "worker_results": results
                }
            else:
                logger.error(f"❌ DeepSeek synthesis error: {response.status_code}")
                return {
                    "success": False,
                    "error": "Synthesis failed",
                    "worker_results": results
                }
                
        except Exception as e:
            logger.error(f"❌ Synthesis exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "worker_results": results
            }


class QwenGPUOrchestrator:
    """
    Orchestrator principal:
    - Inițializează Qwen workers pe GPU-uri
    - Folosește DeepSeek ca manager
    - Coordonează procesarea paralelă
    """
    
    def __init__(self, gpu_ids: List[int] = [6, 7, 8, 9, 10]):
        self.gpu_ids = gpu_ids
        self.deepseek = DeepSeekManager()
        
        # Initialize Qwen workers
        self.qwen_workers = {}
        roles = ["intent_analysis", "serp_analysis", "competitor_analysis", "gap_detection", "content_gen"]
        
        for i, gpu_id in enumerate(gpu_ids):
            role = roles[i % len(roles)]
            self.qwen_workers[f"gpu_{gpu_id}"] = QwenWorker(gpu_id=gpu_id, role=role)
        
        logger.info(f"✅ Qwen GPU Orchestrator initialized with {len(gpu_ids)} workers")
    
    async def orchestrate_analysis(self, task: Dict) -> Dict:
        """
        Orchestrează analiza completă:
        1. DeepSeek planifică subtask-uri
        2. Qwen workers procesează în paralel
        3. DeepSeek sintetizează
        """
        logger.info("="*80)
        logger.info("🚀 QWEN GPU ORCHESTRATION - START")
        logger.info("="*80)
        
        try:
            # STEP 1: DeepSeek planifică
            logger.info("📋 STEP 1: DeepSeek planning subtasks...")
            subtasks = self.deepseek.plan_subtasks(task)
            logger.info(f"   Planned {len(subtasks)} subtasks for workers")
            
            # STEP 2: Qwen workers procesează în paralel
            logger.info("⚡ STEP 2: Qwen workers processing in parallel...")
            
            worker_tasks = []
            for worker_id, subtask in subtasks.items():
                if worker_id in self.qwen_workers:
                    worker_tasks.append(
                        self.qwen_workers[worker_id].process(subtask)
                    )
            
            if worker_tasks:
                results = await asyncio.gather(*worker_tasks)
            else:
                results = []
            
            logger.info(f"   ✅ {len(results)} workers completed")
            
            # STEP 3: DeepSeek sintetizează
            logger.info("🔄 STEP 3: DeepSeek synthesizing results...")
            final_result = self.deepseek.synthesize(results)
            
            logger.info("="*80)
            logger.info("✅ ORCHESTRATION COMPLETE")
            logger.info("="*80)
            
            return final_result
            
        except Exception as e:
            logger.error(f"❌ Orchestration failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Test
async def test_orchestrator():
    print("="*80)
    print("🧪 TESTING QWEN GPU ORCHESTRATOR")
    print("="*80)
    
    orchestrator = QwenGPUOrchestrator(gpu_ids=[6, 7, 8])  # Test cu 3 GPUs
    
    # Test task
    test_task = {
        "type": "keyword_analysis",
        "keywords": [
            "protectie la foc",
            "sisteme antiincendiu",
            "extinctoare certificate"
        ]
    }
    
    result = await orchestrator.orchestrate_analysis(test_task)
    
    if result.get("success"):
        print("\n✅ ORCHESTRATION SUCCESSFUL!")
        print(f"\n📝 Synthesis:\n{result.get('synthesis', 'N/A')[:500]}...")
    else:
        print(f"\n❌ FAILED: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(test_orchestrator())

