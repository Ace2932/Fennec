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
`leg_v6_common.scad:24` — **too short stock**, already known), 4× **M2.5
horn** (driven-side yoke arm → the servo's OUTPUT horn), 4× **M2.5 wheel**
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
| **case → HAA (coax)** ×4, **case → KFE (tibia)** ×4, **case → HFE (femur) NEAR pair** ×2 (`COL_PTS` x=−8.3) | **M2×22 self-tap** | `M2_CLEAR` 2.3 clear + Ø4.6→2.3 countersink through the printed floor | into servo case column | **floor 2.125mm MEASURED** (ray-cast, all 3 parts agree exactly; ~0.4mm under the nominal `FLOOR`=2.5 comment — real bay-cavity-cut boundary sits at z=−20.075, not the `FLOOR_TOP` reference) | ✅ confirms the existing "≥22" baseline |
| **case → HFE (femur) FAR pair** ×2 (`COL_PTS` x=−32.8, under the LA-6/`SUB_FLOOR` underside ramp) | **M2×25 self-tap** | same, but floor is ramped **4.4mm deeper** here (femur-local x=32.8) | into servo case column | **floor 6.525mm MEASURED** (+4.4mm vs the near pair — exact match to the ramp's own "rise 4.4" design note) | ✅ floor 6.525 + the ~19.9mm case-column depth = **26.4mm MAX** before bottoming → **M2×25** (18.5mm engagement, ≈ the near pair's 19.9). NOT M2×28 — that needs 21.5mm engagement, over-runs the ~19.9mm column and bottoms out; 28/26 aren't standard M2 sizes anyway. Column depth ASSUMED ~19.9mm (back-solved from the 22mm baseline at 2.125mm floor — internal to the servo, not measurable in our meshes) |
| **horn → HAA** ×4 (`shoulder_plate.scad`), **horn → KFE** ×4 (`knee_arm.scad`) | **M2.5×6** | `M25_CLEAR` 2.9 clear through `ARM_THK`=4.0, no head c'bore | into horn disc (~3.05mm, project's calipered figure — see note) | **grip 3.6mm MEASURED** (4.0 − 0.4mm `HORN_OD` locating-recess that spans the whole horn footprint) | ✅ 3.6+~2.5 target=6.15 → **round DOWN** to 6 (don't bottom out the 3.05mm disc) |
| **horn → HFE** ×4 (`coax.scad` inboard arm) | **M2.5×5** | same, but arm backs onto the HAA pocket cavity (LA-7: 3.2mm local budget, not the full 4.0mm `ARM_THK`) | into horn disc | **grip 2.8mm MEASURED** (3.2 local budget − 0.4mm recess; `ctr_deep=1.65` override on the center relief only) | ✅ 2.8+~2.5 target=5.35 → round DOWN to 5 |
| **wheel → HFE** ×4 (`coax.scad` outboard arm+boss), **wheel → KFE** ×4 (`femur.scad` own bottom arm+boss) | **M2.5×8** | `M25_CLEAR` 2.9 clear + Ø5.2 head c'bore (**1.6mm real depth**, measured — the shared `wheel_couple_neg()` cylinder is nominally 2.6 but 1.0mm of that is overcut margin below the true exterior) | into wheel disc (~2.1mm MEASURED directly off `servo.stl`, matches the ~2.15 doc figure) | **grip 7.25mm MEASURED** (identical at both joints — same shared module, no override) | ✅ 7.25+~1.7 target=8.95 → round DOWN to 8 (**thin: only ~0.75mm real engagement into the 2.1mm disc — tightest joint in this table**) |
| **wheel → HAA** ×4 (`shoulder.scad` wheel boss, long rear-wall→wheel-face reach) | **M2.5×14** | Ø5.2 head c'bore (**1.75mm measured**, code says 1.8) at the rear-wall exterior | into wheel disc | **grip 12.6mm MEASURED** (boss reaches 14.35mm total, far longer than the leg's own 4.85mm boss) | ✅ 12.6+~1.7 target=14.3 → round DOWN to 14 |
| **stock retention screw** (driven side only — HAA/HFE/KFE horns, NOT wheels) ×1/servo | **STOCK** (Ø5.4 head × ~1.5mm proud, factory-installed with the horn) | printed clearance only: `HORN_CTR_D` Ø6.5 blind c'bore, `HORN_CTR_DEEP` 2.5mm generic / **1.65mm at coax's inboard arm** (LA-7: floor 1.55mm, head margin 0.15mm — first-article check) | n/a | n/a | ✅ NOT sourced — comes with the servo/horn kit |

