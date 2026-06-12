// Nova-SM3 LE — Teensy 4.1 firmware skeleton
// Pattern B bus master per BOM v3.3
//
// Status (2026-05-19): Arduino-only compile-green scaffold. micro-ROS
// integration is gated on NOVA_USE_MICRO_ROS — leave undefined until
// we move firmware builds to the Jetson (Mac micro-ROS build path is
// brittle: needs Python 3.10/3.11 + ROS dev libs). Stubs printed over
// USB-CDC at NOVA_LOOP_HZ for now.

#include <Arduino.h>
#include "feetech_bus.h"
#include "ina226_telemetry.h"
#include "safety_state.h"

// Joint count = 12 (4 legs × 3 joints). Names/frame_id stay empty in
// skeleton — Nova URDF wiring lands once gait controller is on the Jetson.
// Declared outside the micro-ROS ifdef so bus / servo polling code in the
// Arduino-only CI build can size its buffers consistently.
constexpr size_t NOVA_JOINT_COUNT = 12;

// Latched joint-command state — written by the micro-ROS subscriber
// callback (when present) and consumed by broadcast_servo_commands().
// Lives outside the micro-ROS ifdef so the CI build still links against
// the bus driver. In CI / Arduino-only mode this array stays zeroed.
volatile uint32_t joint_cmd_rx_count = 0;
double latched_cmd_position[NOVA_JOINT_COUNT] = {0};

// ---------------- Command-staleness failsafe ----------------
// If /joint_commands stops arriving (USB cable out, Jetson panic, agent
// crash) the broadcast path would otherwise re-send the last target
// forever — robot frozen mid-step with torque held until LVC. Instead:
// after NOVA_CMD_STALE_TIMEOUT_US without a fresh command, overwrite the
// latched targets with the latest MEASURED positions (freeze in place —
// the slew limiter turns that into a gentle decel) and flag /command_stale.
// "Neutral stand pose" is deliberately NOT used: calibration offsets live
// on the Jetson, so raw stand-pose values are meaningless at this layer.
// Recovery is automatic — any fresh command clears the flag and slews
// from the frozen pose to the new target.
#ifndef NOVA_CMD_STALE_TIMEOUT_US
#define NOVA_CMD_STALE_TIMEOUT_US 500000UL   // 500 ms
#endif
uint32_t last_joint_cmd_us = 0;   // stamped in joint_cmd_callback (executor
                                  // runs in tick context — no ISR race)
bool     cmd_stale = false;
uint32_t cmd_stale_events = 0;    // lifetime count, for diagnostics

// Safety state machine — instance + clear-request flag declared up here so
// the bus-write gate (broadcast_servo_commands()) can refuse to fire when a
// latch is active. Definition body lives in safety_state.h.
nova::SafetyFSM safety_fsm;
volatile bool safety_clear_request = false;

// Boot self-test result bitmap — set in setup() after GPIO pinMode but
// before the tick timer starts. Bits:
//   0 = ESTOP_PIN read LOW at boot (button pressed at startup — operator
//       fault, refuse to arm)
//   1 = BATTERY_LOW_PIN read HIGH at boot (pack already under 13.0V —
//       refuse to arm)
// Non-zero result means safety_fsm pre-seeded to a latched fault.
uint8_t boot_self_test_flags = 0;

#ifndef NOVA_BUILD_GIT_SHA
#define NOVA_BUILD_GIT_SHA "unknown"
#endif

#ifdef NOVA_USE_MICRO_ROS
#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/int32.h>
#include <std_msgs/msg/bool.h>
#include <std_msgs/msg/float32_multi_array.h>
#include <std_msgs/msg/string.h>
#include <sensor_msgs/msg/joint_state.h>
#endif

// ---------------- Pinout ----------------
// UART2 → 74HC125 → Feetech bus
constexpr uint8_t BUS_RX_PIN     = 7;   // Serial2 RX
constexpr uint8_t BUS_TX_PIN     = 8;   // Serial2 TX
constexpr uint8_t BUS_OE_TX_PIN  = 6;   // 74HC125 OE for TX gate (HIGH = enable TX)
constexpr uint8_t BUS_OE_RX_PIN  = 5;   // 74HC125 OE for RX gate (LOW = enable RX)
// I2C0 (Wire) — INA226 ×3
constexpr uint8_t I2C_SDA_PIN    = 18;
constexpr uint8_t I2C_SCL_PIN    = 19;
// Safety GPIO
constexpr uint8_t ESTOP_PIN       = 2;   // input from E-stop NC contact (LOW = pressed)
constexpr uint8_t BATTERY_LOW_PIN = 3;   // input from 13.0V comparator (HIGH = below 13.0V)
constexpr uint8_t LED_PIN         = LED_BUILTIN;

// ---------------- Feetech bus (Pattern B half-duplex via 74HC125) ----------------
// Bus class owns the OE pins + Serial2; service_bus_stub still just toggles
// direction until 74HC125 + a real servo are on the bench. Once hardware
// lands, replace the toggle with a round-robin ping/read cycle — the Bus
// instance already has ping(), read_position(), write_goal_position(), and
// sync_write_goal_positions() ready to go.
feetech::Bus servo_bus(BUS_OE_TX_PIN, BUS_OE_RX_PIN, NOVA_BUS_BAUD);

inline void bus_set_tx() { servo_bus.set_tx(); }
inline void bus_set_rx() { servo_bus.set_rx(); }

// ---------------- Stubs (TODO list) ----------------
// service_bus_stub: replace with round-robin ping/read when servos on bench
// read_ina226_stub: integrate Rob Tillaart's INA226 library, 3 rails
// publish_topics:   wire micro-ROS publishers when NOVA_USE_MICRO_ROS defined

void service_bus_stub() {
  // Toggle direction pins so we can scope them during bring-up
  bus_set_tx();
  delayMicroseconds(1);
  bus_set_rx();
}

