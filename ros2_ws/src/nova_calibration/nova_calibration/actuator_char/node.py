"""ROS 2 node: STS3215 actuator step-response characterization.

Drives a square-wave (step up / step down) on ONE joint through the live
firmware path and logs the response at full /joint_states rate to a CSV. The
CSV feeds actuator_char/fit.py offline to extract latency, max velocity, and
the first-order time constant for the sim actuator model (see
docs/sim-training.md).

Why through ROS and not raw serial: the policy will command through this exact
path (Teensy 40 Hz broadcast + slew limit + ~17 Hz round-robin telemetry). We
want the *system* response, not the bare servo, or sim-to-real won't hold.

Service: `~/characterize` (std_srvs/Trigger). Parameters set which joint and
the step shape:

    joint_id        (int)   servo id 1..12                       default 1
    amplitude_raw   (int)   step size in raw counts (~11.4/deg)  default 200
    dwell_s         (double) seconds held at each level          default 1.5
    cycles          (int)   up/down pairs                        default 3

SAFETY: same as servo_homing — only runs when /safety_state == NORMAL. Keep
the leg off the ground; a 200-raw step is ~17.6 deg. Holds the other 11 joints
at their current position throughout.
"""
import csv
import os
import threading
import time
from datetime import datetime

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from sensor_msgs.msg import JointState
from std_msgs.msg import Int32, String
from std_srvs.srv import Trigger

NUM_JOINTS = 12
SAFETY_NORMAL = 0
LOG_DIR = os.path.expanduser('~/.nova/calibration/actuator')


class ActuatorCharNode(Node):

    def __init__(self):
        super().__init__('nova_actuator_char')
        cb = ReentrantCallbackGroup()

        self.declare_parameter('joint_id', 1)
        self.declare_parameter('amplitude_raw', 200)
        self.declare_parameter('dwell_s', 1.5)
        self.declare_parameter('cycles', 3)
        # Sample period for the logger loop; /joint_states updates slower
        # (~17 Hz/joint) but we timestamp each captured value so the fit uses
        # real dt regardless.
        self.declare_parameter('log_hz', 50.0)

        self._pos = [None] * NUM_JOINTS
        self._vel = [0] * NUM_JOINTS
        self._load = [0] * NUM_JOINTS
        self._safety = None
        self._lock = threading.Lock()
        self._hold = [0] * NUM_JOINTS
        self._busy = False

        self.create_subscription(JointState, '/joint_states',
                                 self._on_js, 10, callback_group=cb)
        self.create_subscription(Int32, '/safety_state',
                                 self._on_safety, 10, callback_group=cb)
        self._cmd_pub = self.create_publisher(JointState, '/joint_commands', 10)
        self._status_pub = self.create_publisher(String,
                                                 'nova_calibration_status', 10)
        self.create_service(Trigger, '~/characterize',
                            self._on_trigger, callback_group=cb)

        self.get_logger().info(
            'actuator_char up. service: ~/characterize (std_srvs/Trigger). '
            'set joint_id / amplitude_raw / dwell_s / cycles params first.')

    def _on_js(self, msg: JointState):
        with self._lock:
            for i in range(min(NUM_JOINTS, len(msg.position))):
                self._pos[i] = int(round(msg.position[i]))
            for i in range(min(NUM_JOINTS, len(msg.velocity))):
                self._vel[i] = int(round(msg.velocity[i]))
            for i in range(min(NUM_JOINTS, len(msg.effort))):
                self._load[i] = abs(int(round(msg.effort[i])))

    def _on_safety(self, msg: Int32):
        with self._lock:
            self._safety = int(msg.data)

    def _on_trigger(self, request, response):
        if self._busy:
            response.success = False
            response.message = 'already running'
            return response
        with self._lock:
            if self._safety != SAFETY_NORMAL:
                response.success = False
                response.message = (f'safety_state={self._safety} '
                                    f'(need {SAFETY_NORMAL}=NORMAL)')
                return response
            if any(p is None for p in self._pos):
                response.success = False
                response.message = 'no /joint_states yet'
                return response

        self._busy = True
        threading.Thread(target=self._run, daemon=True).start()
        response.success = True
        response.message = 'characterization started'
        return response

    def _run(self):
        try:
            jid = self.get_parameter('joint_id').value
            amp = self.get_parameter('amplitude_raw').value
            dwell = self.get_parameter('dwell_s').value
            cycles = self.get_parameter('cycles').value
            log_dt = 1.0 / self.get_parameter('log_hz').value
            idx = jid - 1

            with self._lock:
                self._hold = [p if p is not None else 0 for p in self._pos]
                base = self._hold[idx]

            samples = []
            t0 = time.monotonic()

            def log_for(duration):
                end = time.monotonic() + duration
                while time.monotonic() < end:
                    with self._lock:
                        row = (time.monotonic() - t0, self._hold[idx],
                               self._pos[idx], self._vel[idx], self._load[idx])
                    samples.append(row)
                    time.sleep(log_dt)

            self._set_goal(idx, base)
            log_for(dwell)
            for c in range(cycles):
                if not self._safe():
                    self._status('ABORTED — safety tripped')
                    return
                self._set_goal(idx, base + amp)   # step up
                log_for(dwell)
                self._set_goal(idx, base)         # step down
                log_for(dwell)
                self._status(f'cycle {c + 1}/{cycles} done')

            path = self._write_csv(jid, amp, samples)
            self._status(f'done — {len(samples)} samples -> {path}. '
                         f'Fit with actuator_char.fit.fit_step()')
        except Exception as exc:
            self.get_logger().error(f'characterize crashed: {exc!r}')
            self._status(f'ERROR: {exc!r}')
        finally:
            self._busy = False

    def _set_goal(self, idx, raw):
        with self._lock:
            self._hold[idx] = int(raw)
            goals = list(self._hold)
        msg = JointState()
        msg.position = [float(g) for g in goals]
        self._cmd_pub.publish(msg)

    def _safe(self):
        with self._lock:
            return self._safety == SAFETY_NORMAL

    def _write_csv(self, jid, amp, samples):
        os.makedirs(LOG_DIR, mode=0o770, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        path = os.path.join(LOG_DIR, f'step_j{jid}_a{amp}_{stamp}.csv')
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['t', 'goal_raw', 'pos_raw', 'vel_raw', 'load_raw'])
            w.writerows(samples)
        return path

    def _status(self, text):
        self.get_logger().info(text)
        self._status_pub.publish(String(data=text))


def main(args=None):
    rclpy.init(args=args)
    node = ActuatorCharNode()
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
