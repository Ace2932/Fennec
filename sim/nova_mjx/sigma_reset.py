"""Re-inflate a collapsed policy's exploration noise (log-sigma re-init).

THE PROBLEM. Five training runs all inherited ONE 300M-step-converged flat-walker
via `graft_obs.py` parameter grafts. That single ancestor's exploration noise (sigma)
had already collapsed to near-zero, and every graft carried the collapse forward: the
policy is so deterministic that NO reward change ever moves the gait. The means (the
walking skill) are excellent; the *scale* half of the action distribution is dead.

THE SURGERY. Brax's `tanh_normal` policy (NormalTanhDistribution) is a plain MLP whose
FINAL Dense layer emits `2 * action_size` values, split `[loc || scale_logits]`
(see distribution.NormalTanhDistribution.create_dist: `loc, scale = jnp.split(p, 2, -1)`).
The realized std is

    sigma = (softplus(scale_logits) + min_std) * var_scale          (min_std=0.001, var_scale=1)

This script re-initializes ONLY the scale-logits half of that final Dense:
  * ZERO the WEIGHT columns feeding scale_logits  -> scale_logits becomes state-INDEPENDENT
    (a constant = the bias), so post-reset sigma is uniform across all observations.
  * SET the scale-logits half of the BIAS to `--scale-bias` (default 0.0).
  * Leave the loc (means) half + every other parameter BYTE-IDENTICAL. The walk is untouched.
  * Only the POLICY network (params[1]) is touched; normalizer (params[0]) and value net
    (params[2]) are left exactly as loaded (mirrors graft_obs.py's [norm, policy, value]).

sigma at the default/gentle bias (min_std=0.001):
  --scale-bias  0.0  ->  softplus(0.0)  + 0.001 = 0.6931 + 0.001 ~= 0.694   (default, brisk re-inflation)
  --scale-bias -1.0  ->  softplus(-1.0) + 0.001 = 0.3133 + 0.001 ~= 0.314   (gentler option)

The transform + min_std/var_scale defaults are read from the installed brax 0.14.2
`training/distribution.py` (NormalTanhDistribution: min_std=0.001, var_scale=1); the
self-test reads sigma straight out of the live distribution object rather than trusting
these constants.

Usage:
  python sigma_reset.py --src nova_policy.pkl --out nova_policy_sigreset.pkl
  python sigma_reset.py --src nova_policy.pkl --out gentle.pkl --scale-bias -1.0
  JAX_PLATFORMS=cpu python sigma_reset.py --self-test
"""
import argparse
import math
import pickle
import re
from collections.abc import Mapping

import numpy as np

# --- constants read from brax 0.14.2 training/distribution.py (NormalTanhDistribution) ---
MIN_STD = 0.001    # NormalTanhDistribution.__init__ default
VAR_SCALE = 1.0    # NormalTanhDistribution.__init__ default


def _softplus(x):
    """Numerically-stable log(1 + exp(x)) — matches jax.nn.softplus."""
    return np.logaddexp(0.0, np.asarray(x, dtype=np.float64))


def _sigma_from_logits(scale_logits, min_std=MIN_STD, var_scale=VAR_SCALE):
    """The NormalTanhDistribution transform: sigma = (softplus(logits)+min_std)*var_scale."""
    return (_softplus(scale_logits) + min_std) * var_scale


def _to_plain(obj):
    """Deep-copy any Mapping (incl. flax FrozenDict) tree into nested plain dicts,
    leaving leaf arrays as the SAME object references (byte-identical, mutable container).
    Avoids importing flax for the surgery (stdlib + numpy only)."""
    if isinstance(obj, Mapping):
        return {k: _to_plain(v) for k, v in obj.items()}
    return obj


