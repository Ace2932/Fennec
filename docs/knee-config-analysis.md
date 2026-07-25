# Knee Configuration Analysis (backlog #6)

> ## ⛔ SUPERSEDED 2026-07-25 — the robot is TRANSLATED, not X-CONFIG
>
> The 2026-07-06 decision below selected X-CONFIG. **It was never built.**
> Ground truth (Aiden, 2026-07-25): the robot is the **TRANSLATED** layout —
> all four knees bend BACKWARD — and the MJX sim has always matched it
> (`sim/nova_mjx`: `DEFAULT_POSE` hfe +0.6 / kfe −1.2 on every leg).
> `leg_ik.KNEE_FORWARD` is now `{FL, FR, RL, RR: False}`; it previously read
> `{FL: True, FR: True, RL: False, RR: False}`, which commanded the FRONT
> knees FORWARD and would have driven the front legs to a mirrored stance on
> first stand via `controller.gait_pose`.
>
> Verified by `sim/nova_mjx/render_knee_configs.py`, which measures each knee
> against the hip→foot chord: **−66.0 mm (backward) on all four legs**.
>
> **The analysis below is still accurate about the TRADE-OFF**, and the
> translated column's cost is now live rather than hypothetical:
> * Crouching in translated folds the FRONT legs TOWARD the trunk, into the
>   riser skirt (+50° cap, contact ~+55°). The `lie` and `crouch` choreo
>   keyframes need front hfe **+61.3°** and **+57.4°** — both past the cap.
>   Deepest body height inside it is **−16.83 cm**, vs today's keyframes at
>   −14.0 (lie) and −15.0 (crouch); stand at −18.0 is fine (+45.1°).
>   `test_keyframe_feet_under_hips` fails on exactly this and is left failing.
> * The REAR legs crouch by folding AWAY from the trunk, so they keep the
>   −86° away-trunk room and are not skirt-limited.
> * Under X-config BOTH pairs folded away from the trunk, which is where the
>   "46° rear margin" advantage came from. That advantage is now forfeited.
>
> **Open, needs a decision** — three ways to recover the front-leg fold range:
> raise the `lie`/`crouch` keyframes to ≥ −16.83 cm (safe, but leaves almost
> no sit travel); re-measure the skirt cap (precedent: #47 found the front
> `hfe_ext` −50° stale by 36°, but contact here is measured at ~+55°, short of
> the +61.3° needed); or trim the riser skirt itself — it is a printed part,
> and it is the SAME part that caps stair step-up (see the #142 write-up:
> the leg can only shorten 3.81 cm at nominal width before hfe hits +50°).
>
> Also note `within_limits` keys its hfe-window flip off `knee_forward`, which
> in translated is now False for every leg — correct for the REAR pair, wrong
> for the FRONT pair. `solve_side`'s FRONT_LEGS clamp still applies the right
> bound at runtime.

2026-07-06. Question: keep the stock TRANSLATED layout (all knees fold
the same world direction) or switch the rear pair to X-CONFIG
(mirrored, mammal/dog layout) — decide BEFORE gait work bakes it in.

## The headline finding: it's a SOFTWARE choice

The hardware is kinematically sign-symmetric: hfe ±86 mech, kfe ±109 sw
both signs, cable service loops symmetric, mirrored parts exist. And the
chassis crouch gate already swept BOTH signs of every joint at all four
corners — **both configs' pose spaces are already gate-verified.** The
config is just the sign convention of the rear stance/gait tables
(translated rear stance (+40,+80) vs X rear stance (−40,−80)). No
reprints, no URDF change (−86..+50 covers both stances), switchable in
an afternoon of IK sign work — or even A/B tested on the real robot.

## Numbers (real preview transform chain, gate ROM, post height −152.2)

Single-leg reach at level walking height, vs own hip:
**−170 rearward / +141 forward of stance** (span 311, slight rearward
bias) — this asymmetry is what mirroring redistributes.

| Metric | TRANSLATED | X-CONFIG |
|---|---|---|
| robot-level fore/aft workspace | biased (both pairs reach further rearward: better one-direction propulsion reach) | **symmetric** (bidirectional gait, braking, station-keeping) |
| crouch/fold margin from stance | 10° to the +50 cap on ALL four legs | 10° front, **46° rear** (rear folds toward −86, chassis-clean) |
| worst-case front↔rear foot convergence | −28 mm (overlap) | −52 mm (overlap) |
| stand-up choreography | rear pushes "backward-kneed" | rear pushes dog-like (natural sit→stand) |
| ecosystem | matches stock SM3 gaits (which we aren't using) | matches Spot/ANYmal/biology conventions |

Notes on the two negative rows:
- **Foot convergence**: both configs can collide feet at simultaneous
  max reach toward each other; gaits never command that, and both need
  the same gait-level exclusion zone. X's is 24 mm wider. Feet are Ø34 —
  keep a ≥40 mm exclusion either way.
- The +50 fold cap is the riser-skirt graze, applied leg-local to all
  legs. In X the rear pair simply never visits that side of its range.

## ~~DECIDED 2026-07-06: **X-CONFIG** (user call, same day)~~ — SUPERSEDED, see the banner above; the robot is TRANSLATED

Rear crouch margin (46° vs 10°) + robot-level symmetry + natural
stand-up mechanics outweigh the modestly wider foot-exclusion zone. And
because it's pure software on gate-verified pose space, the decision is
reversible at any point before (or even after) gait tuning — the real
commitment is only the IK/gait sign conventions.

If chosen: rear stance table = (−40, −80); IK per-leg knee-sign
parameter; foot-exclusion ≥40 mm in the gait planner; previews get a
rear-mirrored variant when the gait lane starts.
