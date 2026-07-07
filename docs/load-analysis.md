# Structural Load Analysis — full assembly (2026-07-06)

Hand-calc audit of every printed load path at assembly level, run after the
shoulder rev4 joint fixes (flange floor feet + deck gussets) and the tibia
toe_v2 seat. Leg-internal members (pockets, discs, yokes) were sized in
`~/claude-memory/nova-proj/project-leg-v6-design.md` and are unchanged;
this doc covers the **chassis-level joints** the connectivity audit and the
user flagged.

## Load cases

| Case | Value | Basis |
|---|---|---|
| Robot mass | ~4.2 kg → W = 41 N | leg_v6 mass budget |
| Static stand (4 legs) | 10.3 N/leg | W/4 |
| Trot (2-leg support, ×2 dynamic) | ~41 N/leg | doctrine |
| Landing peak, single leg | **60 N** | leg_v6 doctrine worst case |
| Braking/faceplant decel | 2 g horizontal | assumption |
| Material | PA6-CF: 151 MPa flex dry, ~75 wet; Z-layers ×0.6 | Bambu TDS |

## 1. Shoulder ↔ trunk joint (the rev4 fix)

Geometry: C-box carries both hips 77.7 mm fore of the trunk end face.
Fasteners: 4× M3 into flange heat-sets at (±51.75, z 5/24 trunk), only a
19 mm couple — **pre-fix this was the whole joint**. Rev4 adds 2 floor
feet per end (M3×14 csk from below at (±59.5, ±42)) + 2 deck gussets.

| Load | Path & number | Margin |
|---|---|---|
| Forward tip (60 N landing, one leg): M = 60 × 77.7 = **4.66 N·m** | tension in the 2 upper flange bolts, arm 24 mm above the compression edge → **97 N/bolt**; parallel path: 2 riser hold-down screws at z 67.4 trunk (arm ~63) → the riser lid becomes a tension tie between the two shoulders | insert pullout (4 mm engagement, PA6-CF) ≈ 250–350 N → **SF ≥ 2.5** on bolts alone; riser path redundant |
| Reverse tip (braking): same 4.66 N·m opposite | **foot bolts** in tension, arm 75.5 mm (foot z −34 → flange top) → **31 N/bolt** | M3 + csk head bearing in the stock floor ≈ 1 MPa → SF > 20 even in PLA |
| Vertical shear 120 N/end (both legs trot) | flange face bearing on the wall ends (~1100 mm²) + feet on the floor (~145 mm²/pad) | < 0.5 MPa bearing → SF > 100 |
| Yaw twist (36 N lateral scrub at a foot): T ≈ 2.8 N·m | feet pair 84 mm apart + flange bolt group 103.5 wide | ~33 N per foot bolt → SF > 10 |
| Joint rocking / fretting | feet clamp closes the hinge; gussets kill deck-strip flutter | stiffness fix, not strength |

**Verdict: passes with the feet; the pre-fix joint also passed statically
(97 N/bolt) but had a single load path, low couple height, and would rock
under trot cyclic loads. Now triangulated + redundant.**

## 2. Shoulder box members

| Member | Load | Stress | SF (dry) |
|---|---|---|---|
| 2 shear webs 4×66.5 | 4.66 N·m bending | 0.8 MPa | ~190 |
| deck strips 33.4×6.5 ×2 + gussets | share of same | < 1 MPa | > 150 |
| box torsion (yaw 2.8 N·m) | closed-ish section | < 2 MPa shear | > 30 |

## 3. HAA joint (leg ↔ shoulder)

Roll moment 60 N × 64.3 mm (IK d) = 3.86 N·m → couple across the
horn-plate (+17.2) / wheel-boss (−17.7) planes, 34.9 apart → **111 N**
per face.

| Element | Number | Margin |
|---|---|---|
| horn plate 4× M3 deck inserts | 28 N/screw tension | pullout ~400 N (6.5 deck) → SF 14 |
| Ø19 wheel boss shear | 0.4 MPa | SF ≫ 100 |
| 4× M2.5 wheel screws | 28 N shear each | SF > 50 |

## 4. Tibia toe_v2 / shoe

| Element | Number | Margin |
|---|---|---|
| tread → seat disc bearing (60 N) | ~0.6 MPa on the r12.35 disc | SF ≫ 100; TPU crush is the soft element, by design |
| blade torsion from the 30.5 jog | 1.83 N·m → τ ≈ 1.6 MPa at the blade neck | SF ~45 |
| angled web (sector-clipped rev) | 60 N shear through ≥ half-disc section | < 1 MPa → clip cost negligible |

## 5. Masts (flagged "hanging" items — verified fine for operating loads)

| Item | Load (2–4 g inertial) | At the mount | Margin |
|---|---|---|---|
| D456 periscope (~75 g, arm ~30) | 3 N → 0.09 N·m | 4× M3 bracket | SF > 50 |
| L2 mast (~230 g, arm ~80) | 9 N → 0.72 N·m | riser-deck flange screws ~24 N each | SF > 15 |

⚠ **Faceplant is the unbounded case for both masts** — a fall onto the
camera or LiDAR exceeds any printed mount. That is a *policy* limit
(E-stop/limp behavior, handle with care), not a sizing one. Do not
stiffen further; a breakaway mount that shears before the sensor does is
the better failure mode.

## 6. Stock trunk shell (⚠ material unknown)

All shell-side stresses land < 1 MPa (bearing at wall ends, floor under
the feet, csk heads, bolt holes) → fine even in PLA. Actions:
- washers under every shell-side head (spread load into the print)
- when the shell is eventually reprinted, PA6-CF or PETG-CF; until then
  no static concern, watch the wall-end bearing for creep marks at the
  first teardown.

## Standing risks / follow-ups

1. Flange heat-sets: 6.2 bore in a 4-thick flange breaks through; inserts
   hold on ~4 mm. Fine at 97 N (SF ≥ 2.5) but if one spins at assembly,
   fall back to M3 through-bolt + nyloc (aperture access exists).
2. Riser is now a *documented secondary* tension tie (was "never
   structural") — primary path (flange bolts + feet) passes alone; do not
   remove the riser and trot.
3. L2 mast resonance: tall mast + 2 Hz trot — check for wobble at
   bring-up before trusting point clouds; add a damping pad if visible.
4. First assembly: drill the 4 foot holes (±59.5, ±42) with the
   floor_plate template (added to its 10-hole pattern job).
