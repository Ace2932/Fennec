// Posture-aware hfe backstop (#142) — the firmware's chassis protection.
//
// WHY IT EXISTS. The per-joint raw limit table in main.cpp protects the
// LINKAGE: one joint, one window. It cannot protect the CHASSIS, because how
// far a leg may fold depends on where that leg's HIP is. Measured on the
// chassis gate (nova_ops.rom_envelope), front leg:
//
//     haa   0 -> fold cap +66.4 deg
//     haa -15 -> fold cap +12.3 deg      leg tucked inboard, under the LiPo
//
// (Those are the HOST's numbers, i.e. the table with rom_envelope.MARGIN_DEG
// applied — 1.5 deg since 2026-08-06, covering the producer's measured sampling
// scatter. The raw table cells are 67.9 and 13.8; what gets published here is
// the margined pair, so quote the margined pair.)
//
// A scalar cap is therefore permissive exactly where the hazard is. One that
// covered the whole legal haa range would have to be +12.3, which deletes the
// gait (the trot peaks at +59.4). So the bound has to see posture.
//
// WHAT THIS IS NOT. It is not a chassis model and does no geometry. The host
// measures the envelope, converts it to RAW COUNTS with the same rad_to_raw
// the limit table uses, and publishes it (nova_ops safety_envelope/
// firmware_limits.py, build_hfe_envelope_data). This just selects a bucket and
// clamps. Keeping every unit conversion on one side means the two layers
// cannot disagree about what a raw count means.
//
// Pure logic, header-only, no Arduino calls — so the native suite can test it
// (pio test -e native), same as safety_state.h. That matters more than usual
// here: the micro-ROS build cannot be compiled on a Mac, so without this the
// only verification off-Jetson would be "it parses".

#pragma once

#include <math.h>
#include <stddef.h>
#include <stdint.h>

namespace nova {

constexpr size_t HFE_ENV_LEGS = 4;
constexpr size_t HFE_ENV_MAX_BUCKETS = 40;   // host emits 24 (the #181 grid)
constexpr size_t HFE_ENV_STRIDE = 4;         // haa_lo, haa_hi, hfe_lo, hfe_hi
constexpr size_t HFE_ENV_MAX_FLOATS =
    1 + HFE_ENV_LEGS * HFE_ENV_MAX_BUCKETS * HFE_ENV_STRIDE;
constexpr uint16_t HFE_ENV_RAW_MAX = 4095;

// joint_id_map.yaml is PER-LEG SEQUENTIAL: FL 1-3, FR 4-6, RL 7-9, RR 10-12,
// each leg ordered haa -> hfe -> kfe. Zero-based, leg L has haa at 3L and hfe
// at 3L+1 — and the payload's leg order (FL, FR, RL, RR) is that same order.
// BOTH halves have to stay true. Clamping one leg's fold against another
// leg's hip is the exact failure this project keeps hitting at seams, so it is
// named here and tested rather than inlined as a bare 3.
inline size_t hfe_env_haa_index(size_t leg) { return 3 * leg; }
inline size_t hfe_env_hfe_index(size_t leg) { return 3 * leg + 1; }

class HfeEnvelope {
 public:
  //: true once a valid table has been installed. Until then apply() is a
  //: no-op — homing itself must move joints outside walk ROM.
  bool active() const { return n_ != 0; }
  uint8_t buckets() const { return n_; }
  uint32_t clamp_count() const { return clamps_; }

  // Install a table, or reject it WHOLE. Returns false and changes nothing on
  // any fault: a half-applied envelope would clamp some legs against the new
  // table and some against the old, which is worse than either alone.
  //
  // The coverage check is the load-bearing one. apply() declines to clamp a
  // leg whose haa matches no bucket, so a table with a GAP would be a silent
  // hole in the backstop at exactly the haa values inside it. Requiring
  // contiguous 0..4095 coverage per leg means that hole cannot be installed.
  bool load(const float* data, size_t size) {
    if (data == nullptr || size < 1) return false;
    const float n_f = data[0];
    if (isnan(n_f) || n_f < 1.0f || n_f > (float)HFE_ENV_MAX_BUCKETS) return false;
    const size_t n = (size_t)n_f;
    if (size != 1 + HFE_ENV_LEGS * n * HFE_ENV_STRIDE) return false;

    const float* b = &data[1];
    for (size_t leg = 0; leg < HFE_ENV_LEGS; leg++) {
      for (size_t k = 0; k < n; k++) {
        const float* q = &b[(leg * n + k) * HFE_ENV_STRIDE];
        for (size_t f = 0; f < HFE_ENV_STRIDE; f++)
          if (isnan(q[f]) || q[f] < 0.0f || q[f] > (float)HFE_ENV_RAW_MAX)
            return false;
        if (q[0] >= q[1]) return false;   // empty or inverted haa bucket
        if (q[2] > q[3]) return false;    // inverted hfe window (equal = pinned)
        if (k == 0 && q[0] != 0.0f) return false;
        if (k == n - 1 && q[1] != (float)HFE_ENV_RAW_MAX) return false;
        if (k > 0 && q[0] != b[((leg * n + k - 1) * HFE_ENV_STRIDE) + 1])
          return false;                   // gap or overlap between buckets
      }
    }

    for (size_t leg = 0; leg < HFE_ENV_LEGS; leg++) {
      for (size_t k = 0; k < n; k++) {
        const float* q = &b[(leg * n + k) * HFE_ENV_STRIDE];
        haa_lo_[leg][k] = (uint16_t)q[0];
        haa_hi_[leg][k] = (uint16_t)q[1];
        hfe_lo_[leg][k] = (uint16_t)q[2];
        hfe_hi_[leg][k] = (uint16_t)q[3];
      }
    }
    n_ = (uint8_t)n;
    return true;
  }

