// Native unit test for the redefined stall guard (#428, stall_guard.h).
//
// Scenarios mirror what the joint actually does, sampled at the per-joint poll
// rate (each servo is polled at 50 Hz, so one update() = 20 ms):
//   - a loaded STANCE leg: ~95 % duty, holding within a few counts of its goal
//     -> must NEVER trip (the old rule tripped it after 5 polls = 100 ms)
//   - a JAM: ~95 % duty, goal far away, position frozen -> trips at `persist`
//   - a hard SWING: high duty, far from goal, but moving -> never trips
//   - OVERTEMP trips regardless of motion (unchanged behaviour)
//   - no goal yet -> high load alone counts (legacy, conservative)
// plus a DIFFERENTIAL sweep: with the jam conditions disabled the new code must
// reproduce the old inline rule exactly.

#include <unity.h>
#include <stdint.h>

#include "stall_guard.h"

using namespace nova;

static const StallGuardConfig CFG = {900, 60, 3, 70, 5};   // main.cpp defaults

void setUp(void) {}
void tearDown(void) {}

void test_loaded_stance_never_trips(void) {
  StallJointState s;
  for (int i = 0; i < 1000; i++) {                         // 20 s of stance at 95 % duty
    uint16_t pos = 2048 + (i % 3) - 1;                     // +-1 count jitter
    TEST_ASSERT_FALSE(stall_update(CFG, s, 950, 40, pos, 2060));   // 12 counts off goal
  }
}

void test_old_rule_would_have_tripped_the_same_stance(void) {
  // The reason for the change, pinned: same stance, legacy rule (load only).
  StallJointState s;
  StallGuardConfig legacy = CFG;
  bool tripped = false;
  for (int i = 0; i < 10 && !tripped; i++)
    tripped = stall_update(legacy, s, 950, 40, 2048, STALL_GOAL_UNKNOWN);
  TEST_ASSERT_TRUE(tripped);
}

void test_jam_trips_at_persist(void) {
  StallJointState s;
  int trip_at = -1;
  for (int i = 0; i < 20; i++) {
    if (stall_update(CFG, s, 950, 40, 1800, 2200) && trip_at < 0) trip_at = i;
  }
  // first poll has no prev_pos -> counts via the legacy rule; then JAM polls.
  TEST_ASSERT_EQUAL_INT(CFG.persist - 1, trip_at);
}

void test_hard_swing_is_not_a_jam(void) {
  StallJointState s;
  uint16_t pos = 1800;
  for (int i = 0; i < 50; i++) {
    pos += 8;                                              // moving ~0.12 rad/s-ish per poll
    TEST_ASSERT_FALSE(stall_update(CFG, s, 980, 40, pos, (uint16_t)(pos + 300)));
  }
}

void test_one_good_poll_resets_the_count(void) {
  StallJointState s;
  for (int i = 0; i < CFG.persist - 1; i++) stall_update(CFG, s, 950, 40, 1800, 2200);
  stall_update(CFG, s, 100, 40, 1800, 2200);               // load drops for one poll
  for (int i = 0; i < CFG.persist - 1; i++)
    TEST_ASSERT_FALSE(stall_update(CFG, s, 950, 40, 1800, 2200));
  TEST_ASSERT_TRUE(stall_update(CFG, s, 950, 40, 1800, 2200));
}

void test_overtemp_trips_even_while_moving(void) {
  StallJointState s;
  uint16_t pos = 1000;
  bool tripped = false;
  for (int i = 0; i < CFG.persist; i++) { pos += 50; tripped = stall_update(CFG, s, 100, 75, pos, pos); }
  TEST_ASSERT_TRUE(tripped);
}

void test_no_goal_falls_back_to_legacy_load_rule(void) {
  StallJointState s;
  bool tripped = false;
  for (int i = 0; i < CFG.persist; i++) tripped = stall_update(CFG, s, 950, 40, 2048, STALL_GOAL_UNKNOWN);
  TEST_ASSERT_TRUE(tripped);
}

void test_classify_thresholds_are_inclusive(void) {
  // at exactly err_counts off goal and exactly still_counts of motion -> JAM
  TEST_ASSERT_EQUAL(StallReason::JAM, stall_classify(CFG, 900, 40, 2000, 2003, 2060));
  // one count closer to goal -> not a jam
  TEST_ASSERT_EQUAL(StallReason::NONE, stall_classify(CFG, 900, 40, 2000, 2003, 2059));
  // one more count of motion -> not a jam
  TEST_ASSERT_EQUAL(StallReason::NONE, stall_classify(CFG, 900, 40, 2000, 2004, 2060));
  // load one below threshold -> nothing
  TEST_ASSERT_EQUAL(StallReason::NONE, stall_classify(CFG, 899, 40, 2000, 2000, 2400));
}

// --- DIFFERENTIAL: jam conditions disabled == the old inline rule, exactly ------
// Old main.cpp: bad = load >= 900 || temp >= 70; count++ else count=0; trip at >= 5.
static bool reference_old_rule_poll(uint8_t& count, uint16_t load, uint8_t temp) {
  bool bad = (load >= 900) || (temp >= 70);
  if (bad) { if (count < 0xFF) count++; } else { count = 0; }
  return count >= 5;
}

void test_differential_legacy_equivalence(void) {
  StallGuardConfig legacy = {900, 0, 0xFFFF, 70, 5};       // err 0, still "any" -> load-only
  uint32_t lcg = 12345;
  StallJointState s;
  uint8_t ref_count = 0;
  for (int i = 0; i < 200000; i++) {
    lcg = lcg * 1103515245u + 12345u;
    uint16_t load = (uint16_t)((lcg >> 8) % 1001);
    uint8_t temp  = (uint8_t)((lcg >> 20) % 90);
    uint16_t pos  = (uint16_t)((lcg >> 4) % 4096);
    uint16_t goal = (uint16_t)((lcg >> 12) % 4096);
    bool a = stall_update(legacy, s, load, temp, pos, goal);
    bool b = reference_old_rule_poll(ref_count, load, temp);
    if (a != b) TEST_FAIL_MESSAGE("new guard with jam conditions disabled diverged from the old rule");
  }
}

int main(int argc, char** argv) {
  UNITY_BEGIN();
  RUN_TEST(test_loaded_stance_never_trips);
  RUN_TEST(test_old_rule_would_have_tripped_the_same_stance);
  RUN_TEST(test_jam_trips_at_persist);
  RUN_TEST(test_hard_swing_is_not_a_jam);
  RUN_TEST(test_one_good_poll_resets_the_count);
  RUN_TEST(test_overtemp_trips_even_while_moving);
  RUN_TEST(test_no_goal_falls_back_to_legacy_load_rule);
  RUN_TEST(test_classify_thresholds_are_inclusive);
  RUN_TEST(test_differential_legacy_equivalence);
  return UNITY_END();
}
