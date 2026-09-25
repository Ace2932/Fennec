#!/usr/bin/env bash
# Status line: model | git branch+dirty | active board.
set -euo pipefail
JQ=/usr/bin/jq
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

in=$(cat)
model=$(printf '%s' "$in" | "$JQ" -r '.model.display_name // "?"' 2>/dev/null || echo '?')

branch=$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '-')
dirty=$(git -C "$ROOT" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
dirtyflag=""
[ "${dirty:-0}" != "0" ] && dirtyflag="*${dirty}"

printf '%s | fennec:%s%s | board:v6_power_v2' "$model" "$branch" "$dirtyflag"
