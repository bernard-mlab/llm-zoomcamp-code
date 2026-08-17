"""Langfuse tracing helpers. Phase 6.

Every user turn = a Langfuse trace; child spans per agent iteration,
search/llm/fetch call. See the design spec §8.

Uses Langfuse SDK v2 (matches self-hosted Langfuse v2 server).
"""
from __future__ import annotations

import contextlib
import uuid
from typing import Any

from langfuse import Langfuse

from .config import settings

_langfuse: Langfuse | None = None


def get_client() -> Langfuse | None:
    global _langfuse
    if _langfuse is None:
        if not settings.langfuse_public_key or not settings.langfuse_secret_key:
            return None
        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    return _langfuse


def create_trace(name: str, user_id: str | None = None, metadata: dict | None = None) -> str | None:
    lf = get_client()
    if lf is None:
        return None
    trace = lf.trace(
        name=name,
        user_id=user_id,
        metadata=metadata or {},
    )
    return trace.id


@contextlib.contextmanager
def span(trace_id: str | None, name: str, **kwargs: Any):
    lf = get_client()
    if lf is None or trace_id is None:
        yield None
        return

    trace = lf.trace(id=trace_id)
    s = trace.span(
        name=name,
        input=kwargs.get("input"),
        metadata=kwargs.get("metadata"),
    )
    try:
        yield s
    finally:
        s.end()


def score(trace_id: str, name: str, value: float, comment: str | None = None):
    lf = get_client()
    if lf is None:
        return
    lf.score(
        trace_id=trace_id,
        name=name,
        value=value,
        data_type="NUMERIC",
        comment=comment or "",
    )


def flush():
    lf = get_client()
    if lf is not None:
        lf.flush()