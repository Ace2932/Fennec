"""Export a trained NOVA policy for Jetson deployment.

Brax stores JAX params; the Jetson can't easily run JAX. This extracts the
deterministic policy — obs normalizer + the 4x128 MLP — into:
  * nova_policy.npz  — plain numpy weights (PREFERRED: the deploy node runs it
    with a ~10-line numpy forward, zero heavy deps on the Jetson), and
  * nova_policy.onnx — standard portable graph (onnxruntime), if torch is present.

Deterministic action = tanh(loc), loc = MLP(normalize(obs))[:12], silu hidden
activations (Brax NormalTanh policy defaults). Verified numerically against the
Brax policy itself.

  python export_policy.py --policy nova_policy.pkl
"""
import argparse
import pickle

import numpy as np


def extract(params):
    """(normalizer, policy_params) -> mean, std, [kernels], [biases]."""
    norm, pol = params
    mean = np.asarray(norm.mean, np.float32)
    std = np.asarray(norm.std, np.float32)
    layers = pol["params"]
    W, b = [], []
    i = 0
    while f"hidden_{i}" in layers:
        W.append(np.asarray(layers[f"hidden_{i}"]["kernel"], np.float32))  # (in,out)
        b.append(np.asarray(layers[f"hidden_{i}"]["bias"], np.float32))
        i += 1
    return mean, std, W, b


def forward_np(obs, mean, std, W, b, act_size=12):
    """Numpy deterministic policy: normalize -> MLP(silu) -> tanh(loc)."""
    x = (np.asarray(obs, np.float32) - mean) / std
    for i in range(len(W) - 1):
        x = x @ W[i] + b[i]
        x = x * (1.0 / (1.0 + np.exp(-x)))          # silu
    x = x @ W[-1] + b[-1]
    return np.tanh(x[..., :act_size])                # loc -> tanh


def export_onnx(mean, std, W, b, path, act_size=12):
    import torch
    import torch.nn as nn

    class Policy(nn.Module):
        def __init__(self):
            super().__init__()
            self.mean = nn.Parameter(torch.tensor(mean), requires_grad=False)
            self.std = nn.Parameter(torch.tensor(std), requires_grad=False)
            self.lin = nn.ModuleList()
            for Wi, bi in zip(W, b):
                layer = nn.Linear(Wi.shape[0], Wi.shape[1])
                layer.weight.data = torch.tensor(Wi.T.copy())    # flax (in,out)->torch (out,in)
                layer.bias.data = torch.tensor(bi)
                self.lin.append(layer)

        def forward(self, obs):
            x = (obs - self.mean) / self.std
            for layer in self.lin[:-1]:
                x = torch.nn.functional.silu(layer(x))
            x = self.lin[-1](x)
            return torch.tanh(x[..., :act_size])

    m = Policy().eval()
    dummy = torch.zeros(1, mean.shape[0])
    torch.onnx.export(m, dummy, path, input_names=["obs"],
                      output_names=["action"], opset_version=17,
                      dynamic_axes={"obs": {0: "batch"}, "action": {0: "batch"}})
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="nova_policy.pkl")
    ap.add_argument("--npz", default="nova_policy.npz")
    ap.add_argument("--onnx", default="nova_policy.onnx")
    args = ap.parse_args()

    from env import ACTION_SCALE, DEFAULT_POSE
    with open(args.policy, "rb") as f:
        params = pickle.load(f)
    mean, std, W, b = extract(params)
    print(f"MLP: {[Wi.shape for Wi in W]}  obs={mean.shape[0]}")

    # numpy weights bundle — everything the deploy node needs, self-contained
    bundle = {"mean": mean, "std": std,
              "action_scale": np.float32(ACTION_SCALE),
              "default_pose": np.asarray(DEFAULT_POSE, np.float32)}
    for i, (Wi, bi) in enumerate(zip(W, b)):
        bundle[f"W{i}"], bundle[f"b{i}"] = Wi, bi
    np.savez(args.npz, **bundle)
    print(f"saved {args.npz}")

    # verify numpy forward matches the Brax deterministic policy
    try:
        import jax, jax.numpy as jp
        from brax.training.agents.ppo import networks as ppo_networks
        from brax.training.acme import running_statistics
        # build the reference net exactly as ppo.train does with
        # normalize_observations=True (the DEFAULT make_ppo_networks preprocessor
        # is identity -> would skip normalization and mis-verify).
        net = ppo_networks.make_ppo_networks(
            mean.shape[0], len(DEFAULT_POSE),
            preprocess_observations_fn=running_statistics.normalize,
            policy_hidden_layer_sizes=(128, 128, 128, 128),
            value_hidden_layer_sizes=(256, 256, 256, 256))
        infer = ppo_networks.make_inference_fn(net)(params, deterministic=True)
        rng = jax.random.PRNGKey(0)
        obs = np.asarray(jax.random.normal(rng, (mean.shape[0],)))
        brax_a = np.asarray(infer(obs, rng)[0])
        np_a = forward_np(obs, mean, std, W, b)
        err = float(np.max(np.abs(brax_a - np_a)))
        print(f"numpy vs Brax max|err| = {err:.2e}  {'OK' if err < 1e-4 else 'MISMATCH'}")
    except Exception as e:
        print(f"(skipped brax verify: {e})")

    # onnx (optional, needs torch)
    try:
        export_onnx(mean, std, W, b, args.onnx)
        import onnxruntime as ort
        sess = ort.InferenceSession(args.onnx)
        obs = np.random.randn(1, mean.shape[0]).astype(np.float32)
        onnx_a = sess.run(None, {"obs": obs})[0][0]
        np_a = forward_np(obs[0], mean, std, W, b)
        err = float(np.max(np.abs(onnx_a - np_a)))
        print(f"saved {args.onnx}  onnx vs numpy max|err| = {err:.2e}  "
              f"{'OK' if err < 1e-4 else 'MISMATCH'}")
    except ImportError as e:
        print(f"(ONNX skipped — missing {e.name}; pip install torch onnxscript "
              f"onnxruntime. The .npz numpy path needs none of these.)")


if __name__ == "__main__":
    main()
