#!/usr/bin/env python3
"""
🔧 LLM Helper - Wrapper simplu pentru LLMOrchestrator
Folosit de playbook_generator.py și action_agents.py
"""

from typing import Optional
from llm_orchestrator import LLMOrchestrator
import logging

logger = logging.getLogger(__name__)

# Global orchestrator instance
_orchestrator = None


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
        str: Response de la LLM (text content)
    """
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = LLMOrchestrator()
        logger.info("✅ LLM Orchestrator initialized (REAL - NO MOCKS)")
    
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
        # Call DeepSeek directly (REAL API!)
        if model_preference in ["deepseek", "auto"]:
            response = _orchestrator.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
            
        elif model_preference == "qwen":
            # TODO: Add Qwen GPU call
            logger.warning("Qwen not implemented yet, falling back to DeepSeek")
            response = _orchestrator.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
            
        elif model_preference == "kimi":
            if _orchestrator.kimi_client:
                response = _orchestrator.kimi_client.chat.completions.create(
                    model="moonshot-v1-32k",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return response.choices[0].message.content
            else:
                raise RuntimeError("Kimi client not available")
                
        else:
            # Default to DeepSeek
            response = _orchestrator.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
            
    except Exception as e:
        logger.error(f"❌ LLM call failed: {e}")
        raise RuntimeError(f"LLM call failed: {e}")


if __name__ == "__main__":
    # Test
    try:
        response = call_llm_with_fallback(
            prompt="Say 'test successful' in JSON format",
            model_preference="deepseek",
            max_tokens=100
        )
        print(f"✅ Test successful! Response: {response[:100]}")
    except Exception as e:
        print(f"❌ Test failed: {e}")

