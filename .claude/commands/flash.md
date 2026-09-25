---
description: Build + deploy Teensy firmware to the Jetson over USB
allowed-tools: Bash
---
Deploy firmware via the project script (long-running — builds then flashes over the Jetson USB link):
!`bash ./scripts/deploy-firmware.sh`

Report build result and flash outcome. If it errors, quote the failing step.
