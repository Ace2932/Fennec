"""Unit tests for servo_homing/config.py's #284 CAD derivation.

Three checks, each cross-source (imports the authority, never copies its
numbers as literals):

  (i)   every filled stop sits on the correct side of limits.py's ROM, within
        the CAD-documented mechanical margin — see the docstring on
        test_expected_stop_is_beyond_the_rom_in_the_right_direction for why
        this is "just beyond", not "inside" (a hard stop by definition lives
        outside the walkable envelope).
  (ii)  hfe/kfe search_dir is correctly mirrored left vs right, per the same
        derived_signs table the URDF cross-checks itself against
        (test_derived_signs.py's MJCF front/rear negation test).
  (iii) every placeholder=True entry has a documented reason containing
        'placeholder because' — negative-controlled, so a joint can't ship
        "skipped, no explanation".
"""
import math

from nova_calibration.servo_homing.config import (
    JOINT_CONFIGS,
    PLACEHOLDER_REASON,
    JointHomeConfig,
    expected_stop_deg,
    observed_urdf_sign,
)
from nova_ops.safety_envelope.derived_signs import (
    DERIVED_URDF_SIGN,
    HFE_IDS,
    KFE_IDS,
    LEFT_LEGS,
    RIGHT_LEGS,
)
from nova_ops.safety_envelope.limits import load_default_limits

# Real CAD margins between the software ROM and the measured mechanical wall
# are 7 deg (hfe: 86 sw / 93 mech, hardware/cad/leg_v6/check_fit.py:418-419)
# and 9 deg (kfe: 109 sw / 118 mech, check_fit.py:345 / nova_description/
# urdf/nova.urdf.xacro:61). This is a generous ceiling on top of that, not a
# copied value: it exists to catch a derivation that targets the wrong CAD
# feature entirely (e.g. off by a joint's whole range), not to pin the exact
# margin.
MAX_STOP_MARGIN_DEG = 20.0


def _rom_deg(joint_id):
    lim = load_default_limits().get(joint_id)
    return math.degrees(lim.lower), math.degrees(lim.upper)


def _stop_is_sane(cfg: JointHomeConfig, lower_deg: float, upper_deg: float):
    """None if fine, else a string explaining what's wrong.

    A genuine hard-stop target for a joint whose software ROM already sits at
    a conservative margin below the mechanical wall (hfe, kfe — see module
    docstring) is NECESSARILY outside that ROM; hard_stop.py's own module
    docstring says so explicitly ("the stops live outside walk ROM by
    design"). So the correct cross-check is direction + bounded overshoot,
    not containment.
    """
    stop = expected_stop_deg(cfg)
    if cfg.stop_urdf_end == 'lower':
        if not (lower_deg - MAX_STOP_MARGIN_DEG <= stop <= lower_deg):
            return (f"stop {stop:.1f} not within {MAX_STOP_MARGIN_DEG} deg "
                     f"beyond the lower ROM bound {lower_deg:.1f}")
    else:
        if not (upper_deg <= stop <= upper_deg + MAX_STOP_MARGIN_DEG):
            return (f"stop {stop:.1f} not within {MAX_STOP_MARGIN_DEG} deg "
                     f"beyond the upper ROM bound {upper_deg:.1f}")
    return None


def test_expected_stop_is_beyond_the_rom_in_the_right_direction():
    checked = 0
    for jid, cfg in JOINT_CONFIGS.items():
        if cfg.placeholder:
            continue
        checked += 1
        lower_deg, upper_deg = _rom_deg(jid)
        problem = _stop_is_sane(cfg, lower_deg, upper_deg)
        assert problem is None, f"joint {jid} {cfg.name}: {problem}"
    assert checked == 8, f"expected 8 filled (hfe+kfe) configs, saw {checked}"


