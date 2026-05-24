"""
NovaSM3 Shoulder V3.1 — chassis-mounted yoke for servo 1 (hip abduction).

ROLE:
  Static piece bolted to the chassis side panel. U-yoke straddles the
  servo 1 body along its shaft (Z) axis. One yoke arm holds the horn
  disc (top, +Z); the other arm carries a 688ZZ bearing for the
  reaction shaft (bottom, -Z). Coax body slides over servo 1 between
  the yoke arms, rotating around the shaft axis = body forward/back (X).

COORDINATE CONVENTION (this part, in its own frame):
  Z up = servo top (spline+horn-disc side, +Z)
  Z down = servo bottom (reaction shaft, -Z)
  X aligned with servo long axis (along the leg-forward direction when
    coax is at zero abduction)
  Y = lateral; chassis mount face is on +Y (toward body)

PRINT:
  Print yoke-arms-up (the chassis-mount slab flat on bed). Fiber axis
  along X (the load-carrying long axis under leg weight).

ASSEMBLY:
  1. Press 688ZZ bearing into the -Z arm's bearing seat (with sleeve
     adapter on STS3215's 6 mm bottom shaft).
  2. Heat-set 4x Ruthex M3 inserts into the chassis-mount slab.
  3. Bolt slab to chassis side panel.
  4. Slide servo 1 into coax body (separate assembly), then insert
     coax+servo between yoke arms; spline up, reaction shaft into
     bearing.
  5. Mount horn disc on spline; bolt 4x M3 horn screws through +Z arm
     into horn disc.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cadquery as cq
from leg_common import (
    SERVO_L, SERVO_W, SERVO_H, SPLINE_X_OFFSET,
    HORN_DISC_OD, HORN_DISC_THK, BOT_DISC_THK,
    HORN_SCREW_BCD, HORN_SCREW_OD,
    SERVO_CLEAR, WALL_T, CORNER_R, YOKE_ARM_T, YOKE_GAP_Z,
    RUTHEX_M3_BORE, RUTHEX_M3_DEPTH, RUTHEX_M3_BOSS_OD,
    BEAR_688_OD, BEAR_688_W, BEARING_PRESS, BEAR_688_ID,
    horn_disc_receptacle_cuts, bearing_seat_cuts,
)
import math

# ============================================================
# PARAMETERS
# ============================================================

# Chassis mount slab geometry (the flat plate bolted to chassis side panel)
SLAB_X          = 60.0    # along leg-forward
SLAB_Y          = 10.0    # thickness into the body
SLAB_Z          = 70.0    # along servo shaft axis (must span servo + arms)

# Yoke arms: two parallel slabs separated by YOKE_GAP_Z, each YOKE_ARM_T thick
YOKE_ARM_W      = SLAB_X      # along X — wide enough for horn disc + margin
YOKE_ARM_Y      = 30.0        # how far the arm projects -Y from the slab
YOKE_ARM_OFFSET = SERVO_L/2 + SERVO_CLEAR + 2.0  # arms project past body in +X

# Spline center in shoulder local coords:
# Servo body centered at (0, -YOKE_ARM_Y/2, 0). Spline at +SPLINE_X_OFFSET.
SPLINE_X_SHOULDER = SPLINE_X_OFFSET    # = 12.5 in this part's X

# Chassis-mount bolt pattern (4x M3 to existing chassis hole pattern;
# placeholder — user to confirm against real chassis CAD)
CHASSIS_BOLT_PATTERN = [
    (-SLAB_X/2 + 8, -SLAB_Z/2 + 8),
    ( SLAB_X/2 - 8, -SLAB_Z/2 + 8),
    (-SLAB_X/2 + 8,  SLAB_Z/2 - 8),
    ( SLAB_X/2 - 8,  SLAB_Z/2 - 8),
]


def build_shoulder():
    # Chassis-mount slab on +Y face (body-facing side)
    slab = (
        cq.Workplane("XZ")
        .workplane(offset=0)  # at Y=0 plane
        .box(SLAB_X, SLAB_Z, SLAB_Y, centered=(True, True, False))
        .edges("|Y").fillet(CORNER_R)
    )

    # +Z arm (horn-anchor side): top arm
    top_arm_z_min = YOKE_GAP_Z/2          # inner face of arm
    top_arm_z_max = YOKE_GAP_Z/2 + YOKE_ARM_T
    top_arm = (
        cq.Workplane("XY")
        .workplane(offset=top_arm_z_min)
        .center(0, -YOKE_ARM_Y/2)
        .box(YOKE_ARM_W, YOKE_ARM_Y, YOKE_ARM_T, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
    )

    # -Z arm (bearing side): bottom arm
    bot_arm_z_max = -YOKE_GAP_Z/2
    bot_arm_z_min = -YOKE_GAP_Z/2 - YOKE_ARM_T
    bot_arm = (
        cq.Workplane("XY")
        .workplane(offset=bot_arm_z_min)
        .center(0, -YOKE_ARM_Y/2)
        .box(YOKE_ARM_W, YOKE_ARM_Y, YOKE_ARM_T, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
    )

    shoulder = slab.union(top_arm).union(bot_arm)

    # ---- Top arm: horn disc receptacle on -Z face of top arm ----
    # Servo spline at (SPLINE_X_SHOULDER, -YOKE_ARM_Y/2, +Z_BODY_FACE)
    # Top arm -Z face is at top_arm_z_min = YOKE_GAP_Z/2.
    top_arm_wp = (
        cq.Workplane("XY")
        .workplane(offset=top_arm_z_max)
        .center(SPLINE_X_SHOULDER, -YOKE_ARM_Y/2)
    )
    shoulder = horn_disc_receptacle_cuts(
        shoulder.faces(">Z[1]").workplane()
                .center(SPLINE_X_SHOULDER, -YOKE_ARM_Y/2)
        if False else
        # Just carve manually; selecting faces in CadQuery with unioned bodies is fragile
        shoulder, depth_into=YOKE_ARM_T,
    )
    # The helper carves into wp's -normal direction; we want into -Z from
    # top arm's +Z face. Do it explicitly:
    spline_cx = SPLINE_X_SHOULDER
    spline_cy = -YOKE_ARM_Y/2

    # Horn disc clearance pocket on inner face of top arm (facing -Z)
    shoulder = shoulder.cut(
        cq.Workplane("XY")
        .workplane(offset=top_arm_z_min - 0.1)
        .center(spline_cx, spline_cy)
        .circle((HORN_DISC_OD + 0.6)/2)
        .extrude(HORN_DISC_THK + 0.5)
    )
    # Spline + horn boss pass-through through top arm
    shoulder = shoulder.cut(
        cq.Workplane("XY")
        .workplane(offset=top_arm_z_min - 0.1)
        .center(spline_cx, spline_cy)
        .circle(4.5)
        .extrude(YOKE_ARM_T + 0.5)
    )
    # 4x M3 horn screws through top arm (from +Z face)
    for i in range(4):
        a = math.radians(45 + i * 90)
        px = math.cos(a) * (HORN_SCREW_BCD/2) + spline_cx
        py = math.sin(a) * (HORN_SCREW_BCD/2) + spline_cy
        shoulder = shoulder.cut(
            cq.Workplane("XY")
            .workplane(offset=top_arm_z_max + 0.1)
            .center(px, py)
            .circle(HORN_SCREW_OD/2)
            .extrude(-(YOKE_ARM_T + 0.5))
        )

    # ---- Bottom arm: bearing seat on +Z face (facing servo body) ----
    shoulder = shoulder.cut(
        cq.Workplane("XY")
        .workplane(offset=bot_arm_z_max + 0.1)
        .center(spline_cx, spline_cy)
        .circle((BEAR_688_OD + 2*BEARING_PRESS)/2)
        .extrude(-(BEAR_688_W + 0.2))
    )
    # Through-hole below bearing for the bottom shaft + sleeve
    shoulder = shoulder.cut(
        cq.Workplane("XY")
        .workplane(offset=bot_arm_z_max + 0.1)
        .center(spline_cx, spline_cy)
        .circle((BEAR_688_ID + 0.3)/2)
        .extrude(-(YOKE_ARM_T + 0.5))
    )

    # ---- TTL daisy-chain pass-through through slab (cable from chassis to coax) ----
    from leg_common import WIRE_SLOT_W as _WS_W, WIRE_SLOT_H as _WS_H
    shoulder = shoulder.cut(
        cq.Workplane("XZ")
        .workplane(offset=-0.1)
        .center(0, 0)
        .box(_WS_W, _WS_H, SLAB_Y + 0.5, centered=(True, True, False))
    )

    # ---- Chassis-mount bolt clearance holes through slab (along Y axis) ----
    # Slab is on +Y side. Bolts go from -Y (chassis) into +Y.
    for (cx, cz) in CHASSIS_BOLT_PATTERN:
        shoulder = shoulder.cut(
            cq.Workplane("XZ")
            .workplane(offset=-0.1)
            .center(cx, cz)
            .circle(3.4 / 2)   # M3 clearance
            .extrude(SLAB_Y + 0.5)
        )

    return shoulder


if __name__ == "__main__":
    s = build_shoulder()
    cq.exporters.export(s, "shoulder_v31.stl",
                        tolerance=0.01, angularTolerance=0.1)
    bb = s.val().BoundingBox()
    print(f"shoulder bbox: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")
    print(f"shoulder volume: {s.val().Volume():.0f} mm^3")
