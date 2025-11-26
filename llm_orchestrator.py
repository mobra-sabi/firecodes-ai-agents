"""
🎭 LLM ORCHESTRATOR - Universal LLM Manager
============================================

Orchestrează toate apelurile LLM cu fallback inteligent:
1. Qwen local (PRIMARY) - viteză, privacy, cost 0 (Port 8000)
2. DeepSeek (fallback) - ieftin, bun
3. Together AI (emergency) - Llama 70B cloud

Usage:
    from llm_orchestrator import LLMOrchestrator
    
    orchestrator = LLMOrchestrator()
    response = orchestrator.chat("Explică-mi protecția anticorozivă")
"""

import os
from typing import Optional, Dict, List, Any
from openai import OpenAI
import logging
from datetime import datetime
import requests

# Import data collector pentru salvarea interacțiunilor
try:
    from data_collector.collector import save_interaction, save_execution_route, save_diagnostic
    DATA_COLLECTOR_AVAILABLE = True
except ImportError:
    DATA_COLLECTOR_AVAILABLE = False
    logging.warning("⚠️ Data collector not available. Interactions will not be saved.")

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """Orchestrator pentru toate apelurile LLM cu fallback"""
    
    def __init__(self):
        # Load API keys from environment variables
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.together_key = os.getenv("TOGETHER_API_KEY", "")
        self.kimi_key = os.getenv("KIMI_API_KEY", "")
        
        # Initialize clients
        self.deepseek_client = OpenAI(
            api_key=self.deepseek_key,
            base_url="https://api.deepseek.com"
        )
        
        self.openai_client = OpenAI(api_key=self.openai_key)
        
        # Together AI
        self.together_client = None
        if self.together_key:
            self.together_client = OpenAI(
                api_key=self.together_key,
                base_url="https://api.together.xyz/v1"
            )
        
        # Kimi (Moonshot AI)
        self.kimi_client = None
        if self.kimi_key:
            self.kimi_client = OpenAI(
                api_key=self.kimi_key,
                base_url="https://api.moonshot.cn/v1"
            )
        
        # Stats
        self.stats = {
            "deepseek_calls": 0,
            "deepseek_successes": 0,
            "deepseek_failures": 0,
            "together_calls": 0,
            "together_successes": 0,
            "together_failures": 0,
            "openai_calls": 0,
            "openai_successes": 0,
            "openai_failures": 0,
            "kimi_calls": 0,
            "kimi_successes": 0,
            "kimi_failures": 0,
            "qwen_calls": 0,
            "qwen_successes": 0,
            "total_calls": 0
        }
        
        logger.info("🎭 LLM Orchestrator initialized - STRATEGIE LOCAL FIRST")
        logger.info(f"   🚀 PRIMARY: Qwen 2.5 72B Local (Port 8000)")
        logger.info(f"   🔄 FALLBACK 1: DeepSeek: {'✅' if self.deepseek_key else '❌'}")
        logger.info(f"   🔄 FALLBACK 2: Together AI: {'✅' if self.together_key else '❌'}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Apel chat universal cu fallback automat
        """
        self.stats["total_calls"] += 1
        
        # Add system prompt if provided
        if system_prompt and (not messages or messages[0].get("role") != "system"):
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Try models based on preference
        if model == "auto":
            # 1. Try Local Qwen (Fastest, Free)
            result = self._try_qwen_local(messages, temperature, max_tokens)
            if result.get("success"):
                return result.get("content", "")
            
            # 2. Fallback to DeepSeek
            result = self._try_deepseek(messages, temperature, max_tokens)
            if result.get("success"):
                return result.get("content", "")
            
            # 3. Fallback to Together
            if self.together_client:
                result = self._try_together(messages, temperature, max_tokens)
                if result.get("success"):
                    return result.get("content", "")
            
            # 4. Fallback to OpenAI
            result = self._try_openai(messages, temperature, max_tokens)
            if result.get("success"):
                return result.get("content", "")
            
            raise RuntimeError("All LLM providers failed")
        
        elif model == "qwen":
            result = self._try_qwen_local(messages, temperature, max_tokens)
        elif model == "deepseek":
            result = self._try_deepseek(messages, temperature, max_tokens)
        elif model == "together":
            result = self._try_together(messages, temperature, max_tokens)
        else:
            # Generic fallback
            result = self._try_qwen_local(messages, temperature, max_tokens)
        
        if result.get("success"):
            return result.get("content", "")
        else:
            raise RuntimeError(f"LLM call failed: {result.get('error', 'Unknown error')}")
    
    def _try_qwen_local(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """
        Încearcă Qwen2.5-72B-AWQ local pe port 8000
        """
        self.stats["qwen_calls"] += 1
        
        try:
            # vLLM API (OpenAI-compatible)
            response = requests.post(
                "http://localhost:8000/v1/chat/completions",
                json={
                    "model": "local-qwen", # Numele din scriptul de start
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                self.stats["qwen_successes"] += 1
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": "qwen2.5-72b-local",
                    "provider": "local-vllm",
                    "tokens": data.get("usage", {}).get("total_tokens", 0),
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"success": False, "error": f"Status {response.status_code}"}
                
        except Exception as e:
            # Nu logăm eroare critică dacă e doar offline, trecem la fallback
            logger.debug(f"Local LLM not available: {e}")
            return {
                "content": None,
                "model": "qwen-local",
                "provider": "local",
                "success": False,
                "error": str(e)
            }

    def _try_deepseek(self, messages, temperature, max_tokens):
        self.stats["deepseek_calls"] += 1
        try:
            response = self.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            self.stats["deepseek_successes"] += 1
            return {
                "content": response.choices[0].message.content,
                "success": True,
                "provider": "deepseek",
                "model": "deepseek-chat"
            }
        except Exception as e:
            self.stats["deepseek_failures"] += 1
            logger.error(f"DeepSeek Error: {e}")
            return {"success": False, "error": str(e)}

    def _try_together(self, messages, temperature, max_tokens):
        self.stats["together_calls"] += 1
        if not self.together_client:
            return {"success": False, "error": "No API Key"}
            
        try:
            response = self.together_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            self.stats["together_successes"] += 1
            return {
                "content": response.choices[0].message.content,
                "success": True,
                "provider": "together",
                "model": "llama-70b"
            }
        except Exception as e:
            self.stats["together_failures"] += 1
            logger.error(f"Together Error: {e}")
            return {"success": False, "error": str(e)}

    def _try_openai(self, messages, temperature, max_tokens):
        self.stats["openai_calls"] += 1
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            self.stats["openai_successes"] += 1
            return {
                "content": response.choices[0].message.content,
                "success": True,
                "provider": "openai",
                "model": "gpt-4"
            }
        except Exception as e:
            self.stats["openai_failures"] += 1
            return {"success": False, "error": str(e)}

# Singleton instance
_orchestrator_instance = None

def get_orchestrator() -> LLMOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = LLMOrchestrator()
    return _orchestrator_instance

# ============================================================================
# HELPER FUNCTIONS (Outside class)
# ============================================================================

# Singleton instance
_orchestrator_instance = None

def get_orchestrator() -> LLMOrchestrator:
    """Get singleton orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = LLMOrchestrator()
    return _orchestrator_instance

def call_llm_with_fallback(
    prompt: str,
    model_preference: str = "auto",
    max_tokens: int = 2000,
    temperature: float = 0.7,
    system_prompt: Optional[str] = None
) -> str:
    """
    Helper function pentru apeluri LLM simple cu fallback automat
    """
    orch = get_orchestrator()
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
    
    try:
        return orch.chat(
            messages=messages,
            model=model_preference,
            max_tokens=max_tokens,
            temperature=temperature
        )
    except Exception as e:
        logger.error(f"❌ LLM call failed: {e}")
        return f"Error: {str(e)}"
