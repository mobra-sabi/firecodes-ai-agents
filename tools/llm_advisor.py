import re
# tools/llm_advisor.py
# Use existing vLLM servers to generate business advice from agent data

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL","nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434")
def get_embedder():
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)


import os, json, requests
from langchain_ollama import OllamaEmbeddings
from pymongo import MongoClient
from qdrant_client import QdrantClient

LOG = bool(int(os.getenv("SUP_LOG","0")))
def log(*a):
    if LOG:
        print(*a, file=__import__("sys").stderr, flush=True)

# Config
MONGO_URL = os.getenv("MONGODB_URI","mongodb://127.0.0.1:27017")
DB_NAME = os.getenv("MONGO_DB","ai_agents_db")
QDRANT_URL = os.getenv("QDRANT_URL","http://127.0.0.1:6333")
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:9201")  # Use existing vLLM server

def get_relevant_content(domain: str, query: str, limit=5) -> str:
    """
    Get relevant content from agent's vector store.
    """
    qc = QdrantClient(url=QDRANT_URL,)
    mc = MongoClient(MONGO_URL)
    db = mc[DB_NAME]

    # Find agent for domain
    agent = db.agents.find_one({"domain": domain})
    if not agent:
        return "No agent found for this domain."

    collection_name = f"agent_{agent['_id']}"

    # Search vector store
    results = qc.search(
        collection_name=collection_name,
        query_vector=qc.get_collection(collection_name).vectors_config.config.params.size * [0.0],  # Dummy vector, use text search
        limit=limit,
        with_payload=True
    )

    # For now, just get content from DB
    docs = list(db.site_content.find({"domain": domain}, {"content": 1}).limit(limit))
    content = "\n".join([doc.get("content", "")[:1000] for doc in docs])

    return content[:4000]  # Limit for LLM

def generate_advice(domain: str, advice_type: str = "general") -> str:
    """
    Generate business advice using existing vLLM server.
    """
    log(f"Generating {advice_type} advice for {domain}")

    # Get relevant content
    content = get_relevant_content(domain, f"business advice for {domain}")

    if not content:
        return "No content available for advice generation."

    # Craft prompt based on advice type
    prompts = {
        "general": f"Based on this website content, provide 3 specific business improvement suggestions:\n\n{content}",
        "marketing": f"Analyze this website's marketing potential and suggest digital marketing strategies:\n\n{content}",
        "technical": f"Review this website's technical aspects and suggest improvements:\n\n{content}",
        "content": f"Evaluate the content quality and suggest content optimization strategies:\n\n{content}"
    }

    prompt = prompts.get(advice_type, prompts["general"])

    # Call vLLM API
    response = requests.post(
        f"{VLLM_BASE_URL}/v1/chat/completions",
        json={
            "model": "Qwen2.5-7B-Instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.7
        },
        timeout=30
    )

    if response.status_code == 200:
        result = response.json()
        advice = result["choices"][0]["message"]["content"]
        log(f"Generated advice: {advice[:200]}...")
        return advice
    else:
        log(f"vLLM API error: {response.status_code} - {response.text}")
        return "Failed to generate advice."

def get_all_domains() -> list:
    """
    Get all domains with agents.
    """
    mc = MongoClient(MONGO_URL)
    db = mc[DB_NAME]
    agents = db.agents.find({}, {"domain": 1})
    return [agent["domain"] for agent in agents]

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m tools.llm_advisor <domain> [advice_type]")
        sys.exit(1)

    domain = sys.argv[1]
    advice_type = sys.argv[2] if len(sys.argv) > 2 else "general"

    advice = generate_advice(domain, advice_type)
    print(advice)
