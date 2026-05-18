# CAD

**Primary tool: OnShape** (browser-based, public docs free tier).

## Will contain
- Leg redesign — STS3215 pocket geometry, 25T horn fitment, U-bracket back-shaft support
- Chassis modifications — Jetson mount, RealSense bracket, L2 top-center riser
- Cable management — daisy-chain bus routing, star-injection points, strain relief
- Print orientation notes per part (fiber alignment for PA6-CF on Bambu P1S)

## Reference geometry sources

- **STS3215** (19kg + 30kg variants) — pull STEP from GrabCAD or Feetech site, import to OnShape
- **NovaSM3 reference chassis** — repo is `cguweb-com/Arduino-Projects/tree/main/Nova-SM3` (the `SovGVD/NovaSM3` URL in old docs was a misattribution; that repo does not exist). **STEP files are NOT in the repo** — only STL. For OnShape import, either: (a) import STL as a static body, (b) re-model from STL + datasheet + caliper measurements, or (c) contact Chris Locke for the original Fusion 360 source. See [`docs/research/2026-05-17-notes.md`](../../docs/research/2026-05-17-notes.md) §8.
- **Feetech 25T servo horns** — datasheet dims, model in OnShape from scratch
- **Calipers** for in-hand cross-check (back-shaft length, mounting hole pitch, horn spline)

## Workflow

1. OnShape public doc for the assembly
2. Export STEP for archive / sharing
3. Export STL → Bambu Studio slice → P1S print
4. PA6-CF prints: 24h drier first, Magigoo PA glue stick on textured PEI plate, 0.4 mm hardened hotend

## Files

- Source: OnShape public doc (link here once created)
- Exports: `*.step`, `*.stl` committed to this directory
