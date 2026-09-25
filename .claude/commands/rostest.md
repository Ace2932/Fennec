---
description: Run all ROS2 pytest suites (nova_ops + nova_locomotion + nova_calibration)
allowed-tools: Bash
---
Run the ROS2 test suite — the same command as CLAUDE.md "Tests". Packages live at
`ros2_ws/src/<pkg>/<pkg>`, so PYTHONPATH must point at the package roots (NOT repo root —
`PYTHONPATH=.` collects 0 tests). No `--ignore` and no hand-picked file list: `test_preflight`
imports without rclpy now, and a subset list silently drops every test file added after it.
!`S=ros2_ws/src; PYTHONPATH=$S/nova_ops:$S/nova_locomotion:$S/nova_calibration:$S/nova_description .venv/bin/python -m pytest $S/nova_ops/test $S/nova_locomotion/test $S/nova_calibration/test -q 2>&1 | tail -15`

Report pass/fail counts and compare with the count recorded in CLAUDE.md — a drop means tests
stopped being collected, not that they pass. For any failure, quote the assertion and point at file:line.
