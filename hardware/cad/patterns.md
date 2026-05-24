# NovaSM3 Patterns

Project-specific CAD macros + tolerances for the **NovaSM3 quadruped** build.
Sibling to `robotics_patterns.md` (general primitives); this file pins values
to NovaSM3 reality — Bambu P1S printer, PA6-CF / PETG-CF / TPU 95A materials,
specific connectors and modules in the BOM.

When designing NovaSM3 parts, import from here first; fall back to
`robotics_patterns.md` only for primitives not specialized below.

## Skill Scope vs OnShape

This skill (CadQuery + preview loop) is for **utility parts**:

- Cable guides, sensor adapters, mount brackets, panel cutouts
- Print-test coupons, fit-test jigs
- Foot pads, strain reliefs, spacers
- PCB carriers, riser towers, connector pockets
- Anything single-body or single-assembly that doesn't need full
  kinematic constraints

**Use OnShape (not this skill) for:**

- Leg-joint kinematic stack (hip + femur + tibia multi-body assemblies)
- Anything where mate relationships drive geometry
- Anything that needs IK / joint-limit verification before printing

NovaSM3 leg redesign lives in `~/codebases/NOVA/nova_sts3215_redesign/`
(OpenSCAD source) and the OnShape workspace. **Do not re-derive leg
kinematics in CadQuery** — wrong tool for the job. Import the OnShape
STEP into CadQuery only if you need to attach a utility bracket to it.

All dimensions in **mm**. All snippets assume:

```python
import cadquery as cq
```

---

## Table of Contents

1. Printer + Material Profile (Bambu P1S, PA6-CF / PETG-CF / TPU)
2. NovaSM3 Calibration Constants
3. STS3215 Servo Pocket with Back-Shaft U-Bracket
4. LiPo Battery Pocket (4S 4000mAh + XT60)
5. Power Connector Cutouts (XT60, XT30)
6. Panel Cutouts (E-stop, RJ-45, USB 3.1, Barrel Jack)
7. Signal Connector Pockets (JST-XH 2.54)
8. Sensor Mounts (RealSense D456, MPU-6050, L2 LiDAR riser)
8b. Foot Pads + Strain Relief (TPU 95A)
9. PCB Mounts (Teensy 4.1, Arduino Nano, INA226 module)
10. Leg Rail Star-Injection Pattern
10b. Pololu Buck Module Footprint (D42V110 / D24V22 / D42V55)
10c. LC Filter Carrier Pocket (L2 LiDAR rail)
10d. Jetson Orin Nano Antenna Mount (P3766 WiFi 5 + BT 5.1 pair)
10e. WS2812B Status LED Strip Mount
10f. Servo Zero-Position Calibration Jig
11. Workflow Rules (first-article gate, fiber orientation)

---

## 1. Printer + Material Profile

**Printer:** Bambu Lab P1S, **AMS HF bypassed** for the structural workflow.
Build volume **256 × 256 × 256 mm**. 0.4 mm hardened steel nozzle (brass
dies in < 1 spool of CF); 0.6 mm available for PA6-CF if surface finish
acceptable.

**Filament feed path:** Creality SpacePi X4 (dual-chamber, 45-85 °C, 4 spools,
1-48 h timer) → 4 mm PTFE Bowden tube → P1S top-side filament input. PA6-CF
**stays in the dryer chamber during the print** so it doesn't re-absorb
moisture from room air. AMS HF would hold spools in an unheated chamber and
hygroscopic PA6-CF would re-wet within hours, defeating the 24 h pre-dry.
AMS is reserved for future PLA/PETG multicolor work where moisture isn't
critical.

```python
# Bambu P1S build envelope
build_x = 256.0
build_y = 256.0
build_z = 256.0
nozzle_d = 0.4

# Material profiles (nozzle / bed / chamber / drier hours)
MATERIALS = {
    "PA6-CF":  {"nozzle": 280, "bed": 100, "chamber": "enclosed",
                "drier_h": 24, "use": "high-stress structural (leg links, hip)"},
    "PETG-CF": {"nozzle": 250, "bed":  80, "chamber": "enclosed",
                "drier_h": 12, "use": "secondary brackets, mounts"},
    "PETG":    {"nozzle": 240, "bed":  70, "chamber": "open",
                "drier_h":  4, "use": "accent / cable clips"},
    "TPU 95A": {"nozzle": 230, "bed":  60, "chamber": "open",
                "drier_h":  6, "use": "bumpers, gaskets, strain relief"},
    "PLA":     {"nozzle": 220, "bed":  60, "chamber": "open",
                "drier_h":  0, "use": "fit-test coupons, mockups"},
}
```

**PA6-CF specifics (default for structural parts):**