// ---------------- INA226 power-rail telemetry ----------------
// 3 mandatory rails per BOM v3.4. Optional 4th (L2 LiDAR) gated by
// NOVA_INA226_L2. Round-robin one rail per tick so each chip refreshes at
// LOOP_HZ / N_RAILS (≈ 66 Hz for 3 rails @ 200 Hz tick) — well above the
// 10 Hz /diagnostics publish rate.
nova::Rail rail_leg   (nova::INA226_ADDR_LEG,    "leg_7v5");
nova::Rail rail_hip   (nova::INA226_ADDR_HIP,    "hip_12v");
nova::Rail rail_jetson(nova::INA226_ADDR_JETSON, "jetson_12v");
#ifdef NOVA_INA226_L2
nova::Rail rail_l2    (nova::INA226_ADDR_L2,     "l2_12v");
constexpr uint8_t INA226_RAIL_COUNT = 4;
nova::Rail* rails[INA226_RAIL_COUNT] = {&rail_leg, &rail_hip, &rail_jetson, &rail_l2};
#else
constexpr uint8_t INA226_RAIL_COUNT = 3;
nova::Rail* rails[INA226_RAIL_COUNT] = {&rail_leg, &rail_hip, &rail_jetson};
#endif
uint8_t ina226_rr_idx = 0;

void read_ina226_stub() {
  // Round-robin sample. Single chip per tick keeps the I²C bus + main loop
  // budget tight; full set refreshes every INA226_RAIL_COUNT ticks.
  rails[ina226_rr_idx]->poll();
  ina226_rr_idx = (ina226_rr_idx + 1) % INA226_RAIL_COUNT;
}

// ---------------- Servo round-robin telemetry ----------------
// One servo read per tick (5 ms budget at 200 Hz). Bus read costs ~80 µs TX
// + ~1.5 ms response (or full timeout if servo absent). At 12 joints,
// full-fleet refresh = 60 ms = ~17 Hz per joint — adequate for /joint_states
// at the planned 100 Hz aggregate. Servo IDs are 1..NOVA_JOINT_COUNT by
// convention; ID 0 is unused (reserved), ID 0xFE is broadcast.
constexpr uint8_t SERVO_ID_BASE = 1;
uint8_t servo_rr_idx = 0;     // 0..NOVA_JOINT_COUNT-1 → servo ID = SERVO_ID_BASE + idx
// Per-servo telemetry. All raw — gait layer on the Jetson converts to
// radians + Newton-metres using URDF + servo calibration.
//   position:    0..4095 (12-bit encoder)
//   velocity:    int16 sign-magnitude (STS3215 convention)
//   load:        int16 sign-magnitude (0..1000 raw, % of stall torque)
//   voltage:     u8 in 0.1 V units (e.g. 74 = 7.4 V)
//   temperature: u8 in °C (raw, 0..100 typical operating range)
volatile uint16_t servo_position_raw[NOVA_JOINT_COUNT] = {0};
volatile int16_t  servo_velocity_raw[NOVA_JOINT_COUNT] = {0};
volatile int16_t  servo_load_raw    [NOVA_JOINT_COUNT] = {0};
volatile uint8_t  servo_voltage_raw [NOVA_JOINT_COUNT] = {0};
volatile uint8_t  servo_temp_c      [NOVA_JOINT_COUNT] = {0};

// Last-read success bitmask — bit i set ⇒ servo (SERVO_ID_BASE + i) has
// answered at least once since boot. Exposed as /servo_present_mask for
// host-side fleet inventory.
volatile uint16_t servo_present_mask = 0;

// Categorised bus-error counters (monotonic). All start zero; a non-zero
// value on a host dashboard means something went wrong in that category
// since boot. /servo_read_err_count = sum of these three for backward compat.
volatile uint32_t servo_err_timeout   = 0;
volatile uint32_t servo_err_bad_frame = 0;
volatile uint32_t servo_err_servo     = 0;
volatile uint32_t servo_read_err_count = 0;

void poll_one_servo() {
  uint8_t id = SERVO_ID_BASE + servo_rr_idx;
  // 8-byte sweep: REG_PRESENT_POSITION_L (0x38) through
  // REG_PRESENT_TEMPERATURE (0x3F). Layout:
  //   [0..1] = PRESENT_POSITION_L/H   (u16 LE)
  //   [2..3] = PRESENT_VELOCITY_L/H   (s16 LE sign-magnitude)
  //   [4..5] = PRESENT_LOAD_L/H       (s16 LE sign-magnitude)
  //   [6]    = PRESENT_VOLTAGE        (u8, 0.1 V units)
  //   [7]    = PRESENT_TEMPERATURE    (u8, °C)
  // One frame, full per-joint snapshot. Wire cost ~80 µs TX + ~150 µs
  // servo turnaround + 14-byte response = ~370 µs at 1 Mbaud.
  uint8_t buf[8];
  feetech::Bus::Result rc = servo_bus.read_block(
      id, feetech::REG_PRESENT_POSITION_L, 8, buf, /*timeout_us=*/2500);
  if (rc == feetech::Bus::OK) {
    servo_position_raw[servo_rr_idx] = feetech::pack_u16_le(buf[0], buf[1]);
    servo_velocity_raw[servo_rr_idx] = feetech::pack_s16_le(buf[2], buf[3]);
    servo_load_raw    [servo_rr_idx] = feetech::pack_s16_le(buf[4], buf[5]);
    servo_voltage_raw [servo_rr_idx] = buf[6];
    servo_temp_c      [servo_rr_idx] = buf[7];
    servo_present_mask |= (uint16_t)(1u << servo_rr_idx);
  } else {
    servo_read_err_count++;
    switch (rc) {
      case feetech::Bus::ERR_TIMEOUT:   servo_err_timeout++;   break;
      case feetech::Bus::ERR_BAD_FRAME: servo_err_bad_frame++; break;
      case feetech::Bus::ERR_SERVO:     servo_err_servo++;     break;
      default: break;
    }
  }
  servo_rr_idx = (servo_rr_idx + 1) % NOVA_JOINT_COUNT;
}

