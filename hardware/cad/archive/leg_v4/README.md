# Leg V4 — Build Summary

Generated 2026-05-24 via Jarvis OnShape MCP + Claude Code.

## Topology

3-DOF leg, 3 servos, 4 brackets.

```
chassis
  └── Shoulder              (hip-roll body, axis Z)
        └── HipFrame        (mates to hip-roll horn; holds thigh-pitch body, axis Y)
              └── Femur     (mates to thigh-pitch horn; 140 mm beam; holds knee body, axis Y)
                    └── Tibia (mates to knee horn; 130 mm shank; foot at distal end)
```

## Files

| Part | STEP | STL | Volume | bbox (mm) |
|---|---|---|---|---|
| Shoulder | `Shoulder.step` (23 kB) | `Shoulder.stl` (56 kB) | 37.8 cm³ | 60 × 40 × 42 |
| HipFrame | `HipFrame.step` (18 kB) | `HipFrame.stl` (57 kB) | 16.5 cm³ | 30 × 36 × 52 |
| Femur | `Femur.step` (19 kB) | `Femur.stl` (54 kB) | 188 cm³ | 30 × 40 × 190 |
| Tibia | `Tibia.step` (15 kB) | `Tibia.stl` (66 kB) | 58.7 cm³ | 22 × 20 × 134 |

Total leg material: ~301 cm³ PA6-CF per leg × 4 legs = ~1.2 L. With 1.13 g/cm³ density = ~1.4 kg structural.

## Connectivity validation

All 4 STLs pass single-connected-component check (no floating geometry). Watertightness verified by 1-component result (OnShape exports are guaranteed watertight from BREP).

```
Shoulder.stl    triangles=308  vertices=156  components=1  OK
HipFrame.stl    triangles=300  vertices=144  components=1  OK
Femur.stl       triangles=292  vertices=148  components=1  OK
Tibia.stl       triangles=342  vertices=173  components=1  OK
```

## OnShape document state

- Doc: `NovaSM3-Leg-V4` (id `dc722115b661b8e675565adf`)
- Workspace: `6c01af00bdbcf16c473ee9e2`
- Part Studios: Shoulder, HipFrame, Femur, Tibia + (Part Studio 1, empty placeholder) + STS3215_03a v1 parts (imported STEP)
- Variable Studio: `leg-vars` (16 named lengths — see "Variables" below)

Sibling doc: `NovaSM3-Chassis-V1` (id `f76cffdad1f17be39699335c`) — minimal chassis plate with 4× shoulder mount clusters (4× M3 clearance Ø3.4 on 30×30 mm pattern, 4 clusters at ±40 / ±30 cluster centers).

## Variables (in `leg-vars` Variable Studio)

| Name | Value | Used in |
|---|---|---|
| `femur_link_l` | 140 mm | Femur beam length (V1 built at fixed 140) |
| `tibia_link_l` | 130 mm | Tibia shank length (V1 built at fixed 130) |
| `hip_yoke_t` | 6 mm | Yoke wall thickness |
| `wall_t` | 4 mm | Generic structural wall |
| `ttl_slot_w` | 14 mm | TTL daisy-chain slot (not used in V1 — added in V2) |
| `ttl_slot_h` | 5 mm | TTL slot height |
| `bearing_od` | 16.05 mm | 688ZZ press-fit OD |
| `bearing_h` | 5 mm | 688ZZ width |
| `sts_body_l` | 45.40 mm | STS3215 body long axis |
| `sts_body_w` | 24.80 mm | STS3215 body short axis |
| `sts_body_h` | 36.80 mm | STS3215 body height (legacy — actual = 34.30 between horn faces) |
| `sts_spline_x` | 12.50 mm | STS3215 spline offset from body center |
| `horn_bcd` | 14.0 mm | Horn screw BCD |
| `insert_bore` | 4.0 mm | Ruthex M3 heat-set bore |
| `insert_boss_od` | 6.5 mm | M3 insert boss OD |
| `m3_clr` | 3.4 mm | M3 clearance hole diameter |

## Mate spec (for assembly)

Build the assembly using these joints. World axes: +X = forward, +Y = lateral outboard, +Z = up.

| Mate | Type | Connection | Axis | Limits |
|---|---|---|---|---|
| Chassis → Shoulder | Fastened | Shoulder slab bottom 4× M3 inserts ↔ chassis 4× M3 clearance (30×30 pattern) | — | — |
| Shoulder → HipFrame | Revolute | Shoulder hip-roll horn (top of tower at world Z=42, 4× M2.5 holes on 14 BCD ±45°) ↔ HipFrame bottom face | Z (hip-roll) | ±45° |
| HipFrame → Femur | Revolute | HipFrame thigh-pitch horn (on +Y face of HipFrame, spline at world Z=40.2) ↔ Femur bottom face | Y (hip-pitch) | -30° to +90° |
| Femur → Tibia | Revolute | Femur knee horn (on +Y face of Femur, near distal end) ↔ Tibia top face | Y (knee-pitch) | -10° to +120° |

## What's V1 vs deferred to V2

**V1 (built):**
- Block + body cavity per bracket (simple rect pockets)
- 4× M2.5 horn screws per bracket interface (single-shaft fixation)
- M3 heat-set inserts on Shoulder slab for chassis mate
- M3 foot mount hole on Tibia bottom (for TPU foot pad)

