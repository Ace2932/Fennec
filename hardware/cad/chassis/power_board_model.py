#!/usr/bin/env python3
"""Build power_board_model.stl — a faithful 3D model of the NOVA power PCB
(nova_pcb_v6_power_v2), positioned in the robot's TRUNK frame. Replaces the
plain `box(-59.5, 52.5, -45, 45, 6.0, 64.0)` stack-envelope placeholder in
preview_assembly.py:153 with real per-component geometry, so chassis
fitment (riser deck clearance above, floor-plate clearance below, buck-card
pocket) can be checked against the actual board instead of a guess.

Every populated footprint is parsed straight out of the live .kicad_pcb
(reference designator, board-local placement, F.Cu/B.Cu side, and — where
drawn — the KiCad courtyard (CrtYd) rectangle, which gives an accurate XY
footprint envelope without hand-guessing part dimensions). Each footprint is
extruded into a box (or a cylinder for round THT parts, matching the D<n>mm
diameter baked into the footprint's library name) up from the board-top
face (F.Cu / TOP side) or down from the board-bottom face (B.Cu / BOTTOM
side), by the height assigned in HEIGHT_MM below. The 5 off-board Pololu
buck-converter card bodies (which sit in the pocket UNDER the board, wired
to the U1-U5 landing pads rather than living directly on them) are added
separately.

Run standalone to export the STL, the connector-position JSON, and print
the fitment pre-flags:
  ../../../.venv/bin/python power_board_model.py
"""
import json
import re

import trimesh

T = trimesh.transformations.translation_matrix

NOVA = '/Users/afox/codebases/NOVA'
PCB_FILE = (f'{NOVA}/proj/hardware/pcb-mods/nova_pcb_v6_power_v2/'
            'nova_pcb_v6_power_v2.kicad_pcb')

# ---- verified board <-> trunk placement transform (do NOT re-derive) ------
# trunk_x = local_x - TRUNK_DX ; trunk_y = local_y - TRUNK_DY ; no rotation.
# Board-local span X:84-196, Y:51-141 -> trunk exactly (-59.5..52.5, -45..45),
# i.e. the bare slab reproduces the old envelope box's XY footprint exactly.
TRUNK_DX, TRUNK_DY = 143.5, 96.0
BOARD_THK = 1.62

# ---- stack geometry (trunk frame) used for the fitment pre-flags ----------
FLOOR_TOP_Z = 6.0            # floor plate top face (BOTTOM components must stay above this)
RISER_UNDERSIDE_Z = 67.9     # riser deck underside (TOP components must stay below this)
OLD_ENVELOPE = dict(x=(-59.5, 52.5), y=(-45.0, 45.0), z=(6.0, 64.0))  # preview_assembly.py:153

# ---- floor->power-board standoff (CHASSIS-SIDE, parametric) ---------------
# The board + every populated component is ALREADY ORDERED/FAB'D and cannot
# change (locked BOM). The floor->power standoff is the one free chassis
# dimension. Set to 20mm to match the M3x20 brass standoffs already ON HAND
# (order reconciliation, memory project-power-board-arm-phase4 2026-06-14).
# The bottom-side 1000uF caps (C1-C5) are the real ordered part Ø10x17mm
# (NOT the 20mm generic an early modeling pass assumed) on a Ø12.5 THT land;
# at a 20mm standoff their bottoms sit at z9, clearing the floor plate top
# (FLOOR_TOP_Z=6) by 3.0mm. floor_plate.scad's original 16mm spec was 1mm
# short of the 17mm cans (the same order note flagged "1mm over the 16mm
# spec") -- corrected here and there to the 20mm hardware. Do NOT re-derive
# this from a hardcoded value elsewhere; every board-plane Z below flows
# from this one constant.
STANDOFF_FLOOR_MM = 20.0
# Power board -> logic board standoff, UNCHANGED from the original 2-board
# mezzanine spec (README.md "Mezzanine stack" section) -- not part of this
# fix, but exported here so preview_assembly.py derives the logic-board
# plane from the same single source instead of a second hardcoded number.
STANDOFF_PB_LB_MM = 20.0