// ---------------- Servo command broadcast ----------------
// Every CMD_BROADCAST_DECIMATE ticks (= 40 Hz at 200 Hz tick) send a
// SYNC_WRITE goal-position frame to all 12 servos with the latest latched
// commands. Decimation keeps bus utilization sane and matches typical gait
// command rate. Gated on safety_fsm.motion_enabled() — never writes while
// E-stop or battery-low are latched.
constexpr uint8_t CMD_BROADCAST_DECIMATE = 5;   // 200 Hz / 5 = 40 Hz
uint8_t cmd_decimate_count = 0;

// Slew limit — max raw-units change per broadcast (= per 25 ms at 40 Hz).
// STS3215 full travel 0..4095 = 360°. At 50 raw units / 25 ms = 4.4°/25ms
// ≈ 176°/s, well under the servo's mechanical capability but slow enough
// that a step-jump command (e.g. host crash → restart at a far pose) ramps
// in instead of slamming. Tune in `NOVA_SLEW_MAX_DELTA` build flag.
#ifndef NOVA_SLEW_MAX_DELTA
#define NOVA_SLEW_MAX_DELTA 50
#endif

// Per-joint last-commanded raw goal, used to compute the slew-limited
// next value. Initialized to "no command yet" sentinel; on first broadcast
// after boot, ramp is bypassed (first write = current latched target).
constexpr uint16_t SLEW_UNINIT = 0xFFFF;
uint16_t last_cmd_goal[NOVA_JOINT_COUNT];

inline void slew_init_all() {
  for (size_t i = 0; i < NOVA_JOINT_COUNT; i++) last_cmd_goal[i] = SLEW_UNINIT;
}

void broadcast_servo_commands() {
  if (!safety_fsm.motion_enabled()) return;
  // Never write the bus before the first real command arrives — the latched
  // array boots as all-zeros, and SYNC_WRITEing raw 0 to 12 servos at
  // power-on would slam every joint to one end of travel.
  if (joint_cmd_rx_count == 0) return;
  cmd_decimate_count++;
  if (cmd_decimate_count < CMD_BROADCAST_DECIMATE) return;
  cmd_decimate_count = 0;

  uint8_t ids[NOVA_JOINT_COUNT];
  uint16_t goals[NOVA_JOINT_COUNT];
  for (size_t i = 0; i < NOVA_JOINT_COUNT; i++) {
    ids[i] = SERVO_ID_BASE + i;
    double v = latched_cmd_position[i];
    if (v < 0.0)    v = 0.0;
    if (v > 4095.0) v = 4095.0;
    uint16_t target = (uint16_t)v;

    uint16_t out;
    if (last_cmd_goal[i] == SLEW_UNINIT) {
      out = target;                 // first write — accept as-is
    } else {
      int32_t delta = (int32_t)target - (int32_t)last_cmd_goal[i];
      if (delta >  (int32_t)NOVA_SLEW_MAX_DELTA) delta =  (int32_t)NOVA_SLEW_MAX_DELTA;
      if (delta < -(int32_t)NOVA_SLEW_MAX_DELTA) delta = -(int32_t)NOVA_SLEW_MAX_DELTA;
      out = (uint16_t)((int32_t)last_cmd_goal[i] + delta);
    }
    last_cmd_goal[i] = out;
    goals[i] = out;
  }
  servo_bus.sync_write_goal_positions(ids, goals, NOVA_JOINT_COUNT);
}

// ---------------- Real-time loop ----------------
elapsedMillis heartbeat_ms;
elapsedMillis stats_ms;
elapsedMillis power_rails_ms;
elapsedMillis servo_health_ms;
const uint32_t TICK_PERIOD_US = 1000000UL / NOVA_LOOP_HZ;
const uint32_t HEARTBEAT_PERIOD_MS = 1000;
const uint32_t STATS_PERIOD_MS = 1000;
const uint32_t POWER_RAILS_PERIOD_MS = 100;    // 10 Hz — matches Phase 1 spec
const uint32_t SERVO_HEALTH_PERIOD_MS = 200;   // 5 Hz — voltage + temperature

// IntervalTimer ISR drives the tick. Handler in loop() measures
// ISR-fire → handler-entry latency = pure scheduling jitter (target: a
// few µs, far under the <100 µs p99 acceptance gate).
IntervalTimer tick_timer;
volatile bool     tick_pending = false;
volatile uint32_t tick_isr_us  = 0;     // micros() captured in ISR
volatile uint32_t tick_missed  = 0;     // count of ISR fires that found tick_pending already set

// Software watchdog — main loop must increment main_loop_iter at least once
// per WATCHDOG_TICKS ISR fires or the CPU is reset via the ARM system reset
// request register. At 200 Hz tick and 200 ticks budget = 1 s of no main-
// loop progress before reset. Tunable via -D NOVA_WATCHDOG_TICKS=<n>.
#ifndef NOVA_WATCHDOG_TICKS
#define NOVA_WATCHDOG_TICKS 200
#endif
volatile uint32_t main_loop_iter = 0;
volatile uint32_t last_observed_iter = 0;
volatile uint32_t no_progress_ticks = 0;
volatile uint32_t watchdog_resets   = 0;    // survives across resets? no — but
                                            // useful for in-session diag if a
                                            // reset was caught + recovered.

void tick_isr() {
  if (tick_pending) tick_missed++;
  tick_pending = true;
  tick_isr_us  = micros();

  // Software watchdog: did the main loop advance since last ISR fire?
  uint32_t iter_now = main_loop_iter;
  if (iter_now != last_observed_iter) {
    last_observed_iter = iter_now;
    no_progress_ticks = 0;
  } else {
    no_progress_ticks++;
    if (no_progress_ticks >= NOVA_WATCHDOG_TICKS) {
      // SCB AIRCR — system reset request. VECTKEY = 0x05FA, SYSRESETREQ = 1.
      // ARMv7-M canonical reboot path; no return. Teensy 4 imxrt.h exposes
      // the AIRCR register directly as a uint32_t macro.
      SCB_AIRCR = 0x05FA0004;
      while (1) {}   // wait for reset to land
    }
  }
}

