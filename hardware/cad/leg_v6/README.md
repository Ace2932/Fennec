# Leg V6 — functional STS3215 leg (designed-for-assembly)

> Top-level design: [`docs/design-outline.md`](../../../docs/design-outline.md)

Started 2026-07-02. Supersedes the leg_v5 carve-a-cavity approach, which had no
servo insertion path, no retention, and no serviceable joints (user call —
correct: those were blocks, not leg designs).

## Design pattern (every joint, every part)

- **Servo mounting:** drops into an **open-top pocket**, 4× **countersunk M2
  self-tap** through the pocket floor into the case's bottom pilot holes. Lifts
  straight out for service. 🔴 *Read "M2.5" and cited the "9.9×9.9 square" until
  2026-08-02 — both wrong: the case screws are **M2**, and the 9.9×9.9 square is
  the DISC bolt pattern, not the case pattern.* **STEP-verified 2026-08-02:** the
  case pilots are **8× Ø1.5** (with Ø4.2 head recesses) at **y=±10.25** on the two
  shaft-normal faces, x = +4.20 / −20.30 on the bottom face. Subtract the 12.5 mm
  spline offset → **(−8.3, ±10.2) and (−32.8, ±10.25) = `COL_PTS` exactly.** The
  pocket geometry is right. ⚠️ The STEP models these pilots only **1.5 mm deep**;
  the real column is **7.0 mm measured** — and never the 19.9 mm that older docs
  back-solved from a 22 mm screw. Note the faces are **asymmetric** (top face is
  x = +4.20 / −16.50); leg_v6 mounts through the **bottom** face.
