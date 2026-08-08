#!/usr/bin/env python3
"""
ab_seam.py — does the kinematic seam (#165) need a retrain, or a resume?

THE QUESTION. The HFE pitch axis sits 11.6 mm toward the trunk of the HAA
station. `build_mjcf.HAA_TO_HFE[0]` was 0.0 until 8e2927a (2026-07-27) fixed it
to 0.0116. Any checkpoint trained before that date learned a robot whose feet
sit 11.6 mm further out, fore and aft, than the one on the bench:

    front feet  +141.2 -> +129.6 mm      support polygon fore-aft
    rear  feet  -141.2 -> -129.6 mm      282.4 -> 259.2 mm  (-8.2 %)
    CoM         unmoved (0.00 mm)        lateral unchanged

Geometry alone cannot answer whether that matters. `domain_randomize` covers
friction, mass, inertia, kp/kv, damping, torque headroom and terrain — and NO
kinematic quantity at all, so the policy has zero trained robustness to this
class, and it is a systematic same-direction bias rather than a perturbation it
learned to reject. The observation is proprioceptive-only, so the policy cannot
see foot placement, only its consequences. Hence: roll it out and measure.

WHAT THIS RUNS. Three arms, the SAME checkpoint in each, PAIRED seeds so the
comparison is not confounded by episode variance:

    train    x = 0.0000    the geometry the checkpoint learned
    real     x = 0.0116    as built — current nova.xml
    control  x = 0.0580    5x the seam. POSITIVE CONTROL.

WHY THE POSITIVE CONTROL IS NOT OPTIONAL. "real ≈ train" has two causes: the
seam genuinely does not matter, or this harness cannot detect a geometry change
at all. Those are indistinguishable from a null result alone, and the second is
the more common outcome for a measurement written in one sitting. The control
arm is a deliberately large offset that MUST degrade. If it does not, the
harness is broken and this script refuses to issue a verdict rather than
handing you a comfortable one.

It also asserts, before running anything, that the three models really do place
the feet where the arm names claim. A rebuild that silently no-ops would
otherwise produce three identical arms and a very confident "no difference".

NOMINAL DYNAMICS. A bare NovaJoystick applies no domain randomization — that is
the training wrapper's job. Running nominal is deliberate: it isolates geometry
instead of burying an 8 % effect under DR spread.

USAGE
    python ab_seam.py --policy nova_policy.pkl              # 32 eps x 500 steps
    python ab_seam.py --policy p.pkl --episodes 64 --vx 0.4

The checkpoint is the pickle that export_policy.py / rollout.py consume. The
policy loader is IMPORTED from rollout.py on purpose — rollout.load_policy
carries the normalize_observations fix, and duplicating it here is how that bug
comes back.
"""
import argparse
import os
import pathlib
import re
import shutil
import sys
import tempfile

# This script never renders, but `import mujoco` still builds a GL context.
# Do NOT hard-set MUJOCO_GL: 'osmesa' is invalid on macOS (RuntimeError at
# import), and the platform default is already correct there. Only supply one
# on Linux, where a headless box has no display to fall back to. Colab sets
# EGL itself, and an explicit value from the caller always wins.
if sys.platform.startswith("linux"):
    os.environ.setdefault("MUJOCO_GL", "osmesa")

import jax
import jax.numpy as jp
import mujoco
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent

# fore-aft HAA->HFE term per arm. 'real' must match build_mjcf.HAA_TO_HFE[0].
ARMS = {
    "train":   0.0000,
    "real":    0.0116,
    "control": 0.0580,
}
CONTROL_ARM = "control"
BASELINE_ARM = "train"


