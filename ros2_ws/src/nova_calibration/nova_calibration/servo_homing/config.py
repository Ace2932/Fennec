"""Per-joint hard-stop calibration configuration.

The hard-stop routine drives each joint slowly toward a *known* mechanical
limit, detects the stop via the STS3215 load (effort) reading, then computes
the logical home position from the stop position plus a fixed CAD offset.

For each joint you must know two things from the mechanical design:

  search_dir          +1 to drive toward increasing raw counts, -1 toward
                      decreasing. Pick the direction whose mechanical stop is
                      (a) safe to push against and (b) at a repeatable, rigid
                      hard stop — not a soft cable bundle or a foot on the
                      ground.

  stop_to_home_raw    Raw-count distance from the mechanical stop to the
                      logical joint zero (URDF home). Sign is relative to
                      search_dir: home = stop_pos - search_dir * stop_to_home_raw.
                      Measure in CAD (stop angle -> home angle) and convert:
                      raw = degrees * 4096 / 360.

Until these are filled from the actual leg geometry every entry is marked
PLACEHOLDER and the node refuses to run that joint (fail loud, never drive a
joint with a guessed direction into a stop).

STS3215 reference: full travel 0..4095 = 360deg => 11.378 raw/deg.
Servo IDs are 1..12 (SERVO_ID_BASE=1 in firmware); index = id - 1.
"""
from dataclasses import dataclass

RAW_PER_DEG = 4096.0 / 360.0
RAW_FULL_SCALE = 4095


def deg_to_raw(deg: float) -> int:
    return round(deg * RAW_PER_DEG)


@dataclass(frozen=True)
class JointHomeConfig:
    joint_id: int
    name: str
    search_dir: int          # +1 or -1
    stop_to_home_raw: int    # see module docstring
    placeholder: bool = True  # True => values are guesses, node will skip


# v1 leg fleet: 4 legs x 3 joints (coxa/femur/tibia). Names mirror the URDF
# convention planned in nova_description (FL/FR/RL/RR + joint).
#
# TODO(calibration): replace placeholder search_dir / stop_to_home_raw with
# values measured from the leg CAD, then set placeholder=False per joint.
# Until then `ros2 run nova_calibration servo_homing_node` will report every
# joint as skipped.
JOINT_CONFIGS = {
    1:  JointHomeConfig(1,  'FL_coxa',  search_dir=+1, stop_to_home_raw=deg_to_raw(45)),
    2:  JointHomeConfig(2,  'FL_femur', search_dir=+1, stop_to_home_raw=deg_to_raw(90)),
    3:  JointHomeConfig(3,  'FL_tibia', search_dir=+1, stop_to_home_raw=deg_to_raw(90)),
    4:  JointHomeConfig(4,  'FR_coxa',  search_dir=-1, stop_to_home_raw=deg_to_raw(45)),
    5:  JointHomeConfig(5,  'FR_femur', search_dir=-1, stop_to_home_raw=deg_to_raw(90)),
    6:  JointHomeConfig(6,  'FR_tibia', search_dir=-1, stop_to_home_raw=deg_to_raw(90)),
    7:  JointHomeConfig(7,  'RL_coxa',  search_dir=+1, stop_to_home_raw=deg_to_raw(45)),
    8:  JointHomeConfig(8,  'RL_femur', search_dir=+1, stop_to_home_raw=deg_to_raw(90)),
    9:  JointHomeConfig(9,  'RL_tibia', search_dir=+1, stop_to_home_raw=deg_to_raw(90)),
    10: JointHomeConfig(10, 'RR_coxa',  search_dir=-1, stop_to_home_raw=deg_to_raw(45)),
    11: JointHomeConfig(11, 'RR_femur', search_dir=-1, stop_to_home_raw=deg_to_raw(90)),
    12: JointHomeConfig(12, 'RR_tibia', search_dir=-1, stop_to_home_raw=deg_to_raw(90)),
}
