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
this script — rollouts are flat by construction: with DR on (the default,
below) terrain is pinned to terrain_max=0, so `is_crawl` is always 0 — but do
not reuse `extract_blind_obs` against a stair-DR teacher without re-measuring.

DOMAIN RANDOMIZATION (#413, default ON). The teacher trained under train.py's
`make_domain_randomize` (friction, mass+inertia, kp/kv, damping, torque
headroom). BC/DAgger rollouts now draw one robot per episode from that same
distribution (`--dr-scale`, default 1.0 = train.py's default), so the student
is fit on the dynamics spread the real robot will be one sample of, not on the
single nominal robot. `--no-dr` restores the nominal-only rollouts. The EVAL
stays nominal, so it remains comparable to the measured teacher baseline
(colab/DISTILL.md).

CHECKPOINT / RESUME (#413). `--ckpt DIR` auto-resumes (same convention as
train.py --ckpt): the whole run state — phase, episode/epoch index, RNG
streams, collected buffers, student params, Adam state, loss history — is
written atomically to DIR/distill_ckpt.pkl every `--ckpt-every` episodes/epochs
and at every phase change, and a re-run with the same args continues it.
`--scale-cal` prints s/episode and s/epoch for sizing the production run.

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
import dataclasses
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

import jax
import jax.numpy as jp
import numpy as np

from brax.training.agents.ppo.networks import make_inference_fn

from ckpt_utils import atomic_write
from env import DEFAULT_POSE, HIST, PROP, NovaJoystick, make_domain_randomize
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

def make_episode_fns(env, dr_scale=None):
    """-> (new_episode(rng) -> (dr, state), step(dr, state, action) -> state).

    dr_scale=None: nominal dynamics, dr == {} — the pre-#413 behaviour.
    dr_scale=float: every episode draws ONE robot from the same
    `env.make_domain_randomize` the teacher trained under (train.py hands it to
    brax as randomization_fn): friction, per-link mass+inertia, kp/kv, damping,
    torque headroom. Terrain is pinned FLAT (terrain_max=0) because the prefix
    equivalence `extract_blind_obs` relies on is flat-only (module docstring).
    Swapping `env.sys` under trace is brax's own
    DomainRandomizationVmapWrapper.v_env_fn, unbatched; only the randomized
    fields travel as jit args, so a fresh draw per episode does not recompile.
    """
    def swap(dr, fn, *a):
        old = env.sys
        env.sys = old.tree_replace(dr) if dr else old
        try:
            return fn(*a)
        finally:
            env.sys = old

    if dr_scale is None:
        sample = lambda k: {}
    else:
        randomize = make_domain_randomize(0.0, dr_scale)
        _, in_axes = randomize(env.sys, jax.random.split(jax.random.PRNGKey(0), 1))
        # the in_axes=0 (randomized) fields; the shape check drops static int
        # fields (nq, nmocap, ...) that tree_map left untouched and may equal 0
        names = [f.name for f in dataclasses.fields(in_axes)
                 if type(getattr(in_axes, f.name)) is int and getattr(in_axes, f.name) == 0
                 and hasattr(getattr(env.sys, f.name), "shape")]

        @jax.jit
        def sample(k):
            sys_v, _ = randomize(env.sys, k[None])
            return {n: getattr(sys_v, n)[0] for n in names}

    reset = jax.jit(lambda dr, k: swap(dr, env.reset, k))
    step = jax.jit(lambda dr, st, a: swap(dr, env.step, st, a))

    def new_episode(k):
        kd, kr = jax.random.split(k)
        dr = sample(kd)
        return dr, reset(dr, kr)
    return new_episode, step


def run_episode(fns, teacher_infer, student_infer, steps, rng):
    """One rollout on env_t (heightmap=True); each episode gets a FRESH command
    from the env's own reset() sampler (stage-2 range, vx/vy/wz).

    student_infer=None -> BC: the TEACHER drives under its own actions.
    Otherwise DAgger: the STUDENT drives (acting on its own blind slice of the
    state) and the TEACHER labels every visited state from the SAME state's full
    privileged obs. env_t is used for both purely so the teacher has its
    privileged obs to label with; physics are identical to env_b's."""
    new_episode, step = fns
    rng, ke = jax.random.split(rng)
    dr, st = new_episode(ke)
    obs_buf, act_buf = [], []
    for _ in range(steps):
        rng, ka, kb = jax.random.split(rng, 3)
        blind_obs = extract_blind_obs(st.obs)
        a_teacher, _ = teacher_infer(st.obs, kb)          # expert label, same state
        obs_buf.append(np.asarray(blind_obs))
        act_buf.append(np.asarray(a_teacher))
        a = a_teacher if student_infer is None else student_infer(blind_obs, ka)[0]
        st = step(dr, st, a)
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


def train_bc(net, S, obs, act, epochs, batch_size, lr, on_epoch):
    """MSE(tanh(loc), teacher_action) — the same deterministic-action form
    export_policy.forward_np / policy_runner.NovaPolicy.infer use, so what we
    optimize is exactly what the deployed artifact will compute.

    Resumable: reads and advances S's params / opt_state / epoch / keys["fit"],
    appends (phase, epoch, epoch-mean loss) to S["losses"], and calls on_epoch()
    (the checkpoint hook) after every epoch."""
    import optax
    opt = optax.adam(lr)
    if S["opt_state"] is None:
        S["opt_state"] = opt.init(S["params"])
    norm_state = S["norm"]
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

    while S["epoch"] < epochs:
        k0, k = jax.random.split(S["keys"]["fit"])
        perm = np.asarray(jax.random.permutation(k, n))
        params, opt_state, losses = S["params"], S["opt_state"], []
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            params, opt_state, loss = step(params, opt_state, obs_j[idx], act_j[idx])
            losses.append(loss)
        S.update(params=params, opt_state=opt_state, epoch=S["epoch"] + 1)
        S["keys"]["fit"] = np.asarray(k0)
        S["losses"].append((S["phase"], S["epoch"], float(jp.mean(jp.stack(losses)))))
        on_epoch()
    return S["losses"][-1][2]


# --------------------------------------------------------------------------
# checkpoint/resume (#413). One pickle, written with ckpt_utils.atomic_write
# (sibling tempfile + fsync + os.replace), so a kill mid-write leaves the
# PREVIOUS checkpoint intact. ckpt_utils' PROGRESS pointer exists to choose the
# newest of several Brax checkpoint dirs; there is only ever one file here, so
# the file is its own pointer.
# --------------------------------------------------------------------------

CKPT_NAME = "distill_ckpt.pkl"
PHASES = ("bc_collect", "bc_fit", "dagger_collect", "dagger_fit", "done")


def save_ckpt(ckpt_dir, S):
    if ckpt_dir is None:
        return True
    Path(ckpt_dir).mkdir(parents=True, exist_ok=True)
    return atomic_write(Path(ckpt_dir) / CKPT_NAME, pickle.dumps(S), label=CKPT_NAME)


def load_ckpt(ckpt_dir):
    p = Path(ckpt_dir) / CKPT_NAME if ckpt_dir else None
    if p is None or not p.exists():
        return None
    with open(p, "rb") as f:
        return pickle.load(f)


def fresh_state(cfg):
    ks = [np.asarray(k) for k in jax.random.split(jax.random.PRNGKey(cfg["seed"]), 4)]
    return dict(cfg=cfg, phase=PHASES[0], ep=0, epoch=0,
                keys=dict(bc_collect=ks[0], init=ks[1], dagger_collect=ks[2], fit=ks[3]),
                data=dict(bc_collect=[], dagger_collect=[]),
                norm=None, params=None, opt_state=None, losses=[])


def run(cfg, env_t, teacher_infer, ckpt_dir=None, every=10, log=print):
    """BC collect -> BC fit -> DAgger collect -> DAgger refit. Checkpointed every
    `every` episodes / epochs and at each phase change. If ckpt_dir already holds
    a checkpoint, CONTINUE it: same phase + episode/epoch index, same RNG stream,
    same buffers, same Adam moments, same loss history — so a resumed run equals
    the uninterrupted one (test_distill_resume.py). Returns (S, net, timings)."""
    S = load_ckpt(ckpt_dir)
    if S is None:
        S = fresh_state(cfg)
    elif S["cfg"] != cfg:
        raise SystemExit(f"{Path(ckpt_dir) / CKPT_NAME} was written with a different config:\n"
                         f"  checkpoint {S['cfg']}\n  this run   {cfg}\n"
                         "re-run with the same args, or point --ckpt at a fresh dir")
    else:
        log(f"RESUMING {Path(ckpt_dir) / CKPT_NAME}: phase {S['phase']}, episode {S['ep']}, "
            f"epoch {S['epoch']}, {len(S['losses'])} loss points so far")
    net, _ = build_student(jax.random.PRNGKey(0))          # architecture only
    infer = make_inference_fn(net)
    student_apply = jax.jit(lambda p, o, k: infer(p, deterministic=True)(o, k))
    fns = make_episode_fns(env_t, cfg["dr_scale"])
    timings = dict(bc_collect=[], dagger_collect=[], bc_fit=[], dagger_fit=[])

    def advance():
        S["phase"] = PHASES[PHASES.index(S["phase"]) + 1]
        S["ep"] = S["epoch"] = 0
        S["opt_state"] = None                   # each fit starts a fresh Adam, as before
        save_ckpt(ckpt_dir, S)

    def collect(n_eps, steps, student_infer):
        ph = S["phase"]
        log(f"{ph}: {n_eps} episodes x {steps} steps "
            f"({'teacher' if student_infer is None else 'STUDENT'} drives, teacher labels)")
        while S["ep"] < n_eps:
            t = time.time()
            k0, k = jax.random.split(S["keys"][ph])
            S["data"][ph].append(run_episode(fns, teacher_infer, student_infer, steps, k))
            S["keys"][ph] = np.asarray(k0)
            S["ep"] += 1
            timings[ph].append(time.time() - t)
            if S["ep"] % every == 0:
                save_ckpt(ckpt_dir, S)
        log(f"  {sum(o.shape[0] for o, _ in S['data'][ph])} (obs, action) pairs")
        advance()

    def fit(sources):
        ph = S["phase"]
        obs = np.concatenate([o for s in sources for o, _ in S["data"][s]])
        act = np.concatenate([a for s in sources for _, a in S["data"][s]])
        if S["opt_state"] is None and S["epoch"] == 0:
            S["norm"] = fit_normalizer(obs)     # (re)fit on everything this phase trains on
            if S["params"] is None:
                S["params"] = build_student(S["keys"]["init"])[1]
        log(f"{ph}: {obs.shape[0]} pairs, {cfg['epochs']} epochs, batch {cfg['batch_size']}")
        last = [time.time()]

        def on_epoch():
            timings[ph].append(time.time() - last[0])
            last[0] = time.time()
            if S["epoch"] % every == 0:
                save_ckpt(ckpt_dir, S)
        loss = train_bc(net, S, obs, act, cfg["epochs"], cfg["batch_size"], cfg["lr"], on_epoch)
        log(f"  final {ph} MSE {loss:.4f}")
        timings[ph + "_samples"] = obs.shape[0]
        advance()

    if S["phase"] == "bc_collect":
        collect(cfg["bc_episodes"], cfg["bc_steps"], None)
    if S["phase"] == "bc_fit":
        fit(["bc_collect"])
    if S["phase"] == "dagger_collect":
        bc_student = (S["norm"], S["params"])
        collect(cfg["dagger_episodes"], cfg["dagger_steps"],
                lambda o, k: student_apply(bc_student, o, k))
    if S["phase"] == "dagger_fit":
        fit(["bc_collect", "dagger_collect"])
    return S, net, timings


def print_scale_cal(cfg, timings):
    """Seconds per BC / DAgger episode and per fit epoch, on THIS backend. The
    first episode/epoch of each phase carries the XLA compile, so it is shown
    separately and left out of the median. Fit cost is samples x epochs, so a
    SCALE multiplier on episodes AND epochs costs ~SCALE^2 in the fits — a linear
    (cal wall-time x SCALE/SCALE_CAL) projection under-counts that part."""
    med = lambda xs: float(np.median(xs[1:] or xs)) if xs else float("nan")
    dr = "off" if cfg["dr_scale"] is None else f"dr_scale {cfg['dr_scale']}"
    print(f"\nSCALE-CAL — backend {jax.default_backend()}, DR {dr}")
    rate = {}
    for ph, steps in (("bc_collect", cfg["bc_steps"]), ("dagger_collect", cfg["dagger_steps"])):
        t = timings[ph]
        rate[ph] = med(t)
        print(f"  {ph:<15} {rate[ph]:8.3f} s/episode (median, <= {steps} steps; "
              f"first episode {t[0] if t else float('nan'):.1f} s incl. compile)")
    for ph in ("bc_fit", "dagger_fit"):
        n = timings.get(ph + "_samples", 0)
        rate[ph] = med(timings[ph]) / max(n, 1)
        print(f"  {ph:<15} {med(timings[ph]):8.3f} s/epoch at {n} samples "
              f"({rate[ph]*1e6:.2f} us per sample-epoch)")
    per_bc = timings.get("bc_fit_samples", 0) / max(cfg["bc_episodes"], 1)
    per_dg = (timings.get("dagger_fit_samples", 0) - timings.get("bc_fit_samples", 0)) \
        / max(cfg["dagger_episodes"], 1)
    print(f"  projection at this run's samples/episode (BC {per_bc:.0f}, DAgger {per_dg:.0f}); "
          "SCALE x the 1x smoke sizes, excl. eval:")
    for x in (1, 2, 10, 30, 100):
        bc, dg, ep = 12 * x, 6 * x, 60 * x
        s = (bc * rate["bc_collect"] + dg * rate["dagger_collect"]
             + ep * bc * per_bc * rate["bc_fit"]
             + ep * (bc * per_bc + dg * per_dg) * rate["dagger_fit"])
        print(f"    {x:>4}x  BC {bc:>5} / DAgger {dg:>4} eps, {ep:>5} epochs  ~{s / 3600:8.2f} h")


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
    # CPU for the child: it inherits the parent's XLA_PYTHON_CLIENT_MEM_FRACTION,
    # and a second GPU preallocation next to the parent's (and Ollama's) OOMs
    # (2026-09-26 tower production run). The export is a numpy weight dump.
    subprocess.run(
        [sys.executable, "export_policy.py", "--policy", str(pkl_path),
         "--npz", str(npz_path), "--label", label],
        cwd=HERE, check=True, env={**os.environ, "JAX_PLATFORMS": "cpu"})
    return pkl_path, npz_path


# --------------------------------------------------------------------------
# eval — student (blind env) vs teacher (privileged env), paired seeds, flat
# --------------------------------------------------------------------------

def rollout_eval(env, act_fn, episodes, steps, vx, wz, seed0=2000):
    jit_reset, jit_step = jax.jit(env.reset), jax.jit(env.step)
    cmd = jp.array([vx, 0.0, wz])
    dt = float(env.dt)
    fell, alive, ret, travel, speed = [], [], [], [], []
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
        speed.append(dx / max(n * dt, 1e-9))          # per-episode, mirrors ab_seam.run_arm
    return dict(fell=np.array(fell, float), alive=np.array(alive, float),
                ret=np.array(ret), travel=np.array(travel), speed=np.array(speed), dt=dt)


def summarise(name, r, vx):
    """Same fields + format as ab_seam.summarise, so the two harnesses read
    identically — including SPEED AGAINST THE COMMAND. Fall rate alone can't
    tell a stable fast walker from a stable policy that has simply stopped
    trying to hit the command; speed vs cmd is what makes that visible."""
    print(f"  {name:<10} fell {r['fell'].mean()*100:5.1f}%   "
          f"alive {r['alive'].mean():6.1f} steps ({r['alive'].mean()*r['dt']:5.1f}s)   "
          f"return {r['ret'].mean():8.2f}   distance {r['travel'].mean():+.3f} m   "
          f"speed {r['speed'].mean():+.3f} m/s (cmd {vx:+.2f})")


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
    ap.add_argument("--eval-only", default=None, metavar="STUDENT.pkl",
                     help="skip BC/DAgger/export; eval an already-exported student "
                          "params pickle (the (norm_state, policy_params) tuple "
                          "export_student writes) against --teacher")
    ap.add_argument("--ckpt", default=None, metavar="DIR",
                     help="checkpoint dir (put it on Drive / a persistent disk). "
                          "AUTO-RESUMES, like train.py --ckpt: if DIR/" + CKPT_NAME +
                          " exists the run continues from it (same args required), "
                          "else starts fresh. Omit = no checkpointing (old behaviour)")
    ap.add_argument("--ckpt-every", type=int, default=10,
                     help="checkpoint every N episodes and every N fit epochs "
                          "(plus at every phase change)")
    ap.add_argument("--dr-scale", type=float, default=1.0,
                     help="roll out BC/DAgger under the teacher's own domain "
                          "randomization (env.make_domain_randomize, flat terrain) "
                          "at this width; 1.0 = train.py's default")
    ap.add_argument("--no-dr", action="store_true",
                     help="nominal dynamics only — the pre-#413 behaviour")
    ap.add_argument("--scale-cal", action="store_true",
                     help="calibration: run the given sizes, print s/BC-episode, "
                          "s/DAgger-episode, s/epoch and a 1x..100x projection; "
                          "skip export and eval")
    args = ap.parse_args()

    t0 = time.time()
    env_t = NovaJoystick(heightmap=True)
    print(f"loading teacher {args.teacher} ...")
    teacher_infer = jax.jit(load_policy(args.teacher, env_t.observation_size, env_t.action_size))

    if args.eval_only:
        print(f"--eval-only: loading student params from {args.eval_only} "
              "(skipping BC/DAgger/export)")
        with open(args.eval_only, "rb") as f:
            norm_state, policy_params = pickle.load(f)
        net, _ = build_student(jax.random.PRNGKey(0))
    else:
        cfg = dict(teacher=str(args.teacher), bc_episodes=args.bc_episodes,
                   bc_steps=args.bc_steps, dagger_episodes=args.dagger_episodes,
                   dagger_steps=args.dagger_steps, epochs=args.epochs,
                   batch_size=args.batch_size, lr=args.lr, seed=args.seed,
                   dr_scale=None if args.no_dr else args.dr_scale)
        S, net, timings = run(cfg, env_t, teacher_infer, args.ckpt, args.ckpt_every)
        norm_state, policy_params = S["norm"], S["params"]
        n_bc = sum(o.shape[0] for o, _ in S["data"]["bc_collect"])
        n_dg = sum(o.shape[0] for o, _ in S["data"]["dagger_collect"])
        if args.scale_cal:
            print_scale_cal(cfg, timings)
            return

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
    summarise("teacher", r_teacher, args.vx)
    summarise("student", r_student, args.vx)
    print("  (note: 'return' is not directly comparable — the teacher's reward "
          "carries extra weighted terms (swingref/gait/climb/pbrs) the blind "
          "reward doesn't; fall-rate/distance/speed are the comparable numbers. "
          "A low fall rate at a speed well below cmd is a SLOW, conservative gait, "
          "not necessarily a better one — check speed before reading fall rate "
          "as a win.)")

    if not args.eval_only:
        elapsed = time.time() - t0
        print(f"\nSMOKE RUN — {n_bc + n_dg} samples ({n_bc} BC + {n_dg} DAgger), "
              f"{args.epochs} epochs x2 fits, {elapsed:.1f}s wall time this invocation on "
              f"{jax.default_backend()}. This demonstrates "
              "the pipeline end to end and produces a loadable artifact; it is NOT a claim that "
              "the student is deployable — see the module docstring's RUN SIZE section.")


if __name__ == "__main__":
    main()
