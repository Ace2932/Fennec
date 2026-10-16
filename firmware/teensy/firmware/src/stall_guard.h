// Per-joint stall / overtemp guard — extracted from main.cpp and REDEFINED
// (#428, 2026-09-26).
//
// WHAT IT PROTECTS. A jammed joint drives full stall current at a goal it can
// never reach, indefinitely: it cooks the servo and can brown out the hip rail
// (4 x hip stall ~ 20 A > buck). On a trip the caller LIMPs the whole fleet.
//
// WHY THE RULE CHANGED. The old rule was "load >= 900 for N consecutive polls".
// Load is the servo's PWM DUTY, not a jam detector: a trot's two-legs-down
// stance needs ~82 % of knee stall statically (sim probe_stance_torque), so in
// the gait-study sims every walking policy at TORQUE_LIMIT 1000 held some joint
// at >= 90 % duty for ~0.5 s per episode, and the old guard would have limped
// the robot in 100 % of episodes. Training policies to stay under it cost step
// climbing (3 cm success 100 % -> 9 %) and still never got the runs under 100 ms.
//
// A JAM is not "working hard". It is "working hard AND far from where it was
// told to be AND not getting there". A loaded stance leg sits near its goal
// (small error); a swinging leg is moving; neither is a jam. So a poll is BAD
// when:
//     load >= load_raw  AND  |goal - pos| >= err_counts  AND  |pos - prev| <= still_counts
// or, unchanged from before, when the servo is at/over its temperature limit.
// With no reference yet (no commanded goal, or first poll) high load alone
// still counts — the conservative legacy rule, never weaker than before.
//
// THRESHOLDS ARE UNVERIFIED ON HARDWARE. err_counts/still_counts come from the
// sim's position servo (kp 35 N*m/rad -> ~28 counts of deflection at 1.5 N*m).
// Bench before trusting: steady |goal - pos| of a leg held at ~90 % duty under a
// static load (must stay well under err_counts), and a hand-blocked horn (must
// trip). All build-flag tunable in main.cpp.

#pragma once

#include <stdint.h>

namespace nova {

//: Goal not known (nothing commanded yet). Same value as SLEW_UNINIT.
constexpr uint16_t STALL_GOAL_UNKNOWN = 0xFFFF;
//: Previous position not known (first poll, or after a reset).
constexpr uint16_t STALL_POS_UNKNOWN = 0xFFFF;

struct StallGuardConfig {
  uint16_t load_raw;      //: load magnitude (0..1000) at/over which a joint is "working hard"
  uint16_t err_counts;    //: |goal - pos| at/over which it is "far from its goal"
  uint16_t still_counts;  //: |pos - prev_pos| per poll at/under which it is "not moving"
  uint8_t  overtemp_c;    //: temperature (C) at/over which the poll is bad regardless
  uint8_t  persist;       //: consecutive bad polls that trip
};

enum class StallReason : uint8_t { NONE, JAM, OVERTEMP, LOAD_NO_REFERENCE };

struct StallJointState {
  uint8_t  count    = 0;
  uint16_t prev_pos = STALL_POS_UNKNOWN;
};

inline uint16_t stall_absdiff(uint16_t a, uint16_t b) { return a > b ? a - b : b - a; }

//: Classify ONE poll of ONE joint. Pure; no state.
inline StallReason stall_classify(const StallGuardConfig& c, uint16_t load_mag,
                                  uint8_t temp_c, uint16_t pos, uint16_t prev_pos,
                                  uint16_t goal) {
  if (temp_c >= c.overtemp_c) return StallReason::OVERTEMP;
  if (load_mag < c.load_raw) return StallReason::NONE;
  if (goal == STALL_GOAL_UNKNOWN || prev_pos == STALL_POS_UNKNOWN)
    return StallReason::LOAD_NO_REFERENCE;   // legacy rule: high load alone
  bool far  = stall_absdiff(goal, pos) >= c.err_counts;
  bool still = stall_absdiff(pos, prev_pos) <= c.still_counts;
  return (far && still) ? StallReason::JAM : StallReason::NONE;
}

//: Advance one joint by one poll. Returns true while the joint is at/over the
//: persist threshold (the caller latches the fleet trip, as before).
inline bool stall_update(const StallGuardConfig& c, StallJointState& s,
                         uint16_t load_mag, uint8_t temp_c, uint16_t pos,
                         uint16_t goal) {
  StallReason r = stall_classify(c, load_mag, temp_c, pos, s.prev_pos, goal);
  s.prev_pos = pos;
  if (r == StallReason::NONE) {
    s.count = 0;
    return false;
  }
  if (s.count < 0xFF) s.count++;
  return s.count >= c.persist;
}

inline void stall_reset(StallJointState& s) {
  s.count = 0;
  s.prev_pos = STALL_POS_UNKNOWN;
}

}  // namespace nova
