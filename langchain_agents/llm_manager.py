"""
LangChain LLM Manager - Manager centralizat pentru LLM-uri compatibile LangChain

Transformă Qwen și DeepSeek în obiecte LangChain utilizabile direct în lanțuri.
"""

import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# LangChain imports
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.language_models import BaseChatModel
except ImportError:
    try:
        from langchain.chat_models import ChatOpenAI
        from langchain.schema import BaseChatModel
    except ImportError:
        ChatOpenAI = None
        BaseChatModel = None
        logging.warning("⚠️ LangChain ChatOpenAI not available")

load_dotenv(override=True)
logger = logging.getLogger(__name__)

# Configurații
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "http://localhost:9304/v1")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "local")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen2.5")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")  # Fallback la OPENAI_API_KEY
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")  # Cel mai puternic model

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")


class LLMManager:
    """
    Manager centralizat pentru LLM-uri compatibile LangChain
    """
    
    def __init__(self):
        self._llm_cache: Dict[str, BaseChatModel] = {}
    
    def get_langchain_llm(
        self,
        model_name: str = "qwen",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Optional[BaseChatModel]:
        """
        Obține un LLM compatibil LangChain
        
        Args:
            model_name: "qwen", "deepseek", sau "openai"
            temperature: Temperature pentru generare
            max_tokens: Max tokens pentru răspuns
            **kwargs: Parametri suplimentari pentru LLM
        
        Returns:
            Instanță ChatOpenAI sau None dacă nu este disponibil
        """
        if not ChatOpenAI:
            logger.error("❌ LangChain ChatOpenAI not available")
            return None
        
        # Cache key pentru instanțe identice
        cache_key = f"{model_name}_{temperature}_{max_tokens}"
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]
        
        try:
            if model_name.lower() == "qwen":
                llm = self._get_qwen_llm(temperature, max_tokens, **kwargs)
            elif model_name.lower() == "deepseek":
                llm = self._get_deepseek_llm(temperature, max_tokens, **kwargs)
            elif model_name.lower() == "openai":
                llm = self._get_openai_llm(temperature, max_tokens, **kwargs)
            else:
                logger.warning(f"⚠️ Unknown model: {model_name}, using Qwen as default")
                llm = self._get_qwen_llm(temperature, max_tokens, **kwargs)
            
            if llm:
                self._llm_cache[cache_key] = llm
                logger.info(f"✅ Created LangChain LLM: {model_name} (temp={temperature}, max_tokens={max_tokens})")
            
            return llm
            
        except Exception as e:
            logger.error(f"❌ Error creating LLM {model_name}: {e}")
            return None
    
    def _get_qwen_llm(
        self,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Optional[BaseChatModel]:
        """Creează instanță Qwen compatibilă LangChain"""
        try:
            return ChatOpenAI(
                model=QWEN_MODEL,
                base_url=QWEN_BASE_URL,
                api_key=QWEN_API_KEY,
                temperature=temperature,
                max_tokens=max_tokens or 4096,
                timeout=120,  # Qwen local poate dura mai mult
                **kwargs
            )
        except Exception as e:
            logger.error(f"❌ Error creating Qwen LLM: {e}")
            return None
    
    def _get_deepseek_llm(
        self,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Optional[BaseChatModel]:
        """Creează instanță DeepSeek compatibilă LangChain"""
        if not DEEPSEEK_API_KEY:
            logger.error("❌ DEEPSEEK_API_KEY not set")
            return None
        
        try:
            return ChatOpenAI(
                model=DEEPSEEK_MODEL,
                base_url=DEEPSEEK_BASE_URL,
                api_key=DEEPSEEK_API_KEY,
                temperature=temperature,
                max_tokens=max_tokens or 8192,  # DeepSeek suportă mai multe tokens
                timeout=120,
                **kwargs
            )
        except Exception as e:
            logger.error(f"❌ Error creating DeepSeek LLM: {e}")
            return None
    
    def _get_openai_llm(
        self,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Optional[BaseChatModel]:
        """Creează instanță OpenAI compatibilă LangChain (fallback)"""
        if not OPENAI_API_KEY:
            logger.warning("⚠️ OPENAI_API_KEY not set, skipping OpenAI LLM")
            return None
        
        try:
            return ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
                temperature=temperature,
                max_tokens=max_tokens or 4096,
                **kwargs
            )
        except Exception as e:
            logger.error(f"❌ Error creating OpenAI LLM: {e}")
            return None
    
    def get_qwen_for_tasks(self, **kwargs) -> Optional[BaseChatModel]:
        """
        Qwen optimizat pentru sarcini scurte și concrete
        Temperature mai mică pentru răspunsuri mai deterministe
        """
        return self.get_langchain_llm(
            model_name="qwen",
            temperature=0.3,  # Mai determinist pentru task-uri
            max_tokens=2048,
            **kwargs
        )
    
    def get_deepseek_for_reasoning(self, **kwargs) -> Optional[BaseChatModel]:
        """
        DeepSeek optimizat pentru reasoning și strategie
        Temperature mai mare pentru creativitate strategică
        """
        return self.get_langchain_llm(
            model_name="deepseek",
            temperature=0.8,  # Mai creativ pentru strategie
            max_tokens=8192,  # Mai multe tokens pentru reasoning complex
            **kwargs
        )


# Instanță globală
_llm_manager = None

def get_llm_manager() -> LLMManager:
    """Obține instanța globală a LLM Manager"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager

# Funcții de conveniență
def get_langchain_llm(model_name: str = "qwen", **kwargs) -> Optional[BaseChatModel]:
    """Funcție de conveniență pentru obținerea unui LLM"""
    return get_llm_manager().get_langchain_llm(model_name=model_name, **kwargs)

def get_qwen_llm(**kwargs) -> Optional[BaseChatModel]:
    """Obține Qwen LLM pentru task-uri scurte"""
    return get_llm_manager().get_qwen_for_tasks(**kwargs)

def get_deepseek_llm(**kwargs) -> Optional[BaseChatModel]:
    """Obține DeepSeek LLM pentru reasoning"""
    return get_llm_manager().get_deepseek_for_reasoning(**kwargs)