BOARD_BOTTOM_Z = FLOOR_TOP_Z + STANDOFF_FLOOR_MM   # 26.0 at 20mm standoff
BOARD_TOP_Z = BOARD_BOTTOM_Z + BOARD_THK           # 27.62

# ---- upper stack: logic board + Teensy, COMPONENT-SIDE UP -----------------
# Teensy 4.1 + USB face UP toward the removable riser deck (resolves the
# earlier "lid-off service" concern; corrects a prior side-down/ambiguous
# modeling pass and a matching README.md error). Centralized here (rather
# than re-hardcoded in preview_assembly.py / check_fit.py) so both derive
# the logic-board plane and stack ceiling from one source. Not part of the
# 22mm standoff fix -- spec unchanged -- but the logic-board plane now
# floats strictly off BOARD_TOP_Z + STANDOFF_PB_LB_MM rather than being
# pinned to clear Q1's height by construction, so Q1 clearance is instead
# an explicit check_fit.py case-11 assertion.
LOGIC_BOARD_THK = 1.6      # generic 2-layer PCB thickness (matches power board ~1.62)
# ESTIMATE -- caliper-confirm before finalizing the standoff length:
# socketed Teensy 4.1 (2x24 socket footprint) + USB-connector envelope
# height above the logic board's TOP (component) face.
TEENSY_ENVELOPE_H = 14.0
LOGIC_BOARD_Z0 = BOARD_TOP_Z + STANDOFF_PB_LB_MM     # 47.62 -- logic board underside
LOGIC_BOARD_Z1 = LOGIC_BOARD_Z0 + LOGIC_BOARD_THK    # 49.22 -- logic board top (component face)
STACK_TOP_Z = LOGIC_BOARD_Z1 + TEENSY_ENVELOPE_H     # 63.22 -- Teensy/USB envelope top


