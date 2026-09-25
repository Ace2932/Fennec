#!/usr/bin/env bash
# PostToolUse (Edit|Write): run KiCad DRC on edited .kicad_pcb, feed report to Claude.
set -euo pipefail

KICAD=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
JQ=/usr/bin/jq

f=$("$JQ" -r '.tool_input.file_path // empty')
[ -n "$f" ] || exit 0
case "$f" in
  *.kicad_pcb) ;;
  *) exit 0 ;;
esac
[ -f "$f" ] || exit 0

rpt="${f}-drc.rpt"
"$KICAD" pcb drc --schematic-parity --severity-error --exit-code-violations \
  -o "$rpt" "$f" >/dev/null 2>&1 || true

[ -f "$rpt" ] || exit 0
ctx="KiCad DRC report for $(basename "$f") (errors only):"$'\n'"$(cat "$rpt")"
"$JQ" -n --arg c "$ctx" \
  '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$c}}'
exit 0
