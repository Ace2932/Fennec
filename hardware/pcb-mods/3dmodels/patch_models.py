#!/usr/bin/env python3
"""Insert (model ...) entries into footprints that lack them. Idempotent:
strips ALL model blocks inside the target footprints (they had none
originally) before inserting, so it is safe to re-run with new offsets."""
import re
from pathlib import Path

def model_sexpr(path, off, rot=(0,0,0), scale=(1,1,1)):
    return (f'\t\t(model "{path}"\n'
            f'\t\t\t(offset (xyz {off[0]} {off[1]} {off[2]}))\n'
            f'\t\t\t(scale (xyz {scale[0]} {scale[1]} {scale[2]}))\n'
            f'\t\t\t(rotate (xyz {rot[0]} {rot[1]} {rot[2]}))\n'
            f'\t\t)\n')

def matching_paren(s, start):
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '(': depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0: return i
    raise ValueError("unbalanced")

def strip_models(block):
    out = block
    while True:
        m = re.search(r'[ \t]*\(model[\s"]', out)
        if not m: return out
        end = matching_paren(out, out.index('(', m.start()))
        # eat trailing newline
        e = end + 1
        if e < len(out) and out[e] == '\n': e += 1
        out = out[:m.start()] + out[e:]

def patch(board, fpname, models):
    s = board.read_text()
    insert_text = ''.join(model_sexpr(*m) for m in models)
    count = 0
    pos = 0
    while True:
        m = re.search(r'\(footprint\s+"' + re.escape(fpname) + '"', s[pos:])
        if not m: break
        start = pos + m.start()
        end = matching_paren(s, start)
        block = strip_models(s[start:end])
        newblock = block + insert_text + '\t'
        s = s[:start] + newblock + s[end:]
        pos = start + len(newblock) + 1
        count += 1
    board.write_text(s)
    print(f"{board.name}: {fpname} -> {count} footprints patched")

K = "${KICAD9_3DMODEL_DIR}"
P = "${KIPRJMOD}/../3dmodels"

# Board paths resolve from this script's own location, so the script runs from
# any checkout and any cwd: 3dmodels/ -> pcb-mods/ -> <board dir>/.
PCB_MODS = Path(__file__).resolve().parent.parent
POWER = PCB_MODS / "nova_pcb_v6_power_v2" / "nova_pcb_v6_power_v2.kicad_pcb"
LOGIC = PCB_MODS / "nova_pcb_v6_logic" / "nova_pcb_v6_logic.kicad_pcb"

# Buck station: two XT30 (pin1 rect pads at (-2.5,±5), pins along +x, lib native
# orientation, model offset y = -footprint y) + 1x02 sense header at (8,∓1.27).
XTS = (0.6944, 0.6944, 0.6944)  # XT60 model scaled to XT30 (5.0/7.2 pitch)
XT60 = f"{K}/Connector_AMASS.3dshapes/AMASS_XT60-M_1x02_P7.2mm_Vertical.step"
XT30 = f"{P}/XT30-M.step"
patch(POWER, "nova_v6:Buck_Offboard_Terminal_2xXT30", [
    (XT30, (-5.5, -5, 0), (0, 0, 90)),
    (XT30, (-5.5, 5, 0), (0, 0, 90)),
    (f"{K}/Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x02_P2.54mm_Vertical.step", (8, 1.27, 0)),
])

# Standalone XT30 lib footprints: real XT30-M STEP (user-supplied, GrabCAD)
patch(POWER, "Connector_AMASS:AMASS_XT30U-M_1x02_P5.0mm_Vertical", [
    (XT30, (-3, 0, 0), (0, 0, 90)),
])

# INA226 breakout: stock 1x04 header (native pins along +y -> rotate z 90 to run
# along +x from pin1 at (-5.08,6.5)) + module slab WRL (self-positioned).
patch(POWER, "nova_v6:INA226_Module_Breakout", [
    (f"{K}/Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x04_P2.54mm_Vertical.step", (-5.08, -6.5, 0), (0, 0, 90)),
    (f"{P}/INA226_Module.wrl", (0, 0, 0)),
])

# Teensy 4.1: XenGi model, module centered at fp origin, long axis along x,
# USB at -x; nova fp long axis along y, USB at -y -> rotate z -90 (try, verify).
patch(LOGIC, "nova_v6:Teensy_4.1", [
    (f"{P}/Teensy_4.1_Headers.step", (0, 0, 3.3), (0, 0, 90)),
])

# Arduino Nano: KiCad 9 ships no Module.3dshapes STEP -> WRL placeholder
# built in the lib footprint frame (pin1 at origin).
patch(LOGIC, "Module:Arduino_Nano", [
    (f"{P}/Arduino_Nano_Classic.step", (0, 0, 9.5), (-90, 0, 90)),
    (f"{K}/Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x15_P2.54mm_Vertical.step", (0, 0, 0)),
    (f"{K}/Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x15_P2.54mm_Vertical.step", (15.24, 0, 0)),
])
