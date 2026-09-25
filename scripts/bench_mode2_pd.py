"""MODE 2 (PWM open loop) + host PD loop sine test on one STS3215 (bench only, #428).

  .venv/bin/python scripts/bench_mode2_pd.py [KP] [KD]   # defaults 2.0 0.08

Volatile: EEPROM lock (0x37) must already be 1, so the mode write is lost at power
cycle; the finally block also restores mode 0 explicitly. Aborts to PWM 0 if the
horn strays > MAX_DEV steps from center or reads keep failing.
"""
import importlib.util
import math
import sys
import time

import serial

import os
spec = importlib.util.spec_from_file_location(
    "b", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bench_step_response.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

# ponytail: port/ID are constants for the one-servo bench; argparse if this becomes routine
PORT, SID = "/dev/cu.usbmodem5AE60578091", 1
REG_MODE, REG_PWM, REG_LOCK = 0x21, 0x2C, 0x37
MAX_DEV = 350          # steps (~31 deg) from center -> abort
DMAX = 700             # duty clamp, permille
KFF = 1 / 3.5          # permille per step/s (no-load ~3500 steps/s at 100 %)
KP = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0    # permille per step
KD = float(sys.argv[2]) if len(sys.argv) > 2 else 0.08   # permille per step/s


def pwm_bytes(d):
    d = max(-DMAX, min(DMAX, int(round(d))))
    mag = abs(d)
    v = mag | (0x400 if d < 0 else 0)
    return bytes([v & 0xFF, (v >> 8) & 0xFF])


def read_pv(ser):
    r = b.read_bytes(ser, SID, 0x38, 4)
    if r is None:
        return None
    pos = r[0] | (r[1] << 8)
    spd = b.signed15(r[2] | (r[3] << 8))
    return pos, spd


def main():
    ser = serial.Serial(PORT, 1000000, timeout=0.02)
    assert b.read_bytes(ser, SID, REG_LOCK, 1)[0] == 1, "EEPROM lock must be 1 (volatile)"
    center = read_pv(ser)[0]
    try:
        assert b.write_reg(ser, SID, REG_MODE, bytes([2])), "mode write failed"
        assert b.read_bytes(ser, SID, REG_MODE, 1)[0] == 2
        # direction probe: +150 permille for 120 ms
        p0 = read_pv(ser)[0]
        b.write_reg(ser, SID, REG_PWM, pwm_bytes(150))
        time.sleep(0.12)
        b.write_reg(ser, SID, REG_PWM, pwm_bytes(0))
        time.sleep(0.2)
        p1 = read_pv(ser)[0]
        sign = 1 if p1 > p0 else -1
        print(f"direction probe: {p0} -> {p1}  (+duty moves {'+' if sign > 0 else '-'})")
        if abs(p1 - p0) < 3:
            sys.exit("no motion on +150 duty; aborting")
        # re-center under PD
        amp = 15 / b.DEG_PER_CNT
        print(f"KP={KP} KD={KD} KFF={KFF:.3f}  center={center}")
        print("  hz   ratio   lag_ms   loop_hz  peak_duty")
        for hz in (0.5, 1.0, 1.4, 2.0, 3.0):
            rows, fails, t0 = [], 0, time.perf_counter()
            w = 2 * math.pi * hz
            dur = 8 / hz
            peak = 0
            last_p, last_t, vel = None, None, 0.0
            while (t := time.perf_counter() - t0) < dur:
                pv = read_pv(ser)
                if pv is None:
                    fails += 1
                    if fails > 5:
                        raise RuntimeError("read failures")
                    continue
                fails = 0
                pos, _ = pv
                if last_p is not None and t > last_t:
                    vel = 0.7 * vel + 0.3 * (pos - last_p) / (t - last_t)  # steps/s, position frame
                last_p, last_t = pos, t
                if abs(pos - center) > MAX_DEV:
                    raise RuntimeError(f"deviation {pos - center} steps")
                cmd = center + amp * math.sin(w * t)
                vcmd = amp * w * math.cos(w * t)
                d = sign * (KFF * vcmd + KP * (cmd - pos) + KD * (vcmd - vel))
                peak = max(peak, min(DMAX, abs(d)))
                b.write_reg(ser, SID, REG_PWM, pwm_bytes(d))
                rows.append((t, cmd, pos))
            b.write_reg(ser, SID, REG_PWM, pwm_bytes(0))
            keep = [r for r in rows if r[0] >= 3.0 / hz]
            ratio, lag, _ = b.tracking([r[0] for r in keep], [r[1] for r in keep], [r[2] for r in keep], hz)
            print(f"  {hz:4.1f}  {ratio:5.2f}  {lag:7.1f}   {len(rows) / dur:6.0f}   {peak:6.0f}")
            time.sleep(0.5)
    finally:
        b.write_reg(ser, SID, REG_PWM, pwm_bytes(0))
        b.write_reg(ser, SID, REG_MODE, bytes([0]))
        pos = read_pv(ser)[0]
        b.write_reg(ser, SID, b.REG_GOAL, bytes([pos & 0xFF, (pos >> 8) & 0xFF]))
        print("restored: mode", b.read_bytes(ser, SID, REG_MODE, 1)[0], "pos", pos)


if __name__ == "__main__":
    main()
