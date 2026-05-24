"""
NovaSM3 Femur V3.1 — surrounds servo 2, drives servo 3 yoke.
SINGLE solid construction (no hanging parts) + TTL daisy-chain pass-through.

ROLE:
  Body-shell for servo 2 (thigh/quad) at proximal end. Long beam through
  the leg long axis. Distal U-yoke for servo 3 (knee), arms straddling
  the tibia. All ONE connected solid; no floating geometry.

WIRE ROUTING:
  Feetech TTL daisy-chain enters the femur from the proximal end (coax
  side) via a wire slot, runs along the inside of the cavity / mid-link
  channel to servo 2's connectors, exits servo 2 via the second daisy
  connector, continues along the link to the distal end, and exits to
  the next servo (knee/tibia) via a slot on the distal end of the body
  cavity. Yoke arms have notches at their inner edges so the cable can
  pass to the tibia.
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

FEMUR_LENGTH = 140.0

# Proximal body shell (servo 2)
BODY_X = SERVO_L + 2*WALL_T + 2.0
BODY_Y = SERVO_H + 2*SERVO_CLEAR + 2*WALL_T
BODY_Z = SERVO_W + 2*SERVO_CLEAR + WALL_T
BODY_CX = -FEMUR_LENGTH/2 + BODY_X/2 + 4.0

# Mid-link beam
BEAM_Y = BODY_Y * 0.55
BEAM_Z = BODY_Z * 0.75

# Distal yoke for servo 3
S3_GAP_Y = SERVO_H + 2*SERVO_CLEAR
S3_ARM_T = YOKE_ARM_T
S3_ARM_X = SERVO_L + 2*WALL_T + 4.0
S3_ARM_Z = HORN_DISC_OD + 4*WALL_T
S3_AXIS_X = FEMUR_LENGTH/2 - S3_ARM_X/2 - 4.0
S3_AXIS_Z = BODY_Z/2     # yoke axis at body shell mid-height

# Yoke region: BODY_X..FEMUR_END along X, full S3_GAP_Y + 2*ARM_T along Y
YOKE_Y_FULL = S3_GAP_Y + 2*S3_ARM_T

# Lid bosses on proximal body shell
INSET = RUTHEX_M3_BOSS_OD/2 + 0.5
LID_SCREW_POS = [
    (BODY_CX - BODY_X/2 + INSET, -(BODY_Y/2 - INSET)),
    (BODY_CX + BODY_X/2 - INSET, -(BODY_Y/2 - INSET)),
    (BODY_CX - BODY_X/2 + INSET,  (BODY_Y/2 - INSET)),
    (BODY_CX + BODY_X/2 - INSET,  (BODY_Y/2 - INSET)),
]


def build_femur():
    # ===========================================================
    # Outer envelope as ONE solid (3 sections unioned)
    # ===========================================================

    # 1. Proximal body shell: BODY_X × BODY_Y × BODY_Z
    femur = (
        cq.Workplane("XY")
        .center(BODY_CX, 0)
        .box(BODY_X, BODY_Y, BODY_Z, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
    )

    # 2. Mid-link beam: from body shell +X face to yoke -X face
    beam_x0 = BODY_CX + BODY_X/2 - 1.0   # overlap into body
    beam_x1 = S3_AXIS_X - S3_ARM_X/2 + 1.0
    beam_len = beam_x1 - beam_x0
    if beam_len > 0:
        beam = (
            cq.Workplane("XY")
            .center((beam_x0 + beam_x1)/2, 0)
            .box(beam_len, BEAM_Y, BEAM_Z, centered=(True, True, False))
            .edges("|X").fillet(CORNER_R)
        )
        femur = femur.union(beam)

    # 3. Distal yoke region: BODY_X × YOKE_Y_FULL × S3_ARM_Z
    yoke = (
        cq.Workplane("XY")
        .center(S3_AXIS_X, 0)
        .box(S3_ARM_X, YOKE_Y_FULL, S3_ARM_Z, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
    )
    femur = femur.union(yoke)

    # Lid bosses on proximal body
    for (x, y) in LID_SCREW_POS:
        femur = femur.union(
            cq.Workplane("XY")
            .center(x, y)
            .circle(RUTHEX_M3_BOSS_OD/2)
            .extrude(BODY_Z)
        )

    # ===========================================================
    # Carve cavities
    # ===========================================================
    c = SERVO_CLEAR

    # ---- Servo 2 body cavity (drop-in from +Z) ----
    femur = femur.cut(
        cq.Workplane("XY")
        .workplane(offset=WALL_T)
        .center(BODY_CX, 0)
        .box(SERVO_L + 2*c, SERVO_H + 2*c, SERVO_W + 2*c + WALL_T,
             centered=(True, True, False))
    )

    # ---- Servo 2 spline through-hole on +Y face ----
    spline_x_world = BODY_CX + SPLINE_X_OFFSET
    spline_z_world = BODY_Z/2
    femur = femur.cut(
        cq.Workplane("XZ")
        .workplane(offset=BODY_Y/2 - 0.1)
        .center(spline_x_world, spline_z_world)
        .circle((HORN_DISC_OD + 1.0)/2)
        .extrude(WALL_T + 0.5)
    )

    # ---- Servo 2 bottom shaft through-hole on -Y face ----
    femur = femur.cut(
        cq.Workplane("XZ")
        .workplane(offset=-BODY_Y/2 + 0.1)
        .center(spline_x_world, spline_z_world)
        .circle((BOT_DISC_OD + 1.0)/2)
        .extrude(-(WALL_T + 0.5))
    )

    # ---- Heatset pockets ----
    for (x, y) in LID_SCREW_POS:
        femur = femur.cut(
            cq.Workplane("XY")
            .workplane(offset=BODY_Z - RUTHEX_M3_DEPTH)
            .center(x, y)
            .circle(RUTHEX_M3_BORE/2)
            .extrude(RUTHEX_M3_DEPTH + 0.1)
        )

    # ---- TTL daisy-chain pass-throughs ----
    # Slot 1: -X face of body shell (cable IN from coax/upstream)
    femur = femur.cut(
        cq.Workplane("XY")
        .workplane(offset=BODY_Z - WIRE_SLOT_H - 2.0)
        .center(BODY_CX - BODY_X/2 + WALL_T/2, 0)
        .box(WALL_T + 1.0, WIRE_SLOT_W, WIRE_SLOT_H,
             centered=(True, True, False))
    )
    # Slot 2: +X face of body shell (cable OUT toward knee/tibia)
    femur = femur.cut(
        cq.Workplane("XY")
        .workplane(offset=BODY_Z - WIRE_SLOT_H - 2.0)
        .center(BODY_CX + BODY_X/2 - WALL_T/2, 0)
        .box(WALL_T + 1.0, WIRE_SLOT_W, WIRE_SLOT_H,
             centered=(True, True, False))
    )
    # Mid-link cable channel along beam (carved from beam top so cover later)
    if beam_len > 0:
        femur = femur.cut(
            cq.Workplane("XY")
            .workplane(offset=BEAM_Z - WIRE_SLOT_H - 1.0)
            .center((beam_x0 + beam_x1)/2, 0)
            .box(beam_len + 0.5, WIRE_SLOT_W, WIRE_SLOT_H + 0.5,
                 centered=(True, True, False))
        )
    # Notch in yoke arms (inner faces) so cable can exit toward tibia
    for sign in (-1, 1):
        notch_y = sign * (S3_GAP_Y/2)
        femur = femur.cut(
            cq.Workplane("XY")
            .workplane(offset=S3_ARM_Z - WIRE_SLOT_H - 1.0)
            .center(S3_AXIS_X - S3_ARM_X/2 + WALL_T/2, notch_y - sign*S3_ARM_T/2)
            .box(WALL_T + 1.0, WIRE_SLOT_W, WIRE_SLOT_H,
                 centered=(True, True, False))
        )

    # ---- Open gap between yoke arms (tibia body sits here) ----
    femur = femur.cut(
        cq.Workplane("XY")
        .workplane(offset=-0.1)
        .center(S3_AXIS_X, 0)
        .box(S3_ARM_X + 1.0, S3_GAP_Y, S3_ARM_Z + 0.5,
             centered=(True, True, False))
    )

    # ---- Servo 3 horn receptacle (+Y arm) ----
    py_inner = S3_GAP_Y/2
    py_outer = S3_GAP_Y/2 + S3_ARM_T
    femur = femur.cut(
        cq.Workplane("XZ")
        .workplane(offset=py_inner - 0.1)
        .center(S3_AXIS_X, S3_AXIS_Z)
        .circle((HORN_DISC_OD + 0.6)/2)
        .extrude(HORN_DISC_THK + 0.5)
    )
    femur = femur.cut(
        cq.Workplane("XZ")
        .workplane(offset=py_inner - 0.1)
        .center(S3_AXIS_X, S3_AXIS_Z)
        .circle((HORN_BOSS_OD + 2*SHAFT_CLEAR)/2)
        .extrude(S3_ARM_T + 0.5)
    )
    for i in range(4):
        a = math.radians(45 + i*90)
        sx = math.cos(a) * (HORN_SCREW_BCD/2) + S3_AXIS_X
        sz = math.sin(a) * (HORN_SCREW_BCD/2) + S3_AXIS_Z
        femur = femur.cut(
            cq.Workplane("XZ")
            .workplane(offset=py_outer + 0.1)
            .center(sx, sz)
            .circle(HORN_SCREW_OD/2)
            .extrude(-(S3_ARM_T + 0.5))
        )

    # ---- Servo 3 bearing seat (-Y arm) ----
    ny_inner = -S3_GAP_Y/2
    femur = femur.cut(
        cq.Workplane("XZ")
        .workplane(offset=ny_inner + 0.1)
        .center(S3_AXIS_X, S3_AXIS_Z)
        .circle((BEAR_688_OD + 2*BEARING_PRESS)/2)
        .extrude(-(BEAR_688_W + 0.2))
    )
    femur = femur.cut(
        cq.Workplane("XZ")
        .workplane(offset=ny_inner + 0.1)
        .center(S3_AXIS_X, S3_AXIS_Z)
        .circle((BEAR_688_ID + 0.3)/2)
        .extrude(-(S3_ARM_T + 0.5))
    )

    return femur


def build_cover():
    cover_l = FEMUR_LENGTH - 8.0
    cover_w = BODY_Y - 4.0
    cover = (
        cq.Workplane("XY")
        .center(0, 0)
        .box(cover_l, cover_w, COVER_T, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
    )
    # 4 bolt holes over body lid bosses
    for (x, y) in LID_SCREW_POS:
        cover = (cover.faces(">Z").workplane()
                 .center(x, y)
                 .hole(LID_SCREW_OD))
    return cover


if __name__ == "__main__":
    f = build_femur()
    c = build_cover()
    cq.exporters.export(f, "femur_v31_shell.stl",
                        tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(c, "femur_v31_cover.stl",
                        tolerance=0.01, angularTolerance=0.1)
    bb = f.val().BoundingBox()
    cb = c.val().BoundingBox()
    print(f"femur shell bbox: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")
    print(f"femur cover bbox: {cb.xlen:.1f} x {cb.ylen:.1f} x {cb.zlen:.1f} mm")
    print(f"femur shell volume: {f.val().Volume():.0f} mm^3")
