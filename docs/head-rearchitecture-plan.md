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
- [ ] Confirm neck-bracket vs shoulder-variant (user)
- [ ] Build the neck/head at x110..175 z82..170 on the front shoulder top
- [ ] Move D456 + L2 onto it (keep the tilted-eye + crown mounts)
- [ ] Re-gate (chassis check_fit: head-vs-front-leg, L2 ring, CoM); the
      front-hfe −50 cap likely still applies — re-verify at the new x
- [ ] CoM delta + battery-rebalance recommendation
- [ ] Retire/rework the riser front head interface (now unused)
- [ ] Fennec styling pass (broad ears + L2 skull + eye accent + maybe snout)
- [ ] The current `head.scad` (riser-mounted) stays gate-clean until replaced