// Histogram is per response-latency in microseconds. Bucket width 2 µs,
// 64 buckets = 0..128 µs, last bucket = overflow. Reset each report.
constexpr int      HIST_BUCKETS    = 64;
constexpr uint32_t HIST_BUCKET_US  = 2;
uint32_t hist[HIST_BUCKETS];
uint32_t max_latency_us  = 0;
uint32_t tick_count_window = 0;

// Per-tick handler execution time histogram — separate from response-latency.
// Bucket width 10 µs, 64 buckets = 0..640 µs, last = overflow. Captures the
// cost of the work inside the tick (bus, INA226 poll, micro-ROS pubs).
constexpr int      EXEC_HIST_BUCKETS   = 64;
constexpr uint32_t EXEC_HIST_BUCKET_US = 10;
uint32_t exec_hist[EXEC_HIST_BUCKETS];
uint32_t max_exec_us = 0;

#ifdef NOVA_USE_MICRO_ROS
rcl_publisher_t heartbeat_pub;
rcl_publisher_t loop_max_pub;
rcl_publisher_t loop_p99_pub;
rcl_publisher_t loop_exec_max_pub;
rcl_publisher_t loop_exec_p99_pub;
rcl_publisher_t tick_missed_pub;
rcl_publisher_t joint_states_pub;
rcl_publisher_t estop_pub;
rcl_publisher_t battery_low_pub;
rcl_publisher_t safety_state_pub;
rcl_publisher_t command_stale_pub;
rcl_publisher_t power_rails_pub;
rcl_publisher_t joint_cmd_rx_pub;
rcl_publisher_t servo_present_pub;
rcl_publisher_t servo_read_err_pub;
rcl_publisher_t servo_err_timeout_pub;
rcl_publisher_t servo_err_bad_frame_pub;
rcl_publisher_t servo_err_servo_pub;
rcl_publisher_t firmware_version_pub;
rcl_publisher_t servo_voltage_pub;
rcl_publisher_t servo_temperature_pub;
rcl_subscription_t joint_cmd_sub;
rcl_subscription_t safety_clear_sub;

std_msgs__msg__Int32 heartbeat_msg;
std_msgs__msg__Int32 loop_max_msg;
std_msgs__msg__Int32 loop_p99_msg;
std_msgs__msg__Int32 loop_exec_max_msg;
std_msgs__msg__Int32 loop_exec_p99_msg;
std_msgs__msg__Int32 tick_missed_msg;
std_msgs__msg__Int32 safety_state_msg;
std_msgs__msg__Int32 joint_cmd_rx_msg;
std_msgs__msg__Int32 servo_present_msg;
std_msgs__msg__Int32 servo_read_err_msg;
std_msgs__msg__Int32 servo_err_timeout_msg;
std_msgs__msg__Int32 servo_err_bad_frame_msg;
std_msgs__msg__Int32 servo_err_servo_msg;
std_msgs__msg__Bool  safety_clear_msg;
std_msgs__msg__Float32MultiArray power_rails_msg;
std_msgs__msg__String firmware_version_msg;
// Static backing for firmware version string — built once at startup, never
// reallocated. Includes git SHA from build flag.
constexpr size_t FIRMWARE_VERSION_MAX_LEN = 64;
char firmware_version_buf[FIRMWARE_VERSION_MAX_LEN];

// Per-joint voltage + temperature MultiArrays — 12 floats each, published
// at 5 Hz (every 5th heartbeat sub-tick).
std_msgs__msg__Float32MultiArray servo_voltage_msg;
std_msgs__msg__Float32MultiArray servo_temperature_msg;
std_msgs__msg__Bool  estop_msg;
std_msgs__msg__Bool  battery_low_msg;
std_msgs__msg__Bool  command_stale_msg;
sensor_msgs__msg__JointState joint_states_msg;
sensor_msgs__msg__JointState joint_cmd_msg;

// Backing storage for JointState arrays (pub + sub). Names + frame_id stay
// empty for now — see header note.
double js_position[NOVA_JOINT_COUNT];
double js_velocity[NOVA_JOINT_COUNT];
double js_effort  [NOVA_JOINT_COUNT];
double cmd_position[NOVA_JOINT_COUNT];
double cmd_velocity[NOVA_JOINT_COUNT];
double cmd_effort  [NOVA_JOINT_COUNT];

rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;
rclc_executor_t executor;

#define RCCHECK(fn) { rcl_ret_t rc = fn; if (rc != RCL_RET_OK) { /* hold LED on to flag init fail */ digitalWrite(LED_PIN, HIGH); while(1) { delay(100); } } }
#define RCSOFTCHECK(fn) { rcl_ret_t rc = fn; (void)rc; }

void joint_cmd_callback(const void* msgin) {
  const sensor_msgs__msg__JointState* m = (const sensor_msgs__msg__JointState*)msgin;
  size_t n = m->position.size < NOVA_JOINT_COUNT ? m->position.size : NOVA_JOINT_COUNT;
  for (size_t i = 0; i < n; i++) latched_cmd_position[i] = m->position.data[i];
  joint_cmd_rx_count++;
  last_joint_cmd_us = micros();   // staleness-failsafe freshness stamp
}

// /safety_clear sub callback — Bool; data=true requests a latch clear.
// Body defined after the FSM globals (below the #endif).
void safety_clear_callback(const void* msgin);

inline void joint_state_bind(sensor_msgs__msg__JointState* m,
                             double* pos, double* vel, double* eff) {
  m->name.data = NULL;        m->name.size = 0;        m->name.capacity = 0;
  m->position.data = pos;     m->position.size = NOVA_JOINT_COUNT; m->position.capacity = NOVA_JOINT_COUNT;
  m->velocity.data = vel;     m->velocity.size = NOVA_JOINT_COUNT; m->velocity.capacity = NOVA_JOINT_COUNT;
  m->effort.data   = eff;     m->effort.size   = NOVA_JOINT_COUNT; m->effort.capacity   = NOVA_JOINT_COUNT;
  m->header.frame_id.data = NULL; m->header.frame_id.size = 0; m->header.frame_id.capacity = 0;
  m->header.stamp.sec = 0;        m->header.stamp.nanosec = 0;
}
#endif

