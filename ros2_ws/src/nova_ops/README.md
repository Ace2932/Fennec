# nova_ops

NovaSM3 operations layer. Pre-flight health checks, dashcam, safety
envelope, bringup launcher, telemetry, status LED, battery SoC, bag
replay. Not on the gait critical path — every node here is allowed to
crash without killing the robot, with ONE exception: `battery_shutdown`
(§10) is safety-critical and launches with respawn.

Roadmap + feature specs: [`docs/notes-qol-features.md`](../../../docs/notes-qol-features.md).

## Status (2026-05-24)

| Feature | Status |
|---------|--------|
| §1 Preflight check (v1: bus ping + E-stop + battery latch) | ✅ implemented |
| §2 Always-on MCAP dashcam (v1: 20 topics + freeze on safety + janitor) | ✅ implemented |
| §3 Per-joint safety envelope (position+velocity+load) | ✅ library shipped |
| §4 nova bringup launcher with profiles | ✅ implemented |
| §5 make deploy (Teensy over Jetson USB) | ✅ implemented (in `firmware/teensy/firmware/Makefile`) |
| §6 Bag replay harness | 📋 stub |
| §7 Telemetry → CSV / Grafana | 📋 stub |
| §8 RGB status LED on Arduino Nano | 📋 stub |
| §9 Battery SoC widget | 📋 stub |
| §10 `/battery_low` → `systemctl poweroff` node | ✅ implemented (2026-06-12) — `battery_shutdown_node`, in `walk` profile |

## §10 — battery_low shutdown node (gap found 2026-06-12 software review)

