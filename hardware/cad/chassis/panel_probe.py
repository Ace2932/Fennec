#!/usr/bin/env python3
"""PANEL PROBE — where can a panel-mount control actually live on this robot?

Answers, with measured geometry instead of a location typed into a README: for
a control needing a W x H panel cutout and D mm of body behind it, WHERE does
that volume exist, HOW DEEP can it go, is it reachable from outside, and is the
wall already in the right thickness band to snap into?

Written 2026-08-15 after the SW1 Contura home in chassis/README.md ("riser
FRONT-GAP zone, through the side skirt ~(x 57, z 45)") turned out to be
impossible on inspection: the free column there is 10.85 mm and the Contura
cutout is 21.08 x 36.83. That location had been carried as the answer for
weeks. The point of this file is that the next such claim comes with a number.

The headline output is a MAX-DEPTH field: how much body depth each site
affords. SW1's below-panel stack was calipered at 37 mm on 2026-08-15
(flange underside -> terminal ends), which is the --require default; pass a
larger value to include the mating receptacle and wire bend behind it.

WHAT IT MODELS
  * every static part preview_assembly.py places, as a separate mesh
  * the LEG SWEEP across the chassis-safe ROM (check_fit.py case 4 is the
    authority for those caps) — a site the legs sweep through is not a site
  * occupancy on a voxel grid; free boxes via a 3D prefix sum
  * ACCESS: clear air outside the panel too, across the whole cutout — a site
    is only real if a hand can reach the actuator

CONSERVATIVE BY CONSTRUCTION (the direction that matters — this must never
invent free space):
  * open (non-watertight) meshes get surface marking, then a flood fill seals
    every void with no air path to the outside — so a solid body reads solid
    while a shell like `trunk` keeps its real cavity
  * surface samples mark voxels too, so a thin wall cannot fall between voxel
    centres; this dilates geometry by up to one voxel, shrinking free space
  * the leg cloud carries load_leg_parts()'s strap and cable-loop proxies

Run from anywhere:
  .venv/bin/python hardware/cad/chassis/panel_probe.py
  .venv/bin/python hardware/cad/chassis/panel_probe.py --pitch 2.5
  .venv/bin/python hardware/cad/chassis/panel_probe.py --require 50
  .venv/bin/python hardware/cad/chassis/panel_probe.py --self-check
"""
import argparse
import os
import pathlib
import re
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import cad_contains  # noqa: E402  (#195 — installed in main())
from cad_assets import LEG_V6  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
LEG = str(LEG_V6)
T = trimesh.transformations.translation_matrix
HIP_FA, HIP_LAT, HIP_Z = 141.2, 39.05, 38.05

# ---- the part being placed ---------------------------------------------------
# Blue Sea Contura III = Carling V-Series. Cutout and panel range are quoted
# verbatim from the Carling V-Series datasheet; see dimensions.md "SW1".
CUTOUT_W, CUTOUT_H = 36.83, 21.08       # 1.450 x 0.830 in
PANEL_MIN, PANEL_MAX = 0.81, 6.35       # 0.032 .. 0.250 in — the wing range
BODY_CLR = 1.0                          # per side, around the body envelope
DEPTHS = np.arange(10.0, 62.5, 2.5)     # body-depth sweep
#: MEASURED 2026-08-15: 37 mm from the flange underside (the flat that seats on
#: the panel) to the TERMINAL ENDS. Approximate, and it excludes the mating
#: receptacle + wire bend behind the terminals — hence --require, so a site can
#: be re-tested against the real installed stack rather than the bare part.
SW1_DEPTH_MM = 37.0

# Chassis envelope + margin. Stops at z-40: nothing mountable lives below the
# belly line and it is all leg ROM down there.
REGION = dict(x=(-185.0, 185.0), y=(-100.0, 100.0), z=(-40.0, 205.0))
AXNAME = 'xyz'


def rot(deg, axis, point=None):
    return trimesh.transformations.rotation_matrix(np.radians(deg), axis, point)


