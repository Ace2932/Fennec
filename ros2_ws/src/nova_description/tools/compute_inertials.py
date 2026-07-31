#!/usr/bin/env python3
"""Compute per-link inertials (mass, CoM, inertia tensor) for nova.urdf.xacro
from the REAL leg_v6 part meshes + embedded servo masses, mapped into each URDF
link frame.

WHY: the URDF ships crude placeholder inertials (`ixx=iyy=izz=mass*1e-3`,
isotropic, CoM at the joint) — fine for RViz, wrong for MJX/Isaac RL. This emits
real anisotropic tensors so the sim dynamics are physical.

⚠ PROVISIONAL — REFINE BY MEASUREMENT. Two approximations here, both linear to
fix once the printed set exists:
  1. MASS = solid mesh volume x an EFFECTIVE density (PA6-CF 1.17 g/cm3 x infill
     factor). The real part is 4 walls + 40% gyroid, not solid, and the shell
     mass sits at larger radius than a uniform solid -> this slightly
     UNDERESTIMATES inertia. When you WEIGH each printed link, rescale its whole
     <inertial> by measured_mass / computed_mass (CoM unchanged; inertia scales
     linearly with mass). That single ratio absorbs the density error.
  2. SERVO modeled as a 60 g box at the shell centroid (the pocket is ~central).
     If you measure a servo's true seated position, move it and rerun.
Frame maps (STL -> URDF link) are EXACT and validated against the URDF's own
landmarks (femur STL (106.9,0,0) -> link (0,0,-0.1069); tibia foot jog sign).

Run:  ../../../.venv/bin/python compute_inertials.py         # prints table + XACRO
Deps: trimesh, numpy (proj/.venv).
"""

import pathlib

import numpy as np
import trimesh

# Paths resolve from this file, not from one laptop's checkout (#166). The
# stock foot mesh is already vendored in this package's own meshes/ — the old
# ORIG reached out to the ROOT repo for a file sitting one directory away.
_PKG = pathlib.Path(__file__).resolve().parents[1]  # .../src/nova_description
_PROJ = pathlib.Path(__file__).resolve().parents[4]  # proj/
LEG = str(_PROJ / "hardware" / "cad" / "leg_v6")
ORIG = str(_PKG / "meshes")

# ---- materials -------------------------------------------------------------
# CALIBRATED 2026-07-13 from real prints (Bambu slicer estimate confirmed
# accurate: femur slicer 56.7 g vs MEASURED 57 g). 40%-infill parts print at
# 0.712 g/cm3 (femur 57 g / 80.1 cm3); the tibia is 25% infill -> 0.586 g/cm3
# (51 g slicer / 87.0 cm3). Both ~15-30% lighter than the old 0.70 guess.
RHO_PA6CF = 1.17e-3  # g/mm^3 (1.17 g/cm^3 solid)
INFILL_LEG = 0.608  # 40% gyroid + 4 walls -> 0.712 g/cm3 (femur-calibrated)
RHO_LEG = RHO_PA6CF * INFILL_LEG  # 40%-infill parts (coax/femur/knee_arm/shoulder)
RHO_TIBIA = RHO_PA6CF * 0.501  # tibia only: 25% infill -> 0.586 g/cm3
RHO_TPU = 1.20e-3 * 0.9  # TPU shoe, ~100% -> near solid
SERVO_MASS = 60.0  # g, STS3215 (datasheet ~60; URDF had 0.055)
SERVO_BOX = np.array([45.4, 24.8, 39.6])  # servo bbox mm (measured STL)


def box_inertia(mass, dims):
    """Solid-box inertia about its own centroid (mass g, dims mm) -> g*mm^2."""
    x, y, z = dims
    return np.diag(
        [
            mass * (y * y + z * z) / 12.0,
            mass * (x * x + z * z) / 12.0,
            mass * (x * x + y * y) / 12.0,
        ]
    )


def combine(bodies):
    """bodies: list of (mass, com(3), I_about_own_com(3x3)). Returns combined
    (mass, com, I_about_combined_com) via the parallel-axis theorem."""
    m = sum(b[0] for b in bodies)
    com = sum(b[0] * b[1] for b in bodies) / m
    I = np.zeros((3, 3))
    for mb, cb, Ib in bodies:
        d = cb - com
        I += Ib + mb * (np.dot(d, d) * np.eye(3) - np.outer(d, d))
    return m, com, I


