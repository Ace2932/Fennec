# Teensy 4.1 Firmware

Future home of the micro-ROS bridge (Pattern B — Teensy owns the Feetech bus).

## Will contain
- micro-ROS PlatformIO project for Teensy 4.1
- Half-duplex TTL driver glue (1-transistor or TXS0108 — TBD)
- SCServo SDK port for Teensy (or hand-rolled minimal driver)
- Topics published: `/joint_states`, `/joint_temps`, `/joint_loads`
- Topics subscribed: `/joint_commands`
- Real-time loop @ 200-500 Hz

> **Status:** deferred. Pattern A (Jetson direct via FE-URT-1) is current.
> Migrate here only if measured latency or robustness becomes a problem.
