# Parametric STS3215 Fit — OnShape Workflow

> **Superseded for legs (2026-05-26).** The legs moved to the V5 OpenSCAD
> original-shell-carve track (`leg_v5/`), which uses a literal `CLR_BODY` rather
> than an OnShape Variable Studio. The **PA6-CF press-fit clearance calibration
> below is still canonical** — V5's `CLR_BODY = 0.30 mm` is pulled from here —
> but the OnShape `leg-vars` parametric workflow describes the rejected V4 doc.
> Keep this for the clearance method + tolerance reasoning; ignore the OnShape
> Variable-Studio mechanics unless building chassis parts in OnShape.
>
> **leg_v6 note (2026-07-05):** v6 pockets use `CLR_POCKET = 0.45` **drop-in**
> (servo located by its case-column screws, walls only guide) — deliberately
> looser than the 0.30 press calibration here, which applies to v5-style
> carved press pockets and bearing seats only.

How to design your own brackets in OnShape that **stay fit-correct** when STS3215 dims change (e.g., new servo batch arrives with ±0.1 mm tolerance shift). Built around the existing `leg-vars` Variable Studio in `NovaSM3-Leg-V4` doc.

## Source of truth

Variable Studio `leg-vars` (element id `0dc53880d81b63d47a7402ff` in doc `dc722115b661b8e675565adf`) holds every STS3215 dim + bracket clearance + derived sizes. **Never hardcode a servo dim in a sketch. Always reference via `#variable_name`.**

### STS3215 root vars (STEP-verified, manufacturer-fixed)

| Var | Value | Source |
|---|---|---|
| `sts_body_l` | 45.40 mm | STEP `STS3215_03a v1.step`, body long axis |
| `sts_body_w` | 24.80 mm | STEP, body short axis |
| `sts_body_h` | 34.30 mm | STEP, **between horn-disc faces** (NOT bbox z) |
| `sts_bbox_z` | 39.60 mm | full bbox z including both horn discs |
| `sts_spline_x` | 12.50 mm | spline X offset from body center (CRITICAL) |
| `horn_disc_od` | 20.0 mm | top horn disc OD |
| `horn_bcd` | 14.0 mm | horn screw bolt-circle dia |
| `horn_screw_d` | 2.5 mm | M2.5 horn screw |
| `horn_screw_clr` | 2.9 mm | M2.5 wider clearance |
| `back_shaft_d` | 6.0 mm | bottom reaction shaft OD |
| `bearing_od` | 16.05 mm | 688ZZ + press-fit clearance |
| `bearing_h` | 5 mm | 688ZZ width |

### Clearance + workflow vars (project-tunable)

| Var | Value | Use |
|---|---|---|
| `clr_body` | 0.25 mm | press-fit clearance, add to all servo-cavity dims |
| `clr_bearing` | 0.05 mm | added to bearing OD for press fit |
| `horn_relief_d` | 22.0 mm | horn disc OD + 2 mm clearance |
| `horn_relief_r` | 11 mm | radius for `variableRadius` sketches |
| `m3_clr` | 3.4 mm | M3 clearance hole |
| `insert_bore` | 4.0 mm | Ruthex M3 heat-set insert bore |
| `bracket_wall` | 4 mm | generic structural wall thickness |
| `top_cap` | 2 mm | top cap above pocket (where horn protrudes) |
| `slab_overhang` | 10 mm | chassis-mount slab overhang past tower footprint |

### Derived pocket dims (depth-1 chain, works in OnShape UI)

| Var | Expression | Resolved |
|---|---|---|
| `pocket_x` | `#sts_body_l + #clr_body` | 45.65 mm |
| `pocket_y` | `#sts_body_w + #clr_body` | 25.05 mm |
| `pocket_z` | `#sts_body_h + #clr_body` | 34.55 mm |

### Bracket bbox vars (LITERALS — MCP limitation)

These should be expressions like `#pocket_x + #wall_2x` but the OnShape MCP `set_variable` rejects expressions deeper than 2-operand. **In OnShape UI you can edit these to true expressions for full parametric.** Current values are pre-computed literals matching the expression intent.

