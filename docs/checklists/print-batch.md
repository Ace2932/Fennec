# Print Batch Checklist (v6 full set)

From the 2026-07-06 batch-questions review. Prereq: **caliper session
first** (Jetson heatsink, D456 rear pattern, 5191 block, real pack dims)
— else hood / d456_head / floor_plate / battery_pocket print twice.

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
| PA6-CF (DRY 80 °C/10 h; no anneal — §3) | coax, femur, tibia, knee_arm, shoulder, shoulder_plate (+L variants) |
| PETG-CF | riser_bay, floor_plate, battery_pocket, spacer ×8, l2_mast, d456_head, hood (post-caliper) |
| TPU 95A | SM3_Foot shoe ×4+1 (STOCK geometry — crush-zone v2 waits for first-article, #20), skid_rail ×2, cable_clip ×20, **tibia_pad ×5** |

## 2. Slicer spec

| Class | Walls | Layer | Infill | Notes |
|---|---|---|---|---|
| legs PA6-CF | 4 | 0.2 | 40% (**tibia 25%** — stress audit SF 35) | orientations per part headers: femur/tibia flat −Z, coax rear, shoulder rear-face-down + tree supports, tibia tab-down + pillars |
| chassis PETG-CF | 3 | 0.25 | 20% | riser deck-face-down (zero supports), mast flange-down + trees |
| TPU | 2 | 0.2 | 100% | clips/rails flat; shoe per stock orientation |

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
      1× shoulder_plate pair, 1× shoe, 1× skid_rail, 2× cable_clip
- [ ] Fit checks (leg_v6 README "Verify"): pocket drop-in (0.25/side),
      M3 through the Ø3.1 dowel pair, M2 through columns, insert purchase
      at Ø4.0, countersink flush, fork-arm seat flatness
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

- [ ] Left mirrors + 3 more leg sets + 2nd shoulder + plates
- [ ] Chassis set (incl. hood + d456_head if calipers done)
- [ ] TPU: remaining 3+1 shoes, 2nd rail, 18 clips
- [ ] Spares: **2–3 horn discs**, 1 shoe, 4 clips
- [ ] Weigh the full set → final URDF masses; update
      `docs/improvement-backlog.md` #5

## 6. Assembly-adjacent (same bench era)

- [ ] Drill floor: battery 6-hole pattern + shoulder-feet 4 holes
      (floor_plate = template), csk from below for the feet bolts
- [ ] Cable dressing per leg_v6 README (clips at both loop ends, ≥40 mm
      loops, spiral wrap, tug-test all anchors + 24 connector ends)
- [ ] Skid rails: key + CA/VHB under the tray
- [ ] Nylon M3×10 at both mast mounts (hand-tight — fuses, #2)
- [ ] Washers under every stock-shell-side head (#3)
