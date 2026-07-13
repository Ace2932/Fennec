// Native unit tests for safety_state.h — the E-stop / battery-low / overload
// safety FSM. Pure logic (only micros(), shimmed by test/mock_arduino).
// Host-run: pio test -e native.
#include <unity.h>
#include "safety_state.h"

using namespace nova;

void setUp() { mock_micros() = 0; }
void tearDown() {}

// ---- initial state ----
static void test_starts_normal_motion_enabled() {
  SafetyFSM fsm;
  TEST_ASSERT_EQUAL(SAFETY_NORMAL, fsm.state());
  TEST_ASSERT_TRUE(fsm.motion_enabled());
}

// ---- E-stop latches immediately, no debounce ----
static void test_estop_latches_on_first_tick() {
  SafetyFSM fsm;
  fsm.update(/*estop=*/true, /*batt_low=*/false);
  TEST_ASSERT_EQUAL(SAFETY_ESTOP_LATCHED, fsm.state());
  TEST_ASSERT_FALSE(fsm.motion_enabled());
}

static void test_estop_stays_latched_after_release() {
  SafetyFSM fsm;
  fsm.update(true, false);
  fsm.update(false, false);          // released, but must remain latched
  fsm.update(false, false);
  TEST_ASSERT_EQUAL(SAFETY_ESTOP_LATCHED, fsm.state());
  TEST_ASSERT_FALSE(fsm.motion_enabled());
}

// ---- battery-low debounce: needs BATT_LOW_DEBOUNCE_TICKS consecutive ----
static void test_battery_low_needs_full_debounce() {
  SafetyFSM fsm;
  for (int i = 0; i < SafetyFSM::BATT_LOW_DEBOUNCE_TICKS - 1; i++) {
    fsm.update(false, true);
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, fsm.state());   // not yet
  }
  fsm.update(false, true);           // the Nth consecutive tick
  TEST_ASSERT_EQUAL(SAFETY_BATTERY_LOW_LATCHED, fsm.state());
  TEST_ASSERT_FALSE(fsm.motion_enabled());
}

static void test_battery_glitch_resets_debounce() {
  SafetyFSM fsm;
  for (int i = 0; i < SafetyFSM::BATT_LOW_DEBOUNCE_TICKS - 1; i++)
    fsm.update(false, true);
  fsm.update(false, false);          // one clear sample resets the counter
  for (int i = 0; i < SafetyFSM::BATT_LOW_DEBOUNCE_TICKS - 1; i++) {
    fsm.update(false, true);
    TEST_ASSERT_EQUAL(SAFETY_NORMAL, fsm.state());   // count restarted
  }
  fsm.update(false, true);
  TEST_ASSERT_EQUAL(SAFETY_BATTERY_LOW_LATCHED, fsm.state());
}

// ---- overload trip ----
static void test_trip_overload_latches_from_normal() {
  SafetyFSM fsm;
  fsm.trip_overload();
  TEST_ASSERT_EQUAL(SAFETY_FAULT_OTHER, fsm.state());
  TEST_ASSERT_FALSE(fsm.motion_enabled());
}

static void test_trip_overload_does_not_override_estop() {
  SafetyFSM fsm;
  fsm.update(true, false);           // E-stop latched
  fsm.trip_overload();               // must NOT change an already-latched state
  TEST_ASSERT_EQUAL(SAFETY_ESTOP_LATCHED, fsm.state());
}

// ---- E-stop wins over battery in the same tick ----
static void test_estop_priority_over_battery_same_tick() {
  SafetyFSM fsm;
  // pre-load the battery counter to the brink, then assert both at once
  for (int i = 0; i < SafetyFSM::BATT_LOW_DEBOUNCE_TICKS - 1; i++)
    fsm.update(false, true);
  fsm.update(true, true);            // estop + battery-latch-eligible together
  TEST_ASSERT_EQUAL(SAFETY_ESTOP_LATCHED, fsm.state());   // estop, not battery
}

// ---- clear() refusal rules ----
static void test_clear_refused_while_estop_held() {
  SafetyFSM fsm;
  fsm.update(true, false);
  TEST_ASSERT_FALSE(fsm.clear());    // raw E-stop still asserted
  TEST_ASSERT_EQUAL(SAFETY_ESTOP_LATCHED, fsm.state());
}

static void test_clear_succeeds_after_estop_released() {
  SafetyFSM fsm;
  fsm.update(true, false);
  fsm.update(false, false);          // release raw signal (still latched)
  TEST_ASSERT_TRUE(fsm.clear());
  TEST_ASSERT_EQUAL(SAFETY_NORMAL, fsm.state());
  TEST_ASSERT_TRUE(fsm.motion_enabled());
}

static void test_clear_refused_while_battery_still_low() {
  SafetyFSM fsm;
  for (int i = 0; i < SafetyFSM::BATT_LOW_DEBOUNCE_TICKS; i++)
    fsm.update(false, true);
  TEST_ASSERT_EQUAL(SAFETY_BATTERY_LOW_LATCHED, fsm.state());
  TEST_ASSERT_FALSE(fsm.clear());    // batt_low_raw still asserted
}

static void test_clear_from_normal_returns_false() {
  SafetyFSM fsm;
  TEST_ASSERT_FALSE(fsm.clear());
}

static void test_clear_resets_battery_counter() {
  SafetyFSM fsm;
  for (int i = 0; i < SafetyFSM::BATT_LOW_DEBOUNCE_TICKS; i++)
    fsm.update(false, true);
  fsm.update(false, false);          // battery back to clear
  TEST_ASSERT_TRUE(fsm.clear());
  // after clear, a single low tick must not instantly re-latch (counter reset)
  fsm.update(false, true);
  TEST_ASSERT_EQUAL(SAFETY_NORMAL, fsm.state());
}

// ---- transition timestamp uses the (mocked) clock ----
static void test_time_since_transition_tracks_clock() {
  SafetyFSM fsm;
  mock_micros() = 1000;
  fsm.update(true, false);           // latch stamps transition_us_ = 1000
  mock_micros() = 3500;
  TEST_ASSERT_EQUAL_UINT32(2500, fsm.time_since_transition_us());
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_starts_normal_motion_enabled);
  RUN_TEST(test_estop_latches_on_first_tick);
  RUN_TEST(test_estop_stays_latched_after_release);
  RUN_TEST(test_battery_low_needs_full_debounce);
  RUN_TEST(test_battery_glitch_resets_debounce);
  RUN_TEST(test_trip_overload_latches_from_normal);
  RUN_TEST(test_trip_overload_does_not_override_estop);
  RUN_TEST(test_estop_priority_over_battery_same_tick);
  RUN_TEST(test_clear_refused_while_estop_held);
  RUN_TEST(test_clear_succeeds_after_estop_released);
  RUN_TEST(test_clear_refused_while_battery_still_low);
  RUN_TEST(test_clear_from_normal_returns_false);
  RUN_TEST(test_clear_resets_battery_counter);
  RUN_TEST(test_time_since_transition_tracks_clock);
  return UNITY_END();
}
