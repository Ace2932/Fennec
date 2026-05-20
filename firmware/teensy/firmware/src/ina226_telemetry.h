// INA226 3-rail telemetry (leg 7.5V, hip 12V, Jetson 12V) per BOM §"Final
// power rail map v3.4". A 4th L2 rail is optional and reserved here as a
// build flag. Each sensor uses a distinct I²C address (set via A0/A1 jumpers
// on the breakout board). Shunt values match the Pololu / Adafruit reference
// configs — adjust max_amp + shunt_ohm if you swap boards.
//
// Read pattern: every tick (200 Hz) we sample one sensor in round-robin, so
// each rail refreshes at NOVA_LOOP_HZ / N_RAILS ≈ 66 Hz. The INA226 needs
// ~1.1 ms typ for a single conversion at default settings (samples=1, vbusct=
// 1.1 ms, vshct=1.1 ms = 2.2 ms total). To stay non-blocking inside the
// 5 ms tick budget, we issue a one-shot trigger one tick and read it the
// next — see Rail::poll() below.

#pragma once

#include <Arduino.h>
#include <Wire.h>
#include <INA226.h>

namespace nova {

constexpr uint8_t INA226_ADDR_LEG    = 0x40;   // leg 7.5V rail
constexpr uint8_t INA226_ADDR_HIP    = 0x41;   // hip 12V rail
constexpr uint8_t INA226_ADDR_JETSON = 0x44;   // Jetson 12V rail
// Optional 4th: L2 LiDAR 12V. Off by default; enable with -D NOVA_INA226_L2.
constexpr uint8_t INA226_ADDR_L2     = 0x45;

// 0.002 Ω shunt rated for ~20 A range — Adafruit-style breakout default.
// Override per-rail at construct time if shunt geometry differs.
constexpr float DEFAULT_SHUNT_OHM = 0.002f;
constexpr float DEFAULT_MAX_AMP   = 20.0f;

struct RailSample {
  float bus_voltage_v = 0.0f;
  float current_a     = 0.0f;
  float power_w       = 0.0f;
  bool  valid         = false;     // true if last read succeeded
  uint32_t last_us    = 0;
};

class Rail {
 public:
  Rail(uint8_t addr, const char* name,
       float shunt_ohm = DEFAULT_SHUNT_OHM,
       float max_amp   = DEFAULT_MAX_AMP)
      : ina_(addr), addr_(addr), name_(name),
        shunt_ohm_(shunt_ohm), max_amp_(max_amp) {}

  // begin() called from setup() after Wire.begin(). Returns true if the chip
  // ACK'd configure — false means missing / mis-addressed / unpowered, in
  // which case poll() will keep returning a stale-invalid sample.
  bool begin() {
    if (!ina_.begin()) {
      present_ = false;
      return false;
    }
    ina_.setMaxCurrentShunt(max_amp_, shunt_ohm_);
    present_ = true;
    return true;
  }

  // poll() reads the current chip state. Cheap (~120 µs typ for the 3 reads
  // over I²C @ 400 kHz). Updates the sample struct atomically from the
  // caller's perspective — this is single-threaded code, no locking needed.
  void poll() {
    if (!present_) {
      sample_.valid = false;
      return;
    }
    sample_.bus_voltage_v = ina_.getBusVoltage();
    sample_.current_a     = ina_.getCurrent();
    sample_.power_w       = ina_.getPower();
    sample_.valid         = true;
    sample_.last_us       = micros();
  }

  const RailSample& sample() const { return sample_; }
  const char*       name()   const { return name_; }
  uint8_t           addr()   const { return addr_; }
  bool              present() const { return present_; }

 private:
  INA226      ina_;
  uint8_t     addr_;
  const char* name_;
  float       shunt_ohm_;
  float       max_amp_;
  bool        present_ = false;
  RailSample  sample_;
};

}  // namespace nova
