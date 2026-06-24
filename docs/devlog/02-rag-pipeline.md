# 02 · RAG 파이프라인

FEMS 가이드라인 문서를 검색 가능한 형태로 인덱싱하고, 질문에 대해 관련 청크를
가져오는 RAG의 "검색(Retrieval)" 절반을 구현했다.

## 구현 내용

| 파일 | 역할 |
|---|---|
| `src/rag/documents.py` | 문서 로딩(.md/.txt/.pdf) + 문단 기반 청킹 |
| `src/rag/embeddings.py` | bge-m3 임베딩 (Ollama, 배치) |
| `src/rag/store.py` | Chroma 벡터스토어 (cosine 공간, 임베딩 직접 주입) |
| `src/rag/retriever.py` | 질의 임베딩 + 검색 통합 |
| `scripts/build_index.py` | 인덱스 빌드/재빌드 |
| `scripts/rag_demo.py` | 검색 동작 확인 |
| `data/documents/*.md` | 합성 FEMS 가이드라인 5종 |

## 설계 결정과 대안 거절 이유

- **임베딩 = Ollama bge-m3**: 별도 임베딩 API 불필요, 한국어/다국어 우수, 문서·질의에
  동일 모델 사용으로 임베딩 공간 일치. (대안 sentence-transformers → torch 설치 부담·3.12
  휠 리스크로 거절.)
- **임베딩 직접 계산 후 Chroma 주입**: Chroma 기본 임베딩 함수(영어 위주 MiniLM)를 우회.
  한국어 FEMS 문서 검색 품질 확보.
- **cosine 공간**: bge-m3는 정규화 임베딩이라 cosine이 적합 (Chroma 기본 L2 대신 명시).
- **직접 구현(프레임워크 없이)**: LangChain/LlamaIndex 거절 — 무거운 의존성·과도한 추상화.
  투명성과 면접 설명 용이성 우선.
- **폴더 자동 로드**: 공개 PDF를 같은 폴더에 넣으면 자동 인덱싱되도록 설계.

## 적대적 코드 리뷰 결과 및 조치

별도 에이전트가 주석을 배제하고 로직을 추적해 리뷰. 주요 발견과 조치:

| 발견 | 조치 |
|---|---|
| MAJOR: `chunk_text`가 target_chars보다 큰 단일 문단을 안 쪼갬 → 무한정 큰 청크 | `_split_long`으로 오버랩 윈도우 하드 분할 추가 |
| MAJOR: 오버랩이 문자 단순 슬라이스(단어 중간 잘림) → 노이즈 | 문단 경계 컷에는 오버랩 제거, 강제 분할에만 오버랩 적용 |
| MINOR: 파일 1개 실패 시 전체 빌드 중단 | 파일별 try/except로 skip+warn |
| NIT: 거리 주석 "L2/cosine" 부정확 + `RAG_TOP_K` 미사용 | cosine 명시, `RAG_TOP_K` 연결 |

리뷰어가 "문제 아님"으로 확인: `store.query` 중첩 리스트 인덱싱 정확, `ollama.embed`
응답 키 정확, 빈 입력/k 초과 안전.

## 테스트 결과

`python -m scripts.build_index` → 정상 인덱싱. `python -m scripts.rag_demo` 검색 결과
(top-1, cosine 거리):

| 질문 | top-1 | 거리 |
|---|---|---|
| 압축공기 에너지 낭비 | `02_compressed_air.md` | 0.322 |
| 피크 수요 저감 | `01_peak_demand.md` | 0.272 |
| 야간·주말 조명 전력 지속 | `04_lighting.md` | 0.392 |

세 질문 모두 정답 문서를 top-1로 검색. 2순위와 뚜렷한 거리 격차.

## 다음 단계 (Day 3)

분석 레이어: 에너지 시계열 + 검색된 가이드라인을 LLM에 전달해 이상탐지·절감안 생성.
3개 백엔드(Ollama/Claude/GPT) 동일 작업 실행.
