# Print Batch Checklist (v6 full set)

From the 2026-07-06 batch-questions review. The caliper prereqs are now
CLEARED (Jetson heatsink 34.9, D456 rear pattern confirmed, pack 510 g, 5191
= external mount) — so floor_plate / battery_pocket no longer risk a re-print.

## Δ since 2026-07-06 (head re-arch + fit/structure session, 2026-07-07)

**RETIRED — do NOT print:** `l2_mast`, `d456_head` (→ folded into `head`),
`hood` (→ official Jetson case), `tibia_pad` (misplaced → `knee_bumper`),
`spacer` (board in the case).

**NEW parts:** `head.scad` (fwd integrated head, PA6-CF), `neck_bracket.scad`
(front-shoulder-deck adapter, PA6-CF), `knee_bumper.scad` (TPU collapse guard),
`l2_adapter.scad` (L2 accessible-mount plate — the L2 bolts to it on the bench,
2 of the 4 L2 bolts are unreachable on the assembled head; access audit
2026-07-08), `head_ear.scad` ×2 (fennec ears / WiFi-antenna masts, bolt-on).

**CHANGED → re-print (old copies are stale):** all 6 legs (coax/femur/tibia
+ mirrors — new anti-rotation ribs in the servo pocket), `riser_bay` (head
interface removed).

**⚠ NOT print-final:** `head` — functional + gate-clean, but the FENNEC styling
(STYLE=true ears) is a FIRST PASS (L2 skull shroud / eye accent / snout still
TODO) and its L2 (Ø51) + D456 mounts are gate-clean but BENCH-UNVERIFIED vs the
real parts. Print it in Wave 1 as a fit-check article, not the final head.

## 0. Open before starting (user)

- [ ] PETG-CF spool on hand? (buy if not — or all-PA6 and accept warp
      risk on the 127 mm riser lid)
