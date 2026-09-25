// telemetry_schedule.h — the main loop's rate plumbing: per-rate publish
// gates, the command-broadcast decimator, the firmware_version sub-rate, and
// the round-robin index advance for servo and INA226 polling. Extracted from
// main.cpp (#358 slice 2), behaviour-preserving: every function below is the
// expression main.cpp had inline, moved, not rewritten.
//
// WHY THIS IS WORTH A HEADER. The rates are decisions with consumers on the
// other end, and main.cpp is in no native build, so a wrong rate was invisible
// until hardware. #345 is the record: /imu sat inside the 1 Hz heartbeat block
// while policy_node consumes it at control_hz = 50 — the policy would have seen
// the same attitude for 50 ticks, then a jump. test/test_telemetry_schedule
// runs this file's gates on a simulated clock and pins each topic's rate.
//
// WHAT DOES NOT LIVE HERE. The publishes themselves (micro-ROS globals) and
// the clock: rate_due() takes the caller's elapsed-time object, which is
// Teensy's elapsedMillis on the board and a fake in the test.
#pragma once

#include <stdint.h>

namespace nova {

// ---- per-rate publish blocks (ms, gated in loop() by rate_due) -------------
constexpr uint32_t HEARTBEAT_PERIOD_MS    = 1000;  // 1 Hz: LED, heartbeat, counters, late-join refresh
constexpr uint32_t STATS_PERIOD_MS        = 1000;  // 1 Hz: loop timing histograms
constexpr uint32_t IMU_PERIOD_MS          = 10;    // 100 Hz — see note below
constexpr uint32_t POWER_RAILS_PERIOD_MS  = 100;   // 10 Hz — matches Phase 1 spec
constexpr uint32_t SERVO_HEALTH_PERIOD_MS = 200;   // 5 Hz — voltage + temperature
// IMU: 100 Hz. NOT a free choice: policy_node runs control_hz = 50 (policy_node.py:185)
// and consumes gyro + projected gravity as observation dims 0..5, so the IMU must
// publish at least at control rate; 2x gives margin for scheduling jitter without
// the policy ever reusing a sample. poll_imu() already reads the chip and updates
// the tilt filter every tick at NOVA_LOOP_HZ = 200, so every published sample here
// is fresh -- this rate only controls how often that fresh state leaves the board.

// firmware_version rides the heartbeat: 1 in 10 -> every 10 s, first one on
// the first heartbeat so a reconnecting host picks it up without a restart.
constexpr uint32_t FW_VERSION_EVERY_N_HEARTBEATS = 10;

// ---- per-tick work (counted in NOVA_LOOP_HZ ticks) --------------------------
// Command SYNC_WRITE every CMD_BROADCAST_DECIMATE ticks: 200 Hz / 2 = 100 Hz.
// (backlog #21 bus-schedule rework, 2026-07-06: was 5 = 40 Hz. Gait wants
// >= 100 Hz command; NOVA_SLEW_MAX_DELTA scales with the period.)
constexpr uint8_t CMD_BROADCAST_DECIMATE = 2;
// Feedback polls per 5 ms tick (per-joint rate = 200*N/12 Hz): 3 -> 50 Hz
#ifndef NOVA_POLLS_PER_TICK
#define NOVA_POLLS_PER_TICK 3
#endif

//: Per-rate block gate. True at most once per `period_ms`, restarting the
//: window from NOW (elapsed = 0), not from the missed deadline — so a late
//: loop stretches the next period rather than bursting to catch up.
template <class Elapsed>
inline bool rate_due(Elapsed& elapsed, uint32_t period_ms) {
  if (elapsed >= period_ms) {
    elapsed = 0;
    return true;
  }
  return false;
}

//: Fires on the Nth call, then restarts (the command-broadcast decimator).
inline bool decimate(uint8_t& count, uint8_t n) {
  count++;
  if (count < n) return false;
  count = 0;
  return true;
}

//: Fires on the FIRST call and every Nth after (firmware_version's phase).
inline bool every_nth_from_first(uint32_t& count, uint32_t n) {
  return (count++ % n) == 0;
}

//: Round-robin advance: 0..n-1, wrapping. Servo poll and INA226 poll both.
inline uint8_t rr_next(uint8_t idx, uint8_t n) {
  return (uint8_t)((idx + 1) % n);
}

}  // namespace nova
