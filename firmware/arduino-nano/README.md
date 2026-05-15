# Arduino Nano Firmware

Aux peripherals only — no servo control.

## Will contain
- PIR motion sensors (×3) — interrupt-driven
- HC-SR04 ultrasonics (×2) — polling
- SSD1331 OLED — status display
- WS2812B RGB LEDs (×4) — state indication
- DFPlayer Mini Pro — audio prompts
- MPU-6050 — IMU (I2C, raw → Jetson via serial or ROS bridge)

Stripped down from the stock NovaSM3 Arduino sketch — all servo / locomotion
code removed.
