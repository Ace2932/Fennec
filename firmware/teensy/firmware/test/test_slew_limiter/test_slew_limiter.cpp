// Native unit test for the PASS-3 slew limiter, extracted from main.cpp (#358).
//
// The extraction claims to be behaviour-preserving. Reading my own diff is not
// evidence of that, so the first test below is a DIFFERENTIAL one: `reference_*`
// is a verbatim transcription of the loop as it stood in main.cpp before the
// move, and the equivalence sweep is EXHAUSTIVE over the entire reachable input
// domain (every last_goal x every target, and every present_pos x every target,
// across the full 0..4095 raw range) at the shipping max_delta. If the extraction
// changed anything at all, one of those 33.5M comparisons fails.

#include <unity.h>
#include <stdint.h>
#include <stdio.h>

#include "slew_limiter.h"
#include "hfe_envelope.h"   // PASS 2/4 neighbours, for the last_goal re-sync tests

using namespace nova;

static constexpr uint16_t RAW_MAX = 4095;
static constexpr uint16_t SHIPPING_DELTA = 20;   // NOVA_SLEW_MAX_DELTA default

void setUp(void) {}
void tearDown(void) {}

// --- the ORIGINAL logic, transcribed verbatim from main.cpp before #358 -------
// Deliberately not refactored, not tidied, not de-duplicated. Its only job is to
// be the thing the new code must agree with.
static uint16_t reference_slew(uint16_t target, uint16_t last_cmd_goal,
                               bool present, uint16_t servo_position_raw,
                               uint16_t max_delta) {
  uint16_t out;
  if (last_cmd_goal == SLEW_UNINIT) {
    if (present) {
      int32_t seeded = (int32_t)servo_position_raw;
      int32_t delta = (int32_t)target - seeded;
      if (delta >  (int32_t)max_delta) delta =  (int32_t)max_delta;
      if (delta < -(int32_t)max_delta) delta = -(int32_t)max_delta;
      out = (uint16_t)(seeded + delta);
    } else {
      out = target;
    }
  } else {
    int32_t delta = (int32_t)target - (int32_t)last_cmd_goal;
    if (delta >  (int32_t)max_delta) delta =  (int32_t)max_delta;
    if (delta < -(int32_t)max_delta) delta = -(int32_t)max_delta;
    out = (uint16_t)((int32_t)last_cmd_goal + delta);
  }
  return out;
}

// --- equivalence --------------------------------------------------------------

void test_matches_the_original_EXHAUSTIVELY_on_the_steady_state_branch(void) {
  for (uint32_t last = 0; last <= RAW_MAX; last++) {
    for (uint32_t tgt = 0; tgt <= RAW_MAX; tgt++) {
      uint16_t want = reference_slew((uint16_t)tgt, (uint16_t)last, false, 0, SHIPPING_DELTA);
      uint16_t got  = slew_step((uint16_t)tgt, (uint16_t)last, false, 0, SHIPPING_DELTA);
      if (want != got) {
        char msg[128];
        snprintf(msg, sizeof(msg), "last=%u target=%u: reference %u, extracted %u",
                 (unsigned)last, (unsigned)tgt, want, got);
        TEST_FAIL_MESSAGE(msg);
      }
    }
  }
}

void test_matches_the_original_EXHAUSTIVELY_on_the_antisnap_seed_branch(void) {
  for (uint32_t pos = 0; pos <= RAW_MAX; pos++) {
    for (uint32_t tgt = 0; tgt <= RAW_MAX; tgt++) {
      uint16_t want = reference_slew((uint16_t)tgt, SLEW_UNINIT, true, (uint16_t)pos, SHIPPING_DELTA);
      uint16_t got  = slew_step((uint16_t)tgt, SLEW_UNINIT, true, (uint16_t)pos, SHIPPING_DELTA);
      if (want != got) {
        char msg[128];
        snprintf(msg, sizeof(msg), "present_pos=%u target=%u: reference %u, extracted %u",
                 (unsigned)pos, (unsigned)tgt, want, got);
        TEST_FAIL_MESSAGE(msg);
      }
    }
  }
}

