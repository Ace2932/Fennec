# Leg V5 — Original NovaSM3 Shape + STS3215 Cavity

Built 2026-05-26. **Canonical leg design.** Earlier attempts (V2/V3/V4) are in
`../archive/` — see that folder's README for why V5 won.

Strategy: preserve the original NovaSM3 STL outer shape exactly, carve an
STS3215-sized cavity inside via OpenSCAD boolean difference. Keeps the original
Chris Locke styling (curves, fillets, mount patterns); only the internal servo
pocket changes to fit the bigger Feetech servo.

## Status — all 4 shapes placed + confirmed fitting

| Part | Servo | Cavity | Notes |
|---|---|---|---|
| **shoulder** | hip-roll body | none cut | original frame already open in the middle; servo slides in |
| **coax** | thigh-pitch body | carved, confirmed | cavity in main rectangular body, NOT the circular horn-cap extrusion |
| **femur** | knee body | carved, confirmed | prints as **shell + cover**, both carry the SAME cavity |
| **tibia** | — | none | PASSIVE shank; knee servo (in femur) drives it via proximal horn-cap |

Each STS3215 joint spans two parts — body in one, horn drives the next:
shoulder↔coax (hip), coax↔femur (thigh), femur↔tibia (knee).

Cavities don't need to be watertight — they just feed the TTL daisy-chain wires
and let the servo move freely.

## Files

```
leg_v5_common.scad   ← STS3215 dims + cavity/bearing/wire/horn modules + sts3215_solid (preview)
femur_params.scad    ← SHARED cavity placement for femur shell+cover (single source of truth)
shoulder.scad        ← FrontShoulderMiddle.stl, no cut (open frame); horn-enlarge stub commented
coax.scad            ← LeftCoax.stl  + cavity   (OVERLAY toggle for iteration)
coax_R.scad          ← RightCoax.stl + cavity
femur.scad           ← LeftFemur.stl  shell + cavity (uses femur_params)
femur_R.scad         ← RightFemur.stl shell + cavity
femur_cover.scad     ← LeftFemur cover  + SAME cavity (uses femur_params)
femur_cover_R.scad   ← RightFemur cover + SAME cavity
tibia.scad           ← LeftTibia.stl,  no cut (passive)
tibia_R.scad         ← RightTibia.stl, no cut (passive)
preview_with_servo.scad ← visualize STS3215 solid sitting in any part's cavity
build_all.sh         ← runs openscad on each → 9 STLs
```

## Outputs — 9 STLs per leg set

```
shoulder.stl       ← shared front/rear (rotates on chassis)
coax_L.stl  coax_R.stl
femur_shell_L.stl  femur_shell_R.stl
femur_cover_L.stl  femur_cover_R.stl
tibia_L.stl  tibia_R.stl
```

Femur prints as two pieces that bolt together — `femur_params.scad` is included
by both `femur*.scad` (shell) and `femur_cover*.scad` so the cavity stays
identical across the split. Edit cavity placement in ONE file, rebuild both.

## Build

```bash
cd hardware/cad/leg_v5
./build_all.sh          # all 9
# or one part:
openscad -o coax_L.stl coax.scad
```

~1 s per part on M1 MBP. STLs land alongside the `.scad` files.

## Iterating cavity placement

See `ITERATE.md` for the full loop. Short version: each part `.scad` has a
`CAVITY_CENTER` / `CAVITY_ROT` block (femur's lives in `femur_params.scad`). Set
`OVERLAY = true`, F5 in the OpenSCAD GUI to see the servo (blue) in the original
shell (yellow), nudge until it sits right, set `OVERLAY = false`, F6, rebuild.

## STS3215 cavity dims (in `leg_v5_common.scad`)

| Var | Value | Source |
|---|---|---|
| SERVO_L | 45.40 mm | STEP `STS3215_03a v1.step` |
| SERVO_W | 24.80 mm | STEP |
| SERVO_H | 34.30 mm | STEP (between horn-disc faces, NOT bbox z) |
| SPLINE_X_OFFSET | +12.50 mm | STEP (CRITICAL — spline offset from body center) |
| HORN_DISC_OD | 20.0 mm | STEP |
| HORN_DISC_THK | 2.5 mm | STEP |
| BACK_SHAFT_OD | 6.0 mm | STEP |
| CLR_BODY | 0.30 mm | PA6-CF press fit (calibrated per `../parametric-servo-fit.md`) |

## Open follow-ups (need a physical print)

- **First-article every shape.** Coax X-bbox is tight (37.6 mm vs 45.4 mm servo
  spanning the diagonal) — confirm material at every cavity face on a test print
  before batching 4 legs.
- **Shoulder horn cutout** may be sized for the old ~Ø14 hobby horn; STS3215 disc
  is Ø20. Uncomment the enlarge stub in `shoulder.scad` if the disc fouls.
- **Left-variant visual check.** Right confirmed; L uses Y-flipped coords. Eyeball
  `coax.scad` / `femur.scad` in OVERLAY before printing the left legs.
- **Old hobby-servo holes / wire exits** in the source STLs are left as-is — plug
  + re-cut for M2.5 on 14 mm BCD only if a fit issue shows up (snippets in `ITERATE.md`).
