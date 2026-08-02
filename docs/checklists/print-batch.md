# Print Batch Checklist (v6 full set)

From the 2026-07-06 batch-questions review. The caliper prereqs are now
CLEARED (Jetson heatsink 34.9, D456 rear pattern confirmed, pack 510 g, 5191
= external mount) — so floor_plate / battery_pocket no longer risk a re-print.

## ✅ RESOLVED 2026-07-13 — servo disc-interface dims verified (issue #85)

First-article caught one wrong ASSUMED servo dim: idler wheel center hub **Ø8.8**
(not Ø6) bottomed the Ø7 `WHEEL_CTR_D` relief → **fixed → Ø9.5 (#84)**. The rest
now CALIPERED off the real STS3215 and confirmed matching:
- `HORN_OD` 20.0 ✓ · `WHEEL_OD` 20.0 ✓ (both discs measured 20mm)
- `HORN_CTR_D` 6.5 relief ✓ — real retention-screw head **Ø5.1** (0.7mm/side clear)

**ALL leg parts now clear to print** — reprint `coax`/`coax_hfe_plate`/`femur`/
`knee_arm`/`shoulder`/`shoulder_plate` (+L) from the **#84 branch** (has the
wheel-hub fix). `tibia`/`strap`/`knee_bumper`/TPU/chassis were never affected.
(Density calibration + a full first-article grip check still owed per BOM/#5.)

## Δ since 2026-07-06 (head re-arch + fit/structure session, 2026-07-07)

**RETIRED — do NOT print:** `l2_mast`, `d456_head` (→ folded into `head`),
`hood` (→ official Jetson case), `tibia_pad` (misplaced → `knee_bumper`),
`spacer` (board in the case), `jetson_cowl` (→ right-angle plug adapters, #41
2026-07-10).

**NEW parts:** `head.scad` (fwd integrated head, PA6-CF), `neck_bracket.scad`
(front-shoulder-deck adapter, PA6-CF), `knee_bumper.scad` (TPU collapse guard),
`l2_adapter.scad` (L2 accessible-mount plate — the L2 bolts to it on the bench,
2 of the 4 L2 bolts are unreachable on the assembled head; access audit
2026-07-08), `head_ear.scad` ×2 (fennec ears / WiFi-antenna masts, bolt-on),
`control_pod.scad` (rear-top E-stop + OLED pod — re-homes them after the hood
was retired; bolts to the riser rear wall; 2026-07-08).

**CHANGED → re-print (old copies are stale):** all 6 legs (coax/femur/tibia
+ mirrors — new anti-rotation ribs in the servo pocket), `riser_bay` (head
interface removed 2026-07-07 + control-pod mount pad / grommet / guard exception
added 2026-07-08).

**⚠ NOT print-final:** `head` — functional + gate-clean, but the FENNEC styling
(STYLE=true ears) is a FIRST PASS (L2 skull shroud / eye accent / snout still
TODO) and its L2 (Ø51) + D456 mounts are gate-clean but BENCH-UNVERIFIED vs the
real parts. Print it in Wave 1 as a fit-check article, not the final head.

## Δ 2026-07-10 (AUD-12 / AUD-12b — head-boss void + battery-lead notch)

**⚠ RE-PRINT if you already have an article:** `head.scad` — the USB-C column
channel used to run straight through the rear boss, voiding the +y pair of
the 4 breakaway heat-set inserts (0.0mm floor/wall, measured) — an ALREADY
PRINTED head from before this fix has 2 of 4 head→neck_bracket bolts with no
real insert backing. Channel rerouted (shares the L2 cable bore below the
boss top instead); mouth of the L2/D456 cable bore also gained a 0.75mm
chamfer at the x121 breakaway plane. `leg_v6/shoulder.scad` — the
battery-lead notch (flange bottom, x±10) is now chamfered on all 4 nominal
edges at both mouths (was a raw 90° PA6-CF corner); an already-printed
shoulder has the sharp version. Both re-render clean via `build_all.sh`.

**NEW part:** `chassis/lead_notch_grommet.scad` (TPU 95A) — edge liner for
the (now-chamfered) battery-lead notch, same family as `case_slot_grommet`.
~0.2 g (small — check the slicer doesn't drop stray islands at that size).

## 0. Open before starting (user)

- [ ] PETG-CF spool on hand? (buy if not — or all-PA6 and accept warp
      risk on the 127 mm riser lid)
- [x] **TPU 95A on hand — SETTLED 2026-07-31 by having printed with it.** (~100 g
      budgeted, external spool — AMS won't feed.) This had been contradicted across
      three docs: `work-schedule.md` said ✅ on hand, this line said unknown, and
      `master-bom.md` listed only PA6-CF. Resolved in favour of ✅ — see §1b.
- [ ] ~1.5 kg PA6-CF + ~0.6 kg PETG-CF total — enough stock?
- [ ] Shoulder lightening windows (backlog #27): rec DEFER one rev —
      shoulder just took feet + bosses + gussets, prove it first
- [ ] Servo SKU audit (#23) done? (independent of printing but same bench
      session — label hip vs leg units)

## 1. Material allocation (backlog #24)

| Material | Parts |
|---|---|
| PA6-CF (DRY 80 °C/10 h; no anneal — §3) | coax, femur, tibia, knee_arm, shoulder, shoulder_plate (+L variants), strap ×4, **`head`**, **`neck_bracket`**, **`battery_pocket`** (#24 2026-07-10: stays PA6-CF — belly crush guard over the LiPo, puncture=fire #15; impact toughness > flatness) — 4 walls / 40 % / gyroid (**AUDITED** `neck_bracket_analysis.py`: faceplant SF ~12; ⚠ the L2-scan **vibration/resonance** is a stiffness concern, unverified — modal check on the first print) |
| PETG-CF | riser_bay, floor_plate, **`head_ear` ×2** (split off the head 2026-07-07 — prints FLAT, low-warp. Bolts to the head ear-pad; OPTIONAL per the WiFi-antenna decision #32. **MATERIAL 2026-07-13: plain PETG or ASA — NOT a CF filament.** The ear is an antenna mast; carbon fiber is conductive at 2.4/5 GHz and detunes/absorbs the whip (several dB). Rigid low-loss dielectric holds the mast stiff with no RF penalty. If the ears end up pure styling, any filament is fine. **YAWED +45° edge-on to the L2** (`head_ear.scad EAR_YAW`, occlusion_ear.py): blocked LiDAR arc 28.5°→13.8°/ear, ~29° total FoV recovered; ears lean back. First-article: check base stiffness on the longer cantilever), **`l2_adapter`** (FLAT bottom-down, ~6 g; PA6-CF also fine — it carries the L2 mass so PA6-CF preferred if in stock), **`control_pod`** (COLUMN-FACE-DOWN, ~24 g; rear-top E-stop + OLED mount) |
| TPU 95A | ✅ **SM3_Foot shoe ×4+1 PRINTED** (STOCK geometry — crush-zone v2 still waits for first-article fit, #20) · ✅ **skid_rail ×2 PRINTED** · ✅ **knee_bumper ×4+1 PRINTED** (backlog #15 B, replaced the retired ~~tibia_pad~~ — wraps the tibia knee-block, U opening up) · ✅ **cable_clip ×27 PRINTED 2026-08-01** (20 install + 7 spares; batch printed ahead of the §4 first-article step — see the anchor-topology note in §1b) · ⬜ **grommet_insert ×6** · ⬜ **case_slot_grommet** (#41 follow-up, -Y CASE_SLOT edge liner) · ⬜ **lead_notch_grommet ×2** (AUD-12b, 2026-07-10 — battery-lead notch edge liner, one per shoulder/trunk end) |

### 1b. TPU print status — measured, 2026-07-31

Volumes measured from the STLs (trimesh), mass at TPU 95A ρ ≈ 1.21 g/cm³, solid.
The `~100 g` budget in §0 checks out: the full set is **~102 g**.

| part | qty | ea cm³ | set g | status |
|---|---|---|---|---|
| SM3_Foot shoe (`original_body_files/SM3_Foot.stl`) | 5 | 3.6 | ~22 | ✅ printed |
| knee_bumper | 5 | 6.5 | ~40 | ✅ printed |
| skid_rail | 2 | 4.7 | ~11 | ✅ printed |
| cable_clip | 27 | 0.85 | ~28 | ✅ printed 2026-08-01 — 20 install (5/leg) + 7 spares |
| grommet_insert | 6 | 0.40 | ~3 | ⬜ hold for LA-25 press test |
| case_slot_grommet | 1 | 0.55 | ~1 | ⬜ |
| lead_notch_grommet | 2 | 0.24 | ~1 | ⬜ |

**~101 g printed, ~5 g remaining** (updated 2026-08-01). There is no large TPU job
left on this project — the biggest single TPU part is a 6.5 cm³ knee_bumper, and
every one of those is printed. Remaining: **1× `case_slot_grommet`, 2×
`lead_notch_grommet`, 6× `grommet_insert`** ≈ 5 g total.

Still hold the 6 `grommet_insert` until **one** has passed the §5 LA-25 press test
(BARREL_OD 12.2 into a nominal Ø12 hole = 0.2 mm diametral interference, likely
inside FDM/TPU noise, and the axial slit makes it a split ring so retention is
spring-back rather than interference). Print **one**, press it into the printed
shoulder's Ø12 flange hole, tug it; grow `BARREL_OD` in the `.scad` if it spins
free — never re-drill the flange. ⚠️ `lead_notch_grommet` is 0.24 g; preview the
plate before sending, because slicers drop islands that small.

#### ⚠️ Anchor-topology check the clip batch skipped

The 27 clips were printed ahead of §4's 2-off first article, so this is now a
**fit check on parts in hand** rather than a print decision. It is worth doing
before the harness goes on, because it changes install, not the print.

The clip's own zip holes are **Ø3.4 on a Z axis at y = ±5** (`cable_clip.scad:91`),
i.e. straight down through the flat base at **10 mm spacing** — which is exactly
`zip_pair_neg`'s default (`leg_v6_common.scad:343`, `spacing = 10`, axis Z). Three
of the five per-leg stations are that: **femur x44, femur x84, tibia x58.** Those
match by construction.

The other two stations are **not the same kind of anchor**:

| station | source | geometry |
|---|---|---|
| coax tunnel-exit | `coax.scad:600` | `translate([sx*7, 17, -36]) rotate([0, sx*90, 0])` — **axis X**, one hole per ∓X side wall, **14 mm apart** |
| coax HAA connector-bay | `coax.scad:636` | `translate([sx*7, 19, -27]) rotate([0, sx*90, 0])` — same pattern at a different (y,z) |

Both punch **sideways through opposite walls** starting inside an already-open
void — deliberately, so a tie can be looped (a blind pocket cannot). But a tie
threaded through those cannot also thread the clip's vertical base holes: the axes
are perpendicular and the spacings differ (14 vs 10). **That is 2 of 5 stations per
leg = 8 of the 20 installed clips.**

What is *not* established: whether the clip still works there as a tie-clamped
saddle (a tie crossing the void could press bundle-into-clip without threading the
clip at all), and whether an 18 × 16 mm clip physically fits the tunnel void
(grid-probed clean gap at that z-band is x[−9, 9] = 18 mm wide). Both are bench
questions against a printed coax — and the coax was redesigned since
(#234/#235/#240), so they belong to the **#226 first article**, not to a re-print.
Fallback if it does not fit: those two stations revert to what they were designed
as before the clip existed — a plain tie wrapping the bundle against the wall pair,
losing the bell-mouth bend control at the hip crossing only.

The `SM3_Foot` shoe is **not modelled in this repo** — it is stock upstream geometry
at `original_body_files/SM3_Foot.stl`. `leg_v6/check_shoe.py` gates its fit against
the tibia toe; last run 2026-07-31 clean on both sides (0/21000 interference points,
inner-face gap median 0.277 / p90 0.505 against the 0.4 median limit).

## 2. Slicer spec

| Class | Walls | Layer | Infill | Notes |
|---|---|---|---|---|
| legs PA6-CF | 4 | 0.2 | 40% (**tibia 25%** — stress audit SF 35) | orientations per part headers: femur/tibia flat −Z, coax rear-face-down + supports under the yoke bridge, shoulder rear-face-down + tree supports, tibia tab-down + pillars, shoulder_plate horn-seat-down, knee_arm underside-down, strap flat. **⚠ LA-3 (2026-07-11): femur_L / tibia_L do NOT share the R orientation** — the Z-mirror flips which face is flat, so "flat/tab face −Z down" applied to an L part prints it upside-down (tibia_L lands on two ~25.4mm² islands = tip-over risk). Rotate femur_L/tibia_L **180° about X from the R orientation** so they rest on the same flat face R does. |
| head/bracket PA6-CF | 4–5 | 0.2 | 40–60% | `head` CROWN/PAD-DOWN (the flat crown top on the bed = best L2-seat + ear-pad surface; the boss + tilted face + cheeks rise → tree supports under the tilted-face + cheek overhangs); `neck_bracket` BASE-DOWN (deck face on the bed, wall+gussets rise); `l2_adapter` FLAT bottom-down (zero supports) |
| chassis PETG-CF | 3 | 0.25 | 20% | riser DECK-FACE-DOWN (zero supports); floor_plate flat (zero supports); jetson_case_mount base-down (uprights rise, no overhangs after the #34 rework); `jetson_clamp_bar` ×2 flat (PA6-CF; #44 — removable case hold-downs, replaced the 4 clamps); `control_pod` COLUMN-FACE-DOWN (riser-facing face on the bed; light supports under the deck + OLED-panel overhangs). **`battery_pocket` prints PA6-CF settings** (§1 row / #24, not PETG), FLOOR-DOWN opening-up, zero supports. (`jetson_cowl` RETIRED #41 — do NOT print) |
| TPU | 2 | 0.2 | 100% | clips/rails/grommet flat; **knee_bumper U-opening-UP**; shoe per stock orientation |

### 2b. `hardware/cad/slice_plate.py` — slice from the CLI, and prove the settings landed

The table above is prose. `slice_plate.py` is the same table as a registry the
machine can act on, plus three gates the GUI has no way to run:

```
proj/.venv/bin/python hardware/cad/slice_plate.py --list                 # registry + coverage
proj/.venv/bin/python hardware/cad/slice_plate.py grommet_insert case_slot_grommet lead_notch_grommet:2
proj/.venv/bin/python hardware/cad/slice_plate.py --self-test            # prove the verify step fires
```

It slices with OrcaSlicer's CLI, writes G-code to `hardware/cad/slices/`
(gitignored) and a provenance record to `docs/print-records/` — STL + .scad
sha256, git HEAD, every applied setting. That record is the answer to "which
revision is this printed part?", which until now was memory.

**Gates, in order.** Any one of them refuses the plate:

1. **STL freshness** (`check_stl_fresh.py`, #176) — you cannot slice geometry
   that no longer matches its `.scad`.
2. **Material agreement** — the `.scad` `Print:` header and the registry must
   name the same material. This caught `battery_pocket`: the header said
   PETG-CF while §1/#24 had moved it to PA6-CF in 2026-07-10 (belly crush guard
   over the LiPo). Header corrected 2026-08-01. The gate also **reports what it
   could not check**: 5 of 28 parts (`floor_plate`, `head`, `jetson_case_mount`,
   `knee_bumper`, `lead_notch_grommet`) have headers that name no material at
   all — a real doc gap, now visible instead of passing silently.
3. **Orientation, measured not trusted** — after the documented face is rotated
   down, the tool measures how much flat area actually lands on the bed, and
   how slender the result is (height / √contact). Under 5 mm² means the part is
   standing on an edge; over slenderness 1.5 it must declare a brim.
4. **Everything asked for is on ONE plate** — object count matches the request,
   and the slicer did not split the job. `battery_pocket:9` really does become
   three plates (4 + 4 + 1); before this gate the tool read plate 1 and
   reported its 269 g as the total for all nine.
5. **Settings verification** — the emitted G-code matches the flattened
   presets, key by key.

**Two real defects it found on its first run**, both invisible in a GUI:

- **`case_slot_grommet` was being printed on its edge.** The `.scad` says
  "either flat face down" and the mesh's own pose stands it on the 54 × 3.8 mm
  edge — 11.1 mm tall, **19.2 mm²** of contact. Laying it on **+Y** gives
  **156.6 mm²** and 3.8 mm of height. All six faces are measured in the file.
- **`coax_hfe_block_L` had the R part's orientation.** The `_L` is
  `mirror([1,0,0])`, so its mating face is **−X**, not +X: 54.4 mm² against
  366.4. Same trap LA-3 records for `femur_L`/`tibia_L` — and the registry
  reproduced it, then the measurement caught it.

**One divergence it now enforces:** tibia prints at **25 %** (stress audit
SF 35), not the PA6-CF default 40 %. Measured on `tibia_R`: 66.43 g / 3 h 02 m
against 73.52 g / 3 h 23 m. Parts wanting different infills cannot share a
plate, and the tool says so rather than picking one.

**Parts still marked MANUAL** — `shoulder`, `shoulder_plate(_L)`, `head`,
`control_pod`, `knee_bumper` — have orientations documented as a *feature*
("rear face down", "crown/pad-down") rather than an axis. The tool refuses them
and prints every face's measurements so the choice takes a minute. Resolve one
by adding the axis here **and** to the `.scad` header.

**Parts marked UNRESOLVED** — `oled_mount`, `spacer`, `trunk`, `head_ear(_L)` —
are printable but cannot be sliced yet, each for a recorded reason: `oled_mount`
says "PETG/PA6-CF" (two materials); `spacer` names no material anywhere though 8
are needed; `trunk` is built by `trunk_build.py` so the freshness gate skips it;
the ears are deliberately non-CF (#32 — the CF detunes the antenna) and no
non-CF material is modelled yet. `--list` prints this set as a to-do.

⚠️ **These five were in the tool's "not printable" exclusion list on the first
pass**, which made its coverage line read "covers every STL". That is this
project's own *green-but-uncovered* pattern, committed by the tool written to
catch it — worth knowing when reading any coverage claim, including this one.
Coverage is now stated as numbers: 28 registered (6 refused for prose
orientation), 5 unresolved, 4 reference-only, 0 unaccounted.

## 3. DRY yes, ANNEAL no (corrected 2026-07-06 — user catch)

Bambu PA6-CF: annealing is **OPTIONAL** (Bambu guidance) — but the TDS
151 MPa flexural was measured on specimens annealed+dried 80 °C/12 h,
so unannealed parts run ~15–25% below published. Margins re-checked
unannealed: tightest = femur slab SF ~3.4, yoke root SF ~5.5, all else
≥ 12 → **SKIP annealing for this batch** (also removes the 0.5–1%
dimensional-shift + warp risk entirely). **DRYING is non-negotiable**:
80 °C 10 h+ before printing, drybox during. If annealing is ever added
later (hip-thermal #17 or a break), then: anneal FIRST, fit-check
SECOND — anneal moves dims and every fit gate assumed as-modeled.

## 3b. Heat-set insert notes (audit 2026-07-06)

Every insert site depth-probed in the built STLs:
- shoulder deck plate bores: now Ø3 VENTED through (0.25 floor was
  melt-through) — set with a backing finger below, melt exits the vent
- shoulder neck_bracket bolt pilots (NO-DRILL fix 2026-07-10, 4x M3x3.8,
  `neck_heatset` in `shoulder.scad`): 2.3mm floor (probe-verified all 4) —
  BLIND, no vent needed at this depth, press straight down from the deck top
- shoulder D456 pads + lower flange bosses: 0.75 floor — press to flush,
  STOP (slight bulge on the inner face is cosmetic-only if you push)
- femur shelf / flange uppers: 13+ deep, no care needed
- riser: all sites through-vented by design
- **battery_pocket mount pads (AUD-11 fix, 2026-07-10, was a side-loaded nut
  trap — REMOVED, see improvement-backlog.md): +6× M3×3.8 heat-sets**, one
  per pad at (x −40/0/+40, y ±27.5), Ø4.0×4.2mm BLIND, mouth-up — press
  straight down from the pad TOP face (RIM_Z). 1.8mm floor to PAD_Z0
  (probe-verified all 6, ring test) — BLIND, no vent, press to flush and
  STOP (do not force past the mouth chamfer). Press during BATTERY
  SUB-ASSEMBLY, before the pack + trunk mate (the pad top is only
  accessible from outside the tray before it's under the shell).
- iron + M3 tip, inserts from the DOCUMENTED face (several press from
  inner faces — a bench press can't reach; see part headers)

## 4. Wave 1 — first article (~450 g, doctrine: before batching)

- [ ] 1× RIGHT leg set (coax_R, femur_R, tibia_R, knee_arm), 1× shoulder,
      1× shoulder_plate pair, 1× shoe, 1× skid_rail, ~~2× cable_clip~~,
      1× knee_bumper, 1× strap
      — ⚠️ the TPU items here are **already printed in batch** (shoe ×5,
      skid_rail ×2, knee_bumper ×5, **cable_clip ×27**), so for those the
      first-article step is spent. What it would have caught is now a fit check
      against the printed rigid parts instead — see the anchor-topology note in
      §1b for the one that matters (2 of 5 clip stations per leg use a
      perpendicular anchor).
- [ ] 1× head + 1× neck_bracket + 1× l2_adapter + 2× head_ear (FIT-CHECK — prove
      the L2 Ø51 + D456 ±47.5 patterns vs the real parts; the ear feet bolt to
      the pad; the L2 adapter tongue slides under the crown lip)
- [ ] **ASSEMBLY ORDER (head)** — every fastener driver-access audited 2026-07-08:
      - BENCH-a: **L2 → l2_adapter** — 4× M3 up from the adapter BOTTOM (heads
        countersunk flush) into the L2 base. All 4 reachable on the bare plate.
      - BENCH-b: **D456 → head face plate** — 2× M3 from behind the tilted plate
        (the cheeks are pocketed at ±47.2 for driver room). Rear screws are
        unreachable once the head is on the robot — do this on the bench.
      - (1) **neck_bracket → deck** — **NO-DRILL fix 2026-07-10**: 4× M3×8
        SHCS driven straight down from the bracket top through the base
        clearance holes into M3×3.8 heat-sets PRESSED into the shoulder deck
        (`leg_v6/shoulder.scad` `neck_heatset` pockets) — no drilling, no
        nyloc, no under-deck access needed. Front pair now at (117,±20)
        (moved off the shoulder's rear-wall rib onto the flat deck); rear
        pair unchanged at (146,±19.5).
      - (2) **head → bracket** — 4× M3 driven from the REAR (behind the bracket
        wall, x<113, open above the deck) into the boss heat-sets. The aft-gusset
        driver notches clear the ball-key. (Old front-drive was blocked by the
        pillar — access audit.) Head lifts on with the D456 already attached.
      - (3) **l2_adapter (+L2) → crown** — slide the front tongue under the crown
        front lip, then 2× M3 UP from below the crown rear lip into the adapter
        heat-sets (110,±14). No front bolt (front was unreachable).
      - (4) **ears → pad** — 2× M3 each straight down into the pad heat-sets
        (77/83,±10); bolts sit inboard of the ear panel so the driver clears.
- [ ] Fit checks (leg_v6 README "Verify"): **servo drop-in — the pocket is
      0.45 slip + NEW 0.1 anti-rotation ribs (±Y case flats): the servo should
      drop FREE, then not rotate; if a tight print binds, file the rib tips (a
      few seconds) — they're crush ribs**; M3 through the Ø3.1 dowel pair, M2
      through columns, insert purchase at Ø4.0, countersink flush, fork-arm
      seat flatness
- [ ] **#54 assembly ORDER (hard rule): drive each servo's 4 case screws
      BEFORE the parent joint's Ø19 boss fills the same floor window.** Servos
      install first (femur/tibia/coax pockets), joints bolt after — the near
      case-column pair sits r13.15 from the joint axis, only ~2.4–3.65mm to the
      boss edge, so a screwdriver body swinging next to the seated 19mm boss is
      tight. First-article: confirm the driver actually reaches the near case
      screws with the parent boss in place (else strictly follow servos-first).
- [ ] **LA-25 first-article: grommet_insert press-test.** BARREL_OD 12.2 into
      the nominal Ø12 flange hole is only 0.2mm interference (likely inside
      FDM/TPU noise) and the axial slit makes it a split ring — press one
      in, tug-test retention; grow `BARREL_OD` in `grommet_insert.scad` if
      loose.
- [ ] **LA-26 first-article: shoulder_plate 3.1mm dowel holes.** Test-fit an
      M3 in the 2 diagonal "dowel" flange holes before committing — FDM
      often prints small holes 0.1–0.3mm undersize; bump to 3.2–3.3 in
      `shoulder_plate.scad` (`PLATE_BX`/`PLATE_BY` dowel cut) if tight.
- [ ] **LA-23 first-article: horn counterbore floor.** `knee_arm` +
      `shoulder_plate` horn-coupling floors are EXACTLY 1.5mm (`ARM_THK` 4.0 −
      `HORN_CTR_DEEP` 2.5) — the gate minimum, zero slack. Non-load-bearing
      clearance pocket (clears the horn's proud retention screw), but after
      printing probe the floor (~1.5mm, no witness/pinhole from a thin Z-print).
      `ARM_THK` is shared, so it can't be locally deepened without a wider change.
- [ ] knee_bumper: clips over the tibia knee-block, wraps the bottom, stays put
- [ ] head→bracket: 4× M3 boss bolts land; bracket base bolts drill the deck
- [ ] Shoe: snap onto the toe_v2 seat (tabs into pockets, lips over the
      disc), pin θ if slop, photo for dimensions.md
- [ ] **Static test A — tibia**: scrap block clamped in the KFE pocket,
      vise; hang **12 kg (3× robot) from the toe via the shoe**, 60 s;
      inspect web/blade/seat, listen for cracking
- [ ] **Static test B — shoulder**: bolt the flange to the stock trunk
      (4× M3 only, NO feet — worst config); **7 kg sandbag on the deck**
      (≈1.15× worst landing); inspect flange/webs/insert bosses
- [ ] **Static test C — mezzanine standoff self-tap pull test** (CR-8 #4):
      the 4× Ø2.5 pilots in `floor_plate.scad` (mezzanine seat, self-tap M3
      into PA6/PETG) are unbenchmarked. On the first-article floor_plate,
      drive an M3 standoff into one pilot and pull-test to failure (or to
      the stack's static load, whichever is defined first); inspect for
      stripped threads / cracked pilot wall before trusting the pattern
      across the full mezzanine
- [ ] **Mezzanine assembly (AUD-4): clock the M3×20 standoff at (−40.5,−33)
      hex-FLAT toward Q1 (the TO-220).** Across-flats = +0.15mm clearance to
      Q1; across-corners = −0.27mm overlap. Free win at assembly, but the
      gate doesn't model the standoff hardware — do it by hand.
- [ ] Weigh every part → nova.urdf.xacro masses (backlog #5/#13)

## 5. Wave 2 — batch (after wave 1 passes)

- [ ] Left mirrors + 3 more leg sets + 2nd shoulder + plates + 3 more straps
- [ ] Chassis set: **`trunk` (DERIVED, 2026-07-10 — replaces the stock shell;
      see `trunk_build.py`)**, riser_bay, floor_plate, battery_pocket, jetson_case_mount
      + `jetson_clamp` ×4 (removable case hold-downs), neck_bracket (final),
      head (final — AFTER the fennec styling pass + bench-verified mounts, else
      it re-prints), control_pod (rear-top E-stop + OLED) + its 4 riser heat-sets
      (pressed from the pad pocket face)
- [ ] **Jetson case → cradle assembly** (reworked #33/#34/#38): press the 4 upright
      TOP heat-sets (from above) + BASE heat-sets (from below) → bolt the cradle
      to the deck → assemble the case fully (bezel on the +y face) OFF-robot →
      DROP it in (ports face −y/right) → **plug the −y STRAIGHT cables now (full
      access)** → **bolt on `jetson_cowl` ×1** (2× M3 from the −y side into the
      −y upright heat-sets — shields the plugs from a right-side-fall crush; route
      cables down the cowl floor → riser −Y `CASE_SLOT` x−30..30/y−51.5..−47 → bay)
      → set the 4 `jetson_clamp`s on the upright tops, M3×8 down, capping the case
      corner columns (TPU/EVA shim each for preload).
- [ ] TPU: remaining 3+1 shoes, 2nd rail, 18 clips, 3+1 knee_bumper
- [ ] Spares: **2–3 horn discs**, 1 shoe, 4 clips
- [ ] Weigh the full set → final URDF masses; update
      `docs/improvement-backlog.md` #5

## 6. Assembly-adjacent (same bench era)

- [x] ~~Drill floor: battery 6-hole pattern + shoulder-feet 4 holes~~ —
      **ELIMINATED 2026-07-10**: both patterns are now MODELED clearance
      bores in the printed `trunk` part (`trunk.scad`/`trunk_build.py`,
      `check_fit.py` case 13 gates hole↔bolt-axis alignment). Print the
      DERIVED trunk, not the stock STL, and there is nothing left to drill
      here — floor_plate's own csk pattern for the feet bolts is unchanged
      (that's a hole in floor_plate itself, not the trunk).
- [ ] Cable dressing per leg_v6 README (clips at both loop ends, ≥40 mm
      loops, spiral wrap, tug-test all anchors + 24 connector ends)
- [ ] **Free-loop length (backlog #18 / LA-14, `--cable` WARN gate):** per
      leg, fold kfe + hfe to their MECHANICAL LIMITS *before* zip-tying the
      KNEE and HIP loops — dress slack to the worst-case fold, not neutral
      pose. Guidance: KNEE loop (femur-x84↔tibia-x44) needs enough free
      length to stay slack at ~39mm anchor separation (full kfe fold); HIP
      loop (coax-exit↔femur-x44) needs slack down to ~60-79mm across hfe.
      Zip only after confirming slack at the fold limit, not before.
- [ ] **HAA loop too** — the `--cable` sweep covers all three loops, and the
      HAA loop is also under the ≥80 mm spec everywhere: 56.7–62.0 mm across
      the asymmetric envelope (15° inboard … 40° outboard). Two things make
      it the easy one: excursion is only **5.26 mm** end to end, so slack
      sized once is right everywhere; and its worst case (56.7 mm) is at
      **+15° inboard**, which is exactly where runtime is clamped until the
      haa sign is confirmed at homing. Dress it at full inboard.
      Measured 2026-07-29; worst spans that run: KNEE 51.6, HIP 59.9,
      HAA 56.7 mm. Only one sampled pose in the whole sweep meets spec
      (HIP at hfe −93°, 80.7 mm) — treat ≥80 mm as aspirational, not a
      thing you will hit.
- [ ] Body-side dressing: the neck-bracket cable slot ↔ shoulder deck window
      overlap is **+0.80 mm at worst** (chassis `check_fit` case 16, flagged
      KNOWN TIGHT BOUNDARY 2026-07-16). Feed the head bundle through before
      the neck bracket is finally bolted — it is not a slot you want to
      thread a dressed bundle into afterwards.
- [ ] Skid rails: key + CA/VHB under the tray
- [ ] Breakaway fuses (#2): the masts are RETIRED → re-map the nylon-M3
      breakaway concept to the HEAD mount (4× M3 boss→bracket) so the head
      pops off in a fall instead of snapping the neck. ⚠ DECISION open —
      the bracket→deck bolts should stay metal (structural); only the
      head→bracket joint is the breakaway candidate
- [ ] Washers under every stock-shell-side head (#3)
- [ ] EVA foam pad on the battery tray floor + felt/kapton on the
      shoulder-flange bottom edges over the pack (#29)
- [ ] **Battery pocket → floor: 6× M3×10 CSK** driven from ABOVE, through
      `floor_plate`'s csk + the printed-in trunk floor bore, into the pad's
      M3×3.8 heat-set (AUD-11 fix, 2026-07-10 — the nut-trap step from the
      AUD-1 mount is GONE: no nut to feed in from the pad's outboard face,
      no side access needed). First-article: pull-test one mount before
      trusting the pattern (matches Static test C's self-tap discipline).
- [ ] TPU grommet inserts into the 4 flange grommets before cable pull (#30)
- [ ] Riser shake test (0.45 lateral tab slack) after hold-down screws
- [ ] **E-stop pod mounted + wired BEFORE first bus power** — ✅ HOME RESOLVED
      2026-07-08: `control_pod.scad` (rear-top, bolts to the riser rear wall's
      new pod-mount pad, 4× M3). E-stop mushroom UP (slap-down) on the deck; the
      Ø32 block hangs in the rear pocket (verified clear); SSD1331 OLED on the
      tilted rear panel. Cables drop the Ø10 grommet → riser bay → power-board NC
      lines (leg+hip+L2 EN) + Arduino Nano SPI. **Riser RE-PRINTS** (added the
      pod pad + grommet + guard exception). Mount is a light central 4× M3 — E-stop
      is a palm slap, not a hammer
