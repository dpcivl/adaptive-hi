"""Build a question-driven analysis prompt from a data brief + retrieved guidelines.

Plain-text output (not JSON) so the comparison is fair across a 7B local model
and the cloud APIs — JSON adherence would itself bias the result.
"""
from __future__ import annotations

from .brief import DataBrief

SYSTEM = (
    "당신은 공장에너지관리시스템(FEMS) 에너지 분석 전문가다. 주어진 전력 사용 요약과 "
    "참고 가이드라인을 근거로 질문에 답한다. 답변의 근거가 된 가이드라인의 출처 파일명을 "
    "명시한다. 데이터·가이드라인에 없는 내용은 지어내지 말고 '자료에 없음'이라고 답한다. "
    "간결하고 구체적으로 답하며, 반드시 한국어로만 작성하고 중국어 등 다른 언어를 섞지 않는다."
)


def build_analysis_prompt(
    brief: DataBrief, guidelines: list, question: str
) -> tuple[str, str]:
    """Return (system, user). `guidelines` is a list of RetrievedChunk."""
    if guidelines:
        guide_text = "\n\n".join(f"[출처: {g.source}]\n{g.text}" for g in guidelines)
    else:
        guide_text = "(검색된 가이드라인 없음)"

    user = (
        f"## 전력 사용 요약\n{brief.text}\n\n"
        f"## 참고 가이드라인\n{guide_text}\n\n"
        f"## 질문\n{question}\n\n"
        "## 작성 지침\n"
        "- 위 전력 사용 요약과 참고 가이드라인만을 근거로 답하라.\n"
        "- 판단·권장 조치의 근거가 된 가이드라인 출처 파일명을 명시하라.\n"
        "- 데이터·가이드라인에 없는 내용은 추측하지 말고 '자료에 없음'이라고 밝혀라."
    )
    return SYSTEM, user
