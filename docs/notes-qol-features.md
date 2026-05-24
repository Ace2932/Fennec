# Feature Notes — Quality-of-Life Software Features

Forward-looking software ideas to make this build less painful to operate, debug, and iterate on. Captured 2026-05-24. None are on the active schedule — pick them up opportunistically during Phase 1/2, or batch into a "QoL sprint" once the v1 walk gait is stable. Companion to [`notes-virtual-view-autocal.md`](./notes-virtual-view-autocal.md).

Ordering is roughly highest-payoff-per-hour first within each group. All paths assume the repo layout under `ros2_ws/src/` with a new `nova_ops` package as the home for orchestration/safety/health utilities — that package doesn't exist yet, creating it is part of the work.

---

## Operations & safety

### 1. Pre-flight health check

**Goal:** one command answers "is the robot ready to move?" before you let it. Catches dead bus, unplugged Cat6, dead pack, missing sensor topic, stale firmware — all of which currently surface as confusing failures mid-test.

**Scope:**

- New ROS 2 node `nova_ops/preflight_check` exposing a service `~/run` returning a structured pass/fail per check plus an overall result.
- Provide a CLI wrapper `ros2 run nova_ops preflight` that just calls the service, pretty-prints to terminal, and exits non-zero on fail (so it can gate the bringup launch file).
- Each check is a small Python class implementing `name()`, `run() -> (Status, message)` so adding a new check is one file and one entry in the registry.

**Initial check set:**

| Check | What it does | Fail mode |
|-------|--------------|-----------|
| Bus ping sweep | Ask Teensy via existing `/servo_present_mask` topic — verify all 12 expected IDs report present | Missing IDs listed |
| Servo voltage/temp | Read latest `/servo_telemetry` — flag any cell <6.8V (leg) / 11.0V (hip) or temp >55°C | Per-joint table of offenders |
| Battery pack | Read INA226 main-rail topic — flag <13.5V (under load) | "low" with current voltage |
| Topic liveness | For each expected topic (12 from BOM §5 + 4 from sensor stack), check publisher count >0 and last message age <2× expected period | List of stale topics |
| Network | Ping L2 at 192.168.1.62 (single ping, 100 ms timeout) | "L2 unreachable" |
| Disk space | `/` and `/var/log` >2 GB free | Avoids mid-walk rosbag write failure |
| Firmware version | Compare Teensy's reported `/firmware_version` topic against expected hash committed in repo | Mismatch with both versions |
| Time sync | Verify Jetson clock and last bag timestamp drift <500 ms (proxy for "is chrony alive") | Otherwise rosbags get wrong stamps |
| E-stop | Read latest E-stop GPIO state topic — must read "released" | "E-stop engaged" — refuse to bring up gait |

**Integration:**

