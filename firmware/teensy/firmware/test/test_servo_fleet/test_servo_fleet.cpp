// Native test for servo_fleet.h -- the fleet torque arm / disarm path that
// E-stop, overload limp, battery-low and fault-clear all route through.
//
// The bus is a FAKE SERVO MODEL, not the UART mock: what matters here is the
// servos' end state (is torque off? were the dynamics registers rewritten?),
// and a stateful fake answers that directly. Each call that would put a frame
// on the wire takes the next frame index; indices in `drop` are lost (the servo
// never sees them, and nothing comes back).

#include <unity.h>
#include <set>
#include <string>
#include <vector>

#include "servo_fleet.h"

struct FakeBus {
  enum Result : uint8_t { OK = 0, ERR_TIMEOUT = 2 };

  struct Servo {
    bool present = true;     // on the bus at all
    bool deaf = false;       // present but ignores every frame (stuck servo)
    bool torque = true;      // TORQUE_ENABLE register
    uint16_t torque_limit = 1000;   // power-on default
    uint8_t goal_acc = 0;           // power-on default
    uint16_t pos = 2048;            // present position
    uint16_t goal = 0;              // stale goal left from before torque-off
  };

  Servo s[16];               // indexed by servo ID (1..12 used)
  int frame = 0;
  std::set<int> drop;
  std::vector<std::string> log;

  bool reaches(uint8_t id) {
    bool lost = drop.count(frame++) > 0;
    return !lost && s[id].present && !s[id].deaf;
  }
  void note(const char* what, int id, int val) {
    log.push_back(std::string(what) + " " + std::to_string(id) + "=" + std::to_string(val));
  }

  Result torque_enable(uint8_t id, bool on, uint32_t = 0) {
    note("TE", id, on);
    if (!reaches(id)) return ERR_TIMEOUT;
    s[id].torque = on;
    return OK;
  }
  Result set_torque_limit(uint8_t id, uint16_t v, uint32_t = 0) {
    note("TL", id, v);
    if (!reaches(id)) return ERR_TIMEOUT;
    s[id].torque_limit = v;
    return OK;
  }
  Result set_goal_acc(uint8_t id, uint8_t v, uint32_t = 0) {
    note("ACC", id, v);
    if (!reaches(id)) return ERR_TIMEOUT;
    s[id].goal_acc = v;
    return OK;
  }
  Result read_byte(uint8_t id, uint8_t reg, uint8_t* out, uint32_t = 0) {
    note("RD", id, reg);
    if (!reaches(id)) return ERR_TIMEOUT;
    if (reg == feetech::REG_TORQUE_ENABLE) *out = s[id].torque ? 1 : 0;
    return OK;
  }
  Result read_position(uint8_t id, uint16_t* out, uint32_t = 0) {
    note("RPOS", id, 0);
    if (!reaches(id)) return ERR_TIMEOUT;
    *out = s[id].pos;
    return OK;
  }
  Result write_goal_position(uint8_t id, uint16_t v, uint32_t = 0) {
    note("GOAL", id, v);
    if (!reaches(id)) return ERR_TIMEOUT;
    s[id].goal = v;
    return OK;
  }
  // Broadcast: no ACK. A dropped broadcast reaches nobody.
  Result broadcast_write_byte(uint8_t reg, uint8_t val) {
    note("BCAST", reg, val);
    bool lost = drop.count(frame++) > 0;
    if (!lost && reg == feetech::REG_TORQUE_ENABLE)
      for (auto& sv : s) if (sv.present && !sv.deaf) sv.torque = (val != 0);
    return OK;
  }

  int count(const std::string& prefix) const {
    int n = 0;
    for (auto& e : log) if (e.rfind(prefix, 0) == 0) n++;
    return n;
  }
};

static constexpr uint8_t N = 12;
static constexpr uint16_t ALL = 0x0FFF;

void setUp(void) {}
void tearDown(void) {}

