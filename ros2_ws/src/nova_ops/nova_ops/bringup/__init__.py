"""Profile definitions for `ros2 launch nova_ops bringup.launch.py`.

Per docs/notes-qol-features.md §4. v1 uses a Python dict (simple,
gets the launcher shipped). v2 will move profile defs to YAML files
under nova_ops/profiles/ so adding a profile = `git add foo.yaml`.

Each profile is a sequence of "actions":
  ('launch', package, launch_file, dict_of_args)
  ('node',   package, executable,  dict_of_params)
  ('apt',    pkg_name_for_external_node)  -- documented prereq, not enforced
"""

# Available profiles per the spec table in notes-qol-features.md §4.
# Most external packages (gait_controller, nova_perception, etc.) don't
# exist yet — stubs that print a TODO log and exit cleanly are noted
# below. Each profile is documented even if not fully composable today.
PROFILES = {
    "bench": {
        "description": "Teensy uROS bridge + preflight only — desk firmware iteration",
        "preflight": True,
        "actions": [
            # micro_ros_agent runs detached via setup-jetson.md §14.7 setsid.
            # The launch file does NOT spawn it — it's started by ops, not by us.
            # We just include preflight here so you can validate the chain.
            ("node", "nova_ops", "firmware_tables", {"_respawn": True}),
            ("launch", "nova_ops", "preflight.launch.py", {}),
        ],
    },
    "sensors": {
        "description": "RealSense + L2 + dashcam — sensor smoke tests + data collection",
        "preflight": False,  # sensors don't need servo bus
        "actions": [
            (
                "launch",
                "realsense2_camera",
                "rs_launch.py",
                {
                    "enable_color": "true",
                    "enable_depth": "true",
                    "enable_gyro": "true",
                    "enable_accel": "true",
                },
            ),
            ("launch", "unitree_lidar_ros2", "launch.py", {}),
            ("launch", "nova_ops", "dashcam.launch.py", {}),
            # Foxglove bridge — WebSocket for live viz from a laptop/browser
            # (connect ws://<jetson>:8765). apt: ros-humble-foxglove-bridge.
            # SKIPs cleanly if not installed (composer checks the package).
            (
                "node",
                "foxglove_bridge",
                "foxglove_bridge",
                {"port": 8765, "address": "0.0.0.0"},
            ),
        ],
    },
    "slam": {
        "description": "sensors + POINT-LIO + robot_state_publisher",
        "preflight": False,
        "actions": [
            # Compose by reference: load `sensors` profile first.
            ("include_profile", "sensors"),
            ("launch", "point_lio", "mapping_unilidar_l2.launch.py", {}),
            # robot_state_publisher (URDF landed 2026-07-13) — publishes
            # /robot_description + the sensor<->base TF tree POINT-LIO needs.
            ("launch", "nova_description", "robot_state.launch.py", {}),
        ],
    },
    "walk": {
        "description": "Teensy bridge + gait + safety envelope + dashcam + IMU",
        "preflight": True,
        "actions": [
            # FIRST, and before preflight: the Teensy boots with BOTH
            # protection tables wide open (per-joint 0..4095, posture backstop
            # off) and only the host can narrow them (#185). Listed ahead of
            # preflight deliberately — ros2 launch does not guarantee start
            # ORDER, so this is intent, not a guarantee, and #187's arming
            # check has to tolerate the race with a wait window.
            ("node", "nova_ops", "firmware_tables", {"_respawn": True}),
            ("launch", "nova_ops", "preflight.launch.py", {}),
            ("launch", "nova_ops", "dashcam.launch.py", {}),
            # robot_state_publisher — /robot_description + /tf for the 3D robot
            # in Foxglove (and any TF consumer) during gait bring-up.
            ("launch", "nova_description", "robot_state.launch.py", {}),
            # §10 battery_low -> clean poweroff. Safety-critical: the ONLY
            # nova_ops node not allowed to crash silently.
            ("node", "nova_ops", "battery_shutdown_node", {"_respawn": True}),
            # Teensy /heartbeat watchdog -> /system_ok (audit gap closure)
            ("node", "nova_ops", "liveness_node", {"_respawn": True}),
            # systemd WATCHDOG=1 feeder — hang recovery when run under
            # deploy/nova-bringup.service (WatchdogSec=15, NotifyAccess=all);
            # idles harmlessly outside systemd. See nova_ops/watchdog/.
            ("node", "nova_ops", "watchdog_node", {"_respawn": True}),
            # Foxglove bridge — live gait/IMU/telemetry viz during bring-up
            # (ws://<jetson>:8765). Most useful profile for it: watch the
            # policy obs/actions + joint tracking while the robot walks.
            (
                "node",
                "foxglove_bridge",
                "foxglove_bridge",
                {"port": 8765, "address": "0.0.0.0"},
            ),
            # Gait controller (#285 — this used to say package 'nova_gait',
            # executable 'gait_controller', neither of which ever existed;
            # verified against nova_locomotion/setup.py entry_points:
            # "gait_node = nova_locomotion.node:main"). Refuses to leave
            # idle until it observes a preflight PASS on /preflight/status
            # (see nova_locomotion/node.py PreflightGate; bypass with the
            # require_preflight:=false node param for bench debugging).
            ("node", "nova_locomotion", "gait_node", {}),
            # Safety envelope is a library wrapped INSIDE gait_node's
            # publisher path — no separate node. The counters topic is
            # published by gait_node via the wrapper.
        ],
    },
    "full": {
        "description": "walk + slam + Nav2 + Foxglove bridge",
        "preflight": True,
        "actions": [
            ("include_profile", "walk"),  # brings foxglove_bridge via walk/sensors
            ("include_profile", "slam"),
            # Nav2 stubbed; Phase 3 deliverable. Foxglove is already included
            # (walk + sensors both run it; dedup keeps a single instance).
            # ('launch', 'nav2_bringup', 'navigation_launch.py', {}),
        ],
    },
    "vla": {
        "description": "full + VLA inference node (Phase 4)",
        "preflight": True,
        "actions": [
            ("include_profile", "full"),
            # Phase 4. OpenVLA INT4 or NanoVLA on Jetson Orin Nano 8GB.
            # ('node', 'nova_vla', 'vla_policy', {}),
        ],
    },
}