- Pre-print drier: 24 h minimum at 70 °C in SpacePi X4. Keep dryer running
  at 60-70 °C **during** the print with Bowden feed routed straight to the
  P1S input. Do NOT load PA6-CF into the AMS — chamber is unheated, spool
  rewets in hours.
- Bed adhesion: **Magigoo PA** on textured PEI. **Bambu liquid glue is NOT
  rated for PA / PA-CF** — Bambu product page lists PLA/ABS/PETG/ASA/TPU/PET
  only. Bambu wiki PA6-CF guide explicitly calls for PA-specific glue stick.
- Bed soak: 15 min at 100 °C before first layer.
- Speed cap: ≤ 100 mm/s. CF abrades the nozzle — **hardened steel nozzle
  mandatory** (brass nozzle dies in < 1 spool of CF).
- Shrinkage: ~0.5 % linear (similar to ABS). Critical-fit bores need
  scale comp or post-print ream.
- **Infill: 100 %** on load-bearing parts. Walking-gait impact transients
  fatigue partial infill within weeks.
- **Fiber alignment > infill %.** CF fibers align with extrusion flow.
  30 % infill with smart orientation beats 100 % printed wrong. Walls +
  top/bottom layers count more than infill density for stiffness.
- Orient load-bearing parts so layer lines are **NOT** perpendicular to
  load axis. Layer adhesion is the weak axis on FDM. Hip pocket prints
  upright so servo body load presses *along* layers, not pulling them
  apart.

**TPU 95A specifics:**

- AMS auto-cut is a moot point — AMS isn't in the feed path on this build.
  Load TPU directly into SpacePi X4 chamber + Bowden to P1S. Manual spool
  swap when switching from PA6-CF / PETG-CF chamber to TPU chamber.
- Slow print: 20-30 mm/s. P1S Bowden tube works with retraction tuning,
  external Bowden adds another 30-60 cm of soft TPU to compensate for —
  bump retraction distance slightly vs internal-spool default.
- No support, no overhangs > 45°.
- Dry 4-6 h @ 50 °C in SpacePi X4.

**Print queue strategy:**

- Slowest/biggest first overnight (chassis panels, hip pockets in PA6-CF)
- Small iteration parts during day so you can react to fit issues
- Print test coupon in PLA first to verify geometry before committing
  PA6-CF time + filament

---

## 2. NovaSM3 Calibration Constants

Use these instead of the generic `clr_*` from `robotics_patterns.md` for
NovaSM3 parts. Numbers calibrated for **Bambu P1S + PA6-CF**.

```python
# Press-fit tolerances (PA6-CF on Bambu P1S, 0.4 mm nozzle, 0.2 mm layer)
NOVA_CLR = {
    "slip":       0.35,   # rotating shaft (PA-CF more brittle, more clr)
    "locational": 0.25,   # alignment pin, repeatable
    "press":      0.05,   # bearing OD into PA6-CF
    "interference": 0.05, # boss-bigger-than-bore (use sparingly in PA-CF)
}

# PETG-CF — slightly stickier, less shrink than PA6-CF
PETGCF_CLR = {
    "slip":       0.30,
    "locational": 0.20,
    "press":      0.10,
    "interference": 0.08,
}

# TPU 95A — flex compensates for fit; needs wider clearance
TPU_CLR = {
    "slip":       0.50,
    "locational": 0.40,
    "press":      0.20,  # rarely correct in TPU; usually overconstrains
    "interference": 0.0, # don't try
}

# Heat-set inserts: Ruthex M3 standard (project BOM default)
# Ruthex M3 = 4.0 mm bore, 5.7 mm length. CNC Kitchen M3 = 4.0 mm bore, 4.0 mm.
RUTHEX = {
    "M2":   {"bore": 3.2, "depth": 4.0, "boss_od": 5.5},
    "M2.5": {"bore": 3.6, "depth": 5.0, "boss_od": 6.0},
    "M3":   {"bore": 4.0, "depth": 5.7, "boss_od": 6.5},
    "M4":   {"bore": 5.6, "depth": 8.0, "boss_od": 8.5},
}
```

---

## 3. STS3215 Servo Pocket with Back-Shaft U-Bracket

NovaSM3 uses both front-flange mounting AND a **back-shaft pivot bearing**
on hip joints — the BOM calls out "dual-axis back-shaft U-brackets" in the
leg redesign. Generic pocket from `robotics_patterns.md` is incomplete for
hip use.

**Batch tolerance warning:** STS3215 body dimensions vary **±0.1 mm**
between units (manufacturer spec). Always print a fit-test pocket and
measure-tune before batching 12. First-article protocol:
print pocket nominal → measure servo → adjust by 0.05 mm per iteration
until snug-but-not-forced. Loctite 243 the M3s anyway.