// ---- #436 ------------------------------------------------------------------

void test_no_torque_enable_before_the_first_safety_tick(void) {
  // setup() used to arm here, before the agent wait and tick_timer.begin().
  // Whatever calls arm() before the safety loop has run must write nothing.
  FakeBus bus;
  nova::ServoFleet<FakeBus> fleet(bus, 1, N, 600, 50);
  for (auto& sv : bus.s) sv.torque = false;

  fleet.arm(ALL);
  TEST_ASSERT_EQUAL_INT_MESSAGE(0, bus.count("TE"),
      "TORQUE_ENABLE written before the first safety tick (#436)");
  TEST_ASSERT_EQUAL_INT(0, bus.count("TL"));

  // The first safety tick arms, when the FSM allows motion.
  fleet.safety_tick(/*motion_enabled=*/true, ALL);
  TEST_ASSERT_EQUAL_INT(N, bus.count("TE"));
  for (uint8_t id = 1; id <= N; id++) TEST_ASSERT_TRUE(bus.s[id].torque);
}

void test_boot_latched_fault_keeps_the_fleet_limp_on_the_first_tick(void) {
  // Boot self-test semantics: a pre-seeded latch means the first tick must
  // NOT arm; the fault-clear transition re-arms through arm() later.
  FakeBus bus;
  nova::ServoFleet<FakeBus> fleet(bus, 1, N, 600, 50);
  fleet.safety_tick(/*motion_enabled=*/false, ALL);
  TEST_ASSERT_EQUAL_INT(0, bus.count("TE"));
  fleet.arm(ALL);   // fault cleared
  TEST_ASSERT_EQUAL_INT(N, bus.count("TE"));
}

// ---- #437 ------------------------------------------------------------------

// ---- #431 / #466: goal = present before torque-on ---------------------------

void test_arm_holds_present_position_before_enabling_torque(void) {
  // With torque off the servo keeps a stale goal while the joint drifts. Arming
  // must first make the goal WHERE THE JOINT IS, then enable -- never enable
  // toward the stale goal (a full-profile snap once reg 85 = 254).
  FakeBus bus;
  nova::ServoFleet<FakeBus> fleet(bus, 1, N, 600, 0);
  for (auto& sv : bus.s) { sv.torque = false; sv.goal = 100; }
  bus.s[3].pos = 1234;
  fleet.safety_tick(true, ALL);
  TEST_ASSERT_EQUAL_UINT16_MESSAGE(1234, bus.s[3].goal, "goal not set to present");
  TEST_ASSERT_TRUE(bus.s[3].torque);
  int goal_at = -1, te_at = -1;
  for (int k = 0; k < (int)bus.log.size(); k++) {
    if (bus.log[k] == "GOAL 3=1234" && goal_at < 0) goal_at = k;
    if (bus.log[k] == "TE 3=1" && te_at < 0) te_at = k;
  }
  TEST_ASSERT_TRUE_MESSAGE(goal_at >= 0 && te_at > goal_at, "TORQUE_ENABLE before GOAL=present");
}

void test_arm_leaves_a_servo_limp_when_its_position_cannot_be_read(void) {
  FakeBus bus;
  nova::ServoFleet<FakeBus> fleet(bus, 1, N, 600, 0);
  for (auto& sv : bus.s) sv.torque = false;
  fleet.safety_tick(false, ALL);          // go live without arming
  bus.drop.insert(bus.frame);             // servo 1's position read is lost
  uint16_t skipped = fleet.arm(ALL);
  TEST_ASSERT_EQUAL_HEX16(0x0001, skipped);
  TEST_ASSERT_FALSE_MESSAGE(bus.s[1].torque, "armed toward an unknown goal");
  TEST_ASSERT_TRUE(bus.s[2].torque);
}

