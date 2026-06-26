# adaptive-hi — FEMS + LLM 분석 레이어 (로컬 vs API 비교)

가동 중인 공장 에너지관리시스템(FEMS) 위에 얹는 **AI 분석 레이어** 프로토타입.
에너지 사용 시계열을 LLM이 분석해 이상을 탐지하고 절감안을 제안하며, 절감
가이드라인 문서를 RAG로 참고한다. 핵심은 **같은 작업을 로컬(Ollama) /
Claude / GPT 세 백엔드로 돌려 품질·속도·비용을 비교**하는 것.

> MVP — 7일/풀타임 구현. FEMS 시스템 자체가 아니라 그 위에 얹는 LLM 기능을 만든다.

## 무엇을 보여주나

- **데이터 전처리·품질 관리** — 합성 에너지 시계열 생성·정리
- **RAG** — 에너지 절감 가이드라인 검색으로 분석 근거 보강
- **추론 API 연동** — Claude / GPT API
- **로컬 서빙** — Ollama로 허깅페이스 모델 추론
- **모델 성능 평가·비교** — 품질 / latency / 비용
- **외부 토큰사용량 전략** — 로컬 vs API 비용 트레이드오프 분석

## 구조

```
config.py                 # 모델 선택 + 가격표(비용 계산) + 트랙별 max_tokens
app.py                    # (Day 4) Streamlit 발표 대시보드 — 3백엔드 답변 나란히 비교
src/
  llm/
    base.py               # LLMProvider 인터페이스 + LLMResponse(메트릭)
    ollama_provider.py     # 로컬 추론 (비용 0)
    claude_provider.py     # Anthropic SDK
    openai_provider.py     # OpenAI SDK
    registry.py            # API 키 유무에 따라 비교 대상 구성
  data/
    generate_energy_data.py  # 합성 FEMS 에너지 데이터 생성
  rag/                    # (Day 2) 청킹/임베딩/검색/벡터스토어
  analysis/               # (Day 3) 분석 레이어
    brief.py              # 시계열 → 설비별 시간대 요약(brief) 생성
    prompt.py             # RAG 컨텍스트 + brief → 분석 프롬프트 조립
    pipeline.py           # 질문 → 검색 → 프롬프트 → 백엔드별 답변/메트릭
evals/
  questions.py            # (Day 4) 평가 질문 6개 (진단·지식·함정·추론)
scripts/
  smoke_test.py           # Day 1 동작 확인
  build_index.py          # RAG 인덱스 구축
  run_analysis.py         # (Day 3) 6질문 × 3백엔드 실행 → results/comparison.md
data/
  documents/              # RAG 문서 (FEMS 가이드라인)
  energy/                 # 생성된 합성 시계열 CSV
  real_energy/            # 실 제철소 데이터 CSV (steel 트랙)
results/
  comparison.md           # 백엔드별 답변·비용·지연 종합표
  grades.md               # (Day 4) LLM-as-judge 채점표
```

## 빠른 시작

```powershell
# 1. 가상환경 (Python 3.12 — ML 패키지 호환)
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 키 설정
copy .env.example .env   # 편집해서 ANTHROPIC_API_KEY / OPENAI_API_KEY 입력

# 3. Ollama 모델 받기 (https://ollama.com 설치 후)
ollama pull exaone3.5:7.8b   # config 기본 추론 모델 (한국어 특화 — qwen 중국어 혼입 대체)
ollama pull bge-m3           # 임베딩

# 4. 합성 에너지 데이터 생성
python -m src.data.generate_energy_data

# 5. 동작 확인 (설정된 백엔드만 실행)
python -m scripts.smoke_test

# 6. 비교 분석 실행 (6질문 × 3백엔드 → results/comparison.md)
#    전제: .venv 활성화 + Ollama 기동(ollama serve) 상태여야 함
python -m scripts.run_analysis

# 7. 발표 데모 대시보드
streamlit run app.py
```

## 하드웨어 메모

개발 환경: GTX 1660 Super (VRAM 6GB), RAM 32GB. 6GB로는 7B Q4가 한계선이라
일부가 RAM으로 오프로드되어 느리다 — 그 **느린 latency 자체가 "왜 API/서버 추론이
필요한가"를 보여주는 비교 데이터**다. 프로덕션 서빙은 Ollama 대신 vLLM이
적합(높은 throughput, 배칭, OpenAI 호환 API) — 본 프로토타입은 Ollama로 검증한다.

## 비교 축