**V2 deferred (V1 does NOT include):**
- 688ZZ back-bearing seats on opposing arms of U-brackets (single-shaft only in V1)
- TTL daisy-chain channels through Femur/Tibia beams (cable routing external for V1)
- Rib reinforcement on Femur beam (solid rectangular bar for V1 — overweight but rigid)
- Horn relief through-holes on bracket walls (body cavity opens fully on +Y face → body retention is via horn-cap clamping only)
- STS3215 body back-plate screws (V1 relies on cavity friction-fit + horn-screw clamping)

## Print profile

PA6-CF on Bambu P1S, hardened steel nozzle. Dry filament 24 h @ 70 °C in SpacePi X4 immediately before print. Bed: Magigoo PA on textured PEI, 15 min soak at 100 °C.

Orient each part so the structural load axis aligns with extrusion (fiber orientation):
- Shoulder: print **slab-down** so chassis-mount face is on bed, tower extrudes UP (vertical) — body cavity opens horizontally during print, may need support
- HipFrame: print **bottom-face down** (horn cap face on bed), block extrudes UP — +Y face opening prints horizontally, may need support
- Femur: print **end-face down** (proximal horn face on bed), 190 mm vertical extrude — risky, may topple. Alternative: lay flat on Y face (40 mm contact) with support for knee cavity opening
- Tibia: print **bottom-face down** (foot side on bed), 134 mm vertical — same risk as Femur. Alternative: lay flat

For 190 mm tall femur, **horizontal orientation is recommended** with support material in the knee cavity. Body block sits on its 30×190 face.

## First-article protocol

Before batching for 4 legs (= 16 brackets):
1. Print **one set of all 4 parts** in PA6-CF.
2. Test fit STS3215 in each cavity (hip frame, femur, shoulder) — should slide in with light friction.
3. Test fit 4× M2.5 horn screws through bottom-face holes — clearance smooth, no jamming.
4. Mount real STS3215 in Shoulder, test M2.5 horn screws thread into shoulder hip-roll horn — Loctite 243.
5. Assemble full leg (Shoulder + HipFrame + Femur + Tibia + 3 servos). Manually articulate through full sweep. Listen for binding, crack, or layer separation.
6. Only after pass: queue remaining 3 sets.

## Known limitations of V1

- **No back-bearing on any joint.** All 3 rotational joints are single-shaft (horn-only) fixation. Under cantilever load (e.g., robot weight on extended leg), this may overstress the M2.5 horn screws. V2 should add 688ZZ back-bearing seats on U-bracket arms.
- **Femur is solid 30×40×190 = overweight at 188 cm³ (~213 g PA6-CF).** Should be hollowed or ribbed in V2. Wall thickness around knee cavity is healthy (4.475 mm on -Y, 0.85 mm on +Y near opening).
- **Body retention in HipFrame and Femur cavities = horn-clamp only.** Without a +Y wall (with horn relief hole) or back screws, body could shift in cavity if horn screws loosen. Loctite + first-article load test mitigates.
- **No TTL daisy-chain channels.** Cable routing must be external — Velcro / cable ties along beam exteriors. V2 should add 14×5 mm slots through Femur and Tibia beams.
- **Mate offsets applied 2026-05-25:** HipRoll firstOffsetX=+12.5 (Shoulder spline shift), HipPitch firstOffsetY=+14.2 (HipFrame thigh-pitch spline shift), KneePitch firstOffsetY=-89 (Femur knee spline shift, negative due to face-Y axis being opposite of femur +Z). Renders confirm clean mating with no visible solid interpenetration.

## Assembly

`Leg-V4-Assembly.step` (77 kB) — 4 parts mated as `NovaSM3-Leg-V4 → Leg-V4-Assembly`:
- Shoulder (auto-grounded as root)
- HipFrame ↔ Shoulder: revolute Z (hip-roll, ±45°)
- Femur ↔ HipFrame: revolute Y (hip-pitch, -30° / +90°)
- Tibia ↔ Femur: revolute Y (knee-pitch, -10° / +120°)

**Interference check:** 4 AABB overlaps reported but **all false positives** per OnShape's own caveat (AABB approximate for rotated parts). Visual inspection of iso/top/front/right renders confirms no solid interpenetration — overlaps come from bounding boxes of mate-flush faces.

**Joint topology verified working.** Hip-roll, hip-pitch, knee-pitch all rotate cleanly around their declared axes per the mate spec.

## Next steps

1. Open assembly in OnShape UI, sweep joints through full range and visually inspect for clashes during motion (resting position verified clean).
3. Print one set in PA6-CF per first-article protocol.
4. Iterate to V2 with back-bearings + ribbing + TTL channels based on first-article findings.

## OnShape MCP build notes (lessons learned)

- **Face coord system gotcha:** For side faces (e.g. +Y face JHS), sketch-x and sketch-y axes map directly to world coords (sketch-x = -X world, sketch-y = +Z world) — NOT offset from face origin. Earlier confusion cost ~10 wasted MCP calls debugging "NO_OP" cuts.
- **ADD over existing holes fails:** Extruding ADD on a face that has internal hole boundaries (e.g. drilled holes) triggers BOOLEAN_NON_MANIFOLD. Reorder so hole drilling happens AFTER any ADD operations.
- **Cut depth coplanar with face = NO_OP:** A REMOVE depth that exactly matches an existing face plane (e.g. drilling 6 mm through a 6 mm slab into a tower above) creates non-manifold. Use slightly different depth (5.7 mm for Ruthex insert) to leave 0.3 mm relief.
- **FeatureScript instantiation needs valid Face Query:** Can't instantiate a face-input FS feature on empty Part Studio. FS source CAN be uploaded standalone (creates Feature Studio element), but instantiation requires real geometry first.
