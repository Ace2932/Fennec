"""Trot tuning score: RMS/p95/drift math, weighting, CSV loader."""

import math

import pytest

from nova_locomotion.tools.trot_metrics import (
    WEIGHTS,
    _load_csv,
    _p95,
    _rms,
    score_run,
)


def test_rms_constant_and_sine():
    assert _rms([0.05] * 100) == pytest.approx(0.05)
    sine = [0.1 * math.sin(2 * math.pi * i / 100) for i in range(1000)]
    assert _rms(sine) == pytest.approx(0.1 / math.sqrt(2), rel=1e-3)
    assert _rms([]) == 0.0


def test_p95_nearest_rank():
    xs = list(range(1, 101))  # 1..100
    assert _p95(xs) == 95
    assert _p95([7.0]) == 7.0
    assert _p95([]) == 0.0


def test_score_run_components_and_weighting():
    n = 200
    imu = [[0.04, 0.03, 0.5] for _ in range(n)]  # yaw ignored
    loads = [[0.2, -0.6, 0.3] for _ in range(n)]
    r = score_run(imu, loads, lane_drift_m=-0.25, dt=0.02)
    assert r["rms_roll"] == pytest.approx(0.04)
    assert r["rms_pitch"] == pytest.approx(0.03)
    assert r["load_p95"] == pytest.approx(0.6)  # sign stripped
    assert r["drift_penalty"] == pytest.approx(0.25)  # |drift| / 1 m lane half
    assert r["duration_s"] == pytest.approx(n * 0.02)
    expected = sum(WEIGHTS[k] * r[k] for k in WEIGHTS)
    assert r["total_score"] == pytest.approx(expected)
    # documented weighting: attitude x10, load + drift x1
    assert r["total_score"] == pytest.approx(10 * 0.04 + 10 * 0.03 + 0.6 + 0.25)


def test_lower_is_better_ordering():
    quiet = score_run([[0.01, 0.01, 0]] * 50, [[0.2]] * 50, 0.05, 0.02)
    rough = score_run([[0.10, 0.08, 0]] * 50, [[0.8]] * 50, 0.60, 0.02)
    assert quiet["total_score"] < rough["total_score"]


def test_csv_loader(tmp_path):
    p = tmp_path / "run.csv"
    p.write_text(
        "roll,pitch,yaw,load_1,load_2\n"
        "0.01,0.02,0.0,0.1,-0.2\n"
        "0.03,0.04,0.1,0.5,0.6\n"
        "\n"  # trailing blank line tolerated
    )
    imu, loads = _load_csv(str(p))
    assert imu == [[0.01, 0.02, 0.0], [0.03, 0.04, 0.1]]
    assert loads == [[0.1, -0.2], [0.5, 0.6]]


def test_csv_loader_rejects_bad_header(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("time,roll,pitch\n0,0,0\n")
    with pytest.raises(ValueError):
        _load_csv(str(p))
    q = tmp_path / "noload.csv"
    q.write_text("roll,pitch,yaw\n0,0,0\n")
    with pytest.raises(ValueError):
        _load_csv(str(q))
