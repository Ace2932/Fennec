// Native unit tests for hfe_envelope.h — the posture-aware chassis backstop
// (#142). Pure logic, host-run: pio test -e native.
//
// These matter more than usual. The micro-ROS build cannot be compiled on a
// Mac (micro_ros_platformio needs the ROS dev toolchain), so the subscription
// and callback in main.cpp are not compile-verified off the Jetson. Everything
// that DECIDES anything lives here instead, where it can be tested properly.
#include <unity.h>

#include "hfe_envelope.h"

using namespace nova;

void setUp() {}
void tearDown() {}

// A well-formed 2-bucket table. Split at haa 2048, so:
//   bucket 0: haa    0..2048  -> hfe window [1000, 2000]
//   bucket 1: haa 2048..4095  -> hfe window [1500, 3000]
// Per leg the windows are offset by leg*10 so a test can tell the legs apart.
static size_t build(float* out, size_t n_buckets = 2, float leg_step = 10.0f) {
  out[0] = (float)n_buckets;
  size_t i = 1;
  for (size_t leg = 0; leg < HFE_ENV_LEGS; leg++) {
    for (size_t k = 0; k < n_buckets; k++) {
      const float span = 4095.0f / (float)n_buckets;
      out[i++] = (k == 0) ? 0.0f : span * (float)k;
      out[i++] = (k == n_buckets - 1) ? 4095.0f : span * (float)(k + 1);
      out[i++] = 1000.0f + 500.0f * (float)k + leg_step * (float)leg;
      out[i++] = 2000.0f + 1000.0f * (float)k + leg_step * (float)leg;
    }
  }
  return i;
}

// ---- acceptance -----------------------------------------------------------

static void test_wellformed_table_loads() {
  float buf[HFE_ENV_MAX_FLOATS];
  size_t n = build(buf);
  HfeEnvelope env;
  TEST_ASSERT_FALSE(env.active());
  TEST_ASSERT_TRUE(env.load(buf, n));
  TEST_ASSERT_TRUE(env.active());
  TEST_ASSERT_EQUAL_UINT8(2, env.buckets());
}

static void test_inactive_envelope_is_a_NO_OP() {
  // Wide open until the host publishes — homing must move joints outside ROM.
  HfeEnvelope env;
  uint16_t t[12];
  for (size_t i = 0; i < 12; i++) t[i] = (uint16_t)(100 * i);
  uint16_t before[12];
  for (size_t i = 0; i < 12; i++) before[i] = t[i];
  env.apply(t);
  for (size_t i = 0; i < 12; i++) TEST_ASSERT_EQUAL_UINT16(before[i], t[i]);
}

// ---- rejection: every fault must reject the WHOLE table --------------------

static void test_rejects_malformed_tables() {
  float buf[HFE_ENV_MAX_FLOATS];
  HfeEnvelope env;

  TEST_ASSERT_FALSE(env.load(nullptr, 10));
  TEST_ASSERT_FALSE(env.load(buf, 0));

  size_t n = build(buf);
  buf[0] = 0.0f;                                   // zero buckets
  TEST_ASSERT_FALSE(env.load(buf, n));

  n = build(buf);
  buf[0] = (float)(HFE_ENV_MAX_BUCKETS + 1);       // too many
  TEST_ASSERT_FALSE(env.load(buf, n));

  n = build(buf);
  TEST_ASSERT_FALSE(env.load(buf, n - 1));         // size disagrees with count

  n = build(buf);
  buf[3] = NAN;                                    // NaN anywhere
  TEST_ASSERT_FALSE(env.load(buf, n));

  n = build(buf);
  buf[3] = 5000.0f;                                // outside 0..4095
  TEST_ASSERT_FALSE(env.load(buf, n));

  n = build(buf);
  buf[3] = 2500.0f; buf[4] = 1500.0f;              // hfe window inverted
  TEST_ASSERT_FALSE(env.load(buf, n));
}

