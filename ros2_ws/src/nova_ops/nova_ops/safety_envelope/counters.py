"""Per-joint per-failure-mode counters.

Per docs/notes-qol-features.md §3:
    Counters per joint per failure mode published at 1 Hz on
    /safety_envelope_counters. Foxglove panel shows them. Sudden
    uptick on one joint = telltale sign of a stuck encoder, bad URDF
    limit, or a mechanical bind.

Counters publish as Int32MultiArray for v1 (simple). Layout:
  [pos_fail_1, pos_fail_2, ..., pos_fail_12,
   vel_fail_1, ..., vel_fail_12,
   load_fail_1, ..., load_fail_12]
"""
from typing import Dict


# Failure modes in declared layout order
MODES = ('position', 'velocity', 'load')


class EnvelopeCounters:
    """Plain Python counter store. Wrap the rclpy publisher externally —
    keeping the storage class library-only so it's easy to unit-test."""

    def __init__(self, joint_ids):
        self.joint_ids = sorted(joint_ids)
        self._counts: Dict[str, Dict[int, int]] = {
            mode: {jid: 0 for jid in self.joint_ids} for mode in MODES}

    def increment(self, mode: str, joint_id: int) -> None:
        if mode not in self._counts:
            raise ValueError(
                f'unknown mode {mode!r}; expected one of {MODES}')
        if joint_id not in self._counts[mode]:
            return  # joint not tracked (probably arm ID in leg-only build)
        self._counts[mode][joint_id] += 1

    def snapshot(self) -> Dict[str, Dict[int, int]]:
        return {mode: dict(per_joint)
                for mode, per_joint in self._counts.items()}

    def as_flat_list(self) -> list:
        """Flatten to Int32MultiArray layout."""
        out = []
        for mode in MODES:
            for jid in self.joint_ids:
                out.append(self._counts[mode][jid])
        return out

    def reset(self) -> None:
        for per_joint in self._counts.values():
            for k in per_joint:
                per_joint[k] = 0