// Power-rails snapshot buffer — 9 floats (V, A, W per rail × leg/hip/jetson).
// Filled every POWER_RAILS_PERIOD_MS from INA226 Rail samples regardless of
// micro-ROS build; the Float32MultiArray publish itself is ifdef'd.
constexpr size_t POWER_RAILS_FIELDS = 9;
float power_rails_data[POWER_RAILS_FIELDS];

// Per-joint voltage + temperature buffers — see servo_voltage_msg /
// servo_temperature_msg in the micro-ROS block. Lives outside the ifdef so
// the 5 Hz conversion loop runs in both build envs.
float servo_voltage_data    [NOVA_JOINT_COUNT] = {0};
float servo_temperature_data[NOVA_JOINT_COUNT] = {0};

#ifdef NOVA_USE_MICRO_ROS
void safety_clear_callback(const void* msgin) {
  const std_msgs__msg__Bool* m = (const std_msgs__msg__Bool*)msgin;
  if (m->data) safety_clear_request = true;
}
#endif

// Walk histogram cumulatively, return bucket-midpoint µs where cumulative
// count first exceeds 99 % of total. Overflow bucket reports n_buckets *
// bucket_us. Used for both response-latency (hist, 2 µs buckets) and
// exec-time (exec_hist, 10 µs buckets) histograms.
uint32_t compute_p99_us(const uint32_t* h, int n_buckets, uint32_t bucket_us,
                        uint32_t total_count) {
  if (total_count == 0) return 0;
  uint32_t target = (total_count * 99 + 99) / 100;   // ceil(0.99 * n)
  uint32_t cum = 0;
  for (int i = 0; i < n_buckets; i++) {
    cum += h[i];
    if (cum >= target) return i * bucket_us + bucket_us / 2;
  }
  return n_buckets * bucket_us;
}

