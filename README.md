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
config.py                 # 모델 선택 + 가격표(비용 계산)
src/
  llm/
    base.py               # LLMProvider 인터페이스 + LLMResponse(메트릭)
    ollama_provider.py     # 로컬 추론 (비용 0)
    claude_provider.py     # Anthropic SDK
    openai_provider.py     # OpenAI SDK
    registry.py            # API 키 유무에 따라 비교 대상 구성
  data/
    generate_energy_data.py  # 합성 FEMS 에너지 데이터 생성
  rag/                    # (Day 2) 청킹/임베딩/검색
scripts/
  smoke_test.py           # Day 1 동작 확인
data/
  documents/              # RAG 문서 (FEMS 가이드라인)
  energy/                 # 생성된 시계열 CSV
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
ollama pull qwen2.5:7b
ollama pull bge-m3

# 4. 합성 에너지 데이터 생성
python -m src.data.generate_energy_data

# 5. 동작 확인 (설정된 백엔드만 실행)
python -m scripts.smoke_test
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

## 진행 상황

- [x] Day 1 — 골격: LLM 추상화, 합성 데이터 생성, 동작 확인
- [x] Day 2 — RAG 파이프라인 (청킹 → 임베딩 → 검색)
- [x] Day 3 — 분석 레이어 + 3개 백엔드 동일 작업 실행·비교
- [ ] Day 4 — 비교 평가 + Streamlit 대시보드
- [ ] Day 5 — 버퍼 / README / 발표자료

## 메모

- Claude는 비교 공정성을 위해 thinking 끈 기본 호출. 별도 "품질 상한" 실험으로
  adaptive thinking을 켤 수 있다 (`claude_provider.py`).
- OpenAI 가격(`config.py`)은 변동되므로 인용 전 공식 페이지에서 확인할 것.
