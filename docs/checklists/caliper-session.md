# Caliper Session

**STATUS 2026-07-10: nearly all closed 2026-07-07.** The bulk of this session
was done — numbers landed in `hardware/cad/dimensions.md` + the part files and
the geometry re-gated. What remains is the **servo SKU label read (#23)** plus
two minor D456 sub-items. Kept below as the record; ✅ = done, ⏳ = still open.

## 1. Jetson heatsink — ✅ MOOT (hood retired)
The hood this blocked was retired 2026-07-07 (Jetson now on the official-case
cradle). The case itself is calipered: **110.3 × 93.9 × 38.2** (dimensions.md;
cradle POST_TOP/corner columns measured 07-08, #33/#34). No bare-heatsink
measurement needed.

## 2. D456 camera — ✅ mostly done
- [x] Rear mount pattern — **2× M3, 94.4 apart** on the back-face centerline
      (±47.2, width-centered). The old "4× corner" guess was WRONG. Captured in
      `head.scad` MOUNT_Y=47.2 + dimensions.md (CALIPER 2026-07-07).
- [x] Body L×W×H — **123.8 × 26.0 × 29.0** (CALIPER 2026-07-07).
- [ ] ⏳ Thread depth of the 2× rear M3s (screw-length pick) — minor
- [ ] ⏳ Right-angle USB-C plug head L×W×H (must pass the 20-wide flange notch +
      plate window y2..19; also sizes the #41 USB-C adapter) — minor
- [ ] → `head.scad` MOUNT_SLOT + dimensions.md (d456_head.scad RETIRED)

## 3. Blue Sea 5191 MRBF block — ✅ DONE
- [x] Body **61.6 × 20.0 × 46.5**, terminal stud Ø7.8 → **M8** lugs (CALIPER
      2026-07-07).
- [x] Mount DECIDED: **external, assembly-time** (zip/bracket to the
      rear-shoulder exterior or trunk-rear at the battery-lead entry) — no
      captive spot fits it, so the `floor_plate.scad` 5191 slots were REMOVED
      07-07. Drives the #31 harness plan.

## 4. Battery pack — ✅ DONE
- [x] Real L×W×H **155.0 × 46.8 × 35.0** (width +0.8 vs the 46 listing; L/H
      matched). CALIPER 2026-07-07. `battery_pocket.scad` CLR tightened
      0.8→0.6/side → cavity re-cut, chassis gate re-run clean.
- [ ] ⏳ Lead + balance-connector exit geometry — confirm at harness dress (#31)

## 5. L2 leads — ✅ DONE (mast retired)
- [x] Mount pattern CONFIRMED from the manual (CR-1): 4× M3 on Ø51, depth 6.
- [x] Power barrel **3.5 × 1.35** (CALIPER 2026-07-07) → 12V L2 rail.
- [x] L2 data = **RJ45 ethernet** → Jetson `enP8p1s0` (via a switch; static
      IPs L2 192.168.1.62 / Jetson .2). Serial GH1.25-4Y unused.
- Note: the "mast bore" this once blocked is gone (l2_mast RETIRED; L2 now on
  the head crown via l2_adapter). RJ45 head size only matters for head/neck
  cable routing now — low priority.

## 6. SSD1331 OLED module — ⏳ OPEN, and it is what blocks the bracket (#35)

Added 2026-08-02. The display **is wanted**; it has nowhere to bolt. The 4 board
mount holes in `oled_mount.scad` were **removed 2026-07-28** because the vendor
drawing gives the outline (27.3 × 30.7) but **not the hole pitch on either
axis** — the guessed pitch put 2 of 4 holes inside the display window. The
bracket is deliberately unprintable until these come off the **owned** module:

- [ ] ⏳ hole pitch along the **27.3 mm** axis (centre-to-centre)
- [ ] ⏳ hole pitch along the **30.7 mm** axis (centre-to-centre)
- [ ] ⏳ active display area: **size AND its offset from the board datum** — the
      20 × 16 window currently in the file is carried over, **not** derived, so
      it is provisional even once the holes land
- [ ] → `oled_mount.scad` (holes + window), then `slice_plate.py`'s UNRESOLVED
      entry can move to the registry with a material and an axis

Everything else in the chain is already built: `control_pod` bolts to the
`riser_bay` pocket-bosses (4× M3, y±10, z61/66, x−66.5), the bracket bolts to
the pod deck's 2× M2 heat-sets (x−96/−71, y23), and the logic board carries
`J10` plus the `R2`–`R6` 1k series resistors. Three numbers, one caliper.

## Same bench session (not caliper)
- [ ] ⏳ **Servo SKU audit (#23)** — read all 12 + spare labels: 7.4V vs 12V
      SKU. LABEL hips vs legs physically. (+58% knee-torque question.) **← the
      one real open bench item.**
- [ ] ⏳ Jetson SMA/U.FL pigtail reach to the ear bulkhead positions — gated on
      the #32 WiFi bench-range test (decides if the ears become antenna masts).
- [ ] ⏳ Filament stock check: PA6-CF ~1.5 kg, PETG-CF ~0.6 kg, TPU ~100 g
      (PETG-CF now needed for riser/floor/head-brackets per #24).

## Possibly stale (check then close)
- [x] ~~femur-knee-fix memory~~ — leg_v5-era, superseded by the leg_v6
      knee_arm redesign; memory deleted 2026-07-06.
