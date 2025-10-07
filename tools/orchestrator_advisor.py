# tools/orchestrator_advisor.py
# Orchestrator with ChatGPT for industry discovery and LLM advice

import os, json
from typing import List, Dict

# OpenAI for ChatGPT
try:
    from tools.llm_key_loader import ensure_openai_key
except:
    def ensure_openai_key(): ...
ensure_openai_key()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

LOG = bool(int(os.getenv("SUP_LOG","0")))
def log(*a):
    if LOG:
        print(*a, file=__import__("sys").stderr, flush=True)

# Config
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
CHATGPT_MODEL = os.getenv("CHATGPT_MODEL", "gpt-4o-mini")
CHATGPT_TEMP = float(os.getenv("CHATGPT_TEMPERATURE", "0.2"))

llm = ChatOpenAI(model=CHATGPT_MODEL, temperature=CHATGPT_TEMP, base_url=OPENAI_BASE_URL)

# Prompt for industry discovery
industry_prompt = ChatPromptTemplate.from_template("""
You are an AI Orchestrator. A user provided a website URL: {url}

Your tasks:
1. Analyze what industry/business this website belongs to.
2. Suggest 5-10 similar websites/companies in the same industry.
3. Generate 3-5 search queries to find more sites in this industry.
4. Provide advice on how to improve the website for better SEO/engagement.

Respond ONLY with JSON:
{{
  "industry": "string",
  "similar_sites": ["url1", "url2", ...],
  "search_queries": ["query1", "query2", ...],
  "advice": "string with improvement tips"
}}
""")

# Prompt for LLM learning advice
learning_prompt = ChatPromptTemplate.from_template("""
You are an AI Advisor. The local LLM has learned from {num_agents} site agents in the {industry} industry.

Based on the scraped data and agent interactions, provide advice on:
1. How the local LLM can improve its responses in this industry.
2. What additional data/knowledge it should learn.
3. Specific fine-tuning suggestions.

Respond ONLY with JSON:
{{
  "improvement_tips": ["tip1", "tip2", ...],
  "additional_data": ["data1", "data2", ...],
  "fine_tuning": "string with suggestions"
}}
""")

def analyze_website(url: str) -> Dict:
    """
    Use ChatGPT to analyze website and get industry info.
    """
    chain = industry_prompt | llm | JsonOutputParser()
    result = chain.invoke({"url": url})
    log(f"Industry analysis for {url}: {result}")
    return result

def get_learning_advice(industry: str, num_agents: int) -> Dict:
    """
    Get advice for LLM improvement.
    """
    chain = learning_prompt | llm | JsonOutputParser()
    result = chain.invoke({"industry": industry, "num_agents": num_agents})
    log(f"Learning advice: {result}")
    return result

def run_orchestrator(url: str) -> Dict:
    """
    Full orchestrator run: analyze site, get industry, suggest searches, get advice.
    """
    analysis = analyze_website(url)
    advice = get_learning_advice(analysis.get("industry", "unknown"), 1)  # start with 1

    return {
        "url": url,
        "analysis": analysis,
        "advice": advice
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m tools.orchestrator_advisor <url>")
        sys.exit(1)

    url = sys.argv[1]
    result = run_orchestrator(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
