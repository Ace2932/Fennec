// Native unit test for the Pattern-B half-duplex bus driver (feetech_bus.h).
//
// WHY THIS EXISTS. Before 2026-08-14 the native suite was 70/70 green over
// ~29% of the firmware, and `feetech_bus.h` — 274 lines, the largest header,
// the path EVERY joint command travels — had no test at all. The two things it
// gets wrong are both invisible to a final-state check:
//
//   1. OE POLARITY. The 74HC125 output-enables are ACTIVE-LOW. The header
//      records that the original firmware had these inverted, so "TX never
//      drove the bus and the idle-high UART fought every servo response"
//      (feetech_bus.h:29-36). A wrong polarity is a dead or contended bus.
//
//   2. OE ORDERING. transmit_blocking() must flush the UART BEFORE reopening
//      the RX gate, "otherwise the tail of our own TX is interpreted as a
//      servo response" (feetech_bus.h:6-11). Final pin state is identical
//      whether or not you get this right — only the ORDER differs.
//
// So the mock records an ordered event log rather than pin state, and the
// load-bearing assertions here are sequence assertions. See
// test/mock_arduino/Arduino.h.

#include <unity.h>
#include <string>
#include <vector>

#include "feetech_bus.h"

using namespace feetech;

static constexpr uint8_t TX_OE = 2;   // matches main.cpp / nova_pcb_v6_logic
static constexpr uint8_t RX_OE = 3;
static constexpr uint32_t BAUD = 1000000;

void setUp(void)    { mock_reset(); }
void tearDown(void) {}

// ---- helpers ---------------------------------------------------------------

//: Build a valid STS3215 status response: FF FF id len err [params] checksum.
static uint8_t make_status(uint8_t id, uint8_t err, const uint8_t* params,
                           uint8_t plen, uint8_t* out) {
  out[0] = HEADER_BYTE;
  out[1] = HEADER_BYTE;
  out[2] = id;
  out[3] = (uint8_t)(plen + 2);          // err + params + checksum
  out[4] = err;
  for (uint8_t i = 0; i < plen; i++) out[5 + i] = params[i];
  out[5 + plen] = checksum(&out[2], (uint8_t)(3 + plen));
  return (uint8_t)(6 + plen);
}

//: Walk the event log tracking OE levels and confirm every UART write happens
//: with the TX driver ON (tx_oe LOW) and the RX gate MUTED (rx_oe HIGH).
//: This is the invariant that catches BOTH failure modes above at once.
static bool writes_only_while_bus_is_owned(const std::vector<std::string>& ev,
                                           int tx_pin, int rx_pin,
                                           std::string* why) {
  int tx = -1, rx = -1;   // -1 = not yet driven
  for (const auto& e : ev) {
    if (!e.empty() && e[0] == 'P') {
      size_t eq = e.find('=');
      int pin = std::stoi(e.substr(1, eq - 1));
      int val = std::stoi(e.substr(eq + 1));
      if (pin == tx_pin) tx = val;
      else if (pin == rx_pin) rx = val;
    } else if (!e.empty() && e[0] == 'W') {
      if (tx != LOW) {
        *why = "UART write with the TX driver DISABLED (tx_oe=" +
               std::to_string(tx) + ", expected LOW)";
        return false;
      }
      if (rx != HIGH) {
        *why = "UART write with the RX gate STILL OPEN (rx_oe=" +
               std::to_string(rx) + ", expected HIGH) — we would read our own TX";
        return false;
      }
    }
  }
  return true;
}

// ---- begin() ---------------------------------------------------------------

void test_begin_drives_both_OE_pins_and_leaves_the_bus_in_RX(void) {
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();

  // Both OE pins configured as outputs before anything is driven.
  TEST_ASSERT_TRUE(mock_index_of("M2") >= 0);
  TEST_ASSERT_TRUE(mock_index_of("M3") >= 0);

  // Idle state is RX: tx_oe HIGH (driver released), rx_oe LOW (receiver on).
  TEST_ASSERT_TRUE(mock_index_of("P2=1") >= 0);
  TEST_ASSERT_TRUE(mock_index_of("P3=0") >= 0);

  // ...and the UART is opened only AFTER the gates are in a defined state,
  // so a pin floating at power-on cannot jam the bus while we configure it.
  TEST_ASSERT_TRUE(mock_index_of("BEGIN") > mock_index_of("P2=1"));
  TEST_ASSERT_TRUE(mock_index_of("BEGIN") > mock_index_of("P3=0"));
  TEST_ASSERT_EQUAL_UINT32(BAUD, Serial1.baud());
}

// ---- transmit_blocking() ordering — the load-bearing tests -----------------