void setup() {
  // GPIO directions
  pinMode(ESTOP_PIN, INPUT_PULLUP);
  pinMode(BATTERY_LOW_PIN, INPUT_PULLDOWN);
  pinMode(LED_PIN, OUTPUT);

  // Feetech bus init (OE pinModes + Serial2.begin + default to RX).
  servo_bus.begin();

  // USB-CDC for host logging (will become micro-ROS transport once enabled)
  Serial.begin(115200);

  // I²C bus for INA226s. Teensy 4.1 Wire = SDA pin 18, SCL pin 19 (matches
  // pin constants above). 400 kHz keeps per-read I²C cost ≲ 200 µs.
  Wire.begin();
  Wire.setClock(400000);
  for (uint8_t i = 0; i < INA226_RAIL_COUNT; i++) rails[i]->begin();

  // Slew limiter — initialize per-joint history to UNINIT so the first
  // broadcast after boot accepts the latched goal verbatim (no false ramp
  // from a previous boot's residual value).
  slew_init_all();

  // Boot servo ping sweep — one-shot inventory of the bus. Populates
  // servo_present_mask before the tick loop starts so the first
  // /servo_present_mask publish reports actual fleet presence rather than
  // waiting for the round-robin reader to discover each joint over the
  // first ~720 ms. ~1 ms per missing servo × 12 worst case = ~12 ms total
  // delay in setup() — fine, before tick_timer.begin().
  for (uint8_t i = 0; i < NOVA_JOINT_COUNT; i++) {
    if (servo_bus.ping(SERVO_ID_BASE + i, /*timeout_us=*/1000) == feetech::Bus::OK) {
      servo_present_mask |= (uint16_t)(1u << i);
    }
  }

  // Boot self-test: sanity-check safety GPIO before arming. If E-stop is
  // already pressed, or battery-low comparator already asserted, pre-seed
  // the safety FSM into the matching latched state — the operator must
  // resolve and clear before any servo writes can fire.
  bool estop_boot   = (digitalRead(ESTOP_PIN) == LOW);
  bool batt_low_boot = (digitalRead(BATTERY_LOW_PIN) == HIGH);
  if (estop_boot)   boot_self_test_flags |= 0x01;
  if (batt_low_boot) boot_self_test_flags |= 0x02;
  if (boot_self_test_flags) {
    // Force a few update() ticks so the FSM debounce reaches latch.
    for (uint8_t i = 0; i < nova::SafetyFSM::BATT_LOW_DEBOUNCE_TICKS + 1; i++) {
      safety_fsm.update(estop_boot, batt_low_boot);
    }
  }

#ifdef NOVA_USE_MICRO_ROS
  set_microros_serial_transports(Serial);
  delay(2000);  // give agent time to attach

  allocator = rcl_get_default_allocator();
  RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));
  RCCHECK(rclc_node_init_default(&node, "nova_teensy", "", &support));
  RCCHECK(rclc_publisher_init_default(
      &heartbeat_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "heartbeat"));
  RCCHECK(rclc_publisher_init_default(
      &loop_max_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "loop_max_us"));
  RCCHECK(rclc_publisher_init_default(
      &loop_p99_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "loop_p99_us"));
  RCCHECK(rclc_publisher_init_default(
      &loop_exec_max_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "loop_exec_max_us"));
  RCCHECK(rclc_publisher_init_default(
      &loop_exec_p99_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "loop_exec_p99_us"));
  RCCHECK(rclc_publisher_init_default(
      &tick_missed_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "tick_missed_count"));
  RCCHECK(rclc_publisher_init_default(
      &joint_states_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
      "joint_states"));
  RCCHECK(rclc_publisher_init_default(
      &estop_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
      "estop"));
  RCCHECK(rclc_publisher_init_default(
      &battery_low_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
      "battery_low"));
  RCCHECK(rclc_publisher_init_default(
      &safety_state_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "safety_state"));
  RCCHECK(rclc_publisher_init_default(
      &command_stale_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
      "command_stale"));
  RCCHECK(rclc_subscription_init_default(
      &safety_clear_sub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
      "safety_clear"));
  RCCHECK(rclc_publisher_init_default(
      &power_rails_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
      "power_rails"));
  // Bind the Float32MultiArray data sequence to our static buffer. Layout
  // dim sequence stays empty (consumers read by index per the documented
  // order: leg_v, leg_a, leg_w, hip_v, hip_a, hip_w, jetson_v, jetson_a,
  // jetson_w).
  power_rails_msg.data.data     = power_rails_data;
  power_rails_msg.data.size     = POWER_RAILS_FIELDS;
  power_rails_msg.data.capacity = POWER_RAILS_FIELDS;
  power_rails_msg.layout.dim.data     = NULL;
  power_rails_msg.layout.dim.size     = 0;
  power_rails_msg.layout.dim.capacity = 0;
  power_rails_msg.layout.data_offset  = 0;
  for (size_t i = 0; i < POWER_RAILS_FIELDS; i++) power_rails_data[i] = 0.0f;
  RCCHECK(rclc_publisher_init_default(
      &joint_cmd_rx_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "joint_cmd_rx_count"));
  RCCHECK(rclc_publisher_init_default(
      &servo_present_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "servo_present_mask"));
  RCCHECK(rclc_publisher_init_default(
      &servo_read_err_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "servo_read_err_count"));
  RCCHECK(rclc_publisher_init_default(
      &servo_err_timeout_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "servo_err_timeout"));
  RCCHECK(rclc_publisher_init_default(
      &servo_err_bad_frame_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "servo_err_bad_frame"));
  RCCHECK(rclc_publisher_init_default(
      &servo_err_servo_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "servo_err_servo"));
  RCCHECK(rclc_publisher_init_default(
      &firmware_version_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
      "firmware_version"));
  RCCHECK(rclc_publisher_init_default(
      &servo_voltage_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
      "servo_voltage"));
  RCCHECK(rclc_publisher_init_default(
      &servo_temperature_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
      "servo_temperature"));
  // Bind voltage + temperature data buffers; layout dim sequences empty.
  servo_voltage_msg.data.data         = servo_voltage_data;
  servo_voltage_msg.data.size         = NOVA_JOINT_COUNT;
  servo_voltage_msg.data.capacity     = NOVA_JOINT_COUNT;
  servo_voltage_msg.layout.dim.data     = NULL;
  servo_voltage_msg.layout.dim.size     = 0;
  servo_voltage_msg.layout.dim.capacity = 0;
  servo_voltage_msg.layout.data_offset  = 0;
  servo_temperature_msg.data.data     = servo_temperature_data;
  servo_temperature_msg.data.size     = NOVA_JOINT_COUNT;
  servo_temperature_msg.data.capacity = NOVA_JOINT_COUNT;
  servo_temperature_msg.layout.dim.data     = NULL;
  servo_temperature_msg.layout.dim.size     = 0;
  servo_temperature_msg.layout.dim.capacity = 0;
  servo_temperature_msg.layout.data_offset  = 0;
  for (size_t i = 0; i < NOVA_JOINT_COUNT; i++) {
    servo_voltage_data[i] = 0.0f;
    servo_temperature_data[i] = 0.0f;
  }
  // Bind firmware version buffer + write the version once at startup.
  snprintf(firmware_version_buf, FIRMWARE_VERSION_MAX_LEN,
           "nova-teensy %s loop=%dHz", NOVA_BUILD_GIT_SHA, (int)NOVA_LOOP_HZ);
  firmware_version_msg.data.data     = firmware_version_buf;
  firmware_version_msg.data.size     = strlen(firmware_version_buf);
  firmware_version_msg.data.capacity = FIRMWARE_VERSION_MAX_LEN;
  RCCHECK(rclc_subscription_init_default(
      &joint_cmd_sub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
      "joint_commands"));

  joint_state_bind(&joint_states_msg, js_position, js_velocity, js_effort);
  joint_state_bind(&joint_cmd_msg,    cmd_position, cmd_velocity, cmd_effort);
  for (size_t i = 0; i < NOVA_JOINT_COUNT; i++) {
    js_position[i] = 0.0; js_velocity[i] = 0.0; js_effort[i] = 0.0;
    latched_cmd_position[i] = 0.0;
  }

  // Executor sized for 2 subs: joint_commands + safety_clear.
  RCCHECK(rclc_executor_init(&executor, &support.context, 2, &allocator));
  RCCHECK(rclc_executor_add_subscription(
      &executor, &joint_cmd_sub, &joint_cmd_msg,
      &joint_cmd_callback, ON_NEW_DATA));
  RCCHECK(rclc_executor_add_subscription(
      &executor, &safety_clear_sub, &safety_clear_msg,
      &safety_clear_callback, ON_NEW_DATA));

  heartbeat_msg.data = 0;
  estop_msg.data = false;
  battery_low_msg.data = false;
  command_stale_msg.data = false;
#endif

#ifndef NOVA_USE_MICRO_ROS
  // First-boot info to USB-CDC (only when not micro-ROS — agent owns USB)
  delay(500);
  Serial.println("[nova-teensy] boot");
  Serial.print("  loop hz: ");      Serial.println(NOVA_LOOP_HZ);
  Serial.print("  bus baud: ");     Serial.println(NOVA_BUS_BAUD);
  Serial.println("  micro-ROS: disabled (build with -D NOVA_USE_MICRO_ROS on Jetson)");
#endif

  // Start hardware-driven tick. Must come after all init so the ISR
  // doesn't fire into half-built state. Teensy 4.x IntervalTimer takes
  // microseconds; uses one of the 4 free GPT/PIT timer channels.
  tick_timer.begin(tick_isr, TICK_PERIOD_US);
}