```python
# STS3215 (12V 30kg hip + 7.4V 19kg femur/tibia share the same body)
# Source: Feetech datasheet + on-hand measurement
STS3215 = {
    "body_l":       40.0,
    "body_w":       20.0,
    "body_h":       40.5,
    "flange_l":     54.0,
    "flange_t":     2.5,
    "horn_face_z":  35.5,    # measure on real part — varies ±0.3
    "horn_offset":  9.0,     # output-shaft axis from body midpoint
    "back_shaft_d": 6.0,
    "back_shaft_h": 1.5,
    "mount_screw_d": 2.2,    # M2 self-tapper
    "mount_x_pitch": 49.0,
    "mount_y_pitch": 10.0,
}

def nova_sts3215_dual_mount(workplane, clearance_mat="PA6-CF"):
    """Front-flange pocket + back-shaft U-bracket relief in one operation.
    Used on hip joints where both ends of the servo are supported."""
    clr = NOVA_CLR if clearance_mat == "PA6-CF" else PETGCF_CLR

    # Body pocket
    wp = (workplane
          .rect(STS3215["body_l"] + clr["locational"],
                STS3215["body_w"] + clr["locational"])
          .cutBlind(-(STS3215["body_h"] + clr["slip"])))

    # Front mounting screw pattern (4× M2 self-tapper)
    wp = (wp.faces(">Z").workplane()
          .pushPoints([( STS3215["mount_x_pitch"]/2,  STS3215["mount_y_pitch"]/2),
                       ( STS3215["mount_x_pitch"]/2, -STS3215["mount_y_pitch"]/2),
                       (-STS3215["mount_x_pitch"]/2,  STS3215["mount_y_pitch"]/2),
                       (-STS3215["mount_x_pitch"]/2, -STS3215["mount_y_pitch"]/2)])
          .hole(STS3215["mount_screw_d"]))

    # Back-shaft U-bracket: bearing pocket (688ZZ) on opposite link
    # Caller is responsible for placing this on the mating bracket
    return wp

def nova_sts3215_back_bearing_seat(workplane):
    """688ZZ bearing seat for the back-shaft side of the STS3215.
    Place on the opposing bracket so the rear pivot rotates on a real
    bearing instead of grinding into plastic."""
    # 688ZZ = 8 x 16 x 5; bore takes 6 mm shaft + sleeve adapter
    return (workplane
            .circle((16.0 + NOVA_CLR["press"]) / 2)
            .cutBlind(-5.5))  # 5 mm bearing + 0.5 mm relief
```

---

## 4. LiPo Battery Pocket

Dual 4S 4000mAh packs. Project requires hot-swap capability.

```python
LIPO_4S_4000 = {
    "l": 110.0,      # length (varies by brand ±5 mm)
    "w":  35.0,      # width
    "h":  30.0,      # height
    "wire_relief": 12.0,  # extra slot for balance + XT60 leads
}

def lipo_pocket(workplane, n_packs=2, wall=3.0, strap_slots=True):
    """LiPo pocket with optional velcro-strap pass-through slots.
    n_packs=2 means side-by-side. Wire-relief notch on +X face."""
    pocket_l = LIPO_4S_4000["l"] + 2.0           # length clearance
    pocket_w = (LIPO_4S_4000["w"] + 1.0) * n_packs + (n_packs - 1) * 2.0
    pocket_h = LIPO_4S_4000["h"] + 1.0

    wp = workplane.rect(pocket_l, pocket_w).cutBlind(-pocket_h)

    # Wire-relief notch (XT60 + balance leads exit one end)
    wp = (wp.faces(">Z").workplane()
          .center(pocket_l/2, 0)
          .rect(LIPO_4S_4000["wire_relief"], 16.0)
          .cutThruAll())

    if strap_slots:
        # Two velcro slots across the long axis
        for x_off in (-pocket_l*0.3, pocket_l*0.3):
            wp = (wp.faces(">Z").workplane()
                  .center(x_off, 0)
                  .rect(3.0, pocket_w + 2*wall + 4.0)
                  .cutThruAll())

    return wp
```

---

## 5. Power Connector Cutouts

```python
def xt60_panel_cutout(workplane, panel_t=3.0):
    """XT60 panel-mount female cutout. Snap-tabs grip the panel.
    Panel thickness 2-4 mm works; >4 mm requires longer snap tabs."""
    # XT60 panel-mount nominal: 15.5 x 8.0 mm with 1.5 mm corner radius
    return (workplane
            .rect(15.5, 8.0).cutThruAll())

def xt30_panel_cutout(workplane):
    """XT30 panel-mount. Smaller cousin of XT60. Used at leg-rail star
    injection points and hip rail."""
    # XT30 panel-mount: ~10.0 x 5.5 mm
    return (workplane
            .rect(10.0, 5.5).cutThruAll())

def xt30_inline_pocket(workplane, w=8.0, l=18.0, depth=6.0):
    """Inline XT30 (no panel mount): rectangular pocket on chassis floor
    that the connector head sits flush into so the bulk doesn't snag."""
    return workplane.rect(w, l).cutBlind(-depth)
```