- [ ] TPU 95A on hand? (~100 g needed, external spool — AMS won't feed)
- [ ] ~1.5 kg PA6-CF + ~0.6 kg PETG-CF total — enough stock?
- [ ] Shoulder lightening windows (backlog #27): rec DEFER one rev —
      shoulder just took feet + bosses + gussets, prove it first
- [ ] Servo SKU audit (#23) done? (independent of printing but same bench
      session — label hip vs leg units)

## 1. Material allocation (backlog #24)

| Material | Parts |
|---|---|
| PA6-CF (DRY 80 °C/10 h; no anneal — §3) | coax, femur, tibia, knee_arm, shoulder, shoulder_plate (+L variants), strap ×4, **`head`**, **`neck_bracket`** — 4 walls / 40 % / gyroid (**AUDITED** `neck_bracket_analysis.py`: faceplant SF ~12; ⚠ the L2-scan **vibration/resonance** is a stiffness concern, unverified — modal check on the first print) |
| PETG-CF | riser_bay, floor_plate, battery_pocket, **`head_ear` ×2** (split off the head 2026-07-07 — prints FLAT, low-warp; PA6-CF also fine. Bolts to the head ear-pad; OPTIONAL per the WiFi-antenna decision #32), **`l2_adapter`** (FLAT bottom-down, ~6 g; PA6-CF also fine — it carries the L2 mass so PA6-CF preferred if in stock) |
| TPU 95A | SM3_Foot shoe ×4+1 (STOCK geometry — crush-zone v2 waits for first-article, #20), skid_rail ×2, cable_clip ×20, ~~tibia_pad~~ → **knee_bumper ×4+1** (backlog #15 B, replaces the retired tibia_pad — wraps the tibia knee-block, ~8 g TPU, U opening up), **grommet_insert ×6** |

## 2. Slicer spec

| Class | Walls | Layer | Infill | Notes |
|---|---|---|---|---|
| legs PA6-CF | 4 | 0.2 | 40% (**tibia 25%** — stress audit SF 35) | orientations per part headers: femur/tibia flat −Z, coax rear-face-down + supports under the yoke bridge, shoulder rear-face-down + tree supports, tibia tab-down + pillars, shoulder_plate horn-seat-down, knee_arm underside-down, strap flat |
| head/bracket PA6-CF | 4–5 | 0.2 | 40–60% | `head` CROWN/PAD-DOWN (the flat crown top on the bed = best L2-seat + ear-pad surface; the boss + tilted face + cheeks rise → tree supports under the tilted-face + cheek overhangs); `neck_bracket` BASE-DOWN (deck face on the bed, wall+gussets rise); `l2_adapter` FLAT bottom-down (zero supports) |
| chassis PETG-CF | 3 | 0.25 | 20% | riser DECK-FACE-DOWN (zero supports); floor_plate flat (zero supports); battery_pocket FLOOR-DOWN (opening up, zero supports); jetson_case_mount base-down |
| TPU | 2 | 0.2 | 100% | clips/rails/grommet flat; **knee_bumper U-opening-UP**; shoe per stock orientation |

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
- shoulder D456 pads + lower flange bosses: 0.75 floor — press to flush,
  STOP (slight bulge on the inner face is cosmetic-only if you push)
- femur shelf / flange uppers: 13+ deep, no care needed
- riser: all sites through-vented by design
- iron + M3 tip, inserts from the DOCUMENTED face (several press from
  inner faces — a bench press can't reach; see part headers)

## 4. Wave 1 — first article (~450 g, doctrine: before batching)

- [ ] 1× RIGHT leg set (coax_R, femur_R, tibia_R, knee_arm), 1× shoulder,
      1× shoulder_plate pair, 1× shoe, 1× skid_rail, 2× cable_clip,
      1× knee_bumper, 1× strap
- [ ] 1× head + 1× neck_bracket + 1× l2_adapter + 2× head_ear (FIT-CHECK — prove
      the L2 Ø51 + D456 ±47.5 patterns vs the real parts; the ear feet bolt to
      the pad; the L2 adapter tongue slides under the crown lip)
- [ ] **ASSEMBLY ORDER (head)** — every fastener driver-access audited 2026-07-08:
      - BENCH-a: **L2 → l2_adapter** — 4× M3 up from the adapter BOTTOM (heads
        countersunk flush) into the L2 base. All 4 reachable on the bare plate.
      - BENCH-b: **D456 → head face plate** — 2× M3 from behind the tilted plate
        (the cheeks are pocketed at ±47.2 for driver room). Rear screws are
        unreachable once the head is on the robot — do this on the bench.
      - (1) **neck_bracket → deck** — 4 bolts drilled at first assembly, nyloc
        from below (front pair (146,±19) open from above; rear pair (110,±20)
        tight vs the side webs — use a nut driver/socket, not a big handle).
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
- [ ] Weigh every part → nova.urdf.xacro masses (backlog #5/#13)

## 5. Wave 2 — batch (after wave 1 passes)

- [ ] Left mirrors + 3 more leg sets + 2nd shoulder + plates + 3 more straps
- [ ] Chassis set: riser_bay, floor_plate, battery_pocket, jetson_case_mount,
      neck_bracket (final), head (final — AFTER the fennec styling pass +
      bench-verified mounts, else it re-prints)
- [ ] TPU: remaining 3+1 shoes, 2nd rail, 18 clips, 3+1 knee_bumper
- [ ] Spares: **2–3 horn discs**, 1 shoe, 4 clips
- [ ] Weigh the full set → final URDF masses; update
      `docs/improvement-backlog.md` #5

## 6. Assembly-adjacent (same bench era)

- [ ] Drill floor: battery 6-hole pattern + shoulder-feet 4 holes
      (floor_plate = template), csk from below for the feet bolts
- [ ] Cable dressing per leg_v6 README (clips at both loop ends, ≥40 mm
      loops, spiral wrap, tug-test all anchors + 24 connector ends)
- [ ] Skid rails: key + CA/VHB under the tray
- [ ] Breakaway fuses (#2): the masts are RETIRED → re-map the nylon-M3
      breakaway concept to the HEAD mount (4× M3 boss→bracket) so the head
      pops off in a fall instead of snapping the neck. ⚠ DECISION open —
      the bracket→deck bolts should stay metal (structural); only the
      head→bracket joint is the breakaway candidate
- [ ] Washers under every stock-shell-side head (#3)
- [ ] EVA foam pad on the battery tray floor + felt/kapton on the
      shoulder-flange bottom edges over the pack (#29)
- [ ] TPU grommet inserts into the 4 flange grommets before cable pull (#30)
- [ ] Riser shake test (0.45 lateral tab slack) after hold-down screws
- [ ] **E-stop pod mounted + wired BEFORE first bus power** — ⚠ the hood is
      RETIRED (official Jetson case adopted), so the pod + OLED lost their
      home. New mount TBD (case top / riser deck / neck bracket) — resolve
      before this step
