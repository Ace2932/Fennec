"""POSTURE SEARCH — what is the MAXIMUM step-up clearance the robot can make,
using EVERY available lever at once? (#142)

WHY THIS EXISTS
---------------
Every earlier probe fixed most of the robot and swept ONE lever:
  probe_lift_force    : foot-vs-hip range at a fixed body pose, one knee branch
  probe_lift_envelope : force/power envelope, and swing abduction alone
Both asked "how far can the swing foot rise RELATIVE TO ITS HIP" while the body
stayed at a fixed height. But the quantity that actually clears a riser is

    foot clearance above the tread  =  HIP HEIGHT  -  (hip -> foot fold)

and the hip height is set by the OTHER THREE LEGS. Extending/crouching the stance
legs and pitching the body raise the swing hip for free — clearance the swing leg
never has to pay for out of its own (fold-capped) range. Hip abduction is ONE lever,
not the lever.

So: search the posture space jointly. Free variables
  * body height z_b            (stance legs crouch / extend — the "splayed crouch")
  * body pitch                 (nose-up raises the FRONT hips; rear legs must cope)
  * swing-foot lateral offset  (hip abduction on the swinging, unloaded leg)
subject to ALL FOUR legs solving IK inside their joint limits (the +50 deg hfe fold
stop, the haa -15/+40 range, kfe +-109) with either knee branch.

Maximise the swing foot's height above the lower tread. Report which lever the
optimum actually spends, and what binds at the edge — the point is to find out
whether abduction is even NECESSARY once body height and pitch are in play.

  ../../.venv/bin/python probe_posture_search.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# reuse the climber's exact geometry + the validated IK (never re-derive either)
from scripted_crawl_climber import (   # noqa: E402
    PARAMS, HB, SIDE, LAT, _X0, _Z0, LEG_NAMES, rot_pitch,
)
from nova_locomotion.kinematics.leg_ik import (   # noqa: E402
    inverse_kinematics, Unreachable,
)
from build_mjcf import HAA_IN, HAA_OUT, KFE, hfe_range   # noqa: E402
from terrain import STAIR_RISE   # noqa: E402

# PER-LEG, END-KEYED (#180). These used to be ONE pair built from
# (-HFE_EXT, +HFE_FOLD) — the FRONT's range — and applied to all four legs.
# The MJCF hfe axis is "0 1 0" everywhere, so canonical +hfe swings every foot
# REARWARD: toward the trunk at the front, AWAY from it at the rear. The
# conservative chassis fold cap therefore lands on OPPOSITE SIGNS at the two
# ends, which is exactly what build_mjcf.hfe_range(sx) returns and what #163/
# #164 established for the runtime gate. Applying the front's pair to the rear
# let this search spend rear fold it does not have: the pre-fix optimum planted
# both rear legs at hfe -52.4 deg against a -50.0 deg rear cap.
_HFE = {sx: hfe_range(sx) for sx in (1, -1)}
LO_LEG = np.array([[-HAA_IN, _HFE[sx][0], -KFE] for sx in np.sign(HB[:, 0])])
HI_LEG = np.array([[HAA_OUT, _HFE[sx][1], KFE] for sx in np.sign(HB[:, 0])])
# Guard the whole point of the fix: front and rear must NOT share an hfe row.
# A future refactor that collapses these back to one pair fails here rather
# than silently re-permitting rear folds the chassis gate refuses.
assert LO_LEG[0][1] != LO_LEG[2][1] and HI_LEG[0][1] != HI_LEG[2][1], \
    "hfe range must be END-KEYED (front != rear) — see #180"
JN = ["haa", "hfe", "kfe"]


def leg_solve(foot_w, hip_w, R, side, leg_i):
    """Validated IK for one leg from a world foot + world hip + body rotation.
    Returns (theta, knee_branch) for whichever branch is in range, else None."""
    vec_body = R.T @ (foot_w - hip_w)
    canon = (vec_body[0], side * vec_body[1], vec_body[2])
    for kf in (False, True):
        try:
            t = np.array(inverse_kinematics(canon, PARAMS, knee_forward=kf))
        except Unreachable:
            continue
        if np.all(t >= LO_LEG[leg_i] - 1e-9) and np.all(t <= HI_LEG[leg_i] + 1e-9):
            return t, kf
    return None


def binding(foot_w, hip_w, R, side, leg_i):
    """Diagnose WHY a target failed: which joint left range, or unreachable."""
    vec_body = R.T @ (foot_w - hip_w)
    canon = (vec_body[0], side * vec_body[1], vec_body[2])
    msgs = []
    for kf in (False, True):
        try:
            t = np.array(inverse_kinematics(canon, PARAMS, knee_forward=kf))
        except Unreachable as e:
            msgs.append(f"branch{int(kf)}: unreachable ({e})")
            continue
        lo, hi = LO_LEG[leg_i], HI_LEG[leg_i]
        bad = [f"{JN[i]} {t[i]:+.3f} outside [{lo[i]:+.3f},{hi[i]:+.3f}]"
               for i in range(3) if t[i] < lo[i] - 1e-9 or t[i] > hi[i] + 1e-9]
        msgs.append(f"branch{int(kf)}: " + ("; ".join(bad) if bad else "OK"))
    return " | ".join(msgs)


def stance_ok(z_b, pitch, footholds, swing_i):
    """Can the 3 planted legs hold the body at this pose?"""
    R = rot_pitch(pitch)
    Pb = np.array([0.0, 0.0, z_b])
    for i in range(4):
        if i == swing_i:
            continue
        hip_w = Pb + R @ HB[i]
        if leg_solve(footholds[i], hip_w, R, SIDE[i], i) is None:
            return False, R, Pb
    return True, R, Pb


def max_swing_height(z_b, pitch, dy, footholds, swing_i):
    """Highest the swing foot can be lifted at this body pose + lateral offset."""
    ok, R, Pb = stance_ok(z_b, pitch, footholds, swing_i)
    if not ok:
        return None
    hip_w = Pb + R @ HB[swing_i]
    fx = footholds[swing_i][0]
    fy = footholds[swing_i][1] + SIDE[swing_i] * dy
    # bisect UP from the foothold itself (the known-good height); if the foot cannot
    # even sit at its own foothold with this lateral offset, the pose is infeasible.
    lo = float(footholds[swing_i][2])
    hi = lo + 0.30
    if leg_solve(np.array([fx, fy, lo]), hip_w, R, SIDE[swing_i], swing_i) is None:
        return None
    for _ in range(44):                       # bisect the highest feasible foot z
        mid = 0.5 * (lo + hi)
        if leg_solve(np.array([fx, fy, mid]), hip_w, R, SIDE[swing_i], swing_i) is not None:
            lo = mid
        else:
            hi = mid
    return lo


def main():
    swing_i = LEG_NAMES.index("FL")           # a FRONT leg — the one that meets the riser
    # nominal footholds: hip xy + the canonical neutral foot, all on the lower tread
    footholds = np.array([[HB[i, 0] + _X0, HB[i, 1] + SIDE[i] * LAT, 0.0]
                          for i in range(4)])
    # body height that puts every foot exactly on its (z=0) foothold in the neutral
    # pose: hip sits HB.z above the base, and the neutral foot is _Z0 below the hip.
    z_nom = -HB[0, 2] - _Z0

    print("=" * 100)
    print("POSTURE SEARCH — max swing-foot clearance over body height, pitch, abduction")
    print(f"swing leg = {LEG_NAMES[swing_i]}; nominal body height {z_nom*100:.2f} cm")
    print(f"joint ranges: haa [{LO_LEG[0][0]:+.3f},{HI_LEG[0][0]:+.3f}]  "
          f"hfe FRONT [{LO_LEG[0][1]:+.3f},{HI_LEG[0][1]:+.3f}] "
          f"REAR [{LO_LEG[2][1]:+.3f},{HI_LEG[2][1]:+.3f}]  "
          f"kfe [{LO_LEG[0][2]:+.3f},{HI_LEG[0][2]:+.3f}]  "
          f"(hfe fold cap = the chassis riser skirt, END-KEYED per #180)")
    print("=" * 100)

    base = max_swing_height(z_nom, 0.0, 0.0, footholds, swing_i)
    print(f"\n-- BASELINE (what the climber does: fixed body height, no pitch, no abduction) --")
    print(f"  max swing-foot clearance = {base*100:.2f} cm")

    # --- one lever at a time, to see what each is worth on its own ------------
    print("\n-- EACH LEVER ALONE --")
    bz = max(((max_swing_height(z, 0.0, 0.0, footholds, swing_i), z)
              for z in np.arange(0.13, 0.241, 0.0025)), key=lambda r: (r[0] or -9))
    print(f"  body height only : {bz[0]*100:6.2f} cm  at z_b={bz[1]*100:.1f} cm "
          f"({(bz[1]-z_nom)*100:+.1f} cm vs nominal)")
    bp = max(((max_swing_height(z_nom, p, 0.0, footholds, swing_i), p)
              for p in np.arange(-0.40, 0.401, 0.02)), key=lambda r: (r[0] or -9))
    print(f"  pitch only       : {bp[0]*100:6.2f} cm  at pitch={np.degrees(bp[1]):+.1f} deg")
    ba = max(((max_swing_height(z_nom, 0.0, d, footholds, swing_i), d)
              for d in np.arange(0.0, 0.121, 0.005)), key=lambda r: (r[0] or -9))
    print(f"  abduction only   : {ba[0]*100:6.2f} cm  at dy={ba[1]*100:+.1f} cm")

    # --- joint search over all three -----------------------------------------
    print("\n-- ALL THREE TOGETHER (joint search) --")
    best = (-9.0, None)
    for z in np.arange(0.13, 0.241, 0.0025):
        for p in np.arange(-0.40, 0.401, 0.02):
            if not stance_ok(z, p, footholds, swing_i)[0]:
                continue
            for d in np.arange(0.0, 0.121, 0.005):
                h = max_swing_height(z, p, d, footholds, swing_i)
                if h is not None and h > best[0]:
                    best = (h, (z, p, d))
    h, (z, p, d) = best
    print(f"  MAX clearance = {h*100:.2f} cm  at body z={z*100:.1f} cm "
          f"({(z-z_nom)*100:+.1f} cm), pitch={np.degrees(p):+.1f} deg, abduction={d*100:.1f} cm")
    print(f"  gain over baseline: {(h-base)*100:+.2f} cm ({h/base:.2f}x)")

    # what does the optimum posture actually look like?
    ok, R, Pb = stance_ok(z, p, footholds, swing_i)
    print("\n  posture at the optimum (haa, hfe, kfe in rad; * = at a range limit):")
    for i in range(4):
        hip_w = Pb + R @ HB[i]
        if i == swing_i:
            fw = np.array([footholds[i, 0], footholds[i, 1] + SIDE[i] * d, h])
        else:
            fw = footholds[i]
        r = leg_solve(fw, hip_w, R, SIDE[i], i)
        if r is None:
            print(f"    {LEG_NAMES[i]}: (no solution)")
            continue
        t, kf = r
        flags = "".join("*" if (abs(t[j]-LO_LEG[i][j]) < 2e-3 or abs(t[j]-HI_LEG[i][j]) < 2e-3) else " "
                        for j in range(3))
        tag = "SWING" if i == swing_i else "stance"
        print(f"    {LEG_NAMES[i]} {tag:6}: {np.round(t,3)} {flags} knee_fwd={kf}")

    # --- is abduction NECESSARY once height+pitch are used? -------------------
    print("\n-- IS ABDUCTION NECESSARY? (best with abduction FORCED to 0) --")
    b0 = (-9.0, None)
    for zz in np.arange(0.13, 0.241, 0.0025):
        for pp in np.arange(-0.40, 0.401, 0.02):
            hh = max_swing_height(zz, pp, 0.0, footholds, swing_i)
            if hh is not None and hh > b0[0]:
                b0 = (hh, (zz, pp))
    print(f"  best without any abduction: {b0[0]*100:.2f} cm "
          f"(z={b0[1][0]*100:.1f} cm, pitch={np.degrees(b0[1][1]):+.1f} deg)")
    print(f"  abduction is worth a further {(h-b0[0])*100:+.2f} cm on top")

    # --- what does this mean for real risers? --------------------------------
    print("\n-- DEMAND vs BUDGET, per stair level --")
    print(f"  {'level':>6} {'riser':>8} {'demand +2.5cm':>15} {'baseline':>10} {'best':>8}  verdict")
    for lvl in (0.25, 0.5, 0.75, 1.0):
        riser = STAIR_RISE * lvl
        demand = riser + 0.025
        print(f"  {lvl:6.2f} {riser*100:7.1f}cm {demand*100:14.1f}cm "
              f"{base*100:9.2f}cm {h*100:7.2f}cm  "
              f"{'baseline OK' if base >= demand else ('needs posture' if h >= demand else 'OUT OF REACH')}")


if __name__ == "__main__":
    main()