def variant_xml(x_term, workdir):
    """Write an MJCF with HAA_TO_HFE[0] = x_term. Returns the path.

    Rebuilds through build_mjcf so every other constant, and any future change
    to the model, is inherited rather than re-specified here.
    """
    src = (HERE / "build_mjcf.py").read_text()
    patched, n = re.subn(
        r"HAA_TO_HFE = \(\s*[0-9.]+\s*,",
        f"HAA_TO_HFE = ({x_term},",
        src, count=1)
    if n != 1:
        raise SystemExit(
            "ab_seam: could not patch HAA_TO_HFE in build_mjcf.py — the constant "
            "was renamed or reformatted. Fix this regex; do NOT run with an "
            "unpatched copy, which would silently make all three arms identical.")
    d = pathlib.Path(workdir) / f"m{str(x_term).replace('.','_')}"
    shutil.copytree(HERE, d, ignore=shutil.ignore_patterns(
        "__pycache__", "artifacts", "colab", "deploy", "*.mp4", "*.err"))
    (d / "build_mjcf.py").write_text(patched)
    sys.path.insert(0, str(d))
    for k in [k for k in sys.modules if k.startswith("build_mjcf")]:
        del sys.modules[k]
    import build_mjcf as B
    xml = B.MJCF
    sys.path.pop(0)
    for k in [k for k in sys.modules if k.startswith("build_mjcf")]:
        del sys.modules[k]
    out = d / "nova.xml"
    out.write_text(xml)
    return str(out)


def foot_x(xml_path):
    """Front-left foot x at the home keyframe — the arm's fingerprint."""
    m = mujoco.MjModel.from_xml_path(xml_path)
    d = mujoco.MjData(m)
    k = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, "home")
    if k >= 0:
        mujoco.mj_resetDataKeyframe(m, d, k)
    mujoco.mj_forward(m, d)
    g = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "FL_foot")
    return float(d.geom_xpos[g][0])


def run_arm(xml_path, policy_path, episodes, steps, vx, wz, heightmap=False):
    """Roll the policy in one geometry. Returns a dict of per-episode arrays."""
    from env import NovaJoystick
    from rollout import load_policy          # normalize_observations fix lives there

    # heightmap= must match what the CHECKPOINT was trained with, or
    # load_policy's normalizer shape-mismatches against env.observation_size
    # (a 226-d teacher against a 234-d env is how this first surfaced). Every
    # checkpoint on Drive as of 2026-08-08 is a tier-2 teacher, so this flag is
    # not optional for any of them.
    env = NovaJoystick(xml=xml_path, heightmap=heightmap)
    policy = load_policy(policy_path, env.observation_size, env.action_size)
    act = jax.jit(policy)
    jit_reset, jit_step = jax.jit(env.reset), jax.jit(env.step)
    cmd = jp.array([vx, 0.0, wz])
    dt = float(env.dt)

    fell, alive, ret, speed, travel = [], [], [], [], []
    for ep in range(episodes):
        # PAIRED: episode i uses the same seed in every arm.
        rng = jax.random.PRNGKey(1000 + ep)
        st = jit_reset(rng)
        st = st.replace(info={**st.info, "cmd": cmd})
        x0 = float(st.pipeline_state.x.pos[0, 0])
        total, n, down = 0.0, 0, False
        for _ in range(steps):
            rng, k = jax.random.split(rng)
            a, _ = act(st.obs, k)
            st = jit_step(st, a)
            st = st.replace(info={**st.info, "cmd": cmd})
            total += float(st.reward)
            n += 1
            if float(st.done) > 0.5:
                down = True
                break
        dx = float(st.pipeline_state.x.pos[0, 0]) - x0
        fell.append(down)
        alive.append(n)
        ret.append(total)
        travel.append(dx)
        speed.append(dx / max(n * dt, 1e-9))
    return dict(fell=np.array(fell), alive=np.array(alive, float),
                ret=np.array(ret), travel=np.array(travel),
                speed=np.array(speed))


