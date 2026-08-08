"""distill.py — teacher (privileged, obs 234) -> blind student (obs 105) via DAgger.

WHY THIS EXISTS (#304). Every checkpoint on Drive is a NovaJoystick(heightmap=True)
teacher: it sees an 11x11 perfect height map + 8 privileged terms (commanded
footswing height, trot-clock phase/frequency, per-foot swing schedule) that no
NOVA sensor produces. `deploy/policy_runner.py` (now
`ros2_ws/src/nova_locomotion/nova_locomotion/policy_runner.py`, #295) only ever
builds the 105-d blind vector, so #289's sim->real bridge has nothing it can
run. This is the distillation cell that produces a 105-d student artifact for it.

THE OBS MAPPING — MEASURED, NOT ASSUMED. Before writing anything here, both envs
were reset from the SAME jax.random.PRNGKey and stepped with identical actions,
5 seeds x 10 random-action steps each (see test_distill_obs_map.py, which pins
this as a regression test). Result: the blind 105-vector
(`NovaJoystick(heightmap=False)`) is BYTE-IDENTICAL to the first 105 dims of the
teacher's 234-vector (`NovaJoystick(heightmap=True)`) in every case — max|diff|
0.0. So it IS a contiguous prefix, not an interleaved subset: `env.py:1311`
(`_get_obs`) builds `[prop_hist, cmd, last_act]` FIRST in both branches and only
appends the heightmap / cmd_c / gait-clock / swing-schedule teacher-only dims
AFTER; every upstream RNG draw that could have diverged the shared prefix (cmd,
joint_bias, gyro_bias, control delay) is taken from the SAME `reset()` key split
(`jax.random.split(rng, 8)`) regardless of the `heightmap` flag. `extract_blind_obs`
below is that measured slice, `[:BLIND_OBS_DIM]` — a negative control in
test_distill_obs_map.py breaks it (wrong offset) and confirms the test can
actually detect a wrong mapping, not just confirm the right one.

CAVEAT — this equivalence is FLAT-TERRAIN-ONLY. On a staircase (`is_crawl=1`)
the teacher's `sample_command` draws vx from a different (slow-crawl) band than
the blind path ever does, so the prefix would NOT match there. Irrelevant to
this script (bare `NovaJoystick`, no domain randomization -> flat by
construction), but do not reuse `extract_blind_obs` against a stair-DR teacher
without re-measuring.

WHY DAGGER, NOT PURE BEHAVIOUR CLONING. Pure BC trains the student only on
states the TEACHER visits. Walking is a closed-loop dynamical task: the
student's own small errors move it off the teacher's state distribution, and
because it was never trained on THOSE states, it has no gradient telling it how
to recover — errors compound step over step (the classic BC covariate-shift
failure, Ross & Bagnell 2011). DAgger closes that loop: roll the CURRENT
STUDENT, ask the TEACHER what it would have done from the states the student
actually reaches, aggregate those labels into the training set, and refit. This
script always runs at least one such on-policy round after the initial BC fit.

SCOPE — BLIND FLAT STUDENT, NOT A STAIR / PERCEPTION STUDENT. A 105-d obs
carries no terrain information at all, so this student CANNOT climb stairs —
that is not a training deficiency, it is an information-theoretic ceiling
(there is nothing in the input to condition a step-up on). `env.py:300-306`
already names the actual next project: a student distilled on a REALISTIC
occluded/noisy depth-derived height map, which needs hardware (D456+L2)
calibration this repo does not have yet. That is a different, larger project.
This script produces the FLAT student only, and the eval below only measures
flat performance.

RUN SIZE. Defaults here are a CPU SMOKE RUN — enough to exercise every stage of
the pipeline (collect -> DAgger -> fit -> export -> eval) end to end on a
laptop in a couple of minutes, not enough data or gradient steps to produce a
deployable policy. The production run (10-100x the samples/epochs, GPU) belongs
on Colab per the rest of sim/nova_mjx. Do not read a smoke run's eval numbers as
"the student is ready" — read them as "the loop works end to end and the
artifact loads"; main() prints the run's actual step/sample/wall-time counts so
this can't be misread as anything more.

  python distill.py --teacher artifacts/policies/nova_policy_hm234.pkl \\
      --out artifacts/policies/nova_student_blind_smoke
"""
import argparse
import pickle
import subprocess
import sys
import time
from pathlib import Path

