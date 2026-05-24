# Feature Notes — Virtual Real-Time Model Viewing + Auto-Calibration

Forward-looking feature ideas, captured 2026-05-24. Not yet scheduled in the phase roadmap — revisit during Phase 2 (locomotion) once `/joint_states`, URDF, and the sensor topics are stable.

---

## 1. Virtual real-time viewing of the model

**Goal:** a live mirror of the physical robot — joints, pose, sensor streams — viewable from any browser, no need to be on the same network as the Jetson via SSH+X11. Useful for tele-monitoring during a walk test, debugging gait visually, screen-recording demos, and showing the build to people without a ROS 2 dev env.

### Inputs already in place

- `/joint_states` (will be) published by Teensy via micro-ROS once Phase 1 firmware is live
- `nova_description` URDF skeleton planned for Week 2 (see [`work-schedule.md`](./work-schedule.md))
- `/unilidar/cloud` @ 12 Hz, `/unilidar/imu`, `/camera/color/image_raw`, `/camera/depth/image_rect_raw`, `/camera/{accel,gyro}/sample` — all confirmed working ([`setup-jetson.md`](./setup-jetson.md) §13, project log 2026-05-18)

### Approach options

| Option | Pros | Cons |
|--------|------|------|
| **Foxglove Studio** (web app + `foxglove_bridge` ROS 2 node) | Browser-based, no ROS install on viewer side; URDF + 3D + plots + image panels in one UI; works over WiFi/Tailscale | External app (cloud-hosted UI by default; can self-host); bandwidth-heavy if streaming raw point cloud |
| **rviz2 over X-forwarding / VNC** | Native ROS tool, free, full control | Needs X11 on viewer, heavy over WAN, brittle over SSH |
| **Custom web viewer** (rosbridge + roslib.js + three.js URDF loader) | Full UI control, lightweight | Build effort; rebuild URDF loader from scratch |
| **NVIDIA Isaac Sim digital twin** | Photoreal, physics-in-the-loop, great for VLA dev | Heavyweight, Jetson can't host it — runs on workstation; sync overhead |

**Recommended starting point:** **Foxglove Studio + `foxglove_bridge`**. Closest to plug-and-play given the stack already running. Phase 2 task.

### Scope sketch

- Install `ros-humble-foxglove-bridge` on Jetson; expose port 8765 over Tailscale (don't open to LAN by default)
- Build a default Foxglove layout: 3D panel (URDF + TF + LiDAR cloud), 2 image panels (D456 color + depth), plots for `/joint_states` position vs `/joint_commands`, INA226 rail telemetry from `/diagnostics`, battery topic
- Decimate point cloud bandwidth if Tailscale link is the bottleneck (subsample on Jetson side via a relay node, don't ship 5042 pts × 12 Hz raw if the link can't take it)

### Open questions

- Bandwidth budget for remote viewing over LTE/WiFi when away from shop — probably need a "low-bandwidth" layout (no cloud, decimated images) vs "on-LAN" layout
- Recording: Foxglove can save rosbag-equivalent `.mcap` files client-side — could double as the demo-capture path
- Authentication on `foxglove_bridge` — defaults to none; require Tailscale ACL or an SSH tunnel

---

## 2. Auto-calibration features

**Goal:** reduce the manual-calibration burden listed in [`calibration.md`](./calibration.md) by automating the routines that don't strictly need a human in the loop. Most are one-shot procedures invoked via ROS 2 services or launch files.

### Candidates (ordered by ease + payoff)

1. **IMU bias auto-zero on boot** — MPU-6050 + D456 IMU + L2 IMU all benefit. On node start, hold still for 5–10 s, average gyro readings, store as bias, subtract on output. Fully automatic, no human input. Trivial to implement as a ROS 2 service `~/calibrate_imu_bias` plus auto-trigger on launch when `/cmd_vel` has been zero for N seconds.
2. **Servo zero-position auto-detect** — current plan is manual per-joint home offset. Auto path: command each leg to a known reference posture (e.g. tibia against a printed jig under the chassis), record `/joint_states` reading, store offset. Requires the jig but no per-joint human tweaking. Could also use hard-stops: drive servo slowly toward mechanical limit, detect current spike via STS3215 load feedback, back off by known mechanical-stop-to-zero offset. Risk: stop-driven calibration stresses gear train — only run with low torque limit.
3. **IMU–LiDAR–camera extrinsic auto-cal** — Kalibr / `lidar_imu_calibration` style: rotate the robot through a known motion, solve for transforms. More involved but eliminates the hand-eye step in [`calibration.md`](./calibration.md). Phase 2+.
4. **EKF covariance auto-tuning** — log `robot_localization` innovations during a known motion, tune covariance matrices via grid search or maximum-likelihood. Nice-to-have, not blocking.

### Scope sketch (per feature)

- Each auto-cal lives as a ROS 2 service in a new `nova_calibration` package
- Persist results to a YAML in `~/.nova/calibration/` (datestamped); loaders read on node start
- Provide a `nova_calibration_status` topic so the rest of the stack knows what's been calibrated and when
- Manual procedures in [`calibration.md`](./calibration.md) become fallback paths, not the default

### Open questions

- Do we want a single "calibrate everything" wizard launch file, or per-routine services? Wizard is more user-friendly but couples the routines; per-routine is more flexible. Lean toward per-routine + a wizard that just calls them in order.
- Storage location: `~/.nova/calibration/` is per-user; consider `/var/lib/nova/calibration/` if multiple users / system service ever runs. Defer until we have a deployment story.
- Auto-recalibration triggers — re-zero IMU on every boot, or only when the stored bias is older than X days / temperature has drifted? Boot-every-time is simplest, costs 5–10 s of startup.

---

## Tie-in to existing roadmap

- **Phase 1:** publishes the inputs both features need (`/joint_states`, sensor topics). No new work yet.
- **Phase 2 (weeks 5–8):** good slot for the Foxglove bridge + first auto-cal routines (IMU bias zero is a natural pair with EKF bring-up).
- **Phase 4 / VLA:** Isaac Sim digital twin becomes much more interesting as a VLA data-collection environment — note here so we don't reinvent it later.

> **Status:** notes only, not on the active schedule. Promote to checklist items when Phase 2 starts.
