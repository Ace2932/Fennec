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
| `femur.scad` (+`_L`) | ✅ verified | HFE pocket + knee yoke; horn seat @ x=106.9, BCD ±4.95, idler M3 + hip pad w/ heat-set; watertight; prints flat, no pocket supports |
| `tibia.scad` (+`_L`) | ✅ verified | KFE pocket + straight blade; Ø7 foot post @ x=129.0 exact, post z −21..−40 → center −30.5 = measured jog (stock SM3_Foot rubber slips on); zip anchors |
| `coax.scad` (+`_L`) | ✅ verified | HAA pocket (horn −Y to shoulder, insert from front, rear countersunk M2.5 + rear pad/heat-set for the shoulder's yoke); femur yoke on X: horn seat (11.6, −9.5) inboard arm, M3 idler outboard, bridge clears full femur-disc sweep; femur mid-plane @ 33.8 |
| shoulder interface | ⬜ next | stock shoulder frame + BCD14 adapter for STS horn (stock cutout is 25t-hobby sized) + rear idler arm |

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
Cable loops: ≥8mm bend radius, zero tension at plugs (anchors take it).
Keep 2-3 spare horn discs (hard falls can strip a spline).

## Pre-walk firmware gates (from movement review)
Boot-settle ramp (PR #17) · servo torque limits written (open audit item —
trip backdrive protection) · stand-up keeps feet under knees (knee ≤80%
rating with splayed push-up).

## Verify (first-article print, before batching)
1. Pocket drop-in fit (CLR_POCKET 0.25/side, PA6-CF) — servo should seat with
   light push, no rock.
2. Horn seat depth: horn face flush with arm underside ±0.2.
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
