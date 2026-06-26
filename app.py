"""Streamlit 발표용 데모 — FEMS 에너지 분석: 로컬 vs API 백엔드 비교.

좌측에서 데이터(트랙)를 고르면 사용 패턴 차트가 뜨고, 질문을 입력하면 동일한
RAG 프롬프트가 3개 백엔드(Ollama·Claude·GPT)에 전달되어 답변과 메트릭(지연·비용·
토큰)이 나란히 표시된다. 프로젝트의 핵심 주장 — "로컬 7B로 어디까지 되고, 어디서
API가 값을 하는가" — 를 한 화면에서 보여주는 것이 목적이다.

실행:  streamlit run app.py   (사전: .venv 활성화 + Ollama 실행)
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from evals.questions import QUESTIONS
from src.analysis.pipeline import AnalysisPipeline
from src.llm import build_providers
from src.rag.store import VectorStore

st.set_page_config(page_title="FEMS 백엔드 비교 데모", page_icon="⚡", layout="wide")

# 백엔드별 표시 메타 (라벨 + 로컬/클라우드 구분)
_PROVIDER_META = {
    "ollama": ("🖥️ Ollama (로컬)", True),
    "claude": ("🟣 Claude (API)", False),
    "openai": ("🟢 GPT (API)", False),
}


@st.cache_resource(show_spinner="백엔드·RAG 인덱스 준비 중…")
def get_pipeline():
    """providers + RAG 파이프라인을 1회만 구성해 캐시한다."""
    providers = build_providers()
    store = VectorStore(config.CHROMA_DIR)
    pipe = AnalysisPipeline(providers, store=store)
    return pipe, providers, store.count()


@st.cache_data(show_spinner=False)
def load_synthetic() -> pd.DataFrame:
    df = pd.read_csv(config.ENERGY_CSV, parse_dates=["timestamp"])
    return df


@st.cache_data(show_spinner=False)
def load_steel() -> pd.DataFrame:
    df = pd.read_csv(config.STEEL_CSV)
    df["dt"] = pd.to_datetime(df["date"], format="%d/%m/%Y %H:%M")
    return df


def render_synthetic_chart() -> None:
    df = load_synthetic()
    st.caption(
        f"합성 설비 데이터 · {df['timestamp'].min():%Y-%m-%d} ~ {df['timestamp'].max():%Y-%m-%d}"
        f" · 시간당 kW · 설비 {df['equipment'].nunique()}종"
    )
    wide = df.pivot_table(index="timestamp", columns="equipment", values="power_kw")
    st.line_chart(wide, height=320)
    st.caption(
        "💡 주입된 이상: **air_compressor 주말 고착**(5/16–17) · "
        "**lighting 야간 방치**(5/20–26) · **hvac 주간 스파이크**(5/8 오후)"
    )


def render_steel_chart() -> None:
    df = load_steel()
    st.caption(
        f"실 제철소 데이터(UCI) · {df['dt'].min():%Y-%m-%d} ~ {df['dt'].max():%Y-%m-%d}"
        f" · 15분 간격 · {len(df):,}개 측정"
    )
    daily = df.set_index("dt")["Usage_kWh"].resample("D").mean()
    st.line_chart(daily, height=280, y_label="일평균 Usage_kWh")
    by_load = (
        df.groupby("Load_Type")["Usage_kWh"].mean().sort_values(ascending=False)
    )
    st.caption("부하유형(Load_Type)별 평균 사용량 (kWh / 15분)")
    st.bar_chart(by_load, height=220)


def render_result_column(col, label: str, is_local: bool, r) -> None:
    """한 백엔드의 메트릭 + 답변을 한 컬럼에 렌더링."""
    with col:
        st.markdown(f"#### {label}")
        st.caption(r.model)
        if not r.ok:
            st.error(r.text)
            return
        m1, m2, m3 = st.columns(3)
        m1.metric("지연", f"{r.latency_s:.1f}s")
        m2.metric("비용", "로컬 $0" if is_local else f"${r.cost_usd:.4f}")
        tps = r.output_tokens / r.latency_s if r.latency_s > 0 else 0
        m3.metric("출력토큰", f"{r.output_tokens}", f"{tps:.0f} tok/s")
        st.markdown(r.text)


# ── 헤더 ──────────────────────────────────────────────────────────────
st.title("⚡ FEMS 에너지 분석 — 로컬 vs API 백엔드 비교")
st.markdown(
    "동일한 RAG 프롬프트(데이터 요약 + 검색된 가이드라인)를 **Ollama(로컬 7B) · "
    "Claude · GPT** 에 똑같이 던져 **답변 품질 / 지연 / 비용**을 한눈에 비교합니다."
)

try:
    pipe, providers, index_count = get_pipeline()
except Exception as e:  # noqa: BLE001
    st.error(f"파이프라인 초기화 실패: {e}")
    st.stop()

# ── 사이드바 ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("설정")
    active = [_PROVIDER_META.get(p.provider, (p.provider, False))[0] for p in providers]
    if active:
        st.success("활성 백엔드\n\n" + "\n\n".join(f"- {a}" for a in active))
    else:
        st.error("활성 백엔드 없음 — Ollama 실행 / API 키(.env)를 확인하세요.")
    st.caption(f"RAG 인덱스: {index_count}개 청크")

    track = st.radio(
        "데이터 트랙",
        ["synthetic", "steel"],
        format_func=lambda t: "합성 설비(이상 주입)" if t == "synthetic" else "실 제철소(UCI)",
    )
    track_default_tokens = config.MAX_TOKENS_BY_TRACK.get(track, config.DEFAULT_MAX_TOKENS)
    slider_max = max(2048, track_default_tokens)
    max_tokens = st.slider(
        "max_tokens (답변 길이 상한)", 256, slider_max, track_default_tokens, step=128,
        help="트랙 기본값에서 시작 — steel은 답변이 길어 더 큼. 직접 조절 가능.",
    )

# ── 데이터 차트 ───────────────────────────────────────────────────────
st.subheader("1) 데이터 사용 패턴")
if track == "synthetic":
    render_synthetic_chart()
else:
    render_steel_chart()

# ── 질문 → 비교 ───────────────────────────────────────────────────────
st.subheader("2) 질문 → 3백엔드 비교")

canned = [q["question"] for q in QUESTIONS if q["track"] == track]
options = ["(직접 입력)"] + canned
pick = st.selectbox("예시 질문", options, help="evals/questions.py 의 질문 모음")
default_q = "" if pick == "(직접 입력)" else pick
question = st.text_area("질문", value=default_q, height=90)

run = st.button("▶ 3개 백엔드로 실행", type="primary", disabled=not (providers and question.strip()))

if run:
    with st.spinner("RAG 검색 + 백엔드 실행 중…"):
        guidelines, results = pipe.answer(question.strip(), track, max_tokens=max_tokens)

    srcs = list(dict.fromkeys(g.source for g in guidelines))
    st.info("🔎 검색된 가이드라인 출처: " + (", ".join(srcs) if srcs else "(없음)"))

    cols = st.columns(len(results))
    for col, r in zip(cols, results):
        label, is_local = _PROVIDER_META.get(r.provider, (r.provider, False))
        render_result_column(col, label, is_local, r)

    with st.expander("검색된 가이드라인 원문 보기"):
        for g in guidelines:
            st.markdown(f"**[{g.source}]** · 거리 {g.distance:.3f}")
            st.text(g.text)
