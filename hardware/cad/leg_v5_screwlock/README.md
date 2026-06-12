# Leg V5 — Screw-Lock variant

Copy of `../leg_v5/` (coax, femur, tibia) that adds the **screw features the
canonical cavity lacks**, so the STS3215 can be bolted in and locked instead of
relying on the press-fit pocket alone. Originals in `../leg_v5/` are untouched.

Built 2026-06-06.

## What changed vs leg_v5

| Part | leg_v5 | here |
|------|--------|------|
| coax (L/R) | servo cavity only | cavity **+ 4× M2.5 case mount holes** |
| femur shell + cover (L/R) | cavity only | cavity **+ 4× M2.5 case mount holes** (shell + cover share them via `femur_params.scad`) |
| tibia (L/R) | passive, no cut | passive by default; **4× M2.5 horn-coupling pattern** behind a `HORN` flag (mate face not yet measured) |

The outer shape and the existing `CAVITY_CENTER` / `CAVITY_ROT` placements are
copied verbatim — only screw holes are added.

## The hole pattern is STEP-extracted, not guessed

`sts3215_mount.scad` pulls the case mounting pattern straight from the servo
STEP (`feetech_servo_models/.../STS3215_03a v1.step`): the 18 Ø2.5 circles
resolve to a **9.9 × 9.9 mm square** of M2.5 holes, centered on the spline axis,
on each shaft-normal face:

```
(x, y) = {7.55, 17.45} × {-4.95, +4.95}   [cavity-local frame: long=X, width=Y, shaft=Z, spline at +X 12.5]
```

`sts3215_mount_holes()` cuts full-through Ø2.9 (M2.5 clearance) columns at those
4 positions, riding the same `translate(CAVITY_CENTER) rotate(CAVITY_ROT)` as
the cavity.

### Which face to screw

- **Top (+Z, horn side):** holes sit at R≈7 from the spline, inside the Ø20 horn
  disc / Ø21 relief — **not usable** for body mounting (those ends land in
  already-void relief, harmless).
- **Bottom (−Z, back-shaft side):** clear of the Ø6 back-shaft relief. In coax +
  femur this face backs into solid leg material, so a screw through the leg wall
  threads into the servo case and clamps the body. **This is the mounting face.**

## Build

```bash
cd hardware/cad/leg_v5_screwlock
./build_all.sh                 # 8 STLs
# or one: openscad -o coax_L.stl coax.scad
```

Render-verified 2026-06-06: all 8 compile `NoError`. Coax genus 13 → 17 vs the
cavity-only original = exactly the 4 added through-holes.

## ⚠️ Verify on a first-article print (per leg_v5 README)

1. **Wall thickness at the back face** — `MOUNT_COL_LEN` (15 mm) assumes the
   screw passes through ≤15 mm of leg wall to reach the servo. Check the screw
   length needed; adjust if the wall is thin/thick.
2. **No fouling** — confirm the 4 columns don't clip the femur-mate disc or a
   wall you need. Use OVERLAY in `coax.scad` (`OVERLAY = true`, F5) to see the
   cavity (red) + screw columns (blue) in the shell (yellow).
3. **Shaft direction** — assumes the back-shaft face points into solid leg
   material (true for the confirmed leg_v5 placements). If a part's servo is
   flipped, the full-through columns still give a usable hole on whichever face
   has material.
4. **Tibia horn coupling** — `tibia.scad` ships passive. The knee-servo horn
   mate face on the tibia proximal end isn't measured yet. To enable: set
   `HORN = true`, `OVERLAY = true`, nudge `HORN_POS` / `HORN_ROT` until the 4
   holes sit concentric with the knee axis on the mate face, then export.

## Files

```
sts3215_mount.scad   ← STEP-extracted mount-hole + horn-coupling modules
femur_params.scad    ← copied cavity placement (shell + cover share)
coax.scad coax_R.scad
femur.scad femur_R.scad femur_cover.scad femur_cover_R.scad
tibia.scad tibia_R.scad
build_all.sh
```
