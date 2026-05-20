// Safety state machine — E-stop latch + battery-low debounce + master motion
// enable. Wired into the 200 Hz tick. Pure logic, no Arduino calls except
// micros() — pin reads happen in main.cpp and feed in via update().
//
// Latching rule (Phase 1 spec, BOM §"safety chain"): once E-stop is pressed
// or battery_low debounce trips, the master torque-enable flag drops and
// stays dropped until an explicit clear signal arrives (e.g. /safety_clear
// topic on Jetson side, or power cycle). This prevents a glitchy GPIO from
// re-arming the servos mid-fault.

#pragma once

#include <Arduino.h>

namespace nova {

enum SafetyState : uint8_t {
  SAFETY_NORMAL              = 0,
  SAFETY_ESTOP_LATCHED       = 1,
  SAFETY_BATTERY_LOW_LATCHED = 2,
  SAFETY_FAULT_OTHER         = 3,   // reserved for future faults (bus, INA, etc.)
};

class SafetyFSM {
 public:
  // Battery-low debounce: N consecutive ticks of HIGH on the comparator
  // before we latch. At 200 Hz tick, 10 samples = 50 ms — long enough to
  // ride out a single capacitive glitch, short enough to react before the
  // 12.4 V MOSFET hard-cutoff fires.
  static constexpr uint8_t BATT_LOW_DEBOUNCE_TICKS = 10;

  void update(bool estop_pressed_now, bool batt_low_now) {
    // E-stop trips immediately, no debounce (mechanical switch already
    // contact-bounce-clean from the BOM v3.4 wiring).
    if (estop_pressed_now && state_ == SAFETY_NORMAL) {
      state_ = SAFETY_ESTOP_LATCHED;
      transition_us_ = micros();
    }

    // Battery-low: debounced
    if (batt_low_now) {
      if (batt_low_count_ < 0xFF) batt_low_count_++;
    } else {
      batt_low_count_ = 0;
    }
    if (batt_low_count_ >= BATT_LOW_DEBOUNCE_TICKS && state_ == SAFETY_NORMAL) {
      state_ = SAFETY_BATTERY_LOW_LATCHED;
      transition_us_ = micros();
    }

    // Mirror latest raw signals for telemetry — the published /estop and
    // /battery_low topics surface the raw GPIO, not the latched state, so
    // a host operator can see when the source signal is back to clear.
    estop_raw_ = estop_pressed_now;
    batt_low_raw_ = batt_low_now;
  }

  // Clear latched faults — only valid when underlying signals are no
  // longer asserted. Returns true if a clear actually happened.
  bool clear() {
    if (state_ == SAFETY_NORMAL) return false;
    if (estop_raw_)    return false;       // refuse while E-stop still held
    if (batt_low_raw_) return false;       // refuse while battery still low
    state_ = SAFETY_NORMAL;
    batt_low_count_ = 0;
    transition_us_ = micros();
    return true;
  }

  SafetyState state() const          { return state_; }
  bool motion_enabled() const        { return state_ == SAFETY_NORMAL; }
  uint32_t time_since_transition_us() const { return micros() - transition_us_; }

 private:
  SafetyState state_ = SAFETY_NORMAL;
  uint8_t  batt_low_count_ = 0;
  bool     estop_raw_ = false;
  bool     batt_low_raw_ = false;
  uint32_t transition_us_ = 0;
};

}  // namespace nova