---

## 6. Panel Cutouts (Switches, Network, USB, Barrel)

```python
def estop_cutout(workplane):
    """Mxuteuk HB2-ES544 panel-mount 22 mm latching E-stop."""
    return workplane.hole(22.5)   # +0.5 clearance for thread bushing

def rj45_cutout(workplane):
    """Standard RJ-45 pass-through for L2 LiDAR Ethernet."""
    return workplane.rect(16.5, 14.0).cutThruAll()

def usb_a_passthrough(workplane):
    """USB 3.1 Type-A pass-through (RealSense D456 cable routing)."""
    return workplane.rect(13.5, 6.5).cutThruAll()

def barrel_jack_5525(workplane):
    """5.5 x 2.5 mm barrel jack (Jetson power input)."""
    # Standard panel-mount barrel jack: 8 mm hole + 11 mm flat-to-flat
    # for anti-rotation. Use hole + small flat or just round hole + nut.
    return workplane.hole(8.5)

def fuse_holder_class_t(workplane):
    """Class T 30A fuse holder panel mount (battery feed inline)."""
    # Common panel-mount fuse holder: 13 mm dia. round body, 11 mm flats
    return workplane.hole(13.5)
```

---

## 7. Signal Connector Pockets

```python
def jst_xh_header(workplane, pins=4, orient="vertical"):
    """JST-XH 2.54 mm pitch header footprint. Pocket sized so a panel-
    mount JST-XH plug seats flush. Through-PCB headers use the same
    pitch but no pocket needed."""
    # JST-XH body width = pins * 2.50 + 1.94 (per JST datasheet)
    body_w = pins * 2.50 + 1.94
    body_l = 7.6  # standard body length
    if orient == "vertical":
        return workplane.rect(body_w, body_l).cutBlind(-5.0)
    else:
        return workplane.rect(body_l, body_w).cutBlind(-5.0)
```

---

## 8. Sensor Mounts

```python
# Intel RealSense D456 (front-facing depth + RGB + IMU)
D456 = {
    "l": 124.0, "w": 26.0, "h": 29.0,   # depth camera body
    "mount_holes": [  # M3 corners (per Intel D4xx mount datasheet)
        ( 90.0/2,  0), (-90.0/2,  0),    # standard tripod-style M3 pair
    ],
    "lens_offset": 14.0,  # IR projector to center
}

def d456_bracket_face(workplane):
    """Mounting face for D456: 2x M3 with heat-set inserts."""
    return (workplane
            .pushPoints(D456["mount_holes"])
            .circle(RUTHEX["M3"]["boss_od"]/2).extrude(8.0)
            .pushPoints(D456["mount_holes"])
            .hole(RUTHEX["M3"]["bore"]))

# Unitree L2 LiDAR top-mount riser
L2_LIDAR = {
    "base_od": 60.0,      # cylindrical base diameter (verify on part)
    "bolt_circle_d": 50.0,  # M3 mounting bolt circle (verify)
    "n_bolts": 4,
    "riser_h_default": 80.0,  # 5-10 cm above chassis
}

def l2_riser_top(workplane):
    """Top face of L2 LiDAR riser: 4x M3 on a 50 mm bolt circle."""
    import math
    pts = []
    r = L2_LIDAR["bolt_circle_d"] / 2
    for i in range(L2_LIDAR["n_bolts"]):
        a = 2 * math.pi * i / L2_LIDAR["n_bolts"]
        pts.append((r * math.cos(a), r * math.sin(a)))
    return (workplane
            .pushPoints(pts)
            .circle(RUTHEX["M3"]["boss_od"]/2).extrude(8.0)
            .pushPoints(pts)
            .hole(RUTHEX["M3"]["bore"]))

# MPU-6050 on GY-521 breakout board
GY521 = {
    "l": 21.5, "w": 16.5,
    "hole_pitch_x": 15.5, "hole_pitch_y": 0,  # 2-hole mount (some boards)
    "hole_d": 3.2,
}

def gy521_mount(workplane):
    """GY-521 (MPU-6050) 2-hole mount with M3 clearance."""
    return (workplane
            .pushPoints([(GY521["hole_pitch_x"]/2, 0),
                         (-GY521["hole_pitch_x"]/2, 0)])
            .hole(GY521["hole_d"]))
```

**Verify L2 LiDAR bolt circle on real part before committing.** Datasheets
for Unitree L2 are sparse; the 50 mm circle is a placeholder — measure with
calipers.

---

## 8b. Foot Pads + Strain Relief (TPU 95A)

