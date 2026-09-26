# NovaSM3 PCB v6 — Design Spec

Custom PCB replacing the upstream NovaSM3 v5.2b. Driven by the v3.2 architecture audit:
- XL4016 buck rails undersized for walking-gait current (8A cont. vs measured 8-12A avg + 25-40A impact transients)
- No safety chain (no LVC, no E-stop, no per-rail telemetry, no fuse spec)
- No Pattern B prep (any future Teensy-owns-bus migration requires chassis teardown)
- Stock PWM servo headers unused (Feetech bus is daisy-chain TTL)

Reference: BOM v3.2 §2, §3 · [`docs/power-budget.md`](../../docs/power-budget.md) · README "Power System" section.

---

## Feature set (v6 must-have)

### 1. Battery input + reverse protection

- XT60 panel-mount input (matches Ovonic packs)
- **MOSFET-based reverse-polarity protection** (not a diode — too much Vdrop at 10-15A continuous)
- **MRBF-30 terminal fuse — OFF-BOARD**, Blue Sea 5191 block at the pack in the battery→PCB lead (not a PCB footprint; F1 removed from `nova_pcb_v6` 2026-06-04). 30A time-delay, sized for hip-rail worst case ~20A + headroom. ANL/MIDI's ~6 kA interrupt rating can "fail to interrupt" a LiPo dead-short (vapor reconducts) → rejected. Class T (20 kA) was the interim spec, but this single 4S pack's real Isc ≈ 16.8 V ÷ 6–12 mΩ ≈ **1.5–3 kA**, vs MRBF's **~9 kA AIC @ 16.8 V = 3–4× margin** at ⅓ the size/weight → **MRBF chosen 2026-06-12**. At-source placement also protects the battery→PCB cable. See [`docs/research/2026-05-17-notes.md`](../../docs/research/2026-05-17-notes.md) §9 + [`docs/order-list.md`](../../docs/order-list.md) MRBF section.
- Power switch (off-board Blue Sea Contura SPST, **~18A @ 16.8 V DC**; 20A@12V / 15A@24V) wiring to on-board SW1 block. Sized for ~14A sustained; the SW1 terminal block matches it (15–20A class). The 30A MRBF is catastrophic-short (kA) protection, **not** the switch-path thermal limit — so SW1 block + switch are intentionally rated below the fuse.
- Mini digital voltmeter retained for at-a-glance pack state

### 2. Four active power rails + one reserved (v3.4 split)

| Rail | Module | Output | Sized for | Status |
|------|--------|--------|-----------|--------|
| Leg | Pololu D42V110F7 | 7.5V / 10A typ @ 42V Vin | 8× STS3215 19kg | Active v1 |
| Hip | Pololu D42V110F12 | 12V / 9A typ @ 42V Vin | 4× STS3215 30kg ONLY | Active v1 |
| L2 LiDAR | Pololu D24V22F12 | 12V / 2.6A | Unitree L2 (1A, dedicated buck for clean power) | Active v1 (added v3.4) |
| Jetson | Pololu D42V55F12 | 12V / ~3A cont. | Jetson Orin Nano Super MAXN | Active v1 |
| Arm | Pololu D42V55F7 | 7.5V / 3-8A | 6× STS3215 arm (Phase 4) | **Footprint reserved — DO NOT populate v1** |
| Aux 5V | UBEC 5V/5A (off-board) | 5V / 5A | Fans, aux peripherals | Header on board |

Module footprints use Pololu's standard header pitch so cards can be swapped without PCB respin. L2 split from hip rail (v3.4) because D42V110F12's 9A typ @ 42V Vin derates to ~7-8A at our 14.8V Vin, and combined hip+L2 sustained ~9A was over budget.

**Buck modules are OFF-BOARD (2026-06-05).** All five Pololu cards mount in a 3D-printed finned holder (open-air cooling), NOT soldered to the PCB. Forcing reason: every Pololu module is 100 % THT, so on-board the two PCB faces are **not independent placement planes** — pins pierce both. The 5 bucks alone are 47 % of the 112×90 board on a single plane, which pushes the all-THT board to ~74-84 % packing (hand-solder ceiling ≈55 %): it does not fit and is not hand-solderable. Off-board frees ~half the board and cools the bucks better than sandwiching them in the 20 mm mezzanine gap. The PCB keeps the buck **wire-terminal landings** at U1-U5 (footprint swap module → terminal, **netlist untouched** — same move as the INA226 swap). The finned holder is a CAD task tracked separately.

