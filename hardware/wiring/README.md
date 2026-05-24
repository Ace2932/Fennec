# Wiring Diagrams

Power rail map and signal/data wiring for the as-built robot. Refer to BOM v3.4 + `hardware/pcb-mods/README.md` (PCB v6 spec) + `docs/power-budget.md` (current math) for source-of-truth values.

## Power chain (4S LiPo → 4 active rails + 1 reserved)

```
                              ┌─── Class T 30A fuse (LiPo-rated, 20 kA AIC)
                              │
4S LiPo 14.8V (12.8-16.8V) ──┼── MOSFET reverse-polarity protection
   (Ovonic 4000 mAh × 2)     │
                              ├── E-stop NC (Mxuteuk HB2-ES544, 22 mm latching)
                              │        │ kills leg + hip + L2 rail EN lines
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
                                └─ UBEC 5V/5A        → 5V       → Ethernet switch + fans + aux 5V
```

## Safety chain trip points (highest pack voltage first)

| Trip | Pack V | Cell V | Action |
|------|--------|--------|--------|
| 1 | 13.2 V | 3.30 V/cell | 608AC charger LVC alarm (user-facing beep) |
| 2 | 13.0 V | 3.25 V/cell | LM393 comparator → Teensy GPIO pin 3 → `/battery_low` Bool → Jetson `systemctl poweroff` (clean SD unmount). ~30-60 s window. |
| 3 | 12.4 V | 3.10 V/cell | Second LM393 stage → logic-level MOSFET (IRLB3034PBF candidate) → breaks battery feed. Autonomous backstop. |
| — | — | — | E-stop (manual) — kills D42V110F7 + D42V110F12 + D24V22F12 EN lines. Jetson stays alive. |

## Feetech TTL bus (single-ended half-duplex, 1 Mbps default)

```
Teensy 4.1                    74HC125 (quad tri-state buffer)              Bus pad
  Serial2 TX (pin 8) ─────────► gate 1 input ─OE(pin 6 HIGH)────┐
  Serial2 RX (pin 7) ◄───────── gate 2 output ◄─OE(pin 5 LOW)──┤
  GPIO TX_OE (pin 6) ─────► OE pin (gate 1)                    │
  GPIO RX_OE (pin 5) ─────► OE pin (gate 2)                    │
                                                                ▼
                                                       12× STS3215 daisy chain
                                                       IDs 1-4   hips
                                                       IDs 5-12  femur + tibia
                                                       IDs 13-18 reserved (Phase 4 arm)

JP_BUS_MASTER solder bridge:
  default = B (Teensy → 74HC125 → bus)
  alt     = A (FE-URT-1 → bus, for ID assignment + bench debug)
```

**Bus integrity footprints on PCB v6 (populate per measured error rate):**
- Series R (22-100 Ω, 0603) at 74HC125 output — slope rate-limiting
- Ferrite bead at each servo entry — common-mode noise rejection
- Star ground at FE-URT-1 connector
- **NOT** 120 Ω differential termination — Feetech bus is single-ended TTL, not RS-485

**Cable plan:** Feetech daisy-chain cables (ordered), one ferrite bead per servo entry (footprint on PCB), star ground at FE-URT-1. If errors persist after populating: drop baud 1M → 500k → 250k.

**Cable length:** ~2 m total harness. Community reports 12 m / 8 axes workable, so 2 m / 12 nodes is well within margin.

## INA226 telemetry topology

```
Teensy 4.1                          I²C bus (separate from Arduino Nano aux bus)
  SDA (pin 18) ──┬────────────────┬────────────────┬────────────────┐
  SCL (pin 19) ──┤                │                │                │
                 ▼                ▼                ▼                ▼
            INA226 0x40       INA226 0x41       INA226 0x44       INA226 0x45
            leg 7.5V          hip 12V           Jetson 12V        L2 12V
            shunt: 0.001 Ω    shunt: 0.001 Ω    shunt: 1 mΩ stock (opt 4th)
            (Vishay WSLP)     (Vishay WSLP)     (Adafruit breakout)

  → /power_rails Float32MultiArray @ 10 Hz: [leg_v, leg_a, leg_w,
                                              hip_v, hip_a, hip_w,
                                              jetson_v, jetson_a, jetson_w]
```

I²C pull-ups: 10 kΩ to 3.3 V on SDA + SCL at the Teensy end of the bus.

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

```
Unitree L2 LiDAR              ┌─── 5-port unmanaged gigabit switch
  IP: 192.168.1.62  ──Cat 6───┤    (TP-Link LS105G or NETGEAR GS305)
  UDP target: 6101            │    Powered from 5V UBEC rail (~3 W draw)
                              │
Jetson Orin Nano              │
  enP8p1s0:                   │
  192.168.1.2/24 ────Cat 6────┤
  (static via nmcli           │
   connection nova-lan)       │
                              │
Dev laptop (optional) ───Cat 6┘
  192.168.1.10 static
```

Cable: Cable Matters 10 Gbps snagless Cat 6 (1 ft) × 2-3.
Switch can be pulled from its case to save ~60 % volume inside the chassis.

## Wire gauge convention

| Wire | Gauge | Use |
|------|-------|-----|
| 18 AWG silicone | 18 AWG | Servo power (7.5 V + 12 V rails), battery feed to bucks |
| 22 AWG hookup | 22 AWG | Signal-level (INA226 I²C, comparator outputs, E-stop GPIO, RGB LED data) |
| Feetech TTL daisy-chain | 28 AWG (vendor) | Servo bus signal + servo power passthrough |

## Color code

- **Red:** +V (positive supply, all voltages)
- **Black:** GND (common)
- **Yellow:** signal (logic-level, GPIO)
- **Green:** I²C SDA / SCL (preserve white-on-green if available)
- **Blue:** UART data
- **Orange:** safety (E-stop, comparator output)

## Strain relief + routing notes

- Feetech daisy chain follows the opposite chassis edge from the high-current servo power (reduces capacitive coupling)
- L2 Ethernet cable routes through a TPU strain-relief grommet at chassis pass-through (printed pattern in [`../cad/patterns.md`](../cad/patterns.md) §8b)
- Servo wire entry at each leg gets a TPU strain relief (same source)
- Battery leads: short + thick (18 AWG silicone), routed inside a Kapton-wrapped channel near the LiPo pocket
- E-stop button on chassis side panel, kept clear of moving leg envelope

## Outstanding wiring decisions

- Exact USB hub config on Jetson — likely only 4 USB-A ports on P3766, may need a powered hub for D456 + Teensy + FE-URT-1 concurrent. Verify on bench.
- Whether to integrate the lighted rocker switch into PCB v6 or panel-mount via flying lead (see `hardware/pcb-mods/README.md` open questions)
- L2 LiDAR cable routing past the rotating sensor head — needs flex strain relief to survive scans
