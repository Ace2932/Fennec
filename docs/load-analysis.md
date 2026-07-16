# Structural Load Analysis — full assembly (2026-07-06)

Hand-calc audit of every printed load path at assembly level, run after the
shoulder rev4 joint fixes (flange floor feet + deck gussets) and the tibia
toe_v2 seat. Leg-internal members (pockets, discs, yokes) were sized in
`~/claude-memory/nova-proj/project-leg-v6-design.md` and are unchanged;
this doc covers the **chassis-level joints** the connectivity audit and the
user flagged.

> **Servo-pocket retention (2026-07-07, user flag):** the one leg-internal item
> this doc had skipped — now checked in `hardware/cad/leg_v6/servo_pocket_analysis.py`.
> Statically fine (floor bearing SF 11–18 at stall; landing bypasses the pocket
> via the joint discs). The real weakness was **retention, not strength**: the
> joint torque rode 4× M2 self-tap in the servo's plastic (0.45 slip, no anti-
> rotation) → cyclic loosening over trot life. FIXED — **anti-rotation crush
> ribs** on the ±Y case flats (`sts_pocket_neg`, all 3 joints) move the torque
> to wall bearing (**SF ~570** @ 12 V stall), leaving the screws axial-only.

> **Mass refresh (2026-07-16):** the 4.2 kg / 41 N figure below was a stale
> pre-build budget number. `hardware/cad/chassis/mass_model.py` (itemized,
> CoM-tracking model) gives **3898 g / 38.2 N** — confirmed by re-running it.
> The old figure was ~8% conservative (heavy), so it only ever over-stated
> static/standing loads; every SF in this doc computed from the mass (not
> from the fixed 60 N/41 N *doctrine* worst-case loads, which are unchanged)
> gets slightly BETTER, not worse. Not recomputed section-by-section — only
> the mass-derived figures in the Load cases table below are updated.

## Load cases

| Case | Value | Basis |
|---|---|---|
| Robot mass | ~3.9 kg → W = 38.2 N | `hardware/cad/chassis/mass_model.py` (re-run 2026-07-16: 3898 g; supersedes the stale 4.2 kg/41 N budget figure below) |
| Static stand (4 legs) | 9.6 N/leg | W/4 |
| Trot (2-leg support, ×2 dynamic) | ~41 N/leg | doctrine |
| Landing peak, single leg | **60 N** | leg_v6 doctrine worst case |
| Braking/faceplant decel | 2 g horizontal | assumption |
| Material | PA6-CF: 151 MPa flex dry, ~75 wet; Z-layers ×0.6 | Bambu TDS |

## 1. Shoulder ↔ trunk joint (the rev4 fix)

Geometry: C-box carries both hips 77.7 mm fore of the trunk end face.
Fasteners: 4× M3 into flange heat-sets at (±51.75, z 5/24 trunk), only a
19 mm couple — **pre-fix this was the whole joint**. Rev4 adds 2 floor
feet per end (M3×14 csk from below at (±59.5, ±42)) + 2 deck gussets.

| Load | Path & number | Margin |
|---|---|---|
| Forward tip (60 N landing, one leg): M = 60 × 77.7 = **4.66 N·m** | tension in the 2 upper flange bolts, arm 24 mm above the compression edge → **97 N/bolt**; parallel path: 2 riser hold-down screws at z 67.4 trunk (arm ~63) → the riser lid becomes a tension tie between the two shoulders | insert pullout (4 mm engagement, PA6-CF) ≈ 250–350 N → **SF ≥ 2.5** on bolts alone; riser path redundant |
| Reverse tip (braking): same 4.66 N·m opposite | **foot bolts** in tension, arm 75.5 mm (foot z −34 → flange top) → **31 N/bolt** | M3 + csk head bearing in the stock floor ≈ 1 MPa → SF > 20 even in PLA |
| Vertical shear 120 N/end (both legs trot) | flange face bearing on the wall ends (~1100 mm²) + feet on the floor (~145 mm²/pad) | < 0.5 MPa bearing → SF > 100 |
| Yaw twist (36 N lateral scrub at a foot): T ≈ 2.8 N·m | feet pair 84 mm apart + flange bolt group 103.5 wide | ~33 N per foot bolt → SF > 10 |
| Joint rocking / fretting | feet clamp closes the hinge; gussets kill deck-strip flutter | stiffness fix, not strength |

**Verdict: passes with the feet; the pre-fix joint also passed statically
(97 N/bolt) but had a single load path, low couple height, and would rock
under trot cyclic loads. Now triangulated + redundant.**

## 2. Shoulder box members