void loop() {
  // Software-watchdog kick — bump the progress counter every iteration.
  // The ISR observes this from a hardware timer, independent of any main-
  // loop pathology (blocking publish, deadlocked rcl call, etc.).
  main_loop_iter++;

  // Atomic snapshot of ISR flag + timestamp
  noInterrupts();
  bool     pending = tick_pending;
  uint32_t fire_us = tick_isr_us;
  tick_pending = false;
  interrupts();

  if (pending) {
    // Response latency = elapsed time from ISR firing to handler entry.
    // Bare metric is "how late are we to service the tick" — sub-µs is
    // possible on M7 when no contending ISR/spin work blocks the loop().
    uint32_t handler_start_us = micros();
    uint32_t latency_us = handler_start_us - fire_us;

    uint32_t b = latency_us / HIST_BUCKET_US;
    if (b >= (uint32_t)HIST_BUCKETS) b = HIST_BUCKETS - 1;
    hist[b]++;
    if (latency_us > max_latency_us) max_latency_us = latency_us;
    tick_count_window++;

    // Servo bus — one read per tick (round-robin) + decimated SYNC_WRITE
    // broadcast of the latest joint_commands. Both no-ops at the wire level
    // until a real STS3215 is on the bench: poll_one_servo() times out and
    // increments servo_read_err_count; broadcast_servo_commands() sends the
    // sync-write frame but no servo will ACK (broadcast doesn't expect
    // ACK anyway). The OE pin toggle in service_bus_stub() is no longer
    // needed — Bus::transmit_blocking() handles direction switching.
    // Command-staleness failsafe — evaluate BEFORE the broadcast so a
    // freeze takes effect on this tick's SYNC_WRITE, not the next.
    if (joint_cmd_rx_count > 0) {
      bool stale_now =
          (uint32_t)(handler_start_us - last_joint_cmd_us) > NOVA_CMD_STALE_TIMEOUT_US;
      if (stale_now && !cmd_stale) {
        cmd_stale = true;
        cmd_stale_events++;
        // Freeze: retarget every joint that has ever answered a poll to its
        // latest measured position. Joints that never answered keep their
        // last commanded target (no better information exists for them).
        for (size_t i = 0; i < NOVA_JOINT_COUNT; i++) {
          if (servo_present_mask & (uint16_t)(1u << i)) {
            latched_cmd_position[i] = (double)servo_position_raw[i];
          }
        }
      } else if (!stale_now && cmd_stale) {
        cmd_stale = false;   // fresh command arrived — normal slew resumes
      }
    }

    poll_one_servo();
    broadcast_servo_commands();

    // Telemetry sample
    read_ina226_stub();

    // Safety GPIO sense + state-machine update
    bool estop_now = (digitalRead(ESTOP_PIN) == LOW);
    bool batt_low_now = (digitalRead(BATTERY_LOW_PIN) == HIGH);
    nova::SafetyState prev_safety = safety_fsm.state();
    safety_fsm.update(estop_now, batt_low_now);
    if (safety_clear_request) {
      safety_fsm.clear();
      safety_clear_request = false;
    }
    nova::SafetyState curr_safety = safety_fsm.state();
    // On any transition back to NORMAL (clear succeeded), reset the slew
    // history so the next broadcast accepts the current target verbatim
    // rather than ramping from the stale pre-fault goal.
    if (curr_safety == nova::SAFETY_NORMAL && prev_safety != nova::SAFETY_NORMAL) {
      slew_init_all();
    }

#ifdef NOVA_USE_MICRO_ROS
    // Edge-change publish for raw safety signals (host sees the source)
    if (estop_now != estop_msg.data) {
      estop_msg.data = estop_now;
      RCSOFTCHECK(rcl_publish(&estop_pub, &estop_msg, NULL));
    }
    if (batt_low_now != battery_low_msg.data) {
      battery_low_msg.data = batt_low_now;
      RCSOFTCHECK(rcl_publish(&battery_low_pub, &battery_low_msg, NULL));
    }
    // Edge-change publish for the command-staleness failsafe flag
    if (cmd_stale != command_stale_msg.data) {
      command_stale_msg.data = cmd_stale;
      RCSOFTCHECK(rcl_publish(&command_stale_pub, &command_stale_msg, NULL));
    }
    // Edge-change publish for the latched FSM state
    if (curr_safety != prev_safety) {
      safety_state_msg.data = (int32_t)curr_safety;
      RCSOFTCHECK(rcl_publish(&safety_state_pub, &safety_state_msg, NULL));
    }

    // Copy latest servo telemetry into JointState (raw → double). Gait layer
    // on the Jetson converts to radians/rad-per-s/Nm. Servos that haven't
    // answered yet keep their previous value (default 0.0).
    for (size_t i = 0; i < NOVA_JOINT_COUNT; i++) {
      js_position[i] = (double)servo_position_raw[i];
      js_velocity[i] = (double)servo_velocity_raw[i];
      js_effort  [i] = (double)servo_load_raw    [i];
    }
    uint32_t ms = millis();
    joint_states_msg.header.stamp.sec = ms / 1000;
    joint_states_msg.header.stamp.nanosec = (ms % 1000) * 1000000UL;
    RCSOFTCHECK(rcl_publish(&joint_states_pub, &joint_states_msg, NULL));

    // Service incoming subscriptions (joint_commands, safety_clear)
    RCSOFTCHECK(rclc_executor_spin_some(&executor, 0));
#else
    (void)estop_now;
    (void)batt_low_now;
    (void)prev_safety;
    (void)curr_safety;
#endif

    // Exec-time accounting — measure end of handler vs start. Captures the
    // real work cost (bus + I²C + publishes + executor spin) separately
    // from scheduling jitter.
    uint32_t exec_us = micros() - handler_start_us;
    uint32_t eb = exec_us / EXEC_HIST_BUCKET_US;
    if (eb >= (uint32_t)EXEC_HIST_BUCKETS) eb = EXEC_HIST_BUCKETS - 1;
    exec_hist[eb]++;
    if (exec_us > max_exec_us) max_exec_us = exec_us;
  }

  if (heartbeat_ms >= HEARTBEAT_PERIOD_MS) {
    heartbeat_ms = 0;
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));   // 1 Hz LED
#ifdef NOVA_USE_MICRO_ROS
    heartbeat_msg.data++;
    RCSOFTCHECK(rcl_publish(&heartbeat_pub, &heartbeat_msg, NULL));
    joint_cmd_rx_msg.data = (int32_t)joint_cmd_rx_count;
    RCSOFTCHECK(rcl_publish(&joint_cmd_rx_pub, &joint_cmd_rx_msg, NULL));
    servo_present_msg.data = (int32_t)servo_present_mask;
    RCSOFTCHECK(rcl_publish(&servo_present_pub, &servo_present_msg, NULL));
    servo_read_err_msg.data = (int32_t)servo_read_err_count;
    RCSOFTCHECK(rcl_publish(&servo_read_err_pub, &servo_read_err_msg, NULL));
    servo_err_timeout_msg.data   = (int32_t)servo_err_timeout;
    servo_err_bad_frame_msg.data = (int32_t)servo_err_bad_frame;
    servo_err_servo_msg.data     = (int32_t)servo_err_servo;
    RCSOFTCHECK(rcl_publish(&servo_err_timeout_pub,   &servo_err_timeout_msg,   NULL));
    RCSOFTCHECK(rcl_publish(&servo_err_bad_frame_pub, &servo_err_bad_frame_msg, NULL));
    RCSOFTCHECK(rcl_publish(&servo_err_servo_pub,     &servo_err_servo_msg,     NULL));
    // Firmware version — publish every 10 s (1 Hz heartbeat / 10), low-rate
    // identity ping so reconnecting hosts can pick it up without restart.
    static uint32_t fw_pub_count = 0;
    if ((fw_pub_count++ % 10) == 0) {
      RCSOFTCHECK(rcl_publish(&firmware_version_pub, &firmware_version_msg, NULL));
    }
