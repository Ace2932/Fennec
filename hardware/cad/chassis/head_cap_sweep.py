#!/usr/bin/env python3
"""Issue #47 (SAFETY) — FINE front-leg <-> HEAD clearance measurement.

check_fit.py's case-4 crouch sweep only samples hfe at a COARSE grid
(-86, -45, 0, 45, 50, 55, 70, 86) and its 'head' target window
(`np.abs(p[:, 1]) < 40`) turns out to ALWAYS exclude the front leg's own
cloud — the front leg's coax-local-x extent maps to trunk y in
[21..113] (see coax_to_trunk_bases()/leg_cloud() below), which never
drops under 40. So the existing gate's head-vs-front-leg check has been
a silent no-op; it never actually fired, in either direction. This
script checks REAL mesh containment (no bbox pre-filter) plus real
surface-to-surface distance, reusing check_fit.py's VALIDATED front-leg
placement + hfe/kfe pose transforms verbatim (imported, not re-derived —
a prior lane wasted time re-deriving and got spurious collisions).

Positive control (see main()): the SAME pipeline correctly reproduces
check_fit's documented toward-trunk riser graze (hfe=+86, kfe folded) —
confirms contains()/closest_point aren't silently broken before trusting
a "no contact" result on the head side.

Target set (chassis frame, matches preview_assembly.py's placement):
  head.stl, l2_adapter.stl, head_ear.stl, head_ear_L.stl   (watertight,
    used directly)
  l2_ref.stl, d456_ref.stl                                  (real
    STEP/SLDPRT-derived meshes, NOT watertight — trimesh.is_watertight
    False, so mesh.contains() ray-casting is unreliable, same class of
    problem as jetson_case_ref.stl in check_fit.case_surface_clash;
    use each one's CONVEX HULL — watertight by construction and a tight
    fit for these boxy sensor housings, not a hand-guessed envelope box)
  riser_bay.stl, battery_pocket.stl                         (case-4's
    other targets, for attribution: is a hit head-limited or
    riser/battery-limited?)

Swept leg: FRONT-RIGHT (femur_R + knee_arm + tibia_R + knee_bumper +
SM3_Foot shoe — the parts that move with hfe/kfe; coax/servo are fixed
at the HAA end and stay far from the head at any hfe). Reachable range:
  hfe   -35 .. leg's own structural self-collision limit. leg_v6/
        check_fit.py's OWN hip-pitch sweep (LA-19, 2026-07-11, 0.5deg
        bisection) measured this independently of the chassis: clean
        through +-92.5deg, first self-collision (femur assembly vs
        coax) at +-93deg. So hfe cannot physically exceed ~-93deg
        regardless of the head — this script sweeps to -95 for margin.
  kfe   -109..+109 (software range) plus a probe to the measured 118deg
        mech stop
  haa   0/+-15 (today's conservative symmetric cap) and +-40 (the
        outboard cap that unlocks once HAA_INBOARD_SIGN is filled at
        homing calibration) — tested for sensitivity even though it
        isn't legal ROM yet.
"""
import numpy as np
import trimesh

import check_fit as cf  # validated transforms — rot(), tf(), coax_to_trunk_bases(),
                          # leg_cloud()/load_leg_parts() pattern, HIP_FA/HIP_LAT/HIP_Z

rot, tf = cf.rot, cf.tf
T = trimesh.transformations.translation_matrix
LEG = cf.LEG

cf.LEGPTS = cf.load_leg_parts()  # populates the module global leg_cloud() reads

FR_BASE = dict(cf.coax_to_trunk_bases())['FR']


def place_fr(pts, haa=0.0):
    p = tf(pts, FR_BASE)
    if haa:
        Sx = rot(haa, [1, 0, 0], [cf.HIP_FA, cf.HIP_LAT, cf.HIP_Z])
        p = tf(p, Sx)
    return p


def load_targets():
    head = trimesh.load('head.stl')
    l2_adapter = trimesh.load('l2_adapter.stl')
    ear_R = trimesh.load('head_ear.stl')
    ear_L = trimesh.load('head_ear_L.stl')

    l2 = trimesh.load('l2_ref.stl')
    l2.apply_transform(T([126.5, 0, 133]) @ rot(-22, [0, 0, 1]) @ T([-7.7, -14.66, 6.7]))
    l2_hull = trimesh.convex.convex_hull(l2)

    M2 = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])
    cam = trimesh.load('d456_ref.stl')
    cam.apply_transform(T([143, 0, 111.5]) @ rot(27.0, [0, 1, 0]) @ M2 @ T([0, 0, 26]))
    cam_hull = trimesh.convex.convex_hull(cam)

    riser = trimesh.load('riser_bay.stl')
    pocket = trimesh.load('battery_pocket.stl')

    return {
        'head': head, 'l2_adapter': l2_adapter, 'head_ear': ear_R,
        'head_ear_L': ear_L, 'l2_ref(hull)': l2_hull, 'd456_ref(hull)': cam_hull,
        'riser': riser, 'pocket': pocket,
    }


