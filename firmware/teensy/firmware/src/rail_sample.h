// rail_sample.h — one INA226 rail reading, and how it goes onto /power_rails.
// Split out of ina226_telemetry.h (which needs <Wire.h> + the INA226 lib) so
// `pio test -e native` can execute the publish mapping (#358's extraction rule).
//
// #439 — AN INVALID SAMPLE PUBLISHES NaN. /power_rails used to copy voltage,
// current and power and drop `valid`, so a missing or failed INA226 published
// 0.0 V / 0.0 A / 0.0 W -- indistinguishable on the host from a rail that is
// genuinely dead. NaN is unambiguous and keeps the 3-floats-per-rail layout.
// `valid` is false only when Rail::begin() got no ACK at boot; a chip that
// drops off mid-run is not detected yet (Rail::poll() never clears it).
#pragma once

#include <math.h>
#include <stdint.h>

namespace nova {

struct RailSample {
  float bus_voltage_v = 0.0f;
  float current_a     = 0.0f;
  float power_w       = 0.0f;
  bool  valid         = false;     // true if last read succeeded
  uint32_t last_us    = 0;
};

// Write [V, A, W] for one rail into out[0..2]; all three NaN if invalid.
inline void rail_fields(const RailSample& s, float* out) {
  out[0] = s.valid ? s.bus_voltage_v : NAN;
  out[1] = s.valid ? s.current_a     : NAN;
  out[2] = s.valid ? s.power_w       : NAN;
}

}  // namespace nova