```python
# Foot pad — absorbs ground-strike impact + adds floor grip
FOOT_PAD = {
    "od":          35.0,    # foot diameter
    "h":           8.0,     # pad thickness (5-10 mm typical)
    "tread_d":     2.0,     # tread groove diameter
    "tread_pitch": 6.0,     # grid spacing
    "mount_h":     4.0,     # M3 mounting hole depth (into tibia tip)
}

def foot_pad_tpu(workplane):
    """Domed TPU foot pad. Mounts to tibia tip via M3 from above.
    Concentric tread grooves on bottom for floor grip."""
    pad = (workplane
           .circle(FOOT_PAD["od"] / 2)
           .extrude(FOOT_PAD["h"])
           .edges("|Z").fillet(2.0)  # rounded sidewall
           .faces("<Z").fillet(1.5)) # rounded bottom edge

    # Tread grooves (concentric rings on bottom face)
    pad = (pad.faces("<Z").workplane()
           .pushPoints([(r, 0) for r in [5.0, 10.0, 15.0]])
           .circle(FOOT_PAD["tread_d"] / 2)
           .cutBlind(-1.5))

    # Top M3 mount (heat-set insert from PA6-CF tibia engages this hole)
    pad = (pad.faces(">Z").workplane()
           .hole(3.4))   # M3 clearance — bolt threads into tibia insert

    return pad

# Cable strain relief — TPU sleeve at servo wire entry
STRAIN_RELIEF = {
    "bore":         5.0,    # wire bundle OD (3-wire JST + jacket)
    "od":           10.0,   # outer dia
    "l":            15.0,   # length along cable
    "flange_od":    14.0,   # snap-into-bracket flange
    "flange_t":     2.0,
}

def cable_strain_relief_tpu(workplane):
    """TPU cable boot. Inner bore grips wire bundle, flange snaps into
    a 14 mm hole in the PA6-CF bracket."""
    sr = (workplane
          .circle(STRAIN_RELIEF["od"] / 2)
          .extrude(STRAIN_RELIEF["l"]))
    # Flange at base
    sr = (sr.faces("<Z").workplane()
          .circle(STRAIN_RELIEF["flange_od"] / 2)
          .extrude(-STRAIN_RELIEF["flange_t"]))
    # Through-bore for cable
    sr = (sr.faces(">Z").workplane()
          .hole(STRAIN_RELIEF["bore"]))
    return sr
```

**Print orientation note for both:** TPU prints best with the cable bore
**vertical** (Z axis). Layer lines wrap around the bore = stronger pull
resistance. Foot pad prints dome-up (mounting face on bed).

---

## 9. PCB Mounts

```python
# Teensy 4.1
TEENSY_41 = {
    "l": 61.0, "w": 18.0,
    "mount_holes": [(58.0/2, 0), (-58.0/2, 0)],  # 2 holes along long axis
    "hole_d": 2.6,  # M2.5 clearance
}

# Arduino Nano
NANO = {
    "l": 43.2, "w": 17.8,
    "mount_holes": [( 15.2,  6.4), ( 15.2, -6.4),
                    (-15.2,  6.4), (-15.2, -6.4)],
    "hole_d": 1.6,  # M1.6 or M2 clearance
}

# INA226 breakout module (Adafruit / generic)
INA226 = {
    "l": 25.4, "w": 20.3,
    "mount_holes": [(20.3/2,  15.2/2), (20.3/2, -15.2/2),
                    (-20.3/2, 15.2/2), (-20.3/2, -15.2/2)],
    "hole_d": 2.6,
}

def pcb_mount(workplane, spec, standoff_h=8.0, insert="M2.5"):
    """Generic PCB-mount boss pattern. Pass one of the dicts above."""
    bore = RUTHEX[insert]["bore"]
    boss_od = RUTHEX[insert]["boss_od"]
    return (workplane
            .pushPoints(spec["mount_holes"])
            .circle(boss_od/2).extrude(standoff_h)
            .pushPoints(spec["mount_holes"])
            .hole(bore))
```

---

## 10. Leg Rail Star-Injection Pattern

Power architecture calls for 4 XT30 injection points along the 7.5V leg
rail, each with a 1000 µF / 25V bulk cap nearby. Helps soak servo impact
transients near point of load.

```python
# 1000 µF / 25V radial cap (e.g., Panasonic EEU-FR1E102) is ~12.5 mm OD,
# 25 mm tall, 5 mm lead pitch
CAP_1000UF_25V = {"od": 13.0, "h": 26.0, "lead_pitch": 5.0}

def leg_rail_injection_strip(workplane, n_points=4, spacing=80.0):
    """N XT30 cutouts + cap pockets evenly spaced along a strip.
    spacing is center-to-center between injection points."""
    pts = [(i * spacing - (n_points-1)*spacing/2, 0)
           for i in range(n_points)]
    wp = workplane
    for x, y in pts:
        # XT30 cutout
        wp = (wp.faces(">Z").workplane().center(x, y)
              .rect(10.0, 5.5).cutThruAll())
        # Cap pocket alongside
        wp = (wp.faces(">Z").workplane().center(x, y + 12.0)
              .circle(CAP_1000UF_25V["od"]/2 + 0.3)
              .cutBlind(-CAP_1000UF_25V["h"] - 2.0))
    return wp
```

