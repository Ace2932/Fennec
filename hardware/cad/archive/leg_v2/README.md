# Leg V2 — 2-DOF Simplified

Built 2026-05-25 after photo reference review. Drops thigh-pitch DOF for 3-part architecture.

## What changed from V1

V1 = 4 brackets, 3 DOF (hip-roll + hip-pitch + knee). Per photos, hip is mechanically 2 stacked brackets (1 servo each) — can't merge into "1 compact hip block" without losing DOF.

V2 = **3 brackets, 2 DOF (hip-roll + knee)**. Drop hip-pitch. Robot can abduct legs sideways + bend knee. Walks via knee+roll coordination (less natural gait, but functional).

## Topology

```
chassis
  └── Hip-Block (Shoulder-V2-Parametric)   ← hip-roll servo
        └── Femur                            ← knee servo at distal end
              └── Tibia                      ← shank + foot
```

## Parts (reused from V1 except Hip-Block)

| Part | Source | Volume | Notes |
|---|---|---|---|
| Hip-Block | `Shoulder-V2-Parametric` (new parametric build) | 41.4 cm³ | Bbox 63.65 × 43.05 × 42.55. Body pocket + horn relief through top cap. 4× M3 inserts. |
| Femur | V1 `Femur` PS (unchanged, hardcoded) | 188 cm³ | Bbox 30 × 40 × 190. Knee body cavity at distal end. |
| Tibia | V1 `Tibia` PS (unchanged, hardcoded) | 58.7 cm³ | Bbox 22 × 20 × 134. 4× M2.5 knee horn holes + M3 foot. |

Total per leg: ~288 cm³ PA6-CF × 4 legs = 1.15 L = ~1.3 kg structural.

## Assembly

`Leg-V2-Assembly.step` (62 kB) — 3 parts, 2 revolute mates:

| Mate | First (parent) | Second (child) | Axis | Limits | Offset |
|---|---|---|---|---|---|
| HipRoll | Hip-Block face JTe + offsetX=+12.5 (spline shift) | Femur face JLi | Z | ±45° | firstOffsetX = 12.5 |
| Knee | Femur face JPW + offsetY=-89 (knee spline shift along femur) | Tibia face JNi | Y | -10°/+120° | firstOffsetY = -89 |

## Photo-reference design insights captured

From photos, V2 incorporates:

- **Compact hip-block** (replaces V1's Shoulder + HipFrame two-part stack — now just one bracket since hip-pitch dropped)
- **Knee servo in femur distal cavity** (matches photo — knee mounted near foot, not inside femur middle)
- **Top horn relief through-hole on Hip-Block** (matches photo — horn protrudes through bracket top, not buried in open pocket)
- **M3 heat-set insert mounts** (matches assembly hardware visible in photos)

Deferred for V3 (not in V2):
- **Yellow cosmetic shell** wrapping femur — V2 has structural piece only, no decorative cover
- **Cable conduit slots** for TTL daisy-chain — V2 routes cables externally
- **688ZZ back-bearings** on knee servo back-shaft — V2 uses horn-clamp fixation only
- **Restoring hip-pitch DOF** — V3 would re-add the HipFrame piece between Hip-Block and Femur

## OnShape doc state

- Doc: `NovaSM3-Leg-V4` (id `dc722115b661b8e675565adf`) — same doc as V1
- Assembly: `Leg-V2-Assembly` (id `42b2b1edf8112fa8eecd8063`)
- Parts (all already in doc):
  - `Shoulder-V2-Parametric` (id `86c683336d1cc4b52c83e5c6`) — parametric, see `parametric-servo-fit.md`
  - `Femur` (id `feb65d4015e64f7f4687f7f6`) — V1 hardcoded
  - `Tibia` (id `13486f6209e3095449db6730`) — V1 hardcoded

## Print + assembly notes

Same as V1 (`leg_v4/README.md`):
- PA6-CF, Bambu P1S, hardened steel nozzle, 24 h dry, Magigoo PA
- First-article protocol before batching 4 legs
- M3 Ruthex heat-set inserts in Hip-Block slab (chassis mount)
- M2.5 horn screws for each servo joint (Loctite 243)
- M3 foot screw with TPU pad (see `patterns.md` §8b for foot design)

## What you're trading by dropping hip-pitch

Pro: 3 brackets instead of 4 → ~33% less print time + assembly complexity.
Con: Leg can't independently lift forward/back. Walking gait needs body-pitch compensation via knee timing. Limits running, side-step, recovery from disturbances.

For V1 prototype / proof-of-concept: V2 is sufficient. For competitive gait performance: restore hip-pitch in V3.

## Iterating to V3 (restore hip-pitch)

Add HipFrame back between Hip-Block and Femur:
1. Reuse V1's `HipFrame` Part Studio (still in doc, id `8aba8cc0ba5b06371a7d96dc`)
2. New assembly: Hip-Block → HipFrame (hip-pitch revolute Y) → Femur (knee revolute Y) → Tibia
3. Apply offsets per V1 `leg_v4/README.md` mate spec

That's the back-compat path. V1 doc already has everything needed.