static void test_rejects_a_GAP_in_haa_coverage() {
  // The one that would be a silent hole: apply() declines to clamp a haa that
  // matches no bucket, so an uncovered span is a backstop with a blind spot.
  float buf[HFE_ENV_MAX_FLOATS];
  size_t n = build(buf);
  buf[1 + 4] = buf[1 + 4] + 100.0f;    // leg 0 bucket 1 starts late -> gap
  HfeEnvelope env;
  TEST_ASSERT_FALSE(env.load(buf, n));
}

static void test_rejects_coverage_not_reaching_the_rails() {
  float buf[HFE_ENV_MAX_FLOATS];
  HfeEnvelope env;

  size_t n = build(buf);
  buf[1] = 10.0f;                       // first bucket does not start at 0
  TEST_ASSERT_FALSE(env.load(buf, n));

  n = build(buf);
  buf[1 + HFE_ENV_STRIDE + 1] = 4000.0f;   // last bucket stops short of 4095
  TEST_ASSERT_FALSE(env.load(buf, n));
}

static void test_a_rejected_table_leaves_the_PREVIOUS_one_intact() {
  // Atomicity: a bad update must not disarm a good backstop.
  float good[HFE_ENV_MAX_FLOATS];
  size_t n = build(good);
  HfeEnvelope env;
  TEST_ASSERT_TRUE(env.load(good, n));

  float bad[HFE_ENV_MAX_FLOATS];
  size_t bn = build(bad);
  bad[5] = NAN;
  TEST_ASSERT_FALSE(env.load(bad, bn));

  TEST_ASSERT_TRUE(env.active());
  TEST_ASSERT_EQUAL_UINT8(2, env.buckets());
  uint16_t t[12] = {0};
  t[hfe_env_haa_index(0)] = 100;        // bucket 0
  t[hfe_env_hfe_index(0)] = 0;          // below the window -> must be raised
  env.apply(t);
  TEST_ASSERT_EQUAL_UINT16(1000, t[hfe_env_hfe_index(0)]);
}

// ---- clamping -------------------------------------------------------------

static void test_clamps_below_and_above_and_leaves_the_middle_alone() {
  float buf[HFE_ENV_MAX_FLOATS];
  size_t n = build(buf, 2, /*leg_step=*/0.0f);
  HfeEnvelope env;
  TEST_ASSERT_TRUE(env.load(buf, n));

  uint16_t t[12] = {0};
  t[hfe_env_haa_index(0)] = 100;                 // bucket 0 -> [1000, 2000]

  t[hfe_env_hfe_index(0)] = 500;                 // below
  env.apply(t);
  TEST_ASSERT_EQUAL_UINT16(1000, t[hfe_env_hfe_index(0)]);

  t[hfe_env_hfe_index(0)] = 3000;                // above
  env.apply(t);
  TEST_ASSERT_EQUAL_UINT16(2000, t[hfe_env_hfe_index(0)]);

  t[hfe_env_hfe_index(0)] = 1500;                // inside — untouched
  env.apply(t);
  TEST_ASSERT_EQUAL_UINT16(1500, t[hfe_env_hfe_index(0)]);
}

static void test_the_haa_target_SELECTS_the_window() {
  // The whole point: the same fold is legal at one hip angle and not another.
  float buf[HFE_ENV_MAX_FLOATS];
  size_t n = build(buf, 2, 0.0f);
  HfeEnvelope env;
  TEST_ASSERT_TRUE(env.load(buf, n));

  uint16_t t[12] = {0};
  t[hfe_env_hfe_index(0)] = 2500;

  t[hfe_env_haa_index(0)] = 100;                 // bucket 0 caps at 2000
  env.apply(t);
  TEST_ASSERT_EQUAL_UINT16(2000, t[hfe_env_hfe_index(0)]);

  t[hfe_env_hfe_index(0)] = 2500;
  t[hfe_env_haa_index(0)] = 3000;                // bucket 1 allows up to 3000
  env.apply(t);
  TEST_ASSERT_EQUAL_UINT16(2500, t[hfe_env_hfe_index(0)]);
}

