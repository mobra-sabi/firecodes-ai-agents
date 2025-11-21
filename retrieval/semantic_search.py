from __future__ import annotations
import re
from langchain_ollama import OllamaEmbeddings
import os
from typing import List, Dict, Tuple

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL","nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434")
def get_embedder():
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)


from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct
from database.qdrant_vectorizer import QdrantVectorizer
from config.database_config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION

from .rerank import Reranker

TOP_K_VECTOR = int(os.getenv("TOP_K_VECTOR", "50"))   # candidați din vector search
TOP_K_FINAL  = int(os.getenv("TOP_K_FINAL",  "8"))    # returnați după rerank

class SemanticSearcher:
    def __init__(self):
        self.qv = QdrantVectorizer()
        self.qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT,)
        self.col = QDRANT_COLLECTION
        self.reranker = Reranker()

    def search(self, query: str, domain: str | None = None) -> List[Dict]:
        # 1) embedd pentru query
        qv = self.qv.embedder.embed_text(query)

        # 2) filtrare opțională pe domeniu
        qfilter = None
        if domain:
            qfilter = Filter(must=[FieldCondition(key="domain", match=MatchValue(value=domain))])

        # 3) vector search (rapid)
        hits = self.qc.search(
            collection_name=self.col, query_vector=qv, limit=TOP_K_VECTOR, query_filter=qfilter
        )

        # 4) pregătire pt rerank
        doc_pairs: List[Tuple[str,str]] = []
        payloads: Dict[str, Dict] = {}
        for h in hits:
            pid = str(h.id)
            url = (h.payload or {}).get("url") or ""
            title = (h.payload or {}).get("title") or ""
            text = f"{title}\n{url}\n"
            # nu avem text complet în payload, dar titlu+url ajută; dacă vrei, poți adăuga text în payload la ingest
            doc_pairs.append((pid, text))
            payloads[pid] = {"url": url, "title": title, "score_vec": float(h.score)}

        # 5) rerank (precis)
        ranked = self.reranker.rerank(query, doc_pairs)[:TOP_K_FINAL]

        # 6) combină
        out = []
        for pid, text, score_cross in ranked:
            meta = payloads.get(pid, {})
            out.append({
                "id": pid,
                "title": meta.get("title",""),
                "url": meta.get("url",""),
                "score_vec": meta.get("score_vec", 0.0),
                "score_cross": score_cross,
            })
        return out
