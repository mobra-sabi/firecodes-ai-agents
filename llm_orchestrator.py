"""
🎭 LLM ORCHESTRATOR - Universal LLM Manager
============================================

Orchestrează toate apelurile LLM cu fallback inteligent:
1. DeepSeek (primary) - Chat, analysis, strategy
2. OpenAI GPT-4 (fallback) - Când DeepSeek eșuează
3. Qwen local (emergency) - Când toate API-urile eșuează

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
        # Load API keys from environment variables (NO hardcoded keys for security)
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.together_key = os.getenv("TOGETHER_API_KEY", "")
        self.kimi_key = os.getenv("KIMI_API_KEY", "")  # Moonshot AI - ORCHESTRATOR PRINCIPAL
        
        # Initialize clients
        self.deepseek_client = OpenAI(
            api_key=self.deepseek_key,
            base_url="https://api.deepseek.com"
        )
        
        self.openai_client = OpenAI(api_key=self.openai_key)
        
        # Together AI - Llama 3.1 70B + alte modele (70B params, 128K context!)
        self.together_client = None
        if self.together_key:
            self.together_client = OpenAI(
                api_key=self.together_key,
                base_url="https://api.together.xyz/v1"
            )
        
        # Kimi (Moonshot AI) - Compatible with OpenAI SDK (optional, pentru viitor)
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
        
        logger.info("🎭 LLM Orchestrator initialized - STRATEGIE FINALĂ AGENT CREATION")
        logger.info(f"   🎯 PRIMARY: Llama 3.1 70B (Together AI): {'✅' if self.together_key else '❌'} - 70B params, 128K context!")
        logger.info(f"   🔄 FALLBACK: DeepSeek: {'✅' if self.deepseek_key else '❌'} - ieftin, bun")
        logger.info(f"   ⚡ EMERGENCY: Qwen2.5-72B local - 72B params, 32K context, 8 GPU-uri!")
        logger.info(f"   📊 Fallback chain: Llama 3.1 70B → DeepSeek → Qwen2.5-72B local")
    
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
        
        Args:
            messages: Lista de mesaje [{"role": "user", "content": "..."}]
            model: "auto", "deepseek", "openai", "qwen", "together", "kimi"
            temperature: 0.0-1.0
            max_tokens: Limită tokens
            system_prompt: System prompt optional
        
        Returns:
            str: Content from LLM response
        """
        self.stats["total_calls"] += 1
        
        # Add system prompt if provided
        if system_prompt and (not messages or messages[0].get("role") != "system"):
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Try models based on preference
        if model == "auto":
            # Try DeepSeek first (fast and cheap)
            result = self._try_deepseek(messages, temperature, max_tokens)
            if result.get("success"):
                return result.get("content", "")
            
            # Fallback to Together (Llama 3.1 70B)
            if self.together_client:
                result = self._try_together(messages, temperature, max_tokens)
                if result.get("success"):
                    return result.get("content", "")
            
            # Fallback to Kimi
            if self.kimi_client:
                result = self._try_kimi(messages, temperature, max_tokens)
                if result.get("success"):
                    return result.get("content", "")
            
            # Final fallback to OpenAI
            result = self._try_openai(messages, temperature, max_tokens)
            if result.get("success"):
                return result.get("content", "")
            
            raise RuntimeError("All LLM providers failed")
        
        elif model == "deepseek" or "deepseek" in model:
            result = self._try_deepseek(messages, temperature, max_tokens)
        elif model == "together" or "llama" in model.lower():
            result = self._try_together(messages, temperature, max_tokens)
        elif model == "kimi" or "moonshot" in model.lower():
            result = self._try_kimi(messages, temperature, max_tokens)
        elif model == "openai" or "gpt" in model.lower():
            result = self._try_openai(messages, temperature, max_tokens)
        elif model == "qwen":
            result = self._try_qwen_local(messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown model: {model}")
        
        if result.get("success"):
            return result.get("content", "")
        else:
            raise RuntimeError(f"LLM call failed: {result.get('error', 'Unknown error')}")
    
    def _try_deepseek(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Încearcă DeepSeek"""
        self.stats["deepseek_calls"] += 1
        
        try:
            response = self.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            self.stats["deepseek_successes"] += 1
            
            response_content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Salvează interacțiunea pentru fine-tuning
            if DATA_COLLECTOR_AVAILABLE:
                try:
                    prompt_text = messages[-1].get("content", "") if messages else ""
                    save_interaction(
                        prompt=prompt_text,
                        provider_name="deepseek",
                        response_text=response_content,
                        topic="orchestrator_auto",
                        model=response.model,
                        tokens=tokens_used,
                        success=True
                    )
                except Exception as e:
                    logger.warning(f"Failed to save interaction: {e}")
            
            return {
                "content": response_content,
                "model": response.model,
                "provider": "deepseek",
                "tokens": tokens_used,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.stats["deepseek_failures"] += 1
            logger.error(f"❌ DeepSeek error: {e}")
            
            return {
                "content": None,
                "model": "deepseek-chat",
                "provider": "deepseek",
                "tokens": 0,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    
    def _try_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Încearcă OpenAI GPT-4"""
        self.stats["openai_calls"] += 1
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",  # sau gpt-3.5-turbo dacă ai quota
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            self.stats["openai_successes"] += 1
            
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "provider": "openai",
                "tokens": response.usage.total_tokens if response.usage else 0,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.stats["openai_failures"] += 1
            logger.error(f"❌ OpenAI error: {e}")
            
            return {
                "content": None,
                "model": "gpt-4",
                "provider": "openai",
                "tokens": 0,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    
    def _try_kimi(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """
        Încearcă Kimi K2 70B (Moonshot AI)
        
        Kimi K2 70B:
        - 200K context window (perfect pentru site-uri întregi!)
        - 70B parameters (mult mai puternic decât K1.5)
        - Raționament avansat și analiză profundă
        - Suportă Chineză + Engleză + multilingv
        - COT (Chain-of-Thought) pentru probleme complexe
        """
        self.stats["kimi_calls"] += 1
        
        if not self.kimi_client:
            self.stats["kimi_failures"] += 1
            return {
                "content": None,
                "model": "kimi-k2-70b",
                "provider": "kimi",
                "tokens": 0,
                "success": False,
                "error": "Kimi API key not configured",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Try Kimi K2 models (70B parameters)
            # Moonshot API may use different model names:
            # - "moonshot-v1-k2" (latest K2)
            # - "moonshot-v1-128k" (128K context)
            # - "kimi-k2-instruct" (Hugging Face name)
            
            response = self.kimi_client.chat.completions.create(
                model="moonshot-v1-128k",  # K2 70B with 128K context
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            self.stats["kimi_successes"] += 1
            
            response_content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Salvează interacțiunea pentru fine-tuning
            if DATA_COLLECTOR_AVAILABLE:
                try:
                    prompt_text = messages[-1].get("content", "") if messages else ""
                    save_interaction(
                        prompt=prompt_text,
                        provider_name="kimi-k2-70b",
                        response_text=response_content,
                        topic="orchestrator_auto",
                        model=response.model,
                        tokens=tokens_used,
                        success=True
                    )
                except Exception as e:
                    logger.warning(f"Failed to save interaction: {e}")
            
            return {
                "content": response_content,
                "model": response.model,
                "provider": "kimi-k2-70b",
                "tokens": tokens_used,
                "success": True,
                "context_window": "200K tokens",
                "parameters": "70B",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.stats["kimi_failures"] += 1
            logger.error(f"❌ Kimi K2 70B error: {e}")
            
            return {
                "content": None,
                "model": "moonshot-v1-128k",
                "provider": "kimi-k2-70b",
                "tokens": 0,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    
    def _try_together(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """
        Încearcă Together AI cu Llama 3.1 70B
        
        Meta Llama 3.1 70B:
        - 128K context window (mult mai mare decât majoritatea modelelor!)
        - 70B parameters (ultra-puternic, la nivel cu Kimi K2!)
        - Performanță excelentă pentru raționament
        - Suportă multilingual (inclusiv română!)
        - Foarte rapid și stabil
        - Cost rezonabil (~$0.88/1M tokens input, $0.88/1M output)
        """
        self.stats["together_calls"] += 1
        
        if not self.together_client:
            self.stats["together_failures"] += 1
            return {
                "content": None,
                "model": "llama-3.1-70b",
                "provider": "together",
                "tokens": 0,
                "success": False,
                "error": "Together AI API key not configured",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            response = self.together_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            self.stats["together_successes"] += 1
            
            response_content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # Salvează interacțiunea pentru fine-tuning
            if DATA_COLLECTOR_AVAILABLE:
                try:
                    prompt_text = messages[-1].get("content", "") if messages else ""
                    save_interaction(
                        prompt=prompt_text,
                        provider_name="together-llama-3.1-70b",
                        response_text=response_content,
                        topic="orchestrator_auto",
                        model=response.model,
                        tokens=tokens_used,
                        success=True
                    )
                except Exception as e:
                    logger.warning(f"Failed to save interaction: {e}")
            
            return {
                "content": response_content,
                "model": response.model,
                "provider": "together-llama-3.1-70b",
                "tokens": tokens_used,
                "success": True,
                "context_window": "128K tokens",
                "parameters": "70B",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.stats["together_failures"] += 1
            logger.error(f"❌ Together AI (Llama 3.1 70B) error: {e}")
            
            return {
                "content": None,
                "model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                "provider": "together-llama-3.1-70b",
                "tokens": 0,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    
    def _try_qwen_local(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """
        Fallback la Qwen2.5-72B-AWQ local (vLLM pe port 9400)
        
        Configurație:
        - 72B parametri (10× mai puternic decât Qwen 7B)
        - 11 GPU-uri (toate RTX 3080 Ti)
        - 32K context window
        - AWQ quantization pentru viteză
        """
        self.stats["qwen_calls"] += 1
        
        try:
            import requests
            
            # Încearcă mai întâi port 9400 (72B), apoi 9201 (7B)
            ports_to_try = [9400, 9201]
            model_names = ["Qwen2.5-72B", "Qwen2.5-7B"]
            
            for port, model_name in zip(ports_to_try, model_names):
                try:
                    # vLLM API (OpenAI-compatible)
                    response = requests.post(
                        f"http://localhost:{port}/v1/chat/completions",
                        json={
                            "model": model_name,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        },
                        timeout=120  # Longer timeout pentru 72B model
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.stats["qwen_successes"] += 1
                        
                        response_content = data["choices"][0]["message"]["content"]
                        tokens_used = data.get("usage", {}).get("total_tokens", 0)
                        
                        # Detectează modelul folosit (din răspuns sau din port)
                        used_model = data.get("model", model_name)
                        used_port = port
                        
                        # Salvează interacțiunea pentru fine-tuning (cu context pentru învățare)
                        if DATA_COLLECTOR_AVAILABLE:
                            try:
                                prompt_text = messages[-1].get("content", "") if messages else ""
                                # Adaugă context diagnostic dacă există
                                diagnostic_context = {
                                    "gpu_count": 11,
                                    "model_size": "72B" if "72B" in used_model else "7B",
                                    "context_window": "32K",
                                    "local_inference": True,
                                    "port": used_port,
                                    "model_used": used_model
                                }
                                interaction_id = save_interaction(
                                    prompt=prompt_text,
                                    provider_name="qwen2.5-72b-local",
                                    response_text=response_content,
                                    topic="orchestrator_auto_learning",
                                    model=used_model,
                                    tokens=tokens_used,
                                    success=True,
                                    diagnostic_context=diagnostic_context
                                )
                            except Exception as e:
                                logger.warning(f"Failed to save interaction: {e}")
                        
                        # Return success - exit loop
                        return {
                            "content": response_content,
                            "model": used_model,
                            "provider": "qwen2.5-72b-local",
                            "tokens": tokens_used,
                            "success": True,
                            "parameters": "72B" if "72B" in used_model else "7B",
                            "gpus": 11,
                            "context_window": "32K tokens",
                            "port": used_port,
                            "timestamp": datetime.now().isoformat()
                        }
                except Exception as e:
                    logger.debug(f"Port {port} failed: {e}")
                    continue  # Try next port
            
            # All ports failed
            raise Exception("Qwen local not available on ports 9400 or 9201")
                
        except Exception as e:
            logger.error(f"❌ Qwen2.5-72B local error: {e}")
            
            return {
                "content": "❌ All LLM providers failed (Kimi → DeepSeek → Qwen2.5-72B local). Please check API keys and connectivity.",
                "model": "Qwen2.5-72B-AWQ",
                "provider": "qwen2.5-72b-local",
                "tokens": 0,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    
    def analyze_competitive(
        self,
        context: str,
        domain: str,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Analiză competitivă specializată
        Folosit în DeepSeek competitive analyzer
        """
        system_prompt = f"""Ești un expert în analiză competitivă pentru industria de protecție anticorozivă.

Analizează următorul context despre compania {domain} și:
1. Identifică subdomeniile principale de activitate
2. Generează keywords strategice pentru fiecare subdomeniu
3. Oferă insights despre poziționarea competitivă

Context:
{context[:3000]}

Răspunde DOAR în format JSON:
{{
  "subdomains": [
    {{
      "name": "Nume subdomeniu",
      "description": "Descriere",
      "keywords": ["keyword1", "keyword2", ...]
    }}
  ],
  "keywords": ["keyword1", "keyword2", ...],
  "competitive_insights": "Text insights"
}}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analizează domeniul {domain}"}
        ]
        
        return self.chat(messages, model="auto", temperature=0.3, max_tokens=max_tokens)
    
    
    def extract_services(
        self,
        content: str,
        domain: str
    ) -> Dict[str, Any]:
        """
        Extrage servicii dintr-un website
        Folosit în agent creation
        """
        system_prompt = f"""Ești un expert în extragerea informațiilor structurate din conținut web.

Extrage toate serviciile oferite de compania {domain} din următorul conținut:

{content[:2000]}

Răspunde DOAR în format JSON:
{{
  "company_name": "Nume companie",
  "services": [
    {{
      "name": "Nume serviciu",
      "description": "Descriere scurtă"
    }}
  ],
  "industry": "Industrie",
  "location": "Locație"
}}
"""
        
        messages = [{"role": "user", "content": system_prompt}]
        
        return self.chat(messages, model="auto", temperature=0.2, max_tokens=2000)
    
    
    def generate_strategy(
        self,
        agent_context: str,
        competitors_context: str,
        strategy_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Generează strategie marketing bazată pe context
        Folosit în task execution
        """
        system_prompt = f"""Ești un strateg de marketing cu expertiză în {strategy_type}.

Generează o strategie detaliată bazată pe:

AGENT CONTEXT:
{agent_context[:1500]}

COMPETITORS CONTEXT:
{competitors_context[:1500]}

Răspunde cu o strategie acționabilă în format markdown.
"""
        
        messages = [{"role": "user", "content": system_prompt}]
        
        return self.chat(messages, model="auto", temperature=0.7, max_tokens=3000)
    
    
    def get_stats(self) -> Dict[str, Any]:
        """Returnează statistici de utilizare"""
        success_rate = 0
        if self.stats["total_calls"] > 0:
            successes = (
                self.stats["deepseek_successes"] +
                self.stats["together_successes"] +
                self.stats["kimi_successes"] +
                self.stats["openai_successes"] +
                self.stats["qwen_successes"]
            )
            success_rate = (successes / self.stats["total_calls"]) * 100
        
        return {
            **self.stats,
            "success_rate": round(success_rate, 2),
            "primary_provider": "llama-3.1-70b",
            "fallback_chain": ["llama-3.1-70b-together", "deepseek", "qwen2.5-72b-local"]
        }
    
    
    def process_large_content(
        self,
        content: str,
        task: str,
        model: str = "together",
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Procesează conținut mare (site întreg) cu Llama 3.1 70B (128K context) - ORCHESTRATOR PRINCIPAL
        
        Perfect pentru:
        - Analiză site complet (până la 128K tokens cu Llama 3.1 70B!)
        - Extragere informații din documentație lungă
        - Descompunere în subdomenii complexe
        - Generare keywords comprehensivă (10-15 per subdomeniu)
        - Competitive intelligence profundă
        - Raționament complex și analiză profundă
        - Orchestrare creeare agenți AI
        
        Args:
            content: Conținutul complet (până la 128K tokens!)
            task: Task-ul de executat
            model: "together" (Llama 3.1 70B - DEFAULT 128K context), "deepseek" (fallback), "auto"
            temperature: 0.0-1.0
        
        Returns:
            Răspuns cu analiza completă (70B parameters pentru calitate superioară)
        """
        messages = [
            {
                "role": "system",
                "content": """Tu ești un expert în analiza site-urilor și competitive intelligence powered by Llama 3.1 70B (128K context). 
Ai capacitatea de a procesa și analiza conținut FOARTE mare (128K tokens) cu raționament avansat.
Ești specializat în:
- Descompunere site în subdomenii
- Generare keywords SEO inteligente (10-15 per subdomeniu)
- Competitive analysis
- Orchestrare creeare agenți AI

Folosește analiză profundă și oferă insights valoroase și acționabile."""
            },
            {
                "role": "user",
                "content": f"""{task}

CONȚINUT SITE:
{content}

Te rog analizează complet folosind toate capacitățile tale (70B params, 128K context) și oferă un răspuns detaliat și structurat."""
            }
        ]
        
        # Folosește modelul specificat pentru context mare
        if model == "together":
            result = self._try_together(messages, temperature, max_tokens=4000)
        elif model == "deepseek":
            result = self._try_deepseek(messages, temperature, max_tokens=4000)
        else:
            result = self.chat(messages, model=model, temperature=temperature, max_tokens=4000)
        
        return result


# ============================================================================
# HELPER FUNCTIONS (Outside class)
# ============================================================================

# Singleton instance
_orchestrator_instance = None

def call_llm_with_fallback(
    prompt: str,
    model_preference: str = "deepseek",
    max_tokens: int = 2000,
    temperature: float = 0.7,
    system_prompt: Optional[str] = None
) -> str:
    """
    Helper function pentru apeluri LLM simple cu fallback automat
    
    Args:
        prompt: Text prompt pentru LLM
        model_preference: "deepseek", "qwen", "llama", "kimi", "openai"
        max_tokens: Max tokens în response
        temperature: Creativitate (0-1)
        system_prompt: System prompt opțional
    
    Returns:
        str: Response de la LLM
    """
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = LLMOrchestrator()
    
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
    
    # Map model preference la model actual
    model_map = {
        "deepseek": "deepseek-chat",
        "qwen": "qwen2.5-72b-instruct",
        "llama": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "kimi": "moonshot-v1-32k",
        "openai": "gpt-4"
    }
    
    model = model_map.get(model_preference, "auto")
    
    try:
        response = _orchestrator_instance.chat(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response
    except Exception as e:
        logger.error(f"❌ LLM call failed: {e}")
        raise


def get_orchestrator() -> LLMOrchestrator:
    """Get singleton orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = LLMOrchestrator()
    return _orchestrator_instance


if __name__ == "__main__":
    # Test orchestrator
    print("=" * 80)
    print("🧪 TEST LLM ORCHESTRATOR")
    print("=" * 80)
    
    orch = LLMOrchestrator()
    
    # Test 1: Simple chat
    print("\n1️⃣ Test chat simplu:")
    result = orch.chat([
        {"role": "user", "content": "Explică în 2 propoziții ce este protecția anticorozivă."}
    ])
    
    print(f"   Provider: {result.get('provider', 'N/A')}")
    print(f"   Model: {result.get('model', 'N/A')}")
    print(f"   Success: {result.get('success', False)}")
    content = result.get('content', '')
    if content:
        print(f"   Response: {content[:200]}...")
    
    # Test 2: Competitive analysis
    print("\n2️⃣ Test analyze_competitive:")
    result = orch.analyze_competitive(
        context="Anticor oferă servicii de sablare, vopsire și protecție anticorozivă în Cluj-Napoca.",
        domain="anticor.ro"
    )
    
    print(f"   Provider: {result.get('provider', 'N/A')}")
    print(f"   Success: {result.get('success', False)}")
    if result.get('success'):
        content = result.get('content', '')
        print(f"   Response length: {len(content)} chars")
    
    # Stats
    print("\n📊 STATISTICS:")
    stats = orch.get_stats()
    for key, val in stats.items():
        print(f"   {key}: {val}")
    
    print("\n" + "=" * 80)

