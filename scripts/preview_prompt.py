"""Assemble and print the analysis prompt for one question WITHOUT calling any LLM.

Lets you inspect exactly what the backends will see (data brief + retrieved
guidelines + question) before spending API tokens. Uses Ollama embeddings for
retrieval (local, free). Previews the first eval question of the chosen track.

Run:  python -m scripts.preview_prompt            # synthetic track
      python -m scripts.preview_prompt steel      # steel track
"""
import os
import sys

import pandas as pd

import config
from evals.questions import QUESTIONS
from src.analysis.brief import summarize_equipment_data, summarize_plant_data
from src.analysis.prompt import build_analysis_prompt
from src.rag.retriever import Retriever
from src.rag.store import VectorStore


def main() -> None:
    track = "steel" if (len(sys.argv) > 1 and sys.argv[1] == "steel") else "synthetic"
    csv = config.STEEL_CSV if track == "steel" else config.ENERGY_CSV
    if not os.path.exists(csv):
        sys.exit(f"데이터 없음: {csv} — 먼저 'python -m src.data.generate_energy_data'를 실행하세요.")
    df = pd.read_csv(csv)
    brief = summarize_plant_data(df) if track == "steel" else summarize_equipment_data(df)

    matching = [q for q in QUESTIONS if q["track"] == track]
    question = matching[0]["question"] if matching else "이 데이터에서 비정상 패턴을 찾아 설명하라."

    store = VectorStore(config.CHROMA_DIR)
    if store.count() == 0:
        sys.exit("RAG 인덱스가 비었습니다 — 먼저 'python -m scripts.build_index'를 실행하세요.")
    guidelines = Retriever(store).retrieve(question, k=config.RAG_TOP_K)
    system, user = build_analysis_prompt(brief, guidelines, question)

    print(f"### TRACK: {track} — {brief.title}\n")
    print("=" * 70, "\nSYSTEM\n", "=" * 70, sep="")
    print(system)
    print("\n", "=" * 70, "\nUSER\n", "=" * 70, sep="")
    print(user)
    print("\n", "=" * 70, sep="")
    print(f"retrieved {len(guidelines)} guideline chunks: {[g.source for g in guidelines]}")


if __name__ == "__main__":
    main()
