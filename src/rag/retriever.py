"""Tie query embedding + vector search into a single retrieve() call."""
from __future__ import annotations

from dataclasses import dataclass

import config
from .embeddings import embed_texts
from .store import VectorStore


@dataclass
class RetrievedChunk:
    text: str
    source: str
    distance: float  # cosine distance; lower = more similar (0 = identical)


class Retriever:
    def __init__(self, store: VectorStore):
        self.store = store

    def retrieve(self, question: str, k: int | None = None) -> list[RetrievedChunk]:
        k = k if k is not None else config.RAG_TOP_K
        query_embedding = embed_texts([question])[0]
        hits = self.store.query(query_embedding, k=k)
        return [RetrievedChunk(**hit) for hit in hits]
