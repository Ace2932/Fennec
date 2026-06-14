// Feetech STS3215 protocol — frame layout, instruction codes, register map.
// Mirrors the Feetech SCServo SDK enough to issue PING / READ_DATA / WRITE_DATA
// / SYNC_WRITE from Teensy's Serial1 with no extra dependencies. Frames are
// half-duplex over the 74HC125 (Pattern B); the OE direction switching lives
// in feetech_bus.h, not here.

#pragma once

#include <Arduino.h>

namespace feetech {

// ---------------- Wire frame constants ----------------
constexpr uint8_t HEADER_BYTE        = 0xFF;
constexpr uint8_t BROADCAST_ID       = 0xFE;
// Sized for the worst frame on this bus: SYNC_WRITE goal positions to all
// 12 servos = 7 header/inst bytes + 12×(id + 2 data) + checksum = 44 bytes
// → params region needs ≥ 38. 40 leaves margin. (Was 32 → MAX_FRAME_LEN 38,
// which sync_write_goal_positions overflowed by 6 bytes on a full fleet.)
constexpr uint8_t MAX_PARAM_BYTES    = 40;
constexpr uint8_t FRAME_OVERHEAD     = 6;   // 2 header + id + len + inst + checksum
constexpr uint8_t MAX_FRAME_LEN      = FRAME_OVERHEAD + MAX_PARAM_BYTES;
constexpr uint8_t MAX_RESPONSE_LEN   = MAX_FRAME_LEN;

// ---------------- Instructions ----------------
enum Instruction : uint8_t {
  INST_PING        = 0x01,
  INST_READ_DATA   = 0x02,
  INST_WRITE_DATA  = 0x03,
  INST_REG_WRITE   = 0x04,
  INST_ACTION      = 0x05,
  INST_RESET       = 0x06,
  INST_SYNC_READ   = 0x82,
  INST_SYNC_WRITE  = 0x83,
};

// ---------------- STS3215 register map (subset we actually use) ----------------
// EEPROM / RAM split — RAM only here; EEPROM writes (ID change, baud change)
// are infrequent and not on the realtime path.
enum Sts3215Reg : uint8_t {
  REG_ID                   = 0x05,   // EEPROM, 1 byte
  REG_BAUD_RATE            = 0x06,   // EEPROM, 1 byte
  REG_TORQUE_ENABLE        = 0x28,   // RAM,    1 byte (0=off, 1=on)
  REG_GOAL_POSITION_L      = 0x2A,   // RAM,    2 bytes little-endian, 0..4095
  REG_GOAL_VELOCITY_L      = 0x2E,   // RAM,    2 bytes
  REG_GOAL_ACC             = 0x29,   // RAM,    1 byte
  REG_PRESENT_POSITION_L   = 0x38,   // RAM,    2 bytes (read)
  REG_PRESENT_VELOCITY_L   = 0x3A,   // RAM,    2 bytes (read, signed)
  REG_PRESENT_LOAD_L       = 0x3C,   // RAM,    2 bytes (read, signed)
  REG_PRESENT_VOLTAGE      = 0x3E,   // RAM,    1 byte  (read, 0.1 V/unit)
  REG_PRESENT_TEMPERATURE  = 0x3F,   // RAM,    1 byte  (read, °C)
  REG_MOVING               = 0x42,   // RAM,    1 byte  (read)
};

// ---------------- Error bits (response status byte) ----------------
enum ErrorBit : uint8_t {
  ERR_VOLTAGE      = 0x01,
  ERR_ANGLE_LIMIT  = 0x02,
  ERR_OVERHEAT     = 0x04,
  ERR_RANGE        = 0x08,
  ERR_CHECKSUM     = 0x10,
  ERR_OVERLOAD     = 0x20,
  ERR_INSTRUCTION  = 0x40,
};

// ---------------- Checksum ----------------
// Feetech checksum: ~(sum of id+len+inst+params) low byte. Header bytes
// NOT included.
inline uint8_t checksum(const uint8_t* body, uint8_t body_len) {
  uint16_t sum = 0;
  for (uint8_t i = 0; i < body_len; i++) sum += body[i];
  return ~((uint8_t)(sum & 0xFF));
}

// ---------------- Frame builders ----------------
// All builders return total bytes written into `out`. `out` must be at least
// MAX_FRAME_LEN. Param packing uses little-endian for >1-byte register fields,
// matching the STS3215 datasheet.

// PING: returns frame_len. Frame: FF FF id 02 01 checksum
inline uint8_t build_ping(uint8_t id, uint8_t* out) {
  out[0] = HEADER_BYTE;
  out[1] = HEADER_BYTE;
  out[2] = id;
  out[3] = 0x02;                  // length = inst + checksum
  out[4] = INST_PING;
  out[5] = checksum(&out[2], 3);
  return 6;
}

// READ_DATA: frame FF FF id 04 02 reg num_bytes checksum
inline uint8_t build_read(uint8_t id, uint8_t reg, uint8_t num_bytes, uint8_t* out) {
  out[0] = HEADER_BYTE;
  out[1] = HEADER_BYTE;
  out[2] = id;
  out[3] = 0x04;
  out[4] = INST_READ_DATA;
  out[5] = reg;
  out[6] = num_bytes;
  out[7] = checksum(&out[2], 5);
  return 8;
}

// WRITE_DATA: arbitrary register write of N bytes.
// Frame: FF FF id (3+N) 03 reg data... checksum
inline uint8_t build_write(uint8_t id, uint8_t reg,
                           const uint8_t* data, uint8_t data_len,
                           uint8_t* out) {
  out[0] = HEADER_BYTE;
  out[1] = HEADER_BYTE;
  out[2] = id;
  out[3] = data_len + 3;          // length = inst + reg + data + checksum
  out[4] = INST_WRITE_DATA;
  out[5] = reg;
  for (uint8_t i = 0; i < data_len; i++) out[6 + i] = data[i];
  out[6 + data_len] = checksum(&out[2], 4 + data_len);
  return 7 + data_len;
}

// SYNC_WRITE: broadcast write of `data_len_per_servo` bytes to `reg` on each
// of `n` servos. Frame: FF FF 0xFE (4+(1+L)*n) 0x83 reg L [id data*L]xN cksum
// `ids[i]` is the servo ID, `payload[i*L .. i*L+L-1]` is its data.
inline uint8_t build_sync_write(uint8_t reg, uint8_t data_len_per_servo,
                                const uint8_t* ids, uint8_t n,
                                const uint8_t* payload, uint8_t* out) {
  uint8_t total_payload = (1 + data_len_per_servo) * n;
  out[0] = HEADER_BYTE;
  out[1] = HEADER_BYTE;
  out[2] = BROADCAST_ID;
  out[3] = total_payload + 4;     // inst + reg + L + payload + checksum
  out[4] = INST_SYNC_WRITE;
  out[5] = reg;
  out[6] = data_len_per_servo;
  uint8_t* p = &out[7];
  for (uint8_t i = 0; i < n; i++) {
    *p++ = ids[i];
    for (uint8_t b = 0; b < data_len_per_servo; b++) {
      *p++ = payload[i * data_len_per_servo + b];
    }
  }
  out[7 + total_payload] = checksum(&out[2], 5 + total_payload);
  return 8 + total_payload;
}

// ---------------- Response parsing ----------------
// A status response is: FF FF id len err [params...] checksum
// Returns true on a structurally valid frame with passing checksum.
// On success: `error_out` is the servo error byte, `params_out` (caller-
// provided buffer >= MAX_PARAM_BYTES) holds the payload, and `param_len_out`
// is the number of payload bytes. If the response is shorter than expected
// or the checksum fails, returns false.
inline bool parse_response(const uint8_t* buf, uint8_t buf_len,
                           uint8_t* id_out, uint8_t* error_out,
                           uint8_t* params_out, uint8_t* param_len_out) {
  if (buf_len < 6) return false;
  if (buf[0] != HEADER_BYTE || buf[1] != HEADER_BYTE) return false;
  uint8_t id   = buf[2];
  uint8_t len  = buf[3];          // = err + params + checksum
  if (len + 4 > buf_len) return false;
  uint8_t err  = buf[4];
  uint8_t param_len = (len >= 2) ? (len - 2) : 0;
  if (param_len > MAX_PARAM_BYTES) return false;
  uint8_t expected_cksum = checksum(&buf[2], 2 + len - 1);  // id+len+err+params
  if (buf[3 + len] != expected_cksum) return false;
  *id_out = id;
  *error_out = err;
  *param_len_out = param_len;
  for (uint8_t i = 0; i < param_len; i++) params_out[i] = buf[5 + i];
  return true;
}

// ---------------- Unit helpers ----------------
// STS3215 position: 0..4095 over 360° (for the magnetic absolute encoder
// variant). Wrap-aware conversions live with the gait controller — keep this
// layer raw.
inline uint16_t pack_u16_le(uint8_t lo, uint8_t hi) {
  return (uint16_t)lo | ((uint16_t)hi << 8);
}
inline int16_t pack_s16_le(uint8_t lo, uint8_t hi) {
  // STS3215 sign convention: bit 15 = sign, bits 0..14 = magnitude (NOT two's
  // complement). Callers usually want this as the signed quantity.
  uint16_t raw = pack_u16_le(lo, hi);
  int16_t mag = (int16_t)(raw & 0x7FFF);
  return (raw & 0x8000) ? -mag : mag;
}
inline void unpack_u16_le(uint16_t v, uint8_t* lo, uint8_t* hi) {
  *lo = (uint8_t)(v & 0xFF);
  *hi = (uint8_t)((v >> 8) & 0xFF);
}

}  // namespace feetech
