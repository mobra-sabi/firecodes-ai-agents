from __future__ import annotations
# tools/admin_discovery.py

import os
import re
import time
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from dotenv import load_dotenv
from pymongo import MongoClient

# Refolosim utilități/LLM/embeddings din modulul existent:
from tools.site_agent_creator import (
    embed_texts,            # embeddings (OpenAI/Ollama conform setup-ului tău)
    chat_llm,               # LLM routing (OpenAI/Ollama conform .env)
    normalize_domain,       # normalizează domenii
    fetch_html,             # HTTP GET simplu
    extract_text,           # extrage text din HTML
    create_site_agent,      # creează agent (ingest headless)
)

# ---------- Environment ----------
load_dotenv(dotenv_path=os.path.join(os.path.expanduser("~"), "ai_agents", ".env"))

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:9308")
QDRANT_URL  = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333")

# Opțional: SERPAPI (preferat) – altfel DuckDuckGo fallback
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "").strip()

mongo = MongoClient(MONGODB_URI)
db = mongo.get_database("site_agents")
col_agents = db.get_collection("site_agents")
col_pages  = db.get_collection("site_pages")


# ---------- Helpers ----------
def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    sa = sum(x*x for x in a) ** 0.5
    sb = sum(x*x for x in b) ** 0.5
    if sa == 0 or sb == 0:
        return 0.0
    return sum(x*y for x, y in zip(a, b)) / (sa * sb)


def _simple_semantic_similarity(a_text: str, b_text: str) -> float:
    """Heuristică fără LLM: Jaccard pe cuvinte semnificative.
    Evită orice apel la API/embeddings.
    """
    import re
    tokenize = lambda s: [w for w in re.findall(r"[a-zăâîșțA-ZĂÂÎȘȚ0-9_-]+", (s or "").lower()) if len(w) > 3]
    sa = set(tokenize(a_text))
    sb = set(tokenize(b_text))
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    uni = len(sa | sb)
    return inter / uni if uni else 0.0

