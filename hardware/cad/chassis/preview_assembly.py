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
    # SM3_Foot tread crescent on the toe_v2 seat (mesh survey v3): crescent
    # center shoe-local (0,7) -> the O7 post; theta = 54 EXACTLY (band ctr
    # 270 + 54 = stance-plumb -36; the toe_v2 key pockets now fix it).
    # dimensions.md SM3_Foot section; gate: leg_v6/check_shoe.py.
    shoe = trimesh.load(f'{NOVA}/original_body_files/SM3_Foot.stl')
    M_shoe = (T([129, 0, -30.5]) @ rot(54, [0, 0, 1]) @ T([0, -7.0, 0]))
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


def foot_preview():
    """toe_v2 <-> shoe closeup: tibia_R + SM3_Foot in tibia-local frame."""
    tib = trimesh.load(f'{LEG}/tibia_R.stl')
    shoe = trimesh.load(f'{NOVA}/original_body_files/SM3_Foot.stl')
    shoe.apply_transform(
        T([129, 0, -30.5]) @ rot(54, [0, 0, 1]) @ T([0, -7.0, 0]))
    asm = trimesh.util.concatenate([tib, shoe])
    asm.export('foot_assembly_preview.stl')
    print('foot_assembly_preview.stl', asm.bounds.round(1).tolist())


def main():
    foot_preview()
    parts = [trimesh.load(f'{NOVA}/original_body_files/SM3_Frame_ChassisTrunk.stl'),
             trimesh.load('riser_bay.stl'),
             trimesh.load('battery_pocket.stl'),
             trimesh.load('l2_mast.stl'),
             trimesh.load('d456_head.stl'),
             trimesh.load('floor_plate.stl'),
             trimesh.load('jetson_case_mount.stl')]
    # official Jetson case (ref mesh) at its chosen placement: bbox-centre
    # (x-6.85, y0), bottom on the deck (z71.9). Port END faces -x (rear).
    caseref = trimesh.load('jetson_case_ref.stl')
    bc = (caseref.bounds[0] + caseref.bounds[1]) / 2
    caseref.apply_translation([-6.85 - bc[0], -bc[1], 71.9 - caseref.bounds[0][2]])
    parts.append(caseref)
    # TPU skid rails under the tray (backlog #15)
    rail = trimesh.load('skid_rail.stl')
    for sy in (1, -1):
        r = rail.copy()
        r.apply_transform(T([-55, sy * 15 - 6, -39.2]))
        parts.append(r)
    sh = trimesh.load(f'{LEG}/shoulder.stl')
    pl_R = trimesh.load(f'{LEG}/shoulder_plate.stl')
    pl_L = trimesh.load(f'{LEG}/shoulder_plate_L.stl')
    for end in (1, -1):
        S2T = np.array([[0, end, 0, end * HIP_FA],
                        [1, 0, 0, 0], [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])
        for m in (sh, pl_R, pl_L):    # horn plates: the leg<->shoulder bridge
            s = m.copy()
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
              box(16, 91, -37.5, 37.5, 117.4, 182.4),  # L2 body (seat 117.4)
              box(-77.5, 77.5, -23.4, 23.4, -35.9, -0.9),  # pack 46.8 caliper
              box(69.7, 95.7, -61.9, 61.9, 80.5, 109.5)]  # D456, periscope
    asm = trimesh.util.concatenate(parts)
    asm.export('chassis_assembly_preview.stl')
    print('chassis_assembly_preview.stl', asm.bounds.round(1).tolist())


if __name__ == '__main__':
    main()