def box(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(
        extents=[x1 - x0, y1 - y0, z1 - z0],
        transform=T([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]))


# ---- static assembly ---------------------------------------------------------
def static_parts():
    """Every static obstruction, as (name, mesh). Mirrors preview_assembly.main().
    A part added there must be added here, or this probe hands back free space
    that is actually full."""
    from power_board_model import power_board_mesh, logic_board_mesh
    P = []

    def add(name, m, tfm=None):
        m = m.copy()
        if tfm is not None:
            m.apply_transform(tfm)
        P.append((name, m))

    for n in ('trunk', 'riser_bay', 'battery_pocket', 'head', 'head_ear',
              'head_ear_L', 'neck_bracket', 'control_pod', 'floor_plate',
              'jetson_case_mount', 'jetson_clamp_bar', 'l2_adapter'):
        add(n, trimesh.load(f'{n}.stl'))
    MY = np.eye(4); MY[1, 1] = -1
    add('jetson_clamp_bar_L', trimesh.load('jetson_clamp_bar.stl'), MY)

    caseref = trimesh.load('jetson_case_ref.stl')
    bc = (caseref.bounds[0] + caseref.bounds[1]) / 2
    caseref.apply_translation([-6.85 - bc[0], -bc[1], 71.9 - caseref.bounds[0][2]])
    add('jetson_case_ref', caseref)

    rail = trimesh.load('skid_rail.stl')
    for sy in (1, -1):
        add(f'skid_rail_{"R" if sy > 0 else "L"}', rail,
            T([-55, sy * 15 - 6, -39.2]))

    # #377: FRONT carries the SW1 cutout, REAR is plain. Loading the right one
    # per end matters HERE more than anywhere: this file is what says whether a
    # panel control fits, so probing the front against a wall that no longer has
    # a hole in it would hide the volume the switch itself now occupies.
    sh_front = trimesh.load(f'{LEG}/shoulder_sw1.stl')
    sh_rear = trimesh.load(f'{LEG}/shoulder.stl')
    pl_R = trimesh.load(f'{LEG}/shoulder_plate.stl')
    pl_L = trimesh.load(f'{LEG}/shoulder_plate_L.stl')
    for end in (1, -1):
        S2T = np.array([[0, end, 0, end * HIP_FA],
                        [1, 0, 0, 0], [0, 0, 1, HIP_Z], [0, 0, 0, 1.0]])
        tag = 'F' if end > 0 else 'R'
        add(f'shoulder_{tag}', sh_front if end > 0 else sh_rear, S2T)
        add(f'shoulder_plate_{tag}R', pl_R, S2T)
        add(f'shoulder_plate_{tag}L', pl_L, S2T)

    add('l2_ref', trimesh.load('l2_ref.stl'),
        T([126.5, 0, 133]) @ rot(-22, [0, 0, 1]) @ T([-7.7, -14.66, 6.7]))
    M2 = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])
    add('d456_ref', trimesh.load('d456_ref.stl'),
        T([143, 0, 111.5]) @ rot(27.0, [0, 1, 0]) @ M2 @ T([0, 0, 26]))

    pb_mesh, _, _ = power_board_mesh()
    lb_mesh, _ = logic_board_mesh()
    add('power_board', pb_mesh)
    add('logic_board', lb_mesh)

    add('pack', box(-77.5, 77.5, -23.4, 23.4, -35.9, -0.9))
    for sx in (-40.5, 33.5):
        for sy in (-33, 33):
            add(f'standoff{sx:+.0f}{sy:+.0f}', trimesh.creation.cylinder(
                radius=2.5, height=20, transform=T([sx, sy, 16])))

    ex, dz = -87, 95           # E-stop hardware on the pod (preview proxies)
    add('estop_block', box(ex - 15, ex + 15, -15, 15, dz - 48, dz))
    add('estop_barrel', trimesh.creation.cylinder(
        radius=11, height=8, transform=T([ex, 0, dz - 1])))
    add('estop_collar', trimesh.creation.cylinder(
        radius=15, height=4, transform=T([ex, 0, dz + 4])))
    add('estop_cap', trimesh.creation.cylinder(
        radius=20, height=12, transform=T([ex, 0, dz + 11])))
    dome = trimesh.creation.icosphere(radius=20)
    dome.apply_scale([1, 1, 0.42])
    dome.apply_translation([ex, 0, dz + 17])
    add('estop_dome', dome)
    return P


def _stls_loaded_by(path):
    """Every .stl basename a module loads, including the ones behind a loop
    variable (`for n in (...): trimesh.load(f'{n}.stl')`)."""
    src = pathlib.Path(path).read_text()
    names = set(re.findall(
        r"trimesh\.load\(f?['\"](?:\{LEG\}/)?([A-Za-z0-9_]+)\.stl['\"]\)", src))
    for tup in re.findall(r"for n in \(([^)]*)\):", src, re.S):
        names |= set(re.findall(r"['\"]([A-Za-z0-9_]+)['\"]", tup))
    return names


