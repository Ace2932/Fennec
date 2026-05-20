// Pattern B half-duplex bus driver for the Feetech STS3215 chain.
// Owns the 74HC125 OE pins (DE/RE-equivalent gating) and Teensy Serial2 TX
// timing. Frames built in feetech_protocol.h; this file is the wire-side
// state machine.
//
// Real-time contract: every public call is non-blocking *except*
// transmit_blocking() which spins until the UART's last byte has shifted
// out — required before re-enabling the RX gate, otherwise the tail of our
// own TX is interpreted as a servo response. At 1 Mbaud, the spin is
// ~10 µs per byte × frame length (typ. 100 µs total). Fits inside the
// 200 Hz loop budget.

#pragma once

#include <Arduino.h>
#include "feetech_protocol.h"

namespace feetech {

// Pattern B uses Teensy Serial2 (pins 7/8) through 74HC125. Tunable via
// build flags so a Pattern A bench bringup can override.
#ifndef NOVA_FEETECH_UART
#define NOVA_FEETECH_UART Serial2
#endif

class Bus {
 public:
  // OE pin convention matches src/main.cpp's bus_set_tx/rx helpers:
  //   tx mode → tx_oe HIGH, rx_oe HIGH (mute RX gate while we drive)
  //   rx mode → tx_oe LOW,  rx_oe LOW  (release bus, enable RX gate)
  Bus(uint8_t tx_oe_pin, uint8_t rx_oe_pin, uint32_t baud)
      : tx_oe_pin_(tx_oe_pin), rx_oe_pin_(rx_oe_pin), baud_(baud) {}

  void begin() {
    pinMode(tx_oe_pin_, OUTPUT);
    pinMode(rx_oe_pin_, OUTPUT);
    set_rx();
    NOVA_FEETECH_UART.begin(baud_);
  }

  // Send a pre-built frame; spin until TX flushes; flip back to RX.
  // Returns true if the frame was transmitted (no buffer overflow). Servo
  // response is NOT read here — call read_response() afterwards.
  bool transmit_blocking(const uint8_t* frame, uint8_t frame_len) {
    if (frame_len > MAX_FRAME_LEN) return false;
    // Drain any stale RX before we light up the TX gate — left-over half-
    // bytes from a previous response would otherwise re-enter our parser
    // after the next set_rx().
    while (NOVA_FEETECH_UART.available()) NOVA_FEETECH_UART.read();

    set_tx();
    // Tiny settle for the 74HC125 OE transition (datasheet t_pzh < 50 ns,
    // but we account for trace + scope margin). 2 µs is safe and cheap.
    delayMicroseconds(2);

    NOVA_FEETECH_UART.write(frame, frame_len);
    NOVA_FEETECH_UART.flush();           // blocks until last byte shifted out

    delayMicroseconds(2);
    set_rx();
    return true;
  }

  // Read into `out` until either `expected_len` bytes arrive or `timeout_us`
  // elapses. Returns bytes actually read.
  uint8_t read_response(uint8_t* out, uint8_t expected_len, uint32_t timeout_us) {
    uint32_t deadline = micros() + timeout_us;
    uint8_t got = 0;
    while (got < expected_len) {
      if (NOVA_FEETECH_UART.available()) {
        out[got++] = (uint8_t)NOVA_FEETECH_UART.read();
      }
      if ((int32_t)(micros() - deadline) >= 0) break;
    }
    return got;
  }

  // ---------- Convenience wrappers (build + send + recv) ----------
  // Return values match the same convention everywhere: 0 = OK, nonzero = err.
  enum Result : uint8_t {
    OK            = 0,
    ERR_TX_BUSY   = 1,
    ERR_TIMEOUT   = 2,
    ERR_BAD_FRAME = 3,
    ERR_SERVO     = 4,
  };

