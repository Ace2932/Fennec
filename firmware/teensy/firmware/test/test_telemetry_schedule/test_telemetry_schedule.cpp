// Native test for telemetry_schedule.h (#358 slice 2): the main loop's rate
// plumbing, run on a simulated millisecond clock.
//
// The unit under test is the RATE each consumer sees, not the helpers' return
// values in isolation — #345 (/imu at 1 Hz into a 50 Hz policy) had every
// individual line correct and the rate wrong. So the core test drives a model
// of loop() for 10 simulated seconds, with the same structure main.cpp has:
// per-tick work inside `if (pending)`, per-rate gates outside it, evaluated on
// every loop spin.

#include <unity.h>
#include <stdint.h>

#include "telemetry_schedule.h"

using namespace nova;

void setUp(void) {}
void tearDown(void) {}

// Shipping build values that live in main.cpp / platformio.ini, not the header.
static constexpr uint32_t LOOP_HZ = 200;       // -D NOVA_LOOP_HZ=200
static constexpr uint8_t  JOINTS = 12;         // NOVA_JOINT_COUNT
static constexpr uint8_t  RAILS_L2 = 4;        // INA226_RAIL_COUNT with -D NOVA_INA226_L2
static constexpr uint8_t  RAILS_NO_L2 = 3;

// Stand-in for Teensy's elapsedMillis: reads as now - start, assigning v sets
// start = now - v. Same two operators the firmware's gates use.
static uint32_t g_now_ms = 0;
struct FakeElapsedMillis {
  uint32_t start = 0;
  operator uint32_t() const { return g_now_ms - start; }
  FakeElapsedMillis& operator=(uint32_t v) { start = g_now_ms - v; return *this; }
};

struct Counts {
  uint32_t joint_states = 0, broadcast = 0;
  uint32_t heartbeat = 0, fw_version = 0, imu = 0, servo_health = 0,
           power_rails = 0, stats = 0;
  uint32_t servo_polls[JOINTS] = {0};
  uint32_t rail_polls[RAILS_L2] = {0};
};

// loop() for `seconds`, one spin per simulated ms; the tick ISR fires every
// 1000/LOOP_HZ ms. Mirrors main.cpp's order and gating.
static Counts run_loop(uint32_t seconds, uint8_t rails) {
  Counts c;
  g_now_ms = 0;
  FakeElapsedMillis heartbeat_ms, stats_ms, power_rails_ms, servo_health_ms, imu_ms;
  uint8_t servo_rr_idx = 0, ina226_rr_idx = 0, cmd_decimate_count = 0;
  uint32_t fw_pub_count = 0;
  const uint32_t tick_ms = 1000 / LOOP_HZ;
  for (g_now_ms = 1; g_now_ms <= seconds * 1000; g_now_ms++) {
    if (g_now_ms % tick_ms == 0) {                 // tick_pending
      for (uint8_t pk = 0; pk < NOVA_POLLS_PER_TICK; pk++) {
        c.servo_polls[servo_rr_idx]++;
        servo_rr_idx = rr_next(servo_rr_idx, JOINTS);
      }
      if (decimate(cmd_decimate_count, CMD_BROADCAST_DECIMATE)) c.broadcast++;
      c.rail_polls[ina226_rr_idx]++;
      ina226_rr_idx = rr_next(ina226_rr_idx, rails);
      c.joint_states++;                            // published every tick
    }
    if (rate_due(heartbeat_ms, HEARTBEAT_PERIOD_MS)) {
      c.heartbeat++;
      if (every_nth_from_first(fw_pub_count, FW_VERSION_EVERY_N_HEARTBEATS)) c.fw_version++;
    }
    if (rate_due(imu_ms, IMU_PERIOD_MS)) c.imu++;
    if (rate_due(servo_health_ms, SERVO_HEALTH_PERIOD_MS)) c.servo_health++;
    if (rate_due(power_rails_ms, POWER_RAILS_PERIOD_MS)) c.power_rails++;
    if (rate_due(stats_ms, STATS_PERIOD_MS)) c.stats++;
  }
  return c;
}

void test_each_topic_publishes_at_its_documented_rate(void) {
  const Counts c = run_loop(10, RAILS_L2);
  // Per-10-s counts -> Hz. These are the README topic table's numbers.
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(2000, c.joint_states, "/joint_states != 200 Hz");
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(1000, c.imu,          "/imu != 100 Hz (#345)");
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(100,  c.power_rails,  "/power_rails != 10 Hz");
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(50,   c.servo_health, "/servo_voltage,/servo_temperature != 5 Hz");
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(10,   c.heartbeat,    "heartbeat block != 1 Hz");
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(10,   c.stats,        "/loop_* stats != 1 Hz");
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(1,    c.fw_version,   "/firmware_version != every 10 s");
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(1000, c.broadcast,    "command SYNC_WRITE != 100 Hz");
}