| 축 | 측정 |
|---|---|
| 품질 | FEMS 분석/절감안의 충실도·정확성 |
| 속도 | 요청당 latency, 토큰/초 |
| 비용 | API 토큰 비용 vs 로컬(전력) |
| 보안 | 온프레미스 가능성 (공장 데이터 외부 전송 여부) |

비교의 결론은 단순 우열이 아니라 **라우팅 전략**으로 도출한다: 어떤 질의는 로컬,
어떤 질의는 API로 보내면 비용 X% 절감 — 이게 면접 어필 포인트.

## 평가·채점 (LLM-as-judge)

평가 질문 6개(진단·지식·함정 2종·추론 2종)를 3백엔드에 동일하게 돌리고, 코퍼스
원문 사실 확인 + `expect` 기준으로 5축(정답성·환각·출처명시·언어혼입·함정회피)
채점했다. 종합 점수(/10):

| 질문 | 유형 | ollama (exaone) | claude (opus) | openai (gpt-4o) |
|---|---|---|---|---|
| Q1 조명 야간 이상 | 진단 | 8 | 10 | 9 |
| Q2 M&V 산정 | 지식 | 7 | 10 | 9 |
| Q3 생산라인 격차 | **함정·오탐** | 9 | 10 | **3** |
| Q4 ESS payback | **함정·코퍼스밖** | 9 | 10 | 10 |
| Q5 압축기 주말 이상 | 추론 | 9 | 9 | 9 |
| Q6 기본요금 피크저감 | 추론 | 6 | 9 | 8 |
| **평균** | | **8.0** | **9.7** | **8.0** |

핵심 발견: **환각 회피(없는 사실 지어내기)는 셋 다 잘하나, 오탐 회피(있는 사실의
과잉 해석)는 갈린다.** 코퍼스밖 함정 Q4(ESS payback)는 셋 다 "자료에 없음"으로 통과
(9·10·10). 그러나 정상 생산패턴을 이상으로 착각시키는 오탐 함정 Q3에서는 **openai만
"이상 신호로 해석될 수 있습니다"라며 흔들려 3점**, claude(10)·로컬 exaone(9)은 "정상
운영 패턴"으로 정확히 판단했다.

| 백엔드 | 평균/10 | 총비용($) | 평균지연(s) |
|---|---|---|---|
| ollama (exaone3.5) | 8.0 | 0.0000 | 42.2 |
| claude (opus-4-8) | 9.7 | 0.2371 | 14.8 |
| openai (gpt-4o) | 8.0 | 0.0458 | 3.6 |

(6질문 기준. 상세 답변·메트릭은 `results/comparison.md`, 5축 채점 근거는
`results/grades.md`.)

결론은 다시 **라우팅 전략**으로 귀결된다: 오경보 비용이 큰 진단(예: 오탐→불필요
설비점검)에는 opus 프리미엄이 정당하고, 단순·저위험 질의에는 gpt-4o(초저지연·저비용)
또는 로컬(비용 0)이 적합하다.

## 진행 상황

- [x] Day 1 — 골격: LLM 추상화, 합성 데이터 생성, 동작 확인
- [x] Day 2 — RAG 파이프라인 (청킹 → 임베딩 → 검색)
- [x] Day 3 — 분석 레이어 + 3개 백엔드 동일 작업 실행·비교
- [x] Day 4 — 발표 대시보드(`app.py`) + 함정/추론 평가 질문 6개(`evals/questions.py`)
  + 트랙별 max_tokens 차등 + 역할분리 에이전트 4종(code-writer·code-reviewer·
  answer-grader·rag-auditor) + LLM-as-judge 채점(`results/grades.md`)
- [ ] Day 5 (진행 중) — 발표 준비. 남은 작업: 발표 스크립트(talking points MD)·
  pptx 슬라이드 (아직 미작성, 이후 진행 예정)

## 메모

- Claude는 비교 공정성을 위해 thinking 끈 기본 호출. 별도 "품질 상한" 실험으로
  adaptive thinking을 켤 수 있다 (`claude_provider.py`).
- OpenAI 가격(`config.py`)은 변동되므로 인용 전 공식 페이지에서 확인할 것.
- 트랙별 출력 토큰 차등(`MAX_TOKENS_BY_TRACK`): synthetic 1024 / steel 2048.
  steel 상향은 Day4 즉석 steel 질문(패턴 해석+절감안+M&V)이 claude에서 1024에
  절단된 관측이 근거 — 상향 후 현재 steel Q2는 1376 tok으로 정상 완료.
  단 현재 6Q 실행에선 **synthetic Q5·Q6(claude)가 1024에 절단**됨(`comparison.md`
  말미가 문장 중간에 끊김) → synthetic도 상향 검토가 다음 과제.