def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box between corners — same helper idiom as preview_assembly.py."""
    return trimesh.creation.box(
        extents=[x1 - x0, y1 - y0, z1 - z0],
        transform=T([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]))


# ---- component height table (mm) -------------------------------------------
# TOP side (F.Cu) extrudes UP from BOARD_TOP_Z; BOTTOM (B.Cu) extrudes DOWN
# from BOARD_BOTTOM_Z. Values per the verified BOM/mechanical survey.
HEIGHT_MM = {
    'J1': 15,      # XT60 battery in
    'Q1': 18,      # IRLB3034 TO-220 vertical
    **{r: 12 for r in ('J3', 'J4', 'J5', 'J6', 'J7', 'J12', 'J13', 'J14')},  # XT30 conns
    **{r: 12 for r in ('U1', 'U2', 'U3', 'U4', 'U5')},   # buck wire-terminal landings
    **{r: 11 for r in ('U9', 'U10', 'U11', 'U12')},      # INA226 modules
    'C8': 13, 'C9': 13,      # F.Cu D10 radial caps
    'J8': 8,       # servo-bus JST-XH
    'J20': 9,      # IDC 2x6 header
    'J2': 8, 'M1': 8,        # pin headers
    # NOT in the spec's height table: SW1/SW2 are TerminalBlock_Philmore
    # TB132 pads (Value="Rocker_30A"/"Estop_NC_latching") — same off-board
    # wire-terminal-landing pattern as the U1-U5 buck pads and the XT30
    # connectors (the real rocker switch / E-stop body is NOT on this board;
    # the E-stop is already modeled separately at the control pod in
    # preview_assembly.py). Estimated at the XT30-landing height — flag for
    # verification against the physical TB132 part if precise clearance to
    # the deck above ever matters.
    'SW1': 10, 'SW2': 10,
    # BOTTOM side
    # C1-C5 real ordered part = 1000uF/25V Ø10x17mm cans (memory arm-phase4
    # order note 2026-06-14) on a Ø12.5 THT land; 17mm sets the floor margin.
    **{r: 17 for r in ('C1', 'C2', 'C3', 'C4', 'C5')},   # D12.5 land, Ø10x17 can
    'C6': 13,      # D10 radial cap
    'L1': 8,       # SMD inductor
    'U8': 2, 'Q2': 2, 'Q3': 2, 'Q4': 2,   # SOIC-8 / SOT-23, negligible
}
DEFAULT_HEIGHT = 2.0   # unlisted small SMD (0603 R/C, SOD-123 diode, etc.)

# Radial THT caps draw no KiCad courtyard rectangle (round body) — diameter
# is read straight off the footprint library name instead:
#   "Capacitor_THT:CP_Radial_D12.5mm_P5.00mm" -> 12.5mm
ROUND_FOOTPRINT_RE = re.compile(r'CP_Radial_D([\d.]+)mm')

# 5 off-board Pololu buck-converter card bodies, in the pocket BELOW the
# board (floor z6 -> board-bottom z26, a 20mm pocket at STANDOFF_FLOOR_MM)
# near each U1-U5 landing's XY. Sized per spec (~30x20x14mm); modeled flush
# against the board underside (z1=BOARD_BOTTOM_Z) since the landing pads
# wire straight down into the card — this z-placement is a modeling
# choice, not a measured dimension, and leaves ~8mm clearance to the floor
# plate (was ~2mm at the old 16mm standoff).
BUCK_CARD_XY = (30.0, 20.0)
BUCK_CARD_H = 14.0
BUCK_REFS = ('U1', 'U2', 'U3', 'U4', 'U5')

CONNECTOR_PREFIXES = ('J', 'SW')   # what the downstream reachability check wants


# ---- .kicad_pcb parsing -----------------------------------------------------
_FP_LINE_RE = re.compile(
    r'\(fp_line\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\).*?'
    r'\(layer "([^"]+)"\)', re.S)
_FP_RECT_RE = re.compile(
    r'\(fp_rect\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\).*?'
    r'\(layer "([^"]+)"\)', re.S)


def _parse_footprints(pcb_path=PCB_FILE):
    """Extract every footprint's ref, side, board-local placement, courtyard
    bbox (footprint-local mm, pre-rotation) and (for round THT parts) body
    diameter from the live .kicad_pcb. Returns a list of dicts."""
    with open(pcb_path) as f:
        text = f.read()
    starts = [m.start() for m in re.finditer(r'\n\t\(footprint "', text)]
    starts.append(len(text))

    out = []
    for i in range(len(starts) - 1):
        block = text[starts[i]:starts[i + 1]]
        name_m = re.match(r'\n\t\(footprint "([^"]+)"', block)
        layer_m = re.search(r'\(layer "([^"]+)"\)', block)
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', block)
        val_m = re.search(r'\(property "Value" "([^"]*)"', block)
        at_m = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', block)
        if not (name_m and layer_m and ref_m and at_m):
            continue   # not a real footprint block (shouldn't happen)
        x, y = float(at_m.group(1)), float(at_m.group(2))
        rot = float(at_m.group(3) or 0)

        xs, ys = [], []
        for rex in (_FP_LINE_RE, _FP_RECT_RE):
            for m in rex.finditer(block):
                if 'CrtYd' in m.group(5):
                    xs += [float(m.group(1)), float(m.group(3))]
                    ys += [float(m.group(2)), float(m.group(4))]
        crtyd = (max(xs) - min(xs), max(ys) - min(ys)) if xs else None

        round_m = ROUND_FOOTPRINT_RE.search(name_m.group(1))
        diameter = float(round_m.group(1)) if round_m else None

        out.append(dict(ref=ref_m.group(1), footprint=name_m.group(1),
                         value=val_m.group(1) if val_m else '',
                         layer=layer_m.group(1), x=x, y=y, rot=rot,
                         crtyd=crtyd, diameter=diameter))
    return out


def _swapped(rot):
    """True if this footprint's Z rotation is +-90 deg. Every rotation on
    this board is a multiple of 90 deg, so a rotated rectangle's trunk-frame
    X/Y extents are just its local courtyard w/h swapped."""
    return round(abs(rot)) % 180 == 90


def _footprint_xy_extent(fp):
    """(x_extent, y_extent) in trunk axes, after Z rotation."""
    if fp['diameter'] is not None:
        return fp['diameter'], fp['diameter']
    if fp['crtyd'] is None:
        return DEFAULT_HEIGHT, DEFAULT_HEIGHT   # tiny unlisted part, no courtyard drawn
    w, h = fp['crtyd']
    return (h, w) if _swapped(fp['rot']) else (w, h)


def _component_mesh(fp):
    height = HEIGHT_MM.get(fp['ref'], DEFAULT_HEIGHT)
    tx, ty = fp['x'] - TRUNK_DX, fp['y'] - TRUNK_DY
    xw, yw = _footprint_xy_extent(fp)
    top_side = fp['layer'] == 'F.Cu'
    if top_side:
        z0, z1 = BOARD_TOP_Z, BOARD_TOP_Z + height
    else:
        z0, z1 = BOARD_BOTTOM_Z - height, BOARD_BOTTOM_Z

    if fp['diameter'] is not None:
        m = trimesh.creation.cylinder(
            radius=fp['diameter'] / 2, height=height,
            transform=T([tx, ty, (z0 + z1) / 2]))
    else:
        m = box(tx - xw / 2, tx + xw / 2, ty - yw / 2, ty + yw / 2, z0, z1)

    info = dict(ref=fp['ref'], x=tx, y=ty, z0=z0, z1=z1, top_side=top_side)
    return m, info


def _buck_card_meshes(fps_by_ref):
    bw, bd = BUCK_CARD_XY
    out = []
    for ref in BUCK_REFS:
        fp = fps_by_ref[ref]
        tx, ty = fp['x'] - TRUNK_DX, fp['y'] - TRUNK_DY
        xw, yw = (bd, bw) if _swapped(fp['rot']) else (bw, bd)
        z1 = BOARD_BOTTOM_Z
        z0 = z1 - BUCK_CARD_H
        out.append(box(tx - xw / 2, tx + xw / 2, ty - yw / 2, ty + yw / 2, z0, z1))
    return out


def power_board_mesh(pcb_path=PCB_FILE):
    """Return (mesh, components): a single trimesh of the power board — slab
    + every populated footprint extruded to its component height + the 5
    off-board buck-card bodies — in TRUNK frame. `components` is the
    per-part placement list (ref, trunk x/y, z0/z1, side) used for the
    fitment report and the connector JSON; it excludes the slab itself and
    MountingHole footprints (through-holes, no body)."""
    fps = _parse_footprints(pcb_path)
    fps_by_ref = {fp['ref']: fp for fp in fps}

    # Board slab: local X 84-196, Y 51-141 -> trunk exactly the old
    # envelope's XY footprint (-59.5..52.5, -45..45).
    slab = box(84 - TRUNK_DX, 196 - TRUNK_DX, 51 - TRUNK_DY, 141 - TRUNK_DY,
               BOARD_BOTTOM_Z, BOARD_TOP_Z)

    parts = [slab]
    components = []
    for fp in fps:
        if fp['footprint'].startswith('MountingHole:'):
            continue   # M3 clearance hole, no body
        m, info = _component_mesh(fp)
        parts.append(m)
        components.append(info)
    parts += _buck_card_meshes(fps_by_ref)

    mesh = trimesh.util.concatenate(parts)
    return mesh, components, fps_by_ref


def _fitment_report(mesh, components):
    tops = [c for c in components if c['top_side']]
    bots = [c for c in components if not c['top_side']]
    tallest = max(tops, key=lambda c: c['z1'])
    lowest = min(bots, key=lambda c: c['z0'])
    print(f"tallest TOP component: {tallest['ref']} z_top={tallest['z1']:.2f}")
    print(f"lowest BOTTOM component: {lowest['ref']} z_bottom={lowest['z0']:.2f}")

    # (a) riser deck clearance
    over = [c for c in tops if c['z1'] > RISER_UNDERSIDE_Z]
    margin_a = RISER_UNDERSIDE_Z - tallest['z1']
    print(f"(a) riser clearance (top z < {RISER_UNDERSIDE_Z}): "
          f"{'VIOLATION' if over else 'OK'} — max top z={tallest['z1']:.2f} "
          f"({tallest['ref']}), margin={margin_a:.2f}mm"
          + (f", offenders={[c['ref'] for c in over]}" if over else ''))

    # (b) floor plate clearance
    under = [c for c in bots if c['z0'] < FLOOR_TOP_Z]
    excursion_b = FLOOR_TOP_Z - lowest['z0']
    print(f"(b) floor clearance (bottom z > {FLOOR_TOP_Z}): "
          f"{'VIOLATION' if under else 'OK'} — min bottom z={lowest['z0']:.2f} "
          f"({lowest['ref']}), excursion={excursion_b:.2f}mm"
          + (f", offenders={[c['ref'] for c in under]}" if under else ''))

    # (c) old envelope box excursion, per face (0 = fully within)
    (bx0, bx1), (by0, by1), (bz0, bz1) = (OLD_ENVELOPE['x'], OLD_ENVELOPE['y'],
                                           OLD_ENVELOPE['z'])
    lo, hi = mesh.bounds
    exc = dict(
        x_min=max(0.0, bx0 - lo[0]), x_max=max(0.0, hi[0] - bx1),
        y_min=max(0.0, by0 - lo[1]), y_max=max(0.0, hi[1] - by1),
        z_min=max(0.0, bz0 - lo[2]), z_max=max(0.0, hi[2] - bz1),
    )
    print('(c) excursion beyond old envelope box '
          f'{OLD_ENVELOPE} per face (mm, 0.00 = within):')
    for k, v in exc.items():
        print(f'    {k}: {v:.2f}')

    return dict(tallest_top=tallest['ref'], lowest_bottom=lowest['ref'],
                riser_ok=not over, floor_ok=not under, excursion=exc)


def _connector_json(components, fps_by_ref):
    conns = []
    for c in components:
        if not c['ref'].startswith(CONNECTOR_PREFIXES):
            continue
        fp = fps_by_ref[c['ref']]
        conns.append(dict(
            ref=c['ref'], value=fp['value'],
            x=round(c['x'], 3), y=round(c['y'], 3),
            z_top=round(c['z1'] if c['top_side'] else c['z0'], 3),
            face='up' if c['top_side'] else 'down',
        ))
    conns.sort(key=lambda c: c['ref'])
    return conns


def main():
    mesh, components, fps_by_ref = power_board_mesh()

    print('power_board_model.stl bbox (trunk mm):', mesh.bounds.round(2).tolist())
    print(f'trimesh stats: vertices={len(mesh.vertices)} faces={len(mesh.faces)} '
          f'watertight={mesh.is_watertight} '
          + (f'volume={mesh.volume:.1f}mm^3' if mesh.is_watertight else ''))

    _fitment_report(mesh, components)

    conns = _connector_json(components, fps_by_ref)
    out_json = 'power_board_connectors_trunk.json'
    with open(out_json, 'w') as f:
        json.dump(conns, f, indent=2)
    print(f'{out_json}: {len(conns)} connectors written')

    out_stl = 'power_board_model.stl'
    mesh.export(out_stl)
    print(f'{out_stl} exported')


if __name__ == '__main__':
    main()
