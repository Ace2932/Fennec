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
- **ANL 30A fuse** in main feed (sized for hip-rail worst case ~15A + headroom; interrupt rating must survive LiPo dead-short ~1000-2000A for a few hundred ms)
- Power switch (high-current, ≥30A rated)
- Mini digital voltmeter retained for at-a-glance pack state

### 2. Four active power rails + one reserved (v3.4 split)

| Rail | Module | Output | Sized for | Status |
|------|--------|--------|-----------|--------|
| Leg | Pololu D42V110F7 | 7.5V / 10A typ @ 42V Vin | 8× STS3215 19kg | Active v1 |
| Hip | Pololu D42V110F12 | 12V / 9A typ @ 42V Vin | 4× STS3215 30kg ONLY | Active v1 |
| L2 LiDAR | Pololu D24V22F12 | 12V / 2.6A | Unitree L2 (1A, dedicated buck for clean power) | Active v1 (added v3.4) |
| Jetson | Pololu D42V55F12 | 12V / ~3A cont. | Jetson Orin Nano Super MAXN | Active v1 |
| Arm | Pololu D42V55F7 | 7.5V / 3-8A | 6× STS3215 arm (Phase 4) | **Footprint reserved — DO NOT populate v1** |
| Aux 5V | UBEC 5V/5A (off-board) | 5V / 5A | Switch, fans, aux peripherals | Header on board |

Module footprints use Pololu's standard header pitch so cards can be swapped without PCB respin. L2 split from hip rail (v3.4) because D42V110F12's 9A typ @ 42V Vin derates to ~7-8A at our 14.8V Vin, and combined hip+L2 sustained ~9A was over budget.

### 3. Servo bus distribution (star injection)

- Single signal bus (daisy-chained TTL) — no break
- **4 power injection points** along the leg 7.5V trunk (one per leg pair)
- **Bulk caps (1000 µF / 25V) at each injection point** — soaks impact transients near point of load
- Star ground at FE-URT-1 connector
- Hip rail injects at chassis floor (4 hips clustered there)

### 4. Bus master — Pattern B default, Pattern A fallback

**Pattern B is the v1 active path.** Teensy 4.1 hardware UART routed through **74HC125 quad tri-state buffer** as a half-duplex driver to the Feetech TTL bus pads. The 74HC125 must be populated on first build.

- Teensy UART TX → 74HC125 input gate
- Teensy GPIO → 74HC125 OE pins (TX-enable for write, RX-enable for read; half-duplex direction control)
- 74HC125 output → bus signal pad
- FE-URT-1 USB→TTL input header retained for fallback

Solder bridge `JP_BUS_MASTER` selects which path drives the bus pads:

- **B (default — board ships configured this way):** Teensy UART → 74HC125 → bus
- **A (fallback):** FE-URT-1 → bus directly (used for ID setup, debug, post-mortem)

Both paths terminate on the same bus pads; the bridge is the only state change. No chassis teardown to swap.

Linux jitter rationale: USB-CDC latency on Jetson is 1-10 ms typical, 50 ms+ under CUDA / kworker / journald load. 100 Hz gait + 100 ms stall = robot on floor. Teensy bare-metal UART has hard real-time guarantees by construction.

### 5. Bus integrity footprints (populate per measured error rate)

Feetech bus is **single-ended half-duplex TTL UART**, not RS-485. 120 Ω differential termination is the wrong tool here.

- Series R footprints (22-100 Ω, 0603) at FE-URT-1 / 74HC125 output — slope rate-limiting
- Ferrite bead footprints at each servo entry — common-mode noise rejection
- Star ground at FE-URT-1 connector

Default v1 build: leave footprints unpopulated. Populate iteratively if bus error rate exceeds threshold during bring-up. If still poor, drop baud 1M → 500k → 250k.

### 6. Safety chain

- **Charger LVC alarm:** ISDT 608AC set to **3.3V/cell = 13.2V** (above D42V55F12 dropout knee, well within LiPo safe range)
- **MOSFET hard-cutoff:** comparator (TL431 or LM393) drives a logic-level N-channel MOSFET on the battery feed. Trips at **12.4V** = 3.1V/cell. Autonomous backstop independent of charger; protects pack if user ignores alarm.
- **E-stop:** panel-mount latching button, NC contact. Wired in series with the **leg + hip rail enable lines only**. Jetson rail stays alive for post-mortem debug. Twist-to-release.
- **INA226 ×3 (optional 4th):** one per active rail (leg 7.5V, hip 12V, Jetson 12V); optional 4th on L2 12V if telemetry budget allows. I²C bus to Teensy 4.1 → ROS 2 diagnostics topic. Per-rail current/voltage telemetry.

### 7. Aux MCU + peripherals (carryover from Nova v5.2b)

- Arduino Nano slot (3-pack already owned) for PIR motion, HC-SR04 ultrasonic, SSD1331 OLED, WS2812B RGB LEDs, DFPlayer Mini Pro + speaker, MPU-6050 IMU
- Teensy 4.1 footprint (already owned) for INA226 I²C reader, E-stop GPIO, Pattern B half-duplex driver

### 8. Mechanical / connector convention

- M3 mounting holes matching chassis (TBD from CAD)
- JST-XH 2.54 for low-current signals
- XT30 for servo power injection trunks
- XT60 panel-mount for battery
- All connectors keyed to prevent reverse insertion

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
3. Power planes: separate 4-layer stackup (top sig, GND, PWR, bottom sig). Star ground at FE-URT-1.
4. DRC + ERC clean before Gerber export.
5. PCBWay order: 5 boards (spares + iteration), 2 oz copper, ENIG finish, stencil for SMD.
6. First-article: hand-populate one board, bench-test every rail before populating others.

---

## Open questions for design phase

- Final D42V55F7 footprint orientation on arm-rail reservation (depends on Phase 4 mechanical install)
- Whether to integrate the lighted rocker switch into the PCB or keep panel-mount via flying lead
- Whether to add a USB-C dev port for direct Teensy programming (vs pulling the Teensy out for USB-A flashing)
- Whether to mirror the v5.2b voltmeter on the PCB or panel-mount

Resolve during schematic review.

---

> **Status:** design spec updated at BOM v3.4 / v0.3.2-l2-dedicated. Schematic + Gerber work pending.
> **Owner:** Aiden Fox.