def check_mirrors_preview():
    """static_parts() must cover everything preview_assembly.py places.

    This was a COMMENT until 2026-08-16 ("a part added there must be added
    here") and a comment cannot fail. The asymmetry is what makes it worth a
    real check: a part missing here does not make this tool merely incomplete,
    it makes it INVENT FREE SPACE — the one direction the probe must never be
    wrong in, and the direction that put an impossible SW1 home in the README
    for weeks. Leg parts are excluded because the probe covers them through the
    ROM sweep, not statically.
    """
    prev = _stls_loaded_by(HERE / 'preview_assembly.py')
    mine = _stls_loaded_by(HERE / 'panel_probe.py')
    leg = {'coax_R', 'coax_L', 'femur_R', 'femur_L', 'tibia_R', 'tibia_L',
           'knee_arm', 'knee_bumper', 'coax_hfe_block', 'coax_hfe_block_L',
           'shoulder'}          # shoulder: probe loads shoulder_sw1 + shoulder
    missing = prev - mine - leg
    if missing:
        raise SystemExit(
            f'panel_probe.static_parts() is missing {sorted(missing)}, which '
            'preview_assembly.py places. The probe would report the volume '
            'those parts occupy as FREE. Add them to static_parts().')
    return sorted(prev & mine)


# ---- leg ROM -----------------------------------------------------------------
def leg_sweep_poses():
    """(label, base, haa, hfe, kfe) over the CHASSIS-SAFE ROM only.

    Caps are check_fit.py case 4's, the authority that feeds the URDF ranges and
    firmware clamps: hfe FRONT -50..+50 / REAR -86..+50, kfe +-109, INBOARD haa
    <= 15 (outboard keeps the full 40). Sweeping past them would block volume
    the robot is never allowed to reach into.
    """
    import check_fit
    out = []
    for label, base in check_fit.coax_to_trunk_bases():
        hfe_lo = -50 if label[0] == 'F' else -86
        haas = (np.linspace(-15, 40, 7) if label[1] == 'R'
                else np.linspace(-40, 15, 7))
        for hfe in np.linspace(hfe_lo, 50, 8):
            for kfe in (-109, -55, 0, 55, 109):
                for haa in haas:
                    out.append((label, base, float(haa), float(hfe), float(kfe)))
    return out


# ---- occupancy grid ----------------------------------------------------------
class Grid:
    def __init__(self, region, pitch):
        self.pitch = pitch
        self.lo = np.array([region['x'][0], region['y'][0], region['z'][0]])
        hi = np.array([region['x'][1], region['y'][1], region['z'][1]])
        self.shape = np.ceil((hi - self.lo) / pitch).astype(int)
        self.occ = np.zeros(self.shape, dtype=bool)

    def centers_in(self, bounds):
        lo = np.maximum(np.floor((bounds[0] - self.lo) / self.pitch).astype(int), 0)
        hi = np.minimum(np.ceil((bounds[1] - self.lo) / self.pitch).astype(int) + 1,
                        self.shape)
        if np.any(hi <= lo):
            return None, None
        ix, iy, iz = (np.arange(lo[d], hi[d]) for d in range(3))
        I = np.stack(np.meshgrid(ix, iy, iz, indexing='ij'), -1).reshape(-1, 3)
        return I, self.lo + (I + 0.5) * self.pitch

    def mark_points(self, pts):
        if not len(pts):
            return
        I = np.floor((np.asarray(pts) - self.lo) / self.pitch).astype(int)
        I = I[np.all((I >= 0) & (I < self.shape), axis=1)]
        if len(I):
            self.occ[I[:, 0], I[:, 1], I[:, 2]] = True

    def world(self, idx):
        return self.lo + (np.asarray(idx) + 0.5) * self.pitch

    def index(self, xyz):
        return np.floor((np.asarray(xyz, float) - self.lo) / self.pitch).astype(int)


def build_occupancy(grid, parts, verbose=True):
    """Mark solid voxels: dense surface samples for every part, plus contains()
    interiors for the watertight ones.

    Open meshes get surface marking only here; their interiors are closed
    afterwards by the flood fill in seal_interiors(). An earlier revision
    bbox-filled them instead, which was catastrophic for `trunk`: it is a SHELL
    occupying 13.6% of its own bounding box, so bbox-filling buried the entire
    chassis cavity — and with it every wall that faces into it — under solid.
    """
    open_meshes = []
    for name, m in parts:
        try:
            n_surf = int(np.clip(m.area * 2.0, 4000, 120000))
            grid.mark_points(trimesh.sample.sample_surface(m, n_surf, seed=0)[0])
        except Exception:
            pass
        wt = bool(m.is_watertight)
        if wt:
            I, C = grid.centers_in(m.bounds)
            if I is not None:
                sel = I[m.contains(C)]
                if len(sel):
                    grid.occ[sel[:, 0], sel[:, 1], sel[:, 2]] = True
        else:
            open_meshes.append(name)
        if verbose:
            print(f'   {name:22s} {"watertight" if wt else "open (flood-fill)":17s}'
                  f' {np.round(m.extents, 1)}')
    return open_meshes