def _find_layer_container(policy_params):
    """Return (container_dict, sorted_hidden_keys) for the dict holding 'hidden_<i>' Dense
    layers. Brax's tanh_normal policy is a plain MLP; graft_obs.py accesses
    policy['params']['hidden_0']. Search top level and one level down ('params')."""
    candidates = [policy_params]
    if isinstance(policy_params, Mapping):
        candidates += [v for v in policy_params.values() if isinstance(v, Mapping)]
    hidden_re = re.compile(r"^hidden_(\d+)$")
    for cont in candidates:
        if not isinstance(cont, Mapping):
            continue
        hidden = {k: int(hidden_re.match(k).group(1))
                  for k in cont.keys() if hidden_re.match(k)}
        if hidden:
            ordered = sorted(hidden, key=hidden.get)
            return cont, ordered
    raise ValueError(
        "Could not locate 'hidden_<i>' Dense layers in the policy params. This script "
        "supports brax's tanh_normal (NormalTanhDistribution) plain-MLP policy only; the "
        "loaded net does not match that structure.")


def reset_sigma(params, scale_bias=0.0):
    """Zero the scale-logit weight columns and set the scale-logit bias half to `scale_bias`
    in the policy network's final Dense layer. Returns (new_params, info)."""
    is_seq = isinstance(params, (list, tuple))
    if is_seq:
        if len(params) < 2:
            raise ValueError(f"Expected [normalizer, policy, value]; got sequence len {len(params)}.")
        policy_params = params[1]
        policy_idx = 1
    else:
        # Bare policy-params tree (not the [norm,policy,value] tuple).
        policy_params = params
        policy_idx = None

    # Deep-copy ONLY the policy subtree into mutable plain dicts; leaves are shared refs.
    policy_mut = _to_plain(policy_params)
    container, hidden_keys = _find_layer_container(policy_mut)
    final_key = hidden_keys[-1]
    final = container[final_key]

    kernel = np.asarray(final["kernel"])   # (in_features, out_dim)
    bias = np.asarray(final["bias"])       # (out_dim,)
    out_dim = kernel.shape[1]
    assert bias.shape[0] == out_dim, (
        f"final layer '{final_key}' kernel out {out_dim} != bias {bias.shape[0]}")

    # --- GUARD: output must be 2*action_size ([loc || scale_logits]) ---
    if out_dim % 2 != 0:
        raise AssertionError(
            f"final Dense '{final_key}' out_dim={out_dim} is ODD; NormalTanhDistribution "
            f"requires 2*action_size (loc||scale). Refusing to touch anything.")
    action_size = out_dim // 2
    assert out_dim == 2 * action_size  # tautology by construction, but states the contract

    # Pre-reset scale-logit bias stats — the collapse evidence.
    pre_scale_bias = bias[action_size:].astype(np.float64)
    pre_sigma = _sigma_from_logits(pre_scale_bias)

    # --- SURGERY (float copies; loc half untouched) ---
    new_kernel = np.array(kernel, copy=True)
    new_bias = np.array(bias, copy=True)
    new_kernel[:, action_size:] = 0.0            # zero weights feeding scale_logits
    new_bias[action_size:] = float(scale_bias)   # set scale_logits bias half

    # loc half must be byte-identical.
    assert np.array_equal(new_kernel[:, :action_size], kernel[:, :action_size])
    assert np.array_equal(new_bias[:action_size], bias[:action_size])

    final["kernel"] = new_kernel
    final["bias"] = new_bias

    # Reassemble the container in its original list/tuple shape; norm+value are the SAME objects.
    if is_seq:
        new_seq = list(params)
        new_seq[policy_idx] = policy_mut
        new_params = tuple(new_seq) if isinstance(params, tuple) else new_seq
    else:
        new_params = policy_mut

    post_scale_bias = float(scale_bias)
    post_sigma = float(_sigma_from_logits(post_scale_bias))
    tree_path = (f"params[{policy_idx}] -> ['params']['{final_key}']"
                 if policy_idx is not None else f"['{final_key}']")
    info = {
        "tree_path": tree_path,
        "final_key": final_key,
        "action_size": action_size,
        "out_dim": out_dim,
        "in_features": kernel.shape[0],
        "pre_scale_bias_min": float(pre_scale_bias.min()),
        "pre_scale_bias_mean": float(pre_scale_bias.mean()),
        "pre_scale_bias_max": float(pre_scale_bias.max()),
        "pre_sigma_min": float(pre_sigma.min()),
        "pre_sigma_max": float(pre_sigma.max()),
        "post_scale_bias": post_scale_bias,
        "post_sigma": post_sigma,
    }
    return new_params, info


