"""distill.py checkpoint/resume (#413): a run killed mid-DAgger and resumed must
CONTINUE — same episode counter, same loss curve, same final student — not
restart. Also: the checkpoint write is atomic, and DR rollouts really do draw a
different robot per episode.

Tiny CPU scale with a RANDOM-INIT 234-d teacher (the real teacher .pkl is a
gitignored input CI does not have; resume correctness does not depend on the
teacher being any good).

  JAX_PLATFORMS=cpu python test_distill_resume.py
"""
import os
import tempfile
from pathlib import Path

import jax
import numpy as np
from brax.training.acme import running_statistics, specs
from brax.training.agents.ppo import networks as ppo_networks

import ckpt_utils
import distill
from env import NovaJoystick

CFG = dict(teacher="random-init", bc_episodes=3, bc_steps=12, dagger_episodes=3,
           dagger_steps=12, epochs=4, batch_size=16, lr=1e-3, seed=0, dr_scale=1.0)
EVERY = 2
TOL = 1e-6          # same-machine rerun of the same XLA program; 0.0 measured on arm64


class Crash(Exception):
    pass


def _teacher(env):
    net = ppo_networks.make_ppo_networks(
        env.observation_size, env.action_size,
        preprocess_observations_fn=running_statistics.normalize,
        policy_hidden_layer_sizes=distill.POLICY_HIDDEN,
        value_hidden_layer_sizes=(256, 256, 256, 256))
    norm = running_statistics.init_state(specs.Array((env.observation_size,), np.float32))
    params = net.policy_network.init(jax.random.PRNGKey(123))
    return jax.jit(ppo_networks.make_inference_fn(net)((norm, params), deterministic=True))


def _counting_episodes(crash_on=None):
    """Wrap distill.run_episode: count calls, optionally raise on call #crash_on
    (a kill in the middle of an episode, NOT at a checkpoint boundary)."""
    real, calls = distill.run_episode, []

    def wrapped(*a, **k):
        calls.append(1)
        if crash_on is not None and len(calls) == crash_on:
            raise Crash
        return real(*a, **k)
    distill.run_episode = wrapped
    return real, calls


def _flat(params):
    return np.concatenate([np.ravel(x) for x in jax.tree_util.tree_leaves(params)])


def test_resume_continues(env, teacher):
    quiet = lambda *_: None
    with tempfile.TemporaryDirectory() as d_full, tempfile.TemporaryDirectory() as d_crash:
        # --- A: uninterrupted -------------------------------------------------
        real, calls = _counting_episodes()
        try:
            full, _, _ = distill.run(CFG, env, teacher, d_full, EVERY, log=quiet)
        finally:
            distill.run_episode = real
        n_eps = CFG["bc_episodes"] + CFG["dagger_episodes"]
        assert len(calls) == n_eps, calls

        # --- B: killed during the 2nd DAgger episode --------------------------
        crash_on = CFG["bc_episodes"] + 2
        real, calls = _counting_episodes(crash_on)
        try:
            distill.run(CFG, env, teacher, d_crash, EVERY, log=quiet)
            raise AssertionError("simulated crash did not fire")
        except Crash:
            pass
        finally:
            distill.run_episode = real
        on_disk = distill.load_ckpt(d_crash)
        assert on_disk["phase"] == "dagger_collect", on_disk["phase"]
        # last checkpoint = the phase change; DAgger ep 0 finished but was never
        # saved (EVERY=2), so the resume must REDO it, identically
        assert on_disk["ep"] == 0, on_disk["ep"]
        n_bc_losses = len(on_disk["losses"])
        assert n_bc_losses == CFG["epochs"], on_disk["losses"]
        assert not list(Path(d_crash).glob("*.tmp")), "stray tempfile after crash"

        # --- B': resume -------------------------------------------------------
        real, calls = _counting_episodes()
        try:
            res, _, _ = distill.run(CFG, env, teacher, d_crash, EVERY, log=quiet)
        finally:
            distill.run_episode = real

    # CONTINUED, not restarted: only the DAgger episodes were rolled out again
    assert len(calls) == CFG["dagger_episodes"], (
        f"resumed run rolled out {len(calls)} episodes; a continuation rolls out "
        f"{CFG['dagger_episodes']} (the DAgger ones), a restart {n_eps}")
    assert res["phase"] == full["phase"] == "done"
    for ph in ("bc_collect", "dagger_collect"):
        assert len(res["data"][ph]) == len(full["data"][ph])
        for (o1, a1), (o2, a2) in zip(res["data"][ph], full["data"][ph]):
            assert o1.shape == o2.shape and np.max(np.abs(o1 - o2)) <= TOL
            assert np.max(np.abs(a1 - a2)) <= TOL
    # loss curve: same length, BC part carried over from the checkpoint, no reset
    assert len(res["losses"]) == len(full["losses"]) == 2 * CFG["epochs"]
    assert res["losses"][:n_bc_losses] == on_disk["losses"]
    assert [(p, e) for p, e, _ in res["losses"]] == [(p, e) for p, e, _ in full["losses"]]
    lr = np.array([l for *_, l in res["losses"]])
    lf = np.array([l for *_, l in full["losses"]])
    assert np.max(np.abs(lr - lf)) <= TOL, (lr, lf)
    dp = float(np.max(np.abs(_flat(res["params"]) - _flat(full["params"]))))
    assert dp <= TOL, f"final student params differ by {dp}"
    print(f"  resume: {len(calls)} episodes re-run (of {n_eps}), "
          f"{len(res['losses'])} loss points, max|dparams| {dp:.1e}")


