"""
LangChain Agents Package - Sistem complet de agenți LangChain pentru platforma AI Agents

Structură:
- chains/ - Lanțuri predefinite (pipeline-uri Qwen + DeepSeek)
- tools/ - Tool-uri LangChain conectate la platformă
- agents/ - Definiții de agenți (SiteAgent, IndustryAgent, etc.)
- memory/ - Manageri de memorie LangChain
"""

from .llm_manager import (
    get_llm_manager,
    get_langchain_llm,
    get_qwen_llm,
    get_deepseek_llm,
    LLMManager
)

from .chain_registry import (
    get_chain_registry,
    register_chain,
    get_chain,
    ChainRegistry
)

from .agents import (
    SiteAgent,
    initialize_site_agent,
    GlobalOrchestrator,
    get_global_orchestrator,
    orchestrate_request
)
from .chains import (
    SiteAnalysisChain,
    IndustryStrategyChain,
    DecisionChain
)

__all__ = [
    # LLM Manager
    "get_llm_manager",
    "get_langchain_llm",
    "get_qwen_llm",
    "get_deepseek_llm",
    "LLMManager",
    # Chain Registry
    "get_chain_registry",
    "register_chain",
    "get_chain",
    "ChainRegistry",
    # Agents
    "SiteAgent",
    "initialize_site_agent",
    # Chains
    "SiteAnalysisChain",
    "IndustryStrategyChain",
    "DecisionChain",
]

