# Teensy 4.1 Firmware

## v1 role: aux I/O + safety monitor (Pattern A active)

- INA226 ×3 I²C reader (leg / hip+L2 / Jetson rails) → micro-ROS diagnostics topic
- E-stop GPIO sense
- MPU-6050 IMU read (optional, may live on Arduino Nano instead)
- 74HC125 output gating (Pattern B prep — driver IC is physically populated but the solder bridge keeps it inactive)

## Pattern B path (footprint-ready, software stub)

If Phase 1 bench measurement shows gait-loop p99 latency >5 ms via FE-URT-1, flip the PCB v6 `JP_BUS_MASTER` solder bridge and migrate to Pattern B:

- Teensy hardware UART → 74HC125 half-duplex driver → bus pads
- SCServo SDK port (Teensy-compatible) or hand-rolled minimal driver
- Topics published: `/joint_states`, `/joint_temps`, `/joint_loads`
- Topics subscribed: `/joint_commands`
- Real-time loop @ 200-500 Hz

## Stack

- PlatformIO project (favored over Arduino IDE for dependency management)
- micro-ROS Teensy client library
- TeensyDuino core
- Real-time priority on UART ISRs

> **Status:** v1 stub. Aux I/O firmware written during Phase 1; Pattern B migration conditional on measurement.
