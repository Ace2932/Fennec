"""
NovaSM3 Leg V3.1 — common parameters + STS3215 envelope + yoke helpers.

ARCHITECTURE (corrected after user feedback 2026-05-24):
  Body-driven dual-shaft mount on every servo. Each upstream link is a
  U-shaped yoke with two arms straddling the servo. One arm anchors the
  servo's top spline via a horn-disc receptacle (M3 x 4 horn screws +
  spline boss clearance). The other arm carries a 688ZZ bearing pressed
  in flush, with the servo's bottom reaction shaft riding in the bore.
  The downstream link is a body shell that surrounds the STS3215 body
  between the two yoke arms and rotates with it.

  Servo 1 (hip abduction, 30 kg STS3215): shoulder yoke → coax body
  Servo 2 (thigh / quad flexion, 19 kg):  coax yoke → femur body
  Servo 3 (knee, 19 kg):                  femur yoke → tibia body

STS3215 verified from real STEP at
~/codebases/NOVA/feetech_servo_models/feetech_sts3215-1.snapshot.6/
feetech-sts3215/STS3215_03a v1.step

The spline (top horn disc) and the bottom horn disc / reaction shaft
are at the SAME X=+12.5 from body center (coaxial pair), so the yoke
arms straddle along the servo's Z (shaft) axis with arms separated by
SERVO_H plus the disc thicknesses plus clearance.
"""
import cadquery as cq
import math

# ============================================================
# STS3215 — verified from STEP
# ============================================================

SERVO_L = 45.40   # body length, long axis (X)
SERVO_W = 24.80   # body width (Y)
SERVO_H = 36.80   # body height in shaft direction (Z), bare body

SPLINE_X_OFFSET = 12.5  # spline + bottom shaft X offset from body center
SPLINE_OD       = 6.0
HORN_BOSS_OD    = 8.0   # raised disc / boss around the spline
HORN_BOSS_LEN   = 1.0

HORN_DISC_OD    = 20.0  # top horn disc OD (driven side)
HORN_DISC_THK   = 8.8   # top assembly extent above servo body (+Z face)

BOT_DISC_OD     = 20.0  # bottom horn disc / idler face OD
BOT_DISC_THK    = 2.1   # bottom assembly extent below servo body (-Z face)
BOT_SHAFT_OD    = 6.0   # bare reaction shaft below the bottom disc (rides
                        # in 688ZZ inner race; 8 mm sleeve adapter on the shaft)
# Note: 688ZZ bore is 8 mm. STS3215 bottom shaft is 6 mm. Use a 6→8 mm
# sleeve adapter, or specify a 6 mm ID bearing (e.g. MR126ZZ 6x12x4).
# Defaulting to 688ZZ with sleeve to match BOM standard bearing.
USE_688_WITH_SLEEVE = True

# Horn screw pattern — 4x M3 on 14 mm BCD, +45 deg from cardinal
HORN_SCREW_BCD  = 14.0
HORN_SCREW_OD   = 3.2

# ============================================================
# Print + tolerance (PA6-CF on Bambu P1S, per project patterns.md)
# ============================================================

SERVO_CLEAR     = 0.5
SHAFT_CLEAR     = 0.30
HORN_DISC_CLEAR = 0.30
BEARING_PRESS   = 0.05

WALL_T          = 3.0
COVER_T         = 4.0
YOKE_ARM_T      = 6.0    # thickness of each yoke arm
CORNER_R        = 3.0

# Ruthex M3 heat-set inserts (project standard)
RUTHEX_M3_BORE  = 4.0
RUTHEX_M3_DEPTH = 5.7
RUTHEX_M3_BOSS_OD = 7.0
LID_SCREW_OD    = 3.4

# 688ZZ ball bearing (project standard)
BEAR_688_ID     = 8.0
BEAR_688_OD     = 16.0
BEAR_688_W      = 5.0

# Wire pass-through — Feetech TTL daisy-chain.
# JST 3-pin XH connector body: ~7.5 mm wide × 5.9 mm tall × 10 mm long.
# 14 mm DIAMETER round hole fits the connector + cable through during
# assembly, plus 2 cables side-by-side for daisy chain in+out.
# Round holes preferred over rectangular slots: easier to print clean,
# no sharp stress risers, more visible at preview-render scale.
WIRE_HOLE_DIA   = 14.0   # cable + connector + slack pass-through

