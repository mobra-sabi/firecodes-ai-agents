from __future__ import annotations
import os
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from pymongo import MongoClient
from pymongo.errors import OperationFailure

# Refolosim embedderul din vectorizer și configul existent
from database.qdrant_vectorizer import EmbeddingProvider
try:
    from config.database_config import (
        QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION,
        MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION
    )
except Exception:
    QDRANT_HOST = os.getenv("QDRANT_HOST", "127.0.0.1")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "site_embeddings")
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ai_agents_db")
    MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "site_content")


def _minmax(xs: List[float]) -> List[float]:
    if not xs:
        return []
    lo, hi = min(xs), max(xs)
    if hi <= lo:
        return [1.0 for _ in xs]
    return [(x - lo) / (hi - lo) for x in xs]


class SemanticSearcher:
    """Căutare vectorială în Qdrant + căutare hibridă (Qdrant + Mongo $text)."""

    def __init__(self):
        self.qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.collection = QDRANT_COLLECTION

        self.embedder = EmbeddingProvider(
            backend=os.getenv("EMBED_BACKEND", "ollama"),
            ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11436"),
            ollama_model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
            st_model=os.getenv("ST_EMBED_MODEL", "BAAI/bge-base-en-v1.5"),
            st_device=os.getenv("ST_DEVICE", "cpu"),
            embed_dim=int(os.getenv("EMBED_DIM", "768")),
        )
        self.vec_dim = self.embedder.dimension

        self.mc = MongoClient(MONGODB_URI)
        self.mdb = self.mc[MONGODB_DATABASE]
        self.mcol = self.mdb[MONGODB_COLLECTION]

    # ------------------- VECTOR -------------------

    def _build_filter(
        self,
        lang: Optional[str] = None,
        domain: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Optional[Filter]:
        conds = []
        if lang:
            conds.append(FieldCondition(key="lang", match=MatchValue(value=lang)))
        if domain:
            conds.append(FieldCondition(key="domain", match=MatchValue(value=domain)))
        if extra:
            for k, v in extra.items():
                conds.append(FieldCondition(key=k, match=MatchValue(value=v)))
        if not conds:
            return None
        return Filter(must=conds)

    def search_vectors(
        self,
        query: str,
        top_k: int = 10,
        lang: Optional[str] = None,
        domain: Optional[str] = None,
        extra_filter: Optional[Dict[str, Any]] = None,
        with_payload: bool = True,
    ) -> List[Dict[str, Any]]:
        vec = self.embedder.embed_text(query)
        flt = self._build_filter(lang, domain, extra_filter)
        hits = self.qc.search(
            collection_name=self.collection,
            query_vector=vec,
            query_filter=flt,
            limit=top_k,
            with_payload=with_payload,
            with_vectors=False,
        )
        out = []
        for h in hits:
            out.append({
                "id": str(h.id),
                "score": float(h.score),
                "payload": dict(h.payload) if h.payload else {},
            })
        return out

    # ------------------- HYBRID (Mongo $text + Qdrant) -------------------

    def search_hybrid(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = 0.7,   # pondere vector (restul pentru text)
        lang: Optional[str] = None,
        domain: Optional[str] = None,
        extra_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        - Vector: Qdrant (COSINE) -> scoruri normalizate [0..1]
        - Text: Mongo $text (index text necesar) -> textScore normalizat [0..1]
        - Fuziune: score = alpha * vec_norm + (1-alpha) * text_norm
        Merge pe cheie comună: url (payload.url în Qdrant, document['url'] în Mongo)
        """
        # 1) vector
        vec_hits = self.search_vectors(query, top_k=top_k * 3, lang=lang, domain=domain, extra_filter=extra_filter)
        vec_scores = _minmax([h["score"] for h in vec_hits])
        for h, s in zip(vec_hits, vec_scores):
            h["_vec_norm"] = s

        # 2) text (Mongo) — folosim $text ca să avem textScore
        mongo_filter: Dict[str, Any] = {}
        if lang:
            mongo_filter["lang"] = lang
        if domain:
            mongo_filter["domain"] = domain
        if extra_filter:
            mongo_filter.update(extra_filter)

        mongo_hits = []
        try:
            text_query = {"$text": {"$search": query}} if query else {}
            q = {**mongo_filter, **text_query} if text_query else mongo_filter
            if text_query:
                mongo_hits = list(self.mcol.find(
                    q,
                    {"url": 1, "title": 1, "score": {"$meta": "textScore"}}
                ).sort([("score", {"$meta": "textScore"})]).limit(top_k * 3))
            else:
                mongo_hits = list(self.mcol.find(q, {"url": 1, "title": 1}).limit(top_k * 3))
        except OperationFailure:
            # dacă nu există index text, nu picăm — folosim doar vectorial
            mongo_hits = []

        text_scores = _minmax([float(d.get("score", 0.0)) for d in mongo_hits]) if mongo_hits else []
        url_to_text_norm = {d.get("url"): s for d, s in zip(mongo_hits, text_scores)}

        # 3) merge & fuziune scoruri
        fused: Dict[str, Dict[str, Any]] = {}
        for h in vec_hits:
            url = (h.get("payload") or {}).get("url")
            if not url:
                continue
            fused[url] = {
                "url": url,
                "title": (h.get("payload") or {}).get("title"),
                "payload": h.get("payload") or {},
                "vec_norm": h.get("_vec_norm", 0.0),
                "text_norm": url_to_text_norm.get(url, 0.0),
            }
        for d in mongo_hits:
            url = d.get("url")
            if not url or url in fused:
                continue
            fused[url] = {
                "url": url,
                "title": d.get("title"),
                "payload": {"url": url, "title": d.get("title")},
                "vec_norm": 0.0,
                "text_norm": url_to_text_norm.get(url, 0.0),
            }

        rows = []
        for url, item in fused.items():
            final = alpha * item["vec_norm"] + (1 - alpha) * item["text_norm"]
            rows.append({
                "url": url,
                "title": item.get("title"),
                "score": final,
                "vec_norm": item["vec_norm"],
                "text_norm": item["text_norm"],
                "payload": item.get("payload", {}),
            })
        rows.sort(key=lambda r: r["score"], reverse=True)
        return rows[:top_k]


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="Semantic / Hybrid search")
    ap.add_argument("query", type=str, help="Interogarea")
    ap.add_argument("--k", type=int, default=10, help="Top K")
    ap.add_argument("--alpha", type=float, default=0.7, help="Pondere vector (0..1)")
    ap.add_argument("--lang", type=str, default=None)
    ap.add_argument("--domain", type=str, default=None)
    ap.add_argument("--hybrid", action="store_true", help="Activează fuziune vector + text")
    args = ap.parse_args()

    s = SemanticSearcher()
    if args.hybrid:
        res = s.search_hybrid(args.query, top_k=args.k, alpha=args.alpha, lang=args.lang, domain=args.domain)
    else:
        res = s.search_vectors(args.query, top_k=args.k, lang=args.lang, domain=args.domain)
    print(json.dumps(res, ensure_ascii=False, indent=2))
