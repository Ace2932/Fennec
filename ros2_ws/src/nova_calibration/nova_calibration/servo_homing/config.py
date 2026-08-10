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


#: Required on every JOINT_CONFIGS entry still carrying placeholder=True.
#: The string 'placeholder because' is enforced by
#: test_config.test_every_placeholder_has_a_documented_reason — a joint
#: cannot ship "skipped, no explanation" (see #284).
PLACEHOLDER_REASON = {
    # haa (hip abduction/adduction) — issue #284, safety rule.
    #
    # placeholder because: hard-stop homing needs a search_dir that is KNOWN
    # safe (README "never drive a joint into a stop with a guessed
    # direction"). For haa that means knowing which raw-tick direction is
    # OUTBOARD (safe) vs INBOARD (belly-pack strike risk, limits.py:50-60,
    # "belly-pack contact from ~18 inboard"). That direction is
    # HAA_INBOARD_SIGN (limits.py:61), which is None for every hip — the CAD
    # prediction exists (derived_signs.DERIVED_HAA_INBOARD_SIGN, diagonal
    # FL+1/FR-1/RL-1/RR+1, derived_signs.py:198-203) but is explicitly
    # documented "DERIVED, NOT CONFIRMED... nothing here is wired into the
    # runtime" (derived_signs.py:177-182) until confirm_haa_sign() checks it
    # against a real small (well-inside-+-15) observed motion. A hard-stop sweep drives to
    # the REAL mechanical stop, well beyond the conservative +-15 the
    # confirmation step stays inside of, and beyond the ~18-20 inboard
    # belly-pack contact threshold (docs/design-outline.md:29,
    # nova.urdf.xacro:24-25) if the guess is wrong. That is exactly the
    # guessed-direction-into-a-stop case the module docstring forbids.
    # STATUS CORRECTED 2026-08-10: this used to read "#194, record_haa_confirmation
    # has no caller yet" and "unlocks once #194 lands". BOTH ARE NOW FALSE, and the
    # difference matters: #194 HAS landed. record_haa_confirmation() has real
    # callers (nova_calibration/servo_homing/haa_confirm.py:219 and
    # nova_ops/safety_envelope/calibration_io.py:226, which calls itself "the
    # missing half of #194"), and there is a runnable command --
    #     ros2 run nova_calibration confirm_haa_sign      (docs/calibration.md:48)
    #
    # So this is NO LONGER A SOFTWARE GAP. The placeholder below is still correct,
    # but for a different reason: HAA_INBOARD_SIGN is {1,4,7,10: None} because no
    # OBSERVATION has been taken yet, not because there is nowhere to put one.
    # Unlocks the moment confirm_haa_sign() records a real motion for this joint.
    # Left stale, this comment tells whoever does homing that the code is missing
    # and there is nothing to run -- when in fact the procedure is available.
    1: 'placeholder because HAA_INBOARD_SIGN[1] is unconfirmed (limits.py:61) — '
       'see PLACEHOLDER_REASON module comment above for the full chain',
    4: 'placeholder because HAA_INBOARD_SIGN[4] is unconfirmed (limits.py:61) — '
       'see PLACEHOLDER_REASON module comment above for the full chain',
    7: 'placeholder because HAA_INBOARD_SIGN[7] is unconfirmed (limits.py:61) — '
       'see PLACEHOLDER_REASON module comment above for the full chain',
    10: 'placeholder because HAA_INBOARD_SIGN[10] is unconfirmed (limits.py:61) — '
        'see PLACEHOLDER_REASON module comment above for the full chain',
}


