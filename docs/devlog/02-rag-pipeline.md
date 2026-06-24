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

## 실 공개 PDF 통합

합성 문서만으로는 "데이터 품질 관리" 시연이 약해, 실 공개 PDF를 코퍼스에 추가했다:
- `fems_market_report_sample.pdf` — FEMS 기술·시장 리포트 (15p, 공개)
- `iso50001_kab_certification_scheme.pdf` — 한국인정기구(KAB) ISO 50001 인증스킴 요구사항 (36p, 공개)

검증 중 얻은 교훈: pypdf 추출 결과가 PowerShell 콘솔에 깨져 보였으나, readable-ratio(=1.00)와
한글 키워드 카운트로 수치 검증한 결과 추출은 정상이었고 깨짐은 **콘솔 인코딩 표시 문제**였다.
("콘솔 표시 ≠ 실제 데이터" — 성급한 OCR/품질게이트 판단을 자가 정정.) PyMuPDF도 시험했으나
동일하게 콘솔에서만 깨져 보여, 추가 의존성 없이 pypdf 유지.

결과: 총 98개 청크(합성 md 5 + 실 PDF 2). ISO50001/FEMS 질의가 해당 실 PDF를 top-k로 검색함을 확인.

로드맵(면접 답변용): 실무 PDF는 폰트·이미지 문제로 추출 실패가 흔하므로, 향후 품질 게이트
(깨진 추출 자동 감지·제외)나 OCR 폴백을 두는 것이 다음 단계. 현재 코퍼스는 깨끗해 불필요(과설계 회피).

## 다음 단계 (Day 3)

분석 레이어: 에너지 시계열 + 검색된 가이드라인을 LLM에 전달해 이상탐지·절감안 생성.
3개 백엔드(Ollama/Claude/GPT) 동일 작업 실행.