| Var | Literal | Intended expression |
|---|---|---|
| `wall_2x` | `#bracket_wall + #bracket_wall` | works (depth 1) |
| `shoulder_tx` | 53.65 mm | `#pocket_x + #wall_2x` |
| `shoulder_ty` | 33.05 mm | `#pocket_y + #wall_2x` |
| `shoulder_tz` | 36.55 mm | `#pocket_z + #top_cap` |
| `shoulder_sx` | 63.65 mm | `#shoulder_tx + #slab_overhang` |
| `shoulder_sy` | 43.05 mm | `#shoulder_ty + #slab_overhang` |
| `shoulder_slab_z` | 6 mm | literal (heat-set insert length) |
| `shoulder_bolt_pitch` | 30 mm | literal (chassis bolt contract — fixed) |

**To fix in OnShape UI:** open `leg-vars` Variable Studio → edit each var → paste the intended expression. Then changing `sts_body_l` propagates through every bracket dim.

## OnShape UI workflow — building a new bracket

### Step 1: link the Variable Studio

In your Part Studio, top of feature tree → click Insert → "Add Variable Studio" → pick `leg-vars`. Now `#var_name` references resolve in any sketch dim.

### Step 2: sketch with constraint-first style

DON'T just type coordinates. Use the DIMENSION tool to add constraints:
- Click rect dimension → type `#shoulder_sx` (slab width)
- Click rect dimension → type `#shoulder_sy` (slab depth)
- Add a MIDPOINT constraint between rect center + sketch origin → keeps rect centered when dims change

### Step 3: extrude with variable depth

When you click Extrude → in the depth field, type `#shoulder_slab_z`. Extrude binds depth to variable; change var, extrude updates.

### Step 4: servo body pocket recipe

On the face where servo body enters bracket (typically tower top or U-bracket arm):

1. Sketch RECT — dim width = `#pocket_x`, dim height = `#pocket_y`, centered on the servo cavity center
2. Add a CIRCLE — dim radius = `#horn_relief_r`, position center = (`#sts_spline_x`, 0) relative to rect center — this is the horn protrusion through-hole
3. Extrude REMOVE — depth = `#pocket_z`, direction = INTO material

Optional refinement: extrude the horn relief separately (deeper, through the top cap into the cavity) so horn disc protrudes ABOVE the bracket face by ~2 mm.

### Step 5: horn cap mating face recipe

For a bracket that connects to a servo HORN (not body — e.g., femur cap mates to thigh-pitch horn):

1. Pick face → sketch
2. Sketch construction circle, dim DIAMETER = `#horn_bcd` (14 mm BCD)
3. Place 4 holes ON the construction circle at ±45° from cardinal
4. Each hole dim = `#horn_screw_clr` (2.9 mm wider clearance for slop)
5. Extrude REMOVE through-cap

**Constraint pattern for 4 holes on 14 mm BCD at ±45°:**
- Hole 1: DISTANCE_FROM_HORIZONTAL = `#horn_bcd / 2 / sqrt(2)` and DISTANCE_FROM_VERTICAL = same (puts at +45°)
- Or simpler: use create_linear_pattern with 2x2 grid at spacing `#horn_bcd / sqrt(2)`

### Step 6: back-bearing seat recipe (for U-bracket arms)

For the arm opposite the servo body cavity (back-shaft side):

1. Pick face → sketch
2. Circle at (`#sts_spline_x`, 0) relative to face center — dim DIAMETER = `#bearing_od` (16.05 mm with clearance)
3. Extrude REMOVE depth = `#bearing_h` (5 mm)

Add a small relief hole (Ø `#back_shaft_d + 1 mm` = 7 mm) deeper inside the seat so the shaft tip doesn't bottom out:

4. Sketch on bottom of bearing seat: smaller circle, dim DIAMETER = 7 mm
5. Extrude REMOVE 2 mm

### Step 7: insert holes for chassis mount

Chassis/shoulder mount → drill 4× M3 heat-set inserts on slab bottom face:

1. Sketch 4 circles at (`±#shoulder_bolt_pitch/2`, `±#shoulder_bolt_pitch/2`) — radius = `#insert_bore / 2` (=2 mm)
2. Extrude REMOVE depth = `5.7 mm` (Ruthex M3 length, leaves 0.3 mm relief at top to avoid coplanar boundary with tower bottom)

### Step 8: validate

After each bracket built, drop the STS3215-Mock part (`f001f825d89c7bb2d884b6f6` in this doc) into an assembly with your bracket. Mate horn or body to the corresponding bracket face. If they fit cleanly, you're good. If interference, tune `clr_body` up (loosen fit) or the bracket dim that's pinching.

## MCP set_variable limitations (workarounds)

The MCP `set_variable` parser rejects:
- Constants combined with var refs: `#var + 8 mm` ❌
- Multiplication: `2 * #var` ❌
- Parentheses: `(#var)` ❌
- 3+ operand expressions: `#a + #b + #c` ❌

