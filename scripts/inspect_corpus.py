"""Inspect RAG corpus quality: per-doc chunk counts, size distribution,
text-quality ratio, and index integrity (loaded chunks vs Chroma count).

Run:  python -m scripts.inspect_corpus
"""
import statistics
from collections import Counter

import config
from src.rag.documents import load_documents, readable_ratio
from src.rag.embeddings import embed_texts
from src.rag.store import VectorStore

TARGET = 800  # chunk_text target_chars


def main() -> None:
    chunks = load_documents(config.DOCS_DIR)
    sizes = [len(c.text) for c in chunks]
    ratios = [readable_ratio(c.text) for c in chunks]

    # --- per document ---
    per_doc = Counter(c.source for c in chunks)
    chars_doc: Counter = Counter()
    for c in chunks:
        chars_doc[c.source] += len(c.text)

    print(f"=== Documents: {len(per_doc)} files, {len(chunks)} chunks ===")
    print(f"{'source':<42}{'chunks':>7}{'chars':>9}{'avg':>7}")
    for src in sorted(per_doc):
        n, ch = per_doc[src], chars_doc[src]
        print(f"{src:<42}{n:>7}{ch:>9}{ch // n:>7}")

    # --- chunk size distribution ---
    print(f"\n=== Chunk size (target_chars={TARGET}) ===")
    print(
        f"min={min(sizes)}  p50={int(statistics.median(sizes))}  "
        f"mean={int(statistics.mean(sizes))}  max={max(sizes)}"
    )
    oversized = [s for s in sizes if s > TARGET]
    tiny = [s for s in sizes if s < 50]
    print(f"oversized (>{TARGET}): {len(oversized)}   tiny (<50 chars): {len(tiny)}")
    hist = Counter(min(s // 100 * 100, 800) for s in sizes)
    scale = max(1, max(hist.values()) // 40)
    for b in sorted(hist):
        bar = "#" * (hist[b] // scale)
        print(f"  {b:>3}-{b + 99:<3} {bar} {hist[b]}")

    # --- text quality ---
    low = [(c.source, r) for c, r in zip(chunks, ratios) if r < 0.6]
    print(f"\n=== Text quality (readable_ratio) ===")
    print(f"min={min(ratios):.2f}  mean={statistics.mean(ratios):.2f}")
    print(f"chunks below 0.6 (possible garbage): {len(low)}")
    for src, r in low[:5]:
        print(f"  {src}  ratio={r:.2f}")

    # --- index integrity ---
    store = VectorStore(config.CHROMA_DIR)
    count = store.count()
    print(f"\n=== Index integrity ===")
    print(f"chunks loaded: {len(chunks)}   chroma count: {count}   match: {len(chunks) == count}")
    print(f"embedding dim (bge-m3): {len(embed_texts(['probe'])[0])}")


if __name__ == "__main__":
    main()