def _print_report(src, out, scale_bias, info):
    print(f"sigma-reset  {src} -> {out}")
    print(f"  modified tree path : {info['tree_path']}  "
          f"(final Dense '{info['final_key']}', {info['in_features']}->{info['out_dim']})")
    print(f"  action_size        : {info['action_size']}   (out_dim {info['out_dim']} == 2*action_size  [loc || scale_logits])")
    print(f"  PRE-reset scale-logit BIAS  (collapse evidence):")
    print(f"      min/mean/max   : {info['pre_scale_bias_min']:.4f} / "
          f"{info['pre_scale_bias_mean']:.4f} / {info['pre_scale_bias_max']:.4f}")
    print(f"      => pre sigma    : {info['pre_sigma_min']:.5f} .. {info['pre_sigma_max']:.5f}")
    print(f"  POST-reset (scale weights zeroed => sigma uniform across all obs):")
    print(f"      scale bias     : {info['post_scale_bias']:.4f}")
    print(f"      => sigma        : {info['post_sigma']:.5f}   "
          f"[= softplus({info['post_scale_bias']:.2f}) + {MIN_STD}]")
    print(f"  means (loc half) + normalizer + value net: UNTOUCHED (byte-identical).")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", help=".pkl of [normalizer, policy, value] (graft_obs.py format)")
    ap.add_argument("--out", help="output .pkl")
    ap.add_argument("--scale-bias", type=float, default=0.0,
                    help="scale-logit bias to set (default 0.0 -> sigma~=0.694; -1.0 -> ~=0.314 gentler)")
    ap.add_argument("--self-test", action="store_true",
                    help="build a real brax ppo params tree, simulate collapse, verify the reset")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    if not args.src or not args.out:
        ap.error("--src and --out are required (unless --self-test)")

    with open(args.src, "rb") as f:
        params = pickle.load(f)
    new_params, info = reset_sigma(params, scale_bias=args.scale_bias)
    with open(args.out, "wb") as f:
        pickle.dump(new_params, f)
    _print_report(args.src, args.out, args.scale_bias, info)


