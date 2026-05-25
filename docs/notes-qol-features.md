# Feature Notes — Quality-of-Life Software Features

Forward-looking software ideas to make this build less painful to operate, debug, and iterate on. Captured 2026-05-24. None are on the active schedule — pick them up opportunistically during Phase 1/2, or batch into a "QoL sprint" once the v1 walk gait is stable. Companion to [`notes-virtual-view-autocal.md`](./notes-virtual-view-autocal.md).

Ordering is roughly highest-payoff-per-hour first within each group. All paths assume the repo layout under `ros2_ws/src/` with a new `nova_ops` package as the home for orchestration/safety/health utilities — that package doesn't exist yet, creating it is part of the work.

---

## Operations & safety

### 1. Pre-flight health check

**Goal:** one command answers "is the robot ready to move?" before you let it. Catches dead bus, unplugged Cat6, dead pack, missing sensor topic, stale firmware — all of which currently surface as confusing failures mid-test.

**Scope:**

- New ROS 2 node `nova_ops/preflight_check` exposing a service `~/run` returning a structured pass/fail per check plus an overall result.
- Same node also publishes `/preflight_status` (`diagnostic_msgs/DiagnosticStatus` or a small custom msg with `overall: OK|WARN|FAIL` + `last_run_stamp` + per-check rows) at 0.2 Hz, latched. The service updates this topic on each run. Consumers like the §8 LED state machine read the topic instead of polling the service.
- Provide a CLI wrapper `ros2 run nova_ops preflight` that just calls the service, pretty-prints to terminal, and exits non-zero on fail (so it can gate the bringup launch file).
- Each check is a small Python class implementing `name()`, `run() -> (Status, message)` so adding a new check is one file and one entry in the registry.

**v1 check set** (ship exactly these, add more only when a failure makes you wish you had):

