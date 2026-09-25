---
description: Run DRC + ERC on the active power board and summarize violations
allowed-tools: Bash
---
Active board: `hardware/pcb-mods/nova_pcb_v6_power_v2/`

DRC (PCB + schematic parity):
!`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc --schematic-parity --severity-error --severity-warning -o ./hardware/pcb-mods/nova_pcb_v6_power_v2/nova_pcb_v6_power_v2-drc.rpt ./hardware/pcb-mods/nova_pcb_v6_power_v2/nova_pcb_v6_power_v2.kicad_pcb && cat ./hardware/pcb-mods/nova_pcb_v6_power_v2/nova_pcb_v6_power_v2-drc.rpt`

ERC (schematic):
!`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc --severity-error --severity-warning -o ./hardware/pcb-mods/nova_pcb_v6_power_v2/nova_pcb_v6_power_v2-erc.rpt ./hardware/pcb-mods/nova_pcb_v6_power_v2/nova_pcb_v6_power_v2.kicad_sch && cat ./hardware/pcb-mods/nova_pcb_v6_power_v2/nova_pcb_v6_power_v2-erc.rpt`

Summarize: violation counts, then list each error/warning grouped by type with location. Flag anything actionable.
