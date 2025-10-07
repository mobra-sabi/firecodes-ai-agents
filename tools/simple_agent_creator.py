# tools/simple_agent_creator.py
# Simple site agent creator - no graph, just scrape and create QA agent

import os, json, datetime
from urllib.parse import urlsplit

# OpenAI
try:
    from tools.llm_key_loader import ensure_openai_key
except:
    def ensure_openai_key(): ...
ensure_openai_key()

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain.chains import RetrievalQA
from pymongo import MongoClient
import qdrant_client
from trafilatura import fetch_url, extract
from tools.orchestrator_advisor import analyze_website

# Import advanced scraper system
try:
    import os
    import sys
    # Add project root to path for imports
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    from adapters.scraper_adapter import smart_fetch
    USE_ADVANCED_SCRAPER = True
except ImportError as e:
    print(f"Warning: Could not import advanced scraper: {e}")
    USE_ADVANCED_SCRAPER = False

LOG = bool(int(os.getenv("SUP_LOG","0")))
def log(*a):
    if LOG:
        print(*a, file=__import__("sys").stderr, flush=True)

# Config
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMP = float(os.getenv("LLM_TEMPERATURE", "0.2"))

MONGO_URL = os.getenv("MONGODB_URI","mongodb://127.0.0.1:27017")
DB_NAME = os.getenv("MONGO_DB","ai_agents_db")

QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "").strip() or None

llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMP, base_url=OPENAI_BASE_URL)
embeddings = OpenAIEmbeddings()
mc = MongoClient(MONGO_URL)
db = mc[DB_NAME]
qc = qdrant_client.QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

def norm_domain(u: str) -> str:
    try:
        d = urlsplit(u).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except:
        return ""

def create_agent(url: str) -> dict:
    domain = norm_domain(url)
    if not domain:
        return {"ok": False, "error": "Invalid URL"}

    log(f"Creating agent for {domain}")

    # Scrape using advanced scraper system
    if USE_ADVANCED_SCRAPER:
        log("Using advanced scraper system")
        scrape_result = smart_fetch(url)
        if not scrape_result.get("ok"):
            return {"ok": False, "error": "Advanced scraping failed"}
        
        text = scrape_result.get("text", "")
        title = scrape_result.get("title", "")
        if not text:
            return {"ok": False, "error": "No text extracted from advanced scraper"}
    else:
        log("Using fallback trafilatura scraper")
        # Fallback to trafilatura
        html = fetch_url(url)
        if not html:
            return {"ok": False, "error": "Fetch failed"}
        text = extract(html, include_comments=False, include_tables=True, prune_xpath=['//script', '//style'])
        title = ""
        if not text:
            return {"ok": False, "error": "No text extracted"}

    # Store in Mongo
    doc = {
        "url": url,
        "domain": domain,
        "content": text[:20000],  # Increased limit for better content
        "title": title,
        "created_at": datetime.datetime.now().isoformat(),
        "scraper_used": "advanced" if USE_ADVANCED_SCRAPER else "trafilatura"
    }
    db.site_content.update_one({"url": url}, {"$set": doc}, upsert=True)

    # Get industry analysis from ChatGPT
    analysis = analyze_website(url)

    # Agent in Mongo with analysis
    agent_doc = {
        "domain": domain,
        "url": url,
        "created_at": datetime.datetime.now().isoformat(),
        "status": "active",
        "industry": analysis.get("industry"),
        "similar_sites": analysis.get("similar_sites", []),
        "search_queries": analysis.get("search_queries", []),
        "advice": analysis.get("advice")
    }
    db.site_agents.update_one({"domain": domain}, {"$set": agent_doc}, upsert=True)
    agent = db.site_agents.find_one({"domain": domain})

    # Vector store
    collection_name = f"agent_{domain.replace('.', '_')}"
    try:
        qc.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_client.http.models.VectorParams(size=1536, distance=qdrant_client.http.models.Distance.COSINE)
        )
    except:
        pass
    vectorstore = Qdrant(client=qc, collection_name=collection_name, embeddings=embeddings)
    vectorstore.add_texts([text], metadatas=[{"url": url, "domain": domain}])

    return {"ok": True, "agent_id": str(agent["_id"]), "domain": domain, "analysis": analysis}

from bson import ObjectId

def query_agent(agent_id: str, question: str) -> str:
    try:
        agent = db.site_agents.find_one({"_id": ObjectId(agent_id)})
    except:
        return "Invalid agent ID"
    if not agent:
        return "Agent not found"
    domain = agent["domain"]
    collection_name = f"agent_{domain.replace('.', '_')}"
    vectorstore = Qdrant(client=qc, collection_name=collection_name, embeddings=embeddings)
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=vectorstore.as_retriever())
    return qa.run(question)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m tools.simple_agent_creator <url> [question]")
        sys.exit(1)
    url = sys.argv[1]
    if len(sys.argv) > 2:
        question = " ".join(sys.argv[2:])
        domain = norm_domain(url)
        log(f"Querying domain: {domain}")
        agent = db.site_agents.find_one({"domain": domain})
        log(f"Agent found: {agent}")
        if agent:
            answer = query_agent(str(agent["_id"]), question)
            print(json.dumps({"answer": answer}, ensure_ascii=False))
        else:
            print(json.dumps({"error": "Agent not found"}))
    else:
        result = create_agent(url)
        print(json.dumps(result, ensure_ascii=False))