The Teensy publishes `/battery_low` (13.0 V comparator, debounced + latched) and the whole
two-stage LVC design assumes a Jetson node runs a clean shutdown before the 12.4 V hardware
cutoff yanks the rails (`firmware/teensy/README.md` documents it as existing — it doesn't).
Without it: pack sags 13.0→12.4 V under gait load in minutes, HARDCUT fires, Jetson loses
power mid-SD-write.

Implemented in `nova_ops/battery_shutdown/` (decider = pure logic, unit-tested in
`test/test_battery_shutdown.py`; node = thin wrapper). Two trigger paths: `/safety_state == 2`
fires immediately (firmware FSM already debounced), raw `/battery_low` sustained ≥2 s as the
backup if the latched edge message is lost. Once fired the decision is permanent — recovery
at idle doesn't cancel (pack will sag again on next step). Publishes `/shutdown_imminent`
(transient-local), waits `grace_s` for the dashcam freeze to flush, then
`sudo -n systemctl poweroff`. Params: `raw_sustain_s`, `grace_s`, `dry_run`.
**Host prereq:** passwordless poweroff sudoers rule — see `docs/setup-jetson.md`.
Bench test: `ros2 run nova_ops battery_shutdown_node --ros-args -p dry_run:=true` then
`ros2 topic pub --once /safety_state std_msgs/Int32 '{data: 2}'`.
Companion firmware-side fix (command-staleness failsafe) shipped same day — see
`firmware/teensy/README.md`.

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

## Dashcam (v1)

Always-on MCAP rosbag with rolling 2 GB buffer + incident freeze on
safety triggers per `notes-qol-features.md` §2.

**Recorded topics** (v1 set, cameras + lidar deliberately omitted):
joint I/O, bus diagnostics, loop quality, power telemetry, safety
state, identity (`/firmware_version`), `/cmd_vel`, `/tf`. Full list in
`nova_ops/dashcam/topics.py::V1_TOPICS`.

**Triggers** (any of these fires an incident bundle):
- `/estop` goes True
- `/safety_state` goes non-zero (E-stop latch, battery latch, fault)
- `/battery_low` goes True
- Manual: `ros2 service call /dashcam/freeze std_srvs/srv/Trigger`

**Incident bundle** (`/var/log/nova/incidents/<iso-timestamp>/`):
- `bags/<rosbag-dir>/...` — full current rolling buffer copied at trigger
- `metadata.yaml` — trigger reason, free disk, Jetson uptime, git SHA
- `dmesg.tail` — last 50 lines of kernel log

**Janitor:** background thread sweeps every 10 s, deletes oldest bag
when total `retention_mb` exceeded (default 2 GB → ~5 min at mid-
bandwidth).

**Run:**

```bash
sudo apt install ros-humble-rosbag2-storage-mcap   # one-time
ros2 launch nova_ops dashcam.launch.py
# or with custom retention:
ros2 launch nova_ops dashcam.launch.py retention_mb:=10240
# manual freeze from another terminal:
ros2 service call /dashcam/freeze std_srvs/srv/Trigger
```

Default bag buffer location: `~/.nova/dashcam/buffer/`.
Override via parameter `bag_dir`.

### Tuning

- `retention_mb` — default 2048. Longer = more incident context but
  more SD wear (each 60 s bag rolls a new file).
- `max_bag_seconds` — default 60. Shorter splits = finer-grained
  rolling cutoff but more file churn.
- `topics` — passed as a list parameter; replace with `PERCEPTION_TOPICS`
  for high-bandwidth runs (still under buffer cap).

## nova bringup launcher (v1)

Per `notes-qol-features.md` §4. Profile-based composition; profiles
defined as a Python dict in `nova_ops/bringup/__init__.py` (v1).
v2 moves them to YAML.

Profiles:

| Profile | Description |
|---------|-------------|
| `bench` | Teensy uROS bridge + preflight — desk firmware iteration |
| `sensors` | RealSense + L2 + dashcam — sensor smoke / data collection |
| `slam` | sensors + POINT-LIO + robot_state_publisher |
| `walk` | preflight + dashcam + (gait controller — TODO) |
| `full` | walk + slam + Nav2 + Foxglove (TODO) |
| `vla` | full + VLA inference (Phase 4) |

```bash
ros2 launch nova_ops bringup.launch.py profile:=walk
ros2 launch nova_ops bringup.launch.py profile:=sensors dry_run:=true
ros2 launch nova_ops bringup.launch.py profile:=walk no_preflight:=true
```

`include_profile` lets one profile compose another. Missing packages
(gait_controller, nav2, etc.) are skipped with a log line instead of
crashing the launch.

## Per-joint safety envelope (v1)

In-process wrapper library per `notes-qol-features.md` §3 option (a).
The gait controller imports
`nova_ops.safety_envelope.SafeJointCommandPublisher` and calls
`.publish(joint_state)` instead of touching the raw `/joint_commands`
publisher directly.

Checks (v1):
- **Position** — clamp to URDF limits with a 2° soft margin
- **Velocity** — numerical diff vs last command; replace with
  `last + sign * v_max * dt` if over limit
- **Load** — 3-sample mean of `/joint_states.effort[]` above 70%
  refuses goals that would increase joint displacement
- **Temperature** — ⏳ gated on firmware `REG_PRESENT_TEMPERATURE`

Joint limits live in `nova_ops/safety_envelope/limits.py`. Currently
hand-tuned conservative defaults for hip abduction / thigh / knee;
replace with URDF-derived values when the URDF lands.

Counters publish at 1 Hz on `/safety_envelope_counters` (Int32MultiArray
layout: `position_1..12, velocity_1..12, load_1..12`).

For now a placeholder publisher node is provided (publishes all
zeros until the gait controller wires up):

```bash
ros2 run nova_ops safety_counters
```

Unit tests live in `test/test_safety_envelope.py` — pure-Python
mock-rclpy tests covering clamp, velocity, load, counters.

## make deploy (Teensy over Jetson USB)

Per `notes-qol-features.md` §5: build firmware on laptop, flash over the
Jetson's USB connection so the Teensy stays in the chassis.

See `firmware/teensy/firmware/Makefile`:

```bash
cd firmware/teensy/firmware
make deploy            # build + hash-check + scp + remote flash + verify
make deploy-force      # skip hash check
make verify            # check /firmware_version on the Jetson
JETSON_HOST=user@host make deploy   # override SSH target
```

Implementation: `scripts/deploy-firmware.sh`. Handles agent stop/start,
hash caching (`~/.nova/last-deployed.sha`), USB re-enumeration wait,
post-flash `/firmware_version` verification. Refuses to deploy if
`gait_controller` is running on the Jetson unless `DEPLOY_FORCE=1`.

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
