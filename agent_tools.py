#!/usr/bin/env python3
"""
Agent Tools - Acțiune
Implementează tools pentru căutare, fetch URL, calcul și alte acțiuni
"""

import asyncio
import aiohttp
import requests
import json
import logging
import re
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import math
import operator
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_huggingface import HuggingFaceEmbeddings
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

@dataclass
class ToolResult:
    """Rezultat al executării unui tool"""
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Dict = None
    execution_time: float = 0.0

class AgentTools:
    """Colecție de tools pentru agentul AI"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Setup embeddings pentru search
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Setup Qdrant
        self.qdrant_client = QdrantClient(
            host=config.get('qdrant_host', 'localhost'),
            port=config.get('qdrant_port', 9306)
        )
        
        # Setup MongoDB
        self.mongo_client = MongoClient(config.get('mongodb_uri', 'mongodb://localhost:9308'))
        self.db = self.mongo_client[config.get('mongodb_db', 'ai_agents_db')]
        
        # Session pentru requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SiteAI/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })
        
        # Configurații
        self.max_tool_steps = config.get('max_tool_steps', 3)
        self.similarity_threshold = config.get('similarity_threshold', 0.7)
        self.max_search_results = config.get('max_search_results', 5)
    
    async def search_index(self, query: str, agent_id: str, limit: int = None) -> ToolResult:
        """
        Tool: Căutare în indexul semantic al site-ului
        """
        start_time = datetime.now()
        
        try:
            if limit is None:
                limit = self.max_search_results
            
            # Generează embedding pentru query
            query_embedding = self.embeddings.embed_query(query)
            
            # Caută în Qdrant
            collection_name = f"agent_{agent_id}_content"
            
            search_results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=self.similarity_threshold,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="agent_id",
                            match=MatchValue(value=agent_id)
                        )
                    ]
                )
            )
            
            # Procesează rezultatele
            results = []
            for result in search_results:
                results.append({
                    'content': result.payload['content'],
                    'metadata': result.payload['metadata'],
                    'score': result.score,
                    'chunk_id': result.payload['chunk_id'],
                    'source_url': result.payload['metadata'].get('url', '')
                })
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ToolResult(
                success=True,
                result={
                    'query': query,
                    'results': results,
                    'total_found': len(results),
                    'search_time': execution_time
                },
                metadata={
                    'tool': 'search_index',
                    'agent_id': agent_id,
                    'query': query
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error in search_index: {e}")
            
            return ToolResult(
                success=False,
                result=None,
                error=str(e),
                metadata={'tool': 'search_index', 'agent_id': agent_id},
                execution_time=execution_time
            )
    
    async def fetch_url(self, url: str, agent_id: str) -> ToolResult:
        """
        Tool: Descarcă conținut de pe o pagină specifică (doar domeniul site-ului)
        """
        start_time = datetime.now()
        
        try:
            # Verifică dacă URL-ul este din domeniul site-ului
            agent_info = await self._get_agent_info(agent_id)
            if not agent_info:
                return ToolResult(
                    success=False,
                    result=None,
                    error="Agent not found",
                    metadata={'tool': 'fetch_url', 'url': url}
                )
            
            site_domain = urlparse(agent_info['site_url']).netloc
            url_domain = urlparse(url).netloc
            
            if url_domain != site_domain:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"URL must be from the same domain as the site ({site_domain})",
                    metadata={'tool': 'fetch_url', 'url': url}
                )
            
            # Descarcă conținutul
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parsează HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Elimină elemente nedorite
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # Extrage conținutul
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            # Extrage conținutul principal
            main_content = ""
            for selector in ['main', 'article', '.content', '.main-content', '.container', 'body']:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        text = element.get_text(separator=' ', strip=True)
                        if len(text) > len(main_content):
                            main_content = text
            
            # Curăță conținutul
            main_content = re.sub(r'\s+', ' ', main_content).strip()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ToolResult(
                success=True,
                result={
                    'url': url,
                    'title': title,
                    'content': main_content,
                    'content_length': len(main_content),
                    'status_code': response.status_code,
                    'fetch_time': execution_time
                },
                metadata={
                    'tool': 'fetch_url',
                    'url': url,
                    'agent_id': agent_id
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error in fetch_url: {e}")
            
            return ToolResult(
                success=False,
                result=None,
                error=str(e),
                metadata={'tool': 'fetch_url', 'url': url},
                execution_time=execution_time
            )
    
    async def calculate(self, expression: str) -> ToolResult:
        """
        Tool: Efectuează calcule simple în sandbox
        """
        start_time = datetime.now()
        
        try:
            # Lista de funcții permise
            allowed_functions = {
                'abs': abs,
                'round': round,
                'min': min,
                'max': max,
                'sum': sum,
                'pow': pow,
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'log': math.log,
                'log10': math.log10,
                'pi': math.pi,
                'e': math.e
            }
            
            # Operatori permisi
            allowed_operators = {
                '+': operator.add,
                '-': operator.sub,
                '*': operator.mul,
                '/': operator.truediv,
                '//': operator.floordiv,
                '%': operator.mod,
                '**': operator.pow,
                '^': operator.xor
            }
            
            # Verifică dacă expresia conține doar caractere sigure
            safe_chars = set('0123456789+-*/.()^%abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_ ')
            if not all(c in safe_chars for c in expression):
                return ToolResult(
                    success=False,
                    result=None,
                    error="Expression contains unsafe characters",
                    metadata={'tool': 'calculate', 'expression': expression}
                )
            
            # Înlocuiește ^ cu ** pentru putere
            expression = expression.replace('^', '**')
            
            # Evaluează expresia în mod sigur
            try:
                result = eval(expression, {"__builtins__": {}}, allowed_functions)
            except Exception as eval_error:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Calculation error: {str(eval_error)}",
                    metadata={'tool': 'calculate', 'expression': expression}
                )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ToolResult(
                success=True,
                result={
                    'expression': expression,
                    'result': result,
                    'result_type': type(result).__name__,
                    'calculation_time': execution_time
                },
                metadata={
                    'tool': 'calculate',
                    'expression': expression
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error in calculate: {e}")
            
            return ToolResult(
                success=False,
                result=None,
                error=str(e),
                metadata={'tool': 'calculate', 'expression': expression},
                execution_time=execution_time
            )
    
    async def get_agent_info(self, agent_id: str) -> ToolResult:
        """
        Tool: Obține informații despre agent
        """
        start_time = datetime.now()
        
        try:
            agent_info = await self._get_agent_info(agent_id)
            
            if not agent_info:
                return ToolResult(
                    success=False,
                    result=None,
                    error="Agent not found",
                    metadata={'tool': 'get_agent_info', 'agent_id': agent_id}
                )
            
            # Obține statistici
            stats = await self._get_agent_stats(agent_id)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ToolResult(
                success=True,
                result={
                    'agent_info': agent_info,
                    'stats': stats,
                    'info_time': execution_time
                },
                metadata={
                    'tool': 'get_agent_info',
                    'agent_id': agent_id
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error in get_agent_info: {e}")
            
            return ToolResult(
                success=False,
                result=None,
                error=str(e),
                metadata={'tool': 'get_agent_info', 'agent_id': agent_id},
                execution_time=execution_time
            )
    
    async def search_conversations(self, query: str, agent_id: str, limit: int = 5) -> ToolResult:
        """
        Tool: Caută în conversațiile anterioare
        """
        start_time = datetime.now()
        
        try:
            # Caută în conversații
            conversations = list(self.db.conversations.find({
                'agent_id': ObjectId(agent_id),
                '$or': [
                    {'user_question': {'$regex': query, '$options': 'i'}},
                    {'assistant_answer': {'$regex': query, '$options': 'i'}}
                ]
            }).sort('timestamp', -1).limit(limit))
            
            # Procesează rezultatele
            results = []
            for conv in conversations:
                results.append({
                    'question': conv.get('user_question', ''),
                    'answer': conv.get('assistant_answer', ''),
                    'confidence': conv.get('confidence', 0),
                    'timestamp': conv.get('timestamp', ''),
                    'sources': conv.get('sources', [])
                })
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ToolResult(
                success=True,
                result={
                    'query': query,
                    'conversations': results,
                    'total_found': len(results),
                    'search_time': execution_time
                },
                metadata={
                    'tool': 'search_conversations',
                    'agent_id': agent_id,
                    'query': query
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error in search_conversations: {e}")
            
            return ToolResult(
                success=False,
                result=None,
                error=str(e),
                metadata={'tool': 'search_conversations', 'agent_id': agent_id},
                execution_time=execution_time
            )
    
    async def _get_agent_info(self, agent_id: str) -> Optional[Dict]:
        """Helper: Obține informații despre agent"""
        try:
            agent = self.db.agents.find_one({"_id": ObjectId(agent_id)})
            if agent:
                return {
                    'id': str(agent['_id']),
                    'name': agent.get('name', ''),
                    'domain': agent.get('domain', ''),
                    'site_url': agent.get('site_url', ''),
                    'status': agent.get('status', ''),
                    'created_at': agent.get('createdAt', ''),
                    'updated_at': agent.get('updatedAt', '')
                }
        except Exception as e:
            logger.warning(f"Could not get agent info: {e}")
        
        return None
    
    async def _get_agent_stats(self, agent_id: str) -> Dict:
        """Helper: Obține statistici despre agent"""
        try:
            # Numărul de conversații
            conversations_count = self.db.conversations.count_documents({
                'agent_id': ObjectId(agent_id)
            })
            
            # Numărul de chunks
            chunks_count = self.db.site_chunks.count_documents({
                'agent_id': ObjectId(agent_id)
            })
            
            # Numărul de pagini
            pages_count = self.db.site_content.count_documents({
                'agent_id': ObjectId(agent_id)
            })
            
            return {
                'conversations_count': conversations_count,
                'chunks_count': chunks_count,
                'pages_count': pages_count,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting agent stats: {e}")
            return {}
    
    async def execute_tool_chain(self, tools_chain: List[Dict], agent_id: str) -> List[ToolResult]:
        """
        Execută o secvență de tools cu guardrails
        """
        results = []
        
        if len(tools_chain) > self.max_tool_steps:
            logger.warning(f"Tool chain too long ({len(tools_chain)}), limiting to {self.max_tool_steps}")
            tools_chain = tools_chain[:self.max_tool_steps]
        
        for i, tool_call in enumerate(tools_chain):
            tool_name = tool_call.get('tool')
            tool_args = tool_call.get('args', {})
            
            logger.info(f"Executing tool {i+1}/{len(tools_chain)}: {tool_name}")
            
            try:
                if tool_name == 'search_index':
                    result = await self.search_index(
                        tool_args.get('query', ''),
                        agent_id,
                        tool_args.get('limit')
                    )
                elif tool_name == 'fetch_url':
                    result = await self.fetch_url(
                        tool_args.get('url', ''),
                        agent_id
                    )
                elif tool_name == 'calculate':
                    result = await self.calculate(
                        tool_args.get('expression', '')
                    )
                elif tool_name == 'get_agent_info':
                    result = await self.get_agent_info(agent_id)
                elif tool_name == 'search_conversations':
                    result = await self.search_conversations(
                        tool_args.get('query', ''),
                        agent_id,
                        tool_args.get('limit', 5)
                    )
                else:
                    result = ToolResult(
                        success=False,
                        result=None,
                        error=f"Unknown tool: {tool_name}",
                        metadata={'tool': tool_name}
                    )
                
                results.append(result)
                
                # Dacă tool-ul a eșuat, oprește execuția
                if not result.success:
                    logger.warning(f"Tool {tool_name} failed, stopping chain")
                    break
                    
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                results.append(ToolResult(
                    success=False,
                    result=None,
                    error=str(e),
                    metadata={'tool': tool_name}
                ))
                break
        
        return results

# Funcție pentru a obține tools pentru agent
def get_tools_for_agent(agent_id: str) -> List:
    """
    Returnează lista de tools disponibile pentru agent
    """
    # Pentru moment, returnează o listă goală
    # În viitor, aici se poate adăuga logica pentru a returna tools specifice agentului
    return []

# Funcție helper pentru a rula tools
async def run_agent_tools(tool_name: str, tool_args: Dict, agent_id: str, config: Dict = None) -> ToolResult:
    """Funcție helper pentru a rula un tool"""
    if config is None:
        config = {
            'qdrant_url': 'http://localhost:9306',
            'mongodb_uri': 'mongodb://localhost:9308',
            'mongodb_db': 'ai_agents_db',
            'max_tool_steps': 3,
            'similarity_threshold': 0.7,
            'max_search_results': 5
        }
    
    tools = AgentTools(config)
    
    if tool_name == 'search_index':
        return await tools.search_index(tool_args.get('query', ''), agent_id, tool_args.get('limit'))
    elif tool_name == 'fetch_url':
        return await tools.fetch_url(tool_args.get('url', ''), agent_id)
    elif tool_name == 'calculate':
        return await tools.calculate(tool_args.get('expression', ''))
    elif tool_name == 'get_agent_info':
        return await tools.get_agent_info(agent_id)
    elif tool_name == 'search_conversations':
        return await tools.search_conversations(tool_args.get('query', ''), agent_id, tool_args.get('limit', 5))
    else:
        return ToolResult(
            success=False,
            result=None,
            error=f"Unknown tool: {tool_name}",
            metadata={'tool': tool_name}
        )

if __name__ == "__main__":
    # Test
    import asyncio
    
    async def test():
        # Test search_index
        result = await run_agent_tools(
            'search_index',
            {'query': 'servicii', 'limit': 3},
            '68f683f6f86c99d4d127ea81'
        )
        print(f"Search result: {result.success}")
        if result.success:
            print(f"Found {result.result['total_found']} results")
        
        # Test calculate
        result = await run_agent_tools(
            'calculate',
            {'expression': '2 + 2 * 3'},
            '68f683f6f86c99d4d127ea81'
        )
        print(f"Calculate result: {result.success}")
        if result.success:
            print(f"Result: {result.result['result']}")
    
    asyncio.run(test())