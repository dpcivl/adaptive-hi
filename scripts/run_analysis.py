"""Run every eval question across all backends and write a comparison report.

Each question is sent identically to Ollama / Claude / GPT; answers + metrics
(latency, cost, tokens) are collected and graded by you against `expect`.

Run:  python -m scripts.run_analysis
"""
import os
from pathlib import Path

import config
from evals.questions import QUESTIONS
from src.analysis.pipeline import AnalysisPipeline
from src.llm import build_providers
from src.rag.store import VectorStore

OUT = Path("results/comparison.md")
_CSV = {"steel": config.STEEL_CSV, "synthetic": config.ENERGY_CSV}


def main() -> None:
    providers = build_providers()
    if not providers:
        print("실행할 백엔드가 없습니다. .env의 API 키와 Ollama 실행을 확인하세요.")
        return
    if not QUESTIONS:
        print("evals/questions.py에 질문이 없습니다.")
        return

    # pre-flight: index built, and the CSV for each used track exists
    store = VectorStore(config.CHROMA_DIR)
    if store.count() == 0:
        print("RAG 인덱스가 비었습니다 — 먼저 'python -m scripts.build_index'를 실행하세요.")
        return
    for track in {q["track"] for q in QUESTIONS}:
        path = _CSV.get(track)
        if not path or not os.path.exists(path):
            print(f"데이터/트랙 문제: track={track!r}, path={path}")
            return

    pipe = AnalysisPipeline(providers, store=store)
    md = ["# 백엔드 비교 결과\n"]
    # seed so every backend appears in the summary even if it errors on all questions
    totals = {p.provider: {"cost": 0.0, "lat": 0.0, "ok": 0, "err": 0} for p in providers}

    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n[{i}/{len(QUESTIONS)}] ({q['track']}) {q['question']}")
        guidelines, results = pipe.answer(q["question"], q["track"])
        srcs = ", ".join(dict.fromkeys(g.source for g in guidelines))
        print(f"  검색 출처: {srcs}")

        md.append(f"\n## Q{i} · {q['track']} · {q['question']}\n")
        md.append(f"- 검색 출처: {srcs}\n- 기대(채점 기준): {q['expect']}\n")
        for r in results:
            flag = "" if r.ok else " [ERROR]"
            print(f"  {r.provider:8} {r.latency_s:6.1f}s  ${r.cost_usd:.4f}  out {r.output_tokens}tok{flag}")
            md.append(
                f"\n### {r.provider} ({r.model}) — {r.latency_s:.1f}s · "
                f"${r.cost_usd:.4f} · in {r.input_tokens}/out {r.output_tokens} tok\n\n"
            )
            md.append(r.text.strip() + "\n")
            t = totals.setdefault(r.provider, {"cost": 0.0, "lat": 0.0, "ok": 0, "err": 0})
            if r.ok:
                t["cost"] += r.cost_usd
                t["lat"] += r.latency_s
                t["ok"] += 1
            else:
                t["err"] += 1
        md.append("\n---\n")

    md.append("\n## 종합 (백엔드별)\n\n| 백엔드 | 총비용($) | 평균지연(s) | 성공/실패 |\n|---|---|---|---|\n")
    print("\n=== 종합 ===")
    for prov, t in totals.items():
        avg = f"{t['lat'] / t['ok']:.1f}" if t["ok"] else "—"
        md.append(f"| {prov} | {t['cost']:.4f} | {avg} | {t['ok']}/{t['err']} |\n")
        print(f"  {prov:8} 총 ${t['cost']:.4f}  평균 {avg}s  성공 {t['ok']} 실패 {t['err']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(md), encoding="utf-8")
    print(f"\n보고서 저장: {OUT} (한글은 콘솔보다 파일에서 잘 보입니다)")


if __name__ == "__main__":
    main()
