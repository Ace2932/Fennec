# nova_ops

NovaSM3 operations layer. Pre-flight health checks, dashcam, safety
envelope, bringup launcher, telemetry, status LED, battery SoC, bag
replay. Not on the gait critical path — every node here is allowed to
crash without killing the robot.

Roadmap + feature specs: [`docs/notes-qol-features.md`](../../../docs/notes-qol-features.md).

## Status (2026-05-24)

| Feature | Status |
|---------|--------|
| §1 Preflight check (v1: bus ping + E-stop + battery latch) | ✅ implemented |
| §2 Always-on MCAP dashcam | 📋 stub |
| §3 Per-joint safety envelope | 📋 stub |
| §4 nova bringup launcher with profiles | 📋 stub |
| §5 make deploy (Teensy over Jetson USB) | 📋 stub |
| §6 Bag replay harness | 📋 stub |
| §7 Telemetry → CSV / Grafana | 📋 stub |
| §8 RGB status LED on Arduino Nano | 📋 stub |
| §9 Battery SoC widget | 📋 stub |

## Preflight check (v1)

Runs the 3 mandatory critical checks per `notes-qol-features.md` §1:

| Check | Reads | Fail mode |
|-------|-------|-----------|
| `bus_ping` | `/servo_present_mask` Int32 bitmask | missing servo IDs |
| `estop` | `/estop` Bool | E-stop engaged |
| `battery_latch` | `/battery_low` Bool | 13.0 V comparator latched |

All three are critical: a FAIL on any of them blocks gait bringup
(via the launch composition layer). WARN/STALE results print but
don't block.

### Run

Start the service node:

```bash
ros2 run nova_ops preflight_node
# or:
ros2 launch nova_ops preflight.launch.py
```

Call from another terminal:

```bash
ros2 run nova_ops preflight              # CLI, exits non-zero on fail
ros2 service call /preflight/run std_srvs/srv/Trigger    # raw service call
```

The CLI subscribes to `/preflight/status` (a `DiagnosticArray` published
on each run) and pretty-prints per-check status before exiting with
0 = pass, 1 = critical fail, 2 = service not reachable, 3 = timeout.

### Add a new check

1. Create `nova_ops/preflight/checks/<name>.py` with a class subclassing
   `Check` and implementing `name()` + `run(node) -> CheckResult`.
2. Add it to `V1_CHECKS` in `nova_ops/preflight/checks/__init__.py`.
3. Rebuild: `colcon build --packages-select nova_ops`.

Set `critical = False` on the instance if a FAIL should warn but not
block bringup.

### v2 checks (not yet implemented)

Per `notes-qol-features.md` §1:

- **Per-joint voltage / temperature** — gated on firmware
  `REG_PRESENT_VOLTAGE` / `REG_PRESENT_TEMPERATURE` work landing in
  `feetech_bus.h::poll_one_servo()` (see `firmware/teensy/firmware/README.md`).
- **Topic liveness** — count of pubs ≥ 1, last-message age < 2× expected period.
- **Network** — ping L2 at 192.168.1.62, 100 ms timeout.
- **Disk space** — `/` and `/var/log` > 2 GB free.
- **Firmware version match** — `/firmware_version` SHA vs `~/.nova/last-deployed.sha`.
- **Time sync** — drift between Jetson `CLOCK_REALTIME` and last bag stamp < 500 ms.

## Build

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select nova_ops
source install/setup.bash
```

(Note: this is a pure-Python ament_python package — colcon's "build"
just installs entry-points and the launch share, no compile step.)

## Test

```bash
cd ~/ros2_ws
colcon test --packages-select nova_ops
colcon test-result --verbose
```

(Test suite is currently empty; preflight checks are integration-only
because they require the Teensy bridge to be publishing.)
