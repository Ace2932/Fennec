// ICM-42688-P — 6-axis IMU near the CoM (#14, and the step-4 blocker in #289).
//
// WHY THIS PART, AND WHY ON THE TEENSY. The MPU-6050 was cut 2026-05-24 on the
// assumption that the D456 and L2 IMUs would do. improvement-backlog.md item 14
// records why that is wrong for a balance loop: both are HIGH on the robot,
// vibration-rich, behind USB/Ethernet latency, and mounted on masts designed to
// break away in a fall. roadmap-trot-balance.md:67 wants attitude at 1 kHz on
// the Teensy; that is this.
//
// ---------------------------------------------------------------------------
// THE CONSUMER CONTRACT — read this before changing anything below.
// ---------------------------------------------------------------------------
// nova_locomotion/policy_node.py::_on_imu takes sensor_msgs/Imu and uses
// exactly two things:
//
//     gyro      = msg.angular_velocity            -> obs dims 0..2 (x0.25)
//     proj_grav = R(msg.orientation)^T @ [0,0,-1] -> obs dims 3..5
//
// and the sim it must match builds the same quantity as
// `math.rotate(jp.array([0,0,-1]), qinv)` (sim/nova_mjx/env.py:1189).
//
// So this part has to publish an ORIENTATION, and a 6-axis IMU has no fusion
// engine and emits no quaternion. The resolving fact:
//
//     *** proj_grav IS YAW-INVARIANT ***
//
// R^T @ [0,0,-1] depends on roll and pitch only. Yaw cancels. And yaw appears
// NOWHERE else in the observation — the commanded yaw RATE comes from /cmd_vel,
// not from here. So no magnetometer and no full AHRS is required: roll/pitch
// from gyro+accel is sufficient AND complete for what the policy consumes.
// That is why TiltFilter below emits yaw = 0 and is not an oversight.
//
// ---------------------------------------------------------------------------
// REGISTER MAP: VERIFY AGAINST THE DATASHEET BEFORE FIRST BENCH POWER-ON.
// ---------------------------------------------------------------------------
// These constants are written from reference material, not from a datasheet in
// hand, and this file cannot check itself. The runtime guard that catches a
// wrong map is WHO_AM_I: begin() refuses unless it reads back 0x47, so a bad
// address or a mis-remembered map fails LOUD and closed rather than streaming
// plausible garbage into the first six dims of every observation frame.
// Anything that survives WHO_AM_I but is still wrong shows up as a scale error
// in the bench axis check (docs/bench-capture-tonight.md:84).

#pragma once

#include <math.h>
#include <stdint.h>

namespace nova {

// ---- Bank 0 registers -----------------------------------------------------
// CONFIRMED against TDK AN-000488 (EV_ICM-42688-P user guide, rev 1.2), which
// is an authoritative source rather than recollection:
//   * AP_AD0 LOW -> 0x68, HIGH -> 0x69.
//   * AP_CS is a real pin and must be tied HIGH to select I2C -- the part
//     defaults to SPI. A module that leaves CS floating reads as dead on I2C,
//     which is the single most likely bring-up failure here.
// That guide is the EVB manual and carries NO register addresses, so it does
// NOT confirm the map below. WHO_AM_I remains the only guard on that.
constexpr uint8_t ICM_ADDR          = 0x68;  // AP_AD0 low. 0x69 if the pad is
                                             // strapped high. Clear of every
                                             // INA226 (0x40/41/44/45).
constexpr uint8_t ICM_REG_DEVICE_CONFIG = 0x11;  // bit0 = SOFT_RESET_CONFIG
constexpr uint8_t ICM_REG_ACCEL_DATA_X1 = 0x1F;  // 12 bytes: accel then gyro
constexpr uint8_t ICM_REG_GYRO_DATA_X1  = 0x25;
constexpr uint8_t ICM_REG_PWR_MGMT0     = 0x4E;
constexpr uint8_t ICM_REG_GYRO_CONFIG0  = 0x4F;
constexpr uint8_t ICM_REG_ACCEL_CONFIG0 = 0x50;
constexpr uint8_t ICM_REG_WHO_AM_I      = 0x75;
constexpr uint8_t ICM_REG_BANK_SEL      = 0x76;

constexpr uint8_t ICM_WHO_AM_I_VALUE = 0x47;

// PWR_MGMT0: gyro + accel both in Low Noise mode (bits [3:2] and [1:0] = 11).
constexpr uint8_t ICM_PWR_LN_BOTH = 0x0F;
// FS_SEL 000 = widest range, ODR 0110 = 1 kHz, for both sensors.
//   gyro  +-2000 dps -> 16.4 LSB/dps
//   accel +-16 g     -> 2048 LSB/g
// Widest range on purpose: a quadruped foot-strike spikes hard, and a clipped
// accel sample corrupts the gravity estimate far worse than the lost resolution
// costs. The filter cares about DIRECTION, not magnitude.
constexpr uint8_t ICM_GYRO_CFG_2000DPS_1KHZ = 0x06;
constexpr uint8_t ICM_ACCEL_CFG_16G_1KHZ    = 0x06;

constexpr float ICM_GYRO_LSB_PER_DPS = 16.4f;
constexpr float ICM_ACCEL_LSB_PER_G  = 2048.0f;
constexpr float ICM_DEG_TO_RAD       = 3.14159265358979323846f / 180.0f;

struct ImuSample {
  float gyro[3]  = {0, 0, 0};   // rad/s, body frame
  float accel[3] = {0, 0, 0};   // g, body frame
  bool  valid    = false;
};

// Decode the 12-byte burst starting at ACCEL_DATA_X1. Big-endian int16 pairs,
// accel XYZ then gyro XYZ. Split out from any I2C call so the native suite can
// test the sign/endian handling — the exact class of bug that has cost this
// project the most (see interface-boundary-bugs).
inline ImuSample icm_decode(const uint8_t* b) {
  ImuSample s;
  for (int i = 0; i < 3; i++) {
    int16_t a = (int16_t)((uint16_t)b[i * 2] << 8 | b[i * 2 + 1]);
    int16_t g = (int16_t)((uint16_t)b[6 + i * 2] << 8 | b[6 + i * 2 + 1]);
    s.accel[i] = (float)a / ICM_ACCEL_LSB_PER_G;
    s.gyro[i]  = ((float)g / ICM_GYRO_LSB_PER_DPS) * ICM_DEG_TO_RAD;
  }
  s.valid = true;
  return s;
}

// Complementary filter tracking the GRAVITY DIRECTION in the body frame.
//
// Tracks the vector itself rather than Euler angles: no gimbal singularity at
// +-90 deg pitch, and the tracked quantity IS obs dims 3..5, so nothing is
// converted twice. Gyro integrates it forward (fast, drifts); accel corrects it
// (slow, noisy under acceleration). alpha is the accel's share per update.
class TiltFilter {
 public:
  void reset() { g_[0] = 0; g_[1] = 0; g_[2] = -1; primed_ = false; }

