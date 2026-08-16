# Chassis — trunk riser bay (+ Jetson case + integrated head: D456 + L2)

> Top-level design: [`docs/design-outline.md`](../../../docs/design-outline.md)
> · trunk mate dims: [`../dimensions.md`](../dimensions.md) §11 · reasoning:
> `~/claude-memory/nova-proj/project-chassis-integration.md`

Started 2026-07-06. First chassis-lane part: the printed **riser bay** that
replaces the stock trunk lid — its top IS the Jetson tray and the L2 mast
base (design-outline packaging). OpenSCAD + real-mesh fit gate, per leg_v6
doctrine (the cad/README's "OnShape for chassis" note predates leg_v6; this
lane follows the leg_v6 track).

## What the trunk ACTUALLY is (mesh-measured 2026-07-06, `measure_trunk.py`)

The "~118 × 100 × 40 interior tub" assumption was WRONG. The stock
`SM3_Frame_ChassisTrunk.stl` (127 × 110 × 46.91, floor z0, +x = the printed
"F" arrow) is an open frame:

| Feature | Measured |
|---|---|
| floor slab | top z 3.9; big rear opening + corner cutouts (cable/battery pass) |
| side walls | 6.0 thick, inner y ±48.93, **top z 29.0**, notch x 18.2..31.2 → z 12.5 (both) |
| ends | **OPEN above the floor** — closed at assembly by the v6 shoulder flanges |
| corner wedges | 4× leaning slabs (~35°) rising wall-top→plateau; **plateau tabs z 46.91**, x ±(53.3..63.5), y ±(29.9..36.0) |
| wedge windows | ~9.4 × 6.4 under each plateau tab (stock cover hooks; unused by us) |
| shoulder bolt bores | Ø3.16 along x at (y ±51.75, z 5 & 24), 6.5 deep, both ends — matches `shoulder.scad` |
| interior clear width | 97.86 (stack 90 fits, 3.9/side) |

## Parts

