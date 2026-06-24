"""Sanity-check retrieval: ask sample FEMS questions, show the top chunks.

Run (after build_index):  python -m scripts.rag_demo
"""
import config
from src.rag.retriever import Retriever
from src.rag.store import VectorStore

QUESTIONS = [
    "압축공기 시스템에서 에너지 낭비를 줄이려면 어떻게 해야 하나요?",
    "공장 전기요금의 피크 수요를 낮추는 방법은?",
    "야간이나 주말에 조명 전력이 계속 잡히면 무엇을 점검해야 하나요?",
]


def main() -> None:
    store = VectorStore(config.CHROMA_DIR)
    if store.count() == 0:
        print("Index is empty. Run: python -m scripts.build_index")
        return

    retriever = Retriever(store)
    for question in QUESTIONS:
        print(f"\nQ: {question}")
        for hit in retriever.retrieve(question, k=2):
            preview = " ".join(hit.text.split())[:140]
            print(f"  [{hit.source} | dist={hit.distance:.3f}] {preview}...")


if __name__ == "__main__":
    main()
