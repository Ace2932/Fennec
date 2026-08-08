"""STATIC LIFT-FORCE CAPACITY vs LEG CONFIGURATION (#142 follow-up).

THE QUESTION
------------
The scripted crawl-climb expert fails to ascend risers, and scaling hfe/kfe stall
torque 4x barely moves it (+1.5 cm peak base ascent) — so the wall is not raw
torque at the CURRENT configuration. The open hypothesis: could the robot climb by
OPENING THE HIPS (haa abduction/adduction, the 2.9 N*m servo the gait barely uses)
and pushing with a TUCKED femur/tibia, instead of the near-nominal stance the
expert commands?

That is a statics question with an exact answer, so compute it instead of arguing.

METHOD
------
For a planted foot, the joint torques needed to hold a foot force f are tau = J^T f
(J = d(foot)/d(theta) in the hip frame, 3x3). For a PURELY VERTICAL foot force
f = (0, 0, fz):   tau_i = J[2, i] * fz
so the largest supportable fz before some joint saturates is

    fz_max = min_i ( tau_max_i / |J[2, i]| )

and the binding joint is the argmin. Sweep the configuration and read off both.
This is the leg's ability to PUSH THE BODY UP — exactly the positive work a stair
ascent needs — as a function of how splayed and how tucked the leg is.

Torque limits are the MJCF's (build_mjcf EFF_HIP/EFF_LEG): haa 2.9, hfe/kfe 1.8 N*m.
Geometry + IK/FK come from the validated nova_locomotion leg model (never rewritten).

  ../../.venv/bin/python probe_lift_force.py
"""
import os
import sys

import numpy as np

_PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_PROJ, "ros2_ws", "src", "nova_locomotion"))
# nova_ops too: leg_ik imports the chassis ROM envelope from
# nova_ops.rom_envelope (it cannot live in nova_locomotion — nova_locomotion.node
# already imports nova_ops, so that direction would be a package cycle).
sys.path.insert(0, os.path.join(_PROJ, "ros2_ws", "src", "nova_ops"))
from nova_locomotion.kinematics.leg_ik import (   # noqa: E402
    LegParams, forward_kinematics, inverse_kinematics, Unreachable,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_mjcf import (   # noqa: E402
    EFF_HIP, EFF_LEG, HAA_IN, HAA_OUT, HFE_FOLD, HFE_EXT, KFE,
)

P = LegParams()
TAU = np.array([EFF_HIP, EFF_LEG, EFF_LEG])          # haa, hfe, kfe (N*m)
JNAMES = ["haa", "hfe", "kfe"]
# joint ranges as emitted into nova.xml (canonical/left-leg sign convention).
# END-AGNOSTIC, and that is MEASURED, not assumed (#180): the hfe cap sits on
# opposite signs front vs rear, but every pose this sweep visits lands in
# hfe +0.134..+0.853 rad — inside the intersection of both ends' ranges
# (+-0.873), so the numbers below hold for a front OR a rear leg. If a future
# sweep widens past +-0.873 this stops being true; use build_mjcf.hfe_range(sx)
# then, as probe_lift_envelope.py does.
LO = np.array([-HAA_IN, -HFE_EXT, -KFE])
HI = np.array([HAA_OUT, HFE_FOLD, KFE])

# total sprung mass: trunk 2.83 + 4 legs x (hip .0836 + upper .1219 + lower .1110
# + foot .0039) — build_mjcf LINK_I/BASE_I.
MASS = 2.83 + 4 * (0.0836 + 0.1219 + 0.1110 + 0.0039)
WEIGHT = MASS * 9.81


def fk(theta):
    return np.array(forward_kinematics(tuple(theta), P))


def jacobian(theta, h=1e-6):
    """Numeric d(foot_xyz)/d(theta) in the canonical hip frame (3x3)."""
    J = np.zeros((3, 3))
    for i in range(3):
        tp = np.array(theta, dtype=float); tp[i] += h
        tm = np.array(theta, dtype=float); tm[i] -= h
        J[:, i] = (fk(tp) - fk(tm)) / (2 * h)
    return J


def lift_capacity(theta):
    """(fz_max N, binding joint name). Vertical foot force before a joint saturates."""
    J = jacobian(theta)
    dz = np.abs(J[2, :])
    with np.errstate(divide="ignore"):
        cap = np.where(dz > 1e-9, TAU / np.maximum(dz, 1e-12), np.inf)
    i = int(np.argmin(cap))
    return float(cap[i]), JNAMES[i]


def in_limits(theta):
    return bool(np.all(theta >= LO - 1e-9) and np.all(theta <= HI + 1e-9))


def why_blocked(t):
    """Which joint left its range, and by how much (rad)."""
    out = []
    for i, nm in enumerate(JNAMES):
        if t[i] < LO[i]:
            out.append(f"{nm} {t[i]:+.3f} < min {LO[i]:+.3f} (over by {LO[i]-t[i]:.3f})")
        elif t[i] > HI[i]:
            out.append(f"{nm} {t[i]:+.3f} > max {HI[i]:+.3f} (over by {t[i]-HI[i]:.3f})")
    return "; ".join(out)


def solve(x, y, z, reason=False):
    """IK to a canonical hip-frame foot target; None if unreachable/out of range."""
    try:
        t = np.array(inverse_kinematics((x, y, z), P, knee_forward=False))
    except Unreachable as e:
        return (None, f"kinematically unreachable: {e}") if reason else None
    if in_limits(t):
        return (t, "") if reason else t
    return (None, f"JOINT RANGE: {why_blocked(t)}") if reason else None


def row(tag, theta, extra=""):
    fz, who = lift_capacity(theta)
    foot = fk(theta)
    # per-leg share needed: 3-leg support during a crawl -> weight/3 per stance leg
    share = WEIGHT / 3.0
    print(f"  {tag:<22} haa={theta[0]:+.3f} hfe={theta[1]:+.3f} kfe={theta[2]:+.3f} "
          f"| foot y={foot[1]*100:+6.2f} z={foot[2]*100:+7.2f} cm "
          f"| fz_max {fz:7.2f} N ({fz/share:4.2f}x the {share:.1f} N share) "
          f"| binds {who}{extra}")


def main():
    print("=" * 100)
    print("STATIC VERTICAL LIFT CAPACITY per leg — fz_max = min_i tau_i / |dz/dtheta_i|")
    print(f"mass {MASS:.2f} kg -> weight {WEIGHT:.1f} N; 3-leg crawl support "
          f"-> {WEIGHT/3:.1f} N per stance leg")
    print(f"torque limits: haa {EFF_HIP}, hfe {EFF_LEG}, kfe {EFF_LEG} N*m")
    print("=" * 100)

    # --- the nominal stance the gait actually uses ---------------------------
    from env import DEFAULT_POSE   # noqa: E402  (imported late: pulls jax)
    nom = np.array([float(v) for v in DEFAULT_POSE[:3]])
    x0, d0, z0 = fk(nom)
    print("\n-- NOMINAL STANCE (DEFAULT_POSE, what the crawl expert commands) --")
    row("nominal", nom)

    # --- H1: SPLAY the hip. Keep the foot at the same HEIGHT and same fore/aft,
    #     push it laterally outboard/inboard -> haa opens. Does lift capacity rise?
    print("\n-- H1: HIP SPLAY (foot held at nominal height, swept laterally) --")
    print("   (+y = outboard/abducted, -y = tucked under the body/adducted)")
    for dy in (-0.04, -0.02, 0.0, 0.02, 0.04, 0.06, 0.08, 0.10):
        t = solve(x0, d0 + dy, z0)
        if t is None:
            print(f"  {'dy=%+.0f cm' % (dy*100):<22} UNREACHABLE or outside joint range")
            continue
        row(f"dy={dy*100:+.0f} cm", t)

    # --- H2: TUCK. Raise the foot toward the hip (shorter leg = more folded) at
    #     the nominal lateral offset. This is "crouch/tuck then push".
    print("\n-- H2: KNEE TUCK (foot raised toward the hip = shorter, more folded leg) --")
    print("   THE STEP-UP MOVE: to place a foot on a riser the leg must SHORTEN by")
    print("   riser + clearance. How far can it shorten before something stops it?")
    for dz in (0.0, 0.01, 0.02, 0.03, 0.035, 0.04, 0.05, 0.06, 0.08):
        t, why = solve(x0, d0, z0 + dz, reason=True)   # z0 negative (foot below hip)
        if t is None:
            print(f"  {'tuck=%+.1f cm' % (dz*100):<22} BLOCKED — {why}")
            continue
        row(f"tuck={dz*100:+.1f} cm", t)

    # how far can the leg shorten at the BEST splay, and is that enough for a riser?
    print("\n-- H2b: max leg shortening available, per splay (the step-up budget) --")
    for dy in (0.0, 0.02, 0.04, 0.06):
        lo, hi = 0.0, 0.12
        for _ in range(40):                      # bisect the largest feasible tuck
            mid = 0.5 * (lo + hi)
            if solve(x0, d0 + dy, z0 + mid) is not None:
                lo = mid
            else:
                hi = mid
        _t, why = solve(x0, d0 + dy, z0 + hi, reason=True)
        print(f"  splay dy={dy*100:+.0f} cm -> max shorten {lo*100:5.2f} cm  "
              f"(first blocked by: {why})")
    print(f"\n  STAIR DEMAND: riser {2.0:.1f} cm (level 0.25) + swing clearance "
          f"{5.0:.1f} cm (CLEARANCE in the climber) = {7.0:.1f} cm of shortening.")

    # --- H3: the combination the question proposes — splay AND tuck together ---
    print("\n-- H3: SPLAY + TUCK together (the proposed climbing posture) --")
    best = (0.0, None, None)
    for dy in (0.0, 0.02, 0.04, 0.06, 0.08):
        for dz in (0.0, 0.02, 0.04, 0.06):
            t = solve(x0, d0 + dy, z0 + dz)
            if t is None:
                continue
            fz, who = lift_capacity(t)
            if fz > best[0]:
                best = (fz, (dy, dz), (t, who))
    for dy in (0.0, 0.04, 0.08):
        for dz in (0.0, 0.04):
            t = solve(x0, d0 + dy, z0 + dz)
            if t is not None:
                row(f"dy={dy*100:+.0f} tuck={dz*100:+.0f}", t)
    if best[1]:
        dy, dz = best[1]
        t, who = best[2]
        print(f"\n  BEST in sweep: dy={dy*100:+.0f} cm tuck={dz*100:+.0f} cm -> "
              f"fz_max {best[0]:.2f} N (binds {who}), "
              f"{best[0]/(WEIGHT/3):.2f}x the per-leg share")

    # --- H4: how much of fz_max does each JOINT contribute? Which one is the
    #     actual ceiling at nominal, and does haa ever become the binding one? ---
    print("\n-- H4: per-joint vertical-force ceiling at nominal stance --")
    J = jacobian(nom)
    for i, nm in enumerate(JNAMES):
        dz_i = abs(J[2, i])
        cap = TAU[i] / dz_i if dz_i > 1e-9 else float("inf")
        print(f"  {nm}: |dz/dtheta| = {dz_i:.4f} m/rad -> alone caps fz at "
              f"{cap:8.2f} N  (tau_max {TAU[i]} N*m)")
    print("\n  NOTE: a joint with |dz/dtheta| ~ 0 has NO vertical authority in this pose —"
          "\n  it cannot help lift no matter how much stall torque it has.")


if __name__ == "__main__":
    main()