import jax
import jax.numpy as jp
import numpy as np

from brax.training.agents.ppo.networks import make_inference_fn

from env import DEFAULT_POSE, HIST, PROP, NovaJoystick
from rollout import load_policy

HERE = Path(__file__).resolve().parent
ACT_DIM = len(DEFAULT_POSE)                      # 12
BLIND_OBS_DIM = HIST * PROP + 3 + ACT_DIM         # 105 — matches export_policy's own check
POLICY_HIDDEN = (128, 128, 128, 128)              # must match rollout.load_policy / export_policy


def extract_blind_obs(teacher_obs):
    """MEASURED contiguous prefix — see module docstring. `teacher_obs` may be
    (234,) or (N, 234); returns the same leading axis with the last axis sliced
    to BLIND_OBS_DIM."""
    return teacher_obs[..., :BLIND_OBS_DIM]


# --------------------------------------------------------------------------
# data collection
# --------------------------------------------------------------------------

def collect_bc(env_t, teacher_infer, episodes, steps, rng):
    """Roll the TEACHER under its own actions on `env_t` (heightmap=True). Each
    episode gets a FRESH command sampled by the env's own `reset()` (stage-2
    range, vx/vy/wz), so command coverage comes for free from the env's existing
    sampler — no need to override it here."""
    obs_buf, act_buf = [], []
    jit_reset, jit_step = jax.jit(env_t.reset), jax.jit(env_t.step)
    for _ in range(episodes):
        rng, kr = jax.random.split(rng)
        st = jit_reset(kr)
        for _ in range(steps):
            rng, ka = jax.random.split(rng)
            a, _ = teacher_infer(st.obs, ka)
            obs_buf.append(np.asarray(extract_blind_obs(st.obs)))
            act_buf.append(np.asarray(a))
            st = jit_step(st, a)
            if float(st.done) > 0.5:
                break
    return np.stack(obs_buf), np.stack(act_buf)


def collect_dagger(env_t, teacher_infer, student_infer, episodes, steps, rng):
    """DAgger round: the STUDENT drives the rollout (acting on its own blind
    slice of the state), the TEACHER labels every visited state (from the SAME
    state's full privileged obs). Physics are identical whether stepped from
    env_t or env_b (same MJCF, same ctrl formula) — env_t is used here purely so
    the teacher has its privileged obs available to label with."""
    obs_buf, act_buf = [], []
    jit_reset, jit_step = jax.jit(env_t.reset), jax.jit(env_t.step)
    for _ in range(episodes):
        rng, kr = jax.random.split(rng)
        st = jit_reset(kr)
        for _ in range(steps):
            rng, ka, kb = jax.random.split(rng, 3)
            blind_obs = extract_blind_obs(st.obs)
            a_student, _ = student_infer(blind_obs, ka)
            a_teacher, _ = teacher_infer(st.obs, kb)      # expert label, same state
            obs_buf.append(np.asarray(blind_obs))
            act_buf.append(np.asarray(a_teacher))
            st = jit_step(st, a_student)                  # STUDENT drives the trajectory
            if float(st.done) > 0.5:
                break
    return np.stack(obs_buf), np.stack(act_buf)


# --------------------------------------------------------------------------
# student network + BC fit
# --------------------------------------------------------------------------

def build_student(rng, obs_dim=BLIND_OBS_DIM, act_dim=ACT_DIM):
    """Same architecture + normalize_observations semantics rollout.load_policy
    expects: preprocess_observations_fn=running_statistics.normalize, policy
    hidden (128,128,128,128). Value network is built (PPONetworks always has
    one) but never trained/used here — BC only needs the policy head."""
    from brax.training.acme import running_statistics
    from brax.training.agents.ppo import networks as ppo_networks
    net = ppo_networks.make_ppo_networks(
        obs_dim, act_dim,
        preprocess_observations_fn=running_statistics.normalize,
        policy_hidden_layer_sizes=POLICY_HIDDEN,
        value_hidden_layer_sizes=(256, 256, 256, 256))
    policy_params = net.policy_network.init(rng)
    return net, policy_params


def fit_normalizer(obs):
    from brax.training.acme import running_statistics, specs
    state = running_statistics.init_state(specs.Array((obs.shape[-1],), jp.float32))
    return running_statistics.update(state, jp.asarray(obs))


