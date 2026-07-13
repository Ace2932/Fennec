"""NOVA RL walking policy — ROS 2 deploy node (SCAFFOLD).

Runs the sim-trained policy on the robot: read joint state + IMU + cmd_vel at
50 Hz, build the obs EXACTLY as sim (policy_runner), infer, write 12 joint
POSITION targets. When this is real it moves into nova_locomotion beside the
scripted trot (the safety fallback).

⚠ BENCH-BLOCKED — needs real servos + the ICM-42688-P IMU integrated. The
control flow is complete; the HARDWARE BINDINGS below are TODOs (marked ⛏), and
each is a real transfer-critical detail, not boilerplate:

  ⛏ JOINT ORDER — the policy's 12 outputs are URDF order (FL,FR,RL,RR × haa,hfe,
    kfe). Map to/from Feetech servo IDs via config/joint_id_map.yaml. A wrong
    permutation = instant flail.
  ⛏ rad <-> ticks — servo present-position/goal are 0..4095 ticks; the policy is
    radians. Convert with the per-joint home offset + direction sign + scale
    from nova_calibration (the SAME zeros the sim's default_pose assumes).
  ⛏ IMU frame — gyro must be body-frame rad/s in the URDF trunk frame; proj_grav
    = gravity down expressed in that frame (from the IMU orientation, or
    normalize accel at low motion). Align the ICM axes to the URDF trunk axes.
  ⛏ FOOT CONTACT — no foot sensors: estimate (servo load/velocity threshold) or
    retrain the policy without the 4 contact obs. Zeros here = a domain shift.
  ⛏ SAFETY — gate on /safety_state (motion_enabled), clamp targets to the joint
    limits, RAMP from the measured current pose to default on start (never snap),
    and bring up on a harness first.
"""
import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu, JointState
from std_msgs.msg import Float32MultiArray, Int32

from policy_runner import NovaPolicy

# ⛏ URDF joint order the policy expects (must match sim env + joint_id_map.yaml)
JOINT_ORDER = [f"{leg}_{j}" for leg in ("FL", "FR", "RL", "RR")
               for j in ("haa", "hfe", "kfe")]


class PolicyNode(Node):
    def __init__(self):
        super().__init__("nova_policy")
        self.declare_parameter("policy_npz", "nova_policy.npz")
        self.declare_parameter("control_hz", 50.0)
        self.pol = NovaPolicy(self.get_parameter("policy_npz").value)

        self._jpos = np.asarray(self.pol.default_pose, np.float32)
        self._jvel = np.zeros(self.pol.nu, np.float32)
        self._gyro = np.zeros(3, np.float32)
        self._grav = np.array([0, 0, -1], np.float32)
        self._contact = np.zeros(4, np.float32)
        self._cmd = np.zeros(3, np.float32)
        self._motion_ok = False

        self.create_subscription(JointState, "/joint_states", self._on_joints, 10)
        self.create_subscription(Imu, "/imu", self._on_imu, 10)
        self.create_subscription(Twist, "/cmd_vel", self._on_cmd, 10)
        self.create_subscription(Int32, "/safety_state", self._on_safety, 10)
        self.pub = self.create_publisher(Float32MultiArray, "/joint_commands", 10)

        hz = self.get_parameter("control_hz").value
        self.create_timer(1.0 / hz, self._tick)
        self.get_logger().warn(
            "nova_policy SCAFFOLD — verify JOINT_ORDER, rad<->ticks, IMU frame, "
            "foot-contact, and safety before enabling torque (see module docstring).")

    def _on_joints(self, msg):
        idx = {n: i for i, n in enumerate(msg.name)}
        if all(j in idx for j in JOINT_ORDER):     # ⛏ else map via joint_id_map
            self._jpos = np.array([msg.position[idx[j]] for j in JOINT_ORDER], np.float32)
            if msg.velocity:
                self._jvel = np.array([msg.velocity[idx[j]] for j in JOINT_ORDER], np.float32)
        # ⛏ if names are servo IDs / ticks, permute + convert here

    def _on_imu(self, msg):
        g = msg.angular_velocity
        self._gyro = np.array([g.x, g.y, g.z], np.float32)      # ⛏ axis-align to trunk
        q = msg.orientation                                     # ⛏ proj_grav from orientation
        # gravity (world -z) rotated into body frame via the IMU quaternion:
        w, x, y, z = q.w, q.x, q.y, q.z
        self._grav = np.array([                                 # R^T @ [0,0,-1]
            -2 * (x * z - w * y),
            -2 * (y * z + w * x),
            -(1 - 2 * (x * x + y * y))], np.float32)

    def _on_cmd(self, msg):
        self._cmd = np.array([msg.linear.x, msg.linear.y, msg.angular.z], np.float32)

    def _on_safety(self, msg):
        self._motion_ok = (msg.data == 0)          # 0 = SAFETY_NORMAL (see safety_state.h)

    def _tick(self):
        target = self.pol.joint_targets(
            self._gyro, self._grav, self._cmd, self._jpos, self._jvel, self._contact)
        # ⛏ clamp to joint limits; ⛏ ramp from current pose on enable; ⛏ rad->ticks
        if not self._motion_ok:
            self.pol.reset()                       # hold last_action clean while disabled
            return
        self.pub.publish(Float32MultiArray(data=target.tolist()))


def main(args=None):
    rclpy.init(args=args)
    node = PolicyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