---

## 10b. Pololu Buck Module Footprint

All Pololu D42V110-class + D24V22-class + D42V55-class regulators on this
build share a near-identical PCB footprint: ~26 × 26 mm body with 4× 2.54 mm
header pins (Vin / GND / Vout / EN). When mounting a Pololu module to a 3D-
printed chassis carrier (instead of soldering to PCB v6 directly), use this.

```python
POLOLU_42V110 = {  # D42V110F7 / D42V110F12
    "body_w": 25.4, "body_l": 25.4, "body_h": 13.0,
    "header_pitch": 2.54,
    "n_pins": 4,        # Vin / GND / Vout / EN
    "pin_offset_y": 2.54,  # pin row offset from edge
    "mount_holes": [(11.4, 0), (-11.4, 0)],  # 2x M3 corners (some variants)
    "mount_hole_d": 3.4,
}

POLOLU_24V22 = {  # D24V22F12 (L2 LiDAR dedicated)
    "body_w": 20.3, "body_l": 17.8, "body_h": 11.0,
    "header_pitch": 2.54,
    "n_pins": 4,
    "mount_holes": [],  # Smaller modules often have no mount holes
}

POLOLU_42V55 = {  # D42V55F12 (Jetson) / D42V55F7 (arm reserved)
    "body_w": 17.8, "body_l": 22.9, "body_h": 11.0,
    "header_pitch": 2.54,
    "n_pins": 4,
    "mount_holes": [],
}

def pololu_carrier_pocket(workplane, model_dict, standoff_h=4.0):
    """Pocket for a Pololu module sitting on header pins through a printed
    carrier. Standoff height = clearance under PCB so pin tails don't
    bottom-out. Add caller-side header strip holes separately."""
    spec = model_dict
    pocket_w = spec["body_w"] + 1.0  # 0.5 mm clearance each side
    pocket_l = spec["body_l"] + 1.0
    return (workplane
            .rect(pocket_w, pocket_l)
            .cutBlind(-(spec["body_h"] + 1.0)))
```

**Footprint verify-on-receipt:** Pololu spins module revs without renaming;
caliper-measure the actual board against `body_w` / `body_l` / mount-hole
pattern before committing the carrier print. Pololu PDFs show the footprint
but the cap heights vary between revisions.

---

## 10c. LC Filter Carrier Pocket (L2 LiDAR rail)

Between the Pololu D24V22F12 and the L2 LiDAR input: 22 µH series choke +
470 µF / 25V shunt cap. Suppresses buck switching ripple (~400 kHz) so
UDP packet loss on L2 stays zero.

```python
# Standard radial choke + electrolytic cap pocket
LC_FILTER = {
    "choke_od":     12.0,    # 22 µH 2A radial — typically 10-12 mm body
    "choke_h":      10.0,
    "choke_lead_pitch": 5.0,
    "cap_od":       10.0,    # 470 µF / 25V radial — 8-10 mm OD typical
    "cap_h":        20.0,
    "cap_lead_pitch": 3.5,
}

def lc_filter_pocket(workplane):
    """Carrier pocket for the L2-rail LC filter (choke + cap side-by-side)."""
    wp = (workplane
          .center(-7, 0)
          .circle(LC_FILTER["choke_od"]/2 + 0.5)
          .cutBlind(-LC_FILTER["choke_h"] - 1.0))
    wp = (wp.workplane()
          .center(14, 0)  # 14 mm to the right of choke
          .circle(LC_FILTER["cap_od"]/2 + 0.5)
          .cutBlind(-LC_FILTER["cap_h"] - 1.0))
    return wp
```

---

## 10d. Jetson Orin Nano Antenna Mount (P3766)

P3766 dev kit ships with WiFi 5 + BT 5.1 on a built-in module that needs
**two external antennas via U.FL → SMA pigtails**. Standard wireless antenna
panel hole = 6.3 mm with M6×0.75 thread (or 6.5 mm clearance for a press-on
SMA bulkhead). Keep antennas ≥ 30 mm apart for MIMO diversity.

```python
ANTENNA_MOUNT = {
    "hole_d":       6.5,     # SMA bulkhead clearance
    "spacing":      40.0,    # antenna spacing (≥30 mm for diversity)
    "ground_d":     10.0,    # washer + nut footprint
}

def antenna_pair_panel(workplane):
    """Two SMA bulkhead holes for WiFi + BT antennas, MIMO-spaced."""
    return (workplane
            .pushPoints([(ANTENNA_MOUNT["spacing"]/2, 0),
                         (-ANTENNA_MOUNT["spacing"]/2, 0)])
            .hole(ANTENNA_MOUNT["hole_d"]))
```

