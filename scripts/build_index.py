"""Build (or rebuild) the RAG vector index from documents on disk.

Run:  python -m scripts.build_index
"""
import config
from src.rag.documents import load_documents
from src.rag.embeddings import embed_texts
from src.rag.store import VectorStore


def main() -> None:
    chunks = load_documents(config.DOCS_DIR)
    if not chunks:
        print(f"No .md/.txt/.pdf documents found in {config.DOCS_DIR}.")
        return

    print(f"Loaded {len(chunks)} chunks from {config.DOCS_DIR}")
    print(f"Embedding with {config.OLLAMA_EMBED_MODEL} (Ollama)...")
    embeddings = embed_texts([c.text for c in chunks])

    store = VectorStore(config.CHROMA_DIR)
    store.reset()
    store.add(chunks, embeddings)
    print(f"Indexed {store.count()} chunks into {config.CHROMA_DIR}/")


if __name__ == "__main__":
    main()
