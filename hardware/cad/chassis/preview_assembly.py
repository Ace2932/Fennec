#!/usr/bin/env python3
"""Build chassis_assembly_preview.stl — everything designed so far in one
mesh for CAD Viewer review: trunk + riser + shoulders + battery pocket +
L2 mast + 4 legs (stance pose, inside chassis-safe ROM) + ENVELOPE boxes
(mezzanine stack, Jetson+heatsink, L2 body, belly pack). Boxes are
envelopes, not parts — the stack box visibly pokes the trunk corner slabs
(the known trim finding). Run after any part change:
  ../../../.venv/bin/python preview_assembly.py
"""
import numpy as np
import trimesh

T = trimesh.transformations.translation_matrix
NOVA = '/Users/afox/codebases/NOVA'
LEG = f'{NOVA}/proj/hardware/cad/leg_v6'
HIP_FA, HIP_LAT, HIP_Z = 141.2, 39.05, 38.05
HFE, KFE = 40, 80          # stance: toe ~(140, -164) under the hip


def rot(deg, axis, point=None):
    return trimesh.transformations.rotation_matrix(
        np.radians(deg), axis, point)


def box(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(
        extents=[x1 - x0, y1 - y0, z1 - z0],
        transform=T([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]))


def leg_mesh():
    servo = trimesh.load(f'{NOVA}/feetech_servo_models/converted_stl/servo.stl')
    servo.apply_translation([-12.5, 0, 0])
    arm = trimesh.load(f'{LEG}/knee_arm.stl')
    arm.apply_transform(T([59, 0, 17.2]))
    # SM3_Foot shoe on the tibia toe: post (129,0,-30.5 jog), keyed at an
    # EXACT 90 deg (derived 2026-07-06 — pad grounds under the post at the
    # 36.2 deg stance lean; dimensions.md SM3_Foot section)
    shoe = trimesh.load(f'{NOVA}/original_body_files/SM3_Foot.stl')
    M_shoe = (T([129, 0, -30.5]) @ rot(90, [0, 0, 1])
              @ rot(-90, [1, 0, 0]) @ T([-13.0, 0, -5.93]))
    shoe.apply_transform(M_shoe)
    coax_pose = rot(-90, [0, 1, 0]) @ rot(90, [1, 0, 0])
    M_f = T([33.8, 11.6, -9.5]) @ rot(180, [0, 0, 1]) @ rot(90, [0, 1, 0])
    S = rot(HFE, [1, 0, 0], [33.8, 11.6, -9.5])
    Tk = T([106.9, 0, 0])
    M_tib = S @ M_f @ Tk @ rot(KFE, [0, 0, 1])
    out = []
    for m, Tm in [(trimesh.load(f'{LEG}/coax_R.stl'), np.eye(4)),
                  (servo, coax_pose),
                  (trimesh.load(f'{LEG}/femur_R.stl'), S @ M_f),
                  (arm, S @ M_f),
                  (trimesh.load(f'{LEG}/tibia_R.stl'), M_tib),
                  (shoe, M_tib)]:
        c = m.copy()
        c.apply_transform(Tm)
        out.append(c)
    return trimesh.util.concatenate(out)


def main():
    parts = [trimesh.load(f'{NOVA}/original_body_files/SM3_Frame_ChassisTrunk.stl'),
             trimesh.load('riser_bay.stl'),
             trimesh.load('battery_pocket.stl'),
             trimesh.load('l2_mast.stl'),
             trimesh.load('d456_head.stl'),
             trimesh.load('floor_plate.stl')]
    sh = trimesh.load(f'{LEG}/shoulder.stl')
    for end in (1, -1):
        S2T = np.array([[0, end, 0, end * HIP_FA],
                        [1, 0, 0, 0], [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])
        s = sh.copy()
        s.apply_transform(S2T)
        parts.append(s)
    leg = leg_mesh()
    MIR = np.eye(4); MIR[1, 1] = -1
    S2T_f = np.array([[0, 1, 0, HIP_FA],
                      [1, 0, 0, 0], [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])
    FR = leg.copy()
    FR.apply_transform(S2T_f @ T([HIP_LAT, 0, 0]) @ MIR)
    RR = FR.copy()
    RR.apply_transform(T([-2 * HIP_FA, 0, 0]))    # translated: knees same way
    MY = np.eye(4); MY[1, 1] = -1
    FL = FR.copy(); FL.apply_transform(MY)
    RL = RR.copy(); RL.apply_transform(MY)
    parts += [FR, RR, FL, RL]
    parts += [box(-59.5, 52.5, -45, 45, 6.0, 64.0),    # stack on plate, ctr -3.5
              box(-60, 40, -49.4, 30, 78.2, 101.3),    # Jetson + heatsink
              box(16, 91, -37.5, 37.5, 114.4, 179.4),  # L2 body
              box(-77.5, 77.5, -23, 23, -35.9, -0.9),  # pack (inside pocket)
              box(69.7, 95.7, -62, 62, 80.5, 109.5)]   # D456, periscope
    asm = trimesh.util.concatenate(parts)
    asm.export('chassis_assembly_preview.stl')
    print('chassis_assembly_preview.stl', asm.bounds.round(1).tolist())


if __name__ == '__main__':
    main()