---

## 10e. WS2812B Status LED Strip Mount

`docs/notes-qol-features.md` §8 proposes an Arduino-Nano-driven RGB status
LED for at-a-glance robot state. WS2812B addressable strip is the standard
pick — single data wire, daisy-chainable, 5 V power.

```python
# WS2812B standard pixel pitch on a strip
WS2812B = {
    "pixel_pitch":  10.0,    # 60 LEDs/m = 16.7 mm; 144 LEDs/m = 6.9 mm; common 100/m = 10 mm
    "strip_w":      10.0,    # PCB strip width (varies 8-12 mm)
    "strip_h":      2.5,     # PCB + LED stack height
    "diffuser_t":   1.5,     # PETG translucent diffuser thickness
}

def ws2812b_strip_pocket(workplane, n_pixels=5):
    """Recessed channel for a WS2812B strip with diffuser slot above.
    Print the chassis panel face-up; print the diffuser separately in
    translucent PETG accent (white)."""
    strip_l = n_pixels * WS2812B["pixel_pitch"] + 4.0
    # Strip pocket (recess for the LED PCB)
    wp = (workplane
          .rect(strip_l, WS2812B["strip_w"] + 1.0)
          .cutBlind(-WS2812B["strip_h"] - 0.5))
    # Diffuser slot above (frame for a snap-in PETG window)
    wp = (wp.faces(">Z").workplane()
          .rect(strip_l + 2.0, WS2812B["strip_w"] + 3.0)
          .cutBlind(-WS2812B["diffuser_t"]))
    # Wire pass-through at one end (3 wires: +5V, GND, DIN)
    wp = (wp.faces("<Z").workplane()
          .center(strip_l/2 + 2.0, 0)
          .rect(4.0, 6.0)
          .cutThruAll())
    return wp
```

**Print orientation:** chassis panel flat on bed, LED channel face-up.
Diffuser separately in **PETG accent (white)**, single-layer or 0.6 mm
solid wall for translucency. Snap-fit into the frame slot.

---

## 10f. Servo Zero-Position Calibration Jig

`docs/notes-virtual-view-autocal.md` §2 proposes auto-detecting servo zero
offsets by commanding each leg to a known reference posture (e.g., tibia
against a printed jig under the chassis), reading `/joint_states`, storing
the offset. Avoids per-joint human-tweak calibration.

```python
# Reference-posture jig for hip + femur + tibia zero on one leg
# Defaults are placeholders — measure actual leg link lengths in OnShape first
LEG_REF_POSTURE = {
    "hip_to_femur_offset":   60.0,   # mm, hip pivot to femur servo axis
    "femur_to_tibia_offset": 80.0,   # mm, femur servo axis to tibia servo axis
    "tibia_to_foot_offset":  100.0,  # mm, tibia servo axis to foot tip
    "jig_block_w":           30.0,
    "jig_block_h":           20.0,
    "alignment_pin_d":       5.0,    # 5 mm dowel pin between jig + chassis
    "alignment_pin_l":       15.0,
}

def leg_zero_jig(workplane):
    """Block that sits under the chassis. Each leg's tibia rests against
    a specific shoulder on the block — known posture, calipered offsets
    feed the auto-cal routine. One jig serves all 4 legs symmetrically.

    PRINT ORIENTATION: flat-side-down. PETG-CF preferred (dimensional
    stability matters more than impact resistance for a jig)."""
    # Base plate
    L = 200.0  # span across chassis floor
    W = 180.0
    base = (workplane
            .box(L, W, LEG_REF_POSTURE["jig_block_h"],
                 centered=(True, True, False))
            .edges("|Z").fillet(3.0))

    # 4 tibia-rest shoulders, one per leg corner
    for x_off in (L/2 - 30, -(L/2 - 30)):
        for y_off in (W/2 - 30, -(W/2 - 30)):
            base = (base.faces(">Z").workplane()
                    .center(x_off, y_off)
                    .rect(LEG_REF_POSTURE["jig_block_w"],
                          LEG_REF_POSTURE["jig_block_w"])
                    .extrude(LEG_REF_POSTURE["jig_block_h"]))

    # Center 2x alignment pin holes (mate to chassis-floor pegs for repeatability)
    base = (base.faces(">Z").workplane()
            .pushPoints([(L/4, 0), (-L/4, 0)])
            .hole(LEG_REF_POSTURE["alignment_pin_d"] + 0.15))  # locational fit

    return base
```

**Workflow:**

