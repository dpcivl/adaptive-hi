"""Summarize energy time-series into a compact, LLM-readable brief.

The brief must preserve the anomaly *signal* (so the model can find it) without
*solving* the detection for the model — that detection is the task we compare the
backends on. So we give contextual aggregates (per-bucket means + the max and
when it occurred), not pre-flagged anomalies.

Two shapes are supported via separate functions returning the same DataBrief:
- summarize_equipment_data: synthetic per-equipment data (timestamp, equipment, power_kw)
- summarize_plant_data:     real UCI steel plant-level data (15-min, Usage_kWh, ...)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

_BUCKETS = ("평일주간", "평일야간", "주말")


@dataclass
class DataBrief:
    title: str
    text: str  # the LLM-readable summary
    query_hint: str  # used to retrieve relevant guidelines from the RAG index


def summarize_equipment_data(df: pd.DataFrame) -> DataBrief:
    """Per-equipment mean/max split by time bucket.

    Each hour falls in exactly one bucket (평일주간 06-22 / 평일야간 / 주말). The
    per-bucket max is what surfaces "running when it should idle" anomalies that a
    single global max would hide behind a normal weekday peak.
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    hour = df["timestamp"].dt.hour
    weekend = df["timestamp"].dt.dayofweek >= 5
    night = (hour >= 22) | (hour < 6)
    df["bucket"] = np.where(weekend, "주말", np.where(night, "평일야간", "평일주간"))

    start, end = df["timestamp"].min(), df["timestamp"].max()
    lines = [
        f"기간: {start:%Y-%m-%d} ~ {end:%Y-%m-%d} (시간당 kW)",
        f"총 사용량: {df['power_kw'].sum():,.0f} kWh",
        "",
        "설비별 시간대 프로파일 (평균/최대 kW) — 평일주간(06-22) · 평일야간 · 주말:",
    ]
    for eq in sorted(df["equipment"].unique()):
        s = df[df["equipment"] == eq]
        parts = []
        for b in _BUCKETS:
            p = s.loc[s["bucket"] == b, "power_kw"]
            parts.append(f"{b} 평균{p.mean():.0f}/최대{p.max():.0f}" if len(p) else f"{b} -")
        lines.append(f"- {eq}: " + " · ".join(parts))

    return DataBrief(
        title="공장 설비별 에너지 사용 요약",
        text="\n".join(lines),
        query_hint="공장 설비별 전력 이상 탐지 및 에너지 절감 압축공기 공조 조명 피크",
    )


def summarize_plant_data(df: pd.DataFrame) -> DataBrief:
    """Plant-level profile for the UCI steel dataset (real factory data)."""
    df = df.copy()
    df["dt"] = pd.to_datetime(df["date"], format="%d/%m/%Y %H:%M")
    weekend = df["dt"].dt.dayofweek >= 5

    start, end = df["dt"].min(), df["dt"].max()
    lines = [
        f"기간: {start:%Y-%m-%d} ~ {end:%Y-%m-%d} (15분 간격, {len(df):,}개 측정)",
        f"총 사용량: {df['Usage_kWh'].sum():,.0f} kWh"
        f" / 평균 {df['Usage_kWh'].mean():.1f} / 최대 {df['Usage_kWh'].max():.1f} kWh(15분)",
        "",
        "부하유형(Load_Type)별 비율·평균:",
    ]
    for load_type, g in df.groupby("Load_Type"):
        lines.append(
            f"- {load_type}: {len(g) / len(df) * 100:.0f}% / 평균 {g['Usage_kWh'].mean():.1f} kWh"
        )
    lines += [
        "",
        f"지상역률 평균 {df['Lagging_Current_Power_Factor'].mean():.1f}% (낮을수록 무효전력 손실↑)",
        f"주말 평균 {df.loc[weekend, 'Usage_kWh'].mean():.1f}"
        f" vs 평일 평균 {df.loc[~weekend, 'Usage_kWh'].mean():.1f} kWh",
    ]

    return DataBrief(
        title="공장 전체 전력 사용 요약 (실데이터)",
        text="\n".join(lines),
        query_hint="공장 전력 사용 패턴 분석 에너지 절감 피크 수요 역률 부하",
    )
