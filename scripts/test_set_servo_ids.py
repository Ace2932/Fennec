"""Tests for set-servo-ids.py (#287): checksum/frame/parse against the C++
reference (firmware/teensy/firmware/src/feetech_protocol.h), plus the
lock-status-discard regression (a failed EEPROM lock write must not report
overall OK).

Run: .venv/bin/python -m pytest scripts/test_set_servo_ids.py -q
"""
import importlib.util
import os

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "set_servo_ids", os.path.join(_HERE, "set-servo-ids.py")
)
sid_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sid_mod)


class FakeSerial:
    """Minimal serial.Serial stand-in: hands back one canned response per
    write(), ignoring the actual bytes written (tests set the queue up
    per-call to control what each transact() sees)."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.sent = []

    def reset_input_buffer(self):
        pass

    def write(self, data):
        self.sent.append(bytes(data))

    def flush(self):
        pass

    def read(self, n):
        return self._responses.pop(0) if self._responses else b""


def status_response(sid, err=0x00):
    """FF FF id len err checksum — the ack frame Feetech returns for PING
    and WRITE_DATA (no payload). len = err + checksum = 2."""
    body = bytes([sid, 0x02, err])
    return b"\xff\xff" + body + bytes([sid_mod.checksum(body)])


# ---------------------------------------------------------------------------
# checksum() — hand-computed against feetech_protocol.h's algorithm:
#   checksum = ~(sum of id+len+inst+params) & 0xFF, header bytes excluded.
# ---------------------------------------------------------------------------

def test_checksum_matches_hand_computed_ping_frame():
    # PING id=1: body = [id=1, len=2, inst=0x01]. sum = 1+2+1 = 4.
    # checksum = ~4 & 0xFF = 0xFB.
    assert sid_mod.checksum(bytes([1, 2, 1])) == 0xFB


def test_checksum_negative_control_corrupted_byte_is_wrong():
    # Same frame with one byte corrupted must NOT produce the same checksum
    # — proves the test can actually go red, not just always pass.
    good = sid_mod.checksum(bytes([1, 2, 1]))
    bad = sid_mod.checksum(bytes([1, 2, 1 + 1]))  # inst corrupted 1 -> 2
    assert bad != good
    # and restoring the byte reproduces the known-good value again
    assert sid_mod.checksum(bytes([1, 2, 1])) == good


def test_frame_matches_hand_computed_ping_bytes():
    # FF FF 01 02 01 FB
    assert sid_mod.frame(1, 0x01) == bytes([0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB])


def test_frame_matches_hand_computed_write_bytes():
    # write_reg(id=1, reg=0x37, data=[1]): params = [0x37, 0x01], len = 4.
    # body = [1, 4, 3, 0x37, 1], sum = 1+4+3+55+1 = 64, checksum = ~64&0xFF = 0xBF.
    # FF FF 01 04 03 37 01 BF
    got = sid_mod.frame(1, 0x03, bytes([0x37, 0x01]))
    assert got == bytes([0xFF, 0xFF, 0x01, 0x04, 0x03, 0x37, 0x01, 0xBF])


# ---------------------------------------------------------------------------
# ping() — valid + invalid-checksum response parsing
# ---------------------------------------------------------------------------

def test_ping_valid_response_is_ok():
    ser = FakeSerial([status_response(sid=5)])
    assert sid_mod.ping(ser, 5) is True


def test_ping_invalid_checksum_response_is_not_ok():
    """A frame with the right length and the right id byte but a corrupted
    checksum must be rejected, not read as a live servo (regression: ping()
    used to only check len==6 and id match, accepting a bad checksum)."""
    resp = bytearray(status_response(sid=5))
    resp[-1] ^= 0xFF  # corrupt only the checksum byte
    ser = FakeSerial([bytes(resp)])
    assert sid_mod.ping(ser, 5) is False
    # negative control: the same frame un-corrupted passes
    ser_good = FakeSerial([status_response(sid=5)])
    assert sid_mod.ping(ser_good, 5) is True


def test_ping_no_response_is_not_ok():
    ser = FakeSerial([b""])
    assert sid_mod.ping(ser, 5) is False


# ---------------------------------------------------------------------------
# write_reg() — status (err byte) propagation
# ---------------------------------------------------------------------------

def test_write_reg_ok_on_clear_err_byte():
    ser = FakeSerial([status_response(sid=3, err=0x00)])
    assert sid_mod.write_reg(ser, 3, 0x05, [7]) is True


def test_write_reg_fails_on_set_err_byte():
    ser = FakeSerial([status_response(sid=3, err=0x08)])  # ERR_RANGE
    assert sid_mod.write_reg(ser, 3, 0x05, [7]) is False


# ---------------------------------------------------------------------------
# reassign_id() — the #287 regression: a failed EEPROM lock write must sink
# the overall result, not get silently discarded.
# ---------------------------------------------------------------------------

def test_reassign_id_ok_when_every_step_succeeds():
    old_id, new_id = 1, 7
    ser = FakeSerial([
        status_response(old_id),   # ping(old_id)
        status_response(old_id),   # unlock write
        status_response(old_id),   # ID write
        status_response(new_id),   # lock write
        status_response(new_id),   # ping(new_id)
    ])
    assert sid_mod.reassign_id(ser, old_id, new_id) is True


def test_reassign_id_fails_when_lock_write_fails():
    """The regression this ticket exists for: everything else succeeds but
    the EEPROM lock write comes back with an error byte set. Before the
    fix, that return value was discarded and reassign_id would still report
    OK — the new ID would be live but unpersisted, silently reverting to
    old_id on the next power-cycle."""
    old_id, new_id = 1, 7
    ser = FakeSerial([
        status_response(old_id),               # ping(old_id)
        status_response(old_id),               # unlock write
        status_response(old_id),               # ID write
        status_response(new_id, err=0x20),      # lock write FAILS
        status_response(new_id),               # ping(new_id) still succeeds
    ])
    assert sid_mod.reassign_id(ser, old_id, new_id) is False


def test_reassign_id_fails_when_old_id_not_responding():
    ser = FakeSerial([b""])  # ping(old_id) times out
    assert sid_mod.reassign_id(ser, 1, 7) is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
