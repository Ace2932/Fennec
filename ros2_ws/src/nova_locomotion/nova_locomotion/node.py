"""gait_node — thin rclpy glue around controller.GaitController.

Roadmap stage 1 item 1 (docs/roadmap-trot-balance.md). ALL logic lives
in controller.py (pure, tested without rclpy); this file only wires
topics, the 100 Hz timer, and nova_ops' safety envelope. No test
imports this module.

Topology (the project-policy publish path, wrapper.py docstring):
  /nova/mode (std_msgs/String: idle|stand_up|sit|crawl|trot)  --\\
  /cmd_vel   (geometry_msgs/Twist, stored for the Raibert lane) -+-> timer
  /joint_states -> envelope load window + current-pose seed     --/   |
                                                                      v
  GaitController -> radians ordered by bus ID (joint_id_map) ->
  SafeJointCommandPublisher (clamp/refuse) -> _CountsAdapter ->
  /joint_commands

PREFLIGHT GATE (#285): bringup.launch.py documents "gait controller MUST
run preflight and check exit code before enabling motion" but nothing
implemented it. This node subscribes to /preflight/status (the
DiagnosticArray preflight already publishes on every ~/run) and feeds a
PreflightGate (controller.py, pure/tested rclpy-free): GaitController
refuses to leave idle until every critical check has reported OK at
least once. Bypass with the `require_preflight:=false` param for bench
debugging without a preflight chain up — logs a loud warning once.

UNITS — WIRE-AT-CALIBRATION: positions here are RADIANS end to end;
firmware main.cpp reads /joint_commands as RAW STS3215 COUNTS. The
conversion happens AFTER the envelope (limits are radians), in both
directions, and is PER JOINT (#154):

    raw = home_raw + urdf_sign * theta * RAW_PER_RAD

from the homing calibration. This was two GLOBAL scalars, which could
not express the per-joint SIGN the limits path was already using — an
inverted joint would have received a correctly-signed limit window and a
wrong-signed command. Both paths now share firmware_limits.rad_to_raw/
raw_to_rad, so they cannot diverge.

CALIBRATION SOURCE (#188): the homing ARTIFACT
(~/.nova/calibration/servo_offsets_latest.yaml), with the home_raw /
urdf_sign params as a bench override. It used to read the params alone
and nothing ever set them — no launch file, no bringup profile — so this
node ran permanently uncalibrated, publishing radians to a firmware
reading raw counts. main.cpp truncates those to uint16, so 0.87 rad
became raw 0: every joint commanded to one end of travel.

Uncalibrated (any joint with urdf_sign 0) = radians pass straight
through, unchanged, which is the pre-hardware state. All-or-nothing on
purpose: the firmware reads the whole array in ONE unit.
"""

from __future__ import annotations

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import String

from nova_locomotion.controller import (
    ControllerParams,
    GaitController,
    PreflightGate,
    positions_to_pose,
)
from nova_locomotion.gait.backlash import BacklashComp
from nova_ops.joint_map import load_joint_id_map
from nova_ops.safety_envelope.calibration_io import (
    DEFAULT_CALIBRATION_PATH,
    apply_haa_confirmations,
    resolve_calibration,
)
from nova_ops.safety_envelope.firmware_limits import (
    calibration_state,
    convert_positions,
)
from nova_ops.safety_envelope.limits import load_default_limits
from nova_ops.safety_envelope.wrapper import SafeJointCommandPublisher

RATE_HZ = 100.0  # firmware command rate


