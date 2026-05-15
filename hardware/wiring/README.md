# Wiring Diagrams

Power rail map and signal/data wiring for the as-built robot.

## Will contain
- Full power rail diagram (4S LiPo → XL4016 ×2 → Pololu D42V55F12 → UBEC 5V)
- LC filter spec on L2 12V tap (inductor + capacitor values)
- Feetech daisy-chain topology (servo IDs 1-18, cable lengths, branch points)
- I2C bus map (Arduino Nano aux peripherals)
- USB topology (Jetson hub assignments: RealSense, FE-URT-1, Teensy)
- Ethernet wiring (L2 ↔ switch ↔ Jetson `eth0`)
- Color-code conventions
