"""Trot tuning score — one number per run, scripted (pure math + CSV CLI).

Roadmap stage 3 item 4 (docs/roadmap-trot-balance.md): the data-driven
tuning loop. Rosbag every run, score IMU pitch/roll RMS + servo load
spikes + lane drift per parameter set, grid the 3-4 gait params against
the score — afternoons of tuning, not weeks, because the measurement is
scripted. The rosbag->CSV export runs on the Jetson later; this scores
the CSV anywhere.

Score (LOWER IS BETTER):

    total = 10*rms_roll + 10*rms_pitch + 1*load_p95 + 1*drift_penalty

Weighting rationale: a good open-loop trot posts roll/pitch RMS in the
0.03-0.08 rad class, sustained load p95 in the 0.3-0.6 stall-fraction
class, and drift_penalty = |lane drift|/1 m (the stage-3 DoD lane is
2 m wide). The 10x on attitude puts all four terms in the same ~0.3-0.8
band, so no single term silently dominates a grid sweep. Change WEIGHTS
deliberately and re-baseline — scores are only comparable within one
weight set.

CSV format (one row per sample at fixed dt):
    roll,pitch,yaw,load_1,...,load_N
  - roll/pitch/yaw: radians (yaw unused today, logged for the drift
    estimator later)
  - load_i: signed STS3215 load, fraction of stall (the /joint_states
    effort[] convention), any number of columns >= 1
  - header row required; extra columns after the loads are ignored

CLI:  python -m nova_locomotion.tools.trot_metrics run.csv \\
          --dt 0.02 --drift 0.15
"""

from __future__ import annotations
import argparse
import csv
import math
from typing import Dict, Sequence

# lower is better; see module docstring before touching
WEIGHTS = {"rms_roll": 10.0, "rms_pitch": 10.0, "load_p95": 1.0, "drift_penalty": 1.0}
_LANE_HALF_WIDTH_M = 1.0  # stage-3 DoD: 2 m lane


def _rms(xs: Sequence[float]) -> float:
    return math.sqrt(sum(x * x for x in xs) / len(xs)) if xs else 0.0


def _p95(xs: Sequence[float]) -> float:
    """95th percentile, nearest-rank (no numpy dependency on purpose)."""
    if not xs:
        return 0.0
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, math.ceil(0.95 * len(s)) - 1))]


def score_run(
    imu_rpy: Sequence[Sequence[float]],
    joint_loads: Sequence[Sequence[float]],
    lane_drift_m: float,
    dt: float,
) -> Dict[str, float]:
    """Score one run. imu_rpy: Nx3 (roll, pitch, yaw) radians;
    joint_loads: NxM signed stall fractions; lane_drift_m: lateral exit
    offset from the lane centerline; dt: sample period (s) — reported
    as duration, the score itself is time-normalized by construction.
    Returns the metric dict incl. total_score (LOWER IS BETTER)."""
    rms_roll = _rms([row[0] for row in imu_rpy])
    rms_pitch = _rms([row[1] for row in imu_rpy])
    load_p95 = _p95([abs(v) for row in joint_loads for v in row])
    drift_penalty = abs(lane_drift_m) / _LANE_HALF_WIDTH_M
    out = {
        "rms_roll": rms_roll,
        "rms_pitch": rms_pitch,
        "load_p95": load_p95,
        "drift_penalty": drift_penalty,
        "duration_s": len(imu_rpy) * dt,
    }
    out["total_score"] = sum(WEIGHTS[k] * out[k] for k in WEIGHTS)
    return out


def _load_csv(path: str):
    """CSV (module-docstring format) -> (imu_rpy, joint_loads)."""
    imu, loads = [], []
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        cols = [c.strip().lower() for c in header]
        if cols[:3] != ["roll", "pitch", "yaw"]:
            raise ValueError(
                f"{path}: expected header roll,pitch,yaw,load_1,... got {header}"
            )
        load_idx = [i for i, c in enumerate(cols) if c.startswith("load")]
        if not load_idx:
            raise ValueError(f"{path}: no load_* columns")
        for row in reader:
            if not row or not row[0].strip():
                continue
            imu.append([float(row[0]), float(row[1]), float(row[2])])
            loads.append([float(row[i]) for i in load_idx])
    return imu, loads


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv_path", help="run CSV: roll,pitch,yaw,load_1,...")
    ap.add_argument("--dt", type=float, default=0.02, help="sample period, s")
    ap.add_argument("--drift", type=float, default=0.0, help="lane drift at run end, m")
    args = ap.parse_args(argv)
    imu, loads = _load_csv(args.csv_path)
    result = score_run(imu, loads, args.drift, args.dt)
    for k in ("rms_roll", "rms_pitch", "load_p95", "drift_penalty", "duration_s"):
        print(f"{k:>14}: {result[k]:.4f}")
    print(f"{'total_score':>14}: {result['total_score']:.4f}  (lower is better)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
