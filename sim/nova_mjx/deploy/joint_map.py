"""rad <-> Feetech ticks for NOVA's 12 quadruped joints — framework-free (numpy).

The policy outputs RADIANS in URDF order (FL,FR,RL,RR x haa,hfe,kfe); the servo
bus wants TICKS (0..4095) per servo ID. `joint_id_map.yaml` is per-leg-sequential
(FL_haa=1 .. RR_kfe=12), so JOINT_ORDER index i maps straight to servo ID i+1 —
NO permutation, just a per-joint linear rad<->tick convert. The Jetson does the
convert (calibration lives here in Python, not baked into Teensy firmware); the
bridge just writes the ticks.

    ticks = clip(home_tick + direction * rad * RAW_PER_RAD, 0, RAW_FULL-1)

⚠ home_tick + direction are PLACEHOLDERS until on-robot homing (nova_calibration):
  * home_tick default 2048 = the Feetech one-key-center value — set each joint at
    its nominal pose with `scripts/set-servo-ids.py --center <id>`, and 2048
    becomes home by construction (measured convention, docs/bench/README.md).
  * direction default +1. Measured convention: +tick = CLOCKWISE viewed from the
    horn side. The per-joint sign = that convention x the servo's mount
    orientation (mirrored L/R legs flip it) — set the real signs at homing.
The conversion FORMULA is exact + tested now; only the 12 home/direction values
wait for the bench.
"""
import numpy as np

RAW_FULL = 4096                          # STS3215 encoder counts / revolution
RAW_PER_RAD = RAW_FULL / (2 * np.pi)     # 651.90 counts per radian
CENTER_TICK = 2048                       # one-key-center home tick

# URDF joint order = policy output order = servo-ID order (identity, per
# joint_id_map.yaml: FL_haa=1 .. RR_kfe=12). index i <-> servo ID i+1.
_LEGS = ("FL", "FR", "RL", "RR")
_JOINTS = ("haa", "hfe", "kfe")          # mechanical chain order within a leg
JOINT_ORDER = [f"{leg}_{j}" for leg in _LEGS for j in _JOINTS]
NUM_JOINTS = len(JOINT_ORDER)


class JointMap:
    """Per-joint rad <-> ticks. Pass measured home_tick/direction once homed;
    the defaults (2048 / +1) are the documented placeholders."""

    def __init__(self, home_tick=None, direction=None):
        self.home = (np.full(NUM_JOINTS, CENTER_TICK, np.float64)
                     if home_tick is None else
                     np.asarray(home_tick, np.float64))
        self.dir = (np.ones(NUM_JOINTS, np.float64)
                    if direction is None else
                    np.asarray(direction, np.float64))
        assert self.home.shape == (NUM_JOINTS,), self.home.shape
        assert self.dir.shape == (NUM_JOINTS,), self.dir.shape

    def rad_to_ticks(self, rad):
        """12 radians (JOINT_ORDER) -> 12 int ticks (servo-ID order), clamped to
        the encoder range so a wild policy output can never wrap 4095<->0."""
        t = self.home + self.dir * np.asarray(rad, np.float64) * RAW_PER_RAD
        return np.clip(np.round(t), 0, RAW_FULL - 1).astype(np.int32)

    def ticks_to_rad(self, ticks):
        """12 ticks -> 12 radians (inverse of rad_to_ticks, within 1-tick quant)."""
        return ((np.asarray(ticks, np.float64) - self.home)
                / (self.dir * RAW_PER_RAD)).astype(np.float32)


def load_id_map(path):
    """Load joint_id_map.yaml -> {joint_name: servo_id}. Used by the test to lock
    JOINT_ORDER to the canonical map (the same YAML nova_ops.joint_map loads)."""
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    return data["joint_id_map"]
