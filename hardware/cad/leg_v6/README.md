# Leg V6 — functional STS3215 leg (designed-for-assembly)

> Top-level design: [`docs/design-outline.md`](../../../docs/design-outline.md)

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
| `leg_v6_common.scad` | ✅ rev 2 | mesh-verified servo frame, pocket/platform/horn-couple/wheel-boss/strap/zip modules; CLR_POCKET 0.45 DROP-IN |
| `femur.scad` (+`_L`) | ✅ gated | HFE pocket, knee fork w/ FLAT SHELF (top arm is bolt-on), wheel boss, vents, cable groove+anchors, strap pads, side dots; **zero bridging** |
| `knee_arm.scad` (print 4) | ✅ gated | bolt-on knee top arm — horn-seat face prints ON BED; 4× M3 into shelf heat-sets, diagonal pair Ø3.1 close-fit (registration) |
| `tibia.scad` (+`_L`) | ✅ gated | KFE pocket + blade + **toe_v2 designed seat** (disc/boss/key-pockets, mates the SM3_Foot crescent — `check_shoe.py` gated) @129.0, jog −30.5 outboard (stock stance); vents, anchors, dots |
| `coax.scad` (+`_L`) | ✅ gated | HAA pocket (horn −Y, front insert), femur yoke (horn arm 16.6 / wheel boss →51.5, bridge 7.4), front strap pads, vent, bottom cable tunnel |
| `strap.scad` (print 4+) | ✅ | servo tail retention, 2× M2.5 self-tap into rim-pad pilots |
| shoulder | ✅ gated (rev 2026-07-06) | v6 crossmember per trunk end; **riser interface rev**: flange center notch (x ±26 above z 19.5) + 2× Ø3.4 riser hold-down holes (x ±40, z 26.95) — see `../chassis/README.md` |

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
- **Joints bolted BOTH sides:** yoke top arm on the Ø20 horn (4× M2.5 BCD14 +
  M3 center); yoke bottom arm's **Ø19 boss reaches through the Ø21.5 floor
  window and bolts the Ø20 BOTTOM WHEEL** (standard-fitted; 4× M2.5 + M2.5
  center, head counterbores modeled). No heat-set/idler-boss hack.
- **Cables:** the case's rear-bottom connector bay (3.9 deep) is seated by the
  floor; sockets face rearward mid-body — **plug before drop-in**, wires lie in
  the bay and exit the end-wall tunnel (femur/tibia: toward the joint below;
  coax: out the bottom).
