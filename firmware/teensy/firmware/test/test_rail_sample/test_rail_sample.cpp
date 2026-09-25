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

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_an_invalid_rail_publishes_NaN_not_zero);
  return UNITY_END();
}