# v1 leg fleet: 4 legs x 3 joints (haa/hfe/kfe). Names mirror the URDF
# convention in nova_description (FL/FR/RL/RR + joint,
# nova_description/config/joint_id_map.yaml).
#
# #284 derivation (2026-08-06) — see the PR body for the full per-joint
# table. Summary of what each filled entry encodes:
#
#   hfe/kfe stop_urdf_end='lower': the only CAD-verified, rigid, repeatable
#   hard stop for either joint is leg self-collision (femur vs tibia/knee_arm
#   structure), measured SYMMETRIC at both extremes —
#   hardware/cad/leg_v6/check_fit.py:345-347 (kfe: clean to sw 109 deg,
#   mechanical contact at ~118 deg, matching nova.urdf.xacro:61) and
#   check_fit.py:416-419 (hfe: clean to 92.5 deg, first contact at 93 deg,
#   matching nova.urdf.xacro:58-60 / limits.py's "purely MECHANICAL" ±86 deg
#   window). Both ends are equally rigid/safe (leg-on-itself, not
#   leg-on-chassis — "self-collision" per LA-19/LA-19a), so 'lower' (the
#   away-from-zero, more-negative URDF end) was picked as the target for
#   both joints: for hfe check_fit.py:419 found the -93 deg contact more
#   decisive (3 points at first contact vs +93's 1 point); for kfe there is
#   no CAD-measured stop at all on the 'upper' (near-straight) end — the -5
#   deg software ceiling there is an arbitrary "never lock the knee
#   straight" choice (limits.py:311-312), not a measured mechanical wall, so
#   'lower' (deep fold, the ~118 deg stop) is the only option with real data
#   behind it.
#
#   search_dir is chosen so the sweep reaches that 'lower' URDF end, using
#   the CAD-DERIVED (not yet hardware-confirmed) raw-vs-URDF sign from
#   nova_ops.safety_envelope.derived_signs.DERIVED_URDF_SIGN
#   (derived_signs.py:225-236): search_dir = -DERIVED_URDF_SIGN[id] for a
#   'lower'-end target (observed_urdf_sign(search_dir, 'lower') ==
#   search_dir * -1, so this is exactly the value that makes the sweep's own
#   observation agree with the derivation — see
#   test_config.test_hfe_kfe_search_dir_mirrors_left_right_per_derived_urdf_sign
#   and
#   test_hard_stop.test_observed_sign_agrees_with_the_cad_derivation_for_every_joint).
#   This is unlike haa: hfe/kfe do NOT need the direction to be
#   hardware-confirmed first, because BOTH URDF ends are self-collision (not
#   a body-frame-dependent "which way is toward the LiPo" question) — a
#   wrong guess drives into the WRONG rigid CAD stop (a real mechanical wall,
#   detected the same way) rather than into open air toward the chassis.
#   The sweep's own load-ceiling abort (hard_stop.py load_ceiling=600 permille,
#   matching the firmware's 600 permille torque cap, hard_stop.py:19-22)
#   still protects the gearbox either way.
#
#   stop_to_home_raw = deg_to_raw(<mechanical stop magnitude>): the raw-count
#   distance from that stop to the URDF zero (theta=0, "straight down" per
#   leg_ik.py's FK convention, NOT the walking stand pose).
#
#   Current/speed thresholds are GLOBAL, not per-joint (HardStopParams has no
#   per-joint override) — the existing hard_stop.py defaults
#   (load_threshold=200/1000, load_ceiling=600/1000 matching the firmware's
#   600-permille torque cap, step_raw=4 raw/tick @ 20 Hz =~ 7 deg/s) already
#   apply and were not changed by this derivation.
#
#   haa (ids 1, 4, 7, 10) stays placeholder=True — see PLACEHOLDER_REASON.
JOINT_CONFIGS = {
    1:  JointHomeConfig(1,  'FL_haa', search_dir=+1, stop_to_home_raw=deg_to_raw(45)),
    2:  JointHomeConfig(2,  'FL_hfe', search_dir=-1, stop_to_home_raw=deg_to_raw(93),
                         stop_urdf_end='lower', placeholder=False),
    3:  JointHomeConfig(3,  'FL_kfe', search_dir=-1, stop_to_home_raw=deg_to_raw(118),
                         stop_urdf_end='lower', placeholder=False),
    4:  JointHomeConfig(4,  'FR_haa', search_dir=-1, stop_to_home_raw=deg_to_raw(45)),
    5:  JointHomeConfig(5,  'FR_hfe', search_dir=+1, stop_to_home_raw=deg_to_raw(93),
                         stop_urdf_end='lower', placeholder=False),
    6:  JointHomeConfig(6,  'FR_kfe', search_dir=+1, stop_to_home_raw=deg_to_raw(118),
                         stop_urdf_end='lower', placeholder=False),
    7:  JointHomeConfig(7,  'RL_haa', search_dir=+1, stop_to_home_raw=deg_to_raw(45)),
    8:  JointHomeConfig(8,  'RL_hfe', search_dir=-1, stop_to_home_raw=deg_to_raw(93),
                         stop_urdf_end='lower', placeholder=False),
    9:  JointHomeConfig(9,  'RL_kfe', search_dir=-1, stop_to_home_raw=deg_to_raw(118),
                         stop_urdf_end='lower', placeholder=False),
    10: JointHomeConfig(10, 'RR_haa', search_dir=-1, stop_to_home_raw=deg_to_raw(45)),
    11: JointHomeConfig(11, 'RR_hfe', search_dir=+1, stop_to_home_raw=deg_to_raw(93),
                         stop_urdf_end='lower', placeholder=False),
    12: JointHomeConfig(12, 'RR_kfe', search_dir=+1, stop_to_home_raw=deg_to_raw(118),
                         stop_urdf_end='lower', placeholder=False),
}


def expected_stop_deg(cfg: JointHomeConfig) -> float:
    """CAD-expected stop angle in signed URDF degrees (theta=0 = home).

    Pure readback of stop_to_home_raw + stop_urdf_end, in the units the CAD
    ROM sources (nova_ops.safety_envelope.limits) use, so tests/tools can
    cross-check against limits.py without re-deriving the raw math.
    """
    mag_deg = cfg.stop_to_home_raw / RAW_PER_DEG
    return mag_deg if cfg.stop_urdf_end == 'upper' else -mag_deg


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
