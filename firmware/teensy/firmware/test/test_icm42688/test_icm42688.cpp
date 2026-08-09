// Native tests for the ICM-42688-P driver (#14 / #289 step 4).
//
// The part is not owned yet, so NOTHING here talks to hardware. What is
// testable without the chip is exactly what has historically been wrong in this
// project: sign/endian handling at a byte boundary, and whether the value this
// firmware publishes means the same thing the consumer thinks it means.
//
// The centrepiece is test_quaternion_roundtrip_matches_policy_node: it encodes
// policy_node.py::_on_imu's OWN formula and asserts the quaternion this driver
// emits decodes back to the gravity vector it was built from. That is a test
// ACROSS the seam, which is the rule interface-boundary-bugs exists to enforce
// — a unit test on either side alone would pass with the frames swapped.

#include <unity.h>
#include <math.h>
#include <stdio.h>

#include "icm42688.h"

using namespace nova;

static void expect_close(float a, float b, float tol, const char* what) {
  if (fabsf(a - b) > tol) {
    char msg[128];
    snprintf(msg, sizeof(msg), "%s: got %.6f want %.6f", what, a, b);
    TEST_FAIL_MESSAGE(msg);
  }
}

// ---- decode ---------------------------------------------------------------

void test_decode_is_big_endian_signed(void) {
  uint8_t b[12] = {0};
  // accel X = +2048 LSB = +1 g  (0x0800)
  b[0] = 0x08; b[1] = 0x00;
  // accel Y = -2048 LSB = -1 g  (0xF800 two's complement)
  b[2] = 0xF8; b[3] = 0x00;
  ImuSample s = icm_decode(b);
  expect_close(s.accel[0], 1.0f, 1e-6f, "accel +1g");
  expect_close(s.accel[1], -1.0f, 1e-6f, "accel -1g");
  TEST_ASSERT_TRUE(s.valid);
}

void test_decode_gyro_scales_to_rad_per_s(void) {
  uint8_t b[12] = {0};
  // gyro X = +1640 LSB = +100 dps = 1.745329 rad/s
  b[6] = (uint8_t)((1640 >> 8) & 0xFF);
  b[7] = (uint8_t)(1640 & 0xFF);
  ImuSample s = icm_decode(b);
  expect_close(s.gyro[0], 100.0f * ICM_DEG_TO_RAD, 1e-4f, "gyro 100dps");
}

void test_decode_accel_and_gyro_do_not_alias(void) {
  // A byte written into the accel half must never surface in the gyro half.
  // Catches an offset slip between the two 6-byte blocks.
  uint8_t b[12] = {0};
  b[0] = 0x7F; b[1] = 0xFF;          // accel X large positive
  ImuSample s = icm_decode(b);
  TEST_ASSERT_TRUE(s.accel[0] > 15.0f);
  expect_close(s.gyro[0], 0.0f, 1e-9f, "gyro X must stay zero");
  expect_close(s.gyro[1], 0.0f, 1e-9f, "gyro Y must stay zero");
  expect_close(s.gyro[2], 0.0f, 1e-9f, "gyro Z must stay zero");
}

// ---- filter ---------------------------------------------------------------

void test_filter_primes_from_first_accel(void) {
  TiltFilter f;
  f.reset();
  TEST_ASSERT_FALSE(f.primed());
  float omega[3] = {0, 0, 0};
  float level[3] = {0, 0, -1};       // at rest, level
  f.update(omega, level, 0.001f);
  TEST_ASSERT_TRUE(f.primed());
  expect_close(f.gravity()[2], -1.0f, 1e-5f, "level gravity z");
}

void test_filter_converges_to_a_tilt(void) {
  TiltFilter f;
  f.reset();
  // 30 deg roll: gravity leaves -z and gains -y.
  const float s30 = 0.5f, c30 = 0.8660254f;
  float tilt[3] = {0.0f, -s30, -c30};
  float omega[3] = {0, 0, 0};
  for (int i = 0; i < 2000; i++) f.update(omega, tilt, 0.001f);
  expect_close(f.gravity()[1], -s30, 1e-3f, "tilt gravity y");
  expect_close(f.gravity()[2], -c30, 1e-3f, "tilt gravity z");
}

void test_filter_rejects_a_strike(void) {
  // A foot-strike spike is NOT gravity. The filter must coast on the gyro
  // instead of yanking attitude toward a 4 g transient — the failure mode that
  // tips a balance loop.
  TiltFilter f;
  f.reset();
  float omega[3] = {0, 0, 0};
  float level[3] = {0, 0, -1};
  for (int i = 0; i < 500; i++) f.update(omega, level, 0.001f);
  float before = f.gravity()[0];
  float strike[3] = {4.0f, 0.0f, -1.0f};    // |a| ~ 4.1 g, way outside the window
  for (int i = 0; i < 50; i++) f.update(omega, strike, 0.001f);
  expect_close(f.gravity()[0], before, 1e-4f, "attitude must not follow a strike");
}

