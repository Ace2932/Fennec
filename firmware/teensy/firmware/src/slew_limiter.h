// Per-joint slew limiter — PASS 3 of the command pipeline.
//
// EXTRACTED FROM main.cpp 2026-08-14 (#358), behaviour-preserving. It was
// ~30 lines inline in broadcast_commands(), which meant the one piece of
// arithmetic standing between a step-jump command and a full-speed servo
// lurch could not be unit-tested at all: main.cpp is Arduino + micro-ROS and
// is in no native build.
//
// WHAT IT DOES. Each broadcast, every joint moves at most `max_delta` raw
// counts toward its target. At the default 20 counts per 10 ms broadcast
// (100 Hz) that is ~176 deg/s, so a host crash-and-restart at a far pose ramps
// in instead of slamming.
//
// THE ANTI-SNAP SEED is the subtle half (clean-movement lane 2026-07-06, PR
// #17). On the FIRST broadcast after boot or a fault clear there is no
// previous goal, and accepting the target verbatim made the servo jump from
// wherever it physically was to the target at its own max speed — the boot
// lurch, and the lurch after every E-stop clear. Seeding from the servo's
// polled PRESENT position instead makes the same rate limit apply to that
// first move. A servo that has never answered a poll keeps verbatim
// behaviour: nothing real moves on an absent servo, and refusing to command
// it would be worse.
//
// NOT A POSTURE GATE. This limits RATE only. It is deliberately unaware of
// the chassis envelope — and #280 is the record of why that matters: two
// joints slewing independently at one shared rate leave the safe set BETWEEN
// legal endpoints, which is why hfe_envelope.apply() runs again AFTER this
// pass on the values about to be written, not just before it.

#pragma once

#include <stddef.h>
#include <stdint.h>

namespace nova {

//: "No command issued yet" sentinel for a joint's last goal. Safe as a
//: sentinel because the STS3215 raw range is 0..4095, so 0xFFFF is not a
//: reachable goal — see test_the_sentinel_cannot_collide_with_a_real_goal.
constexpr uint16_t SLEW_UNINIT = 0xFFFF;

//: One joint, one broadcast. Returns the value to command now.
//:
//: `last_goal`   previous commanded value, or SLEW_UNINIT on the first tick
//: `present`     has this servo answered at least one telemetry poll?
//: `present_pos` its last polled raw position (only read when `present`)
inline uint16_t slew_step(uint16_t target, uint16_t last_goal, bool present,
                          uint16_t present_pos, uint16_t max_delta) {
  if (last_goal == SLEW_UNINIT) {
    if (!present) return target;      // absent servo — verbatim is harmless
    int32_t seeded = (int32_t)present_pos;
    int32_t delta = (int32_t)target - seeded;
    if (delta > (int32_t)max_delta) delta = (int32_t)max_delta;
    if (delta < -(int32_t)max_delta) delta = -(int32_t)max_delta;
    return (uint16_t)(seeded + delta);
  }
  int32_t delta = (int32_t)target - (int32_t)last_goal;
  if (delta > (int32_t)max_delta) delta = (int32_t)max_delta;
  if (delta < -(int32_t)max_delta) delta = -(int32_t)max_delta;
  return (uint16_t)((int32_t)last_goal + delta);
}

//: The whole PASS-3 loop: slew every joint and write back the bookkeeping.
//:
//: `last_goal` is updated in place — that write-back is load-bearing, because
//: PASS 4 may clamp `out` harder than max_delta and then re-syncs `last_goal`
//: so the NEXT tick ramps from what was actually written rather than from a
//: value that never reached a servo.
//:
//: `present_pos` is volatile: it is filled by the telemetry round-robin.
inline void slew_apply(const uint16_t* targets, uint16_t* last_goal,
                       uint16_t* out, size_t n,
                       const volatile uint16_t* present_pos,
                       uint16_t present_mask, uint16_t max_delta) {
  for (size_t i = 0; i < n; i++) {
    const bool present =
        (present_pos != nullptr) && ((present_mask & (uint16_t)(1u << i)) != 0);
    const uint16_t pos = present ? (uint16_t)present_pos[i] : (uint16_t)0;
    const uint16_t v = slew_step(targets[i], last_goal[i], present, pos, max_delta);
    last_goal[i] = v;
    out[i] = v;
  }
}

}  // namespace nova
