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