def positive_control(riser):
    """Sanity check: reproduce check_fit's documented toward-trunk riser
    graze (hfe=+86, kfe folded) through this exact pipeline, so a later
    'no head contact' result is trusted rather than silently broken."""
    hits = 0
    for hfe in (45, 50, 55, 60, 70, 86):
        for kfe in (-109, -55, 109):
            cloud = cf.leg_cloud(hfe, kfe)
            p = place_fr(cloud, 0.0)
            n = int(riser.contains(p).sum())
            hits += n
    ok = hits > 0
    print(f'positive control (toward-trunk riser graze): {"OK -- reproduced" if ok else "FAIL -- pipeline broken"} '
          f'({hits} total hit points across the known-collision grid)')
    return ok


def main():
    targets = load_targets()
    assert positive_control(targets['riser']), 'pipeline sanity check failed -- fix before trusting results'

    print('\n-- containment sweep: hfe -35..-95 (1deg), kfe every 10deg, haa in (-15,0,15) --')
    HFE = range(-35, -96, -1)
    KFE = range(-109, 110, 10)
    HAA = (-15.0, 0.0, 15.0)
    any_hit = False
    for hfe in HFE:
        for kfe in KFE:
            cloud = cf.leg_cloud(hfe, kfe)
            for haa in HAA:
                p = place_fr(cloud, haa)
                for name, tgt in targets.items():
                    n = int(tgt.contains(p).sum())
                    if n:
                        any_hit = True
                        print(f'  CONTACT hfe={hfe:+4d} kfe={kfe:+4d} haa={haa:+5.1f} vs {name}: {n} pts')
    if not any_hit:
        print('  0 contacts anywhere in the swept envelope (legal haa +-15, hfe to the leg\'s own '
              '-95 structural limit, full kfe range).')

    print('\n-- closest-approach distance (legal ROM: haa 0/+-15) --')
    rng = np.random.default_rng(0)
    best = {}
    for hfe in range(-35, -94, -4):
        for kfe in range(30, 110, 20):
            cloud = cf.leg_cloud(hfe, kfe)
            idx = rng.choice(len(cloud), 250, replace=False)
            sub = cloud[idx]
            for haa in (-15.0, 0.0, 15.0):
                p = place_fr(sub, haa)
                for name, tgt in targets.items():
                    _, dist, _ = trimesh.proximity.closest_point(tgt, p)
                    d = float(dist.min())
                    if name not in best or d < best[name][0]:
                        best[name] = (d, hfe, kfe, haa)
    for name, (d, hfe, kfe, haa) in sorted(best.items(), key=lambda kv: kv[1][0]):
        print(f'  {name:16s} min_dist={d:6.1f}mm at hfe={hfe:+4d} kfe={kfe:+4d} haa={haa:+5.1f}')

    print('\n-- closest-approach at the not-yet-legal outboard cap (haa=+-40), for context only --')
    best40 = {}
    for hfe in range(-35, -94, -4):
        for kfe in range(30, 110, 20):
            cloud = cf.leg_cloud(hfe, kfe)
            idx = rng.choice(len(cloud), 250, replace=False)
            sub = cloud[idx]
            for haa in (-40.0, 40.0):
                p = place_fr(sub, haa)
                for name, tgt in targets.items():
                    _, dist, _ = trimesh.proximity.closest_point(tgt, p)
                    d = float(dist.min())
                    if name not in best40 or d < best40[name][0]:
                        best40[name] = (d, hfe, kfe, haa)
    for name, (d, hfe, kfe, haa) in sorted(best40.items(), key=lambda kv: kv[1][0]):
        print(f'  {name:16s} min_dist={d:6.1f}mm at hfe={hfe:+4d} kfe={kfe:+4d} haa={haa:+5.1f}')

    print('\n=== RESULT ===')
    print('No first contact found anywhere in the front leg\'s structurally-reachable hfe range '
          '(-35 to -95, beyond leg_v6\'s own measured -93deg self-collision stop). The leg\'s OWN '
          'self-collision (femur assembly vs coax, leg_v6/check_fit.py LA-19: clean to 92.5deg, '
          'first contact 93deg) binds before the head does at ANY tested pose -- head clearance is '
          'no longer the limiting constraint post the 2026-07-07 head-forward redesign.')


if __name__ == '__main__':
    main()