| Part | Status | Notes |
|---|---|---|
| `riser_bay.scad` | designed, gated | one print, 126.7 × 110 × 42.9 (z 29.0..71.9). **Reworked 2026-07-07 for the case pivot**: dropped the 96.5×75.4 Jetson standoff grid + all hood pads/inserts; added the case PORT-END cable slot (x −58..−46, y ±18 = also the case bottom-vent breather), 4 cradle deck ties (47.3/−59.0, ±50.35). **Head interface RETIRED 2026-07-07** — the L2-column deck base, L2 cable drop, front-wall camera register + USB grommet removed (head moved fwd onto `neck_bracket.scad`); **SMA bulkheads also removed** — WiFi MIMO antennas consolidated to the head ears (higher, clear of the CF chassis) |
| `spacer.scad` | **RETIRED** | Jetson standoff washers — unused now the board is in the official case (kept in build_all for reference) |
| `trunk.scad` / `trunk_build.py` | **designed, gated (2026-07-10)** | **DERIVED TRUNK** — stock Nova-SM3 trunk geometry (unmodified, imported) + 10 MODELED fastener bores (battery mount ×6, shoulder-foot CSK ×4) so nothing is drilled at assembly; the shoulder-flange end-wall bores (×8) turned out to be already-stock (measured), no cut needed. Shipped `trunk.stl` is built by `trunk_build.py` (trimesh + manifold3d) — see its docstring for why, not the OpenSCAD render (a pre-existing, hole-unrelated mesh-tessellation quirk in the stock STL fails a strict watertight re-check under either engine; `check_fit.py`'s own in-memory asserts are the real gate). `check_fit.py` case 13 verifies every hole sits on its mating part's bolt axis |
| `battery_pocket.scad` | designed, gated | rear-loading belly tray, 6× M3 sandwich mount through the floor (**part-5 plate must adopt the (±40/0, ±26.5) pattern**; hole now MODELED in `trunk.scad`, no drilling), velcro fence at the rear opening |
| `head.scad` | **RE-ARCHITECTED + gated (2026-07-07)** | **forward HEAD on the front-shoulder "neck"** — moved OFF the riser front and FORWARD onto the front-shoulder top so it projects ahead like a fox (not a turret). Bolts to `neck_bracket.scad`, NOT the riser. Sensors shifted **DX+73 DZ+6** vs the old riser head (`forward_head_study.py` = the proof): D456 27° down-tilted face, back-face ctr **(143,0,111.5)**, body x136.4..172.7 z86.8..124.4 y±61.9; L2 crown center **x126.5**, optical z~160, seat 128. Camera bottom clears the front horn-plate top (+2.0) + the bracket base (+3.25); camera top +3.6 under the L2. **0 front-leg hits** across the full ROM. Mounts via a rear boss → 4× M3 into the bracket wall (tall couple). L2 = 4 crown screws from below; camera bolts on the bench. **Right-angle USB-C** (BOM). Print BOSS-DOWN. STYLE (fennec ears/skull) = WIP, default off |
| `neck_bracket.scad` | **designed, gated (2026-07-07)** | **front-shoulder-deck adapter** for the fwd head (user call: separate bracket, keeps the shoulder gate-clean + print-2-identical, head stays removable). Base plate on the deck top (z79.55); **4 corner bolts drill THROUGH the deck at first assembly** (M3 + nyloc below, reached through the deck window + open aperture — NO shoulder-mesh change). Tall rear mount wall (x113..121, to z106) with 4× M3 heat-sets (rows z89/100) = the head-mount face; aft gusset + base-bolt couple react the forward-tipping moment. Cable slot over the deck window (L2 pigtail → C-box → trunk). Print base-down, PA6-CF |
| ~~`l2_mast.scad`~~ **RETIRED** | → `head.scad` | standalone L2 mast; folded into the head crown. File kept (RETIRED header) for its reused bore/flange/bolt knowledge; not built, not gated |
| ~~`d456_head.scad`~~ **RETIRED** | → `head.scad` | v3 periscope; tilted the D456 UP behind the chassis and the trunk front cut its near-ground view. File kept (RETIRED header) for its D456 2×M3@94.4 mount + USB-C routing knowledge; not built, not gated |
| `../leg_v6/shoulder.scad` | **rev'd ×4** | + center notch (x ±26 above z 19.5) + 2× Ø3.4 riser holes (x ±40, z 29.35) + **battery-lead bottom notch** (x ±10 to z −26 = trunk z 12) + **flange floor FEET + deck gussets** (2026-07-06 joint-stiffening, user catch "barely connected": feet bolt the flange bottom to the trunk floor corners at (±59.5, ±42) — M3×14 csk from BELOW, hole now MODELED in `trunk.scad` (no drilling; **DONE 2026-07-10** — was the floor_plate drill template); gussets flange→deck-ext at x ±40); leg_v6 + chassis gates re-run (new shoulder-vs-trunk case in check_fit) |
| `floor_plate.scad` | designed, gated | 2.0 plate = mezzanine seat (top 5.9) + battery-sandwich csk pattern + **drill template** for all 10 floor holes; stack pilots at (−40.5/+33.5, ±33) from the power_v2 fab file (74×66); **stack ctr x −3.5** (rear edge 0.5 off the trunk corner posts, front corners clear the front slabs by 0.8) → rear-only slab trim + CoM −3.5; corner clips for the post base flare; front edge x 45 clears the raised stock "F". **5191 slots REMOVED 2026-07-07** — the calipered block is 61.6×20×46.5 and there is NO clean captive spot on the robot for it (below = leg-crouch space, rear-center = shoulder flange, trunk interior = mezzanine stack; all gate-verified conflicts). **5191 = ASSEMBLY-TIME external mount** (bracket/zip-tie to the rear-shoulder exterior or trunk rear, found empirically with real parts; fuse close to the battery-lead entry). Leads: pack rear → up through the rear shoulder flange notch |
| `skid_rail.scad` | designed, gated | TPU 95A belly skids ×2 (backlog #15): keyed+glued under the tray, new lowest z −42.2; E-stop-limp collapse lands HERE, not on the pack. Inboard-haa 15° cap verified intact with rails in the crouch gate |
| ~~tray hood~~ **RETIRED** | — | Jetson heatsink CALIPERED 34.9 (not 21.5) → heatsink top 113.1 collides the L2 plate. **DECISION 2026-07-07 (user): adopt the OFFICIAL JETSON CASE** (110.5×95.2×38.5, `jetson_case_ref.stl`) instead of the bespoke tray+hood. Case on the deck → top 110.4, clears L2 by 4. Drops the hood; E-stop pod + OLED move off the hood (new homes TBD). Repackaging in progress: case cradle mount + L2/D456/SMA refit |
| `jetson_case_mount.scad` | **designed, gated** (`check_fit.py` case 12) | deck cradle + corner hold-downs for the official case (bottom is vented — mount via 4 drilled corners); riser deck reworked (old Jetson standoffs + hood pads removed). Hold-down consolidated into `jetson_clamp_bar.scad` (2 bars, replaced 4 corner clamps) |

## Riser design (all trunk-frame numbers)

- **Seat**: side skirts (3.2, outer flush y ±55) rest ON the wall tops
  (z 29.0) — two full-length rails = primary datum. End walls (x ±60.15..63.35)
  stop 0.1 above the wedge plateaus. Lateral register: 4 tabs inside the wall
  inner faces at x ±40 (0.45 clearance, drop-in doctrine).
- **Hold-down (NO stock-shell mods)**: 4× **M3×12** horizontal through the
  shoulder flanges into heat-set pads in the riser end walls at (y ±40,
  z 67.4 — the end-wall pad band z 64.4..70.4 sits above the stack envelope
  and fuses into the deck; a z-65-centered pad protruded into the stack
  corners, gate catch). Inserts press from the pad's INNER face (from
  below, pre-mount) so screw tension seats them deeper — outer-face press
  was extraction-loaded (design-review fix).
  Fore-aft location = these screws (±0.15), leg-doctrine style. The riser is
  NEVER structural.
- **Deck top z 71.9** (= trunk top + 25, outline-locked) and FLAT: every
  fixture is an underslung boss → prints deck-face-down, zero supports.
- **Jetson Orin Nano devkit**: grid 96.5 × 75.4 at bores
  (−58.25/+38.25, −47.4/+28.0); carrier spans x −60..+40, y −49.4..+30,
  **ports face +y**, plugs drop through the deck slot (x −53..−44, y 26..46).
  Rear fin + mast stay clear of the plug row. Board plane z 78.2
  (6.3 spacers, **M3×14** — ×16 grazes the stack envelope, ×12 only bites
  3.2mm).
- **HEAD MOUNT — RE-ARCHITECTED 2026-07-07**: the head no longer bolts to the
  riser. It moved FORWARD onto the front-shoulder top (the "neck") via the
  separate `neck_bracket.scad`, so it projects ahead like a fox. The riser
  front head features below (deck L2-column base, front-wall camera register,
  USB grommet) are now **ORPHANED** — pending retire (a riser re-cut + re-gate).
  - **neck bracket → shoulder deck**: base plate on the deck top (z79.55), 4
    corner bolts drilled THROUGH the deck at first assembly (M3 + nyloc below).
    No shoulder-mesh change → shoulder stays gate-clean + print-2-identical.
  - **head → bracket**: a rear boss takes 4× M3 into the bracket's tall wall
    (rows z89/100) — a tall couple vs the forward-tipping moment. Cables drop
    the neck cable slot → deck window → shoulder C-box → trunk.

  Head removal = the 4 boss→bracket bolts → lifts off with the L2 + camera. The
  bracket stays bolted to the deck (drilled once), so the head is a modular
  removable unit for fennec-styling iteration.
- **SMA bulkheads**: REMOVED 2026-07-07 → the 2× WiFi MIMO antennas now live
  in the **head ears** (Ø6.5 SMA bores, higher + clear of the CF chassis). ⚠
  antennas are a PROVISION only — onboard Jetson WiFi works; test bench range
  first, then order (2× SMA bulkhead + 2× U.FL→SMA pigtail + 2× whip, ~$25) and
  verify the WiFi card exposes U.FL.
- ~~**Hood interface**: 4× M3 horizontal heat-sets in the side walls at
  (x −50/+35, z 67)~~ **GONE 2026-07-07** — the hood is retired and
  `riser_bay.scad:34` records these pads as removed. (The M3 heat-sets that
  DO survive at z 67.4 are the riser↔shoulder-flange pads at y ±40 — a
  different fixture; see `riser_bay.scad:70`.)
- **Vents**: 6× 3 mm slots per side, **TWO rows** — upper z 52..66 (logic
  level) and LOW z 33..45, added on thermal review because the under-board
  buck pocket (z 6..22) had zero airflow.

## Battery pocket (`battery_pocket.scad`, trunk-frame numbers)

- Open-top tray under the shell (shell floor caps it); rim at z −0.2, tray
  bottom −39.2; cavity 156.6 × 47.6 × 35.8 (pack + 0.8/side, **listing dims
  — caliper the real pack at first article**). Pack overhangs the trunk
  ~14.8/end, 0.25 under the shoulder flange bottoms.
- Rear-loading: pack slides in from −x; velcro strap wraps the pack's REAR
  CORNER (slots at x −77..−61 — direct tension against slide-out, not
  friction; design-review fix; shake-test at first article). Battery swap =
  strap only, 0 tools.
- Mount: 6× M3×12 from inside the trunk through the 3.9 floor into
  full-height boss columns at (x ±40/0, y ±26.5) with side-loaded **M3 nut
  traps** at z −8.2 (review fix: printable columns + a nut beats an insert
  at the pocket's highest-load joint). Floor gets a **modeled Ø3.4
  clearance hole** there (`trunk.scad`/`trunk_build.py`, 2026-07-10 —
  printed in, no drilling; the part-5 plate adopts the same pattern)
  (screw sandwich: plate + floor + tray).
- Leads: exit the pack rear face behind the trunk end, rise at x ~−70,
  enter through the **shoulder flange bottom notch** (y ±10 to z 12) to the
  MRBF-30 / 5191 block inside (block mount = part-5, ⚠ dims unmeasured).

## Head (`head.scad`) — supersedes the L2 mast + D456 periscope

> ⚠ **RE-ARCHITECTED 2026-07-07 — moved forward onto the front-shoulder neck.**
> The section below describes the head's INTERNAL sensor-mount scheme (crown
> plate + tilted face plate + bolt patterns), which is unchanged and still
> current. What changed: the head now bolts to `neck_bracket.scad` on the
> front-shoulder deck instead of the riser, and the whole thing shifted
> **DX+73 DZ+6** forward/up (L2 crown x126.5, D456 back-face (143,0,111.5)).
> See `forward_head_study.py` + the `neck_bracket.scad` table row above. The
> "REAR LOBE reuses the mast / riser" wording below is HISTORICAL — the mount
> is now the rear boss → bracket wall, but the crown/column geometry carried
> over. CoM moved **+6.5 mm forward** → ~54 mm rearward on the belly battery
> (510 g pack) nulls that delta. Absolute CoM ~+12 mm fwd — see the plan's
> battery note; defer the pack move to a full mass model + the balance-
> controller CoM target.
>
> **REAL D456 mesh (`d456_ref.stl`, from the RealSense SLDPRT, 2026-07-07):**
> confirms the OBB gate envelope is CONSERVATIVE (real = 124×29×26, slightly
> smaller than the 26×123.8×29 box — rounded corners/recessed lens → all head
> clearances hold with margin). Mount VALIDATED: the 2× M3 (±47.2) are on the
> REAR face (user-confirmed), so the rear-plate mount is correct, lens forward-
> down free. The real mesh is in `preview_assembly` (the "eyes"); check_fit
> keeps the OBB as the conservative envelope.
>
> **REAL Unitree L2 mesh (`l2_ref.stl`, from the STEP, 2026-07-07):** 74.9×75.0
> ×63.5, round Ø75 base. **Caught a mount error** — the real base pattern is
> **4 holes on a Ø51 BCD (R25.5), 90° apart** (M3), NOT the 22.5 mm square the
> mast/head had assumed. Crown re-cut to the real pattern (holes at CTR±18,±18
> = R25.5 at 45°; crown grown to x105..148, y±21). Optical center ~27 mm above
> the base (was 32.5 — minor). Real L2 in the preview (the "crown"); check_fit
> keeps the 75×75 box (conservative). ⚠ cable connector on one side (−X).

- **ONE part carries BOTH front sensors.** REAR LOBE = the L2 tower (reuses the
  mast: deck flange bolts (54/59.0, ±14) M3×10 from above; column x51.6..64
  y±9 rises to the crown; crown plate z118..122 carries the L2 on its 4× M3
  22.5 square, bolted from BELOW; cable bore 13×11 → deck drop (53.5,0)). FRONT
  LOBE = the D456 face (stem x63.45..70 through the flange notch to the wall
  row z67.4; a 27° down-tilted plate carries the camera's rear 2× M3 @94.4 +
  a ±3 z-slot; a face pillar backs the plate and ties the stem to the crown;
  right-angle USB-C exits a plate window → stem channel → the wall grommet).
  The two lobes fuse ABOVE the deck-ext fin (z>79.55).
- **Geometry (head_study.py, gate-verified)**: camera body x63.4..99.7,
  z80.8..118.4, y±61.9 — 0 front-leg-sweep hits at the −50 front hfe cap, lowest
  point +1.2 over the fin top 79.55, fwd corner +0.3 inside the x100 leg limit
  (that corner is at z107, far above any leg). L2 optical z~154, 360° ring clear
  (36 below the camera top). CoM fore-aft shift ≈ **0** (L2 kept at x53.5; the
  tilt actually pulls the D456 centroid ~1 mm rearward) — both masses rise ~4 mm
  in z. Retired-mast reference geometry follows.
- Flange (x 38..63.3, y ±20) on the deck, M3×16 into the riser's underslung
  inserts at (44/60, ±14), head wells through the flare. Shaft outer
  x 44..63.3 × y ±9 (Jetson edge gap 2.3; deck-extension fin gap 0.2), cable
  bore 13×9 — passes the RJ45 plug head. Plate 38×38, L2 seat z 114.4 →
  optical center ≈ trunk top + 100.
- **Assembly order (design-review fix — the reverse deadlocks)**: BARE
  mast bolts to the deck first (**M3×10** — longer punctures the stack
  envelope; Ø7 head wells open to the sky), THEN the L2 bolts on from
  BELOW the plate (M3×8 at (42.25/64.75, ±11.25), 38.5 mm of driver room).
  L2 service = those 4 plate screws; mast + Jetson untouched. Cable bore
  13×11 / deck slot 14×12 — must pass BOTH the RJ45 head and the ~Ø10 DC
  plug (⚠ caliper the real plugs).

## Findings the gate must keep honest

0a. **ROM caps re-verified with the ASSEMBLED state swept** (design review
   2026-07-06): the sweep cloud now carries the coax + tibia straps and
   cable-loop proxies (the leg_v6 "straps never sampled" lesson had
   repeated). Result: caps HOLD — hfe clean through +52, inboard haa clean
   through 15 with contact from ~18. No allowance change needed.
0b. **Inboard haa capped at +15° sw per leg (battery pocket)**: the pack
   hangs 39 below the shell; an inboard roll sweeps the folded leg under
   it — contact from ~18–20° at any hfe fold ≥ 15–30 (hfe ≤ 0 clean at
   full ±40). Outboard splay keeps the full 40 (verified clean — stand-up
   choreography unaffected; FR toe at haa −40 crosses the centerline, so
   >15 inboard had no use case anyway). Gate-derived, feeds URDF/firmware
   together with 0.
0c. **hfe FORWARD protraction capped at −50° sw for the FRONT legs only
   (head clearance, 2026-07-07)**: the integrated head (`head.scad`) occupies
   x70..100 z80..120 forward of the chassis; a front leg protracting to −86
   sweeps that volume and hits the D456 face / L2 crown. Capped FRONT hfe at
   −50 (still a strong stride — gait uses −30..−50, and the kfe-109 chord still
   reaches). REAR legs keep −86 (nothing forward of them). Wired: URDF
   `hfe_ext_front` (front) vs `hfe_ext` (rear) via `leg[0]=='F'` in leg.macro;
   `check_fit.py` HEAD case uses hfe_lo −50 front / −86 rear. Beyond-cap poses
   print as documented HITs. Fold (+50) unchanged for all four.
0. **hfe toward-trunk fold capped at +50° sw (chassis-safe ROM)**: with the
   tibia folded (kfe −109) and haa −40, the tibia/knee flank (tibia jogs
   30.5 back inboard) grazes the riser side skirt from hfe ≈ +55. Clean
   through +52 at every hip/haa/kfe combination; away-trunk −86 fully
   clean. Crouch itself needs only ~+40 (kfe-109 chord = 138). Feeds the
   URDF joint ranges + firmware clamps; the gate prints beyond-limit poses
   as documented HITs. It's an anti-gravity pose (knee lifted over the
   deck), not a collapse direction — software limit is the artifact fix.
