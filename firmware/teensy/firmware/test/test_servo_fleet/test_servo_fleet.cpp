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
  RUN_TEST(test_torque_off_survives_a_dropped_first_frame);
  RUN_TEST(test_a_servo_that_never_confirms_is_counted_not_hidden);
  RUN_TEST(test_a_servo_that_drops_and_returns_gets_its_dynamics_rewritten);
  return UNITY_END();
}
