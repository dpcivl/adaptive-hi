"""Verify the injected anomalies are clearly detectable vs the normal baseline.

A demo of model anomaly-detection is only meaningful if the data actually
contains a detectable signal. This compares each anomaly window against the
equipment's normal off-period baseline and flags PASS when the anomaly mean is
clearly elevated (>=2x baseline).

Run (after generate_energy_data):  python -m scripts.verify_anomalies
"""
import math
from pathlib import Path

import pandas as pd

CSV = Path(__file__).resolve().parents[1] / "data" / "energy" / "plant_energy.csv"


def _mean(df, equipment, mask) -> float:
    return df[(df["equipment"] == equipment) & mask]["power_kw"].mean()


def main() -> None:
    if not CSV.exists():
        print("No data. Run: python -m src.data.generate_energy_data")
        return

    df = pd.read_csv(CSV, parse_dates=["timestamp"])
    ts = df["timestamp"]
    hour = ts.dt.hour
    night = (hour >= 22) | (hour <= 4)
    weekend = ts.dt.dayofweek >= 5
    weekday = ts.dt.dayofweek < 5
    afternoon = (hour >= 13) & (hour <= 16)

    comp_anom = (ts >= "2026-05-16") & (ts < "2026-05-18")
    light_week = (ts >= "2026-05-20") & (ts < "2026-05-27")
    hvac_spike = (ts >= "2026-05-08 13:00") & (ts <= "2026-05-08 16:00")

    # each baseline is a like-for-like window (same hours/day-type, excluding the anomaly)
    checks = [
        ("air_compressor 주말 고착", "air_compressor", comp_anom, weekend & ~comp_anom),
        ("lighting 야간 방치", "lighting", night & light_week, night & ~light_week),
        ("hvac 스파이크", "hvac", hvac_spike, weekday & afternoon & ~hvac_spike),
    ]

    print(f"{'anomaly':28}{'anomaly_mean':>13}{'baseline':>10}{'ratio':>8}  verdict")
    all_pass = True
    for label, eq, anom_mask, base_mask in checks:
        a = _mean(df, eq, anom_mask)
        b = _mean(df, eq, base_mask)
        # NaN baseline/anomaly (empty window) -> nan ratio -> FAIL, surfacing the gap
        ratio = a / b if (b and not math.isnan(a) and not math.isnan(b)) else float("nan")
        ok = bool(ratio >= 2.0)
        all_pass &= ok
        print(f"{label:28}{a:>13.1f}{b:>10.1f}{ratio:>8.1f}  {'PASS' if ok else 'FAIL'}")

    print("\nAll anomalies detectable." if all_pass else "\nSome anomalies are NOT detectable.")


if __name__ == "__main__":
    main()