- **Driven joint = yoke:** top arm bolts to the Ø20 output horn (4× **M3** on
  Ø14 BCD ±45° + M3 center); bottom arm pivots on an **M3 shoulder screw into a
  heat-set boss (M3 × D4.6) in the pocket floor**, coaxial with the spline.
  🔴 *Disc fastener was "M2.5" until 2026-08-02 (#263) — it is Ø3.0 nominal, though
  tapped-M3 vs PA3.0 self-tap pilot is UNRESOLVED (#262). The
  ∅2.5 holes in the STEP are the M3 tap drill, not M2.5 clearance (2.9).*
  The Ø20 bolt-on bottom wheel is NOT used — it and the case-screw square both
  occupy r<10 of the bottom face (mutually exclusive with floor mounting), and
  the boss routes joint side-load into the printed bracket, not the servo case.
- **Wires:** slot out the knee-side pocket wall into an open-top channel.
- **Kinematics LOCKED to B2 measured numbers** (`dimensions.md §6`):
  femur 106.9 · tibia 129.0 · lateral jog 30.5 — URDF/IK stay valid.

## Parts

| Part | Status | Notes |
|---|---|---|
| `leg_v6_common.scad` | ✅ rev 2 | mesh-verified servo frame, pocket/platform/horn-couple/wheel-boss/strap/zip modules; CLR_POCKET 0.45 DROP-IN |
| `femur.scad` (+`_L`) | ✅ gated | HFE pocket, knee fork w/ FLAT SHELF (top arm is bolt-on), wheel boss, vents, cable groove+anchors, strap pads, side dots; **zero bridging** |
| `knee_arm.scad` (print 4) | ✅ gated | bolt-on knee top arm — horn-seat face prints ON BED; 4× M3 into shelf heat-sets, diagonal pair Ø3.1 close-fit (registration) |
| `tibia.scad` (+`_L`) | ✅ gated | KFE pocket + blade + **toe_v2 designed seat** (disc/boss/key-pockets, mates the SM3_Foot crescent — `check_shoe.py` gated) @129.0, jog −30.5 outboard (stock stance); vents, anchors, dots |
| `coax.scad` (+`_L`) | ✅ gated | HAA pocket (horn −Y, front insert), femur yoke (horn arm 16.6 / wheel boss →51.5, bridge 7.4), front strap pads, vent, bottom cable tunnel |
| `strap.scad` (print 4+) | ✅ | servo tail retention, 2× Ø3.2 zip-tie bores into rim-pad zip cuts (2026-07-16: was M2.5 self-tap — see row 15) |
| `shoulder_plate.scad` (+`_L`, 4 installed = 2 per side) | ✅ gated | L-bracket hanging off the shoulder deck — vertical face bolts the haa HORN, top flange bolts down into the deck heat-sets; drop 4 screws + 1 plug and the whole leg comes off. **⚠ HANDEDNESS IS NOMINAL (measured 2026-08-02): `_L` is the SAME SHAPE.** The body is symmetric about its own midplane (x=39), so `mirror([1,0,0])` is a pure translation; the only asymmetric feature is the LA-2 dot (volume delta 7.41 mm³ = one Ø3×1.1 dot). Consequences: **both print horn-seat-down in the same orientation** (LA-3's L-orientation warning is for the Z-mirrored femur/tibia, not this), and **a plate on the wrong side is a non-event** — dots here are bookkeeping, not hazard prevention. ⬜ material still INFERRED not sourced (#184) |
| shoulder (+`shoulder_sw1` front, #377) | ✅ gated (rev 2026-07-06; `shoulder_sw1` gated #393) | v6 crossmember per trunk end; **riser interface rev**: flange center notch (x ±26 above z 19.5) + 2× Ø3.4 riser hold-down holes (x ±40, z 26.95) — see `../chassis/README.md`. `mesh_health.py` runs against both `shoulder.stl` (rear, plain) and `shoulder_sw1.stl` (front, + SW1 panel hole); the haa roll sweep (`check_fit.py --sweep`) runs against `shoulder.stl` only — the SW1 cutout sits 27-40mm from the swept hip, so `sw1_cutout_check()` proves the cutout instead (exists, in its designed box, ≥25mm from both hip roll axes) |

**ROM (sweep-gate verified, LEG-LOCAL):** kfe ±109° sw / ~118° mech ·
hfe ±86° sw · haa ±40° = shoulder input. **CHASSIS-SAFE caps are tighter**
(`../chassis/check_fit.py` is the authority for the assembled robot):
hfe toward-trunk +50 sw · haa INBOARD +15 sw (outboard keeps 40) — these
feed the URDF/firmware, not the leg-local numbers. `./build_all.sh` runs
the full gate (6 pockets + pose sweeps) on every build. Side dots:
**1 = RIGHT, 2 = LEFT**.

**v6 lateral chain** (URDF updated, sum still 64.3 = IK d): haa→femur-mid **33.8** ·
femur/tibia coplanar **0** · foot post **30.5**. Stock split was 24.6/9.2/30.5.

Full-leg fit view: `preview_leg_assembly.scad` (coax + femur + tibia + ghost servos).
`./build_all.sh` renders all 6 STLs (R+L).

## rev 2 — pocket + joints rebuilt against the full servo model
The original "case bottom thread square" was a misread (those holes belong to
the horn/wheel discs). rev 2, from `feetech_servo_models/converted_stl/servo.stl`:
- **Mounting:** the servo's own 4 case-screw columns — replace the stock
  self-tappers with **longer M2 screws through the pocket floor** (countersunk;
  measure stock length at first article, spec ≈ stock + 3mm). SO-ARM style.
- **Joints bolted BOTH sides:** yoke top arm on the Ø20 horn (4× **M3** BCD14 +
  M3 center); yoke bottom arm's **Ø19 boss reaches through the Ø21.5 floor
  window and bolts the Ø20 BOTTOM WHEEL** (standard-fitted; 4× **M3**, **NO
  center screw** — idler side, #51/LA-5; head counterbores modeled at Ø6.0).
  No heat-set/idler-boss hack. 🔴 *"M2.5 + M2.5 center" until 2026-08-02: the
  thread is M3 (#263) and the wheel center screw was retired in #51.*
- **Cables:** the case's rear-bottom connector bay (3.9 deep) is seated by the
  floor; sockets face rearward mid-body — **plug before drop-in**, wires lie in
  the bay and exit the end-wall tunnel (femur/tibia: toward the joint below;
  coax: out the bottom).
- **Strap:** retention strap over the servo tail on raised rim bosses (the
  case's rear top cap ridge stands 2.7 proud of the rim plane).

## Hardware per joint
4× **M2×9** CSK (case columns — **not** "stock+3mm"; floor 2.125 + 7.0 measured
column = 9.1 max, and the HFE-far pair takes ×13 on its ramped floor) · 4+1×
**M3×6** (horn + M3 center) · 4× **M3×8** (wheel, through boss, counterbored,
**no center screw**) · strap retention: **tibia**
zip tie (2026-07-16, Ø3.2 through-bore — see row 15); **coax** also zip tie
(2026-07-16, coordinator follow-up — Ø3.2 through-bore at x=±15.60 in its own
separate strap-pilot cut, coax.scad — hand-converted, not a
`strap_pilot_neg()` call, same axis-different-frame reason as before; 1.15mm
verified clear to the servo cavity, outboard side left thin/open to avoid
the known femur-rim graze at x≳16.6).

## Connection & tolerance map (audited 2026-07-06)
Every mate, its fit, and who provides location:

| # | Connection | Nominal fit | Locates via |
|---|---|---|---|
| 1 | servo body ↔ pocket walls | 0.45/side DROP-IN slip | — (guide only) |
| 2 | case columns ↔ floor holes | M2 in Ø2.3 (+csk Ø4.6 cone) | the 4 screws, ±0.15 → THE servo locator |
| 3 | case front-bottom ↔ platform | 0.1 axial seat gap | — |
| 4 | bay ↔ bay seat | 0.3 axial | — |
| 5 | horn Ø20 ↔ arm recess | Ø+0.3 (CLR_HORN 0.15), 0.4 deep | recess + 4×**M3** BCD |
| 6 | horn face ↔ arm underside | bolted contact | — |
| 7 | wheel Ø20 ↔ boss face | flat clamp, NO radial feature (impossible: boss 19 < wheel 20) | the 5 screws, ±0.2 |
| 8 | boss Ø19 ↔ floor window Ø21.5 | 1.25/side swing | — |
| 9 | wheel Ø20 ↔ window Ø21.5 | 0.75/side spin | — |
| 10 | tibia in femur slot (axial) | horn contact top / 0.4 bottom gap | bolted discs |
| 11 | tibia disc r16.05 ↔ slot | 1.0/side | bolted discs |
| 12 | femur disc r16.05 ↔ coax void r16.7 | 0.65 radial (was 0.35 — under print tol, widened) | — |
| 13 | knee arm ↔ shelf | flat + 2× Ø3.1 dowel-fit M3 (0.12) + 2× Ø3.4 | dowel screws |
| 14 | M3 heat-sets | **bore Ø4.0** (insert OD 4.6 — a 4.6 bore drops through; audit catch). ⚠ 2026-07-06: `HEATSET_D/L` were referenced but NEVER DEFINED — OpenSCAD silently dropped every insert bore from femur + shoulder STLs; now defined in `leg_v6_common.scad`, STLs rebuilt. If a printed femur/shoulder predates this, its shelf/deck has NO bores — reprint | — |
| 15 | strap ↔ pads | **zip tie** (2026-07-16, was M2.5 self-tap — 0.374mm wall to the servo cavity, no insert/nut fits, banned project-wide): Ø3.2 through-bore in the boss/rim (`strap_pilot_neg()`) + matching Ø3.2 bore in the strap, both at ±15.60 (shifted outboard off the old 14.25 for ≥1.0mm wall — 1.15mm boss-side / 1.44mm strap-side, TRIMESH-PROBED); pad top 17.6+, cap gap ≥0.2 | — |
| 16 | toe_v2 seat ↔ SM3_Foot | **designed seat** (2026-07-06, replaces the stock outline — it never mated the crescent, sloppy ring): core disc r12.35×14.2 on the shoe's inner face r12.53 (0.18 clr), boss r10.15 under the edge lips (r10.35), 2 sector key pockets take the mid-band tabs (tips r6.88); θ = 54 exactly, ±~2° slop. Contact plumb under the post by construction (dimensions.md SM3_Foot **v3**). **Gated: `check_shoe.py`** (0 penetration, seat gap median 0.28) | key pockets |
| 17 | cable plugs ↔ tunnel | 19×5.9 tunnel — **✅ AUD-3 RESOLVED 2026-07-10 (user caliper)**: real servo dual-connector exits side-by-side at 15.1mm (< 19 tunnel width), plug height <5.9mm (< tunnel height) — the cabled servo passes the tunnel plugged-in, no pocket change needed | — |
First-article: run an M3 through the Ø3.1 dowel pair (prints ~3.0), M2 through
columns, insert purchase test at Ø4.0 before committing the knee arms.

**Corner identity:** only TWO leg variants exist (L/R), two of each — but they
go on **DIAGONAL** corners, not one variant per side (**CORRECTED 2026-07-26**;
this section previously said "front and rear are the same parts translated").
`shoulder.scad` is the same crossmember GEOMETRY at both trunk ends and its
flange bolts to the trunk **end face**, so the rear crossmember is the front one
**yawed 180° about the vertical** — which flips which chirality each rear corner
needs. (**Since #377, 2026-08-15, the two ends are no longer the same PART**:
the front adds the SW1 Contura panel hole and prints from `shoulder_sw1.scad`,
the rear stays plain from `shoulder.scad`. One source, one flag, two STLs. The
yaw argument below is unaffected — it is about placement, not about the hole.) Verified
against the meshes (`../chassis/check_fit.py` `coax_to_trunk_bases()`, fixed the
same day; `docs/cad-review-2026-07-26.md` §1):

| corner | coax / femur / tibia | hip station | hfe axis (trunk frame) |
|---|---|---|---|
| FRONT +y | R parts | x +141.2 | x **+129.6** (11.6 toward the trunk) |
| FRONT −y | L parts | x +141.2 | x +129.6 |
| REAR +y | **L parts** | x −141.2 | x **−129.6** |
| REAR −y | **R parts** | x −141.2 | x −129.6 |

A wrong-chirality leg is caught immediately at assembly (its femur yoke points
*inboard*, under the trunk) — but plan the print batch and the pre-assembly
kitting off the table above, not off "L on the left, R on the right".

An ASSEMBLED leg becomes corner-specific via its servo
IDs (FL 1-3 · FR 4-6 · RL 7-9 · RR 10-12): after ID assignment + centering,
LABEL the coax (tape/marker: corner + IDs). The two legs of the SAME chirality
(now FL↔RR / FR↔RL) are physically identical — swapping them scrambles the gait
with zero visual cue.

## Fit gate (run after every geometry change)
`../../../.venv/bin/python check_fit.py` — places the REAL servo mesh
(`feetech_servo_models/converted_stl/servo.stl`) at each pocket pose and
samples 21k points against the part solid; any point inside = the part cuts
the servo. Wired into `build_all.sh`. Caught the bay-width error the box
model missed (real bay = full case width).

## Assembly order (constraint, not preference)
1. Bolt femur↔coax (hfe horn + wheel) — the horn screws are driven THROUGH
   the empty haa pocket; 2. plug + drop the haa servo, floor screws + strap;
   3. tibia↔femur anytime; 4. shoulder last. Servicing hfe = pull haa servo.
Keep 2-3 spare horn discs (hard falls can strip a spline).

### Cable dressing (backlog #18 — `cable_clip.scad`, TPU 95A, 20 installed = 5 per leg × 4)
Each flex zone gets a **clip at BOTH loop ends** (the existing zip tie
threads the leg's Ø3.2 pair AND the clip's matching holes — no leg mods):
- HIP loop (haa+hfe flex): coax tunnel-exit pair + femur x44 pair
- KNEE loop (kfe flex): femur x84 (yoke plate) + tibia x44 pair
Rules: loop radius **≥40 mm** (8× the Ø5 bundle) between clips — the
clip's bell-mouths control the exit bend, the spiral wrap (Ø6, BOM)
covers the free loop; zero tension at any plug (clips+ties take it);
**tug-test all 24 connector ends + every anchor** at assembly (#25).
femur x52 pair stays a bare-tie spare anchor.

**Free-loop length (backlog #18 / LA-14, `--cable` WARN gate, LA-20):**
the anchor separation itself SHRINKS across ROM below the ≥40mm-radius
(≥80mm-span) spec — KNEE loop (femur-x84 ↔ tibia-x44) drops to **~39mm**
at full kfe fold; HIP loop (coax tunnel-exit ↔ femur-x44) swings
**~60-79mm** across hfe. This is left OPEN as geometry (see LA-14) and
resolved by ASSEMBLY DISCIPLINE instead: dress each loop with slack
sized to the loop's own worst-case (tightest) span, not its neutral-pose
span. Concretely — **fold the joint to its mechanical limit FIRST, THEN
route + zip-tie the loop to both clips** so the loop is slack (never
taut) at full fold and simply has extra spare at neutral. Never dress
a loop at mid-ROM/neutral and call it done; that leaves it taut (and a
fatigue point) at the mechanical stop.

## Pre-walk firmware gates (from movement review)
Boot-settle ramp (PR #17) · servo torque limits written (open audit item —
trip backdrive protection) · stand-up keeps feet under knees (knee ≤80%
rating with splayed push-up).

## Verify (first-article print, before batching)

> **FIRST-ARTICLE RESULTS — 2026-08-10 (right leg, parts printed 08-02/08-06).**
> Recorded here because this list was written for exactly this run and read as
> untested until now.
>
> | # | check | result |
> |---|---|---|
> | 5 | **Yoke gap** 0.2-0.6 mm — *the one that can send the CAD back* | ✅ **PASS** — fits well |
> | 1 | **Servo pocket** drop-in, no rock about Z | ✅ **PASS** — seats, ribs visible |
>
> ⚠️ **"Slides in easily, extra room at the sides" is the DESIGNED feel, not a
> defect** — and it reads like one, which is why it is written down. The ribs are
> ramped at the mouth (`ANTIROT_MOUTH_PROUD` 0.02) and only reach full
> `ANTIROT_PROUD` 0.35 below z 10.5. Free drop ~1.7 mm → easy for 2.5 mm → light
> thumb press. Ribs present + seats + no rock = pass.
>
> 🔑 The rib check was the one that mattered and could not have been caught by
> feel: they are a RETENTION feature. Without them the joint torque reacts
> through 4 M2 **self-tap screws in the servo's own plastic columns** →
> back-out/wallow at ~1e5 cyc/hr (`servo_pocket_analysis.py`; no static SF
> captures it). With them the walls take it, SF 573, screws axial-only.
>
> ⬜ **Still to record:** does the RIB crush or the servo CASE score after a few
> insertions? The wall-bearing analysis assumes the rib profile survives.
> ⛔ **Items 2/3 (M3 through the horn BCD) are BLOCKED** until `knee_arm` ×1 and
> `shoulder_plate` ×2 (printed 08-02, pre-#263) are drilled Ø2.9 → 3.4.

1. Pocket fit (CLR_POCKET 0.45/side) — **this is NOT a free drop all the way
   down, and a print that needs a thumb press is not a failed print** (#167).
   The anti-rotation ribs stand `ANTIROT_PROUD 0.35` into a 0.45 pocket, so
   the nominal clearance AT THE RIBS is **0.10 mm/side** — inside the very
   print tolerance that 0.45 exists to absorb. What a good part feels like:

   - **free drop for the first ~1.7 mm** (`ANTIROT_Z[1]` = 13 sits that far
     below `CASE_TOP`, so nothing touches yet), then
   - **increasing resistance over the next 2.5 mm** as the `ANTIROT_LEADIN`
     taper engages (full-crush zone starts at z 10.5), then
   - **seats with a light thumb press.** Location still comes from the 4
     column screws, not the walls.

   OUT of tolerance is: needing tooling or a clamp, or the servo case galling
   rather than sliding. Free-falling to the floor is not a pass either — it
   means the ribs are missing or short.

   (0.30/side = the v5 press-fit calibration — do NOT "fix" it back. And do
   not "fix" the 0.10 mm either: the ribs are meant to interfere; the thin
   tip crushes to take up print tolerance and carry torque.)

   ⬜ **First article, record it:** does the RIB crush, or does the servo CASE
   score? The ribs are PA6-CF against a much softer case, so scoring is the
   likely outcome and is cosmetic — but `servo_pocket_analysis.py`'s wall-
   bearing claim assumes the rib profile SURVIVES, so the answer changes that
   analysis. Also check the seated servo for any rock about Z, which is the
   failure the ribs exist to prevent.
2. Knee-arm plate: seats flat on the shelf, diagonal Ø3.1 screws register
   snugly BEFORE the clearance pair; horn face flush under the plate ±0.2.
3. **M3** countersink flush (heads must NOT proud into the yoke arm plane).
   Use **button** heads on the wheel ×8/×14: an M3 SHCS head stands ~1.4 mm
   proud of the 1.6 mm counterbore, a button ~0.05 mm.
4. Heat-set **bore Ø4.0** — check insert purchase in PA6-CF at 5.7 deep. The **4.6 is the
   INSERT OD**, not the bore; `HEATSET_D = 4.0` in `leg_v6_common.scad` and a **Ø4.6 bore
   drops straight through** (row 14 of the fastener table above says exactly this, and calls
   it an audit catch — this line had reproduced the error the table was written to prevent).
   ⚠️ Two different inserts exist by design: **4.6 OD × 5.7 everywhere** (ruthex
   `B08BCRZZS3`) and **4.0 OD × 6.0 slim for the HFE block ONLY** (uxcell `B07R9SP532`) —
   the slim one is NOT a substitute in a Ø4.0 bore, where it would have zero interference.
5. Yoke gap: tibia end floats with 0.2-0.6 play. PA6-CF shrinks 0.2-0.8% —
   if the gap CLAMPS the discs, sand the arm faces or reprint at +0.3% Z.

## Build
```bash
/opt/homebrew/bin/openscad -o femur_v6.stl femur.scad
/opt/homebrew/bin/openscad -o /tmp/fit.png --imgsize=1000,650 \
  --camera=55,0,-2,60,0,25,330 preview_femur_fit.scad   # ghost-servo fit view
```
