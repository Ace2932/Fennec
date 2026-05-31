# Leg V4 — OnShape MCP Build Plan

Staged sequence to drive Jarvis OnShape MCP for the full NovaSM3 3-DOF
leg. Run **after** Jarvis is installed and OnShape API keys are entered.

**Topology (3 servos / leg, all STS3215):**

```
chassis
  └── Shoulder bracket    ── servo 1 (hip-roll, ID 1–4)
        └── Femur U-bracket ── servo 2 (femur-pitch, ID 5–8)
              └── Tibia U-bracket ── servo 3 (knee-pitch, ID 9–12)
                    └── Shank link ── TPU foot pad
```

Every bracket carries its STS3215 in a flange-pocket on one face and a
**688ZZ + sleeve** back-shaft bearing seat on the opposing arm of the U.
Daisy-chain TTL runs through a **14 × 5 mm slot** on every bracket
(2× JST-XH 3-pin side-by-side per `dimensions.md` §7).

**Authoritative dims:** `hardware/cad/dimensions.md` (STEP-verified).
The older `patterns.md` STS3215 block (`body_l=40 / horn_offset=9`) is
WRONG — use 45.40 × 24.80 × 36.80 and spline offset **+12.50 mm** in
+X from body center (dimensions.md §1, CRITICAL CORRECTION line 508).

---

## Step 0 — Pre-flight (you run, manually)

- [ ] Jarvis MCP installed + keys entered + Claude Code restarted
- [ ] Verify by asking: *"list my OnShape documents"* → should return
      tool call output
- [ ] Confirm STS3215 STEP path exists:
      `~/codebases/NOVA/feetech_servo_models/feetech_sts3215-1.snapshot.6/feetech-sts3215/STS3215_03a v1.step`

---

## Step 1 — Create document + import refs

Prompt I'll send Claude:

```
Create OnShape document "NovaSM3-Leg-V4".
Add a Variable Studio "leg-vars" with:
  hip_yoke_t     = 6   mm   // bracket wall thickness, hip side
  femur_link_l   = 110 mm   // hip-pitch axis → knee servo axis
  tibia_link_l   = 130 mm   // knee axis → foot tip
  wall_t         = 4   mm   // generic structural wall
  ttl_slot_w     = 14  mm   // dual JST-XH passthrough
  ttl_slot_h     = 5   mm
  bearing_od     = 16.05 mm // 688ZZ OD + press-fit clearance (NOVA_CLR press 0.05)
  bearing_h      = 5   mm
  sts_body_l     = 45.40 mm // STEP-verified
  sts_body_w     = 24.80 mm
  sts_body_h     = 36.80 mm
  sts_spline_x   = 12.50 mm // CRITICAL — spline offset from body center
  horn_bcd       = 14.0 mm
  insert_bore    = 4.0 mm   // Ruthex M3 heat-set
  insert_boss_od = 6.5 mm

Import STEP at <abs path to STS3215 v1.step> as static body "STS3215_ref".
Model a 688ZZ bearing as a flat ring (ID 8.0, OD 16.0, H 5.0) as static
body "Bearing_688ZZ".
```

---

## Step 2 — Reusable servo-grip feature

Build once as a **FeatureScript custom feature**. Reuse on hip, femur,
tibia brackets.

```
Create a FeatureScript feature "STS3215_holder":
  Inputs: which face, orientation (up/down/left/right), with_back_bearing (bool)
  Geometry:
    - Body pocket: rect(sts_body_l + 0.25, sts_body_w + 0.25) cut deep sts_body_h + 0.35
    - Front horn relief: through-cut circle Ø 22 at offset +sts_spline_x in +X
    - 4× M2 mount-screw holes on STS3215 flange (49 × 10 mm pitch — patterns.md line 213,
      but VERIFY against STEP since flange pattern may differ slightly)
    - if with_back_bearing:
        On opposite face, at +sts_spline_x: bearing pocket Ø 16.05, depth 5.5
        with 0.5 mm relief floor
    - TTL slot: cut rect(ttl_slot_w, ttl_slot_h) through bracket on the −X end face
      (cable IN) AND duplicated on the +X end face (cable OUT)
```

---

## Step 3 — Shoulder bracket

```
New part studio "Shoulder".
Sketch on top plane:
  - Chassis mount slab: rect(40 × 40), centered.
  - 4× M3 holes for chassis bolt pattern (mirror chassis pattern — TBD,
    use 28 × 28 mm square as placeholder until chassis doc exists).
Extrude slab down wall_t.
On −Z face: extrude downward an arm 25 mm tall, 40 mm long, 6 mm thick.
On that arm's outer face, apply STS3215_holder feature with:
  orientation = output-horn facing +Y (outboard from robot centerline)
  with_back_bearing = false  // shoulder uses single-shaft anchor to chassis
Add antenna for cable IN slot from chassis side (top), OUT toward femur.
```

