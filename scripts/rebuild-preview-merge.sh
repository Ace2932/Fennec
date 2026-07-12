#!/usr/bin/env bash
# Git MERGE DRIVER for the tracked assembly-preview STLs.
#
# chassis_assembly_preview.stl / foot_assembly_preview.stl are regenerable
# build artifacts (preview_assembly.py output). Every branch rebuilds them, so
# a binary 3-way merge ALWAYS conflicts. Instead of conflicting, regenerate.
#
# Git merges the non-conflicting part .scad/.stl files into the working tree
# BEFORE invoking this driver, so by the time we run, the parts are already the
# correct merged versions -> re-running preview_assembly.py yields the true
# merged preview. We then hand git the freshly-built file as the merge result.
#
# Wired up by .gitattributes (merge=rebuild-preview) + a one-time
# `bash scripts/setup-git-drivers.sh` per clone.
#
# Args (from the driver config line): %A %P  ->  $1 = ours/output temp file,
#                                                 $2 = repo-relative pathname.
set -e
OURS="$1"
PATHNAME="$2"
ROOT="$(git rev-parse --show-toplevel)"
PY="$ROOT/.venv/bin/python"

# No venv (e.g. a CI/headless checkout) -> fail the driver so git falls back to
# a normal conflict rather than silently shipping a stale preview.
[ -x "$PY" ] || { echo "rebuild-preview: no .venv python at $PY -> conflict" >&2; exit 1; }

( cd "$ROOT/hardware/cad/chassis" && "$PY" preview_assembly.py ) >/dev/null 2>&1 \
  || { echo "rebuild-preview: preview_assembly.py failed -> conflict" >&2; exit 1; }

cp "$ROOT/$PATHNAME" "$OURS"   # git expects the merged result in %A
