#!/usr/bin/env bash
# One-time-per-clone setup: register the custom git merge drivers this repo uses.
# Merge-driver *definitions* live in .git/config (per clone, NOT committed), so
# each clone runs this once. The .gitattributes that references them IS
# committed. Safe to re-run.
#
#   bash scripts/setup-git-drivers.sh
set -e
ROOT="$(git rev-parse --show-toplevel)"

# rebuild-preview: regenerate the assembly-preview STLs on merge instead of
# hitting a binary conflict every time (see scripts/rebuild-preview-merge.sh).
git config merge.rebuild-preview.name "regenerate assembly-preview STLs (build artifact)"
git config merge.rebuild-preview.driver "'$ROOT/scripts/rebuild-preview-merge.sh' %A %P"

echo "OK: registered merge driver 'rebuild-preview' for this clone."
echo "    (referenced by .gitattributes; preview STLs now auto-rebuild on merge)"
