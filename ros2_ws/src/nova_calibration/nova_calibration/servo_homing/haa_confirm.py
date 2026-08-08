"""ros2 run nova_calibration confirm_haa_sign — bench confirmation probe (#194).

WHY THIS EXISTS. limits.record_haa_confirmation() (nova_ops.safety_envelope)
is the only supported way to fill HAA_INBOARD_SIGN, and until #194 nothing
called it — HAA_INBOARD_SIGN stayed all-None forever, so every hip stayed on
the conservative symmetric +-15 deg clamp instead of the asymmetric
15-inboard/40-outboard window limits.py already defines. See config.py's
PLACEHOLDER_REASON: haa stays OUT of the hard-stop routine itself (there is
no known-safe search_dir to drive it into a REAL mechanical stop before the
inboard direction is known), so this is a separate, smaller procedure.

WHY AN OPERATOR, NOT AN AUTOMATIC OBSERVATION. #194 considered deriving
"inboard" from the SAME urdf_sign the hard-stop sweep already confirms for
hfe/kfe (raw-vs-URDF-angle direction, physically observed there via
config.observed_urdf_sign). It does not work as an independent check:
DERIVED_HAA_INBOARD_SIGN (derived_signs.py) composes urdf_sign with two facts
that are already certain by construction — the URDF's own "+haa moves the
foot toward +y on every leg" forward kinematics, and which side of the
chassis a leg bolts to. Both are model facts with no per-unit uncertainty, so
an urdf_sign-only "observation" would ALWAYS agree with the derivation it is
supposed to be checking, for every joint, unconditionally — a confirmation
that cannot fail is exactly the "green but uncovered" shape this project has
hit before, not a real check. The one fact those two inputs cannot supply is
what confirm_haa_sign() actually needs: which way the foot swung relative to
the BODY (inboard vs outboard), a fact about the physical assembly in front
of you. That needs a human (or a trustworthy IMU/vision system — this robot
has neither yet, see #14, no IMU driver) to look at the leg and say which way
it went.

SAFETY. The probe motion is capped well inside the runtime's existing
conservative +-15 deg clamp (limits._HAA_INBOARD_CAP) and NEVER drives
further than that in either direction — the whole point is that the
outboard/inboard direction is UNKNOWN going in, so both directions get the
same small, bounded nudge. A confirmed sign, once recorded, unlocks the
ALREADY-DEFINED asymmetric 15-inboard/40-outboard window in limits.py's own
`_hip_abduction()`; that window's numbers are unchanged by this file — #194
only wires the switch limits.py already built to flip it.

Usage (at the bench, servo powered, leg free to move, operator watching):

    ros2 run nova_calibration confirm_haa_sign --joint FL \\
        --observed inboard --assembly "leg_v6 rev2 / FL / servo 1"

    ros2 run nova_calibration confirm_haa_sign --joint 10 --probe-deg 5 \\
        --reverse --observed outboard --assembly "leg_v6 rev2 / RR / servo 10"
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

from nova_ops.safety_envelope.derived_signs import (
    HAA_IDS,
    HOME_TICK,
    SignMismatch,
    confirm_haa_sign,
)
from nova_ops.safety_envelope.limits import (
    HaaSignConfirmation,
    _HAA_INBOARD_CAP,  # the SAME conservative clamp this probe must stay inside
    confirmed_haa_sign,
    record_haa_confirmation,
)

from .config import RAW_PER_DEG

JOINT_STATES_TIMEOUT_SEC = 3.0
DEFAULT_SETTLE_S = 0.5

#: Degrees. The runtime's existing conservative symmetric clamp (limits.py) —
#: read from the SAME constant _hip_abduction() uses, not re-typed, so a
#: future change to the clamp cannot silently drift out of step with this
#: probe's safety fence.
CLAMP_DEG = math.degrees(_HAA_INBOARD_CAP)

#: Degrees. The probe must stay STRICTLY inside CLAMP_DEG — this is the
#: safety MARGIN, not the clamp itself.
MAX_PROBE_DEG = CLAMP_DEG / 2.0

assert 0 < MAX_PROBE_DEG < CLAMP_DEG, "probe bound must stay inside the runtime clamp"


class HaaConfirmRefused(Exception):
    """The probe (or the confirmation call) was refused outright — an unsafe
    or malformed request, distinct from a legitimate SignMismatch."""


# ---- pure logic (no rclpy — testable directly) --------------------------


def resolve_haa_joint(arg: str) -> Tuple[int, str]:
    """--joint accepts a leg name (FL/FR/RL/RR) or a haa bus id (1/4/7/10)."""
    if arg in HAA_IDS:
        return HAA_IDS[arg], arg
    if arg.lstrip("-").isdigit():
        bus_id = int(arg)
        by_id = {v: k for k, v in HAA_IDS.items()}
        if bus_id in by_id:
            return bus_id, by_id[bus_id]
    raise HaaConfirmRefused(
        f"{arg!r} is not a haa joint — expected one of {sorted(HAA_IDS)} or "
        f"bus id {sorted(HAA_IDS.values())}"
    )


def deg_to_raw(deg: float) -> float:
    return deg * RAW_PER_DEG


def probe_fence_raw(home_tick: int = HOME_TICK) -> Tuple[float, float]:
    """Absolute raw-count window the runtime's own +-CLAMP_DEG clamp allows,
    centered on the servo's measured mechanical home tick (HOME_TICK=2048,
    derived_signs.py: "one-key center at the nominal pose", MEASURED, applies
    to every joint by the homing/assembly convention)."""
    span = deg_to_raw(CLAMP_DEG)
    return home_tick - span, home_tick + span


def compute_probe_target(
    present_raw: float,
    probe_deg: float,
    direction: int,
    home_tick: int = HOME_TICK,
) -> float:
    """The raw goal for one bounded haa probe move. REFUSES rather than
    clamps — see HaaConfirmRefused. Clamping silently would mean some probes
    secretly move less than requested near the fence, which hides exactly
    the situation an operator needs to be told about plainly.

    Refuses if: probe_deg is outside (0, MAX_PROBE_DEG]; the present position
    is not already inside the runtime clamp's raw window (a leg that starts
    outside +-CLAMP_DEG of home is not a state this tool should be nudging
    further from); or the computed target would leave that window.
    """
    if direction not in (1, -1):
        raise ValueError(f"direction must be +1 or -1, got {direction!r}")
    if not (0 < probe_deg <= MAX_PROBE_DEG):
        raise HaaConfirmRefused(
            f"probe_deg={probe_deg} must be in (0, {MAX_PROBE_DEG:.1f}] deg "
            f"— well inside the +-{CLAMP_DEG:.0f} deg runtime clamp"
        )
    lo, hi = probe_fence_raw(home_tick)
    if not (lo <= present_raw <= hi):
        raise HaaConfirmRefused(
            f"present position {present_raw:.0f} raw is already outside the "
            f"+-{CLAMP_DEG:.0f} deg clamp window [{lo:.0f}, {hi:.0f}] around "
            f"home tick {home_tick} — refusing to probe from here"
        )
    target = present_raw + direction * deg_to_raw(probe_deg)
    if not (lo <= target <= hi):
        raise HaaConfirmRefused(
            f"probe target {target:.0f} raw would leave the "
            f"+-{CLAMP_DEG:.0f} deg clamp window [{lo:.0f}, {hi:.0f}] — refusing"
        )
    return target


def confirm_and_record(
    joint_id: int,
    raw_delta: float,
    observed_inboard: Optional[bool],
    *,
    assembly: str,
    method: Optional[str] = None,
    observed_utc: Optional[str] = None,
    log=print,
) -> Optional[HaaSignConfirmation]:
    """Check one hip's probe observation and, on agreement, record + return
    the confirmation. Returns None (after logging loudly) on a genuine
    disagreement or when already confirmed — raises only for a request that
    is unsafe or malformed on its face, never for a legitimate mismatch.
    """
    if joint_id not in HAA_IDS.values():
        raise ValueError(
            f"joint {joint_id} is not a haa joint {sorted(HAA_IDS.values())}"
        )
    if not str(assembly).strip():
        raise ValueError(
            "assembly is required — a sign with no recorded 'on what' is not "
            "a confirmation"
        )
    safe_bound = deg_to_raw(MAX_PROBE_DEG) + 1.0  # +1 raw: rounding slack
    if abs(raw_delta) > safe_bound:
        raise HaaConfirmRefused(
            f"raw_delta={raw_delta:+.0f} exceeds the safe probe bound "
            f"(+-{safe_bound:.0f} raw) — refusing to confirm from a motion "
            f"this tool did not itself command"
        )

    existing_sign = confirmed_haa_sign(joint_id)
    if existing_sign is not None:
        log(f"joint {joint_id}: already confirmed sign {existing_sign:+d} — no-op")
        return HaaSignConfirmation(
            sign=existing_sign,
            observed_utc=observed_utc or "",
            method="already confirmed — no-op",
            assembly=assembly,
        )

    try:
        sign = confirm_haa_sign(joint_id, raw_delta, observed_inboard)
    except SignMismatch as exc:
        log(
            f"joint {joint_id}: SIGN MISMATCH — {exc} Leaving HAA_INBOARD_SIGN "
            f"UNCONFIRMED (None). Do not proceed until this is understood."
        )
        return None

    utc = observed_utc or datetime.now(timezone.utc).isoformat(timespec="seconds")
    method = method or (
        f"bench probe: {raw_delta:+.0f} raw counts, operator observed "
        f"{'INBOARD' if observed_inboard else 'OUTBOARD'}"
    )
    record_haa_confirmation(
        joint_id, sign=sign, observed_utc=utc, method=method, assembly=assembly
    )
    log(f"joint {joint_id}: CONFIRMED sign {sign:+d} ({assembly})")
    return HaaSignConfirmation(sign=sign, observed_utc=utc, method=method, assembly=assembly)


# ---- ROS-touching glue (rclpy imported here, not at module scope, so this
# module stays importable — and unit-testable — without a ROS install) ------


def _run(node, args) -> int:
    from nova_ops.jog import _publish_positions, _wait_for_joint_states
    from nova_ops.safety_envelope.calibration_io import (
        DEFAULT_CALIBRATION_PATH,
        apply_haa_confirmations,
    )

    from . import storage

    try:
        joint_id, leg = resolve_haa_joint(args.joint)
    except HaaConfirmRefused as e:
        print(f"refusing: {e}", file=sys.stderr)
        return 1

    # Pick up anything already confirmed & persisted from a prior run/process
    # (#194's other half — calibration_io.apply_haa_confirmations mirrors
    # resolve_calibration() for urdf_sign).
    try:
        apply_haa_confirmations(DEFAULT_CALIBRATION_PATH)
    except Exception as exc:  # noqa: BLE001 — an unreadable artifact must not crash the probe
        print(
            f"warning: could not load persisted haa confirmations: {exc!r}",
            file=sys.stderr,
        )

    existing = confirmed_haa_sign(joint_id)
    if existing is not None:
        print(
            f"{leg}_haa (id {joint_id}): already confirmed, sign={existing:+d} "
            f"— nothing to do"
        )
        return 0

    positions = _wait_for_joint_states(node, JOINT_STATES_TIMEOUT_SEC)
    if positions is None:
        print(
            f"refusing: no /joint_states (12+ positions) within "
            f"{JOINT_STATES_TIMEOUT_SEC:.1f}s — is the Teensy bridge up?",
            file=sys.stderr,
        )
        return 1

    present = positions[joint_id - 1]
    direction = -1 if args.reverse else 1
    try:
        target = compute_probe_target(present, args.probe_deg, direction)
    except HaaConfirmRefused as e:
        print(f"refusing: {e}", file=sys.stderr)
        return 1

    print(
        f"!!! commanding {leg}_haa (id {joint_id}) from {present:.0f} to "
        f"{target:.0f} raw ({direction * args.probe_deg:+.1f} deg) — WATCH "
        f"THE LEG. Report which way the FOOT actually swung with --observed. !!!",
        file=sys.stderr,
    )
    out = list(positions)
    out[joint_id - 1] = target
    _publish_positions(node, out)

    time.sleep(args.settle_s)
    after = _wait_for_joint_states(node, JOINT_STATES_TIMEOUT_SEC)
    if after is None:
        print(
            "refusing: lost /joint_states after the probe move — cannot "
            "confirm from an unmeasured motion",
            file=sys.stderr,
        )
        return 1
    measured_delta = after[joint_id - 1] - present

    confirmation = confirm_and_record(
        joint_id,
        measured_delta,
        args.observed == "inboard",
        assembly=args.assembly,
        log=lambda msg: print(msg, file=sys.stderr),
    )
    if confirmation is None:
        return 1

    path = storage.save_haa_confirmation(joint_id, confirmation)
    print(f"{leg}_haa (id {joint_id}): confirmed and saved to {path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="confirm_haa_sign",
        description=(
            "Bench probe: command a small, bounded haa motion and confirm "
            "HAA_INBOARD_SIGN against the CAD derivation (#194)."
        ),
    )
    parser.add_argument("--joint", required=True, help="FL/FR/RL/RR or haa bus id (1/4/7/10)")
    parser.add_argument(
        "--observed", required=True, choices=("inboard", "outboard"),
        help="which way the FOOT actually swung, as watched by the operator",
    )
    parser.add_argument(
        "--assembly", required=True,
        help="which physical leg/servo this was observed on, e.g. "
             "'leg_v6 rev2 / FL / servo 1'",
    )
    parser.add_argument(
        "--probe-deg", type=float, default=MAX_PROBE_DEG,
        help=f"probe magnitude in degrees, must be <= {MAX_PROBE_DEG:.1f} "
             f"(half the runtime's +-{CLAMP_DEG:.0f} deg clamp)",
    )
    parser.add_argument(
        "--reverse", action="store_true",
        help="probe toward decreasing raw counts instead of increasing",
    )
    parser.add_argument(
        "--settle-s", type=float, default=DEFAULT_SETTLE_S,
        help="seconds to wait after commanding the probe before reading it back",
    )
    args = parser.parse_args(argv)

    import rclpy
    from rclpy.node import Node

    rclpy.init(args=None)
    node = Node("nova_confirm_haa_sign")
    try:
        rc = _run(node, args)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(rc)


if __name__ == "__main__":
    main()
