// loop_timing.h — board-agnostic control-loop timing instrumentation and a
// progress watchdog, extracted from main.cpp (Fennec #358's extraction rule:
// pure logic moves into a header as it is touched, so `pio test -e native`
// can execute it instead of the device builds merely compiling it).
//
// WHAT LIVES HERE
//   LatencyHistogram<N, BUCKET_US>  fixed-bucket histogram of a duration in
//       microseconds with max and count; p99 by cumulative walk. Two are used
//       by the firmware: ISR-fire -> handler-entry latency (2 us buckets, the
//       scheduling-jitter metric behind the <100 us p99 acceptance gate) and
//       per-tick handler exec time (10 us buckets, the cost of the work).
//   ProgressWatchdog  the software watchdog's DECISION: called from the tick
//       ISR with the main loop's iteration counter, it answers "has the main
//       loop advanced since the last tick?" and trips after `budget` ticks
//       without progress. The RESET itself stays in the caller (main.cpp
//       writes SCB_AIRCR), because how a board resets is the one thing here
//       that is not portable.
//
// WHAT DOES NOT LIVE HERE, ON PURPOSE
//   No Arduino, no micros(), no volatile, no ISR primitives. The caller owns
//   the clock, the ISR/handler split and the memory ordering; this header only
//   owns arithmetic. That is what makes it testable on the host and portable:
//   on a Cortex-M7 running Zephyr the same two classes take
//   k_cyc_to_us_floor32(k_cycle_get_32()) deltas and a k_timer ISR, and the
//   watchdog's `true` becomes a call to sys_reboot() or the IWDG being left
//   un-fed. (A hardware IWDG is the stronger design -- it survives this logic
//   itself hanging -- and belongs BESIDE a progress watchdog, not instead of
//   the measurement it gives you.)
//
// PARITY WITH THE PRE-EXTRACTION CODE (2026-09-10): bucket = us / BUCKET_US
// clamped to the last (overflow) bucket; p99 target = ceil(0.99 * n), bucket
// midpoint returned (an all-overflow window reads (N-1)*W + W/2, see
// compute_p99_us); the watchdog counts consecutive ISR fires with an
// unchanged iteration counter and trips at >= budget. test/test_loop_timing
// pins every one of those numbers.
#pragma once

#include <stdint.h>

namespace nova {

// Cumulative-walk p99: the bucket-midpoint microseconds at which the running
// count first reaches ceil(0.99 * total). Samples that overflowed sit in
// bucket n-1 and report ITS midpoint ((n-1)*w + w/2 -- 127 us for the 2 us x
// 64 latency histogram, 635 us for the 10 us x 64 exec one); the trailing
// `n_buckets * bucket_us` return is reached only when total_count exceeds
// what the buckets hold, i.e. an inconsistent caller-supplied count. (The
// pre-extraction comment said "overflow reports n*w"; the code never did, and
// test_loop_timing pins the real number.) Kept as a free function so the
// histogram's p99 and any caller with a raw array (host-side dashboards)
// compute the identical value.
inline uint32_t compute_p99_us(const uint32_t* h, int n_buckets, uint32_t bucket_us,
                               uint32_t total_count) {
  if (total_count == 0) return 0;
  uint32_t target = (total_count * 99 + 99) / 100;   // ceil(0.99 * n), integer
  uint32_t cum = 0;
  for (int i = 0; i < n_buckets; i++) {
    cum += h[i];
    if (cum >= target) return (uint32_t)i * bucket_us + bucket_us / 2;
  }
  return (uint32_t)n_buckets * bucket_us;
}

template <int NBUCKETS, uint32_t BUCKET_US>
class LatencyHistogram {
  static_assert(NBUCKETS > 0, "need at least one bucket");
  static_assert(BUCKET_US > 0, "bucket width must be non-zero");

 public:
  static constexpr int      kBuckets  = NBUCKETS;
  static constexpr uint32_t kBucketUs = BUCKET_US;
  // Durations at or beyond this land in the overflow (last) bucket.
  static constexpr uint32_t kOverflowUs = (uint32_t)(NBUCKETS - 1) * BUCKET_US;

  LatencyHistogram() { reset(); }

  void record(uint32_t us) {
    uint32_t b = us / BUCKET_US;
    if (b >= (uint32_t)NBUCKETS) b = NBUCKETS - 1;
    buckets_[b]++;
    if (us > max_us_) max_us_ = us;
    count_++;
  }

  uint32_t p99_us() const { return compute_p99_us(buckets_, NBUCKETS, BUCKET_US, count_); }
  uint32_t max_us() const { return max_us_; }
  uint32_t count() const { return count_; }
  const uint32_t* buckets() const { return buckets_; }

  // Clears buckets, max and count -- the per-report window reset.
  void reset() {
    for (int i = 0; i < NBUCKETS; i++) buckets_[i] = 0;
    max_us_ = 0;
    count_  = 0;
  }

 private:
  uint32_t buckets_[NBUCKETS];
  uint32_t max_us_;
  uint32_t count_;
};

// Progress watchdog decision. tick() is meant to run in the periodic ISR; the
// argument is a counter the main loop increments once per iteration. Returns
// true when `budget` consecutive ticks have seen no change -- the caller then
// resets the board. Keeps returning true past the threshold (a caller that
// cannot reset immediately must not see the alarm disappear).
class ProgressWatchdog {
 public:
  // `last observed` starts at 0, exactly as the pre-extraction globals did:
  // an ISR fire that sees the counter still at 0 counts as a stalled tick.
  // With the 200-tick default that is 5 ms of a 1 s budget and main.cpp
  // starts the timer as the last step of setup(), so it never matters in
  // practice -- but it is the same number as before, which is the point.
  explicit ProgressWatchdog(uint32_t budget_ticks)
      : budget_(budget_ticks), last_observed_(0), no_progress_(0) {}

  bool tick(uint32_t loop_iter_now) {
    if (loop_iter_now != last_observed_) {
      last_observed_ = loop_iter_now;
      no_progress_ = 0;
      return false;
    }
    no_progress_++;
    return no_progress_ >= budget_;
  }

  uint32_t no_progress_ticks() const { return no_progress_; }
  uint32_t budget() const { return budget_; }

 private:
  uint32_t budget_;
  uint32_t last_observed_;
  uint32_t no_progress_;
};

}  // namespace nova
