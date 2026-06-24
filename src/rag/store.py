"""Chroma-backed vector store. Pure vector ops — embeddings are passed in.

We supply embeddings explicitly (computed by our bge-m3 helper) on both add
and query, so Chroma's built-in embedding function is never used.
"""
from __future__ import annotations

from pathlib import Path

import chromadb

from .documents import Chunk


class VectorStore:
    # cosine matches bge-m3's normalized embeddings (Chroma defaults to L2).
    _METADATA = {"hnsw:space": "cosine"}

    def __init__(self, path: str | Path, collection_name: str = "fems_docs"):
        self._client = chromadb.PersistentClient(path=str(path))
        self._name = collection_name
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata=self._METADATA
        )

    def reset(self) -> None:
        """Drop and recreate the collection for a clean rebuild."""
        try:
            self._client.delete_collection(self._name)
        except Exception:  # noqa: BLE001 - absent collection is fine
            pass
        self._collection = self._client.get_or_create_collection(
            name=self._name, metadata=self._METADATA
        )

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) length mismatch"
            )
        self._collection.add(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=embeddings,
            metadatas=[{"source": c.source, "doc_id": c.doc_id} for c in chunks],
        )

    def query(self, embedding: list[float], k: int = 4) -> list[dict]:
        res = self._collection.query(query_embeddings=[embedding], n_results=k)
        documents = res["documents"][0]
        metadatas = res["metadatas"][0]
        distances = res["distances"][0]
        return [
            {"text": doc, "source": meta["source"], "distance": dist}
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]

    def count(self) -> int:
        return self._collection.count()
