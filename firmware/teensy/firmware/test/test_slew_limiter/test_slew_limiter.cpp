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
  return UNITY_END();
}