def _self_test():
    """Build a real (tiny) brax PPO params tree, drive the scale bias to -5 (collapse),
    run reset_sigma, and verify loc-identical / scale-zeroed / bias==target / sigma-correct.
    Reads sigma from the LIVE distribution object (not the hardcoded constants)."""
    import jax
    import jax.numpy as jnp
    from brax.training.acme import running_statistics, specs
    from brax.training.agents.ppo import networks as ppo_networks

    print("[self-test] building brax ppo_networks (CPU, tiny) ...")
    OBS = 30
    ACT = 12  # Fennec: 12 DoF -> 2*12 = 24 policy outputs
    net = ppo_networks.make_ppo_networks(
        observation_size=OBS,
        action_size=ACT,
        policy_hidden_layer_sizes=(32, 32),   # -> hidden_0,hidden_1,hidden_2 (final=24)
        value_hidden_layer_sizes=(32, 32),
    )
    dist = net.parametric_action_distribution
    print(f"[self-test] distribution = {type(dist).__name__}, param_size = {dist.param_size} "
          f"(expect {2*ACT}); min_std={getattr(dist,'_min_std',None)} var_scale={getattr(dist,'_var_scale',None)}")

    key = jax.random.PRNGKey(0)
    kp, kv = jax.random.split(key)
    policy_params = net.policy_network.init(kp)
    value_params = net.value_network.init(kv)
    normalizer = running_statistics.init_state(specs.Array((OBS,), jnp.float32))
    params = [normalizer, policy_params, value_params]

    # locate final layer + SIMULATE COLLAPSE: force scale-logit bias to -5.0 everywhere,
    # and give scale weights some nonzero garbage so we can prove they get zeroed.
    cont, hidden_keys = _find_layer_container(_to_plain(policy_params))
    final_key = hidden_keys[-1]
    import flax
    pol = flax.core.unfreeze(policy_params)
    layers = pol["params"] if "params" in pol and final_key in pol["params"] else pol
    fk = np.array(layers[final_key]["kernel"], copy=True)
    fb = np.array(layers[final_key]["bias"], copy=True)
    fk[:, ACT:] = 0.37   # nonzero scale weights (collapse-era garbage)
    fb[ACT:] = -5.0      # collapsed scale bias -> sigma ~= softplus(-5)+min_std ~= 0.0077
    layers[final_key]["kernel"] = fk
    layers[final_key]["bias"] = fb
    loc_kernel_before = np.array(fk[:, :ACT], copy=True)
    loc_bias_before = np.array(fb[:ACT], copy=True)
    params[1] = pol

    # sanity: collapsed sigma via LIVE distribution
    dummy_obs = jnp.zeros((1, OBS))
    logits_collapsed = net.policy_network.apply(normalizer, params[1], dummy_obs)
    sig_collapsed = np.asarray(dist.create_dist(logits_collapsed).scale)
    print(f"[self-test] collapsed sigma (from live dist): {sig_collapsed.min():.5f} .. {sig_collapsed.max():.5f}")
    assert sig_collapsed.max() < 0.05, "collapse setup failed"

    # --- RUN THE RESET (target bias 0.0) ---
    TARGET = 0.0
    new_params, info = reset_sigma(params, scale_bias=TARGET)
    print(f"[self-test] reset info: path={info['tree_path']} final={info['final_key']} "
          f"pre_bias(min/mean/max)={info['pre_scale_bias_min']:.3f}/"
          f"{info['pre_scale_bias_mean']:.3f}/{info['pre_scale_bias_max']:.3f}")

    # fetch the reset final layer
    new_pol = new_params[1]
    new_layers = new_pol["params"] if "params" in new_pol and final_key in new_pol["params"] else new_pol
    nk = np.asarray(new_layers[final_key]["kernel"])
    nb = np.asarray(new_layers[final_key]["bias"])

    checks = []
    # 1. loc (means) half byte-identical
    ok = np.array_equal(nk[:, :ACT], loc_kernel_before) and np.array_equal(nb[:ACT], loc_bias_before)
    checks.append(("loc half (kernel+bias) byte-identical", ok))
    # 2. scale weight columns zeroed
    ok = np.all(nk[:, ACT:] == 0.0)
    checks.append(("scale weight columns == 0", ok))
    # 3. scale bias == target
    ok = np.allclose(nb[ACT:], TARGET)
    checks.append((f"scale bias == {TARGET}", ok))
    # 4. normalizer + value net untouched (same objects)
    ok = (new_params[0] is params[0]) and (new_params[2] is params[2])
    checks.append(("normalizer & value net untouched (identity)", ok))
    # 5. resulting sigma via LIVE distribution ~= softplus(TARGET)+min_std, uniform across obs
    rng_obs = jax.random.normal(jax.random.PRNGKey(7), (5, OBS)) * 3.0
    logits_reset = net.policy_network.apply(new_params[0], new_params[1], rng_obs)
    sig_reset = np.asarray(dist.create_dist(logits_reset).scale)
    expected = float((math.log1p(math.exp(TARGET))) + getattr(dist, "_min_std"))  # softplus(0)+min_std
    ok = np.allclose(sig_reset, expected, atol=1e-5) and (sig_reset.std() < 1e-6)
    checks.append((f"sigma == softplus({TARGET})+min_std ~= {expected:.5f} (uniform)", ok))
    print(f"[self-test] post-reset sigma (live dist): {sig_reset.min():.5f} .. {sig_reset.max():.5f} "
          f"(expected {expected:.5f}); info.post_sigma={info['post_sigma']:.5f}")
    # 6. our internal post_sigma matches the live-distribution sigma
    ok = abs(info["post_sigma"] - expected) < 1e-5
    checks.append(("info.post_sigma matches live-dist sigma", ok))

    print("\n[self-test] results:")
    all_ok = True
    for name, ok in checks:
        print(f"    [{'PASS' if ok else 'FAIL'}] {name}")
        all_ok = all_ok and ok
    print(f"\n[self-test] {'ALL PASSED' if all_ok else 'FAILURES PRESENT'}")
    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
