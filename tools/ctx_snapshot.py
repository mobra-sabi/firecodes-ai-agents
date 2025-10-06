# tools/ctx_snapshot.py
import os, json, sys, traceback
from pathlib import Path

def safe_len(v): return len(v) if isinstance(v, str) else 0
def has_file(p): 
    try: 
        return Path(p).is_file(), Path(p).stat().st_size
    except: 
        return False, 0

def check_openai_key():
    # nu printăm cheia; doar sursa și validitatea minimală
    env = os.getenv("OPENAI_API_KEY")
    files = [".secrets/openai.key", str(Path.home()/".config/ai_agents/openai.key")]
    present = bool(env)
    src = "ENV" if present else "file"
    key_text = env
    if not present:
        for f in files:
            if Path(f).is_file():
                key_text = Path(f).read_text(encoding="utf-8").strip()
                present = bool(key_text)
                src = f
                break
    return {"present": present, "src": src, "len": safe_len(key_text)}

def check_brave_key():
    env = os.getenv("BRAVE_API_KEY")
    files = [".secrets/brave.key"]
    present = bool(env)
    src = "ENV" if present else "file"
    key_text = env
    if not present:
        for f in files:
            if Path(f).is_file():
                key_text = Path(f).read_text(encoding="utf-8").strip()
                present = bool(key_text)
                src = f
                break
    return {"present": present, "src": src, "len": safe_len(key_text)}

def check_qdrant():
    try:
        from qdrant_client import QdrantClient
        qc = QdrantClient(host=os.getenv("QDRANT_HOST","127.0.0.1"),
                          port=int(os.getenv("QDRANT_PORT","6333")))
        cols = [c.name for c in qc.get_collections().collections]
        info = {}
        for name in cols:
            try:
                cnt = qc.count(name, exact=False).count
            except Exception:
                cnt = None
            info[name] = cnt
        return {"ok": True, "collections": info}
    except Exception as e:
        return {"ok": False, "error": repr(e)}

def check_mongo():
    try:
        from pymongo import MongoClient
        mc = MongoClient(os.getenv("MONGODB_URI","mongodb://127.0.0.1:27017"))
        db = mc[os.getenv("MONGO_DB","ai_agents_db")]
        return {
            "ok": True,
            "site_agents": db["site_agents"].estimated_document_count(),
            "site_content": db["site_content"].estimated_document_count(),
        }
    except Exception as e:
        return {"ok": False, "error": repr(e)}

def ping_llm():
    try:
        # citim cheia din fișier dacă ENV nu e setat
        from tools.llm_key_loader import ensure_openai_key
        ensure_openai_key()
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=os.getenv("LLM_MODEL","gpt-4o-mini"), temperature=0, timeout=60)
        out = llm.invoke([{"role":"user","content":"OK"}]).content
        return {"ok": True, "reply": out[:40]}
    except Exception as e:
        return {"ok": False, "error": repr(e), "trace": traceback.format_exc()[:800]}

def test_serp():
    try:
        from tools.serp_client import search
        urls = search("site:nfpa.org codes and standards", count=3)
        return {"ok": True, "sample": urls}
    except Exception as e:
        return {"ok": False, "error": repr(e)}

def main():
    snap = {
        "env": {
            "LLM_MODEL": os.getenv("LLM_MODEL","gpt-4o-mini"),
            "SERP_PROVIDER": os.getenv("SERP_PROVIDER","brave"),
            "CRAWL_DELAY": os.getenv("CRAWL_DELAY","0.5"),
            "PER_SITE_PAGES": os.getenv("PER_SITE_PAGES","6"),
            "MAX_SITES": os.getenv("MAX_SITES","30"),
            "MAX_PER_DOMAIN": os.getenv("MAX_PER_DOMAIN","5"),
            "INCLUDE_TLDS": os.getenv("INCLUDE_TLDS","org,gov,edu,int"),
        },
        "keys": {
            "openai": check_openai_key(),
            "brave": check_brave_key(),
        },
        "qdrant": check_qdrant(),
        "mongo": check_mongo(),
        "llm_ping": ping_llm(),
        "serp_test": test_serp(),
    }
    print(json.dumps(snap, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