### 3. Servo bus distribution (star injection)

- Single signal bus (daisy-chained TTL) — no break
- **4 power injection points** along the leg 7.5V trunk (one per leg pair)
- **Bulk caps (1000 µF / 25V) at each injection point** — soaks impact transients near point of load
- GND-plane reference (FE-URT-1; solid GND plane = single low-Z return)
- Hip rail injects at chassis floor (4 hips clustered there)

### 4. Bus master — Pattern B default, Pattern A fallback

**Pattern B is the v1 active path.** Teensy 4.1 hardware UART routed through **SN74LVC125A quad tri-state buffer** as a half-duplex driver to the Feetech TTL bus pads. The SN74LVC125A must be populated on first build.

- Teensy UART TX → SN74LVC125A input gate
- Teensy GPIO → SN74LVC125A OE pins (TX-enable for write, RX-enable for read; half-duplex direction control)
- SN74LVC125A output → bus signal pad
- FE-URT-1 USB→TTL input header retained for fallback

Solder bridge `JP_BUS_MASTER` selects which path drives the bus pads:

- **B (default — board ships configured this way):** Teensy UART → SN74LVC125A → bus
- **A (fallback):** FE-URT-1 → bus directly (used for ID setup, debug, post-mortem)

Both paths terminate on the same bus pads; the bridge is the only state change. No chassis teardown to swap.

Linux jitter rationale: USB-CDC latency on Jetson is 1-10 ms typical, 50 ms+ under CUDA / kworker / journald load. Pattern B isolates the bus-servicing side (Teensy completes UART transactions to all 12 servos on time even when Jetson stalls); the gait command rate from Jetson is still Linux-bounded but the Teensy holds-last-command at 200-500 Hz, so a 100 ms Jetson freeze becomes a mid-step pause instead of a bus timeout.

### 5. Bus integrity footprints (populate per measured error rate)

Feetech bus is **single-ended half-duplex TTL UART**, not RS-485. 120 Ω differential termination is the wrong tool here.

- Series R footprints (22-100 Ω, 0603) at FE-URT-1 / SN74LVC125A output — slope rate-limiting
- Ferrite bead footprints at each servo entry — common-mode noise rejection
- GND-plane reference (FE-URT-1; solid GND plane = single low-Z return)

Default v1 build: leave footprints unpopulated. Populate iteratively if bus error rate exceeds threshold during bring-up. If still poor, drop baud 1M → 500k → 250k.

### 6. Safety chain

Three-stage battery low-voltage chain (highest trip first):
- **Charger LVC alarm:** ISDT 608AC set to **3.3V/cell = 13.2V** (warning beep, user-facing)
- **Graceful-shutdown comparator:** **3.25V/cell = 13.0V** pack. Comparator (LM393) + resistor divider → Teensy GPIO input. Teensy debounces + publishes `/battery_low`. Jetson subscribes + runs `systemctl poweroff` to unmount SD cleanly. ~30-60 s window before the hard cutoff trip at typical discharge rates — enough for Jetson to halt.
- **MOSFET hard-cutoff:** **3.1V/cell = 12.4V** pack. Second comparator stage drives a logic-level MOSFET on the battery feed. Autonomous backstop — fires whether or not Jetson shut down per the 13.0V trigger.

Other safety:
- **E-stop:** panel-mount latching button, NC contact. Wired in series with the **leg + hip + L2 rail enable lines** (D42V110F7 + D42V110F12 + D24V22F12 EN pins). Killing L2 stops the LiDAR spinning under emergency. Jetson rail stays alive for post-mortem debug + telemetry capture. Twist-to-release.
- **INA226 ×4:** one per active rail (leg 7.5V @0x40, hip 12V @0x41, Jetson 12V @0x44, L2 12V @0x45 — the L2 monitor is U12, populated, not optional since 2026-06-30). I²C bus to Teensy 4.1 → ROS 2 diagnostics topic. Per-rail current/voltage telemetry. **All four are identical 2 mΩ-shunt breakout modules** (Adafruit INA226 / "20A" generic) on 2.54 mm THT headers — the module's onboard shunt closes the high-side sense loop, so there is **no bare VSSOP-10 chip and no external 2512 shunt** (was the v1 plan for leg/hip; standardized to modules 2026-06-04). Must be a **2 mΩ** board: cheap 0.1 Ω "meter" modules saturate above ~0.8 A (useless on 8-12 A rails). Net effect: the board now has **zero fine-pitch parts** — everything is THT or 1.27 mm SOIC / SOT-23.

