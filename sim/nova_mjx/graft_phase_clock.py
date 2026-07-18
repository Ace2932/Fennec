"""Graft a trained flat/omni policy onto the PHASE-CLOCK observation (obs +2).

Adding the gait clock grows the obs 105 -> 107, so the trained network's input
layer (105-wide) no longer fits. Rather than retrain from scratch, we EXPAND the
input: append 2 ZERO rows to each first-layer kernel and 2 sane dims to the
normalizer. Zero weights on the phase inputs mean the grafted net is behaviorally
IDENTICAL to the source at step 0 (verified: 0.00e0 output delta for any phase) —
the walk is preserved and the clock's influence grows from zero as training
resumes. The phase dims are the LAST obs dims, matching env._get_obs.

  # from the pickled params (train.py writes nova_policy.pkl each eval):
  python graft_phase_clock.py --src nova_policy.pkl --out nova_policy_phase.pkl
  # or from a Brax checkpoint dir on Drive (survives a Colab disconnect):
  python graft_phase_clock.py --src /content/drive/.../run_XXXX/000040468480 \
      --out nova_policy_phase.pkl

Then resume WITH the clock, from a FRESH ckpt dir (don't mix 105- and 107-dim
checkpoints in one dir):
  python train.py --phase-clock --restore-params-pkl nova_policy_phase.pkl \
      --ckpt /content/drive/MyDrive/nova_ckpt_phase --timesteps 40_000_000

Brax's ppo.train takes `restore_params=[normalizer, policy, value]` directly
(overrides restore_checkpoint_path) — this graft output is exactly that 3-tuple.
"""
import argparse
import os
import pickle

import jax.numpy as jp

ADD = 2   # sin, cos of the gait phase — must equal the env's phase obs width


def _load(src):
    """Return the [normalizer, policy, value] params tuple from a .pkl or a Brax
    checkpoint dir. train.py pickles exactly this 3-tuple; checkpoint.load returns
    the same shape."""
    if os.path.isdir(src):
        from brax.training.agents.ppo import checkpoint
        return checkpoint.load(src)
    with open(src, "rb") as f:
        return pickle.load(f)


def _pad_first_kernel(net_params, add=ADD):
    """Append `add` zero input-rows to hidden_0's kernel: (in,out) -> (in+add,out).
    Deep-copies the touched path so the source params are left intact."""
    import flax
    p = flax.core.unfreeze(net_params)          # -> plain nested dict (copy)
    k = p["params"]["hidden_0"]["kernel"]        # (obs, width)
    p["params"]["hidden_0"]["kernel"] = jp.concatenate(
        [k, jp.zeros((add, k.shape[1]), k.dtype)], axis=0)
    return p


def graft(params, add=ADD):
    norm, pol, val = params[0], params[1], params[2]
    cnt = float(norm.count.lo)                   # running-stats sample count (scalar)

    def ext(a, fill):
        return jp.concatenate([a, jp.full((add,), fill, a.dtype)])

    # phase dims: mean 0, std 1 (sin/cos already live in [-1,1]); summed_variance
    # = count so the recomputed variance stays 1. The normalizer keeps adapting
    # these as training proceeds, so only sane INITIAL values matter.
    norm2 = norm.replace(mean=ext(norm.mean, 0.0), std=ext(norm.std, 1.0),
                         summed_variance=ext(norm.summed_variance, cnt))
    return (norm2, _pad_first_kernel(pol), _pad_first_kernel(val))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help=".pkl of [norm,policy,value] OR a Brax checkpoint dir")
    ap.add_argument("--out", default="nova_policy_phase.pkl")
    args = ap.parse_args()

    params = _load(args.src)
    obs_in = int(params[0].mean.shape[0])
    grafted = graft(params)
    obs_out = int(grafted[0].mean.shape[0])
    k_in = params[1]["params"]["hidden_0"]["kernel"].shape
    k_out = grafted[1]["params"]["hidden_0"]["kernel"].shape
    with open(args.out, "wb") as f:
        pickle.dump(grafted, f)
    print(f"grafted {args.src} -> {args.out}")
    print(f"  obs {obs_in} -> {obs_out}   policy hidden_0 kernel {k_in} -> {k_out}")
    print(f"  phase weights = 0 -> behaviorally identical to the source at step 0.")
    print(f"  resume: python train.py --phase-clock --restore-params-pkl {args.out} "
          f"--ckpt <FRESH dir> --timesteps 40_000_000")


if __name__ == "__main__":
    main()
