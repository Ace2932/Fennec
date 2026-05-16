# Committed Order List — Phase 0 Final Pass (v3.4)

One-shot consolidated checkout for the BOM v3.4 committed adds (~$362, ISDT 608AC charger + Pololu 4-rail redesign + full safety scope). Each item below has primary + backup vendor/SKU options. **Verify in-stock + ship-by date before clicking buy.**

> NVMe is intentionally NOT on this list — deferred until NAND prices recover (<~$100 for 1TB). See BOM §1 + open decision row 8.
> Arm-rail buck (D42V55F7) is NOT on this list — Phase 4 future. PCB v6 footprint reserved.
> v3.4 adds dedicated L2 LiDAR buck (D24V22F12, $19) after datasheet de-rating check on D42V110F12.

---

## 1. Power conversion + charging

### ISDT 608AC LiPo charger — ~$60 ✅ ORDERED
- Modes needed: balance charge, **storage**, discharge
- On arrival: power up no-battery, verify storage-mode menu works, set LVC alarm to 3.3V/cell = 13.2V

### LiPo safe bag — ~$15 ✅ ORDERED
- Fireproof fiberglass bag sized for 4S 4000mAh packs

### XT60 jumper (for 608AC battery input) — $0 ✅ SUPPLIED WITH OVONIC KIT
- Confirmed in Ovonic 4S LiPo kit. Skip purchase.

### XT60 charging lead — $0 ✅ SUPPLIED WITH OVONIC KIT
- Confirmed in Ovonic kit (XT60 ↔ JST-XH balance, 5-pin for 4S). Skip purchase.

