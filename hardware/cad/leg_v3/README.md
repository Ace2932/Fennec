# Leg V3.1 — CadQuery body-driven dual-shaft leg

Python/CadQuery rebuild of the NovaSM3 leg sized for **Feetech STS3215**
(replacing the original PWM hobby servos). Body-driven dual-shaft yoke
mount on every servo — the upstream link is a U-yoke straddling the
servo body along its shaft axis, the downstream link is a shell that
surrounds the body and rotates with it.

Verified against the real STS3215 STEP at
`~/codebases/NOVA/feetech_servo_models/feetech_sts3215-1.snapshot.6/
feetech-sts3215/STS3215_03a v1.step`. Overall link proportions matched
to the original NovaSM3 STLs in `~/codebases/NOVA/original_body_files/`.

> **Workflow scope.** Per the `nova-sm3-cad` skill in this repo
> (`.claude/skills/nova-sm3-cad/SKILL.md`), the OnShape kinematic stack
> remains source of truth. This V3.1 is a Python-CadQuery experiment to
> establish a dimensional baseline + validate the body-driven dual-
> shaft architecture before committing to OnShape sketches. The CAD
> here is bench-validatable (print one, fit-test against real servo +
> bearing) but is **not** the kinematic source of truth.

## Architecture (post-2026-05-24 user clarification)

**3 servos per leg, 12 total. Body-driven dual-shaft mount on every servo.**

| Servo | Function           | Torque   | Upstream (yoke)         | Downstream (body shell) |
|-------|--------------------|----------|-------------------------|--------------------------|
| 1     | Hip abduction      | 30 kg    | **shoulder** (chassis)  | **coax**                |
| 2     | Thigh flexion (quad)| 19 kg    | **coax** (-Z perpendicular yoke) | **femur** (proximal shell) |
| 3     | Knee               | 19 kg    | **femur** (distal yoke) | **tibia** (proximal shell) |

Tibia distal end = passive shin + TPU foot pad mount.

**Per-servo mount detail:**
- Upstream yoke has two parallel arms separated along the servo's shaft
  axis (= SERVO_H + 2 × clearance ≈ 37.8 mm). One arm carries the
  horn-disc receptacle (4× M3 horn screws on a 14 mm BCD + spline
  boss clearance); the other arm carries a 688ZZ bearing pressed in
  flush, riding on the servo's bottom reaction shaft (with a 6 → 8 mm
  sleeve adapter on the STS3215's 6 mm shaft to fit the 688ZZ 8 mm ID).
- Downstream shell pocket-fits the STS3215 body (45.4 × 24.8 × 39.6 mm
  + 0.5 mm clearance per side). Spline at body X = +12.5 from center.
  Shell has through-holes on both shaft-axis faces so the servo's top
  spline + horn-disc and bottom reaction shaft can poke through to the
  yoke arms.

## Critical fix vs V3 + OpenSCAD `coxa.scad`

V3 (and OpenSCAD coax.scad) assumed STS3215 spline was at body center.
STEP shows spline is offset **+12.5 mm** along the long axis from body
center, and the bottom reaction shaft is at the same X (coaxial pair).
V3.1 honors this: every cavity is sized for the real spline offset, every
through-hole is positioned at the correct X.

V3.1 also adopts the **body-driven dual-shaft pattern** that the user's
clarification requires:

- V3 had servo bodies inside link cavities with the spline driving the
  next link via a horn — single-sided cantilever load on the spline.
- V3.1 has the servo HORN anchored to the upstream link via the yoke
  arm + the bottom shaft caught in a 688ZZ on the other arm. Body
  rotates with the downstream shell, supported on both ends. No
  cantilever; much higher torsional rigidity.

## Files

| File | Purpose |
|------|---------|
| `leg_common.py`         | STS3215 envelope, helpers (`horn_disc_receptacle_cuts`, `bearing_seat_cuts`, `heatset_boss_cuts`, etc.), tolerances |
| `shoulder.py`           | Chassis-mount static yoke for servo 1 |
| `coax.py`               | Body shell (servo 1) + perpendicular yoke (servo 2) |
| `femur.py`              | Proximal body shell (servo 2) + distal yoke (servo 3) |
| `tibia.py`              | Body shell (servo 3) + shin + foot mount |
| `build_all.py`          | Builds all 4 pieces, exports STLs + posed assembly preview, prints bbox-comparison table vs originals |
| `*_v31_*.stl`           | Exported meshes (individual pieces are all watertight) |
| `*_preview.png`         | 4-view technical previews (per `parametric-3d-printing` skill) |
| `leg_v31_assembly.stl`  | Layout preview, NOT printable as one piece (overlapping unions) |

## V3.1 vs original NovaSM3 — bbox (mm)

| Part      | Original                               | V3.1 shell           |
|-----------|----------------------------------------|----------------------|
| Shoulder  | Inner 110×70×49, Middle 110×52×70, Outer 110×66×6 (3-piece original) | **60×30×70** (single yoke piece) |
| Coax      | 38×46×58                               | **55×50×82** (taller — yoke extends -Z for servo 2) |
| Femur     | 139×51×35                              | **132×50×45** (slightly shorter; thicker Z for proximal cavity) |
| Tibia     | 129×100×38 (Y=100 includes foot offset)| **138×44×29** (straight link; foot offset folded into shin) |