def test_expected_stop_sanity_check_has_teeth():
    """Negative control: a config with a wildly wrong stop must be flagged.

    Without this, test_expected_stop_is_beyond_the_rom_in_the_right_direction
    could be vacuously true (e.g. a check that never actually looks at the
    values) and nobody would notice.
    """
    lower_deg, upper_deg = _rom_deg(2)  # FL_hfe: lower=-86, upper=+86
    bad_far = JointHomeConfig(
        2, 'FL_hfe', search_dir=-1,
        stop_to_home_raw=round((abs(lower_deg) + 90) * 4096 / 360),
        stop_urdf_end='lower', placeholder=False)
    assert _stop_is_sane(bad_far, lower_deg, upper_deg) is not None

    # Right end declared, but the offset is nowhere near it (still well
    # inside the walkable ROM instead of beyond it) — the direction label
    # alone doesn't make a small offset a valid hard-stop target.
    bad_inside_rom = JointHomeConfig(
        2, 'FL_hfe', search_dir=+1,
        stop_to_home_raw=round(10 * 4096 / 360),
        stop_urdf_end='upper', placeholder=False)
    assert _stop_is_sane(bad_inside_rom, lower_deg, upper_deg) is not None


def test_hfe_kfe_search_dir_mirrors_left_right_per_derived_urdf_sign():
    """L/R mirrored joints must get opposite search_dir.

    Both sides target the SAME URDF end (the self-collision wall is
    symmetric — config.py module comment), so a correctly mirrored pair
    differs only in which raw direction reaches it — exactly the sign flip
    DERIVED_URDF_SIGN encodes left-to-right for the lateral (hfe/kfe) shaft
    (derived_signs.py:56-58), which is itself cross-checked against the
    URDF/MJCF front/rear hfe range negation in test_derived_signs.py.
    """
    pairs = 0
    for ids in (HFE_IDS, KFE_IDS):
        for left, right in zip(LEFT_LEGS, RIGHT_LEGS):
            l_cfg, r_cfg = JOINT_CONFIGS[ids[left]], JOINT_CONFIGS[ids[right]]
            assert not l_cfg.placeholder and not r_cfg.placeholder
            assert l_cfg.stop_urdf_end == r_cfg.stop_urdf_end
            assert l_cfg.search_dir == -r_cfg.search_dir, (
                f"{left}/{right} {ids}: search_dir not mirrored "
                f"({l_cfg.search_dir:+d} / {r_cfg.search_dir:+d})")
            assert DERIVED_URDF_SIGN[ids[left]] == -DERIVED_URDF_SIGN[ids[right]]
            # and each side's config actually implies the derived sign —
            # the load-bearing check (also covered in test_hard_stop.py).
            assert observed_urdf_sign(l_cfg.search_dir, l_cfg.stop_urdf_end) == (
                DERIVED_URDF_SIGN[ids[left]])
            assert observed_urdf_sign(r_cfg.search_dir, r_cfg.stop_urdf_end) == (
                DERIVED_URDF_SIGN[ids[right]])
            pairs += 1
    assert pairs == 4  # 2 joint types x 2 front/rear pairs


def test_every_placeholder_has_a_documented_reason():
    for jid, cfg in JOINT_CONFIGS.items():
        if not cfg.placeholder:
            continue
        reason = PLACEHOLDER_REASON.get(jid)
        assert reason, f"joint {jid} {cfg.name}: placeholder with no PLACEHOLDER_REASON entry"
        assert 'placeholder because' in reason.lower(), (
            f"joint {jid} {cfg.name}: reason does not explain itself "
            f"('placeholder because...'): {reason!r}")


def test_placeholder_reason_check_has_teeth():
    """Negative control: a placeholder joint with no reason must be caught."""
    configs = dict(JOINT_CONFIGS)
    configs[99] = JointHomeConfig(99, 'fake_joint', search_dir=+1, stop_to_home_raw=1)
    reasons = dict(PLACEHOLDER_REASON)  # deliberately NOT adding 99

    undocumented = [
        jid for jid, cfg in configs.items()
        if cfg.placeholder and 'placeholder because' not in reasons.get(jid, '').lower()
    ]
    assert undocumented == [99]


def test_haa_stays_placeholder():
    """#284 safety rule: haa cannot be hard-stop homed until HAA_INBOARD_SIGN
    is hardware-confirmed (#194) — see PLACEHOLDER_REASON."""
    for jid in (1, 4, 7, 10):
        assert JOINT_CONFIGS[jid].placeholder, f"joint {jid} must stay placeholder"
        assert JOINT_CONFIGS[jid].name.endswith('_haa')