| Member | Load | Stress | SF (dry) |
|---|---|---|---|
| 2 shear webs 4×66.5 | 4.66 N·m bending | 0.8 MPa | ~190 |
| deck strips 33.4×6.5 ×2 + gussets | share of same | < 1 MPa | > 150 |
| box torsion (yaw 2.8 N·m) | closed-ish section | < 2 MPa shear | > 30 |

## 3. HAA joint (leg ↔ shoulder)

Roll moment 60 N × 64.3 mm (IK d) = 3.86 N·m → couple across the
horn-plate (+17.75) / wheel-boss (−17.75) planes, 35.5 apart (reconciled
2026-07-10 to the calipered disc-to-disc — was +17.2/−17.7, 34.9 apart) →
**~109 N** per face (was 111 N; ~1.7% change, negligible).

| Element | Number | Margin |
|---|---|---|
| horn plate 4× M3 deck inserts | 28 N/screw tension | pullout ~400 N (6.5 deck) → SF 14 |
| Ø19 wheel boss shear | 0.4 MPa | SF ≫ 100 |
| 4× M2.5 wheel screws | 28 N shear each | SF > 50 |

## 4. Tibia toe_v2 / shoe

| Element | Number | Margin |
|---|---|---|
| tread → seat disc bearing (60 N) | ~0.6 MPa on the r12.35 disc | SF ≫ 100; TPU crush is the soft element, by design |
| blade torsion from the 30.5 jog | 1.83 N·m → τ ≈ 1.6 MPa at the blade neck | SF ~45 |
| angled web (sector-clipped rev) | 60 N shear through ≥ half-disc section | < 1 MPa → clip cost negligible |

## 5. Masts (flagged "hanging" items — verified fine for operating loads)

| Item | Load (2–4 g inertial) | At the mount | Margin |
|---|---|---|---|
| D456 periscope (~75 g, arm ~30) | 3 N → 0.09 N·m | 4× M3 bracket | SF > 50 |
| L2 mast (~230 g, arm ~80) | 9 N → 0.72 N·m | riser-deck flange screws ~24 N each | SF > 15 |

⚠ **Faceplant is the unbounded case for both masts** — a fall onto the
camera or LiDAR exceeds any printed mount. That is a *policy* limit
(E-stop/limp behavior, handle with care), not a sizing one. Do not
stiffen further; a breakaway mount that shears before the sensor does is
the better failure mode.

## 6. Stock trunk shell (⚠ material unknown)

All shell-side stresses land < 1 MPa (bearing at wall ends, floor under
the feet, csk heads, bolt holes) → fine even in PLA. Actions:
- washers under every shell-side head (spread load into the print)
- when the shell is eventually reprinted, PA6-CF or PETG-CF; until then
  no static concern, watch the wall-end bearing for creep marks at the
  first teardown.

## 7. Coax HFE cap — femur horn joint (leg ↔ femur, `coax_hfe_plate.scad` #67, first-article check)

The #67 fix (`hardware/cad/leg_v6/coax_hfe_plate.scad`, `hardware/cad/leg_v6/coax.scad`)
split the coax's femur-yoke horn arm into an INTEGRAL stub (most of the old
disc) + a small removable CAP (just the measured femur-swept wedge) that
carries all 4 horn BCD bolts plus a single M3 heat-set clamp. Both files'
own headers flag it "first-article load check, same as #53" with **no
safety factor established anywhere** — this section closes that gap.

**Load case.** No HFE-specific moment existed anywhere in this doc yet.
Deriving it the same way Section 3 derives HAA's roll moment (60 N landing
peak × a moment arm, per the Load-cases table above): using the locked
kinematics in `leg_v6_common.scad` ("femur 106.9 · tibia 129.0"), arm =
femur + tibia = 106.9 + 129.0 = 235.9 mm →

**M_HFE = 60 N × 0.2359 m ≈ 14.2 N·m**

— which matches the dynamic hip moment already used elsewhere for the
femur slab's own bending check, so this isn't a new load assumption, just
the first time it's applied to this specific joint.