  // PING — succeeds if servo `id` responds within `timeout_us`.
  Result ping(uint8_t id, uint32_t timeout_us = 1000) {
    uint8_t frame[MAX_FRAME_LEN];
    uint8_t n = build_ping(id, frame);
    if (!transmit_blocking(frame, n)) return ERR_TX_BUSY;
    uint8_t resp[MAX_RESPONSE_LEN];
    uint8_t got = read_response(resp, 6, timeout_us);   // ping response is 6 bytes
    if (got < 6) return ERR_TIMEOUT;
    uint8_t resp_id, err, params[MAX_PARAM_BYTES], plen;
    if (!parse_response(resp, got, &resp_id, &err, params, &plen)) return ERR_BAD_FRAME;
    if (resp_id != id) return ERR_BAD_FRAME;
    return err ? ERR_SERVO : OK;
  }

  // READ position (raw 0..4095). Returns OK + writes `pos_out` on success.
  Result read_position(uint8_t id, uint16_t* pos_out, uint32_t timeout_us = 1500) {
    uint8_t frame[MAX_FRAME_LEN];
    uint8_t n = build_read(id, REG_PRESENT_POSITION_L, 2, frame);
    if (!transmit_blocking(frame, n)) return ERR_TX_BUSY;
    uint8_t resp[MAX_RESPONSE_LEN];
    uint8_t got = read_response(resp, 8, timeout_us);
    if (got < 8) return ERR_TIMEOUT;
    uint8_t resp_id, err, params[MAX_PARAM_BYTES], plen;
    if (!parse_response(resp, got, &resp_id, &err, params, &plen)) return ERR_BAD_FRAME;
    if (resp_id != id || plen < 2) return ERR_BAD_FRAME;
    if (err) return ERR_SERVO;
    *pos_out = pack_u16_le(params[0], params[1]);
    return OK;
  }

  // WRITE goal position (raw 0..4095). Returns OK if servo ACKs with no err.
  Result write_goal_position(uint8_t id, uint16_t goal, uint32_t timeout_us = 1500) {
    uint8_t data[2];
    unpack_u16_le(goal, &data[0], &data[1]);
    uint8_t frame[MAX_FRAME_LEN];
    uint8_t n = build_write(id, REG_GOAL_POSITION_L, data, 2, frame);
    if (!transmit_blocking(frame, n)) return ERR_TX_BUSY;
    uint8_t resp[MAX_RESPONSE_LEN];
    uint8_t got = read_response(resp, 6, timeout_us);
    if (got < 6) return ERR_TIMEOUT;
    uint8_t resp_id, err, params[MAX_PARAM_BYTES], plen;
    if (!parse_response(resp, got, &resp_id, &err, params, &plen)) return ERR_BAD_FRAME;
    if (resp_id != id) return ERR_BAD_FRAME;
    return err ? ERR_SERVO : OK;
  }

  // SYNC_WRITE goal positions to a list of servo IDs. Broadcast, no ACK
  // returned — caller follows up with reads if confirmation matters.
  Result sync_write_goal_positions(const uint8_t* ids, const uint16_t* goals, uint8_t n) {
    if (n == 0) return OK;
    if (n > 12) return ERR_BAD_FRAME;   // bounded for v1 (12 servos)
    uint8_t payload[12 * 2];
    for (uint8_t i = 0; i < n; i++) {
      unpack_u16_le(goals[i], &payload[i * 2], &payload[i * 2 + 1]);
    }
    uint8_t frame[MAX_FRAME_LEN];
    uint8_t fn = build_sync_write(REG_GOAL_POSITION_L, 2, ids, n, payload, frame);
    if (!transmit_blocking(frame, fn)) return ERR_TX_BUSY;
    return OK;
  }

  // Direct OE control — kept inline for the main-loop scope hook
  // (service_bus_stub() toggles these during bring-up).
  inline void set_tx() {
    digitalWrite(tx_oe_pin_, HIGH);
    digitalWrite(rx_oe_pin_, HIGH);
  }
  inline void set_rx() {
    digitalWrite(tx_oe_pin_, LOW);
    digitalWrite(rx_oe_pin_, LOW);
  }

 private:
  uint8_t  tx_oe_pin_;
  uint8_t  rx_oe_pin_;
  uint32_t baud_;
};

}  // namespace feetech