  // Clamp each leg's hfe value into the window selected by that SAME
  // vector's own haa value, optionally tightened further by a second,
  // independent haa reading (#280).
  //
  // main.cpp calls this TWICE per broadcast, at two different points in the
  // pipeline, because a single call cannot cover both hazards:
  //
  //   PASS 2 (pre-slew, on the FAR commanded target): catches a target that
  //   is illegal AT REST — both joints landing somewhere the chassis gate
  //   would refuse even once the ramp finishes.
  //
  //   PASS 4 (post-slew, on `goals[]` — what is actually about to be
  //   WRITTEN this tick): catches a target where BOTH endpoints are legal
  //   but the PATH between them is not. PASS 3 slews haa and hfe
  //   independently at one shared rate, so whichever has less travel
  //   arrives first and nothing re-evaluates the pair mid-ramp. Modelled on
  //   the real table, a stand->tuck move (haa 0->-15, hfe +60->+10, both
  //   endpoints legal) put the leg 33.9 deg inside the belly-pack exclusion
  //   0.07 s in.
  //
  // A PRE-slew check cannot close that second hazard no matter which haa
  // value selects the bucket: the far hfe target (+10) is already legal at
  // its own final (tightest, since -15 is the most-tucked point on this
  // path) bucket, so nothing ever clamps it, and PASS 3 then chases that
  // already-legal number with no awareness that the intermediate values on
  // the way there are not legal for wherever haa currently is. Measured by
  // simulating PASS 1-3 against the scenario above: a pre-slew call, even
  // intersected with a live present-haa reading, left the violation at
  // 30.4 deg — no different from target-only, because the far target was
  // never the thing that needed clamping. Calling this AGAIN post-slew, on
  // `goals[]`, closes it to 0.0 deg: each leg's own just-computed haa OUTPUT
  // (zero lag relative to its own hfe output — both came out of the same
  // PASS-3 tick) is exactly "where this tick is telling the hip to go", and
  // bounding hfe against THAT rather than the far-off goal is what "the
  // window opens as haa opens" actually requires.
  //
  // present_position/present_mask (default nullptr/0) let a caller ALSO
  // intersect with a live MEASURED haa reading (servo_position_raw, already
  // polled at 50 Hz) — a second, optional layer against the physical leg
  // having overshot or lagged the command (backlash, stall): a measured
  // reading can only make the selected window tighter, never wider, since
  // it is intersected in, not substituted. Per LEG, present is used only
  // when that leg's haa servo has answered at least one poll (present_mask
  // bit set, mirrors servo_present_mask in main.cpp) — an unknown/stale
  // present sample must not be trusted to narrow the window, and refusing
  // to clamp at all on missing telemetry would block motion outright, a
  // worse hazard than the gap this closes. So an absent present sample
  // falls back to using `targets`'s own haa alone, same as if the caller
  // had not passed present_position at all.
  void apply(uint16_t* targets,
             const volatile uint16_t* present_position = nullptr,
             uint16_t present_mask = 0) {
    if (n_ == 0 || targets == nullptr) return;
    for (size_t leg = 0; leg < HFE_ENV_LEGS; leg++) {
      const size_t haa_i = hfe_env_haa_index(leg);
      const size_t hfe_i = hfe_env_hfe_index(leg);

      uint16_t lo, hi;
      // No matching bucket for the target cannot happen — load() rejects any
      // table without gap-free 0..4095 coverage. If it somehow did, leaving
      // hfe unclamped is the deliberate choice: pinning a joint mid-gait on a
      // table we already know is corrupt trades one hazard for a worse one,
      // and the per-joint table still bounds the joint.
      if (!find_window(leg, targets[haa_i], &lo, &hi)) continue;

      if (present_position != nullptr &&
          (present_mask & (uint16_t)(1u << haa_i))) {
        uint16_t plo, phi;
        if (find_window(leg, (uint16_t)present_position[haa_i], &plo, &phi)) {
          if (plo > lo) lo = plo;   // tighter-of-two: narrowest lower bound
          if (phi < hi) hi = phi;   // tighter-of-two: narrowest upper bound
        }
      }

      if (targets[hfe_i] < lo) { targets[hfe_i] = lo; clamps_++; }
      else if (targets[hfe_i] > hi) { targets[hfe_i] = hi; clamps_++; }
    }
  }

 private:
  // Bucket lookup shared by the target and present-position passes of
  // apply(). Returns false if no bucket's haa range contains `haa` — cannot
  // happen on a table that passed load()'s coverage check, but a caller must
  // not clamp against uninitialized lo/hi if it somehow did.
  bool find_window(size_t leg, uint16_t haa, uint16_t* lo, uint16_t* hi) const {
    for (size_t k = 0; k < n_; k++) {
      if (haa < haa_lo_[leg][k] || haa > haa_hi_[leg][k]) continue;
      *lo = hfe_lo_[leg][k];
      *hi = hfe_hi_[leg][k];
      return true;
    }
    return false;
  }

  uint16_t haa_lo_[HFE_ENV_LEGS][HFE_ENV_MAX_BUCKETS];
  uint16_t haa_hi_[HFE_ENV_LEGS][HFE_ENV_MAX_BUCKETS];
  uint16_t hfe_lo_[HFE_ENV_LEGS][HFE_ENV_MAX_BUCKETS];
  uint16_t hfe_hi_[HFE_ENV_LEGS][HFE_ENV_MAX_BUCKETS];
  uint8_t n_ = 0;
  uint32_t clamps_ = 0;
};

}  // namespace nova
