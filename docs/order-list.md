# Committed Order List — Phase 0 Final Pass (v3.4)

One-shot consolidated checkout for the BOM v3.4 committed adds (~$362, ISDT 608AC charger + Pololu 4-rail redesign + full safety scope). Each item below has primary + backup vendor/SKU options. **Verify in-stock + ship-by date before clicking buy.**

> NVMe is intentionally NOT on this list — deferred until NAND prices recover (<~$100 for 1TB). See BOM §1 + open decision row 8.
> Arm-rail buck (D42V55F7) is NOT on this list — Phase 4 future. PCB v6 footprint reserved.
> v3.4 adds dedicated L2 LiDAR buck (D24V22F12, $19) after datasheet de-rating check on D42V110F12.

---

## 🆕 2026-06-14 update — order reconciliation + arm Phase-4 schematic adds

Cross-checked Amazon order history against the board BOM. **Big/long-lead items DONE since the lists above:** MRBF fuse system (Blue Sea 5191 block + Bay Marine MRBF-30 ×2), SW1 switch (Blue Sea 8282 Contura SPST), Q1 IRLB3034PBF ×5, bulk caps 1000µF/25V ×12 (FymuSing — Ø10×17mm; fits Ø12.5 land + 5mm pitch, clears the 20mm standoff gap, 1mm over the 16mm low-profile spec → fine), 12AWG silicone wire, 5/16" ring lugs, M3×20 mezzanine standoffs, full bench kit (30V/10A PSU, IR thermometer, 24MHz logic analyzer, LCR/transistor tester, 100W load resistors, solder wick).

Arm Phase-4 now wired into the power board (schematic only, ERC clean, F8+route+gerber pending): U5.EN re-gated VBAT_PROTECTED→EN_BUCKS · **J14** arm output XT30 added (was a dangling net) · **U12** arm INA226 added (addr **0x45**, DNP). See [[project-power-board-arm-phase4]].

---

## 🟢 FINAL pre-build order (both boards + Phase-4) — 2026-06-15

Full multi-phase, both-board audit. Both boards are routed + DRC-clean (logic: 0 unconnected / 0 errors; power: clean, and the J14/EN/U12 edits add **zero** new orderable parts). Teensy 4.1 ✅ owned, Nano ✅ ordered, no DNP surprises → **BOM is frozen.** This is intended to be the **last DigiKey/Mouser order**. The 3 non-DigiKey lines at the bottom are separate-vendor orders that can't go on DigiKey.

### A. DigiKey / Mouser cart — ONE order

**Active / ICs**
- LM393DR SOIC-8 ×2 (power U8 + spare)
- BSS138 SOT-23 ×5 (power Q2/Q3/Q4 + spares)
- 74**LVC**125 SOIC-14 ×5 (logic U7 — board uses LVC, 5V-tolerant; keep it) — *Q1 IRLB3034 ✅ already ordered*

**Electrolytics**
- 470µF/25V radial Ø10 5mm-pitch ×4 (power C6/C8/C9 + L2-filter cap; e.g. Nichicon UPW1E471MPD) — *1000µF C1–C5 ✅ ordered*

**Inductor**
- 22µH ≥2A power inductor ×1 (Bourns SRR1260-220M) — power L1 / L2-LiDAR LC filter

**0603 passives — consolidated across BOTH boards** (buy 10-packs, Yageo RC0603 1% / X7R)
| Value | Qty | Refs |
|---|---|---|
| 10k | 9 | pwr R5/R7/R8/R9/R13 + logic R7×2 |
| 1k | 5 | logic R2–R6 |
| 100k | 2 | pwr R2/R16 |
| 4.7k | 2 | pwr R11/R12 |
| 22k · 470k · 1M | 1 each | pwr R3/R14/R15 |
| **11.3k 1%** · **12.1k 1%** | 1 each (buy a few — trip-point) | pwr R4/R6 |
| 22R | 2 | logic R1 (bus series) |
| 100nF (C0603 X7R) | 4 | pwr C7 + logic C1 |
| 600R ferrite (L0603) | 2 | logic FB1 |