- **Strap:** retention strap over the servo tail on raised rim bosses (the
  case's rear top cap ridge stands 2.7 proud of the rim plane).

## Hardware per joint
4× M2 ≈stock+3mm (case columns, countersunk) · 4+1× M2.5×6 (horn + M3 center)
· 4+1× M2.5×8 (wheel, through boss, counterbored) · 2× M2.5 self-tap + strap.

## Connection & tolerance map (audited 2026-07-06)
Every mate, its fit, and who provides location:

| # | Connection | Nominal fit | Locates via |
|---|---|---|---|
| 1 | servo body ↔ pocket walls | 0.45/side DROP-IN slip | — (guide only) |
| 2 | case columns ↔ floor holes | M2 in Ø2.3 (+csk Ø4.6 cone) | the 4 screws, ±0.15 → THE servo locator |
| 3 | case front-bottom ↔ platform | 0.1 axial seat gap | — |
| 4 | bay ↔ bay seat | 0.3 axial | — |
| 5 | horn Ø20 ↔ arm recess | Ø+0.3 (CLR_HORN 0.15), 0.4 deep | recess + 4×M2.5 BCD |
| 6 | horn face ↔ arm underside | bolted contact | — |
| 7 | wheel Ø20 ↔ boss face | flat clamp, NO radial feature (impossible: boss 19 < wheel 20) | the 5 screws, ±0.2 |
| 8 | boss Ø19 ↔ floor window Ø21.5 | 1.25/side swing | — |
| 9 | wheel Ø20 ↔ window Ø21.5 | 0.75/side spin | — |
| 10 | tibia in femur slot (axial) | horn contact top / 0.4 bottom gap | bolted discs |
| 11 | tibia disc r16.05 ↔ slot | 1.0/side | bolted discs |
| 12 | femur disc r16.05 ↔ coax void r16.7 | 0.65 radial (was 0.35 — under print tol, widened) | — |
| 13 | knee arm ↔ shelf | flat + 2× Ø3.1 dowel-fit M3 (0.12) + 2× Ø3.4 | dowel screws |
| 14 | M3 heat-sets | **bore Ø4.0** (insert OD 4.6 — a 4.6 bore drops through; audit catch). ⚠ 2026-07-06: `HEATSET_D/L` were referenced but NEVER DEFINED — OpenSCAD silently dropped every insert bore from femur + shoulder STLs; now defined in `leg_v6_common.scad`, STLs rebuilt. If a printed femur/shoulder predates this, its shelf/deck has NO bores — reprint | — |
| 15 | strap ↔ pads | Ø2.05 pilots, M2.5 self-tap; pad top 17.6+, cap gap ≥0.2 | — |
| 16 | toe_v2 seat ↔ SM3_Foot | **designed seat** (2026-07-06, replaces the stock outline — it never mated the crescent, sloppy ring): core disc r12.35×14.2 on the shoe's inner face r12.53 (0.18 clr), boss r10.15 under the edge lips (r10.35), 2 sector key pockets take the mid-band tabs (tips r6.88); θ = 54 exactly, ±~2° slop. Contact plumb under the post by construction (dimensions.md SM3_Foot **v3**). **Gated: `check_shoe.py`** (0 penetration, seat gap median 0.28) | key pockets |
| 17 | cable plugs ↔ tunnel | 19×5.9 tunnel — **✅ AUD-3 RESOLVED 2026-07-10 (user caliper)**: real servo dual-connector exits side-by-side at 15.1mm (< 19 tunnel width), plug height <5.9mm (< tunnel height) — the cabled servo passes the tunnel plugged-in, no pocket change needed | — |
First-article: run an M3 through the Ø3.1 dowel pair (prints ~3.0), M2 through
columns, insert purchase test at Ø4.0 before committing the knee arms.

**Corner identity:** only TWO leg variants exist (L/R — front and rear are the
same parts translated). An ASSEMBLED leg becomes corner-specific via its servo
IDs (FL 1-3 · FR 4-6 · RL 7-9 · RR 10-12): after ID assignment + centering,
LABEL the coax (tape/marker: corner + IDs). Two assembled left legs are
physically identical — swapping FL↔RL scrambles the gait with zero visual cue.

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

### Cable dressing (backlog #18 — `cable_clip.scad`, TPU 95A, print 20)
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
1. Pocket DROP-IN fit (CLR_POCKET 0.45/side) — servo drops in under gravity
   plus a wiggle, no force; location comes from the 4 column screws, not the
   walls. (0.30/side = the v5 press-fit calibration — do NOT "fix" it back.)
2. Knee-arm plate: seats flat on the shelf, diagonal Ø3.1 screws register
   snugly BEFORE the clearance pair; horn face flush under the plate ±0.2.
3. M2.5 countersink flush (heads must NOT proud into the yoke arm plane).
4. Heat-set bore Ø4.6 — check insert purchase in PA6-CF at 5.7 deep.
5. Yoke gap: tibia end floats with 0.2-0.6 play. PA6-CF shrinks 0.2-0.8% —
   if the gap CLAMPS the discs, sand the arm faces or reprint at +0.3% Z.

## Build
```bash
/opt/homebrew/bin/openscad -o femur_v6.stl femur.scad
/opt/homebrew/bin/openscad -o /tmp/fit.png --imgsize=1000,650 \
  --camera=55,0,-2,60,0,25,330 preview_femur_fit.scad   # ghost-servo fit view
```