def resolve_actions(profile_name: str, _seen=None) -> list:
    """Recursively expand `include_profile` references into a flat list.

    De-duplicates identical actions (so `full` = `walk` + `slam` doesn't
    spawn dashcam twice because both contained it). Guards against
    profile cycles via the _seen set.
    """
    if _seen is None:
        _seen = set()
    if profile_name in _seen:
        raise ValueError(f"profile cycle detected: {profile_name} already in {_seen}")
    if profile_name not in PROFILES:
        raise ValueError(
            f"unknown profile {profile_name!r}; available: {sorted(PROFILES.keys())}"
        )

    _seen = _seen | {profile_name}
    out = []
    seen_actions = set()
    for action in PROFILES[profile_name]["actions"]:
        if action[0] == "include_profile":
            for sub_action in resolve_actions(action[1], _seen=_seen):
                key = _action_key(sub_action)
                if key not in seen_actions:
                    seen_actions.add(key)
                    out.append(sub_action)
        else:
            key = _action_key(action)
            if key not in seen_actions:
                seen_actions.add(key)
                out.append(action)
    return out


def _action_key(action) -> tuple:
    """Hashable identity for an action — used for dedup across includes."""
    kind = action[0]
    if kind in ("launch", "node"):
        # (kind, package, file_or_executable) — args/params not in key
        # so two identical includes with the same args are deduped, but
        # two launches of the same file with DIFFERENT args remain
        # distinct (caller passes them as a list of tuples).
        return (kind, action[1], action[2], tuple(sorted(action[3].items())))
    return (kind,) + action[1:]
