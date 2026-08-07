"""RETIRED (#289) -- moved to nova_locomotion.policy_node.

This scaffold used to publish `Int32MultiArray` on `/joint_goal_ticks`, a
topic with ZERO subscribers anywhere else in the stack, from a directory with
no `package.xml`/`setup.py` -- not even a buildable ROS package. The real
bridge now lives at
`ros2_ws/src/nova_locomotion/nova_locomotion/policy_node.py`: a real colcon
package, publishing `/joint_commands` through the SAME
`SafeJointCommandPublisher` + `_CountsAdapter` path `gait_node` uses (envelope
clamp, posture gate, per-joint homing-calibration conversion), gated on
preflight + full calibration + a live `/imu` + explicit arming
(`/nova/policy_enable`).

    ros2 launch nova_locomotion policy.launch.py policy_npz:=/path/to/nova_policy.npz

This file raises on import so nothing can accidentally resurrect the dead
`/joint_goal_ticks` path by importing it. `deploy/policy_runner.py` moved to
`nova_locomotion/policy_runner.py` (same reason); `deploy/joint_map.py` is
untouched -- the real node converts rad<->raw through
`nova_ops.safety_envelope.firmware_limits` (the homing-calibration path)
instead of this module's placeholder home_tick/direction scheme.
"""

raise ImportError(
    "sim/nova_mjx/deploy/policy_node.py is retired (#289). The sim->real "
    "policy bridge is nova_locomotion.policy_node -- "
    "`ros2 launch nova_locomotion policy.launch.py`."
)
