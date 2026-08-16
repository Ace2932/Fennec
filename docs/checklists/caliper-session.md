# Caliper Session

**SESSION 1 (2026-07-07) — closed.** Numbers landed in
`hardware/cad/dimensions.md` + the part files and the geometry was re-gated.
Only the **servo SKU label read (#23)** and two minor D456 sub-items remain.
Kept below as the record; ✅ = done, ⏳ = still open.

**SESSION 2 (opened 2026-08-15) — the panel controls. See below, it is first
because it is what is currently blocking.**

---

# SESSION 2 — panel controls + bucks (2026-08-15)

Four measurements, one bench trip. Each one blocks a specific CAD rev; nothing
here is nice-to-have.

## S2-1. SW1 Contura rocker — BODY DEPTH ⬜ **the single most valuable number**

The cutout and panel range are already known from the Carling V-Series
datasheet and are in `dimensions.md` (**21.08 × 36.83 mm** hole, panel
**0.81–6.35 mm**, snap-in wings, no screws). Depth is the one thing that is
not, and it decides which face on the robot can host the switch — `panel_probe.py`
reports max available depth per site, so this measurement turns straight into
an answer.

- [ ] Bezel-flange underside → **back of the plastic body**
- [ ] Bezel-flange underside → **tip of the terminals** — take this separately.
      Spade terminals often bend, and right-angle receptacles shorten the stack
      a lot, so the two numbers can imply two different homes.
- [ ] **Wing step positions** — where it locks off. Tells us which panel
      thickness to actually target rather than guessing mid-range.
- [ ] Bezel **proud height + footprint** in front of the panel (rocker
      clearance, and whether a guard is needed so it can't be knocked on)
- [ ] → `dimensions.md` "SW1" row, then **re-run** `panel_probe.py --pitch 2.0`

⚠ Every "no" verdict in #368 currently assumes only that the body needs **more
than 10 mm**. That is the probe's floor, not a measurement.

## S2-2. Panel voltmeter — EVERYTHING ⬜

This part has **no row in `dimensions.md` at all**, and the disposition (#370)
is panel-mount with a horizontal window and a screw each side — so every
dimension in that sentence is currently unmeasured.

- [ ] Bezel L × W × **thickness**
- [ ] **Window** (cutout) L × W
- [ ] **Screw pitch, and the thread size** — this is the one that will be
      guessed wrong if skipped
- [ ] Body depth behind the panel
- [ ] Wire exit direction + connector type
- [ ] → new `dimensions.md` section, then the same pod rev as SW1

## S2-3. ~~Pololu buck cards — TRUE HEIGHTS~~ ✅ RESOLVED 2026-08-16, no caliper needed

**Closed from the vendor, not the bench.** Pololu's product page for the D42V110F7
(item #5674) gives Size **1.25″ × 1.7″ × 0.355″** = **31.75 × 43.18 × 9.02 mm**.
The `~13-15` estimate was wrong by ~6 mm.

Believed without a caliper for a stated reason: the same Size line's L×W matches
reg34c's independently-derived 31.8 × 43.2 exactly, so the source is right about
the two dimensions that could already be checked.

**And it turned out not to be load-bearing anyway** — #366's pocket search returns
24 supported placements at 9.02 mm and 24 at 12.0 mm. Height was never the binding
constraint; footprint against available plate is. Off the blocking list.

<details><summary>original entry</summary>

## S2-3. Pololu buck cards — TRUE HEIGHTS, all four ⬜

`dimensions.md` §4 carries "~13-15 ⚠ REVIEW" for the D42V110 pair and profile
heights for the others. The under-board pocket argument in #366 rests on these.

- [ ] **D42V110F7** (leg) and **D42V110F12** (hip) — total Z
- [ ] **D42V55F12** (Jetson), **D24V22F12** (L2) — total Z
- [ ] Measure **including pin protrusion below the board**, not just the tallest
      top-side component — the pins are what set the seat height in the pocket
- [ ] → `dimensions.md` §4, then re-open #366's fit math

Board outlines are already verified from the Pololu dimension drawings
(31.8 × 43.2 / 25.4 × 25.4 / 17.8 × 17.8) — **do not re-derive those**, they
were wrong once already and the drawings settled it.

</details>

## S2-4. HB2-ES544 E-stop — RESOLVE A CONTRADICTION ⬜

Not a discovery task. Two files disagree and both are in use:

| Source | Says |
|---|---|
| `dimensions.md:239` | Ø40 **assumed**, ⬜ CALIPER NEEDED |
| `chassis/control_pod.scad:24` | "**VERIFIED** specs 2026-07-08: Ø40 mushroom, 77 total length, panel max 6 mm" |

The "verified" set is vendor-page-sourced, not calipered — and a vendor page
already burned this project once (the SSD1331 outline was wrong by 4.9 × 5.1 mm,
§6 below). Thirty seconds converts a disagreement into a fact.

- [ ] Mushroom cap **Ø** · [ ] total length · [ ] below-panel body depth
- [ ] panel-hole Ø · [ ] max panel thickness its lock ring accepts
- [ ] → reconcile BOTH files to one number

## Same trip, not blocking

- [ ] **5191 installed envelope** — lug swing with a 10 AWG ring actually landed
      on the M8 stud, plus boot clearance. The block itself is fully measured
      (§3); this is the assembly envelope the bracket in #369 has to leave air
      for.
- [ ] SSD1331 header **pin protrusion + mating shell** (⬜ in §6) — straight
      Dupont adds ~14 mm, right-angle much less. Sets the tray standoff.
- [ ] D456 rear M3 thread depth + right-angle USB-C plug head (§2 leftovers)

## Do NOT re-measure — already closed

Blue Sea 5191 body/studs (§3) · battery pack (§4) · Jetson case + heatsink (§1)
· D456 body + rear pattern (§2) · L2 mount + barrel (§5) · SSD1331 outline,
hole pitches, back depths (§6) · STS3215 disc-to-disc 35.5.

**Moot, do not measure:** Ethernet switch bare PCB (off the robot 2026-08-14) ·
UBEC body (free-floating, no seat — #367) · Class-T fuse holder (superseded by
the MRBF).

---

# SESSION 1 — 2026-07-07 (record)

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

## 6. SSD1331 OLED module — ✅ DONE 2026-08-08 (#35)

Added 2026-08-02, CLOSED 2026-08-10. Historical context follows: the 4 board
mount holes in `oled_mount.scad` were **removed 2026-07-28** because the vendor
drawing gives the outline (27.3 × 30.7) but **not the hole pitch on either
axis** — the guessed pitch put 2 of 4 holes inside the display window. The
bracket is deliberately unprintable until these come off the **owned** module:

- [x] ✅ hole pitch along the **27.3 mm** axis = **22.8 mm**
- [x] ✅ hole pitch along the **30.7 mm** axis = **26.1 mm**
- [x] ✅ active display area **23.3 × 15.8**, positioned off the MEASURED borders
      (2.0 in from each long edge; 9.3 from the bottom) — the display sits 1.9
      off centre, so centring it would hide ~1.75 mm of screen
- [x] → landed in #337. `oled_mount` was then **DELETED** (2026-08-10, #35): the
      display now mounts on **`oled_tray`**, flat on the rear shoulder deck,
      looking up. Same calipered numbers carried over verbatim.

✅ **Back-side depths were taken in the same session** and are already on record
(dimensions.md:559/561): glass-front → tallest back component (excl. pins)
**4.8**, glass-front → PCB back **3.4**. Together those give the M2 screw
(**M2×6**, engaging 2.6 mm) and the 1.4 mm back-component stand-off, against
`oled_tray`'s 7.10 mm cavity — 5.70 mm clear.

⬜ Only the header **PIN** protrusion is unmeasured, and it cannot bottom: the
header sits over the deck's own through-opening, so the pins hang through.

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