def part_body(path, rho, add_servo):
    """Mesh -> (mass g, com mm, I_about_com g*mm^2) in the STL frame, optionally
    with a servo box added at the shell centroid."""
    m = trimesh.load(path)
    m.density = rho
    shell = (m.mass, m.center_mass.copy(), m.moment_inertia.copy())
    if not add_servo:
        return shell
    servo = (SERVO_MASS, m.center_mass.copy(), box_inertia(SERVO_MASS, SERVO_BOX))
    return combine([shell, servo])


# ---- per-link definitions --------------------------------------------------
# R = STL-frame -> URDF-link-frame rotation (validated vs URDF landmarks).
# origin_stl = the proximal joint axis point in STL mm (link-frame origin).
R_HIP = np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1]], float)  # coax: Y=HAA->x
R_LEG = np.array(
    [[0, -1, 0], [0, 0, 1], [-1, 0, 0]], float
)  # femur/tibia: Z=hinge->y, +X->-z

LINKS = [
    # name, meshes[(path,rho,servo)], R, origin_stl(mm)
    (
        "hip",
        [
            (f"{LEG}/coax_R.stl", RHO_LEG, True),
            (f"{LEG}/coax_hfe_block.stl", RHO_LEG, False),
        ],
        R_HIP,
        np.zeros(3),
    ),
    (
        "upper",
        [
            (f"{LEG}/femur_R.stl", RHO_LEG, True),
            (f"{LEG}/knee_arm.stl", RHO_LEG, False),
        ],
        R_LEG,
        np.zeros(3),
    ),
    ("lower", [(f"{LEG}/tibia_R.stl", RHO_TIBIA, True)], R_LEG, np.zeros(3)),
    # foot: the TPU shoe STL is in its OWN frame (not the tibia frame) and is a
    # ~4 g contact endpoint -> place its inertia at the foot link origin
    # (R=I, origin=None -> shell centroid so CoM_link ~ 0). Orientation is
    # dynamically irrelevant at this mass.
    ("foot", [(f"{ORIG}/SM3_Foot.stl", RHO_TPU, False)], np.eye(3), None),
]


def link_inertial(meshes, R, origin_stl):
    bodies = [part_body(p, rho, sv) for p, rho, sv in meshes]
    m, com_stl, I_stl = combine(bodies)
    if origin_stl is None:  # place the CoM at the link origin
        origin_stl = com_stl
    # STL -> link frame: rotate the tensor, move CoM to the link origin
    com_link = R @ (com_stl - origin_stl)
    I_link = R @ I_stl @ R.T
    return m, com_link, I_link


def fmt(name, m, com, I):
    kg = m / 1000.0
    com_m = com / 1000.0
    Ik = I / 1e9  # g*mm^2 -> kg*m^2
    print(
        f"\n== {name}: mass {kg:.4f} kg  CoM(m) "
        f"[{com_m[0]:+.4f} {com_m[1]:+.4f} {com_m[2]:+.4f}] =="
    )
    print(
        f"   I(kg*m^2) ixx={Ik[0, 0]:.3e} iyy={Ik[1, 1]:.3e} izz={Ik[2, 2]:.3e} "
        f"ixy={Ik[0, 1]:+.2e} ixz={Ik[0, 2]:+.2e} iyz={Ik[1, 2]:+.2e}"
    )
    # emit URDF-ready block
    print("   <inertial>")
    print(
        f'     <origin xyz="{com_m[0]:.5f} {com_m[1]:.5f} {com_m[2]:.5f}" rpy="0 0 0"/>'
    )
    print(f'     <mass value="{kg:.4f}"/>')
    print(
        f'     <inertia ixx="{Ik[0, 0]:.3e}" iyy="{Ik[1, 1]:.3e}" izz="{Ik[2, 2]:.3e}"'
    )
    print(
        f'              ixy="{Ik[0, 1]:.2e}" ixz="{Ik[0, 2]:.2e}" iyz="{Ik[1, 2]:.2e}"/>'
    )
    print("   </inertial>")


if __name__ == "__main__":
    print("NOVA per-link inertials from leg_v6 meshes + STS3215 servos")
    print(
        f"(PA6-CF eff {RHO_LEG * 1e3:.3f} g/cm3, servo {SERVO_MASS} g. "
        f"RIGHT-leg values; mirror y for LEFT.)"
    )
    for name, meshes, R, origin in LINKS:
        m, com, I = link_inertial(meshes, R, origin)
        fmt(name, m, com, I)
    print(
        "\nNOTE base_link (trunk + Jetson + battery + boards + L2/D456) is "
        "payload-dominated (~2.8 kg) -- not computed here; needs the assembled "
        "CoM. Keep m_base estimate until the stack is weighed."
    )
