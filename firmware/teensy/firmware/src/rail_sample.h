// rail_sample.h — one INA226 rail reading, and how it goes onto /power_rails.
// Split out of ina226_telemetry.h (which needs <Wire.h> + the INA226 lib) so
// `pio test -e native` can execute the publish mapping (#358's extraction rule).
//
// #439 — AN INVALID SAMPLE PUBLISHES NaN. /power_rails used to copy voltage,
// current and power and drop `valid`, so a missing or failed INA226 published
// 0.0 V / 0.0 A / 0.0 W -- indistinguishable on the host from a rail that is
// genuinely dead. NaN is unambiguous and keeps the 3-floats-per-rail layout.
// `valid` is false when Rail::begin() got no ACK at boot, and (since the #439
// follow-up, rail_read() below) on any poll whose I2C read failed.
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

// One poll of a present chip (Rail::poll(); templated so the native test can
// pass a fake). #439 remainder: a failed I2C read makes the sample INVALID.
// The INA226 lib returns 0 from a read that got no ACK, so ignoring its error
// published a chip that dropped off mid-run as a live rail at 0.0 V, forever.
// getLastError() reports only the most recent register read (each read resets
// it), hence one check per getter. Fields and last_us keep the last GOOD read.
template <class Ina>
inline void rail_read(Ina& ina, RailSample& s, uint32_t now_us) {
  bool ok = true;
  const float v = ina.getBusVoltage(); ok &= (ina.getLastError() == 0);
  const float a = ina.getCurrent();    ok &= (ina.getLastError() == 0);
  const float w = ina.getPower();      ok &= (ina.getLastError() == 0);
  s.valid = ok;
  if (!ok) return;
  s.bus_voltage_v = v;
  s.current_a     = a;
  s.power_w       = w;
  s.last_us       = now_us;
}

}  // namespace nova
