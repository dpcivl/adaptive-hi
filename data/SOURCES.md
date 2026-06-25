# 데이터 출처 (Data Provenance)

이 프로젝트는 포트폴리오/연구 데모 목적으로 공개 자료를 인용한다. 각 파일의
원본 제목·출처·라이선스를 기록한다.

## RAG 문서 (`data/documents/`)

### 합성 문서 (직접 작성)
프로젝트에서 작성한 FEMS 에너지 절감 가이드라인. 통제된 RAG 검증·데모용.
- `01_peak_demand.md` — 피크 전력 관리
- `02_compressed_air.md` — 압축공기 시스템 효율
- `03_hvac.md` — 공조설비(HVAC) 최적화
- `04_lighting.md` — 조명 에너지 절감
- `05_iso50001.md` — ISO 50001 개요

### 실 공개 문서 (다운로드)
| 파일 | 원본 제목 | 출처 |
|---|---|---|
| `fems_mv_guideline.pdf` | FEMS 에너지 절감성과 측정 및 검증(M&V) 가이드라인 (온라인 배포용) | ETRI/국가과제 |
| `fems_security_guideline.pdf` | FEMS 플랫폼 보안 가이드라인 (온라인 배포용) | ETRI/국가과제 |
| `fems_installation_standard.pdf` | 공장에너지관리시스템(FEMS) 설치확인 기준 가이드 (18.4) | 한국에너지공단(KEA) |
| `iso50001_kab_certification_scheme.pdf` | ISO 50001 에너지경영시스템 인증스킴 요구사항 (KAB-SR-EnMS, 2022) | 한국인정기구(KAB) |
| `energy_rationalization_act.pdf` | 에너지이용 합리화법 (법률 제21065호, 2026.05.28) | 법제처 |
| `fems_market_report_sample.pdf` | 공장에너지관리시스템(FEMS) 기술·시장 리포트 샘플 | 공개 IP 리포트 |

공개 배포용으로 게시된 자료를 비상업적 데모 목적으로 인용함.

## 에너지 시계열 (`data/`)

| 경로 | 설명 | 출처 / 라이선스 |
|---|---|---|
| `energy/plant_energy.csv` | **합성** 공장 에너지 데이터 (설비별, 통제된 이상 주입). `src/data/generate_energy_data.py`로 생성. gitignore됨(재생성 가능). | 자체 생성 |
| `real_energy/steel_industry.csv` | **실** 한국 광양 제철소 전력 소비 데이터 (2018, 15분 간격, 35,040행) | UCI ML Repository — Steel Industry Energy Consumption. CC BY 4.0. (Sathishkumar V E, Shin C, Cho Y) |

- 합성 = 재현 가능한 통제된 이상으로 모델 탐지·설명 능력 비교용.
- 실데이터 = 파이프라인이 실 공장 데이터도 처리함을 검증용. (설비별이 아닌 공장 전체 집계)
