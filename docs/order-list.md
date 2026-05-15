# Committed Order List — Phase 0 Final Pass

One-shot consolidated checkout for the BOM v3.1 committed adds (~$187, ISDT 608AC charger path). Each item below has primary + backup vendor/SKU options. **Verify in-stock + ship-by date before clicking buy.**

> NVMe is intentionally NOT on this list — deferred until NAND prices recover (<~$100 for 1TB). See BOM §1 + open decision row 8.

---

## 1. Power conversion + charging

### ISDT 608AC LiPo charger — ~$60
- **Primary:** ISDT direct (`isdt.co`) or HobbyKing — confirm "608AC" (AC variant, not 608PD)
- **Backup:** Amazon (verify it's the authentic ISDT SKU, not a clone)
- Modes needed: balance charge, **storage**, discharge

### LiPo safe bag — ~$15
- **Primary:** Amazon — fireproof fiberglass bag sized for 4S 4000mAh packs
- Look for: zipper closure, ≥240×180×65 mm internal

### XT60 jumper (for 608AC battery input) — ~$5
- ⚠️ **Likely already have:** Ovonic 4S LiPo packs typically ship with XT60 leads + accessories. **Verify on arrival before ordering.**
- **Fallback primary:** Amazon / HobbyKing — XT60 female ↔ banana-plug pigtail (or whatever the 608AC input expects — confirm with charger datasheet on arrival)
- Could also build from leftover 18AWG silicone wire + spare XT60

### XT60 charging lead — ~$8
- ⚠️ **Likely already have:** Ovonic LiPo kit reportedly included the XT60 ↔ JST-XH charging lead. **Verify on arrival before ordering.**
- **Fallback primary:** HobbyKing — XT60 ↔ 4S JST-XH balance lead
- Make sure the JST-XH end matches the LiPo's balance plug (5-pin for 4S)

### Pololu D24V50F12 — ~$20
- **Primary:** `pololu.com` direct (most reliable for genuine part)
- **Backup:** DigiKey / Mouser (same part #)
- **Why this part:** 12V/5A out, 7-22V in, ~90% efficiency, has UVLO. Drives Jetson barrel jack from 4S LiPo.

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

## 3. Mechanical consumables

### Loctite 243 blue threadlocker — ~$8
- **Primary:** Amazon / hardware store
- Get the **bottle** not single-use vials (you'll re-use it on every servo bracket)

### Electrical tape + Kapton tape — ~$10
- 1× 3M Super 33+ electrical tape (NOT generic vinyl)
- 1× Kapton tape, 10mm wide, for IMU / OLED insulation + LiDAR mast strain points

### Magigoo PA glue stick — ~$15
- **Primary:** Magigoo direct or Matterhackers
- Specifically the **PA** (nylon) formula — not generic Magigoo
- Required for PA6-CF first-layer adhesion on Bambu textured PEI

---

## 4. Display

### DisplayPort cable OR DP→HDMI adapter — ~$10
- **Primary:** Amazon — pick based on monitor: DP-to-DP if monitor has DP input, DP-to-HDMI active adapter otherwise
- **Note:** Jetson Orin Nano Dev Kit has DP only (no HDMI). Passive adapters work for HDMI 1.4-class monitors; if monitor is 4K@60Hz you need an active adapter.

---

## 5. Servo top-up (not in $187 subtotal — separate spend)

### STS3215 7.4V 19kg × 2 (complete 8-count for legs) — ~$50
- **Primary:** Feetech AliExpress store (slow but cheapest)
- **Backup:** Amazon — verify they're genuine Feetech, not clones (clones have inconsistent center calibration)
- Already have ~6 of 8 needed; buy 2 + ideally 1 spare = 3

---

## Total committed-adds spend at checkout

| Line | $ |
|------|----|
| ISDT 608AC | 60 |
| LiPo safe bag | 15 |
| XT60 jumper | 5 (⚠️ skip if Ovonic kit included one) |
| XT60 charging lead | 8 (⚠️ skip if Ovonic kit included one) |
| Pololu D24V50F12 | 20 |
| Switch + Cat6 ×2 + LC parts | 26 |
| Threadlocker + tape | 18 |
| Magigoo PA | 15 |
| DP adapter | 10 |
| **Subtotal (worst case)** | **~$177** |
| **Subtotal if Ovonic supplied leads** | **~$164** |

Add ~$10 shipping buffer across vendors → BOM §13 **~$187** (worst case) or **~$174** (Ovonic leads included).

---

## Ordering strategy

1. **Bundle by vendor** to minimize shipping:
   - **Amazon:** safe bag, threadlocker, tape, DP adapter, Cat6 cables, switch
   - **Pololu direct:** D24V50F12 (consider grabbing spare USB-serial or a cheap multimeter probe to amortize shipping)
   - **DigiKey or Mouser:** LC filter parts (inductor + cap) — bundle with anything else electronics-shaped you've been deferring
   - **HobbyKing / ISDT direct:** 608AC + XT60 leads (one shop)
   - **Feetech / AliExpress:** servo top-up (separate, slow boat)

2. **Verify before pulling trigger:**
   - 608AC vs 608PD (you want AC)
   - DP cable matches your actual monitor input
   - JST-XH balance lead is 5-pin (4S, not 3S/6S)
   - Switch SKU explicitly "gigabit" not "fast ethernet 10/100"

3. **Don't order yet:**
   - NVMe — wait for NAND price recovery
   - Spare bearings / spare servo — order with the next Feetech batch when you actually need them

---

## After things arrive

- [ ] Power up 608AC with no battery — verify storage-mode menu works
- [ ] Bench-load Pololu D24V50F12 → 12V out under Jetson MAXN draw
- [ ] Switch power test: 5V UBEC → switch → all 5 ports link-up
- [ ] LC filter measurement: scope the 12V hip rail under servo load, before/after the LC tap, for the L2 power feed

> Status: drafted at v0.2.0-bom-v3.1. Update with actual SKUs / order #s as items hit Cart.
