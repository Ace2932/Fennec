"""
NovaSM3 Coax V3.1 — surrounds servo 1, drives servo 2 yoke.
SINGLE solid construction (no hanging parts).

ROLE:
  Body-shell for servo 1 (hip abduction) on top, perpendicular yoke for
  servo 2 (thigh flexion) below, all one connected solid.
  Shoulder yoke (static, chassis-side) grips servo 1's top spline + bottom
  reaction shaft. Coax rotates around servo 1's shaft axis (= robot X).
  Femur body fits between coax's yoke arms, surrounding servo 2 body.

CONSTRUCTION:
  Build as one big solid spanning the full Z extent (body shell + neck +
  yoke), then carve all cavities. Yoke arms widen the Y span at the bottom.
  No floating disconnected geometry.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cadquery as cq
import math
from leg_common import (
    SERVO_L, SERVO_W, SERVO_H, SPLINE_X_OFFSET,
    HORN_DISC_OD, HORN_DISC_THK, BOT_DISC_OD, BOT_DISC_THK,
    HORN_SCREW_BCD, HORN_SCREW_OD, HORN_BOSS_OD,
    SERVO_CLEAR, WALL_T, COVER_T, CORNER_R, YOKE_ARM_T,
    RUTHEX_M3_BORE, RUTHEX_M3_DEPTH, RUTHEX_M3_BOSS_OD, LID_SCREW_OD,
    BEAR_688_OD, BEAR_688_W, BEARING_PRESS, BEAR_688_ID,
    WIRE_SLOT_W, WIRE_SLOT_H, SHAFT_CLEAR,
)

# ============================================================
# PARAMETERS
# ============================================================

# Upper body shell (servo 1)
BODY_X = SERVO_L + 2*WALL_T + 2.0
BODY_Y = SERVO_W + 2*WALL_T + 2.0
BODY_Z = SERVO_H + 2*SERVO_CLEAR + WALL_T

# Lower yoke for servo 2
S2_GAP_Y = SERVO_H + 2*SERVO_CLEAR
S2_ARM_T = YOKE_ARM_T
S2_ARM_Z = HORN_DISC_OD + 4*WALL_T

# Servo 2 axis: 6 mm below body shell floor
S2_AXIS_Z = -6.0

# Overall solid spans Z=YOKE_BOT to Z=BODY_Z, X=BODY_X, Y=YOKE_Y (wider than body)
YOKE_BOT = S2_AXIS_Z - S2_ARM_Z/2
YOKE_Y   = S2_GAP_Y + 2*S2_ARM_T

# Lid bosses on body shell top
INSET = RUTHEX_M3_BOSS_OD/2 + 0.5
LID_SCREW_POS = [
    (-(BODY_X/2 - INSET), -(BODY_Y/2 - INSET)),
    ( (BODY_X/2 - INSET), -(BODY_Y/2 - INSET)),
    (-(BODY_X/2 - INSET),  (BODY_Y/2 - INSET)),
    ( (BODY_X/2 - INSET),  (BODY_Y/2 - INSET)),
]


def build_body_shell():
    """Build coax as a single connected solid: body shell on top, neck in
    middle (spans body Y but extends down through yoke Z region), yoke arms
    at bottom (wider Y). Carve all cavities after."""

    # ---- Outer profile ----
    # Top: BODY_X × BODY_Y from Z=0 to Z=BODY_Z
    # Middle: BODY_X × BODY_Y from Z=YOKE_BOT to Z=0 (the neck)
    # Bottom: BODY_X × YOKE_Y from Z=YOKE_BOT to Z=YOKE_BOT+S2_ARM_Z
    #   (this widens Y to give the yoke arms)

    # Build upper body + neck as one big box
    upper = (
        cq.Workplane("XY")
        .workplane(offset=YOKE_BOT)
        .box(BODY_X, BODY_Y, BODY_Z - YOKE_BOT, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
    )

    # Lower yoke region: BODY_X × YOKE_Y from YOKE_BOT to YOKE_BOT+S2_ARM_Z
    yoke = (
        cq.Workplane("XY")
        .workplane(offset=YOKE_BOT)
        .box(BODY_X, YOKE_Y, S2_ARM_Z, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
    )

    shell = upper.union(yoke)

    # Lid bosses on top (heatset inserts)
    for (x, y) in LID_SCREW_POS:
        shell = shell.union(
            cq.Workplane("XY")
            .center(x, y)
            .circle(RUTHEX_M3_BOSS_OD/2)
            .extrude(BODY_Z)
        )

    # ===========================================================
    # Carve all cavities
    # ===========================================================

    # ---- Servo 1 body cavity (drop-in from +Z) ----
    c = SERVO_CLEAR
    shell = shell.cut(
        cq.Workplane("XY")
        .workplane(offset=WALL_T)
        .box(SERVO_L + 2*c, SERVO_W + 2*c, SERVO_H + 2*c + WALL_T,
             centered=(True, True, False))
    )

    # ---- Top opening for spline + horn (servo 1) ----
    shell = shell.cut(
        cq.Workplane("XY")
        .workplane(offset=BODY_Z - 0.1)
        .center(SPLINE_X_OFFSET, 0)
        .circle((HORN_DISC_OD + 1.0)/2)
        .extrude(WALL_T + 1.0)
    )

    # ---- Bottom opening for reaction shaft (servo 1) ----
    # Through the neck region down into the yoke void
    shell = shell.cut(
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .center(SPLINE_X_OFFSET, 0)
        .circle((BOT_DISC_OD + 1.0)/2)
        .extrude(-(abs(YOKE_BOT) + 0.5))
    )

    # ---- Heatset pockets on top ----
    for (x, y) in LID_SCREW_POS:
        shell = shell.cut(
            cq.Workplane("XY")
            .workplane(offset=BODY_Z - RUTHEX_M3_DEPTH)
            .center(x, y)
            .circle(RUTHEX_M3_BORE/2)
            .extrude(RUTHEX_M3_DEPTH + 0.1)
        )

    # ---- Wire slot on -X face ----
    shell = shell.cut(
        cq.Workplane("XY")
        .workplane(offset=BODY_Z - WIRE_SLOT_H - 2.0)
        .center(-BODY_X/2 + WALL_T/2, 0)
        .box(WALL_T + 1.0, WIRE_SLOT_W, WIRE_SLOT_H,
             centered=(True, True, False))
    )

    # ---- Carve the gap between yoke arms (where femur body sits) ----
    # CRITICAL: Z extent is YOKE_BOT to 0 ONLY (do NOT cut into body shell
    # above, would sever upper body from yoke). Width along Y is S2_GAP_Y;
    # body shell BODY_Y must be > S2_GAP_Y so the upper region survives.
    yoke_carve_z_top = -1.0  # stay 1 mm below body shell floor
    yoke_carve_z_bot = YOKE_BOT - 0.5
    shell = shell.cut(
        cq.Workplane("XY")
        .workplane(offset=yoke_carve_z_bot)
        .box(BODY_X + 1.0, S2_GAP_Y, yoke_carve_z_top - yoke_carve_z_bot,
             centered=(True, True, False))
    )

    # ---- Servo 2 horn receptacle on +Y arm inner face ----
    # In coax local coords:
    #   spline X = SPLINE_X_OFFSET
    #   spline Z = S2_AXIS_Z
    #   +Y inner face Y = +S2_GAP_Y/2
    py_inner = S2_GAP_Y/2
    py_outer = S2_GAP_Y/2 + S2_ARM_T
    shell = shell.cut(
        cq.Workplane("XZ")
        .workplane(offset=py_inner - 0.1)
        .center(SPLINE_X_OFFSET, S2_AXIS_Z)
        .circle((HORN_DISC_OD + 0.6)/2)
        .extrude(HORN_DISC_THK + 0.5)
    )
    shell = shell.cut(
        cq.Workplane("XZ")
        .workplane(offset=py_inner - 0.1)
        .center(SPLINE_X_OFFSET, S2_AXIS_Z)
        .circle((HORN_BOSS_OD + 2*SHAFT_CLEAR)/2)
        .extrude(S2_ARM_T + 0.5)
    )
    for i in range(4):
        a = math.radians(45 + i*90)
        sx = math.cos(a) * (HORN_SCREW_BCD/2) + SPLINE_X_OFFSET
        sz = math.sin(a) * (HORN_SCREW_BCD/2) + S2_AXIS_Z
        shell = shell.cut(
            cq.Workplane("XZ")
            .workplane(offset=py_outer + 0.1)
            .center(sx, sz)
            .circle(HORN_SCREW_OD/2)
            .extrude(-(S2_ARM_T + 0.5))
        )

    # ---- Servo 2 bearing seat on -Y arm inner face ----
    ny_inner = -S2_GAP_Y/2
    ny_outer = -S2_GAP_Y/2 - S2_ARM_T
    shell = shell.cut(
        cq.Workplane("XZ")
        .workplane(offset=ny_inner + 0.1)
        .center(SPLINE_X_OFFSET, S2_AXIS_Z)
        .circle((BEAR_688_OD + 2*BEARING_PRESS)/2)
        .extrude(-(BEAR_688_W + 0.2))
    )
    shell = shell.cut(
        cq.Workplane("XZ")
        .workplane(offset=ny_inner + 0.1)
        .center(SPLINE_X_OFFSET, S2_AXIS_Z)
        .circle((BEAR_688_ID + 0.3)/2)
        .extrude(-(S2_ARM_T + 0.5))
    )

    return shell


def build_cover():
    cover = (
        cq.Workplane("XY")
        .box(BODY_X, BODY_Y, COVER_T, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
    )
    for (x, y) in LID_SCREW_POS:
        cover = (cover.faces(">Z").workplane()
                 .center(x, y)
                 .hole(LID_SCREW_OD))
    cover = (cover.faces(">Z").workplane()
             .center(SPLINE_X_OFFSET, 0)
             .hole(HORN_DISC_OD + 1.0))
    return cover


if __name__ == "__main__":
    shell = build_body_shell()
    cover = build_cover()
    cq.exporters.export(shell, "coax_v31_shell.stl",
                        tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(cover, "coax_v31_cover.stl",
                        tolerance=0.01, angularTolerance=0.1)
    sb = shell.val().BoundingBox()
    cb = cover.val().BoundingBox()
    print(f"coax shell bbox: {sb.xlen:.1f} x {sb.ylen:.1f} x {sb.zlen:.1f} mm")
    print(f"coax cover bbox: {cb.xlen:.1f} x {cb.ylen:.1f} x {cb.zlen:.1f} mm")
    print(f"coax shell volume: {shell.val().Volume():.0f} mm^3")