**Geometry (from the .scad, real variable names):**
- Horn seat: `HORN_SEAT = ARM_IN_X1 = FEMUR_MID - HORN_Z1 = 33.8 - 17.75 = 16.05`
- Femur's own wheel-disc contact face: `FEMUR_MID + |WHEEL_Z0| = 33.8 + 17.75 = 51.55`
- Horn↔wheel spacing (same couple method as Section 3's HAA joint):
  `S = 51.55 - 16.05 = 35.5 mm` — the same STS3215 disc-to-disc spacing
  calipered there.
- Cap front-band thickness actually backing the horn bolts:
  `HORN_SEAT - STUB_FRONTX0 = 16.05 - 14.9 = 1.15 mm` — **not** the 3.15 mm
  figure both files' headers quote (`PLATE_X0..ARM_IN_X1 = 12.9..16.05`),
  which is the OLD #53 full-disc span. Post-#67 the stub only reaches
  `STUB_FRONTX0 = 14.9`; the front-band (14.9→16.05) is 100% cap material.
  `coax_hfe_plate.scad`'s own HORN COUPLING note confirms the two "low"
  bolts (y=6.65, below `STUB_MIDY0=7.0`) get zero contribution from the
  mid-band cap addition — 1.15 mm is the true governing section there.
- M3 clamp: single Ruthex M3 heat-set (`HEATSET_D=4.0`, `HEATSET_L=6.2` →
  5.7 mm insert engagement), bored from the bridge's open rear tip
  (`EAR_Y1=27.6`) into the BRIDGE (46 mm deep in Y).

**Method:** couple force at the horn face, same as Section 3:
F_face = M_HFE / S = 14.2 / 0.0355 = **400 N**; 4× M2.5 BCD bolts share it
→ **100 N/bolt**.

| # | Element | Load | Stress | SF dry | SF wet | Verdict |
|---|---|---|---|---|---|---|
| 7a | Horn BCD bearing, 4× M2.5 through the 1.15mm cap front-band (`M25_CLEAR=2.9` dia hole × t=1.15) | 100 N/bolt | 100/(2.9×1.15) = **30.0 MPa** | 151/30.0 = **5.0** | 75/30.0 = **2.5** | **MARGINAL — exactly on the 2.5 floor**, zero spare for hole stress concentration or the thin (~6-layer) section; first-article-verify |
| 7b | M3 clamp, nominal path (shape-key faces react the moment in compression; bolt = retention/anti-spin only, per both files' own LOAD SPLIT note) | preload only | — | high | high | OK *if* the shape-key really carries it |
| 7c | M3 clamp, worst-case bound (the shape-key contact is a `CLR=0.2` **slip fit** — compression-only, cannot react a tension/peel component; if it doesn't, the single M3 bolt alone reacts the full face force) | F = 400 N tension | pullout, scaled from Section 1's own 4mm-engagement 250–350 N figure to this cap's 5.7mm engagement: 250×(5.7/4)=356 N .. 350×(5.7/4)=499 N | 356/400 = **0.89** | (356×0.497)/400 = **0.44** | **FAILS — dry SF <1 outright, wet worse. No redundancy: this is the ONLY fastener holding the cap on.** |
| 7d | Stub/cap split-line, compression-side shape-key bearing (mid-band walls + front-band r=15.8 cylindrical wall, both `CLR=0.2` shrunk contacts) | 400 N over a ~28.8mm² representative contact patch | ≈13.9 MPa | 10.9 | 5.4 | OK — not the limiting path |

**Verdict: two of four items pass with real margin (7b/7d); the other two
are the finding here.** 7a lands exactly on the 2.5 floor even before
accounting for the hole's own stress concentration or the fact that the
1.15mm section is only ~6 print layers thick. 7c — the single M3 clamp
bolt, under the conservative-but-plausible assumption that the slip-fit
shape key can't react the tension side of the couple — **fails outright,
dry or wet**. The cap has **zero redundant fastening**: if the shape-key's
compression-only contact doesn't fully carry the "far side" of the moment
the header describes, this joint depends on one M3 heat-set with no
margin at all. ⚠ **Per instructions this is flagged, not redesigned.**
Recommend a bench first-article load test to confirm the shape-key really
does react the moment (7b's assumption needs to be verified, not just
plausible) before trusting this joint at trot loads.

## Standing risks / follow-ups

1. Flange heat-sets: 6.2 bore in a 4-thick flange breaks through; inserts
   hold on ~4 mm. Fine at 97 N (SF ≥ 2.5) but if one spins at assembly,
   fall back to M3 through-bolt + nyloc (aperture access exists).
2. Riser is now a *documented secondary* tension tie (was "never
   structural") — primary path (flange bolts + feet) passes alone; do not
   remove the riser and trot.
3. L2 mast resonance: tall mast + 2 Hz trot — check for wobble at
   bring-up before trusting point clouds; add a damping pad if visible.
4. First assembly: drill the 4 foot holes (±59.5, ±42) with the
   floor_plate template (added to its 10-hole pattern job).
5. ⚠ **Coax HFE cap (Section 7): SF below the 2.5 floor** — the horn-bolt
   bearing is marginal wet (SF 2.5) and the single M3 clamp bolt fails
   outright under a worst-case (but plausible) load-path assumption (SF
   0.44–0.89). No safety factor existed for this joint before this audit.
   Needs a bench first-article load test before trusting it at trot loads;
   not redesigned here per instructions.
