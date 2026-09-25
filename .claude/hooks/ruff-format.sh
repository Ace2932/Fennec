#!/usr/bin/env bash
# PostToolUse (Edit|Write|MultiEdit): auto-format ROS2 Python with ruff.
# Only touches .py files under ros2_ws. Silent on success.
set -euo pipefail

RUFF="$(cd "$(dirname "$0")/../.." && pwd)/.venv/bin/ruff"
JQ=/usr/bin/jq

f=$("$JQ" -r '.tool_input.file_path // empty')
[ -n "$f" ] || exit 0
case "$f" in
  */ros2_ws/*.py) ;;
  *) exit 0 ;;
esac
[ -f "$f" ] || exit 0

"$RUFF" format "$f" >/dev/null 2>&1 || true
"$RUFF" check --fix "$f" >/dev/null 2>&1 || true
exit 0