def _ddg_search(query: str, limit: int = 10) -> List[Dict[str, str]]:
    url = "https://duckduckgo.com/html/"
    try:
        r = requests.get(url, params={"q": query}, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        out: List[Dict[str, str]] = []
        # DuckDuckGo HTML poate varia; selecția de mai jos funcționează des
        for a in soup.select("a.result__a")[:limit]:
            href = a.get("href")
            if href and href.startswith("http"):
                out.append({"url": href, "title": a.get_text(" ", strip=True)})
        return out
    except Exception:
        return []


def _serpapi_search(query: str, limit: int = 10) -> List[Dict[str, str]]:
    if not SERPAPI_KEY:
        return []
    try:
        r = requests.get(
            "https://serpapi.com/search.json",
            params={"engine": "google", "q": query, "num": limit, "api_key": SERPAPI_KEY},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        org = data.get("organic_results", []) or []
        out: List[Dict[str, str]] = []
        for it in org[:limit]:
            link = it.get("link")
            title = it.get("title") or ""
            if link and link.startswith("http"):
                out.append({"url": link, "title": title})
        return out
    except Exception:
        return []


def web_search(query: str, limit: int = 10) -> List[Dict[str, str]]:
    # Preferă SERPAPI dacă există cheie; altfel DDG HTML fallback
    res = _serpapi_search(query, limit)
    if res:
        return res
    return _ddg_search(query, limit)


def generate_queries(seed_text: str, seed_domain: str, count: int = 8) -> List[str]:
    """Generează interogări determinist, FĂRĂ apel LLM (robust fără chei)."""
    base = (seed_domain or "").replace("www.", "").replace(".ro", "").replace(".com", "")
    base_kw = [x for x in re.split(r"[-_\.]+", base) if x]
    defaults = [
        f"{seed_domain} competitori" if seed_domain else "companii competitoare romania",
        "preturi servicii comparatie site romania",
        "portofoliu proiecte [industrie] romania",
        "certificari autorizatii firma [industrie] romania",
        "verificare mentenanta servicii [industrie]",
        "instalare mentenanta echipamente [industrie]",
        "distribuitori furnizori [industrie] romania",
        "recenzii clienti [industrie] romania",
    ]
    if base_kw:
        defaults = [q.replace("[industrie]", " ".join(base_kw)) for q in defaults]
    else:
        defaults = [q.replace("[industrie]", "industrie") for q in defaults]
    return defaults[:count]


def evaluate_candidate(seed_text: str, candidate_url: str) -> Dict:
    # verifică reachability + extrage text homepage
    html = fetch_html(candidate_url, timeout=15)
    if not html:
        return {"url": candidate_url, "ok": False, "reason": "no_html"}
    text = extract_text(html, candidate_url)
    tl = len(text or "")
    if tl < 300:
        return {"url": candidate_url, "ok": False, "reason": "too_short", "homepage_text_len": tl}

    # scor semantic fără embeddings (fără dependență de chei LLM)
    sim = _simple_semantic_similarity(seed_text, text)

    return {
        "url": candidate_url,
        "ok": True,
        "score": round(sim, 4),
        "reason": "ok",
        "homepage_text_len": tl,
    }


# ---------- Public API ----------
def discover_competitors(agent_id: str, limit: int = 12, queries: Optional[List[str]] = None) -> Dict:
    # 1) seed agent
    # Încearcă să convertească agent_id la ObjectId dacă este posibil
    from bson import ObjectId
    try:
        agent = col_agents.find_one({"_id": ObjectId(agent_id)})
    except Exception:
        agent = None
    
    # Dacă nu s-a găsit cu ObjectId, încearcă fără conversie sau cu domain
    if not agent:
        agent = col_agents.find_one({"_id": agent_id}) or col_agents.find_one({"domain": agent_id})
    
    # Dacă încă nu s-a găsit, încearcă în baza de date corectă (ai_agents_db)
    if not agent:
        try:
            from config.database_config import MONGODB_URI, MONGODB_DATABASE
            mongo_correct = MongoClient(MONGODB_URI)
            db_correct = mongo_correct[MONGODB_DATABASE]
            col_agents_correct = db_correct.site_agents
            try:
                agent = col_agents_correct.find_one({"_id": ObjectId(agent_id)})
            except Exception:
                agent = col_agents_correct.find_one({"_id": agent_id}) or col_agents_correct.find_one({"domain": agent_id})
        except Exception as e:
            pass
    
    if not agent:
        return {"ok": False, "error": "agent_not_found"}
    domain   = agent.get("domain") or ""
    home_url = agent.get("home_url") or agent.get("site_url") or (f"https://{domain}" if domain else "")

    # 2) seed text
    # Încearcă să găsească seed_text din baza de date corectă
    seed_text = ""
    
    # Încearcă din col_pages (baza de date veche)
    seed_page = col_pages.find_one({"url": home_url, "domain": domain}) if home_url else None
    if seed_page:
        seed_text = (seed_page or {}).get("text") or ""
    
    # Dacă nu s-a găsit, încearcă din baza de date corectă (site_content)
    if not seed_text:
        try:
            from config.database_config import MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION
            mongo_correct = MongoClient(MONGODB_URI)
            db_correct = mongo_correct[MONGODB_DATABASE]
            site_content_col = db_correct[MONGODB_COLLECTION]
            
            # Caută conținut pentru agent
            content_docs = site_content_col.find({"agent_id": ObjectId(agent_id)}).limit(5)
            content_parts = []
            for doc in content_docs:
                if doc.get("content"):
                    content_parts.append(doc["content"][:1000])
            if content_parts:
                seed_text = " ".join(content_parts)[:3000]
        except Exception:
            pass
    
    # Dacă încă nu s-a găsit, încearcă să descarce direct de pe site
    if not seed_text and home_url:
        html = fetch_html(home_url, timeout=15)
        if html:
            seed_text = extract_text(html, home_url)

    if len(seed_text) < 300:
        return {"ok": False, "error": "seed_text_too_short"}

    # 3) queries
    qrs = queries or generate_queries(seed_text, domain, count=min(8, limit))

    # 4) web search -> candidați
    seen_hosts, candidates = set(), []
    for q in qrs:
        results = web_search(q, limit=10)
        for r in results:
            url = r.get("url", "")
            if not url.startswith("http"):
                continue
            host = normalize_domain(url)
            if not host or host == domain:
                continue
            if host in seen_hosts:
                continue
            seen_hosts.add(host)
            candidates.append(url)
        if len(candidates) >= (limit * 3):
            break

    # 5) evaluare
    evaluated = []
    for u in candidates:
        try:
            info = evaluate_candidate(seed_text, u)
            if info.get("ok"):
                evaluated.append(info)
        except Exception:
            continue
        if len(evaluated) >= (limit * 2):
            break

    # 6) ordonare și topN
    evaluated.sort(key=lambda x: x.get("score", 0), reverse=True)
    top = evaluated[:limit]
    return {"ok": True, "agent_id": str(agent.get("_id")), "domain": domain, "candidates": top, "queries": qrs}


def ingest_urls(urls: List[str], max_pages: int = 10) -> Dict:
    out = []
    for u in urls:
        try:
            res = create_site_agent(u, max_pages=max_pages, api_key=None)
            out.append({"url": u, "ok": True, "agent_id": res.get("agent_id")})
        except Exception as e:
            out.append({"url": u, "ok": False, "error": str(e)})
        time.sleep(0.1)
    return {"ok": True, "results": out}
