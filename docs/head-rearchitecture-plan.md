# Head Re-architecture — NEXT SESSION (planned 2026-07-07)

The current integrated head (`chassis/head.scad`) mounts to the RISER FRONT
— it perches on the body's top-front and reads as a turret, not a head.
**User call: the head should rest FORWARD on the FRONT SHOULDERS (neck),
projecting ahead like a real fox.** The front hips are at x±141, ~78 mm
forward of the trunk front (x63.5), so the front shoulders cantilever
forward — that's the "neck" the head sits on.

## Feasibility — DONE, it works
Front shoulder spans world **x54..158, z0..80**. A head mounted on its top
and projecting forward+up into **x110..175, z82..170** gets **0 front-leg
hits** across the full ROM (front hfe −50..+50, kfe ±109, inboard-haa ≤15).
Three candidate envelopes all clear (over-shoulder / fwd-neck / tall-neck).
So the anatomically-right forward position is available.

## Implications to handle in the rebuild
1. **Mount → shoulder** (frees the riser front interface). DECISION on the
   interface: **separate NECK BRACKET** (recommended — bolts to the front
   shoulder's existing top holes, keeps the shoulder one gate-clean part,
   head stays a modular removable unit for fennec iteration) vs front-
   specific shoulder variant (stiffest, but breaks print-2-identical +
   re-gates the complex shoulder). ⚠ user still weighing these two — CONFIRM
   before building.
2. **CoM shifts forward** ~50-75 mm of the head mass (L2 230g + D456 72g +
   structure ≈ 400 g). Meaningful — plan to nudge the belly battery rearward
   to rebalance, or accept front-loading. Report the CoM delta.
3. **Cantilever stiffness** — heavier head forward on a neck must not
   vibrate (L2 scan). Wide bolt pattern at the neck base; if a bolted
   bracket, that joint is the weak point.
4. **Re-gate everything**: head vs front-leg sweep at the new position, L2
   360° ring, D456 near-ground view, CoM. Regenerate previews.
5. **Fennec styling redone at the new position** — anatomy LOCKED (see below).

## Fennec anatomy (LOCKED, user calls)
- **L2 = forehead / skull crown** (stays high for 360° mapping — do NOT make
  it a forward muzzle; that kills its mapping vantage + shifts CoM).
- **D456 = eyes** — wide band across the face (its 123.8 length horizontal,
  the two stereo lenses = eyes), tilted down to watch the ground.
- **Ears** = big broad triangles (currently thin blades — BROADEN them),
  house the SMA antennas. Rooted BEHIND the L2 (rear skull shelf) so they
  touch only the blind rear LiDAR sector; side-mount would cost side sectors.
- **NO projecting snout** at the current position (shoulder deck-ext + legs
  box it in) — but on a FORWARD shoulder-mounted head there may finally be
  room below/forward for a proper pointed muzzle; re-check.
- Style TODO: broaden ears, shroud the L2 into a faceted skull, accent the
  D456 lenses as eyes, add a nose/snout if the forward position allows.

## Start-here checklist next session
- [x] Confirm neck-bracket vs shoulder-variant → **NECK BRACKET** (user, 07-07)
- [x] Build the neck/head on the front shoulder top → `neck_bracket.scad` +
      reworked `head.scad`; sensors shifted **DX+73 DZ+6** (`forward_head_study.py`)
- [x] Move D456 + L2 onto it → D456 back-face (143,0,111.5) 27° down; L2 crown
      x126.5, optical z~160. Tilted-eye + crown mounts kept.
- [x] Re-gate → `check_fit.py` PASSES (exit 0). **0 front-leg hits** vs
      head/bracket/camera across the full ROM sweep. The front-hfe −50 cap
      still holds (now conservative — could relax; deferred to the leg-ROM lane).
- [x] CoM delta → **+6.5 mm forward** (L2 230 g x53.5→126.5 dominates; head
      struct MEASURED ~35 g) → ~54 mm rearward on the belly battery nulls THIS
      DELTA (pack = 510 g CALIPERED, BOM "510 g rattle"; the study's old 300 g
      was wrong). NB the ABSOLUTE CoM is ~+12 mm fwd — see the battery note
      below; a full mass model is the right tool.
- [x] Retire the riser front head interface (user: RETIRE NOW, keep SMA) —
      removed the L2-column deck base + bores + L2 cable drop + front-wall
      camera register + USB-C grommet from `riser_bay.scad`; SMA kept. Riser
      re-gated (exit 0), watertight.
- [x] Fennec styling FIRST PASS (user: REARWARD SKULL SHELF ears) — STYLE=true
      now GATE-CLEAN: broad triangular ears root on a rear skull shelf BEHIND
      the L2 (x<89), splay outward, house the SMA antennas; clear the seated L2
      + 0 leg hits. **STILL TODO** (touch sensor FoV → need the L2 ring / D456
      down-cone gate): L2 skull shroud, D456 eye-band accent, pointed snout.
- All parts gate-clean (chassis + leg_v6 exit 0), watertight. Previews +
  renders regenerated. `forward_head_study.py` = the placement proof.