void test_matches_the_original_across_other_slew_rates(void) {
  const uint16_t deltas[] = {1, 2, 19, 20, 21, 100, 4095};
  for (uint16_t d : deltas) {
    for (uint32_t a = 0; a <= RAW_MAX; a += 7) {
      for (uint32_t b = 0; b <= RAW_MAX; b += 13) {
        TEST_ASSERT_EQUAL_UINT16(reference_slew((uint16_t)b, (uint16_t)a, false, 0, d),
                                 slew_step((uint16_t)b, (uint16_t)a, false, 0, d));
        TEST_ASSERT_EQUAL_UINT16(reference_slew((uint16_t)b, SLEW_UNINIT, true, (uint16_t)a, d),
                                 slew_step((uint16_t)b, SLEW_UNINIT, true, (uint16_t)a, d));
      }
    }
  }
}

// --- properties ---------------------------------------------------------------

void test_never_overshoots_the_target(void) {
  // The output must land between where we started and where we are going. This
  // is what makes the limiter safe to apply repeatedly: it can be slow, it can
  // never sail past.
  for (uint32_t last = 0; last <= RAW_MAX; last += 3) {
    for (uint32_t tgt = 0; tgt <= RAW_MAX; tgt += 5) {
      uint16_t out = slew_step((uint16_t)tgt, (uint16_t)last, false, 0, SHIPPING_DELTA);
      uint16_t lo = last < tgt ? (uint16_t)last : (uint16_t)tgt;
      uint16_t hi = last < tgt ? (uint16_t)tgt : (uint16_t)last;
      TEST_ASSERT_TRUE_MESSAGE(out >= lo && out <= hi, "slew output left [start,target]");
    }
  }
}

void test_output_stays_inside_the_raw_range_so_it_cannot_underflow(void) {
  // A uint16 cast of a negative intermediate would appear as ~65500 and be
  // written straight to a servo. It cannot happen: delta is bounded below by
  // -start as well as by -max_delta, so out >= 0 always. Pinned exhaustively
  // rather than argued, including the small-position corner where an unbounded
  // -max_delta WOULD have underflowed.
  for (uint32_t pos = 0; pos <= 64; pos++) {
    for (uint32_t tgt = 0; tgt <= RAW_MAX; tgt += 11) {
      uint16_t a = slew_step((uint16_t)tgt, (uint16_t)pos, false, 0, SHIPPING_DELTA);
      uint16_t b = slew_step((uint16_t)tgt, SLEW_UNINIT, true, (uint16_t)pos, SHIPPING_DELTA);
      TEST_ASSERT_TRUE_MESSAGE(a <= RAW_MAX, "steady-state slew produced an out-of-range value");
      TEST_ASSERT_TRUE_MESSAGE(b <= RAW_MAX, "seeded slew produced an out-of-range value");
    }
  }
}

void test_rate_is_capped_at_max_delta_per_tick(void) {
  uint16_t last = 2048;
  uint16_t out = slew_step(4095, last, false, 0, SHIPPING_DELTA);
  TEST_ASSERT_EQUAL_UINT16(2048 + SHIPPING_DELTA, out);
  out = slew_step(0, last, false, 0, SHIPPING_DELTA);
  TEST_ASSERT_EQUAL_UINT16(2048 - SHIPPING_DELTA, out);
}

void test_a_far_step_command_takes_many_ticks_not_one(void) {
  // The whole point: a host restart at a far pose ramps in.
  uint16_t cur = 2048;
  const uint16_t target = 4095;
  int ticks = 0;
  while (cur != target && ticks < 10000) { cur = slew_step(target, cur, false, 0, SHIPPING_DELTA); ticks++; }
  TEST_ASSERT_EQUAL_UINT16(target, cur);
  TEST_ASSERT_EQUAL_INT_MESSAGE((4095 - 2048 + SHIPPING_DELTA - 1) / SHIPPING_DELTA, ticks,
                                "ramp did not take ceil(distance/max_delta) ticks");
}

