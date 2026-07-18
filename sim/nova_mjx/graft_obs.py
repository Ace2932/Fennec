"""Graft a trained policy onto a WIDER observation (obs + N dims).

Adding inputs (a height map, a gait clock, ...) grows the obs, so the trained
network's input layer no longer fits. Rather than retrain, EXPAND the input:
append N ZERO rows to each first-layer kernel + N sane dims to the normalizer.
Zero weights on the new inputs mean the grafted net is behaviorally IDENTICAL to
the source at step 0 (verified: 0.00e0 output delta) — the walk is preserved and
the new inputs' influence grows from zero as training resumes. The new dims MUST
be the LAST obs dims, matching env._get_obs (height map / clock appended last).

  # tier-2 height-map teacher (HM_N=11 -> 121 new dims):
  python graft_obs.py --src nova_policy.pkl --add-dims 121 --out nova_policy_hm.pkl
  python train.py --heightmap --terrain 0.6 --stair-frac 0.5 \
      --restore-params-pkl nova_policy_hm.pkl --ckpt <FRESH dir> --timesteps 60_000_000

Brax's ppo.train takes restore_params=[normalizer, policy, value] directly
(overrides restore_checkpoint_path) — this graft outputs exactly that 3-tuple.
"""
import argparse
import os
import pickle

import jax.numpy as jp


def _load(src):
    if os.path.isdir(src):
        from brax.training.agents.ppo import checkpoint
        return checkpoint.load(src)
    with open(src, "rb") as f:
        return pickle.load(f)


def _pad_first_kernel(net_params, add):
    """Append `add` zero input-rows to hidden_0's kernel: (in,out)->(in+add,out)."""
    import flax
    p = flax.core.unfreeze(net_params)
    k = p["params"]["hidden_0"]["kernel"]
    p["params"]["hidden_0"]["kernel"] = jp.concatenate(
        [k, jp.zeros((add, k.shape[1]), k.dtype)], axis=0)
    return p


def graft(params, add):
    norm, pol, val = params[0], params[1], params[2]
    cnt = float(norm.count.lo)

    def ext(a, fill):
        return jp.concatenate([a, jp.full((add,), fill, a.dtype)])

    # new dims: mean 0, std 1 (the normalizer adapts them during training), so
    # only sane initial values matter.
    norm2 = norm.replace(mean=ext(norm.mean, 0.0), std=ext(norm.std, 1.0),
                         summed_variance=ext(norm.summed_variance, cnt))
    return (norm2, _pad_first_kernel(pol, add), _pad_first_kernel(val, add))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help=".pkl of [norm,policy,value] OR a Brax checkpoint dir")
    ap.add_argument("--add-dims", type=int, required=True, help="new obs dims (e.g. 121 for an 11x11 height map)")
    ap.add_argument("--out", default="nova_policy_grafted.pkl")
    args = ap.parse_args()

    params = _load(args.src)
    obs_in = int(params[0].mean.shape[0])
    grafted = graft(params, args.add_dims)
    obs_out = int(grafted[0].mean.shape[0])
    with open(args.out, "wb") as f:
        pickle.dump(grafted, f)
    print(f"grafted {args.src} -> {args.out}")
    print(f"  obs {obs_in} -> {obs_out} (+{args.add_dims})   new-input weights = 0 "
          f"-> behaviorally identical to source at step 0.")
    print(f"  resume: python train.py --restore-params-pkl {args.out} --ckpt <FRESH dir> ...")


if __name__ == "__main__":
    main()
