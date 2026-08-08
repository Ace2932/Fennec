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

// ---- #280 present-position tightening -------------------------------------

// Two asymmetric buckets: bucket 0 (haa < 2048) is WIDE (cap 3500), bucket 1
// (haa >= 2048) is TIGHT (cap 800) — mirrors the real table's shape (open
// haa = permissive fold, tucked haa = restrictive) without needing degree
// conversions. leg 0 = FL, used throughout.
static size_t build_asymmetric(float* out) {
  out[0] = 2.0f;
  size_t i = 1;
  for (size_t leg = 0; leg < HFE_ENV_LEGS; leg++) {
    out[i++] = 0.0f;    out[i++] = 2048.0f; out[i++] = 0.0f; out[i++] = 3500.0f;
    out[i++] = 2048.0f; out[i++] = 4095.0f; out[i++] = 0.0f; out[i++] = 800.0f;
  }
  return i;
}

static void test_present_telemetry_further_tightens_the_selected_window() {
  float buf[HFE_ENV_MAX_FLOATS];
  size_t n = build_asymmetric(buf);
  HfeEnvelope env;
  TEST_ASSERT_TRUE(env.load(buf, n));

  uint16_t t[12] = {0};
  uint16_t present[12] = {0};
  t[hfe_env_haa_index(0)] = 100;     // bucket 0 (wide, cap 3500)
  t[hfe_env_hfe_index(0)] = 2500;    // legal under bucket 0 alone

  // No present telemetry passed at all -> old target-only behaviour, no clamp.
  env.apply(t);
  TEST_ASSERT_EQUAL_UINT16(2500, t[hfe_env_hfe_index(0)]);
  TEST_ASSERT_EQUAL_UINT32(0, env.clamp_count());

  // Present haa says this leg's hip is ACTUALLY already tucked (bucket 1,
  // cap 800) even though the commanded haa target is still in bucket 0 —
  // tighter-of-two must catch what target-only misses.
  t[hfe_env_hfe_index(0)] = 2500;
  present[hfe_env_haa_index(0)] = 3000;   // bucket 1
  env.apply(t, present, /*present_mask=*/(uint16_t)(1u << hfe_env_haa_index(0)));
  TEST_ASSERT_EQUAL_UINT16(800, t[hfe_env_hfe_index(0)]);
  TEST_ASSERT_EQUAL_UINT32(1, env.clamp_count());
}

static void test_present_position_unknown_falls_back_to_target_only() {
  // present_mask bit clear (servo never answered a poll) must not be
  // trusted — same choice as the anti-snap seed in main.cpp: fall back
  // rather than block motion on missing telemetry.
  float buf[HFE_ENV_MAX_FLOATS];
  size_t n = build_asymmetric(buf);
  HfeEnvelope env;
  TEST_ASSERT_TRUE(env.load(buf, n));

  uint16_t t[12] = {0};
  uint16_t present[12] = {0};
  t[hfe_env_haa_index(0)] = 100;           // bucket 0 (wide, cap 3500)
  t[hfe_env_hfe_index(0)] = 2500;
  present[hfe_env_haa_index(0)] = 3000;    // would select the tight bucket...
  // ...but the presence bit for this leg's haa is NOT set.
  env.apply(t, present, /*present_mask=*/0);
  TEST_ASSERT_EQUAL_UINT16(2500, t[hfe_env_hfe_index(0)]);
  TEST_ASSERT_EQUAL_UINT32(0, env.clamp_count());
}

