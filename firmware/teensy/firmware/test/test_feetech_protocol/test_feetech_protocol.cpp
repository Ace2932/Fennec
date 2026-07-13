// Native unit tests for feetech_protocol.h — the Feetech STS3215 wire format.
// Pure logic, host-run (pio test -e native). Covers the frame builders, the
// checksum, response parsing bounds/checksum, and the sign-MAGNITUDE 16-bit
// packing (a real STS3215 gotcha: NOT two's complement).
#include <unity.h>
#include "feetech_protocol.h"

using namespace feetech;

void setUp() {}
void tearDown() {}

// ---- checksum: ~(sum of body) low byte, header excluded ----
static void test_checksum_known_vector() {
  // PING body = id(1) len(0x02) inst(0x01) -> sum 0x04 -> ~0x04 = 0xFB
  uint8_t body[] = {0x01, 0x02, 0x01};
  TEST_ASSERT_EQUAL_HEX8(0xFB, checksum(body, 3));
}

static void test_checksum_wraps_low_byte_only() {
  // sum overflows a byte; only the low byte is complemented
  uint8_t body[] = {0xFF, 0xFF, 0x02};  // sum 0x200 -> low 0x00 -> ~0 = 0xFF
  TEST_ASSERT_EQUAL_HEX8(0xFF, checksum(body, 3));
}

// ---- build_ping ----
static void test_build_ping_exact_frame() {
  uint8_t out[MAX_FRAME_LEN];
  uint8_t n = build_ping(0x01, out);
  TEST_ASSERT_EQUAL_UINT8(6, n);
  uint8_t expect[] = {0xFF, 0xFF, 0x01, 0x02, INST_PING, 0xFB};
  TEST_ASSERT_EQUAL_HEX8_ARRAY(expect, out, 6);
}

// ---- build_read ----
static void test_build_read_present_position() {
  uint8_t out[MAX_FRAME_LEN];
  uint8_t n = build_read(0x05, REG_PRESENT_POSITION_L, 2, out);
  TEST_ASSERT_EQUAL_UINT8(8, n);
  // FF FF 05 04 02 38 02 cksum ; cksum=~(05+04+02+38+02)=~0x45=0xBA
  uint8_t expect[] = {0xFF, 0xFF, 0x05, 0x04, INST_READ_DATA, 0x38, 0x02, 0xBA};
  TEST_ASSERT_EQUAL_HEX8_ARRAY(expect, out, 8);
}

// ---- build_write ----
static void test_build_write_torque_enable() {
  uint8_t out[MAX_FRAME_LEN];
  uint8_t data[] = {0x01};
  uint8_t n = build_write(0x03, REG_TORQUE_ENABLE, data, 1, out);
  TEST_ASSERT_EQUAL_UINT8(8, n);           // 7 + data_len(1)
  TEST_ASSERT_EQUAL_HEX8(0x04, out[3]);    // length = data_len + 3
  TEST_ASSERT_EQUAL_HEX8(INST_WRITE_DATA, out[4]);
  TEST_ASSERT_EQUAL_HEX8(REG_TORQUE_ENABLE, out[5]);
  TEST_ASSERT_EQUAL_HEX8(0x01, out[6]);
  // checksum over id..data = ~(03+04+03+28+01)=~0x33=0xCC
  TEST_ASSERT_EQUAL_HEX8(0xCC, out[7]);
}

