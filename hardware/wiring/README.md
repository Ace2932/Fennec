# Wiring Diagrams

Power rail map and signal/data wiring for the as-built robot.

## Will contain
- Full power rail diagram per BOM v3.2 (4S LiPo → Pololu D42V110F7 + D42V110F12 + D42V55F12 + UBEC 5V; arm rail D42V55F7 reserved)
- Safety chain (ANL 30A fuse, MOSFET reverse-protection, MOSFET hard-cutoff @ 12.4V, E-stop on servo rail enables)
- LC filter spec on L2 12V tap (22 µH series choke + 470 µF / 25V shunt)
- Feetech daisy-chain topology (servo IDs 1-12 active, 13-18 reserved; cable lengths; **star injection at 4 points along leg rail**)
- INA226 ×3 I²C topology (leg / hip / Jetson rails → Teensy; optional 4th on L2 rail)
- I²C bus map (Arduino Nano aux peripherals separate bus)
- USB topology (Jetson hub assignments: RealSense, FE-URT-1, Teensy)
- Ethernet wiring (L2 ↔ switch ↔ Jetson `eth0`)
- Pattern A/B bus master path on PCB v6 (solder bridge `JP_BUS_MASTER`)
- Color-code conventions