void test_antisnap_seeds_from_the_SERVO_not_from_the_target(void) {
  // The boot/E-stop-clear lurch this exists to prevent: servo physically at
  // 1000, host commands 4095. Verbatim would command 4095 immediately.
  uint16_t out = slew_step(4095, SLEW_UNINIT, /*present=*/true, /*pos=*/1000, SHIPPING_DELTA);
  TEST_ASSERT_EQUAL_UINT16_MESSAGE(1000 + SHIPPING_DELTA, out,
                                   "first command after boot was not seeded from present position");
}

void test_an_absent_servo_is_commanded_verbatim(void) {
  // Deliberate: a servo that never answered a poll has no trustworthy position,
  // and refusing to command it would be worse than a step it cannot take.
  TEST_ASSERT_EQUAL_UINT16(4095, slew_step(4095, SLEW_UNINIT, /*present=*/false, 0, SHIPPING_DELTA));
}

void test_the_sentinel_cannot_collide_with_a_real_goal(void) {
  // SLEW_UNINIT doubles as a value. It is only safe because the STS3215 raw
  // range tops out at 4095 — if a wider encoder ever lands, this breaks
  // silently by treating a legitimate goal as "no command yet".
  TEST_ASSERT_TRUE_MESSAGE(SLEW_UNINIT > RAW_MAX,
                           "SLEW_UNINIT is inside the reachable raw range");
}

// --- the loop + write-back ----------------------------------------------------

void test_apply_writes_back_last_goal_so_the_next_tick_ramps_from_it(void) {
  uint16_t targets[3] = {2500, 2500, 2500};
  uint16_t last[3]    = {2000, 2000, 2000};
  uint16_t out[3]     = {0, 0, 0};
  slew_apply(targets, last, out, 3, nullptr, 0, SHIPPING_DELTA);
  for (int i = 0; i < 3; i++) {
    TEST_ASSERT_EQUAL_UINT16(2020, out[i]);
    TEST_ASSERT_EQUAL_UINT16_MESSAGE(2020, last[i], "last_goal was not updated in place");
  }
  slew_apply(targets, last, out, 3, nullptr, 0, SHIPPING_DELTA);
  TEST_ASSERT_EQUAL_UINT16(2040, out[0]);
}

void test_apply_uses_each_joints_OWN_present_bit_and_position(void) {
  // Per-joint, not per-vector: joint 1 has answered a poll, joints 0 and 2 have
  // not. Getting this wrong would seed a joint from a neighbour's position.
  uint16_t targets[3] = {3000, 3000, 3000};
  uint16_t last[3]    = {SLEW_UNINIT, SLEW_UNINIT, SLEW_UNINIT};
  uint16_t out[3]     = {0, 0, 0};
  volatile uint16_t pos[3] = {100, 200, 300};
  slew_apply(targets, last, out, 3, pos, /*mask=*/0b010, SHIPPING_DELTA);
  TEST_ASSERT_EQUAL_UINT16_MESSAGE(3000, out[0], "absent joint 0 should be verbatim");
  TEST_ASSERT_EQUAL_UINT16_MESSAGE(200 + SHIPPING_DELTA, out[1], "joint 1 should seed from ITS position");
  TEST_ASSERT_EQUAL_UINT16_MESSAGE(3000, out[2], "absent joint 2 should be verbatim");
}

void test_apply_treats_a_null_present_array_as_all_absent(void) {
  uint16_t targets[2] = {4095, 4095};
  uint16_t last[2]    = {SLEW_UNINIT, SLEW_UNINIT};
  uint16_t out[2]     = {0, 0};
  slew_apply(targets, last, out, 2, nullptr, 0xFFFF, SHIPPING_DELTA);
  TEST_ASSERT_EQUAL_UINT16(4095, out[0]);
  TEST_ASSERT_EQUAL_UINT16(4095, out[1]);
}