#else
    Serial.print("[nova-teensy] alive t=");
    Serial.println(millis());
#endif
  }

  if (servo_health_ms >= SERVO_HEALTH_PERIOD_MS) {
    servo_health_ms = 0;
    // Convert raw voltage (0.1 V units) + temperature (°C, already cooked)
    // into float arrays. Conversion math stays here — host-side consumers
    // see scaled values, not raw bytes.
    for (size_t i = 0; i < NOVA_JOINT_COUNT; i++) {
      servo_voltage_data[i]     = servo_voltage_raw[i] * 0.1f;
      servo_temperature_data[i] = (float)servo_temp_c[i];
    }
#ifdef NOVA_USE_MICRO_ROS
    RCSOFTCHECK(rcl_publish(&servo_voltage_pub,     &servo_voltage_msg,     NULL));
    RCSOFTCHECK(rcl_publish(&servo_temperature_pub, &servo_temperature_msg, NULL));
#endif
  }

  if (power_rails_ms >= POWER_RAILS_PERIOD_MS) {
    power_rails_ms = 0;
    // Pull the latest per-rail samples into the Float32MultiArray buffer.
    // Order: leg_v leg_a leg_w hip_v hip_a hip_w jetson_v jetson_a jetson_w
    // (4th L2 rail intentionally omitted from this msg even when
    // NOVA_INA226_L2 is defined — host-side consumers expect 9-float layout).
    const nova::RailSample& s_leg    = rail_leg.sample();
    const nova::RailSample& s_hip    = rail_hip.sample();
    const nova::RailSample& s_jetson = rail_jetson.sample();
    power_rails_data[0] = s_leg.bus_voltage_v;
    power_rails_data[1] = s_leg.current_a;
    power_rails_data[2] = s_leg.power_w;
    power_rails_data[3] = s_hip.bus_voltage_v;
    power_rails_data[4] = s_hip.current_a;
    power_rails_data[5] = s_hip.power_w;
    power_rails_data[6] = s_jetson.bus_voltage_v;
    power_rails_data[7] = s_jetson.current_a;
    power_rails_data[8] = s_jetson.power_w;
#ifdef NOVA_USE_MICRO_ROS
    RCSOFTCHECK(rcl_publish(&power_rails_pub, &power_rails_msg, NULL));
#endif
  }

  if (stats_ms >= STATS_PERIOD_MS) {
    stats_ms = 0;
#ifdef NOVA_USE_MICRO_ROS
    loop_max_msg.data = (int32_t)max_latency_us;
    loop_p99_msg.data = (int32_t)compute_p99_us(
        hist, HIST_BUCKETS, HIST_BUCKET_US, tick_count_window);
    loop_exec_max_msg.data = (int32_t)max_exec_us;
    loop_exec_p99_msg.data = (int32_t)compute_p99_us(
        exec_hist, EXEC_HIST_BUCKETS, EXEC_HIST_BUCKET_US, tick_count_window);
    tick_missed_msg.data = (int32_t)tick_missed;
    RCSOFTCHECK(rcl_publish(&loop_max_pub,      &loop_max_msg,      NULL));
    RCSOFTCHECK(rcl_publish(&loop_p99_pub,      &loop_p99_msg,      NULL));
    RCSOFTCHECK(rcl_publish(&loop_exec_max_pub, &loop_exec_max_msg, NULL));
    RCSOFTCHECK(rcl_publish(&loop_exec_p99_pub, &loop_exec_p99_msg, NULL));
    RCSOFTCHECK(rcl_publish(&tick_missed_pub,   &tick_missed_msg,   NULL));
#endif
    max_latency_us = 0;
    max_exec_us = 0;
    tick_count_window = 0;
    for (int i = 0; i < HIST_BUCKETS; i++)      hist[i]      = 0;
    for (int i = 0; i < EXEC_HIST_BUCKETS; i++) exec_hist[i] = 0;
    // tick_missed is a monotonic counter, NOT reset — let it accumulate so
    // host-side dashboards can spot a long-term regression.
  }
}
