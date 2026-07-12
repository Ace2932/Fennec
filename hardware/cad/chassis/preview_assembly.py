#!/usr/bin/env python3
"""Build chassis_assembly_preview.stl — everything designed so far in one
mesh for CAD Viewer review: trunk + riser + shoulders + battery pocket +
L2 mast + 4 legs (stance pose, inside chassis-safe ROM) + the REAL power
board (power_board_model.power_board_mesh()) + the REAL logic board
(power_board_model.logic_board_mesh(), replacing the old flat logic-
board/Teensy envelope boxes — both mezzanine boards are now kicad_pcb-
parsed per-component geometry, not placeholders) + ENVELOPE boxes for the
rest (Jetson+heatsink, L2 body, belly pack). Remaining boxes are still
envelopes, not parts. The power board's real rear components (J1) still
poke the trunk's rear corner slab on one side (the known trim finding,
now board-accurate — see check_fit.py case 11). Run after any part change:
  ../../../.venv/bin/python preview_assembly.py
"""
import numpy as np
import trimesh

from power_board_model import power_board_mesh, logic_board_mesh

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
    arm.apply_transform(T([59, 0, 17.75]))  # rev 3 (2026-07-10): 17.2->17.75
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
                  (trimesh.load(f'{LEG}/coax_hfe_plate.stl'), np.eye(4)),  # #53 fix: bolt-on inboard HFE arm
                  (servo, coax_pose),
                  (trimesh.load(f'{LEG}/femur_R.stl'), S @ M_f),
                  (arm, S @ M_f),
                  (trimesh.load(f'{LEG}/tibia_R.stl'), M_tib),
                  (trimesh.load(f'{LEG}/knee_bumper.stl'), M_tib),  # TPU knee guard
                  (shoe, M_tib)]:   # (tibia_pad RETIRED — misplaced, backlog #15)
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
    parts = [trimesh.load('trunk.stl'),   # DERIVED trunk: stock geom + 10 modeled fastener bores
             trimesh.load('riser_bay.stl'),
             trimesh.load('battery_pocket.stl'),
             trimesh.load('head.stl'),        # fwd head (D456 face + L2 crown)
             trimesh.load('head_ear.stl'),      # fennec ear / antenna mast (R)
             trimesh.load('head_ear_L.stl'),    # ear (L)
             trimesh.load('neck_bracket.stl'),  # front-shoulder-deck adapter
             trimesh.load('control_pod.stl'),   # rear-top E-stop + OLED pod
             trimesh.load('floor_plate.stl'),
             trimesh.load('jetson_case_mount.stl')]
    # E-stop (mxuteuk 22mm 2NC — VERIFIED dims: Ø40 mushroom, Ø22 barrel, 77
    # total, ~30x30x48 contact block) at pod ES x-87, deck top z95:
    ex, dz = -87, 95
    parts.append(box(ex-15, ex+15, -15, 15, dz-48, dz))             # 30x30x48 contact block
    parts.append(trimesh.creation.cylinder(radius=11, height=8,
        transform=T([ex, 0, dz-1])))                               # Ø22 barrel thru the 5mm deck
    parts.append(trimesh.creation.cylinder(radius=15, height=4,
        transform=T([ex, 0, dz+4])))                               # twist collar (above panel)
    parts.append(trimesh.creation.cylinder(radius=20, height=12,
        transform=T([ex, 0, dz+11])))                              # mushroom cap body (z99..111)
    dome = trimesh.creation.icosphere(radius=20); dome.apply_scale([1, 1, 0.42])
    dome.apply_translation([ex, 0, dz+17])
    parts.append(dome)                                             # domed top (~z123)
    # 2 case hold-down BARS (#44, replaced the 4 clamps) + OLED bracket (#40)
    bar=trimesh.load('jetson_clamp_bar.stl'); parts.append(bar)
    MYb=np.eye(4); MYb[1,1]=-1; b2=bar.copy(); b2.apply_transform(MYb); parts.append(b2)
    parts.append(trimesh.load('oled_mount.stl'))
    # jetson_cowl RETIRED 2026-07-10 (#41) — right-angle plug adapters replace
    # it; the -Y cables now drop straight through the CASE_SLOT, no cowl.
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
    # REAL D456 (d456_ref.stl, mm, from the RealSense SLDPRT via STL). Mounts
    # rear->plate (the 2x M3 @ ±47.2 are on the REAR face = STL z-26), lens
    # (STL z0) projecting forward-down at 27deg. STL axes: X=length->head Y,
    # Y=height->up, Z=depth (z-26 rear -> at CAM_M, z0 lens -> +x' fwd).
    M2 = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])
    cam = trimesh.load('d456_ref.stl')
    cam.apply_transform(T([143, 0, 111.5]) @ rot(27.0, [0, 1, 0]) @ M2
                        @ T([0, 0, 26]))
    # REAL Unitree L2 (l2_ref.stl, mm, from the STEP). Base center (STEP
    # 7.7,14.66,-6.7) -> seat (126.5,0,128); Rz-22 lands the Ø51/90° base holes
    # on the crown's 45° (±18) pattern; body rises to z191.5. (check_fit keeps
    # the 75x75 box as the conservative envelope.)
    # L2 now on the L2 ADAPTER (l2_adapter.scad) -> base at z133 (was 128).
    l2 = trimesh.load('l2_ref.stl')
    l2.apply_transform(T([126.5, 0, 133]) @ rot(-22, [0, 0, 1])
                       @ T([-7.7, -14.66, 6.7]))
    # REAL power board (power_board_model.py): slab + every populated
    # footprint (kicad_pcb-parsed) + the 5 off-board buck cards, TRUNK frame,
    # standoff off the floor now STANDOFF_FLOOR_MM=22 (power_board_model.py)
    # -- chassis-side fix, board/components unchanged (ordered/locked BOM).
    # See check_fit.py case 11 for the riser/floor/rear-slab/logic-board-
    # underside clearance assertions run against this mesh.
    pb_mesh, pb_components, _ = power_board_mesh()
    # LOGIC BOARD (nova_pcb_v6_logic): REAL kicad_pcb-parsed geometry, no
    # longer an envelope box -- power_board_model.logic_board_mesh() parses
    # the live .kicad_pcb the same way power_board_mesh() does (same
    # footprint parser, courtyard handling, TRUNK_DX/DY transform -- the
    # logic board shares the power board's exact mount-hole pattern) and
    # extrudes every populated component: F.Cu (Teensy 4.1, Arduino Nano,
    # headers, etc.) UP from the top/component face toward the removable
    # riser deck (resolves the earlier "lid-off service" concern; corrects
    # the prior side-down/ambiguous modeling and the matching README.md
    # error), B.Cu (3x 0.6mm resistors) DOWN toward the power board. Planes
    # (LOGIC_BOARD_Z0/Z1) and the real parsed stack ceiling (STACK_TOP_Z)
    # are centralized in power_board_model.py so this file and check_fit.py
    # can't drift apart. Q1 clearing the logic-board underside is an
    # explicit assertion in check_fit.py case 11.
    lb_mesh, lb_components = logic_board_mesh()
    parts += [pb_mesh,                                 # real power board, ctr -3.5
              lb_mesh,                                 # real logic board, kicad_pcb-parsed
              l2, trimesh.load('l2_adapter.stl'),        # real L2 + its adapter
              box(-77.5, 77.5, -23.4, 23.4, -35.9, -0.9),  # pack 46.8 caliper
              cam]                                       # real D456 (down-tilted)
    # 4 mezzanine standoffs (M3x20) — floor plate top (z6) -> power board
    # bottom (z26) at the 74x66 mount pattern (floor_plate STK_X/STK_Y).
    # Preview-only visual so the board visibly stands on its posts (they were
    # missing -> the board read as floating in the bay).
    for sx in (-40.5, 33.5):
        for sy in (-33, 33):
            parts.append(trimesh.creation.cylinder(
                radius=2.5, height=20, transform=T([sx, sy, 16])))
    asm = trimesh.util.concatenate(parts)
    asm.export('chassis_assembly_preview.stl')
    print('chassis_assembly_preview.stl', asm.bounds.round(1).tolist())


if __name__ == '__main__':
    main()
