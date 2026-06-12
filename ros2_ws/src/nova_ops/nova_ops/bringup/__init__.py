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
    'bench': {
        'description': 'Teensy uROS bridge + preflight only — desk firmware iteration',
        'preflight': True,
        'actions': [
            # micro_ros_agent runs detached via setup-jetson.md §14.7 setsid.
            # The launch file does NOT spawn it — it's started by ops, not by us.
            # We just include preflight here so you can validate the chain.
            ('launch', 'nova_ops', 'preflight.launch.py', {}),
        ],
    },

    'sensors': {
        'description': 'RealSense + L2 + dashcam — sensor smoke tests + data collection',
        'preflight': False,   # sensors don't need servo bus
        'actions': [
            ('launch', 'realsense2_camera', 'rs_launch.py', {
                'enable_color': 'true',
                'enable_depth': 'true',
                'enable_gyro': 'true',
                'enable_accel': 'true',
            }),
            ('launch', 'unitree_lidar_ros2', 'launch.py', {}),
            ('launch', 'nova_ops', 'dashcam.launch.py', {}),
        ],
    },

    'slam': {
        'description': 'sensors + POINT-LIO + robot_state_publisher',
        'preflight': False,
        'actions': [
            # Compose by reference: load `sensors` profile first.
            ('include_profile', 'sensors'),
            ('launch', 'point_lio', 'mapping_unilidar_l2.launch.py', {}),
            # robot_state_publisher needs the URDF — wired up once URDF lands.
            # ('node', 'robot_state_publisher', 'robot_state_publisher',
            #  {'robot_description': '<file content of nova.urdf.xacro>'}),
        ],
    },

    'walk': {
        'description': 'Teensy bridge + gait + safety envelope + dashcam + IMU',
        'preflight': True,
        'actions': [
            ('launch', 'nova_ops', 'preflight.launch.py', {}),
            ('launch', 'nova_ops', 'dashcam.launch.py', {}),
            # §10 battery_low -> clean poweroff. Safety-critical: the ONLY
            # nova_ops node not allowed to crash silently.
            ('node', 'nova_ops', 'battery_shutdown_node', {}),
            # Gait controller doesn't exist yet (Phase 2 deliverable).
            # ('node', 'nova_gait', 'gait_controller', {}),
            # Safety envelope is a library wrapped INSIDE gait_controller's
            # publisher path — no separate node. The counters topic is
            # published by gait_controller via the wrapper.
        ],
    },

    'full': {
        'description': 'walk + slam + Nav2 + Foxglove bridge',
        'preflight': True,
        'actions': [
            ('include_profile', 'walk'),
            ('include_profile', 'slam'),
            # Nav2 + Foxglove are external packages (apt-installable).
            # Stubbed; Phase 3 deliverable.
            # ('launch', 'nav2_bringup', 'navigation_launch.py', {}),
            # ('launch', 'foxglove_bridge', 'foxglove_bridge_launch.xml', {}),
        ],
    },

    'vla': {
        'description': 'full + VLA inference node (Phase 4)',
        'preflight': True,
        'actions': [
            ('include_profile', 'full'),
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
        raise ValueError(
            f'profile cycle detected: {profile_name} already in {_seen}')
    if profile_name not in PROFILES:
        raise ValueError(
            f'unknown profile {profile_name!r}; '
            f'available: {sorted(PROFILES.keys())}')

    _seen = _seen | {profile_name}
    out = []
    seen_actions = set()
    for action in PROFILES[profile_name]['actions']:
        if action[0] == 'include_profile':
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
    if kind in ('launch', 'node'):
        # (kind, package, file_or_executable) — args/params not in key
        # so two identical includes with the same args are deduped, but
        # two launches of the same file with DIFFERENT args remain
        # distinct (caller passes them as a list of tuples).
        return (kind, action[1], action[2], tuple(sorted(action[3].items())))
    return (kind,) + action[1:]
