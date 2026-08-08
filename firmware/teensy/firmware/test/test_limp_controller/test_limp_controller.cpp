// Native unit tests for limp_controller.h — the soft-fault controlled-limp
// state machine + per-fault-type policy (#145). Pure logic (only micros(),
// shimmed by test/mock_arduino). Host-run: pio test -e native.
#include <unity.h>
#include "limp_controller.h"
#include "safety_state.h"

using namespace nova;

void setUp() { mock_micros() = 0; }
void tearDown() {}

// ---- fault_gets_controlled_limp: the per-fault-type policy ----------------

static void test_battery_low_GETS_controlled_limp() {
  TEST_ASSERT_TRUE(fault_gets_controlled_limp(SAFETY_BATTERY_LOW_LATCHED));
}

// NEGATIVE CONTROL #1 — a human pressing E-stop must NEVER get a delayed
// release, no matter how tempting a "soft landing" sounds.
static void test_estop_NEVER_gets_controlled_limp() {
  TEST_ASSERT_FALSE(fault_gets_controlled_limp(SAFETY_ESTOP_LATCHED));
}

// NEGATIVE CONTROL #2 — overload/stall is already the hazard the limp pose
// would be commanding the fleet further into; must stay instant.
static void test_overload_NEVER_gets_controlled_limp() {
  TEST_ASSERT_FALSE(fault_gets_controlled_limp(SAFETY_FAULT_OTHER));
}

static void test_normal_is_not_a_fault_to_limp_from() {
  TEST_ASSERT_FALSE(fault_gets_controlled_limp(SAFETY_NORMAL));
}

// ---- LimpController sequencing ---------------------------------------------

static void test_starts_inactive() {
  LimpController lc;
  TEST_ASSERT_FALSE(lc.active());
}

static void test_start_activates_and_holds_the_pose() {
  LimpController lc;
  uint16_t pose[LIMP_JOINT_COUNT];
  for (size_t i = 0; i < LIMP_JOINT_COUNT; i++) pose[i] = (uint16_t)(1000 + i);
  lc.start(pose, /*now_us=*/0);
  TEST_ASSERT_TRUE(lc.active());
  for (size_t i = 0; i < LIMP_JOINT_COUNT; i++) {
    TEST_ASSERT_EQUAL_UINT16(1000 + i, lc.target()[i]);
  }
}

static void test_tick_before_hold_elapses_stays_active_and_returns_false() {
  LimpController lc;
  uint16_t pose[LIMP_JOINT_COUNT] = {0};
  lc.start(pose, 0);
  TEST_ASSERT_FALSE(lc.tick(LIMP_HOLD_US - 1));
  TEST_ASSERT_TRUE(lc.active());
}

static void test_tick_at_exactly_the_hold_window_fires_once() {
  LimpController lc;
  uint16_t pose[LIMP_JOINT_COUNT] = {0};
  lc.start(pose, 0);
  TEST_ASSERT_TRUE(lc.tick(LIMP_HOLD_US));
  TEST_ASSERT_FALSE(lc.active());
  // NEGATIVE CONTROL — a stray second call must not re-fire (no double
  // torque-release side effect if the caller calls tick() again by mistake).
  TEST_ASSERT_FALSE(lc.tick(LIMP_HOLD_US + 1));
}

static void test_tick_on_an_inactive_controller_is_a_harmless_noop() {
  LimpController lc;
  TEST_ASSERT_FALSE(lc.tick(999999999UL));
  TEST_ASSERT_FALSE(lc.active());
}

static void test_reset_aborts_an_in_progress_limp() {
  LimpController lc;
  uint16_t pose[LIMP_JOINT_COUNT] = {0};
  lc.start(pose, 0);
  lc.reset();
  TEST_ASSERT_FALSE(lc.active());
  // aborted early -- the hold elapsing later must not fire
  TEST_ASSERT_FALSE(lc.tick(LIMP_HOLD_US + 1));
}

static void test_start_again_after_reset_begins_a_fresh_window() {
  LimpController lc;
  uint16_t pose[LIMP_JOINT_COUNT] = {0};
  lc.start(pose, 0);
  mock_micros() = 500000;         // 0.5 s in
  lc.reset();                     // aborted (e.g. E-stop)
  lc.start(pose, 500000);         // a fresh limp starts later
  TEST_ASSERT_FALSE(lc.tick(500000 + LIMP_HOLD_US - 1));
  TEST_ASSERT_TRUE(lc.tick(500000 + LIMP_HOLD_US));
}

static void test_clock_wraparound_is_handled_like_SafetyFSM() {
  // Same unsigned-subtraction pattern as SafetyFSM::time_since_transition_us
  // — start just before a uint32 wrap, elapse across it.
  LimpController lc;
  uint16_t pose[LIMP_JOINT_COUNT] = {0};
  const uint32_t start = 0xFFFFFFFFu - 1000;
  lc.start(pose, start);
  TEST_ASSERT_FALSE(lc.tick(start + LIMP_HOLD_US - 1));  // wraps past 0
  TEST_ASSERT_TRUE(lc.tick(start + LIMP_HOLD_US));
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_battery_low_GETS_controlled_limp);
  RUN_TEST(test_estop_NEVER_gets_controlled_limp);
  RUN_TEST(test_overload_NEVER_gets_controlled_limp);
  RUN_TEST(test_normal_is_not_a_fault_to_limp_from);
  RUN_TEST(test_starts_inactive);
  RUN_TEST(test_start_activates_and_holds_the_pose);
  RUN_TEST(test_tick_before_hold_elapses_stays_active_and_returns_false);
  RUN_TEST(test_tick_at_exactly_the_hold_window_fires_once);
  RUN_TEST(test_tick_on_an_inactive_controller_is_a_harmless_noop);
  RUN_TEST(test_reset_aborts_an_in_progress_limp);
  RUN_TEST(test_start_again_after_reset_begins_a_fresh_window);
  RUN_TEST(test_clock_wraparound_is_handled_like_SafetyFSM);
  return UNITY_END();
}