### 7. Aux MCU + peripherals (carryover from Nova v5.2b)

- Arduino Nano slot (3-pack already owned). **BOM v3.5 cut: only SSD1331 OLED + WS2812B LEDs remain active.** PIR / ultrasonic / DFPlayer / MPU-6050 dropped (redundant with D456 + L2 perception stack). Nano now acts as USB-serial bridge from Jetson driving the OLED (SPI) + LED strip (1 GPIO).
- Teensy 4.1 footprint (already owned) for INA226 I²C reader, E-stop GPIO, Pattern B half-duplex driver

### 8. Mechanical / connector convention

- M3 mounting holes matching chassis (TBD from CAD)
- JST-XH 2.54 for low-current signals
- XT30 for servo power injection trunks
- XT60 panel-mount for battery
- All connectors keyed to prevent reverse insertion

---

## Mezzanine stack — cross-board coordinate contract

The 2-board stack is **face-to-face vertical**, NOT an edge-mate. Logic board on TOP (component side UP — Teensy 4.1 + USB face the removable riser deck, so the deck lifts off for service without unstacking the boards), power board on BOTTOM (component side UP), joined by inter-board connector **J20** (2×6 IDC + ribbon) and **4 corner M3 standoffs** (20 mm) — note this is the UPPER set only; a second set of 4 at the same length and pattern carries the power board off the floor plate below it, so the build needs **8** (corrected 2026-08-18). ~~Stack ≈41 mm tall, fits the ~46.9 mm chassis trunk depth.~~ **Wrong comparison:** the real ceiling is `STACK_TOP_Z ≈ 62.22` (Teensy/Nano socket top, measured off the parsed board mesh) and the trunk plateau is 46.91. The stack does not fit inside the trunk and never had to — it rises into the riser bay, clearing the deck underside (67.9) by 5.68 mm. All user I/O (both USB, OLED cable, LED cable, FE-URT bus) exits the **front (low-Y) edge**.

**Both boards share ONE absolute KiCad coordinate frame.** Holes + J20 only mate if their XY match across boards. Logic board is mounted component-side-up by **flipping about the vertical centerline x=140** — so everything in the contract is symmetric about x=140 and survives that flip.

### Locked values (logic board `nova_pcb_v6_logic`, floorplan DONE)

| Item | Value | Note |
|---|---|---|
| Outline (Edge.Cuts) | `(98,57)-(182,135)` = **84×78 mm** | center **(140,96)** = trunk middle |
| Standoff H1-H4 (M3) | `(103,63) (177,63) (103,129) (177,129)` | ±37 from x=140, symmetric → flip-invariant |
| J20 interboard | `(140,124)` **rot90** (6-pin axis along X) | on x=140 axis → stays put under flip; ribbon absorbs pin-1 mirror |

### Power board (`nova_pcb_v6_power` #67) MUST match

- **Same absolute origin frame** (do not re-zero).
- **Same 4 standoff XY**: `(103,63) (177,63) (103,129) (177,129)`.
- **J20 at `(140,124) rot90`** (short ribbon reach to logic J20; ribbon handles pin-1).
- **Outline ENCLOSES logic**, centered (140,96): target ~**112×90 mm** → `(84,51)-(196,141)`.
- Power-board I/O (XT60 battery, XT30 injection, E-stop, switch) goes on the **rear/side edges**, clear of the logic board's front-edge I/O column.
- **Bucks U1-U5 are off-board** (finned holder) — the board carries only their wire-terminal landings, not the 32×44 mm module bodies. On-board THT that remains (INA ×3 + bulk caps + ring/injection connectors + L1 + switches) ≈ 37 % of one plane → 2-sided placement is now genuinely viable.

---

## Out of scope for v6