// ---- build_sync_write: the full-fleet frame must fit MAX_FRAME_LEN ----
static void test_sync_write_full_fleet_no_overflow() {
  uint8_t out[MAX_FRAME_LEN];
  uint8_t ids[12], payload[12 * 2];
  for (uint8_t i = 0; i < 12; i++) {
    ids[i] = i + 1;
    payload[i * 2] = i;         // lo
    payload[i * 2 + 1] = 0;     // hi
  }
  uint8_t n = build_sync_write(REG_GOAL_POSITION_L, 2, ids, 12, payload, out);
  // 8 + (1+2)*12 = 44
  TEST_ASSERT_EQUAL_UINT8(44, n);
  TEST_ASSERT_LESS_OR_EQUAL_UINT8(MAX_FRAME_LEN, n);   // the sizing-bug guard
  TEST_ASSERT_EQUAL_HEX8(BROADCAST_ID, out[2]);
  TEST_ASSERT_EQUAL_HEX8(INST_SYNC_WRITE, out[4]);
  TEST_ASSERT_EQUAL_HEX8(REG_GOAL_POSITION_L, out[5]);
  TEST_ASSERT_EQUAL_HEX8(2, out[6]);       // data_len_per_servo
  // length field = total_payload + 4 = 36 + 4 = 40
  TEST_ASSERT_EQUAL_HEX8(40, out[3]);
  // first servo entry: id then its 2 data bytes
  TEST_ASSERT_EQUAL_HEX8(1, out[7]);
  TEST_ASSERT_EQUAL_HEX8(0, out[8]);
}

static void test_sync_write_layout_two_servos() {
  uint8_t out[MAX_FRAME_LEN];
  uint8_t ids[] = {2, 7};
  uint8_t payload[] = {0xAA, 0xBB, 0xCC, 0xDD};   // servo2={AA,BB}, servo7={CC,DD}
  uint8_t n = build_sync_write(0x2A, 2, ids, 2, payload, out);
  TEST_ASSERT_EQUAL_UINT8(8 + 3 * 2, n);
  uint8_t body[] = {2, 0xAA, 0xBB, 7, 0xCC, 0xDD};
  TEST_ASSERT_EQUAL_HEX8_ARRAY(body, &out[7], 6);
}

// ---- parse_response: round-trip a valid status packet ----
static void build_valid_response(uint8_t id, uint8_t err,
                                 const uint8_t* params, uint8_t plen,
                                 uint8_t* out, uint8_t* out_len) {
  out[0] = 0xFF; out[1] = 0xFF; out[2] = id;
  out[3] = plen + 2;                 // err + params + checksum
  out[4] = err;
  for (uint8_t i = 0; i < plen; i++) out[5 + i] = params[i];
  out[5 + plen] = checksum(&out[2], 3 + plen);   // id+len+err+params
  *out_len = 6 + plen;
}

static void test_parse_valid_position_response() {
  uint8_t params[] = {0x34, 0x12};   // present position 0x1234
  uint8_t buf[MAX_RESPONSE_LEN]; uint8_t blen;
  build_valid_response(0x01, 0x00, params, 2, buf, &blen);

  uint8_t id, err, po[MAX_PARAM_BYTES], plen;
  TEST_ASSERT_TRUE(parse_response(buf, blen, &id, &err, po, &plen));
  TEST_ASSERT_EQUAL_HEX8(0x01, id);
  TEST_ASSERT_EQUAL_HEX8(0x00, err);
  TEST_ASSERT_EQUAL_UINT8(2, plen);
  TEST_ASSERT_EQUAL_UINT16(0x1234, pack_u16_le(po[0], po[1]));
}

static void test_parse_rejects_bad_checksum() {
  uint8_t params[] = {0x34, 0x12};
  uint8_t buf[MAX_RESPONSE_LEN]; uint8_t blen;
  build_valid_response(0x01, 0x00, params, 2, buf, &blen);
  buf[blen - 1] ^= 0xFF;             // corrupt checksum
  uint8_t id, err, po[MAX_PARAM_BYTES], plen;
  TEST_ASSERT_FALSE(parse_response(buf, blen, &id, &err, po, &plen));
}

static void test_parse_rejects_bad_header() {
  uint8_t buf[] = {0xFF, 0x00, 0x01, 0x02, 0x00, 0xFC};
  uint8_t id, err, po[MAX_PARAM_BYTES], plen;
  TEST_ASSERT_FALSE(parse_response(buf, 6, &id, &err, po, &plen));
}

