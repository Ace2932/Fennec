// Native unit tests for loop_timing.h — the histogram + progress watchdog
// extracted from main.cpp (Fennec #358 extraction rule). Pure logic, no
// clock needed. Host-run: pio test -e native.
//
// Every number below is the pre-extraction behaviour of main.cpp (2 us x 64
// latency buckets, 10 us x 64 exec buckets, ceil(0.99 n) p99 target, bucket
// midpoint, overflow = N * width, watchdog trips at >= budget). If a future
// edit changes one, this file says which.
#include <unity.h>
#include "loop_timing.h"

using namespace nova;

using LatHist  = LatencyHistogram<64, 2>;    // main.cpp's response-latency histogram
using ExecHist = LatencyHistogram<64, 10>;   // main.cpp's exec-time histogram

void setUp() {}
void tearDown() {}

// ---- bucketisation ----
static void test_bucket_edges_match_integer_division() {
  LatHist h;
  h.record(0); h.record(1);   // both -> bucket 0 (0..1 us)
  h.record(2);                // -> bucket 1
  h.record(3);                // -> bucket 1
  h.record(4);                // -> bucket 2
  TEST_ASSERT_EQUAL_UINT32(2, h.buckets()[0]);
  TEST_ASSERT_EQUAL_UINT32(2, h.buckets()[1]);
  TEST_ASSERT_EQUAL_UINT32(1, h.buckets()[2]);
  TEST_ASSERT_EQUAL_UINT32(5, h.count());
  TEST_ASSERT_EQUAL_UINT32(4, h.max_us());
}

static void test_overflow_clamps_to_last_bucket() {
  LatHist h;
  h.record(126);      // exactly 63*2 -> last bucket
  h.record(127);
  h.record(100000);   // absurd -> still last bucket, never out of bounds
  TEST_ASSERT_EQUAL_UINT32(3, h.buckets()[63]);
  TEST_ASSERT_EQUAL_UINT32(100000, h.max_us());
  TEST_ASSERT_EQUAL_UINT32(126, LatHist::kOverflowUs);
}

// ---- p99 ----
static void test_p99_empty_is_zero() {
  LatHist h;
  TEST_ASSERT_EQUAL_UINT32(0, h.p99_us());
}

static void test_p99_single_sample_is_its_bucket_midpoint() {
  LatHist h;
  h.record(7);                                   // bucket 3 (6..7) -> midpoint 7
  TEST_ASSERT_EQUAL_UINT32(3 * 2 + 1, h.p99_us());
}

static void test_p99_uses_ceil_not_floor() {
  // 100 samples: 99 at 4 us (bucket 2), 1 at 50 us (bucket 25).
  // ceil(0.99*100) = 99 -> reached inside bucket 2 -> midpoint 5 us.
  LatHist h;
  for (int i = 0; i < 99; i++) h.record(4);
  h.record(50);
  TEST_ASSERT_EQUAL_UINT32(5, h.p99_us());
  // 101 samples: 99 at 4 us, 2 at 50 us. ceil(0.99*101) = ceil(99.99) = 100 ->
  // the 100th sample is in bucket 25 -> midpoint 51. A floor would still say 5.
  h.record(50);
  TEST_ASSERT_EQUAL_UINT32(51, h.p99_us());
}

static void test_p99_all_overflow_reports_last_bucket_midpoint() {
  // Pre-extraction behaviour, pinned as measured (this test first asserted
  // N * width and was wrong): samples in the overflow bucket satisfy the
  // cumulative walk INSIDE bucket N-1, so p99 is that bucket's midpoint --
  // 63*2+1 = 127 us, 63*10+5 = 635 us. The `return n_buckets * bucket_us`
  // fallback is only reachable when total_count exceeds the bucket sum,
  // which a consistent histogram never does. The number a dashboard sees for
  // "everything overflowed" is therefore 127, not 128.
  LatHist h;
  for (int i = 0; i < 10; i++) h.record(500);   // all overflow
  TEST_ASSERT_EQUAL_UINT32(63 * 2 + 1, h.p99_us());
  ExecHist e;
  for (int i = 0; i < 10; i++) e.record(5000);
  TEST_ASSERT_EQUAL_UINT32(63 * 10 + 5, e.p99_us());
  // and the fallback itself, exercised the only way it can be: an
  // inconsistent total (raw array, count larger than the buckets hold)
  uint32_t raw[64] = {0};
  raw[3] = 1;
  TEST_ASSERT_EQUAL_UINT32(64 * 2, compute_p99_us(raw, 64, 2, 1000));
}

