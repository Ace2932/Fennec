// Nova-SM3 LE — Teensy 4.1 firmware skeleton
// Pattern B bus master per BOM v3.3
// Status: compile-green scaffold. No servo I/O, no INA226 reads, no real bus traffic yet.

#include <Arduino.h>
#include <micro_ros_platformio.h>

#include <rcl/rcl.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <sensor_msgs/msg/joint_state.h>
#include <std_msgs/msg/bool.h>
#include <diagnostic_msgs/msg/diagnostic_array.h>

// ---------------- Pinout ----------------
// UART2 → 74HC125 → Feetech bus
constexpr uint8_t BUS_RX_PIN     = 7;   // Serial2 RX
constexpr uint8_t BUS_TX_PIN     = 8;   // Serial2 TX
constexpr uint8_t BUS_OE_TX_PIN  = 6;   // 74HC125 OE for TX gate (HIGH = enable TX)
constexpr uint8_t BUS_OE_RX_PIN  = 5;   // 74HC125 OE for RX gate (LOW = enable RX)
// I2C0 (Wire) — INA226 ×3 + Arduino Nano (separate bus addressing)
constexpr uint8_t I2C_SDA_PIN    = 18;
constexpr uint8_t I2C_SCL_PIN    = 19;
// Safety GPIO
constexpr uint8_t ESTOP_PIN       = 2;   // input from E-stop NC contact (LOW = pressed)
constexpr uint8_t BATTERY_LOW_PIN = 3;   // input from 13.0V comparator (HIGH = below 13.0V)
constexpr uint8_t LED_PIN         = LED_BUILTIN;

// ---------------- Topic + entity handles ----------------
rcl_publisher_t joint_states_pub;
rcl_publisher_t estop_pub;
rcl_publisher_t battery_low_pub;
rcl_publisher_t diagnostics_pub;
rcl_subscription_t joint_commands_sub;

sensor_msgs__msg__JointState joint_states_msg;
sensor_msgs__msg__JointState joint_commands_msg;
std_msgs__msg__Bool estop_msg;
std_msgs__msg__Bool battery_low_msg;
diagnostic_msgs__msg__DiagnosticArray diagnostics_msg;

rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;
rcl_timer_t loop_timer;

// ---------------- Bus direction control (74HC125) ----------------
inline void bus_set_tx() {
  digitalWrite(BUS_OE_TX_PIN, HIGH);  // drive TX onto bus
  digitalWrite(BUS_OE_RX_PIN, HIGH);  // mute RX gate
}

inline void bus_set_rx() {
  digitalWrite(BUS_OE_TX_PIN, LOW);   // mute TX gate
  digitalWrite(BUS_OE_RX_PIN, LOW);   // enable RX from bus
}

// ---------------- Stub: Feetech bus servicing ----------------
// TODO: port SCServo SDK to TeensyDuino + integrate read/write here.
// Placeholder: just toggles direction pins so we can scope them during bring-up.
void service_bus_stub() {
  bus_set_tx();
  delayMicroseconds(1);
  bus_set_rx();
}

// ---------------- Stub: INA226 reads ----------------
// TODO: integrate Rob Tillaart's INA226 library, read 3 rails (leg/hip/Jetson),
// publish to /diagnostics at 10 Hz.
void read_ina226_stub() {
  // No I2C traffic yet. Just heartbeats.
}

// ---------------- Main real-time loop ----------------
void on_loop_timer(rcl_timer_t* timer, int64_t /*last_call_time_ns*/) {
  (void)timer;

  // Servo bus servicing (stub)
  service_bus_stub();

  // Telemetry sample (stub)
  read_ina226_stub();

  // Safety GPIO sense
  bool estop_now = (digitalRead(ESTOP_PIN) == LOW);
  bool batt_low_now = (digitalRead(BATTERY_LOW_PIN) == HIGH);

  // Publish event-driven safety topics on edge change.
  // For skeleton: just publish every tick at low frequency (TODO: change to event-driven).
  static uint32_t pub_counter = 0;
  if (++pub_counter % NOVA_LOOP_HZ == 0) {
    estop_msg.data = estop_now;
    rcl_publish(&estop_pub, &estop_msg, NULL);
    battery_low_msg.data = batt_low_now;
    rcl_publish(&battery_low_pub, &battery_low_msg, NULL);
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));  // 1 Hz heartbeat
  }
}

// ---------------- /joint_commands subscriber callback ----------------
void on_joint_commands(const void* msgin) {
  const sensor_msgs__msg__JointState* msg =
      (const sensor_msgs__msg__JointState*)msgin;
  // TODO: stash target positions, hand off to bus writer in the loop tick.
  (void)msg;
}

// ---------------- Setup ----------------
void setup() {
  // GPIO directions
  pinMode(BUS_OE_TX_PIN, OUTPUT);
  pinMode(BUS_OE_RX_PIN, OUTPUT);
  pinMode(ESTOP_PIN, INPUT_PULLUP);
  pinMode(BATTERY_LOW_PIN, INPUT_PULLDOWN);
  pinMode(LED_PIN, OUTPUT);
  bus_set_rx();   // default to RX so the bus is free

  // UART for Feetech bus
  Serial2.begin(NOVA_BUS_BAUD);

  // micro-ROS transport over USB
  Serial.begin(115200);
  set_microros_serial_transports(Serial);
  delay(2000);  // give the host time to enumerate /dev/ttyACM*

  allocator = rcl_get_default_allocator();
  rclc_support_init(&support, 0, NULL, &allocator);
  rclc_node_init_default(&node, "nova_teensy", "", &support);

  // Publishers
  rclc_publisher_init_default(
      &joint_states_pub, &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
      "/joint_states");
  rclc_publisher_init_default(
      &estop_pub, &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
      "/estop");
  rclc_publisher_init_default(
      &battery_low_pub, &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
      "/battery_low");
  rclc_publisher_init_default(
      &diagnostics_pub, &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(diagnostic_msgs, msg, DiagnosticArray),
      "/diagnostics");

  // Subscriber
  rclc_subscription_init_default(
      &joint_commands_sub, &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
      "/joint_commands");

  // Timer for the real-time loop
  const unsigned int loop_period_ns = 1000000000u / NOVA_LOOP_HZ;
  rclc_timer_init_default(&loop_timer, &support, loop_period_ns, on_loop_timer);

  // Executor
  rclc_executor_init(&executor, &support.context, 2, &allocator);
  rclc_executor_add_subscription(
      &executor, &joint_commands_sub, &joint_commands_msg,
      &on_joint_commands, ON_NEW_DATA);
  rclc_executor_add_timer(&executor, &loop_timer);
}

// ---------------- Loop ----------------
void loop() {
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(1));
}
