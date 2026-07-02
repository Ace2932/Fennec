# Leg V6 — functional STS3215 leg (designed-for-assembly)

Started 2026-07-02. Supersedes the leg_v5 carve-a-cavity approach, which had no
servo insertion path, no retention, and no serviceable joints (user call —
correct: those were blocks, not leg designs).

## Design pattern (every joint, every part)

- **Servo mounting:** drops into an **open-top pocket**, 4× **countersunk M2.5**
  through the pocket floor into the case's threaded bottom holes
  (9.9×9.9 square, STEP-verified). Lifts straight out for service.
- **Driven joint = yoke:** top arm bolts to the Ø20 output horn (4× M2.5 on
  Ø14 BCD ±45° + M3 center); bottom arm pivots on an **M3 shoulder screw into a
  heat-set boss (M3 × D4.6) in the pocket floor**, coaxial with the spline.
  The Ø20 bolt-on bottom wheel is NOT used — it and the case-screw square both
  occupy r<10 of the bottom face (mutually exclusive with floor mounting), and
  the boss routes joint side-load into the printed bracket, not the servo case.
- **Wires:** slot out the knee-side pocket wall into an open-top channel.
- **Kinematics LOCKED to B2 measured numbers** (`dimensions.md §6`):
  femur 106.9 · tibia 129.0 · lateral jog 30.5 — URDF/IK stay valid.

## Parts

| Part | Status | Notes |
|---|---|---|
| `leg_v6_common.scad` | ✅ | pocket / horn-couple / idler-boss / yoke modules |
| `femur.scad` | ✅ first article ready | HFE pocket + knee yoke; verified: horn seat @ x=106.9±0.07, BCD ±4.95, idler M3 @ knee + hip pad w/ heat-set bore; watertight; prints flat, no pocket supports |
| tibia | ⬜ next | KFE pocket + blade to Ø7 foot pin @129 (reuse SM3_Foot rubber) + 30.5 lateral jog |
| coax | ⬜ | HAA pocket (axis ⊥) + yoke for femur horn; preserves 24.6 lateral + 9.5 drop |
| shoulder interface | ⬜ | stock shoulder frame + BCD14 adapter for STS horn (stock cutout is 25t-hobby sized) |

## Hardware per joint
4× M2.5×8 countersunk (floor) · 4× M2.5×8 (horn) · 1× M3×8 shoulder/cap (idler)
· 1× M3 × D4.6 × L5.7 heat-set.

## Verify (first-article print, before batching)
1. Pocket drop-in fit (CLR_POCKET 0.25/side, PA6-CF) — servo should seat with
   light push, no rock.
2. Horn seat depth: horn face flush with arm underside ±0.2.
3. M2.5 countersink flush (heads must NOT proud into the yoke arm plane).
4. Heat-set bore Ø4.6 — check insert purchase in PA6-CF at 5.7 deep.
5. Yoke gap: tibia slab + pad slides in with ≤0.6 total play.

## Build
```bash
/opt/homebrew/bin/openscad -o femur_v6.stl femur.scad
/opt/homebrew/bin/openscad -o /tmp/fit.png --imgsize=1000,650 \
  --camera=55,0,-2,60,0,25,330 preview_femur_fit.scad   # ghost-servo fit view
```