static void test_parse_rejects_short_buffer() {
  uint8_t buf[] = {0xFF, 0xFF, 0x01, 0x02, 0x00};   // 5 < 6
  uint8_t id, err, po[MAX_PARAM_BYTES], plen;
  TEST_ASSERT_FALSE(parse_response(buf, 5, &id, &err, po, &plen));
}

static void test_parse_rejects_len_past_buffer() {
  // len claims more bytes than the buffer holds
  uint8_t buf[] = {0xFF, 0xFF, 0x01, 0x40, 0x00, 0x00};
  uint8_t id, err, po[MAX_PARAM_BYTES], plen;
  TEST_ASSERT_FALSE(parse_response(buf, 6, &id, &err, po, &plen));
}

static void test_parse_error_byte_surfaced() {
  uint8_t buf[MAX_RESPONSE_LEN]; uint8_t blen;
  build_valid_response(0x09, ERR_OVERHEAT | ERR_OVERLOAD, nullptr, 0, buf, &blen);
  uint8_t id, err, po[MAX_PARAM_BYTES], plen;
  TEST_ASSERT_TRUE(parse_response(buf, blen, &id, &err, po, &plen));
  TEST_ASSERT_EQUAL_HEX8(ERR_OVERHEAT | ERR_OVERLOAD, err);
  TEST_ASSERT_EQUAL_UINT8(0, plen);
}

// ---- sign-magnitude 16-bit (STS3215 present velocity / load) ----
static void test_pack_u16_le() {
  TEST_ASSERT_EQUAL_UINT16(0x1234, pack_u16_le(0x34, 0x12));
  TEST_ASSERT_EQUAL_UINT16(0x00FF, pack_u16_le(0xFF, 0x00));
}

static void test_pack_s16_sign_magnitude_not_twos_complement() {
  // bit15 = sign, bits0..14 = magnitude
  TEST_ASSERT_EQUAL_INT16(0,     pack_s16_le(0x00, 0x00));
  TEST_ASSERT_EQUAL_INT16(1,     pack_s16_le(0x01, 0x00));
  TEST_ASSERT_EQUAL_INT16(-1,    pack_s16_le(0x01, 0x80));   // 0x8001
  TEST_ASSERT_EQUAL_INT16(32767, pack_s16_le(0xFF, 0x7F));   // 0x7FFF
  TEST_ASSERT_EQUAL_INT16(-32767, pack_s16_le(0xFF, 0xFF));  // 0xFFFF
  // two's-complement would read 0xFFFF as -1; sign-magnitude reads -32767
  TEST_ASSERT_EQUAL_INT16(0,     pack_s16_le(0x00, 0x80));   // -0 == 0
}

static void test_unpack_u16_roundtrip() {
  uint8_t lo, hi;
  unpack_u16_le(0xBEEF, &lo, &hi);
  TEST_ASSERT_EQUAL_HEX8(0xEF, lo);
  TEST_ASSERT_EQUAL_HEX8(0xBE, hi);
  TEST_ASSERT_EQUAL_UINT16(0xBEEF, pack_u16_le(lo, hi));
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_checksum_known_vector);
  RUN_TEST(test_checksum_wraps_low_byte_only);
  RUN_TEST(test_build_ping_exact_frame);
  RUN_TEST(test_build_read_present_position);
  RUN_TEST(test_build_write_torque_enable);
  RUN_TEST(test_sync_write_full_fleet_no_overflow);
  RUN_TEST(test_sync_write_layout_two_servos);
  RUN_TEST(test_parse_valid_position_response);
  RUN_TEST(test_parse_rejects_bad_checksum);
  RUN_TEST(test_parse_rejects_bad_header);
  RUN_TEST(test_parse_rejects_short_buffer);
  RUN_TEST(test_parse_rejects_len_past_buffer);
  RUN_TEST(test_parse_error_byte_surfaced);
  RUN_TEST(test_pack_u16_le);
  RUN_TEST(test_pack_s16_sign_magnitude_not_twos_complement);
  RUN_TEST(test_unpack_u16_roundtrip);
  return UNITY_END();
}
