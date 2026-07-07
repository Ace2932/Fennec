# Caliper Session (critical path — unblocks hood, E-stop pod, D456 print, floor plate, harness plan)

One evening, calipers + the real parts. Every number lands in
`hardware/cad/dimensions.md` (new/updated rows) and the named part file.

## 1. Jetson heatsink (blocks: hood → E-stop pod)
- [ ] Heatsink TOP height above the carrier board plane (dimensions.md
      says 21.5 ⚠ REVIEW; hood + L2-overhang clearance math uses it)
- [ ] Fan housing outline (x/y) + cable exit side
- [ ] → `dimensions.md` Jetson row; then hood design + E-stop pod ride

## 2. D456 camera (blocks: d456_head print)
- [ ] Rear-panel 4× M3 pattern: exact x/y centers (docs guess slots at
      y ±54, rows z 84-91 / 94-99 — "expect to touch these")
- [ ] Thread depth of the rear M3s (screw length pick)
- [ ] Right-angle USB-C plug head: L × W × H (must pass the 20-wide
      flange notch + plate window y 2..19)
- [ ] → `d456_head.scad` SLOT_Y / SLOT_ROWS + dimensions.md

## 3. Blue Sea 5191 MRBF block (blocks: floor_plate slots, harness plan)
- [ ] Base footprint + mounting hole pattern + stud height w/ fuse
- [ ] Ring-terminal lead exit directions (drives the internal harness
      plan, backlog #31)
- [ ] → `floor_plate.scad` 5191 slots + dimensions.md

## 4. Battery pack (blocks: pocket clearance confidence, #29 chafe gap)
- [ ] Real L × W × H incl. shrink-wrap bulge (listing 155×46×35; cavity
      cut at +0.8/side — re-gate if fatter)
- [ ] Lead + balance-connector exit geometry (rear-notch fit; balance
      lead stowage decision)
- [ ] → dimensions.md pack row; `battery_pocket.scad` CLR if needed

## 5. L2 pigtail plugs (blocks: mast bore confidence)
- [ ] RJ45 plug head W × H (claim 11.7 × 8 — mast bore is 13 × 11)
- [ ] DC barrel plug Ø + length (claim ~Ø10)
- [ ] → dimensions.md L2 row; `l2_mast.scad` BORE if needed

## Same bench session (not caliper)
- [ ] Servo SKU audit (#23): read all 12 + spare labels — 7.4 V vs 12 V
      SKU. LABEL hips vs legs physically. (+58% knee torque question)
- [ ] Jetson SMA/U.FL pigtail reach to the riser bulkhead positions
      (−15/+25, +44) — verify on the real board
- [ ] Filament stock check: PA6-CF ~1.5 kg, PETG-CF ~0.6 kg, TPU ~100 g

## Possibly stale (check then close)
- [ ] memory `project-femur-knee-fix` says "blocked on caliper gap
      measurement" (STS3215 spacer bosses) — predates the leg_v6 rev2
      knee; confirm superseded and close the memory item
