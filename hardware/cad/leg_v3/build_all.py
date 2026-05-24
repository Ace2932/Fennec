"""
Build all V3.1 leg pieces (shoulder + coax + femur + tibia) + render
a posed assembly preview + print comparison vs original NovaSM3 STLs.

V3.1 architecture (corrected after user feedback 2026-05-24):
  Body-driven dual-shaft yoke mount on every servo.
  Servo 1 (hip abduction, 30 kg STS3215): shoulder yoke → coax body
  Servo 2 (thigh / quad flexion, 19 kg):  coax yoke → femur body
  Servo 3 (knee, 19 kg):                  femur yoke → tibia body
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cadquery as cq
import struct

from shoulder import build_shoulder
from coax     import build_body_shell as build_coax,  build_cover as build_coax_cover
from femur    import build_femur,                    build_cover as build_femur_cover
from tibia    import build_tibia,                    build_cover as build_tibia_cover


ORIGINAL_DIR = "/Users/afox/codebases/NOVA/original_body_files"


def stl_bbox(path):
    with open(path, "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        mins = [1e9] * 3
        maxs = [-1e9] * 3
        for _ in range(n):
            f.read(12)
            for _ in range(3):
                v = struct.unpack("<fff", f.read(12))
                for i in range(3):
                    mins[i] = min(mins[i], v[i])
                    maxs[i] = max(maxs[i], v[i])
            f.read(2)
    return (maxs[0] - mins[0], maxs[1] - mins[1], maxs[2] - mins[2])


def main():
    print("Building V3.1 pieces...")
    shoulder = build_shoulder()
    coax_shell = build_coax()
    coax_cover = build_coax_cover()
    femur = build_femur()
    femur_cover = build_femur_cover()
    tibia = build_tibia()
    tibia_cover = build_tibia_cover()

    # Export individual STLs
    parts = [
        ("shoulder_v31.stl",        shoulder),
        ("coax_v31_shell.stl",      coax_shell),
        ("coax_v31_cover.stl",      coax_cover),
        ("femur_v31_shell.stl",     femur),
        ("femur_v31_cover.stl",     femur_cover),
        ("tibia_v31_shell.stl",     tibia),
        ("tibia_v31_cover.stl",     tibia_cover),
    ]
    for name, obj in parts:
        cq.exporters.export(obj, name,
                            tolerance=0.01, angularTolerance=0.1)

    # ---- Posed assembly (preview only, not printable as one piece) ----
    # Mate each link by sharing the servo axis with the upstream piece.
    # Straight-leg pose: leg hangs in -Z direction.
    # Shoulder is fixed at origin; its servo 1 spline axis runs along world Z
    # at world (12.5, -15, 0).
    from leg_common import SPLINE_X_OFFSET, SERVO_H, SERVO_CLEAR
    from shoulder import SPLINE_X_SHOULDER, YOKE_ARM_Y, YOKE_GAP_Z
    from coax     import BODY_Z as COAX_BODY_Z, S2_AXIS_Z, S2_GAP_Y
    from femur    import (BODY_CX as FEMUR_BCX, BODY_Z as FEMUR_BODY_Z,
                          S3_AXIS_X, S3_AXIS_Z)
    from tibia    import BODY_CX as TIBIA_BCX, BODY_Z as TIBIA_BODY_Z

    # 1) Shoulder: at origin. Servo 1 axis at world (12.5, -15, 0) along Z.
    #    Inner face of shoulder top arm (= top of coax body) at Z = +YOKE_GAP_Z/2.
    coax_world_X = 0
    coax_world_Y = -YOKE_ARM_Y / 2     # = -15
    coax_world_Z = YOKE_GAP_Z/2 - COAX_BODY_Z   # body top sits at top-arm inner

    coax_assy = (coax_shell.union(coax_cover)
                 .translate((coax_world_X, coax_world_Y, coax_world_Z)))

    # 2) Coax servo-2 axis in world:
    s2_axis_world = (
        coax_world_X + SPLINE_X_OFFSET,
        coax_world_Y,
        coax_world_Z + S2_AXIS_Z,
    )

    # Femur: rotate +90 about Y so femur local +X -> world -Z (femur hangs down).
    # After rotation, femur servo-2 spline world coords (before translate):
    #   wx = local_Z = FEMUR_BODY_Z/2
    #   wy = local_Y = 0
    #   wz = -local_X = -(FEMUR_BCX + SPLINE_X_OFFSET)
    femur_rot = (femur.union(femur_cover)
                 .rotate((0,0,0), (0,1,0), 90))
    femur_spline_after_rot = (
        FEMUR_BODY_Z / 2,
        0,
        -(FEMUR_BCX + SPLINE_X_OFFSET),
    )
    femur_T = (
        s2_axis_world[0] - femur_spline_after_rot[0],
        s2_axis_world[1] - femur_spline_after_rot[1],
        s2_axis_world[2] - femur_spline_after_rot[2],
    )
    femur_assy = femur_rot.translate(femur_T)

    # 3) Femur servo-3 (knee) axis in world. Femur local: (S3_AXIS_X, 0, S3_AXIS_Z+BODY_Z/2)
    knee_local = (S3_AXIS_X, 0, S3_AXIS_Z + FEMUR_BODY_Z / 2)
    knee_after_rot = (knee_local[2], knee_local[1], -knee_local[0])
    knee_world = (
        knee_after_rot[0] + femur_T[0],
        knee_after_rot[1] + femur_T[1],
        knee_after_rot[2] + femur_T[2],
    )

    # Tibia: same rotation as femur. Translate so its servo-3 spline lands at knee_world.
    tibia_rot = (tibia.union(tibia_cover)
                 .rotate((0,0,0), (0,1,0), 90))
    tibia_spline_after_rot = (
        TIBIA_BODY_Z / 2,
        0,
        -(TIBIA_BCX + SPLINE_X_OFFSET),
    )
    tibia_T = (
        knee_world[0] - tibia_spline_after_rot[0],
        knee_world[1] - tibia_spline_after_rot[1],
        knee_world[2] - tibia_spline_after_rot[2],
    )
    tibia_assy = tibia_rot.translate(tibia_T)

    assy = shoulder.union(coax_assy).union(femur_assy).union(tibia_assy)
    cq.exporters.export(assy, "leg_v31_assembly.stl",
                        tolerance=0.05, angularTolerance=0.5)

    # ---- Comparison table vs original NovaSM3 STLs ----
    print("\n" + "=" * 78)
    print("LEG V3.1 vs ORIGINAL NovaSM3 — BBox compare (mm)")
    print("=" * 78)
    pairs = [
        ("shoulder", ["SM3_Frame_FrontShoulderInner.stl",
                      "SM3_Frame_FrontShoulderMiddle.stl",
                      "SM3_Frame_FrontShoulderOuter.stl"],
                     "shoulder_v31.stl"),
        ("coax",     ["SM3_Frame_LeftCoax.stl"],          "coax_v31_shell.stl"),
        ("femur",    ["SM3_Frame_LeftFemur.stl"],         "femur_v31_shell.stl"),
        ("tibia",    ["SM3_Frame_LeftTibia.stl"],         "tibia_v31_shell.stl"),
    ]
    print(f"{'Part':10s} | {'Original':30s} | {'V3.1':25s}")
    print("-" * 78)
    for name, origs, v3 in pairs:
        for o in origs:
            ox, oy, oz = stl_bbox(os.path.join(ORIGINAL_DIR, o))
            tag = o.replace("SM3_Frame_", "")
            print(f"{name:10s} | {tag:24s} {ox:5.0f}x{oy:3.0f}x{oz:3.0f} | ", end="")
            if o == origs[0]:
                vx, vy, vz = stl_bbox(v3)
                print(f"{v3:14s} {vx:5.0f}x{vy:3.0f}x{vz:3.0f}")
            else:
                print()
    print("=" * 78)

    abox = assy.val().BoundingBox()
    print(f"\nPosed assembly bbox: {abox.xlen:.1f} x {abox.ylen:.1f} x {abox.zlen:.1f} mm")
    print(f"Total volume: {assy.val().Volume():.0f} mm^3")
    print("\nleg_v31_assembly.stl is a layout preview, NOT a single printable piece.")


if __name__ == "__main__":
    main()