1. **REAR stack corners vs trunk slabs (KNOWN, documented in the gate)**:
   with the stack at ctr x −4 (floor plate), only the two REAR corners
   intersect the leaning slabs → **hand-trim the two rear slab inner ends
   to x ≤ −60.5 when the boards arrive**; front slabs stay stock. Gate
   fails on any hit outside that zone (front hits included). The slabs
   only ever supported the stock covers.
2. **Mezzanine seat = the 2.0 floor plate, top z 5.9; stack top 64.0**
   (deck-boss bottoms 65.3 → 1.3 clear; deck underside 67.9 → 3.9).
3. Shoulder flanges rise to z 79.55 — 7.65 proud of the deck at both ends
   (they close the end gaps; Jetson x −60.. keeps 5.5 clear of the rear fin).
4. ~~Jetson heatsink height 21.5 is ⚠ REVIEW — caliper before designing the
   hood~~ **CLOSED 2026-07-07**: heatsink CALIPERED at 34.9, which is what
   killed the bespoke tray+hood and forced the official-case pivot (row 44).
   No hood to design.
5. Front cable lanes: D456 USB3 runs inside the riser ceiling gap
   (stack-top → deck-underside is 6.0 with max bosses) to the deck slot.
6. ~~**E-stop has no home yet (system gap)**~~ **CLOSED**: `control_pod.scad`
   exists, builds, and is in `build_all.sh` — a pod ABOVE the deck rear strip,
   which remains the only volume that fits a panel control (the stack owns
   every column at deck/wall level). The hood it was to be "designed with" was
   retired; the pod was built standalone instead. It now also takes SW1 and the
   voltmeter — see the panel-components table. ⚠ still caliper the real
   HB2-ES544 depth + cap Ø (#372).
7. **CoM sits ~+8 mm forward** of the hip-grid center (L2 + camera + mast
   forward moments vs the centered stack). Cheap trim: shift the mezzanine
   −8 fore-aft when placing the part-5 floor-plate bosses.
8. **Caliper list (one session, before the next prints)** — corrected
   2026-08-15, several entries were already done:
   ~~Jetson heatsink height~~ (done — 34.9) · ~~Blue Sea 5191 block~~ (**done
   2026-07-07** — body 61.6 × 20.0 × 46.5, M8 studs, base hole Ø11.1; the
   bracket in #369 is NOT blocked, only the installed lug-swing envelope with
   a 10 AWG ring fitted is unknown) · ~~Ethernet switch bare PCB~~ (moot — off
   the robot 2026-08-14) · D456 rear pattern + body · L2 pigtail RJ45/DC plug
   heads · pack true dims · stack true height incl. Teensy.
   **Still genuinely open, each with a consumer:**
   - **SW1 Contura below-panel body depth** + wing step positions (#368) —
     cutout is known (21.08 × 36.83) and panel range is known (0.81–6.35);
     DEPTH is the one number that decides which face on the robot can take it.
   - **Panel voltmeter — everything** (#370): bezel L×W, window L×W, screw
     pitch + thread, body depth. No row exists for this part at all.
   - **HB2-ES544 cap Ø** (#372) — ⚠ two files disagree: `dimensions.md:239`
     says "Ø40 assumed, CALIPER NEEDED", `control_pod.scad:24` says "VERIFIED
     specs 2026-07-08: Ø40 mushroom, 77 total length, panel max 6mm". The
     "verified" set is vendor-page-sourced, not calipered, and a vendor page
     already burned us once (SSD1331 outline, wrong by 4.9 × 5.1). 30 seconds
     with calipers turns a contradiction into a fact.
   - **Pololu buck true heights** (#366) — 13-15 is an estimate; it sets the
     under-board pocket and half of that argument.
   - SSD1331 pin-1 position + mating shell protrusion (⬜) — sets the
     `oled_tray` cable standoff, not the bracket.

## Thermal + motion review (2026-07-06)

9. **Bucks placement — REOPENED 2026-08-14 (#366), was "RESOLVED-ON-PAPER"**:
   the outline's "on the floor beside the stack" predates the plate — no
   floor space exists. Disposition was: bucks (13-15 tall ⚠ unmeasured)
   UNDERNEATH the power board on the plate, "off the pack shadow (y ±23)
   **where possible**". **That parenthetical was load-bearing and the
   geometry does not support it**: the outboard band is 48 − 23 = **25 mm**
   (17.5 against the battery *tray* at ±30.5), while a D42V110 is
   **31.8 × 43.2** — it does not clear the pack in EITHER orientation, and
   it's the leg+hip pair, i.e. the two hottest cards. Only the D24V22
   (17.8 sq) fits outboard. The band is further chopped by the mezzanine
   standoffs at x −40.5/33.5, y ±33.
   **Nothing ever caught this** because `power_board_model.py` models the
   cards at `BUCK_CARD_XY = (16.0, 20.0)` — a preview placeholder, 4.3× under
   real area, and its own comment says "not the real buck footprint". So
   `check_fit.py` case 11 has never tested real bucks. See #366 for options.
   Corrections to the rest of this note: standoffs are **20 mm**, not ~16
   (`floor_plate.scad`, 2026-07-09 — the Ø10×17 caps needed it), so the
   pocket is z 5.9→25.9 = **20 mm**; but C1-C5 bottom at z 8.9, leaving only
   3.0 mm under the five cap lands. v1 populates **four** cards, not five
   (D42V55F7 arm is DNP). The riser carries a LOW vent row (z 33..45)
   because the buck pocket (z 6..22, ~6-10 W) had zero airflow. The Ethernet
   switch was deleted from the robot 2026-08-14 (L2 plugs direct into Jetson
   eth0, switch is bench-only), freeing pocket volume it previously shared.
10. **L2 rear-down blindness (quantified, v1-accepted)**: the hood (~z 107)
   will block the rear sector below ~−19° elevation (cone edge −45°) →
   rear ground inside ~0.4 m is invisible to the L2 and NOTHING else looks
   rearward (D456 faces front). Affects reverse maneuvers.
11. **Build order (hard constraint)**: floor plate + battery tray bolt
   BEFORE the mezzanine — all six battery screws sit under the stack.
12. **Leg-vs-leg crossing is in-ROM** (front hfe +50 extended + rear −50
   extended overlap in the same y-plane, x ∓40). Not a chassis-parts
   issue; the URDF/sim lane must enable self-collision checking + the
   gait planner must respect it.
13. Sweep grid densified: kfe now {−109, −55, 0, 55, 109}; link flex
   (~1-2 mm at the foot) is well inside the 4-9 mm contact margins.

## Panel components + small actives (grounding audit 2026-07-06)

Homeless items found by cross-checking the memory docs — all ACTIVE in the
v1 BOM, none had a chassis home. **Rewritten 2026-08-14** (seating audit): the
three "hood" dispositions below were all written before the hood was retired
(row 44) and before the parts that replaced it existed.

| Item | Home | Status |
|---|---|---|
| E-stop (Ø22 × ~50 ⚠) | `control_pod.scad`, above the deck rear strip | **designed + built** (in `build_all.sh`). ⚠ caliper HB2-ES544 cap Ø + body depth (#372); #70 flags its 1.00 mm blind heat-set floor. Not printed |
| SW1 Contura rocker | **FRONT SHOULDER rear wall — APPROVED 2026-08-15** (#368) | Depth MEASURED **37 mm** (flange → terminals); wires solder direct at 90°, so 37 is the design depth and 41.6 mm is clear. All ten previously-proposed faces FAIL; this is the only drop-in on the robot, found independently on the bench and by `panel_probe.py`. **Rotated 90°, long axis VERTICAL.** Cutout centre **(x 108, y +1, z 43)**. Structural pass with ~1000× margin (0.12 MPa at a 3× landing vs 80-110 MPa PA6-CF; the centreline is the wall's quietest station and 18 mm of wall remains to the nearest wheel boss). ⚠ **HARD LIMIT: centre must stay at or below world z 49.6** — above that the cutout eats the wall/deck junction, and the probe cannot see that (it checks the wall exists, not that it can spare it) |
| Panel voltmeter | same — above the deck (#370) | panel-mount, horizontal window + 2 side screws. ⚠ **zero dimensions exist anywhere** — caliper bezel, window, screw pitch, body depth |
| SSD1331 OLED (31×28×11, remote on J10) | `oled_tray.scad`, flat on the rear shoulder deck | **designed + built** (in `build_all.sh`). Replaced the deleted `oled_mount` 2026-08-10 (it cantilevered off `control_pod`) |
| WS2812B strip (10 mm pitch) | riser skirt perimeter, adhesive; cable enters through a vent slot | assembly-time, no CAD |

**All three panel items need the same thing** — a printable panel face with
~30 mm of clear air behind it — and `panel_probe.py` says the chassis below
deck level has nowhere left that offers it. The free volume is ABOVE the deck
(12,745 of ~13,400 admissible placements sit at z > 96; the trunk flanks admit
11, none deeper than 12.5 mm). So this is a pod-design job, not a
find-a-wall-and-cut-it job. Do ONE pod rev that takes all three, after one
caliper session — not three revs.

```bash
# which faces can actually take a panel control, and how deep
../../../.venv/bin/python panel_probe.py --pitch 2.0
../../../.venv/bin/python panel_probe.py --self-check   # exercises the search
```

`panel_probe.py` is an ANALYSIS tool, deliberately not wired into
`build_all.sh` — it has no pass/fail verdict of its own, it answers "where does
this part fit". Re-run it after any chassis geometry change, and re-run it the
moment the Contura body depth is calipered: the depth is an input, and every
verdict above assumes only that the body needs more than 10 mm.

BOM additions flagged: right-angle USB-C cable (D456), velcro strap
(battery), TPU grommet insert for the deck slot (printed).

## Service

battery 0 screws · boards/Teensy/JP1 = **4 flange screws + 2 plugs at the
Jetson** — the riser lifts with the Jetson case + HEAD (L2 + D456) ALL
attached, robot standing · L2 = 4 crown screws under it · HEAD = 4 wall-row +
4 deck screws → lifts off with the L2; camera↔head is bench-only ·
legs/shoulders per leg_v6.

## Build + gate

```bash
./build_all.sh          # renders riser + spacer + shoulder rev, runs BOTH gates
```

`check_fit.py` cases: riser↔trunk mesh (seat bands excluded) · stack envelope
vs riser + trunk (known-zone logic) · shoulders both ends · **CROUCH leg
sweep** (haa ±40 × hfe FRONT −50 / REAR −86 .. +50 × kfe ±109 at all four
hips, mirror placements — envelope check) · **HEAD case** (D456 tilted-face OBB
+ L2 crown vs trunk/riser/case/shoulders/fins + the front-leg sweep, fused from
the old mast + periscope cases) · Jetson case + cradle · **DERIVED TRUNK hole
alignment** (case 13, 2026-07-10: samples every mating fastener's own bolt
axis against `trunk.stl` and asserts it's open, not solid) · static fixture
asserts.

> **Open assembly-time item (unrelated to the head)**: the MRBF-30 / Blue Sea
> 5191 fuse block still has no captive CAD home (61.6×20×46.5, no clean spot —
> see the floor_plate row). Bracket/zip-tie it to the rear-shoulder exterior or
> trunk rear at assembly, near the battery-lead entry.

## First-article checklist (before plate 4 batch)

1. Skirt seats flat on both wall tops, no rock; tabs drop in without force.
2. Riser↔flange screws: M3×10 reaches the inserts across the 0.15 gap; the
   riser doesn't shift fore-aft once torqued.
3. Heat-set purchase at Ø4.0 bores (deck bosses pressed from BELOW, wall
   bores from the outer faces).
4. Jetson on 6.3 spacers: port plugs clear the slot edges; SMA nut clearance.
5. Deck flatness under the mast base (L2 + mast lever arm) — if the deck
   oil-cans, add the two fore-aft ribs deferred from this rev.
6. Stock-shell slab trim done/not-needed per finding 1.
