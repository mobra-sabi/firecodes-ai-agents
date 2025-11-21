#!/usr/bin/env python3
"""
Modul pentru îmbogățirea contextului DeepSeek cu vectori din Qdrant
Permite DeepSeek să înțeleagă profund industria prin search semantic
"""

import torch
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class QdrantContextEnhancer:
    """Extrage context semantic din Qdrant pentru DeepSeek"""
    
    def __init__(self, qdrant_url: str = "http://127.0.0.1:9306"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(
            'sentence-transformers/all-MiniLM-L6-v2', 
            device=self.device
        )
        self.qdrant = QdrantClient(url=qdrant_url)
        logger.info(f"QdrantContextEnhancer initialized on {self.device}")
    
    def get_context_for_query(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Extrage context relevant din Qdrant pentru o query
        
        Args:
            query: Întrebarea sau tema de analizat
            collection_name: Colecția Qdrant (ex: agent_xxx)
            top_k: Câte rezultate să returneze
            
        Returns:
            Listă de dicționare cu text și score
        """
        try:
            # Generate query embedding
            query_vector = self.model.encode(query, convert_to_numpy=True)
            
            # Search in Qdrant
            results = self.qdrant.search(
                collection_name=collection_name,
                query_vector=query_vector.tolist(),
                limit=top_k
            )
            
            # Extract contexts
            contexts = []
            for hit in results:
                contexts.append({
                    "text": hit.payload.get("text", ""),
                    "score": float(hit.score),
                    "url": hit.payload.get("url", ""),
                    "chunk_index": hit.payload.get("chunk_index", 0)
                })
            
            logger.info(f"Found {len(contexts)} relevant contexts for query: {query[:50]}...")
            return contexts
            
        except Exception as e:
            logger.error(f"Error getting context from Qdrant: {e}")
            return []
    
    def get_industry_context(
        self,
        agent_id: str,
        topics: List[str],
        top_k_per_topic: int = 3
    ) -> Dict[str, List[Dict]]:
        """
        Extrage context pentru multiple topice din industrie
        Perfect pentru strategii competitive
        
        Args:
            agent_id: ID-ul agentului (colecția va fi agent_{id})
            topics: Listă de topice (ex: ["protecție la foc", "servicii", "concurență"])
            top_k_per_topic: Câte rezultate per topic
            
        Returns:
            Dict cu context per topic
        """
        collection_name = f"agent_{agent_id}"
        
        industry_context = {}
        for topic in topics:
            contexts = self.get_context_for_query(
                query=topic,
                collection_name=collection_name,
                top_k=top_k_per_topic
            )
            industry_context[topic] = contexts
        
        return industry_context
    
    def build_enriched_prompt_for_deepseek(
        self,
        base_query: str,
        contexts: List[Dict],
        max_context_length: int = 2000
    ) -> str:
        """
        Construiește un prompt îmbogățit cu context din Qdrant pentru DeepSeek
        
        Args:
            base_query: Întrebarea/cererea originală
            contexts: Liste de contexte din Qdrant
            max_context_length: Limită caractere pentru context
            
        Returns:
            Prompt îmbogățit gata pentru DeepSeek
        """
        # Sort by score (descending)
        sorted_contexts = sorted(contexts, key=lambda x: x['score'], reverse=True)
        
        # Build context string
        context_parts = []
        current_length = 0
        
        for i, ctx in enumerate(sorted_contexts, 1):
            text = ctx['text']
            score = ctx['score']
            
            # Add context if within limit
            if current_length + len(text) <= max_context_length:
                context_parts.append(
                    f"[Context {i} - Relevance: {score:.3f}]\n{text}\n"
                )
                current_length += len(text)
            else:
                break
        
        # Build final prompt
        enriched_prompt = f"""=== CONTEXT DIN BAZA DE DATE VECTORIALĂ ===
(Informații extrase semantic din {len(context_parts)} surse relevante)

{''.join(context_parts)}

=== CEREREA TA ===
{base_query}

=== INSTRUCȚIUNI ===
Te rog să analizezi contextul de mai sus și să răspunzi la cerere bazându-te EXCLUSIV pe informațiile concrete din context. 
Fii specific și menționează detalii relevante din context.
"""
        
        return enriched_prompt
    
    def get_full_industry_analysis_context(
        self,
        agent_id: str,
        analysis_focus: str = "strategia competitivă"
    ) -> str:
        """
        Extrage un context complet pentru analiza industriei
        Ideal pentru strategii competitive cu DeepSeek
        
        Args:
            agent_id: ID-ul agentului
            analysis_focus: Focusul analizei
            
        Returns:
            Context complet formatat pentru DeepSeek
        """
        # Topics relevante pentru strategii competitive
        topics = [
            "servicii și produse",
            "avantaje competitive",
            "puncte forte",
            "clienți și piață țintă",
            "experiență și expertiză",
            "certificări și calitate"
        ]
        
        industry_context = self.get_industry_context(
            agent_id=agent_id,
            topics=topics,
            top_k_per_topic=2
        )
        
        # Flatten all contexts
        all_contexts = []
        for topic, contexts in industry_context.items():
            for ctx in contexts:
                ctx['topic'] = topic
                all_contexts.append(ctx)
        
        # Build enriched prompt
        prompt = self.build_enriched_prompt_for_deepseek(
            base_query=f"Analizează {analysis_focus} bazat pe contextul complet al companiei",
            contexts=all_contexts,
            max_context_length=4000  # Mai mult pentru analiză completă
        )
        
        return prompt


# Singleton instance
_enhancer_instance: Optional[QdrantContextEnhancer] = None

def get_context_enhancer() -> QdrantContextEnhancer:
    """Get or create singleton instance"""
    global _enhancer_instance
    if _enhancer_instance is None:
        _enhancer_instance = QdrantContextEnhancer()
    return _enhancer_instance
