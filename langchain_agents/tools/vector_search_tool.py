"""
Vector Search Tool - Tool LangChain pentru căutare semantică în Qdrant

Integrează Qdrant prin QdrantVectorStore din LangChain pentru RAG.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# LangChain imports
try:
    from langchain_core.tools import tool
    from langchain_community.vectorstores import Qdrant as LangchainQdrant
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    try:
        from langchain.tools import tool
        from langchain.vectorstores import Qdrant as LangchainQdrant
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        tool = None
        LangchainQdrant = None
        HuggingFaceEmbeddings = None

from qdrant_client import QdrantClient
import os

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


class VectorSearchTool:
    """
    Tool pentru căutare semantică în Qdrant
    """
    
    def __init__(self, agent_id: str, collection_name: Optional[str] = None):
        self.agent_id = agent_id
        self.collection_name = collection_name or f"agent_{agent_id}"
        
        # Embeddings
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-large-en-v1.5",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize embeddings: {e}")
            self.embeddings = None
        
        # Qdrant Vector Store
        try:
            self.vectorstore = LangchainQdrant(
                client=QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY),
                collection_name=self.collection_name,
                embeddings=self.embeddings
            )
            logger.info(f"✅ VectorSearchTool initialized for agent {agent_id}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Qdrant vectorstore: {e}")
            self.vectorstore = None
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Caută în vectori similari
        
        Args:
            query: Query de căutare
            k: Număr de rezultate
        
        Returns:
            Lista de documente similare
        """
        if not self.vectorstore:
            logger.warning("⚠️ Vectorstore not available")
            return []
        
        try:
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            documents = []
            for doc, score in results:
                documents.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ Error searching vectors: {e}")
            return []
    
    def search_relevant(self, query: str, k: int = 5) -> str:
        """
        Caută și returnează text relevant pentru context
        
        Args:
            query: Query de căutare
            k: Număr de rezultate
        
        Returns:
            Text concatenat cu rezultatele relevante
        """
        documents = self.search(query, k=k)
        
        if not documents:
            return "Nu s-au găsit informații relevante."
        
        result_text = f"Informații relevante pentru '{query}':\n\n"
        for i, doc in enumerate(documents, 1):
            result_text += f"{i}. {doc['content'][:500]}...\n"
            result_text += f"   (Relevanță: {1 - doc['score']:.2%})\n\n"
        
        return result_text


def create_vector_search_tool(agent_id: str) -> Optional[VectorSearchTool]:
    """
    Creează un tool de căutare vectorială pentru un agent
    
    Args:
        agent_id: ID-ul agentului
    
    Returns:
        VectorSearchTool sau None
    """
    try:
        return VectorSearchTool(agent_id)
    except Exception as e:
        logger.error(f"❌ Failed to create VectorSearchTool: {e}")
        return None


# Tool LangChain decorator (dacă este disponibil)
if tool:
    @tool
    def search_site_content(query: str, agent_id: str) -> str:
        """
        Caută informații relevante în conținutul site-ului agentului.
        
        Args:
            query: Întrebarea sau termenul de căutare
            agent_id: ID-ul agentului
        
        Returns:
            Text cu informații relevante
        """
        search_tool = create_vector_search_tool(agent_id)
        if not search_tool:
            return "Tool de căutare nu este disponibil."
        
        return search_tool.search_relevant(query, k=5)

