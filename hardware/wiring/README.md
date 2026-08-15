# Wiring Diagrams

Power rail map and signal/data wiring for the as-built robot. Refer to BOM v3.4 + `hardware/pcb-mods/README.md` (PCB v6 spec) + `docs/power-budget.md` (current math) for source-of-truth values.

## Power chain (4S LiPo → 4 active rails + 1 reserved)

```
                              ┌─── MRBF-30 terminal fuse (Blue Sea 5191 block, 30A / 58V DC)
                              │
4S LiPo 14.8V (12.8-16.8V) ──┼── MOSFET reverse-polarity protection
   (Ovonic 6000 mAh × 2)     │
                              ├── E-stop NC (Mxuteuk HB2-ES544, 22 mm latching)
                              │        │ kills leg + hip + L2 + arm EN (EN_BUCKS)
                              │        │ Jetson rail stays live for debug
                              │
                              ├── MOSFET hard-cutoff @ 12.4V (comparator-driven)
                              │
                              └─┬─ Pololu D42V110F7  → 7.5V/10A → leg rail
                                │                                 (8× STS3215 19kg femur/tibia)
                                │                                 ★ 4× XT30 star injection
                                │                                 1000 µF / 25V bulk cap at each
                                │
                                ├─ Pololu D42V110F12 → 12V/9A   → hip rail
                                │                                 (4× STS3215 30kg ONLY)
                                │                                 XT30 injection at chassis floor
                                │
                                ├─ Pololu D24V22F12  → 12V/2.6A → L2 LiDAR (dedicated)
                                │                                 LC filter on output:
                                │                                 22 µH choke + 470 µF / 25V cap
                                │
                                ├─ Pololu D42V55F12  → 12V/~3A  → Jetson barrel jack (5.5 × 2.5)
                                │
                                ├─ [reserved D42V55F7] → 7.5V → arm rail (Phase 4 unstuffed)
                                │
                                └─ UBEC 5V/5A        → 5V       → fans + aux 5V
                                                                  (Ethernet switch dropped
                                                                   2026-08-14 — off the robot)
```

## Safety chain trip points (highest pack voltage first)

| Trip | Pack V | Cell V | Action |
|------|--------|--------|--------|
| 1 | 13.2 V | 3.30 V/cell | 608AC charger LVC alarm (user-facing beep) |
| 2 | 13.0 V | 3.25 V/cell | LM393 comparator → Teensy GPIO **pin 4** → `/battery_low` Bool → Jetson `systemctl poweroff` (clean SD unmount). ~30-60 s window. |
| 3 | 12.4 V | 3.10 V/cell | Second LM393 stage → **BSS138 (Q2) pulls EN_BUCKS low → all bucks off** (leg/hip/L2/arm); Q4 also kills Jetson EN. Autonomous backstop. (Q1 IRLB3034 = reverse-polarity protection, separate — does NOT break the battery feed.) |
| — | — | — | E-stop (manual, SW2 NC) — pulls EN_BUCKS low via Q3 → kills leg + hip + L2 + **arm** buck EN. Jetson stays alive. |

## Feetech TTL bus (single-ended half-duplex, 1 Mbps default)

```
Teensy 4.1                    SN74LVC125A (quad tri-state buffer)         Bus pad
  Serial1 TX (pin 1) ─────────► gate1 input                           ┐
  Serial1 RX (pin 0) ◄───────── gate2 output                          │
  OE̅_TX (pin 2, active-LOW) ──► gate1 enable (LOW = drive TX → bus)    │
  OE̅_RX (pin 3, active-LOW) ──► gate2 enable (LOW = listen bus → RX)   ▼
                                                       12× STS3215 daisy chain
                                                       PER-LEG SEQ (ID = chain order):
                                                       FL 1-3 · FR 4-6 · RL 7-9 · RR 10-12
                                                       leg = haa,hfe,kfe — haa(1,4,7,10)=12V,
                                                       hfe/kfe=7.5V (see joint_id_map.yaml)
                                                       IDs 13-18 reserved (Phase 4 arm)

JP_BUS_MASTER solder bridge:
  default = B (Teensy → SN74LVC125A → bus)
  alt     = A (FE-URT-1 → bus, for ID assignment + bench debug)
```
> Source of truth for these pins = `firmware/teensy/firmware/src/main.cpp` (Serial1 0/1, OE̅ 2/3) + the `nova_pcb_v6_logic` netlist.