// --- the PASS-4 re-sync (slew_commit) ------------------------------------------
//
// main.cpp's PASS 2/3/4 on a 12-joint vector, built from the extracted pieces
// exactly as broadcast_servo_commands() calls them.

// Two buckets per leg: haa 0..2048 -> hfe cap 3500 (wide), haa 2048..4095 ->
// hfe cap 800 (tucked). Same shape as test_hfe_envelope's build_asymmetric.
static void load_asymmetric(HfeEnvelope& env) {
  float b[HFE_ENV_MAX_FLOATS];
  size_t i = 0;
  b[i++] = 2.0f;
  for (size_t leg = 0; leg < HFE_ENV_LEGS; leg++) {
    b[i++] = 0.0f;    b[i++] = 2048.0f; b[i++] = 0.0f; b[i++] = 3500.0f;
    b[i++] = 2048.0f; b[i++] = 4095.0f; b[i++] = 0.0f; b[i++] = 800.0f;
  }
  TEST_ASSERT_TRUE(env.load(b, i));
}

static void pipeline_tick(HfeEnvelope& env, const uint16_t* cmd, uint16_t* last,
                          uint16_t* out, const volatile uint16_t* pos,
                          uint16_t mask, uint16_t d, bool reference_resync) {
  uint16_t t[12];
  for (size_t i = 0; i < 12; i++) t[i] = cmd[i];
  env.apply(t);                                // PASS 2
  slew_apply(t, last, out, 12, pos, mask, d);  // PASS 3
  env.apply(out, pos, mask);                   // PASS 4
  if (reference_resync) {
    // verbatim from main.cpp before slew_commit() existed
    for (size_t leg = 0; leg < HFE_ENV_LEGS; leg++) {
      const size_t hi = hfe_env_hfe_index(leg);
      last[hi] = out[hi];
    }
  } else {
    slew_commit(last, out, 12);
  }
}

void test_commit_matches_the_original_hfe_only_resync(void) {
  // Differential, random but seeded: 400 runs x 60 ticks through the whole
  // PASS 2-4 pipeline, anti-snap seed branch included (every run starts at
  // SLEW_UNINIT, and ~1 tick in 20 re-inits as a fault clear does).
  HfeEnvelope env_a, env_b;
  load_asymmetric(env_a);
  load_asymmetric(env_b);
  uint32_t x = 0x358u;
  auto rnd = [&x]() { x = x * 1664525u + 1013904223u; return x >> 8; };
  const uint16_t deltas[3] = {SHIPPING_DELTA, 200, RAW_MAX};
  for (int run = 0; run < 400; run++) {
    uint16_t last_a[12], last_b[12], out_a[12], out_b[12], cmd[12];
    volatile uint16_t pos[12];
    for (int i = 0; i < 12; i++) last_a[i] = last_b[i] = SLEW_UNINIT;
    const uint16_t d = deltas[run % 3];
    for (int tick = 0; tick < 60; tick++) {
      for (int i = 0; i < 12; i++) { cmd[i] = rnd() % 4096; pos[i] = rnd() % 4096; }
      const uint16_t mask = (uint16_t)(rnd() & 0x0FFF);
      if (rnd() % 20 == 0)
        for (int i = 0; i < 12; i++) last_a[i] = last_b[i] = SLEW_UNINIT;
      pipeline_tick(env_a, cmd, last_a, out_a, pos, mask, d, true);
      pipeline_tick(env_b, cmd, last_b, out_b, pos, mask, d, false);
      for (int i = 0; i < 12; i++) {
        if (out_a[i] != out_b[i] || last_a[i] != last_b[i]) {
          char msg[96];
          snprintf(msg, sizeof msg, "run %d tick %d joint %d: out %u/%u last %u/%u",
                   run, tick, i, out_a[i], out_b[i], last_a[i], last_b[i]);
          TEST_FAIL_MESSAGE(msg);
        }
      }
    }
  }
}

