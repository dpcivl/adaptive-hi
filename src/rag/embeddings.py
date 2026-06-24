"""Text embeddings via Ollama (bge-m3) — multilingual, strong on Korean.

Kept local so the RAG layer needs no embedding API; the same bge-m3 model
serves both document indexing and query embedding.
"""
from __future__ import annotations

import ollama

import config


def embed_texts(
    texts: list[str], model: str | None = None, batch_size: int = 32
) -> list[list[float]]:
    """Embed a list of texts, batched to keep request sizes reasonable."""
    model = model or config.OLLAMA_EMBED_MODEL
    out: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        resp = ollama.embed(model=model, input=batch)
        out.extend(resp["embeddings"])
    return out