def train_bc(net, policy_params, norm_state, obs, act, epochs, batch_size, lr, rng):
    """MSE(tanh(loc), teacher_action) — the same deterministic-action form
    export_policy.forward_np / policy_runner.NovaPolicy.infer use, so what we
    optimize is exactly what the deployed artifact will compute."""
    import optax
    opt = optax.adam(lr)
    opt_state = opt.init(policy_params)
    obs_j, act_j = jp.asarray(obs), jp.asarray(act)
    n = obs_j.shape[0]

    def loss_fn(params, ob, ac):
        raw = net.policy_network.apply(norm_state, params, ob)
        pred = jp.tanh(raw[..., :ac.shape[-1]])
        return jp.mean((pred - ac) ** 2)

    @jax.jit
    def step(params, opt_state, ob, ac):
        loss, grads = jax.value_and_grad(loss_fn)(params, ob, ac)
        updates, opt_state = opt.update(grads, opt_state, params)
        params = optax.apply_updates(params, updates)
        return params, opt_state, loss

    loss = float("nan")
    for ep in range(epochs):
        rng, k = jax.random.split(rng)
        perm = np.asarray(jax.random.permutation(k, n))
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            policy_params, opt_state, loss = step(policy_params, opt_state, obs_j[idx], act_j[idx])
    return policy_params, float(loss)


# --------------------------------------------------------------------------
# export — reuse export_policy.py verbatim so the artifact format is
# guaranteed identical to every other policy in artifacts/policies/, and its
# own numpy-vs-brax self-check runs for free.
# --------------------------------------------------------------------------

def export_student(net, policy_params, norm_state, out_prefix, label):
    pkl_path = out_prefix.with_suffix(".pkl")
    npz_path = out_prefix.with_suffix(".npz")
    with open(pkl_path, "wb") as f:
        pickle.dump((norm_state, policy_params), f)
    subprocess.run(
        [sys.executable, "export_policy.py", "--policy", str(pkl_path),
         "--npz", str(npz_path), "--label", label],
        cwd=HERE, check=True)
    return pkl_path, npz_path


# --------------------------------------------------------------------------
# eval — student (blind env) vs teacher (privileged env), paired seeds, flat
# --------------------------------------------------------------------------

def rollout_eval(env, act_fn, episodes, steps, vx, wz, seed0=2000):
    jit_reset, jit_step = jax.jit(env.reset), jax.jit(env.step)
    cmd = jp.array([vx, 0.0, wz])
    dt = float(env.dt)
    fell, alive, ret, travel = [], [], [], []
    for ep in range(episodes):
        rng = jax.random.PRNGKey(seed0 + ep)      # PAIRED across arms: same ep -> same seed
        st = jit_reset(rng)
        st = st.replace(info={**st.info, "cmd": cmd})
        x0 = float(st.pipeline_state.x.pos[0, 0])
        total, n, down = 0.0, 0, False
        for _ in range(steps):
            rng, k = jax.random.split(rng)
            a, _ = act_fn(st.obs, k)
            st = jit_step(st, a)
            st = st.replace(info={**st.info, "cmd": cmd})
            total += float(st.reward)
            n += 1
            if float(st.done) > 0.5:
                down = True
                break
        dx = float(st.pipeline_state.x.pos[0, 0]) - x0
        fell.append(down); alive.append(n); ret.append(total); travel.append(dx)
    return dict(fell=np.array(fell, float), alive=np.array(alive, float),
                ret=np.array(ret), travel=np.array(travel), dt=dt)