void test_a_path_clamp_becomes_next_ticks_slew_origin(void) {
  // #280's endpoint vs path distinction, end to end on leg 0. Both endpoints
  // are legal (haa 2000/hfe 3000 in the wide bucket; haa 2100/hfe 500 in the
  // tucked one), so PASS 2 never clamps the far target. The PATH is not:
  // haa crosses 2048 on the 3rd tick while hfe has only ramped 3000 -> 2940.
  HfeEnvelope env;
  load_asymmetric(env);
  const size_t HAA = hfe_env_haa_index(0), HFE = hfe_env_hfe_index(0);
  uint16_t last[12], out[12], cmd[12];
  for (int i = 0; i < 12; i++) last[i] = cmd[i] = 2000;
  last[HFE] = 3000;
  cmd[HAA] = 2100;
  cmd[HFE] = 500;

  int prev = last[HFE];
  int clamp_tick = -1;
  for (int tick = 0; tick < 10; tick++) {
    pipeline_tick(env, cmd, last, out, nullptr, 0, SHIPPING_DELTA, false);
    // path: every WRITTEN hfe is legal for the haa written alongside it
    if (out[HAA] > 2048) TEST_ASSERT_LESS_OR_EQUAL_UINT16(800, out[HFE]);
    // rate: at most max_delta per tick, except the one PASS-4 snap
    if (prev - (int)out[HFE] > (int)SHIPPING_DELTA) {
      TEST_ASSERT_EQUAL_INT_MESSAGE(-1, clamp_tick, "more than one snap");
      clamp_tick = tick;
    }
    TEST_ASSERT_EQUAL_UINT16_MESSAGE(out[HFE], last[HFE],
        "last_goal[hfe] is not what was written (#280 re-sync)");
    prev = out[HFE];
  }
  TEST_ASSERT_EQUAL_INT_MESSAGE(2, clamp_tick, "PASS 4 snap expected on the 3rd tick");
  TEST_ASSERT_EQUAL_UINT16(800 - 7 * SHIPPING_DELTA, out[HFE]);

  // The hazard the re-sync exists for: the host reverses and the window
  // re-opens. hfe must ramp up FROM what was written (660) by max_delta, not
  // restart from the pre-clamp goal that never reached the servo.
  cmd[HAA] = 2000;
  cmd[HFE] = 3000;
  pipeline_tick(env, cmd, last, out, nullptr, 0, SHIPPING_DELTA, false);
  TEST_ASSERT_EQUAL_UINT16_MESSAGE(prev + SHIPPING_DELTA, out[HFE],
      "hfe did not ramp from the written goal: slew started from a clamped-away value");
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_matches_the_original_EXHAUSTIVELY_on_the_steady_state_branch);
  RUN_TEST(test_matches_the_original_EXHAUSTIVELY_on_the_antisnap_seed_branch);
  RUN_TEST(test_matches_the_original_across_other_slew_rates);
  RUN_TEST(test_never_overshoots_the_target);
  RUN_TEST(test_output_stays_inside_the_raw_range_so_it_cannot_underflow);
  RUN_TEST(test_rate_is_capped_at_max_delta_per_tick);
  RUN_TEST(test_a_far_step_command_takes_many_ticks_not_one);
  RUN_TEST(test_antisnap_seeds_from_the_SERVO_not_from_the_target);
  RUN_TEST(test_an_absent_servo_is_commanded_verbatim);
  RUN_TEST(test_the_sentinel_cannot_collide_with_a_real_goal);
  RUN_TEST(test_apply_writes_back_last_goal_so_the_next_tick_ramps_from_it);
  RUN_TEST(test_apply_uses_each_joints_OWN_present_bit_and_position);
  RUN_TEST(test_apply_treats_a_null_present_array_as_all_absent);
  RUN_TEST(test_commit_matches_the_original_hfe_only_resync);
  RUN_TEST(test_a_path_clamp_becomes_next_ticks_slew_origin);
  return UNITY_END();
}
