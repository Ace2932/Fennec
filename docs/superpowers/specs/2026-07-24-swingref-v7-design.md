# Swing-reference v7 — dense trajectory tracking (WTW's real clearance form)

**Date:** 2026-07-24
**Status:** APPROVED (Aiden: "build reference traj")
**Context:** v6 verdict — the gait clock is trackable (wgait −0.28→−0.15, primary signal moved
for the first time) but swing stayed 0.02 through 32M: the schedule cost rewards contact
TIMING, not swing AMPLITUDE. Height still rested on the clearance term, which across v5/v6 was
a broken variant of WTW's clearance reward: one-sided, √v-scaled, outcome-only — it never
specifies the swing PATH, so the correlated lift motion stayed undiscoverable by white noise
(the campaign root cause, patterns/exploration-vs-plant-bandwidth).

**The fix:** WTW's ACTUAL clearance form is `(target − foot_h)²·swing_mask` — two-sided
squared tracking to a phase-varying reference. That gives the foot an exact height target at
EVERY swing phase → a dense gradient the policy mean-shifts along → converts the
noise-discovery problem into a tracking regression. We deviated from it (√v, one-sided, cost)
thinking we improved; the runs + probes + research all converge on: use the real form.

**Why safe NOW (couldn't be in v5):** √v and one-sidedness guarded the ckpt12 held-foot farm.
The v6 clock now guards it TWICE — (a) a foot high during scheduled STANCE is billed by w_gait;
(b) the phase-VARYING reference means a HELD foot can't track a moving target (matches one
phase, billed elsewhere). The clock built the guard; v7 uses WTW's clean form on top.

## Change (surgical — one term, no new obs, no regraft)

### Teacher clearance → dense swing-reference tracking

```
z_ref_i    = cmd_c · sin(π · swing_frac_i)                 # phase-varying height target
swingref   = Σ_i (foot_h_i − z_ref_i)² · swing_sched_i     # two-sided squared, swing-masked
w_swingref = −W_SWINGREF · swingref                        # W_SWINGREF ~100, --w-swingref
```
- REPLACES the v6 one-sided `max(cmd_c·env − foot_h,0)·√v·swing_sched` teacher clearance.
- Two-sided: tracks TO cmd_c (up to the FOOTSWING_MAX 0.06 ceiling) — hitting 5cm from 2cm is
  the goal; exceeding the command is (correctly) mild-billed. NOT the v4 ceiling problem: the
  target is the DESIRED height, commanded, terrain-relative (foot_h is above local ground, #130).
- No √v: the phase-varying reference + the schedule cost are the anti-hold guards now.
- swing_sched mask: stance feet exempt (z_ref=0 there anyway via swing_frac clip).
- `cmd_c` and `swing_frac` (from clock sin/cos) are ALREADY in obs 230 — the policy can predict
  the reference. NO new obs dim, NO regraft.

### Everything else UNCHANGED

Gait clock + w_gait (timing), w_climb/beta/PBRS (ascent + approach), pose/upright (v5),
carry/air, clip, stage schedule, terrain, obs 230. Blind path keeps the v5 one-sided clearance
form EXACTLY (byte-pinned — blind has no clock/swing_sched; deploy path protected, 4th time).

## Non-farmability

- swingref is a COST (max 0 at perfect tracking) — no positive to farm.
- Held-high foot: billed by the phase-varying ref (can't match a moving target) AND by w_gait
  during stance. The two v6 guards replace √v's job.
- Two-sided ≠ v4 ceiling: v4 capped a target we wanted to EXCEED; here the target IS the
  commanded desired height, and we raise cmd_c to want more. Tracking a command is correct.

## Acceptance

- Tests: swingref ≈0 when foot tracks z_ref (manufacture foot at cmd_c·sin(π·sf)); billed when
  below AND when above the ref (two-sided); masked to 0 on scheduled-stance feet; phase-varying
  (a foot held at a fixed height is billed at off-peak phases); blind clearance byte-unchanged
  (numeric pin, as v6 Task 2 did).
- **PROBE GATE (before any run) — the direct test:** probe_reward_landscape sweeps swing
  amplitude with the script phase-aligned to the clock (v6 harness). PASS = total per-step
  reward is MAXIMIZED at the reference amplitude (~5cm at cmd_c 0.05), NOT at 2cm — i.e.
  d(total)/d(amplitude) > 0 from 2cm up toward the reference. Report the amplitude-of-max and
  the swingref term at each amplitude (must be minimized at the reference). If max is still at
  2cm → raise --w-swingref, re-probe (74s iterations). NO-GO until the peak sits at the reference.

## Run plan (fennec_swingref_v7)

RESUME from the v6 policy pkl (fennec_policy_gait_v6.pkl — inherits the phase-lock skill, so v7
tests PURELY whether tracking adds amplitude; fresh hm230 graft is the fallback if v6 habits
interfere). Fresh 4-stage, defaults + beta 20 + the probe-tuned --w-swingref. WATCH: swing
0.02 → tracks toward cmd_c (THE signal — dense gradient should move it EARLY, unlike every
prior run); then gzmax scaling, wclimb growing. wgait should stay locked (~−0.15, inherited).
KILL: swing still 0.02 at 10M despite the probe-confirmed landscape → the dense gradient isn't
followed even when it exists → deepest falsification (mean-shift can't track a feasible
reference = an optimization/actuation wall no reward fixes), full stop → the honest end of the
RL-reward path, pivot to imitation/AMP or bank the walker. Success bar: 4cm probable, 6cm
ambitious, 8cm ceiling-discovery.
