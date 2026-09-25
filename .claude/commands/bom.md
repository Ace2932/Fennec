---
description: Export BOM (CSV) for the active power board from its schematic
allowed-tools: Bash
---
Export the BOM from the active board schematic via kicad-cli:
!`mkdir -p ./hardware/pcb-mods/nova_pcb_v6_power_v2/bom && /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export bom --fields 'Reference,Value,Footprint,${QUANTITY},Manufacturer,MPN' --group-by Value -o ./hardware/pcb-mods/nova_pcb_v6_power_v2/bom/nova_pcb_v6_power_v2-bom.csv ./hardware/pcb-mods/nova_pcb_v6_power_v2/nova_pcb_v6_power_v2.kicad_sch && echo OK`

Confirm output path and line count. Note: this is the kicad-cli CSV BOM; the interactive placement HTML BOM tool isn't installed here — say so if I ask for it.