void test_imu_outpaces_the_policy_that_consumes_it(void) {
  // #345's invariant stated against the CONSUMER, so it survives a deliberate
  // rate change: policy_node reads /imu at control_hz = 50 and must never be
  // handed the same sample twice; and the chip is only read once per tick, so
  // a rate above LOOP_HZ would re-publish stale state.
  const Counts c = run_loop(1, RAILS_L2);
  TEST_ASSERT_GREATER_OR_EQUAL_UINT32_MESSAGE(2 * 50, c.imu,
      "/imu below 2x policy control_hz (#345: it was 1 Hz inside the heartbeat block)");
  TEST_ASSERT_LESS_OR_EQUAL_UINT32(LOOP_HZ, c.imu);
}

void test_every_servo_is_polled_at_50_hz_none_skipped(void) {
  const Counts c = run_loop(10, RAILS_L2);
  for (int i = 0; i < JOINTS; i++)
    TEST_ASSERT_EQUAL_UINT32_MESSAGE(500, c.servo_polls[i],
        "a joint's feedback rate != 200*3/12 = 50 Hz");
}

void test_every_rail_is_polled_equally_with_and_without_l2(void) {
  const Counts four = run_loop(10, RAILS_L2);
  for (int r = 0; r < RAILS_L2; r++) TEST_ASSERT_EQUAL_UINT32(500, four.rail_polls[r]);
  const Counts three = run_loop(3, RAILS_NO_L2);   // 600 ticks: 200 each
  for (int r = 0; r < RAILS_NO_L2; r++) TEST_ASSERT_EQUAL_UINT32(200, three.rail_polls[r]);
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(0, three.rail_polls[3], "rr index escaped a 3-rail build");
}

void test_firmware_version_goes_out_on_the_FIRST_heartbeat(void) {
  // A reconnecting host must not wait up to 10 s for identity.
  uint32_t n = 0;
  TEST_ASSERT_TRUE(every_nth_from_first(n, FW_VERSION_EVERY_N_HEARTBEATS));
  for (int i = 1; i < 10; i++) TEST_ASSERT_FALSE(every_nth_from_first(n, FW_VERSION_EVERY_N_HEARTBEATS));
  TEST_ASSERT_TRUE(every_nth_from_first(n, FW_VERSION_EVERY_N_HEARTBEATS));
}

void test_command_broadcast_skips_the_FIRST_tick(void) {
  // Opposite phase to firmware_version, and that is the pre-extraction
  // behaviour: count++ then compare, so the first broadcast is tick 2.
  uint8_t n = 0;
  TEST_ASSERT_FALSE(decimate(n, CMD_BROADCAST_DECIMATE));
  TEST_ASSERT_TRUE(decimate(n, CMD_BROADCAST_DECIMATE));
  TEST_ASSERT_FALSE(decimate(n, CMD_BROADCAST_DECIMATE));
}

void test_a_late_loop_stretches_the_period_rather_than_bursting(void) {
  // elapsed = 0 restarts the window from NOW. A 25 ms stall past a 10 ms
  // deadline yields ONE publish, then the next is 10 ms after that — not a
  // catch-up burst of two back-to-back.
  g_now_ms = 0;
  FakeElapsedMillis e;
  g_now_ms = 35;
  TEST_ASSERT_TRUE(rate_due(e, IMU_PERIOD_MS));
  g_now_ms = 36;
  TEST_ASSERT_FALSE(rate_due(e, IMU_PERIOD_MS));
  g_now_ms = 44;
  TEST_ASSERT_FALSE(rate_due(e, IMU_PERIOD_MS));
  g_now_ms = 45;
  TEST_ASSERT_TRUE(rate_due(e, IMU_PERIOD_MS));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_each_topic_publishes_at_its_documented_rate);
  RUN_TEST(test_imu_outpaces_the_policy_that_consumes_it);
  RUN_TEST(test_every_servo_is_polled_at_50_hz_none_skipped);
  RUN_TEST(test_every_rail_is_polled_equally_with_and_without_l2);
  RUN_TEST(test_firmware_version_goes_out_on_the_FIRST_heartbeat);
  RUN_TEST(test_command_broadcast_skips_the_FIRST_tick);
  RUN_TEST(test_a_late_loop_stretches_the_period_rather_than_bursting);
  return UNITY_END();
}
