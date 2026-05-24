# Arduino Nano Firmware

**Reduced role per BOM v3.5 cut (2026-05-24).** No more I²C aux bus.

## What the Nano drives

- **SSD1331 96×64 OLED** via SPI — battery / IP / gait state display
- **WS2812B RGB LED strip × 4** via 1 GPIO — at-a-glance robot status
  (per `docs/notes-qol-features.md` §8)

## What's gone (cut from v1, on shelf)

- ~~PIR motion sensors × 3~~ (wrong sensor class for mobile robot)
- ~~HC-SR04 ultrasonics × 2~~ (D456 + L2 perception redundant)
- ~~MPU-6050 IMU~~ (D456 + L2 IMUs higher-quality)
- ~~DFPlayer Mini Pro + speaker~~ (novelty; Phase 4 polish)

## Architecture

```
Jetson ──USB-serial──► Arduino Nano ──SPI──► SSD1331 OLED
                                 │
                                 └─GPIO──► WS2812B LED strip
```

Jetson side: `nova_ops/oled_status` node (stub committed) subscribes to:

- `/battery_low` (Bool) — safety latch state
- `/safety_state` (Int32) — 0/1/2/3 → LED color
- `/firmware_version` (String) — boot splash
- `/joint_cmd_rx_count` (Int32) — gait liveness
- `/power_rails` (Float32MultiArray) — battery voltage

Packs into 4-line text frame + 1 LED state byte. Writes over
`/dev/ttyUSB0` @ 115200 baud.

## Protocol (proposal)

Line-based ASCII, one command per `\n`:

```
STATE <0..3>            # sets LED color (0=OK green, 1=ESTOP red,
                        #                 2=BATT_LOW amber, 3=FAULT red blink)
LINE <0..3> "<text>"    # sets one of 4 OLED text rows, 16-char max
SPLASH                  # show firmware_version briefly
```

Nano echoes acknowledgments (`OK\n` / `ERR\n`) so the Jetson side
can detect a dead Nano.

## Wiring (final layout TBD with PCB v6)

| Nano pin | To | Notes |
|----------|----|----|
| D11 (MOSI) | SSD1331 SDA | SPI |
| D13 (SCK) | SSD1331 SCK | SPI |
| D10 | SSD1331 CS | SPI chip select |
| D9 | SSD1331 DC | data / command |
| D8 | SSD1331 RST | reset |
| D6 | WS2812B DIN | 800 kHz NeoPixel data |
| 5V | OLED + LED Vcc | regulated 5V |
| GND | common | |
| USB | Jetson USB port | serial bridge |

## Sketch (TODO)

- Status: not implemented yet. The OLED + LED hardware works
  standalone; sketch ties them to the USB-serial protocol above.
- Libraries: Adafruit_GFX + Adafruit_SSD1331 + FastLED.
- Roughly 1-2 evenings of work. Phase 1 polish task.
