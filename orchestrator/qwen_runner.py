import os, requests

QWEN_BASE_URL = os.getenv("QWEN_BASE_URL")        # ex: http://127.0.0.1:8000/v1
QWEN_API_KEY  = os.getenv("QWEN_API_KEY", "sk-local")
QWEN_MODEL    = os.getenv("QWEN_MODEL", "qwen2.5-7b-instruct")

def _enabled() -> bool:
    return bool(QWEN_BASE_URL)

def _chat(messages, temperature=0.2, max_tokens=600):
    url = f"{QWEN_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {QWEN_API_KEY}"}
    payload = {
        "model": QWEN_MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    r = requests.post(url, json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def propose_queries(industry_summary: str, gaps: list[str], lang: str="ro") -> list[str]:
    """
    Returnează o listă de interogări SERP. Dacă Qwen nu e configurat, întoarce câteva queries generice.
    """
    if not _enabled():
        base = ["site:org fire protection association", "NFPA 13 firestopping suppliers", "passive fire protection"]
        return base
    sys = {"role":"system","content":"Răspunzi DOAR cu JSON: {\"queries\":[\"...\"]}"}
    usr = {"role":"user","content":f"Rezumat industrie: {industry_summary}\nGoluri: {gaps}\nLimbă: {lang}\nGenerează până la 8 interogări variate."}
    import json
    try:
        txt = _chat([sys, usr])
        data = json.loads(txt)
        return list(dict.fromkeys([q.strip() for q in data.get("queries", []) if isinstance(q,str) and q.strip()]))
    except Exception:
        return []
