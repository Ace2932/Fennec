# Knee Configuration Analysis (backlog #6)

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

## DECIDED 2026-07-06: **X-CONFIG** (user call, same day)

Rear crouch margin (46° vs 10°) + robot-level symmetry + natural
stand-up mechanics outweigh the modestly wider foot-exclusion zone. And
because it's pure software on gate-verified pose space, the decision is
reversible at any point before (or even after) gait tuning — the real
commitment is only the IK/gait sign conventions.

If chosen: rear stance table = (−40, −80); IK per-leg knee-sign
parameter; foot-exclusion ≥40 mm in the gait planner; previews get a
rear-mirrored variant when the gait lane starts.
