// Native unit test for the 12-servo bus TIMING budget — answers the #1 deploy
// question: can the Teensy service all 12 STS3215 at the 50 Hz control rate on
// one 1 Mbaud half-duplex bus?  Pure logic, host-run (pio test -e native).
//
// Deterministic: byte counts come from the REAL frame builders (build_sync_write
// / build_read) so this tracks the actual wire format — if a future change bloats
// a frame or drops sync-write for per-servo writes, the margin here moves and the
// assert catches a regression. Turnaround is a conservative fixed budget.
#include <unity.h>
#include "feetech_protocol.h"

using namespace feetech;

// ---- wire model ----
static constexpr double BAUD          = 1e6;   // 1 Mbaud (bus default)
static constexpr double BITS_PER_BYTE = 10.0;  // 8N1 (start + 8 + stop)
// Per read round-trip: 2x OE settle (~2 us each) + servo return-delay + our
// parse. Conservative — real STS3215 return-delay default is small.
static constexpr double TURNAROUND_US = 120.0;
static constexpr double CONTROL_HZ    = 50.0;
static constexpr double BUDGET_US     = 1e6 / CONTROL_HZ;   // 20 000 us

static double wire_us(int bytes) { return bytes * BITS_PER_BYTE / BAUD * 1e6; }

// One control cycle the deploy path actually runs: ONE sync-write of all 12
// goals (broadcast, no ACK) + 12 block-reads of pos+vel+load (6 bytes each).
static double cycle_syncwrite_us(int n_servos) {
  uint8_t ids[12], payload[12 * 2], frame[MAX_FRAME_LEN];
  for (int i = 0; i < n_servos; i++) { ids[i] = i + 1; payload[i*2]=0; payload[i*2+1]=0; }
  int tx = build_sync_write(REG_GOAL_POSITION_L, 2, ids, n_servos, payload, frame);
  double t = wire_us(tx);                       // broadcast goal write, no response
  int read_tx = build_read(1, REG_PRESENT_POSITION_L, 6, frame);  // request frame bytes
  int read_rx = 6 + 6;                          // FF FF id LEN err [6 params] cksum
  for (int i = 0; i < n_servos; i++)
    t += wire_us(read_tx + read_rx) + TURNAROUND_US;   // each read is a round-trip
  return t;
}

// Naive contrast: per-servo goal WRITE with ACK (12 round-trips) + 12 reads.
static double cycle_per_servo_writes_us(int n_servos) {
  uint8_t frame[MAX_FRAME_LEN]; uint8_t data[2] = {0, 0};
  int w_tx = build_write(1, REG_GOAL_POSITION_L, data, 2, frame);
  int w_rx = 6;                                 // status ACK
  int r_tx = build_read(1, REG_PRESENT_POSITION_L, 6, frame);
  int r_rx = 6 + 6;
  double t = 0;
  for (int i = 0; i < n_servos; i++)
    t += wire_us(w_tx + w_rx) + TURNAROUND_US + wire_us(r_tx + r_rx) + TURNAROUND_US;
  return t;
}

void setUp() {}
void tearDown() {}

// The real (sync-write) path must fit the 50 Hz budget with comfortable margin.
static void test_full_cycle_fits_50hz() {
  double t = cycle_syncwrite_us(12);
  TEST_ASSERT_TRUE_MESSAGE(t < BUDGET_US, "12-servo cycle exceeds the 20 ms/50 Hz budget");
  // require >= 3x headroom so jitter / added telemetry / a slower real
  // turnaround don't blow the budget.
  TEST_ASSERT_TRUE_MESSAGE(t < BUDGET_US / 3.0, "less than 3x headroom at 50 Hz");
}

// Document the max sustainable control rate (informational assert): the cycle
// should comfortably support >= 100 Hz too.
static void test_supports_100hz() {
  double t = cycle_syncwrite_us(12);
  TEST_ASSERT_TRUE_MESSAGE(t < 1e6 / 100.0, "12-servo cycle can't sustain 100 Hz");
}

// Sync-write must be materially faster than naive per-servo writes — this is WHY
// the architecture uses it. If someone regresses to per-servo writes, flag it.
static void test_syncwrite_beats_per_servo() {
  double sync = cycle_syncwrite_us(12);
  double naive = cycle_per_servo_writes_us(12);
  TEST_ASSERT_TRUE_MESSAGE(sync < naive, "sync-write should beat per-servo writes");
}

// The full-fleet sync-write frame must fit the wire buffer (guards the past
// payload overflow) — cross-checks the byte budget the timing relies on.
static void test_syncwrite_frame_within_bounds() {
  uint8_t ids[12], payload[12*2], frame[MAX_FRAME_LEN];
  for (int i = 0; i < 12; i++) { ids[i] = i+1; payload[i*2]=0; payload[i*2+1]=0; }
  int n = build_sync_write(REG_GOAL_POSITION_L, 2, ids, 12, payload, frame);
  TEST_ASSERT_TRUE_MESSAGE(n <= MAX_FRAME_LEN, "sync-write frame exceeds MAX_FRAME_LEN");
  TEST_ASSERT_EQUAL_INT_MESSAGE(8 + 3*12, n, "sync-write frame size drifted");
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_full_cycle_fits_50hz);
  RUN_TEST(test_supports_100hz);
  RUN_TEST(test_syncwrite_beats_per_servo);
  RUN_TEST(test_syncwrite_frame_within_bounds);
  return UNITY_END();
}