- Wireless: keep on Jetson (built-in WiFi 5)
- Storage: Jetson NVMe is direct M.2 (not on PCB)
- High-current arm rail: footprint reserved but unpopulated (Phase 4)
- Custom switching designs (TPS54824 etc.): Pololu modules used instead — easier debug, faster spin, no SMPS expertise needed

---

## Design workflow

1. Schematic in KiCad (or Eagle). Reference designators consistent with BOM v3.4.
2. Footprint placement: keep servo connectors on chassis-facing edge, Jetson connectors on top edge.
3. Power planes: separate 4-layer stackup (top sig, GND, PWR, bottom sig). GND-plane reference (FE-URT-1).
4. DRC + ERC clean before Gerber export.
5. PCBWay order: 5 boards (spares + iteration), 2 oz copper, ENIG finish, stencil for SMD.
6. First-article: hand-populate one board, bench-test every rail before populating others.

---

## Length matching (#416)

A length-matching **rule and gate exist now** so the first board where mismatch is
actually an electrical problem (see "Carry to LPL HIVE" below) already has the
tooling. On the two active v6 boards today it is **not fixing anything** — no
copper changed for this ticket — it is establishing the budget and the CI gate
before they're needed.

**Budget formula:** skew ≈ Δlength × ~6.8 ps/mm (FR-4 typical propagation
delay). A group's `tolerance_mm` is chosen well under the electrical bound
that formula gives (5% of the signal's bit period, converted to a length via
that formula) — see each `length_match.json`'s `budget` string for the exact
derivation per group. On these boards that electrical bound is 3-4 orders of
magnitude looser than the routed lengths (a few thousand mm vs a few tens of
mm), so `tolerance_mm` is set as a **layout-discipline bound** instead — a
number close enough to the measured spread on main to still catch a gross
miroute (a leg rerouted the long way around, a net that grew 10x), not to
enforce timing margin that doesn't apply at these speeds.

**Measured** (recomputed directly from the `.kicad_pcb` `(segment)`/`(via)`
records by `tools/check_length_match.py`, 2026-09-25 — see that command's own
output for the authoritative numbers; the issue's hand-measured table agreed
within its own stated 0.1 mm tolerance except the via count, corrected below):

`nova_pcb_v6_logic` — 155 segments, **4 vias** (the issue's "8 vias" counted
`(vias allowed)` net-class lines, not `(via ...)` records — corrected here):

| group | net | length | vias |
|---|---|---|---|
| Feetech bus (1 Mbaud half-duplex TTL, Pattern B) | `TEENSY_TX` | 55.65 mm | 0 |
| | `TEENSY_RX` | 54.31 mm | 1 |
| | `OE_TX` / `OE_RX` | 52.55 / 52.06 mm | 0 |
| | `BUS_SIGNAL` / `BUS_SERVO` | 40.84 / 40.63 mm | 0 |
| OLED SPI (Teensy/Nano → series-R `_F` nets → SSD1331) | `SPI_SCK`+`SPI_SCK_F` | 52.97+7.27 = 60.24 mm | 0 |
| | `SPI_MOSI`+`SPI_MOSI_F` | 29.82+11.55 = 41.37 mm | 0 |
| | `OLED_CS`+`OLED_CS_F` | 50.88+3.71 = 54.60 mm | 1 |
| | `OLED_DC`+`OLED_DC_F` | 33.56+8.93 = 42.49 mm | 0 |
| I²C (INA226, 400 kHz) | `I2C_SCL` / `I2C_SDA` | 46.44 / 46.44 mm | 0 |

`nova_pcb_v6_power_v2`: `I2C_SDA` 196.16 mm (3 vias) vs `I2C_SCL` 162.76 mm (1
via); `BUS_SERVO` 62.46 mm (2 vias, informational only — a single net has no
partner to match against).

