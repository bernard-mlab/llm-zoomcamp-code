"""Centralized configuration loaded from env (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    # LLM (OpenAI-compatible proxy; model id Hy3)
    llm_api_key: str = os.getenv("OPENCODE_GO_API_KEY", "")
    llm_base_url: str = os.getenv("OPENCODE_GO_BASE_URL", "")
    llm_model: str = os.getenv("OPENCODE_GO_MODEL", "Hy3")
    secondary_model: str = os.getenv("SECONDARY_MODEL", "")

    # Qdrant
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "arxiv_papers")

    # Embed / rerank
    embed_model: str = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    rerank_model: str = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

    # arxiv ingest
    arxiv_max_results: int = int(os.getenv("ARXIV_MAX_RESULTS", "3000"))
    arxiv_categories: tuple[str, ...] = tuple(
        c for c in os.getenv("ARXIV_CATEGORIES", "cs.AI,cs.CL,cs.LG").split(",") if c
    )

    # Langfuse
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    langfuse_public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    langfuse_secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_base_url)


settings = Settings()