| Check | What it does | Fail mode |
|-------|--------------|-----------|
| Bus presence + freshness | Read `/servo_present_mask` (Int32 bitmask — bit i = joint i has answered *since boot*, not "is alive now") AND `/joint_states` (200 Hz) within the last 1 s. Both required: mask catches dead-at-boot servos, freshness catches one that answered at boot then died mid-session. | Missing IDs (from mask) and/or stale `/joint_states` listed separately |
| E-stop | Read latest `/estop` topic — must be `false` (released) | "E-stop engaged" — refuse to bring up gait |
| Battery latch | Read latest `/battery_low` topic — must be `false`. (Continuous voltage isn't measured today; see §9.) | "Battery comparator tripped (≤13.0 V)" |

**Subscription QoS gotcha:** `/estop`, `/battery_low`, and `/safety_state` are *edge-change publishes* per the firmware contract — no message arrives until the GPIO changes. A vanilla subscriber that comes up after the last edge sees nothing and times out. The preflight node must subscribe with `transient_local` durability so the last-published value is delivered on connect. (Verify the firmware publishes with `transient_local` too — if it's `volatile`, the QoS won't match and the subscription will drop. Coordinate the QoS profile in both places.)

**v2 check set** (add as needs surface):

- **Per-joint voltage / temperature** — depends on the ⏳ `REG_PRESENT_VOLTAGE` / `REG_PRESENT_TEMPERATURE` work landing in `feetech_bus.h::poll_one_servo()` (firmware README §"Stubs to fill in"). Until then there's no per-joint V/temp topic to read; don't code the check yet.
- **Topic liveness** for each expected topic (count of pubs ≥1, last message age <2× expected period). Easy to add once the topic list is stable.
- **Network** — ping L2 at 192.168.1.62, 100 ms timeout.
- **Disk space** — `/` and `/var/log` >2 GB free; avoids mid-walk rosbag write failure.
- **Firmware version match** — `/firmware_version` reports `nova-teensy <git-sha> loop=<hz>Hz`. Compare the SHA against the `git_sha` field in `~/.nova/last-deployed.json` (written by `make deploy`, see §5). **Don't** compare against repo `HEAD` directly — any uncommitted WIP would false-mismatch.
- **Time sync** — drift between Jetson `CLOCK_REALTIME` and last bag stamp <500 ms. Jetson L4T ships systemd-timesyncd by default; don't assume chrony.

**Integration:**

- Bringup launch file (see [§4](#4-single-nova-bringup-launcher-with-profiles)) calls the service after all nodes settle (3 s sleep), refuses to enable the gait controller if any **critical** check fails (servo presence, E-stop, battery). Warnings print but don't block.
- A `--quick` flag skips the network ping and topic-liveness wait, so it can run pre-power-on in <500 ms.

**Open questions:**

- Whether to put the check definitions in YAML (data-driven) or Python (code-driven). Lean Python — checks need varied logic; YAML would push that into a DSL.
- Whether a failed check should auto-suggest the fix or just report. Suggestion strings nice but rot fast — start with report-only.

---

### 2. Always-on rosbag dashcam

**Goal:** when something fails — E-stop trips, a servo faults, a node crashes, the robot does something weird — you have the last few minutes of state to reconstruct what happened. Today this would require remembering to start a bag before every test.

**Scope:**

- Dedicated `nova_ops/dashcam` node wrapping `rosbag2`'s recorder API.
- Records to a **circular buffer on disk**: rosbag2 has `--max-bag-duration` to roll bag files at fixed intervals (e.g. 60 s), plus `--max-bag-size`; combine with a background janitor task that deletes the oldest bag once total directory exceeds a configured retention (default 2 GB → ~5 min of mid-bandwidth recording). `rosbag2` has no built-in total-bytes cap, so the janitor is unavoidable.
- Format: **MCAP** (`storage-id: mcap`) — better tooling than sqlite3, faster random access, Foxglove plays it directly. Available in Humble via `ros-humble-rosbag2-storage-mcap`.

**Topic set (start narrow, expand as warranted) — names match the firmware contract in `firmware/teensy/firmware/README.md`:**

```
/joint_states                       # 200 Hz from Teensy (sensor_msgs/JointState — pos/vel/load in effort[])
/joint_commands                     # 100 Hz from gait controller (sensor_msgs/JointState)
/joint_cmd_rx_count                 # 1 Hz — sub-callback ack counter
/servo_present_mask                 # 1 Hz — bit i = joint i answered since boot
/servo_read_err_count               # 1 Hz — aggregate bus error counter
/servo_err_timeout                  # 1 Hz
/servo_err_bad_frame                # 1 Hz
/servo_err_servo                    # 1 Hz
/power_rails                        # 10 Hz Float32MultiArray (9 floats — leg/hip/jetson V/A/W)
/estop                              # edge — Bool, raw GPIO
/battery_low                        # edge — Bool, raw GPIO
/safety_state                       # edge — Int32, latched FSM (0=NORMAL 1=ESTOP 2=BATT_LOW 3=FAULT)
/loop_max_us, /loop_p99_us          # 1 Hz — ISR response latency
/loop_exec_max_us, /loop_exec_p99_us, /tick_missed_count  # 1 Hz — exec quality
/firmware_version                   # 0.1 Hz — pinned for incident reconstruction
/camera/accel/sample                # 101 Hz — D456 accel (per project log 2026-05-18)
/camera/gyro/sample                 # 200 Hz — D456 gyro
# /imu/data from MPU-6050 not on a topic yet — add once a Nano-side IMU node lands
/cmd_vel                            # whatever the controller pubs
/tf, /tf_static                     # for replay-time URDF reconstruction
# Cameras + lidar deliberately omitted — too much bandwidth for always-on.
# Spin up a second recorder profile (`nova_ops/dashcam_perception`) for runs where you want them.
```

Per-joint voltage + temperature are *not* yet on a topic (firmware ⏳); add them to this list when the stub lands.

**Trigger / freeze:**

- Subscribe to `/estop`, `/safety_state`, and `/diagnostics` (once an aggregator is running). On E-stop engage, `safety_state` going non-zero, or any diagnostic going to ERROR: **stop rotation** (so the buffer at fault time is preserved) and copy the current bag set into `/var/log/nova/incidents/<iso-timestamp>/`.
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

- Lives in the **Jetson-side gait controller**, not the Teensy. Teensy gets to assume commands are pre-validated (so the 200-500 Hz bus loop stays tight).
- Two implementation shapes — pick one, don't do both:
  - **(a) In-process wrapper** — gait code calls `safe_publish(joint_commands)`, wrapper either publishes or clamps+logs. Lowest latency. Risk: any other publisher to `/joint_commands` bypasses the check. Acceptable if the gait controller is the only publisher (enforce via package layout / lint, not at runtime).
  - **(b) Standalone filter node** — subscribes `/joint_commands_raw`, publishes `/joint_commands`. Topology-enforced. Costs one extra hop (~sub-ms typically) and a topic rename in the gait controller. Robust against future publishers.
  - Lean (a) for v1 + a comment in `joint_commands` publishers reminding them to go through the wrapper; revisit (b) if a second publisher ever materializes.
- Pulls limits from the URDF (`<limit lower upper effort velocity>` tags on each `<joint>`). Single source of truth — URDF already needs to be right for IK/sim/viewers anyway.

**Per-joint checks on every command** (rows marked ⏳ depend on per-joint V/temp telemetry landing in firmware — see firmware README "Stubs to fill in"):

| Check | Rule | Action on violation |
|-------|------|---------------------|
| Position | `lower ≤ goal ≤ upper`, with 2° margin inside URDF limits | Clamp to limit, log warn (first 10 occurrences per joint, then throttle) |
| Velocity | Numerically diff goal vs last command vs Δt; reject if > URDF velocity limit | Replace goal with last + sign × v_max × Δt |
| Load | STS3215 load is in `effort[]` of `/joint_states` (firmware contract). 3 samples >70% sustained → refuse new goals that increase load, allow ones that reduce | "Joint overloaded — backing off" + log |
| Temperature ⏳ | Per-joint temp not yet published — gated on firmware stub. Once available: >60°C → derate by 20% (slew rate halved); >70°C → reject all goals for that joint | Publish on a new `/safety_envelope_events` topic (software-side, distinct from the firmware's hardware-latched `/safety_state` FSM) |

**Failure visibility:**

- Counters per joint per failure mode published at 1 Hz on `/safety_envelope_counters`. Before Foxglove lands, `ros2 topic echo --once /safety_envelope_counters` is enough; once it does, build a Foxglove plot panel. Sudden uptick on one joint = telltale sign of a stuck encoder, bad URDF limit, or a mechanical bind.

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
  2. SHA256 the hex blob, read the `hex_sha256` field from `~/.nova/last-deployed.json` on the Jetson — skip if identical (no point cycling the bus master if nothing changed).
  3. `scp` the hex to the Jetson (`/tmp/nova-firmware.hex`).
  4. Trigger a remote `teensy_loader_cli --mcu=TEENSY41 -w -v /tmp/nova-firmware.hex` over SSH.
  5. Wait for the Teensy USB device to re-enumerate (Linux: poll `/dev/ttyACM*`).
  6. Confirm the new firmware is alive: `timeout 15 ros2 topic echo --once /firmware_version`. `/firmware_version` publishes at 0.1 Hz (once per 10 s) so a plain `--once` can hang up to that long; the timeout fails loud instead of silent-stalling.
  7. Write `~/.nova/last-deployed.json` with both `git_sha` (the source SHA embedded in `/firmware_version`, used by §1) and `hex_sha256` (the blob hash, used by step 2). Single file, both fields, no naming-collision risk.

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

**v1 (cheap, ships in an afternoon):**

- A thin wrapper `ros2 run nova_ops replay <bag-path>` that calls `ros2 bag play --clock --rate 0.5 <bag>`, and sets `use_sim_time:=true` on a fixed list of launch files for the perception stack (POINT-LIO + robot_state_publisher).
- Hard prereq: every package whose launch is invoked must accept and propagate a `use_sim_time` arg. POINT-LIO + robot_state_publisher already do; per-package launch files we write need to.

**v2 (only if v1 is the bottleneck):**

- Profile system mirroring `nova bringup`:

| Replay profile | Plays | Runs live | Status |
|---------------|-------|-----------|--------|
| `slam` | sensors + IMU + tf | POINT-LIO, robot_state_publisher | feasible today |
| `nav` | sensors + IMU + tf + POINT-LIO `/map` (recorded from a prior SLAM run, or load a pre-built `.pgm`/yaml via `nav2_map_server`) | Nav2 planner + controller | feasible once Nav2 is up; map source has to be explicit, not assumed |
| `gait` | IMU + joint_states + joint_commands | Gait controller, output remapped to `/joint_commands_shadow` so nothing hits the bus | **prereq: gait controller has to support a shadow-output mode; not free** |

- Refuse to start if the live Teensy bridge is publishing `/joint_states` (else the bag-played and live messages collide).
- Optional: record live-node outputs (POINT-LIO's `/Odometry`, etc.) to a new bag stamped with the SHA of the code under test for run-over-run comparison.

**Open questions:**

- Whether to integrate with `rosbag2`'s message filters to drop noisy topics before replay. Useful when you accidentally recorded full image streams and only want the IMU.
- Handoff strategy when the live node needs *initial* hardware state but then takes over (e.g., gait controller wants the very first `/joint_states` to bootstrap its kinematic state). Probably let the bag publish the first 100 ms, then handoff. Worth a small mode flag.

---

## Visibility

### 7. Persistent telemetry → time-series store

**Goal:** the INA226s, servo telemetry, IMU, and battery are all already on ROS 2 topics — they're ephemeral. Logging to a time-series DB unlocks "why did the pack die faster on Tuesday" and "did that gait change reduce hip current draw" without re-instrumenting each time.

**Scope (v1 — start cheap, no daemons):**

- Roll a rotating CSV writer first: `nova_ops/telemetry_csv` node subscribes to the topic set below, appends to `/var/log/nova/telemetry/<date>.csv.gz` (one file per day, gzipped on rotation). Plot with `pandas` + `matplotlib` ad-hoc.
- This costs <50 MB RAM, no Docker, no schema migration. Most "why did the pack die faster" questions answer from CSV + a notebook.

**Scope (v2 — only if the ad-hoc plotting is the actual bottleneck):**

- InfluxDB 2.x + Grafana, both in Docker on the Jetson. **Realistic resource cost is closer to 300-500 MB RAM combined under live ingest, not the 150 MB headline** — non-trivial on an 8 GB box also running ROS 2 + SLAM + (eventually) VLA. Probably belongs on a desktop machine with the Jetson just running the writer, not on-Jetson. Re-evaluate when v1 stops being enough.

**Topics + measurements (names match the firmware contract):**

| Topic | Measurement | Tags | Fields |
|-------|-------------|------|--------|
| `/diagnostics` (per status) | `diagnostic` | name, hardware_id, level | message |
| `/joint_states` | `joint` | joint_id (0-11) | position, velocity, effort (load) |
| `/power_rails` (parse 9-float array) | `rail` | rail ∈ {leg, hip, jetson} | volts, amps, watts |
| `/servo_read_err_count`, `/servo_err_*` | `bus` | err_kind ∈ {timeout, bad_frame, servo, total} | count |
| `/loop_p99_us`, `/loop_exec_p99_us`, `/tick_missed_count` | `firmware_loop` | (none) | p99_us, exec_p99_us, missed |
| `/battery_low`, `/estop`, `/safety_state` | `safety` | (none) | low (bool), estop (bool), state_id |
| (future, ⏳) per-joint voltage + temp | `servo_health` | joint_id | voltage, temp_c |
| `/camera/accel/sample` + `/camera/gyro/sample` (D456, two separate topics — must be re-stitched in the writer) | `imu` | sensor="d456" | accel_{x,y,z} or gyro_{x,y,z} per row |
| `jtop` exporter (jetson-stats) | `jetson` | (none) | gpu_load, cpu_load, ram_used_mb, soc_temp_c, power_mw |

Use `jtop` (the `jetson-stats` Python package) rather than parsing `tegrastats` text — cleaner API, official, designed for L4T.

**Grafana dashboards (only built if v2 happens):**

1. **Power overview** — three INA226 rails + Jetson SoC power on one timescale. Annotated with incident-bundle triggers. Battery rail itself isn't measured (see §9) — overlay the binary `/battery_low` as a state band instead.
2. **Servo health** — per-joint load heatmap (joint_id × time), position vs command error. Add temperature once firmware publishes it.
3. **Compute health** — Jetson CPU/GPU/RAM/temp, ROS 2 node CPU+RSS.

**Open questions:**

- Whether to alert (Grafana alerting) on, e.g., hip rail current >7A sustained, or just log. Lean **log only** for v1; alerting is a tar pit and the safety envelope ([§3](#3-per-joint-safety-envelope-in-the-gait-controller)) covers actual emergencies.

---

### 8. RGB LED status pattern on the Arduino Nano

**Goal:** at-a-glance robot state without tailing logs. Critical when the robot is across the shop and you want to know "is it ready" or "did it fault" without a laptop.

**Scope:**

- Nano already in the aux-peripheral role per [`README.md`](../README.md) hardware architecture, with its own I²C bus (Nano is *master* of that bus, not a slave on a Jetson-shared bus). WS2812 strip (or single RGB LED) connected to one Nano digital pin.
- **Jetson↔Nano transport — pick one, then commit:**
  - **USB-serial** (Nano shows up as `/dev/ttyUSB*` on Jetson). Simplest, most common Nano setup, no new bus wiring. Lean this.
  - **GPIO bit-bang** for a single status pin on the Nano. Lighter still but only carries one signal.
  - I²C-slave on the Nano is technically possible (Wire library slave mode) but turns the Nano's bus into a multi-master arrangement with the existing peripherals — avoid.
- Add a topic `/status_color` (uint8 r, g, b, optional `pattern`: solid / blink_slow / blink_fast / pulse) published by a `nova_ops/status_led` node on the Jetson; the node owns the serial port and writes a small framed protocol to the Nano.
- State machine in the Jetson node consumes (topic names match firmware contract):
  - `/preflight_status` (from §1) → red if last preflight failed
  - `/estop` → solid red if `true`
  - `/safety_state` → red if 2 (battery latch) or 3 (fault), amber if non-zero in a recoverable way
  - `/diagnostics` aggregated → red if any ERROR, amber if any WARN
  - Gait controller state → green if walking, blue if standing-by, off if uninitialized
  - Dashcam state → small blue blip every 10 s if recording, "freeze flash" magenta when bag is frozen for an incident

**Priority rule:** highest-severity state wins. E-stop > preflight fail > error > safety latch > warn > recording > nominal. Single visible color at any time, no rainbow chaos.

**Prerequisite acknowledged:** Nano firmware today is *aux peripherals only* (PIR / OLED / ultrasonic / MPU-6050). Adding a status-LED protocol means new Nano sketch code — not zero work.

**Open questions:**

- WS2812 vs simple common-cathode RGB. WS2812 lets you do a 5-pixel strip with one wire and show multiple states; common RGB is 3 wires and 3 PWM channels. Lean WS2812.
- Whether the LED logic should fail-safe if the Jetson is dead — Nano blinks red at 2 Hz if it hasn't received a frame in >2 seconds. Yes — covers the "Jetson crashed and you can't tell" case.

---

### 9. Battery state-of-charge widget

**Goal:** "12 minutes remaining" beats "14.1 V" when you're deciding whether to start a 10-minute walk test.

**Hardware reality check:** there is **no INA226 on the battery feed** today. The three INA226 chips sit on the output side of the leg / hip / Jetson bucks (`README.md` "Power System" + `firmware/teensy/firmware/src/ina226_telemetry.h`). Battery state surfaces only as the LM393 comparator's binary `/battery_low` GPIO @ 13.0 V. That constrains every implementation option below.

**Option A — sum-of-rails proxy (cheapest, ships with current hardware):**

- Approximate battery input current as `(leg_w + hip_w + jetson_w) / V_batt_assumed`, where `V_batt_assumed` is a static 14.8 V (nominal). Sources for the three rails: `/power_rails` `Float32MultiArray` indices 2 / 5 / 8 at 10 Hz.
- Integrate to Ah consumed. Subtract from usable capacity (`4000 mAh × 0.9 = 3600 mAh` to LVC).
- **Accuracy caveats:** doesn't include buck losses (5-15% depending on load), doesn't include the 5V UBEC + L2 dedicated buck, doesn't react to actual pack voltage sag. Expect ±15-20% error on "minutes remaining." Good enough for "should I start this 10-min test on a 5-min-remaining estimate?" — not good enough for precise telemetry.
- Reset point: bringup assumes 100% if user confirms a freshly-charged pack (no way to measure rest voltage). Add a `--soc=NN` flag to override on bringup.

**Option B — add a 4th INA226 on the battery feed (clean fix, ~$5 + bench time):**

- The firmware already has `NOVA_INA226_L2` as a 4th-rail opt-in build flag. Same pattern: define `NOVA_INA226_BATTERY`, hook one more chip onto the existing I²C bus (address 0x45 or 0x46), wire its shunt before the Class T fuse. PCB v6 has the bus footprint; a bench-wired add-on works for v1.
- Once present: actual battery current + voltage. Coulomb counting becomes meaningful (±3-5% with a few cycles of cal). Reset point becomes "voltage at rest >16.6 V → 100%."
- **Recommend B before investing in v2 below.** Without it, every refinement is layered on top of a ±20% proxy.

**Scope (v2 — assumes Option B is done):**

- Per-cell LiPo discharge curve (V→SoC mapping). Look up SoC from voltage during a "rest" window (current <0.2 A for >5 s), use that as the integrator reset point.
- Temperature derating (cold pack delivers less capacity). MPU-6050 ambient is close enough to pack-side temperature for a first cut.

**Surface:**

- `/battery_soc` topic (`percent`, `minutes_remaining`, `quality: PROXY|MEASURED|UNRELIABLE`) — the canonical source. `PROXY` = Option A, `MEASURED` = Option B.
- Foxglove panel from [`notes-virtual-view-autocal.md`](./notes-virtual-view-autocal.md) §1 shows a big number + a runtime graph. *Until the Foxglove bridge lands (Phase 2 per that doc), the topic is the surface — `ros2 topic echo /battery_soc` works.*
- LED state machine in [§8](#8-rgb-led-status-pattern-on-the-arduino-nano) consumes the same topic for the amber thresholds.

**Open questions:**

- Whether to persist the coulomb-counter across reboots (so a brief power cycle doesn't lose state). Probably yes — write to `/var/lib/nova/battery-state.json` on every shutdown, restore on boot, mark `UNRELIABLE` if the file is >30 minutes old (battery may have been swapped).
- Whether to log SoC at the moment of each known event (E-stop, fault, manual freeze) into the dashcam metadata — useful for "robot fell when battery was at 22%, recheck for brownout risk."

---

## Stretch / Phase 4-ish

### 10. Gazebo or Isaac Sim digital twin sharing the real topic graph

**Goal:** develop gait, Nav2, VLA without hardware-in-the-loop. The robot was on the bench → now in chassis → now battery-only — and at each transition, iteration speed drops. Sim breaks the dependency on hardware availability.

**Scope (Gazebo first, since it's lighter and Humble-native):**

- New package `nova_sim` with a **Gazebo Fortress** (`gz-sim 6.x`) world — Fortress is the Tier 1 binding for Humble per the ROS REPs. Harmonic (`gz-sim 8`) on Humble is possible but unsupported and a known time sink; defer until a Humble→Jazzy migration is on the table.
- Plugins (verify exact package name against the Fortress release you install — naming has churned between `gazebo_ros2_control` (Gazebo Classic), `ign_ros2_control`, and `gz_ros2_control` across releases):
  - A `ros2_control` plugin to expose simulated joint actuators on `/joint_commands` and publish `/joint_states` — *same names, same QoS as the real Teensy bridge*. This is the whole point: every consumer (gait, viz, dashcam) works unchanged.
  - Sensor plugins for camera + depth + IMU; topic-remapped to match the real RealSense and L2 topic names.
- Time: `use_sim_time: true` everywhere. Same flag as bag replay ([§6](#6-bag-replay-harness)) — share the plumbing.
- **LiDAR is the hard part.** Fortress's GPU LiDAR plugin emits a single-line or fan pattern, not the L2's 16384-pt non-repeating prism scan. Two ways out: (a) use the plugin with a coarse 32- or 64-channel approximation, accept that POINT-LIO outputs in sim won't match real-world ones; (b) skip sim LiDAR entirely, drive POINT-LIO from recorded bags ([§6](#6-bag-replay-harness)) for the SLAM-in-sim case. Lean (b) — cheaper and more faithful.

**Mock hardware nodes** to absorb topics the sim doesn't natively produce:

- `mock_servo_load_temp`: publishes synthetic load/temp from sim joint efforts. (Stand-in for the ⏳ firmware per-joint telemetry topics.)
- `mock_power_rails`: publishes `/power_rails` `Float32MultiArray` (9 floats) computed as `f(sum of joint efforts × voltage)` per rail — rough but exercises §7 telemetry + the §9 sum-of-rails SoC proxy.
- `mock_battery`: starts at user-specified SoC, drains by integrating the mock power rails. Lets you exercise [§9](#9-battery-state-of-charge-widget) without waiting for real packs to drain.

**Bringup integration:**

- New profile `sim` in `nova bringup` ([§4](#4-single-nova-bringup-launcher-with-profiles)) — launches Gazebo + the model + mocks instead of hardware-side bridges. Gait controller is unaware which it's talking to.

**Open questions:**

- Whether the URDF should have sim-only vs hardware-only blocks (sim plugins, hardware-specific gazebo tags). Best practice is xacro macros — but only worth the abstraction work once a second consumer of the URDF exists.
- Whether to model the bus latency in sim (inject 5 ms delay on `/joint_commands` to mimic uROS over USB). Useful for catching controllers that secretly rely on zero-latency feedback. Lean yes, behind a sim-arg, default off.
- Isaac Sim is the right answer for VLA photoreal data collection (Phase 4) but not for v1. Note it here so the Gazebo work doesn't preclude an Isaac path later — keep the URDF Isaac-compatible (no Gazebo-only tags outside xacro macros).

---

## Cross-cutting: where this lives in the repo

These features collectively need a new package `nova_ops` (sibling of `nova_description`, `nova_gait`, etc. as planned in [`work-schedule.md`](./work-schedule.md) Week 2, and sibling of the `nova_calibration` package proposed in [`notes-virtual-view-autocal.md`](./notes-virtual-view-autocal.md) — keep them separate, don't fold). Suggested layout:

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

**On-disk paths these features assume** — none exist on a fresh Jetson, and several need permissioning:

| Path | Used by | Created by | Mode |
|------|---------|------------|------|
| `~/.nova/` (e.g. `last-deployed.json`) | §1 preflight, §5 deploy | `make deploy` first-run + bringup `mkdir -p` (per-user path, *not* `tmpfiles.d` territory) | user-owned, `0700` |
| `/var/log/nova/incidents/<ts>/` | §2 dashcam | `tmpfiles.d` snippet | `0775`, group=`nova`, group-writable |
| `/var/log/nova/telemetry/` | §7 CSV writer | `tmpfiles.d` snippet | `0775`, group=`nova`, group-writable |
| `/var/lib/nova/calibration/` | virtual-view §2 auto-cal | `tmpfiles.d` snippet | `0775`, group=`nova`, group-writable |
| `/var/lib/nova/battery-state.json` | §9 SoC persistence | `nova_ops/battery_soc` node on shutdown | user-owned, `0644` |

Ship a `tmpfiles.d` snippet (`/usr/lib/tmpfiles.d/nova.conf`) for the `/var/log/nova/` + `/var/lib/nova/` directories — systemd recreates them on boot, surviving a `/var/log` cleanup or a fresh image. `~/.nova/` isn't a `tmpfiles.d` target (the spec is for system paths); handle it with a one-liner `mkdir -p` in bringup.

---

## Suggested rollout order

Pick from the top of this list during Phase 1 idle time. Rough ordering by "pays back the implementation cost soonest":

1. **§1 preflight (v1 only, 3 checks)** — solid value during Phase 1 servo bring-up itself. Build it first because each subsequent feature wants a check entry. v2 checks land opportunistically.
2. **§5 make deploy** — second-week-of-Phase-1 firmware iteration will demand this. Ship without the dirty-tree / E-stop guards; add them only after a real near-miss.
3. **§2 dashcam** — needed before the first walk attempt. v1 = topic list above + janitor + freeze-on-E-stop. Incident bundle nice-to-haves can wait.
4. **§4 nova bringup** — Phase 1 only has 3-4 launch files in play (Teensy bridge, sensors, SLAM); the launcher pays back later. Build it when the launch count crosses ~6 (Phase 2 mid).
5. **§3 safety envelope** — paired with the first gait controller commit in Phase 2. Position + velocity clamping only; load/temp gated on firmware ⏳ work.
6. **§9 SoC** — only after §9 Option B (add 4th INA226 to battery feed). Without it the v1 proxy gives ±15-20% — useful but not "12 minutes remaining" precise.
7. **§8 LED** — Phase 2 polish. Requires new Nano firmware work; only worth it once §9 SoC is feeding it real thresholds.
8. **§7 telemetry** — Phase 2-3, **CSV writer (v1) only** until Grafana value is proven; resist the InfluxDB+Docker path until the Jetson has memory to spare.
9. **§6 bag replay** — Phase 3 when SLAM/Nav iteration is the bottleneck. v1 = the thin wrapper; profile system only if v1 stops being enough.
10. **§10 sim** — Phase 4 prep. Significant multi-week effort once you start; descope to "kinematic joints + IMU stub" first, defer sensors/terrain.

---

> **Status:** notes only, not on the active schedule. Other agents may break these out into per-feature design docs or checklist items under [`checklists/`](./checklists/).
