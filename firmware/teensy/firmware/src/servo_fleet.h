// servo_fleet.h — fleet-wide torque arm / disarm, extracted from main.cpp's
// set_fleet_torque() so `pio test -e native` can execute it (#358's extraction
// rule; loop_timing.h is the pattern). Templated on the bus so the native test
// drives a fake servo model instead of a UART; main.cpp instantiates it with
// feetech::Bus. Every torque change in the firmware routes through here.
//
// #436 — ARM ONLY ONCE THE SAFETY LOOP IS RUNNING. setup() used to arm the
// fleet BEFORE the micro-ROS agent wait (rclc_support_init retries until the
// Jetson is up, 30-60 s on a cold boot) and before tick_timer.begin(). For that
// whole window the servos held torque with no SafetyFSM update, no stall or
// overtemp check and no software watchdog -- only the hardware E-stop. arm()
// now refuses until safety_tick() has run once, and the first safety_tick()
// is what arms the fleet (if the FSM allows motion -- the boot self-test's
// pre-seeded latch still keeps it limp). disarm() is never gated: cutting
// torque is always allowed, including from rc_init_fail_reset() in setup().
#pragma once

#include <stdint.h>
#include "feetech_protocol.h"

namespace nova {

template <class BusT>
class ServoFleet {
 public:
  ServoFleet(BusT& bus, uint8_t id_base, uint8_t n,
             uint16_t torque_limit, uint8_t goal_acc)
      : bus_(bus), id_base_(id_base), n_(n),
        torque_limit_(torque_limit), goal_acc_(goal_acc) {}

  // TORQUE_ENABLE=1 on every present servo, dynamics first. No-op until the
  // safety loop has ticked once (#436).
  void arm(uint16_t present_mask) {
    if (!safety_live_) return;
    for (uint8_t i = 0; i < n_; i++) {
      if (!(present_mask & (uint16_t)(1u << i))) continue;
      uint8_t id = id_base_ + i;
      // dynamics BEFORE enable so the first held pose is already limited
      write_dynamics(id);
      bus_.torque_enable(id, true);
    }
  }

  // TORQUE_ENABLE=0 on every present servo.
  void disarm(uint16_t present_mask) {
    for (uint8_t i = 0; i < n_; i++) {
      if (present_mask & (uint16_t)(1u << i)) bus_.torque_enable(id_base_ + i, false);
    }
  }

  // Call once per safety tick, AFTER SafetyFSM::update(). The first call marks
  // the safety loop live and arms the fleet if motion is enabled (#436); every
  // later call is a no-op (fault-clear re-arms through arm() as before).
  void safety_tick(bool motion_enabled, uint16_t present_mask) {
    if (safety_live_) return;
    safety_live_ = true;
    if (motion_enabled) arm(present_mask);
  }

  bool safety_live() const { return safety_live_; }

  // Torque limit + goal acc. Both are RAM registers that reset when the servo
  // power-cycles, so they must be rewritten on every arm.
  void write_dynamics(uint8_t id) {
    bus_.set_torque_limit(id, torque_limit_);
    bus_.set_goal_acc(id, goal_acc_);
  }

 private:
  BusT&    bus_;
  uint8_t  id_base_;
  uint8_t  n_;
  uint16_t torque_limit_;
  uint8_t  goal_acc_;
  bool     safety_live_ = false;
};

}  // namespace nova
