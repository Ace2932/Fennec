// =============================================================================
// NovaSM3 Leg V5 — common parameters
// =============================================================================
// V5 strategy: preserve original NovaSM3 STL outer shape + carve STS3215
// cavity inside. First-cut cavities centered at bbox center of each part.
// User iterates position, rotation, holes, bearing seat in subsequent passes.
//
// Source STLs: ~/codebases/NOVA/original_body_files/SM3_Frame_*.stl
// STS3215 dims: STEP-verified at
// ~/codebases/NOVA/feetech_servo_models/feetech_sts3215-1.snapshot.6/
// feetech-sts3215/STS3215_03a v1.step

$fn = 64;
EPS = 0.05;

// ---- STS3215 body dims (STEP-verified) -----------------------------------
SERVO_L   = 45.40;   // body length, long axis
SERVO_W   = 24.80;   // body width
SERVO_H   = 34.30;   // body height between horn-disc faces
SERVO_BBOX_Z = 39.60; // full bbox including horn discs

SPLINE_X_OFFSET = 12.50;  // spline offset from body center along L axis
HORN_DISC_OD    = 20.0;
HORN_DISC_THK   = 2.5;
BACK_SHAFT_OD   = 6.0;
BACK_SHAFT_LEN  = 1.2;

// Horn screw pattern (M2.5 clearance, 14 mm BCD at ±45°)
HORN_SCREW_D    = 2.9;     // M2.5 wider clearance
HORN_BCD        = 14.0;

// ---- Tolerances ---------------------------------------------------------
CLR_BODY    = 0.30;  // STS3215 body in cavity (snug press-fit, PA6-CF)
CLR_BEARING = 0.05;  // 688ZZ press-fit
CLR_SHAFT   = 0.25;  // back-shaft slip

// ---- 688ZZ bearing -------------------------------------------------------
BEARING_OD  = 16.0;
BEARING_H   = 5.0;
BEARING_ID  = 8.0;

// =============================================================================
// MODULES
// =============================================================================

// STS3215 body cavity — rectangular prism + horn relief on +Z + back-shaft relief on -Z
// Position: cavity centered at LOCAL origin. Long axis = X. Short axis = Y. Shaft = Z.
// Caller translates + rotates to fit inside the STL.
module sts3215_cavity(extra_clr = 0) {
    c = CLR_BODY + extra_clr;
    union() {
        // Body rect prism
        cube([SERVO_L + 2*c, SERVO_W + 2*c, SERVO_H + 2*c], center = true);
        // Horn relief (top, +Z, at spline X offset)
        translate([SPLINE_X_OFFSET, 0, SERVO_H/2])
            cylinder(d = HORN_DISC_OD + 2*0.5, h = HORN_DISC_THK + 5, center = false);
        // Back shaft relief (bottom, -Z, at spline X offset)
        translate([SPLINE_X_OFFSET, 0, -(SERVO_H/2) - BACK_SHAFT_LEN - 5])
            cylinder(d = BACK_SHAFT_OD + 2*CLR_SHAFT, h = BACK_SHAFT_LEN + 10, center = false);
    }
}

// 688ZZ bearing seat (use on yoke arm opposite the horn output)
module bearing_seat() {
    cylinder(d = BEARING_OD + 2*CLR_BEARING, h = BEARING_H + 1, center = false);
}

// Horn relief through-hole (Ø 22 mm)
module horn_relief(depth = 10) {
    cylinder(d = HORN_DISC_OD + 2.0, h = depth, center = false);
}

// TTL wire pass-through slot (14 × 5 mm — 2× JST-XH 3-pin side-by-side)
module ttl_slot(depth = 20) {
    cube([14, 5, depth], center = true);
}

// STS3215 SOLID body — for visualization (actual servo placed in cavity).
// Use this with same translate + rotate as sts3215_cavity() to see fit.
// Body centered on origin, shaft along Z.
module sts3215_solid() {
    union() {
        // Main body block
        cube([SERVO_L, SERVO_W, SERVO_H], center = true);
        // Top horn disc (+Z side, at spline X offset)
        translate([SPLINE_X_OFFSET, 0, SERVO_H/2])
            cylinder(d = HORN_DISC_OD, h = HORN_DISC_THK);
        // Bottom back shaft (-Z side, at spline X offset)
        translate([SPLINE_X_OFFSET, 0, -SERVO_H/2 - BACK_SHAFT_LEN])
            cylinder(d = BACK_SHAFT_OD, h = BACK_SHAFT_LEN);
    }
}
