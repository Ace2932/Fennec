# NovaSM3 CAD design — parametric library + headless design loop

Lets parts be **designed/edited headlessly** (by Claude or you) so they always
match the real build: correct STS3215 screw patterns, heat-set inserts, bearing
seats, connector cutouts — all from verified dimensions.

## The loop (no GUI needed)
1. **Author** a `.scad` that `include <../lib/nova_cad_lib.scad>;` (use `include`, NOT `use` — the lib exposes constants `use` won't import) and composes modules. Build parts up from the XY plane (z=0); pass `L = part thickness` to hole modules.
2. **Render** → manifold STL + PNG preview:
   ```bash
   openscad -o part.stl part.scad
   openscad -o part.png --imgsize=700,520 --view=axes --camera=0,0,0,55,0,25,180 part.scad
   ```
3. **Verify** dims: `python3 ../tools/stl_measure.py part.stl` (pure-Python bbox).
4. **Iterate** — tweak params, re-render. (Claude can view the PNG to check shape.)

`demo/demo_horn_bracket.scad` is a worked example (bolts to a real STS3215 horn
+ 2× M3 heat-set bosses) — renders to a clean genus-0 solid, 34×34×11.2 mm.

## What the library gives you (`nova_cad_lib.scad`)
All numbers verified from `dimensions.md` / `parametric-servo-fit.md` / `patterns.md`
(Bambu P1S + PA6-CF tuned):
- **Screws/inserts:** `screw_hole(size,L)`, `screw_counterbore`, `heatset_boss(size)`,
  `heatset_bore` — M2 / M2.5 / M3, Ruthex insert bores + boss OD.
- **STS3215:** `sts_horn_holes` (14 mm BCD), `sts_body_mount_holes` (verified 4×
  M2.5 pattern), `sts_cavity` (press-fit pocket, CLR_BODY).
- **Bearing:** `bearing_seat` (688ZZ, press fit).
- **Cutouts:** `xt30_cutout`, `xt60_cutout`, `estop_22mm`, `m3_panel_mount`.
- **Constants:** STS body/spline/horn, bearing, print clearances.

## What I (Claude) can do with this
- **New parts** (brackets, mounts, adapters, panels) composed from verified primitives.
- **Match current design** — same screw patterns/clearances, no re-measuring.
- **Adjust/reshape** existing `.scad` parts (change params, add features, re-render).
- **Verify** — render + measure each iteration; flag non-manifold / wrong dims.

Limits: OpenSCAD = CSG/parametric (great for mechanical/utility parts). Organic
freeform or large multi-body assemblies → OnShape (Jarvis MCP). Carving cavities
into the original NovaSM3 STLs → the `leg_v5` boolean-carve pattern.
