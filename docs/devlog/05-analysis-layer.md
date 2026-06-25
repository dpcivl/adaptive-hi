# 05 · 분석 레이어 + 3개 백엔드 비교 (Day 3)

데이터·RAG·LLM을 묶어, 질문을 3개 백엔드(Ollama/Claude/GPT)에 동일하게 보내고
출력·메트릭을 비교하는 핵심 단계.

## 구현

| 파일 | 역할 |
|---|---|
| `src/analysis/brief.py` | 에너지 데이터 → LLM용 텍스트 요약 (합성=설비별 버킷, 실=제철소 plant) |
| `src/analysis/prompt.py` | 질문 구동 프롬프트(데이터요약+검색문서+질문), 평문 출력, 한국어 고정 |
| `src/analysis/pipeline.py` | 질문→검색→프롬프트→전 백엔드 실행, 브리프 캐시, 오류 격리 |
| `scripts/run_analysis.py` | 전 질문×전 백엔드 → `results/comparison.md` + 종합 메트릭 |
| `scripts/preview_prompt.py` | LLM 없이 프롬프트 검수 |
| `evals/questions.py` | 평가 질문(track/question/expect). expect는 채점용, 모델엔 미전달 |

## 설계 결정

- **질문이 검색을 주도** → M&V 질문엔 M&V PDF가, 조명 질문엔 조명 런북이 검색됨
  (실 PDF가 비로소 load-bearing).
- **평문 출력(JSON 아님)** → 7B/클라우드 공정 비교.
- **브리프 캐시 / 백엔드 오류 격리 / max_tokens 동일** → 공정성·견고성.

## 적대적 리뷰

- MAJOR: 오류난 백엔드가 평균지연 분모에 포함 → `ok` 플래그로 성공만 집계, 0division 가드.
- MINOR: 미지 track 무음 처리 → 명시적 검증. run_analysis 사전점검 추가.
- 확인: 3백엔드 **동일 프롬프트·max_tokens**(공정성), 질문이 검색 주도, 필드 매핑 정확.

## 로컬 모델 여정 (핵심 교훈)

1. **qwen2.5:7b**: M&V 답을 정확히 시작했으나 긴 생성에서 **중국어 혼입 + GeoJSON 탈선**.
2. **temperature 0.2 + repeat_penalty**: **탈선(degeneration)은 해결**했으나 **중국어 혼입은 오히려 악화**
   → 샘플링은 *탈선*은 잡아도 *언어 편향*은 못 잡음을 실증.
3. **EXAONE 3.5(한국어 특화)로 교체**: 탈선·언어혼입 **모두 해결**.

> 교훈: 증상별 처방을 구분해야 한다. 탈선 = 샘플링(temp/repeat_penalty), 언어 편향 = **모델 선택**.
> 내용 지식은 qwen도 있었음(RAG·M&V 정확) — 작고 양자화된 모델이 *일관성 유지*에 실패한 것.

## 결과 (예시 2문항, exaone/claude-opus-4-8/gpt-4o)

| 백엔드 | 평균 지연 | 비용(2문항) | 비고 |
|---|---|---|---|
| ollama (exaone3.5) | ~64s | $0 | 로컬·무료지만 6GB에서 느림 |
| claude (opus-4-8) | ~8s | $0.060 | |
| openai (gpt-4o) | ~3s | $0.016 | 가장 빠름·저렴, 간결 |

- 검색: Q1 → `04_lighting.md`, Q2 → `fems_mv_guideline.pdf` (실 PDF 활용 확인).
- 속도 ~20×(로컬 vs GPT) 격차 → "중요/긴 질의는 API 라우팅" 근거.

## 알려진 한계 / 다음

- ollama·claude가 max_tokens 512 상한 도달(답변 잘림 가능) → 상한 상향 또는 간결화 튜닝 검토.
- 합성 런북 leakage(정답 근접 서술) → 추론형·함정 질문 추가로 변별력 강화.
- 품질 채점은 사용자가 `expect`와 대조해 수행.
