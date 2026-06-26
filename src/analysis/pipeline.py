"""Run one question through RAG retrieval + every backend, for comparison.

The question drives retrieval (so an M&V question pulls the M&V PDF, an anomaly
question pulls the relevant runbook). The data brief for the question's track is
attached as context and cached across questions.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

import config
from src.rag.retriever import Retriever
from src.rag.store import VectorStore
from .brief import summarize_equipment_data, summarize_plant_data
from .prompt import build_analysis_prompt


@dataclass
class AnswerResult:
    provider: str
    model: str
    text: str
    latency_s: float
    cost_usd: float
    input_tokens: int
    output_tokens: int
    ok: bool = True


def _load_brief(track: str):
    if track == "steel":
        return summarize_plant_data(pd.read_csv(config.STEEL_CSV))
    if track == "synthetic":
        return summarize_equipment_data(pd.read_csv(config.ENERGY_CSV))
    raise ValueError(f"unknown track {track!r} (expected 'synthetic' or 'steel')")


class AnalysisPipeline:
    def __init__(self, providers, store: VectorStore | None = None):
        self.providers = providers
        self.retriever = Retriever(store or VectorStore(config.CHROMA_DIR))
        self._briefs: dict[str, object] = {}

    def _brief(self, track: str):
        if track not in self._briefs:
            self._briefs[track] = _load_brief(track)
        return self._briefs[track]

    def answer(self, question: str, track: str, max_tokens: int | None = None):
        """Retrieve, build the prompt, and run it across every provider.

        max_tokens=None resolves to the track's default (steel answers run long
        and were truncating at 1024; synthetic stay short) — see config.
        """
        if max_tokens is None:
            max_tokens = config.MAX_TOKENS_BY_TRACK.get(track, config.DEFAULT_MAX_TOKENS)
        brief = self._brief(track)
        guidelines = self.retriever.retrieve(question, k=config.RAG_TOP_K)
        system, user = build_analysis_prompt(brief, guidelines, question)

        results: list[AnswerResult] = []
        for p in self.providers:
            try:
                r = p.generate(system, user, max_tokens=max_tokens)
                results.append(
                    AnswerResult(
                        r.provider, r.model, r.text, r.latency_s,
                        r.cost_usd, r.input_tokens, r.output_tokens,
                    )
                )
            except Exception as e:  # noqa: BLE001 - one backend failing shouldn't abort the run
                results.append(
                    AnswerResult(
                        p.provider, getattr(p, "model", "?"), f"[ERROR] {e}",
                        0.0, 0.0, 0, 0, ok=False,
                    )
                )
        return guidelines, results
