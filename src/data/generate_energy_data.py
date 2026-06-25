"""Generate synthetic factory energy time-series — a stand-in for real FEMS data.

Model: each equipment has an always-on **idle** load plus an **active** load that
is added only during weekday work hours. So equipment that should be resting
(nights, weekends) sits near its idle level — which makes "running when it should
be idle" a clearly detectable anomaly. Three anomalies are injected for the
analysis layer to find and explain.

Run:  python -m src.data.generate_energy_data
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "energy" / "plant_energy.csv"

# idle: off-hours base load (kW); active: added during weekday work hours (kW); noise sd (kW)
EQUIPMENT = {
    "air_compressor": dict(idle=30, active=130, noise=6),
    "hvac": dict(idle=20, active=120, noise=6),
    "production_line_1": dict(idle=15, active=320, noise=15),
    "production_line_2": dict(idle=15, active=300, noise=15),
    "lighting": dict(idle=3, active=30, noise=1.5),
}


def _work_shape(hours: np.ndarray) -> np.ndarray:
    """0..1 curve peaking midday, zero outside an ~6:00-18:00 day shift."""
    return np.clip(np.sin((hours - 6) / 12 * np.pi), 0, None)


def generate(days: int = 30, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    periods = days * 24
    idx = pd.date_range("2026-05-01", periods=periods, freq="h")
    shift = _work_shape(idx.hour.to_numpy())
    is_workday = (idx.dayofweek.to_numpy() < 5).astype(float)  # 0 on weekends

    frames = []
    for name, p in EQUIPMENT.items():
        # idle always on; active load only during weekday work hours
        power = p["idle"] + p["active"] * shift * is_workday
        power = power + rng.normal(0, p["noise"], periods)
        frames.append(
            pd.DataFrame({"timestamp": idx, "equipment": name, "power_kw": power})
        )

    df = pd.concat(frames, ignore_index=True)
    df = _inject_anomalies(df)
    df["power_kw"] = df["power_kw"].clip(lower=0).round(1)
    return df


def _inject_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Inject three faults that stand out clearly against the idle baseline."""
    ts = df["timestamp"]
    hour = ts.dt.hour

    # 1. Air compressor stuck near full load all weekend (failed unloader / major leak).
    #    Normal weekend idle ~30 kW -> stuck at ~150 kW.
    weekend = (ts >= "2026-05-16") & (ts < "2026-05-18")
    df.loc[weekend & (df["equipment"] == "air_compressor"), "power_kw"] = 150.0

    # 2. Lighting left on overnight for a week (control schedule misconfigured).
    #    Normal night idle ~3 kW -> stuck at ~30 kW.
    night = (hour >= 22) | (hour <= 4)
    week = (ts >= "2026-05-20") & (ts < "2026-05-27")
    df.loc[night & week & (df["equipment"] == "lighting"), "power_kw"] = 30.0

    # 3. HVAC control fault spike on a weekday afternoon (2026-05-08 is a Friday).
    #    Normal weekday afternoon load ~110 kW -> fault spike to 320 kW.
    spike = (ts >= "2026-05-08 13:00") & (ts <= "2026-05-08 16:00")
    df.loc[spike & (df["equipment"] == "hvac"), "power_kw"] = 320.0

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