def paired_ci(a, b, iters=10000, seed=0):
    """Bootstrap 95 % CI on the paired mean difference (b - a)."""
    d = b - a
    rs = np.random.default_rng(seed)
    idx = rs.integers(0, len(d), (iters, len(d)))
    boot = d[idx].mean(axis=1)
    return float(d.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def summarise(name, r, vx):
    print(f"  {name:<8} fell {r['fell'].mean()*100:5.1f}%   "
          f"alive {r['alive'].mean():6.1f} steps   "
          f"return {r['ret'].mean():8.2f}   "
          f"speed {r['speed'].mean():+.3f} m/s (cmd {vx:+.2f})   "
          f"travel {r['travel'].mean():+.3f} m")


def self_test():
    """Run the guards, and plant the failures they exist to catch.

    A guard that has never been seen go red is not a guard. Run this before
    trusting a verdict from a machine you have not run this on.
    """
    work = tempfile.mkdtemp(prefix="ab_seam_st_")
    ok = True

    print("GUARD 1 · the three arms must actually differ")
    fx = {k: foot_x(variant_xml(v, work)) for k, v in ARMS.items()}
    for k in ARMS:
        print(f"  {k:<8} HAA_TO_HFE[0]={ARMS[k]:<7} FL foot x = {fx[k]*1000:+8.2f} mm")
    good = all(abs(fx[k] - (fx[BASELINE_ARM] - ARMS[k])) < 1e-6 for k in ARMS)
    print(f"  offsets match arm names: {good}")
    ok &= good

    print("\n  PLANTED: rebuild silently no-ops, all arms identical")
    fake = {k: fx[BASELINE_ARM] for k in ARMS}
    flagged = [k for k in ARMS
               if abs(fake[k] - (fake[BASELINE_ARM] - ARMS[k])) > 1e-6]
    print(f"    arms flagged not-distinct: {flagged}  -> aborts: {bool(flagged)}")
    ok &= bool(flagged)

    print("\n  PLANTED: build_mjcf's constant gets renamed")
    src = (HERE / "build_mjcf.py").read_text().replace("HAA_TO_HFE = (", "HAA2HFE = (")
    n = len(re.findall(r"HAA_TO_HFE = \(\s*[0-9.]+\s*,", src))
    print(f"    regex matches: {n} -> variant_xml raises SystemExit: {n != 1}")
    ok &= (n != 1)

    print("\nGUARD 2 · the statistics must see a real drop, and only a real one")
    rs = np.random.default_rng(0)
    a = rs.normal(100, 10, 32)
    for lbl, b, want in (("degraded", a - 15 + rs.normal(0, 2, 32), True),
                         ("null", a + rs.normal(0, 2, 32), False)):
        m, lo, hi = paired_ci(a, b)
        got = hi < 0
        print(f"  {lbl:<9} {m:+7.2f}  CI [{lo:+.2f}, {hi:+.2f}]  detected={got} (want {want})")
        ok &= (got == want)

    print("\n" + "=" * 68)
    print("SELF-TEST PASSED" if ok else "SELF-TEST FAILED — do not trust a verdict")
    print("=" * 68)
    return 0 if ok else 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", help="pickled PPO params (not needed for --self-test)")
    ap.add_argument("--self-test", action="store_true",
                    help="exercise the guards without a checkpoint: build the three "
                         "geometries, confirm they differ by the right amounts, and "
                         "plant the failures the guards exist to catch")
    ap.add_argument("--heightmap", action="store_true",
                    help="build the PRIVILEGED teacher env (obs 234, not the blind 105). "
                         "Required for every checkpoint currently on Drive.")
    ap.add_argument("--episodes", type=int, default=32)
    ap.add_argument("--steps", type=int, default=500)
    ap.add_argument("--vx", type=float, default=0.5)
    ap.add_argument("--wz", type=float, default=0.0)
    ap.add_argument("--tol-return", type=float, default=0.10,
                    help="fractional return drop treated as acceptable (default 10%%)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.policy:
        raise SystemExit("ab_seam: --policy is required (or use --self-test)")
    if not os.path.exists(args.policy):
        raise SystemExit(f"ab_seam: no checkpoint at {args.policy}")

    work = tempfile.mkdtemp(prefix="ab_seam_")
    xmls = {k: variant_xml(v, work) for k, v in ARMS.items()}

    # GUARD 1: the arms must actually differ, and by the amount their name claims.
    print("geometry check (FL foot x at home keyframe):")
    fx = {}
    for k, p in xmls.items():
        fx[k] = foot_x(p)
        print(f"  {k:<8} {fx[k]*1000:+8.2f} mm   (HAA_TO_HFE[0] = {ARMS[k]})")
    for k in ARMS:
        want = fx[BASELINE_ARM] - ARMS[k]
        if abs(fx[k] - want) > 1e-6:
            raise SystemExit(
                f"ab_seam: arm '{k}' foot x is {fx[k]*1000:.2f} mm, expected "
                f"{want*1000:.2f}. The rebuild did not take — refusing to run, "
                f"because identical arms would report a confident 'no difference'.")
    print("  -> all three arms are distinct and match their offsets\n")

    res = {}
    for k, p in xmls.items():
        print(f"rolling {k} ({args.episodes} eps x {args.steps} steps)...")
        res[k] = run_arm(p, args.policy, args.episodes, args.steps, args.vx, args.wz, args.heightmap)

    print("\nper-arm means")
    for k in ARMS:
        summarise(k, res[k], args.vx)

    base = res[BASELINE_ARM]
    print(f"\npaired deltas vs '{BASELINE_ARM}' (same seeds; 95 % bootstrap CI)")
    deltas = {}
    for k in ARMS:
        if k == BASELINE_ARM:
            continue
        m, lo, hi = paired_ci(base["ret"], res[k]["ret"])
        fm, flo, fhi = paired_ci(base["fell"].astype(float), res[k]["fell"].astype(float))
        frac = m / abs(base["ret"].mean()) if base["ret"].mean() else float("nan")
        deltas[k] = dict(ret=m, lo=lo, hi=hi, frac=frac, fell=fm, fell_lo=flo, fell_hi=fhi)
        print(f"  {k:<8} return {m:+8.2f}  [{lo:+.2f}, {hi:+.2f}]  ({frac*100:+.1f}%)"
              f"   fall-rate {fm*100:+.1f} pts  [{flo*100:+.1f}, {fhi*100:+.1f}]")

    # GUARD 2: the harness must be able to SEE a degradation.
    c = deltas[CONTROL_ARM]
    control_degraded = c["hi"] < 0 or c["fell_lo"] > 0
    print("\n" + "=" * 68)
    if not control_degraded:
        print("VERDICT: NONE — HARNESS FAILED ITS POSITIVE CONTROL.")
        print(f"  The {CONTROL_ARM} arm ({ARMS[CONTROL_ARM]*1000:.1f} mm, "
              f"{ARMS[CONTROL_ARM]/ARMS['real']:.0f}x the seam) did not degrade.")
        print("  A geometry change this large MUST show. Since it does not, this")
        print("  run cannot distinguish 'the seam is harmless' from 'this script")
        print("  measures nothing'. Do not read the 'real' row as reassurance.")
        print("  Check: is the policy actually loading? are episodes long enough")
        print("  to express a gait? is the command non-zero?")
        print("=" * 68)
        return 2

    print("positive control OK — the harness detects a geometry change.\n")
    r = deltas["real"]
    worse_ret = r["hi"] < 0 and abs(r["frac"]) > args.tol_return
    worse_fall = r["fell_lo"] > 0
    if not worse_ret and not worse_fall:
        print("VERDICT: NO RETRAIN.")
        print(f"  Return change {r['frac']*100:+.1f}% (CI [{r['lo']:+.2f}, {r['hi']:+.2f}])")
        print(f"  and fall-rate change {r['fell']*100:+.1f} pts are within tolerance")
        print(f"  (+-{args.tol_return*100:.0f}% return, no significant fall increase),")
        print("  while the control arm degrades — so the null is informative.")
        print("  Deploy the existing checkpoint against the corrected geometry.")
        rc = 0
    else:
        print("VERDICT: RESUME AND FINE-TUNE (not from scratch).")
        if worse_ret:
            print(f"  Return drops {r['frac']*100:.1f}% (CI [{r['lo']:+.2f}, {r['hi']:+.2f}]).")
        if worse_fall:
            print(f"  Fall rate rises {r['fell']*100:+.1f} pts "
                  f"(CI [{r['fell_lo']*100:+.1f}, {r['fell_hi']*100:+.1f}]).")
        print("  env.py:384 doctrine: do NOT train stage 2 from scratch — that")
        print("  reopens the stand-basin. Resume from this checkpoint against the")
        print("  corrected nova.xml. The CoM does not move and the polygon shrinks")
        print("  symmetrically, so this is a re-tune, not a relearn.")
        rc = 1
    print("=" * 68)
    print("\nSCOPE. Nominal dynamics, no domain randomization, flat terrain, one")
    print(f"command ({args.vx:+.2f} m/s). It answers 'does the trained gait survive the")
    print("geometry change', not 'does it transfer to hardware'.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
