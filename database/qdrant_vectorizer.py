import os
import uuid
import requests
from langchain_ollama import OllamaEmbeddings
from typing import List, Tuple, Optional

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL","nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434")
def get_embedder():
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)


from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    HnswConfigDiff, OptimizersConfigDiff
)
from config.database_config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION


# ========= Embedding Provider: TEI (GPU) / Ollama / ST fallback =========

class EmbeddingProvider:
    """
    Prioritar: TEI / text-embeddings-router (/v1/embeddings, stil OpenAI)
    Alternative: Ollama (nomic-embed-text) sau Sentence-Transformers.
    Dimensiune țintă 768 (bge-base-en-v1.5 / nomic-embed-text).
    """
    def __init__(
        self,
        backend: str = None,
        ollama_url: str = None,
        ollama_model: str = None,
        st_model: str = None,
        tei_url: str = None,
        tei_model: str = None,
        st_device: str = None,
        strict: Optional[bool] = None,
        **kwargs
    ):
        self.backend = (backend or os.getenv("EMBED_BACKEND", "tei")).lower()
        self.ollama_url = (ollama_url or os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.ollama_model = ollama_model or os.getenv("EMBED_MODEL", "nomic-embed-text")
        self.st_model_name = st_model or os.getenv("ST_EMBED_MODEL", "BAAI/bge-base-en-v1.5")
        self.st_device = st_device or os.getenv("ST_DEVICE")  # ex: "cpu" sau "cuda:0"
        self.tei_url = (tei_url or os.getenv("TEI_URL", "http://127.0.0.1:8080")).rstrip("/")
        self.tei_model = tei_model or os.getenv("TEI_MODEL", "bge-base-en-v1.5")
        self.strict = (bool(int(os.getenv("EMBED_STRICT", "0"))) if strict is None else bool(strict))

        self._st = None
        self._dim = 1024  # compatibil bge-base + nomic-embed-text

        if self.backend not in ("tei", "ollama", "st"):
            self.backend = "tei"

    @property
    def dimension(self) -> int:
        if self.backend == "st" and self._st is not None:
            try:
                return int(self._st.get_sentence_embedding_dimension())
            except Exception:
                return self._dim
        return self._dim

    # ---- TEI / text-embeddings-router (OpenAI-like) ----
    def _embed_tei(self, text: str) -> Optional[List[float]]:
        try:
            url = self.tei_url + "/v1/embeddings"
            r = requests.post(url, json={"model": self.tei_model, "input": text}, timeout=30)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and "data" in data and data["data"]:
                emb = data["data"][0].get("embedding")
                if isinstance(emb, list):
                    return emb
        except Exception:
            return None
        return None

    # ---- Ollama ----
    def _embed_ollama(self, text: str) -> Optional[List[float]]:
        url = self.ollama_url + "/api/embeddings"
        # unele build-uri folosesc "prompt", altele "input"
        for payload in (
            {"model": self.ollama_model, "prompt": text},
            {"model": self.ollama_model, "input": text},
        ):
            try:
                r = requests.post(url, json=payload, timeout=30)
                r.raise_for_status()
                data = r.json()
                if isinstance(data, dict):
                    if "embedding" in data and isinstance(data["embedding"], list):
                        return data["embedding"]
                    if "embeddings" in data and data["embeddings"] and isinstance(data["embeddings"][0], list):
                        return data["embeddings"][0]
            except Exception:
                continue
        return None

    # ---- Sentence-Transformers ----
    def _ensure_st(self):
        if self._st is None:
            from sentence_transformers import SentenceTransformer
            if self.st_device:
                self._st = SentenceTransformer(self.st_model_name, device=self.st_device)
            else:
                self._st = SentenceTransformer(self.st_model_name)

    def _embed_st(self, text: str) -> List[float]:
        self._ensure_st()
        v = self._st.encode(text, normalize_embeddings=True)
        return v.tolist()

    # ---- API public ----
    def embed_text(self, text: str) -> List[float]:
        text = (text or "").strip()
        if not text:
            return [0.0] * self.dimension

        if self.backend == "tei":
            v = self._embed_tei(text)
            if isinstance(v, list) and v:
                return v
            if self.strict:
                return [0.0] * self.dimension
            self.backend = "ollama"  # fallback dacă strict=0

        if self.backend == "ollama":
            v = self._embed_ollama(text)
            if isinstance(v, list) and v:
                return v
            if self.strict:
                return [0.0] * self.dimension
            self.backend = "st"  # fallback dacă strict=0

        if self.backend == "st":
            return self._embed_st(text)

        return [0.0] * self.dimension

    def embed_chunks_mean(self, text: str, max_chars: int = 2000) -> List[float]:
        text = text or ""
        if len(text) <= max_chars:
            return self.embed_text(text)

        chunks, start = [], 0
        while start < len(text):
            end = min(len(text), start + max_chars)
            chunks.append(text[start:end])
            start = end

        dim = self.dimension
        acc = [0.0] * dim
        cnt = 0
        for t in chunks:
            v = self.embed_text(t)
            if isinstance(v, list) and len(v) == dim:
                for i in range(dim):
                    acc[i] += v[i]
                cnt += 1
        return [x / max(cnt, 1) for x in acc]


# ========= Qdrant Vectorizer =========

class QdrantVectorizer:
    def __init__(self):
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT,)
        self.collection_name = QDRANT_COLLECTION
        self.embedder = EmbeddingProvider(
            backend=os.getenv("EMBED_BACKEND", "tei"),
            ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
            ollama_model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
            st_model=os.getenv("ST_EMBED_MODEL", "BAAI/bge-base-en-v1.5"),
            tei_url=os.getenv("TEI_URL", "http://127.0.0.1:8080"),
            tei_model=os.getenv("TEI_MODEL", "bge-base-en-v1.5"),
            st_device=os.getenv("ST_DEVICE"),
            strict=bool(int(os.getenv("EMBED_STRICT", "0"))),
        )
        self._vector_size = self.embedder.dimension

    # --- helper ID ---
    def _normalize_id(self, any_id):
        """
        Qdrant cere point ID = int sau UUID.
        - None/''    -> UUID4 random
        - int        -> int
        - str UUID   -> returnează stringul
        - alt str    -> UUID5 determinist din string
        - orice alt tip -> UUID4
        """
        if any_id is None:
            return str(uuid.uuid4())
        if isinstance(any_id, int):
            return any_id
        if isinstance(any_id, str):
            s = any_id.strip()
            if not s:
                return str(uuid.uuid4())
            try:
                uuid.UUID(s)
                return s
            except Exception:
                return str(uuid.uuid5(uuid.NAMESPACE_URL, s))
        try:
            return int(any_id)
        except Exception:
            return str(uuid.uuid4())

    def create_collection(self):
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
                hnsw_config=HnswConfigDiff(m=16, ef_construct=200),
                optimizers_config=OptimizersConfigDiff(memmap_threshold=20000, indexing_threshold=20000),
            )
            print(f"✅ Qdrant collection '{self.collection_name}' created (size={self._vector_size})")
        except Exception as e:
            print(f"ℹ️ Create collection: {e}")

    def ensure_collection(self):
        try:
            info = self.client.get_collection(self.collection_name)
            current = int(info.config.params.vectors.size)
            if current != int(self._vector_size):
                raise RuntimeError(
                    f"Dimensiune vector incorectă pentru '{self.collection_name}': {current} vs {self._vector_size}."
                )
            print(f"✅ Qdrant collection OK (size={current})")
        except Exception:
            print("ℹ️ Colecția nu există sau nu poate fi citită; încerc să o creez...")
            self.create_collection()

    def vectorize_content(self, content_data: dict) -> Optional[List[float]]:
        try:
            text = content_data.get("content") or content_data.get("text") or ""
            if not text.strip():
                return None
            return self.embedder.embed_chunks_mean(text, max_chars=2000)
        except Exception as e:
            print(f"❌ Eroare la vectorizare: {e}")
            return None

    def store_embedding(self, content_id: str, embedding: List[float], metadata: dict):
        try:
            pid = self._normalize_id(content_id)
            point = PointStruct(id=pid, vector=embedding, payload=metadata)
            self.client.upsert(collection_name=self.collection_name, points=[point])
            print(f"✅ Upsert în Qdrant (1 punct) pentru {pid}")
        except Exception as e:
            print(f"❌ Error storing in Qdrant: {e}")

    def store_embeddings_batch(self, items: List[Tuple[str, List[float], dict]]):
        """Upsert batch: items = [(id, vector, payload), ...]"""
        try:
            dim = self._vector_size
            points = []
            for raw_id, vec, payload in items:
                if not isinstance(vec, list) or len(vec) != dim:
                    continue
                pid = self._normalize_id(raw_id)
                points.append(PointStruct(id=pid, vector=vec, payload=payload))
            if not points:
                print("ℹ️ Nu sunt puncte de upsert.")
                return
            self.client.upsert(collection_name=self.collection_name, points=points)
            print(f"✅ Batch upsert to Qdrant: {len(points)} points")
        except Exception as e:
            print(f"❌ Error in batch upsert: {e}")
