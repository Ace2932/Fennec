#!/usr/bin/env bash
# SessionStart: surface repo state (git HEAD, dirty count, active board DRC).
set -euo pipefail

JQ=/usr/bin/jq
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BOARD="$ROOT/hardware/pcb-mods/nova_pcb_v6_power_v2"

commit=$(git -C "$ROOT" log -1 --format='%h %s (%cr)' 2>/dev/null || echo 'n/a')
branch=$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '-')
dirty=$(git -C "$ROOT" status --porcelain 2>/dev/null | wc -l | tr -d ' ')

drc='no report (run /drc)'
r="$BOARD/nova_pcb_v6_power_v2-drc.rpt"
if [ -f "$r" ]; then
  drc=$(grep -oE 'Found [0-9]+ DRC violations' "$r" | head -1 || true)
fi

ctx="Fennec — ${branch} @ ${commit} | uncommitted files: ${dirty} | active board (v6 power v2) DRC: ${drc}"
"$JQ" -n --arg c "$ctx" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$c}}'