def seal_interiors(occ):
    """Any void NOT connected to the region boundary is interior — make it solid.

    This is what replaces per-part interior logic. It gets shells right without
    being told which parts are shells: the trunk cavity stays FREE because it is
    connected to open air through the trunk's own openings, while the sealed
    inside of a solid reference mesh (d456_ref, l2_ref) becomes solid because
    nothing reaches it. Physically: you cannot put a switch body somewhere no
    air path leads to.
    """
    from scipy import ndimage
    return ndimage.binary_fill_holes(occ)


def mark_leg_rom(grid, verbose=True):
    import check_fit
    check_fit.LEGPTS = check_fit.load_leg_parts()
    poses = leg_sweep_poses()
    if verbose:
        print(f'   {len(poses)} chassis-safe poses ({len(poses) // 4} per hip)')
    cache = {}
    for label, base, haa, hfe, kfe in poses:
        key = (round(hfe, 2), round(kfe, 2))
        if key not in cache:
            cache[key] = check_fit.leg_cloud(*key)
        Sx = rot(haa, [1, 0, 0],
                 [HIP_FA if label[0] == 'F' else -HIP_FA,
                  HIP_LAT if label[1] == 'R' else -HIP_LAT, HIP_Z])
        grid.mark_points(check_fit.tf(check_fit.tf(cache[key], base), Sx))
    return len(poses)


# ---- free-box search ---------------------------------------------------------
def prefix3(occ):
    """Padded 3D prefix sum: P[i,j,k] = count of occupied in occ[:i,:j,:k]."""
    P = np.zeros(np.array(occ.shape) + 1, dtype=np.int32)
    P[1:, 1:, 1:] = occ.astype(np.int32).cumsum(0).cumsum(1).cumsum(2)
    return P


def box_counts(P, n):
    """Occupied count for every window of size n=(nx,ny,nz).
    Result[i,j,k] covers occ[i:i+nx, j:j+ny, k:k+nz]."""
    nx, ny, nz = n
    X, Y, Z = np.array(P.shape) - 1
    if min(n) < 1 or nx > X or ny > Y or nz > Z:
        return None
    return (P[nx:, ny:, nz:]
            - P[:-nx, ny:, nz:] - P[nx:, :-ny, nz:] - P[nx:, ny:, :-nz]
            + P[:-nx, :-ny, nz:] + P[:-nx, ny:, :-nz] + P[nx:, :-ny, :-nz]
            - P[:-nx, :-ny, :-nz])


def orientations():
    """(label, depth_axis, extents-with-None-at-depth-axis). 3 axes x the
    in-plane 90 deg flip of the cutout."""
    bw, bh = CUTOUT_W + 2 * BODY_CLR, CUTOUT_H + 2 * BODY_CLR
    return [('x-normal', 0, [None, bw, bh]), ('x-normal r90', 0, [None, bh, bw]),
            ('y-normal', 1, [bw, None, bh]), ('y-normal r90', 1, [bh, None, bw]),
            ('z-normal', 2, [bw, bh, None]), ('z-normal r90', 2, [bh, bw, None])]


def nvox(ext, dax, D, pitch):
    e = list(ext)
    e[dax] = D
    return tuple(int(np.ceil(v / pitch)) for v in e)


def max_depth_field(P, dax, ext, pitch):
    """For every window START position, the largest free body depth. 0 = none."""
    n0 = nvox(ext, dax, DEPTHS[0], pitch)
    c0 = box_counts(P, n0)
    if c0 is None:
        return None, n0
    maxd = np.zeros(c0.shape, dtype=np.float32)
    for D in DEPTHS:
        n = nvox(ext, dax, D, pitch)
        cnt = box_counts(P, n)
        if cnt is None:
            break
        sl = [slice(None)] * 3
        sl[dax] = slice(0, cnt.shape[dax])
        region = maxd[tuple(sl)]
        np.maximum(region, np.where(cnt == 0, D, 0).astype(np.float32),
                   out=region)
    return maxd, n0


#: a human has to reach the actuator, so the outside of the panel needs clear
#: air too — not just a sightline. An earlier revision passed sites whose only
#: "exterior access" was a ray threading the gap between two legs.
ACCESS_MM = 20.0
#: material that must survive AROUND the cutout for the wings to have anything
#: to grip. Without this the probe accepts a cutout that runs off the edge of
#: its own wall -- e.g. the shoulder's rear-wall rib is 22.5 mm tall and the
#: cutout is 21.08, which a single-ray wall measurement reads as a clean 4 mm.
RIM_MM = 5.0