Posed assembly bbox: **144 × 56 × 293 mm** (straight-leg layout).

## Build + preview

```bash
# Requires Python 3.10-3.12 (CadQuery's OCC kernel)
python3.12 -m venv .venv
source .venv/bin/activate
pip install cadquery trimesh pyrender Pillow numpy

cd hardware/cad/leg_v3
python ~/.claude/skills/parametric-3d-printing/run_cadquery_model.py \
    build_all.py --preview
```

(Omit `--strict` for build_all because the posed-assembly STL is a
unioned overlap, not watertight. Each individual piece IS watertight
and `--strict` passes when built standalone.)

Individual piece:

```bash
python ~/.claude/skills/parametric-3d-printing/run_cadquery_model.py \
    shoulder.py --preview --strict
```

## BOM call-outs

- **4× shoulder** (one per leg) — bolts to chassis side panel
- **4× coax shell + cover** (one per leg)
- **4× femur shell + cover** (one per leg)
- **4× tibia shell + cover** (one per leg)
- **12× 688ZZ ball bearings** (3 per leg: one in each yoke's bearing arm)
- **12× 6 → 8 mm shaft sleeve adapters** (one per servo, fits 688ZZ ID on STS3215's 6 mm bottom shaft)
- **16× Ruthex M3 heat-set inserts** per leg (4 each in coax/femur/tibia covers, optional 4 in shoulder slab for chassis bolts)
- **12× STS3215** servos (4 × 30 kg hip + 8 × 19 kg thigh/knee) — already in BOM
- **4× TPU foot pad** — pattern in [`patterns.md`](../patterns.md) §8b
- **Lots of M3 × 8 cap screws** (horn screws, lid screws, chassis screws)
- **Loctite 243** on every M3

## Print recipe (per project patterns.md)

- **Material:** PA6-CF, hardened steel hotend
- **Bed:** textured PEI + Magigoo PA, 100 °C soak 15 min
- **Feed:** Creality SpacePi X4 dryer → 4 mm PTFE Bowden → P1S top input
  (AMS HF bypassed)
- **Drier:** 24 h @ 70 °C pre-print; keep at 60-70 °C during print
- **Infill:** 100 % on every shell + cover + yoke + tibia (this is the
  leg load path — no exceptions)
- **Orientation:** shells flat-side down (cavity opens up). Yokes flat
  on slab side. Fiber axis along the part's long X axis (load direction).
- **Inserts:** 4× Ruthex M3 heat-set into shell/cover lid bosses
- **Bearings:** 12× 688ZZ press-fit (firm thumb pressure, not arbor)
- **Loctite 243** on every M3 bolt

## First-article gate (mandatory before batching 4 sets)

1. Print **one** shoulder + one coax shell+cover + one femur shell+cover + one tibia shell+cover.
2. Press a **688ZZ** into each yoke bearing seat — should require firm thumb pressure, not pop in. If too loose: cyanoacrylate gap-fill. If too tight: ream with a 15.5 mm drill bit one step under.
3. Bolt a **real STS3215** through every yoke:
   - Spline + horn disc bolted via 4× M3 horn screws into horn-receptacle arm
   - Bottom shaft slid through bearing on the other arm (with 6→8 mm sleeve)
   - Servo body should spin freely between arms with no bind
4. Wrap shell around servo body, bolt cover with 4× M3 into heat-set inserts. Shell should rotate with servo body, gripping it without slop.
5. Hand-load each joint to ~5× body-weight equivalent on the appropriate axis — listen for layer-line cracks.
6. Only after every joint passes do you queue the remaining 3 legs.

## Known open items / TODO

- **6 → 8 mm sleeve adapter:** STS3215 has a 6 mm bottom shaft, 688ZZ has an 8 mm bore. Need to source or print a sleeve (PETG-CF, press-fit on shaft). Alternative: switch bearing standard to MR126ZZ (6 × 12 × 4), which fits the shaft directly but isn't in our BOM.
- **Shoulder chassis-mount bolt pattern** is a placeholder. Real chassis side-panel hole pattern needs to be measured (or chassis side panel designed fresh) and the `CHASSIS_BOLT_PATTERN` in `shoulder.py` updated.
- **Left vs right leg mirror:** all current files are "left" geometry. Right legs need a mirror — add a build flag in each script that mirrors X (or Y depending on part).
- **Cable routing inside coax/femur/tibia:** wire slots are placeholders. Real harness layout needs sizing once cables are in hand.
- **Servo 2 axis offset:** V3.1 places the servo 2 spline axis 5 mm below the coax body cavity floor. May want to bring it closer (saves coax Z height) once we measure the real servo + horn disc thicknesses on the bench.
- **Femur knee yoke open vs closed end:** currently both arms are solid slabs. Could open the distal end into a U-shape (clamshell) to make tibia install easier.
- **Femur weight:** at 132 × 50 × 45 mm and ~52 cm³ of PA6-CF the femur is the heaviest single part of the leg. Could lightweight by adding pocket reliefs in the mid-link beam (no load there) after first-article validation.

## Status

**Experimental.** Each individual STL passes the parametric-3d-printing
skill's `--strict` watertight check. The geometry follows the body-
driven dual-shaft architecture the user clarified on 2026-05-24. Print
first, verify against real STS3215 + 688ZZ on the bench, iterate, THEN
batch the remaining 3 legs.