- Bringup launch file (see [§4](#4-single-nova-bringup-launcher-with-profiles)) calls the service after all nodes settle (3 s sleep), refuses to enable the gait controller if any **critical** check fails (servo presence, E-stop, battery). Warnings (temp, disk) print but don't block.
- A `--quick` flag skips the network ping and topic-liveness wait, so it can run pre-power-on in <500 ms.

**Open questions:**

- Whether to put the check definitions in YAML (data-driven) or Python (code-driven). Lean Python — checks need varied logic; YAML would push that into a DSL.
- Whether a failed check should auto-suggest the fix or just report. Suggestion strings nice but rot fast — start with report-only.

---

### 2. Always-on rosbag dashcam

**Goal:** when something fails — E-stop trips, a servo faults, a node crashes, the robot does something weird — you have the last few minutes of state to reconstruct what happened. Today this would require remembering to start a bag before every test.

**Scope:**

- Dedicated `nova_ops/dashcam` node wrapping `rosbag2`'s recorder API.
- Records to a **circular buffer on disk**: rosbag2 has `--max-bag-duration` to roll bag files at fixed intervals (e.g. 60 s), plus `--max-bag-size`; combine with a janitor goroutine that deletes the oldest bag once total directory exceeds `--retention-bytes` (default 2 GB → ~5 min of mid-bandwidth recording).
- Format: **MCAP** (not sqlite3) — better tooling, faster random access, Foxglove can play it directly.

**Topic set (start narrow, expand as warranted):**

```
/joint_states                       # 100 Hz from Teensy
/joint_commands                     # 100 Hz from gait controller
/diagnostics                        # 1 Hz aggregated
/servo_telemetry                    # 5 Hz per-joint V/temp/load
/battery_voltage                    # 1 Hz INA226 main rail
/imu/data (D456)                    # 200 Hz
/imu/data (MPU-6050)                # 100 Hz
/cmd_vel                            # whatever the controller pubs
/tf, /tf_static                     # for replay-time URDF reconstruction
/estop_state                        # GPIO sense from Teensy
# Cameras + lidar deliberately omitted — too much bandwidth for always-on.
# Spin up a second recorder profile (`nova_ops/dashcam_perception`) for runs where you want them.
```

**Trigger / freeze:**

- Subscribe to `/estop_state` and `/node_diagnostics_aggregator`. On E-stop engage or any node status going to ERROR, **stop rotation** (so the buffer at fault time is preserved) and copy the current bag set into `/var/log/nova/incidents/<iso-timestamp>/`.
- Include a `metadata.yaml` in the incident dir capturing: free disk at trigger, Jetson uptime, recent kernel log tail (`dmesg | tail -50`), git SHA of running code (read from a file written by bringup).
- Provide a `ros2 service call /dashcam/freeze "{}"` for manual capture — when you saw something weird but no fault tripped.

**Open questions:**

- Default retention: 2 GB / ~5 min vs 10 GB / 25 min. Lean 5 min; longer requires SD wear consideration.
- Whether to include `/joint_commands` *intent* vs only what hit the bus. For root-causing "did the controller send this or did the Teensy translate it wrong?" you want both.
- Should the dashcam also store the last 200 lines of each ROS node's stderr in the incident bundle. Probably yes — most node crashes show up there first.

---

### 3. Per-joint safety envelope in the gait controller

**Goal:** mechanical stops + servo torque limits are the last line of defense. Software should refuse to send commands that would clearly hit them in the first place. Today, a buggy gait controller can command tibia-through-hip with nothing in between rejecting it.

**Scope:**

- Lives in the **Jetson-side gait controller**, not the Teensy. Teensy gets to assume commands are pre-validated (so the 200-500 Hz bus loop stays tight). Treat the validator as a wrapper around the publisher: gait code calls `safe_publish(joint_commands)`, wrapper either publishes or rejects+logs.
- Pulls limits from the URDF (`<limit lower upper effort velocity>` tags on each `<joint>`). Single source of truth — URDF already needs to be right for IK/sim/viewers anyway.

**Per-joint checks on every command:**

| Check | Rule | Action on violation |
|-------|------|---------------------|
| Position | `lower ≤ goal ≤ upper`, with 2° margin inside URDF limits | Clamp to limit, log warn (first 10 occurrences per joint, then throttle) |
| Velocity | Numerically diff goal vs last command vs Δt; reject if > URDF velocity limit | Replace goal with last + sign × v_max × Δt |
| Load | Read latest `/servo_telemetry` load value; if last 3 samples >70% sustained, refuse new goals that increase it (allow ones that reduce) | "Joint overloaded — backing off" + log |
| Temperature | Servo temp >60°C → derate by 20% (slew rate halved); >70°C → reject all goals for that joint | Trigger a `/safety_event` topic so other nodes know |

**Failure visibility:**

- Counters per joint per failure mode published at 1 Hz on `/safety_envelope_counters`. Foxglove panel shows them. Sudden uptick on one joint = telltale sign of a stuck encoder, bad URDF limit, or a mechanical bind.

**Open questions:**

- Whether velocity-limit violations should clamp (smooth gait continues) or reject (gait gets jerky, but you'll notice the bug faster). Lean **clamp + count + alarm if counter >10/s** so a smooth controller stays smooth but a runaway controller still surfaces.
- Load limit: STS3215 reports load in % of stall, but the value is noisy. Need to confirm whether 3-sample mean is enough or if a longer window matters — measure during first walk tests.
- Whether to add a "soft envelope" inside the hard envelope: refuse to enter the outer 5° of joint range during gait, but allow it for manual posing. Useful for stair-climbing eventually.

---

## Iteration speed

### 4. Single `nova bringup` launcher with profiles

**Goal:** today, bringing up the full stack means remembering ~6 launch files in the right order. By Phase 3 it'll be more. One command, named profiles.

**Scope:**

- ROS 2 launch file at `ros2_ws/src/nova_ops/launch/bringup.launch.py` that composes existing per-package launches based on a `profile` argument.
- Profiles map to actual lifecycle: each profile is a declarative list of "include these launches, set these params, gate on these prereqs."

| Profile | Includes | When to use |
|---------|----------|-------------|
| `bench` | Teensy uROS bridge only (no gait, no sensors) | Servo ID setup, firmware iteration on the desk |
| `sensors` | RealSense + L2 + IMU + dashcam | Sensor smoke tests, data collection |
| `slam` | `sensors` + POINT-LIO + robot_state_publisher | SLAM tuning, mapping runs |
| `walk` | Teensy bridge + gait controller + safety envelope + dashcam + IMU only | Bench-stand → walk tests |
| `full` | `walk` + `slam` + Nav2 + Foxglove bridge | Autonomous runs |
| `vla` | `full` + VLA inference node | Phase 4 — manipulation runs |

**Conveniences:**

- `--dry-run` prints what *would* launch without launching.
- `--no-preflight` skips the health check (useful when intentionally testing a degraded state).
- `--record` overrides the dashcam profile to also record camera + lidar (the big-bandwidth bag) for the duration of the launch.
- Standard `--ros-args -p` overlay still works for per-run param tweaks.

**Where this differs from a wrapper script:**

A bash wrapper that just calls 6 launch files in sequence would mostly work, but loses (a) clean teardown on Ctrl-C (Python launch handles process tree), (b) `ros2 launch` log aggregation, (c) launch event hooks (e.g., "wait for `/joint_states` before starting gait"). Pay the launch-file Python cost up front.

**Open questions:**

- Whether to put profile definitions in YAML and have one launch file interpret it, vs one launch file per profile. Lean **single launch file + YAML profile definitions** so adding a profile is `git add nova_ops/profiles/foo.yaml`, not a new .py.
- Whether `nova bringup` should be a shell alias / setuptools entry-point vs `ros2 launch nova_ops bringup.launch.py profile:=walk`. Entry-point is nicer to type and discoverable via tab-completion.

---

### 5. `make deploy` for Teensy firmware

**Goal:** once the Teensy is mounted inside the chassis, replugging it into the laptop USB to reflash is a pain. Build on the laptop, deploy over the Jetson's USB connection to the Teensy.

**Scope:**

- Add a `deploy` target to `firmware/teensy/firmware/Makefile` (or `platformio.ini` `extra_scripts`):
  1. Local build via `pio run -e teensy41` → produces `.pio/build/teensy41/firmware.hex`.
  2. Hash the hex, compare against `~/.nova/last-deployed.hash` on the Jetson — skip if identical (no point cycling the bus master if nothing changed).
  3. `scp` the hex to the Jetson (`/tmp/nova-firmware.hex`).
  4. Trigger a remote `teensy_loader_cli --mcu=TEENSY41 -w -v /tmp/nova-firmware.hex` over SSH.
  5. Wait for the Teensy USB device to re-enumerate (Linux: poll `/dev/ttyACM*`).
  6. Run `ros2 topic echo --once /firmware_version` to confirm the new firmware is alive.

**Prerequisites on the Jetson:**

- `teensy_loader_cli` from `koromix/teensy_loader_cli`, built from source (it's a 1-file C compile).
- A udev rule giving the user write access to `/dev/hidraw*` (Teensy bootloader uses HID, not serial). One-time setup.
- SSH key-based auth from laptop to Jetson (almost certainly already set up).

**Safety belt:**

- Refuse to deploy if E-stop is released (i.e., if a fault could cause motion during the post-flash reboot). Operator must engage E-stop first; `make deploy` reads the GPIO state via SSH before proceeding.
- Refuse to deploy if the gait controller is running (`pgrep -f gait_controller`). Same reason.

**Open questions:**

- Whether to also auto-tag a git commit with the deployed firmware hash so the running version is reconstructible. Lean yes — needed for the dashcam metadata in [§2](#2-always-on-rosbag-dashcam) anyway.
- Whether deploys should always happen from a clean tree (`git status` empty) to prevent "what version is on the robot" confusion. Yes — refuse with override flag `--allow-dirty` for development.

---

### 6. Bag replay harness

**Goal:** iterate on SLAM, Nav2, the gait controller, and (eventually) the VLA policy without putting the hardware under load. Once you have a few good rosbags, you can run perception/planning offline indefinitely.

**Scope:**

- `ros2 run nova_ops replay <bag-path>` wraps `ros2 bag play` with a few important defaults:
  - `--clock` enabled, all consumers set `use_sim_time: true` (every package's launch file needs to honor a `use_sim_time` arg).
  - `--rate 0.5` default for first pass (lets a stressed laptop keep up).
  - **Topic remap to mask hardware-side nodes**: if the bag contains `/joint_states`, the live Teensy driver should not be running — replay should refuse to start if it detects the bridge node is up.
- Profiles mirroring the bringup profiles, but consuming-from-bag:

| Replay profile | Plays | Runs live |
|---------------|-------|-----------|
| `slam` | sensors + IMU + tf | POINT-LIO, robot_state_publisher |
| `nav` | sensors + tf + map | Nav2, planner |
| `gait` | IMU + joint_states + joint_commands | Gait controller in *shadow* mode (publishes to `/joint_commands_replay`, not the bus) |

**Visibility:**

- During replay, run the dashcam *in replay mode* — record the outputs of the live nodes (e.g., POINT-LIO's `/Odometry`) to a new bag stamped with the SHA of the code under test. Lets you compare runs over time.

**Open questions:**

- Whether to integrate with `rosbag2`'s message filters to drop noisy topics before replay. Useful when you accidentally recorded full image streams and only want the IMU.
- Handoff strategy when the live node needs *initial* hardware state but then takes over (e.g., gait controller wants the very first `/joint_states` to bootstrap its kinematic state). Probably let the bag publish the first 100 ms, then handoff. Worth a small mode flag.

---

## Visibility

### 7. Persistent telemetry → time-series store

**Goal:** the INA226s, servo telemetry, IMU, and battery are all already on ROS 2 topics — they're ephemeral. Logging to a time-series DB unlocks "why did the pack die faster on Tuesday" and "did that gait change reduce hip current draw" without re-instrumenting each time.

**Scope (light-touch v1):**

- **Stack:** InfluxDB 2.x + Grafana, both running in Docker on the Jetson. InfluxDB native ARM64 images exist; resource cost ~150 MB RAM idle, manageable on 8 GB.
- **Bridge:** small ROS 2 node `nova_ops/telemetry_writer` that subscribes to the topics below and writes line-protocol to InfluxDB. One node, ~150 lines of Python.

**Topics + measurements:**

| Topic | Measurement | Tags | Fields |
|-------|-------------|------|--------|
| `/diagnostics` (per status) | `diagnostic` | name, hardware_id, level | message |
| `/servo_telemetry` | `servo` | joint_id (1-12), name | voltage, temp_c, load_pct, position, velocity |
| `/ina226/leg_7v5` | `rail` | rail="leg" | volts, amps, watts |
| `/ina226/hip_12v` | `rail` | rail="hip" | volts, amps, watts |
| `/ina226/jetson_12v` | `rail` | rail="jetson" | volts, amps, watts |
| `/battery_voltage` | `battery` | (none) | volts, est_soc_pct |
| `/imu/data` (D456) | `imu` | sensor="d456" | accel_{x,y,z}, gyro_{x,y,z}, temp_c |
| Jetson `tegrastats` (via shell exporter) | `jetson` | (none) | gpu_load, cpu_load, ram_used_mb, soc_temp_c, power_mw |

**Retention:**

- Raw resolution: 7 days.
- Downsampled (1-minute mean): 90 days, then dropped. InfluxDB has built-in tasks for this — set up via Flux script in version control under `ops/influx/`.

**Grafana dashboards** (committed JSON in `ops/grafana/`):

1. **Power overview** — battery, three INA226 rails, Jetson SoC power, all on one timescale. Annotated with bag-trigger events.
2. **Servo health** — per-joint temperature heatmap (joint_id × time), load %, position vs command error.
3. **Compute health** — Jetson CPU/GPU/RAM/temp, ROS 2 node CPU+RSS.
4. **Session view** — picks a single bag time window and shows everything for that window.

**Open questions:**

- Whether to run InfluxDB on the Jetson or punt it to a desktop machine. Jetson keeps the data local + survives WiFi outage, but costs ~150 MB RAM you may want for VLA. Lean Jetson now, migrate if memory pressure shows up.
- Whether to alert (Grafana alerting) on, e.g., hip rail current >7A sustained, or just log. Lean **log only** for v1; alerting is a tar pit and the safety envelope ([§3](#3-per-joint-safety-envelope-in-the-gait-controller)) covers actual emergencies.

---

### 8. RGB LED status pattern on the Arduino Nano

**Goal:** at-a-glance robot state without tailing logs. Critical when the robot is across the shop and you want to know "is it ready" or "did it fault" without a laptop.

**Scope:**

- Nano already in the aux-peripheral role per [`README.md`](../README.md) hardware architecture. WS2812 strip (or single RGB LED) connected to one Nano digital pin.
- Add a topic `/status_color` (uint8 r, g, b, optional `pattern`: solid / blink_slow / blink_fast / pulse) published by a `nova_ops/status_led` node on the Jetson, bridged to the Nano via the existing I²C path (Nano already on the aux I²C bus).
- State machine in the Jetson node consumes:
  - `/preflight_status` → red if last preflight failed
  - `/estop_state` → solid red if engaged
  - `/battery_voltage` → amber if <13.5V, blinking amber if <13.0V
  - `/diagnostics` aggregated → red if any ERROR, amber if any WARN
  - Gait controller state → green if walking, blue if standing-by, off if uninitialized
  - Dashcam state → small blue blip every 10 s if recording, "freeze flash" magenta when bag is frozen for an incident

**Priority rule:** highest-severity state wins. E-stop > preflight fail > error > battery critical > warn > recording > nominal. Single visible color at any time, no rainbow chaos.

**Open questions:**

- WS2812 vs simple common-cathode RGB. WS2812 lets you do a 5-pixel strip with one wire and show multiple states; common RGB is 3 wires and 3 PWM channels. Lean WS2812.
- Whether the LED logic should fail-safe if the Jetson is dead — Nano could blink red at 2 Hz if it hasn't received a `/status_color` update in >2 seconds. Yes, do this — covers the "Jetson crashed and you can't tell" case.

---

### 9. Battery state-of-charge widget

**Goal:** "12 minutes remaining" beats "14.1 V" when you're deciding whether to start a 10-minute walk test.

**Scope (v1 — simple, surprisingly useful):**

- Coulomb-count: INA226 on the battery feed already gives you amps at 1 Hz. Integrate to get Ah consumed. Subtract from pack nominal (4S 4000 mAh × derate-to-nominal-from-fullycharged = ~3600 mAh usable to LVC).
- Time remaining: rolling-mean current draw (last 60 s) → `remaining_Ah / mean_A * 60 = minutes_left`. Recompute every second.
- Calibration on each charge: bringup checks battery voltage at rest; if >16.6V, assume 100% full. If <13.5V at rest, refuse to set the counter and warn user to charge first.

**Scope (v2 — if v1 is wrong too often):**

- Replace linear assumption with a per-cell discharge curve (LiPo cells have a known V→SoC mapping). Look up SoC from voltage during a "rest" window (current draw <0.2 A for >5 s), use that as the integrator reset point.
- Account for temperature derating (cold pack delivers less capacity). MPU-6050 or D456 ambient is close enough to pack-side temperature for a first cut.

**Surface:**

- `/battery_soc` topic (`percent`, `minutes_remaining`, `quality: ESTIMATED|CALIBRATED|UNRELIABLE`).
- Foxglove panel from [`notes-virtual-view-autocal.md`](./notes-virtual-view-autocal.md) §1 shows a big number + a runtime graph.
- LED state machine in [§8](#8-rgb-led-status-pattern-on-the-arduino-nano) consumes this for the amber thresholds.

**Open questions:**

- Whether to persist the coulomb-counter across reboots (so a brief power cycle doesn't lose state). Probably yes — write to `/var/lib/nova/battery-state.json` on every shutdown, restore on boot, mark `UNRELIABLE` if the file is >30 minutes old (battery may have been swapped).
- Whether to log SoC at the moment of each known event (E-stop, fault, manual freeze) into the dashcam metadata — useful for "robot fell when battery was at 22%, recheck for brownout risk."

---

## Stretch / Phase 4-ish

### 10. Gazebo or Isaac Sim digital twin sharing the real topic graph

**Goal:** develop gait, Nav2, VLA without hardware-in-the-loop. The robot was on the bench → now in chassis → now battery-only — and at each transition, iteration speed drops. Sim breaks the dependency on hardware availability.

**Scope (Gazebo first, since it's lighter and Humble-native):**

- New package `nova_sim` with a Gazebo (Ignition / `gz-sim 8.x`) world containing the URDF as a controllable model, plus a simple terrain mesh.
- Plugins:
  - `gz_ros2_control` to expose simulated joint actuators on `/joint_commands` and publish `/joint_states` — *same names, same QoS as the real Teensy bridge*. This is the whole point: every consumer (gait, viz, dashcam) works unchanged.
  - `gz_sim_sensors_system` for camera + depth + IMU; topic-remapped to match the real RealSense and L2 topic names.
- Time: `use_sim_time: true` everywhere. Same flag as bag replay ([§6](#6-bag-replay-harness)) — share the plumbing.
- No L2 LiDAR plugin in Gazebo Humble currently; substitute a 64-line LiDAR plugin or import POINT-LIO test bags for LiDAR-only iteration. (Or invest in Isaac Sim if VLA work demands photoreal RGB — but that's a different machine.)

**Mock hardware nodes** to absorb topics that the sim doesn't natively produce:

- `mock_servo_telemetry`: publishes synthetic load/temp from sim joint efforts.
- `mock_ina226`: publishes per-rail current as `f(sum of joint efforts × voltage)` — rough but enough to develop the dashboard against.
- `mock_battery`: starts at user-specified SoC, drains by integrating the mock INA226. Lets you exercise [§9](#9-battery-state-of-charge-widget) without waiting for real packs to drain.

**Bringup integration:**

- New profile `sim` in `nova bringup` ([§4](#4-single-nova-bringup-launcher-with-profiles)) — launches Gazebo + the model + mocks instead of hardware-side bridges. Gait controller is unaware which it's talking to.

**Open questions:**

- Whether the URDF should have sim-only vs hardware-only blocks (sim plugins, hardware-specific gazebo tags). Best practice is xacro macros — but only worth the abstraction work once a second consumer of the URDF exists.
- Whether to model the bus latency in sim (inject 5 ms delay on `/joint_commands` to mimic uROS over USB). Useful for catching controllers that secretly rely on zero-latency feedback. Lean yes, behind a sim-arg, default off.
- Isaac Sim is the right answer for VLA photoreal data collection (Phase 4) but not for v1. Note it here so the Gazebo work doesn't preclude an Isaac path later — keep the URDF Isaac-compatible (no Gazebo-only tags outside xacro macros).

---

## Cross-cutting: where this lives in the repo

These features collectively need a new package `nova_ops` (sibling of `nova_description`, `nova_gait`, etc. as planned in [`work-schedule.md`](./work-schedule.md) Week 2). Suggested layout:

```
ros2_ws/src/nova_ops/
├── nova_ops/
│   ├── preflight/         # §1 check definitions
│   ├── dashcam/           # §2 recorder + freeze handler
│   ├── safety/            # §3 envelope wrapper
│   ├── telemetry/         # §7 InfluxDB writer
│   ├── status_led/        # §8 state machine
│   ├── battery_soc/       # §9 coulomb counter
│   └── replay/            # §6 bag harness
├── launch/
│   ├── bringup.launch.py  # §4
│   └── profiles/          # §4 YAML profile defs
├── scripts/
│   └── preflight          # CLI entry-point
└── package.xml

ops/                       # outside ros2_ws — non-ROS tooling
├── influx/                # §7 Flux retention scripts
├── grafana/               # §7 dashboard JSON
└── deploy/                # §5 Teensy deploy helpers
```

Top-of-package README in `nova_ops/` explains "this package is the operations layer — nothing here is on the gait critical path; everything is allowed to crash without killing the robot." Worth saying explicitly so a future contributor doesn't put time-critical control loops in here.

---

## Suggested rollout order

Pick from the top of this list during Phase 1 idle time. Rough ordering by "pays back the implementation cost soonest":

1. **§1 preflight** — solid value during Phase 1 servo bring-up itself. Build it first because each subsequent feature wants a check entry.
2. **§4 nova bringup** — Phase 1 will have enough launches to make this hurt; ride that pain into building the launcher.
3. **§5 make deploy** — second-week-of-Phase-1 firmware iteration will demand this.
4. **§2 dashcam** — needed before the first walk attempt.
5. **§3 safety envelope** — paired with the first gait controller commit in Phase 2.
6. **§8 LED + §9 SoC** — Phase 2 polish, low effort, high "feels solid" payoff.
7. **§7 telemetry** — Phase 2-3 once there's enough behavior to study.
8. **§6 bag replay** — Phase 3 when SLAM/Nav iteration is the bottleneck.
9. **§10 sim** — Phase 4 prep, or earlier if hardware downtime stretches.

---

> **Status:** notes only, not on the active schedule. Other agents may break these out into per-feature design docs or checklist items under [`checklists/`](./checklists/).
