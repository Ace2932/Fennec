# CAD design review — 2026-07-26

Scope: the canonical mechanical design as committed — `hardware/cad/leg_v6/`
(coax, femur, knee arm, tibia, shoulder, plates, straps, TPU parts),
`hardware/cad/chassis/` (trunk-derived parts, riser, battery pocket, head,
shoulders-in-assembly), and the geometry each of them exports to
`nova_description` / `nova_locomotion` / `nova_ops` / `sim/nova_mjx`.

Method: read every `.scad` + gate script, then re-ran the parts of the gates
that do not need the out-of-repo servo mesh against the committed STLs, plus
independent probes (see §5 for exactly what was executed). Two findings are
structural; the rest are small.

**Tracking:** the placement fix and the doc corrections landed in
[#163](https://github.com/Ace2932/Fennec/pull/163). Everything left open has an
issue: [#164](https://github.com/Ace2932/Fennec/issues/164) (regenerate the rear
ROM rows + pin the rear hfe sign — **sev:high**, §1),
[#165](https://github.com/Ace2932/Fennec/issues/165) (URDF/MJX hip grid, §2),
[#166](https://github.com/Ace2932/Fennec/issues/166) (gate portability + CI, §4),
[#167](https://github.com/Ace2932/Fennec/issues/167) (rib vs drop-in acceptance,
§4), [#168](https://github.com/Ace2932/Fennec/issues/168) (proud wheel screw
heads, §4).

---

## 1. 🔴 The rear hip is placed by a translation, but it is physically a 180° yaw

**Where:** `hardware/cad/chassis/check_fit.py` `coax_to_trunk_bases()` (and the
same bug in `preview_assembly.py`). Introduced 2026-07-25 as a *fix* for an
earlier improper (reflected) placement. **Both** revisions were wrong; the
physical option was never considered.

**Why a yaw is forced** — every number from this repo:

- `shoulder.scad` is ONE part at both ends ("SAME part both ends; print 2").
- Its flange (shoulder-local `y −77.7`) bolts to the trunk **end face**, and
  `trunk.stl` bounds that face at `x ±63.5`. `63.5 + 77.7 = 141.2 = HIP_FA` —
  that identity is *why* the hip station is ±141.2 in the first place.
- Under a pure translation the rear flange lands at `x −218.9`: **155 mm behind
  the trunk it is bolted to**. The rear coax's horn face lands at `−123.4`
  while the rear shoulder's horn plane is at `−158.9` — 35.5 mm apart and
  facing opposite ways.
- `check_fit.py` **already places the shoulder correctly** (cases 3 and 6 keep
  `end` inside the rotation → rear flange on the end face). So the gate was
  bolting a translated rear leg onto a yawed rear shoulder — an internal
  contradiction inside one file.

**Consequences measured against the meshes:**

| | translated rear (shipped) | yawed rear (correct) |
|---|---|---|
| rear hfe axis | `x −152.8` | `x −129.6` (11.6 mm toward the trunk, same as the front) |
| rear leg station error | 23.2 mm too far aft | — |
| leg chirality | same variant per side | **diagonal pairs** (§3) |
| front/rear hfe window | "the two ends do not share a window" | identical windows (mirror images) |

**Downstream, and this is the sharp end:** `hfe_envelope.py` consumes
`coax_to_trunk_bases()` to generate `rom_envelope_table.py`, which
`nova_ops.safety_envelope.wrapper.publish()` applies per leg on every
`/joint_commands` message — and the same 2026-07-25 batch loosened
`limits.py`'s hfe scalar to mechanical ±86°, making that table the **sole**
chassis protection. The shipped rear rows therefore do not describe the built
rear leg. Re-measured with the corrected placement (same targets, same 5 mm
proximity rule, leg-local sign, 2° scan):

| cell (haa, kfe) | shipped REAR row | re-measured REAR | shipped FRONT | re-measured FRONT |
|---|---|---|---|---|
| 0, −109 | [−77.2, +95.0] | [−94, **+66**] | [−95.0, +67.9] | [−94, +66] |
| 0, −50 | [−77.2, +95.0] | [−94, **+68**] | [−95.0, +70.0] | [−94, +68] |
| 0, 0 | [−77.2, +95.0] | [−94, **+72**] | [−95.0, +73.5] | [−94, +72] |
| −15, −109 | [−37.2, +95.0] | [−94, **+14**] | [−95.0, +13.8] | [−94, +12] |
| +40, −109 | [−75.6, +95.0] | [−94, **+46**] | [−95.0, +47.2] | [−94, +46] |

The front rows reproduce the shipped table to ~2° (the scan step) — that is
what validates the method. The rear rows come out **equal to the front's**,
as mirror symmetry requires. Two independent tells that the shipped rear rows
are artefacts: they are identical across *all ten* kfe values (with the rear
leg backwards its knee folds away from the chassis, so kfe stopped mattering),
and their haa profile is unrelated to the front's.

**Applied here:** the placement is fixed in `check_fit.py` (front bases
byte-identical; only the two rear bases move) and in `preview_assembly.py`,
each with the derivation in the docstring/comment. Warnings added at
`hfe_envelope.py` and `nova_ops/rom_envelope.py`.

**Left to the owner (needs the real `servo.stl`, ~3 min on that machine):**

1. Regenerate `rom_envelope_table.py` and copy it to `nova_ops/`.
2. While regenerating, **negate the rear rows** — and note that nothing in the
   pipeline does this yet. `hfe_envelope.py` sweeps `hfe` inside `leg_cloud()`,
   i.e. in the coax frame, where `+hfe` = "fold toward the trunk" for whichever
   leg it is placed on. The canonical hfe axis is **uniform in world** for all
   four legs (`leg.macro.xacro`: `axis xyz="0 1 0"` on every hfe joint), so
   canonical `+hfe` swings all four feet rearward — toward the trunk at the
   front, *away* from it at the rear. Hence
   `canonical_rear = (−hi_local, −lo_local)`.

   Under the old translated placement this was a **no-op** — the rear local
   frame was world-aligned with the front's, so the table came out canonical by
   accident. The placement fix removes the accident, so an un-negated
   regeneration would put the rear bound on the *wrong side*: permitting exactly
   the folds that reach the riser and forbidding the harmless ones. Self-check
   after regenerating: rear rows stay bounded **below** (lo ≈ −66 at haa 0 /
   kfe −109, hi ≈ +95) — same side as today, just tighter and now kfe-dependent.

   Only `hfe` needs an end-keyed sign. `haa` is keyed on **side** in
   `hfe_envelope.clear()`, and outboard is side-determined rather than
   end-determined, so it survives the yaw untouched. The servo frame is the exact
   dual — there only `haa` moves (#170, whose `HAA_INBOARD_SIGN` comes out
   **diagonal**, FL↔RR / FR↔RL, independently corroborating §3).
3. Expect the crouch/ROM cases to move. They should stay green: the corrected
   rear is the front's mirror and the front already passes; the residual
   asymmetries are the head (front-only) and the skid rails (`x −55..75`).
4. Note what *becomes* correct for free: the crouch sweep's per-end window
   (`hfe_lo = −50 FRONT / −86 REAR`, `+50` both) is written in leg-local terms,
   where `+hfe` folds the foot toward the trunk and `−hfe` swings it away — so
   the −50 front cap is the head-clearance one and the rear's −86 is the
   no-head-behind-us allowance. With the translated rear those two directions
   were swapped at the rear end, i.e. the sweep was granting −86 in the
   direction that actually reaches the chassis. The fix makes the existing
   numbers mean what they say; no window edit needed.
5. Decide whether to gate motion before then. A safe interim is to intersect
   the rear rows with the front rows **and their mirror** (symmetric window):
   valid under either sign reading, at the cost of clipping deep-fold rear
   postures. Not applied here — it changes runtime behaviour and clips gait.

## 2. 🔴 URDF/MJX carry the stock hip grid; v6 moved the pitch axes 11.6 mm/end

`dimensions.md`'s "Hip grid 282.4 × 78.1" mixes two references, which is legal
for the stock robot and misleading for v6:

- the **lateral** half (39.05) is measured to the **haa** horn (`X −31.6` vs
  centre 7.45);
- the **fore-aft** half (141.2) is measured to the **hfe** axis (`Y −155.4` vs
  centre −14.2) — the stock haa station is 171.2.

That is fine for stock: the haa axis is fore-aft-parallel, so its own station
along that axis is a kinematic no-op, and putting the URDF hip origin at the
hfe station with `hip_to_upper_x = 0` is exact.

v6 is different. `shoulder.scad` fixes the haa station at ±141.2 (trunk end
face + 77.7 flange) and `coax.scad` puts the hfe axis at `HFE_Y = 11.6` along
that axis — **toward the trunk at both ends** once §1 is applied. So the built
pitch axes are at **±129.6**, spacing **259.2 mm**, while:

- `nova.urdf.xacro`: `body_half_x = 0.1412`, `hip_to_upper_x = 0.0`
- `sim/nova_mjx/build_mjcf.py`: `MOUNT.x = 0.1412`, `HAA_TO_HFE[0] = 0.0`

→ the model's stance is **23.2 mm (8.9 %) longer fore-aft than the robot**, on
a machine whose CoM offsets are argued about at ±5 mm (backlog #43) and whose
gaits are trained in that model. Fix is one of `body_half_x → 0.1296` or
`hip_to_upper_x → ∓0.0116` (they are not equivalent for the *trunk*-relative
CoM, only for the leg chain).

**Not changed here.** It moves the geometry every trained policy was fit to,
and choosing between the two forms is a gait/sim-lane call. Flagged in
`dimensions.md`, `nova.urdf.xacro`, `build_mjcf.py`, and B2.

Everything else in the chain checks out: femur 106.9 / tibia 129.0 / lateral
33.8 + 0 + 30.5 = 64.3 agree across `dimensions.md`, `leg_ik.py`,
`nova.urdf.xacro`, `nova.xml`, `build_mjcf.py`; `mount_z` 38.0 ≈ chassis
`HIP_Z` 38.05; `body_half_y` 39.0 ≈ shoulder `HIP_X` 39.05.

## 3. 🟠 Leg chirality pairs diagonally, not per side

Direct consequence of §1, verified by placing the real `coax_R` geometry at all
four corners and asking which one puts the femur yoke **outboard**:

| corner | needs | (leg_v6 README said) |
|---|---|---|
| front +y | R | R |
| front −y | L | L |
| rear +y | **L** | R |
| rear −y | **R** | L |

Still two variants, two of each — but not "L on the left, R on the right".
A wrong-chirality leg is caught at once during assembly (its femur points
inboard, under the trunk), so this is a kitting/instruction defect rather than
a scrap-parts one. `leg_v6/README.md` "Corner identity" is corrected, including
the ID-labelling note that followed from it (the identical pair is now FL↔RR /
FR↔RL).

## 4. 🟡 Smaller items

- **Cable service loops are still under spec, on all three joints** (known:
  backlog #18 / LA-14). Re-ran `--cable`: worst-case spans KNEE 51.6 mm
  (kfe 118), HIP 59.9 mm (hfe 0), HAA 56.9 mm (haa +25) against an 80 mm
  target. The HAA loop is the one to watch — it is the *largest* ROM on the
  leg and it is the only one whose fixed end is a bare flange grommet. The
  documented mitigation (fold-to-limit, then zip) is an assembly discipline
  with no gate; the WARN is informational and cannot fail the build.
- **Anti-rotation ribs vs the "drop-in" acceptance test.** `CLR_POCKET 0.45`
  minus `ANTIROT_PROUD 0.35` leaves 0.10 mm nominal at the ribs, i.e. inside
  the print tolerance that motivated 0.45 in the first place. The README's
  first-article criterion ("drops in under gravity plus a wiggle") and the rib
  design ("crush ribs … the thin tip crushes to take up print tolerance") will
  not both hold on every print — expect a light press at the ribs, and expect
  a PA6-CF rib to score the servo's softer case (the 2.5 mm lead-in taper
  addresses entry, not steady-state). Worth restating the acceptance test as
  "free to the rib zone, light thumb press past it" rather than treating a
  press as a failed print.
- **Wheel-BCD screw heads stand ~0.9 mm proud** (Ø5.2 × 1.6 mm counterbore vs
  a ~2.5 mm M2.5 SHCS head), 8 per leg, on the femur underside and coax
  outboard flank. Free air both places; snag/scuff only. Noted in
  `fastener-schedule.md` with the low-head option.
- **Stale comments corrected** (this is the failure mode that has bitten this
  design twice — undefined `HEATSET_D`, dots cutting air — so they are worth
  the churn): `femur.scad` `SUB_X1 (32)` → 21; `leg_v6_common.scad` header
  "Ø24 window" → Ø21.5 and the idler relief "Ø7" → Ø9.5; `coax.scad`'s
  pre-rev-3 "cap ridge stands 0.2 proud" (it is 0.35 *behind* the horn plane
  since rev 3, giving the intended 1.15 mm strap gap);
  `fastener-schedule.md`'s "still cuts a 5th center hole" (removed under #51).
- **Neither CAD gate can run anywhere but the author's machine.** `check_fit.py`
  (both), `power_board_model.py`, and friends hardcode `/Users/afox/...` for
  `servo.stl`, the stock trunk STL, the KiCad board, and even the leg directory
  they live next to. CI runs only `firmware-compile` + `ros-pytest`, so no CAD
  gate runs in CI at all — a stale-STL or transform regression has exactly one
  place it can be caught, and it is a laptop. An `NOVA_ROOT` env override plus
  repo-relative defaults would make the leg gates CI-able today (only the
  servo mesh is genuinely external — vendoring it, or a decimated proxy, would
  close that too).

## 5. ✅ What was verified healthy

- `leg_v6/check_fit.py`, servo-independent parts, run against the committed
  STLs: **all green** — LA-21 through-hole probe (48 bores incl. both
  strap-zip conversions and the mirrored coax notch), #67 fastener/heat-set
  reachability + marker dots, HFE horn-bolt channels, KFE joint gate
  (knee-arm horn BCD, femur wheel BCD, knee-arm mount, shelf heat-set blind
  pockets, both chiralities).
- `mesh_health.py` on all 16 printable leg STLs: watertight, single body,
  positive volume. (`leg_v6_assembly_preview.stl` fails by design — it is a
  union of parts, not a printable.)
- The leg's own tolerance/connection map (README §"Connection & tolerance map")
  matches the code it describes, including the fits that are deliberately
  sub-mm (r13 0.40 mm yoke/floor gap, 1.15 mm zip-bore walls).
- Link lengths and joint stations agree across CAD → URDF → IK → MJX (§2),
  except the fore-aft hip grid.

## 6. Not touched, deliberately

`rom_envelope_table.py` (both copies) — regenerating it with a stand-in servo
mesh would put unverified numbers into a safety path. `body_half_x` /
`HAA_TO_HFE` — see §2. The runtime clamp in `wrapper.py` — see §1 item 4.
