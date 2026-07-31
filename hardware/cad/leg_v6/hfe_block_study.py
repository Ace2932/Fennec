#!/usr/bin/env python3
"""Option C HFE joint — geometry proof for the removable OUTBOARD block (#226).

WHY C AND NOT THE CURRENT DESIGN. coax_hfe_plate cannot be installed. Measured
2026-07-31: blocked in all six axes against the seated femur AND against a bare
coax, in the current revision AND in the pre-#7-fix one, while its seated pose
is legitimate (boolean intersection with the coax = 0.0 mm3). A valid final
position with no way to reach it. check_fit.removable_member_checks() now gates
that; this file designs the replacement.

WHY C AND NOT E (boss-only insert). Removing just the O19 boss (1.02 cm3) does
clear the LATERAL +Y path and preserves the fatigue-critical gusset -- but it
leaves the cap, and the cap is the part that cannot be assembled. E fixes the
gate's finding and not the bench's.

THE JOINT, and why it is a tenon rather than bolts:

  split      x = 56.2 (ARM_OUT_X0). The whole outboard arm + gusset + boss
             becomes the removable BLOCK; the inboard arm becomes INTEGRAL
             (coax_hfe_plate fused in), so the cap stops existing.

  loads      static  400 N per disc  (M_HFE 14.2 N.m / 35.5 mm spacing, §7)
             cyclic  20 N lateral foot -> 4.72 N.m -> 133 N per arm along X
             The cyclic case is the binding one: coax.scad records this
             junction as "the only member on the robot under SF 15" (~14 MPa
             at the 4mm root, fatigue SF ~1.9/stride; the 2mm gusset halves it).

  why not bolts in tension. Any bridge-level interface sits ~22 mm above the
  boss, so 133 N becomes ~2.95 N.m at the joint. On a 10 mm-tall face that is
  ~490 N per bolt -- far past M3 heat-set pull-out in wet PA6-CF. A concentric
  spigot would fix the lever arm, but there is no room: MEASURED, the femur
  occupies r 10..16 at the boss station, leaving no free annulus.

  so: MORTISE AND TENON. The tenon reacts the moment in BEARING over its own
  length (2.95 N.m / 12.05 mm = 245 N on ~92 mm2 = 2.7 MPa) and the bolts drop
  to retention. That is exactly the move #7-fix made for the cap -- shape key
  carries, M3 retains -- including its hard-won corollary: the key must be
  CLOSED in both directions, because a compression-only key cannot react peel.
  This tenon is shrunk on y0/y1/z0/z1 and flush only at the mating plane.

  bridge     grown z 13.4 -> 18.0 over x 40..56.2 to host the mortise. MEASURED
             headroom: growing to z=24 still leaves 7.76 mm to shoulder+plate
             across the full +-40 deg haa sweep, so this is free real estate.
  mortise    x 43.8..56.3, y 0..23.2, z 9..16
  tenon      the same, CLR 0.15 off y0/y1/z0/z1
  retention  2x M3 heat-set along -X at the mortise blind end. Cyclic pull-out
             133/2 = 66 N per bolt vs ~175-245 N wet -> SF 2.6-3.7. Driver
             access is +X open air, which is the whole point of C.

LIMIT: this proves GEOMETRY (insertability, no interpenetration), not strength,
printability, or bolt-driver reach. Those are check_fit/mesh_health's job once
the .scad exists. It is a design proof, not a part.
"""

import sys

import numpy as np
import trimesh

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))

SPLIT_X = 56.2
HFE_Y, HFE_Z = 11.6, -9.5
BOSS_R, BOSS_X0 = 9.5, 51.5
BORE_CLR = 0.5            # coax clearance bore = boss + this. See the control.
GROW_X0, GROW_Z1 = 40.0, 18.0
MORT = dict(x0=43.8, x1=56.3, y0=0.0, y1=23.2, z0=9.0, z1=16.0)
CLR = 0.15
DIRS = [('+X', (1, 0, 0)), ('-X', (-1, 0, 0)), ('+Y', (0, 1, 0)),
        ('-Y', (0, -1, 0)), ('+Z', (0, 0, 1)), ('-Z', (0, 0, -1))]


def _box(x0, x1, y0, y1, z0, z1):
    b = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    b.apply_transform(trimesh.transformations.translation_matrix(
        [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]))
    return b


def _axial_cyl(r, x0, x1):
    c = trimesh.creation.cylinder(radius=r, height=x1 - x0)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    c.apply_transform(trimesh.transformations.translation_matrix(
        [(x0 + x1) / 2, HFE_Y, HFE_Z]))
    return c


