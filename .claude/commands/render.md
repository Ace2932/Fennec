---
description: Render an STL (or .scad) to iso/front/top PNG views and inspect
argument-hint: <path-to-stl-or-scad>
allowed-tools: Bash, Read
---
Render the part: $ARGUMENTS

!`bash .claude/hooks/render_part.sh "$ARGUMENTS"`

Then Read each output PNG (iso/front/top) and describe the geometry, key features, and anything that looks off (thin walls, gaps, missing bosses).
