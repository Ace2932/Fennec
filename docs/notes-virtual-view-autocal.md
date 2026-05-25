# Feature Notes — Virtual Real-Time Model Viewing + Auto-Calibration

Forward-looking feature ideas, captured 2026-05-24. Not yet scheduled in the phase roadmap — revisit during Phase 2 (locomotion) once `/joint_states`, URDF, and the sensor topics are stable.

---

## 1. Virtual real-time viewing of the model

**Goal:** a live mirror of the physical robot — joints, pose, sensor streams — viewable from any browser, no need to be on the same network as the Jetson via SSH+X11. Useful for tele-monitoring during a walk test, debugging gait visually, screen-recording demos, and showing the build to people without a ROS 2 dev env.

### Inputs already in place

- `/joint_states` is publishing now (200 Hz, `sensor_msgs/JointState`, pos/vel/load in `effort[]` — see `firmware/teensy/firmware/README.md`)
- `/unilidar/cloud` @ 12 Hz, `/unilidar/imu`, `/camera/color/image_raw`, `/camera/depth/image_rect_raw`, `/camera/{accel,gyro}/sample` — all confirmed working ([`setup-jetson.md`](./setup-jetson.md) §13, project log 2026-05-18)

### Hard prerequisites that *aren't* in place yet

A live 3D mirror needs both of these to land before the Foxglove URDF panel can animate anything:

1. **`nova_description` URDF** — the skeleton was carried into Week 2 ([`work-schedule.md`](./work-schedule.md)). No URDF, no model to bind joints to.
2. **JointState `name[]` populated** — firmware deliberately ships `/joint_states` with empty `name[]` and `frame_id` because URDF joint names haven't been frozen (firmware README line 103, "URDF joint-name binding lands when the gait controller is on the Jetson"). Either the gait controller node has to rewrite the message before Foxglove sees it, or the firmware contract changes once joint names are stable. Pick before building the layout — the layout depends on matching strings.

These are pre-§1, not §1 itself. Without them the rest of this scope sketch is moot.

### Approach options

| Option | Pros | Cons |
|--------|------|------|
| **Foxglove Studio** (web app + `foxglove_bridge` ROS 2 node) | Browser-based, no ROS install on viewer side; URDF + 3D + plots + image panels in one UI; works over WiFi/Tailscale | Studio Free tier is cloud-app or desktop only — self-hosted Studio is a paid/enterprise SKU. Bandwidth-heavy if streaming raw point cloud. |
| **rviz2 over X-forwarding / VNC** | Native ROS tool, free, full control | Needs X11 on viewer, heavy over WAN, brittle over SSH |
| **Custom web viewer** (rosbridge + roslib.js + three.js URDF loader) | Full UI control, lightweight | Build effort; rebuild URDF loader from scratch |
| **NVIDIA Isaac Sim digital twin** | Photoreal, physics-in-the-loop, great for VLA dev | Heavyweight, Jetson can't host it — runs on workstation; sync overhead |

**Recommended starting point:** **Foxglove Studio + `foxglove_bridge`**. Closest to plug-and-play given the stack already running. Phase 2 task.

### Scope sketch

- Install + launch on Jetson:
  ```bash
  sudo apt install ros-$ROS_DISTRO-foxglove-bridge
  ros2 launch foxglove_bridge foxglove_bridge_launch.xml port:=8765
  ```
  `$ROS_DISTRO` is `humble` on the current Jetson (per `docs/setup-jetson.md`). Default port is 8765 — keep it, don't expose to LAN, reach it over Tailscale from the viewer.
- Build a default Foxglove layout: 3D panel (URDF + TF + LiDAR cloud), 2 image panels (D456 color + depth), plots for `/joint_states` position vs `/joint_commands`, per-rail power from `/power_rails` (`Float32MultiArray`, 9 floats `[leg_v,leg_a,leg_w,hip_v,hip_a,hip_w,jetson_v,jetson_a,jetson_w]`), `/battery_low` indicator
- Point cloud bandwidth: the ROS bridge already publishes `/unilidar/cloud` at 12 Hz × 5042 pts (the wrapper decimates from the raw L2 stream via `cloud_scan_num: 18`). That's ~1 MB/s on the wire — fine on LAN/Tailscale, tight on LTE. Further decimation needs a relay node since `foxglove_bridge` can't voxel-downsample.

### Open questions

- Bandwidth budget for remote viewing over LTE/WiFi when away from shop — probably need a "low-bandwidth" layout (no cloud, decimated images) vs "on-LAN" layout
- Recording: Foxglove can save rosbag-equivalent `.mcap` files client-side — could double as the demo-capture path
- Authentication on `foxglove_bridge` — defaults to none; require Tailscale ACL or an SSH tunnel

---

## 2. Auto-calibration features

**Goal:** reduce the manual-calibration burden listed in [`calibration.md`](./calibration.md) by automating the routines that don't strictly need a human in the loop. Most are one-shot procedures invoked via ROS 2 services or launch files.

### Candidates (ordered by ease + payoff)

1. **Gyro bias auto-zero on boot** — MPU-6050 + D456 IMU. On node start, hold still for 5–10 s, average gyro readings, store as bias, subtract on output. (L2 IMU would also benefit but the ROS bridge isn't delivering frames yet — see project log 2026-05-18 and `notes-qol-features.md`; add once the bridge bug is resolved.) Trivial to implement as a ROS 2 service `~/calibrate_gyro_bias`. Auto-trigger on launch by sampling the IMU itself — if gyro magnitude stays <0.01 rad/s for 5 s, the robot is stationary; run the cal. **Don't gate on `/cmd_vel` being zero** — that topic doesn't exist until the controller is up, which is post-launch. Accel bias is a separate, harder problem (needs known gravity orientation) — skip for v1; D456 has factory accel cal in its flash.
2. **Servo zero-position auto-detect** — current plan is manual per-joint home offset. Auto path: command each leg to a known reference posture (e.g. tibia against a printed jig under the chassis), record `/joint_states` reading, store offset. Requires the jig but no per-joint human tweaking. Could also use hard-stops: drive servo slowly toward mechanical limit, detect current spike via STS3215 load feedback, back off by known mechanical-stop-to-zero offset. Risk: stop-driven calibration stresses gear train — only run with low torque limit.
3. **Camera–IMU extrinsic auto-cal (Kalibr)** — D456 has its own IMU so this is mostly checking that the factory extrinsics are still valid; rerun if the camera is remounted. Phase 2+.
4. **LiDAR–IMU extrinsic auto-cal** — separate tool (`lidar_imu_calibration` / `lidar_align`-class). Rotate the robot through known yaw/pitch, solve for the transform. Needed before EKF fusion can use both sources. Phase 2+.
5. **LiDAR–camera extrinsic** — target-based (chessboard visible in both depth and intensity), typically `lidar_camera_calibration` package. Lowest priority until visual+LiDAR fusion actually fires up.
6. **EKF covariance — log innovations for offline review** — `robot_localization` exposes innovation topics; record during a known motion, plot offline, tune by hand. Full auto-tuning (grid search / MLE) is a research project, deliberately out of scope.

### Scope sketch (per feature)

- Each auto-cal lives as a ROS 2 service in a new `nova_calibration` package (sibling of, not folded into, `nova_ops` from [`notes-qol-features.md`](./notes-qol-features.md))
- Persist results to a YAML in `~/.nova/calibration/` (datestamped); loaders read on node start. `~/.nova/` needs to be created (with group-rw perms) by bringup if absent.
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