class _CountsAdapter:
    """Publisher shim: radians -> firmware units AFTER the envelope.

    PER-JOINT since issue #154. This used to apply two GLOBAL scalars
    (counts_per_rad, home_offset) to all twelve joints, while the limits path
    already converted per joint via JointHomeCalib.urdf_sign. A joint whose
    servo is mounted inverted therefore received a correctly-signed limit
    window and a WRONG-SIGNED command — it would drive away from target into
    its stop at full authority, with the firmware backstop computed for the
    opposite sense so it could not help.

    The kinematic left/right mirror is a different thing and is already handled
    (solve_side flips haa only; hfe/kfe need no flip because their axis is
    PARALLEL to the mirror normal, so the axis flip and the angle negation
    cancel). THIS is the servo MOUNTING direction: per joint, physical, and
    only knowable once homing has watched a real servo move.

    Identity until every joint is calibrated — see convert_positions() for why
    the all-or-nothing rule is deliberate.

    SAYS WHICH STATE IT IS IN (#159). Identity behaviour means radians reach a
    firmware reading raw counts — harmless before hardware (nothing listening),
    dangerous during bring-up (0.6 rad becomes 0.6 counts). Those two states
    looked identical in the log; now each announces itself once.
    """

    def __init__(self, raw_pub, calib=None, logger=None):
        self.raw_pub = raw_pub
        self.calib = calib or {}
        self.logger = logger
        self._warned = False
        self._announce()

    def _announce(self):
        if self.logger is None:
            return
        state, missing = calibration_state(self.calib)
        if state == "active":
            self.logger.info("joint calibration ACTIVE: commands convert to raw counts")
        elif state == "uncalibrated":
            self.logger.info(
                "no joint calibration: radians pass through unconverted "
                "(expected pre-hardware — do NOT drive servos in this state)"
            )
        else:
            # already said why nothing converts — don't repeat it from publish()
            self._warned = True
            self.logger.warn(
                "PARTIAL joint calibration: bus IDs "
                f"{missing} have no confirmed sign, so NOTHING converts and "
                "radians are being published to a firmware reading raw counts. "
                "Home the remaining joints before commanding motion."
            )

    def publish(self, msg):
        if self.calib:
            converted = convert_positions(list(msg.position), self.calib, to_raw=True)
            if converted is not None:
                msg.position = converted
            elif not self._warned and self.logger is not None:
                # _announce already covered a partial calib; reaching here with
                # a full one means the MESSAGE was malformed (short array), a
                # different fault that would otherwise be silent.
                self._warned = True
                self.logger.warn(
                    f"conversion declined for a {len(msg.position)}-joint message; "
                    "publishing radians unconverted"
                )
        self.raw_pub.publish(msg)