**Connectors**
- JST **B3B-XH-A** ×4 (power J8 + logic J11 + spares) — DK 455-2247-ND
- 🔴 **IDC box header 2×06 2.54 shrouded ×2** (J20 on *each* board) + **12-way ribbon** + 2 IDC receptacle ends (mezzanine link — currently have zero; pair required, two males can't mate)
- 2.54 pin-header breakaway strip ×1 (Sullins PRPC040SAAN) — covers pwr J2/M1 + logic J10/J21/J9/JP1
- 2.54 shorting jumpers ×3 (JP_BUS_MASTER, logic JP1)
- 🔴 **SW1 15–20A screw block** (KF301-16A / Phoenix MKDS — kit block is 10A, SW1 carries ~15A) *(DigiKey or Amazon)*

**TVS (off-board, power rails incl. Phase-4 arm)**
- SMBJ8.5A ×5 (2 leg + 1 arm Phase-4 + spares) · SMBJ13A ×5 (hip + L2 + spares) — cathode band to +, across injection XT30 pigtails

### B. NOT DigiKey — separate-vendor orders (don't forget)
- **Pololu:** D42V55F7 arm buck (~$32) — Phase-4 install
- **Amazon:** +1 INA226 20A R002 module — arm U12 consumed the 4th/spare → 0 spares now
- **Feetech / AliExpress:** 6× servo daisy-chain cables — Phase-4 arm (user handling)
- **PCBWay:** both boards ×5 + stencils — **after** power-board routing (J14/EN/U12) + gerber regen

### Why this is the last DigiKey trip
Both boards DRC-clean → no design churn pulling new parts; pending power edits add nothing orderable; Phase-4 electronics folded in (TVS arm clamp in the ×5). Only re-order risk = a 1% trip-point value (R4 11.3k / R6 12.1k) failing bench trim → buy a couple neighboring values as insurance.

---

## 🆕 2026-06-18 — cart audit (actual DigiKey cart vs the FINAL list above)

Audited the in-progress DigiKey cart against §A. **Cart deviates — fix before checkout:**

🔴 **Wrong part in cart:** had **SN74HC125D** (DK 296-1192-5-ND) — plain HC, **NOT 5V-tolerant**. Servo bus is 5V-TTL into a 3.3V-powered buffer → HC inputs over-driven. Replace with **SN74LVC125AD, DK 296-8453-5-ND** (74LVC, supply 1.65–3.6V, SOIC-14, 5V-tolerant inputs). Qty 5–10. *(Verified against datasheet 2026-06-18.)*

🟢 **Prior DigiKey order ($25.85, ×10 each) CONFIRMED covers:** LM393DR · BSS138 · 470µF/25V (UPW1E471MPD) · 100nF (CC0603) · **BHR-12-VUA J20 box headers** · SRR1260-220M (L1) · PRPC040 strip · full power-board 0603 R-set (10k/100k/4.7k/22k/470k/1M + **11.3k & 12.1k 1% trips**) · JST B3B-XH-A.

✅ **In current cart, correct:** MKDS SW1 block (277-1263) · SMBJ8.5A/SMBJ13A TVS · Teensy/Nano sockets (PPTC241/151) · J20 ribbon (IDSD-06-D-09.00).

🟡 **Final add-to-cart — logic-board parts in NEITHER prior order (all DK# verified 2026-06-18):**
| Part | DK # | Mfr P/N | Qty | Ref |
|---|---|---|---|---|
| SN74LVC125AD (SOIC-14) | 296-8453-5-ND | SN74LVC125AD | 5 | U7 (HC→LVC swap) |
| 1kΩ 0603 1% | 311-1.00KHRCT-ND | RC0603FR-071KL | 10 | logic R2–R6 (OLED SPI) |
| 22Ω 0603 1% | 311-22.0HRCT-ND | RC0603FR-0722RL | 10 | logic R1 (bus series) |
| 600Ω@100MHz ferrite 0603 | 490-5258-1-ND | BLM18KG601SN1D | 10 | logic FB1 (bus integrity) |
| 2.54 shorting jumper | S9001-ND | SPC02SYAN | 10 | JP_BUS_MASTER + JP1 |

Also: **delete SN74HC125D (296-1192-5-ND)** from the cart — wrong logic family.

🔴 **Q1 gate-harden parts (pending board edit — add to cart):**
| Part | DK # | Mfr P/N | Qty | Ref |
|---|---|---|---|---|
| 10kΩ 0603 1% | 311-10.0KHRCT-ND | RC0603FR-0710KL | ✅ prior order | R17 (gate series / soft-start) |
| **470nF 0603 X7R 25V** | **1276-1037-1-ND** | **CL10B474KO8NNNC** | 10 | **C_gs (soft-start cap) — NEW, ADD** |
| 18V zener SOD-123 | BZT52C18-FDICT-ND | BZT52C18-7-F | 10 | D1 (gate-source clamp, backstop) |
| 100kΩ 0603 1% | 311-100KHRCT-ND | RC0603FR-07100KL | ✅ prior order | R_gs (gate bleed, optional) |

**Q1 protection — ⚠️ MARGINAL, treat as backstop (2026-06-18, revised after deeper analysis):**
Q1 (IRLB3034) gate = VBAT_PROTECTED, source = BATT_NEG → **Vgs ≈ full pack (≤16.8V)**, Vgs(max)
= **20V** → only **3.2V headroom**. Hot-plug LC ring on VBAT (≈5470µF + lead L, no on-board TVS)
can ring to ~22–33V → Vgs > 20V → gate-oxide kill.

**PRIMARY fix = gate soft-start on Q1 (prevents the ring at the source):** Q1 is already the pass
element in the path. Add **C_gs (gate-source cap)** so the gate ramps slowly through R17 → Q1 turns
on gradually → bulk caps charge gently → **no abrupt step, no LC ring, no overshoot.** Same R17 does
double duty (soft-start + zener clamp current-limit).
- **R17 = 10kΩ** (NOT 100Ω/1k). Bigger = tighter zener clamp AND slower ramp. Clamp = Vz + Iz·Zz
  (Zz≈25Ω): 33V spike → Iz=(33−18)/10k=1.5mA → clamp ≈ **18.04V < 20V ✓**. Gate quiescent drop
  negligible (gate leakage only). (100Ω→~21V fail; 1k→18.4V ok; 10k→18.04V best.)
- **C_gs = 470nF.** τ = R17·C_gs = 10k·470n = **4.7ms**. LC ring period = 2π√(LC) ≈ 2π√(1µH·5470µF)
  ≈ **0.5ms**. Charge ramp (~3–5×... effectively spreads inrush over ~5–15ms) **≫ 0.5ms → overdamped,
  no ring.** C_gs (470nF) ≫ Ciss (~3nF) so it dominates the ramp.
- **D1 18V zener = backstop** for any residual transient. Tight (Vz 16.8–19.1V, low corner = full
  pack) but with soft-start preventing the ring it's rarely exercised.
- **R_gs 100k (optional)** gate-source bleed → defined gate + discharges C_gs on disconnect (clean
  turn-off). Q1 turn-off isn't safety-critical (reverse-prot; off when no battery) but good practice.
- **⚠️ SOA CHECK (gating):** during soft-start Q1 is in linear region dissipating the charge energy
  **½CV² = ½·5470µF·16.8² ≈ 0.77 J** over the ~5–15ms ramp. Must stay inside IRLB3034's SOA (check
  the 10ms single-pulse line). If marginal → use a **precharge resistor** (energy in R, not the FET)
  instead, or slow/speed the ramp. **This sets whether soft-start-on-Q1 is safe vs needs precharge.**
- **Cleaner alt if SOA fails:** precharge resistor (bypassed after), or gate divider (Vgs→~12V) +
  smaller zener, or a ±25V-Vgs FET.
- **BENCH-VALIDATE** the real VBAT transient on the scope (Phase-5) before trusting any of it. Do NOT
  fab assuming the gate is solved.

✅ **Received since (Amazon):** M3×20 standoffs, MRBF-30 + Blue Sea 5191, 12AWG wire, ring lugs, solder wick, bench gear (PSU / logic analyzer / 1Ω loads).

**Verify owned before fab:** XT30 ≥18 mating pairs · real 6000mAh pack physical dims (re-measure → `dimensions.md §5` + LiPo pocket, currently flagged).

---

## 1. Power conversion + charging

### ISDT 608AC LiPo charger — ~$60 ✅ ORDERED
- Modes needed: balance charge, **storage**, discharge
- On arrival: power up no-battery, verify storage-mode menu works, set LVC alarm to 3.3V/cell = 13.2V

### LiPo safe bag — ~$15 ✅ ORDERED
- Fireproof fiberglass bag sized for 4S 6000mAh packs (verify owned bag fits the larger pack)

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

### Gigabit Ethernet switch (5-port) — ~$15 ✅ ORDERED
- TP-Link LS105G or NETGEAR GS305 (5-port unmanaged gigabit)
- Plan to remove case for chassis volume (~60% volume savings)

### Cable Matters 10Gbps Snagless Cat 6 — 1ft, ×2 minimum (×3 with spare) — ~$8 ✅ ORDERED
- 30cm length, snagless boot, Cat 6 (gold-flashed per TIA/EIA-568 spec by default), 10 Gbps rated headroom
- Wiring: Jetson `enP8p1s0` ↔ switch port 1, L2 ↔ switch port 2 (port 3 spare for dev laptop)

### LC filter parts for L2 12V tap — ~$3
- 1× inductor: ~22 µH, ≥2A rated (DigiKey series-resonant choke)
- 1× electrolytic cap: 470 µF, 25V
- Bundle into the next DigiKey / Mouser order to save shipping

### 🔴 Class T 30A fuse + block — ~$40 (CRITICAL GAP found 2026-06-12 state-matrix review)
Spec'd in PCB README §1 since the beginning, F1 deliberately moved OFF-BOARD 2026-06-04
(LiPo dead-short = 10–20 kA; only Class T's 20 kA AIC interrupts it — see research notes
2026-05-17 §9) — **but it never entered this order list.** Right now the battery lead is
unfused: a chafed wire or dropped tool across VBAT is the one fire-class failure on the robot.
- ✅ **CHOSEN 2026-06-12: MRBF instead of Class T** — Blue Sea **5191 Surface Mount** block
  ($24) + **Bussmann MRBF-30** fuse (~$10). Engineering note: the 2026-05-17 Class T rationale
  assumed 10–20 kA short current (large-bank figure); this single 4S 4 Ah pack's real Isc =
  16.8 V ÷ ~6–12 mΩ ≈ **1.5–3 kA**, vs MRBF's 10 kA AIC (≈9 kA at 16.8 V) → 3–4× margin, at
  ⅓ the size/weight of a Class T block — better fit for the chassis. Class T (5007 + JJN-30)
  remains the upgrade path if the pack ever grows or parallels.
- Install: 5191 screwed to chassis near the pack; battery XT60 pigtail → 10 AWG ring → stud →
  MRBF-30 → output ring → J1 lead.
- Still banned: ANL/MIDI/blade (1–6 kA AIC — can fail-to-interrupt even on this pack).

### 🟡 LiPo balance-lead buzzer alarm — ~$5 (gap found 2026-06-12)
If the UBEC/V5_AUX dies mid-run, BOTH LM393 LVC stages go silently dead (R16 defaults rails
ON) and the Teensy dies with it — frozen robot drains the pack with no electronic protection.
Independent last line: balance-plug buzzer alarm set to **3.3 V/cell**, plugged in whenever
SW1 is on. ✅ OWNED (verified 2026-06-12): FLY RC 5-pack purchased 2026-05-16, pre-set 3.3 V.
Operational rule: buzzer rides the balance plug any time the robot is switched on.
- ✅ UBEC module VERIFIED OWNED (2026-06-12): SoloGood 5V/5A UBEC ×2, purchased 2026-05-03
  (input 5.5–35 V covers 4S; 5 A ≈ 10× the V5_AUX load; second unit = shelf spare).
  Buzzer still required — the spare doesn't help mid-run.

### ⚠️ TVS regen clamps for servo rails — ~$5 (gap found 2026-06-12, NOT in original order)
Covers the case the electrical review missed: **e-stop pressed mid-gait** → bucks disable
(output high-Z, can no longer sink regen to battery) → coasting legs generate into a rail whose
only sink is the bulk caps (1 J into 5000 µF from 7.5 V ≈ 21 V rail — over servo limits).
- **SMBJ8.5A ×5** (8.5 V standoff / ~14 V clamp) — DigiKey search `SMBJ8.5A` (Littelfuse/Vishay, ~$0.45)
- **SMBJ13A ×5** (13 V standoff / ~21.5 V clamp) — DigiKey search `SMBJ13A`
- Install OFF-BOARD: solder across the injection-point XT30 pigtails, **cathode (band) to +**.
  2× SMBJ8.5A on V7V5_LEG injections, 1× SMBJ13A on V12_HIP, optional 1× SMBJ13A on V12_L2.
  V12_JET needs none (Jetson input tolerates 9–20 V; buck output cap rides through).
- Normal-operation regen is already safe — Pololu bucks are synchronous and sink current back
  to the battery while enabled. The clamp only works during disable/e-stop windows.
- Bundle with the next DigiKey order (this section + LC filter above).

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
- ⚠️ **SHUNT SIZING — CRITICAL.** Stock CJMCU-226 breakout ships a **0.1 Ω** shunt → max ≈0.8 A (INA226 ±81.92 mV ÷ 0.1 Ω). **Leg (~9 A) and hip (~8 A) rails will saturate it.** Order the **high-current INA226 module with 2 mΩ (R002) shunt** (~20 A range) for leg + hip. Jet 12V (~2 A) also fine on R002.
- ✅ **ORDERED 2026-06-08:** "INA226 Voltage Current Monitor 0-36V **20A**" module — **GODIYMODULES** (sold by DIY-Module, Amazon, $12.88), **×4, arriving Thu Jun 11.** 4.2★/12 reviews, 50+ bought/mo. **R002 shunt confirmed in product photo** = 2 mΩ correct, measured −20A~20A. (Passed over Lufasa 1-review slow listing.) NOT the NOYITO B07PMNQ2DQ (R100/0.1Ω, saturates <1A) and NOT blue Qoroos 3-pack (R100). DigiKey doesn't stock this module class.
- 📏 **On arrival:** verify shunt reads `R002`, then MEASURE the module's real IN+/IN−/VCC-header pitch + VBUS pin location → fix the `nova_v6:INA226_Module_Breakout` footprint (pad 8/9 colocation) to match BEFORE fab.
- ⚠️ **FOOTPRINT MISMATCH — board `nova_pcb_v6_power` U9/U10/U11.** `nova_v6:INA226_Module_Breakout` stacks pad 8 (Vbus) on pad 9 (IN−) at identical XY → "drilled holes co-located" DRC error, ×3. Real modules expose **VBUS as its own header pin** (not internally tied to IN−). Fix footprint AFTER picking the exact module: either give VBUS its own landing at the module's real pitch, or delete the board pad and wire VBUS→IN− externally. descr already flags "VERIFY pitch + header vs module before fab."

### Comparator + MOSFET parts for hard-cutoff at 12.4V + graceful-shutdown at 13.0V — ~$13
- **Two comparator stages:**
  - 13.0V trigger → drives Teensy GPIO → `/battery_low` topic → Jetson `systemctl poweroff` (clean SD unmount)
  - 12.4V trigger → drives MOSFET on battery feed → autonomous hard cutoff
- **1× LM393** (dual comparator = both stages in one SOIC-8 chip) — board `nova_pcb_v6_power` U8 is a single LM393. Buy 1 + 1 spare, NOT 2. (TL431 alt would need 2×.)
- 1× IRLB3034PBF logic-level N-channel MOSFET (or similar Rds(on) <5 mΩ at Vgs=4.5V, Id ≥30A)
- 1× P-channel power MOSFET on the high side if doing high-side switching
- 2× trim-pot or precision resistor divider to set each trip point
- Bundle with DigiKey order

### Bulk caps for rail injection points — ~$5
- **5× 1000 µF / 25V** electrolytic — board `nova_pcb_v6_power` has C1–C5 (5×, not 4×). Buy 5 + spares.
- Exact SKU: Nichicon **UPW1E102MPD6** (12.5 × 25 mm body, **5 mm lead pitch** — matches footprint `CP_Radial_D12.5mm_P5.00mm`)
- One per star injection point on the leg 7.5V rail
- Absorbs servo impact transients near point of load

---

## 3b. PCB v6 on-board parts (matched to `nova_pcb_v6_power` board) — ~$25

> Added after a board↔order-list audit (51 footprints). These were missing from the original list — the board needs every one. Bundle connectors with the DigiKey electronics order; AMASS XT from Amazon/Mouser.

### Connectors
| Board ref | Part | Qty | Vendor / SKU |
|---|---|---|---|
| J1 | AMASS **XT60-M** vertical (battery in) | 1 | ✅ **ORDERED** SoloGood Amass **XT60H** 10-pair ($9.99). Verified vs J1 footprint (Ø4.5mm/7.2mm). ⚠️ Snap cover OFF the male before soldering. 30A rated > ~15A draw. |
| J3–J7, J12, J13 | AMASS **XT30U-M** vertical | 7 | — |
| U1–U5 buck offboard terminals | AMASS **XT30** ×2 per buck | 10 | each Pololu buck lands via 2×XT30 |
| **XT30 TOTAL** | **17 board positions** (7 + 10) + cable mates | ✅ **2× 10-pair pack ordered** | SoloGood "10 Pairs XT30 Amass XT30U" ×2 ordered 2026-06-08 (20M+20F, covers 17 board + mates + spares). Males→board (vertical footprint), females→leads. |
| J8 | JST **B3B-XH-A** 1×03 2.5 mm (servo bus TTL) | 1 | DigiKey **455-2247-ND** — [link](https://www.digikey.com/en/products/detail/jst-sales-america-inc/B3B-XH-A/1651046) |
| J2 + M1 | PinHeader 1×03 + 1×02 2.54 (UBEC aux + voltmeter) | 1 strip | Sullins **`PRPC040SAAN-RC`** 40-pin breakaway, snap to length (covers both) |
| J20 | IDC box header **2×06 2.54 shrouded vertical THT** (interboard) | 1 | Würth WR-BHD series — [filter](https://www.digikey.com/en/product-highlight/w/wurth-electronics/wr-bhd-series-box-headers-and-idc-connectors), pick 12-pos 2.54 |
| SW1, SW2 | TB132 footprint = **5mm pitch, 1.2mm drill = standard KF301**. 1×02 PCB screw block | 2 | ✅ **ALREADY HAVE** — Tugermoola 72pc 5mm 2/3/4-pin kit (bought 2026-05-03) has KF301-style 2-pin blocks that drop in. Use 2. ⚠️ Kit rated **10A**; SW2 (mA) fine, **SW1 carries ~15A** → undersized, runs warm. 🔴 NOT OPTIONAL (2026-06-12 review): buy a **15–20 A rated 5 mm-pitch 2-pin block** for SW1 (same KF301/TB132 footprint — search "KF301 16A" or Phoenix MKDS 1.5/2). $3, bundle with next order. |

### SW1 main power switch (off-board, wires to SW1's TB132)
- ✅ **CHOSEN (2026-06-08): Blue Sea Systems Contura SPST, "Off-on" style** ($17.40, Prime). Carling VJB1 body.
- **Rated 20A @ 12VDC, 15A @ 24VDC** — explicitly covers 4S 16.8V (~18A capacity) at the ~15A battery draw. UL 1500, ISO 8846 ignition-protected, sealed/vibration/salt-resistant.
- Why this over alternatives: switches whole battery (VBAT→VBAT_PROTECTED). Rejected KCD4 "30A 250VAC" (AC-only rating, DC breaking ≪15A; lamp needs AC 110V) and the 12V-only Carling listings (didn't document the 24V rating). Blue Sea documents 15A@24VDC in writing.
- Wiring: SPST terminal A → VBAT (TB132 screw 1), terminal B → VBAT_PROTECTED (TB132 screw 2). Screw terminals.
- ⚠️ **Return the Kodrily inline XT60 switch** (wrong: 18AWG undersized for 15A, electronic-latch redundant w/ Q1, XT60 pigtails don't land on TB132). Prime free return.

> ⚠️ Buy **genuine AMASS** XT30/XT60 — clones have loose tolerance on power connectors (heat, intermittent contact under servo transients).

### SMD passives (0603) — Yageo **RC0603FR-07** series, 1 % (DigiKey, search the MPN)
| Value | Qty | DigiKey MPN | Refs |
|---|---|---|---|
| 10k | 5 | `RC0603FR-0710KL` | R5, R7, R8, R9, R13 |
| 100k | 2 | `RC0603FR-07100KL` | R2, R10 |
| 4.7k | 2 | `RC0603FR-074K7L` | R11, R12 |
| 22k | 1 | `RC0603FR-0722KL` | R3 |
| **11.3k** (1 %) | 1 | `RC0603FR-0711K3L` | R4 — divider trip-point |
| **12.1k** (1 %) | 1 | `RC0603FR-0712K1L` | R6 — divider trip-point |
| 470k | 1 | `RC0603FR-07470KL` | R14 |
| 1M | 1 | `RC0603FR-071ML` | R15 |
| 100nF | 1 | `CC0603KRX7R9BB104` (Yageo X7R) | C7 — decoupling |

> R4 (11.3k) + R6 (12.1k) set the comparator trip points → buy **1 % or tighter**. Rest can be 5 %. Buy spares; these are sub-cent each.

### Discretes (DigiKey, same order)
| Ref | Part | DigiKey link / note |
|---|---|---|
| Q1 | **IRLB3034PBF** TO-220 | ⚠️ obsolete at DigiKey → **Amazon/Mouser**. [DK page (sub only)](https://www.digikey.com/en/products/detail/infineon-technologies/IRLB3034PBF/2096638) |
| Q2 | **BSS138** SOT-23 | https://www.digikey.com/en/products/detail/onsemi/BSS138/244210 |
| U8 | **LM393DR** SOIC-8 (dual = both stages, buy 1+spare) | https://www.digikey.com/en/products/detail/texas-instruments/LM393DR/276659 ($0.22, 127k stock) |
| C6 | **470µF 25V** Nichicon **UPW1E471MPD** (10×16mm, 5mm pitch ✓) | https://www.digikey.com/en/products/detail/nichicon/UPW1E471MPD/589567 |
| L1 | **SRR1260-220M** 22µH (12.5×12.5×6mm — verify land vs `L_12x12mm`) | https://www.digikey.com/en/products/detail/bourns-inc/SRR1260-220M/1969958 |

---

## 4. Mechanical consumables

### Loctite 243 blue threadlocker — ~$8 ✅ ORDERED
- Bottle (re-used on every servo bracket)

### Electrical tape + Kapton tape — ~$10 ✅ ORDERED
- 3M Super 33+ electrical tape (NOT generic vinyl)
- Kapton tape, 10mm wide, for IMU / OLED insulation + LiDAR mast strain points

### Bambu Lab Liquid Glue — using existing supply
- Using Bambu's liquid glue on textured PEI for PA6-CF adhesion
- ⚠️ Bambu's stock liquid glue is generic-purpose, not nylon-specific. **Print-test before committing to batch:** if PA6-CF first layer doesn't bond well, fallback to Magigoo PA (~$15) or similar PA-specific adhesion product.

---

## 5. Display

### ~~DisplayPort cable / DP→HDMI adapter~~ — $0 ❌ NOT NEEDED
- Jetson initial setup completed headless (SSH from Mac), no direct console required.
- If a recovery scenario ever needs a console: borrow / order a DP→HDMI active adapter then. Not pre-emptive.

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
| Pololu D42V55F12 (Jetson) #5577 | 32 | ✅ Got |
| Pololu D42V110F7 (leg) #5674 | 60 | ✅ Got |
| Pololu D42V110F12 (hip only) #5677 | 60 | ✅ Got |
| Pololu D24V22F12 (L2 dedicated) #2855 | 19 | ✅ Got |
| INA226 ×3 (HIGH-CURRENT 2mΩ for leg+hip) + 1× LM393 + MOSFETs + 5× bulk caps | 35 | 🆕 To order |
| PCB on-board connectors (2× XT30 10-pk, XT60 pair, JST, headers, IDC, 2× TB132) | 28 | 🆕 To order (audit add) |
| SMD passives (0603 R-set + C7) | 5 | 🆕 To order (audit add) |
| ~~74HC125~~ — on logic board, not this power board | 0 | n/a here |
| E-stop button (Mxuteuk HB2-ES544) | 10 | ✅ Ordered |
| Switch + Cat6 ×2 (Cable Matters 1ft) | 23 | ✅ Ordered |
| LC filter parts (inductor + cap) | 3 | 🆕 To order (DigiKey bundle) |
| Threadlocker + tape | 18 | ✅ Ordered |
| ~~Magigoo PA~~ → Bambu liquid glue | 0 | ✅ Using existing |
| ~~DP adapter~~ | 0 | ❌ Not needed (headless Jetson) |
| **Subtotal (actual remaining spend)** | **~$250** | (was ~$217; +$33 connectors/passives audit add) |

Updates since v3.4:
- ISDT 608AC + LiPo bag + E-stop: ordered ✅
- Ovonic kit confirmed includes XT60 jumper + charging lead → $13 saved
- Bambu liquid glue substituted for Magigoo PA → $15 saved (with fallback if PA6-CF adhesion fails)
- Network bundle (switch + Cable Matters 1ft Cat 6 ×2-3): ordered ✅ 2026-05-17
- Threadlocker + tape: ordered ✅ 2026-05-21
- DP adapter dropped — Jetson set up headless via SSH; revisit only if a console-required recovery scenario hits → $10 saved
- $371 worst case → **$217 actually-need-to-order**

Not included: PCB v6 (~$60), arm servo top-up (~$50).

---

## Ordering strategy

1. **Bundle by vendor** to minimize shipping (✅ ordered items removed):
   - **Amazon:** INA226 breakouts (if not on DigiKey)
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
   - **Arm-rail D42V55F7 (board U5)** — Phase 4. ⚠️ The footprint IS placed on `nova_pcb_v6_power` (U5), but the part is deferred. Board has **5 buck footprints, order only 4** (U1–U4). Leave U5 unpopulated.
   - PCB v6 — until schematic + Gerbers complete
   - Spare bearings / spare servo — order with the next Feetech batch when you actually need them

4. **Open before fab (from board↔BOM audit 2026-06-08):**
   - INA226 shunt: order **2 mΩ high-current** modules for leg+hip, not stock 0.1 Ω CJMCU (saturates <1 A)
   - INA226 footprint colocation DRC error (×3) — fix after module chosen
   - Verify XT30/XT60 are genuine AMASS

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
- [ ] **INA226 bench-test each of 4 modules BEFORE soldering to board** (modules arrive ~Jun 9; catches DOA + the "reads 0 A" calibration trap behind the 1-star reviews):
  - [ ] Visual: shunt next to screw terminal reads **`R002`** (2 mΩ). If `R100`/`R000` → wrong part, return.
  - [ ] ⚠️ Do NOT ohm-meter the shunt — a 2 mΩ shunt reads ~0 Ω on any handheld DMM (lead R ≈ 0.2–0.5 Ω swamps it). "Zero ohms" on a meter is normal, not a fault.
  - [ ] Power VCC 3.3–5 V, I²C scan → must ACK at **0x40** (A0/A1 unsoldered = default)
  - [ ] **Set Calibration register (0x05) for Rshunt = 0.002 Ω** — NOT the library default 0.1 Ω. `CAL = 0.00512 / (current_LSB × Rshunt)`; pick current_LSB ≈ 1 mA → CAL = 0.00512 / (0.001 × 0.002) = 2560 (0x0A00). This is the step the 1-star reviewer skipped → he got 0 A.
  - [ ] Pass a known current (e.g. 2 A bench load through IN+→IN−) → reading matches within a few % → module good. Repeat all 4, label the spare.
- [ ] Verify INA226 ×3 I²C reads (current + voltage) under nominal and loaded states (on-board, after the per-module bench test above)
- [ ] Switch power test: 5V UBEC → switch → all 5 ports link-up
- [ ] LC filter measurement: scope the D24V22F12 output (L2 feed) for ripple at ~400 kHz buck switch frequency, before/after the LC, both at idle and under L2 active load

> Status: updated at BOM v3.4. Update with actual SKUs / order #s as items hit Cart.