**Gate:** `tools/check_length_match.py <board.kicad_pcb> <length_match.json>`
— stdlib-only (no `pcbnew` import), so it runs in CI and on the Mac. Sums
routed copper length per net from the board file, adds a per-via allowance
(`via_allowance_mm` in the spec — derived from the board's own `(general
(thickness …))`, since one through via traverses the full stackup), and
checks each group's spread against `tolerance_mm` and each member against the
optional `max_mm`. Nets are matched to the spec by **leaf name** — the part
of the KiCad net name after the last `/` — because several nets here carry a
hierarchical sheet prefix that itself contains `/` and even `+`
(`/07 Aux MCU + Peripherals/SPI_SCK`), so a spec net list is a JSON array of
leaf names, never a `+`-joined string.

Exit codes: `0` pass, `1` a group's spread exceeds `tolerance_mm` or a member
exceeds `max_mm`, `2` a net named in the spec is missing from the board or
present but unrouted (0 length, 0 vias) — checked *before* 1, so a spec typo
or a deleted net can never be graded as a silent pass. `--selftest` runs a
synthetic two-net fixture through all four outcomes (pass, spread-fail,
missing-net, unrouted-net) with no real board file needed.

CI: `.github/workflows/cad-gates.yml`'s `pcb-length-match` job runs
`--selftest` plus both real boards on every PR that touches the checker, a
board's spec, or the two `.kicad_pcb` files. `tools/test_check_length_match.py`
is the pytest regression suite (run in `ros-pytest.yml`, next to
`test_fab_gate.py` — that file is a standalone script, not
pytest-collectible, see its own docstring).

**In-editor feedback (best effort):** `nova_pcb_v6_logic.kicad_dru` adds
`(constraint length (max …))` rules matching the same `max_mm` ceilings, so
KiCad's own DRC flags a wildly-over-length net while routing. **This is not
the source of truth and cannot fully express the rule above:** KiCad's
`skew` constraint only evaluates true differential pairs, and none of these
groups are diff pairs (the Feetech bus is single-ended TTL, not RS-485 — see
the bus README). There is no KiCad 9/10 DRC construct that checks *group
spread* across independent single-ended nets, so the `.kicad_dru` rules are
per-net `max` ceilings only — they cannot catch "net A grew 20 mm relative to
net B while both stayed under max", which is exactly what
`check_length_match.py` checks and CI enforces. Verified by tightening one
rule to an obviously-violated bound and confirming `kicad-cli pcb drc` reports
it (`length_out_of_range`); at the real thresholds committed here it adds
**zero** new DRC violations (17 pre-existing `lib_footprint_mismatch` before
and after — unrelated cosmetic findings, not touched by this ticket).

**Adding a net to a group:** append its leaf name to the relevant
`length_match.json` `members` list (a new list entry for a standalone net, or
appended into an existing member's array to sum it with its `_F`/continuation
net). Re-run the gate once — it will report the new spread — and only then
decide whether `tolerance_mm` still holds or needs its own re-derivation
(update the `budget` string, never just the number).

**Carry to LPL HIVE:** same tool, different numbers, once a HIVE repo exists
to hold them (none was reachable under `Ace2932` as of 2026-09-25). The groups
that will actually need tight matching there: Ethernet MDI pairs (intra-pair
≤ ~0.1 mm, inter-pair ≤ ~5 mm — real diff-pair matching, where KiCad's `skew`
constraint DOES apply, unlike everything on the v6 boards), RMII
(`REF_CLK` vs `TXD`/`RXD` within the PHY's setup/hold), SDMMC/eMMC
(`CLK` vs `DAT0-3`/`DAT7`), QSPI flash, and the SAR ADC `SCLK`/`SDO` group.
The checker is repo- and board-agnostic by construction (a `.kicad_pcb` path
+ a JSON spec) on the assumption HIVE is KiCad; only the parser would need to
change for Altium.

---

## Open questions for design phase

- Final D42V55F7 footprint orientation on arm-rail reservation (depends on Phase 4 mechanical install)
- Whether to integrate the lighted rocker switch into the PCB or keep panel-mount via flying lead
- Whether to add a USB-C dev port for direct Teensy programming (vs pulling the Teensy out for USB-A flashing)
- Whether to mirror the v5.2b voltmeter on the PCB or panel-mount

Resolve during schematic review.

---

> ⚠️ **DEPRECATED (2026-06-05):** the single-board `nova_pcb_v6/` is **superseded by the 2-board mezzanine** — `nova_pcb_v6_power/` (battery / rails / servo-bus / safety) + `nova_pcb_v6_logic/` (Teensy / 74HC125 / Nano), joined by inter-board connector **J20**. New work happens on the mezzanine projects; this single board is kept for reference/history only. **Teensy/Nano power-input fix was NOT back-ported here:** in this capture the Teensy 4.1 is fed via its 3.3V *output* pin with VIN floating (cannot back-power a Teensy 4.x — onboard PMIC needs VIN) and the Nano `+5V`/`VIN` both float — corrected **only on the mezzanine logic board** (`V5_AUX` → Teensy VIN + Nano `+5V`). The bug remains in this single-board project and will not be fixed.
>
> **Status:** design spec at BOM v3.5 / v0.3.2-l2-dedicated. **Schematic captured + board placed** in KiCad 9 (`nova_pcb_v6/`, §1-§8 hierarchical, autobuild). Schematic: all 51 components footprinted (was 54 — F1 Class-T fuse + R13/R14 2512 shunts removed 2026-06-04) — KiCad-stock libs except **9 components on 5 custom footprints** in `nova_v6.pretty/` (3 Pololu buck families D24V22/D42V55/D42V110 on U1–U5, Teensy 4.1 socketed 2×24 on U6, INA226 breakout module on U9/U10/U11; geometry reconstructed from Pololu dim PDFs + PJRC card11a + INA226 module outline, every `descr` flagged **VERIFY vs physical part before fab**). **Buck connector pin orders extracted + corrected from the Pololu dimension drawings** (reg19a / reg34a / reg34c) + board photos: D42V55 **un-mirrored** to VOUT·GND·VIN·VRP·PG·EN (the prior footprint had it reversed — would have driven the module's VIN pin into an NC/VRP hole), D24V22 set to PG·EN·VIN·GND·VOUT, D42V110 power column re-spanned to 17.94 mm with the invented SCL/SDA/ENB/PFM signal names removed (the family carries only VOUT/GND/VIN/VRP/EN/PG); verified board sizes + per-buck pin maps recorded in [`../../hardware/cad/dimensions.md`](../../hardware/cad/dimensions.md) §4. Net-bearing pad sets (1/2/3/4) unchanged, so the netlist is untouched — propagate the corrected pad geometry to placed U1-U5 via pcbnew **Tools → Update Footprints from Library** (preserves hand-placement). Pin-name-level wiring audit passed, ERC clean except 1 intentional warning (`V7V5_ARM` — reserved Phase-4 arm rail, DNP); audit added the two missing off-board load connectors J12 (`V12_JET`→Jetson) + J13 (`V12_L2`→L2 LiDAR). Power-monitor topology standardized (2026-06-04): all three rails — U9 leg / U10 hip / U11 Jetson — use the identical INA226 breakout module whose onboard 2 mΩ shunt closes the high-side sense loop; external 2512 shunts R13/R14 deleted (each module's internal shunt now bridges that rail's RAW↔clean nets, exactly as the Jetson rail already did). ERC re-run clean (0 errors, 1 expected `V7V5_ARM` warning). L2 12V rail gains a 22 µH + cap LC filter (L1) for LiDAR-clean power. **Layout placement complete:** all 54 footprints placed by power flow (battery left edge → 5 Pololu bucks → INA226 sense → bulk caps → right-edge injection connectors; logic/safety in bottom band; M3 holes at corners), 0 overlaps, spacing audited for Pinecil V2 hand-soldering (≥3.6 mm body gap on the radial caps). Solder load: ~34 parts, all easy THT/SMD — with all 3 INA226 now THT breakout modules the board has **zero VSSOP-10 drag-solder parts** (prior fine-pitch concern eliminated), and the off-board fuse drops F1 from the board; 13 DNP tuning/fallback footprints (R1, R2-R12, FB1) left unpopulated. Netclasses set. **Board re-sync pending (2026-06-04 schematic changes):** the placed `.kicad_pcb` still holds the pre-change 54 footprints — open pcbnew → **Tools → Update PCB from Schematic (F8)** to apply: delete F1 + R13 + R14, and swap U9/U10 from `VSSOP-10` to `nova_v6:INA226_Module_Breakout` (F8 preserves hand-placement of the other footprints; the two bigger INA modules land at U9/U10's old spots and may need a small nudge). **Pending CAD board dims:** Edge.Cuts outline + M3 hole pattern. Next: copper routing + GND / high-current pours (thermal-relief spokes on THT pads so the Pinecil can melt joints) → DRC → Gerber export.
> **Owner:** Aiden Fox.