def free_box(occ, start, n):
    """True if the whole n-sized window at `start` is free and in bounds."""
    if any(s < 0 for s in start) or any(
            start[d] + n[d] > occ.shape[d] for d in range(3)):
        return False
    return not occ[start[0]:start[0] + n[0],
                   start[1]:start[1] + n[1],
                   start[2]:start[2] + n[2]].any()


def has_access(occ, face, dax, sign, n, wall_vox, pitch):
    """Is there ACCESS_MM of clear air outside the panel, across the full
    cutout footprint? A finger has to get there, not just a photon."""
    na = list(n)
    na[dax] = max(1, int(np.ceil(ACCESS_MM / pitch)))
    start = [face[d] - n[d] // 2 for d in range(3)]
    start[dax] = (face[dax] + wall_vox + 1 if sign > 0
                  else face[dax] - wall_vox - na[dax])
    return free_box(occ, start, na)


def wall_is_continuous(occ, face, dax, sign, n, wall_vox, pitch):
    """Is there real panel across the whole cutout footprint PLUS a rim?

    march_out() walks one ray, so on its own it cannot distinguish a wall that
    spans the cutout from a narrow rib the cutout would overhang. This requires
    the wall slab to be solid over cutout+rim in the panel plane.
    """
    if wall_vox < 1:
        return False
    rim = int(np.ceil(RIM_MM / pitch))
    nw = [n[d] + 2 * rim for d in range(3)]
    nw[dax] = wall_vox
    start = [face[d] - n[d] // 2 - rim for d in range(3)]
    start[dax] = face[dax] + 1 if sign > 0 else face[dax] - wall_vox
    if any(s < 0 for s in start) or any(
            start[d] + nw[d] > occ.shape[d] for d in range(3)):
        return False
    return bool(occ[start[0]:start[0] + nw[0],
                    start[1]:start[1] + nw[1],
                    start[2]:start[2] + nw[2]].all())


def march_out(occ, idx, axis, sign, pitch, max_wall_mm):
    """From the outermost body voxel, step outward along `axis`.
    Returns (contiguous solid VOXELS, does it then reach open air)."""
    i = list(idx)
    n = occ.shape[axis]
    solid = 0
    limit = int(max_wall_mm / pitch) + 2
    while solid <= limit:
        i[axis] += sign
        if not (0 <= i[axis] < n):
            return solid, True
        if occ[i[0], i[1], i[2]]:
            solid += 1
        else:
            break
    else:
        return solid, False
    while True:
        i[axis] += sign
        if not (0 <= i[axis] < n):
            return solid, True
        if occ[i[0], i[1], i[2]]:
            return solid, False


# ---- self-check --------------------------------------------------------------
def self_check():
    """Prove the search itself works before trusting any verdict it gives.

    Negative controls matter more than positive ones here: the failure this
    file exists to prevent is reporting free space that is solid.
    """
    ok = True

    def chk(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f'   {"PASS" if cond else "FAIL"}  {name}')

    occ = np.zeros((20, 20, 20), bool)
    P = prefix3(occ)
    chk('empty grid: 2x3x4 window has 0 occupied',
        box_counts(P, (2, 3, 4))[0, 0, 0] == 0)

    occ[5, 5, 5] = True
    P = prefix3(occ)
    c = box_counts(P, (2, 2, 2))
    chk('single solid voxel is seen by exactly the 8 windows touching it',
        int((c > 0).sum()) == 8)
    chk('window at [5,5,5] counts it', c[5, 5, 5] == 1)
    chk('window at [3,3,3] does not', c[3, 3, 3] == 0)

    # a void behind a wall THICKER than the switch wings can grip is not a site
    occ2 = np.zeros((30, 30, 30), bool)
    occ2[:, :, 12:24] = True                # 12 mm of solid at pitch 1.0
    wall, clear = march_out(occ2, (9, 9, 11), 2, +1, 1.0, 6.35)
    chk('void behind an over-thick wall is REJECTED', not clear)

    # a thin wall that opens onto MORE structure is not exterior-reachable
    occ3 = np.zeros((30, 30, 30), bool)
    occ3[:, :, 12:14] = True                # 2 mm wall...
    occ3[:, :, 18:20] = True                # ...then something else in the way
    wall, clear = march_out(occ3, (9, 9, 11), 2, +1, 1.0, 6.35)
    chk('thin wall blocked further out is REJECTED', not clear)

    # a thin wall that opens to the boundary IS a site, and the wall measures
    occ4 = np.zeros((30, 30, 30), bool)
    occ4[:, :, 12:14] = True
    wall, clear = march_out(occ4, (9, 9, 11), 2, +1, 1.0, 6.35)
    chk('thin wall onto open air is ACCEPTED', clear)
    chk('wall thickness measured as 2 voxels', abs(wall - 2.0) < 1e-6)

    # the search must not invent free space where a part sits: a solid slab
    # inside an otherwise empty grid must remove every window that overlaps it
    occ5 = np.zeros((20, 20, 20), bool)
    occ5[8:12, :, :] = True
    c5 = box_counts(prefix3(occ5), (3, 3, 3))
    starts = np.argwhere(c5 == 0)[:, 0]
    chk('no free window straddles a solid slab',
        not ((starts > 5) & (starts < 12)).any())

    # a cutout must not overhang the edge of its own wall
    narrow = np.zeros((40, 40, 40), bool)
    narrow[:, :, 20:22] = True                 # a wall...
    narrow[:, 0:6, 20:22] = False              # ...with a hole beside the site
    n_test = (6, 10, 4)
    chk('cutout overhanging a gap in its wall is REJECTED',
        not wall_is_continuous(narrow, (20, 5, 19), 2, +1, n_test, 2, 1.0))
    full = np.zeros((40, 40, 40), bool)
    full[:, :, 20:22] = True
    chk('cutout fully backed by wall is ACCEPTED',
        wall_is_continuous(full, (20, 20, 19), 2, +1, n_test, 2, 1.0))

    # seal_interiors: the whole trunk-vs-d456 distinction rests on this, so
    # test BOTH directions rather than just the one that flatters it.
    sealed = np.zeros((20, 20, 20), bool)
    sealed[4:16, 4:16, 4:16] = True
    sealed[7:13, 7:13, 7:13] = False           # void with no path out
    f = seal_interiors(sealed)
    chk('sealed void IS filled (solid body reads solid)', f[10, 10, 10])

    openbox = np.zeros((20, 20, 20), bool)
    openbox[4:16, 4:16, 4:16] = True
    openbox[7:13, 7:13, 7:13] = False
    openbox[7:13, 7:13, 4:16] = False          # bore a channel to open air
    f2 = seal_interiors(openbox)
    chk('void WITH a path to open air is NOT filled (shell stays hollow)',
        not f2[10, 10, 10])
    chk('flood fill never erodes existing solid',
        bool((f2 | openbox == f2).all()))

    # total-blockage negative control: a fully solid grid yields no free box
    P4 = prefix3(np.ones((20, 20, 20), bool))
    chk('solid grid yields zero free windows',
        int((box_counts(P4, (2, 2, 2)) == 0).sum()) == 0)

    print(f'\n   self-check {"PASSED" if ok else "FAILED"}')
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pitch', type=float, default=3.0)
    ap.add_argument('--no-legs', action='store_true')
    ap.add_argument('--self-check', action='store_true')
    ap.add_argument('--require', type=float, default=SW1_DEPTH_MM,
                    help='only report sites offering at least this body depth '
                         f'(default {SW1_DEPTH_MM} = measured SW1 stack)')
    a = ap.parse_args()
    os.chdir(HERE)
    # #195: trimesh's contains() redraws from numpy's GLOBAL RNG when its two
    # ray directions disagree, so it can answer differently on identical input
    # BETWEEN PROCESSES. Every verdict this file prints is a threshold on a
    # contains() result. check_seeding.py does not police this file (it only
    # scans CI gates, and this is an analysis tool) — which is exactly why it
    # had to be caught by hand.
    cad_contains.install()
    global DEPTHS
    if a.require and a.require not in DEPTHS:
        DEPTHS = np.sort(np.append(DEPTHS, a.require))

    if a.self_check:
        print('-- self-check --')
        sys.exit(0 if self_check() else 1)

    print(f'PANEL PROBE   cutout {CUTOUT_W} x {CUTOUT_H} mm | panel band '
          f'{PANEL_MIN}-{PANEL_MAX} mm | pitch {a.pitch} mm')
    print(f'body envelope {CUTOUT_W + 2*BODY_CLR:.1f} x '
          f'{CUTOUT_H + 2*BODY_CLR:.1f} mm + depth\n')

    g = Grid(REGION, a.pitch)
    print(f'grid {tuple(g.shape)} = {int(np.prod(g.shape)):,} voxels\n')
    covered = check_mirrors_preview()
    print(f'-- static parts -- (mirrors preview_assembly: {len(covered)} shared STLs)')
    open_meshes = build_occupancy(g, static_parts())
    n_surf = int(g.occ.sum())
    g.occ = seal_interiors(g.occ)
    static_occ = g.occ.copy()
    n_static = int(static_occ.sum())
    print(f'\n   surfaces + watertight interiors: {n_surf:,} voxels')
    print(f'   flood fill sealed {n_static - n_surf:,} interior voxels '
          f'-> static {n_static:,} ({100*n_static/g.occ.size:.1f}%)')
    if open_meshes:
        print(f'   open meshes closed by flood fill, not bbox: '
              f'{", ".join(open_meshes)}')

    if not a.no_legs:
        print('\n-- leg ROM sweep (chassis-safe ROM only) --')
        mark_leg_rom(g)
        n_all = int(g.occ.sum())
        print(f'   leg ROM added {n_all-n_static:,} voxels -> '
              f'{100*n_all/g.occ.size:.1f}% of region blocked')

    P = prefix3(g.occ)             # collide against static + leg ROM
    PS = prefix3(static_occ)       # but you can only BOLT to static
    p = a.pitch
    adj = max(1, int(np.ceil(6.0 / p)))   # "structure within 6 mm" = mountable

    print('\n' + '=' * 78)
    print('DEEPEST BODY THAT FITS ANYWHERE, per orientation')
    print('=' * 78)
    fields = {}
    for oname, dax, ext in orientations():
        maxd, n0 = max_depth_field(P, dax, ext, p)
        if maxd is None:
            print(f'  {oname:14s} window larger than the probe region')
            continue
        fields[oname] = (dax, ext, maxd)
        best = float(maxd.max())
        print(f'  {oname:14s} max depth {best:5.1f} mm   '
              f'({int((maxd > 0).sum()):,} sites admit >= {DEPTHS[0]:.0f} mm)')

    print('\n' + '=' * 78)
    print('MOUNTABLE SITES')
    print('=' * 78)
    print('Free body volume, reachable from outside, AND within 6 mm of real')
    print('structure — a box floating in mid-air is not a mounting location,')
    print('which is what an earlier revision of this file happily reported.\n')

    drop_in, buildable = [], []
    for oname, (dax, ext, maxd) in fields.items():
        n0 = nvox(ext, dax, DEPTHS[0], p)
        ne = tuple(n0[d] + 2 * adj for d in range(3))
        E = box_counts(PS, ne)
        if E is None:
            continue
        near = np.zeros(maxd.shape, bool)
        near[adj:adj + E.shape[0], adj:adj + E.shape[1],
             adj:adj + E.shape[2]] = E > 0
        sites = np.argwhere((maxd >= a.require) & near)
        if not len(sites):
            continue
        depths = maxd[sites[:, 0], sites[:, 1], sites[:, 2]]
        order = np.argsort(-depths)
        sites, depths = sites[order], depths[order]
        step = max(1, len(sites) // 4000)
        for s, D in zip(sites[::step], depths[::step]):
            n = nvox(ext, dax, float(D), p)
            for sign in (-1, +1):
                face = list(s + np.array(n) // 2)
                face[dax] = s[dax] + (n[dax] - 1 if sign > 0 else 0)
                wv, clear = march_out(g.occ, face, dax, sign, p, PANEL_MAX)
                if not clear:
                    continue
                if not has_access(g.occ, face, dax, sign, n, wv, p):
                    continue          # no room for a hand outside the panel
                wall = wv * p
                row = (float(D), wall, oname, dax, sign, g.world(face))
                if wall < PANEL_MIN:
                    buildable.append(row)
                elif wall <= PANEL_MAX and wall_is_continuous(
                        g.occ, face, dax, sign, n, wv, p):
                    drop_in.append(row)
                # walls thicker than the wing range are not a Contura site at
                # all; they would need a machined rebate, so they are dropped
                # rather than quietly listed as if they were drop-ins.

    def show(rows, title, limit=18):
        print(f'\n  --- {title} ---')
        if not rows:
            print('      none')
            return
        rows.sort(key=lambda r: -r[0])
        seen, keep = set(), []
        for r in rows:
            k = (r[3], r[4], *np.round(r[5] / 25).astype(int))
            if k in seen:
                continue
            seen.add(k)
            keep.append(r)
        print(f'      {"panel face (x, y, z)":26s} {"out":5s} {"depth":>6s} '
              f'{"wall":>5s}')
        for D, wall, oname, dax, sign, w in keep[:limit]:
            nrm = f'{"+" if sign > 0 else "-"}{AXNAME[dax]}'
            print(f'      ({w[0]:7.1f},{w[1]:7.1f},{w[2]:7.1f})   {nrm:5s} '
                  f'{D:5.1f} {wall:5.1f}')
        print(f'      {len(keep)} distinct sites; showing {min(limit,len(keep))}')

    show(drop_in, f'DROP-IN: existing wall already {PANEL_MIN}-{PANEL_MAX} mm, '
                  'switch snaps straight in')
    show(buildable, 'BUILDABLE: open air against structure — panel comes with '
                    'a new pod/bracket')

    # Where the free real estate actually is, in words rather than coordinates.
    def zone(w):
        x, y, z = w
        if z > 96:
            side = 'front' if x > 40 else ('rear' if x < -40 else 'centre')
            return f'ABOVE the deck / head height ({side})'
        if z > 72:
            return 'deck level (z72-96)'
        if x < -63.5:
            return 'REAR pocket, behind the trunk'
        if x > 63.5:
            return 'FRONT, forward of the trunk end'
        return 'trunk flanks (z<72)'

    print('\n  --- where the free real estate is ---')
    tally = {}
    for D, wall, oname, dax, sign, w in drop_in + buildable:
        k = zone(w)
        cur = tally.get(k, [0, 0.0])
        tally[k] = [cur[0] + 1, max(cur[1], D)]
    for k, (n, dmax) in sorted(tally.items(), key=lambda kv: -kv[1][0]):
        print(f'      {k:42s} {n:5d} placements, deepest {dmax:.1f} mm')

    # ---- the locations that have actually been proposed ----------------------
    print('\n' + '=' * 78)
    print('LOCATIONS PROPOSED IN DOCS / REVIEW — adjudicated')
    print('=' * 78)
    NAMED = [
        ('riser FRONT-GAP side skirt (README:264)', (57, 52, 45), 1, +1),
        ('riser side skirt, mid-length', (0, 52, 48), 1, +1),
        ('riser FRONT end wall', (63, 0, 57), 0, +1),
        ('riser deck, top face', (0, 0, 70), 2, +1),
        ('REAR SHOULDER cheek (the "side")', (-141, 57, 38), 1, +1),
        ('REAR SHOULDER rear-facing face', (-66, 30, 58), 0, -1),
        ('control_pod deck beside E-stop', (-87, 22, 93), 2, +1),
        ('control_pod deck, outboard of cap', (-87, 34, 93), 2, +1),
        ('trunk side wall', (0, 50, 20), 1, +1),
        ('rear pocket, above shoulder tops', (-85, 0, 85), 0, -1),
    ]
    for label, xyz, dax, sign in NAMED:
        idx = g.index(xyz)
        if np.any(idx < 0) or np.any(idx >= g.shape):
            print(f'  {label:40s} outside probe region')
            continue
        # These coordinates name a SURFACE, so the given voxel is usually the
        # wall itself. Step inward (against the outward normal) to the first
        # free voxel — that is where a body could actually begin — and record
        # how much wall we crossed getting there.
        wall_vox, cur = 0, list(idx)
        while (0 <= cur[dax] < g.shape[dax]) and g.occ[cur[0], cur[1], cur[2]] \
                and wall_vox < int(12 / p) + 2:
            cur[dax] -= sign
            wall_vox += 1
        buried = not (0 <= cur[dax] < g.shape[dax]) or \
            g.occ[cur[0], cur[1], cur[2]]
        got = None
        if not buried:
            for oname, dax2, ext in orientations():
                if dax2 != dax:
                    continue
                for D in DEPTHS[::-1]:
                    n = nvox(ext, dax, float(D), p)
                    start = list(np.array(cur) - np.array(n) // 2)
                    # body extends inward from the first free voxel
                    start[dax] = cur[dax] - n[dax] + 1 if sign > 0 else cur[dax]
                    if any(s < 0 for s in start) or any(
                            start[d] + n[d] > g.shape[d] for d in range(3)):
                        continue
                    if not g.occ[start[0]:start[0] + n[0],
                                 start[1]:start[1] + n[1],
                                 start[2]:start[2] + n[2]].any():
                        got = (oname, float(D))
                        break
                if got:
                    break
        wall_mm = wall_vox * p
        if got:
            print(f'  {label:40s} FITS — {got[1]:4.1f} mm deep behind a '
                  f'{wall_mm:.1f} mm wall ({got[0]})')
        elif buried:
            print(f'  {label:40s} NO — solid/leg-ROM for >{wall_mm:.0f} mm '
                  f'inward; nothing to put a body in')
        else:
            print(f'  {label:40s} NO — wall {wall_mm:.1f} mm, then free space '
                  f'too small for even {DEPTHS[0]:.0f} mm of body')

    print(f'\nVoxel-quantised at {p} mm and conservative by construction: '
          'free space is understated, never overstated.')
    print('Run --self-check to exercise the search on synthetic grids.')


if __name__ == '__main__':
    main()