Mate to expect later: chassis-Shoulder bolt-circle pattern = hip-roll axis.

---

## Step 4 — Femur U-bracket + femur link

```
New part studio "Femur".
Sketch the horn-side cap:
  - Disc Ø 22, 4× M3 clearance holes on horn_bcd at +45° from cardinal
    (matches STS3215 horn screw pattern, dimensions.md line 36).
  - Extrude 6 mm — this is the cap that bolts to the shoulder's hip servo horn.
From the cap, extrude a beam along +X, length femur_link_l, cross-section
  (12 × 14) — this is the femur structural link.
At the far end of the beam, build a U-bracket:
  - Two parallel arms 6 mm thick, spaced (sts_body_w + 12 + bearing_h*2) apart.
  - One arm: STS3215_holder applied, output-horn facing +Z (knee axis is Y).
  - Other arm: bearing seat for back shaft (688ZZ at +sts_spline_x position).
TTL slot: through the femur beam from horn-cap end → knee end.
  Carve a 14×5 channel down the beam centerline, exiting both U-arms.
```

---

## Step 5 — Tibia U-bracket + shank link

```
New part studio "Tibia".
Same horn-cap pattern as femur (mates to knee servo horn).
Extrude shank beam: length tibia_link_l, cross-section (10 × 12) tapering
  to (8 × 10) at foot end.
Foot end: flat circular pad Ø 35 with 1× M3 boss for TPU foot pad
  (foot pad already in patterns.md §8b — print separately in TPU).
TTL slot: shorter — only needs to terminate cleanly with a wire-anchor
  feature inside the U-bracket (knee is end of chain, no downstream servo).
```

---

## Step 6 — Assemble

```
New assembly "Leg-V4-Assembly".
Insert Shoulder, Femur, Tibia.
Mates:
  1. Shoulder.chassis_face → world XY plane, fastened
  2. Femur.horn_cap → Shoulder.hip_servo_horn, revolute (hip-roll axis = Z)
     Limit: ±45° (chassis clearance)
  3. Tibia.horn_cap → Femur.knee_servo_horn, revolute (knee axis = Y)
     Limit: −10° (full extension) to +120° (squat)
Insert Bearing_688ZZ instances at every back-shaft seat — verify slip-fit.
```

---

## Step 7 — Validation (truth-telling per Jarvis vision skill)

```
Run interference check across full joint sweep:
  - Sweep hip-roll −45° to +45° in 15° steps
  - At each, sweep knee 0 to +120° in 30° steps
  - Report any solid-solid intersection
Render multi-view PNGs at three poses: stand, full squat, full extend.
Confirm:
  - No clashes between femur beam and shoulder bracket through full sweep
  - No TTL channel crosses any rotating joint plane (cable would shear)
  - Back-shaft 688ZZ stays seated through full rotation
```

---

## Step 8 — Export

```
Export each part as STEP → save to hardware/cad/leg_v4/
  shoulder.step
  femur.step
  tibia.step
  leg-assembly.step
Export each part as STL → same dir.
Export multi-view PNGs → hardware/cad/leg_v4/renders/
```

**Connectivity validation (still mandatory even on OnShape exports
because slicer-side bool ops can fragment):**

```python
import trimesh
for stl in ["shoulder.stl", "femur.stl", "tibia.stl"]:
    m = trimesh.load(stl, force="mesh")
    assert m.is_watertight, f"{stl}: non-watertight"
    parts = m.split(only_watertight=False)
    assert len(parts) == 1, f"{stl}: {len(parts)} disconnected pieces"
```

---

## Step 9 — First-article gate (PA6-CF, real STS3215)

Before batching for 4 legs (= 12 brackets total), print **one set** in
PA6-CF and verify per `patterns.md` §11 first-article protocol:

1. Real STS3215 sits flange-flat in pocket, no rocking
2. 688ZZ press-fits with thumb (no arbor), does not spin free
3. M2 self-tappers bite Ruthex M3 inserts cleanly
4. TTL passthrough: 2× JST-XH 3-pin cables slide both directions
5. Joint sweep matches OnShape assembly limits — no binding

Only after pass: queue the remaining 11 brackets.

---

## Open questions to resolve before printing

- [ ] Chassis bolt pattern for shoulder mount (depends on chassis doc — TBD)
- [ ] Femur + tibia link lengths — current 110 / 130 are guesses; measure
      against gait spec (stride length, ground clearance) before commit
- [ ] STS3215 flange screw pattern — `dimensions.md` is silent on flange
      hole spacing (only mentions 4× M2.5 rear-plate); patterns.md says
      49 × 10 mm. **Verify against STEP file before cutting holes.**
- [ ] Hip-roll vs hip-pitch axis assignment — which is servo 1? Affects
      whether shoulder bracket rotates the whole leg outboard (roll) or
      swings femur fore/aft (pitch). NovaSM3 v1 convention TBD —
      check `docs/setup-servos.md`.
