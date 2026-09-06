"""hardware/cad/chassis/rom_envelope_table.py and nova_ops/rom_envelope_table.py
must stay byte-identical.

WHY THIS EXISTS (#392). The CAD-side gate (check_fit.py) and the runtime
package (nova_ops.rom_envelope) each need their own importable copy of the
same generated table — one lives outside ros2_ws, one inside it, and nothing
compared them. Same class of bug as #392's nova_geometry.yaml: a file that
LOOKS like a synced copy with no test enforcing the sync.
"""
import pathlib

import pytest

_REPO = pathlib.Path(__file__).resolve().parents[4]
_CHASSIS_COPY = _REPO / "hardware" / "cad" / "chassis" / "rom_envelope_table.py"
_OPS_COPY = pathlib.Path(__file__).resolve().parents[1] / "nova_ops" / "rom_envelope_table.py"


@pytest.mark.skipif(
    not _CHASSIS_COPY.exists(),
    reason="hardware/cad/chassis/rom_envelope_table.py not present in this checkout",
)
def test_rom_envelope_table_copies_are_byte_identical():
    assert _OPS_COPY.exists(), f"{_OPS_COPY} missing"
    assert _CHASSIS_COPY.read_bytes() == _OPS_COPY.read_bytes(), (
        "hardware/cad/chassis/rom_envelope_table.py and "
        "ros2_ws/src/nova_ops/nova_ops/rom_envelope_table.py have drifted — "
        "update both copies together"
    )