class GaitNode(Node):
    def __init__(self):
        super().__init__("gait_node")
        # Per-joint homing calibration (#154). home_raw + urdf_sign per bus ID,
        # filled by servo homing. Empty = uncalibrated = radians pass straight
        # through, which is the pre-hardware state.
        # Params are an OVERRIDE, not the source (#188). All-zero urdf_sign is
        # the declared default, not a calibration — read that way it left this
        # node permanently uncalibrated. The homing artifact is the real source.
        self.declare_parameter("home_raw", [0.0] * 12)
        self.declare_parameter("urdf_sign", [0] * 12)  # 0 = unknown
        self.declare_parameter("calibration_path", DEFAULT_CALIBRATION_PATH)
        # #285: refuse motion modes until preflight has been observed to
        # pass. True is the safe default; bench debugging without a
        # preflight chain up needs an explicit, loud opt-out.
        self.declare_parameter("require_preflight", True)

        self.id_map = load_joint_id_map()
        require_preflight = bool(self.get_parameter("require_preflight").value)
        if not require_preflight:
            self.get_logger().warn(
                "!!! require_preflight:=false — gait_node will accept motion "
                "modes WITHOUT ever observing a preflight PASS. Bench "
                "debugging only. Do not run this against real servos. !!!"
            )
        self.preflight_gate = PreflightGate(require=require_preflight)
        self.controller = GaitController(
            ControllerParams(), BacklashComp(), gate=self.preflight_gate
        )
        self.cmd_vel = (0.0, 0.0)  # stored for the stage-4 Raibert lane
        self._current_positions = None  # last /joint_states positions

        raw_pub = self.create_publisher(JointState, "/joint_commands", 10)
        self.calib = self._load_calib()
        self._load_haa_confirmations()
        adapter = _CountsAdapter(raw_pub, self.calib, logger=self.get_logger())
        self.safe_pub = SafeJointCommandPublisher(
            node=self, limits=load_default_limits(), raw_publisher=adapter
        )

        # #282: preflight needs to observe the posture gate from outside the
        # wrapper. Latched (TRANSIENT_LOCAL) host-to-host status topic, same
        # pattern as safety_envelope/tables_node.py's firmware_tables_state —
        # published once, since the gate's liveness is fixed at construction.
        self._posture_gate_pub = self.create_publisher(
            String,
            "posture_gate_state",
            QoSProfile(
                depth=1,
                reliability=ReliabilityPolicy.RELIABLE,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
            ),
        )
        self._posture_gate_pub.publish(
            String(data="active" if self.safe_pub.posture_gate_active else "inactive")
        )

        self.create_subscription(JointState, "/joint_states", self._on_states, 10)
        self.create_subscription(String, "/nova/mode", self._on_mode, 10)
        self.create_subscription(Twist, "/cmd_vel", self._on_cmd_vel, 10)
        # Absolute topic name — preflight.launch.py remaps its node-relative
        # ~/status to this (#285). Not namespace-relative: gait_node may run
        # under a different namespace than preflight.
        self.create_subscription(
            DiagnosticArray, "/preflight/status", self._on_preflight_status, 10
        )
        self.create_timer(1.0 / RATE_HZ, self._tick)
        self.get_logger().info("gait_node up: modes idle|stand_up|sit|crawl|trot")

    # ---- subscriptions -------------------------------------------------

    def _load_calib(self):
        """Bus ID -> JointHomeCalib, from the params OR the homing artifact.

        Used to read the params alone (#188). Nothing ever set them — no launch
        file, no bringup profile — so this node ran permanently uncalibrated and
        convert_positions() declined, publishing RADIANS to a firmware reading
        raw counts. main.cpp truncates those to uint16, so 0.87 rad became raw
        0: every joint commanded to one end of travel.

        Homing does write a calibration (~/.nova/calibration/), it simply had no
        reader. Params still win when set, so a bench override stays possible.
        """
        calib, source = resolve_calibration(
            list(self.get_parameter("home_raw").value or []),
            list(self.get_parameter("urdf_sign").value or []),
            self.get_parameter("calibration_path").value,
        )
        state, missing = calibration_state(calib)
        if state == "active":
            self.get_logger().info(
                f"calibration from {source}: counts conversion is LIVE"
            )
        elif state == "partial":
            self.get_logger().warn(
                f"calibration from {source} is PARTIAL — bus IDs {missing} "
                f"unhomed. NOTHING converts (all-or-nothing), so radians go to "
                f"a firmware reading raw counts. Do not drive."
            )
        else:
            self.get_logger().warn(
                "no calibration (params unset and no homing artifact). Radians "
                "pass through unconverted — expected before homing, NOT safe "
                "to drive on."
            )
        return calib

    def _load_haa_confirmations(self) -> None:
        """Load persisted haa sign confirmations into limits.HAA_INBOARD_SIGN
        (#194) — the other half of record_haa_confirmation() having a real
        caller now. Without this, a confirmation recorded by a prior
        `confirm_haa_sign` run/process never reaches THIS process: the sign
        lives in nova_ops.safety_envelope.limits' module-global state, which
        starts back at all-None on every fresh interpreter. Same reasoning as
        _load_calib() above, for the OTHER sign (HAA_INBOARD_SIGN, not
        urdf_sign) — must run before load_default_limits() so the wrapper's
        ROM table reflects it.
        """
        path = self.get_parameter("calibration_path").value
        try:
            applied = apply_haa_confirmations(path)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(
                f"haa confirmations at {path} are unreadable: {exc}. haa "
                f"stays on the conservative symmetric clamp until fixed."
            )
            return
        if applied:
            self.get_logger().info(
                f"loaded {applied} confirmed haa sign(s) from {path}"
            )

    def _on_states(self, msg: JointState) -> None:
        self.safe_pub.on_joint_states(msg)  # envelope load window
        if len(msg.position) >= 12:
            # RAW COUNTS -> RADIANS before seeding (#154). positions_to_pose()
            # expects radians; feeding it raw counts made stand_up(start_pose=)
            # begin from a garbage pose — and that is the E-stop RECOVERY path.
            pos = list(msg.position[:12])
            if self.calib:
                converted = convert_positions(pos, self.calib, to_raw=False)
                if converted is not None:
                    pos = converted
            self._current_positions = pos

    def _on_preflight_status(self, msg: DiagnosticArray) -> None:
        # Mirrors PreflightNode._on_run's own verdict (critical FAIL blocks):
        # pass iff there's at least one critical entry and none of them are
        # non-OK. KeyValue 'critical' is stringified True/False (node.py).
        critical = [
            s
            for s in msg.status
            if any(kv.key == "critical" and kv.value == "True" for kv in s.values)
        ]
        ok = bool(critical) and all(s.level == DiagnosticStatus.OK for s in critical)
        self.preflight_gate.observe(ok)

    def _on_mode(self, msg: String) -> None:
        mode = msg.data.strip()
        now = self.get_clock().now().nanoseconds / 1e9
        current = (
            positions_to_pose(self._current_positions, self.id_map)
            if self._current_positions is not None
            else None
        )
        try:
            self.controller.set_mode(mode, now, current_pose=current)
        except ValueError as e:
            self.get_logger().warn(str(e))
            return
        self.get_logger().info(f"mode -> {mode}")

    def _on_cmd_vel(self, msg: Twist) -> None:
        self.cmd_vel = (msg.linear.x, msg.linear.y)

    # ---- 100 Hz command path -------------------------------------------

    def _tick(self) -> None:
        now = self.get_clock().now().nanoseconds / 1e9
        positions = self.controller.command_positions(now, self.id_map)
        if positions is None:
            return  # idle before any pose — publish nothing, servos hold
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        # name[] intentionally empty: firmware convention, position[i] = bus i+1
        msg.position = positions
        self.safe_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = GaitNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