def build(bore_clr=BORE_CLR):
    import check_fit as cf  # noqa: F401  (path/seeding side of the gate suite)
    orig = trimesh.load('coax_R.stl')
    cap = trimesh.load('coax_hfe_plate.stl')
    outer = _box(SPLIT_X, 80, -60, 60, -60, 60)

    block = trimesh.boolean.union([
        trimesh.boolean.intersection([orig, outer]),
        _axial_cyl(BOSS_R, BOSS_X0, SPLIT_X),
        _box(MORT['x0'] + CLR, SPLIT_X, MORT['y0'] + CLR, MORT['y1'] - CLR,
             MORT['z0'] + CLR, MORT['z1'] - CLR)])

    coax = trimesh.boolean.union([orig, cap])
    coax = trimesh.boolean.difference([coax, outer])
    coax = trimesh.boolean.difference(
        [coax, _axial_cyl(BOSS_R + bore_clr, BOSS_X0 - 2, SPLIT_X + 2)])
    coax = trimesh.boolean.union(
        [coax, _box(GROW_X0, SPLIT_X, -4.4, 27.6, 13.4, GROW_Z1)])
    coax = trimesh.boolean.difference(
        [coax, _box(**MORT)])
    return coax, block


def _seated(cf):
    femur = trimesh.load('femur_R.stl')
    arm = trimesh.load('knee_arm.stl')
    arm.apply_transform(trimesh.transformations.translation_matrix([59, 0, 17.75]))
    pts0 = cf.sample_points(cf.servo_mesh())
    asm = np.vstack([trimesh.sample.sample_surface(femur, 8000, seed=0)[0],
                     trimesh.sample.sample_surface(arm, 2000, seed=0)[0],
                     trimesh.transform_points(pts0, cf.rot_z180())])
    M = (trimesh.transformations.translation_matrix([33.8, 11.6, -9.5])
         @ cf.rot_z180()
         @ trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    return trimesh.transform_points(asm, M), M


def _free_axes(cf, pts, obstacles):
    out = []
    for lab, d in DIRS:
        v = np.array(d, float)
        if not any(int(cf.contains_chunked(o, pts + v * t).sum())
                   for o in obstacles for t in range(2, 52, 2)):
            out.append(lab)
    return out


def evaluate(cf, bore_clr, quiet=False):
    coax, block = build(bore_clr)
    seated, M = _seated(cf)
    femur = trimesh.load('femur_R.stl'); femur.apply_transform(M)
    srv = cf.servo_mesh().copy(); srv.apply_transform(M @ cf.rot_z180())
    bpts = trimesh.sample.sample_surface(block, 12000, seed=0)[0]

    femur_free = _free_axes(cf, seated, [coax])
    block_free = _free_axes(cf, bpts, [coax, femur, srv])
    inter = trimesh.boolean.intersection([block, coax])
    overlap = inter.volume if inter is not None and len(inter.faces) else 0.0
    if not quiet:
        print(f'   coax {coax.volume/1000:6.2f} cm3 (watertight={coax.is_watertight})'
              f'   block {block.volume/1000:5.2f} cm3 (watertight={block.is_watertight})')
        print(f'   femur free axes: {femur_free or "NONE"}')
        print(f'   block free axes: {block_free or "NONE"}')
        print(f'   assembled interpenetration: {overlap:.2f} mm3')
    return bool(femur_free) and bool(block_free) and abs(overlap) < 1.0


def main() -> int:
    import check_fit as cf
    print(f'-- option C joint proof (bore clearance {BORE_CLR} mm) --')
    ok = evaluate(cf, BORE_CLR)
    print(f'   -> {"WORKS" if ok else "FAILS"}\n')

    # NEGATIVE CONTROL, and not a hypothetical one: built first with the coax
    # bore at the SAME radius as the block boss. The two graze at r 9.47..9.49
    # and BOTH the femur and the block read trapped -- a real result that looked
    # exactly like an architectural failure until the radii were printed.
    print('-- negative control: bore == boss radius (no clearance) --')
    bad = evaluate(cf, 0.0)
    print(f'   -> {"WORKS (control did not bite -- harness suspect)" if bad else "FAILS as expected"}')

    if not ok:
        print('\nFAIL: the joint geometry does not close.')
        return 1
    if bad:
        print('\nFAIL: the negative control passed, so the proof above is not '
              'discriminating.')
        return 1
    print('\nOK: joint closes with clearance, fails without it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
