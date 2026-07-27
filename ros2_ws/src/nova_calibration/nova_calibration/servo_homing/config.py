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

  stop_urdf_end       'lower' or 'upper' — WHICH end of the joint's URDF range
                      the mechanical stop you are driving into corresponds to.
                      This is the missing piece that makes urdf_sign FREE: the
                      homing run already observes which way raw counts moved to
                      reach the stop, so knowing which URDF end it is gives the
                      raw-vs-URDF direction with no extra motion. See
                      observed_urdf_sign().

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
    stop_urdf_end: str = 'lower'   # 'lower' | 'upper' — see module docstring
    placeholder: bool = True  # True => values are guesses, node will skip


# v1 leg fleet: 4 legs x 3 joints (haa/hfe/kfe). Names mirror the URDF
# convention planned in nova_description (FL/FR/RL/RR + joint).
#
# TODO(calibration): replace placeholder search_dir / stop_to_home_raw with
# values measured from the leg CAD, then set placeholder=False per joint.
# Until then `ros2 run nova_calibration servo_homing_node` will report every
# joint as skipped.
JOINT_CONFIGS = {
    1:  JointHomeConfig(1,  'FL_haa',  search_dir=+1, stop_to_home_raw=deg_to_raw(45)),
    2:  JointHomeConfig(2,  'FL_hfe', search_dir=+1, stop_to_home_raw=deg_to_raw(90)),
    3:  JointHomeConfig(3,  'FL_kfe', search_dir=+1, stop_to_home_raw=deg_to_raw(90)),
    4:  JointHomeConfig(4,  'FR_haa',  search_dir=-1, stop_to_home_raw=deg_to_raw(45)),
    5:  JointHomeConfig(5,  'FR_hfe', search_dir=-1, stop_to_home_raw=deg_to_raw(90)),
    6:  JointHomeConfig(6,  'FR_kfe', search_dir=-1, stop_to_home_raw=deg_to_raw(90)),
    7:  JointHomeConfig(7,  'RL_haa',  search_dir=+1, stop_to_home_raw=deg_to_raw(45)),
    8:  JointHomeConfig(8,  'RL_hfe', search_dir=+1, stop_to_home_raw=deg_to_raw(90)),
    9:  JointHomeConfig(9,  'RL_kfe', search_dir=+1, stop_to_home_raw=deg_to_raw(90)),
    10: JointHomeConfig(10, 'RR_haa',  search_dir=-1, stop_to_home_raw=deg_to_raw(45)),
    11: JointHomeConfig(11, 'RR_hfe', search_dir=-1, stop_to_home_raw=deg_to_raw(90)),
    12: JointHomeConfig(12, 'RR_kfe', search_dir=-1, stop_to_home_raw=deg_to_raw(90)),
}


def observed_urdf_sign(search_dir: int, stop_urdf_end: str) -> int:
    """OBSERVED raw-vs-URDF direction for one joint. +1 / -1.

    Driving in `search_dir` reached the mechanical stop at `stop_urdf_end`, so:

        search_dir=+1 (raw rose) and the stop is the URDF UPPER end
            => raw up went with angle up  => +1
        search_dir=+1 and the stop is the LOWER end
            => raw up went with angle down => -1

    which collapses to sign = search_dir * (+1 upper / -1 lower).

    This is an OBSERVATION -- it comes from a servo that actually moved -- and
    is the missing producer for the `urdf_sign` the command path consumes
    (nova_locomotion node.py, firmware_limits.build_calib). Cross-check it
    against the CAD-derived table before trusting it; see
    nova_ops.safety_envelope.derived_signs.confirm_urdf_sign.
    """
    if search_dir not in (1, -1):
        raise ValueError(f"search_dir must be +1 or -1, got {search_dir}")
    if stop_urdf_end not in ('lower', 'upper'):
        raise ValueError(
            f"stop_urdf_end must be 'lower' or 'upper', got {stop_urdf_end!r}"
        )
    return search_dir * (1 if stop_urdf_end == 'upper' else -1)
