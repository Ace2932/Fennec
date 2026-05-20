// Nova-SM3 LE — Teensy 4.1 firmware skeleton
// Pattern B bus master per BOM v3.3
//
// Status (2026-05-19): Arduino-only compile-green scaffold. micro-ROS
// integration is gated on NOVA_USE_MICRO_ROS — leave undefined until
// we move firmware builds to the Jetson (Mac micro-ROS build path is
// brittle: needs Python 3.10/3.11 + ROS dev libs). Stubs printed over
// USB-CDC at NOVA_LOOP_HZ for now.

#include <Arduino.h>

#ifdef NOVA_USE_MICRO_ROS
#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <std_msgs/msg/int32.h>
#include <std_msgs/msg/bool.h>
#include <sensor_msgs/msg/joint_state.h>
// Joint count = 12 (4 legs × 3 joints). Names/frame_id intentionally empty
// in skeleton — Nova URDF wiring lands once gait controller is on Jetson.
constexpr size_t NOVA_JOINT_COUNT = 12;
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

// ---------------- Bus direction control (74HC125) ----------------
inline void bus_set_tx() {
  digitalWrite(BUS_OE_TX_PIN, HIGH);  // drive TX onto bus
  digitalWrite(BUS_OE_RX_PIN, HIGH);  // mute RX gate
}

inline void bus_set_rx() {
  digitalWrite(BUS_OE_TX_PIN, LOW);   // mute TX gate
  digitalWrite(BUS_OE_RX_PIN, LOW);   // enable RX from bus
}

// ---------------- Stubs (TODO list) ----------------
// service_bus_stub: port SCServo SDK to TeensyDuino, integrate STS3215 read/write
// read_ina226_stub: integrate Rob Tillaart's INA226 library, 3 rails
// publish_topics:   wire micro-ROS publishers when NOVA_USE_MICRO_ROS defined

void service_bus_stub() {
  // Toggle direction pins so we can scope them during bring-up
  bus_set_tx();
  delayMicroseconds(1);
  bus_set_rx();
}

void read_ina226_stub() {
  // No I2C traffic yet — placeholder for INA226 reads
}

// ---------------- Real-time loop ----------------
elapsedMillis heartbeat_ms;
elapsedMillis stats_ms;
const uint32_t TICK_PERIOD_US = 1000000UL / NOVA_LOOP_HZ;
const uint32_t HEARTBEAT_PERIOD_MS = 1000;
const uint32_t STATS_PERIOD_MS = 1000;
uint32_t prev_tick_us = 0;

// Tick-jitter histogram. Bucket width 100 us, 100 buckets = 0..10 ms,
// last bucket = overflow. Used for per-window p99 — reset each report.
constexpr int      HIST_BUCKETS    = 101;
constexpr uint32_t HIST_BUCKET_US  = 100;
uint32_t hist[HIST_BUCKETS];
uint32_t max_period_us = 0;
uint32_t tick_count_window = 0;

#ifdef NOVA_USE_MICRO_ROS
rcl_publisher_t heartbeat_pub;
rcl_publisher_t loop_max_pub;
rcl_publisher_t loop_p99_pub;
rcl_publisher_t joint_states_pub;
rcl_publisher_t estop_pub;
rcl_publisher_t battery_low_pub;
rcl_publisher_t joint_cmd_rx_pub;
rcl_subscription_t joint_cmd_sub;

std_msgs__msg__Int32 heartbeat_msg;
std_msgs__msg__Int32 loop_max_msg;
std_msgs__msg__Int32 loop_p99_msg;
std_msgs__msg__Int32 joint_cmd_rx_msg;
std_msgs__msg__Bool  estop_msg;
std_msgs__msg__Bool  battery_low_msg;
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

// Latched command state — for the gait/servo layer to consume later.
volatile uint32_t joint_cmd_rx_count = 0;
double latched_cmd_position[NOVA_JOINT_COUNT];

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
}

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

// Walk histogram cumulatively, return bucket-midpoint us where cumulative
// count first exceeds 99% of total. Overflow bucket reports HIST_BUCKETS *
// HIST_BUCKET_US (i.e. >= 10 ms).
uint32_t compute_p99_us() {
  if (tick_count_window == 0) return 0;
  uint32_t target = (tick_count_window * 99 + 99) / 100;  // ceil(0.99 * n)
  uint32_t cum = 0;
  for (int i = 0; i < HIST_BUCKETS; i++) {
    cum += hist[i];
    if (cum >= target) {
      return i * HIST_BUCKET_US + HIST_BUCKET_US / 2;
    }
  }
  return HIST_BUCKETS * HIST_BUCKET_US;
}