  // omega: body rates rad/s. accel: body specific force in g. dt: seconds.
  void update(const float* omega, const float* accel, float dt) {
    float an = norm3(accel);
    // First good accel sample defines the initial attitude outright — starting
    // from "level" and letting the filter walk there would feed the policy a
    // wrong gravity for the whole convergence, and it is enabled exactly when
    // the robot is sitting still.
    if (!primed_ && an > 0.5f) {
      for (int i = 0; i < 3; i++) g_[i] = accel[i] / an;
      primed_ = true;
      return;
    }
    // Gyro: the body rotates by omega*dt, so a body-fixed view of a WORLD-fixed
    // vector rotates by -omega*dt. Small-angle cross product; at 1 kHz the
    // per-step angle is ~1e-3 rad and the error is second order.
    float gd[3] = {
        g_[0] - (omega[1] * g_[2] - omega[2] * g_[1]) * dt,
        g_[1] - (omega[2] * g_[0] - omega[0] * g_[2]) * dt,
        g_[2] - (omega[0] * g_[1] - omega[1] * g_[0]) * dt,
    };
    normalize3(gd);
    // Accel correction, but only when the reading looks like gravity alone.
    // Under a foot-strike |a| departs 1 g and the direction is not gravity;
    // trusting it then is how an IMU tips a balance loop over. Outside the
    // window we coast on the gyro, which is what it is good at.
    float w = 0.0f;
    if (an > 0.75f && an < 1.25f) w = alpha_;
    if (w > 0.0f) {
      for (int i = 0; i < 3; i++) gd[i] = (1.0f - w) * gd[i] + w * accel[i] / an;
      normalize3(gd);
    }
    for (int i = 0; i < 3; i++) g_[i] = gd[i];
  }

  const float* gravity() const { return g_; }   // unit, body frame == proj_grav
  bool primed() const { return primed_; }
  void set_alpha(float a) { alpha_ = a; }

  // Quaternion (w,x,y,z) with ZERO YAW whose R^T @ [0,0,-1] reproduces
  // gravity(). This is what goes in sensor_msgs/Imu.orientation, because that
  // is what policy_node reads — see the contract note at the top.
  //
  //   R^T @ [0,0,-1] = [ sin(pitch), -cos(pitch)sin(roll), -cos(pitch)cos(roll) ]
  //
  // so pitch = asin(g_x), roll = atan2(-g_y, -g_z), and the ZYX quaternion at
  // yaw = 0 collapses to the four terms below.
  void quaternion(float* q) const {
    float gx = g_[0];
    if (gx > 1.0f) gx = 1.0f;
    if (gx < -1.0f) gx = -1.0f;
    float pitch = asinf(gx);
    float roll  = atan2f(-g_[1], -g_[2]);
    float cr = cosf(roll * 0.5f), sr = sinf(roll * 0.5f);
    float cp = cosf(pitch * 0.5f), sp = sinf(pitch * 0.5f);
    q[0] = cr * cp;    // w
    q[1] = sr * cp;    // x
    q[2] = cr * sp;    // y
    q[3] = -sr * sp;   // z
  }

 private:
  static float norm3(const float* v) {
    return sqrtf(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
  }
  static void normalize3(float* v) {
    float n = norm3(v);
    if (n > 1e-6f) { v[0] /= n; v[1] /= n; v[2] /= n; }
  }
  float g_[3] = {0, 0, -1};
  // 0.02 at 1 kHz ~= a 50 ms trust horizon on the accel: fast enough to kill
  // gyro drift, slow enough that a single strike cannot yank attitude.
  float alpha_ = 0.02f;
  bool primed_ = false;
};

}  // namespace nova