void test_filter_gyro_only_rotation(void) {
  // With no usable accel, integrating a known rate must move gravity the right
  // way. Sign error here = the policy sees the robot tipping the wrong
  // direction, which is unrecoverable and silent.
  TiltFilter f;
  f.reset();
  float omega0[3] = {0, 0, 0};
  float level[3] = {0, 0, -1};
  f.update(omega0, level, 0.001f);            // prime level
  float roll_rate[3] = {1.0f, 0, 0};          // +1 rad/s about +x
  float none[3] = {0, 0, 0};                  // |a| = 0 -> outside window, coast
  for (int i = 0; i < 100; i++) f.update(roll_rate, none, 0.001f);
  // DERIVED, not guessed -- and this assertion caught its own author.
  // The body turns +theta about +x, so a WORLD-fixed vector seen in the body
  // frame turns -theta. R_x(-theta) @ [0,0,-1] = [0, -sin(theta), -cos(theta)],
  // so g_y goes NEGATIVE. The driver's small-angle term agrees exactly:
  // gd[1] = g[1] - (wz*gx - wx*gz)*dt = 0 - (0 - 1*(-1))*dt = -dt.
  // Physically: if +y (left) rises, body-frame "down" tilts toward -y.
  // The first version of this test asserted > 0. Do not "fix" it back.
  TEST_ASSERT_TRUE(f.gravity()[1] < -0.05f);
  expect_close(f.gravity()[1], -sinf(0.1f), 5e-3f, "gravity y after 0.1 rad");
  expect_close(f.gravity()[2], -cosf(0.1f), 5e-3f, "gravity z after 0.1 rad");
}

// ---- the seam -------------------------------------------------------------

// policy_node.py::_on_imu, transcribed EXACTLY:
//     self._grav = [-2*(x*z - w*y), -2*(y*z + w*x), -(1 - 2*(x*x + y*y))]
static void policy_node_proj_grav(const float* q, float* out) {
  float w = q[0], x = q[1], y = q[2], z = q[3];
  out[0] = -2.0f * (x * z - w * y);
  out[1] = -2.0f * (y * z + w * x);
  out[2] = -(1.0f - 2.0f * (x * x + y * y));
}

void test_quaternion_roundtrip_matches_policy_node(void) {
  // For a spread of attitudes: build the quaternion this driver would publish,
  // push it through the CONSUMER's formula, and require the original gravity
  // back. If firmware and policy_node ever disagree about frame or sign, this
  // is where it shows -- not on the robot.
  const float cases[][3] = {
      { 0.0f,     0.0f,    -1.0f    },   // level
      { 0.0f,    -0.5f,    -0.866f  },   // 30 deg roll
      { 0.5f,     0.0f,    -0.866f  },   // 30 deg pitch
      { 0.342f,  -0.321f,  -0.883f  },   // combined
      { 0.0f,     0.707f,  -0.707f  },   // 45 deg the other way
      {-0.643f,   0.0f,    -0.766f  },   // -40 deg pitch
  };
  for (unsigned c = 0; c < sizeof(cases) / sizeof(cases[0]); c++) {
    float g[3] = {cases[c][0], cases[c][1], cases[c][2]};
    float n = sqrtf(g[0]*g[0] + g[1]*g[1] + g[2]*g[2]);
    for (int i = 0; i < 3; i++) g[i] /= n;

    TiltFilter f;
    f.reset();
    float omega[3] = {0, 0, 0};
    f.update(omega, g, 0.001f);            // prime straight to this attitude

    float q[4];
    f.quaternion(q);
    expect_close(sqrtf(q[0]*q[0]+q[1]*q[1]+q[2]*q[2]+q[3]*q[3]), 1.0f, 1e-4f,
                 "quaternion must be unit");

    float back[3];
    policy_node_proj_grav(q, back);
    expect_close(back[0], g[0], 2e-3f, "roundtrip gx");
    expect_close(back[1], g[1], 2e-3f, "roundtrip gy");
    expect_close(back[2], g[2], 2e-3f, "roundtrip gz");
  }
}

void test_negative_control_wrong_sign_would_be_caught(void) {
  // Proof the roundtrip test can FAIL. Flip gravity's y and the consumer's
  // formula must disagree -- if this ever stops firing, the test above has
  // stopped discriminating and is decoration.
  float g[3] = {0.0f, -0.5f, -0.866f};
  TiltFilter f;
  f.reset();
  float omega[3] = {0, 0, 0};
  f.update(omega, g, 0.001f);
  float q[4];
  f.quaternion(q);
  float back[3];
  policy_node_proj_grav(q, back);
  TEST_ASSERT_TRUE(fabsf(back[1] - (-g[1])) > 0.1f);
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_decode_is_big_endian_signed);
  RUN_TEST(test_decode_gyro_scales_to_rad_per_s);
  RUN_TEST(test_decode_accel_and_gyro_do_not_alias);
  RUN_TEST(test_filter_primes_from_first_accel);
  RUN_TEST(test_filter_converges_to_a_tilt);
  RUN_TEST(test_filter_rejects_a_strike);
  RUN_TEST(test_filter_gyro_only_rotation);
  RUN_TEST(test_quaternion_roundtrip_matches_policy_node);
  RUN_TEST(test_negative_control_wrong_sign_would_be_caught);
  return UNITY_END();
}