void setup() {
  // GPIO directions
  pinMode(BUS_OE_TX_PIN, OUTPUT);
  pinMode(BUS_OE_RX_PIN, OUTPUT);
  pinMode(ESTOP_PIN, INPUT_PULLUP);
  pinMode(BATTERY_LOW_PIN, INPUT_PULLDOWN);
  pinMode(LED_PIN, OUTPUT);
  bus_set_rx();   // default to RX so the bus is free for other masters

  // UART for Feetech bus
  Serial2.begin(NOVA_BUS_BAUD);

  // USB-CDC for host logging (will become micro-ROS transport once enabled)
  Serial.begin(115200);

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
      &joint_cmd_rx_pub,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
      "joint_cmd_rx_count"));
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

  RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));
  RCCHECK(rclc_executor_add_subscription(
      &executor, &joint_cmd_sub, &joint_cmd_msg,
      &joint_cmd_callback, ON_NEW_DATA));

  heartbeat_msg.data = 0;
  estop_msg.data = false;
  battery_low_msg.data = false;
#endif

#ifndef NOVA_USE_MICRO_ROS
  // First-boot info to USB-CDC (only when not micro-ROS — agent owns USB)
  delay(500);
  Serial.println("[nova-teensy] boot");
  Serial.print("  loop hz: ");      Serial.println(NOVA_LOOP_HZ);
  Serial.print("  bus baud: ");     Serial.println(NOVA_BUS_BAUD);
  Serial.println("  micro-ROS: disabled (build with -D NOVA_USE_MICRO_ROS on Jetson)");
#endif
}

void loop() {
  uint32_t now_us = micros();
  if (prev_tick_us == 0) prev_tick_us = now_us;

  // Signed compare handles micros() wraparound at ~71 min.
  if ((int32_t)(now_us - prev_tick_us) >= (int32_t)TICK_PERIOD_US) {
    uint32_t actual_period = now_us - prev_tick_us;
    prev_tick_us += TICK_PERIOD_US;   // nominal stride — no drift from exec time

    // Jitter accounting
    uint32_t b = actual_period / HIST_BUCKET_US;
    if (b >= (uint32_t)HIST_BUCKETS) b = HIST_BUCKETS - 1;
    hist[b]++;
    if (actual_period > max_period_us) max_period_us = actual_period;
    tick_count_window++;

    // Servo bus servicing (stub)
    service_bus_stub();

    // Telemetry sample (stub)
    read_ina226_stub();

    // Safety GPIO sense
    bool estop_now = (digitalRead(ESTOP_PIN) == LOW);
    bool batt_low_now = (digitalRead(BATTERY_LOW_PIN) == HIGH);

#ifdef NOVA_USE_MICRO_ROS
    // Edge-change publish for safety signals
    if (estop_now != estop_msg.data) {
      estop_msg.data = estop_now;
      RCSOFTCHECK(rcl_publish(&estop_pub, &estop_msg, NULL));
    }
    if (batt_low_now != battery_low_msg.data) {
      battery_low_msg.data = batt_low_now;
      RCSOFTCHECK(rcl_publish(&battery_low_pub, &battery_low_msg, NULL));
    }

    // Stamp + publish joint_states (zeros until servo reads land)
    uint32_t ms = millis();
    joint_states_msg.header.stamp.sec = ms / 1000;
    joint_states_msg.header.stamp.nanosec = (ms % 1000) * 1000000UL;
    RCSOFTCHECK(rcl_publish(&joint_states_pub, &joint_states_msg, NULL));

    // Service incoming /joint_commands subscription
    RCSOFTCHECK(rclc_executor_spin_some(&executor, 0));
#else
    (void)estop_now;
    (void)batt_low_now;
#endif
  }

  if (heartbeat_ms >= HEARTBEAT_PERIOD_MS) {
    heartbeat_ms = 0;
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));   // 1 Hz LED
#ifdef NOVA_USE_MICRO_ROS
    heartbeat_msg.data++;
    RCSOFTCHECK(rcl_publish(&heartbeat_pub, &heartbeat_msg, NULL));
    joint_cmd_rx_msg.data = (int32_t)joint_cmd_rx_count;
    RCSOFTCHECK(rcl_publish(&joint_cmd_rx_pub, &joint_cmd_rx_msg, NULL));
#else
    Serial.print("[nova-teensy] alive t=");
    Serial.println(millis());
#endif
  }

  if (stats_ms >= STATS_PERIOD_MS) {
    stats_ms = 0;
#ifdef NOVA_USE_MICRO_ROS
    loop_max_msg.data = (int32_t)max_period_us;
    loop_p99_msg.data = (int32_t)compute_p99_us();
    RCSOFTCHECK(rcl_publish(&loop_max_pub, &loop_max_msg, NULL));
    RCSOFTCHECK(rcl_publish(&loop_p99_pub, &loop_p99_msg, NULL));
#endif
    max_period_us = 0;
    tick_count_window = 0;
    for (int i = 0; i < HIST_BUCKETS; i++) hist[i] = 0;
  }
}
