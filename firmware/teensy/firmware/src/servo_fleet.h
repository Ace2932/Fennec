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
//
// #437 — TORQUE-OFF IS CONFIRMED, NOT ASSUMED. E-stop, overload limp and
// battery-low all end in disarm(), and it used to send one TORQUE_ENABLE=0 per
// servo and ignore the result: one bad frame left that joint holding torque,
// and for overload and battery-low there is no hardware backstop at that
// moment. Now: one broadcast (ID 0xFE, no ACK) reaches every servo in a single
// frame, then each present servo is written AND read back until it reports 0
// or OFF_RETRIES attempts are spent. A servo that never confirms is returned
// in the failed mask and counted in off_fail_count() (/torque_off_fail).
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

  // Attempts per servo (write + read-back) before it is counted as failed.
  // ponytail: 3 x (1.5 ms write + 1.5 ms read timeout) x 12 = ~108 ms worst
  // case, blocking, if the whole bus is dead; inside the 1 s watchdog budget.
  // Tune from bench timing if a partial-bus fault makes the stop feel slow.
  static constexpr uint8_t OFF_RETRIES = 3;

  // TORQUE_ENABLE=0 on the whole bus, confirmed per present servo (#437).
  // Returns the mask of servos that never confirmed torque off.
  uint16_t disarm(uint16_t present_mask) {
    bus_.broadcast_write_byte(feetech::REG_TORQUE_ENABLE, 0);
    uint16_t failed = 0;
    for (uint8_t i = 0; i < n_; i++) {
      if (!(present_mask & (uint16_t)(1u << i))) continue;
      uint8_t id = id_base_ + i;
      bool off = false;
      for (uint8_t a = 0; a < OFF_RETRIES && !off; a++) {
        bus_.torque_enable(id, false);   // ACK ignored: the read-back is the proof
        uint8_t v = 1;
        off = bus_.read_byte(id, feetech::REG_TORQUE_ENABLE, &v) == BusT::OK && v == 0;
      }
      if (!off) {
        failed |= (uint16_t)(1u << i);
        off_fail_count_++;
      }
    }
    return failed;
  }

  // Lifetime count of servos that did not confirm torque off (#437).
  uint32_t off_fail_count() const { return off_fail_count_; }

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
  uint32_t off_fail_count_ = 0;
};

}  // namespace nova