### Pololu D42V55F12 (Jetson 12V rail) — ~$32
- **Primary:** `pololu.com` direct — find on D42V55Fx family page (Pololu's search may not return the F12 SKU; navigate the family page and pick 12V from the variant dropdown)
- **Backup:** DigiKey / Mouser (same part #)
- **Why:** 12V fixed out, 12-60V in, 4.5A typ @ 42V Vin (derates to ~3A at 14.8V Vin per Pololu's de-rating graph). Reverse-polarity protected.
- **LVC reminder:** min Vin is 12V, so set LiPo low-voltage alarm at **3.3V/cell = 13.2V**.
- **Bench validation:** sweep Vin 16.8V → 13.2V under Jetson MAXN load (≈25W). 12V rail should stay flat (no >100 mV droop).

### Pololu D42V110F7 (leg 7.5V rail, 8× STS3215 19kg) — ~$60
- **Primary:** `pololu.com` direct, item #5674
- **Why:** 7.5V fixed out (within STS3215 6-8.4V spec), 7.6-60V Vin range, 10A typ @ 42V Vin (derates at our 14.8V Vin per Pololu's de-rating graph). Sized for walking-gait avg 5-8A with bulk caps absorbing 25-40A impact transients near point of load.
- **Bench validation:** load with 1×, 4×, then 8× STS3215 19kg in a walking-gait stand-in (alternating PWM @ 2 Hz). Watch thermal rise, voltage sag, and transient overshoot. Add bulk caps (1000 µF) at each star injection point if observed.

### Pololu D42V110F12 (hip 12V rail, 4× hip STS3215 30kg only) — ~$60
- **Primary:** `pololu.com` direct, item #5677
- **Why:** 12V fixed out, 12-60V Vin range, 9A typ @ 42V Vin (derates lower at 14.8V Vin). Sized for 4× hip STS3215 30kg sustained ~8A. **L2 LiDAR moved off this rail** to a dedicated buck (v3.4) — combined hip+L2 load was margin-thin under de-rating.
- **Bench validation:** load with 1× then 4× 30kg hip walking-stand-in. Thermal IR after 10 min sustained. Confirm derated continuous capacity matches your measured load. If sustained pull >7A and thermal is concerning, plan parallel modules or upgrade to D24V150F12.

### Pololu D24V22F12 (L2 LiDAR 12V dedicated rail, v3.4 split) — ~$19
- **Primary:** `pololu.com` direct — find on D24V22Fx family page (`pololu.com/category/107/d24v22fx-step-down-voltage-regulators`), pick 12V variant
- **Why:** 12V fixed out, ~2.2-2.6A max, 36V Vin max, 85-95% efficiency. L2 LiDAR draws ~1A → 2.6× headroom. Dedicated buck = clean power for the LiDAR, no servo transient ringing on its supply.
- **Bench validation:** load with L2 LiDAR active. Scope output for ripple at buck switching frequency (~400 kHz) before/after LC filter.

---

## 2. Networking

### TP-Link LS105G OR NETGEAR GS305 — ~$15
- **Primary:** Amazon — 5-port unmanaged gigabit, **must be metal-cased or strip-friendly** (planning to remove case for chassis volume)
- LS105G is the slimmer of the two
- Avoid: ports >5 (unnecessary weight), managed switches (overkill, draws more)

### Short Cat6 patch cables × 2 (0.5m) — ~$8
- **Primary:** Amazon / Monoprice — Cat6, ≤0.5m, snagless boot
- Two: one Jetson↔switch, one L2↔switch
- Avoid: Cat5e (gigabit-marginal under EMI), Cat6a (over-spec'd for this run length)

### LC filter parts for L2 12V tap — ~$3
- 1× inductor: ~22 µH, ≥2A rated (DigiKey series-resonant choke)
- 1× electrolytic cap: 470 µF, 25V
- Bundle into the next DigiKey / Mouser order to save shipping

---

## 3. Safety + bus-master parts (PCB v6 critical-path)

### 74HC125 quad tri-state buffer (Pattern B half-duplex driver) — ~$1
- **Primary:** DigiKey / Mouser (SOIC-14, e.g. SN74HC125N)
- **Why:** v1 critical-path. Drives the Feetech bus from the Teensy 4.1 UART. `JP_BUS_MASTER` solder bridge defaults to Pattern B on PCB v6. Buy 5 (cheap, easy to fry, want spares for bring-up).

### E-stop button (panel-mount, latching, NC contact) — ~$10 ✅ ORDERED
- Mxuteuk HB2-ES544 — 22 mm panel mount, mushroom head, twist-to-release, 2× NC contacts (one each for leg + hip rail enables, or wire all three rails to one contact pair)
- **Wiring:** NC contact in series with the **leg + hip + L2 rail enable lines** (D42V110F7 + D42V110F12 + D24V22F12 EN pins). LiDAR stops spinning; Jetson rail stays alive for debug.

### INA226 current/voltage monitor × 3 — ~$9
- **Primary:** Adafruit / Amazon — INA226 breakout (or bare IC if rolling SMD into PCB v6)
- **Why:** One per active rail (leg 7.5V, hip 12V, Jetson 12V); optional 4th on L2 rail. I²C to Teensy → ROS 2 diagnostics topic.
- Buy 4× — one spare.

### Comparator + MOSFET parts for hard-cutoff at 12.4V + graceful-shutdown at 13.0V — ~$13
- **Two comparator stages:**
  - 13.0V trigger → drives Teensy GPIO → `/battery_low` topic → Jetson `systemctl poweroff` (clean SD unmount)
  - 12.4V trigger → drives MOSFET on battery feed → autonomous hard cutoff
- 2× LM393 (dual comparator, one stage each) OR 2× TL431 (DigiKey)
- 1× IRLB3034PBF logic-level N-channel MOSFET (or similar Rds(on) <5 mΩ at Vgs=4.5V, Id ≥30A)
- 1× P-channel power MOSFET on the high side if doing high-side switching
- 2× trim-pot or precision resistor divider to set each trip point
- Bundle with DigiKey order

### Bulk caps for rail injection points — ~$4
- 4× 1000 µF / 25V electrolytic (Nichicon UPW series or equivalent)
- One per star injection point on the leg 7.5V rail
- Absorbs servo impact transients near point of load

---

## 4. Mechanical consumables

### Loctite 243 blue threadlocker — ~$8
- **Primary:** Amazon / hardware store
- Get the **bottle** not single-use vials (you'll re-use it on every servo bracket)

### Electrical tape + Kapton tape — ~$10
- 1× 3M Super 33+ electrical tape (NOT generic vinyl)
- 1× Kapton tape, 10mm wide, for IMU / OLED insulation + LiDAR mast strain points

### Bambu Lab Liquid Glue — using existing supply
- Using Bambu's liquid glue on textured PEI for PA6-CF adhesion
- ⚠️ Bambu's stock liquid glue is generic-purpose, not nylon-specific. **Print-test before committing to batch:** if PA6-CF first layer doesn't bond well, fallback to Magigoo PA (~$15) or similar PA-specific adhesion product.

---

## 5. Display

### DisplayPort cable OR DP→HDMI adapter — ~$10
- **Primary:** Amazon — pick based on monitor: DP-to-DP if monitor has DP input, DP-to-HDMI active adapter otherwise
- **Note:** Jetson Orin Nano Dev Kit has DP only (no HDMI). Passive adapters work for HDMI 1.4-class monitors; if monitor is 4K@60Hz you need an active adapter.

---

## 6. Servo top-up (not in main subtotal — separate spend)

### STS3215 7.4V 19kg × 2 (complete 8-count for legs) — ~$50
- **Primary:** Feetech AliExpress store (slow but cheapest)
- **Backup:** Amazon — verify they're genuine Feetech, not clones (clones have inconsistent center calibration)
- Already have ~6 of 8 needed; buy 2 + ideally 1 spare = 3
- Reminder: v1 build = 12 active servos. Arm 6× already on shelf, not in scope.

---

## 7. PCB v6 (separate order, after design)

### NovaSM3 PCB v6 — custom redesign (~$60 PCBWay)
- Design spec lives in [`hardware/pcb-mods/README.md`](../hardware/pcb-mods/README.md)
- Order after schematic + Gerbers reviewed
- Recommend ordering 5 boards (PCBWay minimum is usually 5 or 10) for spares + revision iteration
- Stencil: order alongside for SMD population

---

## Total committed-adds spend at checkout

| Line | $ | Status |
|------|----|--------|
| ISDT 608AC | 60 | ✅ Ordered |
| LiPo safe bag | 15 | ✅ Ordered |
| ~~XT60 jumper~~ | 0 | ✅ Supplied (Ovonic kit) |
| ~~XT60 charging lead~~ | 0 | ✅ Supplied (Ovonic kit) |
| Pololu D42V55F12 (Jetson) | 32 | 🆕 To order |
| Pololu D42V110F7 (leg) | 60 | 🆕 To order |
| Pololu D42V110F12 (hip only) | 60 | 🆕 To order |
| Pololu D24V22F12 (L2 dedicated) | 19 | 🆕 To order |
| 74HC125 + INA226 ×3 + 2× comparator + MOSFETs + bulk caps | 33 | 🆕 To order |
| E-stop button (Mxuteuk HB2-ES544) | 10 | ✅ Ordered |
| Switch + Cat6 ×2 + LC parts | 26 | 🆕 To order |
| Threadlocker + tape | 18 | 🆕 To order |
| ~~Magigoo PA~~ → Bambu liquid glue | 0 | ✅ Using existing |
| DP adapter | 10 | 🆕 To order |
| **Subtotal (actual remaining spend)** | **~$268** | |

Updates since v3.4:
- ISDT 608AC + LiPo bag + E-stop: ordered ✅
- Ovonic kit confirmed includes XT60 jumper + charging lead → $13 saved
- Bambu liquid glue substituted for Magigoo PA → $15 saved (with fallback if PA6-CF adhesion fails)
- $371 worst case → **$268 actually-need-to-order**

Not included: PCB v6 (~$60), arm servo top-up (~$50).

---

## Ordering strategy

1. **Bundle by vendor** to minimize shipping (✅ ordered items removed):
   - **Amazon:** threadlocker, tape, DP adapter, Cat6 cables, switch, INA226 breakouts
   - **Pololu direct:** D42V55F12 + D42V110F7 + D42V110F12 + D24V22F12 (one shop, free shipping over $100 — $171 bundle qualifies easily)
   - **DigiKey or Mouser:** LC filter parts (inductor + cap), 74HC125, comparator, MOSFETs, bulk caps — single electronics order
   - **Feetech / AliExpress:** servo top-up (separate, slow boat)
   - **PCBWay:** PCB v6 (after design freeze)

2. **Verify before pulling trigger (remaining items):**
   - DP cable matches your actual monitor input
   - Switch SKU explicitly "gigabit" not "fast ethernet 10/100"
   - Pololu part numbers: F7 = **7.5V output** (within STS3215 6-8.4V spec), F12 = 12V output (don't mix up)
   - MOSFET Rds(on) <5 mΩ at Vgs = 4.5V (logic-level), Id ≥30A (battery dead-short worst case)
   - INA226 shunt rating sized to rail (legs need 10A+ shunt, Jetson can use stock 1Ω)

3. **Don't order yet:**
   - NVMe — wait for NAND price recovery
   - Arm-rail D42V55F7 — Phase 4
   - PCB v6 — until schematic + Gerbers complete
   - Spare bearings / spare servo — order with the next Feetech batch when you actually need them

---

## After things arrive

- [ ] Power up 608AC with no battery — verify storage-mode menu works
- [ ] Set LiPo LVC alarm at 3.3V/cell = 13.2V (above D42V55F12 dropout)
- [ ] Bench-load Pololu D42V55F12 → 12V out under Jetson MAXN draw. Sweep Vin 16.8V → 13.2V, verify 12V rail stays clean (<100 mV droop, no oscillation)
- [ ] Bench-load Pololu D42V110F7 → 7.5V under 1× / 4× / 8× STS3215 19kg walking-stand-in. Thermal IR check after 10 min sustained load.
- [ ] Bench-load Pololu D42V110F12 → 12V under 1× / 4× 30kg hip walking-stand-in (hips only — L2 on dedicated buck). Thermal IR check after 10 min sustained.
- [ ] Bench-load Pololu D24V22F12 → 12V under L2 LiDAR active. Scope output ripple at buck switch freq (~400 kHz) before/after LC filter.
- [ ] Verify 13.0V graceful-shutdown comparator → Teensy `/battery_low` topic → Jetson `systemctl poweroff` (sweep bench supply down to 13.0V, watch topic + log)
- [ ] Verify 12.4V MOSFET hard-cutoff via bench-supply sweep before connecting battery (should fire ~30-60 s after 13.0V trigger at typical discharge rate)
- [ ] Verify E-stop physically opens leg + hip + L2 rail enables (LiDAR stops; Jetson rail stays alive on press)
- [ ] Verify INA226 ×3 I²C reads (current + voltage) under nominal and loaded states
- [ ] Switch power test: 5V UBEC → switch → all 5 ports link-up
- [ ] LC filter measurement: scope the D24V22F12 output (L2 feed) for ripple at ~400 kHz buck switch frequency, before/after the LC, both at idle and under L2 active load

> Status: updated at BOM v3.4. Update with actual SKUs / order #s as items hit Cart.