def summarise(name, r):
    print(f"  {name:<10} fell {r['fell'].mean()*100:5.1f}%   "
          f"alive {r['alive'].mean():6.1f} steps ({r['alive'].mean()*r['dt']:5.1f}s)   "
          f"return {r['ret'].mean():8.2f}   distance {r['travel'].mean():+.3f} m")


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--teacher", default="artifacts/policies/nova_policy_hm234.pkl")
    ap.add_argument("--out", default="artifacts/policies/nova_student_blind_smoke",
                     help="output prefix; writes <out>.pkl (jax params, gitignored) "
                          "and <out>.npz (+ .meta.json) via export_policy.py")
    ap.add_argument("--label", default="distill-smoke")
    ap.add_argument("--bc-episodes", type=int, default=12)
    ap.add_argument("--bc-steps", type=int, default=150)
    ap.add_argument("--dagger-episodes", type=int, default=6)
    ap.add_argument("--dagger-steps", type=int, default=150)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--eval-episodes", type=int, default=16,
                     help="the teacher's known fall mode at vx=0.5 mostly lands "
                          "after step ~300 (measured); shorter defaults would "
                          "silently under-sample it and print a misleadingly "
                          "rosy 0%% for both arms")
    ap.add_argument("--eval-steps", type=int, default=400)
    ap.add_argument("--vx", type=float, default=0.5, help="matches the #288 measured condition")
    ap.add_argument("--wz", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    t0 = time.time()
    rng = jax.random.PRNGKey(args.seed)

    env_t = NovaJoystick(heightmap=True)
    print(f"loading teacher {args.teacher} ...")
    teacher_infer = jax.jit(load_policy(args.teacher, env_t.observation_size, env_t.action_size))

    print(f"BC collection: {args.bc_episodes} episodes x {args.bc_steps} steps ...")
    rng, k = jax.random.split(rng)
    obs0, act0 = collect_bc(env_t, teacher_infer, args.bc_episodes, args.bc_steps, k)
    print(f"  {obs0.shape[0]} (obs, action) pairs")

    rng, k = jax.random.split(rng)
    net, policy_params = build_student(k)
    norm_state = fit_normalizer(obs0)
    print(f"BC fit: {args.epochs} epochs, batch {args.batch_size} ...")
    rng, k = jax.random.split(rng)
    policy_params, loss0 = train_bc(net, policy_params, norm_state, obs0, act0,
                                     args.epochs, args.batch_size, args.lr, k)
    print(f"  final BC MSE {loss0:.4f}")

    student_infer = jax.jit(
        make_inference_fn(net)((norm_state, policy_params), deterministic=True))

    print(f"DAgger round 1: {args.dagger_episodes} episodes x {args.dagger_steps} steps "
          "(student drives, teacher labels) ...")
    rng, k = jax.random.split(rng)
    obs1, act1 = collect_dagger(env_t, teacher_infer, student_infer,
                                 args.dagger_episodes, args.dagger_steps, k)
    print(f"  {obs1.shape[0]} additional (obs, action) pairs")

    obs_agg = np.concatenate([obs0, obs1], axis=0)
    act_agg = np.concatenate([act0, act1], axis=0)
    norm_state = fit_normalizer(obs_agg)          # refit normalizer on the aggregate
    print(f"DAgger refit on {obs_agg.shape[0]} aggregated pairs, {args.epochs} epochs ...")
    rng, k = jax.random.split(rng)
    policy_params, loss1 = train_bc(net, policy_params, norm_state, obs_agg, act_agg,
                                     args.epochs, args.batch_size, args.lr, k)
    print(f"  final DAgger MSE {loss1:.4f}")

    out_prefix = Path(args.out)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    pkl_path, npz_path = export_student(net, policy_params, norm_state, out_prefix, args.label)
    print(f"exported {pkl_path.name}, {npz_path.name}")

    student_infer = jax.jit(
        make_inference_fn(net)((norm_state, policy_params), deterministic=True))

    print(f"\neval on FLAT, {args.eval_episodes} episodes x {args.eval_steps} steps, "
          f"cmd vx={args.vx:+.2f} wz={args.wz:+.2f}, PAIRED seeds:")
    env_b = NovaJoystick(heightmap=False)
    r_teacher = rollout_eval(env_t, teacher_infer, args.eval_episodes, args.eval_steps,
                              args.vx, args.wz)
    r_student = rollout_eval(env_b, student_infer, args.eval_episodes, args.eval_steps,
                              args.vx, args.wz)
    summarise("teacher", r_teacher)
    summarise("student", r_student)
    print("  (note: 'return' is not directly comparable — the teacher's reward "
          "carries extra weighted terms (swingref/gait/climb/pbrs) the blind "
          "reward doesn't; fall-rate and distance are the comparable numbers.)")

    elapsed = time.time() - t0
    n_samples = obs_agg.shape[0]
    print(f"\nSMOKE RUN — {n_samples} samples ({obs0.shape[0]} BC + {obs1.shape[0]} DAgger), "
          f"{args.epochs} epochs x2 fits, {elapsed:.1f}s wall time on CPU. This demonstrates "
          "the pipeline end to end and produces a loadable artifact; it is NOT a claim that "
          "the student is deployable — see the module docstring's RUN SIZE section.")


if __name__ == "__main__":
    main()