static void test_each_leg_uses_its_OWN_hip_not_a_neighbours() {
  // THE seam test. Clamping one leg's fold against another leg's hip is the
  // failure mode this project keeps hitting (see #163/#164), and an off-by-one
  // in the 3L / 3L+1 pairing would produce exactly that while still looking
  // plausible on leg 0.
  float buf[HFE_ENV_MAX_FLOATS];
  size_t n = build(buf, 2, /*leg_step=*/10.0f);   // leg L window offset by 10L
  HfeEnvelope env;
  TEST_ASSERT_TRUE(env.load(buf, n));

  uint16_t t[12] = {0};
  // Put every leg's haa in bucket 0 EXCEPT leg 2, which goes to bucket 1.
  for (size_t leg = 0; leg < HFE_ENV_LEGS; leg++) {
    t[hfe_env_haa_index(leg)] = (leg == 2) ? 3000 : 100;
    t[hfe_env_hfe_index(leg)] = 4000;             // above every window
  }
  env.apply(t);

  // leg 0,1,3 -> bucket 0 hi = 2000 + 10*leg ; leg 2 -> bucket 1 hi = 3000+20
  TEST_ASSERT_EQUAL_UINT16(2000, t[hfe_env_hfe_index(0)]);
  TEST_ASSERT_EQUAL_UINT16(2010, t[hfe_env_hfe_index(1)]);
  TEST_ASSERT_EQUAL_UINT16(3020, t[hfe_env_hfe_index(2)]);
  TEST_ASSERT_EQUAL_UINT16(2030, t[hfe_env_hfe_index(3)]);
}

static void test_only_hfe_joints_are_touched() {
  // haa and kfe must pass through untouched — this clamp owns one joint type.
  float buf[HFE_ENV_MAX_FLOATS];
  size_t n = build(buf, 2, 0.0f);
  HfeEnvelope env;
  TEST_ASSERT_TRUE(env.load(buf, n));

  uint16_t t[12];
  for (size_t i = 0; i < 12; i++) t[i] = 100;     // bucket 0; hfe below window
  env.apply(t);
  for (size_t leg = 0; leg < HFE_ENV_LEGS; leg++) {
    TEST_ASSERT_EQUAL_UINT16(100, t[hfe_env_haa_index(leg)]);
    TEST_ASSERT_EQUAL_UINT16(100, t[3 * leg + 2]);          // kfe
    TEST_ASSERT_EQUAL_UINT16(1000, t[hfe_env_hfe_index(leg)]);
  }
}

static void test_clamp_counter_only_moves_when_it_bites() {
  float buf[HFE_ENV_MAX_FLOATS];
  size_t n = build(buf, 2, 0.0f);
  HfeEnvelope env;
  TEST_ASSERT_TRUE(env.load(buf, n));

  uint16_t t[12] = {0};
  for (size_t leg = 0; leg < HFE_ENV_LEGS; leg++) {
    t[hfe_env_haa_index(leg)] = 100;
    t[hfe_env_hfe_index(leg)] = 1500;             // inside the window
  }
  env.apply(t);
  TEST_ASSERT_EQUAL_UINT32(0, env.clamp_count());

  t[hfe_env_hfe_index(1)] = 4000;                 // one leg out of window
  env.apply(t);
  TEST_ASSERT_EQUAL_UINT32(1, env.clamp_count());
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_wellformed_table_loads);
  RUN_TEST(test_inactive_envelope_is_a_NO_OP);
  RUN_TEST(test_rejects_malformed_tables);
  RUN_TEST(test_rejects_a_GAP_in_haa_coverage);
  RUN_TEST(test_rejects_coverage_not_reaching_the_rails);
  RUN_TEST(test_a_rejected_table_leaves_the_PREVIOUS_one_intact);
  RUN_TEST(test_clamps_below_and_above_and_leaves_the_middle_alone);
  RUN_TEST(test_the_haa_target_SELECTS_the_window);
  RUN_TEST(test_each_leg_uses_its_OWN_hip_not_a_neighbours);
  RUN_TEST(test_only_hfe_joints_are_touched);
  RUN_TEST(test_clamp_counter_only_moves_when_it_bites);
  return UNITY_END();
}
