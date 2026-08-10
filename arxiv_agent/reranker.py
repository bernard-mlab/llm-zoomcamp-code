"""Cross-encoder reranker (sentence-transformers). Phase 2."""
from __future__ import annotations

from arxiv_agent.config import settings


class Reranker:
    def __init__(self, model_name: str | None = None):
        self._model_name = model_name or settings.rerank_model
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)

    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        if not documents:
            return []

        self._ensure_model()

        pairs = [
            (query, f"{doc.get('title', '')} {doc.get('summary', '')}")
            for doc in documents
        ]
        scores = self._model.predict(pairs)
        scored = list(zip(documents, scores, strict=True))
        scored.sort(key=lambda x: float(x[1]), reverse=True)

        results = []
        for doc, score in scored[:top_k]:
            result = dict(doc)
            result["rerank_score"] = float(score)
            results.append(result)
        return results