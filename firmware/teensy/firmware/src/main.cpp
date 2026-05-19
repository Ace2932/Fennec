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
#include <sensor_msgs/msg/joint_state.h>
#include <std_msgs/msg/bool.h>
#include <diagnostic_msgs/msg/diagnostic_array.h>
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
elapsedMillis tick_ms;
elapsedMillis heartbeat_ms;
const uint32_t TICK_PERIOD_MS = 1000 / NOVA_LOOP_HZ;
const uint32_t HEARTBEAT_PERIOD_MS = 1000;

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
  // TODO: micro-ROS node + publishers + subscribers + executor + timer setup.
  // See firmware/teensy/README.md for the topic contract.
  // set_microros_serial_transports(Serial);
#endif

  // First-boot info to USB-CDC
  delay(500);
  Serial.println("[nova-teensy] boot");
  Serial.print("  loop hz: ");      Serial.println(NOVA_LOOP_HZ);
  Serial.print("  bus baud: ");     Serial.println(NOVA_BUS_BAUD);
  Serial.println("  micro-ROS: "
#ifdef NOVA_USE_MICRO_ROS
                 "ENABLED"
#else
                 "disabled (build with -D NOVA_USE_MICRO_ROS on Jetson)"
#endif
                 );
}

void loop() {
  if (tick_ms >= TICK_PERIOD_MS) {
    tick_ms = 0;

    // Servo bus servicing (stub)
    service_bus_stub();

    // Telemetry sample (stub)
    read_ina226_stub();

    // Safety GPIO sense
    bool estop_now = (digitalRead(ESTOP_PIN) == LOW);
    bool batt_low_now = (digitalRead(BATTERY_LOW_PIN) == HIGH);
    (void)estop_now;
    (void)batt_low_now;

#ifdef NOVA_USE_MICRO_ROS
    // TODO: publish /estop + /battery_low on edge change.
    // TODO: rclc_executor_spin_some(...) for /joint_commands callback.
#endif
  }

  if (heartbeat_ms >= HEARTBEAT_PERIOD_MS) {
    heartbeat_ms = 0;
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));   // 1 Hz LED
    Serial.print("[nova-teensy] alive t=");
    Serial.println(millis());
  }
}
