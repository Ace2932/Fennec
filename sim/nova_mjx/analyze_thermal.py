"""I^2t leaky-bucket (#428 research; docs/research/2026-09-26-servo-thermal-guard.md) separation: walking/climbing vs a jam, from thermal_trace.py npz files.

bucket E: dE/dt = (i^2 - E)/tau, E0 = steady walking mean (stationary gait).
Jam at current fraction j: E(t) = j^2 + (E0 - j^2) exp(-t/tau) -> time to cross threshold th.
"""
import sys
import numpy as np

DT = 0.02
TAUS = (2.0, 5.0, 10.0, 30.0)
JT = {"haa": 0, "hfe": 1, "kfe": 2}


def bucket(i2, tau, e0):
    a = DT / tau
    e = np.full(i2.shape[1:], e0, np.float64)
    peak = e.copy()
    for t in range(i2.shape[0]):
        e += a * (i2[t] - e)
        peak = np.maximum(peak, e)
    return peak


def main(files):
    for f in files:
        d = np.load(f)
        print(f"\n=== {f}")
        for sc in [s for s in ("fwd", "mixed", "curb", "stand") if f"{s}_i" in d]:
            i = d[f"{sc}_i"].astype(np.float64)          # T,n,12
            alive = d[f"{sc}_alive"].astype(bool)         # T,n
            i = np.where(alive[..., None], i, 0.0)       # after a fall: zero (bucket peaks are taken before it)
            T = alive.sum(0)                               # steps alive per episode
            ok = T > 50
            i2 = i ** 2
            up = d[f"{sc}_up"].mean() if sc == "curb" else float("nan")
            print(f"-- {sc}: eps {len(T)} fell {1 - alive[-1].mean():.0%} up {up:.0%} "
                  f"servo-unloads/robot {d[f'{sc}_trip'][-1].mean():.2f}")
            for name, k in JT.items():
                x = i2[..., k::3]                           # T,n,4
                mean_ep = x.sum(0) / np.maximum(T, 1)[:, None]      # n,4
                sat = ((i[..., k::3] >= 0.9) & alive[..., None]).sum(0) / np.maximum(T, 1)[:, None]
                m = float(mean_ep[ok].mean())
                # chatter check: i^2 of the 0.2 s moving-average current (gait band only)
                ik = i[..., k::3]
                ker = np.ones(10) / 10
                ilp = np.apply_along_axis(lambda v: np.convolve(v, ker, "same"), 0, ik)
                lp_frac = float((ilp ** 2)[:, ok].sum() / max(x[:, ok].sum(), 1e-9))
                row = (f"   {name}: mean i^2 {m:.3f} (worst joint-ep {mean_ep[ok].max():.3f}, "
                       f"<5Hz share {lp_frac:.2f})  "
                       f"time@i>=0.9 {100 * sat[ok].mean():.1f}%  bucket peak p99/max:")
                for tau in TAUS:
                    pk = bucket(x, tau, m)[ok]
                    row += f"  tau{tau:g}s {np.percentile(pk, 99):.2f}/{pk.max():.2f}"
                print(row)


if __name__ == "__main__":
    main(sys.argv[1:])