**Horn disc thickness note:** the wheel disc (~2.1mm) was confirmed by direct
ray-cast on `feetech_servo_models/converted_stl/servo.stl` (clean, unambiguous
flat face). The horn disc resisted the same clean read — cross-section slicing
showed a 4-lobed registration ring (r 5.75–10) rather than a simple flat disc,
so the horn engagement bound above uses the project's own CALIPERED figure
(~3.05mm, from the 35.5mm real disc-to-disc measurement, `leg_v6_common.scad`
rev-3) rather than a shakier mesh read of that specific feature.

**Stock vs source:** case screws are confirmed too short stock (already
documented). No verified stock M2.5 horn/wheel screw length was found in this
repo to compare against — every position above adds a 3.6–12.6mm printed
yoke arm/boss between the screw head and the disc that a stock (thin-arm,
direct-mount) screw isn't sized for; **source all 6 M2.5 lengths (5/6/8/14mm)
explicitly**, don't assume the servo kit's screws cover any of them.

**~~Open finding~~ CLOSED (re-checked 2026-07-26):** the phantom 5th "center
(wheel is M2.5)" clearance hole in the shared `wheel_couple_neg()` was already
removed under **#51 (2026-07-11)** — the module now cuts only the 4 BCD screws
plus the blind `WHEEL_CTR_D` idler-boss relief, so nothing is latent in
`coax.scad`'s HFE or `femur.scad`'s KFE wheel coupling. This paragraph was
stale, not the code. Still open elsewhere: `design-outline.md:95` ("4× M2.5 +
ctr") repeats the retired assumption.

**Head protrusion at the wheel BCD (noted 2026-07-26, first-article check):**
the Ø5.2 counterbore is **1.6 mm deep** (above) while an M2.5 SHCS head is
~2.5 mm tall, so each of those 8 heads per leg stands **~0.9 mm proud** of the
yoke bottom-arm / coax outboard-arm exterior. Both faces look into free air
(femur underside at the knee, coax outboard flank) and the sweep gates are run
against the STLs, which do not model heads — so this is a snag/scuff item, not
an interference one. Use low-head/button M2.5 if sourcing fresh, or accept it.

**cowl → upright ×2 (M2×10 SHCS + M2×4 insert, Ø5.5 c'bore)** — REMOVED
2026-07-10 (backlog #41): `jetson_cowl.scad` retired in place, superseded by
right-angle plug adapters (`BOM.md`). No cowl bolts/inserts to source.

## Purchase summary (chassis/head/electronics)
- **M3 SHCS**: ×4 **NYLON** M3×12 (head→bracket, breakaway), ×4 M3×12 (riser→flange), ×4 M3×16 (bracket→deck), ×2 M3×8 (adapter→crown), ×4 M3×10 (ears)
- **M3 CSK**: ×4 M3×10 (L2→adapter), ×4 M3×14 (shoulder flange feet → trunk floor, CR-8 #2), ×6 M3×10 (battery pocket → floor, AUD-11 heat-set fix — was ×6 M3×8 + M3 hex nut under AUD-1)
- **M3 nyloc**: ×4 (bracket→deck), ×4 (shoulder flange feet, w/ washer)
- **M2 SHCS**: ×4 M2×8 (pod), ×4 M2×8 (deck-tie), ×4 M2×8 (clamp bar), ×2 M2×8 (OLED bracket foot), ×4 M2×6 (SSD1331)
- **M2 nut**: ×4 (SSD1331)
- **Ruthex inserts**: M3×5.7 ×16 (head 4, ears 4, riser flange 4, + spares), M3×3.8 ×8 (adapter 2, battery pocket 6 — AUD-11 fix), M2×4 ×14 (pod 4, deck-tie 4, clamp bar 4, OLED-bracket-in-pod-deck 2)
- **E-stop**: HB2-ES544 (Ø22, owned)

## Purchase summary (leg_v6 servo screws, MEASURED 2026-07-11 — 12 active servos: 4 HAA + 4 HFE + 4 KFE)
- **M2 self-tap (case-mount)**: ×40 M2×22 (HAA×16 + KFE×16 + HFE-near×8), ×8 M2×25 (HFE-far pair only, ramped floor — longer to span the +4.4mm ramp; NOT longer than 25 or it bottoms the ~19.9mm column)
- **M2.5 (horn, driven side)**: ×32 M2.5×6 (HAA×16 + KFE×16), ×16 M2.5×5 (HFE, thinner LA-7 backing)
- **M2.5 (wheel, idler side, NO center screw)**: ×32 M2.5×8 (HFE×16 + KFE×16), ×16 M2.5×14 (HAA, long boss reach)
- Total 144 screws = 12/servo × 12 servos, self-consistent. Stock retention screw (×12, one per horn) is NOT sourced — factory-installed.
- Add ~10% spares per length given self-tap/plastic-thread wear risk (case) and the thin HFE/KFE wheel engagement margin.
