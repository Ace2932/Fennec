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

## 7. Coax HFE cap — femur horn joint (leg ↔ femur, `coax_hfe_plate.scad` #67/#7-fix)

The #67 fix (`hardware/cad/leg_v6/coax_hfe_plate.scad`, `hardware/cad/leg_v6/coax.scad`)
split the coax's femur-yoke horn arm into an INTEGRAL stub (most of the old
disc) + a small removable CAP (just the measured femur-swept wedge) that
carries all 4 horn BCD bolts plus a single M3 heat-set clamp. Both files'
own headers flag it "first-article load check, same as #53" with **no
safety factor established anywhere** — this section closed that gap
(2026-07-16 first pass) and found two failing cases (7a marginal, 7c
FAILS); the **#7-fix** (same date, below) reworks the joint to close both.
Old→new numbers are shown per case in the table.

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
- Cap front-band thickness actually backing the horn bolts (pre-fix):
  `HORN_SEAT - STUB_FRONTX0 = 16.05 - 14.9 = 1.15 mm` — **not** the 3.15 mm
  figure both files' headers used to quote (`PLATE_X0..ARM_IN_X1 =
  12.9..16.05`), which is the OLD #53 full-disc span (both headers now say
  so explicitly, 2026-07-16). Post-#67 the stub only reached
  `STUB_FRONTX0 = 14.9`; the front-band (14.9→16.05) was 100% cap material.
  `coax_hfe_plate.scad`'s own HORN COUPLING note confirms the two "low"
  bolts (y=6.65, below `STUB_MIDY0=7.0`) got zero contribution from the
  mid-band cap addition — 1.15 mm was the true governing section there
  (in fact ALL 4 bolts sit outside the mid-band box's z-span too, so all 4
  were equally thin — MEASURED via direct trimesh probe of the built STLs).
- M3 clamp: single Ruthex M3 heat-set (`HEATSET_D=4.0`, `HEATSET_L=6.2` →
  5.7 mm insert engagement), bored from the bridge's open rear tip
  (`EAR_Y1=27.6`) into the BRIDGE (46 mm deep in Y). Unchanged by the
  #7-fix — it keeps its originally-intended retention/anti-spin role.

**#7-fix (2026-07-16):** two NEW standalone bearing/engagement bands
(`BAND_*` in both `.scad` files, cut in `coax_hfe_bore()`, filled in
`coax_hfe_cap_body()`) — same x-column as the existing mid-band bore
(13.3..14.9mm), bracketing the horn-bolt BCD circle in Z (`BAND_LO_Z
-17.0..-12.6`, `BAND_HI_Z -6.3..-2.0`, both with ≥0.5mm margin off the
mid-band bore's own MEASURED swept z-limits, -12.1/-6.8 — re-verified via a
direct trimesh probe of the rebuilt STLs that none of the 4 bolt positions
(z=-4.55/-14.45) fall inside the actually-swept region, so neither band
reopens the femur insertion clearance). Two effects, both closing §7
findings at once:
1. **Thickens 7a.** The cap's independent material at every bolt grows
   from front-band-alone (1.15mm) to front-band + band (1.15+1.6 =
   **2.75mm**).
2. **Closes 7c.** Unlike the mid-band box (whose Z1/X1 faces are
   flush/internal unions into the riser/front-band, i.e. NOT stub-facing —
   a +Z peel had no compression path there at all), these new bands are
   shrunk (`CLR_KEY=0.15`) on **all four** side walls (Y0,Y1,Z0,Z1) — only
   X1 is flush. That gives the cap genuine closed engagement against the
   stub in both +Z and −Z, right at the load application point (near-zero
   lever arm to the bolt circle), so the worst-case "single bolt reacts
   the whole peel" assumption no longer holds structurally.

**Method:** couple force at the horn face, same as Section 3:
F_face = M_HFE / S = 14.2 / 0.0355 = **400 N**; 4× M2.5 BCD bolts share it
→ **100 N/bolt**. (Unchanged by the #7-fix — same load case, reworked
load path.)

| # | Element | Load | Stress | SF dry (old→new) | SF wet (old→new) | Verdict |
|---|---|---|---|---|---|---|
| 7a | Horn BCD bearing, 4× M2.5 through the cap front-band (`M25_CLEAR=2.9` dia hole × t) — **t: 1.15mm → 2.75mm** (front-band 1.15 + new band 1.6) | 100 N/bolt | 100/(2.9×1.15)=30.0 MPa → 100/(2.9×2.75)=**12.5 MPa** | 5.0 → **12.0** | 2.5 → **6.0** | **FIXED — was marginal (exactly on the floor), now 2.4× the 2.5 floor** |
| 7b | M3 clamp, nominal path (shape-key faces react the moment in compression; bolt = retention/anti-spin only) | preload only | — | high | high | OK, unchanged — bolt keeps its originally-intended role |
| 7c | M3 clamp / band engagement, worst-case bound — **was**: slip-fit shape-key assumed compression-only (can't react peel) → single M3 bolt alone reacts 400N. **now**: the new bands' Z0/Z1 walls give a genuine closed (both-direction) compression path AT the bolt circle; worst-case single-wall bearing area ≈ 1.6mm(X) × 17mm(Y) = 27.2mm² | F = 400 N | pullout(old) 356N/400N=0.89 dry, 0.44 wet → bearing(new) 400/27.2=**14.7 MPa** | 0.89 → **10.3** | 0.44 → **5.1** | **FIXED — was FAILS outright, now clears the floor with 2× spare; M3 bolt no longer the sole path** |
| 7d | Stub/cap split-line, compression-side shape-key bearing (mid-band walls + front-band r=15.8 cylindrical wall, both `CLR`/`CLR_KEY` shrunk contacts) | 400 N over a ~28.8mm² representative contact patch | ≈13.9 MPa | 10.9 | 5.4 | OK, unchanged — still not the limiting path; now further redundant with the new bands' own compression walls |

**Verdict: all four cases now clear SF ≥ 2.5 wet, with a genuinely
redundant load path.** 7a's independent cap section more than doubled
(1.15→2.75mm), taking horn-bolt bearing from exactly-on-the-floor (2.5) to
2.4× the floor (6.0) wet. 7c's fix is the more important one structurally:
the previous design had **zero redundant fastening** — a single M3
heat-set was the only thing holding the cap on if the shape-key's
compression-only slip fit couldn't react the couple's tension side. The
new bands give the cap a **closed, measured, both-direction** engagement
(not an assumption) directly at the bolt circle, so the M3 bolt is back to
its originally-documented role (retention/anti-spin, 7b) instead of being
a single point of failure. No interference/press fit was needed — the fix
is a second, independently-clearance-verified slip-fit key with a real
mechanical stop in the direction (Z) the old design left completely open.
Cheapest-viable per the brief: no added fastener, no change to the
assembly sequence (cap still slides on after the femur is seated, same M3
draw-up), stays within the existing 1.5mm print-margin floor (2.75mm >
1.5mm), and the servo-insertion/horn-bolt-driver gates (`check_fit.py
--sweep`) all stayed green after the rebuild (see the build log; no gate
constants needed changing — bolt positions, cap outline reference points,
and the insertion envelope were unaffected by this fix).

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
5. ✅ **Coax HFE cap (Section 7): #7-fix closed the SF gap (2026-07-16)** —
   the horn-bolt bearing was marginal wet (SF 2.5, exactly on the floor)
   and the single M3 clamp bolt failed outright under a worst-case (but
   plausible) load-path assumption (SF 0.44–0.89). Reworked with two new
   standalone bearing/engagement bands (`BAND_*`, both `.scad` files) —
   all four §7 cases now clear SF ≥ 2.5 wet (7a → 6.0, 7c → 5.1), with a
   genuinely redundant (not single-fastener) load path. `check_fit.py
   --sweep` reruns green post-rebuild. Still recommend a bench first-
   article load test at final assembly to confirm as-printed behavior
   matches the hand-calc (standard practice for any first-article joint,
   not a flag specific to this fix).
