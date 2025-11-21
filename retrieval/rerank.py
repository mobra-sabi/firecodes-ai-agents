from __future__ import annotations
import os, torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import List, Tuple

# Modele bune:
#  - "BAAI/bge-reranker-v2-m3" (rapid, foarte ok)
#  - "mixedbread-ai/mxbai-rerank-large-v1" (mai mare, mai greu)
MODEL_ID = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
DEVICE = os.getenv("RERANK_DEVICE", "cuda:0") if torch.cuda.is_available() else "cpu"
BATCH = int(os.getenv("RERANK_BATCH", "16"))

class Reranker:
    def __init__(self, model_id: str = MODEL_ID, device: str = DEVICE):
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id)
        self.model.to(device)
        self.model.eval()
        self.device = device

    @torch.inference_mode()
    def score_pairs(self, query: str, docs: List[str]) -> List[float]:
        # Batching pentru GPU
        scores: List[float] = []
        for i in range(0, len(docs), BATCH):
            batch_docs = docs[i:i+BATCH]
            enc = self.tokenizer(
                [query] * len(batch_docs), batch_docs,
                padding=True, truncation=True, max_length=512, return_tensors="pt"
            ).to(self.device)
            out = self.model(**enc).logits.squeeze(-1)
            scores.extend(out.detach().float().cpu().tolist())
        return scores

    def rerank(self, query: str, docs: List[Tuple[str,str]]) -> List[Tuple[str,str,float]]:
        """
        docs: listă de (doc_id, text)
        return: listă sortată desc (doc_id, text, score)
        """
        ids = [d[0] for d in docs]
        texts = [d[1] for d in docs]
        if not texts:
            return []
        scores = self.score_pairs(query, texts)
        ranked = list(zip(ids, texts, scores))
        ranked.sort(key=lambda x: x[2], reverse=True)
        return ranked