1. Print jig once (~3-4 h in PETG-CF).
2. Place under chassis with alignment pins through matching chassis-floor
   holes (chassis-side holes get the same `alignment_pin_d + 0.15` clearance).
3. Run `ros2 service call /calibration/leg_zero std_srvs/srv/Trigger` —
   commands each leg's tibia into contact with its jig shoulder at low
   torque, reads `/joint_states`, computes offset vs URDF nominal, persists
   to `~/.nova/calibration/leg_zero_<date>.yaml`.
4. Bringup loader reads the most-recent file on boot.

**Caveat:** the dimensions above are placeholders. Measure femur + tibia
lengths in OnShape (or with calipers on the redesigned leg) before printing
the jig. Wrong jig dimensions = wrong zero offsets = systemic IK bias.

---

## 11. Workflow Rules (NovaSM3-specific)

### First-Article Validation Gate

Before batch-printing any structural part (leg link, hip bracket):

1. Print **one** copy in **PA6-CF** with target settings.
2. Verify dimensionally with calipers: bearing OD seat, servo back-shaft
   relief, mount hole spacing.
3. Press-fit a real **688ZZ bearing** into the seat — should require
   firm thumb pressure, not arbor press; should not spin freely.
4. Mount a **real STS3215** in the pocket — flange should sit flat, no
   rocking, M2 self-tappers should bite cleanly into Ruthex inserts.
5. Apply mechanical load equivalent to a slow squat cycle (~5× body
   weight on the joint) — listen for layer-line cracks.

Only after these pass do you queue the batch.

### Fiber-Orientation Annotation

PA6-CF and PETG-CF derive most of their strength **along the fiber axis**
(roughly XY in-plane direction during extrusion). For load-bearing parts,
add an explicit comment in the CadQuery script noting the intended print
orientation so the Bambu Studio operator slices correctly:

```python
# PRINT ORIENTATION:
#   Place flat back face on bed (+Z is up in CAD).
#   Long axis of part = X in CAD = primary load direction = fibers aligned.
#   DO NOT print on end — interlayer adhesion will be the failure plane.
```

### Drier Discipline

Add to the script header for any PA6-CF / PETG-CF part:

```python
# MATERIAL: PA6-CF (Bambu PolyMide PA6-CF or similar)
# DRIER:    24 h at 70 C immediately before printing.
# BED PREP: Bambu liquid glue, 15 min bed soak at 100 C.
```

If the operator skips drier time, **the part will fail mechanically**
within 1-2 weeks of use even if it prints cleanly. Bake this into the
delivery message at Phase 3.

### Build-Volume Check

Before exporting, verify the part fits the P1S envelope:

```python
bb = result.val().BoundingBox()
assert bb.xlen <= build_x and bb.ylen <= build_y and bb.zlen <= build_z, \
    f"Part {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} exceeds P1S volume"
```

---

## Bearing-Fit Field Tips

Stock pattern in §3 uses +0.05 mm clearance. Real-world calibration on
PA6-CF / Bambu P1S often lands at **+0.1 mm on bearing ID** for hand-
pressure press-fit (no arbor needed):

- Print pocket at nominal + 0.1 mm. Test with a real 688ZZ.
- **Too loose?** CA glue (cyanoacrylate) gap-fill, hold 30 s. Reliable.
- **Too tight?** Ream with a drill bit one step under the pocket
  diameter. PA6-CF reams cleanly; PETG-CF gummier.
- Press only on the **outer race** when seating. Inner-race pressure
  brinells the balls and shortens bearing life.

## Reference Files in Project

When designing a NovaSM3 part, also read:

**In `~/codebases/NOVA/proj/`:**
- `BOM.md` — confirms part numbers, voltages, quantities
- `docs/power-budget.md` — current draw, transient loads → cap sizing
- `docs/setup-servos.md` — STS3215 bus IDs, calibration ranges
- `hardware/cad/README.md` — existing CAD workflow, OnShape pointers
- `hardware/pcb-mods/README.md` — PCB v6 connector placement
- `hardware/wiring/README.md` — connector pitches, strain-relief locations

**Outside `proj/` (sibling folders in `~/codebases/NOVA/`):**
- `nova-sm3-upstream/` — Chris Locke's reference build (STL only, no STEP)
- `nova_sts3215_redesign/` — OpenSCAD leg-joint redesign (current WIP)
- `feetech_servo_models/` — STS3215 STEP from GrabCAD / Feetech
- `original_body_files/` — stock NovaSM3 chassis geometry
- `modified_stl/` — in-progress modified STLs
- `Unitree_LiDAR/` — L2 reference geometry + mounting docs

If a dimension you need isn't in any of those, **caliper-measure the
real part** before committing it to a printed bracket. Datasheets lie;
calipers don't. Manufacturer batch-to-batch variation on the STS3215 is
±0.1 mm — never trust a single datasheet number for press-fit work.