void test_TX_gate_is_enabled_before_any_byte_leaves(void) {
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  mock_events().clear();

  uint8_t frame[MAX_FRAME_LEN];
  uint8_t n = build_ping(1, frame);
  TEST_ASSERT_TRUE(bus.transmit_blocking(frame, n));

  int tx_on = mock_index_of("P2=0");     // tx_oe LOW  = driver enabled
  int rx_mute = mock_index_of("P3=1");   // rx_oe HIGH = receiver muted
  int wrote = mock_index_of("W" + std::to_string((int)n));
  TEST_ASSERT_TRUE_MESSAGE(tx_on >= 0, "TX gate was never enabled");
  TEST_ASSERT_TRUE_MESSAGE(wrote >= 0, "frame was never written");
  TEST_ASSERT_TRUE_MESSAGE(tx_on < wrote, "wrote bytes before enabling the TX driver");
  TEST_ASSERT_TRUE_MESSAGE(rx_mute < wrote, "wrote bytes with the RX gate still open");
}

void test_UART_is_FLUSHED_before_the_RX_gate_reopens(void) {
  // feetech_bus.h:6-11 — release the gate early and the tail of our own
  // transmission comes back as a servo response. Final pin state is the same
  // either way, so ONLY the order can catch this.
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  mock_events().clear();

  uint8_t frame[MAX_FRAME_LEN];
  uint8_t n = build_ping(1, frame);
  bus.transmit_blocking(frame, n);

  int flushed = mock_index_of("F");
  int rx_reopened = mock_index_of("P3=0");   // rx_oe LOW = receiver on again
  TEST_ASSERT_TRUE_MESSAGE(flushed >= 0, "UART was never flushed");
  TEST_ASSERT_TRUE_MESSAGE(rx_reopened >= 0, "RX gate was never reopened");
  TEST_ASSERT_TRUE_MESSAGE(
      flushed < rx_reopened,
      "RX gate reopened BEFORE the UART flushed — the tail of our own TX will "
      "be parsed as a servo response");
}

void test_no_byte_is_ever_written_while_the_RX_gate_is_open(void) {
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();

  uint8_t frame[MAX_FRAME_LEN];
  uint8_t n = build_write(3, REG_GOAL_POSITION_L, (const uint8_t[]){0x00, 0x08}, 2, frame);
  bus.transmit_blocking(frame, n);
  bus.transmit_blocking(frame, n);     // twice — catches a one-shot setup

  std::string why;
  TEST_ASSERT_TRUE_MESSAGE(
      writes_only_while_bus_is_owned(mock_events(), TX_OE, RX_OE, &why),
      why.c_str());
}

void test_the_OE_invariant_checker_would_actually_catch_a_violation(void) {
  // Guard on the guard: feed the walker a hand-built log with the gates
  // inverted and confirm it reports a failure. Without this, a checker that
  // always returns true would make the test above vacuous.
  std::vector<std::string> inverted = {"P2=1", "P3=0", "D2", "W6", "F"};
  std::string why;
  TEST_ASSERT_FALSE_MESSAGE(
      writes_only_while_bus_is_owned(inverted, TX_OE, RX_OE, &why),
      "the invariant checker passed a log that writes with the TX driver off");
  TEST_ASSERT_TRUE(why.find("TX driver DISABLED") != std::string::npos);

  std::vector<std::string> rx_left_open = {"P2=0", "P3=0", "D2", "W6"};
  TEST_ASSERT_FALSE_MESSAGE(
      writes_only_while_bus_is_owned(rx_left_open, TX_OE, RX_OE, &why),
      "the invariant checker passed a log that writes with the RX gate open");
  TEST_ASSERT_TRUE(why.find("RX gate STILL OPEN") != std::string::npos);
}

void test_stale_RX_is_drained_before_the_TX_gate_opens(void) {
  // feetech_bus.h:52-55 — left-over bytes from a previous response would
  // otherwise re-enter the parser after the next set_rx().
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  const uint8_t junk[] = {0xDE, 0xAD, 0xBE};
  Serial1.script_rx(junk, sizeof(junk));
  mock_events().clear();

  uint8_t frame[MAX_FRAME_LEN];
  uint8_t n = build_ping(1, frame);
  bus.transmit_blocking(frame, n);

  TEST_ASSERT_EQUAL_size_t(0, Serial1.rx_remaining());
  TEST_ASSERT_EQUAL_size_t(sizeof(junk), Serial1.rx_consumed());
}

