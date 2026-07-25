"""TRUE LIFT ENVELOPE — how much upward force/power CAN a leg make? (#142)

WHY THIS EXISTS
---------------
probe_lift_force.py answered "what vertical force can the leg hold?" with the most
conservative possible question: a PURELY VERTICAL foot force, at ONE pose, with ONE
knee branch. It got 24.7 N (1.84x the 13.4 N per-leg share) and concluded torque
was not the wall. That number is a LOWER BOUND, understated in four ways:

  1. PURE-VERTICAL ONLY. The real feasible foot-force set is the parallelepiped
     F = {f : |(J^T f)_i| <= tau_i} = J^-T Box(tau). Allowing horizontal force
     components can only RAISE the achievable fz — and with mu = 1.2 (nova.xml
     foot/floor friction) horizontal force is cheap. Legs splayed left/right can
     push outward-and-down and have the horizontal parts cancel BETWEEN legs, so
     these are not fictitious forces: with 3 stance legs there is a 3-dimensional
     internal-force space (9 force DOF - 6 wrench constraints).
  2. ONE POSE. Vertical capacity is strongly pose-dependent. |dz/dtheta_kfe| is the
     HORIZONTAL knee->foot offset, so a near-straight (stacked) leg approaches a
     singularity where vertical force capacity diverges — the reason a human locks
     their knees to stand. The nominal stance (hfe +0.60, kfe -1.20) is deeply bent.
  3. ONE KNEE BRANCH. knee_forward=False was assumed; the other elbow solution is a
     different posture with different capacity.
  4. FORCE, NOT POWER. "Can it hold the body" and "can it do the positive work to
     RAISE the body" are different questions. Near a singularity the leg holds
     enormous load but has ~zero vertical foot velocity, so it cannot lift at all.
     The honest lifting metric is POWER, under the motor's torque-speed line:
     available tau_i = tau_stall_i * (1 - |thetadot_i| / omega_noload_i).

This probe computes the real envelope for all four.

  ../../.venv/bin/python probe_lift_envelope.py
"""
import os
import sys

import numpy as np

_PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_PROJ, "ros2_ws", "src", "nova_locomotion"))
from nova_locomotion.kinematics.leg_ik import (   # noqa: E402
    LegParams, forward_kinematics, inverse_kinematics, Unreachable,
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_mjcf import (   # noqa: E402
    EFF_HIP, EFF_LEG, VMAX_HIP, VMAX_LEG, HAA_IN, HAA_OUT, HFE_FOLD, HFE_EXT, KFE,
)

P = LegParams()
TAU = np.array([EFF_HIP, EFF_LEG, EFF_LEG])        # haa, hfe, kfe stall (N*m)
OMG = np.array([VMAX_HIP, VMAX_LEG, VMAX_LEG])     # no-load speed (rad/s)
JN = ["haa", "hfe", "kfe"]
LO = np.array([-HAA_IN, -HFE_EXT, -KFE])
HI = np.array([HAA_OUT, HFE_FOLD, KFE])
MU = 1.2                                            # nova.xml foot/floor friction
MASS = 2.83 + 4 * (0.0836 + 0.1219 + 0.1110 + 0.0039)
WEIGHT = MASS * 9.81
SHARE = WEIGHT / 3.0                                # 3-leg crawl support


def fk(t):
    return np.array(forward_kinematics(tuple(t), P))


def jac(t, h=1e-6):
    J = np.zeros((3, 3))
    for i in range(3):
        a = np.array(t, float); a[i] += h
        b = np.array(t, float); b[i] -= h
        J[:, i] = (fk(a) - fk(b)) / (2 * h)
    return J


def in_lim(t):
    return bool(np.all(t >= LO - 1e-9) and np.all(t <= HI + 1e-9))


def solve(x, y, z, knee_fwd):
    try:
        t = np.array(inverse_kinematics((x, y, z), P, knee_forward=knee_fwd))
    except Unreachable:
        return None
    return t if in_lim(t) else None


# --- the four envelope metrics -------------------------------------------------
def fz_pure(J, tau=TAU):
    """Old metric: max vertical force with a PURELY vertical foot force."""
    dz = np.abs(J[2, :])
    return float(np.min(np.where(dz > 1e-12, tau / np.maximum(dz, 1e-12), np.inf)))


def fz_anydir(J, tau=TAU):
    """Exact max fz over the WHOLE feasible force parallelepiped (no friction cap).
    f = J^-T tau with |tau_i| <= tau_max_i  =>  max fz = sum_i |(J^-T)[2,i]| tau_i."""
    try:
        M = np.linalg.inv(J.T)
    except np.linalg.LinAlgError:
        return np.inf
    return float(np.sum(np.abs(M[2, :]) * tau))


def fz_friction(J, tau=TAU, mu=MU, nphi=36, nr=13):
    """Max fz subject to the friction cone |f_xy| <= mu*fz.
    Along a fixed force DIRECTION u = (r cos p, r sin p, 1): tau = fz * J^T u, so
    fz_max(u) = min_i tau_i / |(J^T u)_i|. Grid over (r, p); r=0 recovers fz_pure."""
    best, bu = 0.0, None
    for r in np.linspace(0.0, mu, nr):
        for p in np.linspace(0.0, 2 * np.pi, nphi, endpoint=False):
            u = np.array([r * np.cos(p), r * np.sin(p), 1.0])
            g = np.abs(J.T @ u)
            if np.all(g < 1e-12):
                continue
            v = float(np.min(np.where(g > 1e-12, tau / np.maximum(g, 1e-12), np.inf)))
            if v > best:
                best, bu = v, (r, p)
    return best, bu


def lift_power(J, vz, mu=MU):
    """Max upward POWER at the foot when the foot is rising at vz (m/s).
    Joint speeds for pure vertical foot motion, then the motor's torque-speed line
    de-rates each joint's available torque, then the friction-capped force max."""
    try:
        td = np.linalg.solve(J, np.array([0.0, 0.0, vz]))
    except np.linalg.LinAlgError:
        return 0.0, 0.0, None
    if np.any(np.abs(td) > OMG):                 # past the no-load speed: no torque
        return 0.0, 0.0, td
    tau_av = TAU * (1.0 - np.abs(td) / OMG)      # linear torque-speed de-rate
    fz, _u = fz_friction(J, tau=tau_av, mu=mu)
    return fz, fz * vz, td


def main():
    np.set_printoptions(suppress=True)
    print("=" * 104)
    print("TRUE LIFT ENVELOPE — per stance leg")
    print(f"mass {MASS:.2f} kg, weight {WEIGHT:.1f} N, 3-leg support -> "
          f"share {SHARE:.1f} N/leg; foot friction mu={MU}")
    print(f"stall {TAU} N*m, no-load {OMG} rad/s")
    print("=" * 104)

    from env import DEFAULT_POSE   # noqa: E402
    nom = np.array([float(v) for v in DEFAULT_POSE[:3]])
    x0, d0, z0 = fk(nom)
    Jn = jac(nom)

    print("\n-- 1. HOW MUCH DID THE PURE-VERTICAL ASSUMPTION COST? (nominal stance) --")
    fp = fz_pure(Jn)
    fa = fz_anydir(Jn)
    ff, bu = fz_friction(Jn)
    print(f"  pure-vertical force only : {fp:8.2f} N  ({fp/SHARE:.2f}x share)   <- the old number")
    print(f"  any direction, mu={MU}    : {ff:8.2f} N  ({ff/SHARE:.2f}x share)   "
          f"[best tilt r={bu[0]:.2f} phi={np.degrees(bu[1]):.0f} deg]")
    print(f"  any direction, no friction cap (theoretical): {fa:8.2f} N  ({fa/SHARE:.2f}x share)")
    print(f"  => the pure-vertical assumption understated capacity by "
          f"{100*(ff/fp - 1):.0f}% at the SAME pose.")

    # --- 2. full workspace sweep, both knee branches --------------------------
    print("\n-- 2. FULL WORKSPACE SWEEP (both knee branches, in joint range) --")
    xs = np.linspace(-0.10, 0.10, 21)
    ys = np.linspace(0.01, 0.17, 33)
    zs = np.linspace(-0.235, -0.08, 32)
    best = {"f": (0, None), "p": (0, None)}
    n_ok = 0
    VZ_REF = 0.02            # 2 cm/s foot rise — a realistic stair-ascent rate
    for kf in (False, True):
        for x in xs:
            for y in ys:
                for z in zs:
                    t = solve(x, y, z, kf)
                    if t is None:
                        continue
                    n_ok += 1
                    J = jac(t)
                    if abs(np.linalg.det(J)) < 1e-7:
                        continue                       # singular: hold-only, no lifting
                    f, _ = fz_friction(J, nphi=12, nr=5)   # coarse in the sweep
                    if f > best["f"][0]:
                        best["f"] = (f, (t.copy(), kf, (x, y, z)))
                    _fz, pw, _td = lift_power(J, VZ_REF)
                    if pw > best["p"][0]:
                        best["p"] = (pw, (t.copy(), kf, (x, y, z), _fz))
    print(f"  {n_ok} reachable in-range poses sampled")
    f, (t, kf, pos) = best["f"]
    print(f"  MAX HOLD force : {f:8.2f} N ({f/SHARE:.2f}x share)  "
          f"knee_fwd={kf} theta={np.round(t,3)} foot={np.round(np.array(pos)*100,1)} cm")
    pw, (t2, kf2, pos2, fz2) = best["p"]
    print(f"  MAX LIFT power : {pw:8.3f} W at vz={VZ_REF*100:.0f} cm/s "
          f"(fz {fz2:.1f} N = {fz2/SHARE:.2f}x share)  "
          f"knee_fwd={kf2} theta={np.round(t2,3)} foot={np.round(np.array(pos2)*100,1)} cm")

    # --- 3. hold vs lift: the singularity trap --------------------------------
    print("\n-- 3. HOLD vs LIFT at the nominal stance (torque-speed de-rate) --")
    print(f"  {'vz (cm/s)':>10} {'fz (N)':>9} {'x share':>8} {'power (W)':>10}  joint speeds (rad/s)")
    for vz in (0.0, 0.01, 0.02, 0.04, 0.06, 0.10, 0.15, 0.20):
        fz, pw, td = lift_power(Jn, vz)
        sp = np.round(td, 2) if td is not None else None
        print(f"  {vz*100:10.1f} {fz:9.2f} {fz/SHARE:8.2f} {pw:10.3f}  {sp}")
    print(f"  body-raise demand: lifting {MASS:.2f} kg at 2 cm/s = "
          f"{WEIGHT*0.02:.2f} W total, {WEIGHT*0.02/3:.2f} W per stance leg")

    # --- 4. the pitch alternative --------------------------------------------
    print("\n-- 4. PITCH LEVERAGE (raise the front hips instead of shortening the leg) --")
    print("  The step-up needs FRONT-FOOT ground clearance. Shortening the leg is one")
    print("  way; pitching the body nose-up is another, and it does NOT spend hfe fold.")
    HALF = 0.1412                       # base -> hip x offset (build_mjcf MOUNT.x)
    for deg in (0, 5, 10, 15, 20, 25):
        r = np.radians(deg)
        print(f"    pitch {deg:3d} deg -> front hip rises {HALF*np.sin(r)*100:5.2f} cm, "
              f"rear hip drops {HALF*np.sin(r)*100:5.2f} cm")
    print(f"  compare: the ENTIRE knee-shortening budget at nominal width is 3.81 cm.")

    # --- 5. SWING-PHASE ABDUCTION: the right way to spend hip range -----------
    # A global stance SPLAY was tried in sim and FAILED (n_unreach 4362 -> 6387):
    # widening EVERY foothold spends the STANCE legs' lateral reach, which they need
    # for FWD_LEAN + CoM sway, so total unreachability rose even though the vertical
    # headroom improved. The swing leg is the one that actually needs clearance, and
    # it is UNLOADED. So abduct ONLY the swinging leg, only mid-swing, and return to
    # a nominal-width foothold at touchdown -> stance geometry is untouched.
    print("\n-- 5. SWING-PHASE ABDUCTION: max foot LIFT vs outboard offset --")
    print("  (swing leg only, unloaded; foothold width at touchdown unchanged)")
    print(f"  {'abduct':>8} | " + " | ".join(f"fore/aft {dx*100:+.0f}cm" for dx in
                                             (-0.02, 0.0, 0.02, 0.04)))
    for ab in (0.0, 0.01, 0.02, 0.03, 0.04, 0.06, 0.08, 0.10):
        cells = []
        for dx in (-0.02, 0.0, 0.02, 0.04):
            lo, hi = 0.0, 0.15
            for _ in range(40):                     # bisect max reachable lift
                mid = 0.5 * (lo + hi)
                ok = any(solve(x0 + dx, d0 + ab, z0 + mid, kf) is not None
                         for kf in (False, True))
                if ok:
                    lo = mid
                else:
                    hi = mid
            cells.append(f"{lo*100:11.2f} cm")
        print(f"  {ab*100:6.0f}cm | " + " | ".join(cells))
    print("\n  DEMAND: to clear a 2.0 cm riser with 2.5 cm of margin the swing foot")
    print("  must gain 4.5 cm; with the climber's default 5 cm margin, 7.0 cm.")


if __name__ == "__main__":
    main()
