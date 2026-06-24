"""Generate synthetic factory energy time-series — a stand-in for real FEMS data.

Produces hourly power draw (kW) per equipment unit with realistic daily and
weekly patterns, plus a few injected anomalies for the LLMs to find and explain.
This is the "energy data" the analysis layer reasons over; the RAG documents
(saving guidelines) only supplement it.

Run:  python -m src.data.generate_energy_data
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "energy" / "plant_energy.csv"

# base load (kW), work-hour swing (kW), gaussian noise sd (kW)
EQUIPMENT = {
    "air_compressor": dict(base=120, swing=40, noise=8),
    "hvac": dict(base=80, swing=60, noise=6),
    "production_line_1": dict(base=200, swing=120, noise=15),
    "production_line_2": dict(base=180, swing=110, noise=15),
    "lighting": dict(base=30, swing=20, noise=2),
}


def _work_hour_shape(hours: np.ndarray) -> np.ndarray:
    """0..1 curve peaking across an 8:00-18:00 shift."""
    shape = np.clip(np.sin((hours - 6) / 12 * np.pi), 0, None)
    return shape


def generate(days: int = 30, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    periods = days * 24
    idx = pd.date_range("2026-05-01", periods=periods, freq="h")
    hours = idx.hour.to_numpy()
    weekday = idx.dayofweek.to_numpy()  # 0=Mon .. 6=Sun
    shift = _work_hour_shape(hours)

    frames = []
    for name, p in EQUIPMENT.items():
        # production lines nearly idle on weekends; support loads partly reduced
        weekend_factor = 0.25 if "production" in name else 0.7
        weekly = np.where(weekday < 5, 1.0, weekend_factor)
        power = p["base"] + p["swing"] * shift * weekly
        power = power + rng.normal(0, p["noise"], periods)
        frames.append(
            pd.DataFrame({"timestamp": idx, "equipment": name, "power_kw": power})
        )

    df = pd.concat(frames, ignore_index=True)
    df = _inject_anomalies(df)
    df["power_kw"] = df["power_kw"].clip(lower=0).round(1)
    return df


def _inject_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Add a handful of obvious faults for the analysis layer to surface."""
    ts = df["timestamp"]

    # 1. Air compressor stuck near full load for a full weekend (leak / failed unloader).
    weekend = (ts >= "2026-05-16") & (ts < "2026-05-18")
    mask = weekend & (df["equipment"] == "air_compressor")
    df.loc[mask, "power_kw"] = 155.0

    # 2. HVAC short-circuit spike one afternoon.
    spike = (ts >= "2026-05-09 13:00") & (ts <= "2026-05-09 16:00")
    df.loc[spike & (df["equipment"] == "hvac"), "power_kw"] += 90.0

    # 3. Lighting left on overnight for a week (control schedule misconfigured).
    night = (ts.dt.hour >= 22) | (ts.dt.hour <= 4)
    week = (ts >= "2026-05-20") & (ts < "2026-05-27")
    df.loc[night & week & (df["equipment"] == "lighting"), "power_kw"] = 28.0

    return df


def main() -> None:
    df = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    total_kwh = df["power_kw"].sum()  # 1h intervals -> kW == kWh per row
    print(f"Wrote {len(df):,} rows to {OUT_PATH}")
    print(f"Equipment: {', '.join(EQUIPMENT)}")
    print(f"Span: {df['timestamp'].min()} .. {df['timestamp'].max()}")
    print(f"Total consumption: {total_kwh:,.0f} kWh")


if __name__ == "__main__":
    main()