**Bus integrity footprints on PCB v6 (populate per measured error rate):**
- Series R (22 Ω, R1 0603) + ferrite (FB1) at SN74LVC125A output — slope rate-limiting / EMI
- Ferrite bead at each servo entry — common-mode noise rejection
- Star-ground reference — **implemented by the solid GND.Cu inner plane** (single low-Z return; the plane supersedes a literal star for this single-ended TTL bus — no separate star wiring at FE-URT-1)
- **NOT** 120 Ω differential termination — Feetech bus is single-ended TTL, not RS-485

**Cable plan:** Feetech daisy-chain cables (ordered), one ferrite bead per servo entry (footprint on PCB), GND-plane reference (the GND.Cu plane is the single low-Z return — see above). If errors persist after populating: drop baud 1M → 500k → 250k.

**⚠️ DUAL-VOLTAGE BUS — VCC-isolated boundary links (FRY-CRITICAL, added 2026-06-22):**
ONE shared signal, TWO power voltages. Under the per-leg-sequential ID map, **each haa (hip) = 12V (IDs 1,4,7,10); each hfe/kfe = 7.5V**. The chain runs haa→hfe→kfe per leg, so 12V↔7.5V transitions occur BOTH within a leg (haa→hfe) AND between legs (kfe→next leg's haa). A stock 3-wire Feetech cable carries GND+VCC+Signal — daisy a 12V servo straight to a 7.5V servo and the VCC wire bridges 12V↔7.5V → short / fried servo.

Required harness:
- **Power injected per voltage segment:** 12V to hips (V12_HIP), 7.5V to femur/tibia (V7V5_LEG star injection). Every servo's VCC pin must see its correct rail.
- **At every 12V↔7.5V transition** — haa→hfe WITHIN each leg (×4) AND kfe→next-haa BETWEEN legs (×3) = **7 boundaries** (the earlier "4 hip→femur" undercounted the 3 between-leg ones): use a **SIGNAL+GND-only link (VCC pin pulled/cut)**. Simplest + safest: make **ALL inter-servo cables signal+GND-only** and inject each servo's VCC locally from its rail — then there's no boundary to miscount. NO stock 3-wire cable across a voltage boundary.
- **Meter-verify every servo VCC = its correct rail (7.5 vs 12V) BEFORE the chain sees power.** #1 fry path on the build (pre-power-on §1c).

**Per-link build recipe (how a servo gets power when no cable carries VCC servo-to-servo):**
The STS3215's two 3-pin ports are internally paralleled (all 3 pins bussed straight through), and
the servo doesn't know where each wire came from — power and signal merge **in the connector**, not
on the servo. Each servo-side plug is assembled from three sources:

| pin | comes from |
|---|---|
| VCC | spur off the servo's **local XT30 injection** — 7.5V (J3–J6) for hfe/kfe, 12V (J7) for haa |
| GND | common star ground — **AND kept continuous through every daisy link** (it's both power return and the data line's signal reference; GND following the signal wire = less noise) |
| Data | daisy chain from the previous servo (chain entry = J8 pin 3) |

Steps per link: stock Feetech 3-wire cable → **pull the VCC pin from the upstream end** → crimp the
XT30-fed VCC branch into the servo-side housing. Result: signal path unbroken J8→servo1→…→servo12,
power a star from the XT30s, and a 12V↔7.5V boundary is physically impossible to miscount.

**Connector housings — don't mix:** servo ports are **Molex 5264-style 2.54mm** (Feetech standard);
**JST-XH is the board side only** (J8 pigtail). Don't crimp XH housings for servo ends. Chain entry
from J8 uses **GND + Signal only** — J8's VCC pin (V7V5_LEG) feeds nothing under this plan.

Cables still needed: **extension daisy cables for long leg runs** (Feetech/AliExpress — the ⬜ master-bom item never received) + the **VCC-isolated boundary jumpers** (make by pulling the VCC pin from a stock cable).

**Cable length:** ~2 m total harness. Community reports 12 m / 8 axes workable, so 2 m / 12 nodes is well within margin.

## INA226 telemetry topology

```
Teensy 4.1                          I²C bus (separate from Arduino Nano aux bus)
  SDA (pin 18) ──┬────────────────┬────────────────┬────────────────┐
  SCL (pin 19) ──┤                │                │                │
                 ▼                ▼                ▼                ▼
            INA226 0x40       INA226 0x41       INA226 0x44       INA226 0x45
            leg 7.5V          hip 12V           Jetson 12V        L2 12V
            shunt: 2 mΩ       shunt: 2 mΩ       shunt: 2 mΩ       shunt: 2 mΩ
            GODIY 20A R002 modules (all 4) — firmware setMaxCurrentShunt(20, 0.002)

  → /power_rails Float32MultiArray @ 10 Hz: [leg_v, leg_a, leg_w,
                                              hip_v, hip_a, hip_w,
                                              jetson_v, jetson_a, jetson_w]
```

**Current-sense wiring (CRITICAL — PCB carries NO shunt; R13/R14 deleted):** the INA226 reads current only if the rail flows through its onboard 2 mΩ shunt (IN+→IN−). The board exposes just I²C+power; IN+/IN− are the module's **screw terminals** → wire **inline in the harness**: rail source → IN+ → shunt → IN− → load.
- **Hip (0x41 @ J7) / Jetson (0x44 @ J12) / L2 (0x45 @ J13):** single XT30 injection → insert the module there → full rail current. ✓
- **Leg (0x40):** rail stars into **4× XT30 (J3–J6) on the PCB** → no single point carries total leg current. **DECISION 2026-06-26: DEFERRED (not needed for v1).** ⚠️ Leg INA reads **nothing** unless IN−/VBUS is **tapped to the leg rail** at assembly (board wires only I²C+power; IN± = module screw terminals, VBUS tied to IN−): **tap IN− → `leg_v` valid, `leg_a` invalid** (no inline shunt) = voltage-only; **leave IN− unwired → BOTH `leg_v` and `leg_a` invalid** (not just current). Total leg current has no clean inline point (4× XT30 star) regardless. Leg stall/over-current is covered by **per-servo STS3215 load** (`effort[]` on the bus); hip/Jetson INA cover rail current. Adding total-leg sense (RAW/clean split + sense-loop connector at U1 VOUT) is a **v7-rev** item only if board-level total-leg-power logging is ever wanted — see scope in chat 2026-06-26.

**4th INA (0x45):** v1 → **L2 rail** (matches firmware `INA226_ADDR_L2`; enable `-D NOVA_INA226_L2`). L2 monitoring is *optional* (low-power dedicated rail, alive from its data stream) but you have the module → use it. **Arm rail (Phase-4)** is margin-thin (0.83× peak) → it wants its own INA: add a **5th off-board module at 0x46** when the arm goes in (no board change — taps the same I²C bus). The board's `U12 = arm` label is Phase-4-aspirational; for v1 wire U12's shunt into the **L2** rail.

I²C pull-ups: **4.7 kΩ** to 3.3 V on SDA + SCL (R11/R12 on the power board, near the INA226s).

## Arduino Nano peripheral map (reduced per BOM v3.5 cut)

No I²C aux bus anymore. PIR / ultrasonic / DFPlayer / MPU-6050 dropped
because D456 + L2 perception stack covers their roles. Nano's only job
is to drive the OLED + LED strip from data received over USB-serial from
the Jetson.

```
Jetson ──USB-serial (115200)──► Arduino Nano
                                  │
                                  ├──SPI──► SSD1331 96×64 OLED
                                  │         (MOSI D11, SCK D13, CS D10,
                                  │          DC D9, RST D8)
                                  │
                                  └──GPIO──► WS2812B RGB LED strip
                                            (data D6, 800 kHz)
```

Power: 5 V from UBEC rail. ~0.3 A combined (OLED + 4 LEDs at moderate
brightness).

## USB topology (Jetson Orin Nano Super, P3766)

| Port | Cable | Device | Notes |
|------|-------|--------|-------|
| USB 3.1 (blue, USB-A) | USB 3.1 shielded | Intel RealSense D456 | Color + Depth + IMU (~2-3 W streaming) |
| USB-A | USB-A → micro-USB | Teensy 4.1 | micro-ROS over USB-CDC, agent at `/dev/ttyACM0` |
| USB-A | USB-A → USB-mini | FE-URT-1 | Bench-only (Pattern A fallback for ID setup) |
| USB-C UFP | (optional) | Mac host | Serial console + l4tbr0 USB-C bridge (warning: hijacks default route — see `docs/setup-network.md` Gotcha 2) |

## Ethernet topology

**No switch on the robot (2026-08-14).** The L2 and the Jetson are the only two
nodes that have to talk in flight, and both already carry static addresses — so
they go POINT-TO-POINT and the 5-port switch stays on the bench.

```
Unitree L2 LiDAR                          Jetson Orin Nano
  IP: 192.168.1.62   ──── Cat 6 ────►       enP8p1s0: 192.168.1.2/24
  UDP target: 6101      (1 ft, direct)      (static via nmcli, connection nova-lan)
```

Dev access ON the robot is the Jetson's built-in WiFi. When a laptop needs to
be on the same wired segment (bench sessions), put the switch back in the middle
— it is unchanged gear, just not carried.

Cable: Cable Matters 10 Gbps snagless Cat 6 (1 ft) × 1 on the robot; the rest
are spares/bench.

> `docs/setup-network.md` recorded this same decision on **2026-07-10** ("switch
> is BENCH-ONLY, robot goes L2-DIRECT") and every other networking doc kept
> describing the switch for another month. If you are changing the topology,
> grep for it — it is written down in more places than you expect.

## Wire gauge convention

| Wire | Gauge | Use |
|------|-------|-----|
| 18 AWG silicone | 18 AWG | Servo power (7.5 V + 12 V rails), battery feed to bucks |
| 22 AWG hookup | 22 AWG | Signal-level (INA226 I²C, comparator outputs, E-stop GPIO, RGB LED data) |
| Feetech TTL daisy-chain | 28 AWG (vendor) | Servo bus signal + power passthrough **within one voltage segment only** (see dual-voltage note — no power across 12V↔7.5V boundary) |

## Color code

- **Red:** +V (positive supply, all voltages)
- **Black:** GND (common)
- **Yellow:** signal (logic-level, GPIO)
- **Green:** I²C SDA / SCL (preserve white-on-green if available)
- **Blue:** UART data
- **Orange:** safety (E-stop, comparator output)

## Header wiring — insulation and clearance at `M1` / `J2`

Added 2026-08-13, after the flying leads on both headers were soldered. Nothing in
this repo covered it: the section below is mechanical *routing*, and `BUILD_PLAN.md`
covers what to solder, not what the wire does after the joint cools.

`M1` (pack-voltage tap) and `J2` (UBEC aux tap) are the only 2.54 mm headers carrying
**raw pack voltage next to GND**. Pad nets read out of
`../pcb-mods/nova_pcb_v6_power_v2/nova_pcb_v6_power_v2.kicad_pcb`:

| pair | gap | if they touch |
|---|---|---|
| `M1`.1 `VBAT_PROTECTED` ↔ `M1`.2 `GND` | **2.54 mm** | dead short across the pack |
| `J2`.1 `VBAT_PROTECTED` ↔ `J2`.2 `GND` | **2.54 mm** | dead short across the pack |
| `J2`.2 `GND` ↔ `J2`.3 `V5_AUX` | **2.54 mm** | shorts the UBEC output |
| **`J2`.1 `VBAT_PROTECTED` ↔ `J2`.3 `V5_AUX`** | **5.08 mm** | **16.8 V onto the 5 V rail** |

**The last one is the expensive one, and it is not obvious from the board.** `V5_AUX`
is the *only* supply for every active part on the logic board — traced from
`nova_pcb_v6_logic.kicad_pcb`:

| pad | part | why 16.8 V kills it |
|---|---|---|
| `U6`.1 | **Teensy 4.1 VIN** | 5.5 V absolute max. It is the Teensy's only 5 V input, and its regulated `T3V3` is what sources `+3V3` for `U7` — which is also why `BUILD_PLAN.md` §7 says cut the `VUSB`↔`VIN` pad before seating it |
| `U12`.27 | **Nano 5V pin** | bypasses the Nano's regulator and lands on the ATmega VCC directly. Confirmed by the netlist: pad 30 is `unconnected-(U12-VIN-Pad30)`, so the board feeds 5V, not VIN |
| `J10`.2 | SSD1331 OLED | 5 V module |
| `J11`.1 | WS2812B strip | 5 V module |

One contact kills all four at once, and nothing announces it until power-up.

A short across the pack clears through the off-board MRBF-30, but that is hundreds of
amps for the milliseconds before it opens, through 22 AWG, with `Q1` carrying the fault.

⚠️ `J2` is also the most crowded joint on the board — **four wires into three holes**,
because the SoloGood UBEC has separate input and output grounds that common at `J2`.2.
See `../../docs/order-list.md` §"Wiring to `J2`".

Note `SW1` sits between `VBAT` and `VBAT_PROTECTED`, so all of this is dead with the
rocker off. That is not a mitigation — the exposure is every minute the robot runs.

### Insulation doctrine

1. **Heatshrink is primary.** Ginsco assortment, `../../docs/master-bom.md:232`, which
   already specs it for "every XT / TVS / fuse joint" — this is that class of joint.
   Slide the sleeve on **before** soldering, park it up the wire, solder, trim flush,
   then bring it down over the joint. Doing it after means you cannot get a sleeve on
   without desoldering.
2. **Kapton is for zones a sleeve cannot reach**, not for whole joints. Its silicone
   adhesive lifts off round surfaces under vibration and thermal cycling, it gives no
   strain relief, and a lifted edge re-exposes the joint silently. As a patch on an
   already-soldered joint, or laid flat over the top of a header as a barrier against
   something landing on it from above, it is the right tool.
3. **On a 3-way header, wrap the MIDDLE pin.** One wrap on `J2`.2 blocks both `1↔2`
   and `2↔3`, and leaves only the widest pair (`1↔3`, 5.08 mm) with a wrapped conductor
   physically between them. Cheapest coverage per wrap. Done on the build board
   2026-08-13.
4. **Exposed conductor between the shrink and the joint is an electrical non-issue and
   a mechanical one.** Air breaks down near 3 kV/mm, so 2.54 mm against 16.8 V has
   about five orders of margin — nothing jumps that gap. But shrink that stops short
   leaves the bare zone at the **pin base**, which is exactly where the two conductors
   are closest; further up the wires diverge. Close it with Kapton if it is more than a
   millimetre or so.
5. **Dress both harnesses outward in −y at the joint** — see the clearance note below.

### The logic board overhangs both headers

Both boards share one coordinate frame (`H1`–`H4` at x 103/177, y 63/129 on each), and
the logic board's outline overhangs its own mounting holes by **6.00 mm** in −y — its
Edge.Cuts run y 57.00–135.00 against holes at 63/129. So **the logic board's near edge
lands at y = 57.00**, and that edge crosses between pin 1 and pin 2 of both headers:

| pad | y | vs the logic-board edge |
|---|---|---|
| `M1`.1 | 55.00 | 2.00 mm clear |
| `M1`.2 | 57.54 | **0.54 mm under** |
| `J2`.1 | 56.00 | 1.00 mm clear |
| `J2`.2 | 58.54 | **1.54 mm under** |
| `J2`.3 | 61.08 | **4.08 mm under** |

Consequences:

- **Route the bundles away in −y.** Pin 1 of each is already outside the footprint, so
  bending outward at the joint is the natural direction and keeps nothing standing up
  under the overhang.
- **Height is not the constraint** — M3×20 standoffs give a 20 mm gap, and a soldered
  joint with shrink lying flat is ~1.4 mm. A 2.54 mm connector housing would sit
  ~6–8 mm up *plus* bend radius for a 20 AWG lead, and cramped bends side-load a
  friction-fit housing off its pins. Soldered and dressed flat is the better fit here.
- **Access closes when the mezzanine does.** Neither joint is reachable with the logic
  board mounted. Everything that needs to touch them — the check below,
  `../../docs/pre-power-on-validation.md` — happens at stage 9, before stage 10 fits the
  modules.

### The short check, and why it gets harder later

Board-only path from `VBAT_PROTECTED` to `GND` before stage 9 is `R2` → `VSENSE` → `R3`.
From the parts as measured 2026-08-02 (99.7k + 21.8k) that is **≈121.5k**, at both
`M1`.1↔`M1`.2 and `J2`.1↔`J2`.2. Nothing else bridges those nets yet — `C8`/`C9`, `Q1`,
the bucks and the XT30s are all stage 8–9.

**Take this reading before stage 9.** Once ~5470 µF lands on the rail, every measurement
on that net behaves like the one that already misled this build once: `J2`.1↔`J2`.3 read
as a dead short and was an uncharged cap.

With the UBEC and the voltmeter still attached you will not see a clean 121.5k — both
modules parallel their own input impedance across it. **Chase the shape, not the number:**

- Near-zero, *instantly*, same value in **both probe polarities**, and it stays there →
  a real short. A real short is boring.
- Starts low and climbs, or settles up in the tens or hundreds of k → that is the
  modules and their input caps, not a fault.

## Strain relief + routing notes

- Feetech daisy chain follows the opposite chassis edge from the high-current servo power (reduces capacitive coupling)
- **L2/D456 cable path** (current, post-2026-07-07 head re-architecture +
  AUD-12 — supersedes the old mast-bore/riser-deck-slot route): L2 pigtail
  enters `head.scad`'s crown bore (Ø13×11, x126.5 ±6.5/±5.5). D456's USB-C
  reuses that SAME bore below z106 — rerouted down the column front through
  the face-plate window (AUD-12 fix: a separate channel there would have
  hollowed the head-mount boss's own heat-set inserts). Both then drop
  through `neck_bracket.scad`'s cable slot (18×14, at the deck top) into
  this shoulder's **deck lightening window**, through the shoulder C-box,
  out the Ø12 shoulder flange grommet, into the trunk. Add a TPU
  strain-relief insert (patterns.md §8b pattern) where the bundle
  transitions at the flange grommet.
- Servo wire entry at each leg gets a TPU strain relief (same source)
- **Jetson −Y bundle** (DC barrel + RJ45 + USB-C right-angle adapters,
  backlog #41): sleeve the 3-cable run in spiral wrap (BOM §9) before
  dropping it through the riser's −Y `CASE_SLOT`, seat the TPU
  `case_slot_grommet` (`../cad/chassis/case_slot_grommet.scad`) on the
  slot's cable-bearing edge, then zip-anchor the bundle to the
  grommet's strain-relief tab right where it enters the bay — so plug
  tension at the Jetson ports is relieved by the zip tie + grommet, not
  carried by the port connectors themselves. **No longer blocked** — the
  `riser_bay.scad` CASE_SLOT cut was fixed 2026-07-10 (slot widened
  4.5 → 9 mm at y −49..−40, and `rounded_slot` r dropped 4 → 2.0, which was
  over half the old short span and had blown the cut out past the deck's
  own −Y edge). The chassis gate now clears the grommet against the cradle,
  both clamp bars and the case envelope at 0 pts.
  Still verify at assembly rather than on paper, for a reason the fix does
  not address: **retention is the zip-tie tab, not the edge clip.** The
  gate's 12% edge-clip figure is an inverted proxy (most of the liner's
  volume is cable channel and bay air by design), so it says nothing about
  grip. Check bundle fit and the drop-to-boards run with real cables.
- Battery leads: 18 AWG silicone, exit the pack's REAR face behind the
  trunk end, rise through the shoulder-flange bottom notch (y ±10 →
  z 12) to the MRBF block on the floor plate (`../cad/chassis/README.md`)
- ~~E-stop button on chassis side panel~~ **side panel is impossible** —
  the mezzanine owns every wall-depth column (chassis review 2026-07-06).
  E-stop = pod ABOVE the riser deck rear strip, designed with the hood.

## Outstanding wiring decisions

- Exact USB hub config on Jetson — likely only 4 USB-A ports on P3766, may need a powered hub for D456 + Teensy + FE-URT-1 concurrent. Verify on bench.
- ~~Whether to integrate the lighted rocker switch into PCB v6 or panel-mount via flying lead; candidate home = the riser's FRONT-GAP zone (rocker through the side skirt at ~(x 57, z 45))~~ **RESOLVED 2026-08-15 (#368/#377): panel-mount via flying lead, in the FRONT SHOULDER's rear wall** at trunk (x 108, y +1, z 43), long axis VERTICAL, snapped into the 4 mm wall (Blue Sea Contura = Carling V-Series: sprung wings, no screws, 21.08 × 36.83 mm hole, panel band 0.81–6.35 mm). **The riser FRONT-GAP home was impossible** — that column is 10.85 mm wide against a 21.08 mm cutout, and `hardware/cad/chassis/panel_probe.py` found every other proposed face fails too. Wires solder direct to the spades at 90°; heat-shrink past the solder wick and anchor to the shoulder's Ø12 grommets so flex never lands on the joint (this is the ~14 A master feed on a walking machine).
- L2 LiDAR cable routing past the rotating sensor head — needs flex strain relief to survive scans
