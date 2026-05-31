# CAD archive — superseded leg designs

Rejected leg-design iterations. Kept for reference geometry + STEP files only.
**Canonical leg design is `../leg_v5/`** (OpenSCAD original-shell-carve).

| Dir / file | Tool | Why rejected |
|---|---|---|
| `leg_v2/` | OnShape STEP assembly | early block-bracket geometry, lost original NovaSM3 styling |
| `leg_v3/` | CadQuery (V3.1) | body-driven dual-shaft yoke — all-new mechanical architecture, heavier/taller than original |
| `leg_v4/` | OnShape via Jarvis MCP | rectangular brackets from scratch, blockier than original |
| `leg-v4-onshape-plan.md` | — | build plan for the rejected V4 OnShape approach |

## Why V5 won

V5 keeps the original Chris Locke NovaSM3 outer shape (curves, fillets, mount
patterns) and only carves an STS3215-sized cavity inside via OpenSCAD boolean
difference. Closest print to the original design intent, just sized for the
bigger Feetech servo. See `../leg_v5/README.md`.

## Still-referenced bits

- `leg_v3/*.step` — V3.1 STEP exports are still listed as reference bodies in
  `docs/cad-tooling.md` (importable into OnShape for chassis interface work).
- `leg_v3/leg_common.py` — STS3215 envelope constants (cross-checked against
  `../dimensions.md`, which wins on conflict).