// ---- #280 pipeline: pre-slew (PASS 2) alone vs +post-slew (PASS 4) --------
//
// Reproduces main.cpp's actual PASS 2 / PASS 3 / PASS 4 arithmetic for one
// leg. haa needs little travel (crosses the tight bucket almost immediately)
// while hfe needs a lot (mirrors the real stand->tuck move, where haa
// reaches the restrictive station long before hfe unfolds out of it) — both
// endpoints are legal (hfe's far target, 500, is well under the tight
// bucket's 800 cap), so a pre-slew check on the far target alone can never
// clamp it, exactly as measured on the real table in the issue (30.4 deg
// residual violation either way). Calling apply() AGAIN post-slew, on what
// is actually about to be written, closes it.
static void test_pass2_alone_permits_a_path_violation_pass4_does_not() {
  float buf[HFE_ENV_MAX_FLOATS];
  size_t n = build_asymmetric(buf);
  HfeEnvelope env;
  TEST_ASSERT_TRUE(env.load(buf, n));

  constexpr uint16_t SLEW_MAX = 200;   // test-local, doesn't need to match FW
  const uint16_t target_haa = 2100, target_hfe = 500;   // both legal at rest
  const uint16_t start_haa = 1900, start_hfe = 3000;

  auto slew = [](uint16_t last, uint16_t target) -> uint16_t {
    int32_t delta = (int32_t)target - (int32_t)last;
    if (delta > (int32_t)SLEW_MAX) delta = SLEW_MAX;
    if (delta < -(int32_t)SLEW_MAX) delta = -(int32_t)SLEW_MAX;
    return (uint16_t)((int32_t)last + delta);
  };

  // -- target-only (PASS 2, pre-slew) with NO PASS 4: reproduce the bug --
  {
    HfeEnvelope local = env;
    uint16_t last_haa = start_haa, last_hfe = start_hfe;
    bool violated = false;
    for (int tick = 0; tick < 20; tick++) {
      uint16_t targets[12] = {0};
      targets[hfe_env_haa_index(0)] = target_haa;
      targets[hfe_env_hfe_index(0)] = target_hfe;
      local.apply(targets);   // PASS 2 only — selects by the FAR target
      last_haa = slew(last_haa, targets[hfe_env_haa_index(0)]);
      last_hfe = slew(last_hfe, targets[hfe_env_hfe_index(0)]);
      // Legal RIGHT NOW means: hfe <= the cap selected by haa's OWN value
      // this tick. Check it directly against the table via a probe call.
      uint16_t probe[12] = {0};
      probe[hfe_env_haa_index(0)] = last_haa;
      probe[hfe_env_hfe_index(0)] = 4095;   // force worst case -> ceiling out
      HfeEnvelope ceiling_probe = env;
      ceiling_probe.apply(probe);
      if (last_hfe > probe[hfe_env_hfe_index(0)]) violated = true;
    }
    TEST_ASSERT_TRUE_MESSAGE(violated,
        "target-only PASS 2 was expected to permit a path violation here "
        "(matches the issue's measured 30.4 deg residual) — if this now "
        "passes, the scenario stopped reproducing the bug");
  }

  // -- target-only PASS 2 + post-slew PASS 4 on the same scenario --
  {
    HfeEnvelope local = env;
    uint16_t last_haa = start_haa, last_hfe = start_hfe;
    bool violated = false;
    for (int tick = 0; tick < 20; tick++) {
      uint16_t targets[12] = {0};
      targets[hfe_env_haa_index(0)] = target_haa;
      targets[hfe_env_hfe_index(0)] = target_hfe;
      local.apply(targets);                       // PASS 2
      last_haa = slew(last_haa, targets[hfe_env_haa_index(0)]);
      last_hfe = slew(last_hfe, targets[hfe_env_hfe_index(0)]);

      uint16_t goals[12] = {0};
      goals[hfe_env_haa_index(0)] = last_haa;      // this tick's OWN output
      goals[hfe_env_hfe_index(0)] = last_hfe;
      local.apply(goals);                          // PASS 4
      last_hfe = goals[hfe_env_hfe_index(0)];       // keep slew state in sync

      uint16_t probe[12] = {0};
      probe[hfe_env_haa_index(0)] = last_haa;
      probe[hfe_env_hfe_index(0)] = 4095;
      HfeEnvelope ceiling_probe = env;
      ceiling_probe.apply(probe);
      if (last_hfe > probe[hfe_env_hfe_index(0)]) violated = true;
    }
    TEST_ASSERT_FALSE_MESSAGE(violated,
        "PASS 4 (post-slew re-check on what is actually about to be "
        "written) should never let hfe exceed the window its OWN this-tick "
        "haa output selects");
    // And it must actually have reached the far target eventually, i.e. the
    // fix does not just permanently pin the joint.
    TEST_ASSERT_EQUAL_UINT16(target_hfe, last_hfe);
  }
}

// ---- #186 install/report state ---------------------------------------------
//
// main.cpp publishes joint_limits_rx_count / hfe_envelope_rx_count only when
// their callback's load() returned true, and hfe_envelope_clamps straight
// from clamp_count() — so the REPORTED state is exactly this object's
// active()/buckets()/clamp_count() triple. This tests that triple directly:
// it must read all-zero/inactive before any table, and a REJECTED update
// must never move it, so "accepted" can never be confused with "received".
static void test_report_state_reflects_only_ACCEPTED_tables() {
  HfeEnvelope env;
  TEST_ASSERT_FALSE(env.active());
  TEST_ASSERT_EQUAL_UINT8(0, env.buckets());
  TEST_ASSERT_EQUAL_UINT32(0, env.clamp_count());

  float bad[HFE_ENV_MAX_FLOATS];
  size_t bn = build(bad);
  bad[5] = NAN;
  TEST_ASSERT_FALSE(env.load(bad, bn));
  // A rejected table must not move ANY reported field, not even buckets().
  TEST_ASSERT_FALSE(env.active());
  TEST_ASSERT_EQUAL_UINT8(0, env.buckets());
  TEST_ASSERT_EQUAL_UINT32(0, env.clamp_count());

  float good[HFE_ENV_MAX_FLOATS];
  size_t gn = build(good, 3);
  TEST_ASSERT_TRUE(env.load(good, gn));
  TEST_ASSERT_TRUE(env.active());
  TEST_ASSERT_EQUAL_UINT8(3, env.buckets());
  TEST_ASSERT_EQUAL_UINT32(0, env.clamp_count());   // installed != clamped
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
  RUN_TEST(test_present_telemetry_further_tightens_the_selected_window);
  RUN_TEST(test_present_position_unknown_falls_back_to_target_only);
  RUN_TEST(test_pass2_alone_permits_a_path_violation_pass4_does_not);
  RUN_TEST(test_report_state_reflects_only_ACCEPTED_tables);
  return UNITY_END();
}
