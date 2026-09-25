// Native test for rail_sample.h -- the /power_rails mapping (#439).

#include <unity.h>
#include <math.h>

#include "rail_sample.h"

void setUp(void) {}
void tearDown(void) {}

void test_an_invalid_rail_publishes_NaN_not_zero(void) {
  // A missing INA226 (Rail::begin() failed -> valid stays false) used to
  // publish 0.0 V / 0.0 A / 0.0 W, which reads on the host as a dead rail.
  nova::RailSample s;              // default: valid = false, fields 0.0
  float out[3] = {1.0f, 1.0f, 1.0f};
  nova::rail_fields(s, out);
  for (int i = 0; i < 3; i++)
    TEST_ASSERT_TRUE_MESSAGE(isnan(out[i]), "invalid INA226 sample published as a number (#439)");

  s.bus_voltage_v = 7.4f; s.current_a = 2.5f; s.power_w = 18.5f; s.valid = true;
  nova::rail_fields(s, out);
  TEST_ASSERT_EQUAL_FLOAT(7.4f, out[0]);
  TEST_ASSERT_EQUAL_FLOAT(2.5f, out[1]);
  TEST_ASSERT_EQUAL_FLOAT(18.5f, out[2]);
}

// Stand-in for robtillaart INA226 >= 0.6.4: each getter is one register read,
// and getLastError() reports (then clears) that read's I2C error, 0 = OK.
struct FakeIna {
  bool acks = true;
  int err = 0;
  int read(float* out, float v) { err = acks ? 0 : -1; *out = acks ? v : 0.0f; return 0; }
  float getBusVoltage() { float o; read(&o, 7.4f);  return o; }
  float getCurrent()    { float o; read(&o, 2.5f);  return o; }
  float getPower()      { float o; read(&o, 18.5f); return o; }
  int getLastError()    { int e = err; err = 0; return e; }
};

void test_a_chip_that_drops_off_mid_run_publishes_NaN(void) {
  // #439 remainder: begin() ACKed, so the rail is `present`, then the chip
  // stops answering. The library returns 0 from a failed read and sets an
  // error — so without checking it, the rail keeps publishing 0.0 V as if
  // real (or its last good sample), never NaN.
  FakeIna ina;
  nova::RailSample s;
  float out[3];

  nova::rail_read(ina, s, 1000);
  nova::rail_fields(s, out);
  TEST_ASSERT_EQUAL_FLOAT(7.4f, out[0]);
  TEST_ASSERT_EQUAL_UINT32(1000, s.last_us);

  ina.acks = false;                  // INA226 unplugged / brown-out
  nova::rail_read(ina, s, 2000);
  nova::rail_fields(s, out);
  for (int i = 0; i < 3; i++)
    TEST_ASSERT_TRUE_MESSAGE(isnan(out[i]), "failed INA226 read still published a number (#439)");
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(1000, s.last_us, "last_us must stay the last GOOD read");

  ina.acks = true;                   // and it recovers when the chip returns
  nova::rail_read(ina, s, 3000);
  nova::rail_fields(s, out);
  TEST_ASSERT_EQUAL_FLOAT(18.5f, out[2]);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_an_invalid_rail_publishes_NaN_not_zero);
  RUN_TEST(test_a_chip_that_drops_off_mid_run_publishes_NaN);
  return UNITY_END();
}