void test_torque_off_survives_a_dropped_first_frame(void) {
  // One bad frame used to leave that joint holding torque: disarm() sent one
  // unchecked TORQUE_ENABLE=0 per servo. Drop the first frame on the wire and
  // every servo must still end with torque off, with no failure counted.
  FakeBus bus;
  nova::ServoFleet<FakeBus> fleet(bus, 1, N, 600, 50);
  bus.drop = {0};

  fleet.disarm(ALL);
  for (uint8_t id = 1; id <= N; id++) {
    TEST_ASSERT_FALSE_MESSAGE(bus.s[id].torque,
        ("servo " + std::to_string(id) + " still holds torque after disarm (#437)").c_str());
  }
  TEST_ASSERT_EQUAL_UINT32(0, fleet.off_fail_count());
}

void test_a_servo_that_never_confirms_is_counted_not_hidden(void) {
  // A stuck servo (ignores every frame) cannot be forced off; the retry cap
  // must end the attempt and the failure must be COUNTED for /torque_off_fail.
  // Servo 12 is on the bus but missing from present_mask (its boot ping was
  // lost): only the broadcast reaches it.
  FakeBus bus;
  nova::ServoFleet<FakeBus> fleet(bus, 1, N, 600, 50);
  bus.s[5].deaf = true;

  TEST_ASSERT_EQUAL_HEX16((uint16_t)(1u << 4), fleet.disarm(ALL & ~(1u << 11)));
  TEST_ASSERT_FALSE_MESSAGE(bus.s[12].torque, "broadcast TORQUE_ENABLE=0 missing");
  TEST_ASSERT_EQUAL_UINT32(1, fleet.off_fail_count());
  TEST_ASSERT_EQUAL_INT(nova::ServoFleet<FakeBus>::OFF_RETRIES, bus.count("TE 5=0"));
  for (uint8_t id = 1; id <= N; id++)
    if (id != 5) TEST_ASSERT_FALSE(bus.s[id].torque);
}

// ---- #438 ------------------------------------------------------------------

void test_a_servo_that_drops_and_returns_gets_its_dynamics_rewritten(void) {
  // A brownout resets the servo's RAM: torque limit and goal acc come back at
  // power-on defaults and used to stay there until the next fault clear.
  FakeBus bus;
  nova::ServoFleet<FakeBus> fleet(bus, 1, N, 600, 50);
  const uint8_t i = 4, id = 5;

  fleet.on_poll(i, FakeBus::OK);            // healthy: nothing to rewrite
  TEST_ASSERT_EQUAL_INT(0, bus.count("TL") + bus.count("ACC"));

  fleet.on_poll(i, FakeBus::ERR_TIMEOUT);   // rail browns out
  bus.s[id].torque_limit = 1000;            // ...and the servo reboots
  bus.s[id].goal_acc = 0;
  fleet.on_poll(i, FakeBus::OK);            // answers again

  TEST_ASSERT_EQUAL_UINT16_MESSAGE(600, bus.s[id].torque_limit,
      "torque limit not re-written after the servo came back (#438)");
  TEST_ASSERT_EQUAL_UINT8_MESSAGE(50, bus.s[id].goal_acc,
      "goal acc not re-written after the servo came back (#438)");

  fleet.on_poll(i, FakeBus::OK);            // once only, not every poll
  TEST_ASSERT_EQUAL_INT(1, bus.count("TL"));
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_no_torque_enable_before_the_first_safety_tick);
  RUN_TEST(test_boot_latched_fault_keeps_the_fleet_limp_on_the_first_tick);
  RUN_TEST(test_arm_holds_present_position_before_enabling_torque);
  RUN_TEST(test_arm_leaves_a_servo_limp_when_its_position_cannot_be_read);
  RUN_TEST(test_torque_off_survives_a_dropped_first_frame);
  RUN_TEST(test_a_servo_that_never_confirms_is_counted_not_hidden);
  RUN_TEST(test_a_servo_that_drops_and_returns_gets_its_dynamics_rewritten);
  return UNITY_END();
}
