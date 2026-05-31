# V5 Iteration Workflow

## TL;DR

1. Open `coax.scad` (or femur/tibia/shoulder) in OpenSCAD GUI
2. Set `OVERLAY = true` at top of file
3. Hit F5 → see original STL (yellow) with cavity (red translucent) overlaid
4. Adjust `CAVITY_CENTER` + `CAVITY_ROT` until cavity sits in right place
5. Set `OVERLAY = false` → F6 (full render) → File → Export → STL

## Per part — what to verify in OVERLAY mode

### coax.scad

- Cavity must sit in MAIN RECTANGULAR BODY, NOT in the circular extrusion (the disc-shaped output that mates to femur horn)
- Servo shaft direction (cavity's local Z) should point toward where you want the THIGH-PITCH HORN OUTPUT to be
- Walls in original: 6.4 mm X / 0.35 mm Y (slot side) / 11.6 mm Z — STS3215 barely fits in original coax shape

### femur.scad — RESOLVED, fits

- Knee servo cavity carved + confirmed. Femur prints as **shell + cover**; both
  carry the SAME cavity via the shared `femur_params.scad` (edit placement once,
  both rebuild). Tight in Z but clears with `CLR_BODY` — first-article to confirm.
- Visible features: proximal disc (where coax horn bolts in), beam, distal mount tab

### tibia.scad — PASSIVE, no cavity

- Confirmed passive L-shaped shank. No servo, no cavity cut — knee servo lives in
  the femur and drives the tibia through the proximal horn-cap. Leave `tibia*.scad`
  as plain `import()`.

### shoulder.scad

- Original has 2 large circular horn cutouts in the middle frame
- Verify these match STS3215 horn disc Ø 20 mm
- May not need cavity cut — frame already has servo space

## Common adjustments

**Shift cavity along an axis:**
```scad
CAVITY_CENTER = [X, Y, Z];   // mm in original STL's coords
```

**Rotate servo orientation:**
```scad
CAVITY_ROT = [rx, ry, rz];   // degrees
// [0, 0, 0]    — shaft along Z (vertical)
// [90, 0, 0]   — shaft along Y
// [0, 90, 0]   — shaft along X (along leg)
// [90, 0, 90]  — shaft along Y, body L along Z
```

**Plug an old hole** (e.g. old hobby-servo screw holes):
```scad
difference() {
    union() {
        import(ORIGINAL_STL);
        // Add cylinders/cubes to plug unwanted holes
        translate([15, 0, 30]) cylinder(d=4, h=5);
    }
    translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
}
```

**Add back-bearing seat:**
```scad
difference() {
    import(ORIGINAL_STL);
    translate(CAVITY_CENTER) rotate(CAVITY_ROT) sts3215_cavity();
    // Add 688ZZ pocket on opposite arm
    translate([0, -20, 28.8]) rotate([90, 0, 0]) bearing_seat();
}
```

**Add wire slot:**
```scad
// add a TTL pass-through slot
translate([0, 22, 50]) rotate([0, 0, 0]) ttl_slot(depth=15);
```

## Modules in `leg_v5_common.scad`

| Module | Use |
|---|---|
| `sts3215_cavity(extra_clr=0)` | Servo body cavity + horn relief + back-shaft relief |
| `bearing_seat()` | 688ZZ pocket (Ø 16 + clr, depth 5 mm) |
| `horn_relief(depth)` | Ø 22 through-hole for horn protrusion |
| `ttl_slot(depth)` | 14 × 5 mm wire pass-through |

## Build all

```bash
cd hardware/cad/leg_v5
./build_all.sh
```

Outputs 9 STLs: shoulder + coax_L/R + femur_shell_L/R + femur_cover_L/R + tibia_L/R.

## Watch-out: thin walls in tight parts

The original NovaSM3 was designed for SMALLER hobby servos (~20 mm body). STS3215 is 45.4 × 24.8 × 34.3 mm — larger in every dimension. All 4 shapes now fit with the carved cavities, but coax is tight (X-bbox 37.6 mm vs 45.4 mm servo spanning the diagonal). First-article every shape and check for <1 mm walls before batching. If a wall comes out paper-thin:

1. **Plug + thicken** the offending face with a `union()` cube before the cavity cut (snippet above)
2. **Scale up the original STL** by 1.3–1.5× before cutting cavity (loses true-to-original aesthetic but functional)
3. Rejected earlier approaches (CadQuery V3.1, OnShape V4) are in `../archive/` if you need a purpose-built fallback for one link.
