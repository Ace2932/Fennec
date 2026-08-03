# Fastener Schedule — chassis / head / electronics (audit 2026-07-08)

Every screwed connection with the **standard hardware** it takes + the verification
that the hole/boss actually works for it. Standards used: metric socket-cap (SHCS)
unless noted; **clearance** Ø — M2 2.3, M2.5 2.9, M3 3.4; **Ruthex heat-set** bore
Ø4.0 (M3, OD 4.6, len 5.7 — the "M3×5.7"; short "M3×3.8" where a part is thin),
Ø3.0 (M2, OD 3.2, len 4.0). Boss wall must be **≥1.5mm** (M3) / **≥1.0mm** (M2)
around the insert — verified by ring-in-mesh test.

## Why this audit happened
Bosses were originally sized ~Ø5–6 → 0.3–0.7mm insert walls (M3 heat-sets split
below ~0.75mm). Fixed: widened/relocated the M3 bosses where structural; switched
the LIGHT, pinched mounts (cradle clamps + deck-ties, control-pod) to **M2**
(1.0–1.4mm wall in the 6mm posts, huge load margin); short M3×3.8 inserts where a
part is <6mm. All insert walls now pass.

## Schedule

| Connection | Screw (std) | Hole / insert | Engage | Wall | Status |
|---|---|---|---|---|---|
| **head → neck bracket** ×4 | **NYLON M3×12** SHCS (#42 breakaway) | rear c'bore Ø6.5×3 + wall clear Ø3.4; **M3×5.7 insert** in the head boss (HM_Y=10, centered bore↔edge) | 5.7 | 1.7–2.2 | ✅ (AUD-12 fix 2026-07-10: the old USB-C column channel ran straight through the boss and voided the +y pair of inserts — **0.0mm floor/wall measured at both** (2 of 4 bolts). `head.scad`'s channel rerouted to share the L2 cable bore below the boss top instead of cutting new boss material; all 4 boss floors now probe-verified SOLID (was 0.0 → now solid at every axis). `check_fit.py` case 14 gates this axis going forward; nylon breakaway fuse function unaffected — no bolt/insert position moved) |
| **neck bracket → deck** ×4 | M3×8 SHCS | base clear Ø3.4; **M3×3.8 SHORT insert** pressed into the shoulder deck (`leg_v6/shoulder.scad` `neck_heatset` pockets — printed pilots, no drilling, no nuts) | 3.8 | 2.3 floor | ✅ (NO-DRILL fix 2026-07-10: was drill-at-assembly Ø3.4 + nyloc below. Front pair relocated trunk x110→x117 off the shoulder's 22.5mm rear-wall rib onto the flat deck; probe-verified 2.3mm floor under all 4 pilots) |
| **L2 → l2_adapter** ×4 | M3×10 **CSK** (90° flat) | adapter CSK Ø6.2→3.4; into the **Unitree L2 base M3 threads** | ~5 | n/a | ✅ ⚠ confirm L2 base is M3-threaded at bench |
| **l2_adapter → crown** ×2 | M3×8 SHCS (from below) | crown clear Ø3.4; **M3×3.8 SHORT insert** in the 5mm adapter (L2 sits on top, can't boss up) | 3.8 | ≥1.5 | ✅ (relocated 114,±9 clear of the L2 CSK) |
| **ears → head pad** ×4 (2/ear) | M3×10 SHCS | ear-foot clear Ø3.4; **M3×5.7 insert** in the pad (pad rear extended x71 for wall) | 5.7 | 1.7 | ✅ |
| **riser → shoulder flange** ×4 | M3×12 SHCS | flange clear; **M3×5.7 insert** in the riser end-wall pad (pressed inner) | 5.7 | ok | ✅ (pre-audited 2026-07-06; CR-8 #1 stack-verified 2026-07-10 — reconciled shoulder.scad/design-outline.md off M3×10) |
| **shoulder flange feet → trunk floor** ×4 | **M3×14 CSK** + **M3 nyloc** + washer | Ø3.4 clear + 90° csk **modeled in `trunk.scad`/`trunk_build.py`** (2026-07-10, printed in — no drilling) through the 3.9mm stock floor slab; up through the 4mm FOOT pad; nyloc+washer on top (reached through the open trunk-end aperture before the riser goes on) | nut | n/a | ✅ (CR-8 #2, stack-verified 2026-07-10: 3.9 floor + 0.1 gap + 4.0 pad + 0.5 washer = 8.5mm before the nut; M3×12 leaves only ~3.5mm for the nyloc — no margin; M3×16 leaves ~7.5mm — 3-4mm of bare proud thread. M3×14 leaves ~5.5mm = full nyloc engagement + ~1.5mm proud. Sourced explicitly, `BOM.md`:168) |
| **battery pocket → floor (top-flange)** ×6 | **M3×10 CSK** (from above) | `floor_plate.scad` Ø3.4 clear + 90° csk (top z5.9) + stock trunk floor Ø3.4 (printed in, `trunk_build.py`); into a **M3×3.8 SHORT insert**, vertical, mouth-up, in the `battery_pocket.scad` rim-flange pad at (x −40/0/+40, y ±27.5) | 3.8 | ≥1.5 | ✅ (AUD-11 fix 2026-07-10 — supersedes the AUD-1 side-loaded M3 nut trap, which cut a **0.0mm wall breach into the LiPo cavity** at all 6 mounts, the confirmed defect this closes. Bolt/insert axis BOSS_Y 26.5→27.5 seals a ring-verified 1.5mm wall; pad OUTER edge pinned at y=30.75, unchanged, so leg-sweep clearance is identical to the AUD-1 build — check_fit.py exits 0, no leg-sweep regressions) |
| **control_pod → riser** ×4 | **M2×8** SHCS | pod column clear Ø2.3; **M2×4 insert** in the riser pocket-pad (pad y widened ±14) | 4.0 | ≥1.0 | ✅ (light mount; pinched pad → M2) |
| **cradle → deck (tie)** ×4 | **M2×8** SHCS (from below) | riser deck clear Ø2.3; **M2×4 insert** in the upright base | 4.0 | 1.4 | ✅ (6mm post → M2; huge margin) |
| **clamp bar → upright** ×4 (2/bar) | **M2×8** SHCS | bar clear Ø2.3; **M2×4 insert** in the upright top; bar underside bears the case corner columns (z102.8) | 4.0 | 1.4 | ✅ (#44: 2 bars replaced the 4 clamps) |
| **OLED bracket → pod deck** ×2 | **M2×8** SHCS (down) | bracket foot clear Ø2.3; **M2×4 insert** in the pod deck +y edge (x-96/-71, y23) | 4.0 | 1.5 | ✅ (#40: OLED split off pod) |
| **SSD1331 → OLED bracket** ×4 | M2×6 SHCS + **M2 nut** | bracket panel clear Ø2.3; PCB behind, nut on the +x side | nut | n/a | ✅ |
| **E-stop** ×1 | mxuteuk 22mm 2NC **Ø22 barrel + supplied nut** | Ø22.6 deck hole; Ø40 mushroom; 77mm total; **panel max 6mm** (deck 5 ✓); ~30×30×48 block below (pod gussets flank it y±17) | — | — | ✅ verified vs the Amazon part 2026-07-08 |

leg_v6 fasteners (coax/femur/tibia/shoulder/horn/wheel/foot) were audited
2026-07-06 (memory: heat-set insert notes) — M3/M2.5/M2 clearances + Ruthex M3
bores, all standard; not re-listed here.

## leg_v6 STS3215 servo screws — MEASURED 2026-07-11

Every servo (HAA in `coax`, HFE in `femur`, KFE in `tibia`) takes 3 fastener
families: 4× **M2 case-mount** (replaces the stock self-tap columns — see
`leg_v6_common.scad:24` — **too short stock**, already known), 4× **M3
horn** (driven-side yoke arm → the servo's OUTPUT horn), 4× **M3 wheel**
(idler-side yoke arm/boss → the BOTTOM WHEEL, **no center screw** — the wheel
disc carries only a plastic idler boss there, `WHEEL_CTR_D` relief, not a
thread). All 3 joints take the SAME 12 screws/servo, but **lengths differ by
joint** — measured via `trimesh` ray-casts on freshly-rendered STLs
(`coax_R`/`femur_R`/`tibia_R`/`shoulder`/`shoulder_plate`/`knee_arm`), not
assumed from the SCAD constants. A driven-side **stock retention screw**
(Ø5.4 head × ~1.5mm proud, factory-installed with the horn) is NOT sourced —
only its clearance counterbore (`HORN_CTR_D`/`HORN_CTR_DEEP`) is a design
concern.

| Connection | Screw (std) | Hole / stack | Engage | Grip | Status |
|---|---|---|---|---|---|
| **case → HAA (coax)** ×4, **case → KFE (tibia)** ×4, **case → HFE (femur) NEAR pair** ×2 (`COL_PTS` x=−8.3) | **M2×9 self-tap, CSK** 🔴 *was M2×22* | `M2_CLEAR` 2.3 clear + Ø4.6→2.3 countersink through the printed floor | into servo case column, **7.0 mm blind (MEASURED)** | **floor 2.125mm MEASURED** (ray-cast, all 3 parts agree exactly; ~0.4mm under the nominal `FLOOR`=2.5 comment — real bay-cavity-cut boundary sits at z=−20.075, not the `FLOOR_TOP` reference) | 🔴 **CORRECTED 2026-08-02 — the "≥22 baseline" this row used to confirm was itself back-solved from an ASSUMED 19.9 mm column.** Real column is **7.0 mm blind, measured**: floor 2.125 + 7.0 = **9.1 mm max**, so M2×9. An M2×22 drives ~13 mm past the bottom of a blind hole. See the CASE SCREWS block below |
| **case → HFE (femur) FAR pair** ×2 (`COL_PTS` x=−32.8, under the LA-6/`SUB_FLOOR` underside ramp) | **M2×13 self-tap, CSK** 🔴 *was M2×25* | same, but floor is ramped **4.4mm deeper** here (femur-local x=32.8) | into servo case column, **7.0 mm blind (MEASURED)** | **floor 6.525mm MEASURED** (+4.4mm vs the near pair — exact match to the ramp's own "rise 4.4" design note) | 🔴 **CORRECTED 2026-08-02.** floor 6.525 + **7.0 measured** column = **13.5mm MAX** before bottoming → **M2×13** (M2×14 bottoms by 0.5). The old row's whole chain was built on a column depth *back-solved from the 22mm baseline* — the 22 was never independently measured, so it confirmed itself. That is the circular-self-confirmation trap |
| **horn → HAA** ×4 (`shoulder_plate.scad`), **horn → KFE** ×4 (`knee_arm.scad`) | **M3×6** 🔴 *was M2.5×6* | `M3_CLEAR` **3.4** clear through `ARM_THK`=4.0, no head c'bore | into horn disc (~3.05mm, project's calipered figure — see note) | **grip 3.6mm MEASURED** (4.0 − 0.4mm `HORN_OD` locating-recess that spans the whole horn footprint) | ✅ 3.6+~2.5 target=6.15 → **round DOWN** to 6 (don't bottom out the 3.05mm disc). 🔴 **THREAD CORRECTED TO M3 2026-08-02 (#263)** — the FEETECH STS3215 spec gives the disc threads as M3. Length math is unchanged (grip is geometry, not thread), but `M25_CLEAR` is **deleted** from `leg_v6_common.scad` |
| **HFE block → coax (retention)** ×2 (`coax_hfe_block.scad`, #226 option C) | **M3×16 SHCS** | `M3_CLEAR` 3.4 through the tenon + Ø6.0 head c'bore on the block's outboard face | **SLIM M3 heat-set: 4.0 mm OD × 6.0 long**, in a **Ø3.5 × 6.5** bore at the mortise blind end (x 46.35 → 39.85). ⚠️ **NOT the 4.6 mm OD insert used everywhere else** | **RE-MEASURED 2026-08-02: head seat x=57.0, pocket bottom x=39.85 → 17.2 mm span; M3×16 engages 5.2 mm of the 6.0 insert and stops 1.15 mm clear of the bottom.** Bolt axis moved z 11.5 → **11.7** to sit centred in the slot | ✅ **Why a different insert:** the insert must TRAVEL ~10 mm down the mortise to reach its bore, and that slot was **4.00 mm** against a 4.6 mm insert — undeliverable at any print accuracy, a valid seat with no path, the same failure that retired this joint's cap. Growing the slot to 5.0 for a 4.6 insert puts the roof at exactly 1.50 mm (`MIN_SECTION_MM`, no margin) and more forces `GROW_Z1` up, which **hits the shoulder at haa −40**. Pull-out goes as π·D·L, so 4.0×6.0 = **75 mm²** vs 4.6×5.7 = 82 mm² — **92 % of the strength for a 0.4 mm slot growth instead of 1.0**. `MORT_Z1` 13.5 → 13.9; roof 1.95 mm, floor 1.95 mm, both gated. Retention only — the tenon carries the moment in bearing (66 N/bolt cyclic vs ~160–225 N wet pull-out at this area, SF ≈ 2.4–3.4). `insert_path_checks()` now sweeps the insert's DIAMETER down its delivery path |
| **knee_arm → femur shelf** ×4/leg = 16 (`knee_arm.scad`) | **M3×8 SHCS** ⚠️ *corrected from M3×10 the same day* | 2× Ø3.1 dowel-fit + 2× Ø3.4 clear through the 4.0 plate, head on top (no c'bore) | **M3×5.7 insert** in the femur shelf | **MEASURED by `engagement_checks()`: grip 2.18 mm** — the plate is 4.0 thick but carries a **Ø6.4 × 1.8 head counterbore**, so the seat is 1.8 below the top face. M3×8 → **5.82 mm into the 6.2 bore (1.94×D)**. ⚠️ **My first derivation said M3×10 and was wrong**: it took the head seat from the part's bbox top and missed the counterbore. M3×10 leaves 7.82 mm against a 6.2 bore — **it bottoms** | ⚠️ **THIS ROW DID NOT EXIST until 2026-08-02.** The joint is in `leg_v6/README.md` and in the CAD, but no length was recorded anywhere — the same gap that let the HFE block ship an M3×22 that bottoms out |
| **shoulder_plate → shoulder deck** ×4/plate = 16 (`shoulder_plate.scad`) | **M3×6 SHCS** ⚠️ *corrected from M3×8 the same day* | flange clear Ø3.4, head on top | **M3×5.7 insert** in the deck (`PLATE_BX`×`PLATE_BY`, bored from `DECK_Z1`=41.5) | **MEASURED by `engagement_checks()`: grip 1.38 mm** — same **Ø6.4 × 1.8 counterbore** as knee_arm. M3×6 → **4.62 mm into the 6.2 bore (1.54×D)**. ⚠️ **My first derivation said M3×8 and was wrong** for the same reason (bbox top ≠ head seat); M3×8 leaves 6.62 mm against 6.2 — **it bottoms by 0.42 mm** | ⚠️ Row did not exist until 2026-08-02 |
| **horn → HFE** ×4 (`coax.scad` inboard arm) | **M3×5** 🔴 *was M2.5×5* | same (`M3_CLEAR` **3.4**), but arm backs onto the HAA pocket cavity (LA-7: 3.2mm local budget, not the full 4.0mm `ARM_THK`) | into horn disc | **grip 2.8mm MEASURED** (3.2 local budget − 0.4mm recess; `ctr_deep=1.65` override on the center relief only) | ✅ 2.8+~2.5 target=5.35 → round DOWN to 5 |
| **wheel → HFE** ×4 (`coax_hfe_block.scad` arm+boss — moved off `coax.scad` in #226 option C), **wheel → KFE** ×4 (`femur.scad` own bottom arm+boss) | **M3×8** 🔴 *was M2.5×8* | `M3_CLEAR` **3.4** clear + **Ø6.0** head c'bore (**1.6mm real depth**, measured — the shared `wheel_couple_neg()` cylinder is nominally 2.6 but 1.0mm of that is overcut margin below the true exterior) | into wheel disc (~2.1mm MEASURED directly off `servo.stl`, matches the ~2.15 doc figure) | **grip 6.44mm MEASURED after the 2026-08-02 counterbore fix** (was 7.25). `WHEEL_HEAD_CB_DEEP` 1.6 → **2.4** in the shared `wheel_couple_neg()`, which only HFE and KFE use — **engagement 0.76 → 1.56mm, same ×8 screw**. ⚠️ **×D ratios RESTATED for M3 (#263):** 1.56/3.0 = **0.52×D** (was quoted 0.62×D against the wrong D of 2.5); the pre-fix 0.76mm is **0.25×D**, not 0.30. The absolute millimetres are measured and unchanged — only the ratio's denominator was wrong. Length could never fix this: a longer screw bottoms in the ~2.1mm disc. Engagement = length − GRIP, and the counterbore is what sets grip. ⚠️ Deliberately +0.8 not +1.0: the 2.1mm disc is measured off `servo.stl` and its TAPPED depth is unknown, so 0.54mm of anti-bottoming margin is kept. **FIRST-ARTICLE: measure the disc's real thread depth** — if the holes are through, +1.2 is available. ⚠️ The HAA wheel is cut separately in `shoulder.scad` (its own 1.8 c'bore, 1.40mm engagement) and must NOT be deepened: 2.4mm into a 2.1mm disc bottoms | ✅ 7.25+~1.7 target=8.95 → round DOWN to 8 (**thin: only ~0.75mm real engagement into the 2.1mm disc — tightest joint in this table**) |
| **wheel → HAA** ×4 (`shoulder.scad` wheel boss, long rear-wall→wheel-face reach) | **M3×14** 🔴 *was M2.5×14* | **Ø6.0** head c'bore (**1.75mm measured**, code says 1.8) at the rear-wall exterior | into wheel disc | **grip 12.6mm MEASURED** (boss reaches 14.35mm total, far longer than the leg's own 4.85mm boss) | ✅ 12.6+~1.7 target=14.3 → round DOWN to 14 |
| **stock retention screw** (driven side only — HAA/HFE/KFE horns, NOT wheels) ×1/servo | **STOCK** (Ø5.4 head × ~1.5mm proud, factory-installed with the horn) | printed clearance only: `HORN_CTR_D` Ø6.5 blind c'bore, `HORN_CTR_DEEP` 2.5mm generic / **1.65mm at coax's inboard arm** (LA-7: floor 1.55mm, head margin 0.15mm — first-article check) | n/a | n/a | ✅ NOT sourced — comes with the servo/horn kit |

**Horn disc thickness note:** the wheel disc (~2.1mm) was confirmed by direct
ray-cast on `feetech_servo_models/converted_stl/servo.stl` (clean, unambiguous
flat face). The horn disc resisted the same clean read — cross-section slicing
showed a 4-lobed registration ring (r 5.75–10) rather than a simple flat disc,
so the horn engagement bound above uses the project's own CALIPERED figure
(~3.05mm, from the 35.5mm real disc-to-disc measurement, `leg_v6_common.scad`
rev-3) rather than a shakier mesh read of that specific feature.

**Stock vs source:** case screws are confirmed too short stock (already
documented). No verified stock M3 horn/wheel screw length was found in this
repo to compare against — every position above adds a 3.6–12.6mm printed
yoke arm/boss between the screw head and the disc that a stock (thin-arm,
direct-mount) screw isn't sized for; **source all 4 M3 lengths (5/6/8/14mm)
explicitly**, don't assume the servo kit's screws cover any of them. The servos
*do* ship disc screws, but they are sized for direct thin-arm mounting and are
too short for every position in the table above.

**~~Open finding~~ CLOSED (re-checked 2026-07-26):** the phantom 5th "center
(wheel is M2.5)" clearance hole in the shared `wheel_couple_neg()` was already
removed under **#51 (2026-07-11)** — the module now cuts only the 4 BCD screws
plus the blind `WHEEL_CTR_D` idler-boss relief, so nothing is latent in
`coax.scad`'s HFE or `femur.scad`'s KFE wheel coupling. This paragraph was
stale, not the code. ✅ `design-outline.md:95` ("4× M2.5 + ctr") **also fixed
2026-08-02** — it repeated both retired assumptions (the phantom centre screw
*and* the M2.5 thread).

**Head protrusion at the wheel BCD (noted 2026-07-26, first-article check):**
the counterbore (**now Ø6.0**, #263) is **1.6 mm deep** (above) while an M3 SHCS
head is Ø5.5 × ~3.0 mm tall, so each of those 8 heads per leg stands **~1.4 mm
proud** of the yoke bottom-arm / coax outboard-arm exterior — worse than the
~0.9 mm this paragraph recorded for M2.5. Both faces look into free air (femur
underside at the knee, coax outboard flank) and the sweep gates are run against
the STLs, which do not model heads — so this is a snag/scuff item, not an
interference one. **Use M3 BUTTON head** (ISO 7380, Ø5.7 × 1.65 tall): it drops
the protrusion to ~0.05 mm, effectively flush, and Ø5.7 still clears the 6.0
c'bore. That is why the 6.0 figure was chosen over the 5.5 an SHCS alone needs.

**cowl → upright ×2 (M2×10 SHCS + M2×4 insert, Ø5.5 c'bore)** — REMOVED
2026-07-10 (backlog #41): `jetson_cowl.scad` retired in place, superseded by
right-angle plug adapters (`BOM.md`). No cowl bolts/inserts to source.

### ⚠️ Open on every screw that threads into a servo disc

`engagement_checks()` compares thread engagement against the **disc thickness**
(2.1 mm wheel, 3.05 mm horn), both taken from `servo.stl` / calipers. **The
TAPPED depth inside those discs is not known.** If a disc's thread is shallower
than the engagement figure, that screw bottoms — and a bottomed screw has no
preload at all, which is the same failure as the M3×22 found on 2026-08-02.

Current engagements against the assumed depths: wheel HFE/KFE **1.56 / 2.1**,
wheel HAA **1.40 / 2.1**, horn HFE **2.20 / 3.05**, horn KFE **2.42 / 3.05**,
horn HAA **2.40 / 3.05**. The horn screws use 72–79 % of the assumed depth.

**FIRST-ARTICLE: measure the real thread depth in one horn disc and one wheel
disc.** It resolves five joints at once, and it is the only number standing
between "measured" and "assumed" in this whole table.

## Purchase summary (chassis/head/electronics)
- **M3 SHCS**: ×4 **NYLON** M3×12 (head→bracket, breakaway), ×4 M3×12 (riser→flange), ×4 **M3×8** (bracket→deck — ⚠ **CORRECTED 2026-08-02, this said M3×16**, contradicting both the row-23 detail above and `neck_bracket.scad` lines 28/61, which say M3×8 with `BASE_T = 4`. 4 mm base + 3.8 mm insert = 7.8 mm of usable depth; an M3×16 bottoms on the 2.3 mm deck floor or splits it), ×2 M3×8 (adapter→crown), ×4 M3×10 (ears)
- **M3 CSK**: ×4 M3×10 (L2→adapter), ×4 M3×14 (shoulder flange feet → trunk floor, CR-8 #2), ×6 M3×10 (battery pocket → floor, AUD-11 heat-set fix — was ×6 M3×8 + M3 hex nut under AUD-1)
- **M3 nyloc**: ×4 (shoulder flange feet, w/ washer). ⚠ **The ×4 for bracket→deck was removed 2026-08-02 — obsolete.** The NO-DRILL fix of 2026-07-10 (row 23) replaced drill-at-assembly + nyloc-below with pressed M3×3.8 heat-sets; this line had not followed.
- **M2 SHCS**: ×4 M2×8 (pod), ×4 M2×8 (deck-tie), ×4 M2×8 (clamp bar), ×2 M2×8 (OLED bracket foot), ×4 M2×6 (SSD1331)
- **M2 nut**: ×4 (SSD1331)
- ⚠️ **INSERT COUNT WAS CHASSIS-ONLY — corrected 2026-08-02.** The line below covered head/ears/riser and omitted every leg and shoulder insert. Counted off the CAD: **coax→block 8** (slim 4.0 OD, see the row above) · **femur→knee_arm 16** · **shoulder deck→plate 16** · **shoulder→trunk 16** · chassis 12 = **~68 M3 total**, against a documented 16.
- ✅ **ORDERED 2026-08-02:** M3 × 4.6 OD × 5.7 (ruthex `B08BCRZZS3`) **×100** · M3 short
  RX-M3Sx4.0 (`B09ZHSGHXD`) ×100 · M2 × 4 (`B088QJG676`) ×70.
- 🔴 **NOT ORDERED — this line said "ON ORDER" and that was wrong** (corrected 2026-08-02;
  `master-bom.md` had it right and the two disagreed, in the direction where you read
  "ordered" and never place it): M3 × **4.0 OD × 6.0** (slim, HFE block only) **×25** ·
  **M3×16 SHCS ×20** · **M3×8 ×25** (knee_arm) · **M3×6 ×25** (shoulder_plate).
  The slim insert **did not exist** until #255 merged, which was the same day the order
  went out — so it could not have been on it. The three screw lengths were never placed.
  ⚠️ Two of these gate the next assembly: `coax_R` + `coax_hfe_block` are the next parts
  to print, and that joint needs the slim insert **and** M3×16. Lengths corrected the same
  day after `engagement_checks()` measured the head seat instead of the bbox top — the
  first pass said ×10 and ×8, and both bottom out.
- 🔴 **SUPERSEDED — the M2.5 family does not fit and must not be used.** Received 2026-08-02
  (order 111-2168015-0136233, $37.26): ×100 M2.5×5, ×105 M2.5×6, ×100 M2.5×8, ×100 M2.5×14.
  **The FEETECH STS3215 spec gives the disc threads as M3** (#263, 2026-08-02) — M2.5 was this
  project's own unsourced inference. A 2.5 mm screw in an M3 thread does not engage at all. The
  lengths (5/6/8/14) were right and carry straight over to M3; only the thread was wrong. Keep the
  M2.5 stock for unrelated M2.5 work, don't scrap-hunt it into this build. **Button head is still
  the right head** for the same reason it was before: 1.5 mm tall clears the wheel c'bore's 1.6 mm
  real depth flush, where an SHCS head stands proud. ⚠️ Also outstanding from the same BOM line:
  the servo case-mount self-tappers, now **M2×9 ×40 + M2×13 ×8** (not ×22/×25 — see below).
- **Ruthex inserts**: M3×5.7 ×16 (head 4, ears 4, riser flange 4, + spares), M3×3.8 ×8 (adapter 2, battery pocket 6 — AUD-11 fix), M2×4 ×14 (pod 4, deck-tie 4, clamp bar 4, OLED-bracket-in-pod-deck 2)
- **E-stop**: HB2-ES544 (Ø22, owned)

## 🔴 CASE SCREWS — M2×22/M2×25 WAS WRONG AND WOULD WRECK SERVOS (measured 2026-08-02)

The stock screw and its column were finally measured. Every number below is off a
real STS3215, not back-solved:

| | measured |
|---|---|
| stock screw | **PA ~2.0 self-tapping**, **PAN head Ø3.2**, **7 mm** under-head |
| pitch | **~1.2 mm** (6 crests over 7 mm) — coarse, plastic-forming |
| **case column depth** | **7.0 mm — BLIND** |

**The column is 7 mm, not the 19.9 mm this document assumed.** That 19.9 was
back-solved from the 22 mm baseline, and the 22 was never derived from anything —
`leg_v6/README.md` has always said *"measure stock length at first article, spec ≈
stock + 3 mm"*, which gives **10 mm**. Circular, and nobody measured until now.

🔴 **An M2×22 drives ~13 mm past the bottom of a blind hole in plastic**, with the
gear train and encoder above it. 4 per servo × 12 servos. Do not fit one.

### Correct lengths — `floor + column`, and they must not bottom

| pair | printed floor | max under-head | use | engagement |
|---|---|---|---|---|
| near — HAA `coax`, KFE `tibia`, HFE-near `femur` | 2.125 | **9.125** | **M2×9** (M2×8 safe fallback) | 6.9 mm (8 → 5.9) |
| far — HFE-far `femur` (LA-6 ramp) | 6.525 | **13.525** | **M2×13** (M2×12 safe fallback) | 6.5 mm (12 → 5.5) |

M2×10 bottoms the near pair by 0.9 mm; M2×14 bottoms the far pair by 0.5 mm.
Bottoming in a blind plastic column means no preload, then a stripped or split boss.

### ⚠️ Buy COUNTERSUNK, not pan like the stock screw

The printed floor has a **cone, Ø4.6 → Ø2.3 over 1.4 mm**, and `README.md` specs these
"countersunk" — the intent was always CSK. A **pan head cannot seat in a cone**: it makes
line contact where the cone equals the head Ø (0.85 mm down for Ø3.2), sits ~0.5 mm
proud, and wedges the ~1.15 mm wall around the hole. **The factory screws cannot be
reused in the printed part.** A 90° CSK head (~Ø3.8) contacts near the cone mouth and
seats slightly recessed — the good case, and no CAD change needed.

### They MOUNT THE BODY — they do not hold the servo case shut

Corrected 2026-08-03 (user, at the bench). The version of this block merged in #264 said the
screw "clamps the case shut AND bolts the servo to the leg". **It does not.** These four are
blind mounting columns in the servo's bottom face; the case is held together by its own
hardware. Two consequences, both in the reassuring direction:

- **There is no "case unclamped" window during assembly.** Pulling all four does not open
  the servo. #264's warning to keep it bottom-face-down and not invert it was wrong —
  disregard it. Nothing about the gear train or encoder is exposed.
- **The load is SHEAR, not tension.** The servo reacts its own output torque against these
  four. `COL_PTS` = (−8.3, ±10.2) and (−32.8, ±10.25), so the centroid radius is
  `√(12.25² + 10.2²) ≈ 15.9 mm`; stall is 19.5 kg·cm = 1.91 N·m, giving
  **F ≈ 1.91 / (4 × 0.0159) ≈ 30 N per screw in shear.** Shear capacity is nearly
  independent of engagement depth past the first few threads.

So 5.5–6.9 mm of engagement against the factory's 7 mm is **not a meaningful reduction for
this joint**, and the kit lengths (M2×8 / M2×12, ≈4.0–4.4 mm of thread) are comfortably
adequate rather than a compromise. These screws are also one of four retention features —
pocket walls at 0.45/side, the platform seat, the bay seat, and the printed tail strap — and
per the connection map their real duty is **positional**: "the 4 screws, ±0.15 → THE servo
locator".

⚠️ `leg_v6_common.scad:23` calls these "CASE-SCREW COLUMNS", which is what invited the wrong
reading. The same comment correctly adds "the REAL mounting". Read it as body-mount.


## Purchase summary (leg_v6 STRUCTURAL screws + ALL heat-set inserts) — ADDED 2026-08-02

The two summaries either side of this one leave a hole. The chassis one is scoped
"(chassis/head/electronics)"; line 38 says leg fasteners are "not re-listed here"; and the leg one
below covers **servo screws only**. So the leg's own structural M3s and — more seriously — **every
heat-set insert in the leg** appeared in no buy list anywhere, while the leg is what prints first.
Counted from the CAD loops, not from a summary.

**Heat-set inserts, whole robot:**

| Insert | Leg | Chassis/head | Total | Buy |
|---|---|---|---|---|
| **M3×5.7** | **56** — `shoulder.scad` 16/part ×2 (plate bores `sx×PLATE_BX×PLATE_BY`=8, trunk-flange 4, D456 pads 4) · `femur.scad` 4/part ×4 (`hx[65,75]×hy[±8]`) · `coax.scad` 2/part ×4 (`BOLT_YS`) | 16 | **72** | **100** |
| **M3×3.8** | 8 — shoulder `NECK_HS_XY` 4/part ×2 | 8 — l2_adapter 2, battery pocket 6 | **16** | **25** |
| **M2×4** | 0 | 14 | **14** | **25** |

A botched press wrecks the insert and sometimes the part, so buy 50-packs; spares are not optional.

**Leg structural M3 (lengths computed 2026-08-02 — no length existed anywhere before):**

| Screw | Qty | Stack |
|---|---|---|
| **M3×8 SHCS** | 16 | `knee_arm`→femur shelf ×16 (4/leg): `ARM_THK` 4.0 − 1.8 c'bore = **2.2 grip** + 5.7 insert = 7.9 → 8. `shoulder_plate`→shoulder deck is **M3×6, not M3×8** — measured off the mesh 2026-08-02, an M3×8 **bottoms by 0.42 mm**. My 7.1 → 8 above was arithmetic on constants; the measurement wins |
| **M3×16 SHCS** | 10 | coax option-C block retention, 2/leg (#226). ⚠️ **This row said M3×22 until 2026-08-02 — that BOTTOMS OUT.** #235 moved `MORT_X0` 43.8 → 46.4 and the insert pocket rides it, so usable span is **16.8 mm, not 19.5**; M3×22 bottoms 5.2 mm early and M3×20 3.2 mm early, in a **blind** pocket. Now gated by `fastener_span_checks()` |

Both are first-article-verifiable: seat a screw and check it neither bottoms nor stands proud.

## Purchase summary (leg_v6 servo screws, MEASURED 2026-07-11 — 12 active servos: 4 HAA + 4 HFE + 4 KFE)
- **M2 self-tap (case-mount), COUNTERSUNK**: ×40 **M2×9** (HAA×16 + KFE×16 + HFE-near×8), ×8 **M2×13** (HFE-far pair only, ramped floor). ⚠️ **This line read M2×22 / M2×25 until 2026-08-02** — the column is **7 mm blind, measured**, not the 19.9 mm assumed, so a ×22 goes 13 mm into the servo. See the CASE SCREWS block above.
- **M3 (horn, driven side)**: ×32 **M3×6** (HAA×16 + KFE×16), ×16 **M3×5** (HFE, thinner LA-7 backing)
- **M3 (wheel, idler side, NO center screw)**: ×32 **M3×8** (HFE×16 + KFE×16), ×16 **M3×14** (HAA, long boss reach)
- 🔴 **These two lines read M2.5 until 2026-08-02 (#263).** The FEETECH STS3215 spec gives the
  disc threads as **M3**; the M2.5 figure was this project's own inference, never sourced. Holes
  went 2.9 → **3.4** and the disc-facing head c'bores 5.2 → **6.0** in `leg_v6_common.scad`, and
  `M25_CLEAR` was **deleted** rather than redefined. **Lengths did not change** — grip is set by
  printed geometry, not by thread diameter. ⚠️ **The M2.5 family was already bought and received**
  (order 111-2168015-0136233, $37.26) and is now **scrap for this purpose** — do not re-derive the
  build from it. M3 replacements ordered 2026-08-03.
- Total 144 screws = 12/servo × 12 servos, self-consistent. Stock retention screw (×12, one per horn) is NOT sourced — factory-installed.
- Add ~10% spares per length given self-tap/plastic-thread wear risk (case) and the thin HFE/KFE wheel engagement margin.
