// Soft-fault controlled limp (#145) — sequencing + per-fault-type policy.
//
// main.cpp used to call set_fleet_torque(false) the instant ANY safety latch
// tripped: the robot went limp wherever it happened to be, mid-air included,
// and dropped. The issue asks for something softer for SOME faults: command
// a known-safe pose, hold torque for ~1 s while the EXISTING slew limiter
// (main.cpp broadcast_servo_commands, unmodified) ramps toward it, then
// release exactly like the old instant path.
//
// NOT EVERY FAULT GETS THIS. See fault_gets_controlled_limp() below for the
// per-type decision and the reasoning behind it.
//
// Pure logic, header-only, no Arduino calls except a caller-supplied
// micros() timestamp — native-testable (pio test -e native), same
// convention as safety_state.h / hfe_envelope.h.

#pragma once

#include <stddef.h>
#include <stdint.h>

#include "safety_state.h"

namespace nova {

constexpr size_t LIMP_JOINT_COUNT = 12;

// ~1 s hold, per issue #145's measured-timing table (sim/nova_mjx/
// probe_sitdown.py): the firmware's own max slew rate (NOVA_SLEW_MAX_DELTA)
// lands a full 40 deg splay in ~227-300 ms — "HARD", 3.16x peak contact,
// barely softer than the 151 ms free fall over the same drop — while 1000 ms
// lands "soft" (1.65x) without needlessly prolonging a powered fault. The
// pose itself is reached well inside this window; the remaining time is
// torque held at rest, not additional motion.
constexpr uint32_t LIMP_HOLD_US = 1000000UL;

// Which SafetyState values get the controlled limp instead of an instant
// torque cut. Only battery-low:
//
//   * E-STOP — NEVER. A human pressing E-stop means stop NOW. A real E-stop
//     is expected to be independent of whatever the firmware is in the
//     middle of; spending another second in a powered pose after an
//     operator's emergency stop defeats the point of having one. (main.cpp
//     also aborts an IN-PROGRESS limp instantly if E-stop is pressed mid-
//     hold, for the same reason.)
//
//   * OVERLOAD / STALL (SAFETY_FAULT_OTHER) — NEVER. This fault fires
//     because a joint is ALREADY at/near its thermal or mechanical limit
//     (main.cpp poll_one_servo(), NOVA_STALL_LOAD_RAW / NOVA_OVERTEMP_C).
//     Commanding the whole fleet through another second of powered motion
//     is exactly the hazard that tripped it — and main.cpp already cuts
//     torque for this fault immediately, inside poll_one_servo(), before
//     this dispatch even runs.
//
//   * BATTERY-LOW — CONTROLLED LIMP. This is not an operator emergency stop
//     and it is not "already broken": it is debounced (50 ms,
//     SafetyFSM::BATT_LOW_DEBOUNCE_TICKS) off a comparator set at 13.0 V,
//     and the pack's actual hard cutoff is the LVC MOSFET at 12.4 V — about
//     0.6 V of real margin that removes power at the HARDWARE level
//     regardless of what the firmware does. There is genuine budget to fold
//     the legs into a stable pose before that hard drop.
inline bool fault_gets_controlled_limp(SafetyState fault) {
  return fault == SAFETY_BATTERY_LOW_LATCHED;
}

// Sequences ONE controlled-limp episode: hold a target pose (already RAW
// COUNTS, bus-ID order) with torque on for LIMP_HOLD_US, then signal
// release. Has no opinion on WHERE the pose comes from (main.cpp's
// limp_pose_raw, published by nova_ops safety_envelope/limp_pose.py — the
// same host-table mechanism as joint_limits/hfe_envelope) or on the slew
// limiter / hfe backstop the caller runs the target through — this class
// only tracks "am I sequencing one, and has the hold window elapsed".
class LimpController {
 public:
  void start(const uint16_t* pose_raw /* [LIMP_JOINT_COUNT] */, uint32_t now_us) {
    for (size_t i = 0; i < LIMP_JOINT_COUNT; i++) target_raw_[i] = pose_raw[i];
    start_us_ = now_us;
    active_ = true;
  }

  bool active() const { return active_; }
  const uint16_t* target() const { return target_raw_; }

  // Call once per tick while active(). Returns true exactly once, the tick
  // the hold window elapses — the caller should cut torque that same tick.
  // A no-op (returns false) once inactive, so a stray call after reset()
  // (or after an earlier true) cannot re-fire.
  bool tick(uint32_t now_us) {
    if (!active_) return false;
    if ((uint32_t)(now_us - start_us_) >= LIMP_HOLD_US) {
      active_ = false;
      return true;
    }
    return false;
  }

  // Abort early — E-stop pressed mid-limp, an overload trip, or the fault
  // clearing before the hold elapsed. No "elapsed" signal, just goes idle.
  void reset() { active_ = false; }

 private:
  uint16_t target_raw_[LIMP_JOINT_COUNT] = {0};
  uint32_t start_us_ = 0;
  bool active_ = false;
};

}  // namespace nova
