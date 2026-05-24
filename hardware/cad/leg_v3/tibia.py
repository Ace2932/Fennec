"""
NovaSM3 Tibia V3.1 — surrounds servo 3, foot at distal tip.

ROLE:
  Body-shell for servo 3 (knee) at the proximal end. Long structural
  link extending to the distal end where the TPU foot pad bolts on.
  Servo 3 horn + bottom shaft both straddled by the femur's distal
  yoke (this part is the downstream body, femur is the upstream yoke).

COORDINATE CONVENTION (tibia local frame):
  X = along tibia long axis (proximal -X at knee, distal +X at foot)
  Y = lateral (parallel to servo 3 spline)
  Z = perpendicular to tibia

PRINT:
  Body shell flat, foot end with insert pocket on top. Fiber along X
  (impact load axis at ground touchdown).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cadquery as cq
from leg_common import (
    SERVO_L, SERVO_W, SERVO_H, SPLINE_X_OFFSET,
    HORN_DISC_OD, HORN_DISC_THK, BOT_DISC_OD, BOT_DISC_THK,
    SERVO_CLEAR, WALL_T, COVER_T, CORNER_R,
    RUTHEX_M3_BORE, RUTHEX_M3_DEPTH, RUTHEX_M3_BOSS_OD, LID_SCREW_OD,
    WIRE_SLOT_W, WIRE_SLOT_H, SHAFT_CLEAR,
)

# ============================================================
# PARAMETERS
# ============================================================

TIBIA_LENGTH    = 130.0

# Proximal body shell (houses servo 3)
BODY_X = SERVO_L + 2*WALL_T + 2.0       # ~52.4
BODY_Y = SERVO_H + 2*SERVO_CLEAR + 2*WALL_T  # ~44.8
BODY_Z = SERVO_W + 2*SERVO_CLEAR + WALL_T    # ~31.8

BODY_CX = -TIBIA_LENGTH/2 + BODY_X/2 + 4.0

# Shin section (between body and foot)
SHIN_W = 22.0          # narrow at the shin
SHIN_Z = BODY_Z - 4.0  # slightly thinner

# Foot mount section
FOOT_MOUNT_OFFSET = 6.0
FOOT_PAD_OD       = 35.0   # matches nova_sm3_patterns.md FOOT_PAD spec

INSET = RUTHEX_M3_BOSS_OD/2 + 0.5
LID_SCREW_POS = [
    (BODY_CX - BODY_X/2 + INSET, -(BODY_Y/2 - INSET)),
    (BODY_CX + BODY_X/2 - INSET, -(BODY_Y/2 - INSET)),
    (BODY_CX - BODY_X/2 + INSET,  (BODY_Y/2 - INSET)),
    (BODY_CX + BODY_X/2 - INSET,  (BODY_Y/2 - INSET)),
]


def build_tibia():
    # Proximal body shell
    tibia = (
        cq.Workplane("XY")
        .center(BODY_CX, 0)
        .box(BODY_X, BODY_Y, BODY_Z, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
    )

    # Lid bosses
    for (x, y) in LID_SCREW_POS:
        tibia = tibia.union(
            cq.Workplane("XY")
            .center(x, y)
            .circle(RUTHEX_M3_BOSS_OD/2)
            .extrude(BODY_Z)
        )

    # Carve servo 3 body cavity (drop in from +Z)
    c = SERVO_CLEAR
    tibia = tibia.cut(
        cq.Workplane("XY")
        .workplane(offset=WALL_T)
        .center(BODY_CX, 0)
        .box(SERVO_L + 2*c, SERVO_H + 2*c, SERVO_W + 2*c + WALL_T,
             centered=(True, True, False))
    )

    # Spline through-hole +Y face
    spline_x_world = BODY_CX + SPLINE_X_OFFSET
    spline_z_world = BODY_Z/2
    tibia = tibia.cut(
        cq.Workplane("XZ")
        .workplane(offset=BODY_Y/2 - 0.1)
        .center(spline_x_world, spline_z_world)
        .circle((HORN_DISC_OD + 1.0)/2)
        .extrude(WALL_T + 0.5)
    )
    # Bottom shaft through-hole -Y face
    tibia = tibia.cut(
        cq.Workplane("XZ")
        .workplane(offset=-BODY_Y/2 + 0.1)
        .center(spline_x_world, spline_z_world)
        .circle((BOT_DISC_OD + 1.0)/2)
        .extrude(-(WALL_T + 0.5))
    )

    # Heatset pockets
    for (x, y) in LID_SCREW_POS:
        tibia = tibia.cut(
            cq.Workplane("XY")
            .workplane(offset=BODY_Z - RUTHEX_M3_DEPTH)
            .center(x, y)
            .circle(RUTHEX_M3_BORE/2)
            .extrude(RUTHEX_M3_DEPTH + 0.1)
        )

    # TTL daisy-chain pass-throughs: round 14 mm holes on -X and +X faces
    from leg_common import WIRE_HOLE_DIA
    tibia = tibia.cut(
        cq.Workplane("YZ")
        .workplane(offset=BODY_CX - BODY_X/2 - 0.5)
        .center(0, BODY_Z - WIRE_HOLE_DIA/2 - 3.0)
        .circle(WIRE_HOLE_DIA / 2)
        .extrude(WALL_T + 1.0)
    )
    tibia = tibia.cut(
        cq.Workplane("YZ")
        .workplane(offset=BODY_CX + BODY_X/2 - WALL_T - 0.5)
        .center(0, BODY_Z - WIRE_HOLE_DIA/2 - 3.0)
        .circle(WIRE_HOLE_DIA / 2)
        .extrude(WALL_T + 1.0)
    )

    # --- Shin section: rectangular beam from body to foot ---
    shin_x0 = BODY_CX + BODY_X/2
    shin_x1 = TIBIA_LENGTH/2 - FOOT_PAD_OD/2
    shin_l = shin_x1 - shin_x0
    if shin_l > 0:
        shin = (
            cq.Workplane("XY")
            .center((shin_x0 + shin_x1)/2, 0)
            .box(shin_l, SHIN_W, SHIN_Z, centered=(True, True, False))
            .edges("|X").fillet(CORNER_R)
        )
        tibia = tibia.union(shin)

    # --- Foot mount section at distal tip ---
    foot_x = TIBIA_LENGTH/2 - FOOT_MOUNT_OFFSET
    foot_pad = (
        cq.Workplane("XY")
        .center(foot_x, 0)
        .box(FOOT_PAD_OD + 2.0, SHIN_W + 6.0, SHIN_Z,
             centered=(True, True, False))
        .edges("|Z").fillet(8.0)
    )
    tibia = tibia.union(foot_pad)

    # Heat-set pocket from +Z for M3 (TPU foot pad bolts up into this from -Z)
    tibia = tibia.union(
        cq.Workplane("XY")
        .workplane(offset=SHIN_Z)
        .center(foot_x, 0)
        .circle(RUTHEX_M3_BOSS_OD/2 + 1.0)
        .extrude(2.0)
    )
    tibia = tibia.cut(
        cq.Workplane("XY")
        .workplane(offset=SHIN_Z + 2.0 - RUTHEX_M3_DEPTH)
        .center(foot_x, 0)
        .circle(RUTHEX_M3_BORE/2)
        .extrude(RUTHEX_M3_DEPTH + 0.1)
    )
    # M3 pilot through-hole from -Z up so foot bolt passes through
    tibia = tibia.cut(
        cq.Workplane("XY")
        .center(foot_x, 0)
        .circle(2.0)
        .extrude(SHIN_Z + 2.0 - RUTHEX_M3_DEPTH + 0.1)
    )

    # Locating ring on -Z face for TPU foot pad seat
    tibia = tibia.cut(
        cq.Workplane("XY")
        .workplane(offset=-0.1)
        .center(foot_x, 0)
        .circle(FOOT_PAD_OD/2 - 5.0)
        .extrude(-0.5)
    )

    return tibia


def build_cover():
    cover = (
        cq.Workplane("XY")
        .center(BODY_CX, 0)
        .box(BODY_X, BODY_Y, COVER_T, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
    )
    for (x, y) in LID_SCREW_POS:
        cover = (cover.faces(">Z").workplane()
                 .center(x, y)
                 .hole(LID_SCREW_OD))
    return cover


if __name__ == "__main__":
    t = build_tibia()
    c = build_cover()
    cq.exporters.export(t, "tibia_v31_shell.stl",
                        tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(c, "tibia_v31_cover.stl",
                        tolerance=0.01, angularTolerance=0.1)
    bb = t.val().BoundingBox()
    print(f"tibia shell bbox: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")
    print(f"tibia volume: {t.val().Volume():.0f} mm^3")
