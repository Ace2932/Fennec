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
the LIGHT, pinched mounts (cradle clamps + deck-ties, cowl, control-pod) to **M2**
(1.0–1.4mm wall in the 6mm posts, huge load margin); short M3×3.8 inserts where a
part is <6mm. All insert walls now pass.

## Schedule

| Connection | Screw (std) | Hole / insert | Engage | Wall | Status |
|---|---|---|---|---|---|
| **head → neck bracket** ×4 | M3×12 SHCS | rear c'bore Ø6.5×3 + wall clear Ø3.4; **M3×5.7 insert** in the head boss (HM_Y=10, centered bore↔edge) | 5.7 | 1.7–2.2 | ✅ |
| **neck bracket → deck** ×4 | M3×16 SHCS + **M3 nyloc** | drill-at-assembly Ø3.4 through base+deck, nut below | nut | n/a | ✅ (rear pair driver-tight — socket) |
| **L2 → l2_adapter** ×4 | M3×10 **CSK** (90° flat) | adapter CSK Ø6.2→3.4; into the **Unitree L2 base M3 threads** | ~5 | n/a | ✅ ⚠ confirm L2 base is M3-threaded at bench |
| **l2_adapter → crown** ×2 | M3×8 SHCS (from below) | crown clear Ø3.4; **M3×3.8 SHORT insert** in the 5mm adapter (L2 sits on top, can't boss up) | 3.8 | ≥1.5 | ✅ (relocated 114,±9 clear of the L2 CSK) |
| **ears → head pad** ×4 (2/ear) | M3×10 SHCS | ear-foot clear Ø3.4; **M3×5.7 insert** in the pad (pad rear extended x71 for wall) | 5.7 | 1.7 | ✅ |
| **riser → shoulder flange** ×4 | M3×12 SHCS | flange clear; **M3×5.7 insert** in the riser end-wall pad (pressed inner) | 5.7 | ok | ✅ (pre-audited 2026-07-06) |
| **control_pod → riser** ×4 | **M2×8** SHCS | pod column clear Ø2.3; **M2×4 insert** in the riser pocket-pad (pad y widened ±14) | 4.0 | ≥1.0 | ✅ (light mount; pinched pad → M2) |
| **cradle → deck (tie)** ×4 | **M2×8** SHCS (from below) | riser deck clear Ø2.3; **M2×4 insert** in the upright base | 4.0 | 1.4 | ✅ (6mm post → M2; huge margin) |
| **case clamp → upright** ×4 | **M2×8** SHCS | clamp clear Ø2.3; **M2×4 insert** in the upright top; clamp bears the case corner | 4.0 | 1.4 | ✅ |
| **cowl → upright** ×2 | **M2×10** SHCS | cowl end-wall Ø5.5 c'bore + Ø2.3 shank; **M2×4 insert** in the upright −y face | 4.0 | 1.4 | ✅ (c'bore avoids a silly M2×25) |
| **OLED → pod panel** ×4 | M2×6 SHCS + **M2 nut** | pod panel clear Ø2.3; SSD1331 PCB behind, nut on the +x side | nut | n/a | ✅ |
| **E-stop** ×1 | mxuteuk 22mm 2NC **Ø22 barrel + supplied nut** | Ø22.6 deck hole; Ø40 mushroom; 77mm total; **panel max 6mm** (deck 5 ✓); ~30×30×48 block below (pod gussets flank it y±17) | — | — | ✅ verified vs the Amazon part 2026-07-08 |

leg_v6 fasteners (coax/femur/tibia/shoulder/horn/wheel/foot) were audited
2026-07-06 (memory: heat-set insert notes) — M3/M2.5/M2 clearances + Ruthex M3
bores, all standard; not re-listed here.

## Purchase summary (chassis/head/electronics)
- **M3 SHCS**: ×8 M3×12 (head→bracket 4, riser→flange 4), ×4 M3×16 (bracket→deck), ×2 M3×8 (adapter→crown), ×4 M3×10 (ears)
- **M3 CSK**: ×4 M3×10 (L2→adapter)
- **M3 nyloc**: ×4 (bracket→deck)
- **M2 SHCS**: ×4 M2×8 (pod), ×4 M2×8 (deck-tie), ×4 M2×8 (clamp), ×2 M2×10 (cowl), ×4 M2×6 (OLED)
- **M2 nut**: ×4 (OLED)
- **Ruthex inserts**: M3×5.7 ×16 (head 4, ears 4, riser flange 4, + spares), M3×3.8 ×2 (adapter), M2×4 ×14 (pod 4, deck-tie 4, clamp 4, cowl 2)
- **E-stop**: HB2-ES544 (Ø22, owned)