# Legacy rectangular slot dims (kept for any old code that imports these,
# but new builds should prefer WIRE_HOLE_DIA + a circle).
WIRE_SLOT_W     = WIRE_HOLE_DIA
WIRE_SLOT_H     = WIRE_HOLE_DIA

# Derived: total servo footprint Z including both horn discs +
# clearance (this is how tall a body-shell pocket needs to be along Z)
SERVO_TOTAL_Z   = SERVO_H + HORN_DISC_THK + BOT_DISC_THK + 2 * SERVO_CLEAR

# Yoke arm separation = body Z + clearance both sides
YOKE_GAP_Z      = SERVO_H + 2 * SERVO_CLEAR


# ============================================================
# Helpers
# ============================================================

def rounded_box(x, y, z, r=CORNER_R):
    """Outer-rounded box centered on XY, Z from 0 to z."""
    return (cq.Workplane("XY")
            .box(x, y, z, centered=(True, True, False))
            .edges("|Z").fillet(r))


def horn_disc_receptacle_cuts(wp, depth_into=COVER_T, with_screws=True,
                               screw_rot_deg=45):
    """Cut horn-disc receptacle features on wp's current face.

    Centered at wp origin. Carves: disc clearance pocket, spline boss
    pass-through, 4x M3 horn screw clearance holes. Use for the yoke
    arm that anchors the servo's TOP (driven) spline + horn.
    """
    wp = wp.cut(
        cq.Workplane(wp.plane)
        .circle((HORN_DISC_OD + 2*HORN_DISC_CLEAR)/2)
        .extrude(-(HORN_DISC_THK + 0.5))
    )
    wp = wp.cut(
        cq.Workplane(wp.plane)
        .circle((HORN_BOSS_OD + 2*SHAFT_CLEAR)/2)
        .extrude(-(depth_into + 2.0))
    )
    if with_screws:
        pts = []
        r = HORN_SCREW_BCD / 2
        for i in range(4):
            a = math.radians(screw_rot_deg + i * 90)
            pts.append((r * math.cos(a), r * math.sin(a)))
        wp = wp.pushPoints(pts).hole(HORN_SCREW_OD, depth=depth_into + 2.0)
    return wp


def bearing_seat_cuts(wp, depth=BEAR_688_W + 0.2):
    """Cut a 688ZZ bearing OD press-fit pocket centered at wp origin."""
    pocket = wp.cut(
        cq.Workplane(wp.plane)
        .circle((BEAR_688_OD + 2*BEARING_PRESS)/2)
        .extrude(-depth)
    )
    # Through-hole inside the bearing bore = bottom shaft + sleeve OD
    bore = BEAR_688_ID + 0.3  # 0.3 mm clearance for the 6->8 mm sleeve adapter
    pocket = pocket.cut(
        cq.Workplane(wp.plane)
        .circle(bore / 2)
        .extrude(-(depth + 5.0))
    )
    return pocket


def heatset_boss_cuts(wp, x, y, length, bore=RUTHEX_M3_BORE,
                      boss_od=RUTHEX_M3_BOSS_OD, pocket_depth=RUTHEX_M3_DEPTH):
    """Add a heat-set insert boss extruded `length` from wp; carve pocket."""
    wp = wp.union(
        cq.Workplane(wp.plane)
        .center(x, y)
        .circle(boss_od / 2)
        .extrude(length)
    )
    wp = wp.cut(
        cq.Workplane(wp.plane)
        .workplane(offset=length - pocket_depth)
        .center(x, y)
        .circle(bore / 2)
        .extrude(pocket_depth + 0.1)
    )
    return wp


def wire_slot_cut(wp, x, y, w=WIRE_SLOT_W, h=WIRE_SLOT_H, thru=20.0):
    """Cut a wire exit slot at (x,y), w along wp X, h along wp Z."""
    return wp.cut(
        cq.Workplane(wp.plane)
        .center(x, y)
        .box(w, thru, h, centered=(True, True, True))
    )
