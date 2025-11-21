import os
import time
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv

# Load .env before reading env vars (override to ensure .env values take precedence)
load_dotenv(override=True)

DEEPSEEK_BASE = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
OPENAI_BASE = "https://api.openai.com/v1"


def _get_deepseek_key() -> str:
    import logging
    logger = logging.getLogger(__name__)
    
    # ⭐ VERIFICARE: Ce key avem disponibil?
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    logger.info(f"🔑 DEEPSEEK_API_KEY prezent: {bool(deepseek_key)} (len={len(deepseek_key)})")
    logger.info(f"🔑 OPENAI_API_KEY prezent: {bool(openai_key)} (len={len(openai_key)})")
    
    key = deepseek_key or openai_key
    if not key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY (or OPENAI_API_KEY) in environment")
    
    logger.info(f"✅ Folosesc API key: {key[:10]}... (len={len(key)})")
    return key


def _get_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing OPENAI_API_KEY in environment")
    return key


def reasoner_chat(
    messages: List[Dict[str, str]],
    max_tokens: int = 800,
    temperature: float = 0.3,
    extra: Optional[Dict] = None,
    timeout: int = 180,  # Timeout mai mare pentru DeepSeek Reasoner (3 minute)
    max_retries: int = 3,  # Retry logic pentru timeout-uri
    use_fallback: bool = True,  # 🆕 Activează fallback pe OpenAI
) -> Dict:
    """Call DeepSeek Reasoner model via OpenAI-compatible API, cu fallback pe OpenAI.

    Required env:
      - DEEPSEEK_API_KEY (preferred) or OPENAI_API_KEY
      - OPENAI_BASE_URL (defaults to DeepSeek)
    
    Args:
        timeout: Timeout în secunde (default 180 pentru Reasoner)
        max_retries: Număr maxim de retry-uri pentru timeout-uri
        use_fallback: Dacă True, încearcă OpenAI dacă DeepSeek eșuează (default True)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    payload = {
        "model": "deepseek-chat",  # ⭐ FIX: deepseek-chat în loc de deepseek-reasoner
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if extra:
        payload.update(extra)

    api_key = _get_deepseek_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    logger.info(f"📤 DeepSeek payload: model={payload['model']}, messages={len(messages)}, max_tokens={max_tokens}")

    # Retry logic pentru timeout-uri
    last_error = None
    for attempt in range(max_retries):
        try:
            t0 = time.time()
            logger.info(f"🔄 DeepSeek API call (attempt {attempt + 1}/{max_retries}), timeout={timeout}s, max_tokens={max_tokens}")
            
            resp = requests.post(
                f"{DEEPSEEK_BASE}/chat/completions",
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            duration = time.time() - t0
            resp.raise_for_status()
            data = resp.json()
            
            logger.info(f"✅ DeepSeek API call successful în {duration:.2f}s")
            return {"data": data, "meta": {"duration_s": round(duration, 3), "provider": "deepseek"}}
            
        except requests.exceptions.Timeout as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  # Exponential backoff: 5s, 10s, 15s
                logger.warning(f"⚠️ DeepSeek API timeout (attempt {attempt + 1}/{max_retries}). Retrying în {wait_time}s...")
                time.sleep(wait_time)
                # Mărește timeout-ul pentru următoarea încercare
                timeout = min(timeout + 30, 300)  # Max 5 minute
            else:
                logger.error(f"❌ DeepSeek API timeout după {max_retries} încercări")
                if use_fallback:
                    logger.warning("🔄 Încerc fallback pe OpenAI...")
                    break  # Exit loop pentru fallback
                else:
                    raise Exception(f"DeepSeek API timeout după {max_retries} încercări. Ultimul timeout: {timeout}s. Încearcă să reduci max_tokens sau prompt size.")
                
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                logger.warning(f"⚠️ DeepSeek API error (attempt {attempt + 1}/{max_retries}): {e}. Retrying în {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"❌ DeepSeek API error după {max_retries} încercări: {e}")
                if use_fallback:
                    logger.warning("🔄 Încerc fallback pe OpenAI...")
                    break  # Exit loop pentru fallback
                else:
                    raise Exception(f"DeepSeek API error: {str(e)}")
    
    # 🆕 FALLBACK: Încearcă OpenAI dacă DeepSeek a eșuat
    if use_fallback and last_error:
        try:
            logger.info("🤖 Fallback pe OpenAI GPT-4...")
            
            # Payload pentru OpenAI (model diferit)
            openai_payload = {
                "model": "gpt-4-turbo-preview",  # Sau "gpt-4o" pentru cel mai recent
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if extra:
                openai_payload.update(extra)
            
            openai_headers = {
                "Authorization": f"Bearer {_get_openai_key()}",
                "Content-Type": "application/json",
            }
            
            t0 = time.time()
            resp = requests.post(
                f"{OPENAI_BASE}/chat/completions",
                json=openai_payload,
                headers=openai_headers,
                timeout=timeout
            )
            
            duration = time.time() - t0
            resp.raise_for_status()
            data = resp.json()
            
            logger.info(f"✅ OpenAI API call successful în {duration:.2f}s (fallback)")
            return {"data": data, "meta": {"duration_s": round(duration, 3), "provider": "openai", "fallback": True}}
            
        except Exception as openai_error:
            logger.error(f"❌ OpenAI fallback failed: {openai_error}")
            # Aruncă eroarea originală DeepSeek + eroarea OpenAI
            raise Exception(f"DeepSeek failed: {str(last_error)}. OpenAI fallback failed: {str(openai_error)}")
    
    # Nu ar trebui să ajungă aici, dar pentru siguranță
    if last_error:
        raise Exception(f"DeepSeek API failed: {str(last_error)}")
    raise Exception("DeepSeek API call failed for unknown reason")