static void test_free_function_matches_member_on_raw_array() {
  ExecHist e;
  uint32_t samples[] = {12, 12, 12, 47, 47, 130, 640, 9};
  for (uint32_t s : samples) e.record(s);
  TEST_ASSERT_EQUAL_UINT32(
      compute_p99_us(e.buckets(), ExecHist::kBuckets, ExecHist::kBucketUs, e.count()),
      e.p99_us());
  TEST_ASSERT_EQUAL_UINT32(640, e.max_us());
  TEST_ASSERT_EQUAL_UINT32(8, e.count());
}

// ---- window reset ----
static void test_reset_clears_everything() {
  LatHist h;
  h.record(3); h.record(200);
  h.reset();
  TEST_ASSERT_EQUAL_UINT32(0, h.count());
  TEST_ASSERT_EQUAL_UINT32(0, h.max_us());
  TEST_ASSERT_EQUAL_UINT32(0, h.p99_us());
  for (int i = 0; i < LatHist::kBuckets; i++) TEST_ASSERT_EQUAL_UINT32(0, h.buckets()[i]);
}

// ---- progress watchdog ----
static void test_watchdog_counter_still_zero_at_boot_counts_as_stalled() {
  // Pre-extraction parity: last_observed_iter started at 0, so an ISR fire
  // that finds main_loop_iter still 0 counted one stalled tick. Kept.
  ProgressWatchdog wd(3);
  TEST_ASSERT_FALSE(wd.tick(0));
  TEST_ASSERT_EQUAL_UINT32(1, wd.no_progress_ticks());
  TEST_ASSERT_FALSE(wd.tick(1));            // loop ran -> progress, count clears
  TEST_ASSERT_EQUAL_UINT32(0, wd.no_progress_ticks());
}

static void test_watchdog_progress_never_trips() {
  ProgressWatchdog wd(3);
  for (uint32_t it = 0; it < 1000; it++) TEST_ASSERT_FALSE(wd.tick(it));
  TEST_ASSERT_EQUAL_UINT32(0, wd.no_progress_ticks());
}

static void test_watchdog_trips_at_budget_not_before() {
  ProgressWatchdog wd(200);                 // main.cpp default: 200 ticks = 1 s at 200 Hz
  wd.tick(5);                               // arm
  for (uint32_t k = 1; k < 200; k++) {
    TEST_ASSERT_FALSE_MESSAGE(wd.tick(5), "must not trip before the budget");
    TEST_ASSERT_EQUAL_UINT32(k, wd.no_progress_ticks());
  }
  TEST_ASSERT_TRUE(wd.tick(5));             // 200th stalled tick -> reset
  TEST_ASSERT_TRUE(wd.tick(5));             // stays tripped until the caller resets the board
}

static void test_watchdog_progress_after_stall_resets_count() {
  ProgressWatchdog wd(4);
  wd.tick(1);
  wd.tick(1); wd.tick(1);                   // 2 stalled
  TEST_ASSERT_EQUAL_UINT32(2, wd.no_progress_ticks());
  TEST_ASSERT_FALSE(wd.tick(2));            // progress
  TEST_ASSERT_EQUAL_UINT32(0, wd.no_progress_ticks());
  wd.tick(2); wd.tick(2); wd.tick(2);
  TEST_ASSERT_TRUE(wd.tick(2));             // 4 stalled again -> trips
}

static void test_watchdog_counter_wrap_is_progress() {
  ProgressWatchdog wd(2);
  wd.tick(0xFFFFFFFFu);
  TEST_ASSERT_FALSE(wd.tick(0));            // wrapped, but changed -> progress
  TEST_ASSERT_EQUAL_UINT32(0, wd.no_progress_ticks());
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_bucket_edges_match_integer_division);
  RUN_TEST(test_overflow_clamps_to_last_bucket);
  RUN_TEST(test_p99_empty_is_zero);
  RUN_TEST(test_p99_single_sample_is_its_bucket_midpoint);
  RUN_TEST(test_p99_uses_ceil_not_floor);
  RUN_TEST(test_p99_all_overflow_reports_last_bucket_midpoint);
  RUN_TEST(test_free_function_matches_member_on_raw_array);
  RUN_TEST(test_reset_clears_everything);
  RUN_TEST(test_watchdog_counter_still_zero_at_boot_counts_as_stalled);
  RUN_TEST(test_watchdog_progress_never_trips);
  RUN_TEST(test_watchdog_trips_at_budget_not_before);
  RUN_TEST(test_watchdog_progress_after_stall_resets_count);
  RUN_TEST(test_watchdog_counter_wrap_is_progress);
  return UNITY_END();
}
