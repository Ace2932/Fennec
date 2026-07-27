"""Hard-stop home-finding algorithm — pure logic, no ROS.

Kept ROS-free so it can be unit-tested with fake servo callbacks (see
test/test_hard_stop.py). The node layer (node.py) supplies real callbacks
that talk to the Teensy over /joint_commands and /joint_states.

Method (per joint):

  1. Read the joint's current raw position.
  2. Step the goal slowly in `search_dir` (STEP_RAW per control tick). The
     host step rate is the real speed limiter — keep it gentle; the firmware
     slew limiter (NOVA_SLEW_MAX_DELTA) is a backstop, not the throttle.
  3. Each tick read load (|effort|, 0..1000 = % stall). When load stays above
     LOAD_THRESHOLD for STALL_TICKS consecutive ticks *and* position has
     stopped advancing, the mechanical stop is reached.
  4. Record stop position, then back off BACKOFF_RAW the other way.
  5. home_raw = stop_pos - search_dir * stop_to_home_raw  (clamped 0..4095).

SAFETY: the firmware caps every servo's torque-limit register at 600
permille on arm (main.cpp NOVA_TORQUE_LIMIT_RAW — this note previously
said "no passthrough"; stale as of 2026-07-06), so a missed stop
saturates at 60% of stall. Still keep LOAD_THRESHOLD conservative: 60%
through the gears is plenty to chew a stripped horn. A per-joint
TIMEOUT_TICKS guard aborts if no stop is found (e.g. wrong search_dir,
joint free-spinning) before the servo cooks itself. NOTE: the firmware
per-joint position-limit table (`joint_limits` topic) must stay WIDE
OPEN during homing — the stops live outside walk ROM by design; publish
the table AFTER homing (nova_ops safety_envelope/firmware_limits.py).
"""

from dataclasses import dataclass
from enum import Enum

RAW_FULL_SCALE = 4095


class Outcome(str, Enum):
    OK = "ok"
    TIMEOUT = "timeout"  # never hit a stop — check search_dir / mechanics
    ABORTED = "aborted"  # external abort (safety tripped, e-stop)
    OVERLOAD = "overload"  # load blew past the hard ceiling immediately
    SKIPPED = "skipped"  # placeholder config — not calibrated


@dataclass
class HardStopParams:
    step_raw: int = 4  # goal advance per tick (~4 raw = 0.35 deg)
    tick_hz: float = 20.0  # control-loop rate; 4 raw @ 20 Hz = ~7 deg/s
    load_threshold: int = 200  # |effort| (of 1000) that counts as "pushing"
    load_ceiling: int = 600  # abort immediately if exceeded (gear safety)
    stall_ticks: int = 4  # consecutive over-threshold ticks => stopped
    pos_epsilon: int = 2  # raw counts; below this = "not moving"
    backoff_raw: int = 60  # retreat from the stop after detection (~5 deg)
    leash_raw: int = 24  # max goal lead over last measured position —
    # bounds position error (∝ torque) when the
    # stop is compliant (printed PA6 flexes) or
    # /joint_states is stale (16.7 Hz per joint)
    timeout_s: float = 12.0  # per-joint abort if no stop found

    @property
    def timeout_ticks(self) -> int:
        return max(1, int(self.timeout_s * self.tick_hz))


@dataclass
class HardStopResult:
    joint_id: int
    outcome: Outcome
    stop_pos_raw: int = 0
    home_raw: int = 0
    peak_load: int = 0
    ticks: int = 0
    detail: str = ""
    urdf_sign: int = 0    # 0 = not observed; +1/-1 from config.observed_urdf_sign


def _clamp_raw(v: int) -> int:
    return max(0, min(RAW_FULL_SCALE, v))