It accepts:
- Single literal: `10 mm` ✅
- Single var: `#var` ✅
- 2-var add: `#var1 + #var2` ✅ (depth-1)

**Workarounds:**
1. Pre-compute literal in your head, set as literal — kills parametric chain
2. Chain helper vars (e.g., `wall_2x = #bracket_wall + #bracket_wall`) — preserves chain for one level
3. **Edit in OnShape UI** for full parametric (UI accepts any expression)

For derived bracket dims like `shoulder_tx = pocket_x + bracket_wall * 2`, only the OnShape UI route works. Tip: after I/MCP set the initial literal value, you go into OnShape UI, click the variable, replace literal with the expression. Future MCP calls won't overwrite the expression unless you re-set the var.

## Sketch tool variable params (MCP)

When using MCP sketch tools, pass these for direct var binding (avoids needing to add DIMENSION constraints manually):

- `create_sketch_rectangle`: `variableWidth="var_name"`, `variableHeight="var_name"` — binds rect dim to var
- `create_sketch_circle`: `variableRadius="var_name"` — binds radius (Center binding `variableCenter` is BROKEN per skill — don't use)
- `create_extrude`: `variableDepth="var_name"` — binds extrude depth

Pass the var name **without** the `#` prefix (the tools auto-prepend it).

**Warning:** if the var doesn't exist OR is a depth-2+ derived chain, MCP issues SKETCH_DIMENSION_MISSING_PARAMETER (WARNING) and the sketch falls back to the literal seed corner coords. Geometry is still correct but parametric binding silently drops.

## Example: building Shoulder-V2-Parametric

The new `Shoulder-V2-Parametric` Part Studio (`86c683336d1cc4b52c83e5c6`) in `NovaSM3-Leg-V4` doc demonstrates this. 10 features, all dims driven by vars (where MCP allowed):

1. Slab footprint sketch — variableWidth=`shoulder_sx`, variableHeight=`shoulder_sy`
2. Slab extrude NEW — variableDepth=`shoulder_slab_z`
3. Tower footprint sketch on slab top — variableWidth=`shoulder_tx`, variableHeight=`shoulder_ty`
4. Tower extrude ADD — variableDepth=`shoulder_tz`
5. Horn relief circle on tower top — variableRadius=`horn_relief_r`, center literal (12.5, 0) since `variableCenter` broken
6. Horn relief extrude REMOVE 3 mm (literal — could be `#top_cap + 1 mm` but MCP rejects)
7. Pocket footprint sketch on tower top — variableWidth=`pocket_x`, variableHeight=`pocket_y` [WARNING fallback to literal seed]
8. Pocket extrude REMOVE 34.55 mm (literal seed)
9. 4× insert hole sketch on slab bottom — literal positions (±15, ±15)
10. Insert extrude REMOVE 5.7 mm

Use this as your template for HipFrame, Femur, Tibia rebuilds.

## What to do when STS3215 batch tolerance is off

You receive a batch of servos. Caliper-measure one — body comes out 45.6 × 24.9 × 34.5 (slightly oversized). Steps:

1. Open `leg-vars` Variable Studio in OnShape UI
2. Edit `sts_body_l` → 45.60 mm
3. Edit `sts_body_w` → 24.90 mm
4. Edit `sts_body_h` → 34.50 mm
5. If derived chain is properly set up (`pocket_x = #sts_body_l + #clr_body`), all bracket pockets resize automatically
6. If derived chain is literal (current state), manually update: `pocket_x` = 45.85, `pocket_y` = 25.15, `pocket_z` = 34.75, then update `shoulder_tx` = `pocket_x + wall_2x` = 53.85, etc.
7. Re-export STL → re-print first-article → verify fit

That's the parametric workflow.

## See also

- `dimensions.md` — canonical STS3215 STEP-verified dims (single source of truth — variables mirror these)
- `patterns.md` — CadQuery macros for the same dims (for non-OnShape utility parts)
- `leg_v5/README.md` — canonical leg design (V5 OpenSCAD); pulls `CLR_BODY` from this file
- `archive/leg_v4/README.md` — rejected V4 OnShape build summary (hardcoded, pre-parametric)
- Jarvis OnShape MCP skill at `~/.claude/plugins/cache/jarvis-onshape-mcp/jarvis-onshape-mcp/1.2.0/skills/onshape/SKILL.md` — full OnShape MCP protocol reference
