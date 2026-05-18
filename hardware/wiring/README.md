# Wiring Diagrams

Power rail map and signal/data wiring for the as-built robot.

## Will contain
- Full power rail diagram per BOM v3.4 (4S LiPo → Pololu D42V110F7 + D42V110F12 + D24V22F12 + D42V55F12 + UBEC 5V; arm rail D42V55F7 reserved)
- Safety chain (Class T 30A fuse [LiPo-rated, 20 kA AIC], MOSFET reverse-protection, MOSFET hard-cutoff @ 12.4V, E-stop on leg+hip+L2 rail enables)
- LC filter spec on D24V22F12 output (22 µH series choke + 470 µF / 25V shunt) feeding L2
- Feetech daisy-chain topology (servo IDs 1-12 active, 13-18 reserved; cable lengths; **star injection at 4 points along leg rail**)
- INA226 ×3 I²C topology (leg / hip / Jetson rails → Teensy; optional 4th on L2 rail)
- I²C bus map (Arduino Nano aux peripherals separate bus)
- USB topology (Jetson hub assignments: RealSense, FE-URT-1, Teensy)
- Ethernet wiring (L2 ↔ switch ↔ Jetson `eth0`)
- Pattern A/B bus master path on PCB v6 (solder bridge `JP_BUS_MASTER`)
- Color-code conventions