class HardStopCalibrator:
    """Drive one joint to its mechanical stop and derive the home offset.

    Callbacks (all raw units, all synchronous):
        read_position(joint_id) -> int          present position 0..4095
        read_load(joint_id)     -> int          |present load| 0..1000
        send_goal(joint_id, raw)                command a goal position
        is_aborted()            -> bool         True => stop now (safety/e-stop)
        sleep_tick()                            block one control period
    """

    def __init__(
        self,
        read_position,
        read_load,
        send_goal,
        is_aborted,
        sleep_tick,
        params: HardStopParams = None,
    ):
        self._read_position = read_position
        self._read_load = read_load
        self._send_goal = send_goal
        self._is_aborted = is_aborted
        self._sleep_tick = sleep_tick
        self.p = params or HardStopParams()

    def run_joint(self, cfg) -> HardStopResult:
        """cfg is a config.JointHomeConfig."""
        jid = cfg.joint_id
        if getattr(cfg, "placeholder", False):
            return HardStopResult(
                jid,
                Outcome.SKIPPED,
                detail="placeholder config (fill search_dir / "
                "stop_to_home_raw from CAD)",
            )
        if cfg.search_dir not in (+1, -1):
            return HardStopResult(
                jid, Outcome.SKIPPED, detail=f"bad search_dir {cfg.search_dir}"
            )

        p = self.p
        goal = self._read_position(jid)
        prev_pos = goal
        over_count = 0
        peak_load = 0

        for tick in range(p.timeout_ticks):
            if self._is_aborted():
                return HardStopResult(
                    jid,
                    Outcome.ABORTED,
                    ticks=tick,
                    peak_load=peak_load,
                    detail="aborted mid-run",
                )

            goal = _clamp_raw(goal + cfg.search_dir * p.step_raw)
            # Leash the goal to the last measured position. Without this the
            # goal advances open-loop: at a compliant stop the load can sit
            # below load_threshold while the goal runs away to the 0/4095
            # clamp, grinding the gears at ever-increasing torque until the
            # ceiling finally trips (2026-06-12 review). Leashed, the goal
            # stalls when the joint stalls, so worst-case position error —
            # and therefore torque — is bounded at leash_raw + step_raw.
            if cfg.search_dir > 0:
                goal = min(goal, _clamp_raw(prev_pos + p.leash_raw))
            else:
                goal = max(goal, _clamp_raw(prev_pos - p.leash_raw))
            self._send_goal(jid, goal)
            self._sleep_tick()

            pos = self._read_position(jid)
            load = self._read_load(jid)
            peak_load = max(peak_load, load)

            if load >= p.load_ceiling:
                # Blew past the safe ceiling in one step — bail before damage.
                self._back_off(jid, pos, cfg.search_dir)
                return HardStopResult(
                    jid,
                    Outcome.OVERLOAD,
                    stop_pos_raw=pos,
                    peak_load=peak_load,
                    ticks=tick,
                    detail=f"load {load} >= ceiling {p.load_ceiling}",
                )

            moving = abs(pos - prev_pos) > p.pos_epsilon
            prev_pos = pos

            if load >= p.load_threshold and not moving:
                over_count += 1
            else:
                over_count = 0

            if over_count >= p.stall_ticks:
                stop_pos = pos
                home = _clamp_raw(stop_pos - cfg.search_dir * cfg.stop_to_home_raw)
                self._back_off(jid, stop_pos, cfg.search_dir)
                return HardStopResult(
                    jid,
                    Outcome.OK,
                    stop_pos_raw=stop_pos,
                    home_raw=home,
                    peak_load=peak_load,
                    ticks=tick,
                    detail="stop detected",
                )

        return HardStopResult(
            jid,
            Outcome.TIMEOUT,
            peak_load=peak_load,
            ticks=p.timeout_ticks,
            detail="no stop within timeout — check search_dir / "
            "mechanics / load_threshold",
        )

    def _back_off(self, jid, from_pos, search_dir):
        target = _clamp_raw(from_pos - search_dir * self.p.backoff_raw)
        self._send_goal(jid, target)
