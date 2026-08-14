// Native-test shim for <Arduino.h>. The pure-logic firmware headers
// (feetech_protocol.h, safety_state.h) only need fixed-width ints and a
// micros() clock; this lets `pio test -e native` compile + run them on the
// host with no Teensy toolchain. Added to the include path by the [env:native]
// build_flags (-I test/mock_arduino). NOT compiled into any device build --
// the real <Arduino.h> is used there.
#pragma once

#include <cstdint>
#include <cstddef>

// Controllable fake clock. Tests set the time via mock_micros() = <value> to
// exercise SafetyFSM::time_since_transition_us() deterministically.
inline uint32_t& mock_micros() {
  static uint32_t v = 0;
  return v;
}

inline uint32_t micros() { return mock_micros(); }
inline uint32_t millis() { return mock_micros() / 1000; }

// ---------------------------------------------------------------------------
// GPIO + UART shim, added 2026-08-14 so `feetech_bus.h` can be tested natively.
//
// WHY AN EVENT LOG AND NOT JUST PIN STATE. The thing worth pinning in the bus
// driver is ORDER, not final values: `transmit_blocking()` must flush the UART
// *before* re-enabling the RX gate, or the tail of our own transmission is read
// back as a servo response (feetech_bus.h:6-11). Final pin state is identical
// either way, so a state-only mock cannot see that bug. Every GPIO and UART
// call therefore appends a token to one shared, ordered log.
//
// Everything below is additive — the five pre-existing native suites only use
// micros()/millis()/mock_micros() and are unaffected.
// ---------------------------------------------------------------------------

#include <string>
#include <vector>

constexpr int LOW    = 0;
constexpr int HIGH   = 1;
constexpr int INPUT  = 0;
constexpr int OUTPUT = 1;

//: Ordered record of every mocked side effect. Tokens:
//:   "M<pin>"        pinMode
//:   "P<pin>=<0|1>"  digitalWrite
//:   "D<us>"         delayMicroseconds
//:   "BEGIN"         UART begin
//:   "W<n>"          UART write of n bytes
//:   "F"             UART flush
inline std::vector<std::string>& mock_events() {
  static std::vector<std::string> v;
  return v;
}

//: Microseconds the fake clock advances on each Serial available() poll, so
//: timeout loops in read_response() terminate instead of spinning on a frozen
//: clock. Real polling costs real time; this models that.
inline uint32_t& mock_poll_tick_us() {
  static uint32_t v = 1;
  return v;
}

inline void pinMode(uint8_t pin, int mode) {
  (void)mode;
  mock_events().push_back("M" + std::to_string((int)pin));
}

inline void digitalWrite(uint8_t pin, int value) {
  mock_events().push_back("P" + std::to_string((int)pin) + "=" +
                          std::to_string(value ? 1 : 0));
}

inline void delayMicroseconds(uint32_t us) {
  mock_micros() += us;
  mock_events().push_back("D" + std::to_string((unsigned long)us));
}

//: Minimal HardwareSerial stand-in. `script_rx()` queues bytes the "servo"
//: will return; `tx()` exposes everything the driver transmitted.
class MockUart {
 public:
  void begin(uint32_t baud) {
    baud_ = baud;
    mock_events().push_back("BEGIN");
  }
  int available() {
    mock_micros() += mock_poll_tick_us();
    return (int)(rx_.size() - rx_pos_);
  }
  int read() {
    if (rx_pos_ >= rx_.size()) return -1;
    return (int)rx_[rx_pos_++];
  }
  size_t write(const uint8_t* buf, size_t n) {
    tx_.insert(tx_.end(), buf, buf + n);
    mock_events().push_back("W" + std::to_string((unsigned long)n));
    return n;
  }
  void flush() {
    mock_events().push_back("F");
    // A servo answers AFTER our frame is on the wire. Staged bytes become
    // readable only here — otherwise transmit_blocking()'s stale-RX drain
    // (feetech_bus.h:52-55) correctly eats a response queued too early, and
    // the test, not the driver, is what is wrong.
    rx_.insert(rx_.end(), pending_.begin(), pending_.end());
    pending_.clear();
  }

  // ---- test-side helpers ----
  //: Bytes ALREADY sitting in the RX buffer before we transmit — i.e. stale
  //: junk the driver is supposed to drain.
  void script_rx(const uint8_t* b, size_t n) { rx_.insert(rx_.end(), b, b + n); }
  //: Bytes the servo sends back, delivered on flush(). This is what you want
  //: for any request/response test.
  void script_response(const uint8_t* b, size_t n) {
    pending_.insert(pending_.end(), b, b + n);
  }
  std::vector<uint8_t>& tx() { return tx_; }
  size_t rx_consumed() const { return rx_pos_; }
  size_t rx_remaining() const { return rx_.size() - rx_pos_; }
  uint32_t baud() const { return baud_; }
  void reset() {
    rx_.clear(); tx_.clear(); pending_.clear(); rx_pos_ = 0; baud_ = 0;
  }

 private:
  std::vector<uint8_t> rx_, tx_, pending_;
  size_t   rx_pos_ = 0;
  uint32_t baud_   = 0;
};

inline MockUart Serial1;

//: Clear clock, event log and UART between tests.
inline void mock_reset() {
  mock_micros() = 0;
  mock_poll_tick_us() = 1;
  mock_events().clear();
  Serial1.reset();
}

//: Index of the first event equal to `tok`, or -1. Lets a test assert ORDER
//: ("flush happens before the RX gate reopens") without hard-coding the whole
//: sequence, which would break on any unrelated addition.
inline int mock_index_of(const std::string& tok) {
  const auto& ev = mock_events();
  for (size_t i = 0; i < ev.size(); i++) if (ev[i] == tok) return (int)i;
  return -1;
}
