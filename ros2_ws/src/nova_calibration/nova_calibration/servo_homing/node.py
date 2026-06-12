"""ROS 2 node: servo home auto-detect via hard-stop probing.

Exposes a std_srvs/Trigger service `~/calibrate_homes`. On call it walks the
configured joint set one at a time, drives each to its mechanical stop, derives
the home offset, and persists the result to ~/.nova/calibration/.

Wire contract with the Teensy firmware (see firmware/teensy/.../main.cpp):

  subscribe  /joint_states   sensor_msgs/JointState
               position[i] = raw 0..4095   (servo id = i+1)
               effort[i]   = raw load, sign-magnitude 0..1000 (% stall)
  subscribe  /safety_state   std_msgs/Int32   (0 = SAFETY_NORMAL = motion ok)
  publish    /joint_commands sensor_msgs/JointState
               position[i] = raw 0..4095 goal   (all 12 every message)

The firmware only drives servos while safety == NORMAL and applies its own
slew limit, so a far goal ramps in rather than slamming. We additionally cap
the host step rate (the real throttle) and abort on a load ceiling.

The blocking probe runs in a worker thread; the node keeps spinning so
/joint_states stays fresh and the service caller doesn't time out. Run with a
MultiThreadedExecutor (see main()).
"""
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from sensor_msgs.msg import JointState
from std_msgs.msg import Int32, String
from std_srvs.srv import Trigger

from .config import JOINT_CONFIGS
from .hard_stop import HardStopCalibrator, HardStopParams, Outcome
from . import storage

NUM_JOINTS = 12
SAFETY_NORMAL = 0


class ServoHomingNode(Node):

    def __init__(self):
        super().__init__('nova_servo_homing')
        cb = ReentrantCallbackGroup()

        # Latest telemetry caches (raw). None until first /joint_states.
        self._pos = [None] * NUM_JOINTS
        self._load = [0] * NUM_JOINTS
        self._safety = None
        self._lock = threading.Lock()

        # Held goal array — what we publish every tick. Seeded on calibrate.
        self._hold = [0] * NUM_JOINTS
        self._busy = False
        self._abort = False

        self.create_subscription(
            JointState, '/joint_states', self._on_joint_states, 10,
            callback_group=cb)
        self.create_subscription(
            Int32, '/safety_state', self._on_safety, 10, callback_group=cb)

        self._cmd_pub = self.create_publisher(JointState, '/joint_commands', 10)
        self._status_pub = self.create_publisher(
            String, 'nova_calibration_status', 10)

        self._srv = self.create_service(
            Trigger, '~/calibrate_homes', self._on_calibrate, callback_group=cb)

        self.params = HardStopParams()
        self._status('idle — call ~/calibrate_homes to start')
        self.get_logger().info(
            'servo_homing up. service: ~/calibrate_homes (std_srvs/Trigger)')

    # ---------------- subscriptions ----------------
    def _on_joint_states(self, msg: JointState):
        with self._lock:
            for i in range(min(NUM_JOINTS, len(msg.position))):
                self._pos[i] = int(round(msg.position[i]))
            for i in range(min(NUM_JOINTS, len(msg.effort))):
                self._load[i] = abs(int(round(msg.effort[i])))

    def _on_safety(self, msg: Int32):
        with self._lock:
            self._safety = int(msg.data)

    # ---------------- service ----------------
    def _on_calibrate(self, request, response):
        if self._busy:
            response.success = False
            response.message = 'calibration already running'
            return response

        ok, why = self._preconditions()
        if not ok:
            response.success = False
            response.message = why
            return response

        # Run the (blocking) sweep in a worker so the service returns promptly
        # and the executor keeps publishing commands / reading telemetry.
        self._busy = True
        self._abort = False
        threading.Thread(target=self._run_sweep, daemon=True).start()
        response.success = True
        response.message = 'calibration started — watch nova_calibration_status'
        return response

    def _preconditions(self):
        with self._lock:
            if self._safety is None:
                return False, 'no /safety_state yet — is the Teensy up?'
            if self._safety != SAFETY_NORMAL:
                return False, (f'safety_state={self._safety} (need {SAFETY_NORMAL}='
                               'NORMAL). Clear E-stop / battery-low first.')
            if any(p is None for p in self._pos):
                return False, 'no /joint_states yet for all joints'
        return True, ''

    # ---------------- sweep worker ----------------
    def _run_sweep(self):
        try:
            with self._lock:
                self._hold = [p if p is not None else 0 for p in self._pos]

            calibrator = HardStopCalibrator(
                read_position=self._read_position,
                read_load=self._read_load,
                send_goal=self._send_goal,
                is_aborted=self._is_aborted,
                sleep_tick=self._sleep_tick,
                params=self.params,
            )

            results = []
            for jid in sorted(JOINT_CONFIGS):
                cfg = JOINT_CONFIGS[jid]
                self._status(f'joint {jid} ({cfg.name}): probing...')
                res = calibrator.run_joint(cfg)
                res.name = cfg.name
                results.append(res)
                self.get_logger().info(
                    f'joint {jid} {cfg.name}: {res.outcome.value} '
                    f'home_raw={res.home_raw} stop={res.stop_pos_raw} '
                    f'peak_load={res.peak_load} ({res.detail})')
                if res.outcome == Outcome.ABORTED:
                    self._status('ABORTED — safety tripped mid-sweep')
                    return

            good = [r for r in results if r.outcome == Outcome.OK]
            if good:
                path = storage.save_offsets(good)
                self._status(
                    f'done — {len(good)}/{len(results)} joints homed, saved {path}')
            else:
                self._status('done — 0 joints homed (all skipped/failed). '
                             'Fill config.py from CAD and set placeholder=False.')
        except Exception as exc:  # never leave _busy stuck on a crash
            self.get_logger().error(f'sweep crashed: {exc!r}')
            self._status(f'ERROR: {exc!r}')
        finally:
            self._busy = False

    # ---------------- HardStopCalibrator callbacks ----------------
    def _read_position(self, jid):
        with self._lock:
            return self._pos[jid - 1]

    def _read_load(self, jid):
        with self._lock:
            return self._load[jid - 1]

    def _send_goal(self, jid, raw):
        with self._lock:
            self._hold[jid - 1] = int(raw)
            goals = list(self._hold)
        msg = JointState()
        msg.position = [float(g) for g in goals]
        self._cmd_pub.publish(msg)

    def _is_aborted(self):
        if self._abort:
            return True
        with self._lock:
            return self._safety not in (None, SAFETY_NORMAL)

    def _sleep_tick(self):
        time.sleep(1.0 / self.params.tick_hz)

    # ---------------- helpers ----------------
    def _status(self, text):
        self.get_logger().info(text)
        self._status_pub.publish(String(data=text))


def main(args=None):
    rclpy.init(args=args)
    node = ServoHomingNode()
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