void test_oversize_frame_is_rejected_without_touching_the_bus(void) {
  // A rejected frame must not glitch the OE lines — a momentary TX enable with
  // nothing to send still collides with a servo that is mid-response.
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  mock_events().clear();

  uint8_t frame[MAX_FRAME_LEN];
  TEST_ASSERT_FALSE(bus.transmit_blocking(frame, MAX_FRAME_LEN + 1));
  TEST_ASSERT_EQUAL_size_t(0, mock_events().size());
  TEST_ASSERT_EQUAL_size_t(0, Serial1.tx().size());
}

// ---- read_response() / timeouts -------------------------------------------

void test_ping_succeeds_on_a_valid_response(void) {
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  uint8_t resp[MAX_RESPONSE_LEN];
  uint8_t rn = make_status(5, 0, nullptr, 0, resp);
  TEST_ASSERT_EQUAL_UINT8(6, rn);          // ping response is 6 bytes
  Serial1.script_response(resp, rn);

  TEST_ASSERT_EQUAL_INT(Bus::OK, bus.ping(5));
}

void test_ping_times_out_and_terminates_when_the_bus_is_silent(void) {
  // Also a liveness test: read_response() spins on micros(), so a frozen clock
  // would hang here forever rather than fail.
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  uint32_t t0 = micros();

  TEST_ASSERT_EQUAL_INT(Bus::ERR_TIMEOUT, bus.ping(5, /*timeout_us=*/500));
  TEST_ASSERT_TRUE_MESSAGE(micros() - t0 >= 500,
                           "returned before the timeout could have elapsed");
}

void test_ping_reports_BAD_FRAME_when_another_servo_answers(void) {
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  uint8_t resp[MAX_RESPONSE_LEN];
  uint8_t rn = make_status(9, 0, nullptr, 0, resp);   // asked 5, got 9
  Serial1.script_response(resp, rn);

  TEST_ASSERT_EQUAL_INT(Bus::ERR_BAD_FRAME, bus.ping(5));
}

void test_servo_error_flag_is_surfaced_not_swallowed(void) {
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  uint8_t resp[MAX_RESPONSE_LEN];
  uint8_t rn = make_status(5, /*err=*/0x04, nullptr, 0, resp);
  Serial1.script_response(resp, rn);

  TEST_ASSERT_EQUAL_INT(Bus::ERR_SERVO, bus.ping(5));
}

void test_read_position_unpacks_little_endian(void) {
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  const uint8_t params[] = {0x34, 0x08};      // 0x0834 = 2100
  uint8_t resp[MAX_RESPONSE_LEN];
  uint8_t rn = make_status(2, 0, params, 2, resp);
  TEST_ASSERT_EQUAL_UINT8(8, rn);
  Serial1.script_response(resp, rn);

  uint16_t pos = 0;
  TEST_ASSERT_EQUAL_INT(Bus::OK, bus.read_position(2, &pos));
  TEST_ASSERT_EQUAL_UINT16(2100, pos);
}

// ---- guards ---------------------------------------------------------------

void test_sync_write_of_zero_servos_puts_nothing_on_the_wire(void) {
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  mock_events().clear();

  TEST_ASSERT_EQUAL_INT(Bus::OK, bus.sync_write_goal_positions(nullptr, nullptr, 0));
  TEST_ASSERT_EQUAL_size_t(0, Serial1.tx().size());
  TEST_ASSERT_EQUAL_size_t(0, mock_events().size());
}

void test_sync_write_rejects_a_thirteenth_servo(void) {
  // NOTE THE NAME. This pins the BEHAVIOUR (13 is refused, nothing hits the
  // wire), not which of the two guards refused it — see the coextensive test
  // below for why no test can tell them apart today.
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  mock_events().clear();

  uint8_t ids[13];
  uint16_t goals[13];
  for (int i = 0; i < 13; i++) { ids[i] = (uint8_t)(i + 1); goals[i] = 2048; }

  TEST_ASSERT_EQUAL_INT(Bus::ERR_BAD_FRAME, bus.sync_write_goal_positions(ids, goals, 13));
  TEST_ASSERT_EQUAL_size_t(0, Serial1.tx().size());
}

