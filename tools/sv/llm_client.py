import os
from langchain_openai import ChatOpenAI

def make_llm():
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY lipsă sau gol.")
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    temp = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    return ChatOpenAI(api_key=key, base_url=base, model=model, temperature=temp, timeout=90)