def test_config_mismatch_refused(env, teacher):
    with tempfile.TemporaryDirectory() as d:
        distill.save_ckpt(d, distill.fresh_state(CFG))
        try:
            distill.run(dict(CFG, epochs=99), env, teacher, d, EVERY, log=lambda *_: None)
            raise AssertionError("resumed a checkpoint written with a different config")
        except SystemExit:
            pass


def test_ckpt_write_is_atomic():
    """A write that dies after the bytes hit the tempfile but before the rename
    must leave the previous checkpoint byte-identical and loadable."""
    with tempfile.TemporaryDirectory() as d:
        S = distill.fresh_state(CFG)
        assert distill.save_ckpt(d, S)
        path = Path(d) / distill.CKPT_NAME
        before = path.read_bytes()
        S2 = dict(S, ep=7, losses=[("bc_fit", 1, 0.5)] * 1000)
        real = os.fsync

        def dies(fd):
            raise OSError("simulated kill mid-write")
        ckpt_utils.os.fsync = dies
        try:
            ok = distill.save_ckpt(d, S2)
        finally:
            ckpt_utils.os.fsync = real
        assert ok is False
        assert path.read_bytes() == before, "previous checkpoint was modified"
        assert not list(Path(d).glob("*.tmp")), "partial tempfile left behind"
        assert distill.load_ckpt(d)["ep"] == 0
        assert distill.save_ckpt(d, S2) and distill.load_ckpt(d)["ep"] == 7


def test_dr_draws_differ(env):
    new_episode, _ = distill.make_episode_fns(env, 1.0)
    d1, s1 = new_episode(jax.random.PRNGKey(1))
    d2, _ = new_episode(jax.random.PRNGKey(2))
    f1, f2 = float(d1["geom_friction"][0, 0]), float(d2["geom_friction"][0, 0])
    assert f1 != f2, "two episodes drew the same robot"
    assert float(abs(d1["hfield_data"]).max()) == 0.0, "DR terrain must stay flat"
    assert float(s1.info["is_crawl"]) == 0.0
    nominal, _ = distill.make_episode_fns(env, None)
    assert nominal(jax.random.PRNGKey(1))[0] == {}


if __name__ == "__main__":
    env = NovaJoystick(heightmap=True)
    teacher = _teacher(env)
    test_ckpt_write_is_atomic()
    test_dr_draws_differ(env)
    test_config_mismatch_refused(env, teacher)
    test_resume_continues(env, teacher)
    print("ALL DISTILL RESUME CHECKS PASSED")