void test_the_fleet_bound_stops_being_redundant_if_MAX_FRAME_LEN_grows(void) {
  // sync_write_goal_positions() has TWO guards (feetech_bus.h:243-246):
  //     if (n > 12)                          return ERR_BAD_FRAME;
  //     if (8 + 3 * n > MAX_FRAME_LEN)       return ERR_BAD_FRAME;
  // For the 3-bytes-per-servo goal-position frame they reject exactly the same
  // set of n — 8 + 3n <= 46 iff n <= 12 — so they are COEXTENSIVE and deleting
  // either one alone changes nothing observable. Measured 2026-08-14: removing
  // `n > 12` leaves all 17 tests in this file green.
  //
  // The redundancy is deliberate, and the comment on it names the reason: the
  // 2026-06-12 stack overflow. `payload` is sized 12*2 = 24 bytes and the fill
  // loop writes payload[2n-2], payload[2n-1] — so n = 13 would write past the
  // end. Today the frame-size guard returns first and that is unreachable.
  //
  // Raise MAX_FRAME_LEN to 47+ and it becomes reachable: `n > 12` is then the
  // ONLY thing between a 13-servo call and a 2-byte stack overrun. This assert
  // is the tripwire for that day, because at that point the deletion the
  // sabotage sweep could not catch becomes a live memory-safety bug.
  TEST_ASSERT_TRUE_MESSAGE(
      8 + 3 * 13 > MAX_FRAME_LEN,
      "MAX_FRAME_LEN grew past 46: the frame-size guard no longer backstops the "
      "12-servo bound, so `n > 12` in sync_write_goal_positions() is now the ONLY "
      "protection for payload[12*2]. Confirm it is still there, and size payload "
      "from the same constant.");
}

void test_sync_write_of_the_full_fleet_fits_in_one_frame(void) {
  // The 2026-06-12 stack overflow this guard exists for: 12 servos must still
  // build and transmit as a single frame within MAX_FRAME_LEN.
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  mock_events().clear();

  uint8_t ids[12];
  uint16_t goals[12];
  for (int i = 0; i < 12; i++) { ids[i] = (uint8_t)(i + 1); goals[i] = 2048; }

  TEST_ASSERT_EQUAL_INT(Bus::OK, bus.sync_write_goal_positions(ids, goals, 12));
  TEST_ASSERT_TRUE(Serial1.tx().size() > 0);
  TEST_ASSERT_TRUE_MESSAGE(Serial1.tx().size() <= MAX_FRAME_LEN,
                           "full-fleet sync-write overran MAX_FRAME_LEN");
  TEST_ASSERT_EQUAL_UINT8(BROADCAST_ID, Serial1.tx()[2]);
}

void test_set_id_refuses_to_write_the_broadcast_value(void) {
  // Writing 0xFE into a servo's ID register makes every servo answer at once
  // and there is no way to undo it over the bus.
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();
  mock_events().clear();

  TEST_ASSERT_EQUAL_INT(Bus::ERR_BAD_FRAME, bus.set_id(1, BROADCAST_ID));
  TEST_ASSERT_EQUAL_size_t(0, Serial1.tx().size());
}

void test_torque_limit_is_clamped_to_full_scale(void) {
  Bus bus(TX_OE, RX_OE, BAUD);
  bus.begin();

  bus.set_torque_limit(1, 5000);          // absurd request
  // Frame layout: FF FF id len inst reg lo hi checksum
  TEST_ASSERT_TRUE(Serial1.tx().size() >= 8);
  uint16_t sent = (uint16_t)(Serial1.tx()[6] | (Serial1.tx()[7] << 8));
  TEST_ASSERT_EQUAL_UINT16_MESSAGE(1000, sent,
                                   "torque limit was not clamped to 1000 permille");
}

// ---- runner ----------------------------------------------------------------

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_begin_drives_both_OE_pins_and_leaves_the_bus_in_RX);
  RUN_TEST(test_TX_gate_is_enabled_before_any_byte_leaves);
  RUN_TEST(test_UART_is_FLUSHED_before_the_RX_gate_reopens);
  RUN_TEST(test_no_byte_is_ever_written_while_the_RX_gate_is_open);
  RUN_TEST(test_the_OE_invariant_checker_would_actually_catch_a_violation);
  RUN_TEST(test_stale_RX_is_drained_before_the_TX_gate_opens);
  RUN_TEST(test_oversize_frame_is_rejected_without_touching_the_bus);
  RUN_TEST(test_ping_succeeds_on_a_valid_response);
  RUN_TEST(test_ping_times_out_and_terminates_when_the_bus_is_silent);
  RUN_TEST(test_ping_reports_BAD_FRAME_when_another_servo_answers);
  RUN_TEST(test_servo_error_flag_is_surfaced_not_swallowed);
  RUN_TEST(test_read_position_unpacks_little_endian);
  RUN_TEST(test_sync_write_of_zero_servos_puts_nothing_on_the_wire);
  RUN_TEST(test_sync_write_rejects_a_thirteenth_servo);
  RUN_TEST(test_the_fleet_bound_stops_being_redundant_if_MAX_FRAME_LEN_grows);
  RUN_TEST(test_sync_write_of_the_full_fleet_fits_in_one_frame);
  RUN_TEST(test_set_id_refuses_to_write_the_broadcast_value);
  RUN_TEST(test_torque_limit_is_clamped_to_full_scale);
  return UNITY_END();
}
