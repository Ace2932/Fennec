#!/usr/bin/env bash
# flash-jetpack.sh
#
# Flash JetPack 6.x to a microSD card for the Jetson Orin Nano Super Dev Kit.
#
# STATUS: stub. Populate with the verified procedure once the Jetson arrives
# and JetPack 6.x has been flashed end-to-end on this hardware.
#
# Will wrap:
#   - Image download (sha256-verified) from NVIDIA Developer
#   - Card detection (refuse to write to the host system disk)
#   - dd / bs=4M / status=progress + sync
#   - Post-flash partition expansion
#   - Firmware-update reminder if the shipped firmware predates JetPack 6.x

set -euo pipefail

echo "[flash-jetpack.sh] stub — not yet implemented"
echo "  see docs/setup-jetson.md for the manual procedure"
exit 1
