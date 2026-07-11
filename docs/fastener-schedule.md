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
